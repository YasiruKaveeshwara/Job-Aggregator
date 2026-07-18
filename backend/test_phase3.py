"""
Phase 3 verification: test all four scrapers.

Calls each scraper's fetch() and verifies they return RawJobPosting objects.
"""

import sys
sys.path.insert(0, ".")

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
)

from app.scrapers.base import RawJobPosting
from app.scrapers.itpro import ItproScraper
from app.scrapers.anyjobok import AnyjobokScraper
from app.scrapers.governmentjob import GovernmentjobScraper
from app.scrapers.jobenvoy import JobenvoyScraper


def test_scraper(name: str, scraper_cls):
    """Test a single scraper and return results."""
    print(f"\n{'-' * 60}")
    print(f"  Testing: {name}")
    print(f"{'-' * 60}")

    try:
        scraper = scraper_cls()
        postings = scraper.fetch()
    except Exception as e:
        print(f"  [FAIL] Scraper raised exception: {e}")
        return 0, False

    print(f"  Returned: {len(postings)} postings")

    if not postings:
        print(f"  [WARN] No postings returned (site may be down or blocked)")
        return 0, True  # Not a failure — site could be temporarily unavailable

    # Show first 3
    for i, p in enumerate(postings[:3], 1):
        print(f"  --- {i}. {p.job_title[:60]}")
        print(f"       Company:  {p.company_name[:50]}")
        print(f"       Location: {p.location_raw or '(none)'}")
        print(f"       URL:      {p.source_url[:80]}")

    # Validate types
    all_valid = all(isinstance(p, RawJobPosting) for p in postings)
    print(f"\n  [{'OK' if all_valid else 'FAIL'}] All {len(postings)} results are RawJobPosting")

    # Stats
    with_loc = sum(1 for p in postings if p.location_raw)
    with_date = sum(1 for p in postings if p.posted_date_raw)
    with_desc = sum(1 for p in postings if p.description_raw)
    print(f"  Stats: location={with_loc}, date={with_date}, desc={with_desc}")

    return len(postings), all_valid


def main():
    scrapers = [
        ("itpro.lk", ItproScraper),
        ("anyjobok.com", AnyjobokScraper),
        ("governmentjob.lk", GovernmentjobScraper),
        ("jobenvoy.com", JobenvoyScraper),
    ]

    total = 0
    all_ok = True

    for name, cls in scrapers:
        count, valid = test_scraper(name, cls)
        total += count
        if not valid:
            all_ok = False

    print(f"\n{'=' * 60}")
    print("  PHASE 3 SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total postings across all scrapers: {total}")
    print(f"  All valid: {all_ok}")

    if total > 0 and all_ok:
        print("\n  [OK] PHASE 3 VERIFICATION PASSED")
    else:
        print("\n  [WARN] Check results above -- some scrapers may need attention")

    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
