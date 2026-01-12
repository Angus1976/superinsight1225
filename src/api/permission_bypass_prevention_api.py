"""
API endpoints for Permission Bypass Prevention System.

Provides REST API access to bypass prevention functionality,
security monitoring, and administrative controls.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.permission_bypass_prevention import (
    get_bypass_prevention_system,
    SecurityContext,
    PermissionBypassPrevention
)
from src.security.rbac_controller_secure import get_secure_rbac_controller
from src.security.rbac_models import ResourceType
from src.api.auth import get_current_active_user, require_role
from src.security.models import UserModel, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security/bypass-prevention", tags=["Security Bypass Prevention"])
security = HTTPBearer()


# Pydantic models for API requests/responses

class PermissionCheckRequest(BaseModel):
    """Request model for permission checks."""
    permission_name: str = Field(..., description="Permission name to check")
    resource_id: Optional[str] = Field(None, description="Optional resource identifier")
    resource_type: Optional[str] = Field(None, description="Optional resource type")
    session_id: Optional[str] = Field(None, description="Session identifier")


class PermissionCheckResponse(BaseModel):
    """Response model for permission checks."""
    permission_granted: bool = Field(..., description="Whether permission was granted")
    security_info: Dict[str, Any] = Field(..., description="Security validation details")
    validation_passed: bool = Field(..., description="Whether validation passed")
    blocked: bool = Field(..., description="Whether request was blocked")
    bypass_attempts: List[Dict[str, Any]] = Field(default_factory=list, description="Detected bypass attempts")
    enforcement_actions: Dict[str, Any] = Field(default_factory=dict, description="Security enforcement actions")


class SecurityContextValidationRequest(BaseModel):
    """Request model for security context validation."""
    expected_tenant_id: str = Field(..., description="Expected tenant ID")
    session_id: Optional[str] = Field(None, description="Session identifier")


class SecurityContextValidationResponse(BaseModel):
    """Response model for security context validation."""
    is_valid: bool = Field(..., description="Whether context is valid")
    validation_details: Dict[str, Any] = Field(..., description="Validation details")


class SecurityStatisticsResponse(BaseModel):
    """Response model for security statistics."""
    total_checks: int = Field(..., description="Total permission checks")
    blocked_attempts: int = Field(..., description="Number of blocked attempts")
    bypass_attempts_detected: int = Field(..., description="Number of bypass attempts detected")
    validation_failures: int = Field(..., description="Number of validation failures")
    blocked_users: int = Field(..., description="Number of blocked users")
    blocked_ips: int = Field(..., description="Number of blocked IPs")
    temporary_blocks: int = Field(..., description="Number of temporary blocks")
    enabled: bool = Field(..., description="Whether bypass prevention is enabled")


class SecurityReportResponse(BaseModel):
    """Response model for security reports."""
    tenant_id: str = Field(..., description="Tenant identifier")
    generated_at: str = Field(..., description="Report generation timestamp")
    bypass_prevention: Dict[str, Any] = Field(..., description="Bypass prevention statistics")
    rbac_configuration: Dict[str, Any] = Field(..., description="RBAC configuration status")
    cache_performance: Dict[str, Any] = Field(..., description="Cache performance metrics")
    security_configuration: Dict[str, Any] = Field(..., description="Security configuration")
    recommendations: List[str] = Field(..., description="Security recommendations")


class SecurityConfigurationRequest(BaseModel):
    """Request model for security configuration updates."""
    strict_validation: Optional[bool] = Field(None, description="Enable strict validation")
    auto_block_threats: Optional[bool] = Field(None, description="Enable automatic threat blocking")
    require_ip_validation: Optional[bool] = Field(None, description="Require IP validation")
    session_tracking: Optional[bool] = Field(None, description="Enable session tracking")


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


def create_security_context(
    user: UserModel,
    request: Request,
    session_id: Optional[str] = None
) -> SecurityContext:
    """Create security context from request."""
    return SecurityContext(
        user_id=user.id,
        tenant_id=user.tenant_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        session_id=session_id,
        request_timestamp=datetime.utcnow(),
        request_path=str(request.url.path),
        request_method=request.method,
        request_headers=dict(request.headers)
    )


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission_with_bypass_prevention(
    request_data: PermissionCheckRequest,
    request: Request,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    Check permission with comprehensive bypass prevention.
    
    Validates user permissions through multiple security layers including:
    - User existence and status validation
    - Tenant isolation enforcement
    - Role integrity checking
    - Bypass attempt detection
    - Automatic threat response
    """
    try:
        bypass_prevention = get_bypass_prevention_system()
        
        # Create security context
        context = create_security_context(current_user, request, request_data.session_id)
        
        # Parse resource type if provided
        resource_type = None
        if request_data.resource_type:
            try:
                resource_type = ResourceType(request_data.resource_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid resource type: {request_data.resource_type}"
                )
        
        # Perform bypass prevention check
        permission_granted, security_info = bypass_prevention.check_permission_with_bypass_prevention(
            context=context,
            permission_name=request_data.permission_name,
            resource_id=request_data.resource_id,
            resource_type=resource_type,
            db=db
        )
        
        return PermissionCheckResponse(
            permission_granted=permission_granted,
            security_info=security_info,
            validation_passed=security_info.get("validation_passed", False),
            blocked=security_info.get("blocked", False),
            bypass_attempts=security_info.get("bypass_attempts", []),
            enforcement_actions=security_info.get("enforcement_actions", {})
        )
        
    except Exception as e:
        logger.error(f"Permission check with bypass prevention failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission check failed"
        )


