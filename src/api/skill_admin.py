"""
Skill Admin API — manage OpenClaw gateway skills.

Provides endpoints for listing, syncing, executing, and toggling skill status.
All queries enforce tenant isolation via JWT token.

Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 4.3, 5.1, 5.2, 5.3
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.database.connection import get_db
from src.models.ai_integration import AIGateway, AISkill
from src.security.models import UserModel
from src.ai_integration.skill_sync_service import SkillSyncService
from src.ai_integration.schemas import (
    ExecuteRequest,
    ExecuteResultResponse,
    SkillDetailResponse,
    SkillListResponse,
    StatusToggle,
    SyncResultResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/skills", tags=["Skill Admin"])


# --- Helpers ---


def _get_active_gateway(db: Session, tenant_id: str) -> AIGateway:
    """Find the active openclaw gateway for a tenant, or raise 404."""
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
        raise HTTPException(status_code=404, detail="未找到活跃的 OpenClaw 网关")
    return gateway


def _build_skill_detail(skill: AISkill, gateway: AIGateway) -> SkillDetailResponse:
    """Build a SkillDetailResponse from a DB skill and its gateway."""
    config = skill.configuration or {}
    return SkillDetailResponse(
        id=skill.id,
        name=skill.name,
        version=skill.version,
        status=skill.status,
        description=config.get("description"),
        category=config.get("category"),
        gateway_id=gateway.id,
        gateway_name=gateway.name,
        deployed_at=skill.deployed_at,
        created_at=skill.created_at,
    )


def _find_skill_for_tenant(
    db: Session, skill_id: str, tenant_id: str,
) -> tuple[AISkill, AIGateway]:
    """Locate a skill by ID and verify it belongs to the tenant's gateway."""
    skill = db.query(AISkill).filter(AISkill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    gateway = (
        db.query(AIGateway)
        .filter(
            AIGateway.id == skill.gateway_id,
            AIGateway.tenant_id == tenant_id,
        )
        .first()
    )
    if not gateway:
        raise HTTPException(status_code=404, detail="技能不属于当前租户")

    return skill, gateway


# --- Endpoints ---


@router.get("/", response_model=SkillListResponse)
async def list_skills(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SkillListResponse:
    """Return skills under the tenant's active openclaw gateway.

    Ordered by deployed_at DESC. Excludes removed skills.
    Requirements: 1.1, 1.3, 1.4, 2.1, 2.2
    """
    gateway = (
        db.query(AIGateway)
        .filter(
            AIGateway.tenant_id == current_user.tenant_id,
            AIGateway.gateway_type == "openclaw",
            AIGateway.status == "active",
        )
        .first()
    )
    if not gateway:
        return SkillListResponse(skills=[], total=0)

    skills = (
        db.query(AISkill)
        .filter(AISkill.gateway_id == gateway.id, AISkill.status != "removed")
        .order_by(AISkill.deployed_at.desc())
        .all()
    )

    items = [_build_skill_detail(s, gateway) for s in skills]
    return SkillListResponse(skills=items, total=len(items))


@router.post("/sync", response_model=SyncResultResponse)
async def sync_skills(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyncResultResponse:
    """Sync skills from the OpenClaw Agent into the database.

    Requirements: 3.1–3.7
    """
    gateway = _get_active_gateway(db, current_user.tenant_id)
    service = SkillSyncService(db)
    result = await service.sync_from_agent(gateway)
    return SyncResultResponse(**result)


@router.post("/{skill_id}/execute", response_model=ExecuteResultResponse)
async def execute_skill(
    skill_id: str,
    body: ExecuteRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecuteResultResponse:
    """Execute a deployed skill via the Agent.

    Rejects non-deployed skills with 400.
    Requirements: 4.1–4.6
    """
    skill, gateway = _find_skill_for_tenant(db, skill_id, current_user.tenant_id)

    if skill.status != "deployed":
        raise HTTPException(status_code=400, detail="技能未部署，无法执行")

    service = SkillSyncService(db)
    result = await service.execute_skill(skill, gateway, body.parameters)
    return ExecuteResultResponse(**result)


@router.patch("/{skill_id}/status", response_model=SkillDetailResponse)
async def toggle_skill_status(
    skill_id: str,
    body: StatusToggle,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SkillDetailResponse:
    """Toggle a skill's status between deployed and pending.

    Requirements: 5.1, 5.2, 5.3
    """
    skill, gateway = _find_skill_for_tenant(db, skill_id, current_user.tenant_id)

    skill.status = body.status
    db.commit()
    db.refresh(skill)

    return _build_skill_detail(skill, gateway)
