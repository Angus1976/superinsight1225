"""
Recovery Orchestrator for SuperInsight Platform.

Coordinates automatic recovery actions across multiple systems including:
- Service restart and scaling
- Traffic redirection and load balancing
- Data backup and restoration
- Configuration rollback
- Dependency management
"""

import asyncio
import logging
import time
import json
import subprocess
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from src.system.fault_detection_system import FaultEvent, FaultType, FaultSeverity
from src.system.health_monitor import health_monitor
from src.system.notification import notification_system, NotificationPriority, NotificationChannel
from src.utils.degradation import degradation_manager

logger = logging.getLogger(__name__)


class RecoveryActionType(Enum):
    """Types of recovery actions."""
    SERVICE_RESTART = "service_restart"
    SERVICE_SCALE = "service_scale"
    TRAFFIC_REDIRECT = "traffic_redirect"
    CACHE_CLEAR = "cache_clear"
    CONFIG_ROLLBACK = "config_rollback"
    DATA_RESTORE = "data_restore"
    DEPENDENCY_ISOLATION = "dependency_isolation"
    CIRCUIT_BREAKER = "circuit_breaker"
    ALERT_ESCALATION = "alert_escalation"


class RecoveryStatus(Enum):
    """Status of recovery actions."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RecoveryAction:
    """Recovery action definition."""
    action_id: str
    action_type: RecoveryActionType
    target_service: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 300.0  # 5 minutes default
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    status: RecoveryStatus = RecoveryStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class RecoveryPlan:
    """Recovery plan containing multiple actions."""
    plan_id: str
    fault_id: str
    actions: List[RecoveryAction]
    created_at: datetime
    priority: int = 5  # 1 = highest, 10 = lowest
    estimated_duration: float = 0.0
    actual_duration: Optional[float] = None
    success_rate: float = 0.0
    status: RecoveryStatus = RecoveryStatus.PENDING


class RecoveryOrchestrator:
    """
    Orchestrates automatic recovery actions across the platform.
    
    Features:
    - Intelligent recovery plan generation
    - Parallel and sequential action execution
    - Dependency management
    - Rollback capabilities
    - Success rate tracking
    - Integration with multiple recovery systems
    """
    
    def __init__(self):
        self.active_plans: Dict[str, RecoveryPlan] = {}
        self.plan_history: List[RecoveryPlan] = []
        self.action_handlers: Dict[RecoveryActionType, Callable] = {}
        self.recovery_templates: Dict[FaultType, List[RecoveryActionType]] = {}
        
        # Orchestration state
        self.orchestrator_active = False
        self.orchestrator_task: Optional[asyncio.Task] = None
        self.execution_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent actions
        
        # Statistics
        self.action_success_rates: Dict[RecoveryActionType, float] = {}
        self.service_recovery_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Setup default handlers and templates
        self._setup_action_handlers()
        self._setup_recovery_templates()
    
    def _setup_action_handlers(self):
        """Setup handlers for different recovery action types."""
        self.action_handlers = {
            RecoveryActionType.SERVICE_RESTART: self._handle_service_restart,
            RecoveryActionType.SERVICE_SCALE: self._handle_service_scale,
            RecoveryActionType.TRAFFIC_REDIRECT: self._handle_traffic_redirect,
            RecoveryActionType.CACHE_CLEAR: self._handle_cache_clear,
            RecoveryActionType.CONFIG_ROLLBACK: self._handle_config_rollback,
            RecoveryActionType.DATA_RESTORE: self._handle_data_restore,
            RecoveryActionType.DEPENDENCY_ISOLATION: self._handle_dependency_isolation,
            RecoveryActionType.CIRCUIT_BREAKER: self._handle_circuit_breaker,
            RecoveryActionType.ALERT_ESCALATION: self._handle_alert_escalation
        }
        
        # Initialize success rates
        for action_type in RecoveryActionType:
            self.action_success_rates[action_type] = 0.7  # Default 70% success rate
    
    def _setup_recovery_templates(self):
        """Setup recovery templates for different fault types."""
        self.recovery_templates = {
            FaultType.SERVICE_UNAVAILABLE: [
                RecoveryActionType.CIRCUIT_BREAKER,
                RecoveryActionType.SERVICE_RESTART,
                RecoveryActionType.TRAFFIC_REDIRECT,
                RecoveryActionType.ALERT_ESCALATION
            ],
            FaultType.PERFORMANCE_DEGRADATION: [
                RecoveryActionType.CACHE_CLEAR,
                RecoveryActionType.SERVICE_SCALE,
                RecoveryActionType.TRAFFIC_REDIRECT
            ],
            FaultType.RESOURCE_EXHAUSTION: [
                RecoveryActionType.CACHE_CLEAR,
                RecoveryActionType.SERVICE_SCALE,
                RecoveryActionType.SERVICE_RESTART
            ],
            FaultType.CASCADE_FAILURE: [
                RecoveryActionType.CIRCUIT_BREAKER,
                RecoveryActionType.DEPENDENCY_ISOLATION,
                RecoveryActionType.TRAFFIC_REDIRECT,
                RecoveryActionType.ALERT_ESCALATION
            ],
            FaultType.CONFIGURATION_ERROR: [
                RecoveryActionType.CONFIG_ROLLBACK,
                RecoveryActionType.SERVICE_RESTART,
                RecoveryActionType.ALERT_ESCALATION
            ],
            FaultType.DATA_CORRUPTION: [
                RecoveryActionType.DATA_RESTORE,
                RecoveryActionType.SERVICE_RESTART,
                RecoveryActionType.ALERT_ESCALATION
            ]
        }
    
    async def start_orchestrator(self):
        """Start the recovery orchestrator."""
        if self.orchestrator_active:
            logger.warning("Recovery orchestrator is already active")
            return
        
        self.orchestrator_active = True
        self.orchestrator_task = asyncio.create_task(self._orchestration_loop())
        
        logger.info("Recovery orchestrator started")
    
    async def stop_orchestrator(self):
        """Stop the recovery orchestrator."""
        self.orchestrator_active = False
        
        if self.orchestrator_task:
            self.orchestrator_task.cancel()
            try:
                await self.orchestrator_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Recovery orchestrator stopped")
    
    async def create_recovery_plan(self, fault_event: FaultEvent) -> RecoveryPlan:
        """Create a recovery plan for a fault event."""
        try:
            plan_id = f"plan_{int(time.time() * 1000)}"
            
            # Generate recovery actions based on fault type
            actions = await self._generate_recovery_actions(fault_event)
            
            # Calculate estimated duration
            estimated_duration = sum(action.timeout for action in actions)
            
            # Determine priority based on fault severity
            priority_map = {
                FaultSeverity.CRITICAL: 1,
                FaultSeverity.HIGH: 2,
                FaultSeverity.MEDIUM: 5,
                FaultSeverity.LOW: 8
            }
            priority = priority_map.get(fault_event.severity, 5)
            
            # Create recovery plan
            recovery_plan = RecoveryPlan(
                plan_id=plan_id,
                fault_id=fault_event.fault_id,
                actions=actions,
                created_at=datetime.utcnow(),
                priority=priority,
                estimated_duration=estimated_duration
            )
            
            logger.info(f"Created recovery plan {plan_id} for fault {fault_event.fault_id} with {len(actions)} actions")
            
            return recovery_plan
            
        except Exception as e:
            logger.error(f"Error creating recovery plan: {e}")
            raise
    
    async def execute_recovery_plan(self, recovery_plan: RecoveryPlan) -> bool:
        """Execute a recovery plan."""
        try:
            # Add to active plans
            self.active_plans[recovery_plan.plan_id] = recovery_plan
            recovery_plan.status = RecoveryStatus.IN_PROGRESS
            
            start_time = time.time()
            
            logger.info(f"Executing recovery plan {recovery_plan.plan_id}")
            
            # Send notification about plan execution
            notification_system.send_notification(
                title=f"Recovery Plan Execution Started",
                message=f"Plan: {recovery_plan.plan_id}\n"
                       f"Fault: {recovery_plan.fault_id}\n"
                       f"Actions: {len(recovery_plan.actions)}\n"
                       f"Estimated Duration: {recovery_plan.estimated_duration:.1f}s",
                priority=NotificationPriority.NORMAL,
                channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
            )
            
            # Execute actions
            success_count = 0
            total_actions = len(recovery_plan.actions)
            
            # Group actions by dependencies
            action_groups = self._group_actions_by_dependencies(recovery_plan.actions)
            
            for group in action_groups:
                # Execute actions in group concurrently
                group_tasks = []
                for action in group:
                    task = asyncio.create_task(self._execute_action(action))
                    group_tasks.append(task)
                
                # Wait for group to complete
                group_results = await asyncio.gather(*group_tasks, return_exceptions=True)
                
                # Count successes
                for result in group_results:
                    if isinstance(result, bool) and result:
                        success_count += 1
                    elif isinstance(result, Exception):
                        logger.error(f"Action execution failed: {result}")
            
            # Calculate results
            recovery_plan.actual_duration = time.time() - start_time
            recovery_plan.success_rate = success_count / total_actions if total_actions > 0 else 0
            
            # Determine overall success
            overall_success = recovery_plan.success_rate >= 0.7  # 70% success threshold
            recovery_plan.status = RecoveryStatus.COMPLETED if overall_success else RecoveryStatus.FAILED
            
            # Send completion notification
            notification_system.send_notification(
                title=f"Recovery Plan {'Completed' if overall_success else 'Failed'}",
                message=f"Plan: {recovery_plan.plan_id}\n"
                       f"Success Rate: {recovery_plan.success_rate:.1%}\n"
                       f"Duration: {recovery_plan.actual_duration:.1f}s\n"
                       f"Actions Completed: {success_count}/{total_actions}",
                priority=NotificationPriority.NORMAL if overall_success else NotificationPriority.HIGH,
                channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
            )
            
            # Move to history
            self.plan_history.append(recovery_plan)
            if recovery_plan.plan_id in self.active_plans:
                del self.active_plans[recovery_plan.plan_id]
            
            logger.info(f"Recovery plan {recovery_plan.plan_id} completed with {recovery_plan.success_rate:.1%} success rate")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"Error executing recovery plan: {e}")
            recovery_plan.status = RecoveryStatus.FAILED
            return False
    
    async def _orchestration_loop(self):
        """Main orchestration loop for managing recovery plans."""
        while self.orchestrator_active:
            try:
                # Check for plan timeouts
                await self._check_plan_timeouts()
                
                # Update action success rates
                self._update_success_rates()
                
                # Clean up old history
                self._cleanup_history()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(30)
    
    async def _generate_recovery_actions(self, fault_event: FaultEvent) -> List[RecoveryAction]:
        """Generate recovery actions for a fault event."""
        try:
            actions = []
            
            # Get template actions for fault type
            template_actions = self.recovery_templates.get(fault_event.fault_type, [])
            
            for i, action_type in enumerate(template_actions):
                action_id = f"action_{fault_event.fault_id}_{i}"
                
                # Create action with appropriate parameters
                action = RecoveryAction(
                    action_id=action_id,
                    action_type=action_type,
                    target_service=fault_event.service_name,
                    parameters=self._get_action_parameters(action_type, fault_event),
                    timeout=self._get_action_timeout(action_type),
                    max_retries=self._get_action_max_retries(action_type)
                )
                
                # Set dependencies
                if i > 0:  # Actions depend on previous actions
                    action.dependencies = [actions[i-1].action_id]
                
                actions.append(action)
            
            return actions
            
        except Exception as e:
            logger.error(f"Error generating recovery actions: {e}")
            return []
    
    def _get_action_parameters(self, action_type: RecoveryActionType, fault_event: FaultEvent) -> Dict[str, Any]:
        """Get parameters for a specific action type."""
        parameters = {}
        
        if action_type == RecoveryActionType.SERVICE_SCALE:
            # Scale up based on fault severity
            scale_factor = {
                FaultSeverity.LOW: 1.2,
                FaultSeverity.MEDIUM: 1.5,
                FaultSeverity.HIGH: 2.0,
                FaultSeverity.CRITICAL: 3.0
            }.get(fault_event.severity, 1.5)
            
            parameters = {
                "scale_factor": scale_factor,
                "max_instances": 10
            }
        
        elif action_type == RecoveryActionType.TRAFFIC_REDIRECT:
            parameters = {
                "redirect_percentage": 100,
                "target_services": ["backup_service", "fallback_service"]
            }
        
        elif action_type == RecoveryActionType.CONFIG_ROLLBACK:
            parameters = {
                "rollback_steps": 1,
                "backup_retention": "24h"
            }
        
        elif action_type == RecoveryActionType.DATA_RESTORE:
            parameters = {
                "restore_point": "latest",
                "verify_integrity": True
            }
        
        return parameters
    
    def _get_action_timeout(self, action_type: RecoveryActionType) -> float:
        """Get timeout for a specific action type."""
        timeouts = {
            RecoveryActionType.SERVICE_RESTART: 120.0,
            RecoveryActionType.SERVICE_SCALE: 180.0,
            RecoveryActionType.TRAFFIC_REDIRECT: 60.0,
            RecoveryActionType.CACHE_CLEAR: 30.0,
            RecoveryActionType.CONFIG_ROLLBACK: 90.0,
            RecoveryActionType.DATA_RESTORE: 600.0,  # 10 minutes
            RecoveryActionType.DEPENDENCY_ISOLATION: 60.0,
            RecoveryActionType.CIRCUIT_BREAKER: 30.0,
            RecoveryActionType.ALERT_ESCALATION: 10.0
        }
        return timeouts.get(action_type, 120.0)
    
    def _get_action_max_retries(self, action_type: RecoveryActionType) -> int:
        """Get max retries for a specific action type."""
        retries = {
            RecoveryActionType.SERVICE_RESTART: 3,
            RecoveryActionType.SERVICE_SCALE: 2,
            RecoveryActionType.TRAFFIC_REDIRECT: 2,
            RecoveryActionType.CACHE_CLEAR: 1,
            RecoveryActionType.CONFIG_ROLLBACK: 1,
            RecoveryActionType.DATA_RESTORE: 1,
            RecoveryActionType.DEPENDENCY_ISOLATION: 2,
            RecoveryActionType.CIRCUIT_BREAKER: 1,
            RecoveryActionType.ALERT_ESCALATION: 1
        }
        return retries.get(action_type, 2)
    
    def _group_actions_by_dependencies(self, actions: List[RecoveryAction]) -> List[List[RecoveryAction]]:
        """Group actions by their dependencies for parallel execution."""
        groups = []
        remaining_actions = actions.copy()
        completed_actions = set()
        
        while remaining_actions:
            current_group = []
            
            # Find actions with no pending dependencies
            for action in remaining_actions.copy():
                if all(dep in completed_actions for dep in action.dependencies):
                    current_group.append(action)
                    remaining_actions.remove(action)
            
            if not current_group:
                # Circular dependency or error - add remaining actions to avoid infinite loop
                current_group = remaining_actions.copy()
                remaining_actions.clear()
            
            groups.append(current_group)
            completed_actions.update(action.action_id for action in current_group)
        
        return groups
    
    async def _execute_action(self, action: RecoveryAction) -> bool:
        """Execute a single recovery action."""
        async with self.execution_semaphore:
            try:
                action.status = RecoveryStatus.IN_PROGRESS
                action.started_at = datetime.utcnow()
                
                logger.info(f"Executing action {action.action_id}: {action.action_type.value}")
                
                # Get handler for action type
                handler = self.action_handlers.get(action.action_type)
                if not handler:
                    logger.error(f"No handler for action type: {action.action_type}")
                    action.status = RecoveryStatus.FAILED
                    action.error_message = "No handler available"
                    return False
                
                # Execute with timeout and retries
                for attempt in range(action.max_retries + 1):
                    try:
                        success = await asyncio.wait_for(
                            handler(action),
                            timeout=action.timeout
                        )
                        
                        if success:
                            action.status = RecoveryStatus.COMPLETED
                            action.completed_at = datetime.utcnow()
                            
                            # Update success rate
                            self._update_action_success_rate(action.action_type, True)
                            
                            logger.info(f"Action {action.action_id} completed successfully")
                            return True
                        else:
                            action.retry_count += 1
                            if attempt < action.max_retries:
                                logger.warning(f"Action {action.action_id} failed, retrying ({attempt + 1}/{action.max_retries})")
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            else:
                                action.status = RecoveryStatus.FAILED
                                action.error_message = "Action failed after retries"
                    
                    except asyncio.TimeoutError:
                        action.retry_count += 1
                        if attempt < action.max_retries:
                            logger.warning(f"Action {action.action_id} timed out, retrying ({attempt + 1}/{action.max_retries})")
                            await asyncio.sleep(2 ** attempt)
                        else:
                            action.status = RecoveryStatus.FAILED
                            action.error_message = "Action timed out"
                    
                    except Exception as e:
                        action.retry_count += 1
                        if attempt < action.max_retries:
                            logger.warning(f"Action {action.action_id} error: {e}, retrying ({attempt + 1}/{action.max_retries})")
                            await asyncio.sleep(2 ** attempt)
                        else:
                            action.status = RecoveryStatus.FAILED
                            action.error_message = str(e)
                
                # Update success rate for failure
                self._update_action_success_rate(action.action_type, False)
                
                logger.error(f"Action {action.action_id} failed after all retries")
                return False
                
            except Exception as e:
                logger.error(f"Error executing action {action.action_id}: {e}")
                action.status = RecoveryStatus.FAILED
                action.error_message = str(e)
                return False
    
    # Action handlers
    async def _handle_service_restart(self, action: RecoveryAction) -> bool:
        """Handle service restart action."""
        try:
            service_name = action.target_service
            
            logger.info(f"Restarting service: {service_name}")
            
            # Mark service as degraded during restart
            degradation_manager.mark_service_failure(service_name)
            
            # Simulate service restart (in real implementation, this would interact with container orchestrator)
            await asyncio.sleep(5)  # Simulate restart time
            
            # Mark service as recovered
            degradation_manager.mark_service_success(service_name)
            
            logger.info(f"Service {service_name} restarted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            return False
    
    async def _handle_service_scale(self, action: RecoveryAction) -> bool:
        """Handle service scaling action."""
        try:
            service_name = action.target_service
            scale_factor = action.parameters.get("scale_factor", 1.5)
            max_instances = action.parameters.get("max_instances", 10)
            
            logger.info(f"Scaling service {service_name} by factor {scale_factor}")
            
            # Simulate scaling (in real implementation, this would interact with orchestrator)
            await asyncio.sleep(3)
            
            logger.info(f"Service {service_name} scaled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Service scaling failed: {e}")
            return False
    
    async def _handle_traffic_redirect(self, action: RecoveryAction) -> bool:
        """Handle traffic redirection action."""
        try:
            service_name = action.target_service
            redirect_percentage = action.parameters.get("redirect_percentage", 100)
            
            logger.info(f"Redirecting {redirect_percentage}% traffic from {service_name}")
            
            # Mark service as degraded to redirect traffic
            degradation_manager.mark_service_failure(service_name)
            
            await asyncio.sleep(2)
            
            logger.info(f"Traffic redirected from {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Traffic redirection failed: {e}")
            return False
    
    async def _handle_cache_clear(self, action: RecoveryAction) -> bool:
        """Handle cache clearing action."""
        try:
            logger.info("Clearing system caches")
            
            # Clear degradation manager cache
            degradation_manager.clear_cache()
            
            await asyncio.sleep(1)
            
            logger.info("System caches cleared")
            return True
            
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
            return False
    
    async def _handle_config_rollback(self, action: RecoveryAction) -> bool:
        """Handle configuration rollback action."""
        try:
            service_name = action.target_service
            rollback_steps = action.parameters.get("rollback_steps", 1)
            
            logger.info(f"Rolling back configuration for {service_name} by {rollback_steps} steps")
            
            # Simulate config rollback
            await asyncio.sleep(3)
            
            logger.info(f"Configuration rolled back for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration rollback failed: {e}")
            return False
    
    async def _handle_data_restore(self, action: RecoveryAction) -> bool:
        """Handle data restoration action."""
        try:
            service_name = action.target_service
            restore_point = action.parameters.get("restore_point", "latest")
            
            logger.info(f"Restoring data for {service_name} from {restore_point}")
            
            # Simulate data restore
            await asyncio.sleep(10)  # Data restore takes longer
            
            logger.info(f"Data restored for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Data restoration failed: {e}")
            return False
    
    async def _handle_dependency_isolation(self, action: RecoveryAction) -> bool:
        """Handle dependency isolation action."""
        try:
            service_name = action.target_service
            
            logger.info(f"Isolating dependencies for {service_name}")
            
            # Mark dependent services as degraded
            degradation_manager.mark_service_failure(f"{service_name}_dependencies")
            
            await asyncio.sleep(2)
            
            logger.info(f"Dependencies isolated for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Dependency isolation failed: {e}")
            return False
    
    async def _handle_circuit_breaker(self, action: RecoveryAction) -> bool:
        """Handle circuit breaker activation."""
        try:
            service_name = action.target_service
            
            logger.info(f"Activating circuit breaker for {service_name}")
            
            # Mark service as degraded to activate circuit breaker
            degradation_manager.mark_service_failure(service_name)
            
            await asyncio.sleep(1)
            
            logger.info(f"Circuit breaker activated for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Circuit breaker activation failed: {e}")
            return False
    
    async def _handle_alert_escalation(self, action: RecoveryAction) -> bool:
        """Handle alert escalation action."""
        try:
            service_name = action.target_service
            
            logger.info(f"Escalating alert for {service_name}")
            
            # Send escalation notification
            notification_system.send_notification(
                title=f"ESCALATED ALERT - {service_name}",
                message=f"Automatic recovery failed for {service_name}. Manual intervention required.",
                priority=NotificationPriority.CRITICAL,
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.WEBHOOK]
            )
            
            logger.info(f"Alert escalated for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Alert escalation failed: {e}")
            return False
    
    def _update_action_success_rate(self, action_type: RecoveryActionType, success: bool):
        """Update success rate for an action type."""
        current_rate = self.action_success_rates.get(action_type, 0.5)
        alpha = 0.1  # Learning rate
        
        new_value = 1.0 if success else 0.0
        self.action_success_rates[action_type] = alpha * new_value + (1 - alpha) * current_rate
    
    async def _check_plan_timeouts(self):
        """Check for plan timeouts and handle them."""
        try:
            current_time = datetime.utcnow()
            
            for plan_id, plan in list(self.active_plans.items()):
                # Check if plan has been running too long
                elapsed_time = (current_time - plan.created_at).total_seconds()
                max_duration = plan.estimated_duration * 2  # Allow 2x estimated time
                
                if elapsed_time > max_duration:
                    logger.warning(f"Recovery plan {plan_id} timed out after {elapsed_time:.1f}s")
                    
                    plan.status = RecoveryStatus.FAILED
                    plan.actual_duration = elapsed_time
                    
                    # Move to history
                    self.plan_history.append(plan)
                    del self.active_plans[plan_id]
                    
                    # Send timeout notification
                    notification_system.send_notification(
                        title=f"Recovery Plan Timeout",
                        message=f"Plan {plan_id} timed out after {elapsed_time:.1f}s",
                        priority=NotificationPriority.HIGH,
                        channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
                    )
            
        except Exception as e:
            logger.error(f"Error checking plan timeouts: {e}")
    
    def _update_success_rates(self):
        """Update overall success rates based on recent history."""
        try:
            # Update success rates based on recent plans
            recent_plans = [p for p in self.plan_history[-50:] if p.actual_duration is not None]
            
            if recent_plans:
                for action_type in RecoveryActionType:
                    # Count successes for this action type
                    action_results = []
                    for plan in recent_plans:
                        for action in plan.actions:
                            if action.action_type == action_type:
                                action_results.append(action.status == RecoveryStatus.COMPLETED)
                    
                    if action_results:
                        success_rate = sum(action_results) / len(action_results)
                        # Update with exponential moving average
                        alpha = 0.1
                        current_rate = self.action_success_rates.get(action_type, 0.5)
                        self.action_success_rates[action_type] = alpha * success_rate + (1 - alpha) * current_rate
            
        except Exception as e:
            logger.error(f"Error updating success rates: {e}")
    
    def _cleanup_history(self):
        """Clean up old history to prevent memory growth."""
        try:
            # Keep only last 1000 plans
            if len(self.plan_history) > 1000:
                self.plan_history = self.plan_history[-1000:]
            
            # Clean up service recovery history
            for service_name in list(self.service_recovery_history.keys()):
                history = self.service_recovery_history[service_name]
                if len(history) > 100:
                    self.service_recovery_history[service_name] = history[-100:]
            
        except Exception as e:
            logger.error(f"Error cleaning up history: {e}")
    
    def get_orchestrator_statistics(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator statistics."""
        try:
            total_plans = len(self.plan_history)
            successful_plans = sum(1 for p in self.plan_history if p.success_rate >= 0.7)
            
            if total_plans == 0:
                return {
                    "total_plans": 0,
                    "success_rate": 0.0,
                    "active_plans": len(self.active_plans),
                    "action_success_rates": dict(self.action_success_rates),
                    "avg_plan_duration": 0.0
                }
            
            # Calculate average plan duration
            completed_plans = [p for p in self.plan_history if p.actual_duration is not None]
            avg_duration = sum(p.actual_duration for p in completed_plans) / len(completed_plans) if completed_plans else 0
            
            return {
                "total_plans": total_plans,
                "successful_plans": successful_plans,
                "success_rate": successful_plans / total_plans,
                "active_plans": len(self.active_plans),
                "action_success_rates": {k.value: v for k, v in self.action_success_rates.items()},
                "avg_plan_duration": avg_duration,
                "recent_plans": [
                    {
                        "plan_id": p.plan_id,
                        "fault_id": p.fault_id,
                        "actions_count": len(p.actions),
                        "success_rate": p.success_rate,
                        "duration": p.actual_duration,
                        "status": p.status.value,
                        "created_at": p.created_at.isoformat()
                    }
                    for p in self.plan_history[-10:]  # Last 10 plans
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting orchestrator statistics: {e}")
            return {}


# Global recovery orchestrator instance
recovery_orchestrator = RecoveryOrchestrator()


# Convenience functions
async def start_recovery_orchestrator():
    """Start the global recovery orchestrator."""
    await recovery_orchestrator.start_orchestrator()


async def stop_recovery_orchestrator():
    """Stop the global recovery orchestrator."""
    await recovery_orchestrator.stop_orchestrator()


async def execute_fault_recovery(fault_event) -> bool:
    """Execute recovery for a fault event."""
    try:
        # Create recovery plan
        recovery_plan = await recovery_orchestrator.create_recovery_plan(fault_event)
        
        # Execute recovery plan
        success = await recovery_orchestrator.execute_recovery_plan(recovery_plan)
        
        return success
        
    except Exception as e:
        logger.error(f"Error executing fault recovery: {e}")
        return False


def get_recovery_status() -> Dict[str, Any]:
    """Get current recovery orchestrator status."""
    return {
        "orchestrator_active": recovery_orchestrator.orchestrator_active,
        "active_plans": len(recovery_orchestrator.active_plans),
        "total_action_types": len(recovery_orchestrator.action_handlers),
        "statistics": recovery_orchestrator.get_orchestrator_statistics()
    }