"""
QueryHandler — 结构化数据查询处理器。

校验 data_type、构建 QueryParams、调用 DataProvider 并返回分页结果。
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from src.service_engine.base import BaseHandler
from src.service_engine.providers import (
    BaseDataProvider,
    QueryParams,
    VALID_DATA_TYPES,
    get_data_providers,
)
from src.service_engine.router import ServiceEngineError
from src.service_engine.schemas import (
    ResponseMetadata,
    ServiceRequest,
    ServiceResponse,
)

_DEFAULT_TENANT = "default-tenant"


class QueryHandler(BaseHandler):
    """Handler for request_type='query' — structured data queries."""

    def __init__(
        self,
        providers: Optional[Dict[str, BaseDataProvider]] = None,
    ) -> None:
        self._providers = providers or get_data_providers()

    # -- validate ------------------------------------------------------------

    async def validate(self, request: ServiceRequest) -> None:
        """Ensure data_type is present and belongs to VALID_DATA_TYPES."""
        if not request.data_type:
            raise ServiceEngineError(
                status_code=400,
                error_code="INVALID_DATA_TYPE",
                message="data_type is required for query requests",
                details={"supported_types": list(VALID_DATA_TYPES)},
            )
        if request.data_type not in VALID_DATA_TYPES:
            raise ServiceEngineError(
                status_code=400,
                error_code="INVALID_DATA_TYPE",
                message=f"Unsupported data_type: {request.data_type}",
                details={"supported_types": list(VALID_DATA_TYPES)},
            )

    # -- build_context -------------------------------------------------------

    async def build_context(self, request: ServiceRequest) -> dict:
        """Build QueryParams from the incoming request fields."""
        tenant_id = _extract_tenant_id(request)
        params = QueryParams(
            tenant_id=tenant_id,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            fields=request.fields,
            filters=request.filters,
        )
        return {"query_params": params}

    # -- execute -------------------------------------------------------------

    async def execute(
        self,
        request: ServiceRequest,
        context: dict,
    ) -> ServiceResponse:
        """Query the provider and return a paginated response."""
        # Workflow routing: delegate when workflow_id is present
        if request.workflow_id:
            return await self._execute_via_workflow(request, context)

        start = time.monotonic()

        params: QueryParams = context["query_params"]
        provider = self._providers[request.data_type]
        result = await provider.query(params)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return _build_response(request, result, elapsed_ms)

    # -- workflow delegation --------------------------------------------------

    async def _execute_via_workflow(
        self, request: ServiceRequest, context: dict,
    ) -> ServiceResponse:
        """Delegate to WorkflowService for workflow-routed query execution."""
        from src.database.connection import get_db_session
        from src.ai.workflow_service import WorkflowService

        skill_whitelist = context.get("_skill_whitelist", [])
        api_overrides = _build_api_overrides(skill_whitelist)
        user = _build_mock_user(request)
        prompt = f"query:{request.data_type}" if request.data_type else "query"

        start = time.monotonic()
        with next(get_db_session()) as db:
            service = WorkflowService(db)
            result = await service.execute_workflow(
                workflow_id=request.workflow_id,
                user=user,
                prompt=prompt,
                api_overrides=api_overrides,
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ServiceResponse(
            success=True,
            request_type="query",
            data={"content": result.get("content", ""), **_workflow_extras(result)},
            metadata=ResponseMetadata(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=elapsed_ms,
            ),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_tenant_id(request: ServiceRequest) -> str:
    """Extract tenant_id from extensions or fall back to a default."""
    if request.extensions and "tenant_id" in request.extensions:
        return str(request.extensions["tenant_id"])
    return _DEFAULT_TENANT


class _MockUser:
    """Lightweight user object for WorkflowService when called from Service Engine."""

    __slots__ = ("user_id", "tenant_id", "role")

    def __init__(self, user_id: str, tenant_id: str, role: str) -> None:
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


def _build_mock_user(request: ServiceRequest) -> "_MockUser":
    """Build a mock user from ServiceRequest fields."""
    tenant_id = _extract_tenant_id(request)
    role = "api"
    if request.extensions and "role" in request.extensions:
        role = str(request.extensions["role"])
    return _MockUser(user_id=request.user_id, tenant_id=tenant_id, role=role)


def _build_api_overrides(skill_whitelist: list) -> "Optional[dict]":
    """Build api_overrides dict from API key's skill_whitelist."""
    if not skill_whitelist:
        return None
    return {"skill_ids": list(skill_whitelist)}


def _workflow_extras(result: dict) -> dict:
    """Extract optional workflow metadata from execution result."""
    extras: dict = {}
    if result.get("workflow_id"):
        extras["workflow_id"] = result["workflow_id"]
    if result.get("output_modes"):
        extras["output_modes"] = result["output_modes"]
    if result.get("failed_skills"):
        extras["failed_skills"] = result["failed_skills"]
    return extras


def _build_response(request, result, elapsed_ms: int) -> ServiceResponse:
    """Assemble the unified ServiceResponse with pagination metadata."""
    return ServiceResponse(
        success=True,
        request_type="query",
        data={
            "items": result.items,
            "pagination": {
                "total": result.total,
                "page": result.page,
                "page_size": result.page_size,
                "total_pages": result.total_pages,
            },
        },
        metadata=ResponseMetadata(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=elapsed_ms,
        ),
    )
