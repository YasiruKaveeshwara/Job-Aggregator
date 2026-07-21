"""
findmyjob.lk scraper — WordPress REST API (awsm_job_openings CPT).

Endpoint::

    GET https://findmyjob.lk/wp-json/wp/v2/awsm_job_openings
        ?per_page=20&page=1
        &_fields=id,title,content,excerpt,link,date
        &search={keyword}

Response is a JSON array of WP post objects.  We search each role keyword
separately and deduplicate by post ``id``.

Relevant fields::

    id              int    -- unique WP post ID
    date            str    -- ISO 8601 published date (e.g. "2026-07-16T07:08:40")
    link            str    -- canonical URL on findmyjob.lk
    title.rendered  str    -- HTML-encoded job title
    content.rendered str   -- full HTML post body (company name lives here)
    excerpt.rendered str   -- short HTML excerpt used as description

Company name extraction: The content HTML sometimes has an H2 "About the
company" section, but it's not reliable across all posts.  We do a best-effort
attempt; fall back to empty string which normalize.py tolerates.
"""

import logging
import re
from html import unescape
from typing import Any, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, RawJobPosting
from app.search_keywords import get_enabled_search_keywords
from app.config import SCRAPER_MAX_PAGES, SCRAPER_PAGE_SIZE

logger = logging.getLogger(__name__)

_BASE_URL = "https://findmyjob.lk"
_API_URL = f"{_BASE_URL}/wp-json/wp/v2/awsm_job_openings"



_CATEGORY_SOFTWARE = "software-development-web-qa-data-gis"

# Pattern to extract company name from "About the company" section heading text
_COMPANY_SECTION = re.compile(r"about the company", re.IGNORECASE)


class FindmyjobScraper(BaseScraper):
    """Scraper for findmyjob.lk using their WP REST API."""

    platform_name = "findmyjob.lk"

    def fetch(self) -> list[RawJobPosting]:
        """Search findmyjob.lk for all configured keywords and merge results."""
        results: list[RawJobPosting] = []
        seen_ids: set[int] = set()

        if not self.robots_allowed(_API_URL):
            logger.warning("[%s] robots.txt disallows — skipping", self.platform_name)
            return []

        keywords = get_enabled_search_keywords()
        if not keywords:
            logger.warning("[%s] No search keywords in DB — skipping", self.platform_name)
            return []

        with self._get_client() as client:
            for query in keywords:
                new_count = self._fetch_query(client, results, seen_ids, search=query)
                logger.info(
                    "[%s] Query '%s' → %d new (total: %d)",
                    self.platform_name, query, new_count, len(results),
                )

            # Extra pass: fetch by IT category
            new_count = self._fetch_query(
                client, results, seen_ids, category=_CATEGORY_SOFTWARE
            )
            logger.info(
                "[%s] Category '%s' → %d new (total: %d)",
                self.platform_name, _CATEGORY_SOFTWARE, new_count, len(results),
            )

        logger.info(
            "[%s] Finished — %d postings collected", self.platform_name, len(results)
        )
        return results

    def _fetch_query(
        self,
        client,
        results: list[RawJobPosting],
        seen_ids: set[int],
        search: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        """Paginate through results for a single keyword or category. Returns number of new jobs added."""
        new_count = 0

        for page in range(1, SCRAPER_MAX_PAGES + 1):
            params = {
                "per_page": SCRAPER_PAGE_SIZE,
                "page": page,
                "_fields": "id,title,content,excerpt,link,date",
            }
            if search:
                params["search"] = search
            if category:
                params["fmj_category"] = category

            url = f"{_API_URL}?{urlencode(params)}"

            try:
                response = self._request_with_retry(client, "GET", url)
                items: list[dict[str, Any]] = response.json()
            except Exception:
                logger.warning(
                    "[%s] Request failed for search='%s' category='%s' page=%d",
                    self.platform_name, search, category, page, exc_info=True,
                )
                break

            if not items:
                break  # no more pages

            for item in items:
                post_id = item.get("id")
                if post_id is None or post_id in seen_ids:
                    continue

                posting = self._parse_item(item)
                if posting:
                    seen_ids.add(post_id)
                    results.append(posting)
                    new_count += 1

            logger.debug(
                "[%s] search='%s' category='%s' page=%d → %d items",
                self.platform_name, search, category, page, len(items),
            )

            # If fewer than a full page returned, we've reached the end
            if len(items) < SCRAPER_PAGE_SIZE:
                break

        return new_count

    def _parse_item(self, item: dict[str, Any]) -> Optional[RawJobPosting]:
        """Convert one WP REST API post into a RawJobPosting."""
        try:
            # Title: HTML-encoded, e.g. "Senior Software Engineer &#8211; AI"
            raw_title = item.get("title", {}).get("rendered", "")
            title = unescape(
                BeautifulSoup(raw_title, "html.parser").get_text(strip=True)
            )
            if not title:
                return None

            source_url: str = item.get("link", "")
            posted_date: Optional[str] = item.get("date")  # "2026-07-16T07:08:40"

            # Content HTML — extract company name from "About the company" section
            content_html: str = item.get("content", {}).get("rendered", "")
            company = self._extract_company(content_html)

            # Excerpt — short description as plain text
            excerpt_html: str = item.get("excerpt", {}).get("rendered", "")
            description = BeautifulSoup(excerpt_html, "html.parser").get_text(
                separator=" ", strip=True
            )

            return RawJobPosting(
                job_title=title,
                company_name=company,
                location_raw="Sri Lanka",  # API doesn't expose location field
                salary_raw=None,
                description_raw=description,
                posted_date_raw=posted_date,
                source_url=source_url,
                image_url=None,
            )

        except Exception:
            logger.warning(
                "[%s] Failed to parse post id=%s",
                self.platform_name,
                item.get("id", "?"),
                exc_info=True,
            )
            return None

    @staticmethod
    def _extract_company(content_html: str) -> str:
        """
        Try to extract company name from the content HTML.

        The post body sometimes contains::

            <h2>About the company</h2>
            <p>Our client is XYZ Company...</p>

        We grab the first meaningful <p> after that heading.
        Falls back to empty string if not found.
        """
        if not content_html:
            return ""

        soup = BeautifulSoup(content_html, "html.parser")

        for heading in soup.find_all(["h2", "h3"]):
            if _COMPANY_SECTION.search(heading.get_text(strip=True)):
                # Grab the next <p> tag
                next_p = heading.find_next_sibling("p")
                if next_p:
                    text = next_p.get_text(strip=True)
                    # Take just the first sentence — company names are usually short
                    sentence = text.split(".")[0].strip()
                    # Trim "Our client is " / "Our client, " prefixes
                    sentence = re.sub(
                        r"^(our client(,?\s*(is|the|a|an))?\s*)", "",
                        sentence, flags=re.IGNORECASE,
                    ).strip()
                    if sentence:
                        return sentence[:120]  # cap length

        return ""

