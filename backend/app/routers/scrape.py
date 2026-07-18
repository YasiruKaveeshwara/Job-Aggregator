"""
Scrape control endpoints.

POST /api/scrape/run           — start a scrape run (background task)
GET  /api/scrape/status/{id}   — poll a run's status
GET  /api/scrape/runs          — list past runs

Implemented in Phase 5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/scrape", tags=["scrape"])
