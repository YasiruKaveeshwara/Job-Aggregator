"""
FastAPI application entry point.

Wires up:
- Database initialisation (table creation + default Source seeding)
- CORS middleware for the Next.js dev server
- Router registration (stubs for now — fleshed out in Phase 5)
- A /health smoke-test endpoint
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.config import CORS_ORIGINS
from app.db import create_db_and_tables, engine
from app.models import Source
from app.orchestrator import cancel_all_runs

logger = logging.getLogger(__name__)

# ── Default sources seeded on first startup ──────────────────────────
_DEFAULT_SOURCES = [
    "itpro.lk",
    "anyjobok.com",
    "governmentjob.lk",
    "jobenvoy.com",
    "rooster.jobs",
    "topjobs.lk",
    "xpress.jobs",
    "findmyjob.lk",
    "hire.lk",
]


def _seed_sources() -> None:
    """Insert default Source rows if they don't already exist."""
    with Session(engine) as session:
        existing = {s.name for s in session.exec(select(Source)).all()}

        added = 0
        for name in _DEFAULT_SOURCES:
            if name not in existing:
                session.add(Source(name=name, enabled=True))
                added += 1

        if added:
            session.commit()
            logger.info("Seeded %d new source(s)", added)


# ── Lifespan (startup / shutdown) ────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup: create tables, seed sources, load keyword config."""
    create_db_and_tables()
    _seed_sources()
    # Load persisted keyword config (if any)
    from app.routers.keywords import load_keywords_from_disk

    load_keywords_from_disk()
    logger.info("Database ready — tables created and sources seeded")
    yield
    logger.info("Shutting down — cancelling any in-flight scrape runs")
    cancel_all_runs()


# ── App instance ─────────────────────────────────────────────────────

app = FastAPI(
    title="Job Aggregator API",
    description=(
        "Backend API for the Job Aggregator — aggregates software engineering "
        "job listings from Sri Lankan job sites, deduplicates them, and exposes "
        "them for a Kanban dashboard."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────

from app.routers import jobs, keywords, scrape, sources

app.include_router(jobs.router)
app.include_router(scrape.router)
app.include_router(sources.router)
app.include_router(keywords.router)


# ── Health check ─────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}
