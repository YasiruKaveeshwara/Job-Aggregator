"""
SQLModel table definitions.

These are the canonical database tables for the entire application.
Every other layer (scrapers, normalizer, API) reads/writes through these models.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    """A single job posting, deduplicated across all sources."""

    id: Optional[int] = Field(default=None, primary_key=True)
    job_hash: str = Field(index=True)  # sha256(normalized_company + normalized_title)

    job_title: str
    company_name: str
    location_raw: Optional[str] = None
    location_normalized: Optional[str] = None

    role_match: str  # which keyword matched, e.g. "web developer"

    salary_disclosed: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    description_clean: Optional[str] = None
    image_url: Optional[str] = None  # company logo or job image

    posted_date: Optional[datetime] = None

    # Pipeline state: NEW | APPLIED
    application_state: str = "NEW"
    state_updated_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class JobSource(SQLModel, table=True):
    """
    Tracks which platform a Job was found on.

    Many-to-one: a single Job can have multiple JobSource rows
    (one per site that listed the same posting).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")

    platform: str   # e.g. "itpro.lk", "anyjobok.com"
    url: str        # direct link to the posting on that platform
    scraped_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ScrapeRun(SQLModel, table=True):
    """
    One row per scrape invocation (triggered from the admin portal).

    `site_results` is a JSON string like:
    {
        "itpro.lk":       {"found": 40, "new": 5, "duplicates": 35, "error": null},
        "anyjobok.com":   {"found": 12, "new": 3, "duplicates": 9, "error": null}
    }
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    finished_at: Optional[datetime] = None

    # RUNNING | COMPLETED | FAILED
    status: str = "RUNNING"
    triggered_by: str = "manual"

    # Per-site breakdown, updated live so the admin portal can poll progress
    site_results: str = "{}"  # JSON string


class Source(SQLModel, table=True):
    """
    A scrapable job site.

    Seeded on first startup; the admin portal can toggle `enabled` to
    temporarily disable a site without touching code.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)   # e.g. "itpro.lk"
    enabled: bool = True
    last_scraped_at: Optional[datetime] = None
