"""
Keyword configuration endpoints.

GET  /api/keywords  -- get current role keyword config
PUT  /api/keywords  -- update role keyword config

Keywords are persisted in ``keyword_config.json`` alongside the
database so they survive restarts.  On startup, ``config.py`` defaults
are used unless the JSON file exists.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

import app.config as config

router = APIRouter(prefix="/api/keywords", tags=["keywords"])
logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "keyword_config.json"


# ── Request / Response models ────────────────────────────────────────

class KeywordConfig(BaseModel):
    """Role-keyword configuration."""
    include: list[str]
    intern_modifiers: list[str]
    exclude: list[str]


# ── Lifecycle ────────────────────────────────────────────────────────

def load_keywords_from_disk() -> None:
    """Load keyword_config.json (if it exists) into config module vars.

    Called once at startup from main.py.
    """
    if not _CONFIG_PATH.exists():
        return

    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        config.ROLE_KEYWORDS_INCLUDE = data.get("include", config.ROLE_KEYWORDS_INCLUDE)
        config.ROLE_KEYWORDS_INTERN_MODIFIER = data.get(
            "intern_modifiers", config.ROLE_KEYWORDS_INTERN_MODIFIER
        )
        config.ROLE_KEYWORDS_EXCLUDE = data.get("exclude", config.ROLE_KEYWORDS_EXCLUDE)
        logger.info("Loaded keyword config from %s", _CONFIG_PATH)
    except Exception:
        logger.warning("Failed to load keyword_config.json", exc_info=True)


def _save_keywords() -> None:
    """Persist current config to keyword_config.json."""
    data = {
        "include": config.ROLE_KEYWORDS_INCLUDE,
        "intern_modifiers": config.ROLE_KEYWORDS_INTERN_MODIFIER,
        "exclude": config.ROLE_KEYWORDS_EXCLUDE,
    }
    _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("", response_model=KeywordConfig)
def get_keywords():
    """Return the current role-keyword configuration."""
    return KeywordConfig(
        include=config.ROLE_KEYWORDS_INCLUDE,
        intern_modifiers=config.ROLE_KEYWORDS_INTERN_MODIFIER,
        exclude=config.ROLE_KEYWORDS_EXCLUDE,
    )


@router.put("", response_model=KeywordConfig)
def update_keywords(body: KeywordConfig):
    """Update the role-keyword configuration.

    Changes take effect immediately and are persisted to disk.
    """
    # Normalize: strip whitespace, lowercase, deduplicate
    config.ROLE_KEYWORDS_INCLUDE = _clean(body.include)
    config.ROLE_KEYWORDS_INTERN_MODIFIER = _clean(body.intern_modifiers)
    config.ROLE_KEYWORDS_EXCLUDE = _clean(body.exclude)

    _save_keywords()

    return KeywordConfig(
        include=config.ROLE_KEYWORDS_INCLUDE,
        intern_modifiers=config.ROLE_KEYWORDS_INTERN_MODIFIER,
        exclude=config.ROLE_KEYWORDS_EXCLUDE,
    )


def _clean(keywords: list[str]) -> list[str]:
    """Strip, lowercase, deduplicate while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        kw = kw.strip().lower()
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result
