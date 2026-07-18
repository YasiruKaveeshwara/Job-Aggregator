"""
ITPro.lk scraper — API-based, no HTML parsing needed.

Uses the public endpoint ``GET https://itpro.lk/api/v1/jobs`` which returns
a JSON list of all recent job postings.  No API key is required for read access.

The API returns jobs across all categories.  Since there's no working server-side
category filter, we fetch all jobs and let normalize.py's role-keyword matching
(Phase 4) handle filtering.  This is fine — itpro.lk is an IT-only board, so
most postings are relevant anyway.

API response shape per job::

    {
        "id": "14363",
        "title": "Associate Software Engineer",
        "description": "<p>HTML content...</p>",
        "summary": "Join Oak Integrated Systems as...",
        "type_id": "1",
        "category_id": "10",
        "location": "79",
        "company": "Oak Integrated Systems",
        "website": "https://example.com",
        "views_count": "66",
        "created_on": "2026-07-17 14:43:42"
    }

Location is a numeric ID (not a city name), so we construct the location from
the job detail page URL pattern instead.  The source URL for each posting is
``https://itpro.lk/job/{id}/``.
"""

import logging
from typing import Any

from app.scrapers.base import BaseScraper, RawJobPosting

logger = logging.getLogger(__name__)

# The API endpoint returns a JSON list of recent jobs.
# limit=200 fetches a large batch; the API also supports &page=N for pagination.
_API_URL = "https://itpro.lk/api/v1/jobs?limit=200"

# Location IDs to city names — mapped from the site's sidebar.
# This is a best-effort lookup; unknown IDs fall back to None.
_LOCATION_MAP: dict[str, str] = {
    "79": "Colombo",
    "80": "Galle",
    "81": "Gampaha",
    "82": "Jaffna",
    "83": "Kandy",
    "84": "Kegalle",
    "85": "Kurunegala",
    "86": "Matara",
    "88": "Remote",
    # Add more as you discover them — the API uses numeric IDs.
}


class ItproScraper(BaseScraper):
    """Scraper for itpro.lk using their public JSON API."""

    platform_name = "itpro.lk"

    def fetch(self) -> list[RawJobPosting]:
        """
        Fetch all current job postings from itpro.lk's API.

        Returns every posting as a ``RawJobPosting`` — role-keyword filtering
        happens later in normalize.py (Phase 4).
        """
        if not self.robots_allowed(_API_URL):
            logger.warning("robots.txt disallows access to %s — aborting", _API_URL)
            return []

        with self._get_client() as client:
            response = self._request_with_retry(client, "GET", _API_URL)
            data: list[dict[str, Any]] = response.json()

        logger.info("[%s] API returned %d postings", self.platform_name, len(data))

        results: list[RawJobPosting] = []
        for item in data:
            try:
                posting = self._parse_item(item)
                results.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse job id=%s — skipping",
                    self.platform_name,
                    item.get("id", "?"),
                    exc_info=True,
                )

        logger.info(
            "[%s] Successfully parsed %d/%d postings",
            self.platform_name,
            len(results),
            len(data),
        )
        return results

    def _parse_item(self, item: dict[str, Any]) -> RawJobPosting:
        """Convert one API response item into a RawJobPosting."""
        job_id = item.get("id", "")
        source_url = f"https://itpro.lk/job/{job_id}/"

        # Location is a numeric ID — look it up, default to None
        location_id = str(item.get("location", ""))
        location_name = _LOCATION_MAP.get(location_id)

        return RawJobPosting(
            job_title=item.get("title", "").strip(),
            company_name=item.get("company", "").strip(),
            location_raw=location_name,
            salary_raw=None,  # itpro.lk API doesn't expose salary data
            description_raw=item.get("description", ""),
            posted_date_raw=item.get("created_on"),
            source_url=source_url,
        )
