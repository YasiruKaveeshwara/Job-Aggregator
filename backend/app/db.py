"""
Database engine and session management.

The SQLite database is the single source of truth, and this module is
the only place that creates the engine / sessions.  Every router and
service function receives a session via FastAPI's dependency injection
(``Depends(get_session)``).
"""

from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL

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
