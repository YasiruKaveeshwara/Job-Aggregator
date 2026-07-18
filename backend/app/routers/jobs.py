"""
Job listing endpoints.

GET  /api/jobs       -- list jobs (with optional filters)
PATCH /api/jobs/{id} -- update a job's application_state
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, col, select

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
    posted_date: Optional[datetime]
    application_state: str
    state_updated_date: datetime
    created_at: datetime
    sources: list[JobSourceOut]


class JobStateUpdate(BaseModel):
    """Body for PATCH /api/jobs/{id}."""
    application_state: str


_VALID_STATES = {
    "DISCOVERED", "REVIEWING", "APPLIED", "INTERVIEWING", "ARCHIVED",
}


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("", response_model=list[JobOut])
def list_jobs(
    state: Optional[str] = Query(None, description="Filter by application_state"),
    source: Optional[str] = Query(None, description="Filter by source platform"),
    role_match: Optional[str] = Query(None, description="Filter by role_match keyword"),
    q: Optional[str] = Query(None, description="Free-text search (title + company)"),
    session: Session = Depends(get_session),
):
    """List all jobs, with optional filters."""
    statement = select(Job)

    if state:
        statement = statement.where(Job.application_state == state)
    if role_match:
        statement = statement.where(Job.role_match == role_match)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            col(Job.job_title).ilike(pattern)
            | col(Job.company_name).ilike(pattern)
        )

    # Order by most recent first
    statement = statement.order_by(col(Job.created_at).desc())
    jobs = session.exec(statement).all()

    # If filtering by source, we need to check JobSource
    if source:
        source_job_ids = set()
        src_stmt = select(JobSource.job_id).where(JobSource.platform == source)
        for row in session.exec(src_stmt).all():
            source_job_ids.add(row)
        jobs = [j for j in jobs if j.id in source_job_ids]

    # Attach sources to each job
    result: list[JobOut] = []
    for job in jobs:
        src_stmt = select(JobSource).where(JobSource.job_id == job.id)
        sources = session.exec(src_stmt).all()
        result.append(
            JobOut(
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
        )

    return result


@router.patch("/{job_id}", response_model=JobOut)
def update_job_state(
    job_id: int,
    body: JobStateUpdate,
    session: Session = Depends(get_session),
):
    """Update a job's application_state (e.g. DISCOVERED -> APPLIED)."""
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
