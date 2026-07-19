"""
Scrape orchestrator.

Given a list of site names (or ``"all"`` for all enabled sites), for each one:

1. Checks the ``Source`` table -- skip if disabled.
2. Runs that scraper's ``.fetch()`` in a try/except so one site's failure
   doesn't stop the others.
3. Passes results through ``normalize.py``, then ``dedup.py``.
4. Records per-site counts (``found``, ``new``, ``duplicates``, ``error``)
   into the ``ScrapeRun.site_results`` JSON *as it goes*, so the admin
   portal can poll progress live.
5. Marks the ``ScrapeRun`` row ``COMPLETED`` (or ``FAILED``).
"""

import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db import engine
from app.dedup import dedup_and_insert
from app.models import ScrapeRun, Source
from app.normalize import normalize
from app.scrapers.base import BaseScraper

# ── Scraper registry ─────────────────────────────────────────────────
# Import lazily inside the function to avoid circular imports at module
# load time, but declare the mapping here for clarity.

from app.scrapers.itpro import ItproScraper
from app.scrapers.anyjobok import AnyjobokScraper
from app.scrapers.governmentjob import GovernmentjobScraper
from app.scrapers.jobenvoy import JobenvoyScraper
from app.scrapers.rooster import RoosterScraper
from app.scrapers.topjobs import TopjobsScraper
from app.scrapers.xpressjobs import XpressjobsScraper

logger = logging.getLogger(__name__)

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "itpro.lk": ItproScraper,
    "anyjobok.com": AnyjobokScraper,
    "governmentjob.lk": GovernmentjobScraper,
    "jobenvoy.com": JobenvoyScraper,
    "rooster.jobs": RoosterScraper,
    "topjobs.lk": TopjobsScraper,
    "xpress.jobs": XpressjobsScraper,
}


# ── Public API ───────────────────────────────────────────────────────


def run_scrape(run_id: int, sites: list[str] | str) -> None:
    """
    Execute a scrape run.

    Args:
        run_id: ID of the ScrapeRun row (already created by the caller).
        sites: List of site names, or ``"all"`` for all enabled sites.
    """
    try:
        _execute_run(run_id, sites)
    except Exception:
        logger.exception("[orchestrator] Fatal error in run %d", run_id)
        _mark_run_failed(run_id)


def _execute_run(run_id: int, sites: list[str] | str) -> None:
    """Core logic, wrapped so the outer function can catch and mark FAILED."""

    # Resolve site list
    with Session(engine) as session:
        if sites == "all":
            statement = select(Source).where(Source.enabled == True)  # noqa: E712
            enabled_sources = session.exec(statement).all()
            site_names = [s.name for s in enabled_sources]
        else:
            site_names = list(sites)

    logger.info("[orchestrator] Run %d starting for sites: %s", run_id, site_names)

    # Process each site independently
    for site_name in site_names:
        _process_site(run_id, site_name)

    # Mark run as completed
    _mark_run_completed(run_id)


def _process_site(run_id: int, site_name: str) -> None:
    """Fetch, normalize, and dedup postings from a single site."""

    # Check if site is enabled
    with Session(engine) as session:
        statement = select(Source).where(Source.name == site_name)
        source = session.exec(statement).first()
        if source and not source.enabled:
            logger.info("[orchestrator] %s is disabled -- skipping", site_name)
            _update_site_result(
                run_id,
                site_name,
                {
                    "found": 0,
                    "new": 0,
                    "duplicates": 0,
                    "error": "disabled",
                },
            )
            return

    # Get the scraper class
    scraper_cls = SCRAPER_REGISTRY.get(site_name)
    if scraper_cls is None:
        logger.warning("[orchestrator] No scraper registered for %s", site_name)
        _update_site_result(
            run_id,
            site_name,
            {
                "found": 0,
                "new": 0,
                "duplicates": 0,
                "error": f"no scraper for {site_name}",
            },
        )
        return

    fetch_error: str | None = None
    raw_postings = []

    # ── Fetch ────────────────────────────────────────────────────
    try:
        scraper = scraper_cls()
        raw_postings = scraper.fetch()
    except Exception as exc:
        logger.exception("[orchestrator] %s fetch failed", site_name)
        fetch_error = str(exc)

    found = len(raw_postings)
    new_count = 0
    dup_count = 0

    try:
        if fetch_error is None:
            # ── Normalize + Dedup ────────────────────────────────────────
            with Session(engine) as session:
                for raw in raw_postings:
                    # Normalize (role-keyword filter)
                    normalized = normalize(raw, platform=site_name)
                    if normalized is None:
                        # Filtered out by role-keyword matching
                        continue

                    # Dedup + insert
                    try:
                        result = dedup_and_insert(session, normalized)
                        if result == "new":
                            new_count += 1
                        else:
                            dup_count += 1
                    except Exception:
                        logger.warning(
                            "[orchestrator] Failed to insert posting '%s' from %s",
                            raw.job_title,
                            site_name,
                            exc_info=True,
                        )

                session.commit()

            logger.info(
                "[orchestrator] %s: found=%d, new=%d, duplicates=%d",
                site_name,
                found,
                new_count,
                dup_count,
            )

            _update_site_result(
                run_id,
                site_name,
                {
                    "found": found,
                    "new": new_count,
                    "duplicates": dup_count,
                    "error": None,
                },
            )
        else:
            _update_site_result(
                run_id,
                site_name,
                {
                    "found": 0,
                    "new": 0,
                    "duplicates": 0,
                    "error": fetch_error,
                },
            )
    finally:
        _update_source_timestamp(site_name)


# ── ScrapeRun helpers ────────────────────────────────────────────────


def _update_site_result(
    run_id: int,
    site_name: str,
    result: dict,
) -> None:
    """Update the site_results JSON for a specific site in the ScrapeRun row."""
    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        if run is None:
            logger.error("[orchestrator] ScrapeRun %d not found", run_id)
            return

        site_results = json.loads(run.site_results or "{}")
        site_results[site_name] = result
        run.site_results = json.dumps(site_results)

        session.add(run)
        session.commit()


def _mark_run_completed(run_id: int) -> None:
    """Mark a ScrapeRun as COMPLETED."""
    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        if run:
            run.status = "COMPLETED"
            run.finished_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()
            logger.info("[orchestrator] Run %d COMPLETED", run_id)


def _mark_run_failed(run_id: int) -> None:
    """Mark a ScrapeRun as FAILED."""
    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        if run:
            run.status = "FAILED"
            run.finished_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()
            logger.error("[orchestrator] Run %d FAILED", run_id)


def _update_source_timestamp(site_name: str) -> None:
    """Set Source.last_scraped_at to now after the latest scrape attempt."""
    with Session(engine) as session:
        statement = select(Source).where(Source.name == site_name)
        source = session.exec(statement).first()
        if source:
            source.last_scraped_at = datetime.now(timezone.utc)
            session.add(source)
            session.commit()
