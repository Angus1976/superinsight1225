"""
Workflow Engine for SuperInsight Platform.

Provides quality governance workflow orchestration:
- State machine management
- Workflow definition and execution
- Approval flow integration
- Automated transitions
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid
import asyncio

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """Standard workflow states."""
    DRAFT = "draft"
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class TransitionType(str, Enum):
    """Types of state transitions."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CONDITIONAL = "conditional"
    APPROVAL = "approval"
    TIMEOUT = "timeout"


@dataclass
class StateTransition:
    """Defines a state transition."""
    transition_id: str
    name: str
    from_state: WorkflowState
    to_state: WorkflowState
    transition_type: TransitionType
    conditions: List[str] = field(default_factory=list)
    required_approvers: int = 0
    timeout_hours: Optional[float] = None
    actions: List[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "name": self.name,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "transition_type": self.transition_type.value,
            "conditions": self.conditions,
            "required_approvers": self.required_approvers,
            "timeout_hours": self.timeout_hours,
            "actions": self.actions,
            "enabled": self.enabled
        }


@dataclass
class WorkflowDefinition:
    """Defines a workflow type."""
    workflow_id: str
    name: str
    description: str
    initial_state: WorkflowState
    final_states: List[WorkflowState]
    transitions: List[StateTransition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "initial_state": self.initial_state.value,
            "final_states": [s.value for s in self.final_states],
            "transitions": [t.to_dict() for t in self.transitions],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }

    def get_available_transitions(self, current_state: WorkflowState) -> List[StateTransition]:
        """Get available transitions from current state."""
        return [t for t in self.transitions if t.from_state == current_state and t.enabled]


@dataclass
class WorkflowInstance:
    """Instance of a workflow execution."""
    instance_id: str
    workflow_id: str
    entity_id: str
    entity_type: str
    current_state: WorkflowState
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    pending_approvals: List[Dict[str, Any]] = field(default_factory=list)
    completed_approvals: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    owner: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "workflow_id": self.workflow_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "current_state": self.current_state.value,
            "state_history": self.state_history,
            "pending_approvals": self.pending_approvals,
            "completed_approvals": self.completed_approvals,
            "context": self.context,
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ApprovalRequest:
    """Represents an approval request."""
    request_id: str
    instance_id: str
    transition_id: str
    approver_id: str
    status: str = "pending"  # pending, approved, rejected
    requested_at: datetime = field(default_factory=datetime.now)
    responded_at: Optional[datetime] = None
    comments: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "instance_id": self.instance_id,
            "transition_id": self.transition_id,
            "approver_id": self.approver_id,
            "status": self.status,
            "requested_at": self.requested_at.isoformat(),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "comments": self.comments
        }


class StateMachine:
    """State machine for workflow state management."""

    def __init__(self, definition: WorkflowDefinition):
        self.definition = definition
        self._transition_map: Dict[WorkflowState, List[StateTransition]] = defaultdict(list)
        self._build_transition_map()

    def _build_transition_map(self):
        """Build transition lookup map."""
        for transition in self.definition.transitions:
            self._transition_map[transition.from_state].append(transition)

    def can_transition(
        self,
        current_state: WorkflowState,
        target_state: WorkflowState
    ) -> bool:
        """Check if transition is valid."""
        transitions = self._transition_map.get(current_state, [])
        return any(t.to_state == target_state and t.enabled for t in transitions)

    def get_transition(
        self,
        current_state: WorkflowState,
        target_state: WorkflowState
    ) -> Optional[StateTransition]:
        """Get transition between states."""
        transitions = self._transition_map.get(current_state, [])
        for t in transitions:
            if t.to_state == target_state and t.enabled:
                return t
        return None

    def get_available_states(self, current_state: WorkflowState) -> List[WorkflowState]:
        """Get states reachable from current state."""
        transitions = self._transition_map.get(current_state, [])
        return [t.to_state for t in transitions if t.enabled]

    def is_final_state(self, state: WorkflowState) -> bool:
        """Check if state is a final state."""
        return state in self.definition.final_states


