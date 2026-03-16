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
        start = time.monotonic()

        params: QueryParams = context["query_params"]
        provider = self._providers[request.data_type]
        result = await provider.query(params)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return _build_response(request, result, elapsed_ms)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_tenant_id(request: ServiceRequest) -> str:
    """Extract tenant_id from extensions or fall back to a default."""
    if request.extensions and "tenant_id" in request.extensions:
        return str(request.extensions["tenant_id"])
    return _DEFAULT_TENANT


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
