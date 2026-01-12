"""
Audit Integrity API Endpoints.

Provides REST API endpoints for audit log integrity verification,
tampering detection, and anti-tampering management.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import padding

from src.database.connection import get_db_session
from src.security.audit_service_with_integrity import integrity_audit_service
from src.security.models import AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit/integrity", tags=["audit-integrity"])


# Pydantic Models
class IntegrityVerificationRequest(BaseModel):
    """完整性验证请求"""
    audit_log_id: UUID = Field(..., description="审计日志ID")


class BatchIntegrityVerificationRequest(BaseModel):
    """批量完整性验证请求"""
    tenant_id: str = Field(..., description="租户ID")
    days: int = Field(default=30, ge=1, le=365, description="验证天数")


class TamperingDetectionRequest(BaseModel):
    """篡改检测请求"""
    tenant_id: str = Field(..., description="租户ID")
    days: int = Field(default=30, ge=1, le=365, description="检测天数")


class IntegrityRepairRequest(BaseModel):
    """完整性修复请求"""
    tenant_id: str = Field(..., description="租户ID")
    violation_ids: Optional[List[str]] = Field(None, description="要修复的违规ID列表")


class AuditEventRequest(BaseModel):
    """审计事件请求"""
    user_id: Optional[UUID] = Field(None, description="用户ID")
    tenant_id: str = Field(..., description="租户ID")
    action: str = Field(..., description="审计动作")
    resource_type: str = Field(..., description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


# API Endpoints

@router.post("/log-event")
async def log_audit_event_with_integrity(
    request: AuditEventRequest,
    db: Session = Depends(get_db_session)
):
    """
    记录具有完整性保护的审计事件
    
    创建新的审计日志记录，并自动添加数字签名和哈希验证信息。
    """
    
    try:
        # 验证审计动作
        try:
            action = AuditAction(request.action)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的审计动作: {request.action}"
            )
        
        # 记录审计事件
        result = await integrity_audit_service.log_audit_event_with_integrity(
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            action=action,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            details=request.details,
            db=db
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"记录审计事件失败: {result.get('error', '未知错误')}"
            )
        
        return {
            "success": True,
            "message": "审计事件记录成功",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"记录完整性保护审计事件失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.post("/verify")
async def verify_audit_log_integrity(
    request: IntegrityVerificationRequest,
    db: Session = Depends(get_db_session)
):
    """
    验证单个审计日志的完整性
    
    检查指定审计日志的数字签名和哈希值，确认其未被篡改。
    """
    
    try:
        result = integrity_audit_service.verify_audit_log_integrity(
            audit_log_id=request.audit_log_id,
            db=db
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=404 if "不存在" in result.get("error", "") else 500,
                detail=result.get("error", "验证失败")
            )
        
        verification_result = result["verification_result"]
        
        return {
            "success": True,
            "message": "完整性验证完成",
            "data": {
                "audit_log_id": str(request.audit_log_id),
                "is_valid": verification_result["is_valid"],
                "hash_valid": verification_result["hash_valid"],
                "signature_valid": verification_result["signature_valid"],
                "chain_valid": verification_result["chain_valid"],
                "errors": verification_result["errors"],
                "verification_timestamp": verification_result["verification_timestamp"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证审计日志完整性失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.post("/batch-verify")
async def batch_verify_integrity(
    request: BatchIntegrityVerificationRequest,
    db: Session = Depends(get_db_session)
):
    """
    批量验证租户审计日志完整性
    
    验证指定租户在指定时间范围内所有审计日志的完整性。
    """
    
    try:
        result = integrity_audit_service.batch_verify_tenant_integrity(
            tenant_id=request.tenant_id,
            db=db,
            days=request.days
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "批量验证失败")
            )
        
        verification_result = result["verification_result"]
        
        return {
            "success": True,
            "message": "批量完整性验证完成",
            "data": {
                "tenant_id": request.tenant_id,
                "verification_period_days": request.days,
                "total_logs": result["total_logs"],
                "valid_logs": verification_result["valid_logs"],
                "invalid_logs": verification_result["invalid_logs"],
                "integrity_score": verification_result["integrity_score"],
                "verification_timestamp": verification_result["verification_timestamp"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量验证完整性失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.post("/detect-tampering")
async def detect_audit_tampering(
    request: TamperingDetectionRequest,
    db: Session = Depends(get_db_session)
):
    """
    检测审计日志篡改
    
    分析指定租户的审计日志，检测可能的篡改模式和异常行为。
    """
    
    try:
        result = integrity_audit_service.detect_audit_tampering(
            tenant_id=request.tenant_id,
            db=db,
            days=request.days
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "篡改检测失败")
            )
        
        detection_result = result["detection_result"]
        
        return {
            "success": True,
            "message": "篡改检测完成",
            "data": {
                "tenant_id": request.tenant_id,
                "analysis_period_days": request.days,
                "total_logs_analyzed": detection_result["total_logs_analyzed"],
                "overall_risk_level": detection_result["overall_risk_level"],
                "risk_score": detection_result.get("risk_score", 0),
                "integrity_violations_count": len(detection_result["integrity_violations"]),
                "suspicious_patterns_count": len(detection_result["suspicious_patterns"]),
                "integrity_violations": detection_result["integrity_violations"],
                "suspicious_patterns": detection_result["suspicious_patterns"],
                "analysis_timestamp": detection_result["analysis_timestamp"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检测审计日志篡改失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.get("/report/{tenant_id}")
async def generate_integrity_report(
    tenant_id: str,
    days: int = Query(default=30, ge=1, le=365, description="报告天数"),
    db: Session = Depends(get_db_session)
):
    """
    生成完整性报告
    
    为指定租户生成详细的审计日志完整性报告，包括风险评估和改进建议。
    """
    
    try:
        result = integrity_audit_service.generate_integrity_report(
            tenant_id=tenant_id,
            db=db,
            days=days
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "生成报告失败")
            )
        
        return {
            "success": True,
            "message": "完整性报告生成成功",
            "data": result["report"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成完整性报告失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.post("/repair")
async def repair_integrity_violations(
    request: IntegrityRepairRequest,
    db: Session = Depends(get_db_session)
):
    """
    修复完整性违规
    
    重新生成指定审计日志的完整性保护信息，修复检测到的违规问题。
    """
    
    try:
        result = integrity_audit_service.repair_integrity_violations(
            tenant_id=request.tenant_id,
            db=db,
            violation_ids=request.violation_ids
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "修复失败")
            )
        
        return {
            "success": True,
            "message": "完整性违规修复完成",
            "data": {
                "tenant_id": request.tenant_id,
                "total_processed": result["total_processed"],
                "repaired_count": len(result["repaired_logs"]),
                "failed_count": len(result["failed_repairs"]),
                "repaired_logs": result["repaired_logs"],
                "failed_repairs": result["failed_repairs"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修复完整性违规失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.get("/statistics/{tenant_id}")
async def get_integrity_statistics(
    tenant_id: str,
    days: int = Query(default=30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db_session)
):
    """
    获取完整性统计信息
    
    获取指定租户的审计日志完整性统计数据，包括保护率和风险评估。
    """
    
    try:
        result = integrity_audit_service.get_integrity_statistics(
            tenant_id=tenant_id,
            db=db,
            days=days
        )
        
        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "获取统计信息失败")
            )
        
        return {
            "success": True,
            "message": "完整性统计信息获取成功",
            "data": result["statistics"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取完整性统计信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.get("/health")
async def integrity_service_health():
    """
    完整性服务健康检查
    
    检查审计完整性服务的运行状态和配置。
    """
    
    try:
        # 检查完整性服务状态
        service_status = {
            "service_name": "audit_integrity_service",
            "status": "healthy",
            "integrity_enabled": integrity_audit_service.integrity_enabled,
            "hash_algorithm": integrity_audit_service.integrity_service.hash_algorithm,
            "chain_hash_enabled": integrity_audit_service.integrity_service.chain_hash_enabled,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 检查密钥状态
        try:
            # 尝试生成测试签名来验证密钥
            test_data = "health_check_test"
            test_signature = integrity_audit_service.integrity_service.private_key.sign(
                test_data.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(integrity_audit_service.integrity_service.signature_algorithm),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                integrity_audit_service.integrity_service.signature_algorithm
            )
            service_status["key_status"] = "valid"
        except Exception as e:
            service_status["key_status"] = f"error: {str(e)}"
            service_status["status"] = "degraded"
        
        return {
            "success": True,
            "message": "完整性服务健康检查完成",
            "data": service_status
        }
        
    except Exception as e:
        logger.error(f"完整性服务健康检查失败: {e}")
        return {
            "success": False,
            "message": "完整性服务健康检查失败",
            "error": str(e),
            "data": {
                "service_name": "audit_integrity_service",
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat()
            }
        }


@router.get("/config")
async def get_integrity_configuration():
    """
    获取完整性配置信息
    
    返回当前审计完整性服务的配置参数。
    """
    
    try:
        config = {
            "integrity_enabled": integrity_audit_service.integrity_enabled,
            "hash_algorithm": integrity_audit_service.integrity_service.hash_algorithm,
            "signature_algorithm": "RSA-PSS-SHA256",
            "chain_hash_enabled": integrity_audit_service.integrity_service.chain_hash_enabled,
            "key_size": 2048,  # RSA密钥大小
            "service_version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "message": "完整性配置获取成功",
            "data": config
        }
        
    except Exception as e:
        logger.error(f"获取完整性配置失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内部服务器错误: {str(e)}"
        )