"""
Enhanced Sync Push API Routes.

Enterprise-level push API with:
- Incremental push with permission validation
- Push target management
- Push routing and load balancing
- Push result verification and confirmation
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.sync.gateway.auth import (
    AuthToken,
    Permission,
    PermissionLevel,
    ResourceType,
    get_tenant_id,
    sync_auth_handler,
)
from src.sync.push import (
    IncrementalPushService,
    PushTargetManager,
    PushRouter,
    PushResultVerifier
)
from src.sync.push.incremental_push import ChangeRecord, PushContext
from src.sync.push.target_manager import PushTargetConfig
from src.sync.push.result_verifier import VerificationRule, ConfirmationRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sync/push/enterprise", tags=["sync-push-enterprise"])

# Initialize services
push_service = IncrementalPushService()
target_manager = PushTargetManager()
push_router = PushRouter(target_manager)
result_verifier = PushResultVerifier()


# ============================================================================
# Request/Response Models
# ============================================================================

class IncrementalPushRequest(BaseModel):
    """Request for incremental push operation."""
    source_id: str
    target_ids: Optional[List[str]] = None  # If None, use routing
    since_timestamp: Optional[datetime] = None
    verification_rules: Optional[List[str]] = None
    confirmation_type: str = "auto"  # auto, manual, delayed
    priority: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IncrementalPushResponse(BaseModel):
    """Response for incremental push operation."""
    push_id: str
    tenant_id: str
    source_id: str
    changes_detected: int
    changes_pushed: int
    target_results: List[Dict[str, Any]]
    verification_results: List[Dict[str, Any]]
    confirmation_status: str
    total_execution_time_ms: float
    status: str
    message: str


class CreateTargetRequest(BaseModel):
    """Request to create push target."""
    name: str
    description: Optional[str] = None
    target_type: str  # database, api, file, webhook, queue
    connection_config: Dict[str, Any]
    format_config: Dict[str, Any] = Field(default_factory=dict)
    retry_config: Dict[str, Any] = Field(default_factory=dict)
    routing_config: Dict[str, Any] = Field(default_factory=dict)
    health_check_config: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 1
    weight: int = 100


class CreateTargetResponse(BaseModel):
    """Response for target creation."""
    target_id: str
    name: str
    target_type: str
    status: str
    health_status: str
    created_at: datetime
    message: str


class TargetListResponse(BaseModel):
    """Response for target listing."""
    targets: List[Dict[str, Any]]
    total: int
    statistics: Dict[str, Any]


class PushStatusResponse(BaseModel):
    """Response for push status query."""
    push_id: str
    status: str
    progress: float
    changes_detected: int
    changes_pushed: int
    changes_failed: int
    verification_status: str
    confirmation_status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ============================================================================
# Incremental Push Endpoints
# ============================================================================

@router.post("/incremental", response_model=IncrementalPushResponse)
async def execute_incremental_push(
    request: IncrementalPushRequest,
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.WRITE)
    )
):
    """
    Execute incremental push operation.
    
    Detects changes since last push, validates permissions, routes to appropriate
    targets, and verifies results with optional confirmation.
    """
    push_id = str(uuid4())
    start_time = datetime.utcnow()
    
    try:
        # Step 1: Detect changes
        changes = await push_service.detect_changes(
            tenant_id=tenant_id,
            source_id=request.source_id,
            since_timestamp=request.since_timestamp
        )
        
        if not changes:
            return IncrementalPushResponse(
                push_id=push_id,
                tenant_id=tenant_id,
                source_id=request.source_id,
                changes_detected=0,
                changes_pushed=0,
                target_results=[],
                verification_results=[],
                confirmation_status="not_required",
                total_execution_time_ms=0.0,
                status="success",
                message="No changes detected"
            )
        
        # Step 2: Validate permissions
        if request.target_ids:
            # Use specified targets
            selected_targets = []
            permission_errors = []
            
            for target_id in request.target_ids:
                target = await target_manager.get_target(tenant_id, target_id)
                if target:
                    allowed_changes, errors = await push_service.validate_push_permissions(
                        auth, tenant_id, changes, target_id
                    )
                    if allowed_changes:
                        selected_targets.append(target)
                    permission_errors.extend(errors)
                else:
                    permission_errors.append(f"Target {target_id} not found")
            
            if permission_errors:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission errors: {'; '.join(permission_errors)}"
                )
        else:
            # Use routing to select targets
            context = PushContext(
                tenant_id=tenant_id,
                table_name=changes[0].table_name if changes else None,
                operation=changes[0].operation if changes else None,
                record_count=len(changes),
                data_size_bytes=sum(len(str(c.new_data or {})) for c in changes),
                priority=request.priority,
                metadata=request.metadata
            )
            
            routing_decision = await push_router.route_push(context, changes)
            selected_targets = routing_decision.selected_targets
            
            if not selected_targets:
                raise HTTPException(
                    status_code=404,
                    detail="No available targets for push operation"
                )
            
            # Validate permissions for routed targets
            validated_targets = []
            for target in selected_targets:
                allowed_changes, errors = await push_service.validate_push_permissions(
                    auth, tenant_id, changes, target.target_id
                )
                if allowed_changes:
                    validated_targets.append(target)
                elif errors:
                    logger.warning(f"Permission denied for target {target.target_id}: {errors}")
            
            selected_targets = validated_targets
        
        if not selected_targets:
            raise HTTPException(
                status_code=403,
                detail="No targets available after permission validation"
            )
        
        # Step 3: Execute push operations
        target_results = []
        total_pushed = 0
        
        for target in selected_targets:
            # Validate permissions for this specific target
            allowed_changes, permission_errors = await push_service.validate_push_permissions(
                auth, tenant_id, changes, target.target_id
            )
            
            if not allowed_changes:
                target_results.append({
                    "target_id": target.target_id,
                    "status": "permission_denied",
                    "records_pushed": 0,
                    "records_failed": len(changes),
                    "error_message": f"Permission denied: {'; '.join(permission_errors)}"
                })
                continue
            
            # Execute push with retry
            push_result = await push_service.push_with_retry(
                tenant_id=tenant_id,
                changes=allowed_changes,
                target=target,
                max_retries=3
            )
            
            target_results.append({
                "target_id": target.target_id,
                "status": push_result.status,
                "records_pushed": push_result.records_pushed,
                "records_failed": push_result.records_failed,
                "execution_time_ms": push_result.execution_time_ms,
                "retry_count": push_result.retry_count,
                "error_message": push_result.error_message
            })
            
            total_pushed += push_result.records_pushed
        
        # Step 4: Verify results
        verification_results = []
        for i, target in enumerate(selected_targets):
            target_result = target_results[i]
            if target_result["status"] == "success":
                # Create mock push result for verification
                from src.sync.push.incremental_push import PushResult
                mock_push_result = PushResult(
                    push_id=push_id,
                    target_id=target.target_id,
                    status=target_result["status"],
                    records_pushed=target_result["records_pushed"],
                    records_failed=target_result["records_failed"],
                    execution_time_ms=target_result["execution_time_ms"]
                )
                
                verifications = await result_verifier.verify_push_result(
                    push_result=mock_push_result,
                    target=target,
                    original_changes=changes,
                    verification_rules=request.verification_rules
                )
                
                for verification in verifications:
                    verification_results.append({
                        "verification_id": verification.verification_id,
                        "rule_id": verification.rule_id,
                        "target_id": verification.target_id,
                        "status": verification.status,
                        "records_verified": verification.records_verified,
                        "records_failed": verification.records_failed,
                        "error_message": verification.error_message
                    })
        
        # Step 5: Process confirmation
        confirmation_status = "not_required"
        if request.confirmation_type != "none":
            # For demo, auto-confirm if all verifications passed
            all_verifications_passed = all(
                v["status"] == "success" for v in verification_results
            )
            confirmation_status = "confirmed" if all_verifications_passed else "rejected"
        
        # Calculate total execution time
        total_execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Determine overall status
        successful_targets = len([r for r in target_results if r["status"] == "success"])
        if successful_targets == len(target_results):
            overall_status = "success"
        elif successful_targets > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"
        
        logger.info(
            f"Incremental push {push_id} completed: "
            f"{len(changes)} changes detected, {total_pushed} records pushed to {len(selected_targets)} targets"
        )
        
        return IncrementalPushResponse(
            push_id=push_id,
            tenant_id=tenant_id,
            source_id=request.source_id,
            changes_detected=len(changes),
            changes_pushed=total_pushed,
            target_results=target_results,
            verification_results=verification_results,
            confirmation_status=confirmation_status,
            total_execution_time_ms=total_execution_time,
            status=overall_status,
            message=f"Pushed {total_pushed} records to {successful_targets}/{len(selected_targets)} targets"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in incremental push: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Target Management Endpoints
# ============================================================================

@router.post("/targets", response_model=CreateTargetResponse)
async def create_push_target(
    request: CreateTargetRequest,
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.ADMIN)
    )
):
    """Create a new push target."""
    try:
        target_config = {
            "name": request.name,
            "description": request.description,
            "target_type": request.target_type,
            "connection_config": request.connection_config,
            "format_config": request.format_config,
            "retry_config": request.retry_config,
            "routing_config": request.routing_config,
            "health_check_config": request.health_check_config,
            "priority": request.priority,
            "weight": request.weight
        }
        
        target = await target_manager.create_target(tenant_id, target_config)
        
        return CreateTargetResponse(
            target_id=target.target_id,
            name=target.name,
            target_type=target.target_type,
            status="created",
            health_status=target.health_status,
            created_at=target.created_at,
            message="Push target created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating push target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/targets", response_model=TargetListResponse)
async def list_push_targets(
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    enabled_only: bool = Query(False, description="Only return enabled targets"),
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.READ)
    )
):
    """List push targets for the tenant."""
    try:
        targets = await target_manager.list_targets(
            tenant_id=tenant_id,
            target_type=target_type,
            enabled_only=enabled_only
        )
        
        target_data = []
        for target in targets:
            target_data.append({
                "target_id": target.target_id,
                "name": target.name,
                "description": target.description,
                "target_type": target.target_type,
                "enabled": target.enabled,
                "priority": target.priority,
                "weight": target.weight,
                "health_status": target.health_status,
                "consecutive_failures": target.consecutive_failures,
                "last_health_check": target.last_health_check,
                "created_at": target.created_at,
                "updated_at": target.updated_at
            })
        
        statistics = target_manager.get_target_statistics(tenant_id)
        
        return TargetListResponse(
            targets=target_data,
            total=len(target_data),
            statistics=statistics
        )
        
    except Exception as e:
        logger.error(f"Error listing push targets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/targets/{target_id}")
async def get_push_target(
    target_id: str,
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.READ)
    )
):
    """Get push target details."""
    try:
        target = await target_manager.get_target(tenant_id, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Push target not found")
        
        # Don't expose sensitive connection config
        safe_config = {k: v for k, v in target.connection_config.items() 
                      if k not in ["password", "api_key", "secret", "token"]}
        
        return {
            "target_id": target.target_id,
            "name": target.name,
            "description": target.description,
            "target_type": target.target_type,
            "connection_config": safe_config,
            "format_config": target.format_config,
            "retry_config": target.retry_config,
            "routing_config": target.routing_config,
            "health_check_config": target.health_check_config,
            "enabled": target.enabled,
            "priority": target.priority,
            "weight": target.weight,
            "health_status": target.health_status,
            "consecutive_failures": target.consecutive_failures,
            "last_health_check": target.last_health_check,
            "last_error": target.last_error,
            "created_at": target.created_at,
            "updated_at": target.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting push target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/targets/{target_id}")
async def update_push_target(
    target_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.ADMIN)
    )
):
    """Update push target configuration."""
    try:
        target = await target_manager.update_target(tenant_id, target_id, updates)
        
        return {
            "target_id": target.target_id,
            "status": "updated",
            "updated_at": target.updated_at,
            "message": "Push target updated successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating push target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/targets/{target_id}")
async def delete_push_target(
    target_id: str,
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.ADMIN)
    )
):
    """Delete push target."""
    try:
        success = await target_manager.delete_target(tenant_id, target_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Push target not found")
        
        return {
            "target_id": target_id,
            "status": "deleted",
            "message": "Push target deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting push target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check and Monitoring Endpoints
# ============================================================================

@router.post("/targets/health-check")
async def run_health_checks(
    target_id: Optional[str] = Query(None, description="Check specific target only"),
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.READ)
    )
):
    """Run health checks on push targets."""
    try:
        results = await target_manager.run_health_checks(tenant_id)
        
        if target_id:
            results = {target_id: results.get(target_id)} if target_id in results else {}
        
        health_data = {}
        for tid, result in results.items():
            health_data[tid] = {
                "status": result.status,
                "response_time_ms": result.response_time_ms,
                "error_message": result.error_message,
                "timestamp": result.timestamp
            }
        
        return {
            "health_checks": health_data,
            "total_checked": len(health_data),
            "healthy_targets": len([r for r in results.values() if r.status == "healthy"]),
            "unhealthy_targets": len([r for r in results.values() if r.status == "unhealthy"])
        }
        
    except Exception as e:
        logger.error(f"Error running health checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_push_statistics(
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.READ)
    )
):
    """Get comprehensive push statistics."""
    try:
        target_stats = target_manager.get_target_statistics(tenant_id)
        routing_stats = push_router.get_routing_statistics(tenant_id)
        verification_stats = result_verifier.get_verification_statistics()
        
        return {
            "target_statistics": target_stats,
            "routing_statistics": routing_stats,
            "verification_statistics": verification_stats,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error getting push statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Verification and Confirmation Endpoints
# ============================================================================

@router.get("/verification/rules")
async def list_verification_rules(
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.READ)
    )
):
    """List available verification rules."""
    try:
        rules = result_verifier.list_verification_rules()
        
        rule_data = []
        for rule in rules:
            rule_data.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "rule_type": rule.rule_type,
                "enabled": rule.enabled,
                "error_threshold": rule.error_threshold,
                "timeout_seconds": rule.timeout_seconds,
                "max_retries": rule.max_retries
            })
        
        return {
            "verification_rules": rule_data,
            "total": len(rule_data)
        }
        
    except Exception as e:
        logger.error(f"Error listing verification rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verification/rules")
async def create_verification_rule(
    rule_data: Dict[str, Any],
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.ADMIN)
    )
):
    """Create custom verification rule."""
    try:
        rule = VerificationRule(**rule_data)
        result_verifier.add_verification_rule(rule)
        
        return {
            "rule_id": rule.rule_id,
            "status": "created",
            "message": "Verification rule created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating verification rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/push/{push_id}/status", response_model=PushStatusResponse)
async def get_push_status(
    push_id: str,
    tenant_id: str = Depends(get_tenant_id),
    auth: AuthToken = Depends(
        sync_auth_handler.require_permission(ResourceType.SYNC_JOB, PermissionLevel.READ)
    )
):
    """Get status of a push operation."""
    try:
        # In production, this would query the database for push status
        # For now, return a mock status
        return PushStatusResponse(
            push_id=push_id,
            status="completed",
            progress=1.0,
            changes_detected=100,
            changes_pushed=95,
            changes_failed=5,
            verification_status="passed",
            confirmation_status="confirmed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting push status: {e}")
        raise HTTPException(status_code=500, detail=str(e))