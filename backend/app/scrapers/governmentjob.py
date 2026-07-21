"""
governmentjob.lk scraper — browser-visible search results + API/HTML fallback.

The public search results page for ``?s=software&post_type=job_listing`` is
rendered as article cards and is the most reliable way to fetch the job
postings that appear in the browser. We use a browser context to load those
public pages, then fall back to the WordPress REST API and the older HTML
category page if needed.

The site still publishes some blog-style vacancy announcements, so we keep a
fallback parser for the older layouts as well.
"""

import logging
import re
from html import unescape
from typing import Any, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, RawJobPosting
from app.search_keywords import get_enabled_search_keywords
from app.config import SCRAPER_MAX_PAGES

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://governmentjob.lk/?s={query}&post_type=job_listing"
_SEARCH_PAGE_URL = (
    "https://governmentjob.lk/page/{page}/?s={query}&post_type=job_listing"
)

# WP REST API endpoint — category 15 = "Government Job Vacancies"
_WP_API_URL = "https://governmentjob.lk/wp-json/wp/v2/posts"
_WP_CATEGORY_ID = 15  # "government-job-vacancies"


# HTML fallback
_HTML_URL = "https://governmentjob.lk/government-job-vacancies/"

# Pattern to extract "company" from titles like "Ministry of Defence Vacancies 2026"
_TITLE_PATTERN = re.compile(r"^(.+?)\s+(?:Vacancies|Vacancy|Jobs?)\b", re.IGNORECASE)


