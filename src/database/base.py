"""
Database base module for SQLAlchemy models.

Re-exports the Base class from connection module for convenience.
"""

from src.database.connection import Base

__all__ = ['Base']
