import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.scrapers.jobenvoy import JobenvoyScraper


def test_jobenvoy_search_fixture_parses_job_cards():
    fixture_path = Path(__file__).parent / "fixtures" / "jobenvoy_search_page.html"
    html = fixture_path.read_text(encoding="utf-8")

    scraper = JobenvoyScraper()
    postings, next_url = scraper._parse_listing_page(
        html, "https://jobenvoy.com/jobs?q=software&country=LK"
    )

    assert len(postings) == 1
    assert postings[0].job_title == "Engineer - Application and Software"
    assert postings[0].company_name == "Envoy Ortus"
    assert postings[0].location_raw == "Colombo, Sri Lanka"
    assert postings[0].posted_date_raw == "🕒 27 days left"
    assert (
        postings[0].source_url
        == "https://jobenvoy.com/jobs/view_job_post?jp_token=ODEyMA=="
    )
    assert next_url == "https://jobenvoy.com/jobs?q=software&country=LK&per_page=2"


if __name__ == "__main__":
    test_jobenvoy_search_fixture_parses_job_cards()
    print("JobEnvoy search fixture parsed successfully")
