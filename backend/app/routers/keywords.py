"""
Keyword and Location configuration endpoints.

All keywords are stored in the ``SearchKeyword`` DB table and serve
a dual purpose:
  1. Scrapers use them as search terms when querying job boards.
  2. normalize.py uses them as the inclusion filter when deciding
     whether a scraped posting is relevant.

Locations are stored in the ``SearchLocation`` DB table and used by
scrapers that support location filtering (rooster, xpressjobs, hirelk).

GET    /api/keywords/search              -- list all keywords
POST   /api/keywords/search              -- add a new keyword
PATCH  /api/keywords/search/{id}         -- toggle enabled / rename
DELETE /api/keywords/search/{id}         -- delete permanently

GET    /api/keywords/locations            -- list all locations
POST   /api/keywords/locations            -- add a new location
PATCH  /api/keywords/locations/{id}       -- toggle enabled / rename
DELETE /api/keywords/locations/{id}       -- delete permanently

── Exclude list (optional, rarely changed) ──────────────────────────────
GET  /api/keywords/exclude               -- get exclusion keywords
PUT  /api/keywords/exclude               -- update exclusion keywords
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

import app.config as config
from app.db import get_session
from app.models import SearchKeyword, SearchLocation

router = APIRouter(prefix="/api/keywords", tags=["keywords"])
logger = logging.getLogger(__name__)

_EXCLUDE_PATH = Path(__file__).resolve().parent.parent / "keyword_exclude.json"


# ── Response models ───────────────────────────────────────────────────

class SearchKeywordOut(BaseModel):
    id: int
    keyword: str
    enabled: bool


class SearchKeywordCreate(BaseModel):
    keyword: str


class SearchKeywordPatch(BaseModel):
    enabled: Optional[bool] = None
    keyword: Optional[str] = None


class ExcludeConfig(BaseModel):
    exclude: list[str]


class SearchLocationOut(BaseModel):
    id: int
    location: str
    enabled: bool


class SearchLocationCreate(BaseModel):
    location: str


class SearchLocationPatch(BaseModel):
    enabled: Optional[bool] = None
    location: Optional[str] = None


# ── Lifecycle helpers ─────────────────────────────────────────────────

def load_keywords_from_disk() -> None:
    """Load persisted exclude list from disk (called at startup)."""
    if _EXCLUDE_PATH.exists():
        try:
            data = json.loads(_EXCLUDE_PATH.read_text(encoding="utf-8"))
            config.ROLE_KEYWORDS_EXCLUDE = data.get("exclude", [])
            logger.info("Loaded exclude keywords from %s", _EXCLUDE_PATH)
        except Exception:
            logger.warning("Failed to load keyword_exclude.json", exc_info=True)


# ── Search keyword endpoints ──────────────────────────────────────────

@router.get("/search", response_model=list[SearchKeywordOut])
def list_search_keywords(session: Session = Depends(get_session)):
    """Return all keywords (enabled and disabled), sorted alphabetically."""
    rows = session.exec(select(SearchKeyword).order_by(SearchKeyword.keyword)).all()
    return [SearchKeywordOut(id=r.id, keyword=r.keyword, enabled=r.enabled) for r in rows]


@router.post("/search", response_model=SearchKeywordOut)
def add_search_keyword(body: SearchKeywordCreate, session: Session = Depends(get_session)):
    """Add a new keyword."""
    keyword = body.keyword.strip().lower()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")

    existing = session.exec(
        select(SearchKeyword).where(SearchKeyword.keyword == keyword)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Keyword '{keyword}' already exists")

    row = SearchKeyword(keyword=keyword, enabled=True)
    session.add(row)
    session.commit()
    session.refresh(row)
    return SearchKeywordOut(id=row.id, keyword=row.keyword, enabled=row.enabled)


@router.patch("/search/{keyword_id}", response_model=SearchKeywordOut)
def patch_search_keyword(
    keyword_id: int,
    body: SearchKeywordPatch,
    session: Session = Depends(get_session),
):
    """Toggle a keyword's enabled state or rename it."""
    row = session.get(SearchKeyword, keyword_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Keyword {keyword_id} not found")

    if body.enabled is not None:
        row.enabled = body.enabled
    if body.keyword is not None:
        row.keyword = body.keyword.strip().lower()

    session.add(row)
    session.commit()
    session.refresh(row)
    return SearchKeywordOut(id=row.id, keyword=row.keyword, enabled=row.enabled)


@router.delete("/search/{keyword_id}")
def delete_search_keyword(keyword_id: int, session: Session = Depends(get_session)):
    """Delete a keyword permanently."""
    row = session.get(SearchKeyword, keyword_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Keyword {keyword_id} not found")
    session.delete(row)
    session.commit()
    return {"detail": f"Deleted keyword '{row.keyword}'"}


# ── Exclude keyword endpoints ─────────────────────────────────────────

@router.get("/exclude", response_model=ExcludeConfig)
def get_exclude():
    """Return the current exclusion keyword list."""
    return ExcludeConfig(exclude=config.ROLE_KEYWORDS_EXCLUDE)


@router.put("/exclude", response_model=ExcludeConfig)
def update_exclude(body: ExcludeConfig):
    """Update the exclusion keyword list (persisted to disk)."""
    config.ROLE_KEYWORDS_EXCLUDE = _clean(body.exclude)
    data = {"exclude": config.ROLE_KEYWORDS_EXCLUDE}
    _EXCLUDE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return ExcludeConfig(exclude=config.ROLE_KEYWORDS_EXCLUDE)


# ── Backward-compat stub (old GET /api/keywords) ──────────────────────
# Some older frontend code may still call this. Returns an empty include
# list now that the DB is the source of truth.

@router.get("", include_in_schema=False)
def get_keywords_compat():
    return {
        "include": [],
        "intern_modifiers": [],
        "exclude": config.ROLE_KEYWORDS_EXCLUDE,
    }


# ── Location endpoints ────────────────────────────────────────────────

@router.get("/locations", response_model=list[SearchLocationOut])
def list_locations(session: Session = Depends(get_session)):
    """Return all locations (enabled and disabled), sorted alphabetically."""
    rows = session.exec(select(SearchLocation).order_by(SearchLocation.location)).all()
    return [SearchLocationOut(id=r.id, location=r.location, enabled=r.enabled) for r in rows]


@router.post("/locations", response_model=SearchLocationOut)
def add_location(body: SearchLocationCreate, session: Session = Depends(get_session)):
    """Add a new location."""
    location = body.location.strip().lower()
    if not location:
        raise HTTPException(status_code=400, detail="Location cannot be empty")

    existing = session.exec(
        select(SearchLocation).where(SearchLocation.location == location)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Location '{location}' already exists")

    row = SearchLocation(location=location, enabled=True)
    session.add(row)
    session.commit()
    session.refresh(row)
    return SearchLocationOut(id=row.id, location=row.location, enabled=row.enabled)


@router.patch("/locations/{location_id}", response_model=SearchLocationOut)
def patch_location(
    location_id: int,
    body: SearchLocationPatch,
    session: Session = Depends(get_session),
):
    """Toggle a location's enabled state or rename it."""
    row = session.get(SearchLocation, location_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    if body.enabled is not None:
        row.enabled = body.enabled
    if body.location is not None:
        row.location = body.location.strip().lower()

    session.add(row)
    session.commit()
    session.refresh(row)
    return SearchLocationOut(id=row.id, location=row.location, enabled=row.enabled)


@router.delete("/locations/{location_id}")
def delete_location(location_id: int, session: Session = Depends(get_session)):
    """Delete a location permanently."""
    row = session.get(SearchLocation, location_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")
    session.delete(row)
    session.commit()
    return {"detail": f"Deleted location '{row.location}'"}


# ── Helpers ───────────────────────────────────────────────────────────

def _clean(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        kw = kw.strip().lower()
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result
