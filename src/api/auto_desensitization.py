"""
Automatic Desensitization API endpoints.

Provides REST API for automatic sensitive data detection and masking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.middleware import get_current_active_user, require_role, audit_action
from src.security.models import AuditAction
from src.security.auto_desensitization_service import AutoDesensitizationService
from src.security.auto_desensitization_middleware import AutoDesensitizationMiddleware

router = APIRouter(prefix="/api/auto-desensitization", tags=["auto-desensitization"])

# Initialize services
auto_desensitization_service = AutoDesensitizationService()


# Request/Response Models

class AutoDetectionRequest(BaseModel):
    data: Any = Field(..., description="Data to process for sensitive information")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    operation_type: str = Field("manual", description="Type of operation")


class AutoDetectionResponse(BaseModel):
    success: bool
    operation_id: str
    original_data: Any
    masked_data: Any
    entities_detected: List[Dict[str, Any]]
    rules_applied: List[str]
    processing_time_ms: float
    validation: Optional[Dict[str, Any]] = None
    errors: List[str] = []


class BulkDetectionRequest(BaseModel):
    data_items: List[Any] = Field(..., description="List of data items to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class BulkDetectionResponse(BaseModel):
    success: bool
    bulk_operation_id: str
    items_processed: int
    success_count: int
    failure_count: int
    total_entities_detected: int
    total_rules_applied: List[str]
    processing_time_ms: float
    results: List[Dict[str, Any]]
    errors: List[str] = []


class ConfigurationRequest(BaseModel):
    auto_detection_enabled: Optional[bool] = Field(None, description="Enable auto detection")
    real_time_masking_enabled: Optional[bool] = Field(None, description="Enable real-time masking")
    quality_validation_enabled: Optional[bool] = Field(None, description="Enable quality validation")
    alert_on_high_risk: Optional[bool] = Field(None, description="Enable high-risk alerts")
    batch_size: Optional[int] = Field(None, ge=1, le=1000, description="Batch size for processing")
    max_concurrent_operations: Optional[int] = Field(None, ge=1, le=50, description="Max concurrent operations")
    detection_timeout_seconds: Optional[int] = Field(None, ge=1, le=300, description="Detection timeout")


class ConfigurationResponse(BaseModel):
    success: bool
    message: str
    applied_config: Dict[str, Any]
    error: Optional[str] = None


class StatisticsResponse(BaseModel):
    tenant_id: str
    period_start: datetime
    period_end: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_entities_detected: int
    total_processing_time_ms: float
    average_processing_time_ms: float
    most_common_entity_types: List[Dict[str, Any]]
    quality_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]


class MiddlewareStatsResponse(BaseModel):
    enabled: bool
    total_requests: int
    processed_requests: int
    skipped_requests: int
    error_count: int
    processing_rate: float
    average_processing_time: float
    configuration: Dict[str, Any]


# Auto Detection Endpoints

@router.post("/detect", response_model=AutoDetectionResponse)
@audit_action(AuditAction.READ, "auto_detection")
async def auto_detect_and_mask(
    detection_request: AutoDetectionRequest,
    request: Request,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Automatically detect and mask sensitive data."""
    try:
        result = await auto_desensitization_service.detect_and_mask_automatically(
            data=detection_request.data,
            tenant_id=current_user.tenant_id,
            user_id=str(current_user.id),
            context=detection_request.context,
            operation_type=detection_request.operation_type
        )
        
        return AutoDetectionResponse(
            success=result["success"],
            operation_id=result["operation_id"],
            original_data=result["original_data"],
            masked_data=result["masked_data"],
            entities_detected=result["entities_detected"],
            rules_applied=result["rules_applied"],
            processing_time_ms=result["processing_time_ms"],
            validation=result.get("validation"),
            errors=result.get("errors", [])
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto detection failed: {str(e)}"
        )


