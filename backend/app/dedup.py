"""
Deduplication logic.

Computes ``job_hash = sha256(normalized_company + normalized_title)`` and
decides whether a scraped posting is:

- **New job** -- no match -> insert ``Job`` + ``JobSource``.
- **Duplicate source** -- match within the dedup window -> add ``JobSource`` only.
- **New posting cycle** -- match but outside the dedup window -> insert new ``Job``.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import parser as dateutil_parser
from sqlmodel import Session, select

from app.config import DEDUP_WINDOW_DAYS
from app.models import Job, JobSource
from app.normalize import NormalizedPosting

logger = logging.getLogger(__name__)


# ── Hash computation ─────────────────────────────────────────────────

def compute_job_hash(company: str, title: str) -> str:
    """
    SHA-256 hash of normalized company + title.

    Both inputs are lowered and stripped to maximise collision rate
    across scrapers that may report slightly different casing.
    """
    key = f"{company.lower().strip()}|{title.lower().strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ── Date parsing helper ──────────────────────────────────────────────

def _parse_date(raw: Optional[str]) -> Optional[datetime]:
    """Best-effort parse of a raw date string into a UTC datetime."""
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw, fuzzy=True)
        # Make timezone-aware if it isn't already
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, OverflowError):
        return None


# ── Public API ───────────────────────────────────────────────────────

def dedup_and_insert(
    session: Session,
    posting: NormalizedPosting,
) -> str:
    """
    Insert a normalized posting into the DB with deduplication.

    Returns one of:
    - ``"new"``        -- a new Job row was created
    - ``"duplicate"``  -- only a new JobSource row was added to an existing Job
    """
    job_hash = compute_job_hash(posting.company_name, posting.job_title)
    posted_date = _parse_date(posting.posted_date_raw)

    # Look for existing jobs with the same hash
    statement = select(Job).where(Job.job_hash == job_hash)
    existing_jobs = session.exec(statement).all()

    if not existing_jobs:
        # ── Brand new job ────────────────────────────────────────
        return _insert_new_job(session, posting, job_hash, posted_date)

    # ── Check dedup window ───────────────────────────────────────
    # Find the most recent matching job
    best_match: Optional[Job] = None
    for job in existing_jobs:
        if _within_dedup_window(job.posted_date, posted_date):
            # Prefer the most recent match
            if best_match is None or (
                job.created_at and best_match.created_at
                and job.created_at > best_match.created_at
            ):
                best_match = job

    if best_match is not None:
        # Same posting, different source -> add JobSource only
        _add_source(session, best_match.id, posting)
        return "duplicate"

    # ── New posting cycle (same role re-posted after window) ─────
    return _insert_new_job(session, posting, job_hash, posted_date)


# ── Internal helpers ─────────────────────────────────────────────────

def _within_dedup_window(
    existing_date: Optional[datetime],
    new_date: Optional[datetime],
) -> bool:
    """
    Check if two dates are within the dedup window.

    If either date is missing, we assume they're within the window
    (conservative -- avoids creating accidental duplicates).
    """
    if existing_date is None or new_date is None:
        return True

    # Make both timezone-aware for comparison
    if existing_date.tzinfo is None:
        existing_date = existing_date.replace(tzinfo=timezone.utc)
    if new_date.tzinfo is None:
        new_date = new_date.replace(tzinfo=timezone.utc)

    return abs(existing_date - new_date) <= timedelta(days=DEDUP_WINDOW_DAYS)


def _insert_new_job(
    session: Session,
    posting: NormalizedPosting,
    job_hash: str,
    posted_date: Optional[datetime],
) -> str:
    """Create a new Job row + its first JobSource row."""
    now = datetime.now(timezone.utc)

    job = Job(
        job_hash=job_hash,
        job_title=posting.job_title,
        company_name=posting.company_name,
        location_raw=posting.location_raw,
        location_normalized=posting.location_normalized,
        role_match=posting.role_match,
        salary_disclosed=posting.salary_disclosed,
        salary_min=posting.salary_min,
        salary_max=posting.salary_max,
        description_clean=posting.description_clean,
        posted_date=posted_date,
        application_state="DISCOVERED",
        state_updated_date=now,
        created_at=now,
    )
    session.add(job)
    session.flush()  # assign job.id before creating JobSource

    source = JobSource(
        job_id=job.id,
        platform=posting.platform,
        url=posting.source_url,
        scraped_date=now,
    )
    session.add(source)

    return "new"


def _add_source(
    session: Session,
    job_id: int,
    posting: NormalizedPosting,
) -> None:
    """Add a new JobSource row to an existing Job (deduplication hit)."""
    # Check if this exact platform + URL combo already exists
    statement = select(JobSource).where(
        JobSource.job_id == job_id,
        JobSource.platform == posting.platform,
        JobSource.url == posting.source_url,
    )
    existing = session.exec(statement).first()
    if existing:
        return  # already recorded this exact source

    source = JobSource(
        job_id=job_id,
        platform=posting.platform,
        url=posting.source_url,
        scraped_date=datetime.now(timezone.utc),
    )
    session.add(source)
