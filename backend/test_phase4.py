"""
Phase 4 verification: normalize + dedup + orchestrator end-to-end.

Tests:
1. normalize.py -- keyword matching, company cleanup, salary parsing
2. dedup.py     -- hash computation, dedup window, insert logic
3. orchestrator -- full pipeline with real scraper (itpro.lk)
4. Idempotency  -- running orchestrator twice doesn't create duplicates
"""

import sys
sys.path.insert(0, ".")

import json
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
)

# Use a test DB so we don't pollute the real one
os.environ["DATABASE_URL"] = "sqlite:///./test_phase4.db"

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db import create_db_and_tables, engine
from app.models import Job, JobSource, ScrapeRun, Source
from app.normalize import normalize, _normalize_company, _match_role, _parse_salary
from app.scrapers.base import RawJobPosting
from app.dedup import compute_job_hash, dedup_and_insert
from app.normalize import NormalizedPosting


def sep(title):
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


def test_normalize():
    """Test the normalizer on sample data."""
    sep("TEST: normalize.py")

    # 1. Company normalization
    cases = [
        ("Virtusa (Pvt) Ltd", "Virtusa"),
        ("WSO2 Lanka Private Limited", "WSO2 Lanka"),
        ("IFS R&D International Pvt Ltd.", "IFS R&D International"),
        ("Google Inc.", "Google"),
        ("SentryLabs", "SentryLabs"),
    ]
    all_ok = True
    for raw, expected in cases:
        result = _normalize_company(raw)
        ok = result == expected
        if not ok:
            all_ok = False
        print(f"  Company: '{raw}' -> '{result}' {'[OK]' if ok else f'[FAIL] expected {expected}'}")

    # 2. Role matching
    role_cases = [
        ("Software Engineer", "software engineer"),
        ("Junior Web Developer", "web developer"),
        ("Frontend Developer - React", "frontend"),
        ("Software Engineer Intern", "software engineer intern"),
        ("Associate Software Engineer Trainee", "associate software engineer trainee"),
        ("Marketing Manager", None),  # should be filtered
        ("Accountant", None),
        ("Full Stack Developer", "full stack"),
    ]
    for title, expected in role_cases:
        result = _match_role(title)
        ok = result == expected
        if not ok:
            all_ok = False
        print(f"  Role: '{title}' -> {result!r} {'[OK]' if ok else f'[FAIL] expected {expected!r}'}")

    # 3. Salary parsing
    salary_cases = [
        ("LKR 50,000 - 100,000", (True, 50000, 100000)),
        ("Rs. 80000", (True, 80000, 80000)),
        (None, (False, None, None)),
        ("Negotiable", (False, None, None)),
    ]
    for raw, expected in salary_cases:
        result = _parse_salary(raw)
        ok = result == expected
        if not ok:
            all_ok = False
        print(f"  Salary: {raw!r} -> {result} {'[OK]' if ok else f'[FAIL] expected {expected}'}")

    # 4. Full normalize pass
    raw = RawJobPosting(
        job_title="  Senior Software Engineer  ",
        company_name="Virtusa (Pvt) Ltd",
        location_raw="Colombo",
        salary_raw="LKR 200,000 - 350,000",
        description_raw="<p>We are looking for a <b>Senior SWE</b>.</p>",
        posted_date_raw="2026-07-18",
        source_url="https://example.com/job/123",
    )
    result = normalize(raw, "test.com")
    if result:
        print(f"  Full normalize: title='{result.job_title}', company='{result.company_name}'")
        print(f"    role={result.role_match}, salary={result.salary_min}-{result.salary_max}")
        print(f"    desc='{result.description_clean[:50]}...'")
    else:
        print(f"  [FAIL] Full normalize returned None for a valid posting")
        all_ok = False

    # 5. Filtered posting
    raw_filtered = RawJobPosting(
        job_title="Marketing Manager",
        company_name="Some Corp",
        location_raw="Kandy",
        salary_raw=None,
        description_raw="Not relevant",
        posted_date_raw=None,
        source_url="https://example.com/job/999",
    )
    result_filtered = normalize(raw_filtered, "test.com")
    ok = result_filtered is None
    if not ok:
        all_ok = False
    print(f"  Filtered out non-matching: {result_filtered is None} {'[OK]' if ok else '[FAIL]'}")

    return all_ok


