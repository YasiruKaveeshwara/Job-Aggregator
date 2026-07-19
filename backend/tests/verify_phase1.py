"""
Phase 1 verification script.
Tests that the ORM works: insert a Job, query it back, check Source seeding.
"""

import sys
sys.path.insert(0, ".")

from datetime import datetime, timezone
from sqlmodel import Session, select

from app.db import engine
from app.models import Job, JobSource, Source, ScrapeRun


def main():
    with Session(engine) as session:
        # 1. Check seeded sources
        sources = session.exec(select(Source)).all()
        print("=== Seeded Sources ===")
        for s in sources:
            print(f"  {s.id}: {s.name} (enabled={s.enabled})")
        assert len(sources) == 4, f"Expected 4 sources, got {len(sources)}"
        print(f"[OK] {len(sources)} sources seeded correctly\n")

        # 2. Insert a test Job
        job = Job(
            job_hash="test_hash_abc123",
            job_title="Software Engineer",
            company_name="Test Company",
            location_raw="Colombo, Sri Lanka",
            role_match="software engineer",
            description_clean="A test job posting for verification.",
            posted_date=datetime.now(timezone.utc),
            application_state="DISCOVERED",
            state_updated_date=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        print(f"=== Inserted Job ===")
        print(f"  ID: {job.id}")
        print(f"  Title: {job.job_title}")
        print(f"  Company: {job.company_name}")
        print(f"  State: {job.application_state}")

        # 3. Add a JobSource for it
        source = JobSource(
            job_id=job.id,
            platform="itpro.lk",
            url="https://itpro.lk/jobs/12345",
            scraped_date=datetime.now(timezone.utc),
        )
        session.add(source)
        session.commit()
        session.refresh(source)
        print(f"\n=== Inserted JobSource ===")
        print(f"  ID: {source.id}")
        print(f"  Job ID: {source.job_id}")
        print(f"  Platform: {source.platform}")
        print(f"  URL: {source.url}")

        # 4. Query it back
        queried_job = session.exec(
            select(Job).where(Job.job_hash == "test_hash_abc123")
        ).first()
        assert queried_job is not None, "Failed to query job back"
        assert queried_job.id == job.id
        print(f"\n[OK] Successfully queried Job back by hash (id={queried_job.id})")

        # 5. Query JobSources for this job
        job_sources = session.exec(
            select(JobSource).where(JobSource.job_id == job.id)
        ).all()
        assert len(job_sources) == 1
        print(f"[OK] Found {len(job_sources)} source(s) for job id={job.id}")

        # 6. Clean up test data
        session.delete(source)
        session.delete(queried_job)
        session.commit()
        print("\n[OK] Cleaned up test data")

        print("\n" + "=" * 50)
        print("ALL PHASE 1 VERIFICATIONS PASSED")
        print("=" * 50)


if __name__ == "__main__":
    main()

