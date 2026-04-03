"""
Property-based tests for test data factory relationship validity.

**Feature: comprehensive-testing-qa-system, Property 26: Test Data Relationship Validity**
**Validates: Requirements 11.5**

Verifies that all foreign key relationships created by factory functions
are valid and satisfy database constraints. Uses Hypothesis to generate
diverse entity combinations and checks that related records can be
persisted together without constraint violations.
"""

from uuid import uuid4

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET, ARRAY
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.database.models import (
    DocumentModel,
    TaskModel,
    TaskStatus,
    TaskPriority,
    AnnotationType,
    BillingRecordModel,
    QualityIssueModel,
    IssueSeverity,
    IssueStatus,
)
from src.security.models import (
    UserModel,
    UserRole,
    ProjectPermissionModel,
    PermissionType,
)


# =============================================================================
# SQLite Compatibility
# =============================================================================

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "JSON"


# =============================================================================
# Engine / Session Helpers
# =============================================================================

def _create_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    # Enable FK enforcement for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


_ENGINE = _create_engine()
_SessionFactory = sessionmaker(bind=_ENGINE, autoflush=False)


@pytest.fixture()
def session():
    """Provide a transactional session that rolls back after each test."""
    connection = _ENGINE.connect()
    transaction = connection.begin()
    sess = _SessionFactory(bind=connection)

    yield sess

    sess.close()
    transaction.rollback()
    connection.close()


# =============================================================================
# Factory Helpers
# =============================================================================

def create_user(session, **overrides):
    """Create a user record with sensible defaults."""
    defaults = {
        "id": uuid4(),
        "username": f"user_{uuid4().hex[:8]}",
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password_hash": "hashed_pw_placeholder",
        "full_name": "Test User",
        "role": UserRole.VIEWER.value,
        "tenant_id": "test_tenant",
        "is_active": True,
    }
    defaults.update(overrides)
    user = UserModel(**defaults)
    session.add(user)
    session.flush()
    return user


def create_document(session, **overrides):
    """Create a document record with sensible defaults."""
    defaults = {
        "id": uuid4(),
        "source_type": "test",
        "source_config": {"type": "test"},
        "content": "Test document content",
        "document_metadata": {},
    }
    defaults.update(overrides)
    doc = DocumentModel(**defaults)
    session.add(doc)
    session.flush()
    return doc


def create_task(session, *, created_by, document_id=None, assignee_id=None, **overrides):
    """Create a task record with explicit FK references."""
    defaults = {
        "id": uuid4(),
        "title": f"Task {uuid4().hex[:6]}",
        "name": f"Task {uuid4().hex[:6]}",
        "project_id": "test_project",
        "created_by": created_by,
        "document_id": document_id,
        "assignee_id": assignee_id,
        "status": TaskStatus.PENDING,
        "priority": TaskPriority.MEDIUM,
        "annotation_type": AnnotationType.CUSTOM,
        "tenant_id": "test_tenant",
    }
    defaults.update(overrides)
    task = TaskModel(**defaults)
    session.add(task)
    session.flush()
    return task


def create_billing_record(session, *, task_id, **overrides):
    """Create a billing record linked to a task."""
    defaults = {
        "id": uuid4(),
        "tenant_id": "test_tenant",
        "user_id": "test_user",
        "task_id": task_id,
        "annotation_count": 10,
        "time_spent": 3600,
        "cost": 25.0,
    }
    defaults.update(overrides)
    record = BillingRecordModel(**defaults)
    session.add(record)
    session.flush()
    return record


def create_quality_issue(session, *, task_id, **overrides):
    """Create a quality issue linked to a task."""
    defaults = {
        "id": uuid4(),
        "task_id": task_id,
        "tenant_id": "test_tenant",
        "issue_type": "accuracy",
        "description": "Test quality issue",
        "severity": IssueSeverity.MEDIUM,
        "status": IssueStatus.OPEN,
    }
    defaults.update(overrides)
    issue = QualityIssueModel(**defaults)
    session.add(issue)
    session.flush()
    return issue


def create_permission(session, *, user_id, granted_by=None, **overrides):
    """Create a project permission linked to users."""
    defaults = {
        "id": uuid4(),
        "user_id": user_id,
        "project_id": "test_project",
        "permission_type": PermissionType.READ,
        "granted_by": granted_by,
    }
    defaults.update(overrides)
    perm = ProjectPermissionModel(**defaults)
    session.add(perm)
    session.flush()
    return perm


# =============================================================================
# Hypothesis Strategies
# =============================================================================

