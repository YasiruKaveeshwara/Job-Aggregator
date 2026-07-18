"""
Quick end-to-end test for rooster.jobs through the full pipeline:
  rooster scraper → normalize → dedup → orchestrator → DB

Run with: .\\venv\\Scripts\\python.exe test_rooster_e2e.py
"""
import os, sys, json, logging

logging.basicConfig(level=logging.WARNING)  # quiet — only show summary

# Use a temp DB so we don't pollute the real one
os.environ["DATABASE_URL"] = "sqlite:///test_rooster_e2e.db"

from sqlmodel import Session, select, create_engine
from app.db import create_db_and_tables, engine
from app.models import Job, JobSource, ScrapeRun, Source
from app.orchestrator import run_scrape

def seed_source():
    with Session(engine) as s:
        if not s.exec(select(Source).where(Source.name == "rooster.jobs")).first():
            s.add(Source(name="rooster.jobs", enabled=True))
            s.commit()

def main():
    print("-" * 60)
    print("  E2E TEST: rooster.jobs → normalize → dedup → DB")
    print("-" * 60)

    create_db_and_tables()
    seed_source()

    # Create a ScrapeRun and trigger via orchestrator
    with Session(engine) as s:
        run = ScrapeRun(
            started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            status="RUNNING",
            triggered_by="test",
            site_results="{}",
        )
        s.add(run)
        s.commit()
        s.refresh(run)
        run_id = run.id

    print(f"\n  Running orchestrator for rooster.jobs (run_id={run_id})…")
    run_scrape(run_id, ["rooster.jobs"])

    # Check results
    with Session(engine) as s:
        run = s.get(ScrapeRun, run_id)
        results = json.loads(run.site_results or "{}")
        jobs = s.exec(select(Job)).all()
        sources = s.exec(select(JobSource)).all()

    site = results.get("rooster.jobs", {})
    print(f"\n  Scrape status : {run.status}")
    print(f"  Raw found     : {site.get('found', 0)}")
    print(f"  New jobs      : {site.get('new', 0)}")
    print(f"  Duplicates    : {site.get('duplicates', 0)}")
    print(f"  Error         : {site.get('error')}")
    print(f"\n  Job rows in DB    : {len(jobs)}")
    print(f"  JobSource rows    : {len(sources)}")

    if jobs:
        print(f"\n  Sample jobs (first 5):")
        for j in jobs[:5]:
            print(f"    - {j.job_title} @ {j.company_name}")
            print(f"      role={j.role_match}  salary={'yes' if j.salary_disclosed else 'no'}")

    # Validate
    ok = True
    if run.status != "COMPLETED":
        print(f"\n  FAIL: run status is {run.status}")
        ok = False
    if len(jobs) == 0:
        print("\n  FAIL: no jobs were inserted")
        ok = False
    if site.get("error"):
        print(f"\n  FAIL: site error = {site['error']}")
        ok = False

    # Cleanup
    engine.dispose()
    if os.path.exists("test_rooster_e2e.db"):
        os.remove("test_rooster_e2e.db")

    if ok:
        print(f"\n  ROOSTER E2E TEST PASSED")
    else:
        print(f"\n  ROOSTER E2E TEST FAILED")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()
