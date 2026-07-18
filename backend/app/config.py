"""
Application configuration.

Loads environment variables from .env and holds the role-keyword
allowlist / denylist used by normalize.py for filtering job postings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend/ directory (one level above app/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── Database ──────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

# ── Scraper HTTP settings ─────────────────────────────────────────────
USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "job-aggregator-personal-use (contact: your-email@example.com)",
)
ITPRO_API_KEY: str = os.getenv("ITPRO_API_KEY", "")

# ── Rate limiting ─────────────────────────────────────────────────────
# Default delay (seconds) between consecutive HTTP requests to the same host.
DEFAULT_RATE_LIMIT_SECONDS: float = 2.0

# ── Retry settings ────────────────────────────────────────────────────
MAX_RETRIES: int = 3
RETRY_BACKOFF_FACTOR: float = 1.0  # waits 1s, 2s, 4s …

# ── Role-keyword matching (used by normalize.py) ──────────────────────
# A posting is kept if its title matches any of these (case-insensitive).
ROLE_KEYWORDS_INCLUDE: list[str] = [
    "software engineer",
    "associate software engineer",
    "web developer",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "full stack",
    "fullstack",
    "swe",
]

# If any of these appear alongside an INCLUDE keyword, the posting is
# still kept and role_match gets the combo (e.g. "software engineer intern").
ROLE_KEYWORDS_INTERN_MODIFIER: list[str] = [
    "intern",
    "internship",
    "trainee",
]

# Postings whose title matches an INCLUDE keyword but also matches one
# of these are discarded.  Add false positives here as you notice them.
ROLE_KEYWORDS_EXCLUDE: list[str] = []

# ── Deduplication ─────────────────────────────────────────────────────
# Two postings with the same hash are treated as separate postings if
# their posted_dates are more than this many days apart.
DEDUP_WINDOW_DAYS: int = 45

# ── CORS ──────────────────────────────────────────────────────────────
# Origins allowed to make cross-origin requests to the API.
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",   # Next.js dev server
    "http://127.0.0.1:3000",
]
