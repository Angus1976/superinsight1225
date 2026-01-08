"""
Fault Detection and Recovery Integration for SuperInsight Platform.

Integrates all fault detection and recovery components into a unified system:
- Fault Detection System
- Recovery Orchestrator  
- Service Dependency Mapper
- Health Monitor
- Enhanced Recovery Coordinator
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from src.system.fault_detection_system import (
    fault_detection_system, FaultEvent, start_fault_detection, stop_fault_detection
)
from src.system.recovery_orchestrator import (
    recovery_orchestrator, start_recovery_orchestrator, stop_recovery_orchestrator,
    execute_fault_recovery
)
from src.system.service_dependency_mapper import (
    service_dependency_mapper, start_dependency_monitoring, stop_dependency_monitoring
)
from src.system.health_monitor import health_monitor, start_health_monitoring, stop_health_monitoring
from src.system.enhanced_recovery import recovery_coordinator, get_recovery_status
from src.system.fault_tolerance_system import fault_tolerance_system, start_fault_tolerance, stop_fault_tolerance
from src.system.notification import notification_system, NotificationPriority, NotificationChannel

logger = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    """Overall system status."""
    fault_detection_active: bool
    recovery_orchestrator_active: bool
    dependency_monitoring_active: bool
    health_monitoring_active: bool
    fault_tolerance_active: bool
    active_faults: int
    active_recoveries: int
    system_health: str
    last_update: datetime


class FaultRecoveryIntegration:
    """
    Integrated fault detection and recovery system.
    
    Coordinates all components to provide comprehensive fault management:
    - Automatic fault detection
    - Impact analysis using dependency mapping
    - Intelligent recovery orchestration
    - Health monitoring and alerting
    """
    
    def __init__(self):
        self.integration_active = False
        self.integration_task: Optional[asyncio.Task] = None
        self.fault_callbacks: List[Callable[[FaultEvent], None]] = []
        
        # Integration statistics
        self.total_faults_handled = 0
        self.total_recoveries_executed = 0
        self.integration_start_time: Optional[datetime] = None
        
        # Setup fault event handling
        self._setup_fault_handling()
    
    def _setup_fault_handling(self):
        """Setup fault event handling integration."""
        # Register callback with fault detection system
        fault_detection_system.add_fault_callback(self._handle_fault_event)
        
        logger.info("Fault handling integration configured")
    
    async def start_integration(self):
        """Start the integrated fault detection and recovery system."""
        if self.integration_active:
            logger.warning("Fault recovery integration is already active")
            return
        
        try:
            logger.info("Starting integrated fault detection and recovery system...")
            
            # Start all components
            await self._start_all_components()
            
            # Start integration coordination
            self.integration_active = True
            self.integration_start_time = datetime.utcnow()
            self.integration_task = asyncio.create_task(self._integration_loop())
            
            # Send startup notification
            notification_system.send_notification(
                title="Fault Recovery System Started",
                message="Integrated fault detection and recovery system is now active",
                priority=NotificationPriority.NORMAL,
                channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
            )
            
            logger.info("Integrated fault detection and recovery system started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start fault recovery integration: {e}")
            await self.stop_integration()
            raise
    
    async def stop_integration(self):
        """Stop the integrated fault detection and recovery system."""
        logger.info("Stopping integrated fault detection and recovery system...")
        
        self.integration_active = False
        
        # Stop integration task
        if self.integration_task:
            self.integration_task.cancel()
            try:
                await self.integration_task
            except asyncio.CancelledError:
                pass
        
        # Stop all components
        await self._stop_all_components()
        
        # Send shutdown notification
        notification_system.send_notification(
            title="Fault Recovery System Stopped",
            message="Integrated fault detection and recovery system has been stopped",
            priority=NotificationPriority.NORMAL,
            channels=[NotificationChannel.LOG]
        )
        
        logger.info("Integrated fault detection and recovery system stopped")
    
    async def _start_all_components(self):
        """Start all fault detection and recovery components."""
        try:
            # Start health monitoring first (foundation)
            start_health_monitoring()
            await asyncio.sleep(2)  # Allow health monitor to initialize
            
            # Start dependency monitoring
            await start_dependency_monitoring()
            await asyncio.sleep(1)
            
            # Start fault detection
            await start_fault_detection()
            await asyncio.sleep(1)
            
            # Start recovery orchestrator
            await start_recovery_orchestrator()
            await asyncio.sleep(1)
            
            # Start fault tolerance system
            await start_fault_tolerance()
            await asyncio.sleep(1)
            
            logger.info("All fault recovery components started")
            
        except Exception as e:
            logger.error(f"Error starting components: {e}")
            raise
    
    async def _stop_all_components(self):
        """Stop all fault detection and recovery components."""
        try:
            # Stop in reverse order
            await stop_fault_tolerance()
            await stop_recovery_orchestrator()
            await stop_fault_detection()
            await stop_dependency_monitoring()
            stop_health_monitoring()
            
            logger.info("All fault recovery components stopped")
            
        except Exception as e:
            logger.error(f"Error stopping components: {e}")
    
    async def _integration_loop(self):
        """Main integration coordination loop."""
        while self.integration_active:
            try:
                # Check component health
                await self._check_component_health()
                
                # Coordinate fault resolution
                await self._coordinate_fault_resolution()
                
                # Update integration statistics
                self._update_statistics()
                
                # Sleep before next cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in integration loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_component_health(self):
        """Check health of all integration components."""
        try:
            components_status = {
                "fault_detection": fault_detection_system.detection_active,
                "recovery_orchestrator": recovery_orchestrator.orchestrator_active,
                "dependency_monitoring": service_dependency_mapper.monitoring_active,
                "health_monitoring": health_monitor.monitoring_active,
                "fault_tolerance": fault_tolerance_system.system_active
            }
            
            # Check for failed components
            failed_components = [name for name, status in components_status.items() if not status]
            
            if failed_components:
                logger.warning(f"Failed components detected: {failed_components}")
                
                # Attempt to restart failed components
                for component in failed_components:
                    try:
                        await self._restart_component(component)
                    except Exception as e:
                        logger.error(f"Failed to restart component {component}: {e}")
            
        except Exception as e:
            logger.error(f"Error checking component health: {e}")
    
    async def _restart_component(self, component_name: str):
        """Restart a failed component."""
        logger.info(f"Restarting component: {component_name}")
        
        if component_name == "fault_detection":
            await start_fault_detection()
        elif component_name == "recovery_orchestrator":
            await start_recovery_orchestrator()
        elif component_name == "dependency_monitoring":
            await start_dependency_monitoring()
        elif component_name == "health_monitoring":
            start_health_monitoring()
        elif component_name == "fault_tolerance":
            await start_fault_tolerance()
        
        logger.info(f"Component {component_name} restarted")
    
    async def _coordinate_fault_resolution(self):
        """Coordinate fault resolution across components."""
        try:
            # Get active faults
            active_faults = fault_detection_system.get_active_faults()
            
            for fault_data in active_faults:
                fault_id = fault_data["fault_id"]
                service_name = fault_data["service_name"]
                
                # Check if recovery is already in progress
                recovery_stats = recovery_orchestrator.get_orchestrator_statistics()
                active_plans = recovery_stats.get("active_plans", 0)
                
                # Limit concurrent recoveries to prevent system overload
                if active_plans >= 3:
                    logger.debug("Maximum concurrent recoveries reached, waiting...")
                    continue
                
                # Analyze service impact using dependency mapper
                impact_analysis = await service_dependency_mapper._analyze_cascade_impact(service_name)
                
                # If high cascade probability, prioritize recovery
                if impact_analysis.cascade_probability > 0.7:
                    logger.warning(f"High cascade risk detected for {service_name}: {impact_analysis.cascade_probability:.2f}")
                    
                    # Send high priority notification
                    notification_system.send_notification(
                        title=f"High Cascade Risk - {service_name}",
                        message=f"Service {service_name} failure has {impact_analysis.cascade_probability:.1%} cascade probability affecting {len(impact_analysis.directly_affected)} services",
                        priority=NotificationPriority.CRITICAL,
                        channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.WEBHOOK]
                    )
            
        except Exception as e:
            logger.error(f"Error coordinating fault resolution: {e}")
    
    def _handle_fault_event(self, fault_event: FaultEvent):
        """Handle fault events from the detection system."""
        try:
            self.total_faults_handled += 1
            
            logger.info(f"Handling fault event: {fault_event.fault_id} - {fault_event.description}")
            
            # Create recovery task
            asyncio.create_task(self._execute_integrated_recovery(fault_event))
            
            # Notify callbacks
            for callback in self.fault_callbacks:
                try:
                    callback(fault_event)
                except Exception as e:
                    logger.error(f"Error in fault callback: {e}")
            
        except Exception as e:
            logger.error(f"Error handling fault event: {e}")
    
    async def _execute_integrated_recovery(self, fault_event: FaultEvent):
        """Execute integrated recovery for a fault event."""
        try:
            self.total_recoveries_executed += 1
            
            logger.info(f"Executing integrated recovery for fault {fault_event.fault_id}")
            
            # Step 1: Analyze impact using dependency mapper
            impact_analysis = await service_dependency_mapper._analyze_cascade_impact(fault_event.service_name)
            
            # Step 2: Execute recovery using orchestrator
            recovery_success = await execute_fault_recovery(fault_event)
            
            # Step 3: Monitor recovery progress
            await self._monitor_recovery_progress(fault_event, recovery_success)
            
            # Step 4: Verify system stability
            await self._verify_system_stability(fault_event.service_name)
            
            logger.info(f"Integrated recovery completed for fault {fault_event.fault_id}: {'success' if recovery_success else 'failed'}")
            
        except Exception as e:
            logger.error(f"Error executing integrated recovery: {e}")
    
    async def _monitor_recovery_progress(self, fault_event: FaultEvent, recovery_success: bool):
        """Monitor recovery progress and adjust if needed."""
        try:
            if not recovery_success:
                logger.warning(f"Recovery failed for fault {fault_event.fault_id}, attempting fallback")
                
                # Try enhanced recovery coordinator as fallback
                from src.system.enhanced_recovery import trigger_manual_recovery
                
                fallback_success = trigger_manual_recovery(
                    error_category="system",
                    service_name=fault_event.service_name
                )
                
                if fallback_success:
                    logger.info(f"Fallback recovery succeeded for fault {fault_event.fault_id}")
                else:
                    logger.error(f"All recovery attempts failed for fault {fault_event.fault_id}")
                    
                    # Send critical alert
                    notification_system.send_notification(
                        title=f"Recovery Failed - {fault_event.service_name}",
                        message=f"All recovery attempts failed for fault {fault_event.fault_id}. Manual intervention required.",
                        priority=NotificationPriority.CRITICAL,
                        channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.WEBHOOK]
                    )
            
        except Exception as e:
            logger.error(f"Error monitoring recovery progress: {e}")
    
    async def _verify_system_stability(self, service_name: str):
        """Verify system stability after recovery."""
        try:
            # Wait for system to stabilize
            await asyncio.sleep(30)
            
            # Check service health
            service_deps = service_dependency_mapper.get_service_dependencies(service_name)
            service_status = service_deps.get("status", "unknown")
            
            if service_status == "healthy":
                logger.info(f"System stability verified for {service_name}")
            else:
                logger.warning(f"System stability check failed for {service_name}: {service_status}")
                
                # Send stability warning
                notification_system.send_notification(
                    title=f"Stability Warning - {service_name}",
                    message=f"Service {service_name} recovery completed but stability check shows status: {service_status}",
                    priority=NotificationPriority.HIGH,
                    channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
                )
            
        except Exception as e:
            logger.error(f"Error verifying system stability: {e}")
    
    def _update_statistics(self):
        """Update integration statistics."""
        try:
            # This could be expanded to track more detailed metrics
            pass
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def add_fault_callback(self, callback: Callable[[FaultEvent], None]):
        """Add callback for fault events."""
        self.fault_callbacks.append(callback)
    
    def get_system_status(self) -> SystemStatus:
        """Get overall system status."""
        try:
            # Get component statuses
            fault_detection_active = fault_detection_system.detection_active
            recovery_orchestrator_active = recovery_orchestrator.orchestrator_active
            dependency_monitoring_active = service_dependency_mapper.monitoring_active
            health_monitoring_active = health_monitor.monitoring_active
            fault_tolerance_active = fault_tolerance_system.system_active
            
            # Get active counts
            active_faults = len(fault_detection_system.active_faults)
            active_recoveries = len(recovery_orchestrator.active_plans)
            
            # Determine overall system health
            if not fault_detection_active or not health_monitoring_active:
                system_health = "critical"
            elif active_faults > 5 or active_recoveries > 3:
                system_health = "degraded"
            elif active_faults > 0:
                system_health = "warning"
            else:
                system_health = "healthy"
            
            return SystemStatus(
                fault_detection_active=fault_detection_active,
                recovery_orchestrator_active=recovery_orchestrator_active,
                dependency_monitoring_active=dependency_monitoring_active,
                health_monitoring_active=health_monitoring_active,
                fault_tolerance_active=fault_tolerance_active,
                active_faults=active_faults,
                active_recoveries=active_recoveries,
                system_health=system_health,
                last_update=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return SystemStatus(
                fault_detection_active=False,
                recovery_orchestrator_active=False,
                dependency_monitoring_active=False,
                health_monitoring_active=False,
                fault_tolerance_active=False,
                active_faults=0,
                active_recoveries=0,
                system_health="unknown",
                last_update=datetime.utcnow()
            )
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get comprehensive integration statistics."""
        try:
            system_status = self.get_system_status()
            
            # Get component statistics
            fault_stats = fault_detection_system.get_fault_statistics()
            recovery_stats = recovery_orchestrator.get_orchestrator_statistics()
            dependency_stats = service_dependency_mapper.get_dependency_statistics()
            health_stats = health_monitor.get_metrics_summary()
            fault_tolerance_stats = fault_tolerance_system.get_system_statistics()
            
            # Calculate uptime
            uptime_seconds = 0
            if self.integration_start_time:
                uptime_seconds = (datetime.utcnow() - self.integration_start_time).total_seconds()
            
            return {
                "integration_active": self.integration_active,
                "uptime_seconds": uptime_seconds,
                "total_faults_handled": self.total_faults_handled,
                "total_recoveries_executed": self.total_recoveries_executed,
                "system_status": {
                    "fault_detection_active": system_status.fault_detection_active,
                    "recovery_orchestrator_active": system_status.recovery_orchestrator_active,
                    "dependency_monitoring_active": system_status.dependency_monitoring_active,
                    "health_monitoring_active": system_status.health_monitoring_active,
                    "fault_tolerance_active": system_status.fault_tolerance_active,
                    "active_faults": system_status.active_faults,
                    "active_recoveries": system_status.active_recoveries,
                    "system_health": system_status.system_health
                },
                "component_statistics": {
                    "fault_detection": fault_stats,
                    "recovery_orchestrator": recovery_stats,
                    "dependency_mapper": dependency_stats,
                    "health_monitor": health_stats,
                    "fault_tolerance": fault_tolerance_stats
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting integration statistics: {e}")
            return {}


# Global fault recovery integration instance
fault_recovery_integration = FaultRecoveryIntegration()


# Convenience functions
async def start_fault_recovery_system():
    """Start the integrated fault detection and recovery system."""
    await fault_recovery_integration.start_integration()


async def stop_fault_recovery_system():
    """Stop the integrated fault detection and recovery system."""
    await fault_recovery_integration.stop_integration()


def get_fault_recovery_status() -> Dict[str, Any]:
    """Get current fault recovery system status."""
    system_status = fault_recovery_integration.get_system_status()
    return {
        "integration_active": fault_recovery_integration.integration_active,
        "system_health": system_status.system_health,
        "active_faults": system_status.active_faults,
        "active_recoveries": system_status.active_recoveries,
        "all_components_active": all([
            system_status.fault_detection_active,
            system_status.recovery_orchestrator_active,
            system_status.dependency_monitoring_active,
            system_status.health_monitoring_active
        ])
    }


def register_fault_callback(callback: Callable[[FaultEvent], None]):
    """Register a callback for fault events."""
    fault_recovery_integration.add_fault_callback(callback)