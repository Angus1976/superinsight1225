"""
Property-based tests for SkillHandler and WebhookManager.

Tests skill whitelist enforcement and webhook CRUD round-trip using Hypothesis.
Covers Properties 9 and 15 from the design document.
"""

from uuid import uuid4

import pytest
from hypothesis import assume, given, settings, strategies as st

from src.service_engine.handlers.skill import SkillHandler
from src.service_engine.router import ServiceEngineError
from src.service_engine.webhook import WebhookManager

# ---------------------------------------------------------------------------
# Reuse FakeSession infrastructure from test_webhook.py
# ---------------------------------------------------------------------------
from tests.test_service_engine.test_webhook import _make_factory


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------
_nonempty_text = st.text(min_size=1, max_size=30).filter(lambda s: s.strip())


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 9: 技能白名单强制执行
# For any skill request, if skill_id is not in the API Key's skill_whitelist,
# the system should return 403 with error_code SKILL_NOT_ALLOWED.
# When skill_id IS in the whitelist (or whitelist is empty), no error.
# Validates: Requirements 5.2, 5.3
# ---------------------------------------------------------------------------

@given(
    skill_id=_nonempty_text,
    whitelist=st.lists(_nonempty_text, min_size=1, max_size=10),
)
@settings(max_examples=100)
def test_skill_whitelist_enforcement(skill_id: str, whitelist: list[str]):
    """skill_id not in non-empty whitelist → 403; in whitelist → no error."""
    if skill_id in whitelist:
        # Should NOT raise
        SkillHandler.check_whitelist(skill_id, whitelist)
    else:
        with pytest.raises(ServiceEngineError) as exc_info:
            SkillHandler.check_whitelist(skill_id, whitelist)
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "SKILL_NOT_ALLOWED"


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 15: Webhook 配置 CRUD 往返
# For any valid webhook config, creating it then reading it back should
# return consistent webhook_url, webhook_secret, and webhook_events.
# Validates: Requirements 8.2
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(
    webhook_url=st.from_regex(
        r"https://[a-z]{3,20}\.[a-z]{2,5}/[a-z]{1,10}", fullmatch=True,
    ),
    webhook_secret=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    webhook_events=st.lists(
        st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
        min_size=0,
        max_size=5,
    ),
)
@settings(max_examples=100)
async def test_webhook_crud_round_trip(
    webhook_url: str,
    webhook_secret: str,
    webhook_events: list[str],
):
    """Create a webhook config then read it back — fields must match."""
    store: list = []
    manager = WebhookManager(session_factory=_make_factory(store))
    api_key_id = str(uuid4())

    created = await manager.create(
        api_key_id, webhook_url, webhook_secret, webhook_events,
    )
    fetched = await manager.get(created["id"])

    assert fetched is not None
    assert fetched["webhook_url"] == webhook_url
    assert fetched["webhook_secret"] == webhook_secret
    assert fetched["webhook_events"] == webhook_events
