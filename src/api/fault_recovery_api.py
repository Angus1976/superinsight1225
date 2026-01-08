"""
Fault Detection and Recovery API for SuperInsight Platform.

Provides REST API endpoints for:
- System status monitoring
- Fault detection management
- Recovery orchestration
- Service dependency visualization
- Health monitoring
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from pydantic import BaseModel, Field

from src.system.fault_recovery_integration import (
    fault_recovery_integration, start_fault_recovery_system, stop_fault_recovery_system,
    get_fault_recovery_status
)
from src.system.fault_detection_system import fault_detection_system, FaultType, FaultSeverity
from src.system.recovery_orchestrator import recovery_orchestrator
from src.system.service_dependency_mapper import service_dependency_mapper, DependencyType
from src.system.health_monitor import health_monitor

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/fault-recovery", tags=["Fault Recovery"])


# Pydantic models for API
class SystemStatusResponse(BaseModel):
    """System status response model."""
    integration_active: bool
    system_health: str
    active_faults: int
    active_recoveries: int
    all_components_active: bool
    timestamp: datetime


class FaultEventResponse(BaseModel):
    """Fault event response model."""
    fault_id: str
    fault_type: str
    severity: str
    service_name: str
    description: str
    root_cause: Optional[str]
    detected_at: str
    recovery_actions: List[str]
    affected_services: List[str]


class RecoveryPlanResponse(BaseModel):
    """Recovery plan response model."""
    plan_id: str
    fault_id: str
    actions_count: int
    success_rate: float
    duration: Optional[float]
    status: str
    created_at: str


class ServiceDependencyResponse(BaseModel):
    """Service dependency response model."""
    service_name: str
    status: str
    criticality_score: float
    recovery_priority: int
    failure_count: int
    dependencies: List[Dict[str, Any]]
    dependents: List[str]


class DependencyGraphResponse(BaseModel):
    """Dependency graph response model."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    statistics: Dict[str, Any]


class CreateDependencyRequest(BaseModel):
    """Create dependency request model."""
    source_service: str = Field(..., description="Source service name")
    target_service: str = Field(..., description="Target service name")
    dependency_type: str = Field(..., description="Dependency type (hard, soft, optional)")
    weight: float = Field(1.0, ge=0.0, le=1.0, description="Dependency weight")
    timeout_threshold: float = Field(30.0, gt=0, description="Timeout threshold in seconds")
    failure_threshold: int = Field(3, gt=0, description="Failure threshold count")


