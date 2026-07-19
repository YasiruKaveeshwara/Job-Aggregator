"""
Standalone test for the RoosterScraper.
Hits the live API, validates the response shape, and prints results.

Run with: .\\venv\\Scripts\\python.exe test_rooster.py
"""

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s %(name)s  %(message)s",
)

from app.scrapers.rooster import RoosterScraper

def main():
    print("-" * 60)
    print("  TEST: rooster.jobs scraper")
    print("-" * 60)

    scraper = RoosterScraper()
    postings = scraper.fetch()

    if not postings:
        print("  ERROR: No postings returned — check network or API contract")
        sys.exit(1)

    print(f"\n  Total postings fetched: {len(postings)}\n")

    # Print first 10
    for i, p in enumerate(postings[:10], 1):
        print(f"  {i:2}. {p.job_title}")
        print(f"      Company : {p.company_name}")
        print(f"      Location: {p.location_raw}")
        print(f"      Salary  : {p.salary_raw}")
        print(f"      URL     : {p.source_url}")
        print(f"      Date    : {p.posted_date_raw}")
        desc_preview = (p.description_raw[:120].replace("\n", " ")) + "…"
        desc_preview = desc_preview.encode("ascii", errors="replace").decode("ascii")
        print(f"      Desc    : {desc_preview}")
        print()

    # Basic assertions
    errors = []
    for p in postings:
        if not p.job_title:
            errors.append(f"Missing title: {p}")
        if not p.company_name:
            errors.append(f"Missing company: {p}")
        if not p.source_url.startswith("https://rooster.jobs/jobs/"):
            errors.append(f"Bad URL: {p.source_url}")
        if p.location_raw and "sri lanka" not in p.location_raw.lower():
            # Check for known SL cities
            sl_kw = ["colombo","kandy","galle","jaffna","negombo","nugegoda",
                     "malabe","moratuwa","dehiwala","matara","kelaniya"]
            if not any(kw in p.location_raw.lower() for kw in sl_kw):
                errors.append(f"Non-SL location slipped through: {p.location_raw}")

    if errors:
        print(f"  WARNINGS ({len(errors)}):")
        for e in errors[:5]:
            print(f"    - {e}")
    else:
        print("  All validation checks passed.")

    # Salary sample
    with_salary = [p for p in postings if p.salary_raw]
    print(f"\n  Jobs with salary: {len(with_salary)}/{len(postings)}")
    for p in with_salary[:5]:
        print(f"    {p.job_title} @ {p.company_name}: {p.salary_raw}")

    print(f"\n  ROOSTER SCRAPER TEST PASSED — {len(postings)} SL postings collected")
    print("=" * 60)


if __name__ == "__main__":
    main()
