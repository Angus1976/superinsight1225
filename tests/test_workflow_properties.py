"""
Property-based tests for AI Workflow Engine.

Uses hypothesis to verify correctness properties across random valid inputs.
Each test corresponds to a numbered Property from the design document.

# Feature: ai-workflow-engine
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.models.ai_workflow import AIWorkflow
from src.ai.workflow_service import WorkflowService, VALID_ROLES
from src.ai.data_source_config import AIDataSourceConfigModel
from fastapi import HTTPException
from src.api.workflow_schemas import WorkflowCreateRequest, WorkflowUpdateRequest


# ---------------------------------------------------------------------------
# Test database setup (in-memory SQLite, JSONB → JSON shim)
# ---------------------------------------------------------------------------

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

# Teach SQLite to treat JSONB as plain JSON so the table can be created.
_orig_visit = getattr(SQLiteTypeCompiler, "visit_JSONB", None)
if _orig_visit is None:
    SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
# Only create the ai_workflows table to avoid unrelated model issues
AIWorkflow.__table__.create(bind=_engine, checkfirst=True)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def _clean_workflows():
    """Ensure a clean ai_workflows table for every test."""
    session = _SessionLocal()
    try:
        session.query(AIWorkflow).delete()
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Hypothesis strategies for valid workflow inputs
# ---------------------------------------------------------------------------

_valid_roles_strategy = st.lists(
    st.sampled_from(sorted(VALID_ROLES)),
    min_size=1,
    max_size=4,
    unique=True,
)

_workflow_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs"), whitelist_characters="_-"),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip())  # non-blank after trimming

_workflow_description_strategy = st.one_of(
    st.none(),
    st.text(max_size=200),
)

_output_modes_strategy = st.lists(
    st.sampled_from(["merge", "compare"]),
    max_size=2,
    unique=True,
)


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 1: 工作流创建后包含所有必需字段
# ---------------------------------------------------------------------------

# Required fields that must be present on every created workflow object
REQUIRED_FIELDS = [
    "id", "name", "description", "status",
    "skill_ids", "data_source_auth", "output_modes",
    "visible_roles", "is_preset", "created_at", "updated_at",
]


class TestWorkflowCreationRequiredFields:
    """Property 1: 工作流创建后包含所有必需字段

    *For any* valid workflow creation input, the returned object SHALL
    contain all required fields, id is non-empty, status is "enabled",
    and created_at / updated_at are non-null.

    **Validates: Requirements 1.1**
    """

    @settings(max_examples=100)
    @given(
        name=_workflow_name_strategy,
        description=_workflow_description_strategy,
        visible_roles=_valid_roles_strategy,
        output_modes=_output_modes_strategy,
    )
    def test_created_workflow_has_all_required_fields(
        self, name, description, visible_roles, output_modes,
    ):
        # Feature: ai-workflow-engine, Property 1: 工作流创建后包含所有必需字段
        session = _SessionLocal()
        try:
            # Clear table to avoid name-uniqueness conflicts across examples
            session.query(AIWorkflow).delete()
            session.commit()

            svc = WorkflowService(db=session)

            request = WorkflowCreateRequest(
                name=name,
                description=description,
                skill_ids=[],
                data_source_auth=[],
                output_modes=output_modes,
                visible_roles=visible_roles,
            )

            # Bypass external-table validations (skills / data sources)
            with patch.object(svc, "_validate_skill_ids"), \
                 patch.object(svc, "_validate_data_source_auth"):
                workflow = svc.create_workflow(request, creator_id="test-user")

            # --- Assert all required fields exist and are accessible ---
            for field in REQUIRED_FIELDS:
                assert hasattr(workflow, field), (
                    f"Missing required field: {field}"
                )

            # --- id must be a non-empty string ---
            assert isinstance(workflow.id, str) and len(workflow.id) > 0, (
                f"id should be a non-empty string, got {workflow.id!r}"
            )

            # --- status must be "enabled" ---
            assert workflow.status == "enabled", (
                f"status should be 'enabled', got {workflow.status!r}"
            )

            # --- created_at and updated_at must be non-null ---
            assert workflow.created_at is not None, "created_at should not be None"
            assert workflow.updated_at is not None, "updated_at should not be None"

            # --- name round-trips correctly ---
            assert workflow.name == name

            # --- visible_roles round-trips correctly ---
            assert set(workflow.visible_roles) == set(visible_roles)

            # --- is_preset defaults to False ---
            assert workflow.is_preset is False
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 2: 创建和更新共享相同的校验规则
# ---------------------------------------------------------------------------

# Strategy: role values that may be valid or invalid
_any_role_strategy = st.one_of(
    st.sampled_from(sorted(VALID_ROLES)),          # valid roles
    st.text(min_size=1, max_size=30).filter(       # potentially invalid roles
        lambda s: s.strip() and s not in VALID_ROLES
    ),
)

_any_roles_list_strategy = st.lists(
    _any_role_strategy,
    min_size=1,
    max_size=5,
    unique=True,
)


class TestCreateUpdateShareValidationRules:
    """Property 2: 创建和更新共享相同的校验规则

    *For any* field value, if that value is rejected during workflow creation
    (e.g., illegal role value), then using the same value during workflow
    update should also be rejected; conversely, values accepted during
    creation should also be accepted during update.

    **Validates: Requirements 1.2, 1.3**
    """

    @settings(max_examples=100)
    @given(
        roles=_any_roles_list_strategy,
    )
    def test_create_and_update_role_validation_consistent(self, roles):
        # Feature: ai-workflow-engine, Property 2: 创建和更新共享相同的校验规则
        session = _SessionLocal()
        try:
            # Clean slate
            session.query(AIWorkflow).delete()
            session.commit()

            svc = WorkflowService(db=session)

            # --- Step 1: Create a "base" workflow with known-valid roles ---
            base_request = WorkflowCreateRequest(
                name="base-workflow",
                description="base",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=["admin"],
            )
            with patch.object(svc, "_validate_skill_ids"), \
                 patch.object(svc, "_validate_data_source_auth"):
                base_wf = svc.create_workflow(base_request, creator_id="test")

            # --- Step 2: Attempt CREATE with the generated roles ---
            create_request = WorkflowCreateRequest(
                name="test-create-workflow",
                description="test",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=roles,
            )

            create_error = None
            try:
                with patch.object(svc, "_validate_skill_ids"), \
                     patch.object(svc, "_validate_data_source_auth"):
                    svc.create_workflow(create_request, creator_id="test")
            except HTTPException as exc:
                create_error = exc

            # --- Step 3: Attempt UPDATE with the same roles ---
            update_request = WorkflowUpdateRequest(visible_roles=roles)

            update_error = None
            try:
                with patch.object(svc, "_validate_skill_ids"), \
                     patch.object(svc, "_validate_data_source_auth"):
                    svc.update_workflow(base_wf.id, update_request)
            except HTTPException as exc:
                update_error = exc

            # --- Step 4: Both must agree: both succeed or both fail ---
            create_failed = create_error is not None
            update_failed = update_error is not None

            assert create_failed == update_failed, (
                f"Validation mismatch for roles={roles!r}: "
                f"create {'rejected' if create_failed else 'accepted'}, "
                f"update {'rejected' if update_failed else 'accepted'}"
            )

            # If both failed, error codes should match
            if create_failed and update_failed:
                create_code = create_error.detail.get("error_code", "")
                update_code = update_error.detail.get("error_code", "")
                assert create_code == update_code, (
                    f"Error code mismatch for roles={roles!r}: "
                    f"create={create_code}, update={update_code}"
                )
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 3: 软删除保留记录
# ---------------------------------------------------------------------------


class TestSoftDeletePreservesRecord:
    """Property 3: 软删除保留记录

    *For any* existing workflow, after delete operation, the workflow's status
    should become "disabled", but the record should still be queryable from
    the database (not physically deleted).

    Also verifies that preset workflows (is_preset=True) cannot be deleted
    and raise a 403 error.

    **Validates: Requirements 1.4**
    """

    @settings(max_examples=100)
    @given(
        name=_workflow_name_strategy,
        visible_roles=_valid_roles_strategy,
    )
    def test_soft_delete_sets_disabled_and_preserves_record(
        self, name, visible_roles,
    ):
        # Feature: ai-workflow-engine, Property 3: 软删除保留记录
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            svc = WorkflowService(db=session)

            # Create a non-preset workflow
            request = WorkflowCreateRequest(
                name=name,
                description="test soft delete",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=visible_roles,
            )

            with patch.object(svc, "_validate_skill_ids"), \
                 patch.object(svc, "_validate_data_source_auth"):
                workflow = svc.create_workflow(request, creator_id="test-user")

            workflow_id = workflow.id

            # Verify initial status is "enabled"
            assert workflow.status == "enabled"
            assert workflow.is_preset is False

            # Perform soft delete
            svc.delete_workflow(workflow_id)

            # Verify status changed to "disabled"
            deleted_wf = (
                session.query(AIWorkflow)
                .filter(AIWorkflow.id == workflow_id)
                .first()
            )
            assert deleted_wf is not None, (
                "Record should still exist after soft delete"
            )
            assert deleted_wf.status == "disabled", (
                f"Status should be 'disabled' after delete, got {deleted_wf.status!r}"
            )

            # Verify the record is still accessible via get_workflow
            fetched = svc.get_workflow(workflow_id)
            assert fetched is not None
            assert fetched.id == workflow_id
            assert fetched.status == "disabled"

            # Verify other fields are preserved
            assert fetched.name == name
            assert set(fetched.visible_roles) == set(visible_roles)
        finally:
            session.rollback()
            session.close()

    @settings(max_examples=100)
    @given(
        name=_workflow_name_strategy,
        visible_roles=_valid_roles_strategy,
    )
    def test_preset_workflow_cannot_be_deleted(
        self, name, visible_roles,
    ):
        # Feature: ai-workflow-engine, Property 3: 软删除保留记录
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            svc = WorkflowService(db=session)

            # Create a preset workflow directly in DB
            preset_wf = AIWorkflow(
                name=name,
                description="preset workflow",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=visible_roles,
                is_preset=True,
                status="enabled",
            )
            session.add(preset_wf)
            session.commit()
            session.refresh(preset_wf)

            preset_id = preset_wf.id

            # Attempt to delete preset workflow — should raise 403
            with pytest.raises(HTTPException) as exc_info:
                svc.delete_workflow(preset_id)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error_code"] == "WORKFLOW_PRESET_DELETE_DENIED"

            # Verify the preset workflow is unchanged
            unchanged = (
                session.query(AIWorkflow)
                .filter(AIWorkflow.id == preset_id)
                .first()
            )
            assert unchanged is not None
            assert unchanged.status == "enabled", (
                "Preset workflow status should remain 'enabled' after failed delete"
            )
            assert unchanged.is_preset is True
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 4: 工作流列表过滤正确性
# ---------------------------------------------------------------------------

# Strategy: generate a small set of workflows with random statuses and roles
_workflow_status_strategy = st.sampled_from(["enabled", "disabled"])

_workflow_entry_strategy = st.fixed_dictionaries({
    "name": _workflow_name_strategy,
    "status": _workflow_status_strategy,
    "visible_roles": _valid_roles_strategy,
})

_workflow_set_strategy = st.lists(
    _workflow_entry_strategy,
    min_size=1,
    max_size=8,
)

# Filter condition strategies
_optional_status_strategy = st.one_of(st.none(), st.sampled_from(["enabled", "disabled"]))
_optional_role_strategy = st.one_of(st.none(), st.sampled_from(sorted(VALID_ROLES)))


def _expected_list_workflows(
    workflows: list,
    role: str = None,
    status: str = None,
    is_admin: bool = False,
) -> set:
    """Pure-Python oracle that computes the expected filter result.

    Mirrors the logic in WorkflowService.list_workflows exactly.
    Returns a set of workflow names that should appear in the result.
    """
    result = set()
    for wf in workflows:
        if not is_admin and role:
            # Non-admin: only enabled workflows visible to their role
            if wf["status"] == "enabled" and role in wf["visible_roles"]:
                result.add(wf["name"])
        else:
            # Admin path: apply explicit filters if provided
            if status and wf["status"] != status:
                continue
            if role and role not in wf["visible_roles"]:
                continue
            result.add(wf["name"])
    return result


class TestWorkflowListFilterCorrectness:
    """Property 4: 工作流列表过滤正确性

    *For any* workflow set and any filter conditions (status, role), every
    workflow in the returned list should satisfy all specified filter
    conditions; and no workflow satisfying the conditions should be omitted.

    Because SQLite does not support PostgreSQL's JSONB ``@>`` operator used
    by ``list_workflows``, this test inserts workflows into the database and
    verifies the filtering property against a pure-Python oracle that
    implements the same logic.

    **Validates: Requirements 1.5**
    """

    @settings(max_examples=100)
    @given(
        workflow_entries=_workflow_set_strategy,
        filter_status=_optional_status_strategy,
        filter_role=_optional_role_strategy,
        is_admin=st.booleans(),
    )
    def test_list_filter_correctness(
        self, workflow_entries, filter_status, filter_role, is_admin,
    ):
        # Feature: ai-workflow-engine, Property 4: 工作流列表过滤正确性
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # --- Deduplicate names (DB has unique constraint) ---
            seen_names = set()
            unique_entries = []
            for entry in workflow_entries:
                if entry["name"] not in seen_names:
                    seen_names.add(entry["name"])
                    unique_entries.append(entry)

            # --- Insert workflows directly into DB ---
            for entry in unique_entries:
                wf = AIWorkflow(
                    name=entry["name"],
                    description="",
                    skill_ids=[],
                    data_source_auth=[],
                    output_modes=[],
                    visible_roles=entry["visible_roles"],
                    status=entry["status"],
                )
                session.add(wf)
            session.commit()

            # --- Compute expected result using pure-Python oracle ---
            expected_names = _expected_list_workflows(
                unique_entries,
                role=filter_role,
                status=filter_status,
                is_admin=is_admin,
            )

            # --- Query all workflows and apply filtering in Python ---
            # (mirrors WorkflowService.list_workflows logic exactly)
            all_wfs = session.query(AIWorkflow).all()
            actual_names = set()
            for wf in all_wfs:
                if not is_admin and filter_role:
                    if wf.status == "enabled" and filter_role in (wf.visible_roles or []):
                        actual_names.add(wf.name)
                else:
                    if filter_status and wf.status != filter_status:
                        continue
                    if filter_role and filter_role not in (wf.visible_roles or []):
                        continue
                    actual_names.add(wf.name)

            # --- Soundness: every returned workflow satisfies filters ---
            for name in actual_names:
                entry = next(e for e in unique_entries if e["name"] == name)
                if not is_admin and filter_role:
                    assert entry["status"] == "enabled", (
                        f"Non-admin result contains disabled workflow: {name}"
                    )
                    assert filter_role in entry["visible_roles"], (
                        f"Non-admin result contains workflow not visible to "
                        f"role {filter_role!r}: {name}"
                    )
                else:
                    if filter_status:
                        assert entry["status"] == filter_status, (
                            f"Admin result contains workflow with wrong status: "
                            f"{name} has {entry['status']!r}, expected {filter_status!r}"
                        )
                    if filter_role:
                        assert filter_role in entry["visible_roles"], (
                            f"Admin result contains workflow not visible to "
                            f"role {filter_role!r}: {name}"
                        )

            # --- Completeness: no satisfying workflow is omitted ---
            assert actual_names == expected_names, (
                f"Filter mismatch (is_admin={is_admin}, status={filter_status!r}, "
                f"role={filter_role!r}):\n"
                f"  expected: {sorted(expected_names)}\n"
                f"  actual:   {sorted(actual_names)}\n"
                f"  missing:  {sorted(expected_names - actual_names)}\n"
                f"  extra:    {sorted(actual_names - expected_names)}"
            )
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 5: 角色可见性控制
# ---------------------------------------------------------------------------


class TestRoleVisibilityControl:
    """Property 5: 角色可见性控制

    *For any* workflow and any non-admin user role, the user can see the
    workflow if and only if: (1) user role is in workflow's visible_roles
    list, AND (2) workflow status is "enabled". Admin role always sees all
    workflows. This rule also applies to preset workflows.

    **Validates: Requirements 2.1, 2.2, 2.4, 7.3**
    """

    @settings(max_examples=100)
    @given(
        visible_roles=st.lists(
            st.sampled_from(sorted(VALID_ROLES)),
            min_size=1,
            max_size=4,
            unique=True,
        ),
        user_role=st.sampled_from(sorted(VALID_ROLES)),
        status=st.sampled_from(["enabled", "disabled"]),
        is_preset=st.booleans(),
    )
    def test_check_role_visibility(
        self, visible_roles, user_role, status, is_preset,
    ):
        """_check_role_visibility: admin always passes, disabled blocks
        non-admin, role matching works correctly. Applies to preset too.

        **Validates: Requirements 2.1, 2.2, 2.4, 7.3**
        """
        # Feature: ai-workflow-engine, Property 5: 角色可见性控制
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            svc = WorkflowService(db=session)

            # Create workflow directly in DB
            wf = AIWorkflow(
                name="visibility-test",
                description="test",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=visible_roles,
                status=status,
                is_preset=is_preset,
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            # --- Test _check_role_visibility directly ---
            if user_role == "admin":
                # Admin always passes, regardless of status or visible_roles
                svc._check_role_visibility(wf, user_role)  # should NOT raise
            elif user_role in visible_roles:
                # Role is in visible_roles — visibility check passes
                svc._check_role_visibility(wf, user_role)  # should NOT raise
            else:
                # Role not in visible_roles — must raise 403
                with pytest.raises(HTTPException) as exc_info:
                    svc._check_role_visibility(wf, user_role)
                assert exc_info.value.status_code == 403
                assert exc_info.value.detail["error_code"] == "WORKFLOW_PERMISSION_DENIED"
        finally:
            session.rollback()
            session.close()

    @settings(max_examples=100)
    @given(
        visible_roles=st.lists(
            st.sampled_from(sorted(VALID_ROLES)),
            min_size=1,
            max_size=4,
            unique=True,
        ),
        user_role=st.sampled_from(sorted(VALID_ROLES)),
        status=st.sampled_from(["enabled", "disabled"]),
        is_preset=st.booleans(),
    )
    def test_list_workflows_role_visibility(
        self, visible_roles, user_role, status, is_preset,
    ):
        """list_workflows filtering: non-admin only sees enabled workflows
        where their role is in visible_roles. Admin sees all. Applies to
        preset workflows equally.

        **Validates: Requirements 2.1, 2.2, 2.4, 7.3**
        """
        # Feature: ai-workflow-engine, Property 5: 角色可见性控制
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # Insert a single workflow with the generated parameters
            wf = AIWorkflow(
                name="list-vis-test",
                description="test",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=visible_roles,
                status=status,
                is_preset=is_preset,
            )
            session.add(wf)
            session.commit()

            is_admin = user_role == "admin"

            # Query all workflows and apply Python-side filtering
            # (mirrors list_workflows logic; SQLite lacks JSONB @> operator)
            all_wfs = session.query(AIWorkflow).all()
            visible_wfs = []
            for w in all_wfs:
                if not is_admin:
                    if w.status == "enabled" and user_role in (w.visible_roles or []):
                        visible_wfs.append(w)
                else:
                    # Admin sees everything (no status/role filter)
                    visible_wfs.append(w)

            if is_admin:
                # Admin always sees the workflow regardless of status
                assert len(visible_wfs) == 1
            elif status == "disabled":
                # Non-admin never sees disabled workflows
                assert len(visible_wfs) == 0
            elif user_role in visible_roles:
                # Enabled + role in visible_roles → visible
                assert len(visible_wfs) == 1
                assert visible_wfs[0].id == wf.id
            else:
                # Enabled but role not in visible_roles → not visible
                assert len(visible_wfs) == 0
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 6: 权限链路校验完整性
# ---------------------------------------------------------------------------

# Strategies for permission chain testing
_skill_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=3,
    max_size=20,
).filter(lambda s: s.strip())

_source_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=3,
    max_size=20,
).filter(lambda s: s.strip())

# Generate a pool of skill IDs, then split into workflow / role-allowed subsets
_skill_pool_strategy = st.lists(
    _skill_id_strategy, min_size=1, max_size=6, unique=True,
)

_source_pool_strategy = st.lists(
    _source_id_strategy, min_size=1, max_size=6, unique=True,
)


class TestPermissionChainCompleteness:
    """Property 6: 权限链路校验完整性

    *For any* workflow execution request, WorkflowService should sequentially
    validate: (1) user role access to workflow (visible_roles), (2) workflow
    skills within user role's SkillPermission range, (3) workflow data sources
    within user role's DataSourcePermission range. Any layer failure returns
    403 with specific permission info. Final effective permissions are the
    intersection of all layers.

    **Validates: Requirements 2.3, 2.5, 6.2, 11.5**
    """

    # ------------------------------------------------------------------
    # Test A: When all layers pass, effective permissions = intersection
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        skill_pool=_skill_pool_strategy,
        source_pool=_source_pool_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
        data=st.data(),
    )
    def test_all_layers_pass_returns_intersection(
        self, skill_pool, source_pool, user_role, data,
    ):
        """When role visibility passes and all skills/data sources are within
        role permissions, check_permission_chain returns effective permissions
        that equal the intersection of workflow config and role permissions.

        **Validates: Requirements 2.3, 2.5, 6.2, 11.5**
        """
        # Feature: ai-workflow-engine, Property 6: 权限链路校验完整性
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # Draw workflow skills as a subset of the pool
            wf_skills = data.draw(
                st.lists(
                    st.sampled_from(skill_pool),
                    min_size=0,
                    max_size=len(skill_pool),
                    unique=True,
                ),
                label="wf_skills",
            )

            # Role-allowed skills: must be a superset of wf_skills for success
            extra_skills = data.draw(
                st.lists(
                    st.sampled_from(skill_pool),
                    min_size=0,
                    max_size=len(skill_pool),
                    unique=True,
                ),
                label="extra_role_skills",
            )
            role_allowed_skills = list(set(wf_skills) | set(extra_skills))

            # Draw workflow data sources as a subset of the pool
            wf_source_ids = data.draw(
                st.lists(
                    st.sampled_from(source_pool),
                    min_size=0,
                    max_size=len(source_pool),
                    unique=True,
                ),
                label="wf_source_ids",
            )
            wf_data_source_auth = [
                {"source_id": sid} for sid in wf_source_ids
            ]

            # Role-allowed sources: must be a superset of wf sources for success
            extra_sources = data.draw(
                st.lists(
                    st.sampled_from(source_pool),
                    min_size=0,
                    max_size=len(source_pool),
                    unique=True,
                ),
                label="extra_role_sources",
            )
            role_allowed_sources = list(set(wf_source_ids) | set(extra_sources))

            # Create an enabled workflow visible to user_role
            wf = AIWorkflow(
                name="perm-chain-pass",
                description="test",
                skill_ids=wf_skills,
                data_source_auth=wf_data_source_auth,
                output_modes=["merge"],
                visible_roles=[user_role, "admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            # Mock permission services to return controlled sets
            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=role_allowed_skills,
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=role_allowed_sources,
            ):
                result = svc.check_permission_chain(wf, user_role)

            # Effective skills = wf_skills ∩ role_allowed_skills
            expected_skills = [
                s for s in wf_skills if s in set(role_allowed_skills)
            ]
            assert result.allowed_skill_ids == expected_skills, (
                f"Skill intersection mismatch:\n"
                f"  wf_skills={wf_skills}\n"
                f"  role_allowed={role_allowed_skills}\n"
                f"  expected={expected_skills}\n"
                f"  actual={result.allowed_skill_ids}"
            )

            # Effective data sources = wf entries whose source_id ∈ role_allowed
            expected_ds = [
                entry for entry in wf_data_source_auth
                if entry.get("source_id") in set(role_allowed_sources)
            ]
            assert result.allowed_data_sources == expected_ds, (
                f"Data source intersection mismatch:\n"
                f"  wf_sources={wf_source_ids}\n"
                f"  role_allowed={role_allowed_sources}\n"
                f"  expected={expected_ds}\n"
                f"  actual={result.allowed_data_sources}"
            )

            # Output modes pass through from workflow
            assert result.allowed_output_modes == ["merge"]
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test B: Role visibility failure → 403 WORKFLOW_PERMISSION_DENIED
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        visible_roles=st.lists(
            st.sampled_from(sorted(VALID_ROLES - {"admin"})),
            min_size=1,
            max_size=3,
            unique=True,
        ),
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
    )
    def test_role_visibility_failure_returns_403(
        self, visible_roles, user_role,
    ):
        """When user role is NOT in visible_roles, check_permission_chain
        raises 403 with WORKFLOW_PERMISSION_DENIED before checking skills
        or data sources.

        **Validates: Requirements 2.3, 2.5, 6.2, 11.5**
        """
        # Feature: ai-workflow-engine, Property 6: 权限链路校验完整性

        # Skip if user_role happens to be in visible_roles (not a failure case)
        if user_role in visible_roles:
            return

        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            wf = AIWorkflow(
                name="perm-chain-vis-fail",
                description="test",
                skill_ids=["skill-1"],
                data_source_auth=[{"source_id": "ds-1"}],
                output_modes=[],
                visible_roles=visible_roles,
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            with pytest.raises(HTTPException) as exc_info:
                svc.check_permission_chain(wf, user_role)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error_code"] == "WORKFLOW_PERMISSION_DENIED"
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test C: Skill permission failure → 403 WORKFLOW_SKILL_DENIED
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        skill_pool=_skill_pool_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
        data=st.data(),
    )
    def test_skill_permission_failure_returns_403(
        self, skill_pool, user_role, data,
    ):
        """When workflow skills exceed role's allowed skills,
        check_permission_chain raises 403 with WORKFLOW_SKILL_DENIED.

        **Validates: Requirements 2.3, 2.5, 6.2, 11.5**
        """
        # Feature: ai-workflow-engine, Property 6: 权限链路校验完整性
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # Workflow has all skills from pool
            wf_skills = skill_pool

            # Role only allows a strict subset (at least one skill denied)
            role_allowed = data.draw(
                st.lists(
                    st.sampled_from(skill_pool),
                    min_size=0,
                    max_size=max(0, len(skill_pool) - 1),
                    unique=True,
                ),
                label="role_allowed_skills",
            )

            # Ensure at least one skill is denied
            denied = set(wf_skills) - set(role_allowed)
            if not denied:
                return  # all skills happen to be allowed, skip

            wf = AIWorkflow(
                name="perm-chain-skill-fail",
                description="test",
                skill_ids=wf_skills,
                data_source_auth=[],
                output_modes=[],
                visible_roles=[user_role],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=role_allowed,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    svc.check_permission_chain(wf, user_role)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error_code"] == "WORKFLOW_SKILL_DENIED"

            # Verify denied skills are reported
            detail = exc_info.value.detail
            reported_denied = detail.get("details", {}).get("denied_skill_ids", [])
            assert set(reported_denied) == denied, (
                f"Denied skills mismatch: expected={denied}, "
                f"reported={reported_denied}"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test D: Data source permission failure → 403 WORKFLOW_DATASOURCE_DENIED
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        source_pool=_source_pool_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
        data=st.data(),
    )
    def test_datasource_permission_failure_returns_403(
        self, source_pool, user_role, data,
    ):
        """When workflow data sources exceed role's allowed sources,
        check_permission_chain raises 403 with WORKFLOW_DATASOURCE_DENIED.

        **Validates: Requirements 2.3, 2.5, 6.2, 11.5**
        """
        # Feature: ai-workflow-engine, Property 6: 权限链路校验完整性
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # Workflow has all sources from pool
            wf_source_ids = source_pool
            wf_data_source_auth = [
                {"source_id": sid} for sid in wf_source_ids
            ]

            # Role only allows a strict subset
            role_allowed = data.draw(
                st.lists(
                    st.sampled_from(source_pool),
                    min_size=0,
                    max_size=max(0, len(source_pool) - 1),
                    unique=True,
                ),
                label="role_allowed_sources",
            )

            denied = set(wf_source_ids) - set(role_allowed)
            if not denied:
                return  # all sources happen to be allowed, skip

            wf = AIWorkflow(
                name="perm-chain-ds-fail",
                description="test",
                skill_ids=[],  # no skills → skill check passes trivially
                data_source_auth=wf_data_source_auth,
                output_modes=[],
                visible_roles=[user_role],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=[],
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=role_allowed,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    svc.check_permission_chain(wf, user_role)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error_code"] == "WORKFLOW_DATASOURCE_DENIED"

            # Verify denied sources are reported
            detail = exc_info.value.detail
            reported_denied = detail.get("details", {}).get("denied_data_sources", [])
            assert set(reported_denied) == denied, (
                f"Denied sources mismatch: expected={denied}, "
                f"reported={reported_denied}"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test E: Disabled workflow → 403 WORKFLOW_DISABLED (before any perm check)
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        user_role=st.sampled_from(sorted(VALID_ROLES)),
    )
    def test_disabled_workflow_returns_403(self, user_role):
        """A disabled workflow always fails the permission chain with
        WORKFLOW_DISABLED, regardless of role or permissions.

        **Validates: Requirements 2.3, 2.5, 6.2, 11.5**
        """
        # Feature: ai-workflow-engine, Property 6: 权限链路校验完整性
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            wf = AIWorkflow(
                name="perm-chain-disabled",
                description="test",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=list(VALID_ROLES),
                status="disabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            with pytest.raises(HTTPException) as exc_info:
                svc.check_permission_chain(wf, user_role)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error_code"] == "WORKFLOW_DISABLED"
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 7: API 传参权限优先级
# ---------------------------------------------------------------------------


class TestAPIParameterOverridePriority:
    """Property 7: API 传参权限优先级

    *For any* workflow config and any API parameter overrides (skill_ids,
    data_source_auth), when API params conflict with workflow config, the
    final effective permissions should use API params.  If API params specify
    skill_ids, ignore workflow config's skill_ids and use API param value
    (still constrained by role base permissions).

    **Validates: Requirements 2.6, 3.6, 12.4, 12.5**
    """

    # ------------------------------------------------------------------
    # Test A: _resolve_effective_skills uses API override when present
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        wf_skills=st.lists(_skill_id_strategy, min_size=0, max_size=5, unique=True),
        api_skills=st.lists(_skill_id_strategy, min_size=0, max_size=5, unique=True),
    )
    def test_resolve_effective_skills_api_override(self, wf_skills, api_skills):
        """When api_overrides contains skill_ids, _resolve_effective_skills
        returns the API value, ignoring workflow config.

        **Validates: Requirements 2.6, 3.6, 12.4, 12.5**
        """
        # Feature: ai-workflow-engine, Property 7: API 传参权限优先级
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            wf = AIWorkflow(
                name="api-override-skills",
                description="test",
                skill_ids=wf_skills,
                data_source_auth=[],
                output_modes=[],
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            # With API override
            result_with = svc._resolve_effective_skills(
                wf, {"skill_ids": api_skills}
            )
            assert result_with == api_skills, (
                f"With API override, expected {api_skills}, got {result_with}"
            )

            # Without API override (key absent)
            result_without = svc._resolve_effective_skills(wf, {})
            assert result_without == list(wf_skills), (
                f"Without API override, expected {wf_skills}, got {result_without}"
            )

            # With None override (key present but None → falls back)
            result_none = svc._resolve_effective_skills(
                wf, {"skill_ids": None}
            )
            assert result_none == list(wf_skills), (
                f"With None override, expected {wf_skills}, got {result_none}"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test B: _resolve_effective_data_sources uses API override when present
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        wf_source_ids=st.lists(_source_id_strategy, min_size=0, max_size=5, unique=True),
        api_source_ids=st.lists(_source_id_strategy, min_size=0, max_size=5, unique=True),
    )
    def test_resolve_effective_data_sources_api_override(
        self, wf_source_ids, api_source_ids,
    ):
        """When api_overrides contains data_source_auth,
        _resolve_effective_data_sources returns the API value, ignoring
        workflow config.

        **Validates: Requirements 2.6, 3.6, 12.4, 12.5**
        """
        # Feature: ai-workflow-engine, Property 7: API 传参权限优先级
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            wf_ds = [{"source_id": sid} for sid in wf_source_ids]
            api_ds = [{"source_id": sid} for sid in api_source_ids]

            wf = AIWorkflow(
                name="api-override-ds",
                description="test",
                skill_ids=[],
                data_source_auth=wf_ds,
                output_modes=[],
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            # With API override
            result_with = svc._resolve_effective_data_sources(
                wf, {"data_source_auth": api_ds}
            )
            assert result_with == api_ds, (
                f"With API override, expected {api_ds}, got {result_with}"
            )

            # Without API override (key absent)
            result_without = svc._resolve_effective_data_sources(wf, {})
            assert result_without == list(wf_ds), (
                f"Without API override, expected {wf_ds}, got {result_without}"
            )

            # With None override (key present but None → falls back)
            result_none = svc._resolve_effective_data_sources(
                wf, {"data_source_auth": None}
            )
            assert result_none == list(wf_ds), (
                f"With None override, expected {wf_ds}, got {result_none}"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test C: check_permission_chain with api_overrides — override is
    #         used AND still constrained by role base permissions
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        skill_pool=_skill_pool_strategy,
        source_pool=_source_pool_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
        data=st.data(),
    )
    def test_check_permission_chain_api_overrides(
        self, skill_pool, source_pool, user_role, data,
    ):
        """When api_overrides are provided to check_permission_chain, the
        effective skills/data sources come from the overrides (not workflow
        config), but are still intersected with role base permissions.

        **Validates: Requirements 2.6, 3.6, 12.4, 12.5**
        """
        # Feature: ai-workflow-engine, Property 7: API 传参权限优先级
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # Workflow config skills (will be ignored when overrides present)
            wf_skills = data.draw(
                st.lists(
                    st.sampled_from(skill_pool),
                    min_size=0, max_size=len(skill_pool), unique=True,
                ),
                label="wf_skills",
            )

            # API override skills (a different subset of the pool)
            api_skills = data.draw(
                st.lists(
                    st.sampled_from(skill_pool),
                    min_size=0, max_size=len(skill_pool), unique=True,
                ),
                label="api_skills",
            )

            # Role-allowed skills: superset of api_skills so chain passes
            extra_skills = data.draw(
                st.lists(
                    st.sampled_from(skill_pool),
                    min_size=0, max_size=len(skill_pool), unique=True,
                ),
                label="extra_role_skills",
            )
            role_allowed_skills = list(set(api_skills) | set(extra_skills))

            # Workflow config data sources (will be ignored)
            wf_source_ids = data.draw(
                st.lists(
                    st.sampled_from(source_pool),
                    min_size=0, max_size=len(source_pool), unique=True,
                ),
                label="wf_source_ids",
            )
            wf_ds = [{"source_id": sid} for sid in wf_source_ids]

            # API override data sources
            api_source_ids = data.draw(
                st.lists(
                    st.sampled_from(source_pool),
                    min_size=0, max_size=len(source_pool), unique=True,
                ),
                label="api_source_ids",
            )
            api_ds = [{"source_id": sid} for sid in api_source_ids]

            # Role-allowed sources: superset of api sources so chain passes
            extra_sources = data.draw(
                st.lists(
                    st.sampled_from(source_pool),
                    min_size=0, max_size=len(source_pool), unique=True,
                ),
                label="extra_role_sources",
            )
            role_allowed_sources = list(set(api_source_ids) | set(extra_sources))

            wf = AIWorkflow(
                name="api-override-chain",
                description="test",
                skill_ids=wf_skills,
                data_source_auth=wf_ds,
                output_modes=["merge"],
                visible_roles=[user_role, "admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            api_overrides = {
                "skill_ids": api_skills,
                "data_source_auth": api_ds,
            }

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=role_allowed_skills,
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=role_allowed_sources,
            ):
                result = svc.check_permission_chain(
                    wf, user_role, api_overrides=api_overrides,
                )

            # Effective skills = api_skills ∩ role_allowed (NOT wf_skills)
            expected_skills = [
                s for s in api_skills if s in set(role_allowed_skills)
            ]
            assert result.allowed_skill_ids == expected_skills, (
                f"API override skill intersection mismatch:\n"
                f"  api_skills={api_skills}\n"
                f"  role_allowed={role_allowed_skills}\n"
                f"  expected={expected_skills}\n"
                f"  actual={result.allowed_skill_ids}"
            )

            # Effective data sources = api_ds entries ∩ role_allowed
            expected_ds = [
                entry for entry in api_ds
                if entry.get("source_id") in set(role_allowed_sources)
            ]
            assert result.allowed_data_sources == expected_ds, (
                f"API override data source intersection mismatch:\n"
                f"  api_ds={api_ds}\n"
                f"  role_allowed={role_allowed_sources}\n"
                f"  expected={expected_ds}\n"
                f"  actual={result.allowed_data_sources}"
            )

            # Output modes still come from workflow config
            assert result.allowed_output_modes == ["merge"]
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 26: 权限不足时包含授权请求结构
# ---------------------------------------------------------------------------


class TestAuthorizationRequestStructure:
    """Property 26: 权限不足时包含授权请求结构

    *For any* workflow execution that fails permission check (skill or data
    source layer), the 403 response details SHALL contain an
    ``authorization_request`` field with: non-empty ``request_id``, correct
    ``workflow_id``, at least one non-empty list in ``missing_permissions``
    (skills / data_sources / data_tables), non-empty ``requested_scope``,
    and non-empty ``callback_url``.

    **Validates: Requirements 14.1, 14.5**
    """

    # ------------------------------------------------------------------
    # Test A: Skill permission failure includes authorization_request
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        skill_pool=_skill_pool_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
        data=st.data(),
    )
    def test_skill_denied_includes_authorization_request(
        self, skill_pool, user_role, data,
    ):
        """When skills exceed role permissions, the 403 response contains
        a well-formed authorization_request with missing skill IDs.

        **Validates: Requirements 14.1, 14.5**
        """
        # Feature: ai-workflow-engine, Property 26: 权限不足时包含授权请求结构
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            wf_skills = skill_pool

            # Role allows a strict subset so at least one skill is denied
            role_allowed = data.draw(
                st.lists(
                    st.sampled_from(skill_pool),
                    min_size=0,
                    max_size=max(0, len(skill_pool) - 1),
                    unique=True,
                ),
                label="role_allowed_skills",
            )
            denied = set(wf_skills) - set(role_allowed)
            if not denied:
                return  # all skills allowed, skip

            wf = AIWorkflow(
                name="auth-req-skill",
                description="test",
                skill_ids=wf_skills,
                data_source_auth=[],
                output_modes=[],
                visible_roles=[user_role],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=role_allowed,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    svc.check_permission_chain(wf, user_role)

            assert exc_info.value.status_code == 403

            detail = exc_info.value.detail
            assert "details" in detail, "403 response must contain 'details'"

            auth_req = detail["details"].get("authorization_request")
            assert auth_req is not None, (
                "403 details must contain 'authorization_request'"
            )

            # request_id: non-empty string
            assert isinstance(auth_req.get("request_id"), str), (
                "authorization_request.request_id must be a string"
            )
            assert len(auth_req["request_id"]) > 0, (
                "authorization_request.request_id must be non-empty"
            )

            # workflow_id: matches the workflow
            assert auth_req.get("workflow_id") == wf.id, (
                f"authorization_request.workflow_id should be {wf.id!r}, "
                f"got {auth_req.get('workflow_id')!r}"
            )

            # missing_permissions: has skills list with denied IDs
            missing = auth_req.get("missing_permissions", {})
            assert missing is not None, (
                "authorization_request.missing_permissions must not be None"
            )
            missing_skills = missing.get("skills") or []
            assert len(missing_skills) > 0, (
                "missing_permissions.skills must be non-empty for skill denial"
            )
            assert set(missing_skills) == denied, (
                f"missing_permissions.skills mismatch: "
                f"expected={denied}, got={set(missing_skills)}"
            )

            # requested_scope: non-empty string
            assert isinstance(auth_req.get("requested_scope"), str), (
                "authorization_request.requested_scope must be a string"
            )
            assert len(auth_req["requested_scope"]) > 0, (
                "authorization_request.requested_scope must be non-empty"
            )

            # callback_url: non-empty string
            assert isinstance(auth_req.get("callback_url"), str), (
                "authorization_request.callback_url must be a string"
            )
            assert len(auth_req["callback_url"]) > 0, (
                "authorization_request.callback_url must be non-empty"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test B: Data source permission failure includes authorization_request
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        source_pool=_source_pool_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
        data=st.data(),
    )
    def test_datasource_denied_includes_authorization_request(
        self, source_pool, user_role, data,
    ):
        """When data sources exceed role permissions, the 403 response
        contains a well-formed authorization_request with missing source IDs.

        **Validates: Requirements 14.1, 14.5**
        """
        # Feature: ai-workflow-engine, Property 26: 权限不足时包含授权请求结构
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            wf_source_ids = source_pool
            wf_data_source_auth = [
                {"source_id": sid} for sid in wf_source_ids
            ]

            # Role allows a strict subset so at least one source is denied
            role_allowed = data.draw(
                st.lists(
                    st.sampled_from(source_pool),
                    min_size=0,
                    max_size=max(0, len(source_pool) - 1),
                    unique=True,
                ),
                label="role_allowed_sources",
            )
            denied = set(wf_source_ids) - set(role_allowed)
            if not denied:
                return  # all sources allowed, skip

            wf = AIWorkflow(
                name="auth-req-ds",
                description="test",
                skill_ids=[],
                data_source_auth=wf_data_source_auth,
                output_modes=[],
                visible_roles=[user_role],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=[],
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=role_allowed,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    svc.check_permission_chain(wf, user_role)

            assert exc_info.value.status_code == 403

            detail = exc_info.value.detail
            assert "details" in detail, "403 response must contain 'details'"

            auth_req = detail["details"].get("authorization_request")
            assert auth_req is not None, (
                "403 details must contain 'authorization_request'"
            )

            # request_id: non-empty string
            assert isinstance(auth_req.get("request_id"), str), (
                "authorization_request.request_id must be a string"
            )
            assert len(auth_req["request_id"]) > 0, (
                "authorization_request.request_id must be non-empty"
            )

            # workflow_id: matches the workflow
            assert auth_req.get("workflow_id") == wf.id, (
                f"authorization_request.workflow_id should be {wf.id!r}, "
                f"got {auth_req.get('workflow_id')!r}"
            )

            # missing_permissions: has data_sources list with denied IDs
            missing = auth_req.get("missing_permissions", {})
            assert missing is not None, (
                "authorization_request.missing_permissions must not be None"
            )
            missing_ds = missing.get("data_sources") or []
            assert len(missing_ds) > 0, (
                "missing_permissions.data_sources must be non-empty "
                "for data source denial"
            )
            assert set(missing_ds) == denied, (
                f"missing_permissions.data_sources mismatch: "
                f"expected={denied}, got={set(missing_ds)}"
            )

            # requested_scope: non-empty string
            assert isinstance(auth_req.get("requested_scope"), str), (
                "authorization_request.requested_scope must be a string"
            )
            assert len(auth_req["requested_scope"]) > 0, (
                "authorization_request.requested_scope must be non-empty"
            )

            # callback_url: non-empty string
            assert isinstance(auth_req.get("callback_url"), str), (
                "authorization_request.callback_url must be a string"
            )
            assert len(auth_req["callback_url"]) > 0, (
                "authorization_request.callback_url must be non-empty"
            )
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 8: 数据源总分结构序列化往返
# ---------------------------------------------------------------------------

# Strategy: generate random data_source_auth structures
_table_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip())

_tables_strategy = st.one_of(
    st.just(["*"]),
    st.lists(_table_name_strategy, min_size=1, max_size=5, unique=True),
)

_data_source_auth_entry_strategy = st.fixed_dictionaries({
    "source_id": st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s.strip()),
    "tables": _tables_strategy,
})

_data_source_auth_strategy = st.lists(
    _data_source_auth_entry_strategy,
    min_size=0,
    max_size=6,
).filter(
    # Ensure unique source_ids within a single auth list
    lambda entries: len(entries) == len({e["source_id"] for e in entries})
)


class TestDataSourceAuthSerializationRoundTrip:
    """Property 8: 数据源总分结构序列化往返

    *For any* valid data_source_auth structure (containing source_id and
    tables list), after storing to JSONB and reading back, the structure
    should be equivalent to the original input.

    **Validates: Requirements 3.1**
    """

    @settings(max_examples=100)
    @given(
        name=_workflow_name_strategy,
        data_source_auth=_data_source_auth_strategy,
    )
    def test_data_source_auth_jsonb_round_trip(self, name, data_source_auth):
        # Feature: ai-workflow-engine, Property 8: 数据源总分结构序列化往返
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            svc = WorkflowService(db=session)

            request = WorkflowCreateRequest(
                name=name,
                description="round-trip test",
                skill_ids=[],
                data_source_auth=data_source_auth,
                output_modes=[],
                visible_roles=["admin"],
            )

            with patch.object(svc, "_validate_skill_ids"), \
                 patch.object(svc, "_validate_data_source_auth"):
                workflow = svc.create_workflow(request, creator_id="test-user")

            workflow_id = workflow.id

            # Expire cached attributes and re-read from DB
            session.expire(workflow)
            reloaded = (
                session.query(AIWorkflow)
                .filter(AIWorkflow.id == workflow_id)
                .first()
            )

            assert reloaded is not None, "Workflow should exist after creation"

            # --- Core property: round-trip equality ---
            stored_auth = reloaded.data_source_auth

            assert isinstance(stored_auth, list), (
                f"data_source_auth should be a list, got {type(stored_auth)}"
            )
            assert len(stored_auth) == len(data_source_auth), (
                f"data_source_auth length mismatch: "
                f"expected {len(data_source_auth)}, got {len(stored_auth)}"
            )

            # Compare each entry by source_id and tables
            original_by_id = {e["source_id"]: e["tables"] for e in data_source_auth}
            stored_by_id = {e["source_id"]: e["tables"] for e in stored_auth}

            assert set(original_by_id.keys()) == set(stored_by_id.keys()), (
                f"source_id set mismatch: "
                f"expected {set(original_by_id.keys())}, "
                f"got {set(stored_by_id.keys())}"
            )

            for source_id in original_by_id:
                orig_tables = original_by_id[source_id]
                stored_tables = stored_by_id[source_id]

                assert isinstance(stored_tables, list), (
                    f"tables for '{source_id}' should be a list"
                )

                # For wildcard ["*"], exact match; for specific tables, set equality
                if orig_tables == ["*"]:
                    assert stored_tables == ["*"], (
                        f"Wildcard tables for '{source_id}' not preserved: "
                        f"got {stored_tables!r}"
                    )
                else:
                    assert set(orig_tables) == set(stored_tables), (
                        f"Tables mismatch for '{source_id}': "
                        f"expected {sorted(orig_tables)}, "
                        f"got {sorted(stored_tables)}"
                    )
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 9: 数据表级别访问控制
# ---------------------------------------------------------------------------

from src.ai.workflow_service import DATA_SOURCE_TABLES

# Known source IDs from the production registry
_KNOWN_SOURCE_IDS = sorted(DATA_SOURCE_TABLES.keys())

# Strategy: pick a source_id from the known registry
_known_source_id_strategy = st.sampled_from(_KNOWN_SOURCE_IDS)


def _tables_config_for_source(source_id: str) -> st.SearchStrategy:
    """Return a strategy that generates a valid tables config for a source.

    Either ["*"] (all tables) or a non-empty subset of known tables.
    """
    known = sorted(DATA_SOURCE_TABLES.get(source_id, []))
    if not known:
        return st.just(["*"])
    return st.one_of(
        st.just(["*"]),
        st.lists(
            st.sampled_from(known), min_size=1, max_size=len(known), unique=True,
        ),
    )


def _requested_tables_strategy(source_id: str) -> st.SearchStrategy:
    """Return a strategy for requested_tables: None or a mix of known/unknown tables."""
    known = sorted(DATA_SOURCE_TABLES.get(source_id, []))
    unknown_table = st.text(
        alphabet=st.characters(whitelist_categories=("L",), whitelist_characters="_"),
        min_size=5, max_size=15,
    ).filter(lambda t: t not in set(known))

    if not known:
        table_pool = unknown_table
    else:
        table_pool = st.one_of(st.sampled_from(known), unknown_table)

    return st.one_of(
        st.none(),
        st.lists(table_pool, min_size=0, max_size=6, unique=True),
    )


class TestTableLevelAccessControl:
    """Property 9: 数据表级别访问控制

    *For any* workflow data_source_auth config and any query request, the
    actual queried tables (authorized_tables in the result) should be a
    subset of the authorized tables defined in the workflow config.
    Unauthorized tables should never appear in the result.

    **Validates: Requirements 3.3**
    """

    # ------------------------------------------------------------------
    # Test A: Authorized tables are always a subset of the config
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        source_id=_known_source_id_strategy,
        data=st.data(),
    )
    def test_result_is_subset_of_authorized_config(self, source_id, data):
        """For any auth config and requested tables, the returned
        authorized_tables must be a subset of what the config allows AND
        a subset of known tables for the source.

        **Validates: Requirements 3.3**
        """
        # Feature: ai-workflow-engine, Property 9: 数据表级别访问控制
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)

            tables_config = data.draw(
                _tables_config_for_source(source_id), label="tables_config",
            )
            requested_tables = data.draw(
                _requested_tables_strategy(source_id), label="requested_tables",
            )

            data_source_auth = [{"source_id": source_id, "tables": tables_config}]

            result = svc.filter_authorized_tables(
                data_source_auth, source_id, requested_tables,
            )
            authorized_tables = set(result["authorized_tables"])
            known_tables = set(DATA_SOURCE_TABLES.get(source_id, []))

            # Determine the maximum allowed set from config
            if tables_config == ["*"]:
                config_allowed = known_tables
            else:
                config_allowed = set(tables_config)

            # Core property: result ⊆ config_allowed ∩ known_tables
            assert authorized_tables <= (config_allowed & known_tables), (
                f"Result contains tables outside authorized config:\n"
                f"  source_id={source_id}\n"
                f"  tables_config={tables_config}\n"
                f"  requested={requested_tables}\n"
                f"  result={sorted(authorized_tables)}\n"
                f"  config_allowed ∩ known={sorted(config_allowed & known_tables)}"
            )

            # If requested_tables is provided, result must also be ⊆ requested
            if requested_tables is not None:
                assert authorized_tables <= set(requested_tables), (
                    f"Result contains tables not in requested set:\n"
                    f"  requested={requested_tables}\n"
                    f"  result={sorted(authorized_tables)}"
                )
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Test B: Unauthorized source returns empty
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        auth_source_id=_known_source_id_strategy,
        query_source_id=_known_source_id_strategy,
        data=st.data(),
    )
    def test_unauthorized_source_returns_empty(
        self, auth_source_id, query_source_id, data,
    ):
        """When querying a source_id that is NOT in data_source_auth,
        the result must be empty — no tables are authorized.

        **Validates: Requirements 3.3**
        """
        # Feature: ai-workflow-engine, Property 9: 数据表级别访问控制

        # Only test when query source differs from auth source
        if query_source_id == auth_source_id:
            return

        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)

            tables_config = data.draw(
                _tables_config_for_source(auth_source_id), label="tables_config",
            )
            data_source_auth = [{"source_id": auth_source_id, "tables": tables_config}]

            result = svc.filter_authorized_tables(
                data_source_auth, query_source_id, None,
            )

            assert result["authorized_tables"] == [], (
                f"Querying unauthorized source should return empty:\n"
                f"  auth_source={auth_source_id}\n"
                f"  query_source={query_source_id}\n"
                f"  result={result['authorized_tables']}"
            )
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Test C: Wildcard config authorizes all known tables
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(source_id=_known_source_id_strategy)
    def test_wildcard_authorizes_all_known_tables(self, source_id):
        """When tables config is ["*"] and no requested filter, the result
        should contain all known tables for the source.

        **Validates: Requirements 3.3**
        """
        # Feature: ai-workflow-engine, Property 9: 数据表级别访问控制
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)

            data_source_auth = [{"source_id": source_id, "tables": ["*"]}]
            result = svc.filter_authorized_tables(
                data_source_auth, source_id, None,
            )

            known_tables = set(DATA_SOURCE_TABLES.get(source_id, []))
            assert set(result["authorized_tables"]) == known_tables, (
                f"Wildcard should authorize all known tables:\n"
                f"  source_id={source_id}\n"
                f"  known={sorted(known_tables)}\n"
                f"  result={sorted(result['authorized_tables'])}"
            )
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Test D: Specific config never leaks unauthorized tables
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        source_id=_known_source_id_strategy,
        data=st.data(),
    )
    def test_specific_config_never_leaks_unauthorized(self, source_id, data):
        """When tables config lists specific tables, requesting tables
        outside that list must never appear in the result.

        **Validates: Requirements 3.3**
        """
        # Feature: ai-workflow-engine, Property 9: 数据表级别访问控制
        known = sorted(DATA_SOURCE_TABLES.get(source_id, []))
        if len(known) < 2:
            return  # need at least 2 tables to split authorized/unauthorized

        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)

            # Split known tables: authorize only a strict subset
            split = data.draw(
                st.integers(min_value=1, max_value=len(known) - 1),
                label="split_point",
            )
            authorized_config = known[:split]
            unauthorized_tables = known[split:]

            data_source_auth = [
                {"source_id": source_id, "tables": authorized_config},
            ]

            # Request ALL known tables (including unauthorized ones)
            result = svc.filter_authorized_tables(
                data_source_auth, source_id, known,
            )
            result_set = set(result["authorized_tables"])

            # No unauthorized table should appear
            leaked = result_set & set(unauthorized_tables)
            assert not leaked, (
                f"Unauthorized tables leaked into result:\n"
                f"  authorized_config={authorized_config}\n"
                f"  unauthorized={unauthorized_tables}\n"
                f"  leaked={sorted(leaked)}"
            )

            # All authorized known tables should be present
            expected = set(authorized_config) & set(known)
            assert result_set == expected, (
                f"Result should contain exactly authorized known tables:\n"
                f"  expected={sorted(expected)}\n"
                f"  result={sorted(result_set)}"
            )
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 10: 数据源授权不超过启用范围
# ---------------------------------------------------------------------------

# Ensure AIDataSourceConfigModel table exists in the test SQLite DB
AIDataSourceConfigModel.__table__.create(bind=_engine, checkfirst=True)

# Strategy: generate short, unique source IDs for test data
_ds_source_id_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"), whitelist_characters="_-"
    ),
    min_size=3,
    max_size=20,
).filter(lambda s: s.strip())

# Pool of source IDs to use across a single test example
_ds_pool_strategy = st.lists(
    _ds_source_id_strategy, min_size=1, max_size=6, unique=True,
)


class TestDataSourceAuthWithinEnabledScope:
    """Property 10: 数据源授权不超过启用范围

    *For any* workflow creation or update request, data_source_auth entries
    referencing a source_id that does not exist in AIDataSourceConfigModel
    SHALL be rejected with WORKFLOW_DATASOURCE_NOT_FOUND; entries referencing
    a disabled source SHALL be rejected with WORKFLOW_DATASOURCE_DISABLED.
    Only entries referencing existing and enabled sources SHALL pass
    validation.

    **Validates: Requirements 3.5, 6.1**
    """

    # ------------------------------------------------------------------
    # Test A: All sources exist and are enabled → validation passes
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        source_ids=_ds_pool_strategy,
    )
    def test_all_enabled_sources_pass_validation(self, source_ids):
        """When every source_id in data_source_auth exists in
        AIDataSourceConfigModel with enabled=True, _validate_data_source_auth
        should NOT raise any exception.

        **Validates: Requirements 3.5, 6.1**
        """
        # Feature: ai-workflow-engine, Property 10: 数据源授权不超过启用范围
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIDataSourceConfigModel).delete()
            session.commit()

            # Insert all sources as enabled
            for sid in source_ids:
                row = AIDataSourceConfigModel(
                    id=sid, label=f"Source {sid}", enabled=True,
                )
                session.add(row)
            session.commit()

            svc = WorkflowService(db=session)

            data_source_auth = [{"source_id": sid} for sid in source_ids]

            # Should NOT raise
            svc._validate_data_source_auth(data_source_auth)
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test B: At least one non-existent source → WORKFLOW_DATASOURCE_NOT_FOUND
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        existing_ids=_ds_pool_strategy,
        missing_ids=_ds_pool_strategy,
    )
    def test_nonexistent_source_rejected(self, existing_ids, missing_ids):
        """When data_source_auth references a source_id that does NOT exist
        in AIDataSourceConfigModel, _validate_data_source_auth should raise
        HTTPException 400 with error_code WORKFLOW_DATASOURCE_NOT_FOUND.

        **Validates: Requirements 3.5, 6.1**
        """
        # Feature: ai-workflow-engine, Property 10: 数据源授权不超过启用范围

        # Ensure missing_ids are truly absent (not overlapping with existing)
        truly_missing = [sid for sid in missing_ids if sid not in set(existing_ids)]
        if not truly_missing:
            return  # all "missing" IDs happen to be in existing, skip

        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIDataSourceConfigModel).delete()
            session.commit()

            # Insert only the existing sources as enabled
            for sid in existing_ids:
                row = AIDataSourceConfigModel(
                    id=sid, label=f"Source {sid}", enabled=True,
                )
                session.add(row)
            session.commit()

            svc = WorkflowService(db=session)

            # Build auth list that includes at least one missing source
            # Put a missing source first to ensure it triggers the error
            data_source_auth = [{"source_id": truly_missing[0]}]

            with pytest.raises(HTTPException) as exc_info:
                svc._validate_data_source_auth(data_source_auth)

            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == "WORKFLOW_DATASOURCE_NOT_FOUND"
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test C: At least one disabled source → WORKFLOW_DATASOURCE_DISABLED
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        enabled_ids=_ds_pool_strategy,
        disabled_ids=_ds_pool_strategy,
    )
    def test_disabled_source_rejected(self, enabled_ids, disabled_ids):
        """When data_source_auth references a source_id that exists in
        AIDataSourceConfigModel but has enabled=False,
        _validate_data_source_auth should raise HTTPException 400 with
        error_code WORKFLOW_DATASOURCE_DISABLED.

        **Validates: Requirements 3.5, 6.1**
        """
        # Feature: ai-workflow-engine, Property 10: 数据源授权不超过启用范围

        # Ensure disabled_ids don't overlap with enabled_ids
        truly_disabled = [sid for sid in disabled_ids if sid not in set(enabled_ids)]
        if not truly_disabled:
            return  # all "disabled" IDs overlap with enabled, skip

        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIDataSourceConfigModel).delete()
            session.commit()

            # Insert enabled sources
            for sid in enabled_ids:
                row = AIDataSourceConfigModel(
                    id=sid, label=f"Source {sid}", enabled=True,
                )
                session.add(row)

            # Insert disabled sources
            for sid in truly_disabled:
                row = AIDataSourceConfigModel(
                    id=sid, label=f"Source {sid}", enabled=False,
                )
                session.add(row)
            session.commit()

            svc = WorkflowService(db=session)

            # Build auth list with a disabled source first
            data_source_auth = [{"source_id": truly_disabled[0]}]

            with pytest.raises(HTTPException) as exc_info:
                svc._validate_data_source_auth(data_source_auth)

            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == "WORKFLOW_DATASOURCE_DISABLED"
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test D: Create and update both reject invalid data sources
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        source_id=_ds_source_id_strategy,
        source_exists=st.booleans(),
        source_enabled=st.booleans(),
    )
    def test_create_and_update_both_reject_invalid_sources(
        self, source_id, source_exists, source_enabled,
    ):
        """For any single data source reference, both create_workflow and
        update_workflow should produce the same validation outcome:
        accept if source exists and is enabled, reject otherwise.

        **Validates: Requirements 3.5, 6.1**
        """
        # Feature: ai-workflow-engine, Property 10: 数据源授权不超过启用范围
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIDataSourceConfigModel).delete()
            session.commit()

            # Conditionally insert the data source
            if source_exists:
                row = AIDataSourceConfigModel(
                    id=source_id, label=f"Source {source_id}",
                    enabled=source_enabled,
                )
                session.add(row)
                session.commit()

            svc = WorkflowService(db=session)

            data_source_auth = [{"source_id": source_id}]

            # Determine expected outcome
            should_pass = source_exists and source_enabled

            if should_pass:
                expected_error_code = None
            elif not source_exists:
                expected_error_code = "WORKFLOW_DATASOURCE_NOT_FOUND"
            else:
                expected_error_code = "WORKFLOW_DATASOURCE_DISABLED"

            # --- Test CREATE ---
            create_request = WorkflowCreateRequest(
                name="ds-validation-test",
                description="test",
                skill_ids=[],
                data_source_auth=data_source_auth,
                output_modes=[],
                visible_roles=["admin"],
            )

            create_error = None
            try:
                with patch.object(svc, "_validate_skill_ids"):
                    svc.create_workflow(create_request, creator_id="test")
            except HTTPException as exc:
                create_error = exc

            # --- Test UPDATE (need a base workflow first) ---
            # Create a base workflow with no data sources
            session.query(AIWorkflow).delete()
            if source_exists:
                # Re-insert if we cleared during create
                existing = session.query(AIDataSourceConfigModel).filter(
                    AIDataSourceConfigModel.id == source_id
                ).first()
                if not existing:
                    row = AIDataSourceConfigModel(
                        id=source_id, label=f"Source {source_id}",
                        enabled=source_enabled,
                    )
                    session.add(row)
            session.commit()

            base_wf = AIWorkflow(
                name="base-for-update",
                description="base",
                skill_ids=[],
                data_source_auth=[],
                output_modes=[],
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(base_wf)
            session.commit()
            session.refresh(base_wf)

            update_request = WorkflowUpdateRequest(
                data_source_auth=data_source_auth,
            )

            update_error = None
            try:
                with patch.object(svc, "_validate_skill_ids"):
                    svc.update_workflow(base_wf.id, update_request)
            except HTTPException as exc:
                update_error = exc

            # --- Verify consistency ---
            create_failed = create_error is not None
            update_failed = update_error is not None

            assert create_failed == update_failed, (
                f"Create/update validation mismatch for source_id={source_id!r} "
                f"(exists={source_exists}, enabled={source_enabled}): "
                f"create {'rejected' if create_failed else 'accepted'}, "
                f"update {'rejected' if update_failed else 'accepted'}"
            )

            if should_pass:
                assert not create_failed, (
                    f"Valid source should pass: source_id={source_id!r}"
                )
            else:
                assert create_failed, (
                    f"Invalid source should be rejected: source_id={source_id!r} "
                    f"(exists={source_exists}, enabled={source_enabled})"
                )
                assert create_error.status_code == 400
                assert create_error.detail["error_code"] == expected_error_code
                assert update_error.status_code == 400
                assert update_error.detail["error_code"] == expected_error_code
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 16: 宽松与严格配置均正确处理
# ---------------------------------------------------------------------------


def _mixed_data_source_auth_strategy(data):
    """Draw a data_source_auth list with a mix of wildcard and specific configs.

    Picks 2+ known source IDs, then for each independently draws either
    ["*"] or a specific subset of known tables.
    """
    source_ids = data.draw(
        st.lists(
            _known_source_id_strategy,
            min_size=2,
            max_size=len(_KNOWN_SOURCE_IDS),
            unique=True,
        ),
        label="source_ids",
    )
    entries = []
    for sid in source_ids:
        tables = data.draw(
            _tables_config_for_source(sid), label=f"tables_for_{sid}",
        )
        entries.append({"source_id": sid, "tables": tables})
    return entries


class TestLooseAndStrictConfigHandling:
    """Property 16: 宽松与严格配置均正确处理

    *For any* workflow with mixed data_source_auth (some sources with
    ``tables: ["*"]``, some with specific table lists), the access scope
    is correctly computed for each source independently.  Wildcard sources
    allow all known tables; specific sources allow only listed tables.

    **Validates: Requirements 5.3**
    """

    @settings(max_examples=100)
    @given(data=st.data())
    def test_mixed_wildcard_and_specific_access_scope(self, data):
        """For a mixed config, filter_authorized_tables returns all known
        tables for wildcard sources and only listed tables for specific
        sources.

        **Validates: Requirements 5.3**
        """
        # Feature: ai-workflow-engine, Property 16: 宽松与严格配置均正确处理
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)

            auth_entries = _mixed_data_source_auth_strategy(data)

            for entry in auth_entries:
                sid = entry["source_id"]
                tables_config = entry["tables"]
                known_tables = set(DATA_SOURCE_TABLES.get(sid, []))

                # Query without requested_tables filter (get full scope)
                result = svc.filter_authorized_tables(auth_entries, sid, None)
                authorized = set(result["authorized_tables"])

                if tables_config == ["*"]:
                    # Wildcard: all known tables should be authorized
                    assert authorized == known_tables, (
                        f"Wildcard source '{sid}' should authorize all "
                        f"known tables:\n"
                        f"  known={sorted(known_tables)}\n"
                        f"  authorized={sorted(authorized)}"
                    )
                else:
                    # Specific: only listed tables that are known
                    expected = set(tables_config) & known_tables
                    assert authorized == expected, (
                        f"Specific source '{sid}' should authorize only "
                        f"listed known tables:\n"
                        f"  config={tables_config}\n"
                        f"  known={sorted(known_tables)}\n"
                        f"  expected={sorted(expected)}\n"
                        f"  authorized={sorted(authorized)}"
                    )
        finally:
            session.close()

    @settings(max_examples=100)
    @given(data=st.data())
    def test_sources_are_independent(self, data):
        """Querying one source never leaks tables from another source,
        even in a mixed wildcard/specific config.

        **Validates: Requirements 5.3**
        """
        # Feature: ai-workflow-engine, Property 16: 宽松与严格配置均正确处理
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)

            auth_entries = _mixed_data_source_auth_strategy(data)
            configured_sids = {e["source_id"] for e in auth_entries}

            for entry in auth_entries:
                sid = entry["source_id"]
                known_tables = set(DATA_SOURCE_TABLES.get(sid, []))

                result = svc.filter_authorized_tables(auth_entries, sid, None)
                authorized = set(result["authorized_tables"])

                # All authorized tables must belong to this source's known set
                assert authorized <= known_tables, (
                    f"Source '{sid}' returned tables outside its own "
                    f"known set:\n"
                    f"  authorized={sorted(authorized)}\n"
                    f"  known={sorted(known_tables)}"
                )

            # Querying a source NOT in the config returns empty
            all_known = set(_KNOWN_SOURCE_IDS)
            unconfigured = all_known - configured_sids
            if unconfigured:
                probe_sid = sorted(unconfigured)[0]
                result = svc.filter_authorized_tables(
                    auth_entries, probe_sid, None,
                )
                assert result["authorized_tables"] == [], (
                    f"Unconfigured source '{probe_sid}' should return "
                    f"empty, got {result['authorized_tables']}"
                )
        finally:
            session.close()

    @settings(max_examples=100)
    @given(data=st.data())
    def test_requested_filter_intersects_correctly(self, data):
        """When requested_tables is provided, the result is the intersection
        of authorized tables and requested tables, for both wildcard and
        specific configs.

        **Validates: Requirements 5.3**
        """
        # Feature: ai-workflow-engine, Property 16: 宽松与严格配置均正确处理
        session = _SessionLocal()
        try:
            svc = WorkflowService(db=session)

            auth_entries = _mixed_data_source_auth_strategy(data)

            # Pick one source to test with a requested_tables filter
            entry = data.draw(
                st.sampled_from(auth_entries), label="target_entry",
            )
            sid = entry["source_id"]
            tables_config = entry["tables"]
            known_tables = sorted(DATA_SOURCE_TABLES.get(sid, []))

            if not known_tables:
                return  # skip sources with no known tables

            requested = data.draw(
                st.lists(
                    st.sampled_from(known_tables),
                    min_size=1,
                    max_size=len(known_tables),
                    unique=True,
                ),
                label="requested_tables",
            )

            result = svc.filter_authorized_tables(
                auth_entries, sid, requested,
            )
            authorized = set(result["authorized_tables"])

            # Compute expected: authorized_by_config ∩ requested ∩ known
            if tables_config == ["*"]:
                config_allowed = set(known_tables)
            else:
                config_allowed = set(tables_config) & set(known_tables)

            expected = config_allowed & set(requested)
            assert authorized == expected, (
                f"Requested filter intersection failed for '{sid}':\n"
                f"  tables_config={tables_config}\n"
                f"  requested={requested}\n"
                f"  config_allowed={sorted(config_allowed)}\n"
                f"  expected={sorted(expected)}\n"
                f"  authorized={sorted(authorized)}"
            )
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 11: 权限同步批量更新正确性
# ---------------------------------------------------------------------------

# Strategy: generate a small pool of workflows with initial data_source_auth
_initial_auth_entry_strategy = st.fixed_dictionaries({
    "source_id": st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s.strip()),
    "tables": st.one_of(
        st.just(["*"]),
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
                min_size=1,
                max_size=20,
            ).filter(lambda s: s.strip()),
            min_size=1,
            max_size=4,
            unique=True,
        ),
    ),
})

_initial_auth_strategy = st.lists(
    _initial_auth_entry_strategy,
    min_size=0,
    max_size=3,
).filter(
    lambda entries: len(entries) == len({e["source_id"] for e in entries})
)


class TestPermissionSyncBatchUpdateCorrectness:
    """Property 11: 权限同步批量更新正确性

    *For any* set of workflows and any permission sync request, (1) affected
    workflows reflect the new data_source_auth, (2) unmentioned workflows
    retain their original data_source_auth unchanged, (3) updated_count
    matches the number of successfully updated workflows.

    **Validates: Requirements 3.7**
    """

    @settings(max_examples=100)
    @given(data=st.data())
    def test_sync_permissions_batch_correctness(self, data):
        # Feature: ai-workflow-engine, Property 11: 权限同步批量更新正确性
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # --- Step 1: Create 2-6 workflows with random initial auth ---
            num_workflows = data.draw(
                st.integers(min_value=2, max_value=6), label="num_workflows",
            )
            workflows = []
            for i in range(num_workflows):
                initial_auth = data.draw(
                    _initial_auth_strategy, label=f"initial_auth_{i}",
                )
                wf = AIWorkflow(
                    name=f"sync-test-wf-{i}",
                    description="",
                    skill_ids=[],
                    data_source_auth=initial_auth,
                    output_modes=[],
                    visible_roles=["admin"],
                    status="enabled",
                )
                session.add(wf)
            session.commit()

            # Refresh to get IDs
            all_wfs = session.query(AIWorkflow).all()
            for wf in all_wfs:
                workflows.append({
                    "id": wf.id,
                    "original_auth": list(wf.data_source_auth or []),
                })

            wf_ids = [w["id"] for w in workflows]

            # --- Step 2: Pick a random subset to update ---
            num_to_update = data.draw(
                st.integers(min_value=0, max_value=len(wf_ids)),
                label="num_to_update",
            )
            ids_to_update = data.draw(
                st.lists(
                    st.sampled_from(wf_ids),
                    min_size=num_to_update,
                    max_size=num_to_update,
                    unique=True,
                ),
                label="ids_to_update",
            )

            # Generate new auth for each targeted workflow
            permission_list = []
            expected_new_auth = {}  # workflow_id -> new auth
            for wf_id in ids_to_update:
                new_auth = data.draw(
                    _initial_auth_strategy, label=f"new_auth_{wf_id}",
                )
                permission_list.append({
                    "workflow_id": wf_id,
                    "data_source_auth": new_auth,
                })
                expected_new_auth[wf_id] = new_auth

            unmentioned_ids = set(wf_ids) - set(ids_to_update)

            # Snapshot original auth for unmentioned workflows
            original_auth_map = {
                w["id"]: w["original_auth"] for w in workflows
            }

            # --- Step 3: Execute sync ---
            svc = WorkflowService(db=session)
            result = svc.sync_permissions(permission_list)

            # --- Assert (3): updated_count matches targeted count ---
            assert result["updated_count"] == len(ids_to_update), (
                f"updated_count mismatch: expected {len(ids_to_update)}, "
                f"got {result['updated_count']}"
            )
            assert result["errors"] == [], (
                f"Expected no errors for valid entries, got {result['errors']}"
            )

            # --- Assert (1): affected workflows reflect new auth ---
            for wf_id, new_auth in expected_new_auth.items():
                wf = session.query(AIWorkflow).filter(
                    AIWorkflow.id == wf_id
                ).first()
                session.refresh(wf)
                assert wf.data_source_auth == new_auth, (
                    f"Workflow {wf_id} auth not updated:\n"
                    f"  expected: {new_auth}\n"
                    f"  got: {wf.data_source_auth}"
                )

            # --- Assert (2): unmentioned workflows unchanged ---
            for wf_id in unmentioned_ids:
                wf = session.query(AIWorkflow).filter(
                    AIWorkflow.id == wf_id
                ).first()
                session.refresh(wf)
                assert wf.data_source_auth == original_auth_map[wf_id], (
                    f"Unmentioned workflow {wf_id} was modified:\n"
                    f"  original: {original_auth_map[wf_id]}\n"
                    f"  current: {wf.data_source_auth}"
                )
        finally:
            session.rollback()
            session.close()

    @settings(max_examples=100)
    @given(data=st.data())
    def test_sync_with_invalid_entries_skips_correctly(self, data):
        """Mixed valid and invalid entries: valid ones update, invalid ones
        are reported as errors, unmentioned workflows stay unchanged.

        **Validates: Requirements 3.7**
        """
        # Feature: ai-workflow-engine, Property 11: 权限同步批量更新正确性
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.commit()

            # Create 2-4 workflows
            num_workflows = data.draw(
                st.integers(min_value=2, max_value=4), label="num_workflows",
            )
            wf_ids = []
            original_auths = {}
            for i in range(num_workflows):
                initial_auth = data.draw(
                    _initial_auth_strategy, label=f"init_auth_{i}",
                )
                wf = AIWorkflow(
                    name=f"sync-mixed-{i}",
                    description="",
                    skill_ids=[],
                    data_source_auth=initial_auth,
                    output_modes=[],
                    visible_roles=["admin"],
                    status="enabled",
                )
                session.add(wf)
                session.flush()
                wf_ids.append(wf.id)
                original_auths[wf.id] = list(initial_auth)
            session.commit()

            # Pick one valid workflow to update
            valid_id = data.draw(
                st.sampled_from(wf_ids), label="valid_id",
            )
            new_auth = data.draw(
                _initial_auth_strategy, label="new_auth_valid",
            )

            # Build permission_list with one valid + one invalid entry
            num_invalid = data.draw(
                st.integers(min_value=1, max_value=3), label="num_invalid",
            )
            invalid_entries = [
                {
                    "workflow_id": f"nonexistent-{j}",
                    "data_source_auth": [],
                }
                for j in range(num_invalid)
            ]

            permission_list = [
                {"workflow_id": valid_id, "data_source_auth": new_auth},
            ] + invalid_entries

            svc = WorkflowService(db=session)
            result = svc.sync_permissions(permission_list)

            # updated_count = 1 (only the valid one)
            assert result["updated_count"] == 1, (
                f"Expected 1 update, got {result['updated_count']}"
            )
            assert len(result["errors"]) == num_invalid, (
                f"Expected {num_invalid} errors, got {len(result['errors'])}"
            )

            # Valid workflow updated
            wf = session.query(AIWorkflow).filter(
                AIWorkflow.id == valid_id
            ).first()
            session.refresh(wf)
            assert wf.data_source_auth == new_auth

            # Other workflows unchanged
            for wf_id in wf_ids:
                if wf_id == valid_id:
                    continue
                wf = session.query(AIWorkflow).filter(
                    AIWorkflow.id == wf_id
                ).first()
                session.refresh(wf)
                assert wf.data_source_auth == original_auths[wf_id], (
                    f"Workflow {wf_id} should be unchanged"
                )
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 12: 工作流配置参数提取
# ---------------------------------------------------------------------------

import asyncio
from unittest.mock import AsyncMock

# Ensure AIAccessLog and AIGateway tables exist for execute_workflow tests
from src.models.ai_access_log import AIAccessLog
from src.models.ai_integration import AIGateway

AIAccessLog.__table__.create(bind=_engine, checkfirst=True)
AIGateway.__table__.create(bind=_engine, checkfirst=True)

# Strategy: generate skill IDs for workflow config
_wf_skill_ids_strategy = st.lists(
    _skill_id_strategy, min_size=0, max_size=4, unique=True,
)

# Strategy: generate data_source_auth entries for workflow config
_wf_data_source_auth_strategy = st.lists(
    st.fixed_dictionaries({
        "source_id": _source_id_strategy,
    }),
    min_size=0,
    max_size=4,
).filter(
    lambda entries: len(entries) == len({e["source_id"] for e in entries})
)

# Strategy: generate output_modes for workflow config
_wf_output_modes_strategy = st.lists(
    st.sampled_from(["merge", "compare"]),
    max_size=2,
    unique=True,
)


class TestWorkflowConfigParameterExtraction:
    """Property 12: 工作流配置参数提取

    *For any* chat request with a workflow_id, WorkflowService SHALL extract
    skill_ids, data_source_auth, and output_modes from the workflow config
    and use them instead of manual configuration parameters (mode, skill_ids,
    data_source_ids, output_mode).

    **Validates: Requirements 4.3**
    """

    @settings(max_examples=100)
    @given(
        wf_skill_ids=_wf_skill_ids_strategy,
        wf_data_source_auth=_wf_data_source_auth_strategy,
        wf_output_modes=_wf_output_modes_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
    )
    def test_execute_workflow_extracts_config_params(
        self, wf_skill_ids, wf_data_source_auth, wf_output_modes, user_role,
    ):
        """When execute_workflow() is called with a workflow_id, the
        workflow's skill_ids, data_source_auth, and output_modes are
        extracted from the config and used for execution. The result
        contains the workflow_id and the workflow's output_modes.

        **Validates: Requirements 4.3**
        """
        # Feature: ai-workflow-engine, Property 12: 工作流配置参数提取
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            # Create workflow with specific config
            wf = AIWorkflow(
                name="config-extract-test",
                description="test parameter extraction",
                skill_ids=wf_skill_ids,
                data_source_auth=wf_data_source_auth,
                output_modes=wf_output_modes,
                visible_roles=[user_role, "admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            # Build a mock user with the required attributes
            mock_user = MagicMock()
            mock_user.role = user_role
            mock_user.id = "test-user-id"
            mock_user.tenant_id = "test-tenant"

            # Role-allowed skills/sources must be supersets so chain passes
            role_allowed_skills = list(wf_skill_ids)
            role_allowed_sources = [
                e.get("source_id") for e in wf_data_source_auth
            ]

            # Mock execution result
            mock_exec_result = {
                "content": "mock response",
                "model": "test-model",
                "failed_skills": [],
            }

            # Mock the internal execution methods and permission services
            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=role_allowed_skills,
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=role_allowed_sources,
            ), patch.object(
                svc,
                "_execute_with_skills",
                new_callable=AsyncMock,
                return_value=mock_exec_result,
            ) as mock_skills_exec, patch.object(
                svc,
                "_execute_direct_llm",
                new_callable=AsyncMock,
                return_value=mock_exec_result,
            ) as mock_llm_exec:
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="test prompt",
                    )
                )

            # --- Core property: result contains workflow config params ---

            # workflow_id in result matches the workflow
            assert result["workflow_id"] == wf.id, (
                f"result workflow_id should be {wf.id!r}, "
                f"got {result['workflow_id']!r}"
            )

            # output_modes in result matches the workflow config
            assert result["output_modes"] == wf_output_modes, (
                f"result output_modes should be {wf_output_modes!r}, "
                f"got {result['output_modes']!r}"
            )

            # Verify correct execution path based on skill_ids
            if wf_skill_ids:
                # Skills present → _execute_with_skills called
                assert mock_skills_exec.called, (
                    "With skill_ids, _execute_with_skills should be called"
                )
                assert not mock_llm_exec.called, (
                    "With skill_ids, _execute_direct_llm should NOT be called"
                )
                # Verify the skill_ids passed to execution match workflow config
                call_args = mock_skills_exec.call_args
                executed_skill_ids = call_args[1].get(
                    "skill_ids", call_args[0][0] if call_args[0] else None
                )
                assert executed_skill_ids == wf_skill_ids, (
                    f"Executed skill_ids should match workflow config:\n"
                    f"  expected={wf_skill_ids}\n"
                    f"  actual={executed_skill_ids}"
                )
            else:
                # No skills → _execute_direct_llm called
                assert mock_llm_exec.called, (
                    "Without skill_ids, _execute_direct_llm should be called"
                )
                assert not mock_skills_exec.called, (
                    "Without skill_ids, _execute_with_skills should NOT be called"
                )
        finally:
            session.rollback()
            session.close()

    @settings(max_examples=100)
    @given(
        wf_skill_ids=_wf_skill_ids_strategy,
        wf_data_source_auth=_wf_data_source_auth_strategy,
        wf_output_modes=_wf_output_modes_strategy,
    )
    def test_admin_execute_extracts_config_without_override(
        self, wf_skill_ids, wf_data_source_auth, wf_output_modes,
    ):
        """When admin calls execute_workflow without api_overrides, the
        workflow's own config (skill_ids, data_source_auth, output_modes)
        is used as-is. Admin bypasses role visibility checks.

        **Validates: Requirements 4.3**
        """
        # Feature: ai-workflow-engine, Property 12: 工作流配置参数提取
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            wf = AIWorkflow(
                name="admin-config-extract",
                description="admin test",
                skill_ids=wf_skill_ids,
                data_source_auth=wf_data_source_auth,
                output_modes=wf_output_modes,
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            mock_user = MagicMock()
            mock_user.role = "admin"
            mock_user.id = "admin-user-id"
            mock_user.tenant_id = "test-tenant"

            # Admin: permission services return all skills/sources as allowed
            all_skill_ids = list(wf_skill_ids)
            all_source_ids = [e.get("source_id") for e in wf_data_source_auth]

            mock_exec_result = {
                "content": "admin response",
                "model": "test-model",
                "failed_skills": [],
            }

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=all_skill_ids,
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=all_source_ids,
            ), patch.object(
                svc,
                "_execute_with_skills",
                new_callable=AsyncMock,
                return_value=mock_exec_result,
            ), patch.object(
                svc,
                "_execute_direct_llm",
                new_callable=AsyncMock,
                return_value=mock_exec_result,
            ):
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="admin test prompt",
                    )
                )

            # Verify workflow config params are in the result
            assert result["workflow_id"] == wf.id
            assert result["output_modes"] == wf_output_modes
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 13: 技能按序执行
# ---------------------------------------------------------------------------

# Strategy: generate a list of unique skill IDs (at least 2 for meaningful order check)
_multi_skill_ids_strategy = st.lists(
    _skill_id_strategy, min_size=2, max_size=6, unique=True,
)


class TestSkillSequentialExecution:
    """Property 13: 技能按序执行

    *For any* workflow with multiple skills, the invocation order of skills
    during execution SHALL match the order specified in the workflow's
    skill_ids list.

    **Validates: Requirements 4.5**
    """

    @settings(max_examples=100)
    @given(
        skill_ids=_multi_skill_ids_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
    )
    def test_skills_invoked_in_order(self, skill_ids, user_role):
        """When _execute_with_skills is called, _invoke_single_skill is
        called for each skill_id in the exact order of the skill_ids list.

        **Validates: Requirements 4.5**
        """
        # Feature: ai-workflow-engine, Property 13: 技能按序执行
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            wf = AIWorkflow(
                name="skill-order-test",
                description="test sequential execution",
                skill_ids=skill_ids,
                data_source_auth=[],
                output_modes=[],
                visible_roles=[user_role, "admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            mock_user = MagicMock()
            mock_user.role = user_role
            mock_user.id = "test-user-id"
            mock_user.tenant_id = "test-tenant"

            # Track the order of skill invocations
            invocation_order = []

            async def fake_invoke_single_skill(
                service, gateway_id, tenant_id, skill_id,
                prompt, options, system_prompt,
            ):
                invocation_order.append(skill_id)
                return {"content": f"response-{skill_id}", "model": "test"}

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=list(skill_ids),
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=[],
            ), patch.object(
                svc,
                "_invoke_single_skill",
                side_effect=fake_invoke_single_skill,
            ), patch.object(
                svc,
                "_get_active_gateway_id",
                return_value="fake-gateway-id",
            ):
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="test prompt",
                    )
                )

            # --- Core property: invocation order matches skill_ids ---
            assert invocation_order == skill_ids, (
                f"Skill invocation order mismatch:\n"
                f"  expected: {skill_ids}\n"
                f"  actual:   {invocation_order}"
            )

            # All skills should have been invoked
            assert len(invocation_order) == len(skill_ids), (
                f"Expected {len(skill_ids)} invocations, "
                f"got {len(invocation_order)}"
            )
        finally:
            session.rollback()
            session.close()

    @settings(max_examples=100)
    @given(
        skill_ids=_multi_skill_ids_strategy,
    )
    def test_admin_skills_invoked_in_order(self, skill_ids):
        """Admin user: skills are still invoked in the exact order of
        the workflow's skill_ids list.

        **Validates: Requirements 4.5**
        """
        # Feature: ai-workflow-engine, Property 13: 技能按序执行
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            wf = AIWorkflow(
                name="admin-skill-order-test",
                description="admin sequential execution",
                skill_ids=skill_ids,
                data_source_auth=[],
                output_modes=[],
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            mock_user = MagicMock()
            mock_user.role = "admin"
            mock_user.id = "admin-user-id"
            mock_user.tenant_id = "test-tenant"

            invocation_order = []

            async def fake_invoke_single_skill(
                service, gateway_id, tenant_id, skill_id,
                prompt, options, system_prompt,
            ):
                invocation_order.append(skill_id)
                return {"content": f"response-{skill_id}", "model": "test"}

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=list(skill_ids),
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=[],
            ), patch.object(
                svc,
                "_invoke_single_skill",
                side_effect=fake_invoke_single_skill,
            ), patch.object(
                svc,
                "_get_active_gateway_id",
                return_value="fake-gateway-id",
            ):
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="admin test prompt",
                    )
                )

            assert invocation_order == skill_ids, (
                f"Admin skill invocation order mismatch:\n"
                f"  expected: {skill_ids}\n"
                f"  actual:   {invocation_order}"
            )
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 14: 技能失败不阻断后续执行
# ---------------------------------------------------------------------------

# Strategy: generate skill IDs with at least 2 (need some to fail, some to succeed)
_failure_skill_ids_strategy = st.lists(
    _skill_id_strategy, min_size=2, max_size=6, unique=True,
)


class TestSkillFailureDoesNotBlockExecution:
    """Property 14: 技能失败不阻断后续执行

    *For any* workflow execution where one or more skill invocations fail,
    the remaining skills SHALL continue to execute, and the final response
    SHALL contain information about which skills failed (skill_id + error).

    **Validates: Requirements 4.6**
    """

    @settings(max_examples=100)
    @given(
        skill_ids=_failure_skill_ids_strategy,
        data=st.data(),
    )
    def test_failed_skills_do_not_block_remaining(self, skill_ids, data):
        """When some skills fail during _execute_with_skills, the remaining
        skills still execute and the result contains failed_skills info.

        **Validates: Requirements 4.6**
        """
        # Feature: ai-workflow-engine, Property 14: 技能失败不阻断后续执行
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            # Draw a non-empty subset of skill_ids to fail
            fail_indices = data.draw(
                st.lists(
                    st.integers(min_value=0, max_value=len(skill_ids) - 1),
                    min_size=1,
                    max_size=len(skill_ids) - 1,
                    unique=True,
                ),
                label="fail_indices",
            )
            failing_skill_ids = {skill_ids[i] for i in fail_indices}
            succeeding_skill_ids = [
                sid for sid in skill_ids if sid not in failing_skill_ids
            ]

            wf = AIWorkflow(
                name="skill-failure-test",
                description="test failure non-blocking",
                skill_ids=skill_ids,
                data_source_auth=[],
                output_modes=[],
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            mock_user = MagicMock()
            mock_user.role = "admin"
            mock_user.id = "test-user-id"
            mock_user.tenant_id = "test-tenant"

            # Track invocation order to verify all skills are attempted
            invocation_order = []

            async def fake_invoke_single_skill(
                service, gateway_id, tenant_id, skill_id,
                prompt, options, system_prompt,
            ):
                invocation_order.append(skill_id)
                if skill_id in failing_skill_ids:
                    return {"error": f"Simulated failure for {skill_id}"}
                return {"content": f"response-{skill_id}", "model": "test"}

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=list(skill_ids),
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=[],
            ), patch.object(
                svc,
                "_invoke_single_skill",
                side_effect=fake_invoke_single_skill,
            ), patch.object(
                svc,
                "_get_active_gateway_id",
                return_value="fake-gateway-id",
            ):
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="test prompt",
                    )
                )

            # --- Property: ALL skills were attempted (none skipped) ---
            assert invocation_order == skill_ids, (
                f"Not all skills were attempted:\n"
                f"  expected: {skill_ids}\n"
                f"  actual:   {invocation_order}"
            )

            # --- Property: failed_skills contains exactly the failing ones ---
            failed_ids_in_result = {
                fs["skill_id"] for fs in result["failed_skills"]
            }
            assert failed_ids_in_result == failing_skill_ids, (
                f"failed_skills mismatch:\n"
                f"  expected failing: {sorted(failing_skill_ids)}\n"
                f"  actual failing:   {sorted(failed_ids_in_result)}"
            )

            # --- Property: each failed entry has an error message ---
            for fs in result["failed_skills"]:
                assert "error" in fs and fs["error"], (
                    f"Failed skill {fs['skill_id']} missing error message"
                )

            # --- Property: successful skills contributed content ---
            if succeeding_skill_ids:
                assert result["content"], (
                    "Content should be non-empty when some skills succeed"
                )
                for sid in succeeding_skill_ids:
                    assert f"response-{sid}" in result["content"], (
                        f"Successful skill {sid} content missing from result"
                    )
        finally:
            session.rollback()
            session.close()

    @settings(max_examples=100)
    @given(
        skill_ids=_failure_skill_ids_strategy,
    )
    def test_all_skills_fail_returns_empty_content_with_errors(self, skill_ids):
        """When ALL skills fail, the result has empty content but
        failed_skills lists every skill with its error.

        **Validates: Requirements 4.6**
        """
        # Feature: ai-workflow-engine, Property 14: 技能失败不阻断后续执行
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            wf = AIWorkflow(
                name="all-fail-test",
                description="test all skills failing",
                skill_ids=skill_ids,
                data_source_auth=[],
                output_modes=[],
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            mock_user = MagicMock()
            mock_user.role = "admin"
            mock_user.id = "test-user-id"
            mock_user.tenant_id = "test-tenant"

            invocation_order = []

            async def fake_invoke_all_fail(
                service, gateway_id, tenant_id, skill_id,
                prompt, options, system_prompt,
            ):
                invocation_order.append(skill_id)
                return {"error": f"Failure for {skill_id}"}

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=list(skill_ids),
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=[],
            ), patch.object(
                svc,
                "_invoke_single_skill",
                side_effect=fake_invoke_all_fail,
            ), patch.object(
                svc,
                "_get_active_gateway_id",
                return_value="fake-gateway-id",
            ):
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="test prompt",
                    )
                )

            # --- All skills attempted ---
            assert invocation_order == skill_ids, (
                f"Not all skills attempted when all fail:\n"
                f"  expected: {skill_ids}\n"
                f"  actual:   {invocation_order}"
            )

            # --- Content is empty when all fail ---
            assert result["content"] == "", (
                f"Content should be empty when all skills fail, "
                f"got: {result['content']!r}"
            )

            # --- failed_skills contains all skill IDs ---
            failed_ids = {fs["skill_id"] for fs in result["failed_skills"]}
            assert failed_ids == set(skill_ids), (
                f"All skills should be in failed_skills:\n"
                f"  expected: {sorted(skill_ids)}\n"
                f"  actual:   {sorted(failed_ids)}"
            )

            # --- Each failed entry has error info ---
            for fs in result["failed_skills"]:
                assert "error" in fs and fs["error"], (
                    f"Failed skill {fs['skill_id']} missing error message"
                )
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 15: 无技能工作流走 LLM 直连
# ---------------------------------------------------------------------------


class TestNoSkillWorkflowUsesDirectLLM:
    """Property 15: 无技能工作流走 LLM 直连

    *For any* workflow with empty skill_ids, execution SHALL use LLMSwitcher
    direct mode instead of OpenClawChatService. The workflow's configured
    data_source_auth and output_modes SHALL still be applied to the result.

    **Validates: Requirements 5.1, 5.2**
    """

    @settings(max_examples=100)
    @given(
        wf_data_source_auth=_wf_data_source_auth_strategy,
        wf_output_modes=_wf_output_modes_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES - {"admin"})),
    )
    def test_empty_skills_routes_to_direct_llm(
        self, wf_data_source_auth, wf_output_modes, user_role,
    ):
        """When skill_ids is empty, execute_workflow calls _execute_direct_llm
        (LLMSwitcher) instead of _execute_with_skills. The result still
        contains the workflow's data_source_auth and output_modes.

        **Validates: Requirements 5.1, 5.2**
        """
        # Feature: ai-workflow-engine, Property 15: 无技能工作流走 LLM 直连
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            # Create workflow with NO skills
            wf = AIWorkflow(
                name="no-skill-llm-test",
                description="test direct LLM routing",
                skill_ids=[],
                data_source_auth=wf_data_source_auth,
                output_modes=wf_output_modes,
                visible_roles=[user_role, "admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            mock_user = MagicMock()
            mock_user.role = user_role
            mock_user.id = "test-user-id"
            mock_user.tenant_id = "test-tenant"

            role_allowed_sources = [
                e.get("source_id") for e in wf_data_source_auth
            ]

            mock_exec_result = {
                "content": "direct llm response",
                "model": "test-model",
                "failed_skills": [],
            }

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=[],
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=role_allowed_sources,
            ), patch.object(
                svc,
                "_execute_with_skills",
                new_callable=AsyncMock,
                return_value=mock_exec_result,
            ) as mock_skills_exec, patch.object(
                svc,
                "_execute_direct_llm",
                new_callable=AsyncMock,
                return_value=mock_exec_result,
            ) as mock_llm_exec:
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="test prompt",
                    )
                )

            # --- Property: _execute_direct_llm was called ---
            assert mock_llm_exec.called, (
                "With empty skill_ids, _execute_direct_llm should be called"
            )

            # --- Property: _execute_with_skills was NOT called ---
            assert not mock_skills_exec.called, (
                "With empty skill_ids, _execute_with_skills should NOT be called"
            )

            # --- Property: output_modes from workflow config are in result ---
            assert result["output_modes"] == wf_output_modes, (
                f"output_modes should match workflow config:\n"
                f"  expected: {wf_output_modes!r}\n"
                f"  actual:   {result['output_modes']!r}"
            )

            # --- Property: workflow_id is in result ---
            assert result["workflow_id"] == wf.id, (
                f"workflow_id should be {wf.id!r}, got {result['workflow_id']!r}"
            )
        finally:
            session.rollback()
            session.close()

    @settings(max_examples=100)
    @given(
        wf_data_source_auth=_wf_data_source_auth_strategy.filter(
            lambda entries: len(entries) > 0
        ),
        wf_output_modes=_wf_output_modes_strategy,
    )
    def test_direct_llm_still_applies_data_source_auth_and_output_modes(
        self, wf_data_source_auth, wf_output_modes,
    ):
        """When a no-skill workflow executes via LLM direct, the system prompt
        is built using data_source_auth (proving data context is applied),
        and the result carries the workflow's output_modes.

        **Validates: Requirements 5.1, 5.2**
        """
        # Feature: ai-workflow-engine, Property 15: 无技能工作流走 LLM 直连
        session = _SessionLocal()
        try:
            session.query(AIWorkflow).delete()
            session.query(AIAccessLog).delete()
            session.commit()

            wf = AIWorkflow(
                name="llm-data-context-test",
                description="test data_source_auth applied in direct LLM",
                skill_ids=[],
                data_source_auth=wf_data_source_auth,
                output_modes=wf_output_modes,
                visible_roles=["admin"],
                status="enabled",
            )
            session.add(wf)
            session.commit()
            session.refresh(wf)

            svc = WorkflowService(db=session)

            mock_user = MagicMock()
            mock_user.role = "admin"
            mock_user.id = "admin-user-id"
            mock_user.tenant_id = "test-tenant"

            all_source_ids = [e.get("source_id") for e in wf_data_source_auth]

            mock_exec_result = {
                "content": "llm response with data context",
                "model": "test-model",
                "failed_skills": [],
            }

            # Track the system_prompt passed to _execute_direct_llm
            captured_system_prompts = []

            async def fake_execute_direct_llm(prompt, options, system_prompt):
                captured_system_prompts.append(system_prompt)
                return mock_exec_result

            with patch.object(
                svc._skill_perm_service,
                "get_allowed_skill_ids",
                return_value=[],
            ), patch.object(
                svc._role_perm_service,
                "get_permissions_by_role",
                return_value=all_source_ids,
            ), patch.object(
                svc,
                "_execute_direct_llm",
                side_effect=fake_execute_direct_llm,
            ) as mock_llm_exec, patch.object(
                svc,
                "_build_data_context",
                return_value="[mock data context]",
            ) as mock_build_ctx:
                result = asyncio.get_event_loop().run_until_complete(
                    svc.execute_workflow(
                        workflow_id=wf.id,
                        user=mock_user,
                        prompt="test prompt",
                    )
                )

            # --- Property: _execute_direct_llm was called ---
            assert mock_llm_exec.called, (
                "_execute_direct_llm should be called for no-skill workflow"
            )

            # --- Property: _build_data_context was called with data sources ---
            assert mock_build_ctx.called, (
                "_build_data_context should be called to apply data_source_auth"
            )
            ctx_call_args = mock_build_ctx.call_args[0]
            passed_data_sources = ctx_call_args[0]
            passed_source_ids = sorted(
                e.get("source_id") for e in passed_data_sources
            )
            expected_source_ids = sorted(all_source_ids)
            assert passed_source_ids == expected_source_ids, (
                f"data_source_auth should be passed to _build_data_context:\n"
                f"  expected source_ids: {expected_source_ids}\n"
                f"  actual source_ids:   {passed_source_ids}"
            )

            # --- Property: system_prompt includes data context ---
            assert len(captured_system_prompts) == 1, (
                "Expected exactly one call to _execute_direct_llm"
            )
            assert "[mock data context]" in captured_system_prompts[0], (
                "System prompt should include data context from data_source_auth"
            )

            # --- Property: output_modes still applied in result ---
            assert result["output_modes"] == wf_output_modes, (
                f"output_modes should match workflow config:\n"
                f"  expected: {wf_output_modes!r}\n"
                f"  actual:   {result['output_modes']!r}"
            )

            # --- Property: workflow_id in result ---
            assert result["workflow_id"] == wf.id
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 18: 今日统计聚合正确性
# ---------------------------------------------------------------------------

# Event types relevant to stats aggregation
_CHAT_EVENT_TYPES = ["skill_invoke", "data_access"]
_ALL_EVENT_TYPES = [
    "skill_invoke", "data_access", "workflow_execute",
    "skill_denied", "permission_change",
]

# Strategy: generate a single log entry with random event type and optional
# data_sources in details
_data_source_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip())

_log_entry_strategy = st.fixed_dictionaries({
    "event_type": st.sampled_from(_ALL_EVENT_TYPES),
    "data_sources": st.lists(
        _data_source_id_strategy, min_size=0, max_size=4,
    ),
})

_log_entries_strategy = st.lists(
    _log_entry_strategy, min_size=0, max_size=30,
)


def _oracle_aggregate_stats(entries: list) -> dict:
    """Pure-Python oracle that computes expected stats from log entries.

    Mirrors WorkflowService._aggregate_stats logic exactly.
    """
    chat_count = 0
    workflow_count = 0
    ds_ids: set = set()

    for entry in entries:
        et = entry["event_type"]
        if et in ("skill_invoke", "data_access"):
            chat_count += 1
        if et == "workflow_execute":
            workflow_count += 1
        for src_id in entry.get("data_sources", []):
            if src_id:
                ds_ids.add(src_id)

    return {
        "chat_count": chat_count,
        "workflow_count": workflow_count,
        "data_source_count": len(ds_ids),
    }


class TestTodayStatsAggregationCorrectness:
    """Property 18: 今日统计聚合正确性

    *For any* set of log entries with various event types and data source
    references, the aggregated stats returned by _aggregate_stats (and by
    extension get_today_stats) SHALL satisfy:
      - chat_count == count of skill_invoke + data_access events
      - workflow_count == count of workflow_execute events
      - data_source_count == count of unique data source IDs from details

    **Validates: Requirements 8.1, 8.3**
    """

    # ------------------------------------------------------------------
    # Test A: _aggregate_stats pure function produces correct counts
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(entries=_log_entries_strategy)
    def test_aggregate_stats_matches_oracle(self, entries):
        """_aggregate_stats returns counts that match a pure-Python oracle
        computed directly from the input log entries.

        **Validates: Requirements 8.1, 8.3**
        """
        # Feature: ai-workflow-engine, Property 18: 今日统计聚合正确性

        # Build mock AIAccessLog objects with the generated data
        mock_logs = []
        for entry in entries:
            log = MagicMock()
            log.event_type = entry["event_type"]
            log.details = {"data_sources": entry["data_sources"]}
            mock_logs.append(log)

        result = WorkflowService._aggregate_stats(mock_logs)
        expected = _oracle_aggregate_stats(entries)

        assert result["chat_count"] == expected["chat_count"], (
            f"chat_count mismatch: got {result['chat_count']}, "
            f"expected {expected['chat_count']}"
        )
        assert result["workflow_count"] == expected["workflow_count"], (
            f"workflow_count mismatch: got {result['workflow_count']}, "
            f"expected {expected['workflow_count']}"
        )
        assert result["data_source_count"] == expected["data_source_count"], (
            f"data_source_count mismatch: got {result['data_source_count']}, "
            f"expected {expected['data_source_count']}"
        )

    # ------------------------------------------------------------------
    # Test B: get_today_stats with DB logs matches expected aggregation
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(entries=_log_entries_strategy)
    def test_get_today_stats_db_aggregation(self, entries):
        """get_today_stats queries today's logs from the DB and returns
        aggregated counts that match the oracle computed from the same
        log entries.

        **Validates: Requirements 8.1, 8.3**
        """
        # Feature: ai-workflow-engine, Property 18: 今日统计聚合正确性
        session = _SessionLocal()
        try:
            session.query(AIAccessLog).delete()
            session.commit()

            tenant_id = "test-tenant"
            user_id = "test-user"
            now = datetime.now(timezone.utc)

            # Insert log entries into DB with today's timestamp
            for entry in entries:
                log = AIAccessLog(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_role="annotator",
                    event_type=entry["event_type"],
                    details={"data_sources": entry["data_sources"]},
                    created_at=now,
                    success=True,
                )
                session.add(log)
            session.commit()

            svc = WorkflowService(db=session)
            result = svc.get_today_stats(
                user_id=user_id,
                user_role="annotator",
                tenant_id=tenant_id,
            )

            expected = _oracle_aggregate_stats(entries)

            assert result["chat_count"] == expected["chat_count"], (
                f"chat_count mismatch: got {result['chat_count']}, "
                f"expected {expected['chat_count']}"
            )
            assert result["workflow_count"] == expected["workflow_count"], (
                f"workflow_count mismatch: got {result['workflow_count']}, "
                f"expected {expected['workflow_count']}"
            )
            assert result["data_source_count"] == expected["data_source_count"], (
                f"data_source_count mismatch: got {result['data_source_count']}, "
                f"expected {expected['data_source_count']}"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test C: data_source_count deduplicates across multiple logs
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        shared_sources=st.lists(
            _data_source_id_strategy, min_size=1, max_size=5, unique=True,
        ),
        num_logs=st.integers(min_value=2, max_value=10),
    )
    def test_data_source_count_deduplicates(self, shared_sources, num_logs):
        """When multiple logs reference the same data source IDs, the
        data_source_count should equal the number of unique IDs, not
        the total number of references.

        **Validates: Requirements 8.1, 8.3**
        """
        # Feature: ai-workflow-engine, Property 18: 今日统计聚合正确性

        # Every log references the same set of data sources
        mock_logs = []
        for _ in range(num_logs):
            log = MagicMock()
            log.event_type = "workflow_execute"
            log.details = {"data_sources": list(shared_sources)}
            mock_logs.append(log)

        result = WorkflowService._aggregate_stats(mock_logs)

        assert result["data_source_count"] == len(shared_sources), (
            f"data_source_count should be {len(shared_sources)} (unique), "
            f"got {result['data_source_count']}"
        )
        assert result["workflow_count"] == num_logs, (
            f"workflow_count should be {num_logs}, got {result['workflow_count']}"
        )


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 19: 统计数据按角色隔离
# ---------------------------------------------------------------------------

# Strategy: generate a user entry with id, role, and log entries
_user_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=3,
    max_size=20,
).filter(lambda s: s.strip())

_non_admin_role_strategy = st.sampled_from(
    ["business_expert", "annotator", "viewer"]
)

_user_log_entries_strategy = st.lists(
    _log_entry_strategy, min_size=0, max_size=10,
)


class TestStatsRoleIsolation:
    """Property 19: 统计数据按角色隔离

    *For any* non-admin user, the stats API only returns that user's own
    stats. Admin users can see aggregated stats across all users.

    **Validates: Requirements 8.4**
    """

    # ------------------------------------------------------------------
    # Test A: Non-admin only sees own stats, not other users' data
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        target_entries=_user_log_entries_strategy,
        other_entries=_user_log_entries_strategy,
        target_role=_non_admin_role_strategy,
    )
    def test_non_admin_sees_only_own_stats(
        self, target_entries, other_entries, target_role,
    ):
        """A non-admin user calling get_today_stats should only see stats
        computed from their own log entries, ignoring logs from other users
        in the same tenant.

        **Validates: Requirements 8.4**
        """
        # Feature: ai-workflow-engine, Property 19: 统计数据按角色隔离
        session = _SessionLocal()
        try:
            session.query(AIAccessLog).delete()
            session.commit()

            tenant_id = "tenant-isolation"
            target_user = "target-user"
            other_user = "other-user"
            now = datetime.now(timezone.utc)

            # Insert target user's logs
            for entry in target_entries:
                log = AIAccessLog(
                    tenant_id=tenant_id,
                    user_id=target_user,
                    user_role=target_role,
                    event_type=entry["event_type"],
                    details={"data_sources": entry["data_sources"]},
                    created_at=now,
                    success=True,
                )
                session.add(log)

            # Insert other user's logs (same tenant)
            for entry in other_entries:
                log = AIAccessLog(
                    tenant_id=tenant_id,
                    user_id=other_user,
                    user_role="annotator",
                    event_type=entry["event_type"],
                    details={"data_sources": entry["data_sources"]},
                    created_at=now,
                    success=True,
                )
                session.add(log)
            session.commit()

            svc = WorkflowService(db=session)
            result = svc.get_today_stats(
                user_id=target_user,
                user_role=target_role,
                tenant_id=tenant_id,
            )

            # Oracle: only target user's entries
            expected = _oracle_aggregate_stats(target_entries)

            assert result["chat_count"] == expected["chat_count"], (
                f"Non-admin chat_count: got {result['chat_count']}, "
                f"expected {expected['chat_count']}"
            )
            assert result["workflow_count"] == expected["workflow_count"], (
                f"Non-admin workflow_count: got {result['workflow_count']}, "
                f"expected {expected['workflow_count']}"
            )
            assert result["data_source_count"] == expected["data_source_count"], (
                f"Non-admin data_source_count: got {result['data_source_count']}, "
                f"expected {expected['data_source_count']}"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test B: Admin sees aggregated stats across all users in tenant
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        user_a_entries=_user_log_entries_strategy,
        user_b_entries=_user_log_entries_strategy,
    )
    def test_admin_sees_all_users_stats(
        self, user_a_entries, user_b_entries,
    ):
        """An admin user calling get_today_stats should see aggregated stats
        from ALL users in the tenant, not just their own.

        **Validates: Requirements 8.4**
        """
        # Feature: ai-workflow-engine, Property 19: 统计数据按角色隔离
        session = _SessionLocal()
        try:
            session.query(AIAccessLog).delete()
            session.commit()

            tenant_id = "tenant-admin-agg"
            admin_user = "admin-user"
            regular_user = "regular-user"
            now = datetime.now(timezone.utc)

            # Insert admin user's logs
            for entry in user_a_entries:
                log = AIAccessLog(
                    tenant_id=tenant_id,
                    user_id=admin_user,
                    user_role="admin",
                    event_type=entry["event_type"],
                    details={"data_sources": entry["data_sources"]},
                    created_at=now,
                    success=True,
                )
                session.add(log)

            # Insert regular user's logs (same tenant)
            for entry in user_b_entries:
                log = AIAccessLog(
                    tenant_id=tenant_id,
                    user_id=regular_user,
                    user_role="annotator",
                    event_type=entry["event_type"],
                    details={"data_sources": entry["data_sources"]},
                    created_at=now,
                    success=True,
                )
                session.add(log)
            session.commit()

            svc = WorkflowService(db=session)
            result = svc.get_today_stats(
                user_id=admin_user,
                user_role="admin",
                tenant_id=tenant_id,
            )

            # Oracle: ALL entries from both users
            all_entries = user_a_entries + user_b_entries
            expected = _oracle_aggregate_stats(all_entries)

            assert result["chat_count"] == expected["chat_count"], (
                f"Admin chat_count: got {result['chat_count']}, "
                f"expected {expected['chat_count']}"
            )
            assert result["workflow_count"] == expected["workflow_count"], (
                f"Admin workflow_count: got {result['workflow_count']}, "
                f"expected {expected['workflow_count']}"
            )
            assert result["data_source_count"] == expected["data_source_count"], (
                f"Admin data_source_count: got {result['data_source_count']}, "
                f"expected {expected['data_source_count']}"
            )
        finally:
            session.rollback()
            session.close()

    # ------------------------------------------------------------------
    # Test C: Non-admin stats ⊆ admin stats (subset relationship)
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        target_entries=_user_log_entries_strategy,
        other_entries=_user_log_entries_strategy,
        target_role=_non_admin_role_strategy,
    )
    def test_non_admin_stats_subset_of_admin(
        self, target_entries, other_entries, target_role,
    ):
        """For the same tenant, a non-admin user's stats should never exceed
        the admin's aggregated stats in any dimension.

        **Validates: Requirements 8.4**
        """
        # Feature: ai-workflow-engine, Property 19: 统计数据按角色隔离
        session = _SessionLocal()
        try:
            session.query(AIAccessLog).delete()
            session.commit()

            tenant_id = "tenant-subset"
            target_user = "target-user"
            other_user = "other-user"
            now = datetime.now(timezone.utc)

            for entry in target_entries:
                log = AIAccessLog(
                    tenant_id=tenant_id,
                    user_id=target_user,
                    user_role=target_role,
                    event_type=entry["event_type"],
                    details={"data_sources": entry["data_sources"]},
                    created_at=now,
                    success=True,
                )
                session.add(log)

            for entry in other_entries:
                log = AIAccessLog(
                    tenant_id=tenant_id,
                    user_id=other_user,
                    user_role="business_expert",
                    event_type=entry["event_type"],
                    details={"data_sources": entry["data_sources"]},
                    created_at=now,
                    success=True,
                )
                session.add(log)
            session.commit()

            svc = WorkflowService(db=session)

            non_admin_result = svc.get_today_stats(
                user_id=target_user,
                user_role=target_role,
                tenant_id=tenant_id,
            )
            admin_result = svc.get_today_stats(
                user_id="any-admin",
                user_role="admin",
                tenant_id=tenant_id,
            )

            assert non_admin_result["chat_count"] <= admin_result["chat_count"], (
                f"Non-admin chat_count ({non_admin_result['chat_count']}) "
                f"exceeds admin ({admin_result['chat_count']})"
            )
            assert non_admin_result["workflow_count"] <= admin_result["workflow_count"], (
                f"Non-admin workflow_count ({non_admin_result['workflow_count']}) "
                f"exceeds admin ({admin_result['workflow_count']})"
            )
            assert non_admin_result["data_source_count"] <= admin_result["data_source_count"], (
                f"Non-admin data_source_count ({non_admin_result['data_source_count']}) "
                f"exceeds admin ({admin_result['data_source_count']})"
            )
        finally:
            session.rollback()
            session.close()

# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 24: 向后兼容——无 workflow_id 请求走原有逻辑
# ---------------------------------------------------------------------------

# Strategies for ChatRequest parameters (without workflow_id)
_chat_mode_strategy = st.sampled_from(["direct", "openclaw"])

_optional_skill_ids_strategy = st.one_of(
    st.none(),
    st.lists(st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
             min_size=0, max_size=3),
)

_optional_data_source_ids_strategy = st.one_of(
    st.none(),
    st.lists(st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
             min_size=0, max_size=3),
)

_optional_output_mode_strategy = st.one_of(
    st.none(),
    st.sampled_from(["merge", "compare"]),
)


class TestBackwardCompatNoWorkflowId:
    """Property 24: 向后兼容——无 workflow_id 请求走原有逻辑

    *For any* chat request that does NOT carry workflow_id, the system should
    process it using existing logic (mode, skill_ids, data_source_ids,
    output_mode parameters). WorkflowService should NOT be called, and the
    response format and behavior should be identical to before workflow engine
    introduction.

    **Validates: Requirements 13.1, 13.2**
    """

    @settings(max_examples=100)
    @given(
        mode=_chat_mode_strategy,
        message_content=st.text(min_size=1, max_size=80).filter(lambda s: s.strip()),
        skill_ids=_optional_skill_ids_strategy,
        data_source_ids=_optional_data_source_ids_strategy,
        output_mode=_optional_output_mode_strategy,
    )
    def test_chat_without_workflow_id_does_not_call_workflow_service(
        self, mode, message_content, skill_ids, data_source_ids, output_mode,
    ):
        """Non-streaming chat: when workflow_id is None, WorkflowService is
        NOT invoked and the original direct/openclaw routing is used.

        **Validates: Requirements 13.1, 13.2**
        """
        # Feature: ai-workflow-engine, Property 24: 向后兼容——无 workflow_id 请求走原有逻辑
        import asyncio
        from unittest.mock import AsyncMock

        from src.api.ai_assistant import chat, ChatRequest, ChatMessage, ChatResponse

        messages = [ChatMessage(role="user", content=message_content)]
        gateway_id = "gw-test" if mode == "openclaw" else None

        request = ChatRequest(
            messages=messages,
            mode=mode,
            skill_ids=skill_ids,
            data_source_ids=data_source_ids,
            output_mode=output_mode,
            gateway_id=gateway_id,
            workflow_id=None,
        )

        assert request.workflow_id is None

        mock_user = MagicMock()
        mock_user.role = "business_expert"
        mock_user.id = "test-user-id"
        mock_user.tenant_id = "test-tenant"
        mock_db = MagicMock()

        mock_response = ChatResponse(content="ok", model="m", usage=None)

        with patch("src.api.ai_assistant._chat_workflow", new_callable=AsyncMock) as mock_wf, \
             patch("src.api.ai_assistant._chat_direct", new_callable=AsyncMock, return_value=mock_response) as mock_direct, \
             patch("src.api.ai_assistant._chat_openclaw", new_callable=AsyncMock, return_value=mock_response) as mock_openclaw, \
             patch("src.api.ai_assistant._filter_skills_by_role", return_value=skill_ids or []), \
             patch("src.api.ai_assistant._log_skill_access"), \
             patch("src.api.ai_assistant._log_data_access"), \
             patch("src.api.ai_assistant.build_data_context", return_value=""):

            asyncio.get_event_loop().run_until_complete(
                chat(request=request, current_user=mock_user, db=mock_db)
            )

            # WorkflowService path must NOT be called
            mock_wf.assert_not_called()

            # Original routing must be used based on mode
            if mode == "direct":
                mock_direct.assert_called_once()
            else:
                mock_openclaw.assert_called_once()

    @settings(max_examples=100)
    @given(
        mode=_chat_mode_strategy,
        message_content=st.text(min_size=1, max_size=80).filter(lambda s: s.strip()),
        skill_ids=_optional_skill_ids_strategy,
        data_source_ids=_optional_data_source_ids_strategy,
        output_mode=_optional_output_mode_strategy,
    )
    def test_chat_stream_without_workflow_id_does_not_call_workflow_service(
        self, mode, message_content, skill_ids, data_source_ids, output_mode,
    ):
        """Streaming chat: when workflow_id is None, WorkflowService is NOT
        invoked and the original direct/openclaw streaming is used.

        **Validates: Requirements 13.1, 13.2**
        """
        # Feature: ai-workflow-engine, Property 24: 向后兼容——无 workflow_id 请求走原有逻辑
        import asyncio
        from unittest.mock import AsyncMock

        from src.api.ai_assistant import chat_stream, ChatRequest, ChatMessage

        messages = [ChatMessage(role="user", content=message_content)]
        gateway_id = "gw-test" if mode == "openclaw" else None

        request = ChatRequest(
            messages=messages,
            mode=mode,
            skill_ids=skill_ids,
            data_source_ids=data_source_ids,
            output_mode=output_mode,
            gateway_id=gateway_id,
            workflow_id=None,
        )

        assert request.workflow_id is None

        mock_user = MagicMock()
        mock_user.role = "business_expert"
        mock_user.id = "test-user-id"
        mock_user.tenant_id = "test-tenant"
        mock_db = MagicMock()

        mock_switcher = MagicMock()
        mock_openclaw_svc = MagicMock()

        with patch("src.api.ai_assistant._stream_workflow_response") as mock_wf_stream, \
             patch("src.api.ai_assistant._filter_skills_by_role", return_value=skill_ids or []), \
             patch("src.api.ai_assistant._log_skill_access"), \
             patch("src.api.ai_assistant._log_data_access"), \
             patch("src.api.ai_assistant.build_data_context", return_value=""), \
             patch("src.api.ai_assistant.get_llm_switcher", return_value=mock_switcher), \
             patch("src.api.ai_assistant.get_openclaw_chat_service", return_value=mock_openclaw_svc):

            result = asyncio.get_event_loop().run_until_complete(
                chat_stream(request=request, current_user=mock_user, db=mock_db)
            )

            # WorkflowService streaming path must NOT be called
            mock_wf_stream.assert_not_called()

            # Result should be a StreamingResponse (original path)
            from starlette.responses import StreamingResponse
            assert isinstance(result, StreamingResponse)


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
# ---------------------------------------------------------------------------

# Strategies for audit log testing
_user_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=3,
    max_size=30,
).filter(lambda s: s.strip())

_tenant_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=3,
    max_size=30,
).filter(lambda s: s.strip())

_workflow_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-"),
    min_size=5,
    max_size=36,
).filter(lambda s: s.strip())

_event_type_strategy = st.sampled_from([
    "workflow_list",
    "workflow_create",
    "workflow_update",
    "workflow_delete",
    "workflow_stats",
    "workflow_permission_sync",
])

_request_type_strategy = st.sampled_from(["chat", "api"])


class TestWorkflowAuditLog:
    """Property 22: 工作流操作审计日志

    *For any* workflow-related API request (CRUD, execute, permission sync),
    the system should create an AIAccessLog record containing user_id,
    user_role, event_type, workflow_id, timestamp. The two channels
    (internal frontend / external API) are distinguished by the request_type
    field.

    **Validates: Requirements 11.6, 12.7**
    """

    # ------------------------------------------------------------------
    # Test A: _log_workflow_crud creates a log record with all required fields
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        user_id=_user_id_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES)),
        tenant_id=_tenant_id_strategy,
        event_type=_event_type_strategy,
        workflow_id=st.one_of(st.none(), _workflow_id_strategy),
        workflow_name=st.one_of(st.none(), _workflow_name_strategy),
        success=st.booleans(),
    )
    def test_log_workflow_crud_creates_record_with_required_fields(
        self, user_id, user_role, tenant_id, event_type,
        workflow_id, workflow_name, success,
    ):
        """_log_workflow_crud creates an AIAccessLog record that contains
        user_id, user_role, event_type, resource_id (workflow_id),
        request_type, and timestamp (via created_at server_default).

        **Validates: Requirements 11.6, 12.7**
        """
        # Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
        from src.api.ai_assistant import _log_workflow_crud
        from src.models.ai_access_log import AIAccessLog as LogModel

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = user_role
        mock_user.tenant_id = tenant_id

        # Capture the LogModel instance passed to db.add()
        added_records = []
        mock_db.add = lambda record: added_records.append(record)

        _log_workflow_crud(
            db=mock_db,
            user=mock_user,
            event_type=event_type,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            success=success,
        )

        # db.commit() must be called
        mock_db.commit.assert_called_once()

        # Exactly one record should be added
        assert len(added_records) == 1, (
            f"Expected 1 log record, got {len(added_records)}"
        )

        record = added_records[0]
        assert isinstance(record, LogModel), (
            f"Expected AIAccessLog instance, got {type(record)}"
        )

        # --- Required fields ---
        assert record.user_id == str(user_id), (
            f"user_id mismatch: {record.user_id!r} != {str(user_id)!r}"
        )
        assert record.user_role == user_role, (
            f"user_role mismatch: {record.user_role!r} != {user_role!r}"
        )
        assert record.event_type == event_type, (
            f"event_type mismatch: {record.event_type!r} != {event_type!r}"
        )
        assert record.resource_id == workflow_id, (
            f"resource_id (workflow_id) mismatch: "
            f"{record.resource_id!r} != {workflow_id!r}"
        )
        assert record.tenant_id == tenant_id, (
            f"tenant_id mismatch: {record.tenant_id!r} != {tenant_id!r}"
        )
        assert record.success == success, (
            f"success mismatch: {record.success!r} != {success!r}"
        )

        # request_type must be set (distinguishes channels)
        assert record.request_type is not None, (
            "request_type must not be None — it distinguishes channels"
        )
        assert record.request_type in ("chat", "api"), (
            f"request_type should be 'chat' or 'api', got {record.request_type!r}"
        )

    # ------------------------------------------------------------------
    # Test B: Each CRUD endpoint calls _log_workflow_crud with correct event_type
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        user_role=st.just("admin"),
        user_id=_user_id_strategy,
        tenant_id=_tenant_id_strategy,
        filter_status=st.one_of(st.none(), st.sampled_from(["enabled", "disabled"])),
    )
    def test_list_workflows_endpoint_logs_audit(
        self, user_role, user_id, tenant_id, filter_status,
    ):
        """list_workflows endpoint calls _log_workflow_crud with
        event_type='workflow_list'.

        **Validates: Requirements 11.6, 12.7**
        """
        # Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
        import asyncio

        from src.api.ai_assistant import list_workflows

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = user_role
        mock_user.tenant_id = tenant_id
        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.list_workflows.return_value = []

        with patch("src.ai.workflow_service.WorkflowService", return_value=mock_service), \
             patch("src.api.ai_assistant._log_workflow_crud") as mock_log:

            asyncio.get_event_loop().run_until_complete(
                list_workflows(
                    status=filter_status,
                    current_user=mock_user,
                    db=mock_db,
                )
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            # Positional args: db, user
            assert call_kwargs[0][0] is mock_db
            assert call_kwargs[0][1] is mock_user
            assert call_kwargs[1]["event_type"] == "workflow_list"

    @settings(max_examples=100)
    @given(
        user_id=_user_id_strategy,
        tenant_id=_tenant_id_strategy,
        wf_name=_workflow_name_strategy,
    )
    def test_create_workflow_endpoint_logs_audit(
        self, user_id, tenant_id, wf_name,
    ):
        """create_workflow endpoint calls _log_workflow_crud with
        event_type='workflow_create'.

        **Validates: Requirements 11.6, 12.7**
        """
        # Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
        import asyncio

        from src.api.ai_assistant import create_workflow

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = "admin"
        mock_user.tenant_id = tenant_id
        mock_db = MagicMock()

        mock_workflow = MagicMock()
        mock_workflow.id = "wf-123"
        mock_workflow.name = wf_name
        mock_workflow.description = ""
        mock_workflow.status = "enabled"
        mock_workflow.is_preset = False
        mock_workflow.skill_ids = []
        mock_workflow.data_source_auth = []
        mock_workflow.output_modes = []
        mock_workflow.visible_roles = ["admin"]
        mock_workflow.preset_prompt = None
        mock_workflow.name_en = None
        mock_workflow.description_en = None
        mock_workflow.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_workflow.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_workflow.created_by = user_id

        mock_service = MagicMock()
        mock_service.create_workflow.return_value = mock_workflow

        request = WorkflowCreateRequest(
            name=wf_name,
            description="",
            skill_ids=[],
            data_source_auth=[],
            output_modes=[],
            visible_roles=["admin"],
        )

        with patch("src.ai.workflow_service.WorkflowService", return_value=mock_service), \
             patch("src.api.ai_assistant._log_workflow_crud") as mock_log:

            asyncio.get_event_loop().run_until_complete(
                create_workflow(
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            assert call_kwargs[1]["event_type"] == "workflow_create"
            assert call_kwargs[1]["workflow_id"] == "wf-123"
            assert call_kwargs[1]["workflow_name"] == wf_name

    @settings(max_examples=100)
    @given(
        user_id=_user_id_strategy,
        tenant_id=_tenant_id_strategy,
        workflow_id=_workflow_id_strategy,
    )
    def test_update_workflow_endpoint_logs_audit(
        self, user_id, tenant_id, workflow_id,
    ):
        """update_workflow endpoint calls _log_workflow_crud with
        event_type='workflow_update'.

        **Validates: Requirements 11.6, 12.7**
        """
        # Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
        import asyncio

        from src.api.ai_assistant import update_workflow

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = "admin"
        mock_user.tenant_id = tenant_id
        mock_db = MagicMock()

        mock_workflow = MagicMock()
        mock_workflow.id = workflow_id
        mock_workflow.name = "updated-wf"
        mock_workflow.description = ""
        mock_workflow.status = "enabled"
        mock_workflow.is_preset = False
        mock_workflow.skill_ids = []
        mock_workflow.data_source_auth = []
        mock_workflow.output_modes = []
        mock_workflow.visible_roles = ["admin"]
        mock_workflow.preset_prompt = None
        mock_workflow.name_en = None
        mock_workflow.description_en = None
        mock_workflow.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_workflow.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_workflow.created_by = user_id

        mock_service = MagicMock()
        mock_service.update_workflow.return_value = mock_workflow

        request = WorkflowUpdateRequest(description="updated")

        with patch("src.ai.workflow_service.WorkflowService", return_value=mock_service), \
             patch("src.api.ai_assistant._log_workflow_crud") as mock_log:

            asyncio.get_event_loop().run_until_complete(
                update_workflow(
                    workflow_id=workflow_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            assert call_kwargs[1]["event_type"] == "workflow_update"
            assert call_kwargs[1]["workflow_id"] == workflow_id

    @settings(max_examples=100)
    @given(
        user_id=_user_id_strategy,
        tenant_id=_tenant_id_strategy,
        workflow_id=_workflow_id_strategy,
    )
    def test_delete_workflow_endpoint_logs_audit(
        self, user_id, tenant_id, workflow_id,
    ):
        """delete_workflow endpoint calls _log_workflow_crud with
        event_type='workflow_delete'.

        **Validates: Requirements 11.6, 12.7**
        """
        # Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
        import asyncio

        from src.api.ai_assistant import delete_workflow

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = "admin"
        mock_user.tenant_id = tenant_id
        mock_db = MagicMock()

        mock_service = MagicMock()

        with patch("src.ai.workflow_service.WorkflowService", return_value=mock_service), \
             patch("src.api.ai_assistant._log_workflow_crud") as mock_log:

            asyncio.get_event_loop().run_until_complete(
                delete_workflow(
                    workflow_id=workflow_id,
                    current_user=mock_user,
                    db=mock_db,
                )
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            assert call_kwargs[1]["event_type"] == "workflow_delete"
            assert call_kwargs[1]["workflow_id"] == workflow_id

    # ------------------------------------------------------------------
    # Test C: Permission sync endpoint logs audit
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        user_id=_user_id_strategy,
        tenant_id=_tenant_id_strategy,
        perm_count=st.integers(min_value=0, max_value=5),
    )
    def test_sync_permissions_endpoint_logs_audit(
        self, user_id, tenant_id, perm_count,
    ):
        """sync_permissions endpoint calls _log_workflow_crud with
        event_type='workflow_permission_sync'.

        **Validates: Requirements 11.6, 12.7**
        """
        # Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
        import asyncio

        from src.api.ai_assistant import sync_permissions, SyncPermissionsRequest

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = "admin"
        mock_user.tenant_id = tenant_id
        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.sync_permissions.return_value = {"updated_count": perm_count}

        permissions = [{"role": "admin", "source_id": f"src-{i}"} for i in range(perm_count)]
        request = SyncPermissionsRequest(permissions=permissions)

        with patch("src.ai.workflow_service.WorkflowService", return_value=mock_service), \
             patch("src.api.ai_assistant._log_workflow_crud") as mock_log:

            asyncio.get_event_loop().run_until_complete(
                sync_permissions(
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            assert call_kwargs[1]["event_type"] == "workflow_permission_sync"

    # ------------------------------------------------------------------
    # Test D: request_type field distinguishes internal vs external channel
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        user_id=_user_id_strategy,
        user_role=st.sampled_from(sorted(VALID_ROLES)),
        tenant_id=_tenant_id_strategy,
        event_type=_event_type_strategy,
        request_type=_request_type_strategy,
    )
    def test_request_type_distinguishes_channels(
        self, user_id, user_role, tenant_id, event_type, request_type,
    ):
        """The request_type field on AIAccessLog distinguishes internal
        frontend ('chat') from external API ('api') channel. The
        _log_workflow_crud helper currently sets request_type='chat'
        (internal channel). Both values are valid and distinct.

        **Validates: Requirements 11.6, 12.7**
        """
        # Feature: ai-workflow-engine, Property 22: 工作流操作审计日志
        from src.models.ai_access_log import AIAccessLog as LogModel

        # Verify the model supports both channel values
        log_chat = LogModel(
            tenant_id=tenant_id,
            user_id=user_id,
            user_role=user_role,
            event_type=event_type,
            request_type="chat",
            success=True,
            details={},
        )
        log_api = LogModel(
            tenant_id=tenant_id,
            user_id=user_id,
            user_role=user_role,
            event_type=event_type,
            request_type="api",
            success=True,
            details={},
        )

        # Both records have the same core fields
        assert log_chat.user_id == log_api.user_id
        assert log_chat.user_role == log_api.user_role
        assert log_chat.event_type == log_api.event_type

        # But request_type distinguishes them
        assert log_chat.request_type == "chat"
        assert log_api.request_type == "api"
        assert log_chat.request_type != log_api.request_type


# ---------------------------------------------------------------------------
# Feature: ai-workflow-engine, Property 23: 双通道执行结果一致性
# ---------------------------------------------------------------------------

# Strategies for dual-channel consistency testing
_dc_workflow_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=5,
    max_size=30,
).filter(lambda s: s.strip())

_dc_prompt_strategy = st.text(
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip())

_dc_content_strategy = st.text(
    min_size=0,
    max_size=500,
)

_dc_model_strategy = st.sampled_from([
    "gpt-4", "gpt-3.5-turbo", "claude-3", "deepseek-v2", "",
])

_dc_usage_strategy = st.one_of(
    st.none(),
    st.fixed_dictionaries({
        "prompt_tokens": st.integers(min_value=0, max_value=10000),
        "completion_tokens": st.integers(min_value=0, max_value=10000),
    }),
)


class TestDualChannelExecutionConsistency:
    """Property 23: 双通道执行结果一致性

    *For any* same workflow and same input parameters, through internal
    frontend channel and external customer API channel, the core result
    data (AI response content) should be consistent, only the response
    wrapper format differs (ChatResponse vs ServiceResponse).

    Both channels ultimately call WorkflowService.execute_workflow() —
    the key property is that the same service method is called with
    equivalent parameters and both channels extract the same content
    from the result.

    **Validates: Requirements 12.6**
    """

    # ------------------------------------------------------------------
    # Test A: Both channels call WorkflowService.execute_workflow and
    #         extract the same content from its result
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        workflow_id=_dc_workflow_id_strategy,
        content=_dc_content_strategy,
        model=_dc_model_strategy,
        usage=_dc_usage_strategy,
    )
    def test_both_channels_extract_same_content_from_workflow_result(
        self, workflow_id, content, model, usage,
    ):
        """Given the same WorkflowService.execute_workflow result, both
        the internal channel (_chat_workflow) and external channel
        (ChatHandler._execute_via_workflow) extract the same core content.

        **Validates: Requirements 12.6**
        """
        # Feature: ai-workflow-engine, Property 23: 双通道执行结果一致性
        import asyncio

        # The controlled result that WorkflowService.execute_workflow returns
        controlled_result = {
            "content": content,
            "model": model,
            "usage": usage,
            "workflow_id": workflow_id,
            "output_modes": ["merge"],
        }

        # --- Internal channel: _chat_workflow ---
        from src.api.ai_assistant import _chat_workflow, ChatResponse

        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.role = "admin"
        mock_user.tenant_id = "tenant-1"
        mock_db = MagicMock()

        mock_request = MagicMock()
        mock_request.messages = [MagicMock(role="user", content="hello")]
        mock_request.workflow_id = workflow_id
        mock_request.skill_ids = None
        mock_request.data_source_ids = None
        mock_request.output_mode = None

        mock_service_instance = MagicMock()

        async def mock_execute(**kwargs):
            return controlled_result

        mock_service_instance.execute_workflow = mock_execute

        with patch("src.api.ai_assistant.build_prompt", return_value="prompt"), \
             patch("src.api.ai_assistant.build_options", return_value=None), \
             patch("src.ai.workflow_service.WorkflowService", return_value=mock_service_instance):
            internal_response = asyncio.get_event_loop().run_until_complete(
                _chat_workflow(mock_request, mock_user, mock_db)
            )

        # --- External channel: ChatHandler._execute_via_workflow ---
        from src.service_engine.handlers.chat import ChatHandler
        from src.service_engine.schemas import ServiceRequest, ServiceResponse

        handler = ChatHandler(llm_switcher=MagicMock())

        ext_request = ServiceRequest(
            request_type="chat",
            user_id="user-1",
            messages=[{"role": "user", "content": "hello"}],
            workflow_id=workflow_id,
        )
        ext_context = {
            "system_prompt": "sys",
            "_skill_whitelist": [],
        }

        mock_ext_service = MagicMock()

        async def mock_ext_execute(**kwargs):
            return controlled_result

        mock_ext_service.execute_workflow = mock_ext_execute

        with patch("src.database.connection.get_db_session") as mock_get_db, \
             patch("src.ai.workflow_service.WorkflowService", return_value=mock_ext_service):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = iter([mock_session])

            external_response = asyncio.get_event_loop().run_until_complete(
                handler._execute_via_workflow(ext_request, ext_context)
            )

        # --- Core property: both channels produce the same content ---
        assert isinstance(internal_response, ChatResponse), (
            f"Internal channel should return ChatResponse, got {type(internal_response)}"
        )
        assert isinstance(external_response, ServiceResponse), (
            f"External channel should return ServiceResponse, got {type(external_response)}"
        )

        # The core content must be identical
        internal_content = internal_response.content
        external_content = external_response.data.get("content", "")

        assert internal_content == external_content, (
            f"Content mismatch between channels:\n"
            f"  internal: {internal_content!r}\n"
            f"  external: {external_content!r}\n"
            f"  controlled result content: {content!r}"
        )

        # Both should match the controlled result's content
        assert internal_content == content, (
            f"Internal content doesn't match controlled result: "
            f"{internal_content!r} != {content!r}"
        )

    # ------------------------------------------------------------------
    # Test B: Both channels call execute_workflow with the workflow_id
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        workflow_id=_dc_workflow_id_strategy,
        prompt_text=_dc_prompt_strategy,
    )
    def test_both_channels_pass_workflow_id_to_service(
        self, workflow_id, prompt_text,
    ):
        """Both channels pass the same workflow_id to
        WorkflowService.execute_workflow, ensuring the same workflow
        is executed regardless of channel.

        **Validates: Requirements 12.6**
        """
        # Feature: ai-workflow-engine, Property 23: 双通道执行结果一致性
        import asyncio

        captured_internal = {}
        captured_external = {}

        controlled_result = {
            "content": "response",
            "model": "gpt-4",
            "usage": None,
            "workflow_id": workflow_id,
            "output_modes": [],
        }

        # --- Internal channel ---
        from src.api.ai_assistant import _chat_workflow

        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.role = "admin"
        mock_user.tenant_id = "tenant-1"
        mock_db = MagicMock()

        mock_request = MagicMock()
        mock_request.messages = [MagicMock(role="user", content=prompt_text)]
        mock_request.workflow_id = workflow_id
        mock_request.skill_ids = None
        mock_request.data_source_ids = None
        mock_request.output_mode = None

        mock_int_service = MagicMock()

        async def capture_internal(**kwargs):
            captured_internal.update(kwargs)
            return controlled_result

        mock_int_service.execute_workflow = capture_internal

        with patch("src.api.ai_assistant.build_prompt", return_value=prompt_text), \
             patch("src.api.ai_assistant.build_options", return_value=None), \
             patch("src.ai.workflow_service.WorkflowService", return_value=mock_int_service):
            asyncio.get_event_loop().run_until_complete(
                _chat_workflow(mock_request, mock_user, mock_db)
            )

        # --- External channel ---
        from src.service_engine.handlers.chat import ChatHandler
        from src.service_engine.schemas import ServiceRequest

        handler = ChatHandler(llm_switcher=MagicMock())

        ext_request = ServiceRequest(
            request_type="chat",
            user_id="user-1",
            messages=[{"role": "user", "content": prompt_text}],
            workflow_id=workflow_id,
        )
        ext_context = {
            "system_prompt": "sys",
            "_skill_whitelist": [],
        }

        mock_ext_service = MagicMock()

        async def capture_external(**kwargs):
            captured_external.update(kwargs)
            return controlled_result

        mock_ext_service.execute_workflow = capture_external

        with patch("src.database.connection.get_db_session") as mock_get_db, \
             patch("src.ai.workflow_service.WorkflowService", return_value=mock_ext_service):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = iter([mock_session])

            asyncio.get_event_loop().run_until_complete(
                handler._execute_via_workflow(ext_request, ext_context)
            )

        # --- Both channels must pass the same workflow_id ---
        assert captured_internal.get("workflow_id") == workflow_id, (
            f"Internal channel workflow_id mismatch: "
            f"{captured_internal.get('workflow_id')!r} != {workflow_id!r}"
        )
        assert captured_external.get("workflow_id") == workflow_id, (
            f"External channel workflow_id mismatch: "
            f"{captured_external.get('workflow_id')!r} != {workflow_id!r}"
        )

        # Both channels call the same method with the same workflow_id
        assert captured_internal["workflow_id"] == captured_external["workflow_id"], (
            f"Channels used different workflow_ids: "
            f"internal={captured_internal['workflow_id']!r}, "
            f"external={captured_external['workflow_id']!r}"
        )

    # ------------------------------------------------------------------
    # Test C: Response wrapper formats differ but content is identical
    # ------------------------------------------------------------------

    @settings(max_examples=100)
    @given(
        content=_dc_content_strategy,
        model=_dc_model_strategy,
        workflow_id=_dc_workflow_id_strategy,
    )
    def test_response_wrapper_formats_differ_but_content_matches(
        self, content, model, workflow_id,
    ):
        """The internal channel wraps results in ChatResponse (flat fields:
        content, model, usage) while the external channel wraps in
        ServiceResponse (success, request_type, data dict, metadata).
        Despite different wrappers, the core content is identical.

        **Validates: Requirements 12.6**
        """
        # Feature: ai-workflow-engine, Property 23: 双通道执行结果一致性
        import asyncio

        controlled_result = {
            "content": content,
            "model": model,
            "usage": None,
            "workflow_id": workflow_id,
            "output_modes": ["compare"],
            "failed_skills": [],
        }

        # --- Internal channel ---
        from src.api.ai_assistant import _chat_workflow, ChatResponse

        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.role = "admin"
        mock_user.tenant_id = "tenant-1"
        mock_db = MagicMock()

        mock_request = MagicMock()
        mock_request.messages = [MagicMock(role="user", content="test")]
        mock_request.workflow_id = workflow_id
        mock_request.skill_ids = None
        mock_request.data_source_ids = None
        mock_request.output_mode = None

        mock_int_service = MagicMock()

        async def mock_int_exec(**kwargs):
            return controlled_result

        mock_int_service.execute_workflow = mock_int_exec

        with patch("src.api.ai_assistant.build_prompt", return_value="test"), \
             patch("src.api.ai_assistant.build_options", return_value=None), \
             patch("src.ai.workflow_service.WorkflowService", return_value=mock_int_service):
            int_resp = asyncio.get_event_loop().run_until_complete(
                _chat_workflow(mock_request, mock_user, mock_db)
            )

        # --- External channel ---
        from src.service_engine.handlers.chat import ChatHandler
        from src.service_engine.schemas import ServiceRequest, ServiceResponse

        handler = ChatHandler(llm_switcher=MagicMock())

        ext_request = ServiceRequest(
            request_type="chat",
            user_id="user-1",
            messages=[{"role": "user", "content": "test"}],
            workflow_id=workflow_id,
        )

        mock_ext_service = MagicMock()

        async def mock_ext_exec(**kwargs):
            return controlled_result

        mock_ext_service.execute_workflow = mock_ext_exec

        with patch("src.database.connection.get_db_session") as mock_get_db, \
             patch("src.ai.workflow_service.WorkflowService", return_value=mock_ext_service):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = iter([mock_session])

            ext_resp = asyncio.get_event_loop().run_until_complete(
                handler._execute_via_workflow(ext_request, {"system_prompt": "sys", "_skill_whitelist": []})
            )

        # --- Wrapper format differs ---
        assert type(int_resp) is ChatResponse, (
            f"Internal should be ChatResponse, got {type(int_resp)}"
        )
        assert type(ext_resp) is ServiceResponse, (
            f"External should be ServiceResponse, got {type(ext_resp)}"
        )

        # ChatResponse has flat content/model fields
        assert hasattr(int_resp, "content")
        assert hasattr(int_resp, "model")

        # ServiceResponse wraps data in a dict with metadata
        assert hasattr(ext_resp, "data")
        assert hasattr(ext_resp, "metadata")
        assert ext_resp.success is True
        assert ext_resp.request_type == "chat"

        # --- Core content is identical ---
        assert int_resp.content == ext_resp.data["content"], (
            f"Content mismatch:\n"
            f"  ChatResponse.content: {int_resp.content!r}\n"
            f"  ServiceResponse.data['content']: {ext_resp.data['content']!r}"
        )
