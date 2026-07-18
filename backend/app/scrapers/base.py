"""
Base scraper interface and shared helpers.

Every site-specific scraper (itpro.py, anyjobok.py, …) subclasses
``BaseScraper`` and implements ``fetch()``.  This module provides:

- ``RawJobPosting`` — the Pydantic model every scraper returns per listing.
- ``BaseScraper`` — abstract class with HTTP client setup, robots.txt
  checking, rate limiting, and retry logic.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from pydantic import BaseModel

from app.config import (
    DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    USER_AGENT,
)

logger = logging.getLogger(__name__)


# ── Data shape returned by every scraper ─────────────────────────────

class RawJobPosting(BaseModel):
    """
    A single job posting as scraped from a site, before any cleaning.

    Normalisation (title cleaning, salary parsing, role-keyword matching)
    happens later in normalize.py — scrapers just capture what they see.
    """

    job_title: str
    company_name: str
    location_raw: Optional[str] = None
    salary_raw: Optional[str] = None       # un-parsed; normalize.py handles it
    description_raw: str
    posted_date_raw: Optional[str] = None  # raw string; normalize.py parses it
    source_url: str


# ── Robot-file cache ──────────────────────────────────────────────────
# One RobotFileParser per origin, cached for the lifetime of the process
# so we don't re-fetch robots.txt on every request.

_robots_cache: dict[str, RobotFileParser] = {}


def _get_robots_parser(url: str) -> RobotFileParser:
    """Return a (cached) RobotFileParser for the origin of *url*."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in _robots_cache:
        robots_url = f"{origin}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            logger.warning("Could not fetch robots.txt from %s — assuming allowed", robots_url)
            # If we can't read robots.txt, default to allowing (common practice).
            rp.allow_all = True
        _robots_cache[origin] = rp

    return _robots_cache[origin]


# ── Base scraper ──────────────────────────────────────────────────────

class BaseScraper(ABC):
    """
    Abstract base class for all site scrapers.

    Subclasses must set ``platform_name`` and implement ``fetch()``.
    They can use the provided helpers for HTTP requests, robots.txt
    compliance, and rate limiting.
    """

    platform_name: str  # e.g. "itpro.lk" — set by each subclass

    def __init__(self) -> None:
        self._last_request_time: float = 0.0

    # ── HTTP client ──────────────────────────────────────────────────

    def _get_client(self) -> httpx.Client:
        """Return a configured ``httpx.Client`` with our User-Agent."""
        return httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        )

    # ── Robots.txt ───────────────────────────────────────────────────

    def robots_allowed(self, url: str) -> bool:
        """Check whether our User-Agent is allowed to fetch *url*."""
        rp = _get_robots_parser(url)
        allowed = rp.can_fetch(USER_AGENT, url)
        if not allowed:
            logger.info(
                "[%s] robots.txt disallows fetching %s — skipping",
                self.platform_name,
                url,
            )
        return allowed

    # ── Rate limiting ────────────────────────────────────────────────

    def _rate_limit(self, seconds: float = DEFAULT_RATE_LIMIT_SECONDS) -> None:
        """
        Sleep if needed so that consecutive requests to the same host
        are spaced at least *seconds* apart.
        """
        elapsed = time.time() - self._last_request_time
        if elapsed < seconds:
            time.sleep(seconds - elapsed)
        self._last_request_time = time.time()

    # ── Retry with backoff ───────────────────────────────────────────

    def _request_with_retry(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic retry on transient failures.

        Retries on 429, 5xx, and network errors with exponential backoff.
        Raises the last exception if all retries are exhausted.
        """
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = client.request(method, url, **kwargs)

                # Retry on server errors and rate limits
                if response.status_code in (429, 500, 502, 503, 504):
                    wait = RETRY_BACKOFF_FACTOR * (2 ** attempt)
                    logger.warning(
                        "[%s] HTTP %d from %s — retrying in %.1fs (attempt %d/%d)",
                        self.platform_name,
                        response.status_code,
                        url,
                        wait,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError:
                # Non-retryable HTTP errors (4xx other than 429)
                raise

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                wait = RETRY_BACKOFF_FACTOR * (2 ** attempt)
                logger.warning(
                    "[%s] Network error fetching %s: %s — retrying in %.1fs (attempt %d/%d)",
                    self.platform_name,
                    url,
                    exc,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(wait)

        # All retries exhausted
        raise RuntimeError(
            f"[{self.platform_name}] Failed to fetch {url} after {MAX_RETRIES} attempts"
        ) from last_exc

    # ── The one method subclasses must implement ─────────────────────

    @abstractmethod
    def fetch(self) -> list[RawJobPosting]:
        """
        Return every posting from this site that's worth considering.

        Site-specific filtering (e.g. category=software-engineering)
        happens inside the scraper; role-keyword matching happens later
        in normalize.py.
        """
        ...
