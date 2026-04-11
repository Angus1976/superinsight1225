"""
Ensure a default OpenClaw gateway exists per tenant and seed the skill library.

Fixes empty skill lists when admins never registered a gateway or migration left
ai_skills empty. Idempotent.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from src.models.ai_integration import AIGateway, AISkill
from src.ai_integration.gateway_manager import GatewayManager
from src.ai_integration.clawhub_seed_skills import seed_clawhub_skills
from src.ai.skill_permission_service import SkillPermissionService
from src.ai.openclaw_integration_settings import (
    resolve_openclaw_agent_url,
    resolve_openclaw_gateway_base_url,
)

logger = logging.getLogger(__name__)

DEFAULT_GATEWAY_NAME = "OpenClaw (SuperInsight)"


def openclaw_auto_bootstrap_enabled() -> bool:
    """When false, skip automatic gateway+skill seeding (used in unit tests)."""
    return os.environ.get("OPENCLAW_AUTO_BOOTSTRAP_SKILLS", "1").lower() not in (
        "0",
        "false",
        "no",
    )


def _default_gateway_configuration(db: Session, tenant_id: str) -> dict:
    """Minimal config that passes GatewayManager validation (channels + network_settings).

    ``base_url`` / ``agent_url`` 来自 LLM 库 ``config_data.openclaw``，其次环境变量，最后默认。
    """
    base_url = resolve_openclaw_gateway_base_url(db, tenant_id, None)
    agent_url = resolve_openclaw_agent_url(db, tenant_id)
    return {
        "channels": [
            {
                "channel_type": "webchat",
                "enabled": False,
                "credentials": {},
                "settings": {},
            },
        ],
        "network_settings": {
            "base_url": base_url,
            "host": "openclaw-gateway",
            "port": 3000,
            "protocol": "http",
        },
        "agent_url": agent_url,
    }


def ensure_default_openclaw_gateway(db: Session, tenant_id: str) -> AIGateway:
    """Return active OpenClaw gateway for tenant; create and activate if missing."""
    existing = (
        db.query(AIGateway)
        .filter(
            AIGateway.tenant_id == tenant_id,
            AIGateway.gateway_type == "openclaw",
        )
        .order_by(AIGateway.created_at.asc())
        .first()
    )
    if existing:
        if existing.status != "active":
            existing.status = "active"
            db.commit()
            db.refresh(existing)
        return existing

    manager = GatewayManager(db)
    gateway, _credentials = manager.register_gateway(
        name=DEFAULT_GATEWAY_NAME,
        gateway_type="openclaw",
        tenant_id=tenant_id,
        configuration=_default_gateway_configuration(db, tenant_id),
    )
    gateway.status = "active"
    db.commit()
    db.refresh(gateway)
    logger.info("Created default OpenClaw gateway %s for tenant %s", gateway.id, tenant_id)
    return gateway


def bootstrap_openclaw_skill_library(db: Session, tenant_id: str) -> dict:
    """Ensure gateway, seed ClawHub catalog skills, grant admin permissions.

    Idempotent. Returns counts and gateway_id.
    """
    gateway = ensure_default_openclaw_gateway(db, tenant_id)
    seed_result = seed_clawhub_skills(db, gateway.id)
    perm_service = SkillPermissionService(db)
    perm_added = perm_service.init_admin_all_skills()
    return {
        "gateway_id": gateway.id,
        "added": seed_result.get("added", 0),
        "skipped": seed_result.get("skipped", 0),
        "admin_permissions_added": perm_added,
    }


def should_auto_bootstrap_skills(db: Session, tenant_id: str) -> bool:
    """True if tenant has no active gateway or no non-removed skills on that gateway."""
    if not openclaw_auto_bootstrap_enabled():
        return False
    gateway = (
        db.query(AIGateway)
        .filter(
            AIGateway.tenant_id == tenant_id,
            AIGateway.gateway_type == "openclaw",
            AIGateway.status == "active",
        )
        .first()
    )
    if not gateway:
        return True
    n = (
        db.query(AISkill)
        .filter(AISkill.gateway_id == gateway.id, AISkill.status != "removed")
        .count()
    )
    return n == 0
