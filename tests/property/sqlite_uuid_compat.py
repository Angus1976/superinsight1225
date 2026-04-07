"""
Shared SQLite UUID column patching for property tests.

Multiple test modules used to define their own SQLiteUUID TypeDecorator and
restore with isinstance(col.type, SQLiteUUID). That breaks when another module
left columns as a *different* SQLiteUUID subclass — teardown skipped restore
and later tests saw broken PGUUID / bind behavior.

Always normalize from a snapshot of PGUUID columns, then restore captured
original types on teardown.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, cast
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import TypeDecorator


class SQLiteUUID(TypeDecorator):
    """UUID type that works with SQLite by storing as string."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value) if isinstance(value, UUID) else str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value) if not isinstance(value, UUID) else value
        return value


def snapshot_uuid_columns(models):
    """Pairs of (column, PGUUID type instance) captured at import time."""
    pairs = []
    for model in models:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                pairs.append((col, col.type))
    return pairs


def patch_models_to_sqlite_uuid(models, snapshot):
    """
    Reset columns from snapshot to PGUUID, then replace with SQLiteUUID.
    Returns a list of (column, original_type) for teardown.
    """
    for col, original_pg in snapshot:
        col.type = original_pg

    restore = []
    for model in models:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                restore.append((col, col.type))
                col.type = SQLiteUUID()
    return restore


def restore_uuid_columns(restore_list):
    for col, original_type in restore_list:
        col.type = original_type


def uuid_pk_eq(column, value):
    """Compare a UUID primary-key column to str/UUID (reliable SQLite + PGUUID)."""
    return cast(column, String) == str(value)
