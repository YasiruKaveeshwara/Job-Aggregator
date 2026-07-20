"""
ITPro.lk scraper — HTML-based keyword search.

The site does not expose a reliable public API. Instead it serves
a standard HTML page for each keyword search:

    GET https://itpro.lk/search/{keyword}/
    GET https://itpro.lk/search/{keyword}/?p={page}

Each page returns up to 50 job cards. We scrape all pages for each
keyword and deduplicate by job ID.

HTML structure (per job card):
    <article class="job-card" id="{job_id}">
      <a href="{job_url}">
        <h2 class="jc-title">{title}</h2>
        <span class="jc-company">{company}</span>
        <span class="la">...{location}</span>
        <time class="time-posted" datetime="{iso_date}">...</time>
      </a>
    </article>

Pagination nav:
    <nav class='pagination'>
      <a class='navigate_page' href='.../?p=2'>2</a>
      ...
    </nav>
"""

import logging
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, RawJobPosting
from app.search_keywords import get_enabled_search_keywords

logger = logging.getLogger(__name__)

_BASE_SEARCH = "https://itpro.lk/search"
_MAX_PAGES = 10  # safety cap per keyword


class ItproScraper(BaseScraper):
    """Scraper for itpro.lk using keyword-based HTML search with pagination."""

    platform_name = "itpro.lk"

    def fetch(self) -> list[RawJobPosting]:
        seen_ids: set[str] = set()
        results: list[RawJobPosting] = []

        keywords = get_enabled_search_keywords()
        if not keywords:
            logger.warning("[%s] No search keywords in DB — skipping", self.platform_name)
            return []

        for keyword in keywords:
            self._fetch_keyword(keyword, seen_ids, results)

        logger.info("[%s] Total unique jobs fetched: %d", self.platform_name, len(results))
        return results

    def _fetch_keyword(
        self,
        keyword: str,
        seen_ids: set[str],
        results: list[RawJobPosting],
    ) -> None:
        """Fetch all pages for a single keyword, updating seen_ids and results in-place."""
        # URL-encode the keyword for use in the path
        slug = keyword.replace(" ", "+")
        base_url = f"{_BASE_SEARCH}/{slug}/"

        page = 1
        while page <= _MAX_PAGES:
            url = base_url if page == 1 else f"{base_url}?p={page}"

            try:
                with self._get_client() as client:
                    resp = self._request_with_retry(client, "GET", url)
            except Exception:
                logger.warning(
                    "[%s] Failed to fetch keyword=%r page=%d",
                    self.platform_name,
                    keyword,
                    page,
                    exc_info=True,
                )
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("article.job-card")

            if not cards:
                logger.debug(
                    "[%s] keyword=%r page=%d — no cards, stopping",
                    self.platform_name,
                    keyword,
                    page,
                )
                break

            new_on_page = 0
            for card in cards:
                job_id = card.get("id", "")
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                posting = self._parse_card(card, job_id)
                if posting:
                    results.append(posting)
                    new_on_page += 1

            logger.debug(
                "[%s] keyword=%r page=%d — %d cards, %d new",
                self.platform_name,
                keyword,
                page,
                len(cards),
                new_on_page,
            )

            # Check if there's a next page
            has_next = bool(soup.select_one(f"nav.pagination a.navigate_page[href*='p={page + 1}']"))
            if not has_next:
                break

            page += 1

        logger.info(
            "[%s] keyword=%r done — %d total unique so far",
            self.platform_name,
            keyword,
            len(seen_ids),
        )

    def _parse_card(self, card, job_id: str) -> RawJobPosting | None:
        """Parse a single job-card article element into a RawJobPosting."""
        try:
            link_tag = card.select_one("a[href]")
            job_url = link_tag["href"] if link_tag else f"https://itpro.lk/job/{job_id}/"

            title_tag = card.select_one("h2.jc-title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            company_tag = card.select_one("span.jc-company")
            company = company_tag.get_text(strip=True) if company_tag else ""

            # Location is in the second <span class="la"> inside <p>
            # (first la span contains the SVG icon, text is after it)
            location_tag = card.select_one("span.la")
            location = location_tag.get_text(strip=True) if location_tag else None
            # Strip leading SVG icon text artifacts
            if location:
                location = re.sub(r"^\s*[\u2000-\u9fff\ue000-\uffff]*\s*", "", location).strip()

            # Prefer the datetime attribute on time.time-posted
            time_tag = card.select_one("time.time-posted")
            posted_date_raw = time_tag.get("datetime") if time_tag else None

            return RawJobPosting(
                job_title=title,
                company_name=company,
                location_raw=location or None,
                salary_raw=None,
                description_raw="",
                posted_date_raw=posted_date_raw,
                source_url=str(job_url),
            )
        except Exception:
            logger.warning(
                "[%s] Failed to parse card id=%s",
                self.platform_name,
                job_id,
                exc_info=True,
            )
            return None
