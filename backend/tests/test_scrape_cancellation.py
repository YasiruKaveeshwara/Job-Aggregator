import threading
from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from app import orchestrator
from app.db import create_db_and_tables, engine
from app.models import ScrapeRun
from app.orchestrator import (
    cancel_all_runs,
    _register_cancel_event,
    _process_site,
    _unregister_cancel_event,
)
from app.routers.scrape import cancel_scrape
from app.scrapers.base import BaseScraper


class DummyScraper(BaseScraper):
    platform_name = "dummy"

    def fetch(self):
        self._raise_if_cancelled()
        return []


def test_base_scraper_raises_when_cancelled():
    cancel_event = threading.Event()
    scraper = DummyScraper(cancel_event=cancel_event)

    scraper._raise_if_cancelled()

    cancel_event.set()
    with pytest.raises(RuntimeError, match="cancelled"):
        scraper._raise_if_cancelled()


def test_cancel_all_sets_registered_run_events():
    event_a = _register_cancel_event(101)
    event_b = _register_cancel_event(102)

    cancel_all_runs()

    assert event_a.is_set()
    assert event_b.is_set()

    _unregister_cancel_event(101)
    _unregister_cancel_event(102)


def test_source_timestamp_is_updated_before_site_result(monkeypatch):
    create_db_and_tables()
    events = []

    class EmptyScraper:
        def run(self):
            return []

    monkeypatch.setitem(orchestrator.SCRAPER_REGISTRY, "test-source", EmptyScraper)
    monkeypatch.setattr(
        orchestrator,
        "_update_source_timestamp",
        lambda site_name: events.append(("timestamp", site_name)),
    )
    monkeypatch.setattr(
        orchestrator,
        "_update_site_result",
        lambda run_id, site_name, result: events.append(("result", site_name)),
    )

    _process_site(9999, "test-source", [])

    assert events == [("timestamp", "test-source"), ("result", "test-source")]


def test_cancel_scrape_marks_running_run_cancelled_even_without_registered_event():
    create_db_and_tables()

    with Session(engine) as session:
        run = ScrapeRun(
            started_at=datetime.now(timezone.utc),
            status="RUNNING",
            triggered_by="manual",
            site_results="{}",
            progress="{}",
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        payload = cancel_scrape(run.id, session=session)

        session.refresh(run)
        assert payload["detail"] == f"Cancel signal sent for run {run.id}"
        assert run.status == "CANCELLED"
