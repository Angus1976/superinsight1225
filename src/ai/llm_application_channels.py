"""
LLM 应用通道解析（与 ``llm_applications.code`` 对齐）

---------------------------------------------------------------------------
两条独立通道（请勿混用绑定表行）
---------------------------------------------------------------------------

1. **AI 助手 · LLM 直连 / 内置回退**（``application_code="ai_assistant"``）

   - 调用链：``get_llm_switcher(application_code="ai_assistant")`` → ``LLMSwitcher``。
   - 绑定：管理台「LLM 配置 → 应用绑定」里 **AI 助手** 应用的优先级链。
   - 无绑定时：与 ``LLMSwitcher.initialize`` 一致，回退到 ``LLMConfigManager.get_config``；
     此处同步预览用「租户单条 ``llm_configurations`` + env merge」近似（见
     ``resolve_ai_assistant_direct_llm_config_sync``）。

2. **OpenClaw · 技能 / 网关 → Core**（``application_code="openclaw"``）

   - 调用链：``OpenClawChatService`` → ``openclaw-gateway`` → OpenClaw Core ``/v1/chat/completions``，
     模型 ID 由 ``OpenClawLLMBridge.sync_resolve_openclaw_chat_model_for_gateway`` 解析。
   - 绑定：管理台 **OpenClaw 网关** 应用；若 AI 集成里为网关 **固定** ``llm_configuration_id``，
     则 **优先于** 本应用绑定（见 ``OpenClawLLMBridge.sync_openclaw_llm_preview``）。

3. **Ollama 容器探活**（``service-status`` 中的 ``ollama`` 字段）

   - 仅表示 **Docker 内 Ollama 服务是否可达**，不表示直连或 OpenClaw 当前选用的模型一定是 Ollama。
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from src.ai.llm_config_manager import configuration_row_to_llm_config
from src.ai.llm_env_merge import merge_llm_config_with_env_defaults
from src.ai.llm_schemas import LLMConfig
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.models.llm_configuration import LLMConfiguration

AI_ASSISTANT_LLM_APPLICATION_CODE = "ai_assistant"
OPENCLAW_LLM_APPLICATION_CODE = "openclaw"

# 与前端 / API 展示一致
SOURCE_APPLICATION_BINDING = "application_binding"
SOURCE_TENANT_DEFAULT_ROW = "tenant_default_row"
SOURCE_CONFIG_MANAGER_FALLBACK = "config_manager_fallback"


def _normalize_tenant_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def get_application_primary_llm_configuration_row(
    db: Session,
    tenant_id: Optional[str],
    application_code: str,
) -> Optional[LLMConfiguration]:
    """
    指定 LLM 应用在绑定表中 **priority 最小** 的活跃配置行（租户 + 全局 NULL 租户）。
    """
    app = db.execute(
        select(LLMApplication).where(
            LLMApplication.code == application_code,
            LLMApplication.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()
    if not app:
        return None

    stmt = (
        select(LLMApplicationBinding)
        .options(selectinload(LLMApplicationBinding.llm_config))
        .where(
            LLMApplicationBinding.application_id == app.id,
            LLMApplicationBinding.is_active == True,  # noqa: E712
        )
        .join(LLMConfiguration)
        .where(LLMConfiguration.is_active == True)  # noqa: E712
        .order_by(LLMApplicationBinding.priority.asc())
    )

    tid = _normalize_tenant_id(tenant_id)
    if tid:
        stmt = stmt.where(
            or_(
                LLMConfiguration.tenant_id == tid,
                LLMConfiguration.tenant_id.is_(None),
            )
        )
    else:
        stmt = stmt.where(LLMConfiguration.tenant_id.is_(None))

    binding = db.execute(stmt).scalars().first()
    if not binding or not binding.llm_config:
        return None
    return binding.llm_config


def get_openclaw_primary_llm_configuration_row(
    db: Session,
    tenant_id: Optional[str],
) -> Optional[LLMConfiguration]:
    return get_application_primary_llm_configuration_row(
        db, tenant_id, OPENCLAW_LLM_APPLICATION_CODE
    )


def resolve_ai_assistant_direct_llm_config_sync(
    db: Session,
    tenant_id: Optional[str],
) -> Tuple[LLMConfig, str]:
    """
    解析 **AI 助手直连** 将使用的主配置（同步、供状态 API）。

    返回 ``(LLMConfig, source)``；``source`` 取值见模块常量。
    """
    row = get_application_primary_llm_configuration_row(
        db, tenant_id, AI_ASSISTANT_LLM_APPLICATION_CODE
    )
    if row and row.config_data:
        cfg = configuration_row_to_llm_config(row)
        return merge_llm_config_with_env_defaults(cfg), SOURCE_APPLICATION_BINDING

    stmt = select(LLMConfiguration).where(
        LLMConfiguration.tenant_id == (tenant_id if tenant_id else None),
        LLMConfiguration.is_active == True,  # noqa: E712
    )
    r = db.execute(stmt).scalar_one_or_none()
    if r and r.config_data:
        cfg = configuration_row_to_llm_config(r)
        return merge_llm_config_with_env_defaults(cfg), SOURCE_TENANT_DEFAULT_ROW

    cfg = LLMConfig()
    return merge_llm_config_with_env_defaults(cfg), SOURCE_CONFIG_MANAGER_FALLBACK
