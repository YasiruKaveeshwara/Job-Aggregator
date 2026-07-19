"""
topjobs.lk scraper — POST-based search form.

topjobs.lk uses a server-rendered HTML table returned via a POST form
submission.  We search for each of our role keywords and merge the results.

POST endpoint::

    https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp

Required form fields (discovered via browser DevTools):
    txtKeyWord   -- search term (e.g. "software engineer")
    hdnBlockSize -- max results to return (we use 1000 to get all at once)
    btnSearch    -- literal "Search"
    ... (other fields left empty)

Response HTML structure (table row per job)::

    <tr id="tr0" onclick="createAlert('0','DEFZZZ','0001525035','DEFZZZ','...')">
      <td>1</td>                          <!-- row number -->
      <td>1525035</td>                    <!-- job ref no -->
      <td>                               <!-- position + employer -->
        <span hidden id="hdnJC0">0001525035</span>  <!-- job code (JC) -->
        <span hidden id="hdnEC0">DEFZZZ</span>       <!-- employer code (EC) -->
        <span hidden id="hdnAC0">DEFZZZ</span>       <!-- advert code (AC) -->
        <h2><span>Software Developer </span></h2>
        <h1>Siyapatha Finance PLC</h1>
      </td>
      <td>Please refer the vacancy</td>  <!-- description -->
      <td>Sun Jul 19 2026</td>           <!-- opening date -->
      <td>Thu Jul 30 2026</td>           <!-- closing date -->
      <td>Borella</td>                   <!-- town -->
    </tr>

Job detail URL::

    https://www.topjobs.lk/applicant/vacancy.jsp?AC={AC}&EC={EC}&JC={JC}
"""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag

from app.scrapers.base import BaseScraper, RawJobPosting

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.topjobs.lk"
_SEARCH_URL = f"{_BASE_URL}/applicant/vacancybyfunctionalarea.jsp"
_JOB_URL_TEMPLATE = f"{_BASE_URL}/applicant/vacancy.jsp?AC={{ac}}&EC={{ec}}&JC={{jc}}"

# Search terms that cover our IT role keywords.
# topjobs is Sri Lanka's largest job board so these are broad on purpose;
# normalize.py's role-keyword filter handles precision.
_QUERIES = [
    "software engineer",
    "web developer",
    "frontend",
    "backend",
    "full stack",
    "software intern",
]

_BLOCK_SIZE = "1000"  # ask for up to 1000 results per search (server-side limit)


class TopjobsScraper(BaseScraper):
    """Scraper for topjobs.lk using its POST-based vacancy search."""

    platform_name = "topjobs.lk"

    def _get_client(self) -> httpx.Client:
        """Browser-like headers to avoid bot-detection."""
        return httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": _BASE_URL,
                "Referer": _SEARCH_URL,
            },
            follow_redirects=True,
            timeout=30.0,
        )

    def fetch(self) -> list[RawJobPosting]:
        """Search topjobs.lk for all configured role queries and merge."""
        results: list[RawJobPosting] = []
        seen_urls: set[str] = set()

        if not self.robots_allowed(_SEARCH_URL):
            logger.warning("[%s] robots.txt disallows — skipping", self.platform_name)
            return []

        with self._get_client() as client:
            for query in _QUERIES:
                postings = self._search(client, query)
                for p in postings:
                    if p.source_url not in seen_urls:
                        seen_urls.add(p.source_url)
                        results.append(p)
                logger.info(
                    "[%s] Query '%s' → %d unique so far",
                    self.platform_name, query, len(results),
                )

        logger.info(
            "[%s] Finished — %d postings collected", self.platform_name, len(results)
        )
        return results

    def _search(self, client: httpx.Client, keyword: str) -> list[RawJobPosting]:
        """POST a search for *keyword* and parse all job rows from the response."""
        payload = {
            "txtJSCode": "",
            "txtKeyWord": keyword,
            "btnSearch": "Search",
            "FA": "",
            "pageNo": "",
            "CookieAppend": "false",
            "SID": "",
            "hdnPreJC": "",
            "hdnPreAC": "",
            "hdnPreEC": "",
            "hdnNextJC": "",
            "hdnNextAC": "",
            "hdnNextEC": "",
            "selectdRow": "",
            "hdnNavigateLink": (
                "../applicant/vacancybyfunctionalarea.jsp"
                f"?FA=&jst=OPEN&sQut=&txtKeyWord={keyword}"
                "&chkGovt=&chkParttime=&chkWalkin=&chkNGO=&"
            ),
            "hdnBlockSize": _BLOCK_SIZE,
            "hdnTotalJobs": "0",
            "hdnCurrentPage": "1",
        }

        try:
            response = self._request_with_retry(
                client, "POST", _SEARCH_URL, data=payload
            )
        except Exception:
            logger.warning(
                "[%s] POST failed for keyword='%s'",
                self.platform_name, keyword, exc_info=True,
            )
            return []

        return self._parse_results_page(response.text)

    def _parse_results_page(self, html: str) -> list[RawJobPosting]:
        """Parse the search results HTML table into RawJobPosting objects."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[RawJobPosting] = []

        for row in soup.select("tr[id^='tr']"):
            # Only process rows whose id matches tr0, tr1, tr2, …
            row_id = row.get("id", "")
            if not re.match(r"^tr\d+$", row_id):
                continue

            try:
                posting = self._parse_row(row)
                if posting:
                    postings.append(posting)
            except Exception:
                logger.warning(
                    "[%s] Failed to parse row %s — skipping",
                    self.platform_name, row_id, exc_info=True,
                )

        return postings

    def _parse_row(self, row: Tag) -> Optional[RawJobPosting]:
        """Extract one RawJobPosting from a <tr id='trN'> row."""
        tds = row.select("td")
        if len(tds) < 7:
            return None

        # ── Position column (TD[2]) ──────────────────────────────────
        td_position = tds[2]

        # Hidden spans carry the codes needed to build the detail URL
        jc_span = td_position.find("span", id=re.compile(r"^hdnJC"))
        ec_span = td_position.find("span", id=re.compile(r"^hdnEC"))
        ac_span = td_position.find("span", id=re.compile(r"^hdnAC"))
        jc = jc_span.get_text(strip=True) if jc_span else ""
        ec = ec_span.get_text(strip=True) if ec_span else ""
        ac = ac_span.get_text(strip=True) if ac_span else ""

        # Job title is in <h2><span>
        h2 = td_position.find("h2")
        if not h2:
            return None
        title = h2.get_text(strip=True)
        if not title:
            return None

        # Company name is in <h1>
        h1 = td_position.find("h1")
        company = h1.get_text(strip=True) if h1 else ""

        # ── Other columns ─────────────────────────────────────────────
        description = tds[3].get_text(strip=True)
        opening_date = tds[4].get_text(strip=True)   # "Sun Jul 19 2026"
        location = tds[6].get_text(strip=True) if len(tds) > 6 else None

        # Build the canonical detail page URL
        if jc and ec and ac:
            source_url = _JOB_URL_TEMPLATE.format(ac=ac, ec=ec, jc=jc)
        else:
            # Fallback: use the search URL (avoids dedup collisions)
            source_url = _SEARCH_URL

        return RawJobPosting(
            job_title=title,
            company_name=company,
            location_raw=location or None,
            salary_raw=None,
            description_raw=description,
            posted_date_raw=opening_date or None,
            source_url=source_url,
            image_url=None,
        )
