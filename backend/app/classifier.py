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

from app.ai_prompt_defaults import SYSTEM_PROMPT_KEY, USER_PROMPT_KEY
from app.config import GEMINI_BATCH_SIZE
from app.db import engine
from app.gemini_models import list_available_gemini_models, model_rank
from app.models import AIPrompt, Job
from app.secrets import get_secret, set_secret

logger = logging.getLogger(__name__)

# Best-effort candidates are used only when model discovery itself is unavailable.
_MODEL_DISCOVERY_FALLBACKS = (
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemma-4-26b-a4b-it",
)

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

# ── Public API ───────────────────────────────────────────────────────


def classify_new_jobs(job_ids: list[int]) -> dict:
    """
    Classify jobs by ID and auto-REMOVE irrelevant ones.

    Uses local rule pre-filtering + Gemini model fallback chain.
    """
    if not job_ids:
        return {"kept": 0, "removed": 0, "skipped": 0}

    logger.info(
        "[classifier] Classifying %d jobs (batch size %d)",
        len(job_ids),
        GEMINI_BATCH_SIZE,
    )

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
        logger.info(
            "[classifier] Local pre-filter removed %d obvious non-IT jobs",
            len(local_removed_ids),
        )

    total_kept = 0
    total_removed = len(local_removed_ids)
    pending_ids: list[int] = []
    attempted_models: list[str] = []
    failure_messages: list[str] = []
    model_used: str | None = None

    if not remaining_jobs:
        return _classification_result(
            total_kept,
            total_removed,
            pending_ids,
            attempted_models,
            model_used,
        )

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY is not configured — skipping AI classification for remaining %d jobs. "
            "Postings will still be saved, just without AI filtering. "
            "Add a key on the Settings screen to enable this.",
            len(remaining_jobs),
        )
        pending_ids.extend(j.id for j in remaining_jobs if j.id is not None)
        total_kept += len(remaining_jobs)
        return _classification_result(
            total_kept,
            total_removed,
            pending_ids,
            attempted_models,
            model_used,
            "Gemini API key is not configured.",
        )

    selected_model = get_secret("GEMINI_MODEL")
    discovery_error: str | None = None
    try:
        available_models = list_available_gemini_models(api_key)
    except Exception as exc:
        available_models = [
            {"id": name, "display_name": name}
            for name in sorted(_MODEL_DISCOVERY_FALLBACKS, key=model_rank)
        ]
        discovery_error = _safe_error_message(exc)
        logger.warning(
            "[classifier] Could not discover available Gemini models; trying known fallbacks: %s",
            exc,
        )

    available_ids = [model["id"] for model in available_models]
    if selected_model and (
        discovery_error or not available_ids or selected_model in available_ids
    ):
        model_candidates = [selected_model]
        model_candidates.extend(
            model for model in available_ids if model != selected_model
        )
    else:
        model_candidates = available_ids

    if not model_candidates:
        pending_ids.extend(j.id for j in remaining_jobs if j.id is not None)
        total_kept += len(remaining_jobs)
        error = "No available Gemini models support content generation."
        if discovery_error:
            error = f"Could not discover Gemini models: {discovery_error}"
        return _classification_result(
            total_kept,
            total_removed,
            pending_ids,
            attempted_models,
            model_used,
            error,
        )

    # 3. Process remaining jobs in batches with Gemini AI
    remaining_ids = [j.id for j in remaining_jobs]
    batches = [
        remaining_ids[i : i + GEMINI_BATCH_SIZE]
        for i in range(0, len(remaining_ids), GEMINI_BATCH_SIZE)
    ]

    for batch_num, batch_ids in enumerate(batches, 1):
        batch_jobs = [job_map[jid] for jid in batch_ids if jid in job_map]
        if not batch_jobs:
            continue

        decisions, successful_model, tried_models, errors = (
            _classify_batch_with_fallbacks(batch_jobs, model_candidates)
        )
        for model in tried_models:
            if model not in attempted_models:
                attempted_models.append(model)

        if decisions is None:
            # Keep unclassified jobs unchanged and make them available for retry.
            total_kept += len(batch_jobs)
            pending_ids.extend(j.id for j in batch_jobs if j.id is not None)
            failure_messages.extend(errors)
            if not errors:
                failure_messages.append("No available model returned valid results.")
            logger.warning(
                "[classifier] Batch %d failed with all available models — kept as NEW: %s",
                batch_num,
                failure_messages[-1],
            )
            continue

        if successful_model:
            model_used = successful_model
            model_candidates.remove(successful_model)
            model_candidates.insert(0, successful_model)
            try:
                set_secret("GEMINI_MODEL", successful_model)
            except Exception:
                logger.exception(
                    "[classifier] Could not save working Gemini model '%s'",
                    successful_model,
                )

        # Apply AI decisions
        remove_ids = [jid for jid, keep in decisions.items() if not keep]
        keep_count = sum(1 for keep in decisions.values() if keep)

        if remove_ids:
            _bulk_remove(remove_ids)

        total_kept += keep_count
        total_removed += len(remove_ids)

    logger.info(
        "[classifier] Complete — total kept=%d, total removed=%d, skipped=%d",
        total_kept,
        total_removed,
        len(pending_ids),
    )
    error = None
    if pending_ids:
        models_text = ", ".join(attempted_models) or "available models"
        last_error = (
            failure_messages[-1] if failure_messages else "Unknown model error."
        )
        error = (
            f"AI filtering unsuccessful for {len(pending_ids)} job(s) after trying "
            f"{models_text}. Last error: {last_error}"
        )
    return _classification_result(
        total_kept,
        total_removed,
        pending_ids,
        attempted_models,
        model_used,
        error,
    )


