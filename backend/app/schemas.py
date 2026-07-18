"""
Pydantic request/response schemas.

These are the shapes exposed by the REST API, intentionally separate from
the SQLModel table classes in models.py so the API contract doesn't leak
internal DB concerns (auto-generated IDs, raw timestamps, etc.).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Job ───────────────────────────────────────────────────────────────

class JobSourceResponse(BaseModel):
    """One source entry for a job (which platform, which URL)."""
    id: int
    platform: str
    url: str
    scraped_date: datetime


class JobResponse(BaseModel):
    """Full job record as returned by GET /api/jobs."""
    id: int
    job_hash: str
    job_title: str
    company_name: str
    location_raw: Optional[str] = None
    location_normalized: Optional[str] = None
    role_match: str
    salary_disclosed: bool
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description_clean: Optional[str] = None
    posted_date: Optional[datetime] = None
    application_state: str
    state_updated_date: datetime
    created_at: datetime
    sources: list[JobSourceResponse] = []


class JobUpdate(BaseModel):
    """Body for PATCH /api/jobs/{id} — only the fields you can change."""
    application_state: str


# ── Source ────────────────────────────────────────────────────────────

class SourceResponse(BaseModel):
    """A scrapable site with its enabled/disabled status."""
    id: int
    name: str
    enabled: bool


class SourceUpdate(BaseModel):
    """Body for PATCH /api/sources/{name}."""
    enabled: bool


# ── Scrape ────────────────────────────────────────────────────────────

class ScrapeRunRequest(BaseModel):
    """Body for POST /api/scrape/run."""
    sites: list[str] | str  # list of site names, or the string "all"


class ScrapeRunResponse(BaseModel):
    """Returned immediately after starting a scrape."""
    run_id: int


class ScrapeRunStatus(BaseModel):
    """Full status of a scrape run (for polling)."""
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    triggered_by: str
    site_results: str  # JSON string — parsed by the frontend
