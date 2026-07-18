"""
governmentjob.lk scraper — WordPress REST API + HTML fallback.

Uses the WP REST API ``GET /wp-json/wp/v2/posts`` to fetch vacancy posts
from the "Government Job Vacancies" category (id=15).  Falls back to HTML
scraping of ``/government-job-vacancies/`` if the API is unavailable.

This site publishes blog-style vacancy announcements (e.g. "Ministry of
Defence Vacancies 2026"), not structured job cards.  Each post title serves
as the job_title, and the post content contains the full description.
The "company" is extracted from the title (e.g. "Ministry of Defence").

Lower frequency source — mostly non-tech public-sector roles, but
occasionally includes state-owned tech employer postings (ICTA, LK Domain
Registry, etc.).  Role-keyword filtering in normalize.py handles relevance.
"""

import logging
import re
from html import unescape
from typing import Any, Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, RawJobPosting

logger = logging.getLogger(__name__)

# WP REST API endpoint — category 15 = "Government Job Vacancies"
_WP_API_URL = "https://governmentjob.lk/wp-json/wp/v2/posts"
_WP_CATEGORY_ID = 15  # "government-job-vacancies"
_WP_PER_PAGE = 50

# HTML fallback
_HTML_URL = "https://governmentjob.lk/government-job-vacancies/"

# Pattern to extract "company" from titles like "Ministry of Defence Vacancies 2026"
_TITLE_PATTERN = re.compile(r"^(.+?)\s+(?:Vacancies|Vacancy|Jobs?)\b", re.IGNORECASE)


class GovernmentjobScraper(BaseScraper):
    """Scraper for governmentjob.lk using WP REST API with HTML fallback."""

    platform_name = "governmentjob.lk"

    def fetch(self) -> list[RawJobPosting]:
        """Fetch government job vacancy posts."""
        # Try WP REST API first
        results = self._fetch_via_api()
        if results:
            return results

        # Fallback to HTML scraping
        logger.info("[%s] WP API failed — falling back to HTML", self.platform_name)
        return self._fetch_via_html()

    # ── WP REST API approach ─────────────────────────────────────────

    def _fetch_via_api(self) -> list[RawJobPosting]:
        """Fetch posts from WP REST API."""
        url = f"{_WP_API_URL}?categories={_WP_CATEGORY_ID}&per_page={_WP_PER_PAGE}"

        if not self.robots_allowed(url):
            return []

        try:
            with self._get_client() as client:
                response = self._request_with_retry(client, "GET", url)
                posts: list[dict[str, Any]] = response.json()
        except Exception:
            logger.warning(
                "[%s] WP API request failed", self.platform_name, exc_info=True
            )
            return []

        if not isinstance(posts, list):
            logger.warning("[%s] WP API returned non-list response", self.platform_name)
            return []

        results: list[RawJobPosting] = []
        for post in posts:
            try:
                posting = self._parse_wp_post(post)
                results.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse WP post id=%s — skipping",
                    self.platform_name,
                    post.get("id", "?"),
                    exc_info=True,
                )

        logger.info(
            "[%s] WP API returned %d posts, parsed %d",
            self.platform_name,
            len(posts),
            len(results),
        )
        return results

    def _parse_wp_post(self, post: dict[str, Any]) -> RawJobPosting:
        """Convert one WP REST API post into a RawJobPosting."""
        # Title is HTML-encoded, e.g. "Ministry of Defence Vacancies 2026"
        raw_title = post.get("title", {}).get("rendered", "")
        title = unescape(BeautifulSoup(raw_title, "html.parser").get_text(strip=True))

        # Extract company from title pattern
        company = self._extract_company(title)

        # Description from post content
        description = post.get("content", {}).get("rendered", "")

        # Source URL
        source_url = post.get("link", "")

        # Posted date
        posted_date = post.get("date")  # e.g. "2026-04-09T06:25:49"

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw="Sri Lanka",  # Government jobs are nationwide
            salary_raw=None,
            description_raw=description,
            posted_date_raw=posted_date,
            source_url=source_url,
        )

    # ── HTML fallback ────────────────────────────────────────────────

    def _fetch_via_html(self) -> list[RawJobPosting]:
        """Scrape job listings from the HTML category page."""
        if not self.robots_allowed(_HTML_URL):
            return []

        try:
            with self._get_client() as client:
                response = self._request_with_retry(client, "GET", _HTML_URL)
        except Exception:
            logger.warning(
                "[%s] HTML fallback request failed", self.platform_name, exc_info=True
            )
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        results: list[RawJobPosting] = []

        # Blog cards: <article class="blog-card ...">
        for article in soup.select("article.blog-card"):
            try:
                posting = self._parse_blog_card(article)
                if posting:
                    results.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse blog card — skipping",
                    self.platform_name,
                    exc_info=True,
                )

        logger.info(
            "[%s] HTML fallback yielded %d postings", self.platform_name, len(results)
        )
        return results

    def _parse_blog_card(self, article) -> Optional[RawJobPosting]:
        """Extract a posting from a blog-card <article>."""
        # Title: <h2 class="blog-card__title"><a href="...">Title</a></h2>
        h2 = article.select_one("h2.blog-card__title")
        if not h2:
            return None

        link = h2.find("a")
        title = link.get_text(strip=True) if link else h2.get_text(strip=True)
        source_url = link.get("href", "") if link else ""

        if not title:
            return None

        # Company from title
        company = self._extract_company(title)

        # Posted date: <time datetime="2026-04-09">
        time_tag = article.find("time")
        posted_date = time_tag.get("datetime") if time_tag else None

        # Excerpt as description
        excerpt_p = article.select_one("p.blog-card__excerpt")
        description = excerpt_p.get_text(strip=True) if excerpt_p else ""

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw="Sri Lanka",
            salary_raw=None,
            description_raw=description,
            posted_date_raw=posted_date,
            source_url=source_url,
        )

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_company(title: str) -> str:
        """
        Extract company/organisation name from vacancy title.

        "National Building Research Institute Vacancies 2026"
        → "National Building Research Institute"
        """
        match = _TITLE_PATTERN.match(title)
        return match.group(1).strip() if match else "Government of Sri Lanka"
