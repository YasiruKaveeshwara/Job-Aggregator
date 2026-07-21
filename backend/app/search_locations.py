"""
Central interface for location preferences.

Scrapers call ``get_enabled_search_locations()`` to obtain the current
list of active location strings from the database.
"""

from sqlmodel import Session, select

from app.db import engine
from app.models import SearchLocation


def get_enabled_search_locations() -> list[str]:
    """Return all enabled location strings, sorted alphabetically."""
    with Session(engine) as session:
        rows = session.exec(
            select(SearchLocation)
            .where(SearchLocation.enabled == True)  # noqa: E712
            .order_by(SearchLocation.location)
        ).all()
        return [r.location for r in rows]
