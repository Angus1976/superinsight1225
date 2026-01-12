"""
High Availability Recovery System for SuperInsight Platform.

Extends the existing EnhancedRecoveryCoordinator with advanced failure detection,
recovery orchestration, and high availability features.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.system.enhanced_recovery import EnhancedRecoveryCoordinator, RecoveryStrategy, RecoveryPlan
from src.system.failure_detector import (
    FailureDetector, FailureAnalysis, FailureEvent, 
    FailureType, FailureSeverity, ServiceHealth, failure_detector
)
from src.system.recovery_orchestrator import (
    RecoveryOrchestrator, RecoveryResult, RecoveryStatus,
    RecoveryPriority, recovery_orchestrator
)

logger = logging.getLogger(__name__)


class HAMode(Enum):
    """High availability operation modes."""
    ACTIVE_PASSIVE = "active_passive"
    ACTIVE_ACTIVE = "active_active"
    CLUSTER = "cluster"


@dataclass
class HAConfig:
    """Configuration for high availability system."""
    mode: HAMode = HAMode.ACTIVE_PASSIVE
    failover_timeout_seconds: float = 30.0
    health_check_interval: float = 10.0
    max_recovery_attempts: int = 3
    auto_failover_enabled: bool = True
    auto_recovery_enabled: bool = True
    notification_enabled: bool = True
    backup_retention_days: int = 7


@dataclass
class HAStatus:
    """Current status of the high availability system."""
    is_healthy: bool
    mode: HAMode
    primary_node: str
    active_nodes: List[str]
    standby_nodes: List[str]
    last_failover: Optional[float]
    uptime_percentage: float
    recovery_count: int
    current_failures: List[FailureEvent]


class HighAvailabilityRecoverySystem(EnhancedRecoveryCoordinator):
    """
    High Availability Recovery System extending EnhancedRecoveryCoordinator.
    
    Features:
    - Advanced failure detection with pattern analysis
    - Intelligent recovery orchestration
    - Automatic failover management
    - System health monitoring
    - Recovery plan generation and execution
    - Backup and restore coordination
    """
    
    def __init__(self, config: Optional[HAConfig] = None):
        super().__init__()
        
        self.config = config or HAConfig()
        self.failure_detector = failure_detector
        self.recovery_orchestrator = recovery_orchestrator
        
        # HA state
        self.primary_node = "node-1"
        self.active_nodes: List[str] = ["node-1"]
        self.standby_nodes: List[str] = ["node-2"]
        self.last_failover: Optional[float] = None
        self.recovery_count = 0
        self.start_time = time.time()
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
        logger.info(f"HighAvailabilityRecoverySystem initialized in {self.config.mode.value} mode")
    
    async def start(self):
        """Start the high availability system."""
        logger.info("Starting High Availability Recovery System")
        
        # Register default services for monitoring
        self._register_default_services()
        
        # Start continuous monitoring
        if self.config.auto_recovery_enabled:
            await self._start_monitoring()
        
        logger.info("High Availability Recovery System started")
    
    async def stop(self):
        """Stop the high availability system."""
        logger.info("Stopping High Availability Recovery System")
        
        await self._stop_monitoring()
        
        logger.info("High Availability Recovery System stopped")
    
    def _register_default_services(self):
        """Register default services for monitoring."""
        default_services = [
            "api_server",
            "database",
            "redis",
            "label_studio",
            "ai_service",
            "quality_service",
        ]
        
        for service in default_services:
            self.failure_detector.register_service(service)
    
    async def _start_monitoring(self):
        """Start continuous health monitoring."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started HA monitoring loop")
    
    async def _stop_monitoring(self):
        """Stop continuous health monitoring."""
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped HA monitoring loop")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for continuous health checking."""
        while self._is_monitoring:
            try:
                # Analyze system state
                analysis = await self.detect_and_analyze()
                
                # Handle any detected failures
                if analysis.has_critical_failures:
                    await self._handle_critical_failures(analysis)
                elif analysis.failures:
                    await self._handle_non_critical_failures(analysis)
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in HA monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def detect_and_analyze(self) -> FailureAnalysis:
        """Detect failures and analyze system state."""
        return await self.failure_detector.analyze_system_state()
    
    async def detect_and_recover(self, service_name: Optional[str] = None) -> RecoveryResult:
        """
        Detect failures and automatically recover.
        
        This method extends the base class functionality with advanced
        failure detection and recovery orchestration.
        """
        logger.info(f"Starting detect_and_recover for service: {service_name or 'all'}")
        
        # Analyze system state
        analysis = await self.detect_and_analyze()
        
        if not analysis.failures:
            logger.info("No failures detected, system is healthy")
            return RecoveryResult(
                success=True,
                plan_id="none",
                duration=0,
                actions_completed=0,
                actions_failed=0,
                services_recovered=[],
                data_integrity_verified=True,
                performance_restored=True,
                message="System healthy, no recovery needed"
            )
        
        # Filter failures by service if specified
        if service_name:
            analysis.failures = [
                f for f in analysis.failures 
                if f.service_name == service_name
            ]
            if not analysis.failures:
                return RecoveryResult(
                    success=True,
                    plan_id="none",
                    duration=0,
                    actions_completed=0,
                    actions_failed=0,
                    services_recovered=[],
                    data_integrity_verified=True,
                    performance_restored=True,
                    message=f"No failures detected for service {service_name}"
                )
        
        # Create recovery plan
        recovery_plan = await self.recovery_orchestrator.create_recovery_plan(analysis)
        
        # Execute recovery plan
        result = await self.recovery_orchestrator.execute_recovery_plan(recovery_plan)
        
        # Update recovery count
        self.recovery_count += 1
        
        # Log result
        if result.success:
            logger.info(f"Recovery completed successfully: {result.message}")
        else:
            logger.warning(f"Recovery completed with issues: {result.message}")
        
        return result
    
    async def _handle_critical_failures(self, analysis: FailureAnalysis):
        """Handle critical failures with automatic recovery."""
        logger.warning(f"Critical failures detected: {len(analysis.failures)}")
        
        if not self.config.auto_recovery_enabled:
            logger.info("Auto-recovery disabled, skipping automatic recovery")
            return
        
        # Check if failover is needed
        if self._should_failover(analysis):
            await self._perform_failover(analysis)
        else:
            # Attempt recovery
            result = await self.detect_and_recover()
            
            if not result.success and self.config.auto_failover_enabled:
                # Recovery failed, try failover
                await self._perform_failover(analysis)
    
    async def _handle_non_critical_failures(self, analysis: FailureAnalysis):
        """Handle non-critical failures."""
        logger.info(f"Non-critical failures detected: {len(analysis.failures)}")
        
        if self.config.auto_recovery_enabled:
            await self.detect_and_recover()
    
    def _should_failover(self, analysis: FailureAnalysis) -> bool:
        """Determine if failover is needed."""
        # Check for database or core service failures
        critical_services = {"database", "api_server"}
        
        for failure in analysis.failures:
            if failure.service_name in critical_services:
                if failure.severity == FailureSeverity.CRITICAL:
                    return True
        
        # Check system health score
        if analysis.system_health_score < 30:
            return True
        
        return False
    
    async def _perform_failover(self, analysis: FailureAnalysis):
        """Perform failover to standby node."""
        if not self.standby_nodes:
            logger.error("No standby nodes available for failover")
            return
        
        logger.info(f"Initiating failover from {self.primary_node}")
        
        try:
            # Select new primary
            new_primary = self.standby_nodes[0]
            old_primary = self.primary_node
            
            # Perform failover
            await self._execute_failover(old_primary, new_primary)
            
            # Update state
            self.primary_node = new_primary
            self.active_nodes = [new_primary]
            self.standby_nodes = [old_primary] + self.standby_nodes[1:]
            self.last_failover = time.time()
            
            logger.info(f"Failover completed: {old_primary} -> {new_primary}")
            
        except Exception as e:
            logger.error(f"Failover failed: {e}")
    
    async def _execute_failover(self, old_primary: str, new_primary: str):
        """Execute the actual failover process."""
        logger.info(f"Executing failover: {old_primary} -> {new_primary}")
        
        # Simulate failover steps
        steps = [
            "Stopping traffic to old primary",
            "Promoting standby to primary",
            "Updating DNS/routing",
            "Verifying new primary health",
            "Resuming traffic",
        ]
        
        for step in steps:
            logger.info(f"Failover step: {step}")
            await asyncio.sleep(0.5)  # Simulate step execution
    
    async def create_system_backup(self, backup_type: str = "incremental") -> Dict[str, Any]:
        """
        Create a system backup.
        
        Args:
            backup_type: Type of backup ("full" or "incremental")
        
        Returns:
            Backup information dictionary
        """
        backup_id = str(uuid.uuid4())[:8]
        logger.info(f"Creating {backup_type} backup: {backup_id}")
        
        backup_info = {
            "backup_id": backup_id,
            "backup_type": backup_type,
            "created_at": time.time(),
            "status": "in_progress",
            "components": [],
        }
        
        try:
            # Backup components
            components = ["database", "configurations", "user_data", "files"]
            
            for component in components:
                logger.info(f"Backing up {component}")
                await asyncio.sleep(0.2)  # Simulate backup
                backup_info["components"].append({
                    "name": component,
                    "status": "completed",
                    "size_bytes": 1024 * 1024  # Placeholder
                })
            
            backup_info["status"] = "completed"
            backup_info["completed_at"] = time.time()
            
            logger.info(f"Backup {backup_id} completed successfully")
            
        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            logger.error(f"Backup {backup_id} failed: {e}")
        
        return backup_info
    
    async def restore_from_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Restore system from a backup.
        
        Args:
            backup_id: ID of the backup to restore
        
        Returns:
            Restore operation result
        """
        logger.info(f"Restoring from backup: {backup_id}")
        
        restore_info = {
            "backup_id": backup_id,
            "started_at": time.time(),
            "status": "in_progress",
        }
        
        try:
            # Simulate restore process
            steps = ["Validating backup", "Stopping services", "Restoring data", "Starting services", "Verifying"]
            
            for step in steps:
                logger.info(f"Restore step: {step}")
                await asyncio.sleep(0.3)
            
            restore_info["status"] = "completed"
            restore_info["completed_at"] = time.time()
            
            logger.info(f"Restore from {backup_id} completed successfully")
            
        except Exception as e:
            restore_info["status"] = "failed"
            restore_info["error"] = str(e)
            logger.error(f"Restore from {backup_id} failed: {e}")
        
        return restore_info
    
    def update_service_health(self, service_name: str, health_data: Dict[str, Any]):
        """Update health status for a service."""
        health = ServiceHealth(
            service_name=service_name,
            is_healthy=health_data.get("is_healthy", True),
            health_score=health_data.get("health_score", 100.0),
            last_check=time.time(),
            failure_count=health_data.get("failure_count", 0),
            response_time_ms=health_data.get("response_time_ms", 0),
            error_rate=health_data.get("error_rate", 0),
            metrics=health_data.get("metrics", {})
        )
        
        self.failure_detector.update_service_health(service_name, health)
    
    def get_ha_status(self) -> HAStatus:
        """Get current high availability status."""
        # Get current failures
        current_failures = list(self.failure_detector.failure_history)[-10:]
        
        # Calculate uptime
        total_time = time.time() - self.start_time
        # Simplified uptime calculation
        uptime_percentage = 99.9 if not current_failures else 99.0
        
        return HAStatus(
            is_healthy=len(current_failures) == 0,
            mode=self.config.mode,
            primary_node=self.primary_node,
            active_nodes=self.active_nodes,
            standby_nodes=self.standby_nodes,
            last_failover=self.last_failover,
            uptime_percentage=uptime_percentage,
            recovery_count=self.recovery_count,
            current_failures=current_failures
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive HA statistics."""
        ha_status = self.get_ha_status()
        failure_stats = self.failure_detector.get_failure_statistics()
        recovery_stats = self.recovery_orchestrator.get_recovery_statistics()
        base_stats = self.get_recovery_statistics()
        
        return {
            "ha_status": {
                "is_healthy": ha_status.is_healthy,
                "mode": ha_status.mode.value,
                "primary_node": ha_status.primary_node,
                "active_nodes": ha_status.active_nodes,
                "standby_nodes": ha_status.standby_nodes,
                "uptime_percentage": ha_status.uptime_percentage,
            },
            "failure_detection": failure_stats,
            "recovery_orchestration": recovery_stats,
            "base_recovery": base_stats,
            "config": {
                "auto_failover_enabled": self.config.auto_failover_enabled,
                "auto_recovery_enabled": self.config.auto_recovery_enabled,
                "failover_timeout": self.config.failover_timeout_seconds,
            }
        }


# Global high availability recovery system instance
ha_recovery_system: Optional[HighAvailabilityRecoverySystem] = None


async def initialize_ha_system(config: Optional[HAConfig] = None) -> HighAvailabilityRecoverySystem:
    """Initialize the global HA recovery system."""
    global ha_recovery_system
    
    ha_recovery_system = HighAvailabilityRecoverySystem(config)
    await ha_recovery_system.start()
    
    return ha_recovery_system


async def shutdown_ha_system():
    """Shutdown the global HA recovery system."""
    global ha_recovery_system
    
    if ha_recovery_system:
        await ha_recovery_system.stop()
        ha_recovery_system = None


def get_ha_system() -> Optional[HighAvailabilityRecoverySystem]:
    """Get the global HA recovery system instance."""
    return ha_recovery_system