# System Status Endpoints
@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get overall fault recovery system status."""
    try:
        status = get_fault_recovery_status()
        return SystemStatusResponse(
            integration_active=status["integration_active"],
            system_health=status["system_health"],
            active_faults=status["active_faults"],
            active_recoveries=status["active_recoveries"],
            all_components_active=status["all_components_active"],
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_system_statistics():
    """Get comprehensive system statistics."""
    try:
        return fault_recovery_integration.get_integration_statistics()
    except Exception as e:
        logger.error(f"Error getting system statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_system(background_tasks: BackgroundTasks):
    """Start the fault recovery system."""
    try:
        if fault_recovery_integration.integration_active:
            return {"message": "Fault recovery system is already active"}
        
        background_tasks.add_task(start_fault_recovery_system)
        return {"message": "Fault recovery system startup initiated"}
    except Exception as e:
        logger.error(f"Error starting system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_system(background_tasks: BackgroundTasks):
    """Stop the fault recovery system."""
    try:
        if not fault_recovery_integration.integration_active:
            return {"message": "Fault recovery system is not active"}
        
        background_tasks.add_task(stop_fault_recovery_system)
        return {"message": "Fault recovery system shutdown initiated"}
    except Exception as e:
        logger.error(f"Error stopping system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Fault Detection Endpoints
@router.get("/faults", response_model=List[FaultEventResponse])
async def get_active_faults():
    """Get list of active faults."""
    try:
        active_faults = fault_detection_system.get_active_faults()
        return [
            FaultEventResponse(
                fault_id=fault["fault_id"],
                fault_type=fault["fault_type"],
                severity=fault["severity"],
                service_name=fault["service_name"],
                description=fault["description"],
                root_cause=fault["root_cause"],
                detected_at=fault["detected_at"],
                recovery_actions=fault["recovery_actions"],
                affected_services=fault["affected_services"]
            )
            for fault in active_faults
        ]
    except Exception as e:
        logger.error(f"Error getting active faults: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faults/statistics")
async def get_fault_statistics():
    """Get fault detection statistics."""
    try:
        return fault_detection_system.get_fault_statistics()
    except Exception as e:
        logger.error(f"Error getting fault statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faults/{fault_id}")
async def get_fault_details(fault_id: str = Path(..., description="Fault ID")):
    """Get details for a specific fault."""
    try:
        active_faults = fault_detection_system.get_active_faults()
        
        for fault in active_faults:
            if fault["fault_id"] == fault_id:
                return fault
        
        raise HTTPException(status_code=404, detail="Fault not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fault details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Recovery Orchestration Endpoints
@router.get("/recovery/plans", response_model=List[RecoveryPlanResponse])
async def get_recovery_plans():
    """Get list of recovery plans."""
    try:
        stats = recovery_orchestrator.get_orchestrator_statistics()
        recent_plans = stats.get("recent_plans", [])
        
        return [
            RecoveryPlanResponse(
                plan_id=plan["plan_id"],
                fault_id=plan["fault_id"],
                actions_count=plan["actions_count"],
                success_rate=plan["success_rate"],
                duration=plan["duration"],
                status=plan["status"],
                created_at=plan["created_at"]
            )
            for plan in recent_plans
        ]
    except Exception as e:
        logger.error(f"Error getting recovery plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recovery/statistics")
async def get_recovery_statistics():
    """Get recovery orchestrator statistics."""
    try:
        return recovery_orchestrator.get_orchestrator_statistics()
    except Exception as e:
        logger.error(f"Error getting recovery statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recovery/trigger/{service_name}")
async def trigger_manual_recovery(
    service_name: str = Path(..., description="Service name"),
    fault_type: str = Query("service_unavailable", description="Fault type"),
    severity: str = Query("high", description="Fault severity")
):
    """Manually trigger recovery for a service."""
    try:
        # Validate fault type and severity
        try:
            fault_type_enum = FaultType(fault_type)
            severity_enum = FaultSeverity(severity)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid fault type or severity: {e}")
        
        # Create a mock fault event for manual recovery
        from src.system.fault_detection_system import FaultEvent
        
        fault_event = FaultEvent(
            fault_id=f"manual_{int(datetime.utcnow().timestamp() * 1000)}",
            fault_type=fault_type_enum,
            severity=severity_enum,
            service_name=service_name,
            description=f"Manual recovery triggered for {service_name}",
            detected_at=datetime.utcnow()
        )
        
        # Execute recovery
        from src.system.recovery_orchestrator import execute_fault_recovery
        success = await execute_fault_recovery(fault_event)
        
        return {
            "message": f"Manual recovery {'succeeded' if success else 'failed'} for {service_name}",
            "fault_id": fault_event.fault_id,
            "success": success
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering manual recovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Service Dependencies Endpoints
@router.get("/dependencies/graph", response_model=DependencyGraphResponse)
async def get_dependency_graph():
    """Get service dependency graph data."""
    try:
        graph_data = service_dependency_mapper.get_dependency_graph_data()
        return DependencyGraphResponse(
            nodes=graph_data["nodes"],
            edges=graph_data["edges"],
            statistics=graph_data["statistics"]
        )
    except Exception as e:
        logger.error(f"Error getting dependency graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependencies/services/{service_name}", response_model=ServiceDependencyResponse)
async def get_service_dependencies(service_name: str = Path(..., description="Service name")):
    """Get dependencies for a specific service."""
    try:
        service_deps = service_dependency_mapper.get_service_dependencies(service_name)
        
        if not service_deps:
            raise HTTPException(status_code=404, detail="Service not found")
        
        return ServiceDependencyResponse(
            service_name=service_deps["service_name"],
            status=service_deps["status"],
            criticality_score=service_deps["criticality_score"],
            recovery_priority=service_deps["recovery_priority"],
            failure_count=service_deps["failure_count"],
            dependencies=service_deps["dependencies"],
            dependents=service_deps["dependents"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dependencies")
async def create_dependency(request: CreateDependencyRequest):
    """Create a new service dependency."""
    try:
        # Validate dependency type
        try:
            dependency_type = DependencyType(request.dependency_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid dependency type. Must be one of: {[dt.value for dt in DependencyType]}"
            )
        
        # Add dependency
        dependency = service_dependency_mapper.add_dependency(
            source_service=request.source_service,
            target_service=request.target_service,
            dependency_type=dependency_type,
            weight=request.weight,
            timeout_threshold=request.timeout_threshold,
            failure_threshold=request.failure_threshold
        )
        
        return {
            "message": f"Dependency created: {request.source_service} -> {request.target_service}",
            "dependency": {
                "source_service": dependency.source_service,
                "target_service": dependency.target_service,
                "dependency_type": dependency.dependency_type.value,
                "weight": dependency.weight,
                "timeout_threshold": dependency.timeout_threshold,
                "failure_threshold": dependency.failure_threshold
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating dependency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dependencies/{source_service}/{target_service}")
async def remove_dependency(
    source_service: str = Path(..., description="Source service name"),
    target_service: str = Path(..., description="Target service name")
):
    """Remove a service dependency."""
    try:
        success = service_dependency_mapper.remove_dependency(source_service, target_service)
        
        if not success:
            raise HTTPException(status_code=404, detail="Dependency not found")
        
        return {"message": f"Dependency removed: {source_service} -> {target_service}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing dependency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependencies/statistics")
async def get_dependency_statistics():
    """Get service dependency statistics."""
    try:
        return service_dependency_mapper.get_dependency_statistics()
    except Exception as e:
        logger.error(f"Error getting dependency statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependencies/impact/{service_name}")
async def analyze_service_impact(service_name: str = Path(..., description="Service name")):
    """Analyze the impact of a service failure."""
    try:
        impact_analysis = await service_dependency_mapper._analyze_cascade_impact(service_name)
        
        return {
            "failed_service": impact_analysis.failed_service,
            "directly_affected": impact_analysis.directly_affected,
            "indirectly_affected": impact_analysis.indirectly_affected,
            "cascade_probability": impact_analysis.cascade_probability,
            "estimated_recovery_time": impact_analysis.estimated_recovery_time,
            "recovery_order": impact_analysis.recovery_order
        }
    except Exception as e:
        logger.error(f"Error analyzing service impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Monitoring Endpoints
@router.get("/health/summary")
async def get_health_summary():
    """Get health monitoring summary."""
    try:
        return health_monitor.get_metrics_summary()
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/report")
async def get_health_report():
    """Get comprehensive health report."""
    try:
        report = health_monitor.get_health_report()
        return {
            "timestamp": report.timestamp,
            "overall_status": report.overall_status.value,
            "metrics": {name: metric.to_dict() for name, metric in report.metrics.items()},
            "issues": report.issues,
            "recommendations": report.recommendations,
            "service_health": report.service_health
        }
    except Exception as e:
        logger.error(f"Error getting health report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health/check/{service_name}")
async def force_health_check(service_name: str = Path(..., description="Service name")):
    """Force an immediate health check for a service."""
    try:
        # This would need to be implemented in the health monitor
        # For now, return a placeholder response
        return {
            "message": f"Health check initiated for {service_name}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error forcing health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Endpoints
@router.get("/config/thresholds")
async def get_detection_thresholds():
    """Get fault detection thresholds."""
    try:
        return {
            "performance_thresholds": fault_detection_system.performance_thresholds,
            "fault_patterns": {
                pattern_id: {
                    "pattern_type": pattern.pattern_type,
                    "features": pattern.features,
                    "threshold": pattern.threshold,
                    "confidence": pattern.confidence
                }
                for pattern_id, pattern in fault_detection_system.fault_patterns.items()
            }
        }
    except Exception as e:
        logger.error(f"Error getting detection thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/thresholds")
async def update_detection_thresholds(thresholds: Dict[str, float]):
    """Update fault detection thresholds."""
    try:
        # Validate thresholds
        valid_keys = set(fault_detection_system.performance_thresholds.keys())
        invalid_keys = set(thresholds.keys()) - valid_keys
        
        if invalid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid threshold keys: {invalid_keys}. Valid keys: {valid_keys}"
            )
        
        # Update thresholds
        fault_detection_system.performance_thresholds.update(thresholds)
        
        return {
            "message": "Detection thresholds updated",
            "updated_thresholds": thresholds
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating detection thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Fault Tolerance Endpoints
@router.get("/fault-tolerance/status")
async def get_fault_tolerance_status():
    """Get fault tolerance system status."""
    try:
        from src.system.fault_tolerance_system import get_fault_tolerance_status
        return get_fault_tolerance_status()
    except Exception as e:
        logger.error(f"Error getting fault tolerance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fault-tolerance/circuit-breakers")
async def get_circuit_breakers():
    """Get all circuit breaker statuses."""
    try:
        from src.system.fault_tolerance_system import fault_tolerance_system
        
        circuit_breakers = {}
        for name, cb in fault_tolerance_system.circuit_breakers.items():
            circuit_breakers[name] = cb.get_statistics()
        
        return {"circuit_breakers": circuit_breakers}
    except Exception as e:
        logger.error(f"Error getting circuit breakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fault-tolerance/circuit-breakers/{service_name}")
async def get_circuit_breaker_status(service_name: str = Path(..., description="Service name")):
    """Get circuit breaker status for a specific service."""
    try:
        from src.system.fault_tolerance_system import fault_tolerance_system
        
        if service_name not in fault_tolerance_system.circuit_breakers:
            raise HTTPException(status_code=404, detail=f"Circuit breaker not found for service: {service_name}")
        
        cb = fault_tolerance_system.circuit_breakers[service_name]
        return cb.get_statistics()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting circuit breaker status for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fault-tolerance/rate-limiters")
async def get_rate_limiters():
    """Get all rate limiter statuses."""
    try:
        from src.system.fault_tolerance_system import fault_tolerance_system
        
        rate_limiters = {}
        for name, rl in fault_tolerance_system.rate_limiters.items():
            rate_limiters[name] = rl.get_statistics()
        
        return {"rate_limiters": rate_limiters}
    except Exception as e:
        logger.error(f"Error getting rate limiters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fault-tolerance/rate-limiters/{service_name}")
async def get_rate_limiter_status(service_name: str = Path(..., description="Service name")):
    """Get rate limiter status for a specific service."""
    try:
        from src.system.fault_tolerance_system import fault_tolerance_system
        
        if service_name not in fault_tolerance_system.rate_limiters:
            raise HTTPException(status_code=404, detail=f"Rate limiter not found for service: {service_name}")
        
        rl = fault_tolerance_system.rate_limiters[service_name]
        return rl.get_statistics()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rate limiter status for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fault-tolerance/degradation")
async def get_service_degradation():
    """Get service degradation statuses."""
    try:
        from src.system.fault_tolerance_system import fault_tolerance_system
        
        degradation_status = {}
        for name, dm in fault_tolerance_system.degradation_managers.items():
            degradation_status[name] = dm.get_status()
        
        return {"degradation_managers": degradation_status}
    except Exception as e:
        logger.error(f"Error getting service degradation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fault-tolerance/degradation/{service_name}")
async def get_service_degradation_status(service_name: str = Path(..., description="Service name")):
    """Get degradation status for a specific service."""
    try:
        from src.system.fault_tolerance_system import fault_tolerance_system
        
        if service_name not in fault_tolerance_system.degradation_managers:
            raise HTTPException(status_code=404, detail=f"Degradation manager not found for service: {service_name}")
        
        dm = fault_tolerance_system.degradation_managers[service_name]
        return dm.get_status()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting degradation status for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fault-tolerance/features/{service_name}/{feature_name}")
async def check_feature_enabled(
    service_name: str = Path(..., description="Service name"),
    feature_name: str = Path(..., description="Feature name")
):
    """Check if a feature is enabled for a service."""
    try:
        from src.system.fault_tolerance_system import is_feature_enabled
        
        enabled = is_feature_enabled(service_name, feature_name)
        return {
            "service_name": service_name,
            "feature_name": feature_name,
            "enabled": enabled
        }
    except Exception as e:
        logger.error(f"Error checking feature {feature_name} for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates (placeholder)
@router.get("/ws/status")
async def websocket_status_endpoint():
    """WebSocket endpoint for real-time status updates."""
    # This would be implemented as a WebSocket endpoint in a real application
    return {"message": "WebSocket endpoint not implemented in this example"}


# Export the router
__all__ = ["router"]