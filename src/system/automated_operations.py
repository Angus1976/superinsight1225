"""
Automated Operations System for SuperInsight Platform.

Provides automated operational capabilities including:
- Automated fault handling and recovery
- Auto-scaling based on metrics and predictions
- Automated backup and recovery operations
- Automated optimization execution
- Self-healing system capabilities
"""

import asyncio
import logging
import time
import json
import subprocess
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import psutil
import shutil
import os

from src.system.intelligent_operations import IntelligentOperationsSystem, OperationalRecommendation, RecommendationType
from src.system.fault_detection_system import FaultDetectionSystem, FaultEvent, FaultType, FaultSeverity
from src.system.monitoring import MetricsCollector, PerformanceMonitor
from src.system.backup_recovery_system import BackupRecoverySystem
from src.system.notification import notification_system, NotificationPriority, NotificationChannel

logger = logging.getLogger(__name__)


class AutomationLevel(Enum):
    """Levels of automation for operations."""
    MANUAL = "manual"              # No automation, manual approval required
    SEMI_AUTOMATIC = "semi_auto"   # Automated with confirmation
    AUTOMATIC = "automatic"        # Fully automated
    EMERGENCY_ONLY = "emergency"   # Only in emergency situations


class OperationType(Enum):
    """Types of automated operations."""
    SCALING = "scaling"
    RECOVERY = "recovery"
    OPTIMIZATION = "optimization"
    BACKUP = "backup"
    MAINTENANCE = "maintenance"
    SECURITY = "security"


@dataclass
class AutomationRule:
    """Rule for automated operations."""
    rule_id: str
    operation_type: OperationType
    automation_level: AutomationLevel
    trigger_conditions: Dict[str, Any]
    action_parameters: Dict[str, Any]
    cooldown_seconds: int = 300
    max_executions_per_hour: int = 5
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None
    execution_count: int = 0


@dataclass
class AutomationExecution:
    """Record of an automated operation execution."""
    execution_id: str
    rule_id: str
    operation_type: OperationType
    action_taken: str
    trigger_reason: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    result: Optional[str] = None
    error_message: Optional[str] = None
    metrics_before: Dict[str, float] = field(default_factory=dict)
    metrics_after: Dict[str, float] = field(default_factory=dict)


