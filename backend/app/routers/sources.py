"""
Source management endpoints.

GET   /api/sources         — list all sites with their enabled flag
PATCH /api/sources/{name}  — enable or disable a site

Implemented in Phase 5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/sources", tags=["sources"])
