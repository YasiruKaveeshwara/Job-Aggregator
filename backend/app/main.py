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

logger = logging.getLogger(__name__)

# ── Default sources seeded on first startup ──────────────────────────
_DEFAULT_SOURCES = [
    "itpro.lk",
    "anyjobok.com",
    "governmentjob.lk",
    "jobenvoy.com",
]


def _seed_sources() -> None:
    """Insert default Source rows if the table is empty."""
    with Session(engine) as session:
        existing = session.exec(select(Source)).all()
        if existing:
            return  # already seeded

        for name in _DEFAULT_SOURCES:
            session.add(Source(name=name, enabled=True))
        session.commit()
        logger.info("Seeded %d default sources", len(_DEFAULT_SOURCES))


# ── Lifespan (startup / shutdown) ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup: create tables, seed sources."""
    create_db_and_tables()
    _seed_sources()
    logger.info("Database ready — tables created and sources seeded")
    yield
    # Nothing to clean up on shutdown (SQLite file stays)


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

from app.routers import jobs, scrape, sources

app.include_router(jobs.router)
app.include_router(scrape.router)
app.include_router(sources.router)


# ── Health check ─────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}
