"""
AI Assistant API endpoints for SuperInsight Platform.

Provides non-streaming and streaming chat endpoints powered by LLMSwitcher.
Supports mode routing: direct (LLMSwitcher) and openclaw (OpenClawChatService).
"""

import json
import logging
import asyncio
from typing import AsyncIterator, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.security.models import UserModel
from src.ai.llm_switcher import get_llm_switcher
from src.ai.llm_schemas import GenerateOptions, LLMErrorCode
from src.ai_integration.openclaw_chat_service import (
    OpenClawChatService,
    OpenClawUnavailableError,
)
from src.ai_integration.openclaw_llm_bridge import get_openclaw_llm_bridge
from src.ai_integration.schemas import SkillInfoResponse, OpenClawStatusResponse
from src.database.connection import get_db
from src.models.ai_integration import AIGateway
from src.api.workflow_schemas import WorkflowCreateRequest, WorkflowUpdateRequest

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v1/ai-assistant", tags=["AI Assistant"])

# System prompt for the AI assistant
SYSTEM_PROMPT = (
    "你是 SuperInsight 智能数据治理平台的 AI 助手。"
    "你的职责是帮助用户进行数据治理、数据标注、数据质量分析等工作。"
    "请用简洁专业的中文回答用户问题，必要时提供具体的操作建议。"
)

DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.7
REQUEST_TIMEOUT_SECONDS = 60


# --- Pydantic Models ---


class ChatMessage(BaseModel):
    """Single chat message."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Chat request with message history and optional parameters."""

    messages: list[ChatMessage] = Field(..., min_length=1)
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    mode: Literal["direct", "openclaw"] = "direct"
    gateway_id: Optional[str] = None
    skill_ids: Optional[list[str]] = None
    data_source_ids: Optional[list[str]] = None
    output_mode: Optional[Literal["merge", "compare"]] = None
    workflow_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_openclaw_fields(self):
        """Require gateway_id when mode is openclaw."""
        if self.mode == "openclaw" and not self.gateway_id:
            raise ValueError("gateway_id is required for openclaw mode")
        return self


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    content: str
    model: str
    usage: Optional[dict] = None


# --- Helper Functions ---


def format_chat_history(messages: list[ChatMessage]) -> str:
    """Concatenate message history into a context string.

    Format: "role: content\\n" for each message.
    """
    if not messages:
        return ""
    return "\n".join(f"{msg.role}: {msg.content}" for msg in messages)


def build_prompt(messages: list[ChatMessage]) -> str:
    """Extract prompt from message list: history context + last user message."""
    history = format_chat_history(messages[:-1])
    last_message = messages[-1].content
    return f"{history}\n{last_message}" if history else last_message


def build_data_context(
    data_source_ids: list[str], output_mode: str, db: Session
) -> str:
    """Query selected data sources and build context string for LLM."""
    if not data_source_ids:
        return ""

    from src.ai.data_source_config import AIDataSourceService

    service = AIDataSourceService(db)
    results = {}
    for src_id in data_source_ids:
        results[src_id] = service.query_source_data(src_id)

    if output_mode == "compare":
        parts = ["以下是各数据源的数据，请分别分析并对比："]
        for src_id, data in results.items():
            parts.append(
                f"\n--- 数据源: {src_id} ---\n{json.dumps(data, ensure_ascii=False, default=str)}"
            )
        return "\n".join(parts)

    # merge mode (default)
    parts = ["以下是所选数据源的汇总数据，请综合分析："]
    for src_id, data in results.items():
        parts.append(f"[{src_id}]: {json.dumps(data, ensure_ascii=False, default=str)}")
    return "\n".join(parts)


def build_options(request: ChatRequest, *, stream: bool = False) -> GenerateOptions:
    """Build GenerateOptions from a ChatRequest."""
    return GenerateOptions(
        max_tokens=request.max_tokens or DEFAULT_MAX_TOKENS,
        temperature=request.temperature or DEFAULT_TEMPERATURE,
        stream=stream,
    )


def get_openclaw_chat_service(db: Session) -> OpenClawChatService:
    """Create an OpenClawChatService with the shared LLM bridge."""
    bridge = get_openclaw_llm_bridge()
    return OpenClawChatService(bridge=bridge, db=db)


