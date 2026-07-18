"""
Job listing endpoints.

GET  /api/jobs       — list jobs (with optional filters)
PATCH /api/jobs/{id} — update a job's application_state

Implemented in Phase 5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
