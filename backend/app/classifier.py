"""
Gemini-powered job relevance classifier with Multi-Model Fallback + Local Rule Pre-filter.

After each scrape run (or manually), this module classifies jobs in batches
and marks irrelevant ones (non-IT / non-software) as REMOVED automatically.

Key features:
1. Fast Local Rule Pre-filter: Instantly removes obvious non-IT jobs (Air Ticketing,
   Tour Executive, Barista, Kitchen, Nurse, Retail Sales, etc.) without API calls.
2. Model Fallback Chain: Tries 'gemini-3.1-flash-lite', 'gemini-flash-lite-latest',
   'gemma-4-26b-a4b-it' if primary model hits rate/quota limits.
3. High Batch Capacity: 250 jobs per request -> entire scrape run classified in 1 request.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from app.config import GEMINI_API_KEY, GEMINI_BATCH_SIZE, GEMINI_MODEL
from app.db import engine
from app.models import Job

logger = logging.getLogger(__name__)

# Fallback models in priority order if primary model hits rate limits
_MODEL_FALLBACK_CHAIN = [
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemma-4-26b-a4b-it",
    "gemini-3.5-flash",
]

# Obvious non-IT title patterns for instant local filtering
_OBVIOUS_NON_TECH_PATTERNS = re.compile(
    r"\b("
    r"air ticketing|visa processing|tour executive|travel consultant|tour consultant|inbound tour|"
    r"barista|barman|bartender|kitchen|cook|chef|commis|waiter|waitress|steward|hostess|housekeeping|room boy|room attendant|"
    r"nurse|pharmacist|medical officer|doctor|dental|"
    r"driver|rider|delivery rider|chauffeur|"
    r"cashier|front office|receptionist|telecaller|"
    r"sales executive|sales officer|sales associate|retail sales|showroom sales|"
    r"beverage|restaurant|bakery"
    r")\b",
    re.IGNORECASE,
)

# ── Prompt ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a job relevance classifier for a personal tech job aggregator in Sri Lanka.

Your task: decide whether each job posting is RELEVANT or IRRELEVANT to the software/IT industry.

RELEVANT jobs (keep these: "keep": true):
- Software Engineer / Developer (junior, senior, intern, trainee, associate, lead)
- Web Developer (frontend, backend, full stack)
- Mobile Developer (Android, iOS, Flutter, React Native)
- QA / Test Engineer / Quality Assurance / Software Tester
- DevOps / Cloud / Infrastructure / System Admin / Network / Cybersecurity
- Data Engineer / Data Scientist / Data Analyst / AI / ML Engineer
- Tech-focused Interns, IT Interns, Software Interns, Trainee Engineers
- IT Project Managers, Business Analysts in Software/Tech, UI/UX Designers
- Any software, coding, or IT industry technical role

IRRELEVANT jobs (remove these: "keep": false):
- Travel / Aviation: Air ticketing officers, visa processing officers, tour executives
- Hospitality: Hotel staff, chefs, cooks, baristas, kitchen helpers, waiters
- Healthcare: Doctors, nurses, pharmacists, lab technicians
- Non-IT Sales & Marketing: Retail sales, showroom sales, direct sales (unless software/IT product sales)
- General Admin, HR, Receptionists, Clerks, Cashiers, Drivers, Factory workers
- Non-IT Engineering: Civil, mechanical, electrical (unless software/firmware/automation)
- Any role clearly outside the software/IT industry

Respond ONLY with a valid JSON array. Format: [{"id": <number>, "keep": <true|false>}, ...]
"""

_USER_PROMPT_TEMPLATE = """Classify these job postings. Return ONLY a JSON array.

Jobs:
{jobs_json}
"""


# ── Public API ───────────────────────────────────────────────────────

