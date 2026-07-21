"""
Application configuration.

All runtime-tunable settings are loaded from environment variables (or a
``.env`` file at the backend root).  No magic numbers anywhere else in the
codebase — import from here instead.

Environment variables and their defaults
-----------------------------------------
DATABASE_URL            sqlite:///./jobs.db
USER_AGENT              job-aggregator-personal-use (contact: your-email@example.com)

# HTTP / scraper behaviour
DEFAULT_RATE_LIMIT_SECONDS   2.0    seconds between requests to the same host
MAX_RETRIES                  3      total attempts per request
RETRY_BACKOFF_FACTOR         1.0    base multiplier for exponential backoff (1s, 2s, 4s …)
HTTP_TIMEOUT_SECONDS         30.0   socket/connect timeout per request

# Pagination limits (applied to every paginated scraper)
SCRAPER_MAX_PAGES       10     maximum pages fetched per keyword/query
SCRAPER_PAGE_SIZE       20     results per page when the API supports it

# Deduplication
DEDUP_WINDOW_DAYS       45     treat same hash as separate if >N days apart

# CORS (comma-separated origins)
CORS_ORIGINS    http://localhost:3000,http://127.0.0.1:3000
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend/ directory (one level above app/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _getenv_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _getenv_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _getenv_list(key: str, default: list[str], sep: str = ",") -> list[str]:
    raw = os.getenv(key)
    if not raw:
        return default
    return [item.strip() for item in raw.split(sep) if item.strip()]


# ── Database ──────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

# ── HTTP / User-Agent ─────────────────────────────────────────────────
USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "job-aggregator-personal-use (contact: your-email@example.com)",
)

# ── Scraper HTTP settings ─────────────────────────────────────────────
DEFAULT_RATE_LIMIT_SECONDS: float = _getenv_float("DEFAULT_RATE_LIMIT_SECONDS", 2.0)
HTTP_TIMEOUT_SECONDS: float = _getenv_float("HTTP_TIMEOUT_SECONDS", 30.0)

# ── Retry settings ────────────────────────────────────────────────────
MAX_RETRIES: int = _getenv_int("MAX_RETRIES", 3)
RETRY_BACKOFF_FACTOR: float = _getenv_float("RETRY_BACKOFF_FACTOR", 1.0)

# ── Pagination limits (global caps shared by all paginated scrapers) ──
SCRAPER_MAX_PAGES: int = _getenv_int("SCRAPER_MAX_PAGES", 10)
SCRAPER_PAGE_SIZE: int = _getenv_int("SCRAPER_PAGE_SIZE", 20)

# ── Deduplication ─────────────────────────────────────────────────────
DEDUP_WINDOW_DAYS: int = _getenv_int("DEDUP_WINDOW_DAYS", 45)

# ── Exclusion keywords (also editable via admin portal) ───────────────
# Postings whose title matches an include keyword but also matches one
# of these are discarded.  Persisted in keyword_exclude.json at runtime.
ROLE_KEYWORDS_EXCLUDE: list[str] = []

# ── CORS ──────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = _getenv_list(
    "CORS_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)