def test_dedup():
    """Test deduplication logic."""
    sep("TEST: dedup.py")

    # Fresh DB
    create_db_and_tables()
    all_ok = True

    with Session(engine) as session:
        # 1. Insert new job
        posting1 = NormalizedPosting(
            job_title="Software Engineer",
            company_name="Virtusa",
            location_raw="Colombo",
            location_normalized="Colombo",
            role_match="software engineer",
            salary_disclosed=False,
            salary_min=None,
            salary_max=None,
            description_clean="Build stuff",
            posted_date_raw="2026-07-18",
            source_url="https://itpro.lk/job/1",
            platform="itpro.lk",
        )
        r1 = dedup_and_insert(session, posting1)
        session.commit()
        ok = r1 == "new"
        if not ok:
            all_ok = False
        print(f"  First insert: {r1} {'[OK]' if ok else '[FAIL] expected new'}")

        # 2. Insert same job from different source (should be duplicate)
        posting2 = NormalizedPosting(
            job_title="Software Engineer",
            company_name="Virtusa",
            location_raw="Colombo",
            location_normalized="Colombo",
            role_match="software engineer",
            salary_disclosed=False,
            salary_min=None,
            salary_max=None,
            description_clean="Build stuff",
            posted_date_raw="2026-07-15",  # within 45 days
            source_url="https://anyjobok.com/jobs/se-virtusa",
            platform="anyjobok.com",
        )
        r2 = dedup_and_insert(session, posting2)
        session.commit()
        ok = r2 == "duplicate"
        if not ok:
            all_ok = False
        print(f"  Duplicate source: {r2} {'[OK]' if ok else '[FAIL] expected duplicate'}")

        # Check DB state
        jobs = session.exec(select(Job)).all()
        sources = session.exec(select(JobSource)).all()
        ok_jobs = len(jobs) == 1
        ok_sources = len(sources) == 2
        if not ok_jobs:
            all_ok = False
        if not ok_sources:
            all_ok = False
        print(f"  Job rows: {len(jobs)} {'[OK]' if ok_jobs else '[FAIL] expected 1'}")
        print(f"  Source rows: {len(sources)} {'[OK]' if ok_sources else '[FAIL] expected 2'}")

        # 3. Insert different job (should be new)
        posting3 = NormalizedPosting(
            job_title="Web Developer",
            company_name="WSO2",
            location_raw="Colombo",
            location_normalized="Colombo",
            role_match="web developer",
            salary_disclosed=True,
            salary_min=100000,
            salary_max=200000,
            description_clean="Frontend work",
            posted_date_raw="2026-07-18",
            source_url="https://itpro.lk/job/2",
            platform="itpro.lk",
        )
        r3 = dedup_and_insert(session, posting3)
        session.commit()
        ok = r3 == "new"
        if not ok:
            all_ok = False
        print(f"  Different job: {r3} {'[OK]' if ok else '[FAIL] expected new'}")

        jobs = session.exec(select(Job)).all()
        ok = len(jobs) == 2
        if not ok:
            all_ok = False
        print(f"  Total Job rows now: {len(jobs)} {'[OK]' if ok else '[FAIL] expected 2'}")

    return all_ok


def test_orchestrator():
    """Test full orchestrator pipeline with real data."""
    sep("TEST: orchestrator (live itpro.lk)")

    from app.orchestrator import run_scrape

    create_db_and_tables()

    # Seed sources
    with Session(engine) as session:
        for name in ["itpro.lk", "anyjobok.com", "governmentjob.lk", "jobenvoy.com"]:
            existing = session.exec(select(Source).where(Source.name == name)).first()
            if not existing:
                session.add(Source(name=name, enabled=True))
        session.commit()

    # Create a ScrapeRun
    with Session(engine) as session:
        run = ScrapeRun(
            started_at=datetime.now(timezone.utc),
            status="RUNNING",
            triggered_by="test",
        )
        session.add(run)
        session.commit()
        run_id = run.id

    print(f"  Created ScrapeRun id={run_id}")

    # Run only itpro.lk (guaranteed to work)
    run_scrape(run_id, ["itpro.lk"])

    # Check results
    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        print(f"  Run status: {run.status}")
        results = json.loads(run.site_results)
        print(f"  Site results: {json.dumps(results, indent=2)}")

        jobs = session.exec(select(Job)).all()
        sources = session.exec(select(JobSource)).all()
        print(f"  Job rows: {len(jobs)}")
        print(f"  JobSource rows: {len(sources)}")

    all_ok = run.status == "COMPLETED" and len(jobs) > 0
    return all_ok, run_id, len(jobs)


def test_idempotency(first_run_job_count):
    """Test that running the orchestrator again doesn't create duplicates."""
    sep("TEST: idempotency (second run)")

    from app.orchestrator import run_scrape

    # Create another ScrapeRun
    with Session(engine) as session:
        run = ScrapeRun(
            started_at=datetime.now(timezone.utc),
            status="RUNNING",
            triggered_by="test",
        )
        session.add(run)
        session.commit()
        run_id = run.id

    run_scrape(run_id, ["itpro.lk"])

    with Session(engine) as session:
        run = session.get(ScrapeRun, run_id)
        results = json.loads(run.site_results)
        itpro_results = results.get("itpro.lk", {})
        print(f"  Run status: {run.status}")
        print(f"  itpro.lk: new={itpro_results.get('new', '?')}, duplicates={itpro_results.get('duplicates', '?')}")

        jobs = session.exec(select(Job)).all()
        sources = session.exec(select(JobSource)).all()
        print(f"  Total Job rows after 2nd run: {len(jobs)}")
        print(f"  Total JobSource rows: {len(sources)}")

    # Job count should be the same (no new jobs since same data)
    ok = len(jobs) == first_run_job_count
    print(f"  Idempotent: {ok} {'[OK]' if ok else f'[FAIL] expected {first_run_job_count}, got {len(jobs)}'}")
    return ok


def main():
    # Clean up test DB
    if os.path.exists("test_phase4.db"):
        os.remove("test_phase4.db")

    ok1 = test_normalize()
    ok2 = test_dedup()

    # Clean DB for orchestrator test
    engine.dispose()
    if os.path.exists("test_phase4.db"):
        os.remove("test_phase4.db")

    ok3, _, job_count = test_orchestrator()
    ok4 = test_idempotency(job_count)

    sep("PHASE 4 SUMMARY")
    print(f"  normalize.py:   {'[OK]' if ok1 else '[FAIL]'}")
    print(f"  dedup.py:       {'[OK]' if ok2 else '[FAIL]'}")
    print(f"  orchestrator:   {'[OK]' if ok3 else '[FAIL]'}")
    print(f"  idempotency:    {'[OK]' if ok4 else '[FAIL]'}")

    if all([ok1, ok2, ok3, ok4]):
        print("\n  PHASE 4 VERIFICATION PASSED")
    else:
        print("\n  PHASE 4 VERIFICATION FAILED -- check results above")

    print(f"{'=' * 60}")

    # Cleanup
    engine.dispose()
    if os.path.exists("test_phase4.db"):
        os.remove("test_phase4.db")


if __name__ == "__main__":
    main()