def classify_new_jobs(job_ids: list[int]) -> dict[str, int]:
    """
    Classify jobs by ID and auto-REMOVE irrelevant ones.

    Uses local rule pre-filtering + Gemini model fallback chain.
    """
    if not job_ids:
        return {"kept": 0, "removed": 0, "skipped": 0}

    logger.info("[classifier] Classifying %d jobs (batch size %d)", len(job_ids), GEMINI_BATCH_SIZE)

    # 1. Load jobs from DB
    with Session(engine) as session:
        jobs = session.query(Job).filter(Job.id.in_(job_ids)).all()  # type: ignore[attr-defined]
        job_map = {j.id: j for j in jobs}

    # 2. Local rule pre-filter for obvious non-tech jobs
    local_removed_ids: list[int] = []
    remaining_jobs: list[Job] = []

    for j in job_map.values():
        if _OBVIOUS_NON_TECH_PATTERNS.search(j.job_title):
            local_removed_ids.append(j.id)
        else:
            remaining_jobs.append(j)

    if local_removed_ids:
        _bulk_remove(local_removed_ids)
        logger.info("[classifier] Local pre-filter removed %d obvious non-IT jobs", len(local_removed_ids))

    total_kept = 0
    total_removed = len(local_removed_ids)
    total_skipped = 0

    if not remaining_jobs:
        return {"kept": 0, "removed": total_removed, "skipped": 0}

    if not GEMINI_API_KEY:
        logger.info("[classifier] GEMINI_API_KEY not set — skipping AI classification for remaining %d jobs", len(remaining_jobs))
        return {"kept": len(remaining_jobs), "removed": total_removed, "skipped": 0}

    # 3. Process remaining jobs in batches with Gemini AI
    remaining_ids = [j.id for j in remaining_jobs]
    batches = [remaining_ids[i : i + GEMINI_BATCH_SIZE] for i in range(0, len(remaining_ids), GEMINI_BATCH_SIZE)]

    for batch_num, batch_ids in enumerate(batches, 1):
        batch_jobs = [job_map[jid] for jid in batch_ids if jid in job_map]
        if not batch_jobs:
            continue

        decisions = _classify_batch_with_fallbacks(batch_jobs)

        if decisions is None:
            # AI failed all model fallbacks — keep as NEW
            total_skipped += len(batch_jobs)
            total_kept += len(batch_jobs)
            logger.warning("[classifier] Batch %d AI classification unavailable — kept as NEW", batch_num)
            continue

        # Apply AI decisions
        remove_ids = [jid for jid, keep in decisions.items() if not keep]
        keep_count = sum(1 for keep in decisions.values() if keep)
        unclassified = len(batch_jobs) - len(decisions)

        if remove_ids:
            _bulk_remove(remove_ids)

        total_kept += keep_count + unclassified
        total_removed += len(remove_ids)
        total_skipped += unclassified

    logger.info(
        "[classifier] Complete — total kept=%d, total removed=%d, skipped=%d",
        total_kept, total_removed, total_skipped,
    )
    return {"kept": total_kept, "removed": total_removed, "skipped": total_skipped}


# ── Internal AI call with model fallback chain ───────────────────────

def _classify_batch_with_fallbacks(jobs: list[Job]) -> Optional[dict[int, bool]]:
    """Try primary GEMINI_MODEL first, then fallback model chain on 429 errors."""
    models_to_try = [GEMINI_MODEL] + [m for m in _MODEL_FALLBACK_CHAIN if m != GEMINI_MODEL]

    for model_name in models_to_try:
        logger.info("[classifier] Attempting batch classification with model '%s'...", model_name)
        res = _classify_batch_single_model(jobs, model_name)
        if res is not None:
            return res
        logger.warning("[classifier] Model '%s' failed, trying fallback...", model_name)

    return None


def _classify_batch_single_model(jobs: list[Job], model_name: str) -> Optional[dict[int, bool]]:
    """Call Gemini API for a single model with backoff retry."""
    import time
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        job_entries = [{"id": j.id, "title": j.job_title, "company": j.company_name} for j in jobs]
        prompt = _USER_PROMPT_TEMPLATE.format(jobs_json=json.dumps(job_entries, ensure_ascii=False))
        full_prompt = f"{_SYSTEM_PROMPT}\n\n{prompt}"

        for attempt in range(1, 3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=8192,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = response.text.strip()
                decisions_list: list[dict] = json.loads(raw_text)
                return {item["id"]: bool(item["keep"]) for item in decisions_list if "id" in item and "keep" in item}
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "quota" in err_str.lower()) and attempt < 2:
                    time.sleep(2)
                    continue
                raise

    except Exception as e:
        logger.warning("[classifier] Model '%s' error: %s", model_name, e)
        return None


def _bulk_remove(job_ids: list[int]) -> None:
    """Set application_state = 'REMOVED' for a list of job IDs."""
    if not job_ids:
        return
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        jobs = session.query(Job).filter(Job.id.in_(job_ids)).all()  # type: ignore[attr-defined]
        for job in jobs:
            job.application_state = "REMOVED"
            job.state_updated_date = now
        session.commit()
    logger.debug("[classifier] Marked %d jobs as REMOVED", len(job_ids))
