import logging
import sqlite3

from sqlmodel import Session, SQLModel, create_engine, select

from app.config import DATABASE_URL

_logger = logging.getLogger(__name__)

# connect_args={"check_same_thread": False} is required for SQLite
# when used with FastAPI (which may serve requests from different threads).
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# ── Default search keywords (seeded once into the DB) ──────────────────
_DEFAULT_SEARCH_KEYWORDS: list[str] = [
    "software engineer",
    "web developer",
    "frontend developer",
    "backend developer",
    "full stack developer",
    "software intern",
    "intern",
    "internship",
    "trainee",
    "data engineer",
    "QA engineer",
    "devops engineer",
    "mobile developer",
    "machine learning",
    "software developer",
]

# ── Default search locations (seeded once into the DB) ─────────────────
# All 25 Sri Lankan districts + country-level + work-type modifiers
_DEFAULT_SEARCH_LOCATIONS: list[str] = [
    # Country
    "sri lanka",
    # Western Province
    "colombo", "gampaha", "kalutara",
    # Central Province
    "kandy", "matale", "nuwara eliya",
    # Southern Province
    "galle", "matara", "hambantota",
    # Northern Province
    "jaffna", "kilinochchi", "mannar", "mullaitivu", "vavuniya",
    # Eastern Province
    "batticaloa", "ampara", "trincomalee",
    # North Western Province
    "kurunegala", "puttalam",
    # North Central Province
    "anuradhapura", "polonnaruwa",
    # Uva Province
    "badulla", "monaragala",
    # Sabaragamuwa Province
    "ratnapura", "kegalle",
    # Work type
    "remote", "onsite", "hybrid",
]


def create_db_and_tables() -> None:
    """Create all tables defined by SQLModel subclasses (if they don't exist)."""
    SQLModel.metadata.create_all(engine)
    _run_migrations()
    _seed_search_keywords()
    _seed_search_locations()


def _run_migrations() -> None:
    """Lightweight column-level migrations for SQLite.

    SQLModel's ``create_all`` won't ALTER existing tables, so we add any
    missing columns here.  Each migration is idempotent (checks first).
    """
    url = str(engine.url).replace("sqlite:///", "")
    try:
        conn = sqlite3.connect(url)
        cur = conn.cursor()

        # ── Source.last_scraped_at ────────────────────────────────
        cur.execute("PRAGMA table_info(source)")
        columns = {row[1] for row in cur.fetchall()}
        if "last_scraped_at" not in columns:
            cur.execute("ALTER TABLE source ADD COLUMN last_scraped_at TIMESTAMP")
            _logger.info("Migration: added 'last_scraped_at' to source table")

        # ── Job.image_url ─────────────────────────────────────────
        cur.execute("PRAGMA table_info(job)")
        job_cols = {row[1] for row in cur.fetchall()}
        if "image_url" not in job_cols:
            cur.execute("ALTER TABLE job ADD COLUMN image_url TEXT")
            _logger.info("Migration: added 'image_url' to job table")

        # ── ScrapeRun.progress & duration_seconds ─────────────────
        cur.execute("PRAGMA table_info(scraperun)")
        run_cols = {row[1] for row in cur.fetchall()}
        if "progress" not in run_cols:
            cur.execute("ALTER TABLE scraperun ADD COLUMN progress TEXT DEFAULT '{}'")
            _logger.info("Migration: added 'progress' to scraperun table")
        if "duration_seconds" not in run_cols:
            cur.execute("ALTER TABLE scraperun ADD COLUMN duration_seconds REAL")
            _logger.info("Migration: added 'duration_seconds' to scraperun table")

        conn.commit()
        conn.close()
    except Exception:
        _logger.warning("Migration check failed (may be first run)", exc_info=True)


def _seed_search_keywords() -> None:
    """Insert default search keywords if the table is empty."""
    # Import here to avoid circular import (models imports db indirectly)
    from app.models import SearchKeyword

    with Session(engine) as session:
        existing = session.exec(select(SearchKeyword)).first()
        if existing is not None:
            return  # already seeded

        for kw in _DEFAULT_SEARCH_KEYWORDS:
            session.add(SearchKeyword(keyword=kw, enabled=True))
        session.commit()
        _logger.info("Seeded %d default search keywords", len(_DEFAULT_SEARCH_KEYWORDS))


def _seed_search_locations() -> None:
    """Insert default search locations if the table is empty."""
    from app.models import SearchLocation

    with Session(engine) as session:
        existing = session.exec(select(SearchLocation)).first()
        if existing is not None:
            return  # already seeded

        for loc in _DEFAULT_SEARCH_LOCATIONS:
            session.add(SearchLocation(location=loc, enabled=True))
        session.commit()
        _logger.info("Seeded %d default search locations", len(_DEFAULT_SEARCH_LOCATIONS))


def get_session():
    """
    FastAPI dependency that yields a database session.

    Usage in a router::

        @router.get("/items")
        def list_items(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session

