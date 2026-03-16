"""
Property-based tests for UserMemory and ContextBuilder memory toggle.

Tests memory persistence round-trip, compression threshold, and
include_memory toggle using Hypothesis.
Covers Properties 12, 13, and 14 from the design document.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from src.service_engine.memory import COMPRESSION_THRESHOLD, MemoryManager
from src.service_engine.context import ContextBuilder
from src.service_engine.models import UserMemory
from src.service_engine.schemas import ServiceRequest

# ---------------------------------------------------------------------------
# Reuse FakeSession infrastructure from test_memory.py
# ---------------------------------------------------------------------------
from tests.test_service_engine.test_memory import _make_factory


def _seed_n(store: list, n: int, user_id: str = "u-1", tenant_id: str = "t-1"):
    """Seed *n* interaction entries (handles n > 59 unlike test_memory._seed)."""
    for i in range(n):
        store.append(
            UserMemory(
                id=uuid4(),
                user_id=user_id,
                tenant_id=tenant_id,
                memory_type="interaction",
                content={"msg": f"entry-{i}"},
                created_at=datetime(
                    2025, 1, 1, i // 3600, (i // 60) % 60, i % 60,
                    tzinfo=timezone.utc,
                ),
            )
        )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------
# Non-empty printable strings for user_id / tenant_id
_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip())


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 12: 记忆持久化往返
# For any user interaction, after processing, user_memories should have a
# new record with matching user_id, tenant_id, and a created_at timestamp.
# Validates: Requirements 7.1, 7.3, 7.5
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(user_id=_id_strategy, tenant_id=_id_strategy)
@settings(max_examples=100)
async def test_memory_persistence_round_trip(user_id: str, tenant_id: str):
    """Appending a memory then loading returns a matching entry."""
    store: list = []
    manager = MemoryManager(session_factory=_make_factory(store))

    await manager.append_memory(user_id, tenant_id, {"role": "user", "text": "hi"})
    entries = await manager.load_memories(user_id, tenant_id)

    assert len(entries) >= 1
    latest = entries[-1]
    assert latest["user_id"] == user_id
    assert latest["tenant_id"] == tenant_id
    assert latest["memory_type"] == "interaction"
    assert latest["created_at"] is not None


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 13: 记忆压缩阈值
# For any user, when memory entries exceed 50, compression should be
# triggered, and the count after compression should be less than before.
# Validates: Requirements 7.4
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(n=st.integers(min_value=51, max_value=100))
@settings(max_examples=100)
async def test_memory_compression_threshold(n: int):
    """When entries exceed COMPRESSION_THRESHOLD, compress reduces count."""
    store: list = []
    manager = MemoryManager(session_factory=_make_factory(store))

    _seed_n(store, n)
    count_before = len(store)
    assert count_before == n
    assert count_before > COMPRESSION_THRESHOLD

    await manager.compress_if_needed("u-1", "t-1")

    entries = await manager.load_memories("u-1", "t-1")
    count_after = len(entries)

    assert count_after < count_before
    assert any(e["memory_type"] == "summary" for e in entries)


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 14: include_memory 开关
# For any request with include_memory=false, the system should not load
# history memory. With include_memory=true, memory should be returned.
# Validates: Requirements 7.6
# ---------------------------------------------------------------------------

_memory_entry = st.fixed_dictionaries({
    "id": st.text(min_size=1, max_size=10),
    "content": st.text(min_size=0, max_size=50),
})


@pytest.mark.asyncio
@given(entries=st.lists(_memory_entry, min_size=0, max_size=10))
@settings(max_examples=100)
async def test_include_memory_toggle(entries: list[dict]):
    """include_memory=False yields empty memory; True yields input entries."""
    builder = ContextBuilder()

    req_off = ServiceRequest(
        request_type="chat",
        user_id="u1",
        messages=[{"role": "user", "content": "hi"}],
        include_memory=False,
    )
    ctx_off = await builder.build(req_off, entries)
    assert ctx_off["memory"] == []

    req_on = ServiceRequest(
        request_type="chat",
        user_id="u1",
        messages=[{"role": "user", "content": "hi"}],
        include_memory=True,
    )
    ctx_on = await builder.build(req_on, entries)
    assert ctx_on["memory"] == entries