class AutoScaler:
    """
    Automated scaling system based on metrics and predictions.
    
    Handles both horizontal and vertical scaling decisions.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.scaling_history: deque = deque(maxlen=100)
        self.scaling_rules: Dict[str, Dict[str, Any]] = {}
        self.cooldown_periods: Dict[str, datetime] = {}
        
        # Default scaling thresholds
        self.default_thresholds = {
            'cpu_scale_up': 80.0,
            'cpu_scale_down': 30.0,
            'memory_scale_up': 85.0,
            'memory_scale_down': 40.0,
            'response_time_scale_up': 2.0,
            'error_rate_scale_up': 5.0
        }
        
        # Scaling configuration
        self.min_instances = 1
        self.max_instances = 10
        self.scale_up_cooldown = 300  # 5 minutes
        self.scale_down_cooldown = 600  # 10 minutes
        
    def add_scaling_rule(self, service_name: str, rule_config: Dict[str, Any]):
        """Add a scaling rule for a service."""
        self.scaling_rules[service_name] = rule_config
        logger.info(f"Added scaling rule for {service_name}")
    
    async def evaluate_scaling_decision(self, service_name: str, current_metrics: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Evaluate if scaling is needed for a service."""
        try:
            # Check cooldown period
            if service_name in self.cooldown_periods:
                if datetime.utcnow() < self.cooldown_periods[service_name]:
                    return None
            
            # Get service-specific rules or use defaults
            rules = self.scaling_rules.get(service_name, self.default_thresholds)
            
            cpu_usage = current_metrics.get('system.cpu.usage_percent', 0)
            memory_usage = current_metrics.get('system.memory.usage_percent', 0)
            response_time = current_metrics.get('requests.duration', 0)
            error_rate = current_metrics.get('error_rate_percent', 0)
            
            # Scale up conditions
            scale_up_reasons = []
            if cpu_usage > rules.get('cpu_scale_up', 80):
                scale_up_reasons.append(f"CPU usage {cpu_usage:.1f}% > {rules['cpu_scale_up']}%")
            
            if memory_usage > rules.get('memory_scale_up', 85):
                scale_up_reasons.append(f"Memory usage {memory_usage:.1f}% > {rules['memory_scale_up']}%")
            
            if response_time > rules.get('response_time_scale_up', 2.0):
                scale_up_reasons.append(f"Response time {response_time:.2f}s > {rules['response_time_scale_up']}s")
            
            if error_rate > rules.get('error_rate_scale_up', 5.0):
                scale_up_reasons.append(f"Error rate {error_rate:.1f}% > {rules['error_rate_scale_up']}%")
            
            if scale_up_reasons:
                return {
                    'action': 'scale_up',
                    'service': service_name,
                    'reasons': scale_up_reasons,
                    'recommended_instances': min(self.max_instances, self._get_current_instances(service_name) + 1),
                    'cooldown': self.scale_up_cooldown
                }
            
            # Scale down conditions (only if no scale up needed)
            scale_down_reasons = []
            if (cpu_usage < rules.get('cpu_scale_down', 30) and 
                memory_usage < rules.get('memory_scale_down', 40) and
                response_time < 1.0 and error_rate < 1.0):
                
                current_instances = self._get_current_instances(service_name)
                if current_instances > self.min_instances:
                    scale_down_reasons.append(f"Low resource usage: CPU {cpu_usage:.1f}%, Memory {memory_usage:.1f}%")
                    
                    return {
                        'action': 'scale_down',
                        'service': service_name,
                        'reasons': scale_down_reasons,
                        'recommended_instances': max(self.min_instances, current_instances - 1),
                        'cooldown': self.scale_down_cooldown
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating scaling decision for {service_name}: {e}")
            return None
    
    async def execute_scaling_action(self, scaling_decision: Dict[str, Any]) -> bool:
        """Execute a scaling action."""
        try:
            service_name = scaling_decision['service']
            action = scaling_decision['action']
            target_instances = scaling_decision['recommended_instances']
            
            logger.info(f"Executing {action} for {service_name} to {target_instances} instances")
            
            # Record scaling action
            scaling_record = {
                'timestamp': datetime.utcnow(),
                'service': service_name,
                'action': action,
                'target_instances': target_instances,
                'reasons': scaling_decision['reasons']
            }
            
            # Simulate scaling action (in real implementation, this would call container orchestrator)
            success = await self._simulate_scaling(service_name, action, target_instances)
            
            scaling_record['success'] = success
            self.scaling_history.append(scaling_record)
            
            # Set cooldown period
            cooldown_duration = timedelta(seconds=scaling_decision['cooldown'])
            self.cooldown_periods[service_name] = datetime.utcnow() + cooldown_duration
            
            if success:
                logger.info(f"Successfully executed {action} for {service_name}")
            else:
                logger.error(f"Failed to execute {action} for {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing scaling action: {e}")
            return False
    
    async def _simulate_scaling(self, service_name: str, action: str, target_instances: int) -> bool:
        """Simulate scaling action (placeholder for real implementation)."""
        try:
            # In a real implementation, this would:
            # - Call Kubernetes API to scale deployments
            # - Update Docker Compose services
            # - Call cloud provider APIs (AWS ECS, Azure Container Instances, etc.)
            
            await asyncio.sleep(1)  # Simulate API call delay
            
            # Simulate 95% success rate
            import random
            return random.random() > 0.05
            
        except Exception as e:
            logger.error(f"Error in scaling simulation: {e}")
            return False
    
    def _get_current_instances(self, service_name: str) -> int:
        """Get current number of instances for a service."""
        # In real implementation, this would query the orchestrator
        # For simulation, return a default value
        return 2
    
    def get_scaling_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent scaling history."""
        return list(self.scaling_history)[-limit:]


class AutomatedRecoverySystem:
    """
    Automated recovery system for handling faults and failures.
    
    Implements self-healing capabilities and automated remediation.
    """
    
    def __init__(self, fault_detector: FaultDetectionSystem, backup_system: BackupRecoverySystem):
        self.fault_detector = fault_detector
        self.backup_system = backup_system
        self.recovery_handlers: Dict[FaultType, Callable] = {}
        self.recovery_history: deque = deque(maxlen=100)
        self.recovery_rules: Dict[str, Dict[str, Any]] = {}
        
        # Setup default recovery handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default recovery handlers for different fault types."""
        self.recovery_handlers[FaultType.SERVICE_UNAVAILABLE] = self._handle_service_unavailable
        self.recovery_handlers[FaultType.PERFORMANCE_DEGRADATION] = self._handle_performance_degradation
        self.recovery_handlers[FaultType.RESOURCE_EXHAUSTION] = self._handle_resource_exhaustion
        self.recovery_handlers[FaultType.CASCADE_FAILURE] = self._handle_cascade_failure
        self.recovery_handlers[FaultType.CONFIGURATION_ERROR] = self._handle_configuration_error
        
        logger.info("Default recovery handlers configured")
    
    async def handle_fault_automatically(self, fault_event: FaultEvent) -> bool:
        """Handle a fault event automatically."""
        try:
            handler = self.recovery_handlers.get(fault_event.fault_type)
            
            if not handler:
                logger.warning(f"No handler for fault type: {fault_event.fault_type}")
                return False
            
            # Check if automatic recovery is allowed for this fault
            if not self._is_automatic_recovery_allowed(fault_event):
                logger.info(f"Automatic recovery not allowed for fault {fault_event.fault_id}")
                return False
            
            logger.info(f"Starting automatic recovery for fault {fault_event.fault_id}")
            
            # Record recovery attempt
            recovery_record = {
                'fault_id': fault_event.fault_id,
                'fault_type': fault_event.fault_type.value,
                'service_name': fault_event.service_name,
                'started_at': datetime.utcnow(),
                'actions_taken': []
            }
            
            # Execute recovery
            success = await handler(fault_event, recovery_record)
            
            recovery_record['completed_at'] = datetime.utcnow()
            recovery_record['success'] = success
            
            self.recovery_history.append(recovery_record)
            
            if success:
                logger.info(f"Automatic recovery successful for fault {fault_event.fault_id}")
            else:
                logger.error(f"Automatic recovery failed for fault {fault_event.fault_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in automatic fault handling: {e}")
            return False
    
    def _is_automatic_recovery_allowed(self, fault_event: FaultEvent) -> bool:
        """Check if automatic recovery is allowed for this fault."""
        # Don't auto-recover critical faults without human oversight
        if fault_event.severity == FaultSeverity.CRITICAL:
            return False
        
        # Check if service has specific recovery rules
        service_rules = self.recovery_rules.get(fault_event.service_name, {})
        if not service_rules.get('auto_recovery_enabled', True):
            return False
        
        # Check recovery attempt limits
        recent_recoveries = [r for r in self.recovery_history 
                           if r['service_name'] == fault_event.service_name and
                           (datetime.utcnow() - r['started_at']).total_seconds() < 3600]  # Last hour
        
        max_recoveries_per_hour = service_rules.get('max_recoveries_per_hour', 3)
        if len(recent_recoveries) >= max_recoveries_per_hour:
            logger.warning(f"Recovery limit exceeded for {fault_event.service_name}")
            return False
        
        return True
    
    async def _handle_service_unavailable(self, fault_event: FaultEvent, recovery_record: Dict[str, Any]) -> bool:
        """Handle service unavailable fault."""
        try:
            service_name = fault_event.service_name
            actions_taken = []
            
            # Step 1: Try to restart the service
            restart_success = await self._restart_service(service_name)
            actions_taken.append(f"restart_service: {'success' if restart_success else 'failed'}")
            
            if restart_success:
                # Wait for service to stabilize
                await asyncio.sleep(30)
                
                # Check if service is now healthy
                if await self._check_service_health(service_name):
                    recovery_record['actions_taken'] = actions_taken
                    return True
            
            # Step 2: Check and restart dependencies
            deps_restarted = await self._restart_dependencies(service_name)
            actions_taken.append(f"restart_dependencies: {'success' if deps_restarted else 'failed'}")
            
            if deps_restarted:
                await asyncio.sleep(30)
                if await self._check_service_health(service_name):
                    recovery_record['actions_taken'] = actions_taken
                    return True
            
            # Step 3: Enable circuit breaker to prevent cascade failures
            circuit_breaker_enabled = await self._enable_circuit_breaker(service_name)
            actions_taken.append(f"enable_circuit_breaker: {'success' if circuit_breaker_enabled else 'failed'}")
            
            recovery_record['actions_taken'] = actions_taken
            return False  # Service still unavailable, manual intervention needed
            
        except Exception as e:
            logger.error(f"Error handling service unavailable fault: {e}")
            return False
    
    async def _handle_performance_degradation(self, fault_event: FaultEvent, recovery_record: Dict[str, Any]) -> bool:
        """Handle performance degradation fault."""
        try:
            service_name = fault_event.service_name
            actions_taken = []
            
            # Step 1: Clear caches
            cache_cleared = await self._clear_caches(service_name)
            actions_taken.append(f"clear_caches: {'success' if cache_cleared else 'failed'}")
            
            # Step 2: Optimize database connections
            db_optimized = await self._optimize_database_connections(service_name)
            actions_taken.append(f"optimize_database: {'success' if db_optimized else 'failed'}")
            
            # Step 3: Scale up if needed
            scaled_up = await self._scale_up_service(service_name)
            actions_taken.append(f"scale_up: {'success' if scaled_up else 'failed'}")
            
            recovery_record['actions_taken'] = actions_taken
            return cache_cleared or db_optimized or scaled_up
            
        except Exception as e:
            logger.error(f"Error handling performance degradation fault: {e}")
            return False
    
    async def _handle_resource_exhaustion(self, fault_event: FaultEvent, recovery_record: Dict[str, Any]) -> bool:
        """Handle resource exhaustion fault."""
        try:
            actions_taken = []
            
            # Step 1: Clean up temporary files
            cleanup_success = await self._cleanup_temporary_files()
            actions_taken.append(f"cleanup_temp_files: {'success' if cleanup_success else 'failed'}")
            
            # Step 2: Restart memory-intensive services
            restart_success = await self._restart_memory_intensive_services()
            actions_taken.append(f"restart_memory_services: {'success' if restart_success else 'failed'}")
            
            # Step 3: Scale up resources
            scale_success = await self._scale_up_resources()
            actions_taken.append(f"scale_up_resources: {'success' if scale_success else 'failed'}")
            
            recovery_record['actions_taken'] = actions_taken
            return cleanup_success or restart_success or scale_success
            
        except Exception as e:
            logger.error(f"Error handling resource exhaustion fault: {e}")
            return False
    
    async def _handle_cascade_failure(self, fault_event: FaultEvent, recovery_record: Dict[str, Any]) -> bool:
        """Handle cascade failure fault."""
        try:
            actions_taken = []
            
            # Step 1: Enable circuit breakers for all affected services
            circuit_breakers_enabled = True
            for service in fault_event.affected_services:
                success = await self._enable_circuit_breaker(service)
                circuit_breakers_enabled = circuit_breakers_enabled and success
            
            actions_taken.append(f"enable_circuit_breakers: {'success' if circuit_breakers_enabled else 'failed'}")
            
            # Step 2: Isolate failed services
            isolation_success = await self._isolate_failed_services(fault_event.affected_services)
            actions_taken.append(f"isolate_services: {'success' if isolation_success else 'failed'}")
            
            # Step 3: Activate fallback services
            fallback_success = await self._activate_fallback_services(fault_event.affected_services)
            actions_taken.append(f"activate_fallbacks: {'success' if fallback_success else 'failed'}")
            
            recovery_record['actions_taken'] = actions_taken
            return circuit_breakers_enabled and isolation_success
            
        except Exception as e:
            logger.error(f"Error handling cascade failure fault: {e}")
            return False
    
    async def _handle_configuration_error(self, fault_event: FaultEvent, recovery_record: Dict[str, Any]) -> bool:
        """Handle configuration error fault."""
        try:
            service_name = fault_event.service_name
            actions_taken = []
            
            # Step 1: Validate current configuration
            config_valid = await self._validate_configuration(service_name)
            actions_taken.append(f"validate_config: {'valid' if config_valid else 'invalid'}")
            
            if not config_valid:
                # Step 2: Restore backup configuration
                backup_restored = await self._restore_backup_configuration(service_name)
                actions_taken.append(f"restore_backup_config: {'success' if backup_restored else 'failed'}")
                
                if backup_restored:
                    # Step 3: Restart service with restored config
                    restart_success = await self._restart_service(service_name)
                    actions_taken.append(f"restart_service: {'success' if restart_success else 'failed'}")
                    
                    recovery_record['actions_taken'] = actions_taken
                    return restart_success
            
            recovery_record['actions_taken'] = actions_taken
            return config_valid
            
        except Exception as e:
            logger.error(f"Error handling configuration error fault: {e}")
            return False
    
    # Helper methods for recovery actions
    async def _restart_service(self, service_name: str) -> bool:
        """Restart a service."""
        try:
            logger.info(f"Restarting service: {service_name}")
            # In real implementation, this would call the service manager
            await asyncio.sleep(2)  # Simulate restart time
            return True
        except Exception as e:
            logger.error(f"Error restarting service {service_name}: {e}")
            return False
    
    async def _check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        try:
            # In real implementation, this would check service health endpoints
            await asyncio.sleep(1)
            return True  # Simulate healthy service
        except Exception as e:
            logger.error(f"Error checking health of service {service_name}: {e}")
            return False
    
    async def _restart_dependencies(self, service_name: str) -> bool:
        """Restart service dependencies."""
        try:
            logger.info(f"Restarting dependencies for service: {service_name}")
            await asyncio.sleep(3)  # Simulate dependency restart
            return True
        except Exception as e:
            logger.error(f"Error restarting dependencies for {service_name}: {e}")
            return False
    
    async def _enable_circuit_breaker(self, service_name: str) -> bool:
        """Enable circuit breaker for a service."""
        try:
            logger.info(f"Enabling circuit breaker for service: {service_name}")
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error enabling circuit breaker for {service_name}: {e}")
            return False
    
    async def _clear_caches(self, service_name: str) -> bool:
        """Clear caches for a service."""
        try:
            logger.info(f"Clearing caches for service: {service_name}")
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error clearing caches for {service_name}: {e}")
            return False
    
    async def _optimize_database_connections(self, service_name: str) -> bool:
        """Optimize database connections for a service."""
        try:
            logger.info(f"Optimizing database connections for service: {service_name}")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error optimizing database for {service_name}: {e}")
            return False
    
    async def _scale_up_service(self, service_name: str) -> bool:
        """Scale up a service."""
        try:
            logger.info(f"Scaling up service: {service_name}")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error scaling up service {service_name}: {e}")
            return False
    
    async def _cleanup_temporary_files(self) -> bool:
        """Clean up temporary files."""
        try:
            logger.info("Cleaning up temporary files")
            # In real implementation, this would clean /tmp, logs, etc.
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")
            return False
    
    async def _restart_memory_intensive_services(self) -> bool:
        """Restart memory-intensive services."""
        try:
            logger.info("Restarting memory-intensive services")
            await asyncio.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Error restarting memory-intensive services: {e}")
            return False
    
    async def _scale_up_resources(self) -> bool:
        """Scale up system resources."""
        try:
            logger.info("Scaling up system resources")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error scaling up resources: {e}")
            return False
    
    async def _isolate_failed_services(self, services: List[str]) -> bool:
        """Isolate failed services."""
        try:
            logger.info(f"Isolating failed services: {services}")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error isolating services: {e}")
            return False
    
    async def _activate_fallback_services(self, services: List[str]) -> bool:
        """Activate fallback services."""
        try:
            logger.info(f"Activating fallback services for: {services}")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error activating fallback services: {e}")
            return False
    
    async def _validate_configuration(self, service_name: str) -> bool:
        """Validate service configuration."""
        try:
            logger.info(f"Validating configuration for service: {service_name}")
            await asyncio.sleep(1)
            return True  # Simulate valid config
        except Exception as e:
            logger.error(f"Error validating configuration for {service_name}: {e}")
            return False
    
    async def _restore_backup_configuration(self, service_name: str) -> bool:
        """Restore backup configuration for a service."""
        try:
            logger.info(f"Restoring backup configuration for service: {service_name}")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error restoring backup configuration for {service_name}: {e}")
            return False
    
    def get_recovery_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent recovery history."""
        return list(self.recovery_history)[-limit:]


class AutomatedBackupSystem:
    """
    Automated backup and recovery system.
    
    Handles scheduled backups and automated recovery operations.
    """
    
    def __init__(self, backup_system: BackupRecoverySystem):
        self.backup_system = backup_system
        self.backup_schedule: Dict[str, Dict[str, Any]] = {}
        self.backup_history: deque = deque(maxlen=100)
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
    async def start_scheduler(self):
        """Start the backup scheduler."""
        if self.is_running:
            logger.warning("Backup scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Automated backup scheduler started")
    
    async def stop_scheduler(self):
        """Stop the backup scheduler."""
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Automated backup scheduler stopped")
    
    def schedule_backup(self, backup_name: str, interval_hours: int, backup_type: str = "incremental"):
        """Schedule a recurring backup."""
        self.backup_schedule[backup_name] = {
            'interval_hours': interval_hours,
            'backup_type': backup_type,
            'last_backup': None,
            'next_backup': datetime.utcnow()
        }
        logger.info(f"Scheduled backup '{backup_name}' every {interval_hours} hours")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                for backup_name, schedule in self.backup_schedule.items():
                    if current_time >= schedule['next_backup']:
                        await self._execute_scheduled_backup(backup_name, schedule)
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in backup scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _execute_scheduled_backup(self, backup_name: str, schedule: Dict[str, Any]):
        """Execute a scheduled backup."""
        try:
            logger.info(f"Executing scheduled backup: {backup_name}")
            
            backup_record = {
                'backup_name': backup_name,
                'backup_type': schedule['backup_type'],
                'started_at': datetime.utcnow(),
                'success': False
            }
            
            # Execute backup
            success = await self._perform_backup(backup_name, schedule['backup_type'])
            
            backup_record['completed_at'] = datetime.utcnow()
            backup_record['success'] = success
            
            # Update schedule
            schedule['last_backup'] = datetime.utcnow()
            schedule['next_backup'] = datetime.utcnow() + timedelta(hours=schedule['interval_hours'])
            
            self.backup_history.append(backup_record)
            
            if success:
                logger.info(f"Scheduled backup '{backup_name}' completed successfully")
            else:
                logger.error(f"Scheduled backup '{backup_name}' failed")
            
        except Exception as e:
            logger.error(f"Error executing scheduled backup {backup_name}: {e}")
    
    async def _perform_backup(self, backup_name: str, backup_type: str) -> bool:
        """Perform the actual backup operation."""
        try:
            # In real implementation, this would call the backup system
            await asyncio.sleep(5)  # Simulate backup time
            return True  # Simulate successful backup
        except Exception as e:
            logger.error(f"Error performing backup {backup_name}: {e}")
            return False
    
    async def trigger_emergency_backup(self, reason: str) -> bool:
        """Trigger an emergency backup."""
        try:
            logger.info(f"Triggering emergency backup: {reason}")
            
            backup_record = {
                'backup_name': f"emergency_{int(time.time())}",
                'backup_type': 'full',
                'reason': reason,
                'started_at': datetime.utcnow(),
                'emergency': True
            }
            
            success = await self._perform_backup(backup_record['backup_name'], 'full')
            
            backup_record['completed_at'] = datetime.utcnow()
            backup_record['success'] = success
            
            self.backup_history.append(backup_record)
            
            return success
            
        except Exception as e:
            logger.error(f"Error triggering emergency backup: {e}")
            return False
    
    def get_backup_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent backup history."""
        return list(self.backup_history)[-limit:]


class AutomatedOperationsSystem:
    """
    Main automated operations system coordinating all automated capabilities.
    
    Integrates auto-scaling, recovery, backup, and optimization automation.
    """
    
    def __init__(self, intelligent_ops: IntelligentOperationsSystem,
                 metrics_collector: MetricsCollector,
                 fault_detector: FaultDetectionSystem,
                 backup_system: BackupRecoverySystem):
        self.intelligent_ops = intelligent_ops
        self.metrics_collector = metrics_collector
        self.fault_detector = fault_detector
        self.backup_system = backup_system
        
        # Automation components
        self.auto_scaler = AutoScaler(metrics_collector)
        self.recovery_system = AutomatedRecoverySystem(fault_detector, backup_system)
        self.backup_automation = AutomatedBackupSystem(backup_system)
        
        # Automation rules and state
        self.automation_rules: Dict[str, AutomationRule] = {}
        self.execution_history: deque = deque(maxlen=500)
        self.is_running = False
        self.automation_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.automation_interval = 60  # 1 minute
        self.max_concurrent_operations = 3
        self.active_operations: Set[str] = set()
        
        # Setup fault handler
        self.fault_detector.add_fault_callback(self._handle_fault_event)
        
        # Setup default automation rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default automation rules."""
        # Auto-scaling rule
        self.add_automation_rule(AutomationRule(
            rule_id="auto_scale_cpu",
            operation_type=OperationType.SCALING,
            automation_level=AutomationLevel.AUTOMATIC,
            trigger_conditions={"cpu_usage_threshold": 80.0},
            action_parameters={"scale_type": "cpu_based"},
            cooldown_seconds=300,
            max_executions_per_hour=10
        ))
        
        # Auto-recovery rule
        self.add_automation_rule(AutomationRule(
            rule_id="auto_recover_service",
            operation_type=OperationType.RECOVERY,
            automation_level=AutomationLevel.SEMI_AUTOMATIC,
            trigger_conditions={"fault_severity": ["medium", "high"]},
            action_parameters={"recovery_type": "service_restart"},
            cooldown_seconds=600,
            max_executions_per_hour=5
        ))
        
        # Auto-backup rule
        self.add_automation_rule(AutomationRule(
            rule_id="scheduled_backup",
            operation_type=OperationType.BACKUP,
            automation_level=AutomationLevel.AUTOMATIC,
            trigger_conditions={"schedule": "daily"},
            action_parameters={"backup_type": "incremental"},
            cooldown_seconds=86400,  # 24 hours
            max_executions_per_hour=1
        ))
        
        logger.info("Default automation rules configured")
    
    def add_automation_rule(self, rule: AutomationRule):
        """Add an automation rule."""
        self.automation_rules[rule.rule_id] = rule
        logger.info(f"Added automation rule: {rule.rule_id}")
    
    async def start(self):
        """Start the automated operations system."""
        if self.is_running:
            logger.warning("Automated operations system is already running")
            return
        
        self.is_running = True
        self.automation_task = asyncio.create_task(self._automation_loop())
        
        # Start backup scheduler
        await self.backup_automation.start_scheduler()
        
        logger.info("Automated operations system started")
    
    async def stop(self):
        """Stop the automated operations system."""
        self.is_running = False
        
        if self.automation_task:
            self.automation_task.cancel()
            try:
                await self.automation_task
            except asyncio.CancelledError:
                pass
        
        # Stop backup scheduler
        await self.backup_automation.stop_scheduler()
        
        logger.info("Automated operations system stopped")
    
    async def _automation_loop(self):
        """Main automation loop."""
        while self.is_running:
            try:
                # Limit concurrent operations
                if len(self.active_operations) >= self.max_concurrent_operations:
                    await asyncio.sleep(self.automation_interval)
                    continue
                
                # Get current system state
                current_metrics = self.metrics_collector.get_all_metrics_summary()
                recommendations = self.intelligent_ops.recommendations
                
                # Evaluate automation rules
                await self._evaluate_automation_rules(current_metrics, recommendations)
                
                # Sleep until next evaluation
                await asyncio.sleep(self.automation_interval)
                
            except Exception as e:
                logger.error(f"Error in automation loop: {e}")
                await asyncio.sleep(self.automation_interval)
    
    async def _evaluate_automation_rules(self, current_metrics: Dict[str, Dict[str, Any]], 
                                       recommendations: List[OperationalRecommendation]):
        """Evaluate automation rules and execute actions."""
        try:
            flat_metrics = self._flatten_metrics(current_metrics)
            
            for rule_id, rule in self.automation_rules.items():
                if not rule.enabled:
                    continue
                
                # Check if rule should be triggered
                if await self._should_trigger_rule(rule, flat_metrics, recommendations):
                    await self._execute_automation_rule(rule, flat_metrics)
            
        except Exception as e:
            logger.error(f"Error evaluating automation rules: {e}")
    
    async def _should_trigger_rule(self, rule: AutomationRule, metrics: Dict[str, float],
                                 recommendations: List[OperationalRecommendation]) -> bool:
        """Check if an automation rule should be triggered."""
        try:
            # Check cooldown
            if rule.last_executed:
                cooldown_elapsed = (datetime.utcnow() - rule.last_executed).total_seconds()
                if cooldown_elapsed < rule.cooldown_seconds:
                    return False
            
            # Check execution limits
            recent_executions = [e for e in self.execution_history 
                               if e.rule_id == rule.rule_id and
                               (datetime.utcnow() - e.started_at).total_seconds() < 3600]
            
            if len(recent_executions) >= rule.max_executions_per_hour:
                return False
            
            # Check trigger conditions based on operation type
            if rule.operation_type == OperationType.SCALING:
                return await self._check_scaling_triggers(rule, metrics)
            
            elif rule.operation_type == OperationType.BACKUP:
                return await self._check_backup_triggers(rule)
            
            elif rule.operation_type == OperationType.OPTIMIZATION:
                return await self._check_optimization_triggers(rule, recommendations)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rule triggers: {e}")
            return False
    
    async def _check_scaling_triggers(self, rule: AutomationRule, metrics: Dict[str, float]) -> bool:
        """Check scaling triggers."""
        try:
            cpu_threshold = rule.trigger_conditions.get('cpu_usage_threshold', 80.0)
            cpu_usage = metrics.get('system.cpu.usage_percent', 0)
            
            return cpu_usage > cpu_threshold
            
        except Exception as e:
            logger.error(f"Error checking scaling triggers: {e}")
            return False
    
    async def _check_backup_triggers(self, rule: AutomationRule) -> bool:
        """Check backup triggers."""
        try:
            schedule = rule.trigger_conditions.get('schedule', 'daily')
            
            if schedule == 'daily':
                # Check if 24 hours have passed since last execution
                if rule.last_executed:
                    hours_elapsed = (datetime.utcnow() - rule.last_executed).total_seconds() / 3600
                    return hours_elapsed >= 24
                else:
                    return True  # First execution
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking backup triggers: {e}")
            return False
    
    async def _check_optimization_triggers(self, rule: AutomationRule, 
                                         recommendations: List[OperationalRecommendation]) -> bool:
        """Check optimization triggers."""
        try:
            # Check if there are high-priority optimization recommendations
            high_priority_optimizations = [r for r in recommendations 
                                         if r.recommendation_type == RecommendationType.OPTIMIZE_PERFORMANCE and
                                         r.priority in ['high', 'critical']]
            
            return len(high_priority_optimizations) > 0
            
        except Exception as e:
            logger.error(f"Error checking optimization triggers: {e}")
            return False
    
    async def _execute_automation_rule(self, rule: AutomationRule, metrics: Dict[str, float]):
        """Execute an automation rule."""
        try:
            execution_id = f"exec_{rule.rule_id}_{int(time.time())}"
            
            # Check if manual approval is needed
            if rule.automation_level == AutomationLevel.SEMI_AUTOMATIC:
                # In real implementation, this would send notification and wait for approval
                logger.info(f"Semi-automatic rule {rule.rule_id} requires approval")
                return
            
            if rule.automation_level == AutomationLevel.MANUAL:
                logger.info(f"Manual rule {rule.rule_id} skipped (requires manual execution)")
                return
            
            # Add to active operations
            self.active_operations.add(execution_id)
            
            execution = AutomationExecution(
                execution_id=execution_id,
                rule_id=rule.rule_id,
                operation_type=rule.operation_type,
                action_taken="",
                trigger_reason="",
                started_at=datetime.utcnow(),
                metrics_before=metrics.copy()
            )
            
            try:
                # Execute based on operation type
                if rule.operation_type == OperationType.SCALING:
                    success = await self._execute_scaling_operation(rule, execution)
                
                elif rule.operation_type == OperationType.BACKUP:
                    success = await self._execute_backup_operation(rule, execution)
                
                elif rule.operation_type == OperationType.OPTIMIZATION:
                    success = await self._execute_optimization_operation(rule, execution)
                
                else:
                    success = False
                    execution.error_message = f"Unknown operation type: {rule.operation_type}"
                
                execution.success = success
                execution.completed_at = datetime.utcnow()
                
                # Update rule execution tracking
                rule.last_executed = datetime.utcnow()
                rule.execution_count += 1
                
                # Get metrics after execution
                post_metrics = self.metrics_collector.get_all_metrics_summary()
                execution.metrics_after = self._flatten_metrics(post_metrics)
                
                self.execution_history.append(execution)
                
                if success:
                    logger.info(f"Successfully executed automation rule: {rule.rule_id}")
                else:
                    logger.error(f"Failed to execute automation rule: {rule.rule_id}")
                
            finally:
                # Remove from active operations
                self.active_operations.discard(execution_id)
            
        except Exception as e:
            logger.error(f"Error executing automation rule {rule.rule_id}: {e}")
            self.active_operations.discard(execution_id)
    
    async def _execute_scaling_operation(self, rule: AutomationRule, execution: AutomationExecution) -> bool:
        """Execute scaling operation."""
        try:
            execution.action_taken = "auto_scale"
            execution.trigger_reason = "CPU usage threshold exceeded"
            
            # Get scaling decision
            current_metrics = self._flatten_metrics(self.metrics_collector.get_all_metrics_summary())
            scaling_decision = await self.auto_scaler.evaluate_scaling_decision("main_service", current_metrics)
            
            if scaling_decision:
                success = await self.auto_scaler.execute_scaling_action(scaling_decision)
                execution.result = f"Scaling action: {scaling_decision['action']}"
                return success
            
            execution.result = "No scaling action needed"
            return True
            
        except Exception as e:
            execution.error_message = str(e)
            return False
    
    async def _execute_backup_operation(self, rule: AutomationRule, execution: AutomationExecution) -> bool:
        """Execute backup operation."""
        try:
            execution.action_taken = "scheduled_backup"
            execution.trigger_reason = "Scheduled backup interval reached"
            
            backup_type = rule.action_parameters.get('backup_type', 'incremental')
            success = await self.backup_automation.trigger_emergency_backup(f"Automated {backup_type} backup")
            
            execution.result = f"Backup completed: {backup_type}"
            return success
            
        except Exception as e:
            execution.error_message = str(e)
            return False
    
    async def _execute_optimization_operation(self, rule: AutomationRule, execution: AutomationExecution) -> bool:
        """Execute optimization operation."""
        try:
            execution.action_taken = "performance_optimization"
            execution.trigger_reason = "High-priority optimization recommendations available"
            
            # In real implementation, this would execute specific optimizations
            await asyncio.sleep(2)  # Simulate optimization time
            
            execution.result = "Performance optimizations applied"
            return True
            
        except Exception as e:
            execution.error_message = str(e)
            return False
    
    async def _handle_fault_event(self, fault_event: FaultEvent):
        """Handle fault events for automated recovery."""
        try:
            # Check if automated recovery is enabled for this fault
            recovery_rule = None
            for rule in self.automation_rules.values():
                if (rule.operation_type == OperationType.RECOVERY and
                    fault_event.severity.value in rule.trigger_conditions.get('fault_severity', [])):
                    recovery_rule = rule
                    break
            
            if recovery_rule and recovery_rule.automation_level == AutomationLevel.AUTOMATIC:
                logger.info(f"Triggering automated recovery for fault {fault_event.fault_id}")
                await self.recovery_system.handle_fault_automatically(fault_event)
            
        except Exception as e:
            logger.error(f"Error handling fault event for automation: {e}")
    
    def _flatten_metrics(self, metrics_summary: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Flatten metrics summary to simple key-value pairs."""
        flat_metrics = {}
        
        for metric_name, metric_data in metrics_summary.items():
            if isinstance(metric_data, dict) and 'latest' in metric_data:
                flat_metrics[metric_name] = metric_data['latest'] or 0.0
        
        return flat_metrics
    
    def get_automation_status(self) -> Dict[str, Any]:
        """Get automation system status."""
        try:
            return {
                "is_running": self.is_running,
                "active_operations": len(self.active_operations),
                "automation_rules": {
                    rule_id: {
                        "operation_type": rule.operation_type.value,
                        "automation_level": rule.automation_level.value,
                        "enabled": rule.enabled,
                        "last_executed": rule.last_executed.isoformat() if rule.last_executed else None,
                        "execution_count": rule.execution_count
                    }
                    for rule_id, rule in self.automation_rules.items()
                },
                "recent_executions": [
                    {
                        "execution_id": exec.execution_id,
                        "rule_id": exec.rule_id,
                        "operation_type": exec.operation_type.value,
                        "success": exec.success,
                        "started_at": exec.started_at.isoformat(),
                        "completed_at": exec.completed_at.isoformat() if exec.completed_at else None
                    }
                    for exec in list(self.execution_history)[-10:]
                ],
                "scaling_history": self.auto_scaler.get_scaling_history(10),
                "recovery_history": self.recovery_system.get_recovery_history(10),
                "backup_history": self.backup_automation.get_backup_history(10)
            }
            
        except Exception as e:
            logger.error(f"Error getting automation status: {e}")
            return {"error": str(e)}


# Global instance
automated_operations = None

def get_automated_operations() -> AutomatedOperationsSystem:
    """Get the global automated operations instance."""
    global automated_operations
    if automated_operations is None:
        from src.system.intelligent_operations import get_intelligent_operations
        from src.system.monitoring import MetricsCollector
        from src.system.fault_detection_system import FaultDetectionSystem
        from src.system.backup_recovery_system import BackupRecoverySystem
        
        intelligent_ops = get_intelligent_operations()
        metrics_collector = MetricsCollector()
        fault_detector = FaultDetectionSystem()
        backup_system = BackupRecoverySystem()
        
        automated_operations = AutomatedOperationsSystem(
            intelligent_ops=intelligent_ops,
            metrics_collector=metrics_collector,
            fault_detector=fault_detector,
            backup_system=backup_system
        )
    
    return automated_operations