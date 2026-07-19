import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.scrapers.anyjobok import AnyjobokScraper


def test_anyjobok_public_jobs_fixture_parses_article_cards():
    fixture_path = Path(__file__).parent / "fixtures" / "anyjobok_jobs_page.html"
    html = fixture_path.read_text(encoding="utf-8")

    scraper = AnyjobokScraper()
    postings = scraper._parse_listing_page(html)

    assert len(postings) == 2
    assert postings[0].job_title == "Social Media Executive"
    assert postings[0].company_name == "Grape Expectations (Pvt) Ltd"
    assert postings[0].location_raw == "Colombo 03"
    assert (
        postings[0].source_url
        == "https://anyjobok.com/jobs/social-media-executive-grape-expectations-pvt-ltd"
    )

    assert postings[1].job_title == "Recovery Officer"
    assert postings[1].company_name == "Ninewells Hospital (Pvt) Ltd"
    assert postings[1].location_raw == "Colombo 05"


if __name__ == "__main__":
    test_anyjobok_public_jobs_fixture_parses_article_cards()
    print("AnyJobOK public jobs fixture parsed successfully")
