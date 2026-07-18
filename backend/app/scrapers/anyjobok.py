"""
anyjobok.com scraper — HTML-based, server-rendered listings.

Entry point: ``https://anyjobok.com`` or ``https://anyjobok.com/jobs``
Pagination: ``?page=N``

Job card HTML structure::

    <a href="https://anyjobok.com/jobs/{slug}" class="block rounded-xl ...">
      <h2 class="text-lg ...">Job Title</h2>
      <div class="mt-1 text-sm text-gray-600">Company · Location</div>
      <div class="...">FULL_TIME</div>
      <time datetime="2026-01-26T01:15:38+00:00">5 months ago</time>
    </a>

The site uses Tailwind classes, so we match by tag structure rather than
semantic class names.
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup, Tag

from app.scrapers.base import BaseScraper, RawJobPosting

logger = logging.getLogger(__name__)

# We scrape all jobs (all categories). Role-keyword filtering is in normalize.py.
_BASE_URL = "https://anyjobok.com"
_MAX_PAGES = 5  # 20 per page × 5 = 100 jobs max


class AnyjobokScraper(BaseScraper):
    """Scraper for anyjobok.com using server-rendered HTML."""

    platform_name = "anyjobok.com"

    def fetch(self) -> list[RawJobPosting]:
        """Fetch job postings from anyjobok.com across multiple pages."""
        results: list[RawJobPosting] = []

        with self._get_client() as client:
            for page in range(1, _MAX_PAGES + 1):
                url = f"{_BASE_URL}?page={page}" if page > 1 else _BASE_URL

                if not self.robots_allowed(url):
                    logger.warning("robots.txt disallows %s — stopping", url)
                    break

                try:
                    response = self._request_with_retry(client, "GET", url)
                except Exception:
                    logger.warning(
                        "[%s] Failed to fetch page %d — stopping pagination",
                        self.platform_name,
                        page,
                        exc_info=True,
                    )
                    break

                page_results = self._parse_listing_page(response.text)

                if not page_results:
                    logger.info(
                        "[%s] No jobs on page %d — pagination complete",
                        self.platform_name,
                        page,
                    )
                    break

                results.extend(page_results)
                logger.info(
                    "[%s] Page %d yielded %d postings (total: %d)",
                    self.platform_name,
                    page,
                    len(page_results),
                    len(results),
                )

        logger.info(
            "[%s] Finished — %d postings collected", self.platform_name, len(results)
        )
        return results

    def _parse_listing_page(self, html: str) -> list[RawJobPosting]:
        """Parse a single listing page into RawJobPosting objects."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[RawJobPosting] = []

        # Job cards are <a> elements linking to /jobs/{slug}
        for card in soup.select('a[href*="/jobs/"]'):
            href = card.get("href", "")
            # Filter out nav links like /jobs (without a slug)
            if href.rstrip("/").endswith("/jobs") or "/jobs?" in href:
                continue

            try:
                posting = self._parse_card(card, href)
                if posting:
                    postings.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse card %s — skipping",
                    self.platform_name,
                    href,
                    exc_info=True,
                )

        return postings

    def _parse_card(self, card: Tag, href: str) -> Optional[RawJobPosting]:
        """Extract a single job posting from an <a> card element."""
        # Title: <h2> inside the card
        h2 = card.find("h2")
        if not h2:
            return None
        title = h2.get_text(strip=True)
        if not title:
            return None

        # Company + Location: <div> with "text-sm text-gray-600"
        # Format is "Company  · Location" (with the middot separator)
        company = ""
        location = None
        meta_div = card.find("div", class_=lambda c: c and "text-gray-600" in c)
        if meta_div:
            meta_text = meta_div.get_text(strip=True)
            if "·" in meta_text:
                parts = meta_text.split("·", 1)
                company = parts[0].strip()
                location = parts[1].strip() if len(parts) > 1 else None
            else:
                company = meta_text

        # Posted date: <time datetime="...">
        time_tag = card.find("time")
        posted_date = time_tag.get("datetime") if time_tag else None

        # Source URL
        source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location,
            salary_raw=None,
            description_raw="",  # Detail pages would need a separate fetch
            posted_date_raw=posted_date,
            source_url=source_url,
        )
