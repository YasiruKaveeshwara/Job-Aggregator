"""
rooster.jobs scraper — JSON API (POST-based search).

Endpoint discovered via DevTools:
    POST https://api.rooster.jobs/jobSearch/jobs/search

Request body::

    {
        "query": ["software engineer"],
        "limit": 20,
        "page": 1,
        "filters": {}
    }

The response ``body.data`` is a list of structured job objects with full
salary, location, description (Markdown), and company info already parsed —
no HTML scraping needed.

Strategy:
- Search multiple role queries to maximise coverage (the API keyword-matches
  on the server side).
- Paginate each query until the page is empty or we've fetched enough.
- Filter server-side using ``country`` filter for Sri Lanka where possible;
  also post-filter client-side on location string to avoid noise from
  Pakistan / India results that slip through.
- Deduplicate by ``id`` across queries so the same posting isn't returned
  twice.
"""

import logging
from typing import Any, Optional

from app.scrapers.base import BaseScraper, RawJobPosting
from app.search_keywords import get_enabled_search_keywords

logger = logging.getLogger(__name__)

_API_URL = "https://api.rooster.jobs/jobSearch/jobs/search"
_JOB_URL_TEMPLATE = "https://rooster.jobs/jobs/{job_id}"

# Queries to run — each maps to one or more role keywords we care about.
# Using broader terms intentionally so we catch most variants, then
# normalize.py's role-keyword filter handles precision.
_PAGE_LIMIT = 20          # max items per page (API default)
_MAX_PAGES_PER_QUERY = 10  # cap at 200 results per query term

# Keep only jobs in Sri Lanka to avoid flooding with overseas roles
_LOCATION_KEYWORDS = ["sri lanka", "colombo", "kandy", "galle", "jaffna",
                       "negombo", "matara", "kurunegala", "ratnapura",
                       "badulla", "trincomalee", "batticaloa", "anuradhapura",
                       "polonnaruwa", "nugegoda", "dehiwala", "moratuwa",
                       "kelaniya", "malabe"]


class RoosterScraper(BaseScraper):
    """Scraper for rooster.jobs using their internal search JSON API."""

    platform_name = "rooster.jobs"

    def fetch(self) -> list[RawJobPosting]:
        """Fetch software-related job postings from rooster.jobs."""
        results: list[RawJobPosting] = []
        seen_ids: set[int] = set()

        if not self.robots_allowed(_API_URL):
            logger.warning("[%s] robots.txt disallows API endpoint", self.platform_name)
            return []

        keywords = get_enabled_search_keywords()
        if not keywords:
            logger.warning("[%s] No search keywords in DB — skipping", self.platform_name)
            return []

        with self._get_client() as client:
            for kw in keywords:
                query_results = self._fetch_query(client, [kw], seen_ids)
                results.extend(query_results)

        logger.info(
            "[%s] Finished — %d unique postings collected",
            self.platform_name,
            len(results),
        )
        return results

    def _fetch_query(
        self,
        client,
        query_terms: list[str],
        seen_ids: set[int],
    ) -> list[RawJobPosting]:
        """Paginate through results for a single query term."""
        postings: list[RawJobPosting] = []

        for page in range(1, _MAX_PAGES_PER_QUERY + 1):
            payload = {
                "query": query_terms,
                "limit": _PAGE_LIMIT,
                "page": page,
                "filters": {},
            }

            try:
                response = self._request_with_retry(
                    client, "POST", _API_URL, json=payload
                )
                data = response.json()
            except Exception:
                logger.warning(
                    "[%s] Request failed for query=%s page=%d",
                    self.platform_name,
                    query_terms,
                    page,
                    exc_info=True,
                )
                break

            items: list[dict[str, Any]] = (
                data.get("body", {}).get("data", []) or []
            )

            if not items:
                break  # no more pages

            for item in items:
                job_id = item.get("id")
                if job_id is None or job_id in seen_ids:
                    continue

                # Location filter — skip overseas roles
                if not self._is_srilanka(item.get("location", "")):
                    continue

                posting = self._parse_item(item)
                if posting:
                    seen_ids.add(job_id)
                    postings.append(posting)

            logger.debug(
                "[%s] query=%s page=%d → %d items (%d kept so far)",
                self.platform_name,
                query_terms,
                page,
                len(items),
                len(postings),
            )

            # If fewer than a full page returned, we've reached the end
            if len(items) < _PAGE_LIMIT:
                break

        return postings

    def _parse_item(self, item: dict[str, Any]) -> Optional[RawJobPosting]:
        """Convert a rooster.jobs API job object into a RawJobPosting."""
        try:
            job_id: int = item["id"]
            title: str = (item.get("title") or "").strip()
            company: str = (
                item.get("company_name")
                or item.get("subsidiary_company_name")
                or ""
            ).strip()
            location: str = (item.get("location") or "").strip()
            description: str = (item.get("description") or "").strip()
            posted_date: Optional[str] = item.get("created_at")
            source_url = _JOB_URL_TEMPLATE.format(job_id=job_id)

            if not title or not company:
                return None

            # Salary — rooster provides structured min/max/currency
            salary_raw = self._format_salary(item)

            image_url = item.get("company_logo_url")

            return RawJobPosting(
                job_title=title,
                company_name=company,
                location_raw=location or None,
                salary_raw=salary_raw,
                description_raw=description,
                posted_date_raw=posted_date,
                source_url=source_url,
                image_url=image_url,
            )
        except (KeyError, TypeError):
            logger.warning(
                "[%s] Failed to parse item id=%s",
                self.platform_name,
                item.get("id", "?"),
                exc_info=True,
            )
            return None

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _format_salary(item: dict[str, Any]) -> Optional[str]:
        """
        Build a salary_raw string from structured API fields.

        Rooster provides: min_salary, max_salary, salary_currency,
        salary_frequency.  We produce e.g. "LKR 80,000 - 300,000/month".
        """
        min_s = item.get("min_salary")
        max_s = item.get("max_salary")
        currency = item.get("salary_currency") or ""
        frequency = item.get("salary_frequency") or ""

        if min_s is None and max_s is None:
            return None

        currency = currency.upper()

        if min_s is not None and max_s is not None and min_s != max_s:
            amount = f"{int(min_s):,} - {int(max_s):,}"
        elif min_s is not None:
            amount = f"{int(min_s):,}"
        else:
            amount = f"{int(max_s):,}"

        parts = [currency, amount]
        if frequency:
            parts.append(f"/{frequency}")

        return " ".join(p for p in parts if p)

    @staticmethod
    def _is_srilanka(location: str) -> bool:
        """Check if a location string refers to Sri Lanka."""
        if not location:
            return False
        loc_lower = location.lower()
        return any(kw in loc_lower for kw in _LOCATION_KEYWORDS)
