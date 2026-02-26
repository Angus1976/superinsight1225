"""
Unit tests for JobStateMachine in src/models/structuring.py.

Tests the state machine independently from the pipeline, covering
valid/invalid transitions, terminal states, and utility methods.
"""

from __future__ import annotations

import pytest

from src.models.structuring import JobStateMachine, JobStatus


# ---------------------------------------------------------------------------
# is_valid_transition / can_transition
# ---------------------------------------------------------------------------

class TestIsValidTransition:
    """Core transition validation."""

    HAPPY_PATH = [
        (JobStatus.PENDING.value, JobStatus.EXTRACTING.value),
        (JobStatus.EXTRACTING.value, JobStatus.INFERRING.value),
        (JobStatus.INFERRING.value, JobStatus.CONFIRMING.value),
        (JobStatus.CONFIRMING.value, JobStatus.EXTRACTING_ENTITIES.value),
        (JobStatus.EXTRACTING_ENTITIES.value, JobStatus.COMPLETED.value),
    ]

    @pytest.mark.parametrize("src,dst", HAPPY_PATH)
    def test_forward_transitions_are_valid(self, src, dst):
        assert JobStateMachine.is_valid_transition(src, dst) is True

    def test_any_state_can_transition_to_failed(self):
        for status in JobStatus:
            assert JobStateMachine.is_valid_transition(
                status.value, JobStatus.FAILED.value,
            ) is True

    def test_backward_transition_is_invalid(self):
        assert JobStateMachine.is_valid_transition(
            JobStatus.INFERRING.value, JobStatus.EXTRACTING.value,
        ) is False

    def test_skip_transition_is_invalid(self):
        assert JobStateMachine.is_valid_transition(
            JobStatus.PENDING.value, JobStatus.INFERRING.value,
        ) is False

    def test_completed_cannot_go_forward(self):
        assert JobStateMachine.is_valid_transition(
            JobStatus.COMPLETED.value, JobStatus.PENDING.value,
        ) is False

    def test_can_transition_is_alias(self):
        """can_transition delegates to is_valid_transition."""
        for src, dst in self.HAPPY_PATH:
            assert JobStateMachine.can_transition(src, dst) is True
        assert JobStateMachine.can_transition(
            JobStatus.PENDING.value, JobStatus.COMPLETED.value,
        ) is False


# ---------------------------------------------------------------------------
# validate_transition
# ---------------------------------------------------------------------------

class TestValidateTransition:
    """validate_transition raises on illegal moves."""

    def test_valid_transition_does_not_raise(self):
        JobStateMachine.validate_transition(
            JobStatus.PENDING.value, JobStatus.EXTRACTING.value,
        )

    def test_invalid_transition_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid status transition"):
            JobStateMachine.validate_transition(
                JobStatus.PENDING.value, JobStatus.COMPLETED.value,
            )

    def test_transition_to_failed_does_not_raise(self):
        JobStateMachine.validate_transition(
            JobStatus.EXTRACTING.value, JobStatus.FAILED.value,
        )


# ---------------------------------------------------------------------------
# get_next_states
# ---------------------------------------------------------------------------

class TestGetNextStates:
    """Verify reachable states from each status."""

    def test_pending_next_states(self):
        result = JobStateMachine.get_next_states(JobStatus.PENDING.value)
        assert JobStatus.EXTRACTING.value in result
        assert JobStatus.FAILED.value in result
        assert len(result) == 2

    def test_extracting_entities_next_states(self):
        result = JobStateMachine.get_next_states(
            JobStatus.EXTRACTING_ENTITIES.value,
        )
        assert JobStatus.COMPLETED.value in result
        assert JobStatus.FAILED.value in result

    def test_completed_only_failed(self):
        result = JobStateMachine.get_next_states(JobStatus.COMPLETED.value)
        assert result == [JobStatus.FAILED.value]

    def test_failed_has_no_next(self):
        result = JobStateMachine.get_next_states(JobStatus.FAILED.value)
        assert result == []


# ---------------------------------------------------------------------------
# is_terminal
# ---------------------------------------------------------------------------

class TestIsTerminal:
    """Terminal state detection."""

    def test_completed_is_terminal(self):
        assert JobStateMachine.is_terminal(JobStatus.COMPLETED.value) is True

    def test_failed_is_terminal(self):
        assert JobStateMachine.is_terminal(JobStatus.FAILED.value) is True

    def test_pending_is_not_terminal(self):
        assert JobStateMachine.is_terminal(JobStatus.PENDING.value) is False

    def test_extracting_is_not_terminal(self):
        assert JobStateMachine.is_terminal(JobStatus.EXTRACTING.value) is False


# ---------------------------------------------------------------------------
# get_forward_path
# ---------------------------------------------------------------------------

class TestGetForwardPath:
    """Happy-path state sequence."""

    def test_forward_path_order(self):
        path = JobStateMachine.get_forward_path()
        assert path == [
            "pending",
            "extracting",
            "inferring",
            "confirming",
            "extracting_entities",
            "completed",
        ]

    def test_forward_path_length(self):
        assert len(JobStateMachine.get_forward_path()) == 6
