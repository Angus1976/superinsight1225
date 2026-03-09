"""
Property-Based Tests for Data Lifecycle State Transitions

Tests Property 2: State Transition Validity
Tests Property 3: State History Completeness

**Validates: Requirements 2.1, 2.2, 2.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    DataState,
    ResourceType,
    TempDataModel,
    OperationType
)
from src.services.data_lifecycle_state_manager import (
    DataStateManager,
    StateTransitionContext,
    STATE_TRANSITIONS
)
from tests.conftest import db_session


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating valid DataState values
data_state_strategy = st.sampled_from(list(DataState))

# Strategy for generating user IDs
user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'),
    min_codepoint=ord('a'),
    max_codepoint=ord('z')
))

# Strategy for generating reasons
reason_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=200)
)

# Strategy for generating metadata
metadata_strategy = st.one_of(
    st.none(),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False))
    )
)


# ============================================================================
# Helper Functions
# ============================================================================

def create_temp_data(db: Session, state: DataState = DataState.TEMP_STORED) -> str:
    """Create a temporary data item for testing"""
    temp_data = TempDataModel(
        id=uuid4(),
        source_document_id=str(uuid4()),
        content={"test": "data"},
        state=state,
        uploaded_by="test_user",
        uploaded_at=datetime.utcnow(),
        metadata={}
    )
    db.add(temp_data)
    db.commit()
    return str(temp_data.id)


def get_valid_transition_pairs():
    """Generate all valid state transition pairs from STATE_TRANSITIONS"""
    pairs = []
    for current_state, next_states in STATE_TRANSITIONS.items():
        for next_state in next_states:
            pairs.append((current_state, next_state))
    return pairs


def get_invalid_transition_pairs():
    """Generate invalid state transition pairs"""
    all_states = list(DataState)
    invalid_pairs = []
    
    for current_state in all_states:
        valid_next = STATE_TRANSITIONS.get(current_state, set())
        for target_state in all_states:
            if target_state not in valid_next:
                invalid_pairs.append((current_state, target_state))
    
    return invalid_pairs


# ============================================================================
# Property 2: State Transition Validity
# **Validates: Requirements 2.1, 2.2**
# ============================================================================

@pytest.mark.property
class TestStateTransitionValidity:
    """
    Property 2: State Transition Validity
    
    For all data items, only valid state transitions according to the state
    machine definition should succeed, and invalid transitions should be
    rejected with valid next state options.
    """
    
    @given(
        user_id=user_id_strategy,
        reason=reason_strategy,
        metadata=metadata_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_valid_transitions_succeed(
        self,
        db_session: Session,
        user_id: str,
        reason: str,
        metadata: dict
    ):
        """
        Property: All valid state transitions should succeed.
        
        For any valid transition pair (current_state, target_state) defined
        in STATE_TRANSITIONS, the transition should succeed.
        """
        # Test a sample of valid transitions
        valid_pairs = get_valid_transition_pairs()
        
        # Pick a random valid transition pair
        if not valid_pairs:
            return
        
        import random
        current_state, target_state = random.choice(valid_pairs)
        
        # Create temp data in the current state
        data_id = create_temp_data(db_session, current_state)
        
        # Create state manager
        manager = DataStateManager(db_session)
        
        # Create transition context
        context = StateTransitionContext(
            user_id=user_id,
            reason=reason,
            metadata=metadata
        )
        
        # Attempt transition
        result = manager.transition_state(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=target_state,
            context=context
        )
        
        # Assert: Valid transition should succeed
        assert result.success, (
            f"Valid transition from {current_state.value} to {target_state.value} "
            f"should succeed. Error: {result.error}"
        )
        assert result.previous_state == current_state
        assert result.current_state == target_state
        assert result.error is None
    
    @given(
        user_id=user_id_strategy,
        reason=reason_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_invalid_transitions_rejected(
        self,
        db_session: Session,
        user_id: str,
        reason: str
    ):
        """
        Property: All invalid state transitions should be rejected.
        
        For any invalid transition pair (current_state, target_state) not
        defined in STATE_TRANSITIONS, the transition should fail and return
        valid next state options.
        """
        # Test a sample of invalid transitions
        invalid_pairs = get_invalid_transition_pairs()
        
        # Pick a random invalid transition pair
        if not invalid_pairs:
            return
        
        import random
        current_state, target_state = random.choice(invalid_pairs)
        
        # Skip if current_state has no valid transitions (terminal state)
        if not STATE_TRANSITIONS.get(current_state):
            return
        
        # Create temp data in the current state
        data_id = create_temp_data(db_session, current_state)
        
        # Create state manager
        manager = DataStateManager(db_session)
        
        # Create transition context
        context = StateTransitionContext(
            user_id=user_id,
            reason=reason
        )
        
        # Attempt invalid transition
        result = manager.transition_state(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=target_state,
            context=context
        )
        
        # Assert: Invalid transition should fail
        assert not result.success, (
            f"Invalid transition from {current_state.value} to {target_state.value} "
            f"should be rejected"
        )
        assert result.error is not None
        assert "Invalid transition" in result.error
        assert "Valid next states" in result.error
        
        # Assert: Error message should include valid next states
        valid_next_states = STATE_TRANSITIONS.get(current_state, set())
        for valid_state in valid_next_states:
            assert valid_state.value in result.error, (
                f"Error message should include valid next state: {valid_state.value}"
            )
    
    def test_validate_transition_correctness(self, db_session: Session):
        """
        Property: validate_transition should correctly identify valid/invalid transitions.
        
        For all state pairs, validate_transition should return True for valid
        transitions and False for invalid transitions.
        """
        manager = DataStateManager(db_session)
        
        # Test all valid transitions
        for current_state, next_states in STATE_TRANSITIONS.items():
            for next_state in next_states:
                assert manager.validate_transition(current_state, next_state), (
                    f"validate_transition should return True for valid transition: "
                    f"{current_state.value} -> {next_state.value}"
                )
        
        # Test all invalid transitions
        all_states = list(DataState)
        for current_state in all_states:
            valid_next = STATE_TRANSITIONS.get(current_state, set())
            for target_state in all_states:
                if target_state not in valid_next:
                    assert not manager.validate_transition(current_state, target_state), (
                        f"validate_transition should return False for invalid transition: "
                        f"{current_state.value} -> {target_state.value}"
                    )
    
    def test_get_valid_next_states_correctness(self, db_session: Session):
        """
        Property: get_valid_next_states should return exactly the states defined in STATE_TRANSITIONS.
        
        For all states, get_valid_next_states should return the same set of
        states as defined in STATE_TRANSITIONS.
        """
        manager = DataStateManager(db_session)
        
        for current_state, expected_next_states in STATE_TRANSITIONS.items():
            actual_next_states = set(manager.get_valid_next_states(current_state))
            assert actual_next_states == expected_next_states, (
                f"get_valid_next_states for {current_state.value} should return "
                f"{[s.value for s in expected_next_states]}, "
                f"but got {[s.value for s in actual_next_states]}"
            )


# ============================================================================
# Property 3: State History Completeness
# **Validates: Requirements 2.3**
# ============================================================================

@pytest.mark.property
class TestStateHistoryCompleteness:
    """
    Property 3: State History Completeness
    
    For all data items, every successful state transition must be recorded
    in the state history with timestamp and user information.
    """
    
    @given(
        user_id=user_id_strategy,
        reason=reason_strategy,
        metadata=metadata_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_successful_transition_recorded_in_history(
        self,
        db_session: Session,
        user_id: str,
        reason: str,
        metadata: dict
    ):
        """
        Property: Every successful state transition is recorded in history.
        
        After a successful state transition, the state history should contain
        a record with the correct state, user ID, timestamp, and metadata.
        """
        # Pick a valid transition
        valid_pairs = get_valid_transition_pairs()
        if not valid_pairs:
            return
        
        import random
        current_state, target_state = random.choice(valid_pairs)
        
        # Create temp data
        data_id = create_temp_data(db_session, current_state)
        
        # Create state manager
        manager = DataStateManager(db_session)
        
        # Get initial history count
        initial_history = manager.get_state_history(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA
        )
        initial_count = len(initial_history)
        
        # Create transition context
        context = StateTransitionContext(
            user_id=user_id,
            reason=reason,
            metadata=metadata
        )
        
        # Perform transition
        before_transition = datetime.utcnow()
        result = manager.transition_state(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=target_state,
            context=context
        )
        after_transition = datetime.utcnow()
        
        # Skip if transition failed
        if not result.success:
            return
        
        # Get updated history
        updated_history = manager.get_state_history(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA
        )
        
        # Assert: History count should increase by 1
        assert len(updated_history) == initial_count + 1, (
            f"State history should have {initial_count + 1} records after transition, "
            f"but has {len(updated_history)}"
        )
        
        # Get the latest history record
        latest_record = updated_history[-1]
        
        # Assert: Latest record should have correct state
        assert latest_record.state == target_state, (
            f"Latest history record should have state {target_state.value}, "
            f"but has {latest_record.state.value}"
        )
        
        # Assert: Latest record should have correct user ID
        assert latest_record.user_id == user_id, (
            f"Latest history record should have user_id {user_id}, "
            f"but has {latest_record.user_id}"
        )
        
        # Assert: Latest record should have timestamp within transition window
        assert before_transition <= latest_record.transitioned_at <= after_transition, (
            f"Latest history record timestamp should be between "
            f"{before_transition} and {after_transition}, "
            f"but is {latest_record.transitioned_at}"
        )
        
        # Assert: Latest record should have correct reason
        assert latest_record.reason == reason, (
            f"Latest history record should have reason {reason}, "
            f"but has {latest_record.reason}"
        )
        
        # Assert: Latest record should have correct metadata
        if metadata:
            assert latest_record.metadata == metadata, (
                f"Latest history record should have metadata {metadata}, "
                f"but has {latest_record.metadata}"
            )
    
    def test_multiple_transitions_all_recorded(self, db_session: Session):
        """
        Property: Multiple state transitions are all recorded in order.
        
        After performing multiple valid state transitions, all transitions
        should be recorded in the state history in chronological order.
        """
        # Create a sequence of valid transitions
        # TEMP_STORED -> UNDER_REVIEW -> APPROVED -> IN_SAMPLE_LIBRARY
        transitions = [
            (DataState.TEMP_STORED, DataState.UNDER_REVIEW),
            (DataState.UNDER_REVIEW, DataState.APPROVED),
            (DataState.APPROVED, DataState.IN_SAMPLE_LIBRARY)
        ]
        
        # Create temp data in initial state
        data_id = create_temp_data(db_session, DataState.TEMP_STORED)
        
        # Create state manager
        manager = DataStateManager(db_session)
        
        # Perform all transitions
        for i, (current_state, target_state) in enumerate(transitions):
            context = StateTransitionContext(
                user_id=f"user_{i}",
                reason=f"transition_{i}"
            )
            
            result = manager.transition_state(
                data_id=data_id,
                resource_type=ResourceType.TEMP_DATA,
                target_state=target_state,
                context=context
            )
            
            assert result.success, f"Transition {i} should succeed"
        
        # Get complete history
        history = manager.get_state_history(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA
        )
        
        # Assert: History should have all transitions
        assert len(history) == len(transitions), (
            f"History should have {len(transitions)} records, "
            f"but has {len(history)}"
        )
        
        # Assert: History should be in chronological order
        for i in range(len(history) - 1):
            assert history[i].transitioned_at <= history[i + 1].transitioned_at, (
                f"History record {i} should be before record {i + 1}"
            )
        
        # Assert: Each transition should be recorded correctly
        for i, (current_state, target_state) in enumerate(transitions):
            assert history[i].state == target_state, (
                f"History record {i} should have state {target_state.value}, "
                f"but has {history[i].state.value}"
            )
            assert history[i].user_id == f"user_{i}", (
                f"History record {i} should have user_id user_{i}, "
                f"but has {history[i].user_id}"
            )
            assert history[i].reason == f"transition_{i}", (
                f"History record {i} should have reason transition_{i}, "
                f"but has {history[i].reason}"
            )
    
    def test_failed_transition_not_recorded(self, db_session: Session):
        """
        Property: Failed state transitions are not recorded in history.
        
        After an invalid state transition attempt, the state history should
        not change.
        """
        # Create temp data
        data_id = create_temp_data(db_session, DataState.TEMP_STORED)
        
        # Create state manager
        manager = DataStateManager(db_session)
        
        # Get initial history
        initial_history = manager.get_state_history(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA
        )
        initial_count = len(initial_history)
        
        # Attempt invalid transition (TEMP_STORED -> ANNOTATED is invalid)
        context = StateTransitionContext(
            user_id="test_user",
            reason="invalid_transition"
        )
        
        result = manager.transition_state(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=DataState.ANNOTATED,
            context=context
        )
        
        # Assert: Transition should fail
        assert not result.success
        
        # Get updated history
        updated_history = manager.get_state_history(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA
        )
        
        # Assert: History count should not change
        assert len(updated_history) == initial_count, (
            f"State history should still have {initial_count} records after failed transition, "
            f"but has {len(updated_history)}"
        )
