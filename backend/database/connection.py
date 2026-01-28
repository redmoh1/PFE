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


def init_db():
    """Initialize database tables.
    
    Creates all tables defined in models.py if they don't exist.
    For production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)
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
