"""
hire.lk scraper — HTML page with embedded JSON job data.

hire.lk is a server-side rendered site (Laravel/Blade).  Each job card is
rendered as an ``<article class="job-card">`` element whose ``data-card``
attribute holds a **complete JSON blob** with all the data we need — no
child-element parsing required.

Entry URL pattern::

    GET https://hire.lk/jobs?q={keyword}&location=

Also fetches IT-category browse (extra pass)::

    GET https://hire.lk/jobs?industry=it-software-engineering-web-cloud

``data-card`` JSON shape (relevant fields)::

    {
        "ulid":            "01KXN4AWECBHEDC0TR3FK2ACZP",
        "title":           "SOFTWARE ENGINEER",
        "company_name":    "NAWALOKA HOSPITALS PLC",
        "company_logo_url":"https://hire.lk/storage/32/download.webp",
        "location":        "COLOMBO",
        "detail_url":      "https://hire.lk/jobs/nawaloka.../software.../01K...",
        "description_snippet": "We're looking for a Software Engineer...",
        "badge_label":     "On-site",
        "employment_type_label": "Full Time",
        "industry_name":   "IT Software / Engineering / Web / Cloud",
        "expires_at_formatted": "July 30, 2026"
    }

All results fit on a single page — no pagination needed.
Deduplication is by ``ulid`` across all keyword passes.
"""

import json
import logging
from html import unescape
from typing import Any, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, RawJobPosting

logger = logging.getLogger(__name__)

_BASE_URL = "https://hire.lk"
_SEARCH_URL = f"{_BASE_URL}/jobs?q={{query}}&location="
_INDUSTRY_URL = f"{_BASE_URL}/jobs?industry=it-software-engineering-web-cloud"

# Keywords to search one by one
_QUERIES = [
    "software engineer",
    "web developer",
    "frontend developer",
    "backend developer",
    "full stack developer",
    "software intern",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class HirelkScraper(BaseScraper):
    """Scraper for hire.lk using its server-side rendered HTML pages."""

    platform_name = "hire.lk"

    def fetch(self) -> list[RawJobPosting]:
        """Search hire.lk for all configured keywords, then browse the IT industry."""
        results: list[RawJobPosting] = []
        seen_ulids: set[str] = set()

        with self._get_client() as client:
            # Keyword search passes
            for query in _QUERIES:
                url = _SEARCH_URL.format(query=quote_plus(query))

                if not self.robots_allowed(url):
                    logger.warning(
                        "[%s] robots.txt disallows %s — skipping",
                        self.platform_name, url,
                    )
                    continue

                new_count = self._fetch_page(client, url, results, seen_ulids)
                logger.info(
                    "[%s] Query '%s' → %d new (total: %d)",
                    self.platform_name, query, new_count, len(results),
                )

            # Extra pass: browse IT industry category
            if self.robots_allowed(_INDUSTRY_URL):
                new_count = self._fetch_page(client, _INDUSTRY_URL, results, seen_ulids)
                logger.info(
                    "[%s] IT industry browse → %d new (total: %d)",
                    self.platform_name, new_count, len(results),
                )

        logger.info(
            "[%s] Finished — %d postings collected", self.platform_name, len(results)
        )
        return results

    def _fetch_page(
        self,
        client,
        url: str,
        results: list[RawJobPosting],
        seen_ulids: set[str],
    ) -> int:
        """Fetch a single search/browse page and extract job cards. Returns new count."""
        try:
            response = self._request_with_retry(client, "GET", url, headers=_HEADERS)
        except Exception:
            logger.warning(
                "[%s] Request failed for %s", self.platform_name, url, exc_info=True
            )
            return 0

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select("article[data-card]")

        new_count = 0
        for article in articles:
            posting = self._parse_card(article)
            if posting is None:
                continue
            ulid = article.get("data-ulid", "")
            if not ulid or ulid in seen_ulids:
                continue
            seen_ulids.add(ulid)
            results.append(posting)
            new_count += 1

        logger.debug(
            "[%s] %s → %d articles, %d new",
            self.platform_name, url, len(articles), new_count,
        )
        return new_count

    def _parse_card(self, article) -> Optional[RawJobPosting]:
        """Parse the data-card JSON attribute of a single job article."""
        raw = article.get("data-card", "")
        if not raw:
            return None

        try:
            # BeautifulSoup already un-escapes HTML entities (&quot; → ")
            # json.loads handles JSON escape sequences (\/ etc.)
            data: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "[%s] Failed to decode data-card JSON — skipping",
                self.platform_name, exc_info=True,
            )
            return None

        title = (data.get("title") or "").strip().title()  # CAPS → Title Case
        company = (data.get("company_name") or "").strip().title()

        if not title:
            return None

        # Location: "COLOMBO" → "Colombo"
        location_raw = (data.get("location") or "").strip().title() or "Sri Lanka"

        # Build description from snippet + employment type + workplace mode
        snippet = unescape(data.get("description_snippet") or "")
        emp_type = data.get("employment_type_label") or ""
        workplace = data.get("badge_label") or ""
        desc_parts = [p for p in [emp_type, workplace, snippet] if p]
        description = " | ".join(desc_parts[:2]) + (" — " + snippet if snippet else "")

        # Expiry date as the only date available from this endpoint
        expires = data.get("expires_at_formatted")  # e.g. "July 30, 2026"

        detail_url = data.get("detail_url") or ""
        logo_url = data.get("company_logo_url")

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location_raw,
            salary_raw=None,
            description_raw=description,
            posted_date_raw=expires,
            source_url=detail_url,
            image_url=logo_url,
        )
