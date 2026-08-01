"""
Base scraper interface and shared helpers.

Every site-specific scraper (itpro.py, anyjobok.py, …) subclasses
``BaseScraper`` and implements ``fetch()``.  This module provides:

- ``RawJobPosting`` — the Pydantic model every scraper returns per listing.
- ``BaseScraper`` — abstract class with HTTP client setup, robots.txt
  checking, rate limiting, and retry logic.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from pydantic import BaseModel

from app.config import (
    CONNECT_TIMEOUT_SECONDS,
    READ_TIMEOUT_SECONDS,
    DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    USER_AGENT,
)

logger = logging.getLogger(__name__)

_active_cancel_event: threading.local = threading.local()


class ScrapeCancelled(RuntimeError):
    """Raised when a scrape run is cancelled while a scraper is in flight."""


class SiteUnavailableError(RuntimeError):
    """
    Raised when a scraper's circuit breaker opens.

    After ``CIRCUIT_BREAKER_THRESHOLD`` consecutive site-level failures
    (CDN-down codes 522/523/524, or all retries exhausted on 5xx / network
    errors), the circuit opens and every subsequent call to
    ``_request_with_retry`` raises this immediately — no network call, no
    delay.  The circuit resets automatically on the next successful response.
    """


def set_active_cancel_event(cancel_event: threading.Event | None) -> None:
    """Bind a cancel event to the current thread for scraper use."""
    if cancel_event is None:
        if hasattr(_active_cancel_event, "value"):
            del _active_cancel_event.value
    else:
        _active_cancel_event.value = cancel_event


def clear_active_cancel_event() -> None:
    """Remove the active cancel event from the current thread."""
    if hasattr(_active_cancel_event, "value"):
        del _active_cancel_event.value


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
    salary_raw: Optional[str] = None  # un-parsed; normalize.py handles it
    description_raw: str
    posted_date_raw: Optional[str] = None  # raw string; normalize.py parses it
    source_url: str
    image_url: Optional[str] = None  # company logo or job image URL


# ── Robot-file cache ──────────────────────────────────────────────────
# One RobotFileParser per origin, cached for the lifetime of the process
# so we don't re-fetch robots.txt on every request.

_robots_cache: dict[str, RobotFileParser] = {}


def _get_robots_parser(url: str) -> RobotFileParser:
    """Return a (cached) RobotFileParser for the origin of *url*.

    Uses httpx (with our configured User-Agent) to fetch robots.txt
    so the request matches what the scraper itself sends.  Falls back
    to allow-all on any network error, 4xx/5xx response, or parse
    failure — the standard behaviour when robots.txt is unavailable.
    """
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in _robots_cache:
        robots_url = f"{origin}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            resp = httpx.get(
                robots_url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=5.0,
            )
            if resp.status_code == 200:
                # Parse the fetched content — handles encoding better
                # than urllib's built-in rp.read() which can choke on
                # malformed files or Cloudflare challenge pages.
                lines = resp.text.splitlines()
                rp.parse(lines)
            else:
                # Non-200 (404, 403, 5xx) → assume all allowed
                logger.info(
                    "robots.txt from %s returned HTTP %d — assuming allowed",
                    robots_url,
                    resp.status_code,
                )
                rp.allow_all = True
        except Exception:
            logger.warning(
                "Could not fetch robots.txt from %s — assuming allowed",
                robots_url,
            )
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

    #: Base URL used for the pre-flight connectivity probe.
    #: Set this in every subclass (e.g. "https://itpro.lk").
    #: Leave as empty string to skip the probe for that scraper.
    SITE_PROBE_URL: str = ""

    def __init__(self, cancel_event: threading.Event | None = None) -> None:
        self._last_request_time: float = 0.0
        self._cancel_event = cancel_event
        # ── Circuit breaker state ────────────────────────────────────
        self._consecutive_failures: int = 0
        self._circuit_open: bool = False

    # ── Circuit breaker ──────────────────────────────────────────────

    #: Number of consecutive site-level failures before the circuit opens.
    #: Subclasses may override this class variable to tune per-site.
    CIRCUIT_BREAKER_THRESHOLD: int = 2

    def _record_failure(self) -> None:
        """Increment the consecutive-failure counter; open circuit if threshold hit."""
        self._consecutive_failures += 1
        if (
            self._consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD
            and not self._circuit_open
        ):
            self._circuit_open = True
            logger.warning(
                "[%s] Circuit breaker OPEN after %d consecutive failures — "
                "skipping remaining requests to this site",
                self.platform_name,
                self._consecutive_failures,
            )

    def _record_success(self) -> None:
        """Reset the circuit breaker on a successful response."""
        if self._consecutive_failures:
            self._consecutive_failures = 0
            self._circuit_open = False

    def _raise_if_cancelled(self) -> None:
        """Raise if the current run has been cancelled."""
        event = self._cancel_event or getattr(_active_cancel_event, "value", None)
        if event is not None and event.is_set():
            raise ScrapeCancelled("Scrape cancelled")

    # ── HTTP client ──────────────────────────────────────────────────

    def _get_client(self) -> httpx.Client:
        """Return a configured ``httpx.Client`` with split connect/read timeouts."""
        return httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT_SECONDS,
                read=READ_TIMEOUT_SECONDS,
                write=READ_TIMEOUT_SECONDS,
                pool=CONNECT_TIMEOUT_SECONDS,
            ),
        )

    # ── Pre-flight probe + public entry point ────────────────────────

    def _probe_site(self) -> bool:
        """
        Quick 5-second connectivity check against ``SITE_PROBE_URL``.

        Returns ``True`` if the site is reachable (any non-CDN-down response
        counts — even a 4xx means the server answered).  Returns ``False`` on
        connection errors or CDN "origin down" codes (522/523/524).

        On ``False`` the circuit breaker is opened immediately so that every
        subsequent ``_request_with_retry`` call short-circuits instantly.
        """
        url = self.SITE_PROBE_URL
        if not url:
            return True  # no probe configured — assume reachable

        try:
            with httpx.Client(
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=httpx.Timeout(5.0),
            ) as probe_client:
                resp = probe_client.head(url)
                if resp.status_code in (522, 523, 524):
                    # CDN confirms origin is unreachable
                    self._record_failure()
                    self._record_failure()  # ensure threshold is always met
                    logger.warning(
                        "[%s] Pre-flight probe: HTTP %d — site appears DOWN",
                        self.platform_name,
                        resp.status_code,
                    )
                    return False
                return True

        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.TimeoutException,
        ):
            # Could not connect at all within 5 s — open circuit immediately
            self._record_failure()
            self._record_failure()  # ensure threshold is always met
            logger.warning(
                "[%s] Pre-flight probe: unreachable within 5s — skipping site",
                self.platform_name,
            )
            return False

        except Exception:
            # Unknown error (redirect loop, SSL, etc.) — let fetch() try anyway
            logger.debug(
                "[%s] Pre-flight probe raised unexpected error — proceeding",
                self.platform_name,
                exc_info=True,
            )
            return True

    def run(self) -> list[RawJobPosting]:
        """
        Public entry point called by the orchestrator.

        Runs a quick pre-flight check first; if the site is unreachable the
        circuit breaker is opened and an empty list is returned immediately
        without entering the keyword loop.  On success, delegates to
        ``fetch()``.
        """
        if not self._probe_site():
            return []
        return self.fetch()

    # ── Robots.txt ───────────────────────────────────────────────────────

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
        self._raise_if_cancelled()
        elapsed = time.time() - self._last_request_time
        if elapsed < seconds:
            remaining = seconds - elapsed
            while remaining > 0:
                self._raise_if_cancelled()
                chunk = min(0.2, remaining)
                time.sleep(chunk)
                remaining -= chunk
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
        Raises ``SiteUnavailableError`` immediately (no network call) when
        the circuit breaker is open — i.e. the site has failed repeatedly.
        """
        # ── Circuit breaker check ─────────────────────────────────────
        if self._circuit_open:
            raise SiteUnavailableError(
                f"[{self.platform_name}] Circuit breaker is open — "
                "site appears to be down, skipping request"
            )

        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._raise_if_cancelled()
            self._rate_limit()

            try:
                response = client.request(method, url, **kwargs)

                # Cloudflare / CDN "origin is down" codes — non-retryable.
                # Count toward circuit breaker and raise immediately.
                # 522 = Connection Timed Out, 523 = Origin Unreachable,
                # 524 = A Timeout Occurred.
                if response.status_code in (522, 523, 524):
                    self._record_failure()
                    response.raise_for_status()

                # Retry on transient server errors and rate limits.
                # Note: 429 (rate-limited) is NOT a site-down signal.
                if response.status_code in (429, 500, 502, 503, 504):
                    wait = RETRY_BACKOFF_FACTOR * (2**attempt)
                    logger.warning(
                        "[%s] HTTP %d from %s — retrying in %.1fs (attempt %d/%d)",
                        self.platform_name,
                        response.status_code,
                        url,
                        wait,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    while wait > 0:
                        self._raise_if_cancelled()
                        chunk = min(0.2, wait)
                        time.sleep(chunk)
                        wait -= chunk
                    continue

                response.raise_for_status()
                self._record_success()  # successful response — reset circuit
                return response

            except httpx.HTTPStatusError:
                # 522/523/524 already recorded above; other 4xx are not
                # site-down signals (application-level rejections).
                raise

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                wait = RETRY_BACKOFF_FACTOR * (2**attempt)
                logger.warning(
                    "[%s] Network error fetching %s: %s — retrying in %.1fs (attempt %d/%d)",
                    self.platform_name,
                    url,
                    exc,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                while wait > 0:
                    self._raise_if_cancelled()
                    chunk = min(0.2, wait)
                    time.sleep(chunk)
                    wait -= chunk

        # All retries exhausted — count as a site-level failure
        self._record_failure()
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
