"""
xpress.jobs scraper — JSON API (GET-based search).

Endpoint::

    GET https://xpress.jobs/api/jobs/searchJobs
        ?page=1&pageSize=20&keyword={keyword}
        &locations=&sectors=&jobTypes=&careerLevels=
        &sortBy=SortedCreateDate+DESC&byCVLess=false&byWalkIn=false

Response is a JSON array of job objects.  The field ``recordCount`` on the
first item tells us the total number of results so we can paginate cleanly.

Job detail URL::

    https://xpress.jobs/job/{jobId}

Relevant fields per item::

    jobId             int    -- unique identifier
    jobTitle          str    -- job title
    organizationName  str    -- company name
    overview          str    -- short description text
    locations         str    -- e.g. " Colombo, Western Province"
    jobType           str    -- e.g. "Full-Time"
    expiryDateOnWebsite str  -- ISO datetime (closing date)
    logoUri           str    -- company logo URL (nullable)
    recordCount       int    -- total results for this query (pagination)

Strategy:
- For each role keyword, paginate until the page is empty or we've
  exhausted ``recordCount``.
- Deduplicate by ``jobId`` across all keyword queries.
- normalize.py's role-keyword matching handles final precision filtering.
"""

import logging
from typing import Any, Optional
from urllib.parse import urlencode

from app.scrapers.base import BaseScraper, RawJobPosting
from app.search_keywords import get_enabled_search_keywords
from app.search_locations import get_enabled_search_locations
from app.config import SCRAPER_MAX_PAGES, SCRAPER_PAGE_SIZE

logger = logging.getLogger(__name__)

_BASE_URL = "https://xpress.jobs"
_API_URL = f"{_BASE_URL}/api/jobs/searchJobs"
_JOB_URL_TEMPLATE = f"{_BASE_URL}/jobs/view/{{job_id}}/"





class XpressjobsScraper(BaseScraper):
    """Scraper for xpress.jobs using their public JSON search API."""

    platform_name = "xpress.jobs"

    def fetch(self) -> list[RawJobPosting]:
        """Search xpress.jobs for all configured keywords and merge results."""
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
                new_count = self._fetch_query(client, query, results, seen_ids)
                logger.info(
                    "[%s] Query '%s' → %d new (total: %d)",
                    self.platform_name, query, new_count, len(results),
                )

        logger.info(
            "[%s] Finished — %d postings collected", self.platform_name, len(results)
        )
        return results

    def _fetch_query(
        self,
        client,
        keyword: str,
        results: list[RawJobPosting],
        seen_ids: set[int],
        location_str: str = "",
    ) -> int:
        """Paginate through results for a single keyword. Returns number of new jobs added."""
        new_count = 0

        for page in range(1, SCRAPER_MAX_PAGES + 1):
            params = {
                "page": page,
                "pageSize": SCRAPER_PAGE_SIZE,
                "keyword": keyword,
                "locations": location_str,
                "sectors": "",
                "jobTypes": "",
                "careerLevels": "",
                "sortBy": "SortedCreateDate DESC",
                "byCVLess": "false",
                "byWalkIn": "false",
            }
            url = f"{_API_URL}?{urlencode(params)}"

            try:
                response = self._request_with_retry(client, "GET", url)
                items: list[dict[str, Any]] = response.json()
            except Exception:
                logger.warning(
                    "[%s] Request failed for keyword='%s' page=%d",
                    self.platform_name, keyword, page, exc_info=True,
                )
                break

            if not items:
                break  # no more pages

            for item in items:
                job_id = item.get("jobId")
                if job_id is None or job_id in seen_ids:
                    continue

                posting = self._parse_item(item)
                if posting:
                    seen_ids.add(job_id)
                    results.append(posting)
                    new_count += 1

            logger.debug(
                "[%s] keyword='%s' page=%d → %d items",
                self.platform_name, keyword, page, len(items),
            )

            # If fewer than a full page returned, we've reached the end
            if len(items) < SCRAPER_PAGE_SIZE:
                break

        return new_count

    def _parse_item(self, item: dict[str, Any]) -> Optional[RawJobPosting]:
        """Convert one API response item into a RawJobPosting."""
        try:
            job_id: int = item["jobId"]
            title: str = (item.get("jobTitle") or "").strip()
            company: str = (item.get("organizationName") or "").strip()

            if not title or not company:
                return None

            # Locations: " Colombo, Western Province; Gampaha, Western Province"
            # Clean and take just the first location if multiple
            raw_location = (item.get("locations") or "").strip()
            location = raw_location.split(";")[0].strip() if raw_location else None

            # Overview is a short job description
            description = (item.get("overview") or "").strip()

            # Job type (Full-Time, Part-Time, etc.) — prepend to description
            job_type = (item.get("jobType") or "").strip()
            if job_type and description:
                description = f"{job_type} | {description}"
            elif job_type:
                description = job_type

            # Posted date — use the sorted create date, NOT the expiry date
            posted_date: Optional[str] = item.get("sortedCreateDate")

            # Company logo
            logo_uri: Optional[str] = item.get("logoUri")

            source_url = _JOB_URL_TEMPLATE.format(job_id=job_id)

            return RawJobPosting(
                job_title=title,
                company_name=company,
                location_raw=location,
                salary_raw=None,
                description_raw=description,
                posted_date_raw=posted_date,
                source_url=source_url,
                image_url=logo_uri,
            )
        except (KeyError, TypeError):
            logger.warning(
                "[%s] Failed to parse item id=%s",
                self.platform_name,
                item.get("jobId", "?"),
                exc_info=True,
            )
            return None

