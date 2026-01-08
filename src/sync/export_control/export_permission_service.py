"""
Export Permission Service for data export access control.

Provides comprehensive permission checking for data exports with policy
enforcement, quota management, and security validation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from dataclasses import dataclass

from src.database.connection import get_db_session
from ..rbac.permission_manager import PermissionManager, PermissionContext
from ..rbac.models import PermissionAction, ResourceType
from .models import (
    ExportRequestModel, ExportPolicyModel, ExportRequestStatus,
    ExportFormat, ExportScope
)

logger = logging.getLogger(__name__)


@dataclass
class ExportPermissionRequest:
    """Export permission request data."""
    user_id: UUID
    tenant_id: str
    table_names: List[str]
    field_names: Optional[List[str]] = None
    export_format: ExportFormat = ExportFormat.CSV
    export_scope: ExportScope = ExportScope.FILTERED_DATA
    estimated_records: Optional[int] = None
    business_justification: str = ""
    filter_conditions: Optional[Dict[str, Any]] = None


@dataclass
class ExportPermissionResult:
    """Result of export permission check."""
    allowed: bool
    reason: str
    requires_approval: bool = False
    approval_level: int = 1
    policy_restrictions: Optional[Dict[str, Any]] = None
    quota_status: Optional[Dict[str, Any]] = None
    estimated_approval_time: Optional[timedelta] = None


class ExportPermissionService:
    """
    Export permission service for data export access control.
    
    Provides comprehensive permission checking, policy enforcement,
    and quota management for data exports.
    """
    
    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self.permission_manager = permission_manager or PermissionManager()
    
    def check_export_permission(
        self,
        request: ExportPermissionRequest,
        db: Optional[Session] = None
    ) -> ExportPermissionResult:
        """
        Check if user has permission to export data.
        
        Args:
            request: Export permission request
            db: Database session
            
        Returns:
            ExportPermissionResult with permission decision
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Check basic export permission
            basic_permission = self._check_basic_export_permission(request, db)
            if not basic_permission.allowed:
                return basic_permission
            
            # Check table-specific permissions
            table_permission = self._check_table_permissions(request, db)
            if not table_permission.allowed:
                return table_permission
            
            # Check field-level permissions
            field_permission = self._check_field_permissions(request, db)
            if not field_permission.allowed:
                return field_permission
            
            # Apply export policies
            policy_result = self._apply_export_policies(request, db)
            if not policy_result.allowed:
                return policy_result
            
            # Check quotas and limits
            quota_result = self._check_export_quotas(request, db)
            if not quota_result.allowed:
                return quota_result
            
            # Determine approval requirements
            approval_info = self._determine_approval_requirements(request, db)
            
            return ExportPermissionResult(
                allowed=True,
                reason="Export permission granted",
                requires_approval=approval_info["requires_approval"],
                approval_level=approval_info["approval_level"],
                policy_restrictions=policy_result.policy_restrictions,
                quota_status=quota_result.quota_status,
                estimated_approval_time=approval_info.get("estimated_time")
            )
            
        except Exception as e:
            logger.error(f"Error checking export permission: {e}")
            return ExportPermissionResult(
                allowed=False,
                reason=f"Permission check failed: {str(e)}"
            )
    
    def create_export_request(
        self,
        request: ExportPermissionRequest,
        request_title: str,
        request_description: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[ExportRequestModel]:
        """
        Create export request with permission validation.
        
        Args:
            request: Export permission request
            request_title: Title for the export request
            request_description: Description for the export request
            db: Database session
            
        Returns:
            Created export request or None if failed
        """
        if db is None:
            db = next(get_db_session())
        
        # Check permissions first
        permission_result = self.check_export_permission(request, db)
        if not permission_result.allowed:
            logger.warning(f"Export request denied: {permission_result.reason}")
            return None
        
        try:
            # Get applicable policies
            policies = self._get_applicable_policies(request, db)
            
            # Calculate approval requirements
            approval_level = permission_result.approval_level
            requires_approval = permission_result.requires_approval
            
            # Determine watermark and tracking settings
            watermark_config = self._get_watermark_config(policies)
            enable_watermark = any(p.mandatory_watermark for p in policies) if policies else True
            enable_tracking = any(p.mandatory_tracking for p in policies) if policies else True
            
            # Calculate retention period
            retention_days = min(p.max_retention_days for p in policies) if policies else 30
            
            # Create export request
            export_request = ExportRequestModel(
                tenant_id=request.tenant_id,
                requester_id=request.user_id,
                request_title=request_title,
                request_description=request_description,
                business_justification=request.business_justification,
                export_format=request.export_format,
                export_scope=request.export_scope,
                table_names=request.table_names,
                field_names=request.field_names,
                filter_conditions=request.filter_conditions or {},
                requires_approval=requires_approval,
                approval_level=approval_level,
                enable_watermark=enable_watermark,
                watermark_config=watermark_config,
                enable_tracking=enable_tracking,
                retention_days=retention_days,
                estimated_records=request.estimated_records,
                status=ExportRequestStatus.PENDING if requires_approval else ExportRequestStatus.APPROVED
            )
            
            db.add(export_request)
            db.commit()
            db.refresh(export_request)
            
            logger.info(f"Export request created: {export_request.id}")
            return export_request
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating export request: {e}")
            return None
    
    def get_user_export_quota(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get user's current export quota status.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dictionary with quota information
        """
        if db is None:
            db = next(get_db_session())
        
        # Get applicable policies
        policies = db.query(ExportPolicyModel).filter(
            and_(
                ExportPolicyModel.tenant_id == tenant_id,
                ExportPolicyModel.is_active == True
            )
        ).all()
        
        # Calculate current usage
        today = datetime.utcnow().date()
        month_start = today.replace(day=1)
        
        # Daily exports
        daily_exports = db.query(ExportRequestModel).filter(
            and_(
                ExportRequestModel.tenant_id == tenant_id,
                ExportRequestModel.requester_id == user_id,
                func.date(ExportRequestModel.created_at) == today
            )
        ).count()
        
        # Monthly exports
        monthly_exports = db.query(ExportRequestModel).filter(
            and_(
                ExportRequestModel.tenant_id == tenant_id,
                ExportRequestModel.requester_id == user_id,
                ExportRequestModel.created_at >= month_start
            )
        ).count()
        
        # Get limits from policies
        max_daily = None
        max_monthly = None
        max_records = None
        
        for policy in policies:
            if policy.max_exports_per_day:
                max_daily = min(max_daily or float('inf'), policy.max_exports_per_day)
            if policy.max_exports_per_month:
                max_monthly = min(max_monthly or float('inf'), policy.max_exports_per_month)
            if policy.max_records_per_export:
                max_records = min(max_records or float('inf'), policy.max_records_per_export)
        
        return {
            "daily_usage": {
                "current": daily_exports,
                "limit": max_daily,
                "remaining": max_daily - daily_exports if max_daily else None
            },
            "monthly_usage": {
                "current": monthly_exports,
                "limit": max_monthly,
                "remaining": max_monthly - monthly_exports if max_monthly else None
            },
            "record_limit": max_records,
            "quota_exceeded": (
                (max_daily and daily_exports >= max_daily) or
                (max_monthly and monthly_exports >= max_monthly)
            )
        }
    
    def get_export_policies(
        self,
        tenant_id: str,
        user_id: Optional[UUID] = None,
        table_name: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[ExportPolicyModel]:
        """
        Get applicable export policies for user/table.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID (optional)
            table_name: Table name (optional)
            db: Database session
            
        Returns:
            List of applicable export policies
        """
        if db is None:
            db = next(get_db_session())
        
        query = db.query(ExportPolicyModel).filter(
            and_(
                ExportPolicyModel.tenant_id == tenant_id,
                ExportPolicyModel.is_active == True
            )
        )
        
        # Filter by table if specified
        if table_name:
            query = query.filter(
                or_(
                    ExportPolicyModel.applies_to_tables.is_(None),
                    ExportPolicyModel.applies_to_tables.contains([table_name])
                )
            )
        
        # Filter by user if specified
        if user_id:
            query = query.filter(
                or_(
                    ExportPolicyModel.applies_to_users.is_(None),
                    ExportPolicyModel.applies_to_users.contains([str(user_id)])
                )
            )
        
        return query.order_by(ExportPolicyModel.priority.desc()).all()
    
    def _check_basic_export_permission(
        self,
        request: ExportPermissionRequest,
        db: Session
    ) -> ExportPermissionResult:
        """Check basic export permission using RBAC."""
        
        context = PermissionContext(
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            resource_type=ResourceType.SYNC_JOB,  # Using sync job as export resource
            action=PermissionAction.EXPORT
        )
        
        permission_result = self.permission_manager.check_permission(context, db)
        
        if not permission_result.granted:
            return ExportPermissionResult(
                allowed=False,
                reason=f"Basic export permission denied: {permission_result.reason}"
            )
        
        return ExportPermissionResult(
            allowed=True,
            reason="Basic export permission granted"
        )
    
    def _check_table_permissions(
        self,
        request: ExportPermissionRequest,
        db: Session
    ) -> ExportPermissionResult:
        """Check table-specific export permissions."""
        
        for table_name in request.table_names:
            context = PermissionContext(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                resource_type=ResourceType.SYNC_JOB,
                resource_id=table_name,
                action=PermissionAction.EXPORT,
                table_name=table_name
            )
            
            permission_result = self.permission_manager.check_permission(context, db)
            
            if not permission_result.granted:
                return ExportPermissionResult(
                    allowed=False,
                    reason=f"Table export permission denied for {table_name}: {permission_result.reason}"
                )
        
        return ExportPermissionResult(
            allowed=True,
            reason="Table export permissions granted"
        )
    
    def _check_field_permissions(
        self,
        request: ExportPermissionRequest,
        db: Session
    ) -> ExportPermissionResult:
        """Check field-level export permissions."""
        
        if not request.field_names:
            return ExportPermissionResult(
                allowed=True,
                reason="No specific field restrictions"
            )
        
        from ..rbac.field_access_control import FieldAccessController
        field_controller = FieldAccessController(self.permission_manager)
        
        for table_name in request.table_names:
            for field_name in request.field_names:
                field_result = field_controller.check_field_access(
                    request.user_id, request.tenant_id, table_name, field_name, None, db=db
                )
                
                if not field_result.allowed:
                    return ExportPermissionResult(
                        allowed=False,
                        reason=f"Field export permission denied for {table_name}.{field_name}: {field_result.reason}"
                    )
        
        return ExportPermissionResult(
            allowed=True,
            reason="Field export permissions granted"
        )
    
    def _apply_export_policies(
        self,
        request: ExportPermissionRequest,
        db: Session
    ) -> ExportPermissionResult:
        """Apply export policies and restrictions."""
        
        policies = self._get_applicable_policies(request, db)
        
        if not policies:
            return ExportPermissionResult(
                allowed=True,
                reason="No applicable export policies"
            )
        
        restrictions = {}
        
        for policy in policies:
            # Check format restrictions
            if policy.allowed_formats and request.export_format.value not in policy.allowed_formats:
                return ExportPermissionResult(
                    allowed=False,
                    reason=f"Export format {request.export_format.value} not allowed by policy {policy.policy_name}"
                )
            
            # Check record limits
            if policy.max_records_per_export and request.estimated_records:
                if request.estimated_records > policy.max_records_per_export:
                    return ExportPermissionResult(
                        allowed=False,
                        reason=f"Estimated records ({request.estimated_records}) exceeds policy limit ({policy.max_records_per_export})"
                    )
            
            # Collect restrictions
            if policy.max_records_per_export:
                restrictions["max_records"] = min(
                    restrictions.get("max_records", float('inf')),
                    policy.max_records_per_export
                )
            
            if policy.max_retention_days:
                restrictions["max_retention_days"] = min(
                    restrictions.get("max_retention_days", float('inf')),
                    policy.max_retention_days
                )
        
        return ExportPermissionResult(
            allowed=True,
            reason="Export policies satisfied",
            policy_restrictions=restrictions
        )
    
    def _check_export_quotas(
        self,
        request: ExportPermissionRequest,
        db: Session
    ) -> ExportPermissionResult:
        """Check export quotas and limits."""
        
        quota_status = self.get_user_export_quota(request.user_id, request.tenant_id, db)
        
        if quota_status["quota_exceeded"]:
            return ExportPermissionResult(
                allowed=False,
                reason="Export quota exceeded",
                quota_status=quota_status
            )
        
        return ExportPermissionResult(
            allowed=True,
            reason="Export quota available",
            quota_status=quota_status
        )
    
    def _determine_approval_requirements(
        self,
        request: ExportPermissionRequest,
        db: Session
    ) -> Dict[str, Any]:
        """Determine approval requirements for export request."""
        
        policies = self._get_applicable_policies(request, db)
        
        requires_approval = False
        approval_level = 1
        estimated_time = None
        
        for policy in policies:
            if policy.requires_manager_approval:
                requires_approval = True
                approval_level = max(approval_level, 1)
            
            if policy.requires_senior_approval:
                requires_approval = True
                approval_level = max(approval_level, 2)
            
            # Check auto-approve threshold
            if (policy.auto_approve_threshold and 
                request.estimated_records and 
                request.estimated_records <= policy.auto_approve_threshold):
                requires_approval = False
        
        # Estimate approval time based on level
        if requires_approval:
            if approval_level == 1:
                estimated_time = timedelta(hours=4)  # Manager approval
            elif approval_level == 2:
                estimated_time = timedelta(days=1)   # Senior approval
            else:
                estimated_time = timedelta(days=2)   # Executive approval
        
        return {
            "requires_approval": requires_approval,
            "approval_level": approval_level,
            "estimated_time": estimated_time
        }
    
    def _get_applicable_policies(
        self,
        request: ExportPermissionRequest,
        db: Session
    ) -> List[ExportPolicyModel]:
        """Get policies applicable to the export request."""
        
        policies = []
        
        for table_name in request.table_names:
            table_policies = self.get_export_policies(
                request.tenant_id, request.user_id, table_name, db
            )
            policies.extend(table_policies)
        
        # Remove duplicates and sort by priority
        unique_policies = {p.id: p for p in policies}.values()
        return sorted(unique_policies, key=lambda p: p.priority, reverse=True)
    
    def _get_watermark_config(self, policies: List[ExportPolicyModel]) -> Dict[str, Any]:
        """Get watermark configuration from policies."""
        
        config = {
            "type": "visible",
            "text": "CONFIDENTIAL - {user_id} - {timestamp}",
            "position": "bottom_right",
            "opacity": 0.3
        }
        
        # Policies could override watermark configuration
        for policy in policies:
            if policy.mandatory_watermark:
                # Could extract watermark config from policy metadata
                pass
        
        return config