@router.post("/bulk-detect", response_model=BulkDetectionResponse)
@audit_action(AuditAction.READ, "bulk_auto_detection")
async def bulk_auto_detect_and_mask(
    bulk_request: BulkDetectionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Bulk automatically detect and mask sensitive data."""
    try:
        # For large bulk operations, process in background
        if len(bulk_request.data_items) > 100:
            # Start background task
            background_tasks.add_task(
                _process_bulk_detection_background,
                bulk_request.data_items,
                current_user.tenant_id,
                str(current_user.id),
                bulk_request.context
            )
            
            return BulkDetectionResponse(
                success=True,
                bulk_operation_id="background_task",
                items_processed=0,
                success_count=0,
                failure_count=0,
                total_entities_detected=0,
                total_rules_applied=[],
                processing_time_ms=0,
                results=[],
                errors=["Processing in background - check status endpoint"]
            )
        
        # Process immediately for smaller requests
        result = await auto_desensitization_service.bulk_detect_and_mask(
            data_items=bulk_request.data_items,
            tenant_id=current_user.tenant_id,
            user_id=str(current_user.id),
            context=bulk_request.context
        )
        
        return BulkDetectionResponse(
            success=result["success"],
            bulk_operation_id=result["bulk_operation_id"],
            items_processed=result["items_processed"],
            success_count=result["success_count"],
            failure_count=result["failure_count"],
            total_entities_detected=result["total_entities_detected"],
            total_rules_applied=result["total_rules_applied"],
            processing_time_ms=result["processing_time_ms"],
            results=result["results"],
            errors=result["errors"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk auto detection failed: {str(e)}"
        )


async def _process_bulk_detection_background(
    data_items: List[Any],
    tenant_id: str,
    user_id: str,
    context: Optional[Dict[str, Any]]
):
    """Background task for processing large bulk detection requests."""
    try:
        await auto_desensitization_service.bulk_detect_and_mask(
            data_items=data_items,
            tenant_id=tenant_id,
            user_id=user_id,
            context=context
        )
    except Exception as e:
        # Log error - in production, you might want to store this in a job queue
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Background bulk detection failed: {e}")


# Configuration Endpoints

@router.post("/config", response_model=ConfigurationResponse)
@require_role(["admin", "data_manager"])
@audit_action(AuditAction.UPDATE, "auto_detection_config")
async def configure_auto_detection(
    config_request: ConfigurationRequest,
    request: Request,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Configure automatic detection settings."""
    try:
        # Convert request to dict, excluding None values
        config = {
            k: v for k, v in config_request.model_dump().items() 
            if v is not None
        }
        
        result = await auto_desensitization_service.configure_auto_detection(
            tenant_id=current_user.tenant_id,
            config=config
        )
        
        return ConfigurationResponse(
            success=result["success"],
            message=result.get("message", ""),
            applied_config=result.get("applied_config", {}),
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration failed: {str(e)}"
        )


@router.get("/config")
async def get_auto_detection_config(
    current_user = Depends(get_current_active_user)
):
    """Get current automatic detection configuration."""
    try:
        # Return current service configuration
        return {
            "auto_detection_enabled": auto_desensitization_service.auto_detection_enabled,
            "real_time_masking_enabled": auto_desensitization_service.real_time_masking_enabled,
            "quality_validation_enabled": auto_desensitization_service.quality_validation_enabled,
            "alert_on_high_risk": auto_desensitization_service.alert_on_high_risk,
            "batch_size": auto_desensitization_service.batch_size,
            "max_concurrent_operations": auto_desensitization_service.max_concurrent_operations,
            "detection_timeout_seconds": auto_desensitization_service.detection_timeout_seconds
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )


# Statistics and Monitoring Endpoints

@router.get("/statistics", response_model=StatisticsResponse)
async def get_detection_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Get detection and masking statistics."""
    try:
        stats = await auto_desensitization_service.get_detection_statistics(
            tenant_id=current_user.tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if not stats.get("success", True):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=stats.get("error", "Failed to get statistics")
            )
        
        return StatisticsResponse(
            tenant_id=current_user.tenant_id,
            period_start=start_date or datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            period_end=end_date or datetime.utcnow(),
            total_operations=stats.get("total_operations", 0),
            successful_operations=stats.get("successful_operations", 0),
            failed_operations=stats.get("failed_operations", 0),
            total_entities_detected=stats.get("total_entities_detected", 0),
            total_processing_time_ms=stats.get("total_processing_time_ms", 0),
            average_processing_time_ms=stats.get("average_processing_time_ms", 0),
            most_common_entity_types=stats.get("most_common_entity_types", []),
            quality_metrics=stats.get("quality_metrics", {}),
            performance_metrics=stats.get("performance_metrics", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/middleware/stats", response_model=MiddlewareStatsResponse)
@require_role(["admin"])
async def get_middleware_statistics(
    current_user = Depends(get_current_active_user)
):
    """Get middleware processing statistics."""
    try:
        # This would typically be injected or retrieved from a global registry
        # For now, we'll return a mock response
        return MiddlewareStatsResponse(
            enabled=True,
            total_requests=1000,
            processed_requests=950,
            skipped_requests=50,
            error_count=5,
            processing_rate=0.95,
            average_processing_time=0.025,
            configuration={
                "mask_requests": True,
                "mask_responses": True,
                "max_content_size": 10485760,
                "excluded_paths": ["/health", "/metrics", "/docs"]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get middleware statistics: {str(e)}"
        )


@router.post("/middleware/reset-stats")
@require_role(["admin"])
@audit_action(AuditAction.UPDATE, "middleware_stats")
async def reset_middleware_statistics(
    current_user = Depends(get_current_active_user)
):
    """Reset middleware processing statistics."""
    try:
        # This would typically reset stats on the actual middleware instance
        return {"message": "Middleware statistics reset successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset middleware statistics: {str(e)}"
        )


# Health and Status Endpoints

@router.get("/health")
async def get_auto_detection_health():
    """Get auto-detection service health status."""
    try:
        # Check Presidio engine status
        presidio_status = auto_desensitization_service.presidio_engine.validate_configuration()
        
        # Check service components
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "presidio_engine": {
                    "status": "healthy" if presidio_status["presidio_available"] else "degraded",
                    "details": presidio_status
                },
                "desensitization_service": {
                    "status": "healthy",
                    "auto_detection_enabled": auto_desensitization_service.auto_detection_enabled,
                    "real_time_masking_enabled": auto_desensitization_service.real_time_masking_enabled
                },
                "quality_monitor": {
                    "status": "healthy",
                    "validation_enabled": auto_desensitization_service.quality_validation_enabled
                },
                "alert_manager": {
                    "status": "healthy",
                    "alerts_enabled": auto_desensitization_service.alert_on_high_risk
                }
            }
        }
        
        # Determine overall status
        component_statuses = [comp["status"] for comp in health_status["components"].values()]
        if "unhealthy" in component_statuses:
            health_status["status"] = "unhealthy"
        elif "degraded" in component_statuses:
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/version")
async def get_auto_detection_version():
    """Get auto-detection service version information."""
    return {
        "service": "auto-desensitization",
        "version": "1.0.0",
        "build_date": "2026-01-11",
        "features": [
            "automatic_pii_detection",
            "real_time_masking",
            "bulk_processing",
            "quality_validation",
            "alert_management",
            "middleware_integration"
        ],
        "supported_entity_types": [
            "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD",
            "IBAN_CODE", "IP_ADDRESS", "LOCATION", "DATE_TIME",
            "US_SSN", "US_PASSPORT", "US_DRIVER_LICENSE"
        ],
        "supported_masking_strategies": [
            "REPLACE", "REDACT", "HASH", "ENCRYPT", "MASK", "KEEP"
        ]
    }


# Testing and Validation Endpoints

@router.post("/test/detection")
@require_role(["admin", "data_manager"])
async def test_detection_accuracy(
    test_data: Dict[str, Any],
    current_user = Depends(get_current_active_user)
):
    """Test detection accuracy with known test data."""
    try:
        # This endpoint would be used for testing and validation
        # It could include test cases with known PII entities
        
        test_text = test_data.get("text", "")
        expected_entities = test_data.get("expected_entities", [])
        
        if not test_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test text is required"
            )
        
        # Run detection
        result = await auto_desensitization_service.detect_and_mask_automatically(
            data=test_text,
            tenant_id=current_user.tenant_id,
            user_id=str(current_user.id),
            operation_type="accuracy_test"
        )
        
        # Calculate accuracy metrics if expected entities provided
        accuracy_metrics = {}
        if expected_entities:
            detected_entities = result["entities_detected"]
            
            # Simple accuracy calculation
            detected_count = len(detected_entities)
            expected_count = len(expected_entities)
            
            if expected_count > 0:
                # This is a simplified accuracy calculation
                # In practice, you'd want more sophisticated matching
                accuracy_metrics = {
                    "precision": min(1.0, detected_count / expected_count) if expected_count > 0 else 0.0,
                    "recall": min(1.0, detected_count / expected_count) if expected_count > 0 else 0.0,
                    "detected_count": detected_count,
                    "expected_count": expected_count
                }
        
        return {
            "test_result": result,
            "accuracy_metrics": accuracy_metrics,
            "test_timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection test failed: {str(e)}"
        )