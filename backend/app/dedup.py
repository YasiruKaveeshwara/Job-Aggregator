"""
Deduplication logic.

Computes job_hash = sha256(normalized_company + normalized_title) and
decides whether a scraped posting is a new job, a duplicate source for
an existing job, or a new posting cycle of a recurring role.

Implemented in Phase 4.
"""
