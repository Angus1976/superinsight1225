"""
Enhanced Audit Service with Integrity Protection.

Extends the existing audit service to include anti-tampering features
through digital signatures and hash-based integrity verification.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from src.security.audit_service import EnhancedAuditService, RiskLevel
from src.security.audit_integrity import audit_integrity_service
from src.security.models import AuditAction, AuditLogModel

logger = logging.getLogger(__name__)


class IntegrityProtectedAuditService(EnhancedAuditService):
    """
    具有完整性保护的审计服务
    
    在现有增强审计服务基础上添加防篡改功能，包括：
    - 数字签名
    - 哈希验证
    - 链式完整性检查
    - 篡改检测
    """
    
    def __init__(self):
        super().__init__()
        self.integrity_service = audit_integrity_service
        self.integrity_enabled = True
        
    async def log_audit_event_with_integrity(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        记录具有完整性保护的审计事件
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            action: 审计动作
            resource_type: 资源类型
            resource_id: 资源ID
            ip_address: IP地址
            user_agent: 用户代理
            details: 详细信息
            db: 数据库会话
            
        Returns:
            审计结果，包含完整性信息
        """
        
        try:
            # 首先使用增强审计服务记录基础信息
            base_result = await self.log_enhanced_audit_event(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                db=db
            )
            
            if base_result.get("status") != "success":
                return base_result
            
            # 获取创建的审计日志
            audit_log_id = base_result.get("audit_log_id")
            if not audit_log_id:
                return {
                    "status": "error",
                    "error": "无法获取审计日志ID"
                }
            
            # 从数据库重新获取审计日志对象（确保包含所有字段）
            from sqlalchemy import select
            stmt = select(AuditLogModel).where(AuditLogModel.id == audit_log_id)
            audit_log = db.execute(stmt).scalar_one_or_none()
            
            if not audit_log:
                return {
                    "status": "error",
                    "error": "无法找到创建的审计日志"
                }
            
            # 生成完整性保护信息
            if self.integrity_enabled:
                integrity_data = self.integrity_service.sign_audit_log(audit_log)
                
                # 更新审计日志的details字段，添加完整性信息
                if not audit_log.details:
                    audit_log.details = {}
                
                audit_log.details["integrity"] = integrity_data
                
                # 保存更新
                db.commit()
                
                return {
                    **base_result,
                    "integrity_protected": True,
                    "integrity_data": integrity_data
                }
            else:
                return {
                    **base_result,
                    "integrity_protected": False,
                    "message": "完整性保护已禁用"
                }
                
        except Exception as e:
            if db:
                db.rollback()
            
            logger.error(f"记录完整性保护审计事件失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "integrity_protected": False
            }
    
    def verify_audit_log_integrity(
        self,
        audit_log_id: UUID,
        db: Session
    ) -> Dict[str, Any]:
        """
        验证单个审计日志的完整性
        
        Args:
            audit_log_id: 审计日志ID
            db: 数据库会话
            
        Returns:
            验证结果
        """
        
        try:
            # 获取审计日志
            from sqlalchemy import select
            stmt = select(AuditLogModel).where(AuditLogModel.id == audit_log_id)
            audit_log = db.execute(stmt).scalar_one_or_none()
            
            if not audit_log:
                return {
                    "status": "error",
                    "error": "审计日志不存在"
                }
            
            # 获取完整性数据
            integrity_data = audit_log.details.get("integrity")
            if not integrity_data:
                return {
                    "status": "error",
                    "error": "审计日志缺少完整性数据"
                }
            
            # 验证完整性
            verification_result = self.integrity_service.verify_audit_log_integrity(
                audit_log, integrity_data
            )
            
            return {
                "status": "success",
                "audit_log_id": str(audit_log_id),
                "verification_result": verification_result
            }
            
        except Exception as e:
            logger.error(f"验证审计日志完整性失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def batch_verify_tenant_integrity(
        self,
        tenant_id: str,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        批量验证租户审计日志完整性
        
        Args:
            tenant_id: 租户ID
            db: 数据库会话
            days: 验证天数
            
        Returns:
            批量验证结果
        """
        
        try:
            from datetime import timedelta
            from sqlalchemy import select, and_
            
            # 查询指定时间范围内的审计日志
            start_date = datetime.utcnow() - timedelta(days=days)
            
            stmt = select(AuditLogModel).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= start_date
                )
            ).order_by(AuditLogModel.timestamp)
            
            audit_logs = db.execute(stmt).scalars().all()
            
            if not audit_logs:
                return {
                    "status": "success",
                    "message": "没有找到审计日志",
                    "total_logs": 0,
                    "verification_result": {}
                }
            
            # 批量验证
            verification_result = self.integrity_service.batch_verify_integrity(audit_logs, db)
            
            return {
                "status": "success",
                "tenant_id": tenant_id,
                "verification_period_days": days,
                "total_logs": len(audit_logs),
                "verification_result": verification_result
            }
            
        except Exception as e:
            logger.error(f"批量验证租户审计日志完整性失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def detect_audit_tampering(
        self,
        tenant_id: str,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        检测审计日志篡改
        
        Args:
            tenant_id: 租户ID
            db: 数据库会话
            days: 检测天数
            
        Returns:
            篡改检测结果
        """
        
        try:
            detection_result = self.integrity_service.detect_tampering_patterns(
                tenant_id, db, days
            )
            
            return {
                "status": "success",
                "detection_result": detection_result
            }
            
        except Exception as e:
            logger.error(f"检测审计日志篡改失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def generate_integrity_report(
        self,
        tenant_id: str,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        生成完整性报告
        
        Args:
            tenant_id: 租户ID
            db: 数据库会话
            days: 报告天数
            
        Returns:
            完整性报告
        """
        
        try:
            report = self.integrity_service.generate_integrity_report(
                tenant_id, db, days
            )
            
            return {
                "status": "success",
                "report": report
            }
            
        except Exception as e:
            logger.error(f"生成完整性报告失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def repair_integrity_violations(
        self,
        tenant_id: str,
        db: Session,
        violation_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        修复完整性违规
        
        Args:
            tenant_id: 租户ID
            db: 数据库会话
            violation_ids: 要修复的违规ID列表（可选）
            
        Returns:
            修复结果
        """
        
        try:
            from sqlalchemy import select, and_
            
            repair_result = {
                "status": "success",
                "tenant_id": tenant_id,
                "repaired_logs": [],
                "failed_repairs": [],
                "total_processed": 0
            }
            
            # 如果指定了违规ID，只处理这些日志
            if violation_ids:
                stmt = select(AuditLogModel).where(
                    and_(
                        AuditLogModel.tenant_id == tenant_id,
                        AuditLogModel.id.in_([UUID(vid) for vid in violation_ids])
                    )
                )
            else:
                # 否则处理所有缺少完整性数据的日志
                stmt = select(AuditLogModel).where(
                    AuditLogModel.tenant_id == tenant_id
                )
            
            audit_logs = db.execute(stmt).scalars().all()
            
            for audit_log in audit_logs:
                try:
                    repair_result["total_processed"] += 1
                    
                    # 检查是否需要修复
                    integrity_data = audit_log.details.get("integrity")
                    needs_repair = False
                    
                    if not integrity_data:
                        needs_repair = True
                    else:
                        # 验证现有完整性数据
                        verification = self.integrity_service.verify_audit_log_integrity(
                            audit_log, integrity_data
                        )
                        if not verification["is_valid"]:
                            needs_repair = True
                    
                    if needs_repair:
                        # 重新生成完整性数据
                        new_integrity_data = self.integrity_service.sign_audit_log(audit_log)
                        
                        # 更新审计日志
                        if not audit_log.details:
                            audit_log.details = {}
                        
                        audit_log.details["integrity"] = new_integrity_data
                        audit_log.details["integrity_repaired"] = {
                            "repaired_at": datetime.utcnow().isoformat(),
                            "reason": "integrity_violation_repair"
                        }
                        
                        repair_result["repaired_logs"].append({
                            "log_id": str(audit_log.id),
                            "repaired_at": datetime.utcnow().isoformat()
                        })
                    
                except Exception as e:
                    repair_result["failed_repairs"].append({
                        "log_id": str(audit_log.id),
                        "error": str(e)
                    })
            
            # 提交所有修复
            db.commit()
            
            return repair_result
            
        except Exception as e:
            if db:
                db.rollback()
            
            logger.error(f"修复完整性违规失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_integrity_statistics(
        self,
        tenant_id: str,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取完整性统计信息
        
        Args:
            tenant_id: 租户ID
            db: 数据库会话
            days: 统计天数
            
        Returns:
            完整性统计
        """
        
        try:
            from datetime import timedelta
            from sqlalchemy import select, and_, func
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 总审计日志数
            total_logs_stmt = select(func.count(AuditLogModel.id)).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= start_date
                )
            )
            total_logs = db.execute(total_logs_stmt).scalar() or 0
            
            # 具有完整性保护的日志数
            protected_logs_stmt = select(func.count(AuditLogModel.id)).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.details.has_key("integrity")
                )
            )
            protected_logs = db.execute(protected_logs_stmt).scalar() or 0
            
            # 计算保护率
            protection_rate = (protected_logs / total_logs * 100) if total_logs > 0 else 0
            
            # 获取最近的篡改检测结果
            detection_result = self.detect_audit_tampering(tenant_id, db, days)
            
            statistics = {
                "tenant_id": tenant_id,
                "analysis_period_days": days,
                "total_audit_logs": total_logs,
                "protected_logs": protected_logs,
                "unprotected_logs": total_logs - protected_logs,
                "protection_rate_percent": round(protection_rate, 2),
                "integrity_status": "good" if protection_rate >= 95 else "needs_attention",
                "last_analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            # 添加篡改检测统计
            if detection_result.get("status") == "success":
                detection_data = detection_result["detection_result"]
                statistics.update({
                    "tampering_risk_level": detection_data["overall_risk_level"],
                    "integrity_violations_count": len(detection_data["integrity_violations"]),
                    "suspicious_patterns_count": len(detection_data["suspicious_patterns"]),
                    "risk_score": detection_data.get("risk_score", 0)
                })
            
            return {
                "status": "success",
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"获取完整性统计信息失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# 全局完整性保护审计服务实例
integrity_audit_service = IntegrityProtectedAuditService()