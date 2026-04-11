"""
Resolve OpenClaw-related URLs/tokens: LLM 库表（租户 → 全局）→ 环境变量 → 默认值。

与 docker-compose 中 OPENCLAW_* 对齐；生产环境可由编排注入 env，或由管理员写入
``llm_configurations.config_data.openclaw``。
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.models.llm_configuration import LLMConfiguration

DEFAULT_GATEWAY_BASE = "http://openclaw-gateway:3000"
DEFAULT_CORE_URL = "http://openclaw-core:18789"
DEFAULT_AGENT_URL = "http://openclaw-agent:8080"


def _openclaw_from_llm_row(config_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not config_data or not isinstance(config_data, dict):
        return {}
    oc = config_data.get("openclaw")
    if isinstance(oc, dict):
        return oc
    return {}


def get_openclaw_dict_from_llm_db(db: Session, tenant_id: Optional[str]) -> Dict[str, Any]:
    """合并租户级与全局级 ``config_data.openclaw``：租户字段优先。"""
    merged: Dict[str, Any] = {}
    if tenant_id:
        row = (
            db.query(LLMConfiguration)
            .filter(
                LLMConfiguration.tenant_id == tenant_id,
                LLMConfiguration.is_active.is_(True),
            )
            .first()
        )
        if row:
            merged.update(_openclaw_from_llm_row(row.config_data))
    row_g = (
        db.query(LLMConfiguration)
        .filter(
            LLMConfiguration.tenant_id.is_(None),
            LLMConfiguration.is_active.is_(True),
        )
        .first()
    )
    if row_g:
        g = _openclaw_from_llm_row(row_g.config_data)
        for k, v in g.items():
            if merged.get(k) in (None, "") and v not in (None, ""):
                merged[k] = v
    return merged


def resolve_openclaw_gateway_base_url(
    db: Session,
    tenant_id: Optional[str],
    gateway_configuration: Optional[Dict[str, Any]] = None,
) -> str:
    """后端调用兼容网关的根 URL（不含路径）。

    顺序：``llm_configurations.config_data.openclaw.gateway_base_url`` →
    ``AIGateway.configuration.network_settings.base_url`` →
    ``OPENCLAW_GATEWAY_BASE_URL`` → 默认。
    """
    d = get_openclaw_dict_from_llm_db(db, tenant_id)
    url = (d.get("gateway_base_url") or "").strip()
    if url:
        return url.rstrip("/")
    cfg = gateway_configuration or {}
    net = cfg.get("network_settings") or {}
    gbu = (net.get("base_url") or "").strip()
    if gbu:
        return gbu.rstrip("/")
    env = (os.environ.get("OPENCLAW_GATEWAY_BASE_URL") or "").strip()
    if env:
        return env.rstrip("/")
    return DEFAULT_GATEWAY_BASE


def resolve_openclaw_core_url(db: Session, tenant_id: Optional[str]) -> str:
    """与网关容器 ``OPENCLAW_CORE_URL`` 对应；供默认网关配置与文档一致。"""
    d = get_openclaw_dict_from_llm_db(db, tenant_id)
    url = (d.get("core_url") or "").strip()
    if url:
        return url.rstrip("/")
    env = (os.environ.get("OPENCLAW_CORE_URL") or "").strip()
    if env:
        return env.rstrip("/")
    return DEFAULT_CORE_URL


def resolve_openclaw_gateway_token(db: Session, tenant_id: Optional[str]) -> str:
    """Bearer token，需与 OpenClaw Core ``gateway.auth.token`` 一致。"""
    d = get_openclaw_dict_from_llm_db(db, tenant_id)
    tok = (d.get("gateway_token") or "").strip()
    if tok:
        return tok
    env = (os.environ.get("OPENCLAW_GATEWAY_TOKEN") or "").strip()
    if env:
        return env
    return ""


def resolve_openclaw_agent_url(db: Session, tenant_id: Optional[str]) -> str:
    d = get_openclaw_dict_from_llm_db(db, tenant_id)
    url = (d.get("agent_url") or "").strip()
    if url:
        return url.rstrip("/")
    env = (os.environ.get("OPENCLAW_AGENT_URL") or "").strip()
    if env:
        return env.rstrip("/")
    return DEFAULT_AGENT_URL


