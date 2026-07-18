"""
Phase 2 verification: test the itpro.lk scraper.

Calls ItproScraper.fetch() and prints the results to verify
it returns real, current job postings as RawJobPosting objects.
"""

import sys
sys.path.insert(0, ".")

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
)

from app.scrapers.itpro import ItproScraper


def main():
    scraper = ItproScraper()
    postings = scraper.fetch()

    print(f"\n{'=' * 60}")
    print(f"  itpro.lk scraper returned {len(postings)} postings")
    print(f"{'=' * 60}\n")

    if not postings:
        print("[FAIL] No postings returned!")
        sys.exit(1)

    # Show first 5 postings
    for i, p in enumerate(postings[:5], 1):
        print(f"--- Posting {i} ---")
        print(f"  Title:    {p.job_title}")
        print(f"  Company:  {p.company_name}")
        print(f"  Location: {p.location_raw or '(not available)'}")
        print(f"  Posted:   {p.posted_date_raw or '(not available)'}")
        print(f"  URL:      {p.source_url}")
        desc_preview = p.description_raw[:120].replace('\n', ' ').replace('\r', '')
        print(f"  Desc:     {desc_preview}...")
        print()

    # Summary stats
    with_location = sum(1 for p in postings if p.location_raw)
    with_date = sum(1 for p in postings if p.posted_date_raw)
    print(f"Stats:")
    print(f"  Total postings:       {len(postings)}")
    print(f"  With location:        {with_location}")
    print(f"  With posted date:     {with_date}")
    print(f"  With description:     {sum(1 for p in postings if p.description_raw)}")
    print()

    # Validate that all are RawJobPosting instances
    from app.scrapers.base import RawJobPosting
    all_valid = all(isinstance(p, RawJobPosting) for p in postings)
    print(f"[{'OK' if all_valid else 'FAIL'}] All results are RawJobPosting instances")

    if len(postings) > 0 and all_valid:
        print(f"\n{'=' * 60}")
        print(f"  PHASE 2 VERIFICATION PASSED")
        print(f"{'=' * 60}")
    else:
        print(f"\n[FAIL] Phase 2 verification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