class WorkflowEngine:
    """
    Workflow orchestration engine.
    
    Provides:
    - Workflow definition management
    - Instance lifecycle management
    - State transitions with validation
    - Approval flow handling
    """

    def __init__(self):
        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.instances: Dict[str, WorkflowInstance] = {}
        self.state_machines: Dict[str, StateMachine] = {}
        self.approval_requests: Dict[str, ApprovalRequest] = {}
        self.action_handlers: Dict[str, Callable] = {}
        self.condition_evaluators: Dict[str, Callable] = {}
        self._initialize_default_workflows()
        self._register_default_handlers()

    def _initialize_default_workflows(self):
        """Initialize default workflow definitions."""
        # Quality improvement workflow
        quality_improvement = WorkflowDefinition(
            workflow_id="quality_improvement",
            name="质量改进工作流",
            description="标准质量改进流程",
            initial_state=WorkflowState.DRAFT,
            final_states=[WorkflowState.COMPLETED, WorkflowState.CANCELLED],
            transitions=[
                StateTransition(
                    transition_id="submit",
                    name="提交审核",
                    from_state=WorkflowState.DRAFT,
                    to_state=WorkflowState.PENDING,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="start_review",
                    name="开始审核",
                    from_state=WorkflowState.PENDING,
                    to_state=WorkflowState.IN_REVIEW,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="approve",
                    name="审核通过",
                    from_state=WorkflowState.IN_REVIEW,
                    to_state=WorkflowState.APPROVED,
                    transition_type=TransitionType.APPROVAL,
                    required_approvers=1
                ),
                StateTransition(
                    transition_id="reject",
                    name="审核拒绝",
                    from_state=WorkflowState.IN_REVIEW,
                    to_state=WorkflowState.REJECTED,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="start_work",
                    name="开始执行",
                    from_state=WorkflowState.APPROVED,
                    to_state=WorkflowState.IN_PROGRESS,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="complete",
                    name="完成",
                    from_state=WorkflowState.IN_PROGRESS,
                    to_state=WorkflowState.COMPLETED,
                    transition_type=TransitionType.MANUAL,
                    actions=["notify_completion"]
                ),
                StateTransition(
                    transition_id="cancel",
                    name="取消",
                    from_state=WorkflowState.DRAFT,
                    to_state=WorkflowState.CANCELLED,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="cancel_pending",
                    name="取消待处理",
                    from_state=WorkflowState.PENDING,
                    to_state=WorkflowState.CANCELLED,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="hold",
                    name="暂停",
                    from_state=WorkflowState.IN_PROGRESS,
                    to_state=WorkflowState.ON_HOLD,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="resume",
                    name="恢复",
                    from_state=WorkflowState.ON_HOLD,
                    to_state=WorkflowState.IN_PROGRESS,
                    transition_type=TransitionType.MANUAL
                )
            ]
        )
        self.register_workflow(quality_improvement)

        # Anomaly resolution workflow
        anomaly_resolution = WorkflowDefinition(
            workflow_id="anomaly_resolution",
            name="异常处理工作流",
            description="质量异常处理流程",
            initial_state=WorkflowState.PENDING,
            final_states=[WorkflowState.COMPLETED, WorkflowState.CANCELLED],
            transitions=[
                StateTransition(
                    transition_id="assign",
                    name="分配处理",
                    from_state=WorkflowState.PENDING,
                    to_state=WorkflowState.IN_PROGRESS,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="auto_assign",
                    name="自动分配",
                    from_state=WorkflowState.PENDING,
                    to_state=WorkflowState.IN_PROGRESS,
                    transition_type=TransitionType.AUTOMATIC,
                    timeout_hours=4
                ),
                StateTransition(
                    transition_id="submit_resolution",
                    name="提交解决方案",
                    from_state=WorkflowState.IN_PROGRESS,
                    to_state=WorkflowState.IN_REVIEW,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="approve_resolution",
                    name="确认解决",
                    from_state=WorkflowState.IN_REVIEW,
                    to_state=WorkflowState.COMPLETED,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="reject_resolution",
                    name="退回修改",
                    from_state=WorkflowState.IN_REVIEW,
                    to_state=WorkflowState.IN_PROGRESS,
                    transition_type=TransitionType.MANUAL
                ),
                StateTransition(
                    transition_id="cancel",
                    name="取消",
                    from_state=WorkflowState.PENDING,
                    to_state=WorkflowState.CANCELLED,
                    transition_type=TransitionType.MANUAL
                )
            ]
        )
        self.register_workflow(anomaly_resolution)

    def _register_default_handlers(self):
        """Register default action handlers."""
        self.action_handlers["notify_completion"] = self._handle_notify_completion
        self.action_handlers["send_email"] = self._handle_send_email
        self.action_handlers["update_metrics"] = self._handle_update_metrics

    async def _handle_notify_completion(
        self,
        instance: WorkflowInstance,
        transition: StateTransition
    ):
        """Handle completion notification."""
        logger.info(f"Workflow {instance.instance_id} completed")
        # TODO: Integrate with notification system

    async def _handle_send_email(
        self,
        instance: WorkflowInstance,
        transition: StateTransition
    ):
        """Handle email sending."""
        logger.info(f"Sending email for workflow {instance.instance_id}")
        # TODO: Integrate with email system

    async def _handle_update_metrics(
        self,
        instance: WorkflowInstance,
        transition: StateTransition
    ):
        """Handle metrics update."""
        logger.info(f"Updating metrics for workflow {instance.instance_id}")
        # TODO: Integrate with metrics system

    def register_workflow(self, definition: WorkflowDefinition):
        """Register a workflow definition."""
        self.definitions[definition.workflow_id] = definition
        self.state_machines[definition.workflow_id] = StateMachine(definition)
        logger.info(f"Registered workflow: {definition.name}")

    def register_action_handler(self, action_name: str, handler: Callable):
        """Register an action handler."""
        self.action_handlers[action_name] = handler

    def register_condition_evaluator(self, condition_name: str, evaluator: Callable):
        """Register a condition evaluator."""
        self.condition_evaluators[condition_name] = evaluator

    async def create_instance(
        self,
        workflow_id: str,
        entity_id: str,
        entity_type: str,
        owner: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowInstance]:
        """
        Create a new workflow instance.
        
        Args:
            workflow_id: ID of the workflow definition
            entity_id: ID of the entity being processed
            entity_type: Type of entity
            owner: Owner of the workflow
            context: Initial context data
            
        Returns:
            Created WorkflowInstance or None
        """
        definition = self.definitions.get(workflow_id)
        if not definition:
            logger.error(f"Workflow definition not found: {workflow_id}")
            return None

        instance = WorkflowInstance(
            instance_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            entity_id=entity_id,
            entity_type=entity_type,
            current_state=definition.initial_state,
            owner=owner,
            context=context or {}
        )

        # Record initial state
        instance.state_history.append({
            "state": definition.initial_state.value,
            "timestamp": datetime.now().isoformat(),
            "action": "created"
        })

        self.instances[instance.instance_id] = instance
        logger.info(f"Created workflow instance {instance.instance_id} for {entity_type}/{entity_id}")

        return instance

    async def transition(
        self,
        instance_id: str,
        target_state: WorkflowState,
        triggered_by: Optional[str] = None,
        comments: Optional[str] = None
    ) -> bool:
        """
        Execute a state transition.
        
        Args:
            instance_id: Instance ID
            target_state: Target state
            triggered_by: User triggering the transition
            comments: Transition comments
            
        Returns:
            True if transition successful
        """
        instance = self.instances.get(instance_id)
        if not instance:
            return False

        state_machine = self.state_machines.get(instance.workflow_id)
        if not state_machine:
            return False

        # Get transition
        transition = state_machine.get_transition(instance.current_state, target_state)
        if not transition:
            logger.warning(
                f"Invalid transition: {instance.current_state} -> {target_state}"
            )
            return False

        # Check conditions
        if transition.conditions:
            if not await self._evaluate_conditions(instance, transition):
                logger.warning(f"Transition conditions not met")
                return False

        # Handle approval transitions
        if transition.transition_type == TransitionType.APPROVAL:
            if transition.required_approvers > 0:
                approved_count = len([
                    a for a in instance.completed_approvals
                    if a.get("transition_id") == transition.transition_id and
                    a.get("status") == "approved"
                ])
                if approved_count < transition.required_approvers:
                    logger.warning(f"Insufficient approvals: {approved_count}/{transition.required_approvers}")
                    return False

        # Execute transition
        old_state = instance.current_state
        instance.current_state = target_state
        instance.updated_at = datetime.now()

        # Record history
        instance.state_history.append({
            "from_state": old_state.value,
            "to_state": target_state.value,
            "transition_id": transition.transition_id,
            "triggered_by": triggered_by,
            "comments": comments,
            "timestamp": datetime.now().isoformat()
        })

        # Check if completed
        if state_machine.is_final_state(target_state):
            instance.completed_at = datetime.now()

        # Execute actions
        for action_name in transition.actions:
            handler = self.action_handlers.get(action_name)
            if handler:
                try:
                    await handler(instance, transition)
                except Exception as e:
                    logger.error(f"Action {action_name} failed: {e}")

        logger.info(f"Transitioned {instance_id}: {old_state} -> {target_state}")
        return True

    async def _evaluate_conditions(
        self,
        instance: WorkflowInstance,
        transition: StateTransition
    ) -> bool:
        """Evaluate transition conditions."""
        for condition in transition.conditions:
            evaluator = self.condition_evaluators.get(condition)
            if evaluator:
                try:
                    if not await evaluator(instance, transition):
                        return False
                except Exception as e:
                    logger.error(f"Condition evaluation failed: {e}")
                    return False
        return True

    async def request_approval(
        self,
        instance_id: str,
        transition_id: str,
        approver_ids: List[str]
    ) -> List[ApprovalRequest]:
        """Request approvals for a transition."""
        instance = self.instances.get(instance_id)
        if not instance:
            return []

        requests = []
        for approver_id in approver_ids:
            request = ApprovalRequest(
                request_id=str(uuid.uuid4()),
                instance_id=instance_id,
                transition_id=transition_id,
                approver_id=approver_id
            )
            self.approval_requests[request.request_id] = request
            instance.pending_approvals.append(request.to_dict())
            requests.append(request)

        return requests

    async def respond_to_approval(
        self,
        request_id: str,
        approved: bool,
        comments: Optional[str] = None
    ) -> bool:
        """Respond to an approval request."""
        request = self.approval_requests.get(request_id)
        if not request or request.status != "pending":
            return False

        instance = self.instances.get(request.instance_id)
        if not instance:
            return False

        request.status = "approved" if approved else "rejected"
        request.responded_at = datetime.now()
        request.comments = comments

        # Move from pending to completed
        instance.pending_approvals = [
            a for a in instance.pending_approvals
            if a.get("request_id") != request_id
        ]
        instance.completed_approvals.append(request.to_dict())

        return True

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get a workflow instance."""
        return self.instances.get(instance_id)

    def get_instances_by_entity(
        self,
        entity_id: str,
        entity_type: str
    ) -> List[WorkflowInstance]:
        """Get instances for an entity."""
        return [
            i for i in self.instances.values()
            if i.entity_id == entity_id and i.entity_type == entity_type
        ]

    def list_instances(
        self,
        workflow_id: Optional[str] = None,
        state: Optional[WorkflowState] = None,
        owner: Optional[str] = None,
        limit: int = 100
    ) -> List[WorkflowInstance]:
        """List workflow instances."""
        instances = list(self.instances.values())

        if workflow_id:
            instances = [i for i in instances if i.workflow_id == workflow_id]
        if state:
            instances = [i for i in instances if i.current_state == state]
        if owner:
            instances = [i for i in instances if i.owner == owner]

        return sorted(instances, key=lambda i: i.updated_at, reverse=True)[:limit]

    def get_available_transitions(
        self,
        instance_id: str
    ) -> List[StateTransition]:
        """Get available transitions for an instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            return []

        definition = self.definitions.get(instance.workflow_id)
        if not definition:
            return []

        return definition.get_available_transitions(instance.current_state)

    def get_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        by_workflow = defaultdict(int)
        by_state = defaultdict(int)
        completed_count = 0
        active_count = 0

        for instance in self.instances.values():
            by_workflow[instance.workflow_id] += 1
            by_state[instance.current_state.value] += 1

            if instance.completed_at:
                completed_count += 1
            else:
                active_count += 1

        return {
            "total_instances": len(self.instances),
            "active_instances": active_count,
            "completed_instances": completed_count,
            "by_workflow": dict(by_workflow),
            "by_state": dict(by_state),
            "pending_approvals": len([
                r for r in self.approval_requests.values()
                if r.status == "pending"
            ]),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
workflow_engine = WorkflowEngine()
