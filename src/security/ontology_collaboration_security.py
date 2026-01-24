"""
本体专家协作安全集成模块

提供专家协作功能的安全控制：
- 基于角色的访问控制 (RBAC)
- 基于专业领域的授权
- 审计日志集成
- 加密完整性验证

Validates: Task 27.4 - Integrate with security system
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

from src.security.models import AuditAction
from src.security.audit_service import AuditService
from src.security.audit_integrity import AuditIntegrityService
from src.collaboration.audit_service import AuditService as CollaborationAuditService

logger = logging.getLogger(__name__)


class OntologyPermission(str, Enum):
    """本体协作权限类型"""
    # 专家管理权限
    EXPERT_VIEW = "ontology.expert.view"
    EXPERT_CREATE = "ontology.expert.create"
    EXPERT_UPDATE = "ontology.expert.update"
    EXPERT_DELETE = "ontology.expert.delete"
    EXPERT_RECOMMEND = "ontology.expert.recommend"
    
    # 模板管理权限
    TEMPLATE_VIEW = "ontology.template.view"
    TEMPLATE_CREATE = "ontology.template.create"
    TEMPLATE_UPDATE = "ontology.template.update"
    TEMPLATE_DELETE = "ontology.template.delete"
    TEMPLATE_INSTANTIATE = "ontology.template.instantiate"
    TEMPLATE_CUSTOMIZE = "ontology.template.customize"
    TEMPLATE_EXPORT = "ontology.template.export"
    TEMPLATE_IMPORT = "ontology.template.import"
    
    # 协作编辑权限
    COLLABORATION_JOIN = "ontology.collaboration.join"
    COLLABORATION_EDIT = "ontology.collaboration.edit"
    COLLABORATION_LOCK = "ontology.collaboration.lock"
    COLLABORATION_RESOLVE_CONFLICT = "ontology.collaboration.resolve_conflict"
    
    # 审批工作流权限
    APPROVAL_VIEW = "ontology.approval.view"
    APPROVAL_CREATE = "ontology.approval.create"
    APPROVAL_APPROVE = "ontology.approval.approve"
    APPROVAL_REJECT = "ontology.approval.reject"
    APPROVAL_MANAGE_CHAIN = "ontology.approval.manage_chain"
    
    # 验证规则权限
    VALIDATION_VIEW = "ontology.validation.view"
    VALIDATION_CREATE = "ontology.validation.create"
    VALIDATION_UPDATE = "ontology.validation.update"
    VALIDATION_DELETE = "ontology.validation.delete"
    
    # 合规模板权限
    COMPLIANCE_VIEW = "ontology.compliance.view"
    COMPLIANCE_APPLY = "ontology.compliance.apply"
    COMPLIANCE_REPORT = "ontology.compliance.report"
    
    # 影响分析权限
    IMPACT_VIEW = "ontology.impact.view"
    IMPACT_ANALYZE = "ontology.impact.analyze"
    
    # 审计权限
    AUDIT_VIEW = "ontology.audit.view"
    AUDIT_EXPORT = "ontology.audit.export"
    AUDIT_ROLLBACK = "ontology.audit.rollback"
    
    # 管理员权限
    ADMIN_ALL = "ontology.admin.all"


class OntologyRole(str, Enum):
    """本体协作角色类型"""
    # 系统角色
    ONTOLOGY_ADMIN = "ontology_admin"           # 本体管理员
    ONTOLOGY_EXPERT = "ontology_expert"         # 本体专家
    ONTOLOGY_REVIEWER = "ontology_reviewer"     # 本体审核员
    ONTOLOGY_CONTRIBUTOR = "ontology_contributor"  # 本体贡献者
    ONTOLOGY_VIEWER = "ontology_viewer"         # 本体查看者


# 角色权限映射
ROLE_PERMISSIONS: Dict[OntologyRole, Set[OntologyPermission]] = {
    OntologyRole.ONTOLOGY_ADMIN: {
        OntologyPermission.ADMIN_ALL,
        # 包含所有权限
        OntologyPermission.EXPERT_VIEW,
        OntologyPermission.EXPERT_CREATE,
        OntologyPermission.EXPERT_UPDATE,
        OntologyPermission.EXPERT_DELETE,
        OntologyPermission.EXPERT_RECOMMEND,
        OntologyPermission.TEMPLATE_VIEW,
        OntologyPermission.TEMPLATE_CREATE,
        OntologyPermission.TEMPLATE_UPDATE,
        OntologyPermission.TEMPLATE_DELETE,
        OntologyPermission.TEMPLATE_INSTANTIATE,
        OntologyPermission.TEMPLATE_CUSTOMIZE,
        OntologyPermission.TEMPLATE_EXPORT,
        OntologyPermission.TEMPLATE_IMPORT,
        OntologyPermission.COLLABORATION_JOIN,
        OntologyPermission.COLLABORATION_EDIT,
        OntologyPermission.COLLABORATION_LOCK,
        OntologyPermission.COLLABORATION_RESOLVE_CONFLICT,
        OntologyPermission.APPROVAL_VIEW,
        OntologyPermission.APPROVAL_CREATE,
        OntologyPermission.APPROVAL_APPROVE,
        OntologyPermission.APPROVAL_REJECT,
        OntologyPermission.APPROVAL_MANAGE_CHAIN,
        OntologyPermission.VALIDATION_VIEW,
        OntologyPermission.VALIDATION_CREATE,
        OntologyPermission.VALIDATION_UPDATE,
        OntologyPermission.VALIDATION_DELETE,
        OntologyPermission.COMPLIANCE_VIEW,
        OntologyPermission.COMPLIANCE_APPLY,
        OntologyPermission.COMPLIANCE_REPORT,
        OntologyPermission.IMPACT_VIEW,
        OntologyPermission.IMPACT_ANALYZE,
        OntologyPermission.AUDIT_VIEW,
        OntologyPermission.AUDIT_EXPORT,
        OntologyPermission.AUDIT_ROLLBACK,
    },
    OntologyRole.ONTOLOGY_EXPERT: {
        OntologyPermission.EXPERT_VIEW,
        OntologyPermission.EXPERT_UPDATE,
        OntologyPermission.EXPERT_RECOMMEND,
        OntologyPermission.TEMPLATE_VIEW,
        OntologyPermission.TEMPLATE_INSTANTIATE,
        OntologyPermission.TEMPLATE_CUSTOMIZE,
        OntologyPermission.TEMPLATE_EXPORT,
        OntologyPermission.COLLABORATION_JOIN,
        OntologyPermission.COLLABORATION_EDIT,
        OntologyPermission.COLLABORATION_LOCK,
        OntologyPermission.COLLABORATION_RESOLVE_CONFLICT,
        OntologyPermission.APPROVAL_VIEW,
        OntologyPermission.APPROVAL_CREATE,
        OntologyPermission.VALIDATION_VIEW,
        OntologyPermission.COMPLIANCE_VIEW,
        OntologyPermission.COMPLIANCE_REPORT,
        OntologyPermission.IMPACT_VIEW,
        OntologyPermission.IMPACT_ANALYZE,
        OntologyPermission.AUDIT_VIEW,
    },
    OntologyRole.ONTOLOGY_REVIEWER: {
        OntologyPermission.EXPERT_VIEW,
        OntologyPermission.TEMPLATE_VIEW,
        OntologyPermission.COLLABORATION_JOIN,
        OntologyPermission.APPROVAL_VIEW,
        OntologyPermission.APPROVAL_APPROVE,
        OntologyPermission.APPROVAL_REJECT,
        OntologyPermission.VALIDATION_VIEW,
        OntologyPermission.COMPLIANCE_VIEW,
        OntologyPermission.COMPLIANCE_REPORT,
        OntologyPermission.IMPACT_VIEW,
        OntologyPermission.IMPACT_ANALYZE,
        OntologyPermission.AUDIT_VIEW,
    },
    OntologyRole.ONTOLOGY_CONTRIBUTOR: {
        OntologyPermission.EXPERT_VIEW,
        OntologyPermission.TEMPLATE_VIEW,
        OntologyPermission.TEMPLATE_INSTANTIATE,
        OntologyPermission.COLLABORATION_JOIN,
        OntologyPermission.COLLABORATION_EDIT,
        OntologyPermission.APPROVAL_VIEW,
        OntologyPermission.APPROVAL_CREATE,
        OntologyPermission.VALIDATION_VIEW,
        OntologyPermission.COMPLIANCE_VIEW,
        OntologyPermission.IMPACT_VIEW,
    },
    OntologyRole.ONTOLOGY_VIEWER: {
        OntologyPermission.EXPERT_VIEW,
        OntologyPermission.TEMPLATE_VIEW,
        OntologyPermission.APPROVAL_VIEW,
        OntologyPermission.VALIDATION_VIEW,
        OntologyPermission.COMPLIANCE_VIEW,
        OntologyPermission.IMPACT_VIEW,
    },
}


class OntologyCollaborationSecurityService:
    """
    本体协作安全服务
    
    提供：
    - 权限检查
    - 基于专业领域的授权
    - 审计日志记录
    - 完整性验证
    """
    
    def __init__(
        self,
        audit_service: Optional[AuditService] = None,
        collaboration_audit: Optional[CollaborationAuditService] = None,
    ):
        """
        初始化安全服务
        
        Args:
            audit_service: 系统审计服务
            collaboration_audit: 协作审计服务
        """
        self._audit_service = audit_service
        self._collaboration_audit = collaboration_audit or CollaborationAuditService()
        self._lock = asyncio.Lock()
        
        # 用户角色缓存
        self._user_roles: Dict[str, Set[OntologyRole]] = {}
        
        # 用户专业领域缓存
        self._user_expertise: Dict[str, Set[str]] = {}
        
        logger.info("OntologyCollaborationSecurityService initialized")
    
    # ========================================================================
    # 权限检查
    # ========================================================================
    
    async def check_permission(
        self,
        user_id: str,
        permission: OntologyPermission,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            user_id: 用户ID
            permission: 权限类型
            tenant_id: 租户ID
            
        Returns:
            是否有权限
        """
        user_roles = await self.get_user_roles(user_id)
        
        for role in user_roles:
            role_permissions = ROLE_PERMISSIONS.get(role, set())
            
            # 检查是否有管理员权限
            if OntologyPermission.ADMIN_ALL in role_permissions:
                return True
            
            # 检查具体权限
            if permission in role_permissions:
                return True
        
        return False
    
    async def check_permissions(
        self,
        user_id: str,
        permissions: List[OntologyPermission],
        require_all: bool = True,
    ) -> bool:
        """
        检查用户是否有多个权限
        
        Args:
            user_id: 用户ID
            permissions: 权限列表
            require_all: 是否需要全部权限
            
        Returns:
            是否有权限
        """
        results = []
        for permission in permissions:
            has_permission = await self.check_permission(user_id, permission)
            results.append(has_permission)
        
        if require_all:
            return all(results)
        else:
            return any(results)
    
    # ========================================================================
    # 基于专业领域的授权
    # ========================================================================
    
    async def check_expertise_authorization(
        self,
        user_id: str,
        ontology_area: str,
    ) -> bool:
        """
        检查用户是否有特定本体领域的专业授权
        
        Args:
            user_id: 用户ID
            ontology_area: 本体领域
            
        Returns:
            是否有授权
        """
        user_expertise = await self.get_user_expertise(user_id)
        
        # 检查是否有该领域的专业知识
        if ontology_area in user_expertise:
            return True
        
        # 检查是否有相关领域的专业知识
        related_areas = self._get_related_expertise_areas(ontology_area)
        for area in related_areas:
            if area in user_expertise:
                return True
        
        return False
    
    def _get_related_expertise_areas(self, area: str) -> Set[str]:
        """获取相关专业领域"""
        # 专业领域关联映射
        related_map = {
            "金融": {"经济", "会计", "投资"},
            "医疗": {"生物", "制药", "健康"},
            "制造": {"工程", "供应链", "质量"},
            "政务": {"法律", "公共管理", "政策"},
            "法律": {"政务", "合规", "知识产权"},
            "教育": {"培训", "学术", "研究"},
        }
        return related_map.get(area, set())
    
    # ========================================================================
    # 角色管理
    # ========================================================================
    
    async def get_user_roles(self, user_id: str) -> Set[OntologyRole]:
        """获取用户角色"""
        if user_id in self._user_roles:
            return self._user_roles[user_id]
        
        # 默认返回查看者角色
        return {OntologyRole.ONTOLOGY_VIEWER}
    
    async def assign_role(
        self,
        user_id: str,
        role: OntologyRole,
        assigned_by: str,
    ) -> bool:
        """
        分配角色给用户
        
        Args:
            user_id: 用户ID
            role: 角色
            assigned_by: 分配者ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            if user_id not in self._user_roles:
                self._user_roles[user_id] = set()
            
            self._user_roles[user_id].add(role)
            
            # 记录审计日志
            await self._log_security_event(
                user_id=assigned_by,
                action="ROLE_ASSIGNED",
                resource_type="user_role",
                resource_id=user_id,
                details={
                    "role": role.value,
                    "target_user": user_id,
                },
            )
            
            return True
    
    async def revoke_role(
        self,
        user_id: str,
        role: OntologyRole,
        revoked_by: str,
    ) -> bool:
        """
        撤销用户角色
        
        Args:
            user_id: 用户ID
            role: 角色
            revoked_by: 撤销者ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            if user_id in self._user_roles:
                self._user_roles[user_id].discard(role)
                
                # 记录审计日志
                await self._log_security_event(
                    user_id=revoked_by,
                    action="ROLE_REVOKED",
                    resource_type="user_role",
                    resource_id=user_id,
                    details={
                        "role": role.value,
                        "target_user": user_id,
                    },
                )
                
                return True
        
        return False

    # ========================================================================
    # 专业领域管理
    # ========================================================================
    
    async def get_user_expertise(self, user_id: str) -> Set[str]:
        """获取用户专业领域"""
        if user_id in self._user_expertise:
            return self._user_expertise[user_id]
        
        return set()
    
    async def set_user_expertise(
        self,
        user_id: str,
        expertise_areas: List[str],
        set_by: str,
    ) -> bool:
        """
        设置用户专业领域
        
        Args:
            user_id: 用户ID
            expertise_areas: 专业领域列表
            set_by: 设置者ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            self._user_expertise[user_id] = set(expertise_areas)
            
            # 记录审计日志
            await self._log_security_event(
                user_id=set_by,
                action="EXPERTISE_SET",
                resource_type="user_expertise",
                resource_id=user_id,
                details={
                    "expertise_areas": expertise_areas,
                    "target_user": user_id,
                },
            )
            
            return True
    
    # ========================================================================
    # 审计日志
    # ========================================================================
    
    async def _log_security_event(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录安全事件"""
        try:
            await self._collaboration_audit.log_change(
                ontology_id="security",
                user_id=user_id,
                change_type=action,
                affected_elements=[resource_id],
                before_state=None,
                after_state=details,
                description=f"Security event: {action} on {resource_type}",
            )
        except Exception as e:
            logger.warning(f"Failed to log security event: {e}")
    
    async def log_access_attempt(
        self,
        user_id: str,
        permission: OntologyPermission,
        resource_id: str,
        granted: bool,
        reason: Optional[str] = None,
    ) -> None:
        """
        记录访问尝试
        
        Args:
            user_id: 用户ID
            permission: 请求的权限
            resource_id: 资源ID
            granted: 是否授权
            reason: 原因
        """
        await self._log_security_event(
            user_id=user_id,
            action="ACCESS_ATTEMPT",
            resource_type="permission",
            resource_id=resource_id,
            details={
                "permission": permission.value,
                "granted": granted,
                "reason": reason,
            },
        )
    
    # ========================================================================
    # 完整性验证
    # ========================================================================
    
    async def verify_audit_integrity(
        self,
        ontology_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        验证审计日志完整性
        
        Args:
            ontology_id: 本体ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            验证结果
        """
        try:
            result = await self._collaboration_audit.verify_integrity(
                ontology_id=ontology_id,
            )
            
            return {
                "verified": result.get("verified", False) if result else False,
                "total_logs": result.get("total_logs", 0) if result else 0,
                "valid_logs": result.get("valid_logs", 0) if result else 0,
                "invalid_logs": result.get("invalid_logs", []) if result else [],
                "verified_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to verify audit integrity: {e}")
            return {
                "verified": False,
                "error": str(e),
            }
    
    # ========================================================================
    # 权限装饰器辅助
    # ========================================================================
    
    def require_permission(self, permission: OntologyPermission):
        """
        权限检查装饰器
        
        用法:
            @security_service.require_permission(OntologyPermission.EXPERT_CREATE)
            async def create_expert(user_id: str, ...):
                ...
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 从参数中获取 user_id
                user_id = kwargs.get('user_id') or (args[0] if args else None)
                
                if not user_id:
                    raise PermissionError("User ID required")
                
                has_permission = await self.check_permission(user_id, permission)
                
                if not has_permission:
                    await self.log_access_attempt(
                        user_id=user_id,
                        permission=permission,
                        resource_id="unknown",
                        granted=False,
                        reason="Permission denied",
                    )
                    raise PermissionError(f"Permission denied: {permission.value}")
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_expertise(self, ontology_area: str):
        """
        专业领域检查装饰器
        
        用法:
            @security_service.require_expertise("金融")
            async def edit_finance_ontology(user_id: str, ...):
                ...
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                user_id = kwargs.get('user_id') or (args[0] if args else None)
                
                if not user_id:
                    raise PermissionError("User ID required")
                
                has_expertise = await self.check_expertise_authorization(
                    user_id, ontology_area
                )
                
                if not has_expertise:
                    raise PermissionError(
                        f"Expertise required for area: {ontology_area}"
                    )
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator


# 全局实例
_security_service: Optional[OntologyCollaborationSecurityService] = None


def get_ontology_security_service() -> OntologyCollaborationSecurityService:
    """获取或创建全局安全服务实例"""
    global _security_service
    
    if _security_service is None:
        _security_service = OntologyCollaborationSecurityService()
    
    return _security_service


async def check_ontology_permission(
    user_id: str,
    permission: OntologyPermission,
) -> bool:
    """便捷函数：检查本体权限"""
    service = get_ontology_security_service()
    return await service.check_permission(user_id, permission)


async def check_ontology_expertise(
    user_id: str,
    ontology_area: str,
) -> bool:
    """便捷函数：检查专业领域授权"""
    service = get_ontology_security_service()
    return await service.check_expertise_authorization(user_id, ontology_area)
