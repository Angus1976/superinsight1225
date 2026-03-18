"""
Property-based tests for workflow migration logic.

Verifies that generate_default_workflows() and _generate_default_for_role()
preserve each role's access capabilities during migration.

# Feature: ai-workflow-engine
"""

import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, settings
from hypothesis import strategies as st
from typing import List

from src.ai.workflow_service import WorkflowService
from src.models.ai_workflow import AIWorkflow


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

role_st = st.sampled_from(["admin", "business_expert", "annotator", "viewer"])

skill_ids_st = st.lists(
    st.text(alphabet="abcdef0123456789-", min_size=8, max_size=36),
    min_size=0,
    max_size=5,
    unique=True,
)

source_ids_st = st.lists(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=3, max_size=20),
    min_size=0,
    max_size=5,
    unique=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service() -> WorkflowService:
    """Create a WorkflowService with a mocked DB session."""
    svc = WorkflowService.__new__(WorkflowService)
    svc.db = MagicMock()
    return svc


def _mock_no_existing_workflow(mock_db: MagicMock) -> None:
    """Configure mock DB to return no existing workflow."""
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query


def _mock_existing_workflow(mock_db: MagicMock, role: str) -> None:
    """Configure mock DB to return an existing workflow for the role."""
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_existing = MagicMock()
    mock_existing.name = f"默认工作流-{role}"
    mock_filter.first.return_value = mock_existing
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query


# ---------------------------------------------------------------------------
# Property 17 tests
# ---------------------------------------------------------------------------


class TestMigrationPreservesAccess:
    """Property 17: Default workflow migration preserves access capabilities."""

    @settings(max_examples=100)
    @given(
        role=role_st,
        skill_ids=skill_ids_st,
        source_ids=source_ids_st,
    )
    def test_migration_preserves_permissions(self, role, skill_ids, source_ids):
        """# Feature: ai-workflow-engine, Property 17: Migration preserves access

        For any role with permissions, the generated default workflow should
        contain exactly the same skill_ids and data_source_auth as the role's
        original permissions.

        **Validates: Requirements 6.3**
        """
        # No permissions → no workflow expected
        if not skill_ids and not source_ids:
            return

        service = _make_service()
        _mock_no_existing_workflow(service.db)

        ds_auth = [{"source_id": sid, "tables": ["*"]} for sid in source_ids]

        with patch.object(service, "_get_role_skill_ids", return_value=skill_ids), \
             patch.object(service, "_get_role_data_source_auth", return_value=ds_auth):
            workflow = service._generate_default_for_role(role)

        assert workflow is not None

        # Skills preserved
        assert set(workflow.skill_ids) == set(skill_ids)

        # Data sources preserved
        generated_source_ids = {d["source_id"] for d in workflow.data_source_auth}
        assert generated_source_ids == set(source_ids)

        # All data sources have wildcard access
        for auth in workflow.data_source_auth:
            assert auth["tables"] == ["*"]

        # Workflow is visible to the role
        assert role in workflow.visible_roles

    @settings(max_examples=50)
    @given(role=role_st)
    def test_migration_idempotent(self, role):
        """# Feature: ai-workflow-engine, Property 17: Migration is idempotent

        Running migration twice should not create duplicate workflows.

        **Validates: Requirements 6.3**
        """
        service = _make_service()
        _mock_existing_workflow(service.db, role)

        result = service._generate_default_for_role(role)

        # Should return None (skipped)
        assert result is None
        # Should NOT call db.add
        service.db.add.assert_not_called()

    def test_no_permissions_skips_workflow(self):
        """# Feature: ai-workflow-engine, Property 17: No permissions = no workflow

        Roles with no permissions should not get a default workflow.

        **Validates: Requirements 6.3**
        """
        service = _make_service()
        _mock_no_existing_workflow(service.db)

        with patch.object(service, "_get_role_skill_ids", return_value=[]), \
             patch.object(service, "_get_role_data_source_auth", return_value=[]):
            result = service._generate_default_for_role("viewer")

        assert result is None
        service.db.add.assert_not_called()
