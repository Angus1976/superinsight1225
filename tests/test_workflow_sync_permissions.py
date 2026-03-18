"""
Unit tests for WorkflowService.sync_permissions().

Validates Requirements 3.6, 3.7, 11.7:
- Batch update data_source_auth for specified workflows
- Workflows not mentioned are left untouched
- Invalid workflow_ids are skipped with errors
"""

import pytest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

from src.models.ai_workflow import AIWorkflow
from src.ai.workflow_service import WorkflowService
from src.api.workflow_schemas import WorkflowCreateRequest

# ---------------------------------------------------------------------------
# SQLite JSONB shim + in-memory DB
# ---------------------------------------------------------------------------

if not getattr(SQLiteTypeCompiler, "_jsonb_patched", False):
    SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
    SQLiteTypeCompiler._jsonb_patched = True

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AIWorkflow.__table__.create(bind=_engine, checkfirst=True)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def _clean():
    session = _SessionLocal()
    try:
        session.query(AIWorkflow).delete()
        session.commit()
    finally:
        session.close()


def _create_workflow(session, name, data_source_auth=None, **kwargs):
    """Helper to create a workflow directly in DB."""
    wf = AIWorkflow(
        name=name,
        description="",
        skill_ids=[],
        data_source_auth=data_source_auth or [],
        output_modes=[],
        visible_roles=["admin"],
        **kwargs,
    )
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


class TestSyncPermissions:
    """Unit tests for sync_permissions() method."""

    def test_empty_list_returns_zero(self):
        """Empty permission_list returns updated_count=0, no errors."""
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            result = svc.sync_permissions([])
            assert result == {"updated_count": 0, "errors": []}
        finally:
            session.close()

    def test_updates_single_workflow(self):
        """Single valid entry updates the workflow's data_source_auth."""
        session = _SessionLocal()
        try:
            wf = _create_workflow(session, "wf-1", data_source_auth=[])
            svc = WorkflowService(db=session)

            new_auth = [{"source_id": "tasks", "tables": ["task_list"]}]
            result = svc.sync_permissions([
                {"workflow_id": wf.id, "data_source_auth": new_auth},
            ])

            assert result["updated_count"] == 1
            assert result["errors"] == []

            session.refresh(wf)
            assert wf.data_source_auth == new_auth
        finally:
            session.close()

    def test_updates_multiple_workflows(self):
        """Multiple valid entries update each workflow independently."""
        session = _SessionLocal()
        try:
            wf1 = _create_workflow(session, "wf-a")
            wf2 = _create_workflow(session, "wf-b")

            auth1 = [{"source_id": "tasks", "tables": ["*"]}]
            auth2 = [{"source_id": "quality", "tables": ["quality_scores"]}]

            svc = WorkflowService(db=session)
            result = svc.sync_permissions([
                {"workflow_id": wf1.id, "data_source_auth": auth1},
                {"workflow_id": wf2.id, "data_source_auth": auth2},
            ])

            assert result["updated_count"] == 2
            assert result["errors"] == []

            session.refresh(wf1)
            session.refresh(wf2)
            assert wf1.data_source_auth == auth1
            assert wf2.data_source_auth == auth2
        finally:
            session.close()

    def test_unmentioned_workflows_not_modified(self):
        """Workflows not in the permission_list keep their original auth."""
        session = _SessionLocal()
        try:
            original_auth = [{"source_id": "tasks", "tables": ["task_list"]}]
            wf_untouched = _create_workflow(
                session, "untouched", data_source_auth=original_auth
            )
            wf_updated = _create_workflow(session, "updated")

            svc = WorkflowService(db=session)
            new_auth = [{"source_id": "quality", "tables": ["*"]}]
            svc.sync_permissions([
                {"workflow_id": wf_updated.id, "data_source_auth": new_auth},
            ])

            session.refresh(wf_untouched)
            assert wf_untouched.data_source_auth == original_auth
        finally:
            session.close()

    def test_invalid_workflow_id_skipped_with_error(self):
        """Non-existent workflow_id is skipped and reported in errors."""
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            result = svc.sync_permissions([
                {
                    "workflow_id": "nonexistent-id",
                    "data_source_auth": [{"source_id": "x", "tables": []}],
                },
            ])

            assert result["updated_count"] == 0
            assert len(result["errors"]) == 1
            assert result["errors"][0]["workflow_id"] == "nonexistent-id"
            assert "not found" in result["errors"][0]["reason"]
        finally:
            session.close()

    def test_missing_workflow_id_field(self):
        """Entry without workflow_id is reported as error."""
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            result = svc.sync_permissions([
                {"data_source_auth": [{"source_id": "x", "tables": []}]},
            ])

            assert result["updated_count"] == 0
            assert len(result["errors"]) == 1
            assert "missing workflow_id" in result["errors"][0]["reason"]
        finally:
            session.close()

    def test_missing_data_source_auth_field(self):
        """Entry without data_source_auth is reported as error."""
        session = _SessionLocal()
        try:
            wf = _create_workflow(session, "wf-missing-auth")
            svc = WorkflowService(db=session)
            result = svc.sync_permissions([
                {"workflow_id": wf.id},
            ])

            assert result["updated_count"] == 0
            assert len(result["errors"]) == 1
            assert "missing data_source_auth" in result["errors"][0]["reason"]
        finally:
            session.close()

    def test_mixed_valid_and_invalid_entries(self):
        """Mix of valid and invalid entries: valid ones update, invalid ones error."""
        session = _SessionLocal()
        try:
            wf = _create_workflow(session, "wf-mix")
            svc = WorkflowService(db=session)

            new_auth = [{"source_id": "tasks", "tables": ["task_list"]}]
            result = svc.sync_permissions([
                {"workflow_id": wf.id, "data_source_auth": new_auth},
                {"workflow_id": "bad-id", "data_source_auth": []},
                {"data_source_auth": []},  # missing workflow_id
            ])

            assert result["updated_count"] == 1
            assert len(result["errors"]) == 2

            session.refresh(wf)
            assert wf.data_source_auth == new_auth
        finally:
            session.close()

    def test_overwrite_existing_auth(self):
        """Sync replaces existing data_source_auth entirely."""
        session = _SessionLocal()
        try:
            old_auth = [
                {"source_id": "tasks", "tables": ["task_list"]},
                {"source_id": "quality", "tables": ["*"]},
            ]
            wf = _create_workflow(session, "wf-overwrite", data_source_auth=old_auth)

            svc = WorkflowService(db=session)
            new_auth = [{"source_id": "user_activity", "tables": ["login_records"]}]
            svc.sync_permissions([
                {"workflow_id": wf.id, "data_source_auth": new_auth},
            ])

            session.refresh(wf)
            assert wf.data_source_auth == new_auth
        finally:
            session.close()
