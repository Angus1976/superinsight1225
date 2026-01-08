"""
Export API Service for data export management endpoints.

Provides REST API endpoints for export request management, approval workflow,
monitoring, and compliance reporting.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.database.connection import get_db_session
from ..rbac.tenant_isolation import tenant_context, set_tenant_context
from .export_permission_service import ExportPermissionService, ExportPermissionRequest
from .watermark_service import WatermarkService
from .approval_workflow import ApprovalWorkflowService, ApprovalRequest, ApprovalDecision
from .export_monitor import ExportMonitorService, AccessEvent, BehaviorEvent
from .models import (
    ExportRequestModel, ExportFormat, ExportScope, ExportBehaviorType,
    WatermarkType
)

logger = logging.getLogger(__name__)

# Pydantic models for API
class ExportRequestCreate(BaseModel):
    """Export request creation model."""
    request_title: str = Field(..., min_length=1, max_length=200)
    request_description: Optional[str] = Field(None, max_length=1000)
    business_justification: str = Field(..., min_length=10, max_length=2000)
    table_names: List[str] = Field(..., min_items=1)
    field_names: Optional[List[str]] = None
    export_format: ExportFormat
    export_scope: ExportScope
    filter_conditions: Optional[Dict[str, Any]] = None
    estimated_records: Optional[int] = Field(None, ge=0)


class ExportApprovalDecision(BaseModel):
    """Export approval decision model."""
    decision: ApprovalDecision
    reason: Optional[str] = Field(None, max_length=1000)
    conditions: Optional[Dict[str, Any]] = None
    escalate_to: Optional[UUID] = None


class AccessEventCreate(BaseModel):
    """Access event creation model."""
    export_request_id: UUID
    access_type: str
    access_method: str
    file_path: Optional[str] = None
    bytes_transferred: Optional[int] = Field(None, ge=0)
    access_duration: Optional[float] = Field(None, ge=0)


class BehaviorEventCreate(BaseModel):
    """Behavior event creation model."""
    export_request_id: UUID
    session_id: str
    behavior_type: ExportBehaviorType
    behavior_details: Dict[str, Any] = Field(default_factory=dict)
    device_type: Optional[str] = None
    browser_type: Optional[str] = None
    shared_with: Optional[List[str]] = None


class ExportAPIService:
    """
    Export API service for data export management.
    
    Provides REST API endpoints for export operations, approval workflow,
    monitoring, and compliance reporting.
    """
    
    def __init__(self):
        self.permission_service = ExportPermissionService()
        self.watermark_service = WatermarkService()
        self.approval_service = ApprovalWorkflowService()
        self.monitor_service = ExportMonitorService()
        self.router = APIRouter(prefix="/api/v1/export", tags=["export"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        # Export request management
        self.router.add_api_route(
            "/requests",
            self.create_export_request,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/requests/{request_id}",
            self.get_export_request,
            methods=["GET"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/requests",
            self.list_export_requests,
            methods=["GET"],
            response_model=Dict[str, Any]
        )
        
        # Permission checking
        self.router.add_api_route(
            "/permissions/check",
            self.check_export_permission,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/permissions/quota/{user_id}",
            self.get_user_quota,
            methods=["GET"],
            response_model=Dict[str, Any]
        )
        
        # Approval workflow
        self.router.add_api_route(
            "/approvals/pending",
            self.get_pending_approvals,
            methods=["GET"],
            response_model=List[Dict[str, Any]]
        )
        
        self.router.add_api_route(
            "/approvals/{request_id}/decide",
            self.process_approval_decision,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/approvals/{request_id}/history",
            self.get_approval_history,
            methods=["GET"],
            response_model=List[Dict[str, Any]]
        )
        
        # Watermarking
        self.router.add_api_route(
            "/watermarks/{request_id}",
            self.create_watermark,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/watermarks/{request_id}/info",
            self.get_watermark_info,
            methods=["GET"],
            response_model=List[Dict[str, Any]]
        )
        
        self.router.add_api_route(
            "/watermarks/verify",
            self.verify_watermark,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        
        # Monitoring and tracking
        self.router.add_api_route(
            "/tracking/access",
            self.track_access_event,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/tracking/behavior",
            self.track_behavior_event,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/analytics/{request_id}",
            self.get_export_analytics,
            methods=["GET"],
            response_model=Dict[str, Any]
        )
        
        self.router.add_api_route(
            "/dashboard",
            self.get_tenant_dashboard,
            methods=["GET"],
            response_model=Dict[str, Any]
        )
        
        # Security and compliance
        self.router.add_api_route(
            "/security/alerts",
            self.get_security_alerts,
            methods=["GET"],
            response_model=List[Dict[str, Any]]
        )
    
    async def create_export_request(
        self,
        request_data: ExportRequestCreate,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Create new export request."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            # Create permission request
            permission_request = ExportPermissionRequest(
                user_id=user_id,
                tenant_id=tenant_id,
                table_names=request_data.table_names,
                field_names=request_data.field_names,
                export_format=request_data.export_format,
                export_scope=request_data.export_scope,
                estimated_records=request_data.estimated_records,
                business_justification=request_data.business_justification,
                filter_conditions=request_data.filter_conditions
            )
            
            # Create export request
            export_request = self.permission_service.create_export_request(
                permission_request,
                request_data.request_title,
                request_data.request_description,
                db
            )
            
            if not export_request:
                raise HTTPException(status_code=403, detail="Export request denied")
            
            # Initiate approval workflow if required
            if export_request.requires_approval:
                workflow_initiated = self.approval_service.initiate_approval_workflow(
                    export_request, db=db
                )
                if not workflow_initiated:
                    logger.warning(f"Failed to initiate approval workflow for {export_request.id}")
            
            return {
                "success": True,
                "export_request_id": str(export_request.id),
                "status": export_request.status.value,
                "requires_approval": export_request.requires_approval,
                "approval_level": export_request.approval_level,
                "message": "Export request created successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating export request: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_export_request(
        self,
        request_id: UUID,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Get export request details."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            export_request = db.query(ExportRequestModel).filter(
                ExportRequestModel.id == request_id,
                ExportRequestModel.tenant_id == tenant_id
            ).first()
            
            if not export_request:
                raise HTTPException(status_code=404, detail="Export request not found")
            
            # Check if user can access this request
            if (export_request.requester_id != user_id and 
                not self._user_can_view_request(user_id, export_request, db)):
                raise HTTPException(status_code=403, detail="Access denied")
            
            return {
                "id": str(export_request.id),
                "title": export_request.request_title,
                "description": export_request.request_description,
                "status": export_request.status.value,
                "requester_id": str(export_request.requester_id),
                "business_justification": export_request.business_justification,
                "export_format": export_request.export_format.value,
                "export_scope": export_request.export_scope.value,
                "table_names": export_request.table_names,
                "field_names": export_request.field_names,
                "filter_conditions": export_request.filter_conditions,
                "estimated_records": export_request.estimated_records,
                "requires_approval": export_request.requires_approval,
                "approval_level": export_request.approval_level,
                "created_at": export_request.created_at.isoformat(),
                "updated_at": export_request.updated_at.isoformat(),
                "expires_at": export_request.expires_at.isoformat() if export_request.expires_at else None,
                "download_url": export_request.download_url,
                "download_expires_at": export_request.download_expires_at.isoformat() if export_request.download_expires_at else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting export request: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def list_export_requests(
        self,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        status: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """List export requests for user."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            query = db.query(ExportRequestModel).filter(
                ExportRequestModel.tenant_id == tenant_id,
                ExportRequestModel.requester_id == user_id
            )
            
            if status:
                query = query.filter(ExportRequestModel.status == status)
            
            total_count = query.count()
            export_requests = query.order_by(
                ExportRequestModel.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            return {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "requests": [
                    {
                        "id": str(er.id),
                        "title": er.request_title,
                        "status": er.status.value,
                        "export_format": er.export_format.value,
                        "table_count": len(er.table_names),
                        "estimated_records": er.estimated_records,
                        "created_at": er.created_at.isoformat(),
                        "requires_approval": er.requires_approval
                    }
                    for er in export_requests
                ]
            }
            
        except Exception as e:
            logger.error(f"Error listing export requests: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_export_permission(
        self,
        request_data: ExportRequestCreate,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Check export permission without creating request."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            permission_request = ExportPermissionRequest(
                user_id=user_id,
                tenant_id=tenant_id,
                table_names=request_data.table_names,
                field_names=request_data.field_names,
                export_format=request_data.export_format,
                export_scope=request_data.export_scope,
                estimated_records=request_data.estimated_records,
                business_justification=request_data.business_justification,
                filter_conditions=request_data.filter_conditions
            )
            
            result = self.permission_service.check_export_permission(permission_request, db)
            
            return {
                "allowed": result.allowed,
                "reason": result.reason,
                "requires_approval": result.requires_approval,
                "approval_level": result.approval_level,
                "policy_restrictions": result.policy_restrictions,
                "quota_status": result.quota_status,
                "estimated_approval_time": result.estimated_approval_time.total_seconds() if result.estimated_approval_time else None
            }
            
        except Exception as e:
            logger.error(f"Error checking export permission: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_user_quota(
        self,
        user_id: UUID,
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Get user export quota status."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            quota_status = self.permission_service.get_user_export_quota(user_id, tenant_id, db)
            
            return quota_status
            
        except Exception as e:
            logger.error(f"Error getting user quota: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_pending_approvals(
        self,
        approver_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> List[Dict[str, Any]]:
        """Get pending approvals for approver."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, approver_id)
            
            pending_approvals = self.approval_service.get_pending_approvals(
                approver_id, tenant_id, db
            )
            
            return pending_approvals
            
        except Exception as e:
            logger.error(f"Error getting pending approvals: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def process_approval_decision(
        self,
        request_id: UUID,
        decision_data: ExportApprovalDecision,
        approver_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Process approval decision."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, approver_id)
            
            approval_request = ApprovalRequest(
                export_request_id=request_id,
                approver_id=approver_id,
                decision=decision_data.decision,
                reason=decision_data.reason,
                conditions=decision_data.conditions,
                escalate_to=decision_data.escalate_to
            )
            
            result = self.approval_service.process_approval_decision(approval_request, db)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing approval decision: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_approval_history(
        self,
        request_id: UUID,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> List[Dict[str, Any]]:
        """Get approval history for export request."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            # Verify user can access this request
            export_request = db.query(ExportRequestModel).filter(
                ExportRequestModel.id == request_id,
                ExportRequestModel.tenant_id == tenant_id
            ).first()
            
            if not export_request:
                raise HTTPException(status_code=404, detail="Export request not found")
            
            if (export_request.requester_id != user_id and 
                not self._user_can_view_request(user_id, export_request, db)):
                raise HTTPException(status_code=403, detail="Access denied")
            
            history = self.approval_service.get_approval_history(request_id, db)
            
            return history
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting approval history: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_watermark(
        self,
        request_id: UUID,
        watermark_type: WatermarkType = Body(...),
        config: Optional[Dict[str, Any]] = Body(None),
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Create watermark for export request."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            export_request = db.query(ExportRequestModel).filter(
                ExportRequestModel.id == request_id,
                ExportRequestModel.tenant_id == tenant_id
            ).first()
            
            if not export_request:
                raise HTTPException(status_code=404, detail="Export request not found")
            
            watermark = self.watermark_service.create_watermark(
                export_request, watermark_type, config, db
            )
            
            if not watermark:
                raise HTTPException(status_code=500, detail="Failed to create watermark")
            
            return {
                "success": True,
                "watermark_id": watermark.watermark_id,
                "watermark_type": watermark.watermark_type.value,
                "created_at": watermark.created_at.isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating watermark: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_watermark_info(
        self,
        request_id: UUID,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> List[Dict[str, Any]]:
        """Get watermark information for export request."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            watermark_info = self.watermark_service.get_watermark_info(request_id, db)
            
            return watermark_info
            
        except Exception as e:
            logger.error(f"Error getting watermark info: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def verify_watermark(
        self,
        file_path: str = Body(...),
        watermark_id: str = Body(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Verify watermark in file."""
        
        try:
            verification_result = self.watermark_service.verify_watermark(
                file_path, watermark_id, db
            )
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Error verifying watermark: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def track_access_event(
        self,
        event_data: AccessEventCreate,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Track access event."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            access_event = AccessEvent(
                export_request_id=event_data.export_request_id,
                accessor_id=user_id,
                access_type=event_data.access_type,
                ip_address=None,  # Would be extracted from request
                user_agent=None,  # Would be extracted from request
                session_id=None,  # Would be extracted from request
                access_method=event_data.access_method,
                file_path=event_data.file_path,
                bytes_transferred=event_data.bytes_transferred,
                access_duration=event_data.access_duration
            )
            
            tracking_id = self.monitor_service.track_access_event(access_event, db)
            
            return {
                "success": True,
                "tracking_id": str(tracking_id)
            }
            
        except Exception as e:
            logger.error(f"Error tracking access event: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def track_behavior_event(
        self,
        event_data: BehaviorEventCreate,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Track behavior event."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            behavior_event = BehaviorEvent(
                export_request_id=event_data.export_request_id,
                user_id=user_id,
                session_id=event_data.session_id,
                behavior_type=event_data.behavior_type,
                behavior_details=event_data.behavior_details,
                device_type=event_data.device_type,
                browser_type=event_data.browser_type,
                shared_with=event_data.shared_with
            )
            
            behavior_id = self.monitor_service.track_behavior_event(behavior_event, db)
            
            return {
                "success": True,
                "behavior_id": str(behavior_id)
            }
            
        except Exception as e:
            logger.error(f"Error tracking behavior event: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_export_analytics(
        self,
        request_id: UUID,
        user_id: UUID = Query(...),
        tenant_id: str = Query(...),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Get export usage analytics."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            # Verify user can access this request
            export_request = db.query(ExportRequestModel).filter(
                ExportRequestModel.id == request_id,
                ExportRequestModel.tenant_id == tenant_id
            ).first()
            
            if not export_request:
                raise HTTPException(status_code=404, detail="Export request not found")
            
            if (export_request.requester_id != user_id and 
                not self._user_can_view_request(user_id, export_request, db)):
                raise HTTPException(status_code=403, detail="Access denied")
            
            analytics = self.monitor_service.get_export_usage_analytics(request_id, db)
            
            return analytics
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting export analytics: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_tenant_dashboard(
        self,
        tenant_id: str = Query(...),
        user_id: UUID = Query(...),
        start_date: Optional[datetime] = Query(None),
        end_date: Optional[datetime] = Query(None),
        db: Session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """Get tenant export dashboard."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            # Check if user has dashboard access (would check admin permissions)
            # For now, allow all users to see tenant dashboard
            
            dashboard = self.monitor_service.get_tenant_export_dashboard(
                tenant_id, start_date, end_date, db
            )
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error getting tenant dashboard: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_security_alerts(
        self,
        tenant_id: str = Query(...),
        user_id: UUID = Query(...),
        lookback_hours: int = Query(24, ge=1, le=168),  # Max 1 week
        db: Session = Depends(get_db_session)
    ) -> List[Dict[str, Any]]:
        """Get security alerts."""
        
        try:
            # Set tenant context
            set_tenant_context(tenant_id, user_id)
            
            # Check if user has security access (would check admin permissions)
            
            alerts = self.monitor_service.detect_suspicious_behavior(
                tenant_id, lookback_hours, db
            )
            
            return [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "alert_type": alert.alert_type,
                    "export_request_id": str(alert.export_request_id),
                    "user_id": str(alert.user_id) if alert.user_id else None,
                    "description": alert.description,
                    "risk_score": alert.risk_score,
                    "evidence": alert.evidence,
                    "recommendations": alert.recommendations,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in alerts
            ]
            
        except Exception as e:
            logger.error(f"Error getting security alerts: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def _user_can_view_request(
        self,
        user_id: UUID,
        export_request: ExportRequestModel,
        db: Session
    ) -> bool:
        """Check if user can view export request (admin/approver permissions)."""
        
        # Simplified check - in production would use proper RBAC
        # For now, allow users to view requests in their tenant
        return True
    
    def get_router(self) -> APIRouter:
        """Get FastAPI router."""
        return self.router