"""
Scrape control endpoints.

POST /api/scrape/run           -- start a scrape run (background task)
GET  /api/scrape/status/{id}   -- poll a run's status + progress
POST /api/scrape/cancel/{id}   -- cancel a running scrape gracefully
GET  /api/scrape/runs          -- list past runs
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, select

from app.db import get_session, engine
from app.models import ScrapeRun
from app.orchestrator import run_scrape, request_cancel

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


# ── Request / Response models ────────────────────────────────────────


class ScrapeRunRequest(BaseModel):
    """Body for POST /api/scrape/run."""

    sites: Union[list[str], str]  # ["itpro.lk", "anyjobok.com"] or "all"


class ProgressOut(BaseModel):
    """Progress info for a running scrape."""

    total_sites: int = 0
    completed_sites: int = 0
    current_site: Optional[str] = None
    requested_sites: list[str] = []


class ScrapeRunOut(BaseModel):
    """Response for a ScrapeRun record."""

    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    triggered_by: str
    site_results: dict[str, Any]  # parsed from JSON string
    progress: ProgressOut


class ScrapeRunCreated(BaseModel):
    """Response for POST /api/scrape/run."""

    run_id: int


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/run", response_model=ScrapeRunCreated)
def start_scrape(
    body: ScrapeRunRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """
    Start a scrape run in the background.

    Returns the run_id immediately. Use GET /api/scrape/status/{run_id}
    to poll progress.
    """
    # Create the ScrapeRun row
    run = ScrapeRun(
        started_at=datetime.now(timezone.utc),
        status="RUNNING",
        triggered_by="manual",
        site_results="{}",
        progress="{}",
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Launch orchestrator in background
    background_tasks.add_task(run_scrape, run.id, body.sites)

    return ScrapeRunCreated(run_id=run.id)


@router.get("/status/{run_id}", response_model=ScrapeRunOut)
def get_scrape_status(
    run_id: int,
    session: Session = Depends(get_session),
):
    """Poll a scrape run's current status, including partial site_results."""
    run = session.get(ScrapeRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"ScrapeRun {run_id} not found")

    return _run_to_out(run)


@router.post("/cancel/{run_id}")
def cancel_scrape(
    run_id: int,
    session: Session = Depends(get_session),
):
    """
    Cancel a running scrape gracefully.

    The current site will finish processing, but no further sites will
    be started.  All results gathered so far are saved.
    """
    run = session.get(ScrapeRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"ScrapeRun {run_id} not found")

    if run.status == "RUNNING":
        request_cancel(run_id)
        return {"detail": f"Cancel signal sent for run {run_id}"}

    if run.status == "CANCELLED":
        return {"detail": f"Run {run_id} is already cancelled"}

    raise HTTPException(
        status_code=400,
        detail=f"Run {run_id} is not running (status: {run.status})",
    )


@router.get("/runs", response_model=list[ScrapeRunOut])
def list_scrape_runs(
    session: Session = Depends(get_session),
):
    """List all past scrape runs, most recent first."""
    statement = select(ScrapeRun).order_by(col(ScrapeRun.started_at).desc())
    runs = session.exec(statement).all()
    return [_run_to_out(r) for r in runs]


# ── Helpers ──────────────────────────────────────────────────────────


def _run_to_out(run: ScrapeRun) -> ScrapeRunOut:
    """Convert a ScrapeRun DB row to the API response model."""
    try:
        site_results = json.loads(run.site_results or "{}")
    except json.JSONDecodeError:
        site_results = {}

    try:
        progress_data = json.loads(run.progress or "{}")
    except (json.JSONDecodeError, AttributeError):
        progress_data = {}

    return ScrapeRunOut(
        id=run.id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        triggered_by=run.triggered_by,
        site_results=site_results,
        progress=ProgressOut(**progress_data) if progress_data else ProgressOut(),
    )
