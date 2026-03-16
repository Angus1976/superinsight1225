"""Unit tests for WebhookManager.

Uses a pure in-memory mock approach adapted from test_memory.py.
FakeSession stores WebhookConfig rows in a plain list and interprets
SQLAlchemy statement objects via isinstance checks.
"""

import pytest
from contextlib import contextmanager
from typing import Optional
from uuid import uuid4

from sqlalchemy.sql.dml import Delete
from sqlalchemy.sql.selectable import Select

from src.service_engine.models import WebhookConfig
from src.service_engine.webhook import WebhookManager


# ---------------------------------------------------------------------------
# Fake session / session-factory (pure in-memory, no DB)
# ---------------------------------------------------------------------------

class _FakeScalars:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeResult:
    def __init__(self, rows: Optional[list] = None) -> None:
        self._rows = rows or []

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)


class FakeSession:
    """In-memory session backed by a shared list of WebhookConfig objects."""

    def __init__(self, store: list) -> None:
        self._store = store
        self._pending: list = []

    def add(self, obj) -> None:
        self._pending.append(obj)

    def flush(self) -> None:
        self._store.extend(self._pending)
        self._pending.clear()

    def commit(self) -> None:
        self._store.extend(self._pending)
        self._pending.clear()

    def rollback(self) -> None:
        self._pending.clear()

    def close(self) -> None:
        pass

    def execute(self, stmt):
        if isinstance(stmt, Delete):
            return self._exec_delete(stmt)
        if isinstance(stmt, Select):
            return self._exec_select(stmt)
        return _FakeResult()

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _extract_filters(stmt):
        """Pull id / api_key_id values from the WHERE clause."""
        wh_id = api_key_id = None
        clause = getattr(stmt, "whereclause", None)
        if clause is None:
            return wh_id, api_key_id
        parts = list(clause.clauses) if hasattr(clause, "clauses") else [clause]
        for part in parts:
            left = getattr(part, "left", None)
            right = getattr(part, "right", None)
            if left is None or right is None:
                continue
            col = str(getattr(left, "key", ""))
            val = getattr(right, "value", None)
            if col == "id":
                wh_id = val
            elif col == "api_key_id":
                api_key_id = val
        return wh_id, api_key_id

    def _filtered(self, stmt) -> list:
        wh_id, api_key_id = self._extract_filters(stmt)
        rows = self._store
        if wh_id is not None:
            rows = [r for r in rows if str(r.id) == str(wh_id)]
        if api_key_id is not None:
            rows = [r for r in rows if str(r.api_key_id) == str(api_key_id)]
        return rows

    def _exec_select(self, stmt: Select) -> _FakeResult:
        return _FakeResult(rows=self._filtered(stmt))

    def _exec_delete(self, stmt: Delete) -> _FakeResult:
        wh_id, api_key_id = self._extract_filters(stmt)
        self._store[:] = [
            r for r in self._store
            if not (
                (wh_id is None or str(r.id) == str(wh_id))
                and (api_key_id is None or str(r.api_key_id) == str(api_key_id))
            )
        ]
        return _FakeResult()


def _make_factory(store: list):
    @contextmanager
    def factory():
        s = FakeSession(store)
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
    return factory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

API_KEY_ID = str(uuid4())
API_KEY_ID_2 = str(uuid4())


@pytest.fixture()
def store():
    return []


@pytest.fixture()
def session_factory(store):
    return _make_factory(store)


@pytest.fixture()
def manager(session_factory):
    return WebhookManager(session_factory=session_factory)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed(store: list, api_key_id: str = API_KEY_ID, n: int = 1) -> list[WebhookConfig]:
    configs = []
    for i in range(n):
        cfg = WebhookConfig(
            id=uuid4(),
            api_key_id=api_key_id,
            webhook_url=f"https://example.com/hook-{i}",
            webhook_secret=f"secret-{i}",
            webhook_events=["event.created", "event.updated"],
            enabled=True,
        )
        store.append(cfg)
        configs.append(cfg)
    return configs


# ---------------------------------------------------------------------------
# Tests — create
# ---------------------------------------------------------------------------

class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_dict_with_all_fields(self, manager):
        result = await manager.create(
            api_key_id=API_KEY_ID,
            webhook_url="https://example.com/hook",
            webhook_secret="s3cret",
            webhook_events=["order.created"],
            enabled=True,
        )
        assert isinstance(result, dict)
        assert result["api_key_id"] == API_KEY_ID
        assert result["webhook_url"] == "https://example.com/hook"
        assert result["webhook_secret"] == "s3cret"
        assert result["webhook_events"] == ["order.created"]
        assert result["enabled"] is True
        assert "id" in result

    @pytest.mark.asyncio
    async def test_create_default_enabled(self, manager):
        result = await manager.create(
            api_key_id=API_KEY_ID,
            webhook_url="https://example.com/hook",
            webhook_secret="s3cret",
            webhook_events=[],
        )
        assert result["enabled"] is True


# ---------------------------------------------------------------------------
# Tests — get
# ---------------------------------------------------------------------------

class TestGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, manager, store):
        configs = _seed(store)
        result = await manager.get(str(configs[0].id))
        assert result is not None
        assert result["id"] == str(configs[0].id)
        assert result["webhook_url"] == configs[0].webhook_url

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, manager):
        result = await manager.get(str(uuid4()))
        assert result is None


# ---------------------------------------------------------------------------
# Tests — get_by_api_key
# ---------------------------------------------------------------------------

class TestGetByApiKey:
    @pytest.mark.asyncio
    async def test_returns_all_for_api_key(self, manager, store):
        _seed(store, api_key_id=API_KEY_ID, n=3)
        _seed(store, api_key_id=API_KEY_ID_2, n=2)
        results = await manager.get_by_api_key(API_KEY_ID)
        assert len(results) == 3
        assert all(r["api_key_id"] == API_KEY_ID for r in results)

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_api_key(self, manager):
        results = await manager.get_by_api_key(str(uuid4()))
        assert results == []


# ---------------------------------------------------------------------------
# Tests — update
# ---------------------------------------------------------------------------

class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_modifies_fields(self, manager, store):
        configs = _seed(store)
        wh_id = str(configs[0].id)
        result = await manager.update(
            wh_id,
            webhook_url="https://new.example.com/hook",
            enabled=False,
        )
        assert result is not None
        assert result["webhook_url"] == "https://new.example.com/hook"
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, manager):
        result = await manager.update(str(uuid4()), webhook_url="https://x.com")
        assert result is None


# ---------------------------------------------------------------------------
# Tests — delete
# ---------------------------------------------------------------------------

class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_config(self, manager, store):
        configs = _seed(store)
        wh_id = str(configs[0].id)
        deleted = await manager.delete(wh_id)
        assert deleted is True
        assert await manager.get(wh_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, manager):
        result = await manager.delete(str(uuid4()))
        assert result is False
