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
5. Marks the ``ScrapeRun`` row ``COMPLETED`` (or ``FAILED`` / ``CANCELLED``).
"""

import json
import logging
import threading
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db import engine
from app.dedup import dedup_and_insert
from app.models import ScrapeRun, Source
from app.normalize import normalize
from app.scrapers.base import BaseScraper
from app.classifier import classify_new_jobs

# ── Scraper registry ─────────────────────────────────────────────────

from app.scrapers.itpro import ItproScraper
from app.scrapers.anyjobok import AnyjobokScraper
from app.scrapers.governmentjob import GovernmentjobScraper
from app.scrapers.jobenvoy import JobenvoyScraper
from app.scrapers.rooster import RoosterScraper
from app.scrapers.topjobs import TopjobsScraper
from app.scrapers.xpressjobs import XpressjobsScraper
from app.scrapers.findmyjob import FindmyjobScraper
from app.scrapers.hirelk import HirelkScraper

logger = logging.getLogger(__name__)

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "itpro.lk": ItproScraper,
    "anyjobok.com": AnyjobokScraper,
    "governmentjob.lk": GovernmentjobScraper,
    "jobenvoy.com": JobenvoyScraper,
    "rooster.jobs": RoosterScraper,
    "topjobs.lk": TopjobsScraper,
    "xpress.jobs": XpressjobsScraper,
    "findmyjob.lk": FindmyjobScraper,
    "hire.lk": HirelkScraper,
}


# ── Cancel registry (thread-safe) ───────────────────────────────────
# Maps run_id → threading.Event.  When set, the orchestrator loop checks
# this flag between sites and aborts gracefully.

_cancel_events: dict[int, threading.Event] = {}
_cancel_lock = threading.Lock()


def request_cancel(run_id: int) -> bool:
    """
    Signal a running scrape to stop after the current site finishes.

    Returns True if the run was found and signalled, False otherwise.
    """
    with _cancel_lock:
        event = _cancel_events.get(run_id)
        if event is None:
            return False
        event.set()
        return True


def _register_cancel_event(run_id: int) -> threading.Event:
    """Create and register a cancel event for a run."""
    event = threading.Event()
    with _cancel_lock:
        _cancel_events[run_id] = event
    return event


def _unregister_cancel_event(run_id: int) -> None:
    """Remove the cancel event when the run finishes."""
    with _cancel_lock:
        _cancel_events.pop(run_id, None)


# ── Public API ───────────────────────────────────────────────────────


def run_scrape(run_id: int, sites: list[str] | str) -> None:
    """
    Execute a scrape run.

    Args:
        run_id: ID of the ScrapeRun row (already created by the caller).
        sites: List of site names, or ``"all"`` for all enabled sites.
    """
    cancel_event = _register_cancel_event(run_id)
    try:
        _execute_run(run_id, sites, cancel_event)
    except Exception:
        logger.exception("[orchestrator] Fatal error in run %d", run_id)
        _mark_run_failed(run_id)
    finally:
        _unregister_cancel_event(run_id)


def _execute_run(
    run_id: int, sites: list[str] | str, cancel_event: threading.Event
) -> None:
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

    # Write initial progress
    _update_progress(run_id, {
        "total_sites": len(site_names),
        "completed_sites": 0,
        "current_site": site_names[0] if site_names else None,
        "requested_sites": site_names,
        "classifying": False,
    })

    # Process each site independently — collect IDs of newly inserted jobs
    all_new_job_ids: list[int] = []
    completed = 0
    for i, site_name in enumerate(site_names):
        # Check for cancellation BEFORE starting each site
        if cancel_event.is_set():
            logger.info(
                "[orchestrator] Run %d CANCELLED after %d/%d sites",
                run_id, completed, len(site_names),
            )
            _mark_run_cancelled(run_id)
            return

        # Update progress: which site we're currently scraping
        _update_progress(run_id, {
            "total_sites": len(site_names),
            "completed_sites": completed,
            "current_site": site_name,
            "requested_sites": site_names,
        })

        _process_site(run_id, site_name, all_new_job_ids)
        completed += 1

    # ── Gemini classification ────────────────────────────────────────
    # Run after ALL sites are done — classify all new jobs in one pass
    if all_new_job_ids:
        logger.info(
            "[orchestrator] Run %d — classifying %d new jobs with Gemini",
            run_id, len(all_new_job_ids),
        )
        _update_progress(run_id, {
            "total_sites": len(site_names),
            "completed_sites": completed,
            "current_site": None,
            "requested_sites": site_names,
            "classifying": True,
            "classifying_count": len(all_new_job_ids),
        })
        try:
            classifier_stats = classify_new_jobs(all_new_job_ids)
            logger.info("[orchestrator] Classifier: %s", classifier_stats)
            _update_classifier_result(run_id, classifier_stats)
        except Exception:
            logger.exception("[orchestrator] Classifier failed — jobs kept as NEW")

    # Final progress update
    _update_progress(run_id, {
        "total_sites": len(site_names),
        "completed_sites": completed,
        "current_site": None,
        "requested_sites": site_names,
        "classifying": False,
    })

    # Mark run as completed
    _mark_run_completed(run_id)


def _process_site(run_id: int, site_name: str, new_job_ids: list[int]) -> None:
    """Fetch, normalize, and dedup postings from a single site.
    
    Appends IDs of newly inserted jobs to new_job_ids for later classification.
    """

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
                        status, inserted_id = dedup_and_insert(session, normalized)
                        if status == "new":
                            new_count += 1
                            if inserted_id is not None and inserted_id not in new_job_ids:
                                new_job_ids.append(inserted_id)
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


def _update_classifier_result(run_id: int, stats: dict) -> None:
    """Store classifier stats in the ScrapeRun's site_results under '__classifier__' key."""
    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        if run is None:
            return
        site_results = json.loads(run.site_results or "{}")
        site_results["__classifier__"] = stats
        run.site_results = json.dumps(site_results)
        session.add(run)
        session.commit()



def _update_progress(run_id: int, progress: dict) -> None:
    """Update the progress JSON on the ScrapeRun row."""
    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        if run is None:
            return
        run.progress = json.dumps(progress)
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


def _mark_run_cancelled(run_id: int) -> None:
    """Mark a ScrapeRun as CANCELLED, saving all results gathered so far."""
    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        if run:
            run.status = "CANCELLED"
            run.finished_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()
            logger.info("[orchestrator] Run %d CANCELLED (partial results saved)", run_id)


def _update_source_timestamp(site_name: str) -> None:
    """Set Source.last_scraped_at to now after the latest scrape attempt."""
    with Session(engine) as session:
        statement = select(Source).where(Source.name == site_name)
        source = session.exec(statement).first()
        if source:
            source.last_scraped_at = datetime.now(timezone.utc)
            session.add(source)
            session.commit()
