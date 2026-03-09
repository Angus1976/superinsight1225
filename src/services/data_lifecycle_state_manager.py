"""
Data Lifecycle State Manager Service

Manages state transitions for data throughout its lifecycle, enforcing
valid transitions according to the state machine definition.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.data_lifecycle import (
    DataState,
    TempDataModel,
    SampleModel,
    AnnotationTaskModel,
    EnhancedDataModel,
    AuditLogModel,
    OperationType,
    OperationResult,
    Action,
    ResourceType
)


# ============================================================================
# State Machine Definition
# ============================================================================

# Valid state transitions mapping: current_state -> set of valid next states
STATE_TRANSITIONS: Dict[DataState, Set[DataState]] = {
    DataState.RAW: {DataState.STRUCTURED},
    DataState.STRUCTURED: {DataState.TEMP_STORED},
    DataState.TEMP_STORED: {DataState.UNDER_REVIEW},
    DataState.UNDER_REVIEW: {DataState.REJECTED, DataState.APPROVED},
    DataState.REJECTED: set(),  # Terminal state (can be deleted or resubmitted manually)
    DataState.APPROVED: {DataState.IN_SAMPLE_LIBRARY},
    DataState.IN_SAMPLE_LIBRARY: {
        DataState.ANNOTATION_PENDING,
        DataState.TRIAL_CALCULATION
    },
    DataState.ANNOTATION_PENDING: {DataState.ANNOTATING},
    DataState.ANNOTATING: {DataState.ANNOTATED},
    DataState.ANNOTATED: {
        DataState.ENHANCING,
        DataState.TRIAL_CALCULATION
    },
    DataState.ENHANCING: {DataState.ENHANCED},
    DataState.ENHANCED: {
        DataState.IN_SAMPLE_LIBRARY,  # Iterative optimization
        DataState.TRIAL_CALCULATION,
        DataState.ARCHIVED
    },
    DataState.TRIAL_CALCULATION: {
        DataState.IN_SAMPLE_LIBRARY,  # Return from trial
        DataState.ANNOTATED,  # Return from trial
        DataState.ENHANCED  # Return from trial
    },
    DataState.ARCHIVED: set()  # Terminal state
}


class StateTransitionContext:
    """Context for state transition operations"""
    def __init__(
        self,
        user_id: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.user_id = user_id
        self.reason = reason
        self.metadata = metadata or {}


class StateTransitionResult:
    """Result of a state transition operation"""
    def __init__(
        self,
        success: bool,
        previous_state: DataState,
        current_state: DataState,
        transitioned_at: datetime,
        error: Optional[str] = None
    ):
        self.success = success
        self.previous_state = previous_state
        self.current_state = current_state
        self.transitioned_at = transitioned_at
        self.error = error


class StateHistory:
    """State history record"""
    def __init__(
        self,
        id: UUID,
        data_id: str,
        state: DataState,
        user_id: str,
        transitioned_at: datetime,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.id = id
        self.data_id = data_id
        self.state = state
        self.user_id = user_id
        self.transitioned_at = transitioned_at
        self.reason = reason
        self.metadata = metadata or {}


# ============================================================================
# Data State Manager Service
# ============================================================================

class DataStateManager:
    """
    Manages data state transitions throughout the lifecycle.
    
    Responsibilities:
    - Enforce valid state transitions
    - Track state history
    - Validate transition permissions
    - Emit state change events (via audit logging)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_current_state(self, data_id: str, resource_type: ResourceType) -> DataState:
        """
        Get the current state of a data item.
        
        Args:
            data_id: The data item ID
            resource_type: The type of resource (temp_data, sample, etc.)
        
        Returns:
            Current DataState
        
        Raises:
            ValueError: If data item not found
        """
        model_class = self._get_model_class(resource_type)
        data_item = self.db.query(model_class).filter(
            model_class.id == data_id
        ).first()
        
        if not data_item:
            raise ValueError(f"Data item {data_id} not found")
        
        # Get state based on resource type
        if resource_type == ResourceType.TEMP_DATA:
            return data_item.state
        elif resource_type == ResourceType.SAMPLE:
            return DataState.IN_SAMPLE_LIBRARY
        elif resource_type == ResourceType.ANNOTATED_DATA:
            # Check task status to determine state
            task = self.db.query(AnnotationTaskModel).filter(
                AnnotationTaskModel.id == data_id
            ).first()
            if task:
                if task.status.value == 'created':
                    return DataState.ANNOTATION_PENDING
                elif task.status.value == 'in_progress':
                    return DataState.ANNOTATING
                elif task.status.value == 'completed':
                    return DataState.ANNOTATED
        elif resource_type == ResourceType.ENHANCED_DATA:
            enhanced = self.db.query(EnhancedDataModel).filter(
                EnhancedDataModel.id == data_id
            ).first()
            if enhanced:
                return DataState.ENHANCED
        
        raise ValueError(f"Cannot determine state for {resource_type}: {data_id}")
    
    def validate_transition(
        self,
        current_state: DataState,
        target_state: DataState
    ) -> bool:
        """
        Validate if a state transition is allowed.
        
        Args:
            current_state: Current state
            target_state: Target state
        
        Returns:
            True if transition is valid, False otherwise
        """
        valid_next_states = STATE_TRANSITIONS.get(current_state, set())
        return target_state in valid_next_states
    
    def get_valid_next_states(self, current_state: DataState) -> List[DataState]:
        """
        Get list of valid next states from current state.
        
        Args:
            current_state: Current state
        
        Returns:
            List of valid next states
        """
        return list(STATE_TRANSITIONS.get(current_state, set()))
    
    def transition_state(
        self,
        data_id: str,
        resource_type: ResourceType,
        target_state: DataState,
        context: StateTransitionContext
    ) -> StateTransitionResult:
        """
        Transition data to a new state.
        
        This operation is atomic - either the entire transition succeeds
        (state updated, history recorded, audit logged) or it fails with
        no partial changes.
        
        Args:
            data_id: The data item ID
            resource_type: The type of resource
            target_state: Target state to transition to
            context: Transition context with user info and reason
        
        Returns:
            StateTransitionResult with success status and details
        """
        try:
            # Get current state
            current_state = self.get_current_state(data_id, resource_type)
            
            # Validate transition
            if not self.validate_transition(current_state, target_state):
                valid_states = self.get_valid_next_states(current_state)
                return StateTransitionResult(
                    success=False,
                    previous_state=current_state,
                    current_state=current_state,
                    transitioned_at=datetime.utcnow(),
                    error=f"Invalid transition from {current_state.value} to {target_state.value}. "
                          f"Valid next states: {[s.value for s in valid_states]}"
                )
            
            # Update state in database
            model_class = self._get_model_class(resource_type)
            data_item = self.db.query(model_class).filter(
                model_class.id == data_id
            ).first()
            
            if not data_item:
                return StateTransitionResult(
                    success=False,
                    previous_state=current_state,
                    current_state=current_state,
                    transitioned_at=datetime.utcnow(),
                    error=f"Data item {data_id} not found"
                )
            
            # Update state based on resource type
            if resource_type == ResourceType.TEMP_DATA:
                data_item.state = target_state
                data_item.updated_at = datetime.utcnow()
            
            transitioned_at = datetime.utcnow()
            
            # Record state history in audit log
            self._record_state_history(
                data_id=data_id,
                resource_type=resource_type,
                previous_state=current_state,
                new_state=target_state,
                context=context,
                transitioned_at=transitioned_at
            )
            
            # Commit transaction (atomic operation)
            self.db.commit()
            
            return StateTransitionResult(
                success=True,
                previous_state=current_state,
                current_state=target_state,
                transitioned_at=transitioned_at
            )
            
        except Exception as e:
            # Rollback on any error to ensure atomicity
            self.db.rollback()
            return StateTransitionResult(
                success=False,
                previous_state=current_state if 'current_state' in locals() else DataState.RAW,
                current_state=current_state if 'current_state' in locals() else DataState.RAW,
                transitioned_at=datetime.utcnow(),
                error=str(e)
            )
    
    def get_state_history(
        self,
        data_id: str,
        resource_type: ResourceType
    ) -> List[StateHistory]:
        """
        Get state transition history for a data item.
        
        Args:
            data_id: The data item ID
            resource_type: The type of resource
        
        Returns:
            List of StateHistory records ordered by timestamp
        """
        # Query audit logs for state change operations
        audit_logs = self.db.query(AuditLogModel).filter(
            and_(
                AuditLogModel.resource_id == str(data_id),
                AuditLogModel.resource_type == resource_type,
                AuditLogModel.operation_type == OperationType.STATE_CHANGE
            )
        ).order_by(AuditLogModel.timestamp.asc()).all()
        
        history = []
        for log in audit_logs:
            # Extract state information from details
            details = log.details or {}
            history.append(StateHistory(
                id=log.id,
                data_id=data_id,
                state=DataState(details.get('new_state', 'raw')),
                user_id=log.user_id,
                transitioned_at=log.timestamp,
                reason=details.get('reason'),
                metadata=details.get('metadata', {})
            ))
        
        return history
    
    def _get_model_class(self, resource_type: ResourceType):
        """Get SQLAlchemy model class for resource type"""
        if resource_type == ResourceType.TEMP_DATA:
            return TempDataModel
        elif resource_type == ResourceType.SAMPLE:
            return SampleModel
        elif resource_type == ResourceType.ANNOTATION_TASK:
            return AnnotationTaskModel
        elif resource_type == ResourceType.ENHANCED_DATA:
            return EnhancedDataModel
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def _record_state_history(
        self,
        data_id: str,
        resource_type: ResourceType,
        previous_state: DataState,
        new_state: DataState,
        context: StateTransitionContext,
        transitioned_at: datetime
    ):
        """Record state transition in audit log"""
        audit_log = AuditLogModel(
            operation_type=OperationType.STATE_CHANGE,
            user_id=context.user_id,
            resource_type=resource_type,
            resource_id=str(data_id),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=0,  # State transitions are fast
            details={
                'previous_state': previous_state.value,
                'new_state': new_state.value,
                'reason': context.reason,
                'metadata': context.metadata
            },
            timestamp=transitioned_at
        )
        self.db.add(audit_log)
