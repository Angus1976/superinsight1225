"""
Auto-Remediation Engine for SuperInsight Platform.

Provides automatic quality issue remediation:
- Repair strategy registry
- Automatic fix application
- Validation and verification
- Rollback support
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import asyncio
import uuid

logger = logging.getLogger(__name__)


class RemediationStrategy(str, Enum):
    """Types of remediation strategies."""
    AUTO_CORRECT = "auto_correct"
    REASSIGN = "reassign"
    ESCALATE = "escalate"
    RETRAIN = "retrain"
    MERGE = "merge"
    SPLIT = "split"
    VALIDATE = "validate"
    NOTIFY = "notify"


class RemediationStatus(str, Enum):
    """Status of remediation actions."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class RemediationPriority(str, Enum):
    """Priority levels for remediation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RemediationAction:
    """Represents a remediation action."""
    action_id: str
    strategy: RemediationStrategy
    priority: RemediationPriority
    status: RemediationStatus
    anomaly_id: str
    entity_id: str
    entity_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rollback_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "strategy": self.strategy.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "anomaly_id": self.anomaly_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "description": self.description,
            "parameters": self.parameters,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class RepairStrategy:
    """Definition of a repair strategy."""
    strategy_id: str
    name: str
    description: str
    strategy_type: RemediationStrategy
    applicable_anomaly_types: List[str]
    applicable_entity_types: List[str]
    priority: RemediationPriority
    auto_execute: bool = False
    requires_approval: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
    handler: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type.value,
            "applicable_anomaly_types": self.applicable_anomaly_types,
            "applicable_entity_types": self.applicable_entity_types,
            "priority": self.priority.value,
            "auto_execute": self.auto_execute,
            "requires_approval": self.requires_approval,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds
        }


class RepairStrategyRegistry:
    """Registry for repair strategies."""

    def __init__(self):
        self.strategies: Dict[str, RepairStrategy] = {}
        self._initialize_default_strategies()

    def _initialize_default_strategies(self):
        """Initialize default repair strategies."""
        default_strategies = [
            RepairStrategy(
                strategy_id="auto_correct_low_accuracy",
                name="自动修正低准确率",
                description="自动修正准确率低于阈值的标注",
                strategy_type=RemediationStrategy.AUTO_CORRECT,
                applicable_anomaly_types=["threshold", "statistical"],
                applicable_entity_types=["task", "annotation"],
                priority=RemediationPriority.HIGH,
                auto_execute=False,
                requires_approval=True
            ),
            RepairStrategy(
                strategy_id="reassign_low_performer",
                name="重新分配低效标注员任务",
                description="将低效标注员的任务重新分配给高效标注员",
                strategy_type=RemediationStrategy.REASSIGN,
                applicable_anomaly_types=["threshold", "trend"],
                applicable_entity_types=["annotator", "task"],
                priority=RemediationPriority.MEDIUM,
                auto_execute=True,
                requires_approval=False
            ),
            RepairStrategy(
                strategy_id="escalate_critical",
                name="升级关键问题",
                description="将关键质量问题升级给管理员",
                strategy_type=RemediationStrategy.ESCALATE,
                applicable_anomaly_types=["*"],
                applicable_entity_types=["*"],
                priority=RemediationPriority.CRITICAL,
                auto_execute=True,
                requires_approval=False
            ),
            RepairStrategy(
                strategy_id="retrain_annotator",
                name="标注员再培训",
                description="为表现不佳的标注员安排再培训",
                strategy_type=RemediationStrategy.RETRAIN,
                applicable_anomaly_types=["threshold", "trend"],
                applicable_entity_types=["annotator"],
                priority=RemediationPriority.LOW,
                auto_execute=False,
                requires_approval=True
            ),
            RepairStrategy(
                strategy_id="merge_annotations",
                name="合并标注结果",
                description="合并多个标注员的结果以提高准确性",
                strategy_type=RemediationStrategy.MERGE,
                applicable_anomaly_types=["statistical"],
                applicable_entity_types=["task", "annotation"],
                priority=RemediationPriority.MEDIUM,
                auto_execute=True,
                requires_approval=False
            ),
            RepairStrategy(
                strategy_id="validate_annotation",
                name="验证标注质量",
                description="对可疑标注进行额外验证",
                strategy_type=RemediationStrategy.VALIDATE,
                applicable_anomaly_types=["*"],
                applicable_entity_types=["annotation", "task"],
                priority=RemediationPriority.MEDIUM,
                auto_execute=True,
                requires_approval=False
            ),
            RepairStrategy(
                strategy_id="notify_stakeholders",
                name="通知相关方",
                description="通知项目相关方质量问题",
                strategy_type=RemediationStrategy.NOTIFY,
                applicable_anomaly_types=["*"],
                applicable_entity_types=["*"],
                priority=RemediationPriority.LOW,
                auto_execute=True,
                requires_approval=False
            )
        ]

        for strategy in default_strategies:
            self.strategies[strategy.strategy_id] = strategy

    def register(self, strategy: RepairStrategy):
        """Register a repair strategy."""
        self.strategies[strategy.strategy_id] = strategy
        logger.info(f"Registered repair strategy: {strategy.name}")

    def unregister(self, strategy_id: str) -> bool:
        """Unregister a repair strategy."""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            return True
        return False

    def get(self, strategy_id: str) -> Optional[RepairStrategy]:
        """Get a strategy by ID."""
        return self.strategies.get(strategy_id)

    def find_applicable(
        self,
        anomaly_type: str,
        entity_type: str
    ) -> List[RepairStrategy]:
        """Find applicable strategies for an anomaly."""
        applicable = []
        for strategy in self.strategies.values():
            type_match = (
                "*" in strategy.applicable_anomaly_types or
                anomaly_type in strategy.applicable_anomaly_types
            )
            entity_match = (
                "*" in strategy.applicable_entity_types or
                entity_type in strategy.applicable_entity_types
            )
            if type_match and entity_match:
                applicable.append(strategy)
        return sorted(applicable, key=lambda s: s.priority.value, reverse=True)

    def list_all(self) -> List[RepairStrategy]:
        """List all registered strategies."""
        return list(self.strategies.values())


class AutoRemediationEngine:
    """
    Automatic remediation engine for quality issues.
    
    Provides:
    - Automatic issue detection and remediation
    - Strategy selection and execution
    - Validation and rollback support
    """

    def __init__(self):
        self.strategy_registry = RepairStrategyRegistry()
        self.pending_actions: Dict[str, RemediationAction] = {}
        self.action_history: List[RemediationAction] = []
        self.execution_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"success": 0, "failed": 0, "skipped": 0}
        )
        self._handlers: Dict[RemediationStrategy, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default remediation handlers."""
        self._handlers[RemediationStrategy.AUTO_CORRECT] = self._handle_auto_correct
        self._handlers[RemediationStrategy.REASSIGN] = self._handle_reassign
        self._handlers[RemediationStrategy.ESCALATE] = self._handle_escalate
        self._handlers[RemediationStrategy.RETRAIN] = self._handle_retrain
        self._handlers[RemediationStrategy.MERGE] = self._handle_merge
        self._handlers[RemediationStrategy.VALIDATE] = self._handle_validate
        self._handlers[RemediationStrategy.NOTIFY] = self._handle_notify

    def register_handler(
        self,
        strategy_type: RemediationStrategy,
        handler: Callable
    ):
        """Register a custom handler for a strategy type."""
        self._handlers[strategy_type] = handler

    async def create_remediation(
        self,
        anomaly_id: str,
        entity_id: str,
        entity_type: str,
        anomaly_type: str,
        severity: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[RemediationAction]:
        """
        Create remediation actions for an anomaly.
        
        Args:
            anomaly_id: ID of the detected anomaly
            entity_id: ID of the affected entity
            entity_type: Type of entity (task, annotator, project)
            anomaly_type: Type of anomaly
            severity: Severity level
            context: Additional context
            
        Returns:
            List of created remediation actions
        """
        # Find applicable strategies
        strategies = self.strategy_registry.find_applicable(anomaly_type, entity_type)
        
        if not strategies:
            logger.warning(f"No applicable strategies for {anomaly_type}/{entity_type}")
            return []

        actions = []
        for strategy in strategies:
            # Determine priority based on severity
            priority = self._determine_priority(severity, strategy.priority)
            
            action = RemediationAction(
                action_id=str(uuid.uuid4()),
                strategy=strategy.strategy_type,
                priority=priority,
                status=RemediationStatus.PENDING,
                anomaly_id=anomaly_id,
                entity_id=entity_id,
                entity_type=entity_type,
                description=f"{strategy.name}: {entity_type}/{entity_id}",
                parameters={
                    "strategy_id": strategy.strategy_id,
                    "context": context or {},
                    "anomaly_type": anomaly_type,
                    "severity": severity
                }
            )
            
            self.pending_actions[action.action_id] = action
            actions.append(action)
            
            # Auto-execute if configured
            if strategy.auto_execute and not strategy.requires_approval:
                asyncio.create_task(self.execute_action(action.action_id))

        logger.info(f"Created {len(actions)} remediation actions for anomaly {anomaly_id}")
        return actions

    def _determine_priority(
        self,
        severity: str,
        default_priority: RemediationPriority
    ) -> RemediationPriority:
        """Determine action priority based on severity."""
        severity_map = {
            "critical": RemediationPriority.CRITICAL,
            "high": RemediationPriority.HIGH,
            "medium": RemediationPriority.MEDIUM,
            "low": RemediationPriority.LOW
        }
        severity_priority = severity_map.get(severity.lower(), default_priority)
        
        # Use higher priority
        if severity_priority.value > default_priority.value:
            return severity_priority
        return default_priority

    async def execute_action(
        self,
        action_id: str,
        force: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute a remediation action.
        
        Args:
            action_id: ID of the action to execute
            force: Force execution even if requires approval
            
        Returns:
            Tuple of (success, error_message)
        """
        action = self.pending_actions.get(action_id)
        if not action:
            return False, "Action not found"

        strategy = self.strategy_registry.get(
            action.parameters.get("strategy_id", "")
        )
        
        if strategy and strategy.requires_approval and not force:
            return False, "Action requires approval"

        action.status = RemediationStatus.IN_PROGRESS
        action.started_at = datetime.now()

        try:
            handler = self._handlers.get(action.strategy)
            if not handler:
                raise ValueError(f"No handler for strategy: {action.strategy}")

            # Execute handler
            result = await handler(action)
            
            action.status = RemediationStatus.COMPLETED
            action.completed_at = datetime.now()
            action.result = result
            
            # Update stats
            self.execution_stats[action.strategy.value]["success"] += 1
            
            # Move to history
            self.action_history.append(action)
            del self.pending_actions[action_id]
            
            logger.info(f"Remediation action {action_id} completed successfully")
            return True, None

        except Exception as e:
            action.status = RemediationStatus.FAILED
            action.completed_at = datetime.now()
            action.error_message = str(e)
            
            self.execution_stats[action.strategy.value]["failed"] += 1
            
            logger.error(f"Remediation action {action_id} failed: {e}")
            return False, str(e)

    async def rollback_action(self, action_id: str) -> Tuple[bool, Optional[str]]:
        """
        Rollback a completed remediation action.
        
        Args:
            action_id: ID of the action to rollback
            
        Returns:
            Tuple of (success, error_message)
        """
        # Find action in history
        action = None
        for a in self.action_history:
            if a.action_id == action_id:
                action = a
                break

        if not action:
            return False, "Action not found in history"

        if action.status != RemediationStatus.COMPLETED:
            return False, "Can only rollback completed actions"

        if not action.rollback_data:
            return False, "No rollback data available"

        try:
            # Execute rollback based on strategy
            await self._execute_rollback(action)
            
            action.status = RemediationStatus.ROLLED_BACK
            logger.info(f"Rolled back action {action_id}")
            return True, None

        except Exception as e:
            logger.error(f"Rollback failed for {action_id}: {e}")
            return False, str(e)

    async def _execute_rollback(self, action: RemediationAction):
        """Execute rollback for an action."""
        rollback_data = action.rollback_data
        if not rollback_data:
            return

        # Strategy-specific rollback logic
        if action.strategy == RemediationStrategy.REASSIGN:
            # Restore original assignment
            original_assignee = rollback_data.get("original_assignee")
            if original_assignee:
                logger.info(f"Restoring assignment to {original_assignee}")
                # Integration with task management would go here

        elif action.strategy == RemediationStrategy.AUTO_CORRECT:
            # Restore original value
            original_value = rollback_data.get("original_value")
            if original_value:
                logger.info(f"Restoring original value")
                # Integration with annotation system would go here

    # Default handlers
    async def _handle_auto_correct(self, action: RemediationAction) -> Dict[str, Any]:
        """Handle auto-correction strategy."""
        context = action.parameters.get("context", {})
        
        # Store rollback data
        action.rollback_data = {
            "original_value": context.get("current_value"),
            "entity_id": action.entity_id
        }
        
        # Simulate correction logic
        logger.info(f"Auto-correcting {action.entity_type}/{action.entity_id}")
        
        return {
            "corrected": True,
            "entity_id": action.entity_id,
            "correction_type": "auto",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_reassign(self, action: RemediationAction) -> Dict[str, Any]:
        """Handle reassignment strategy."""
        context = action.parameters.get("context", {})
        
        # Store rollback data
        action.rollback_data = {
            "original_assignee": context.get("current_assignee"),
            "entity_id": action.entity_id
        }
        
        # Simulate reassignment logic
        logger.info(f"Reassigning {action.entity_type}/{action.entity_id}")
        
        return {
            "reassigned": True,
            "entity_id": action.entity_id,
            "new_assignee": "auto_selected",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_escalate(self, action: RemediationAction) -> Dict[str, Any]:
        """Handle escalation strategy."""
        logger.info(f"Escalating {action.entity_type}/{action.entity_id}")
        
        return {
            "escalated": True,
            "entity_id": action.entity_id,
            "escalation_level": "manager",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_retrain(self, action: RemediationAction) -> Dict[str, Any]:
        """Handle retraining strategy."""
        logger.info(f"Scheduling retraining for {action.entity_id}")
        
        return {
            "training_scheduled": True,
            "entity_id": action.entity_id,
            "training_type": "quality_improvement",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_merge(self, action: RemediationAction) -> Dict[str, Any]:
        """Handle merge strategy."""
        logger.info(f"Merging annotations for {action.entity_id}")
        
        return {
            "merged": True,
            "entity_id": action.entity_id,
            "merge_method": "consensus",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_validate(self, action: RemediationAction) -> Dict[str, Any]:
        """Handle validation strategy."""
        logger.info(f"Validating {action.entity_type}/{action.entity_id}")
        
        return {
            "validated": True,
            "entity_id": action.entity_id,
            "validation_result": "pending_review",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_notify(self, action: RemediationAction) -> Dict[str, Any]:
        """Handle notification strategy."""
        logger.info(f"Sending notification for {action.entity_id}")
        
        return {
            "notified": True,
            "entity_id": action.entity_id,
            "notification_type": "quality_alert",
            "timestamp": datetime.now().isoformat()
        }

    def approve_action(self, action_id: str, approved_by: str) -> bool:
        """Approve a pending action."""
        action = self.pending_actions.get(action_id)
        if not action:
            return False

        action.parameters["approved_by"] = approved_by
        action.parameters["approved_at"] = datetime.now().isoformat()
        
        # Schedule execution
        asyncio.create_task(self.execute_action(action_id, force=True))
        return True

    def reject_action(self, action_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a pending action."""
        action = self.pending_actions.get(action_id)
        if not action:
            return False

        action.status = RemediationStatus.SKIPPED
        action.parameters["rejected_by"] = rejected_by
        action.parameters["rejection_reason"] = reason
        
        self.execution_stats[action.strategy.value]["skipped"] += 1
        
        self.action_history.append(action)
        del self.pending_actions[action_id]
        
        return True

    def get_pending_actions(
        self,
        priority: Optional[RemediationPriority] = None
    ) -> List[RemediationAction]:
        """Get pending actions, optionally filtered by priority."""
        actions = list(self.pending_actions.values())
        if priority:
            actions = [a for a in actions if a.priority == priority]
        return sorted(actions, key=lambda a: a.created_at)

    def get_action_history(
        self,
        limit: int = 100,
        status: Optional[RemediationStatus] = None
    ) -> List[RemediationAction]:
        """Get action history."""
        history = self.action_history
        if status:
            history = [a for a in history if a.status == status]
        return history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get remediation statistics."""
        total_pending = len(self.pending_actions)
        total_completed = sum(
            s["success"] for s in self.execution_stats.values()
        )
        total_failed = sum(
            s["failed"] for s in self.execution_stats.values()
        )
        total_skipped = sum(
            s["skipped"] for s in self.execution_stats.values()
        )

        success_rate = (
            total_completed / (total_completed + total_failed)
            if (total_completed + total_failed) > 0 else 0
        )

        return {
            "pending_actions": total_pending,
            "completed_actions": total_completed,
            "failed_actions": total_failed,
            "skipped_actions": total_skipped,
            "success_rate": success_rate,
            "by_strategy": dict(self.execution_stats),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
auto_remediation_engine = AutoRemediationEngine()