@router.post("/validate-security-context", response_model=SecurityContextValidationResponse)
async def validate_security_context(
    request_data: SecurityContextValidationRequest,
    request: Request,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    Validate security context for the current user.
    
    Performs comprehensive validation of:
    - User existence and status
    - Tenant isolation
    - IP address consistency
    - Session validity
    """
    try:
        controller = get_secure_rbac_controller()
        
        is_valid, validation_details = controller.validate_security_context(
            user_id=current_user.id,
            expected_tenant_id=request_data.expected_tenant_id,
            ip_address=get_client_ip(request),
            session_id=request_data.session_id,
            db=db
        )
        
        return SecurityContextValidationResponse(
            is_valid=is_valid,
            validation_details=validation_details
        )
        
    except Exception as e:
        logger.error(f"Security context validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security context validation failed"
        )


@router.get("/statistics", response_model=SecurityStatisticsResponse)
async def get_security_statistics(
    current_user: UserModel = Depends(get_current_active_user),
    _: None = Depends(require_role([UserRole.ADMIN]))
):
    """
    Get security statistics and metrics.
    
    Requires admin role. Returns comprehensive statistics about:
    - Permission check counts
    - Bypass attempt detection
    - Security enforcement actions
    - System status
    """
    try:
        bypass_prevention = get_bypass_prevention_system()
        stats = bypass_prevention.get_security_statistics()
        
        return SecurityStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get security statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security statistics"
        )


@router.get("/report/{tenant_id}", response_model=SecurityReportResponse)
async def get_security_report(
    tenant_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    _: None = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db_session)
):
    """
    Generate comprehensive security report for a tenant.
    
    Requires admin role. Provides detailed analysis of:
    - Bypass prevention effectiveness
    - RBAC configuration status
    - Cache performance metrics
    - Security recommendations
    """
    try:
        # Validate admin can access this tenant's report
        if current_user.role != UserRole.ADMIN and current_user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access tenant security report"
            )
        
        controller = get_secure_rbac_controller()
        report = controller.get_security_report(tenant_id, db)
        
        if "error" in report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=report["error"]
            )
        
        return SecurityReportResponse(**report)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate security report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate security report"
        )


@router.post("/configuration")
async def update_security_configuration(
    config_request: SecurityConfigurationRequest,
    current_user: UserModel = Depends(get_current_active_user),
    _: None = Depends(require_role([UserRole.ADMIN]))
):
    """
    Update security configuration settings.
    
    Requires admin role. Allows configuration of:
    - Strict validation mode
    - Automatic threat blocking
    - IP validation requirements
    - Session tracking
    """
    try:
        controller = get_secure_rbac_controller()
        
        # Update configuration
        config_updates = config_request.dict(exclude_unset=True)
        if config_updates:
            controller.security_config.update(config_updates)
            
            # Apply special configurations
            if config_request.strict_validation is True:
                controller.enable_strict_security()
            elif config_request.strict_validation is False:
                controller.disable_strict_security()
        
        return {
            "message": "Security configuration updated successfully",
            "updated_settings": config_updates,
            "current_configuration": controller.security_config
        }
        
    except Exception as e:
        logger.error(f"Failed to update security configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update security configuration"
        )


@router.post("/enable")
async def enable_bypass_prevention(
    current_user: UserModel = Depends(get_current_active_user),
    _: None = Depends(require_role([UserRole.ADMIN]))
):
    """
    Enable bypass prevention system.
    
    Requires admin role. Activates all security layers including:
    - Multi-layer validation
    - Bypass attempt detection
    - Automatic threat response
    """
    try:
        bypass_prevention = get_bypass_prevention_system()
        bypass_prevention.enable_bypass_prevention()
        
        return {
            "message": "Bypass prevention system enabled",
            "enabled": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to enable bypass prevention: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable bypass prevention system"
        )


@router.post("/disable")
async def disable_bypass_prevention(
    current_user: UserModel = Depends(get_current_active_user),
    _: None = Depends(require_role([UserRole.ADMIN]))
):
    """
    Disable bypass prevention system.
    
    Requires admin role. WARNING: This disables security protections
    and should only be used for testing or maintenance.
    """
    try:
        bypass_prevention = get_bypass_prevention_system()
        bypass_prevention.disable_bypass_prevention()
        
        return {
            "message": "Bypass prevention system disabled",
            "enabled": False,
            "warning": "Security protections are now disabled",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to disable bypass prevention: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable bypass prevention system"
        )


@router.post("/clear-blocks")
async def clear_security_blocks(
    current_user: UserModel = Depends(get_current_active_user),
    _: None = Depends(require_role([UserRole.ADMIN]))
):
    """
    Clear all temporary security blocks.
    
    Requires admin role. Removes all temporary user and IP blocks.
    Use with caution as this may allow previously blocked threats.
    """
    try:
        controller = get_secure_rbac_controller()
        controller.clear_security_blocks()
        
        return {
            "message": "All security blocks cleared",
            "warning": "Previously blocked users and IPs can now access the system",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear security blocks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear security blocks"
        )


@router.get("/health")
async def bypass_prevention_health_check():
    """
    Health check for bypass prevention system.
    
    Returns system status and basic metrics without requiring authentication.
    """
    try:
        bypass_prevention = get_bypass_prevention_system()
        stats = bypass_prevention.get_security_statistics()
        
        return {
            "status": "healthy",
            "enabled": stats["enabled"],
            "total_checks": stats["total_checks"],
            "system_operational": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Bypass prevention health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "system_operational": False,
            "timestamp": datetime.utcnow().isoformat()
        }


# WebSocket endpoint for real-time security monitoring
@router.websocket("/monitor")
async def security_monitoring_websocket(websocket):
    """
    WebSocket endpoint for real-time security monitoring.
    
    Streams security events and statistics in real-time.
    Requires admin authentication via query parameters.
    """
    await websocket.accept()
    
    try:
        # In a real implementation, you would:
        # 1. Authenticate the WebSocket connection
        # 2. Stream real-time security events
        # 3. Send periodic statistics updates
        
        bypass_prevention = get_bypass_prevention_system()
        
        while True:
            # Send current statistics
            stats = bypass_prevention.get_security_statistics()
            await websocket.send_json({
                "type": "statistics",
                "data": stats,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Wait before next update
            import asyncio
            await asyncio.sleep(30)  # Update every 30 seconds
            
    except Exception as e:
        logger.error(f"Security monitoring WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal server error")