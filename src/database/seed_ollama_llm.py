"""
Idempotent seed: two local Ollama Qwen configs (7B + 1.5B) and per-app bindings.

Docker 内 Ollama 服务名一般为 ``ollama``；本机直连可用环境变量覆盖。
"""

from __future__ import annotations

import os

from sqlalchemy import select

from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.models.llm_configuration import LLMConfiguration
from src.ai.llm_application_channels import OPENCLAW_LLM_APPLICATION_CODE


def ensure_openclaw_llm_application(session) -> LLMApplication:
    """注册 OpenClaw 为独立 LLM 应用，便于在管理台绑定模型（与网关解析一致）。"""
    row = session.execute(
        select(LLMApplication).where(LLMApplication.code == OPENCLAW_LLM_APPLICATION_CODE)
    ).scalar_one_or_none()
    if row:
        row.is_active = True
        if not row.name:
            row.name = "OpenClaw 网关"
        return row
    app = LLMApplication(
        code=OPENCLAW_LLM_APPLICATION_CODE,
        name="OpenClaw 网关",
        description="OpenClaw 智能体网关（技能工作流）使用的 LLM；未在网关上固定配置时由此应用绑定决定模型。",
        llm_usage_pattern="与 AI 助手中「智能问数」等 OpenClaw 模式对应",
        is_active=True,
    )
    session.add(app)
    session.flush()
    return app


def _ollama_base_v1() -> str:
    raw = (os.environ.get("OLLAMA_BASE_URL") or "http://ollama:11434").rstrip("/")
    return raw if raw.endswith("/v1") else f"{raw}/v1"


def _used_priorities(session, application_id) -> set[int]:
    rows = session.execute(
        select(LLMApplicationBinding.priority).where(
            LLMApplicationBinding.application_id == application_id,
            LLMApplicationBinding.is_active == True,  # noqa: E712
        )
    ).scalars().all()
    return set(rows)


def _next_free_priority(used: set[int], min_priority: int) -> int:
    p = min_priority
    while p <= 99 and p in used:
        p += 1
    if p > 99:
        raise RuntimeError("No free binding priority (1–99) for LLM application")
    return p


def _ensure_config(
    session,
    name: str,
    model_name: str,
    base_v1: str,
) -> LLMConfiguration:
    row = session.execute(
        select(LLMConfiguration).where(LLMConfiguration.name == name)
    ).scalar_one_or_none()
    payload = {
        "provider": "ollama",
        "base_url": base_v1,
        "model_name": model_name,
        "api_key": "ollama",
    }
    if row:
        row.is_active = True
        row.provider = "ollama"
        row.default_method = "local_ollama"
        merged = dict(row.config_data or {})
        merged.update(payload)
        row.config_data = merged
    else:
        row = LLMConfiguration(
            name=name,
            provider="ollama",
            default_method="local_ollama",
            config_data=payload,
            is_active=True,
        )
        session.add(row)
    session.flush()
    return row


def _ensure_binding(
    session,
    application_id,
    cfg: LLMConfiguration,
    min_priority: int,
) -> int:
    existing = session.execute(
        select(LLMApplicationBinding).where(
            LLMApplicationBinding.application_id == application_id,
            LLMApplicationBinding.llm_config_id == cfg.id,
        )
    ).scalar_one_or_none()
    if existing:
        existing.is_active = True
        return existing.priority

    used = _used_priorities(session, application_id)
    p = _next_free_priority(used, min_priority)
    session.add(
        LLMApplicationBinding(
            llm_config_id=cfg.id,
            application_id=application_id,
            priority=p,
            max_retries=1,
            timeout_seconds=60,
            is_active=True,
        )
    )
    session.flush()
    return p


def seed_ollama_qwen_pair(session) -> None:
    """
    Upsert ``Ollama qwen2.5:7b`` and ``Ollama qwen2.5:1.5b``, bind to all active apps.

    同一应用内保证 7B 的 priority 小于 1.5B（先试 7B，再降级 1.5B）。
    """
    ensure_openclaw_llm_application(session)
    base_v1 = _ollama_base_v1()
    cfg_7 = _ensure_config(session, "Ollama qwen2.5:7b", "qwen2.5:7b", base_v1)
    cfg_15 = _ensure_config(session, "Ollama qwen2.5:1.5b", "qwen2.5:1.5b", base_v1)

    apps = session.execute(
        select(LLMApplication).where(LLMApplication.is_active == True)  # noqa: E712
    ).scalars().all()

    for app in apps:
        p7 = _ensure_binding(session, app.id, cfg_7, min_priority=2)
        _ensure_binding(session, app.id, cfg_15, min_priority=max(3, p7 + 1))
