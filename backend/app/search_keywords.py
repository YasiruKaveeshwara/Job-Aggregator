"""
Shared helper for loading search keywords from the database.

All scrapers call ``get_enabled_search_keywords()`` instead of maintaining
their own hardcoded ``_QUERIES`` lists.  Keywords are editable via the
admin portal at runtime.
"""

import logging

from sqlmodel import Session, select

from app.db import engine
from app.models import SearchKeyword

_logger = logging.getLogger(__name__)


def get_enabled_search_keywords() -> list[str]:
    """Return the list of enabled search keywords from the database.

    Falls back to an empty list if the DB is unavailable (scrapers
    should still run gracefully — they'll just find no results).
    """
    try:
        with Session(engine) as session:
            rows = session.exec(
                select(SearchKeyword).where(SearchKeyword.enabled == True)
            ).all()
            keywords = [row.keyword for row in rows]
            _logger.debug("Loaded %d search keywords from DB", len(keywords))
            return keywords
    except Exception:
        _logger.warning("Failed to load search keywords from DB", exc_info=True)
        return []
