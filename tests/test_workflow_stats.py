"""
Unit tests for WorkflowService.get_workflow_stats() and get_today_stats().

Validates Requirements 8.1, 8.3, 8.4:
- Aggregate stats: chat_count, workflow_count, data_source_count
- Support filtering by role and date range
- Non-admin sees only own data, admin sees aggregated
"""

import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from fastapi import HTTPException

from src.models.ai_workflow import AIWorkflow
from src.models.ai_access_log import AIAccessLog
from src.ai.workflow_service import WorkflowService


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
AIAccessLog.__table__.create(bind=_engine, checkfirst=True)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def _clean():
    session = _SessionLocal()
    try:
        session.query(AIAccessLog).delete()
        session.query(AIWorkflow).delete()
        session.commit()
    finally:
        session.close()


def _create_workflow(session, name="test-wf", **kwargs):
    """Helper to create a workflow directly in DB."""
    wf = AIWorkflow(
        name=name,
        description="",
        skill_ids=[],
        data_source_auth=[],
        output_modes=[],
        visible_roles=["admin"],
        **kwargs,
    )
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


def _create_log(session, **kwargs):
    """Helper to create an AIAccessLog entry."""
    defaults = {
        "tenant_id": "t1",
        "user_id": "u1",
        "user_role": "admin",
        "event_type": "workflow_execute",
        "success": True,
        "details": {},
    }
    defaults.update(kwargs)
    log = AIAccessLog(**defaults)
    session.add(log)
    session.commit()
    return log


# ---------------------------------------------------------------------------
# get_workflow_stats tests
# ---------------------------------------------------------------------------


class TestGetWorkflowStats:
    """Tests for get_workflow_stats()."""

    def test_returns_zero_counts_for_no_logs(self):
        session = _SessionLocal()
        try:
            wf = _create_workflow(session)
            svc = WorkflowService(db=session)
            stats = svc.get_workflow_stats(wf.id)
            assert stats == {
                "chat_count": 0,
                "workflow_count": 0,
                "data_source_count": 0,
            }
        finally:
            session.close()

    def test_counts_workflow_execute_events(self):
        session = _SessionLocal()
        try:
            wf = _create_workflow(session)
            svc = WorkflowService(db=session)

            # Create 3 workflow_execute logs for this workflow
            for _ in range(3):
                _create_log(
                    session,
                    resource_id=wf.id,
                    event_type="workflow_execute",
                    details={"data_sources": ["tasks"]},
                )

            stats = svc.get_workflow_stats(wf.id)
            assert stats["workflow_count"] == 3
            assert stats["data_source_count"] == 1  # "tasks" deduplicated
        finally:
            session.close()

    def test_counts_unique_data_sources(self):
        session = _SessionLocal()
        try:
            wf = _create_workflow(session)
            svc = WorkflowService(db=session)

            _create_log(
                session,
                resource_id=wf.id,
                event_type="workflow_execute",
                details={"data_sources": ["tasks", "quality"]},
            )
            _create_log(
                session,
                resource_id=wf.id,
                event_type="workflow_execute",
                details={"data_sources": ["tasks", "user_activity"]},
            )

            stats = svc.get_workflow_stats(wf.id)
            assert stats["workflow_count"] == 2
            assert stats["data_source_count"] == 3  # tasks, quality, user_activity
        finally:
            session.close()

    def test_filters_by_date_range(self):
        session = _SessionLocal()
        try:
            wf = _create_workflow(session)
            svc = WorkflowService(db=session)

            now = datetime.now(timezone.utc)
            old_time = now - timedelta(days=10)

            # Old log
            _create_log(
                session,
                resource_id=wf.id,
                event_type="workflow_execute",
                created_at=old_time,
                details={"data_sources": ["tasks"]},
            )
            # Recent log
            _create_log(
                session,
                resource_id=wf.id,
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["quality"]},
            )

            # Query only recent (last 2 days)
            start = now - timedelta(days=2)
            stats = svc.get_workflow_stats(wf.id, start_date=start)
            assert stats["workflow_count"] == 1
            assert stats["data_source_count"] == 1
        finally:
            session.close()

    def test_raises_404_for_nonexistent_workflow(self):
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            with pytest.raises(HTTPException) as exc_info:
                svc.get_workflow_stats("nonexistent-id")
            assert exc_info.value.status_code == 404
        finally:
            session.close()

    def test_ignores_logs_for_other_workflows(self):
        session = _SessionLocal()
        try:
            wf1 = _create_workflow(session, name="wf-1")
            wf2 = _create_workflow(session, name="wf-2")
            svc = WorkflowService(db=session)

            _create_log(
                session,
                resource_id=wf1.id,
                event_type="workflow_execute",
                details={"data_sources": ["tasks"]},
            )
            _create_log(
                session,
                resource_id=wf2.id,
                event_type="workflow_execute",
                details={"data_sources": ["quality"]},
            )

            stats = svc.get_workflow_stats(wf1.id)
            assert stats["workflow_count"] == 1
            assert stats["data_source_count"] == 1
        finally:
            session.close()


