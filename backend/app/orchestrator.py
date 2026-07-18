"""
Scrape orchestrator.

Given a list of site names (or "all enabled"), runs each scraper's
.fetch() in isolation, passes results through normalize → dedup,
and records per-site counts into the ScrapeRun row for live progress
polling from the admin portal.

Implemented in Phase 4.
"""
