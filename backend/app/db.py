import logging
import sqlite3

from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL

_logger = logging.getLogger(__name__)

# connect_args={"check_same_thread": False} is required for SQLite
# when used with FastAPI (which may serve requests from different threads).
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    """Create all tables defined by SQLModel subclasses (if they don't exist)."""
    SQLModel.metadata.create_all(engine)
    _run_migrations()


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

        conn.commit()
        conn.close()
    except Exception:
        _logger.warning("Migration check failed (may be first run)", exc_info=True)


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
