"""
anyjobok.com scraper — HTML-based, public jobs listings.

Supported entry points:
- ``https://anyjobok.com/jobs``

Pagination uses ``?page=N`` on those public listing pages.

The current public jobs pages render listings as ``<article>`` cards with an
``<h2><a ...>`` title link, a company/location line, and a visible posted
date. We also keep a fallback parser for the older link-wrapped card shape so
the scraper can still handle browser-captured fixtures from previous layouts.

NOTE ON ACCESS
--------------
The search URL is blocked in this environment, but the public listing pages
above are accessible and contain the same job cards. This scraper uses those
supported routes instead of trying to force the blocked search endpoint.
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup, Tag
import httpx

from app.scrapers.base import BaseScraper, RawJobPosting
from app.search_keywords import get_enabled_search_keywords

logger = logging.getLogger(__name__)

_BASE_URL = "https://anyjobok.com"
_MAX_PAGES_PER_ENTRYPOINT = 10

# Telltale strings from Cloudflare-style interstitials. If any of these show
# up in a "successful" (200 OK) response, it's not a real page — it's a
# challenge screen, and treating it as "0 results" would hide a block behind
# what looks like a normal empty search.
_CHALLENGE_MARKERS = (
    "just a moment",
    "checking your browser",
    "cf-browser-verification",
    "enable javascript and cookies to continue",
    "attention required! | cloudflare",
    "verify you are human",
)


def _looks_like_challenge_page(html: str) -> bool:
    """Heuristic check for a bot-management interstitial instead of a
    real listings page."""
    lowered = html[:3000].lower()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


class AnyjobokScraper(BaseScraper):
    """Scraper for anyjobok.com using public HTML listing pages."""

    platform_name = "anyjobok.com"

    def _get_client(self) -> httpx.Client:
        """Configured client for AnyJobOK public pages."""
        return httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    def fetch(self) -> list[RawJobPosting]:
        """Fetch job postings from anyjobok.com's public listing pages."""
        results: list[RawJobPosting] = []
        seen_urls: set[str] = set()

        # Build entrypoints: always include /jobs, plus one per keyword
        keywords = get_enabled_search_keywords()
        entrypoints = ["/jobs"] + [
            f"/jobs?search={kw.replace(' ', '+')}" for kw in keywords
        ]

        with self._get_client() as client:
            for entrypoint in entrypoints:
                base_url = f"{_BASE_URL}{entrypoint}"

                if not self.robots_allowed(base_url):
                    logger.warning("robots.txt disallows %s — skipping", base_url)
                    continue

                for page in range(1, _MAX_PAGES_PER_ENTRYPOINT + 1):
                    url = base_url if page == 1 else f"{base_url}&page={page}"

                    try:
                        response = self._request_with_retry(
                            client, "GET", url, timeout=30.0
                        )
                    except Exception:
                        logger.warning(
                            "[%s] Failed to fetch %s page %d — stopping pagination",
                            self.platform_name,
                            entrypoint,
                            page,
                            exc_info=True,
                        )
                        break

                    page_results = self._parse_listing_page(response.text)

                    if not page_results:
                        logger.info(
                            "[%s] No jobs on %s page %d — pagination complete",
                            self.platform_name,
                            entrypoint,
                            page,
                        )
                        break

                    new_jobs = 0
                    for job in page_results:
                        if job.source_url not in seen_urls:
                            seen_urls.add(job.source_url)
                            results.append(job)
                            new_jobs += 1

                    logger.info(
                        "[%s] %s page %d yielded %d new postings (total: %d)",
                        self.platform_name,
                        entrypoint,
                        page,
                        new_jobs,
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
        seen_urls: set[str] = set()

        for article in soup.select("main article"):
            try:
                posting = self._parse_article_card(article)
                if posting and posting.source_url not in seen_urls:
                    seen_urls.add(posting.source_url)
                    postings.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse article card — skipping",
                    self.platform_name,
                    exc_info=True,
                )

        if postings:
            return postings

        # Fallback for the older link-wrapped card layout captured in earlier fixtures.
        for card in soup.select('a[href*="/jobs/"]'):
            href = card.get("href", "")
            if href.rstrip("/").endswith("/jobs") or "/jobs?" in href:
                continue

            try:
                posting = self._parse_link_card(card, href)
                if posting and posting.source_url not in seen_urls:
                    seen_urls.add(posting.source_url)
                    postings.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse card %s — skipping",
                    self.platform_name,
                    href,
                    exc_info=True,
                )

        return postings

    def _parse_article_card(self, article: Tag) -> Optional[RawJobPosting]:
        """Extract a single job posting from a public <article> listing card."""
        link = article.select_one('h2 a[href*="/jobs/"]') or article.select_one(
            'a[href*="/jobs/"]'
        )
        if not link:
            return None
        href = link.get("href", "")
        if not href:
            return None

        title = link.get_text(strip=True)
        if not title:
            return None

        meta_div = article.find("div", class_=lambda c: c and "text-gray-600" in c)
        company = ""
        location = None
        if meta_div:
            meta_text = meta_div.get_text(strip=True)
            if "·" in meta_text:
                parts = meta_text.split("·", 1)
                company = parts[0].strip()
                location = parts[1].strip() if len(parts) > 1 else None
            else:
                company = meta_text

        time_tag = article.find("time")
        posted_date = None
        if time_tag:
            posted_date = (
                time_tag.get("datetime") or time_tag.get_text(strip=True) or None
            )

        source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location,
            salary_raw=None,
            description_raw="",
            posted_date_raw=posted_date,
            source_url=source_url,
            image_url=None,
        )

    def _parse_link_card(self, card: Tag, href: str) -> Optional[RawJobPosting]:
        """Extract a single job posting from the older link-wrapped layout."""
        h2 = card.find("h2")
        if not h2:
            return None
        title = h2.get_text(strip=True)
        if not title:
            return None

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

        time_tag = card.find("time")
        posted_date = None
        if time_tag:
            posted_date = (
                time_tag.get("datetime") or time_tag.get_text(strip=True) or None
            )

        source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        img = card.find("img")
        image_url = img.get("src") if img else None
        if image_url and not image_url.startswith("http"):
            image_url = f"{_BASE_URL}{image_url}"

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location,
            salary_raw=None,
            description_raw="",  # Detail pages would need a separate fetch
            posted_date_raw=posted_date,
            source_url=source_url,
            image_url=image_url,
        )
