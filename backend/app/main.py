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
    allow_origins=["*"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────

from app.routers import jobs, keywords, scrape, settings, sources

app.include_router(jobs.router)
app.include_router(scrape.router)
app.include_router(sources.router)
app.include_router(keywords.router)
app.include_router(settings.router)


# ── Health check ─────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}


# ── Static Frontend Mount ────────────────────────────────────────────

import os
import sys

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def _resolve_frontend_build_dir() -> str:
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        possible_dirs = [
            os.path.join(base_dir, "frontend_out"),
            os.path.join(base_dir, "_internal", "frontend_out"),
            os.path.join(os.path.dirname(sys.executable), "frontend_out"),
            os.path.join(os.path.dirname(sys.executable), "_internal", "frontend_out"),
        ]
        for d in possible_dirs:
            if os.path.isdir(d):
                return d
        return os.path.join(base_dir, "frontend_out")
    # Normal development execution.
    return os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out")


_FRONTEND_BUILD_DIR = _resolve_frontend_build_dir()


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404 and not path.startswith("api"):
                index_path = os.path.join(self.directory, "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
            return response
        except Exception:
            if not path.startswith("api"):
                index_path = os.path.join(self.directory, "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
            raise


if os.path.isdir(_FRONTEND_BUILD_DIR):
    app.mount("/", SPAStaticFiles(directory=_FRONTEND_BUILD_DIR, html=True), name="frontend")
