"""
Normalizer — cleans raw scraper output for insertion into the Job table.

Takes a ``RawJobPosting`` from any scraper and produces cleaned fields:

1. Strips whitespace / HTML remnants from title, company, description.
2. Normalizes company name (strips ``Pvt``, ``Ltd``, ``Limited``, etc.).
3. Parses ``salary_raw`` into ``salary_disclosed`` / ``salary_min`` / ``salary_max``.
4. Role-keyword matching against the config-driven allowlist.
"""

import re
from dataclasses import dataclass
from html import unescape
from typing import Optional

from bs4 import BeautifulSoup

from app.config import (
    ROLE_KEYWORDS_EXCLUDE,
)
from app.scrapers.base import RawJobPosting
from app.search_keywords import get_enabled_search_keywords


# ── Company-name normalization ───────────────────────────────────────

# Suffixes to strip, ordered longest-first so "(Pvt) Ltd." matches
# before "Ltd" alone.  Case-insensitive.
_COMPANY_SUFFIXES = re.compile(
    r"""
    \s*                         # leading whitespace before the suffix
    (?:
        \(Pvt\)\s*Ltd\.?        # (Pvt) Ltd  or  (Pvt) Ltd.
      | \(Private\)\s*Limited   # (Private) Limited
      | Private\s+Limited       # Private Limited
      | Pvt\.?\s*Ltd\.?         # Pvt Ltd  or  Pvt. Ltd.
      | Limited                 # Limited
      | Ltd\.?                  # Ltd  or  Ltd.
      | PLC                     # Public Limited Company
      | Inc\.?                  # Inc  or  Inc.
      | Corp\.?                 # Corp  or  Corp.
    )
    \s*$                        # trailing whitespace + end-of-string
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ── Salary parsing ───────────────────────────────────────────────────

# Match patterns like "LKR 50,000 - 100,000" or "Rs. 50000-100000"
# or just "LKR 80000" (single figure).
_SALARY_RANGE = re.compile(
    r"""
    (?:LKR|Rs\.?)\s*            # currency prefix
    ([\d,]+)                    # min salary
    (?:                         # optional range part
        \s*[-\u2013\u2014to]+\s*  # separator (hyphen, en-dash, em-dash, or "to")
        (?:LKR|Rs\.?)?\s*       # optional repeated prefix
        ([\d,]+)                # max salary
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ── Result dataclass ─────────────────────────────────────────────────

@dataclass
class NormalizedPosting:
    """Cleaned posting fields, ready for dedup.py / Job insertion."""

    job_title: str
    company_name: str               # normalized (suffixes stripped)
    location_raw: Optional[str]
    location_normalized: Optional[str]
    role_match: str                  # the keyword(s) that matched
    salary_disclosed: bool
    salary_min: Optional[int]
    salary_max: Optional[int]
    description_clean: Optional[str]
    posted_date_raw: Optional[str]   # still raw; orchestrator parses to datetime
    source_url: str
    platform: str                    # which scraper produced this
    image_url: Optional[str] = None  # company logo or job image URL


# ── Public API ───────────────────────────────────────────────────────

def normalize(
    raw: RawJobPosting,
    platform: str,
) -> Optional[NormalizedPosting]:
    """
    Clean a raw posting and check role-keyword match.

    Returns ``None`` if the posting doesn't match any role keyword
    (meaning it should be discarded).
    """
    title = _clean_text(raw.job_title)
    company = _normalize_company(raw.company_name)
    description = _clean_html(raw.description_raw) if raw.description_raw else None
    location = _clean_text(raw.location_raw) if raw.location_raw else None

    # ── Role-keyword matching ────────────────────────────────────
    role_match = _match_role(title)
    if role_match is None:
        return None  # not a relevant posting

    # ── Salary parsing ───────────────────────────────────────────
    salary_disclosed, salary_min, salary_max = _parse_salary(raw.salary_raw)

    return NormalizedPosting(
        job_title=title,
        company_name=company,
        location_raw=raw.location_raw,
        location_normalized=location,
        role_match=role_match,
        salary_disclosed=salary_disclosed,
        salary_min=salary_min,
        salary_max=salary_max,
        description_clean=description,
        posted_date_raw=raw.posted_date_raw,
        source_url=raw.source_url,
        platform=platform,
        image_url=raw.image_url,
    )


# ── Internal helpers ─────────────────────────────────────────────────

def _clean_text(text: Optional[str]) -> str:
    """Strip whitespace, collapse runs of spaces, unescape HTML entities."""
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_html(html: str) -> str:
    """Strip HTML tags and return plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Collapse multiple spaces / newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_company(name: str) -> str:
    """Strip corporate suffixes and clean whitespace."""
    name = _clean_text(name)
    name = _COMPANY_SUFFIXES.sub("", name).strip()
    # Remove trailing dots/commas left behind
    name = name.rstrip(".,").strip()
    return name


def _match_role(title: str) -> Optional[str]:
    """
    Check if a title matches the role-keyword config.

    Prefers the longest matching keyword (so ``"associate software engineer"``
    wins over ``"software engineer"`` when both appear in the title).

    Returns the matched keyword string (e.g. ``"software engineer intern"``)
    or ``None`` if no match.
    """
    title_lower = title.lower()

    # Load include keywords from DB (same list scrapers use to search)
    include_keywords = get_enabled_search_keywords()

    # Check exclusion list first
    for excl in ROLE_KEYWORDS_EXCLUDE:
        if excl.lower() in title_lower:
            return None

    # Check inclusion keywords — prefer the longest match
    matched_keyword: Optional[str] = None
    for kw in include_keywords:
        if kw.lower() in title_lower:
            if matched_keyword is None or len(kw) > len(matched_keyword):
                matched_keyword = kw

    return matched_keyword


def _parse_salary(
    salary_raw: Optional[str],
) -> tuple[bool, Optional[int], Optional[int]]:
    """
    Parse a raw salary string into structured values.

    Returns (salary_disclosed, salary_min, salary_max).
    """
    if not salary_raw:
        return False, None, None

    match = _SALARY_RANGE.search(salary_raw)
    if not match:
        return False, None, None

    min_str = match.group(1).replace(",", "")
    salary_min = int(min_str)

    max_str = match.group(2)
    salary_max = int(max_str.replace(",", "")) if max_str else salary_min

    return True, salary_min, salary_max
