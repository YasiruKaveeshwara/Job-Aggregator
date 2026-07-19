import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.scrapers.governmentjob import GovernmentjobScraper


def test_governmentjob_search_fixture_parses_article_cards():
    fixture_path = (
        Path(__file__).parent / "fixtures" / "governmentjob_search_results.html"
    )
    html = fixture_path.read_text(encoding="utf-8")

    scraper = GovernmentjobScraper()
    postings = scraper._parse_search_results_page(html)

    assert len(postings) == 2
    assert postings[0].job_title == "Software Developer"
    assert postings[0].company_name == "Siyapatha Finance PLC"
    assert postings[0].location_raw == "Colombo, Sri Lanka"
    assert postings[0].salary_raw == "Negotiable"
    assert postings[0].posted_date_raw == "3 days ago"

    assert postings[1].job_title == "Category Lead – AMC (Software & Hardware)"
    assert postings[1].company_name == "Nawaloka Hospitals PLC"
    assert postings[1].location_raw == "Colombo, Sri Lanka"
    assert postings[1].salary_raw == "Negotiable"
    assert postings[1].posted_date_raw == "Jul 23"


if __name__ == "__main__":
    test_governmentjob_search_fixture_parses_article_cards()
    print("GovernmentJob search fixture parsed successfully")
