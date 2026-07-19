"""
jobenvoy.com scraper — HTML-based, public search listings.

Entry point: ``https://jobenvoy.com/jobs?q=software&country=LK``.
The page exposes a public search UI plus pagination links, and the job card
markup is stable across the visible results pages.

Job card HTML structure::

    <div class="col-sm-12 col-md-4 col-lg-3 job-card-section">
      <a href="/jobs/view_job_post?jp_token=ODA5Ng==">
        <div class="job-card">
          <div class="job-meta">
            <span class="time-left">🕒 12 days left</span>
            <span class="job-type">Full-time Job</span>
          </div>
          <div class="job-details">
            <p class="employer">Company Name</p>
            <h3 class="job-title">Job Title</h3>
            <p class="location"><i ...></i> Colombo, Sri Lanka</p>
          </div>
        </div>
      </a>
    </div>
"""

import logging
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.scrapers.base import BaseScraper, RawJobPosting

logger = logging.getLogger(__name__)

_BASE_URL = "https://jobenvoy.com"
_SEARCH_URL = f"{_BASE_URL}/jobs?q=software&country=LK"
_MAX_PAGES = 3


class JobenvoyScraper(BaseScraper):
    """Scraper for jobenvoy.com using public search-result HTML."""

    platform_name = "jobenvoy.com"

    def fetch(self) -> list[RawJobPosting]:
        """Fetch software job postings from jobenvoy.com."""
        results: list[RawJobPosting] = []
        seen_urls: set[str] = set()

        with self._get_client() as client:
            next_url: Optional[str] = _SEARCH_URL

            for page_num in range(1, _MAX_PAGES + 1):
                if not next_url:
                    break

                if not self.robots_allowed(next_url):
                    logger.warning("robots.txt disallows %s — skipping", next_url)
                    break

                try:
                    response = self._request_with_retry(client, "GET", next_url)
                except Exception:
                    logger.warning(
                        "[%s] Failed to fetch %s — skipping",
                        self.platform_name,
                        next_url,
                        exc_info=True,
                    )
                    break

                page_results, discovered_next_url = self._parse_listing_page(
                    response.text, next_url
                )

                new_jobs = 0
                for posting in page_results:
                    if posting.source_url not in seen_urls:
                        seen_urls.add(posting.source_url)
                        results.append(posting)
                        new_jobs += 1

                logger.info(
                    "[%s] page %d (%s) yielded %d new postings (total: %d)",
                    self.platform_name,
                    page_num,
                    next_url,
                    new_jobs,
                    len(results),
                )

                if not discovered_next_url or discovered_next_url == next_url:
                    break

                next_url = discovered_next_url

        logger.info(
            "[%s] Finished — %d unique postings collected",
            self.platform_name,
            len(results),
        )
        return results

    def _parse_listing_page(
        self, html: str, base_url: str
    ) -> tuple[list[RawJobPosting], Optional[str]]:
        """Parse a single listing page into RawJobPosting objects."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[RawJobPosting] = []
        next_url: Optional[str] = None

        # Job cards are in <div class="job-card-section">
        for section in soup.select("div.job-card-section"):
            try:
                posting = self._parse_card(section)
                if posting:
                    postings.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse job card — skipping",
                    self.platform_name,
                    exc_info=True,
                )

        next_link = soup.select_one('a[href][rel="next"]') or soup.find(
            "a", string=lambda s: isinstance(s, str) and s.strip().lower() == "next"
        )
        if next_link and next_link.get("href"):
            next_url = urljoin(base_url, next_link.get("href"))

        return postings, next_url

    def _parse_card(self, section: Tag) -> Optional[RawJobPosting]:
        """Extract a single job posting from a job-card-section div."""
        # Find the link wrapping the card
        link = section.find("a", href=True)
        if not link:
            return None

        href = link.get("href", "")
        source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        # Job title: <h3 class="job-title">
        title_tag = section.find("h3", class_="job-title")
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        if not title:
            return None

        # Company: <p class="employer">
        employer_tag = section.find("p", class_="employer")
        company = employer_tag.get_text(strip=True) if employer_tag else ""

        # Location: <p class="location"> (contains an <i> icon prefix)
        location_tag = section.find("p", class_="location")
        location = None
        if location_tag:
            location = location_tag.get_text(strip=True)

        # Job type: <span class="job-type">
        type_tag = section.find("span", class_="job-type")
        job_type = type_tag.get_text(strip=True) if type_tag else None

        # Time left: <span class="time-left"> (e.g. "🕒 12 days left")
        time_tag = section.find("span", class_="time-left")
        time_left = time_tag.get_text(strip=True) if time_tag else None

        # Image URL: <img> inside the link
        img = link.find("img")
        image_url = img.get("src") if img else None
        if image_url and not image_url.startswith("http"):
            image_url = f"{_BASE_URL}{image_url}"

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location,
            salary_raw=None,
            description_raw=f"Job type: {job_type}" if job_type else "",
            posted_date_raw=time_left,  # "🕒 12 days left" — normalize.py handles
            source_url=source_url,
            image_url=image_url,
        )