# ── Internal AI call with model fallback chain ───────────────────────


def _classification_result(
    kept: int,
    removed: int,
    pending_job_ids: list[int],
    attempted_models: list[str],
    model_used: str | None,
    error: str | None = None,
) -> dict:
    return {
        "kept": kept,
        "removed": removed,
        "skipped": len(pending_job_ids),
        "success": not pending_job_ids,
        "status": "failed" if pending_job_ids else "completed",
        "error": (
            f"AI filtering unsuccessful: {error}" if error and pending_job_ids else None
        ),
        "pending_job_ids": pending_job_ids,
        "attempted_models": attempted_models,
        "model_used": model_used,
    }


def _safe_error_message(error: Exception) -> str:
    message = str(error).strip()
    return message[:300] if message else type(error).__name__


def _classify_batch_with_fallbacks(
    jobs: list[Job], model_candidates: list[str]
) -> tuple[Optional[dict[int, bool]], str | None, list[str], list[str]]:
    """Try the selected model first, then each other available model."""
    attempted: list[str] = []
    errors: list[str] = []
    for model_name in model_candidates:
        attempted.append(model_name)
        logger.info("[classifier] Attempting batch with model '%s'...", model_name)
        try:
            decisions = _classify_batch_single_model(jobs, model_name)
            return decisions, model_name, attempted, errors
        except Exception as exc:
            error = _safe_error_message(exc)
            errors.append(f"{model_name}: {error}")
            logger.warning("[classifier] Model '%s' failed: %s", model_name, error)
    return None, None, attempted, errors


def _classify_batch_single_model(jobs: list[Job], model_name: str) -> dict[int, bool]:
    """Call Gemini API for a single model with backoff retry."""
    import time

    try:
        from google import genai
        from google.genai import types

        api_key = get_secret("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        job_entries = [
            {"id": j.id, "title": j.job_title, "company": j.company_name} for j in jobs
        ]
        with Session(engine) as session:
            system_prompt = session.get(AIPrompt, SYSTEM_PROMPT_KEY)
            user_prompt = session.get(AIPrompt, USER_PROMPT_KEY)
            if system_prompt is None or user_prompt is None:
                raise RuntimeError(
                    "AI prompts have not been initialized in the database"
                )

        prompt = user_prompt.prompt.replace(
            "{jobs_json}",
            json.dumps(job_entries, ensure_ascii=False),
        )
        full_prompt = f"{system_prompt.prompt}\n\n{prompt}"

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
                raw_text = response.text
                if not isinstance(raw_text, str) or not raw_text.strip():
                    raise ValueError("Model returned an empty response.")
                decisions_list = json.loads(raw_text)
                expected_ids = {job.id for job in jobs}
                if not isinstance(decisions_list, list):
                    raise ValueError("Model response was not a JSON array.")

                decisions: dict[int, bool] = {}
                for item in decisions_list:
                    if (
                        not isinstance(item, dict)
                        or type(item.get("id")) is not int
                        or type(item.get("keep")) is not bool
                    ):
                        raise ValueError(
                            "Model response contained an invalid decision."
                        )
                    if item["id"] in decisions:
                        raise ValueError("Model response contained duplicate job IDs.")
                    decisions[item["id"]] = item["keep"]

                if set(decisions) != expected_ids:
                    raise ValueError(
                        "Model response did not classify every requested job."
                    )
                return decisions
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "quota" in err_str.lower()) and attempt < 2:
                    time.sleep(2)
                    continue
                raise

    except Exception:
        logger.exception("[classifier] Model '%s' request failed", model_name)
        raise


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
