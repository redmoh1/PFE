"""
Database connection and session management.

FEATURES:
- SQLAlchemy session management
- Database initialization
- Dependency injection for FastAPI
- Migration support
"""

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base

# Database configuration
BASE_DIR = Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)

# Database URL (SQLite for now, easily switchable to PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DB_DIR / 'sales_intelligence.db'}"
)

# Create engine
# For SQLite: check_same_thread=False allows multi-threaded access
# For production with PostgreSQL, remove connect_args
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _sqlite_table_columns(conn, table_name: str) -> set[str]:
    return {str(row[1]) for row in conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()}


def _ensure_sqlite_column(conn, table_name: str, column_name: str, definition: str) -> None:
    columns = _sqlite_table_columns(conn, table_name)
    if column_name not in columns:
        conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    """Initialize database tables.
    
    Creates all tables defined in models.py if they don't exist.
    For production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)

    # Lightweight migrations for older local databases.
    with engine.begin() as conn:
        if DATABASE_URL.startswith("sqlite"):
            _ensure_sqlite_column(conn, "users", "branch_id", "INTEGER")
            _ensure_sqlite_column(conn, "users", "company_id", "INTEGER")
            _ensure_sqlite_column(conn, "users", "is_active", "BOOLEAN NOT NULL DEFAULT 1")
            _ensure_sqlite_column(conn, "users", "is_email_verified", "BOOLEAN NOT NULL DEFAULT 1")
            _ensure_sqlite_column(conn, "users", "email_verified_at", "DATETIME")

            _ensure_sqlite_column(conn, "branches", "phone", "VARCHAR(255)")
            _ensure_sqlite_column(conn, "branches", "is_active", "BOOLEAN NOT NULL DEFAULT 1")

            # Older local databases can miss tenant-scoping columns on analytics tables.
            _ensure_sqlite_column(conn, "forecast_results", "branch_id", "INTEGER")
            _ensure_sqlite_column(conn, "rfm_results", "branch_id", "INTEGER")
            _ensure_sqlite_column(conn, "sentiment_results", "branch_id", "INTEGER")
            _ensure_sqlite_column(conn, "model_performance_logs", "branch_id", "INTEGER")
            _ensure_sqlite_column(conn, "notifications", "branch_id", "INTEGER")

    print(f"Database initialized at: {DATABASE_URL}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions.
    
    Usage in FastAPI:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Drop and recreate all tables. USE WITH CAUTION!
    
    Only for development/testing purposes.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset complete")


init_db()