class GovernmentjobScraper(BaseScraper):
    """Scraper for governmentjob.lk search results with fallbacks."""

    platform_name = "governmentjob.lk"

    def fetch(self) -> list[RawJobPosting]:
        """Fetch government job vacancy posts."""
        results = self._fetch_via_browser_search()
        if results:
            return results

        # Try WP REST API next
        results = self._fetch_via_api()
        if results:
            return results

        # Fallback to HTML scraping
        logger.info(
            "[%s] Browser/API failed — falling back to HTML", self.platform_name
        )
        return self._fetch_via_html()

    # ── Browser search results approach ─────────────────────────────

    def _fetch_via_browser_search(self) -> list[RawJobPosting]:
        """Fetch public search results pages for every configured keyword."""
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            logger.info("[%s] Playwright not available", self.platform_name)
            return []

        results: list[RawJobPosting] = []
        seen_urls: set[str] = set()

        try:
            with sync_playwright() as playwright:
                browser = self._launch_browser(playwright)
                try:
                    page = browser.new_page(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/126.0.0.0 Safari/537.36"
                        ),
                        locale="en-US",
                        viewport={"width": 1440, "height": 1200},
                    )

                    search_queries = get_enabled_search_keywords()
                    for query in search_queries:
                        query_encoded = quote_plus(query)
                        for page_num in range(1, SCRAPER_MAX_PAGES + 1):
                            url = (
                                _SEARCH_URL.format(query=query_encoded)
                                if page_num == 1
                                else _SEARCH_PAGE_URL.format(page=page_num, query=query_encoded)
                            )

                            try:
                                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                                page.wait_for_selector("main article", timeout=10000)
                            except Exception:
                                logger.warning(
                                    "[%s] Browser load failed for query='%s' page %d",
                                    self.platform_name, query, page_num, exc_info=True,
                                )
                                break

                            page_results = self._parse_search_results_page(page.content())
                            if not page_results:
                                logger.info(
                                    "[%s] No results for query='%s' page %d — stopping",
                                    self.platform_name, query, page_num,
                                )
                                break

                            new_jobs = 0
                            for job in page_results:
                                if job.source_url not in seen_urls:
                                    seen_urls.add(job.source_url)
                                    results.append(job)
                                    new_jobs += 1

                            logger.info(
                                "[%s] Query '%s' page %d → %d new (total: %d)",
                                self.platform_name, query, page_num, new_jobs, len(results),
                            )
                finally:
                    browser.close()
        except Exception:
            logger.warning(
                "[%s] Browser search fetch failed",
                self.platform_name,
                exc_info=True,
            )
            return []

        logger.info(
            "[%s] Browser search finished — %d postings collected",
            self.platform_name,
            len(results),
        )
        return results

    def _launch_browser(self, playwright):
        """Launch a Chromium browser using the best available local install."""
        launch_options = [
            {},
            {"channel": "msedge"},
            {"channel": "chrome"},
        ]

        last_error: Exception | None = None
        for options in launch_options:
            try:
                return playwright.chromium.launch(headless=True, **options)
            except Exception as exc:
                last_error = exc

        if last_error:
            raise last_error
        raise RuntimeError("Could not launch a browser")

    # ── WP REST API approach ─────────────────────────────────────────

    def _fetch_via_api(self) -> list[RawJobPosting]:
        """Fetch posts from WP REST API."""
        url = f"{_WP_API_URL}?categories={_WP_CATEGORY_ID}&per_page={SCRAPER_PAGE_SIZE}"

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

    def _parse_search_results_page(self, html: str) -> list[RawJobPosting]:
        """Parse browser-rendered search result cards."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[RawJobPosting] = []

        for article in soup.select("main article"):
            posting = self._parse_search_article(article)
            if posting:
                postings.append(posting)

        return postings

    def _parse_search_article(self, article) -> Optional[RawJobPosting]:
        """Extract a posting from the browser-rendered search result card."""
        link = article.select_one("h2.gjc-title a[href]") or article.select_one(
            'a[href*="/job/"]'
        )
        if not link:
            return None

        title = link.get_text(strip=True)
        source_url = link.get("href", "")
        if not title or not source_url:
            return None

        company_tag = article.select_one("p.gjc-company")
        company = (
            company_tag.get_text(strip=True)
            if company_tag
            else "Government of Sri Lanka"
        )

        location = self._clean_card_text(article.select_one("span.gjc-pill--loc"))
        employment_type = self._clean_card_text(
            article.select_one("span.gjc-pill--type")
        )
        salary = self._clean_card_text(article.select_one("span.gjc-pill--salary"))
        posted_hint = self._clean_card_text(article.select_one("span.gjc-pill--soon"))
        posted_date = posted_hint or self._clean_card_text(
            article.select_one("span.gjc-time")
        )

        img = article.select_one("img.gjc-logo-img")
        image_url = img.get("src") if img else None

        description_parts = [part for part in [employment_type, salary] if part]
        card_description = " | ".join(description_parts)

        # Fetch the detail page to get full vacancy description
        full_description = self._fetch_detail_description(source_url, card_description)

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location or "Sri Lanka",
            salary_raw=salary,
            description_raw=full_description,
            posted_date_raw=posted_date,
            source_url=source_url,
            image_url=image_url,
        )

    @staticmethod
    def _clean_card_text(node) -> Optional[str]:
        if not node:
            return None
        text = node.get_text(" ", strip=True)
        return text or None

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

    def _fetch_detail_description(self, url: str, fallback: str) -> str:
        """
        Fetch the job detail page and extract the main content body as plain text.

        Falls back to ``fallback`` if the page cannot be fetched or parsed.
        Uses the base-class HTTP client with rate limiting.
        """
        if not url or not url.startswith("http"):
            return fallback
        try:
            with self._get_client() as client:
                resp = self._request_with_retry(client, "GET", url)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Try common WP content containers in order of preference
            for selector in (
                ".entry-content",
                ".post-content",
                "article .content",
                "article",
                "main",
            ):
                node = soup.select_one(selector)
                if node:
                    text = node.get_text(separator="\n", strip=True)
                    if len(text) > 100:
                        return text
        except Exception:
            logger.debug(
                "[%s] Could not fetch detail page %s — using card snippet",
                self.platform_name,
                url,
            )
        return fallback


    @staticmethod
    def _extract_company(title: str) -> str:
        """
        Extract company/organisation name from vacancy title.

        "National Building Research Institute Vacancies 2026"
        → "National Building Research Institute"
        """
        match = _TITLE_PATTERN.match(title)
        return match.group(1).strip() if match else "Government of Sri Lanka"