def _log_skill_access(
    db: Session,
    user: "UserModel",
    original_ids: list,
    filtered_ids: list,
) -> None:
    """Log skill invocation and any denied skills."""
    from src.ai.access_log_service import AIAccessLogService

    svc = AIAccessLogService(db)
    user_id = str(user.id)

    # Log allowed skills
    if filtered_ids:
        svc.log_skill_invoke(
            tenant_id=user.tenant_id,
            user_id=user_id,
            user_role=user.role,
            skill_ids=filtered_ids,
            success=True,
        )

    # Log denied skills
    denied = list(set(original_ids) - set(filtered_ids))
    if denied:
        svc.log_skill_invoke(
            tenant_id=user.tenant_id,
            user_id=user_id,
            user_role=user.role,
            skill_ids=denied,
            success=False,
            error_message="Denied by role permission",
            details={"denied_ids": denied, "requested_ids": original_ids},
        )


def _log_data_access(
    db: Session,
    user: "UserModel",
    source_ids: list,
    output_mode: Optional[str],
) -> None:
    """Log data source access from AI assistant."""
    from src.ai.access_log_service import AIAccessLogService

    svc = AIAccessLogService(db)
    svc.log_data_access(
        tenant_id=user.tenant_id,
        user_id=str(user.id),
        user_role=user.role,
        source_ids=source_ids,
        output_mode=output_mode,
    )


def _log_permission_change(
    db: Session,
    user: "UserModel",
    target_type: str,
    changes: list,
) -> None:
    """Log a permission change (skill or data source)."""
    from src.ai.access_log_service import AIAccessLogService

    svc = AIAccessLogService(db)
    svc.log_permission_change(
        tenant_id=user.tenant_id,
        user_id=str(user.id),
        user_role=user.role,
        target_type=target_type,
        changes=changes,
    )


def _filter_skills_by_role(
    skill_ids: list,
    user_role: str,
    db: Session,
) -> list:
    """Filter requested skill_ids by the user's role permissions.

    Returns only the skill IDs that the role is allowed to use.
    Logs a warning for any denied skill IDs.
    """
    from src.ai.skill_permission_service import SkillPermissionService

    service = SkillPermissionService(db)
    allowed = service.get_allowed_skill_ids(user_role)
    allowed_set = set(allowed)

    filtered = [sid for sid in skill_ids if sid in allowed_set]
    denied = set(skill_ids) - set(filtered)
    if denied:
        logger.warning(
            "Skill IDs denied by role permission (role=%s): %s",
            user_role,
            denied,
        )
    return filtered


