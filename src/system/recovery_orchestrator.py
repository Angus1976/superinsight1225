"""
Recovery Orchestrator for High Availability System.

Coordinates and executes recovery plans for system failures,
managing the recovery workflow and ensuring system stability.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from src.system.failure_detector import FailureAnalysis, FailureEvent, FailureType, FailureSeverity

logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """Status of a recovery operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class RecoveryPriority(Enum):
    """Priority levels for recovery operations."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


@dataclass
class RecoveryAction:
    """Represents a single recovery action."""
    action_id: str
    name: str
    description: str
    execute_func: Callable
    rollback_func: Optional[Callable] = None
    timeout_seconds: float = 60.0
    retry_count: int = 3
    retry_delay: float = 5.0
    dependencies: List[str] = field(default_factory=list)
    status: RecoveryStatus = RecoveryStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class RecoveryPlan:
    """A complete recovery plan with ordered actions."""
    plan_id: str
    name: str
    description: str
    priority: RecoveryPriority
    actions: List[RecoveryAction]
    failure_analysis: FailureAnalysis
    status: RecoveryStatus = RecoveryStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    success_rate: float = 0.0
    rollback_on_failure: bool = True


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool
    plan_id: str
    duration: float
    actions_completed: int
    actions_failed: int
    services_recovered: List[str]
    data_integrity_verified: bool
    performance_restored: bool
    message: str = ""
    errors: List[str] = field(default_factory=list)


class RecoveryOrchestrator:
    """
    Orchestrates recovery operations for system failures.
    
    Features:
    - Intelligent recovery plan generation
    - Ordered action execution with dependencies
    - Automatic rollback on failure
    - Recovery progress tracking
    - Concurrent recovery management
    """
    
    def __init__(self):
        self.active_recoveries: Dict[str, RecoveryPlan] = {}
        self.recovery_history: deque = deque(maxlen=500)
        self.recovery_actions: Dict[str, Callable] = {}
        self.rollback_actions: Dict[str, Callable] = {}
        self.max_concurrent_recoveries = 3
        self._lock = asyncio.Lock()
        
        # Register default recovery actions
        self._register_default_actions()
        
        logger.info("RecoveryOrchestrator initialized")
    
    def _register_default_actions(self):
        """Register default recovery actions."""
        # Service recovery actions
        self.register_action("restart_service", self._restart_service, self._stop_service)
        self.register_action("scale_service", self._scale_service, self._scale_down_service)
        self.register_action("failover_service", self._failover_service, self._failback_service)
        
        # Database recovery actions
        self.register_action("reconnect_database", self._reconnect_database)
        self.register_action("switch_to_replica", self._switch_to_replica, self._switch_to_primary)
        self.register_action("restore_from_backup", self._restore_from_backup)
        
        # Resource recovery actions
        self.register_action("clear_caches", self._clear_caches)
        self.register_action("free_memory", self._free_memory)
        self.register_action("cleanup_disk", self._cleanup_disk)
        
        # Network recovery actions
        self.register_action("reset_connections", self._reset_connections)
        self.register_action("enable_circuit_breaker", self._enable_circuit_breaker, self._disable_circuit_breaker)
        
        # Degradation actions
        self.register_action("enable_degraded_mode", self._enable_degraded_mode, self._disable_degraded_mode)
        self.register_action("reduce_load", self._reduce_load, self._restore_load)
    
    def register_action(
        self, 
        name: str, 
        execute_func: Callable, 
        rollback_func: Optional[Callable] = None
    ):
        """Register a recovery action."""
        self.recovery_actions[name] = execute_func
        if rollback_func:
            self.rollback_actions[name] = rollback_func
        logger.debug(f"Registered recovery action: {name}")
    
    async def create_recovery_plan(
        self, 
        failure_analysis: FailureAnalysis
    ) -> RecoveryPlan:
        """Create a recovery plan based on failure analysis."""
        plan_id = str(uuid.uuid4())[:8]
        
        # Determine priority based on failures
        priority = self._determine_priority(failure_analysis)
        
        # Generate recovery actions based on failures
        actions = await self._generate_recovery_actions(failure_analysis)
        
        # Order actions by dependencies
        ordered_actions = self._order_actions_by_dependencies(actions)
        
        plan = RecoveryPlan(
            plan_id=plan_id,
            name=f"Recovery Plan {plan_id}",
            description=self._generate_plan_description(failure_analysis),
            priority=priority,
            actions=ordered_actions,
            failure_analysis=failure_analysis,
            rollback_on_failure=priority.value >= RecoveryPriority.HIGH.value
        )
        
        logger.info(f"Created recovery plan {plan_id} with {len(actions)} actions")
        return plan
    
    def _determine_priority(self, analysis: FailureAnalysis) -> RecoveryPriority:
        """Determine recovery priority based on failure analysis."""
        if analysis.has_critical_failures:
            critical_count = sum(
                1 for f in analysis.failures 
                if f.severity == FailureSeverity.CRITICAL
            )
            if critical_count >= 2:
                return RecoveryPriority.EMERGENCY
            return RecoveryPriority.CRITICAL
        
        high_count = sum(
            1 for f in analysis.failures 
            if f.severity == FailureSeverity.HIGH
        )
        if high_count >= 2:
            return RecoveryPriority.HIGH
        elif high_count == 1:
            return RecoveryPriority.MEDIUM
        
        return RecoveryPriority.LOW
    
    async def _generate_recovery_actions(
        self, 
        analysis: FailureAnalysis
    ) -> List[RecoveryAction]:
        """Generate recovery actions based on failure analysis."""
        actions = []
        action_id = 0
        
        for failure in analysis.failures:
            failure_actions = self._get_actions_for_failure(failure)
            for action_name, description, deps in failure_actions:
                if action_name in self.recovery_actions:
                    action = RecoveryAction(
                        action_id=f"action_{action_id}",
                        name=action_name,
                        description=description,
                        execute_func=self.recovery_actions[action_name],
                        rollback_func=self.rollback_actions.get(action_name),
                        dependencies=deps
                    )
                    actions.append(action)
                    action_id += 1
        
        # Deduplicate actions
        seen = set()
        unique_actions = []
        for action in actions:
            if action.name not in seen:
                seen.add(action.name)
                unique_actions.append(action)
        
        return unique_actions
    
    def _get_actions_for_failure(
        self, 
        failure: FailureEvent
    ) -> List[tuple]:
        """Get recovery actions for a specific failure type."""
        actions_map = {
            FailureType.SERVICE_DOWN: [
                ("restart_service", f"Restart {failure.service_name}", []),
                ("failover_service", f"Failover {failure.service_name}", ["restart_service"]),
            ],
            FailureType.PERFORMANCE_DEGRADATION: [
                ("clear_caches", "Clear system caches", []),
                ("scale_service", f"Scale {failure.service_name}", ["clear_caches"]),
                ("reduce_load", "Reduce system load", []),
            ],
            FailureType.RESOURCE_EXHAUSTION: [
                ("free_memory", "Free up memory", []),
                ("cleanup_disk", "Cleanup disk space", []),
                ("enable_degraded_mode", "Enable degraded mode", []),
            ],
            FailureType.DATABASE_FAILURE: [
                ("reconnect_database", "Reconnect to database", []),
                ("switch_to_replica", "Switch to database replica", ["reconnect_database"]),
            ],
            FailureType.NETWORK_PARTITION: [
                ("reset_connections", "Reset network connections", []),
                ("enable_circuit_breaker", "Enable circuit breaker", []),
            ],
            FailureType.EXTERNAL_DEPENDENCY: [
                ("enable_circuit_breaker", "Enable circuit breaker", []),
                ("enable_degraded_mode", "Enable degraded mode", []),
            ],
        }
        
        return actions_map.get(failure.failure_type, [
            ("enable_degraded_mode", "Enable degraded mode", [])
        ])
    
    def _order_actions_by_dependencies(
        self, 
        actions: List[RecoveryAction]
    ) -> List[RecoveryAction]:
        """Order actions based on their dependencies."""
        action_map = {a.action_id: a for a in actions}
        name_to_id = {a.name: a.action_id for a in actions}
        
        # Topological sort
        ordered = []
        visited = set()
        temp_visited = set()
        
        def visit(action_id: str):
            if action_id in temp_visited:
                return  # Circular dependency, skip
            if action_id in visited:
                return
            
            temp_visited.add(action_id)
            action = action_map.get(action_id)
            if action:
                for dep_name in action.dependencies:
                    dep_id = name_to_id.get(dep_name)
                    if dep_id:
                        visit(dep_id)
            
            temp_visited.remove(action_id)
            visited.add(action_id)
            if action:
                ordered.append(action)
        
        for action in actions:
            visit(action.action_id)
        
        return ordered
    
    def _generate_plan_description(self, analysis: FailureAnalysis) -> str:
        """Generate a description for the recovery plan."""
        failure_types = set(f.failure_type.value for f in analysis.failures)
        services = set(f.service_name for f in analysis.failures)
        
        return (
            f"Recovery plan for {len(analysis.failures)} failures "
            f"({', '.join(failure_types)}) affecting {', '.join(services)}"
        )
    
    async def execute_recovery_plan(
        self, 
        plan: RecoveryPlan,
        context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """Execute a recovery plan."""
        async with self._lock:
            if len(self.active_recoveries) >= self.max_concurrent_recoveries:
                logger.warning("Maximum concurrent recoveries reached")
                return RecoveryResult(
                    success=False,
                    plan_id=plan.plan_id,
                    duration=0,
                    actions_completed=0,
                    actions_failed=0,
                    services_recovered=[],
                    data_integrity_verified=False,
                    performance_restored=False,
                    message="Maximum concurrent recoveries reached"
                )
            
            self.active_recoveries[plan.plan_id] = plan
        
        plan.status = RecoveryStatus.IN_PROGRESS
        plan.started_at = time.time()
        
        context = context or {}
        actions_completed = 0
        actions_failed = 0
        services_recovered = []
        errors = []
        
        try:
            logger.info(f"Executing recovery plan {plan.plan_id}")
            
            for action in plan.actions:
                action_result = await self._execute_action(action, context)
                
                if action_result["success"]:
                    actions_completed += 1
                    if "service" in action.name:
                        services_recovered.append(action.name)
                else:
                    actions_failed += 1
                    errors.append(action_result.get("error", "Unknown error"))
                    
                    if plan.rollback_on_failure:
                        logger.info(f"Rolling back plan {plan.plan_id} due to action failure")
                        await self._rollback_plan(plan, actions_completed)
                        plan.status = RecoveryStatus.ROLLED_BACK
                        break
            
            if plan.status != RecoveryStatus.ROLLED_BACK:
                plan.status = RecoveryStatus.COMPLETED if actions_failed == 0 else RecoveryStatus.FAILED
            
            plan.completed_at = time.time()
            duration = plan.completed_at - plan.started_at
            
            total_actions = len(plan.actions)
            plan.success_rate = actions_completed / total_actions if total_actions > 0 else 0
            
            # Verify recovery
            data_integrity = await self._verify_data_integrity()
            performance_restored = await self._verify_performance()
            
            result = RecoveryResult(
                success=plan.status == RecoveryStatus.COMPLETED,
                plan_id=plan.plan_id,
                duration=duration,
                actions_completed=actions_completed,
                actions_failed=actions_failed,
                services_recovered=services_recovered,
                data_integrity_verified=data_integrity,
                performance_restored=performance_restored,
                message=f"Recovery {'completed' if plan.status == RecoveryStatus.COMPLETED else 'failed'}",
                errors=errors
            )
            
            # Record in history
            self.recovery_history.append({
                "plan_id": plan.plan_id,
                "result": result,
                "timestamp": time.time()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Recovery plan {plan.plan_id} failed with exception: {e}")
            plan.status = RecoveryStatus.FAILED
            plan.completed_at = time.time()
            
            return RecoveryResult(
                success=False,
                plan_id=plan.plan_id,
                duration=time.time() - plan.started_at,
                actions_completed=actions_completed,
                actions_failed=actions_failed + 1,
                services_recovered=services_recovered,
                data_integrity_verified=False,
                performance_restored=False,
                message=f"Recovery failed: {str(e)}",
                errors=errors + [str(e)]
            )
        
        finally:
            async with self._lock:
                self.active_recoveries.pop(plan.plan_id, None)
    
    async def _execute_action(
        self, 
        action: RecoveryAction, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single recovery action with retry logic."""
        action.status = RecoveryStatus.IN_PROGRESS
        action.start_time = time.time()
        
        for attempt in range(action.retry_count):
            try:
                logger.info(f"Executing action {action.name} (attempt {attempt + 1})")
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    action.execute_func(context),
                    timeout=action.timeout_seconds
                )
                
                action.status = RecoveryStatus.COMPLETED
                action.end_time = time.time()
                action.result = result
                
                return {"success": True, "result": result}
                
            except asyncio.TimeoutError:
                logger.warning(f"Action {action.name} timed out (attempt {attempt + 1})")
                action.error = "Timeout"
            except Exception as e:
                logger.warning(f"Action {action.name} failed (attempt {attempt + 1}): {e}")
                action.error = str(e)
            
            if attempt < action.retry_count - 1:
                await asyncio.sleep(action.retry_delay)
        
        action.status = RecoveryStatus.FAILED
        action.end_time = time.time()
        
        return {"success": False, "error": action.error}
    
    async def _rollback_plan(self, plan: RecoveryPlan, completed_count: int):
        """Rollback completed actions in reverse order."""
        logger.info(f"Rolling back {completed_count} actions for plan {plan.plan_id}")
        
        # Get completed actions in reverse order
        completed_actions = [a for a in plan.actions[:completed_count] if a.rollback_func]
        completed_actions.reverse()
        
        for action in completed_actions:
            try:
                logger.info(f"Rolling back action {action.name}")
                await asyncio.wait_for(
                    action.rollback_func({}),
                    timeout=action.timeout_seconds
                )
            except Exception as e:
                logger.error(f"Rollback of {action.name} failed: {e}")
    
    async def _verify_data_integrity(self) -> bool:
        """Verify data integrity after recovery."""
        # Placeholder - would implement actual verification
        return True
    
    async def _verify_performance(self) -> bool:
        """Verify system performance after recovery."""
        # Placeholder - would implement actual verification
        return True
    
    # Default recovery action implementations
    async def _restart_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Restart a service."""
        logger.info("Executing: restart_service")
        await asyncio.sleep(0.5)  # Simulate restart
        return {"status": "restarted"}
    
    async def _stop_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a service (rollback for restart)."""
        logger.info("Executing: stop_service")
        return {"status": "stopped"}
    
    async def _scale_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Scale up a service."""
        logger.info("Executing: scale_service")
        return {"status": "scaled", "replicas": 3}
    
    async def _scale_down_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Scale down a service."""
        logger.info("Executing: scale_down_service")
        return {"status": "scaled_down", "replicas": 1}
    
    async def _failover_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Failover to backup service."""
        logger.info("Executing: failover_service")
        return {"status": "failed_over"}
    
    async def _failback_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Failback to primary service."""
        logger.info("Executing: failback_service")
        return {"status": "failed_back"}
    
    async def _reconnect_database(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reconnect to database."""
        logger.info("Executing: reconnect_database")
        return {"status": "reconnected"}
    
    async def _switch_to_replica(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to database replica."""
        logger.info("Executing: switch_to_replica")
        return {"status": "switched_to_replica"}
    
    async def _switch_to_primary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Switch back to primary database."""
        logger.info("Executing: switch_to_primary")
        return {"status": "switched_to_primary"}
    
    async def _restore_from_backup(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Restore from backup."""
        logger.info("Executing: restore_from_backup")
        return {"status": "restored"}
    
    async def _clear_caches(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Clear system caches."""
        logger.info("Executing: clear_caches")
        return {"status": "caches_cleared"}
    
    async def _free_memory(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Free up memory."""
        logger.info("Executing: free_memory")
        import gc
        gc.collect()
        return {"status": "memory_freed"}
    
    async def _cleanup_disk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Cleanup disk space."""
        logger.info("Executing: cleanup_disk")
        return {"status": "disk_cleaned"}
    
    async def _reset_connections(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reset network connections."""
        logger.info("Executing: reset_connections")
        return {"status": "connections_reset"}
    
    async def _enable_circuit_breaker(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enable circuit breaker."""
        logger.info("Executing: enable_circuit_breaker")
        return {"status": "circuit_breaker_enabled"}
    
    async def _disable_circuit_breaker(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Disable circuit breaker."""
        logger.info("Executing: disable_circuit_breaker")
        return {"status": "circuit_breaker_disabled"}
    
    async def _enable_degraded_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enable degraded mode."""
        logger.info("Executing: enable_degraded_mode")
        return {"status": "degraded_mode_enabled"}
    
    async def _disable_degraded_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Disable degraded mode."""
        logger.info("Executing: disable_degraded_mode")
        return {"status": "degraded_mode_disabled"}
    
    async def _reduce_load(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reduce system load."""
        logger.info("Executing: reduce_load")
        return {"status": "load_reduced"}
    
    async def _restore_load(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Restore normal load."""
        logger.info("Executing: restore_load")
        return {"status": "load_restored"}
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        if not self.recovery_history:
            return {"total_recoveries": 0}
        
        history = list(self.recovery_history)
        successful = sum(1 for h in history if h["result"].success)
        
        return {
            "total_recoveries": len(history),
            "successful_recoveries": successful,
            "failed_recoveries": len(history) - successful,
            "success_rate": successful / len(history) if history else 0,
            "active_recoveries": len(self.active_recoveries),
        }


# Global recovery orchestrator instance
recovery_orchestrator = RecoveryOrchestrator()
