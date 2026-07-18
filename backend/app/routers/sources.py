"""
Source management endpoints.

GET   /api/sources         -- list all sites with their enabled flag
PATCH /api/sources/{name}  -- enable or disable a site
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Source

router = APIRouter(prefix="/api/sources", tags=["sources"])


# ── Response models ──────────────────────────────────────────────────

class SourceOut(BaseModel):
    """A scrapable job site."""
    id: int
    name: str
    enabled: bool


class SourceUpdate(BaseModel):
    """Body for PATCH /api/sources/{name}."""
    enabled: bool


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("", response_model=list[SourceOut])
def list_sources(
    session: Session = Depends(get_session),
):
    """List all configured job sites with their enabled/disabled status."""
    sources = session.exec(select(Source)).all()
    return [
        SourceOut(id=s.id, name=s.name, enabled=s.enabled)
        for s in sources
    ]


@router.patch("/{name}", response_model=SourceOut)
def toggle_source(
    name: str,
    body: SourceUpdate,
    session: Session = Depends(get_session),
):
    """Enable or disable a job site by name."""
    statement = select(Source).where(Source.name == name)
    source = session.exec(statement).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{name}' not found")

    source.enabled = body.enabled
    session.add(source)
    session.commit()
    session.refresh(source)

    return SourceOut(id=source.id, name=source.name, enabled=source.enabled)