# --- Non-Streaming Endpoints ---


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Non-streaming chat endpoint. Routes to LLMSwitcher or OpenClaw."""
    # Workflow routing: delegate to WorkflowService when workflow_id is present
    if request.workflow_id:
        return await _chat_workflow(request, current_user, db)

    prompt = build_prompt(request.messages)

    # Filter skill_ids by role permissions
    original_skill_ids = list(request.skill_ids or [])
    if request.skill_ids:
        request.skill_ids = _filter_skills_by_role(
            request.skill_ids,
            current_user.role,
            db,
        )

    # Log skill invocation
    if original_skill_ids:
        _log_skill_access(
            db,
            current_user,
            original_skill_ids,
            request.skill_ids or [],
        )

    # Log data source access
    if request.data_source_ids:
        _log_data_access(
            db,
            current_user,
            request.data_source_ids,
            request.output_mode,
        )

    # Inject data source context if selected
    data_ctx = build_data_context(
        request.data_source_ids or [], request.output_mode or "merge", db
    )
    effective_system = f"{SYSTEM_PROMPT}\n\n{data_ctx}" if data_ctx else SYSTEM_PROMPT

    options = build_options(request)

    if request.mode == "openclaw":
        return await _chat_openclaw(
            request, prompt, options, current_user, db, system_prompt=effective_system
        )

    return await _chat_direct(prompt, options, system_prompt=effective_system)


async def _chat_direct(
    prompt: str, options: GenerateOptions, system_prompt: str = SYSTEM_PROMPT
) -> ChatResponse:
    """Handle direct mode: forward to LLMSwitcher."""
    switcher = get_llm_switcher()
    try:
        response = await asyncio.wait_for(
            switcher.generate(
                prompt=prompt,
                options=options,
                system_prompt=system_prompt,
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="AI 服务响应超时，请稍后重试")
    except Exception as e:
        error_code = getattr(e, "error_code", None)
        if error_code == LLMErrorCode.SERVICE_UNAVAILABLE:
            raise HTTPException(status_code=503, detail="AI 服务暂不可用")
        logger.error("AI chat error: %s", e)
        raise HTTPException(status_code=500, detail="AI 服务内部错误")

    return _build_chat_response(response)


async def _chat_openclaw(
    request: ChatRequest,
    prompt: str,
    options: GenerateOptions,
    current_user: UserModel,
    db: Session,
    system_prompt: str = SYSTEM_PROMPT,
) -> ChatResponse:
    """Handle openclaw mode: forward to OpenClawChatService."""
    service = get_openclaw_chat_service(db)
    tenant_id = current_user.tenant_id

    try:
        response = await asyncio.wait_for(
            service.chat(
                gateway_id=request.gateway_id,
                tenant_id=tenant_id,
                prompt=prompt,
                options=options,
                system_prompt=system_prompt,
                skill_ids=request.skill_ids,
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except OpenClawUnavailableError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="OpenClaw 网关响应超时，请稍后重试",
        )
    except Exception as e:
        logger.error("OpenClaw chat error: %s", e)
        raise HTTPException(status_code=503, detail="OpenClaw 服务暂不可用")

    return _build_chat_response(response)


def _build_chat_response(response) -> ChatResponse:
    """Convert an LLMResponse to ChatResponse."""
    usage = None
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    return ChatResponse(content=response.content, model=response.model, usage=usage)


# --- Workflow Routing Helpers ---


def _build_workflow_api_overrides(request: ChatRequest) -> Optional[dict]:
    """Build api_overrides dict from request fields when present."""
    overrides = {}
    if request.skill_ids:
        overrides["skill_ids"] = request.skill_ids
    if request.data_source_ids:
        overrides["data_source_ids"] = request.data_source_ids
    if request.output_mode:
        overrides["output_mode"] = request.output_mode
    return overrides or None


async def _chat_workflow(
    request: ChatRequest,
    user: UserModel,
    db: Session,
) -> ChatResponse:
    """Handle workflow-routed non-streaming chat request."""
    from src.ai.workflow_service import WorkflowService

    prompt = build_prompt(request.messages)
    options = build_options(request)
    api_overrides = _build_workflow_api_overrides(request)

    service = WorkflowService(db)
    result = await service.execute_workflow(
        workflow_id=request.workflow_id,
        user=user,
        prompt=prompt,
        options=options,
        api_overrides=api_overrides,
    )
    return ChatResponse(
        content=result.get("content", ""),
        model=result.get("model", ""),
        usage=result.get("usage"),
    )


async def _disconnect_aware(
    generator: AsyncIterator[str],
    http_request: FastAPIRequest,
) -> AsyncIterator[str]:
    """Wrap an async generator to stop when the client disconnects.

    Checks ``http_request.is_disconnected()`` between chunks so that
    long-running LLM calls are cancelled promptly when the user clicks
    "Stop", saving tokens.
    """
    try:
        async for chunk in generator:
            if await http_request.is_disconnected():
                logger.info("Client disconnected, stopping stream")
                break
            yield chunk
    finally:
        await generator.aclose()


def _stream_workflow_response(
    request: ChatRequest,
    user: UserModel,
    db: Session,
    http_request: FastAPIRequest,
) -> StreamingResponse:
    """Build a StreamingResponse for workflow-routed streaming chat."""
    from src.ai.workflow_service import WorkflowService

    prompt = build_prompt(request.messages)
    options = build_options(request, stream=True)
    api_overrides = _build_workflow_api_overrides(request)

    service = WorkflowService(db)
    generator = service.stream_execute_workflow(
        workflow_id=request.workflow_id,
        user=user,
        prompt=prompt,
        options=options,
        api_overrides=api_overrides,
    )
    return StreamingResponse(
        _disconnect_aware(generator, http_request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# --- Streaming ---


async def generate_stream(
    request: ChatRequest, switcher, system_prompt: str = SYSTEM_PROMPT
) -> AsyncIterator[str]:
    """Async generator that yields SSE-formatted chunks from LLMSwitcher."""
    prompt = build_prompt(request.messages)
    options = build_options(request, stream=True)

    try:
        async for chunk in switcher.stream_generate(
            prompt=prompt, options=options, system_prompt=system_prompt
        ):
            yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
    except BaseException as e:
        # Catch BaseException to handle all exceptions including SystemExit, KeyboardInterrupt
        # Convert to proper Exception type for logging and response
        logger.error("AI stream error: %s (type: %s)", e, type(e).__name__)
        error_message = str(e) if str(e) else f"Stream error: {type(e).__name__}"
        yield f"data: {json.dumps({'error': error_message, 'done': True})}\n\n"
        # Re-raise if it's a system exception (SystemExit, KeyboardInterrupt)
        if isinstance(e, (SystemExit, KeyboardInterrupt)):
            raise


async def openclaw_stream(
    request: ChatRequest,
    service: OpenClawChatService,
    current_user: UserModel,
    system_prompt: str = SYSTEM_PROMPT,
) -> AsyncIterator[str]:
    """Async generator that yields SSE chunks from OpenClawChatService."""
    prompt = build_prompt(request.messages)
    options = build_options(request, stream=True)
    tenant_id = current_user.tenant_id

    try:
        async for chunk in service.stream_chat(
            gateway_id=request.gateway_id,
            tenant_id=tenant_id,
            prompt=prompt,
            options=options,
            system_prompt=system_prompt,
            skill_ids=request.skill_ids,
        ):
            yield chunk
    except OpenClawUnavailableError as e:
        logger.warning("OpenClaw unavailable during stream: %s", e)
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    except BaseException as e:
        # Catch BaseException to handle all exceptions including SystemExit, KeyboardInterrupt
        # Convert to proper Exception type for logging and response
        logger.error("OpenClaw stream error: %s (type: %s)", e, type(e).__name__)
        error_message = str(e) if str(e) else f"Stream error: {type(e).__name__}"
        yield f"data: {json.dumps({'error': error_message, 'done': True})}\n\n"
        # Re-raise if it's a system exception (SystemExit, KeyboardInterrupt)
        if isinstance(e, (SystemExit, KeyboardInterrupt)):
            raise


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: FastAPIRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Streaming chat endpoint. Routes to LLMSwitcher or OpenClaw SSE stream."""
    # Workflow routing: delegate to WorkflowService when workflow_id is present
    if request.workflow_id:
        return _stream_workflow_response(request, current_user, db, http_request)

    # Filter skill_ids by role permissions
    original_skill_ids = list(request.skill_ids or [])
    if request.skill_ids:
        request.skill_ids = _filter_skills_by_role(
            request.skill_ids,
            current_user.role,
            db,
        )

    # Log skill invocation
    if original_skill_ids:
        _log_skill_access(
            db,
            current_user,
            original_skill_ids,
            request.skill_ids or [],
        )

    # Log data source access
    if request.data_source_ids:
        _log_data_access(
            db,
            current_user,
            request.data_source_ids,
            request.output_mode,
        )

    # Inject data source context if selected
    data_ctx = build_data_context(
        request.data_source_ids or [], request.output_mode or "merge", db
    )
    effective_system = f"{SYSTEM_PROMPT}\n\n{data_ctx}" if data_ctx else SYSTEM_PROMPT

    if request.mode == "openclaw":
        service = get_openclaw_chat_service(db)
        generator = openclaw_stream(
            request, service, current_user, system_prompt=effective_system
        )
    else:
        switcher = get_llm_switcher()
        generator = generate_stream(request, switcher, system_prompt=effective_system)

    return StreamingResponse(
        _disconnect_aware(generator, http_request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/chat/openclaw-status", response_model=OpenClawStatusResponse)
async def openclaw_status(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OpenClawStatusResponse:
    """Query OpenClaw gateway availability and deployed skills for current tenant."""
    service = get_openclaw_chat_service(db)
    return await service.get_status(tenant_id=current_user.tenant_id)


# --- Data Source Configuration Endpoints ---


class DataSourceConfigItem(BaseModel):
    """Single data source config item for admin update."""

    id: str
    label: Optional[str] = None
    enabled: Optional[bool] = None
    access_mode: Optional[str] = None


class DataSourceConfigRequest(BaseModel):
    """Admin request to update data source configs."""

    sources: list[DataSourceConfigItem]


class RolePermissionItem(BaseModel):
    """Single role-permission mapping item."""

    role: str
    source_id: str
    allowed: bool


class RolePermissionRequest(BaseModel):
    """Request to batch update role-permission mappings."""

    permissions: list[RolePermissionItem]


class SkillPermissionItem(BaseModel):
    """Single role-skill permission mapping item."""

    role: str
    skill_id: str
    allowed: bool


class SkillPermissionRequest(BaseModel):
    """Request to batch update role-skill permission mappings."""

    permissions: list[SkillPermissionItem]


@router.get("/data-sources/available")
async def get_available_data_sources(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get data sources available to the current user (filtered by role)."""
    from src.ai.data_source_config import AIDataSourceService

    service = AIDataSourceService(db)
    return service.get_available_sources(role=current_user.role)


@router.get("/data-sources/config")
async def get_data_source_config(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get all data source configs (admin)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from src.ai.data_source_config import AIDataSourceService

    service = AIDataSourceService(db)
    return service.get_config()


@router.post("/data-sources/config")
async def update_data_source_config(
    request: DataSourceConfigRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Update data source configs (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from src.ai.data_source_config import AIDataSourceService

    service = AIDataSourceService(db)
    items = [item.model_dump(exclude_none=True) for item in request.sources]
    return service.update_config(items)


@router.get("/data-sources/role-permissions")
async def get_role_permissions(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get all role-permission mappings (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from src.ai.role_permission_service import RolePermissionService

    service = RolePermissionService(db)
    return {"permissions": service.get_all_permissions()}


@router.post("/data-sources/role-permissions")
async def update_role_permissions(
    request: RolePermissionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Batch update role-permission mappings (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from src.ai.role_permission_service import RolePermissionService

    service = RolePermissionService(db)
    items = [item.model_dump() for item in request.permissions]
    service.update_permissions(items)
    _log_permission_change(db, current_user, "datasource_permission", items)
    return {"permissions": service.get_all_permissions()}


# --- Skill Role Permission Endpoints ---


@router.get("/skills/available")
async def get_available_skills(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get skills available to the current user (filtered by role permissions)."""
    from src.ai.skill_permission_service import SkillPermissionService

    service = SkillPermissionService(db)
    allowed_ids = service.get_allowed_skill_ids(current_user.role)
    return {"skill_ids": allowed_ids, "role": current_user.role}


@router.get("/skills/role-permissions")
async def get_skill_role_permissions(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get all role-skill permission mappings (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from src.ai.skill_permission_service import SkillPermissionService

    service = SkillPermissionService(db)
    return {"permissions": service.get_all_permissions()}


@router.post("/skills/role-permissions")
async def update_skill_role_permissions(
    request: SkillPermissionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Batch update role-skill permission mappings (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from src.ai.skill_permission_service import SkillPermissionService

    service = SkillPermissionService(db)
    items = [item.model_dump() for item in request.permissions]
    service.update_permissions(items)
    _log_permission_change(db, current_user, "skill_permission", items)
    return {"permissions": service.get_all_permissions()}


@router.post("/skills/init-admin")
async def init_admin_skill_permissions(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Initialize admin role with all deployed skills (idempotent, admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from src.ai.skill_permission_service import SkillPermissionService

    service = SkillPermissionService(db)
    added = service.init_admin_all_skills()
    return {
        "added": added,
        "message": f"Admin role initialized with {added} new skill permissions",
    }


# --- Access Log Endpoints ---


@router.get("/access-logs")
async def query_access_logs(
    page: int = 1,
    page_size: int = 50,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Query AI access logs (newest first). Admin only.

    Supports filtering by event_type and user_id with pagination.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from src.ai.access_log_service import AIAccessLogService

    svc = AIAccessLogService(db)
    return svc.query_logs(
        tenant_id=current_user.tenant_id,
        event_type=event_type,
        user_id=user_id,
        page=max(1, page),
        page_size=min(max(1, page_size), 100),
    )


# --- Service Status Endpoint ---


@router.get("/service-status")
async def get_service_status(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """聚合基础设施与 **两条 LLM 通道** 的解析结果（见 ``llm_application_channels`` 模块文档）。

    - ``llm_direct``：AI 助手直连 / 内置 LLM（``ai_assistant`` 应用绑定）。
    - ``openclaw``：技能工作流经网关 → Core（``openclaw`` 应用绑定，可被网关固定配置覆盖）。
    - ``ollama``：仅表示本机/容器内 Ollama 服务探活，**不等于**上述通道当前选用的提供商。
    """
    import httpx
    import os

    results: dict = {}
    tid = current_user.tenant_id or ""

    # 1. App backend — if we're responding, we're healthy
    results["backend"] = {"healthy": True, "label": "running"}

    # 2. Ollama — 侧车探活（本地推理运行时）
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                results["ollama"] = {
                    "healthy": True,
                    "label": "running",
                    "models": models,
                    "scope": "local_ollama_runtime_probe",
                }
            else:
                results["ollama"] = {
                    "healthy": False,
                    "label": "unhealthy",
                    "scope": "local_ollama_runtime_probe",
                }
    except Exception as exc:
        logger.warning("Ollama health check failed: %s", exc)
        results["ollama"] = {
            "healthy": False,
            "label": "offline",
            "scope": "local_ollama_runtime_probe",
        }

    # 3. LLM 直连通道（ai_assistant）— 与 get_llm_switcher 绑定一致
    try:
        bridge = get_openclaw_llm_bridge()
        results["llm_direct"] = {
            "llm": bridge.sync_llm_direct_channel_preview(db, tid),
        }
    except Exception as exc:
        logger.debug("llm_direct preview skipped: %s", exc)
        results["llm_direct"] = {"llm": None}

    # 4. OpenClaw 网关 + 该通道解析出的 LLM
    try:
        service = get_openclaw_chat_service(db)
        status = await service.get_status(tenant_id=current_user.tenant_id)
        oc_ok = bool(
            status.available
            and getattr(status, "gateway_reachable", False)
        )
        gw = (
            db.query(AIGateway)
            .filter(
                AIGateway.tenant_id == current_user.tenant_id,
                AIGateway.gateway_type == "openclaw",
                AIGateway.status == "active",
            )
            .first()
        )
        llm_preview: Optional[dict] = None
        try:
            bridge = get_openclaw_llm_bridge()
            llm_preview = bridge.sync_openclaw_llm_preview(db, tid, gw)
        except Exception as prev_exc:
            logger.debug("OpenClaw LLM preview skipped: %s", prev_exc)

        results["openclaw"] = {
            "healthy": oc_ok,
            "label": "running" if oc_ok else "offline",
            "skills_count": len(status.skills) if status.skills else 0,
            "role": "skills_workflow_gateway",
            "llm": llm_preview,
        }
    except Exception as exc:
        logger.warning("OpenClaw status check failed: %s", exc)
        results["openclaw"] = {
            "healthy": False,
            "label": "offline",
            "role": "skills_workflow_gateway",
            "llm": None,
        }

    return results


# --- Workflow CRUD Endpoints ---


def _workflow_to_response(workflow) -> dict:
    """Convert an AIWorkflow model instance to a response dict."""
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description or "",
        "status": workflow.status,
        "is_preset": workflow.is_preset,
        "skill_ids": workflow.skill_ids or [],
        "data_source_auth": workflow.data_source_auth or [],
        "output_modes": workflow.output_modes or [],
        "visible_roles": workflow.visible_roles or [],
        "preset_prompt": workflow.preset_prompt,
        "name_en": workflow.name_en,
        "description_en": workflow.description_en,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else "",
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else "",
        "created_by": workflow.created_by,
    }


def _log_workflow_crud(
    db: Session,
    user: "UserModel",
    event_type: str,
    workflow_id: Optional[str] = None,
    workflow_name: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Record a workflow CRUD operation in AIAccessLog."""
    from src.models.ai_access_log import AIAccessLog as LogModel

    db.add(
        LogModel(
            tenant_id=user.tenant_id,
            user_id=str(user.id),
            user_role=user.role,
            event_type=event_type,
            resource_id=workflow_id,
            resource_name=workflow_name,
            request_type="chat",
            success=success,
            error_message=error_message,
            details=details or {},
        )
    )
    db.commit()


@router.get("/workflows")
async def list_workflows(
    status: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[dict]:
    """List workflows. Non-admin users see only role-visible enabled workflows."""
    from src.ai.workflow_service import WorkflowService

    service = WorkflowService(db)
    is_admin = current_user.role == "admin"
    workflows = service.list_workflows(
        role=current_user.role,
        status=status,
        is_admin=is_admin,
    )

    _log_workflow_crud(
        db,
        current_user,
        event_type="workflow_list",
        details={"count": len(workflows), "filter_status": status},
    )

    return [_workflow_to_response(w) for w in workflows]


@router.post("/workflows", status_code=201)
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new workflow. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from src.ai.workflow_service import WorkflowService

    service = WorkflowService(db)
    workflow = service.create_workflow(request, creator_id=str(current_user.id))

    _log_workflow_crud(
        db,
        current_user,
        event_type="workflow_create",
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        details={"workflow_id": workflow.id, "name": workflow.name},
    )

    return _workflow_to_response(workflow)


@router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update an existing workflow. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from src.ai.workflow_service import WorkflowService

    service = WorkflowService(db)
    workflow = service.update_workflow(workflow_id, request)

    _log_workflow_crud(
        db,
        current_user,
        event_type="workflow_update",
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        details={"workflow_id": workflow.id, "name": workflow.name},
    )

    return _workflow_to_response(workflow)


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Hard-delete a workflow. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from src.ai.workflow_service import WorkflowService

    service = WorkflowService(db)
    service.delete_workflow(workflow_id)

    _log_workflow_crud(
        db,
        current_user,
        event_type="workflow_delete",
        workflow_id=workflow_id,
        details={"workflow_id": workflow_id},
    )

    return {"success": True, "message": f"Workflow {workflow_id} deleted"}


# --- Workflow Stats & Permission Sync Endpoints ---


@router.get("/workflows/{workflow_id}/stats")
async def get_workflow_stats(
    workflow_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get execution stats for a specific workflow."""
    from src.ai.workflow_service import WorkflowService

    service = WorkflowService(db)
    stats = service.get_workflow_stats(workflow_id)

    _log_workflow_crud(
        db,
        current_user,
        event_type="workflow_stats",
        workflow_id=workflow_id,
        details={"workflow_id": workflow_id},
    )

    return {"success": True, "data": stats}


@router.get("/stats/today")
async def get_today_stats(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get current user's today stats."""
    from src.ai.workflow_service import WorkflowService

    service = WorkflowService(db)
    stats = service.get_today_stats(
        user_id=str(current_user.id),
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
    )

    return {"success": True, "data": stats}


class SyncPermissionsRequest(BaseModel):
    """Request body for batch permission sync."""

    permissions: List[dict]


@router.post("/workflows/sync-permissions")
async def sync_permissions(
    request: SyncPermissionsRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Batch sync workflow permissions. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from src.ai.workflow_service import WorkflowService

    service = WorkflowService(db)
    result = service.sync_permissions(request.permissions)

    _log_workflow_crud(
        db,
        current_user,
        event_type="workflow_permission_sync",
        details={
            "permission_count": len(request.permissions),
            "updated_count": result.get("updated_count", 0),
        },
    )

    return {"success": True, "data": result}


@router.post("/workflows/request-authorization", status_code=501)
async def request_authorization(
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Dynamic authorization request (placeholder, not yet implemented)."""
    raise HTTPException(
        status_code=501,
        detail={
            "success": False,
            "error_code": "AUTHORIZATION_NOT_IMPLEMENTED",
            "message": "Dynamic authorization request is not yet implemented",
        },
    )
