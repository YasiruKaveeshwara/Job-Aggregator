"""
Job listing endpoints.

GET  /api/jobs       -- list jobs (with optional filters + pagination)
PATCH /api/jobs/{id} -- update a job's application_state
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, col, select, func

from app.db import get_session
from app.models import Job, JobSource

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ── Response models ──────────────────────────────────────────────────

class JobSourceOut(BaseModel):
    """A single source where a job was found."""
    id: int
    platform: str
    url: str
    scraped_date: datetime


class JobOut(BaseModel):
    """Full job record with its sources."""
    id: int
    job_hash: str
    job_title: str
    company_name: str
    location_raw: Optional[str]
    location_normalized: Optional[str]
    role_match: str
    salary_disclosed: bool
    salary_min: Optional[int]
    salary_max: Optional[int]
    description_clean: Optional[str]
    image_url: Optional[str]
    posted_date: Optional[datetime]
    application_state: str
    state_updated_date: datetime
    created_at: datetime
    sources: list[JobSourceOut]


class JobsPageOut(BaseModel):
    """Paginated job list response."""
    total: int
    page: int
    page_size: int
    total_pages: int
    jobs: list[JobOut]


class JobStateUpdate(BaseModel):
    """Body for PATCH /api/jobs/{id}."""
    application_state: str


_VALID_STATES = {"NEW", "APPLIED", "REMOVED"}

_PAGE_SIZE = 30


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("", response_model=JobsPageOut)
def list_jobs(
    state: Optional[str] = Query(None, description="Filter by application_state"),
    source: Optional[str] = Query(None, description="Filter by source platform"),
    role_match: Optional[str] = Query(None, description="Filter by role_match keyword"),
    q: Optional[str] = Query(None, description="Free-text search (title + company)"),
    date_from: Optional[str] = Query(None, description="Filter: posted on or after (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter: posted on or before (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(_PAGE_SIZE, ge=1, le=200, description="Jobs per page"),
    session: Session = Depends(get_session),
):
    """List jobs with optional filters and pagination. Newest first by default.

    REMOVED jobs are excluded unless state=REMOVED is explicitly requested.
    """
    statement = select(Job)

    # By default exclude REMOVED; only show them when explicitly requested
    if state:
        if state not in _VALID_STATES:
            raise HTTPException(status_code=422, detail=f"Invalid state '{state}'")
        statement = statement.where(Job.application_state == state)
    else:
        statement = statement.where(Job.application_state != "REMOVED")

    if role_match:
        statement = statement.where(Job.role_match == role_match)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            col(Job.job_title).ilike(pattern)
            | col(Job.company_name).ilike(pattern)
        )
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            statement = statement.where(col(Job.posted_date) >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            statement = statement.where(col(Job.posted_date) <= dt_to)
        except ValueError:
            pass

    # Order by most recent posted_date first, then created_at
    statement = statement.order_by(
        col(Job.posted_date).desc().nulls_last(),
        col(Job.created_at).desc(),
    )
    all_jobs = session.exec(statement).all()

    # If filtering by source, filter in Python (avoids complex subquery)
    if source:
        source_job_ids: set[int] = set()
        src_stmt = select(JobSource.job_id).where(JobSource.platform == source)
        for row in session.exec(src_stmt).all():
            source_job_ids.add(row)
        all_jobs = [j for j in all_jobs if j.id in source_job_ids]

    total = len(all_jobs)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    page_jobs = all_jobs[offset : offset + page_size]

    # Attach sources to each job on this page only
    result: list[JobOut] = []
    for job in page_jobs:
        src_stmt = select(JobSource).where(JobSource.job_id == job.id)
        sources = session.exec(src_stmt).all()
        result.append(_job_to_out(job, sources))

    return JobsPageOut(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        jobs=result,
    )


@router.patch("/{job_id}", response_model=JobOut)
def update_job_state(
    job_id: int,
    body: JobStateUpdate,
    session: Session = Depends(get_session),
):
    """Update a job's application_state (NEW | APPLIED | REMOVED)."""
    if body.application_state not in _VALID_STATES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid state '{body.application_state}'. "
                   f"Valid states: {', '.join(sorted(_VALID_STATES))}",
        )

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job.application_state = body.application_state
    job.state_updated_date = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    session.refresh(job)

    # Return with sources
    src_stmt = select(JobSource).where(JobSource.job_id == job.id)
    sources = session.exec(src_stmt).all()

    return _job_to_out(job, sources)

def _job_to_out(job: Job, sources: list[JobSource]) -> JobOut:
    return JobOut(
        id=job.id,
        job_hash=job.job_hash,
        job_title=job.job_title,
        company_name=job.company_name,
        location_raw=job.location_raw,
        location_normalized=job.location_normalized,
        role_match=job.role_match,
        salary_disclosed=job.salary_disclosed,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        description_clean=job.description_clean,
        image_url=job.image_url,
        posted_date=job.posted_date,
        application_state=job.application_state,
        state_updated_date=job.state_updated_date,
        created_at=job.created_at,
        sources=[
            JobSourceOut(
                id=s.id,
                platform=s.platform,
                url=s.url,
                scraped_date=s.scraped_date,
            )
            for s in sources
        ],
    )
