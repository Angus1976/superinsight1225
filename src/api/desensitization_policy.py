"""
脱敏策略管理API
基于现有API模式实现策略CRUD操作
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from src.database import get_db
from src.security.controller import SecurityController
from src.models.desensitization import SensitivityPolicy, SensitivityPattern, MaskingRule
from src.schemas.desensitization import (
    SensitivityPolicyCreate,
    SensitivityPolicyUpdate,
    SensitivityPolicyResponse,
    SensitivityPatternCreate,
    MaskingRuleCreate
)

router = APIRouter(prefix="/api/desensitization/policies", tags=["Desensitization Policies"])

@router.post("/", response_model=SensitivityPolicyResponse)
async def create_policy(
    policy: SensitivityPolicyCreate,
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """创建脱敏策略"""
    # 权限检查
    if not await security.check_permission(policy.tenant_id, "desensitization.policy", "create"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # 检查策略名称唯一性
    existing = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.tenant_id == policy.tenant_id,
        SensitivityPolicy.name == policy.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Policy name already exists")
    
    # 创建策略
    db_policy = SensitivityPolicy(
        id=str(uuid.uuid4()),
        name=policy.name,
        tenant_id=policy.tenant_id,
        patterns=[pattern.dict() for pattern in policy.patterns],
        masking_rules=[rule.dict() for rule in policy.masking_rules],
        is_active=policy.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    
    return SensitivityPolicyResponse.from_orm(db_policy)

@router.get("/", response_model=List[SensitivityPolicyResponse])
async def list_policies(
    tenant_id: str = Query(...),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """获取脱敏策略列表"""
    # 权限检查
    if not await security.check_permission(tenant_id, "desensitization.policy", "read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    query = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.tenant_id == tenant_id
    )
    
    if active_only:
        query = query.filter(SensitivityPolicy.is_active == True)
    
    policies = query.offset(skip).limit(limit).all()
    
    return [SensitivityPolicyResponse.from_orm(policy) for policy in policies]

@router.get("/{policy_id}", response_model=SensitivityPolicyResponse)
async def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """获取单个脱敏策略"""
    policy = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.id == policy_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # 权限检查
    if not await security.check_permission(policy.tenant_id, "desensitization.policy", "read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return SensitivityPolicyResponse.from_orm(policy)

@router.put("/{policy_id}", response_model=SensitivityPolicyResponse)
async def update_policy(
    policy_id: str,
    policy_update: SensitivityPolicyUpdate,
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """更新脱敏策略"""
    policy = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.id == policy_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # 权限检查
    if not await security.check_permission(policy.tenant_id, "desensitization.policy", "update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # 更新策略
    update_data = policy_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "patterns" and value:
            setattr(policy, field, [pattern.dict() for pattern in value])
        elif field == "masking_rules" and value:
            setattr(policy, field, [rule.dict() for rule in value])
        else:
            setattr(policy, field, value)
    
    policy.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(policy)
    
    return SensitivityPolicyResponse.from_orm(policy)

@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """删除脱敏策略"""
    policy = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.id == policy_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # 权限检查
    if not await security.check_permission(policy.tenant_id, "desensitization.policy", "delete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    db.delete(policy)
    db.commit()
    
    return {"message": "Policy deleted successfully"}

@router.post("/{policy_id}/activate")
async def activate_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """激活脱敏策略"""
    policy = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.id == policy_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # 权限检查
    if not await security.check_permission(policy.tenant_id, "desensitization.policy", "update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    policy.is_active = True
    policy.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Policy activated successfully"}

@router.post("/{policy_id}/deactivate")
async def deactivate_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """停用脱敏策略"""
    policy = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.id == policy_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # 权限检查
    if not await security.check_permission(policy.tenant_id, "desensitization.policy", "update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    policy.is_active = False
    policy.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Policy deactivated successfully"}

@router.get("/{policy_id}/audit")
async def get_policy_audit_log(
    policy_id: str,
    db: Session = Depends(get_db),
    security: SecurityController = Depends()
):
    """获取策略审计日志"""
    policy = db.query(SensitivityPolicy).filter(
        SensitivityPolicy.id == policy_id
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # 权限检查
    if not await security.check_permission(policy.tenant_id, "desensitization.policy", "audit"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # 查询审计日志
    from src.security.audit_service import EnhancedAuditService
    audit_service = EnhancedAuditService()
    
    audit_logs = await audit_service.query_audit_events(
        resource=f"desensitization_policy:{policy_id}",
        tenant_id=policy.tenant_id
    )
    
    return {"policy_id": policy_id, "audit_logs": audit_logs}