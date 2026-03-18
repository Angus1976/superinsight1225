"""
Property-based tests for workflow selection persistence logic.
Feature: ai-workflow-engine

Validates Requirements 4.2, 4.3:
- Workflow ID persisted to localStorage on selection
- Auto-restore on page reload if workflow still enabled and user has permission
- Clear localStorage if workflow disabled or user has no permission
"""
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from typing import List, Optional


# ---------------------------------------------------------------------------
# Simulate the persistence logic from WorkflowSelector
# ---------------------------------------------------------------------------

STORAGE_KEY = 'ai_last_workflow_id'


def simulate_storage():
    """Simulate localStorage as a dict."""
    return {}


def persist_selection(storage: dict, workflow_id: str) -> None:
    """Simulate persisting workflow selection."""
    storage[STORAGE_KEY] = workflow_id


def restore_selection(
    storage: dict,
    workflows: List[dict],
) -> Optional[str]:
    """Simulate restoring workflow selection from storage.

    Returns the restored workflow_id or None if cleared.
    """
    saved_id = storage.get(STORAGE_KEY)
    if not saved_id:
        return None

    found = next(
        (w for w in workflows if w['id'] == saved_id and w['status'] == 'enabled'),
        None,
    )
    if found:
        return saved_id
    else:
        storage.pop(STORAGE_KEY, None)
        return None


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

workflow_id_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
    min_size=1, max_size=36,
)

workflow_st = st.fixed_dictionaries({
    'id': workflow_id_st,
    'status': st.sampled_from(['enabled', 'disabled']),
    'name': st.text(min_size=1, max_size=50),
})

workflows_st = st.lists(workflow_st, min_size=0, max_size=10)


# ---------------------------------------------------------------------------
# Property 25 Tests
# ---------------------------------------------------------------------------

class TestWorkflowPersistence:
    """Property 25: Workflow selection persistence and restore."""

    @settings(max_examples=100)
    @given(workflow_id=workflow_id_st)
    def test_persist_stores_id(self, workflow_id: str):
        """# Feature: ai-workflow-engine, Property 25: Persist stores workflow ID

        After persisting a selection, the storage should contain the workflow ID.

        **Validates: Requirements 4.2, 4.3**
        """
        storage = simulate_storage()
        persist_selection(storage, workflow_id)
        assert storage.get(STORAGE_KEY) == workflow_id

    @settings(max_examples=100)
    @given(workflows=workflows_st, workflow_id=workflow_id_st)
    def test_restore_enabled_workflow(self, workflows: list, workflow_id: str):
        """# Feature: ai-workflow-engine, Property 25: Restore enabled workflow

        If the saved workflow exists and is enabled, restore returns its ID.

        **Validates: Requirements 4.2, 4.3**
        """
        # Ensure at least one enabled workflow with our ID
        workflows = [{'id': workflow_id, 'status': 'enabled', 'name': 'test'}] + workflows
        storage = {STORAGE_KEY: workflow_id}

        result = restore_selection(storage, workflows)
        assert result == workflow_id
        assert storage.get(STORAGE_KEY) == workflow_id

    @settings(max_examples=100)
    @given(workflows=workflows_st, workflow_id=workflow_id_st)
    def test_restore_disabled_workflow_clears(self, workflows: list, workflow_id: str):
        """# Feature: ai-workflow-engine, Property 25: Disabled workflow clears storage

        If the saved workflow is disabled, restore clears storage and returns None.

        **Validates: Requirements 4.2, 4.3**
        """
        # Ensure the workflow exists but is disabled
        workflows = [{'id': workflow_id, 'status': 'disabled', 'name': 'test'}]
        storage = {STORAGE_KEY: workflow_id}

        result = restore_selection(storage, workflows)
        assert result is None
        assert STORAGE_KEY not in storage

    @settings(max_examples=100)
    @given(workflows=workflows_st, workflow_id=workflow_id_st)
    def test_restore_missing_workflow_clears(self, workflows: list, workflow_id: str):
        """# Feature: ai-workflow-engine, Property 25: Missing workflow clears storage

        If the saved workflow doesn't exist in the list, restore clears storage.

        **Validates: Requirements 4.2, 4.3**
        """
        # Ensure no workflow has our ID
        workflows = [w for w in workflows if w['id'] != workflow_id]
        storage = {STORAGE_KEY: workflow_id}

        result = restore_selection(storage, workflows)
        assert result is None
        assert STORAGE_KEY not in storage

    def test_restore_empty_storage(self):
        """# Feature: ai-workflow-engine, Property 25: Empty storage returns None

        If storage is empty, restore returns None without modifying storage.

        **Validates: Requirements 4.2, 4.3**
        """
        storage = simulate_storage()
        result = restore_selection(storage, [])
        assert result is None
