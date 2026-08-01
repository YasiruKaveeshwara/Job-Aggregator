"""
jobseeker.lk scraper — WordPress-based Sri Lankan job portal.

jobseeker.lk is a WordPress site using the CoverNews theme.  Job listings
are rendered as ``<article>`` elements inside search-result pages.

Entry URL pattern::

    GET https://jobseeker.lk/?s={keyword}

Pagination::

    GET https://jobseeker.lk/page/{n}/?s={keyword}

Each article contains:
  - ``h3.article-title > a``  → job title + detail URL
  - ``ul.cat-links a``        → categories (e.g. "IT Jobs", "Internship")
  - ``.posts-date > a``       → relative date ("2 weeks ago")
  - ``.post-description > p`` → short description snippet
  - ``a.aft-readmore``        → apply/detail link (same as title href)

All data is in server-side rendered HTML — no JavaScript execution needed.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, RawJobPosting
from app.search_keywords import get_enabled_search_keywords

logger = logging.getLogger(__name__)

_BASE_URL = "https://jobseeker.lk"
_SEARCH_URL = f"{_BASE_URL}/?s={{query}}"
_PAGE_URL = f"{_BASE_URL}/page/{{page}}/?s={{query}}"
_MAX_PAGES = 5  # Cap per keyword to avoid over-crawling

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class JobseekerlkScraper(BaseScraper):
    """Scraper for jobseeker.lk using server-side rendered HTML search pages."""

    platform_name = "jobseeker.lk"

    def fetch(self) -> list[RawJobPosting]:
        """Search jobseeker.lk for all configured keywords across multiple pages."""
        results: list[RawJobPosting] = []
        seen_urls: set[str] = set()

        keywords = get_enabled_search_keywords()

        with self._get_client() as client:
            for query in keywords:
                encoded_query = quote_plus(query)

                for page_num in range(1, _MAX_PAGES + 1):
                    if page_num == 1:
                        url = _SEARCH_URL.format(query=encoded_query)
                    else:
                        url = _PAGE_URL.format(page=page_num, query=encoded_query)

                    if not self.robots_allowed(url):
                        logger.warning(
                            "[%s] robots.txt disallows %s — skipping",
                            self.platform_name,
                            url,
                        )
                        break

                    new_count = self._fetch_page(client, url, results, seen_urls)
                    logger.info(
                        "[%s] Query '%s' page %d -> %d new (total: %d)",
                        self.platform_name,
                        query,
                        page_num,
                        new_count,
                        len(results),
                    )

                    # If no new jobs were found on this page, stop paginating
                    if new_count == 0:
                        break

        logger.info(
            "[%s] Finished — %d postings collected", self.platform_name, len(results)
        )
        return results

    def _fetch_page(
        self,
        client,
        url: str,
        results: list[RawJobPosting],
        seen_urls: set[str],
    ) -> int:
        """Fetch a single search page and extract job articles. Returns new count."""
        try:
            response = self._request_with_retry(client, "GET", url, headers=_HEADERS)
        except Exception:
            logger.warning(
                "[%s] Request failed for %s", self.platform_name, url, exc_info=True
            )
            return 0

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select("article.post")

        new_count = 0
        for article in articles:
            posting = self._parse_article(article)
            if posting is None:
                continue
            if posting.source_url in seen_urls:
                continue
            seen_urls.add(posting.source_url)
            results.append(posting)
            new_count += 1

        logger.debug(
            "[%s] %s → %d articles, %d new",
            self.platform_name,
            url,
            len(articles),
            new_count,
        )
        return new_count

    def _parse_article(self, article) -> Optional[RawJobPosting]:
        """Parse a single <article> element into a RawJobPosting."""

        # ── Title and URL ────────────────────────────────────────────
        title_tag = article.select_one("h3.article-title a")
        if title_tag is None:
            return None

        title = title_tag.get_text(strip=True)
        detail_url = title_tag.get("href", "")

        if not title or not detail_url:
            return None

        # ── Categories ───────────────────────────────────────────────
        cat_tags = article.select("ul.cat-links a.covernews-categories")
        categories = [
            c.get_text(strip=True) for c in cat_tags if c.get_text(strip=True)
        ]

        # ── Date ─────────────────────────────────────────────────────
        date_tag = article.select_one(".item-metadata.posts-date a")
        date_text = date_tag.get_text(strip=True) if date_tag else ""
        posted_date_raw = self._parse_relative_time(date_text)

        # ── Description snippet ──────────────────────────────────────
        desc_tag = article.select_one(".post-description p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Append categories to description for better context
        if categories:
            cat_str = " | ".join(categories)
            if description:
                description = f"{cat_str} — {description}"
            else:
                description = cat_str

        # Ensure we have at least some description
        if not description:
            description = title

        # ── Company name ─────────────────────────────────────────────
        # jobseeker.lk does not display company names in search results;
        # attempt to extract from the description snippet.
        company = self._extract_company(description)

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw="Sri Lanka",
            salary_raw=None,
            description_raw=description,
            posted_date_raw=posted_date_raw,
            source_url=detail_url,
            image_url=None,
        )

    @staticmethod
    def _extract_company(description: str) -> str:
        """Try to extract a company name from the description snippet.

        jobseeker.lk snippets often contain patterns like:
          'Company:- TeaAI ( Pekoe Pvt ltd)'
          'Oak Integrated Systems Associate Software Engineer'
          'Predictiv AI is Hiring: Software Engineer'

        Falls back to 'jobseeker.lk' if no company can be identified.
        """
        if not description:
            return "jobseeker.lk"

        # Pattern: "Company:- <name>"
        match = re.search(r"Company[:\-–—\s]+([A-Z][\w\s&.,()]+)", description)
        if match:
            return match.group(1).strip().rstrip(".")

        return "jobseeker.lk"

    @staticmethod
    def _parse_relative_time(text: str) -> Optional[str]:
        """Convert '2 weeks ago', '3 days ago' etc. into an ISO datetime string."""
        if not text:
            return None

        text = text.lower().strip()
        match = re.search(
            r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*(?:ago|from now)",
            text,
        )
        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2)

        multipliers = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "month": 2592000,  # ~30 days
            "year": 31536000,  # ~365 days
        }

        seconds = amount * multipliers.get(unit, 0)
        if "ago" in text:
            dt = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        else:
            return None

        return dt.isoformat()
