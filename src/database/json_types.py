"""JSON vs JSONB for SQLAlchemy: SQLite tests use JSON; Postgres uses JSONB."""
import os

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import INET, JSONB

from src.config.settings import settings


def get_json_type():
    """Appropriate JSON column type for the current DATABASE_URL."""
    url = os.getenv("DATABASE_URL", "") or settings.database.database_url
    if url.startswith("sqlite"):
        return JSON
    return JSONB


def get_inet_type():
    """INET for Postgres; string for SQLite (in-memory tests)."""
    url = os.getenv("DATABASE_URL", "") or settings.database.database_url
    if url.startswith("sqlite"):
        return String(45)
    return INET