task_statuses = st.sampled_from(list(TaskStatus))
task_priorities = st.sampled_from(list(TaskPriority))
annotation_types = st.sampled_from(list(AnnotationType))
issue_severities = st.sampled_from(list(IssueSeverity))
issue_statuses = st.sampled_from(list(IssueStatus))
permission_types = st.sampled_from(list(PermissionType))
user_roles = st.sampled_from([r.value for r in UserRole])

optional_fk_flags = st.fixed_dictionaries({
    "with_document": st.booleans(),
    "with_assignee": st.booleans(),
    "with_billing": st.booleans(),
    "with_quality_issue": st.booleans(),
    "with_granted_by": st.booleans(),
})


# =============================================================================
# Property Tests
# =============================================================================

class TestFactoryRelationshipValidity:
    """
    Property 26: Test Data Relationship Validity

    For any test data created with relationships using factory functions,
    all foreign key relationships and associations SHALL be valid and
    satisfy database constraints.
    """

    @given(
        status=task_statuses,
        priority=task_priorities,
        ann_type=annotation_types,
        flags=optional_fk_flags,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_task_fk_relationships_are_valid(
        self, session, status, priority, ann_type, flags
    ):
        """
        Factory-generated tasks with any combination of optional FKs
        produce valid, queryable records in the database.

        **Validates: Requirements 11.5**
        """
        owner = create_user(session)
        doc = create_document(session) if flags["with_document"] else None
        assignee = create_user(session) if flags["with_assignee"] else None

        task = create_task(
            session,
            created_by=owner.id,
            document_id=doc.id if doc else None,
            assignee_id=assignee.id if assignee else None,
            status=status,
            priority=priority,
            annotation_type=ann_type,
        )

        fetched = session.get(TaskModel, task.id)
        assert fetched is not None
        assert fetched.created_by == owner.id

        if doc:
            assert fetched.document_id == doc.id
            assert fetched.document is not None
        else:
            assert fetched.document_id is None

        if assignee:
            assert fetched.assignee_id == assignee.id
            assert fetched.assignee is not None
        else:
            assert fetched.assignee_id is None

    @given(
        severity=issue_severities,
        issue_status=issue_statuses,
        flags=optional_fk_flags,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_child_records_reference_valid_parent_task(
        self, session, severity, issue_status, flags
    ):
        """
        BillingRecord and QualityIssue always reference an existing task.

        **Validates: Requirements 11.5**
        """
        owner = create_user(session)
        task = create_task(session, created_by=owner.id)

        if flags["with_billing"]:
            billing = create_billing_record(session, task_id=task.id)
            fetched = session.get(BillingRecordModel, billing.id)
            assert fetched is not None
            assert fetched.task_id == task.id
            assert fetched.task is not None

        if flags["with_quality_issue"]:
            issue = create_quality_issue(
                session, task_id=task.id,
                severity=severity, status=issue_status,
            )
            fetched = session.get(QualityIssueModel, issue.id)
            assert fetched is not None
            assert fetched.task_id == task.id
            assert fetched.task is not None

    @given(perm_type=permission_types, flags=optional_fk_flags)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_permission_references_valid_users(
        self, session, perm_type, flags
    ):
        """
        ProjectPermission always references existing users for both
        user_id and optional granted_by.

        **Validates: Requirements 11.5**
        """
        user = create_user(session)
        granter = create_user(session) if flags["with_granted_by"] else None

        perm = create_permission(
            session,
            user_id=user.id,
            granted_by=granter.id if granter else None,
            permission_type=perm_type,
        )

        fetched = session.get(ProjectPermissionModel, perm.id)
        assert fetched is not None
        assert fetched.user_id == user.id
        assert fetched.user is not None

        if granter:
            assert fetched.granted_by == granter.id

    @given(data=st.data())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_full_entity_graph_satisfies_all_constraints(
        self, session, data
    ):
        """
        A complete entity graph (user → document → task → billing + issue + permission)
        can be persisted and all relationships resolve correctly.

        **Validates: Requirements 11.5**
        """
        admin = create_user(session, role=UserRole.ADMIN.value)
        annotator = create_user(session, role=UserRole.CONTRACTOR.value)
        doc = create_document(session)

        task = create_task(
            session,
            created_by=admin.id,
            document_id=doc.id,
            assignee_id=annotator.id,
            status=data.draw(task_statuses),
            priority=data.draw(task_priorities),
        )

        create_billing_record(session, task_id=task.id)
        create_quality_issue(session, task_id=task.id)
        create_permission(
            session, user_id=annotator.id, granted_by=admin.id,
        )

        # Verify the entire graph is consistent
        fetched_task = session.get(TaskModel, task.id)
        assert fetched_task.document.id == doc.id
        assert fetched_task.assignee.id == annotator.id
        assert len(fetched_task.billing_records) >= 1
        assert len(fetched_task.quality_issues) >= 1
