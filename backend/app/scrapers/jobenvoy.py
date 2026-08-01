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
from app.search_keywords import get_enabled_search_keywords
from app.config import SCRAPER_MAX_PAGES

logger = logging.getLogger(__name__)

_BASE_URL = "https://jobenvoy.com"
_SEARCH_URL_TEMPLATE = f"{_BASE_URL}/jobs?q={{query}}&country=LK"


class JobenvoyScraper(BaseScraper):
    """Scraper for jobenvoy.com using public search-result HTML."""

    platform_name = "jobenvoy.com"
    SITE_PROBE_URL = "https://jobenvoy.com"

    def fetch(self) -> list[RawJobPosting]:
        """Fetch job postings from jobenvoy.com for all configured keywords."""
        results: list[RawJobPosting] = []
        seen_urls: set[str] = set()

        keywords = get_enabled_search_keywords()
        if not keywords:
            logger.warning(
                "[%s] No search keywords in DB — skipping", self.platform_name
            )
            return []

        with self._get_client() as client:
            for query in keywords:
                query_slug = query.replace(" ", "+")
                start_url = _SEARCH_URL_TEMPLATE.format(query=query_slug)

                # Check robots.txt once per keyword (result is cached per-origin)
                if not self.robots_allowed(start_url):
                    logger.warning(
                        "[%s] robots.txt disallows %s — skipping keyword '%s'",
                        self.platform_name,
                        start_url,
                        query,
                    )
                    continue

                next_url: Optional[str] = start_url

                for page_num in range(1, SCRAPER_MAX_PAGES + 1):
                    if not next_url:
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
                        "[%s] query='%s' page %d -> %d new (total: %d)",
                        self.platform_name,
                        query,
                        page_num,
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

        # Image URL: <img> inside the link
        img = link.find("img")
        image_url = img.get("src") if img else None
        if image_url and not image_url.startswith("http"):
            image_url = f"{_BASE_URL}{image_url}"

        description = f"{title} - {company}" + (f" ({job_type})" if job_type else "")

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location,
            salary_raw=None,
            description_raw=description,
            posted_date_raw=None,
            source_url=source_url,
            image_url=image_url,
        )

    def _fetch_detail_description(self, url: str, fallback: str = "") -> str:
        """
        GET the jobenvoy.com job detail page and extract the description body.

        Falls back to ``fallback`` on any error.
        """
        if not url or not url.startswith("http"):
            return fallback
        try:
            with self._get_client() as client:
                resp = self._request_with_retry(client, "GET", url)
            soup = BeautifulSoup(resp.text, "html.parser")
            for selector in (
                ".job-description",
                ".job-detail",
                "[class*='description']",
                ".card-body",
                "article",
                "main section",
                "main",
            ):
                node = soup.select_one(selector)
                if node:
                    text = node.get_text(separator="\n", strip=True)
                    if len(text) > 80:
                        return text
        except Exception:
            logger.debug(
                "[%s] Detail page fetch failed for %s — using fallback",
                self.platform_name,
                url,
            )
        return fallback
