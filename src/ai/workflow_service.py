"""
AI Workflow Service.

Core service for workflow CRUD, permission chain validation, and execution
dispatch. Reuses existing AIDataSourceService, RolePermissionService,
SkillPermissionService, and AIAccessLogService.
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, AsyncIterator
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from src.models.ai_workflow import AIWorkflow
from src.models.ai_integration import AISkill
from src.ai.data_source_config import AIDataSourceConfigModel
from src.ai.role_permission_service import RolePermissionService
from src.ai.skill_permission_service import SkillPermissionService
from src.api.workflow_schemas import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    EffectivePermissions,
    AuthorizationRequest,
    MissingPermissions,
)
from src.ai.llm_schemas import GenerateOptions, LLMResponse
from src.models.ai_access_log import AIAccessLog
from src.models.ai_integration import AIGateway

logger = logging.getLogger(__name__)

VALID_ROLES = {"admin", "business_expert", "annotator", "viewer"}
ADMIN_ROLE = "admin"
WORKFLOW_SYSTEM_PROMPT = (
    "你是 SuperInsight 智能数据治理平台的 AI 助手。"
    "你的职责是帮助用户进行数据治理、数据标注、数据质量分析等工作。"
    "请用简洁专业的中文回答用户问题，必要时提供具体的操作建议。"
)
EXECUTE_TIMEOUT_SECONDS = 60

# Known tables per data source — used for table-level authorization validation.
# tables: ["*"] means all tables; specific list means only those tables.
DATA_SOURCE_TABLES: dict = {
    "tasks": ["task_list", "task_status_summary"],
    "annotation_efficiency": ["efficiency_trend", "completion_rate", "quality_score"],
    "user_activity": ["login_records", "operation_records", "online_duration"],
    "data_sync": ["sync_sources", "sync_jobs"],
    "data_lifecycle": ["temp_data", "samples", "annotation", "enhancement", "ai_trial"],
    "augmentation": ["augmentation_tasks", "augmentation_samples"],
    "quality": ["quality_scores", "quality_reports"],
}


class WorkflowService:
    """Workflow engine core service."""

    def __init__(self, db: Session):
        self.db = db
        self._role_perm_service = RolePermissionService(db)
        self._skill_perm_service = SkillPermissionService(db)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_workflow(
        self, data: WorkflowCreateRequest, creator_id: Optional[str] = None
    ) -> AIWorkflow:
        """Create a new workflow after validating all fields."""
        self._validate_name_unique(data.name)
        self._validate_skill_ids(data.skill_ids or [])
        self._validate_data_source_auth(data.data_source_auth or [])
        self._validate_roles(data.visible_roles)

        workflow = AIWorkflow(
            id=str(uuid4()),
            name=data.name,
            description=data.description or "",
            skill_ids=data.skill_ids or [],
            data_source_auth=data.data_source_auth or [],
            output_modes=data.output_modes or [],
            visible_roles=data.visible_roles,
            preset_prompt=data.preset_prompt,
            name_en=data.name_en,
            description_en=data.description_en,
            created_by=creator_id,
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def update_workflow(
        self, workflow_id: str, data: WorkflowUpdateRequest
    ) -> AIWorkflow:
        """Update an existing workflow with partial data."""
        workflow = self._get_or_404(workflow_id)

        update_fields = data.dict(exclude_unset=True)
        if not update_fields:
            return workflow

        # Validate changed fields using the same rules as create
        if "name" in update_fields and update_fields["name"] != workflow.name:
            self._validate_name_unique(update_fields["name"])
        if "skill_ids" in update_fields:
            self._validate_skill_ids(update_fields["skill_ids"] or [])
        if "data_source_auth" in update_fields:
            self._validate_data_source_auth(update_fields["data_source_auth"] or [])
        if "visible_roles" in update_fields:
            self._validate_roles(update_fields["visible_roles"])

        for key, value in update_fields.items():
            setattr(workflow, key, value)

        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def delete_workflow(self, workflow_id: str) -> None:
        """Soft-delete a workflow by setting status to 'disabled'.

        Preset workflows cannot be deleted.
        """
        workflow = self._get_or_404(workflow_id)

        if workflow.is_preset:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_PRESET_DELETE_DENIED",
                    "message": "Preset workflows cannot be deleted",
                },
            )

        workflow.status = "disabled"
        self.db.commit()

    def get_workflow(self, workflow_id: str) -> AIWorkflow:
        """Get a single workflow by ID."""
        return self._get_or_404(workflow_id)

    def list_workflows(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
        is_admin: bool = False,
    ) -> List[AIWorkflow]:
        """List workflows with optional filters.

        Non-admin users are automatically filtered by role visibility
        and only see enabled workflows.
        """
        query = self.db.query(AIWorkflow)

        if not is_admin and role:
            # Non-admin: only enabled workflows visible to their role
            query = query.filter(
                AIWorkflow.visible_roles.contains([role]),
                AIWorkflow.status == "enabled",
            )
        else:
            # Admin: apply explicit filters if provided
            if status:
                query = query.filter(AIWorkflow.status == status)
            if role:
                query = query.filter(AIWorkflow.visible_roles.contains([role]))

        return query.order_by(AIWorkflow.created_at.desc()).all()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_404(self, workflow_id: str) -> AIWorkflow:
        """Fetch workflow by ID or raise 404."""
        workflow = (
            self.db.query(AIWorkflow)
            .filter(AIWorkflow.id == workflow_id)
            .first()
        )
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow {workflow_id} not found",
                },
            )
        return workflow

    def _validate_name_unique(self, name: str) -> None:
        """Raise 409 if a workflow with the same name already exists."""
        exists = (
            self.db.query(AIWorkflow.id)
            .filter(AIWorkflow.name == name)
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=409,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_NAME_CONFLICT",
                    "message": f"Workflow name '{name}' already exists",
                },
            )

    def _validate_skill_ids(self, skill_ids: List[str]) -> None:
        """Raise 400 if any skill_id does not exist in deployed skills."""
        if not skill_ids:
            return
        existing_ids = {
            row.id
            for row in self.db.query(AISkill.id)
            .filter(AISkill.id.in_(skill_ids), AISkill.status != "removed")
            .all()
        }
        missing = set(skill_ids) - existing_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_SKILL_NOT_FOUND",
                    "message": f"Skills not found: {sorted(missing)}",
                    "details": {"missing_skill_ids": sorted(missing)},
                },
            )

    def _validate_data_source_auth(self, data_source_auth: List[dict]) -> None:
        """Validate each data source entry: source exists, enabled, tables valid.

        Checks source_id existence/enabled status (raises on failure).
        Validates tables field structure and logs warnings for unknown tables.
        """
        if not data_source_auth:
            return
        for entry in data_source_auth:
            source_id = entry.get("source_id")
            if not source_id:
                continue
            self._validate_single_data_source(source_id)
            self._validate_tables_field(source_id, entry.get("tables"))

    def _validate_single_data_source(self, source_id: str) -> None:
        """Check one data source exists and is enabled."""
        row = (
            self.db.query(AIDataSourceConfigModel)
            .filter(AIDataSourceConfigModel.id == source_id)
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_DATASOURCE_NOT_FOUND",
                    "message": f"Data source '{source_id}' not found",
                },
            )
        if not row.enabled:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_DATASOURCE_DISABLED",
                    "message": f"Data source '{source_id}' is disabled",
                },
            )

    def _validate_tables_field(
        self, source_id: str, tables: Optional[List[str]]
    ) -> None:
        """Validate the tables list for a data source entry.

        Accepts ["*"] (all tables) or a list of specific table names.
        Logs warnings for tables not found in the known registry.
        """
        if tables is None:
            return
        if not isinstance(tables, list):
            return

        # Wildcard means all tables — no further validation needed
        if tables == ["*"]:
            return

        known = set(DATA_SOURCE_TABLES.get(source_id, []))
        for table in tables:
            if table not in known:
                logger.warning(
                    "Table '%s' not found in data source '%s', will be skipped",
                    table,
                    source_id,
                )

    def _validate_roles(self, roles: List[str]) -> None:
        """Raise 400 if any role value is not in the valid set."""
        if not roles:
            return
        invalid = set(roles) - VALID_ROLES
        if invalid:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_INVALID_ROLE",
                    "message": f"Invalid roles: {sorted(invalid)}",
                    "details": {
                        "invalid_roles": sorted(invalid),
                        "valid_roles": sorted(VALID_ROLES),
                    },
                },
            )

    # ------------------------------------------------------------------
    # Data source table-level authorization
    # ------------------------------------------------------------------

    @staticmethod
    def get_known_tables_for_source(source_id: str) -> List[str]:
        """Return the list of known tables for a data source."""
        return list(DATA_SOURCE_TABLES.get(source_id, []))

    def filter_authorized_tables(
        self,
        data_source_auth: List[dict],
        source_id: str,
        requested_tables: Optional[List[str]] = None,
    ) -> dict:
        """Filter tables to only those authorized by the workflow config.

        Returns {"authorized_tables": [...], "warnings": [...]}.
        - tables: ["*"] → all known tables for the source are authorized.
        - tables: ["t1", "t2"] → only those specific tables.
        - Non-existent tables are skipped with a warning.
        - If source_id is not in data_source_auth, returns empty.
        """
        auth_entry = self._find_source_auth_entry(data_source_auth, source_id)
        if auth_entry is None:
            return {"authorized_tables": [], "warnings": []}

        tables_config = auth_entry.get("tables", [])
        known_tables = set(DATA_SOURCE_TABLES.get(source_id, []))

        authorized = self._resolve_authorized_tables(
            tables_config, known_tables
        )
        return self._apply_requested_filter(
            authorized, known_tables, requested_tables, source_id
        )

    @staticmethod
    def _find_source_auth_entry(
        data_source_auth: List[dict], source_id: str
    ) -> Optional[dict]:
        """Find the auth entry for a given source_id, or None."""
        for entry in data_source_auth:
            if entry.get("source_id") == source_id:
                return entry
        return None

    @staticmethod
    def _resolve_authorized_tables(
        tables_config: List[str], known_tables: set
    ) -> List[str]:
        """Resolve tables config to a concrete list of authorized tables.

        ["*"] expands to all known tables; specific names are kept as-is.
        """
        if tables_config == ["*"]:
            return sorted(known_tables)
        return list(tables_config)

    @staticmethod
    def _apply_requested_filter(
        authorized: List[str],
        known_tables: set,
        requested_tables: Optional[List[str]],
        source_id: str,
    ) -> dict:
        """Intersect authorized tables with requested tables, warn on unknown.

        If requested_tables is None, returns all authorized tables.
        """
        warnings: List[str] = []
        authorized_set = set(authorized)

        if requested_tables is None:
            # Return all authorized, warn about unknown ones
            result = []
            for t in authorized:
                if t not in known_tables:
                    warnings.append(
                        f"Table '{t}' not found in data source '{source_id}'"
                    )
                    logger.warning(
                        "Table '%s' not found in data source '%s', skipped",
                        t, source_id,
                    )
                else:
                    result.append(t)
            return {"authorized_tables": result, "warnings": warnings}

        # Filter to only requested tables that are also authorized
        result = []
        for t in requested_tables:
            if t not in authorized_set:
                continue
            if t not in known_tables:
                warnings.append(
                    f"Table '{t}' not found in data source '{source_id}'"
                )
                logger.warning(
                    "Table '%s' not found in data source '%s', skipped",
                    t, source_id,
                )
            else:
                result.append(t)
        return {"authorized_tables": result, "warnings": warnings}

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_workflow_stats(
        self,
        workflow_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Aggregate execution stats for a specific workflow.

        Returns chat_count, workflow_count, data_source_count for the
        given workflow within the optional date range.
        """
        # Ensure the workflow exists
        self._get_or_404(workflow_id)

        query = self.db.query(AIAccessLog).filter(
            AIAccessLog.resource_id == workflow_id,
            AIAccessLog.event_type == "workflow_execute",
        )
        query = self._apply_date_range(query, start_date, end_date)

        logs = query.all()
        return self._aggregate_stats(logs)

    def get_today_stats(
        self,
        user_id: str,
        user_role: str,
        tenant_id: str,
    ) -> dict:
        """Return today's aggregated stats for the current user.

        Non-admin users see only their own data.
        Admin users see aggregated stats across all users in the tenant.
        """
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        query = self.db.query(AIAccessLog).filter(
            AIAccessLog.tenant_id == tenant_id,
            AIAccessLog.created_at >= start_of_day,
        )

        if user_role != ADMIN_ROLE:
            query = query.filter(AIAccessLog.user_id == user_id)

        logs = query.all()
        return self._aggregate_stats(logs)

    @staticmethod
    def _apply_date_range(
        query,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ):
        """Apply optional date range filters to a query."""
        if start_date is not None:
            query = query.filter(AIAccessLog.created_at >= start_date)
        if end_date is not None:
            query = query.filter(AIAccessLog.created_at <= end_date)
        return query

    @staticmethod
    def _aggregate_stats(logs: List[AIAccessLog]) -> dict:
        """Compute chat_count, workflow_count, data_source_count from logs."""
        chat_count = 0
        workflow_count = 0
        data_source_ids: set = set()

        for log in logs:
            if log.event_type in ("skill_invoke", "data_access"):
                chat_count += 1
            if log.event_type == "workflow_execute":
                workflow_count += 1
            # Collect unique data source IDs from details
            details = log.details or {}
            for src_id in details.get("data_sources", []):
                if src_id:
                    data_source_ids.add(src_id)

        return {
            "chat_count": chat_count,
            "workflow_count": workflow_count,
            "data_source_count": len(data_source_ids),
        }

    # ------------------------------------------------------------------
    # Permission sync
    # ------------------------------------------------------------------

    def sync_permissions(self, permission_list: List[dict]) -> dict:
        """Batch-update data_source_auth for specified workflows.

        Each entry in permission_list must contain:
          - workflow_id: str
          - data_source_auth: list[dict]

        Workflows not mentioned are left untouched.
        Returns {"updated_count": N, "errors": [...]}.
        """
        if not permission_list:
            return {"updated_count": 0, "errors": []}

        updated_count = 0
        errors: List[dict] = []

        for entry in permission_list:
            result = self._sync_single_permission(entry)
            if result is None:
                updated_count += 1
            else:
                errors.append(result)

        self.db.commit()
        return {"updated_count": updated_count, "errors": errors}

    def _sync_single_permission(self, entry: dict) -> Optional[dict]:
        """Process one permission sync entry. Returns error dict or None on success."""
        workflow_id = entry.get("workflow_id")
        if not workflow_id:
            return {"workflow_id": None, "reason": "missing workflow_id"}

        new_auth = entry.get("data_source_auth")
        if new_auth is None:
            return {"workflow_id": workflow_id, "reason": "missing data_source_auth"}

        workflow = (
            self.db.query(AIWorkflow)
            .filter(AIWorkflow.id == workflow_id)
            .first()
        )
        if not workflow:
            logger.warning("sync_permissions: workflow %s not found, skipping", workflow_id)
            return {"workflow_id": workflow_id, "reason": "workflow not found"}

        workflow.data_source_auth = list(new_auth)
        return None

    # ------------------------------------------------------------------
    # Permission chain validation
    # ------------------------------------------------------------------

    def check_permission_chain(
        self,
        workflow: AIWorkflow,
        user_role: str,
        api_overrides: Optional[dict] = None,
    ) -> EffectivePermissions:
        """Validate three-layer permission chain and return effective permissions.

        Layers: (1) workflow enabled, (2) role visibility,
        (3) skill permissions, (4) data source permissions.

        Permission formula: role_base ∩ max(workflow_config, api_overrides).
        """
        api_overrides = api_overrides or {}

        self._check_workflow_enabled(workflow)
        self._check_role_visibility(workflow, user_role)

        effective_skills = self._resolve_effective_skills(workflow, api_overrides)
        effective_data_sources = self._resolve_effective_data_sources(
            workflow, api_overrides
        )

        allowed_skills = self._check_skill_permissions(
            workflow, user_role, effective_skills
        )
        allowed_data_sources = self._check_datasource_permissions(
            workflow, user_role, effective_data_sources
        )

        return EffectivePermissions(
            allowed_skill_ids=allowed_skills,
            allowed_data_sources=allowed_data_sources,
            allowed_output_modes=workflow.output_modes or [],
        )

    def build_authorization_request(
        self,
        workflow: AIWorkflow,
        user_role: str,
        missing_permissions: MissingPermissions,
    ) -> AuthorizationRequest:
        """Build an authorization request structure for 403 responses."""
        scope_parts = []
        if missing_permissions.skills:
            scope_parts.append(
                f"skills: {', '.join(missing_permissions.skills)}"
            )
        if missing_permissions.data_sources:
            scope_parts.append(
                f"data_sources: {', '.join(missing_permissions.data_sources)}"
            )
        if missing_permissions.data_tables:
            table_descs = [
                f"{t.get('source_id', '?')}" for t in missing_permissions.data_tables
            ]
            scope_parts.append(f"data_tables: {', '.join(table_descs)}")

        requested_scope = (
            "; ".join(scope_parts) if scope_parts else "unknown"
        )

        return AuthorizationRequest(
            request_id=str(uuid4()),
            workflow_id=workflow.id,
            missing_permissions=missing_permissions,
            requested_scope=requested_scope,
            callback_url="/api/v1/service/authorization-callback",
        )

    # ------------------------------------------------------------------
    # Permission chain helpers
    # ------------------------------------------------------------------

    def _check_workflow_enabled(self, workflow: AIWorkflow) -> None:
        """Guard: workflow must be enabled."""
        if workflow.status != "enabled":
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_DISABLED",
                    "message": f"Workflow '{workflow.name}' is disabled",
                },
            )

    def _check_role_visibility(
        self, workflow: AIWorkflow, user_role: str
    ) -> None:
        """Guard: user role must be in visible_roles (admin always passes)."""
        if user_role == ADMIN_ROLE:
            return
        visible = workflow.visible_roles or []
        if user_role not in visible:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_PERMISSION_DENIED",
                    "message": (
                        f"Role '{user_role}' is not authorized "
                        f"for workflow '{workflow.name}'"
                    ),
                },
            )

    def _resolve_effective_skills(
        self, workflow: AIWorkflow, api_overrides: dict
    ) -> List[str]:
        """Determine effective skill list: api_overrides > workflow config."""
        override_skills = api_overrides.get("skill_ids")
        if override_skills is not None:
            return list(override_skills)
        return list(workflow.skill_ids or [])

    def _resolve_effective_data_sources(
        self, workflow: AIWorkflow, api_overrides: dict
    ) -> List[dict]:
        """Determine effective data sources: api_overrides > workflow config."""
        override_ds = api_overrides.get("data_source_auth")
        if override_ds is not None:
            return list(override_ds)
        return list(workflow.data_source_auth or [])

    def _check_skill_permissions(
        self,
        workflow: AIWorkflow,
        user_role: str,
        effective_skills: List[str],
    ) -> List[str]:
        """Intersect effective skills with role-allowed skills.

        Raises 403 if any effective skill exceeds role permissions.
        """
        if not effective_skills:
            return []

        allowed_by_role = set(
            self._skill_perm_service.get_allowed_skill_ids(user_role)
        )
        denied_skills = [
            sid for sid in effective_skills if sid not in allowed_by_role
        ]

        if denied_skills:
            missing = MissingPermissions(skills=denied_skills)
            auth_request = self.build_authorization_request(
                workflow, user_role, missing
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_SKILL_DENIED",
                    "message": (
                        f"Skills {denied_skills} exceed role "
                        f"'{user_role}' permissions"
                    ),
                    "details": {
                        "denied_skill_ids": denied_skills,
                        "authorization_request": auth_request.dict(),
                    },
                },
            )

        # Return intersection preserving order
        return [sid for sid in effective_skills if sid in allowed_by_role]

    def _check_datasource_permissions(
        self,
        workflow: AIWorkflow,
        user_role: str,
        effective_data_sources: List[dict],
    ) -> List[dict]:
        """Intersect effective data sources with role-allowed sources.

        Raises 403 if any effective data source exceeds role permissions.
        """
        if not effective_data_sources:
            return []

        allowed_source_ids = set(
            self._role_perm_service.get_permissions_by_role(user_role)
        )
        denied_sources = [
            entry.get("source_id", "")
            for entry in effective_data_sources
            if entry.get("source_id") not in allowed_source_ids
        ]

        if denied_sources:
            missing = MissingPermissions(data_sources=denied_sources)
            auth_request = self.build_authorization_request(
                workflow, user_role, missing
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_DATASOURCE_DENIED",
                    "message": (
                        f"Data sources {denied_sources} exceed role "
                        f"'{user_role}' permissions"
                    ),
                    "details": {
                        "denied_data_sources": denied_sources,
                        "authorization_request": auth_request.dict(),
                    },
                },
            )

        # Return only allowed entries preserving order
        return [
            entry
            for entry in effective_data_sources
            if entry.get("source_id") in allowed_source_ids
        ]

    # ------------------------------------------------------------------
    # Workflow execution
    # ------------------------------------------------------------------

    async def execute_workflow(
        self,
        workflow_id: str,
        user: "UserModel",
        prompt: str,
        options: Optional[GenerateOptions] = None,
        api_overrides: Optional[dict] = None,
    ) -> dict:
        """Execute a workflow: load → check permissions → dispatch to skills or LLM.

        Returns dict with content, model, failed_skills, workflow_id, output_modes.
        """
        options = options or GenerateOptions()
        workflow = self._get_or_404(workflow_id)
        effective = self.check_permission_chain(workflow, user.role, api_overrides)

        system_prompt = self._build_execution_system_prompt(
            effective.allowed_data_sources, workflow.preset_prompt,
        )

        start_ms = time.time()
        if effective.allowed_skill_ids:
            result = await self._execute_with_skills(
                effective.allowed_skill_ids, user.tenant_id,
                prompt, options, system_prompt,
            )
        else:
            result = await self._execute_direct_llm(prompt, options, system_prompt)

        duration_ms = int((time.time() - start_ms) * 1000)
        self._log_workflow_execute(user, workflow, effective, result, duration_ms)

        result["workflow_id"] = workflow_id
        result["output_modes"] = effective.allowed_output_modes
        return result

    async def stream_execute_workflow(
        self,
        workflow_id: str,
        user: "UserModel",
        prompt: str,
        options: Optional[GenerateOptions] = None,
        api_overrides: Optional[dict] = None,
    ) -> AsyncIterator[str]:
        """Stream-execute a workflow, yielding SSE-formatted chunks.

        Same flow as execute_workflow but yields chunks instead of returning.
        """
        options = options or GenerateOptions()
        workflow = self._get_or_404(workflow_id)
        effective = self.check_permission_chain(workflow, user.role, api_overrides)

        system_prompt = self._build_execution_system_prompt(
            effective.allowed_data_sources, workflow.preset_prompt,
        )

        start_ms = time.time()
        failed_skills: List[dict] = []

        if effective.allowed_skill_ids:
            async for chunk in self._stream_with_skills(
                effective.allowed_skill_ids, user.tenant_id,
                prompt, options, system_prompt, failed_skills,
            ):
                yield chunk
        else:
            async for chunk in self._stream_direct_llm(
                prompt, options, system_prompt,
            ):
                yield chunk

        duration_ms = int((time.time() - start_ms) * 1000)
        result = {"failed_skills": failed_skills}
        self._log_workflow_execute(user, workflow, effective, result, duration_ms)

    # ------------------------------------------------------------------
    # Execution helpers — skill-based
    # ------------------------------------------------------------------

    async def _execute_with_skills(
        self,
        skill_ids: List[str],
        tenant_id: str,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str,
    ) -> dict:
        """Execute skills sequentially; failures don't block subsequent skills."""
        from src.ai_integration.openclaw_chat_service import OpenClawChatService
        from src.ai_integration.openclaw_llm_bridge import get_openclaw_llm_bridge

        service = OpenClawChatService(bridge=get_openclaw_llm_bridge(), db=self.db)
        gateway_id = self._get_active_gateway_id(tenant_id)

        contents: List[str] = []
        failed_skills: List[dict] = []
        model_name = "openclaw"

        for skill_id in skill_ids:
            result = await self._invoke_single_skill(
                service, gateway_id, tenant_id, skill_id,
                prompt, options, system_prompt,
            )
            if result.get("error"):
                failed_skills.append({"skill_id": skill_id, "error": result["error"]})
            else:
                contents.append(result["content"])
                model_name = result.get("model", model_name)

        return {
            "content": "\n\n".join(contents) if contents else "",
            "model": model_name,
            "failed_skills": failed_skills,
        }

    async def _invoke_single_skill(
        self,
        service: "OpenClawChatService",
        gateway_id: Optional[str],
        tenant_id: str,
        skill_id: str,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str,
    ) -> dict:
        """Invoke one skill via OpenClawChatService. Returns content or error."""
        if not gateway_id:
            return {"error": "No active OpenClaw gateway available"}
        try:
            response = await service.chat(
                gateway_id=gateway_id,
                tenant_id=tenant_id,
                prompt=prompt,
                options=options,
                system_prompt=system_prompt,
                skill_ids=[skill_id],
            )
            return {"content": response.content, "model": response.model}
        except Exception as exc:
            logger.warning("Skill %s failed: %s", skill_id, exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Execution helpers — direct LLM
    # ------------------------------------------------------------------

    async def _execute_direct_llm(
        self,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str,
    ) -> dict:
        """Execute via LLMSwitcher when workflow has no skills."""
        from src.ai.llm_switcher import get_llm_switcher

        switcher = get_llm_switcher()
        try:
            response = await switcher.generate(
                prompt=prompt, options=options, system_prompt=system_prompt,
            )
            return {
                "content": response.content,
                "model": response.model,
                "failed_skills": [],
            }
        except Exception as exc:
            logger.error("LLM direct execution failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error_code": "WORKFLOW_LLM_UNAVAILABLE",
                    "message": f"LLM service unavailable: {exc}",
                },
            )

    # ------------------------------------------------------------------
    # Streaming helpers
    # ------------------------------------------------------------------

    async def _stream_with_skills(
        self,
        skill_ids: List[str],
        tenant_id: str,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str,
        failed_skills: List[dict],
    ) -> AsyncIterator[str]:
        """Stream skill responses sequentially; failures annotated inline."""
        from src.ai_integration.openclaw_chat_service import OpenClawChatService
        from src.ai_integration.openclaw_llm_bridge import get_openclaw_llm_bridge

        service = OpenClawChatService(bridge=get_openclaw_llm_bridge(), db=self.db)
        gateway_id = self._get_active_gateway_id(tenant_id)

        for skill_id in skill_ids:
            async for chunk in self._stream_single_skill(
                service, gateway_id, tenant_id, skill_id,
                prompt, options, system_prompt, failed_skills,
            ):
                yield chunk

        # Final done chunk
        yield self._sse_chunk(content="", done=True)

    async def _stream_single_skill(
        self,
        service: "OpenClawChatService",
        gateway_id: Optional[str],
        tenant_id: str,
        skill_id: str,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str,
        failed_skills: List[dict],
    ) -> AsyncIterator[str]:
        """Stream one skill; on failure, emit error chunk and continue."""
        if not gateway_id:
            failed_skills.append({"skill_id": skill_id, "error": "No active gateway"})
            yield self._sse_chunk(
                error=f"Skill {skill_id}: No active OpenClaw gateway", done=False,
            )
            return
        try:
            async for chunk in service.stream_chat(
                gateway_id=gateway_id,
                tenant_id=tenant_id,
                prompt=prompt,
                options=options,
                system_prompt=system_prompt,
                skill_ids=[skill_id],
            ):
                yield chunk
        except Exception as exc:
            logger.warning("Skill %s stream failed: %s", skill_id, exc)
            failed_skills.append({"skill_id": skill_id, "error": str(exc)})
            yield self._sse_chunk(
                error=f"Skill {skill_id} failed: {exc}", done=False,
            )

    async def _stream_direct_llm(
        self,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str,
    ) -> AsyncIterator[str]:
        """Stream via LLMSwitcher when workflow has no skills."""
        from src.ai.llm_switcher import get_llm_switcher

        switcher = get_llm_switcher()
        try:
            async for chunk in switcher.stream_generate(
                prompt=prompt, options=options, system_prompt=system_prompt,
            ):
                yield self._sse_chunk(content=chunk, done=False)
            yield self._sse_chunk(content="", done=True)
        except Exception as exc:
            logger.error("LLM stream failed: %s", exc)
            yield self._sse_chunk(error=f"LLM service error: {exc}", done=True)

    # ------------------------------------------------------------------
    # Execution support helpers
    # ------------------------------------------------------------------

    def _get_active_gateway_id(self, tenant_id: str) -> Optional[str]:
        """Find the first active OpenClaw gateway for a tenant."""
        gateway = (
            self.db.query(AIGateway)
            .filter(
                AIGateway.tenant_id == tenant_id,
                AIGateway.gateway_type == "openclaw",
                AIGateway.status == "active",
            )
            .first()
        )
        return str(gateway.id) if gateway else None

    def _build_execution_system_prompt(
        self,
        data_sources: List[dict],
        preset_prompt: Optional[str] = None,
    ) -> str:
        """Build system prompt with data context and optional preset prompt."""
        parts = [WORKFLOW_SYSTEM_PROMPT]

        if preset_prompt:
            parts.append(preset_prompt)

        data_ctx = self._build_data_context(data_sources)
        if data_ctx:
            parts.append(data_ctx)

        return "\n\n".join(parts)

    def _build_data_context(self, data_sources: List[dict]) -> str:
        """Query authorized data sources and build context string for LLM."""
        if not data_sources:
            return ""

        from src.ai.data_source_config import AIDataSourceService
        service = AIDataSourceService(self.db)

        parts = ["以下是所选数据源的汇总数据，请综合分析："]
        for entry in data_sources:
            source_id = entry.get("source_id", "")
            if not source_id:
                continue
            try:
                data = service.query_source_data(source_id)
                parts.append(
                    f"[{source_id}]: {json.dumps(data, ensure_ascii=False, default=str)}"
                )
            except Exception as exc:
                logger.warning("Failed to query data source %s: %s", source_id, exc)

        return "\n".join(parts) if len(parts) > 1 else ""

    def _log_workflow_execute(
        self,
        user: "UserModel",
        workflow: AIWorkflow,
        effective: EffectivePermissions,
        result: dict,
        duration_ms: int,
    ) -> None:
        """Record a workflow_execute event in AIAccessLog."""
        failed = result.get("failed_skills", [])
        success = len(failed) == 0

        self.db.add(AIAccessLog(
            tenant_id=user.tenant_id,
            user_id=str(user.id),
            user_role=user.role,
            event_type="workflow_execute",
            resource_id=workflow.id,
            resource_name=workflow.name,
            request_type="chat",
            success=success,
            error_message=(
                json.dumps(failed, ensure_ascii=False) if failed else None
            ),
            duration_ms=duration_ms,
            details={
                "workflow_id": workflow.id,
                "skill_ids": effective.allowed_skill_ids,
                "data_sources": [
                    e.get("source_id") for e in effective.allowed_data_sources
                ],
                "output_modes": effective.allowed_output_modes,
                "failed_skills": failed,
            },
        ))
        self.db.commit()

    # ------------------------------------------------------------------
    # Data migration — default workflow generation
    # ------------------------------------------------------------------

    def generate_default_workflows(self) -> List[AIWorkflow]:
        """Generate default workflows based on existing role permissions.

        For each role that has permissions, creates a default workflow
        with the same skill_ids and data_source_auth as the role's
        current permissions. Idempotent — skips if workflow already exists.

        Returns list of created workflow objects.
        """
        created: List[AIWorkflow] = []
        roles = ["admin", "business_expert", "annotator", "viewer"]

        for role in roles:
            workflow = self._generate_default_for_role(role)
            if workflow is not None:
                created.append(workflow)

        if created:
            self.db.commit()
            for w in created:
                self.db.refresh(w)

        return created

    def _generate_default_for_role(self, role: str) -> Optional[AIWorkflow]:
        """Create a default workflow for one role if it doesn't exist yet.

        Returns the new AIWorkflow or None if skipped.
        """
        default_name = f"默认工作流-{role}"

        # Idempotent: skip if already exists
        existing = self.db.query(AIWorkflow).filter(
            AIWorkflow.name == default_name
        ).first()
        if existing:
            return None

        skill_ids = self._get_role_skill_ids(role)
        data_source_auth = self._get_role_data_source_auth(role)

        # Skip roles with no permissions at all
        if not skill_ids and not data_source_auth:
            return None

        workflow = AIWorkflow(
            name=default_name,
            name_en=f"Default Workflow - {role}",
            description=f"基于 {role} 角色现有权限自动生成的默认工作流",
            description_en=f"Auto-generated default workflow based on {role} role permissions",
            status="enabled",
            is_preset=False,
            skill_ids=skill_ids,
            data_source_auth=data_source_auth,
            output_modes=["merge"],
            visible_roles=[role],
            created_by="system_migration",
        )
        self.db.add(workflow)
        return workflow

    def _get_role_skill_ids(self, role: str) -> List[str]:
        """Get skill IDs allowed for a role from AISkillRolePermission."""
        try:
            from src.models.ai_skill_role_permission import AISkillRolePermission
            perms = self.db.query(AISkillRolePermission).filter(
                AISkillRolePermission.role == role,
                AISkillRolePermission.allowed == True,  # noqa: E712
            ).all()
            return [p.skill_id for p in perms]
        except Exception:
            return []

    def _get_role_data_source_auth(self, role: str) -> List[dict]:
        """Get data source auth config for a role from AIDataSourceRolePermission."""
        try:
            from src.models.ai_data_source_role_permission import AIDataSourceRolePermission
            perms = self.db.query(AIDataSourceRolePermission).filter(
                AIDataSourceRolePermission.role == role,
                AIDataSourceRolePermission.allowed == True,  # noqa: E712
            ).all()
            return [{"source_id": p.source_id, "tables": ["*"]} for p in perms]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Preset workflow creation
    # ------------------------------------------------------------------

    def create_preset_workflows(self) -> List[AIWorkflow]:
        """Create 4 system preset workflows. Idempotent — skips existing.

        Preset workflow names/descriptions are defined in i18n translation files.
        """
        presets = [
            {
                "name": "销售预测分析",
                "name_en": "Sales Forecast Analysis",
                "description": "基于历史数据进行销售趋势预测和分析",
                "description_en": "Predict and analyze sales trends based on historical data",
                "skill_ids": [],
                "data_source_auth": [],
                "output_modes": ["merge"],
                "visible_roles": ["admin", "business_expert"],
                "preset_prompt": "请基于历史销售数据，分析销售趋势并给出预测建议。",
            },
            {
                "name": "数据质量检查",
                "name_en": "Data Quality Check",
                "description": "自动检测数据质量问题并生成改进建议",
                "description_en": "Automatically detect data quality issues and generate improvement suggestions",
                "skill_ids": [],
                "data_source_auth": [],
                "output_modes": ["merge"],
                "visible_roles": ["admin", "business_expert", "annotator"],
                "preset_prompt": "请检查当前数据集的质量问题，包括缺失值、异常值、重复数据等，并给出改进建议。",
            },
            {
                "name": "智能标注建议",
                "name_en": "Smart Annotation Suggestions",
                "description": "基于上下文提供智能标注建议",
                "description_en": "Provide intelligent annotation suggestions based on context",
                "skill_ids": [],
                "data_source_auth": [],
                "output_modes": ["merge"],
                "visible_roles": ["admin", "annotator"],
                "preset_prompt": "请根据当前标注任务的上下文，提供智能标注建议和最佳实践。",
            },
            {
                "name": "任务进度追踪",
                "name_en": "Task Progress Tracking",
                "description": "追踪和分析任务完成进度",
                "description_en": "Track and analyze task completion progress",
                "skill_ids": [],
                "data_source_auth": [],
                "output_modes": ["merge"],
                "visible_roles": ["admin", "business_expert", "annotator", "viewer"],
                "preset_prompt": "请分析当前任务的完成进度，包括已完成、进行中和待处理的任务统计。",
            },
        ]

        created: List[AIWorkflow] = []
        for preset in presets:
            existing = self.db.query(AIWorkflow).filter(
                AIWorkflow.name == preset["name"]
            ).first()
            if existing:
                continue

            workflow = AIWorkflow(
                name=preset["name"],
                name_en=preset["name_en"],
                description=preset["description"],
                description_en=preset["description_en"],
                status="enabled",
                is_preset=True,
                skill_ids=preset["skill_ids"],
                data_source_auth=preset["data_source_auth"],
                output_modes=preset["output_modes"],
                visible_roles=preset["visible_roles"],
                preset_prompt=preset["preset_prompt"],
                created_by="system_preset",
            )
            self.db.add(workflow)
            created.append(workflow)

        if created:
            self.db.commit()
            for w in created:
                self.db.refresh(w)

        return created

    @staticmethod
    def _sse_chunk(
        content: str = "",
        done: bool = False,
        error: Optional[str] = None,
    ) -> str:
        """Format a single SSE data line."""
        payload: dict = {"content": content, "done": done}
        if error:
            payload["error"] = error
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