# ---------------------------------------------------------------------------
# get_today_stats tests
# ---------------------------------------------------------------------------


class TestGetTodayStats:
    """Tests for get_today_stats()."""

    def test_returns_zero_counts_when_no_logs(self):
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            stats = svc.get_today_stats(
                user_id="u1", user_role="admin", tenant_id="t1"
            )
            assert stats == {
                "chat_count": 0,
                "workflow_count": 0,
                "data_source_count": 0,
            }
        finally:
            session.close()

    def test_counts_today_events(self):
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            now = datetime.now(timezone.utc)

            # workflow_execute logs
            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["tasks"]},
            )
            # skill_invoke log (counts as chat)
            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="skill_invoke",
                created_at=now,
                details={},
            )
            # data_access log (counts as chat)
            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="data_access",
                created_at=now,
                details={"data_sources": ["quality"]},
            )

            stats = svc.get_today_stats(
                user_id="u1", user_role="admin", tenant_id="t1"
            )
            assert stats["chat_count"] == 2  # skill_invoke + data_access
            assert stats["workflow_count"] == 1
            assert stats["data_source_count"] == 2  # tasks + quality
        finally:
            session.close()

    def test_non_admin_sees_only_own_data(self):
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            now = datetime.now(timezone.utc)

            # User u1 logs
            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["tasks"]},
            )
            # User u2 logs
            _create_log(
                session,
                tenant_id="t1", user_id="u2",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["quality"]},
            )

            # Non-admin u1 should only see own data
            stats = svc.get_today_stats(
                user_id="u1", user_role="annotator", tenant_id="t1"
            )
            assert stats["workflow_count"] == 1
            assert stats["data_source_count"] == 1
        finally:
            session.close()

    def test_admin_sees_all_users_data(self):
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            now = datetime.now(timezone.utc)

            # User u1 logs
            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["tasks"]},
            )
            # User u2 logs
            _create_log(
                session,
                tenant_id="t1", user_id="u2",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["quality"]},
            )

            # Admin sees all
            stats = svc.get_today_stats(
                user_id="u1", user_role="admin", tenant_id="t1"
            )
            assert stats["workflow_count"] == 2
            assert stats["data_source_count"] == 2
        finally:
            session.close()

    def test_excludes_yesterday_logs(self):
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(days=1)

            # Yesterday's log
            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="workflow_execute",
                created_at=yesterday,
                details={"data_sources": ["tasks"]},
            )
            # Today's log
            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["quality"]},
            )

            stats = svc.get_today_stats(
                user_id="u1", user_role="admin", tenant_id="t1"
            )
            assert stats["workflow_count"] == 1
            assert stats["data_source_count"] == 1
        finally:
            session.close()

    def test_filters_by_tenant(self):
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)
            now = datetime.now(timezone.utc)

            _create_log(
                session,
                tenant_id="t1", user_id="u1",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["tasks"]},
            )
            _create_log(
                session,
                tenant_id="t2", user_id="u1",
                event_type="workflow_execute",
                created_at=now,
                details={"data_sources": ["quality"]},
            )

            stats = svc.get_today_stats(
                user_id="u1", user_role="admin", tenant_id="t1"
            )
            assert stats["workflow_count"] == 1
        finally:
            session.close()
