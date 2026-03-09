"""
Property-Based Tests for Error Message Informativeness

Tests Property 37: Error Message Informativeness

**Validates: Requirements 25.2, 25.6**

For any operation failure (invalid transition, permission denial, validation
failure), the error message must include specific information to help resolve
the issue.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.services.error_handler import (
    DataLifecycleError,
    InvalidStateTransitionError,
    PermissionDeniedError,
    DataValidationError,
    EnhancementJobError,
)


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for non-empty strings (state names, resource IDs, etc.)
non_empty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip())

# Strategy for state names
state_name_strategy = st.sampled_from([
    "raw", "structured", "temp_stored", "under_review",
    "rejected", "approved", "in_sample_library",
    "annotation_pending", "annotating", "annotated",
    "enhancing", "enhanced", "trial_calculation", "archived",
])

# Strategy for valid transition lists (non-empty)
valid_transitions_strategy = st.lists(
    state_name_strategy, min_size=1, max_size=5, unique=True,
)

# Strategy for empty transition lists
empty_transitions_strategy = st.just([])

# Strategy for permission names
permission_strategy = st.sampled_from([
    "view", "edit", "delete", "transfer", "review",
    "annotate", "enhance", "trial", "admin",
])

# Strategy for permission lists
permission_list_strategy = st.lists(
    permission_strategy, min_size=1, max_size=5, unique=True,
)

# Strategy for validation error dicts
validation_error_strategy = st.fixed_dictionaries({
    "field": non_empty_text,
    "message": non_empty_text,
})

validation_errors_list_strategy = st.lists(
    validation_error_strategy, min_size=1, max_size=5,
)

# Strategy for job IDs
job_id_strategy = non_empty_text

# Strategy for enhancement types
enhancement_type_strategy = st.sampled_from([
    "data_augmentation", "quality_improvement",
    "noise_reduction", "feature_extraction", "normalization",
])

# Strategy for retry params (optional)
retry_params_strategy = st.one_of(
    st.none(),
    st.fixed_dictionaries({"batch_size": st.integers(1, 100)}),
)

# Required keys for to_response_dict
REQUIRED_RESPONSE_KEYS = {"error_type", "message", "details", "suggestions", "timestamp"}


# ============================================================================
# Property 37: Error Message Informativeness
# **Validates: Requirements 25.2, 25.6**
# ============================================================================


@pytest.mark.property
class TestErrorMessageInformativeness:
    """
    Property 37: Error Message Informativeness

    Verifies that all error classes produce structured, informative
    responses containing the information needed to resolve the issue.
    """

    # ------------------------------------------------------------------ #
    # Sub-property 1: InvalidStateTransitionError always contains
    #                 valid_transitions in details
    # ------------------------------------------------------------------ #

    @given(
        current=state_name_strategy,
        attempted=state_name_strategy,
        transitions=st.one_of(valid_transitions_strategy, empty_transitions_strategy),
        resource_id=st.one_of(st.none(), non_empty_text),
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_invalid_state_transition_contains_valid_transitions(
        self, current, attempted, transitions, resource_id,
    ):
        """
        For any InvalidStateTransitionError, to_response_dict always
        contains valid_transitions in details.

        **Validates: Requirements 25.2, 25.6**
        """
        error = InvalidStateTransitionError(
            current_state=current,
            attempted_state=attempted,
            valid_transitions=transitions,
            resource_id=resource_id,
        )
        resp = error.to_response_dict()

        assert "valid_transitions" in resp["details"], (
            f"details missing 'valid_transitions': {resp['details']}"
        )
        assert resp["details"]["valid_transitions"] == transitions

    # ------------------------------------------------------------------ #
    # Sub-property 2: PermissionDeniedError always contains
    #                 required_permissions and user_permissions
    # ------------------------------------------------------------------ #

    @given(
        required=permission_list_strategy,
        user_perms=st.one_of(st.just([]), permission_list_strategy),
        resource_id=st.one_of(st.none(), non_empty_text),
        user_id=st.one_of(st.none(), non_empty_text),
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_permission_denied_contains_required_and_user_permissions(
        self, required, user_perms, resource_id, user_id,
    ):
        """
        For any PermissionDeniedError, to_response_dict always contains
        required_permissions and user_permissions in details.

        **Validates: Requirements 25.2, 25.6**
        """
        error = PermissionDeniedError(
            required_permissions=required,
            user_permissions=user_perms,
            resource_id=resource_id,
            user_id=user_id,
        )
        resp = error.to_response_dict()

        assert "required_permissions" in resp["details"], (
            f"details missing 'required_permissions': {resp['details']}"
        )
        assert "user_permissions" in resp["details"], (
            f"details missing 'user_permissions': {resp['details']}"
        )
        assert resp["details"]["required_permissions"] == required
        assert resp["details"]["user_permissions"] == user_perms

    # ------------------------------------------------------------------ #
    # Sub-property 3: All DataLifecycleError subclasses always contain
    #                 all 5 required keys in to_response_dict
    # ------------------------------------------------------------------ #

    @given(
        current=state_name_strategy,
        attempted=state_name_strategy,
        transitions=valid_transitions_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_response_dict_has_all_required_keys_state_transition(
        self, current, attempted, transitions,
    ):
        """
        For any InvalidStateTransitionError, to_response_dict always
        contains all 5 required keys.

        **Validates: Requirements 25.6**
        """
        error = InvalidStateTransitionError(
            current_state=current,
            attempted_state=attempted,
            valid_transitions=transitions,
        )
        resp = error.to_response_dict()
        missing = REQUIRED_RESPONSE_KEYS - set(resp.keys())
        assert not missing, f"Missing keys in response: {missing}"

    @given(
        required=permission_list_strategy,
        user_perms=permission_list_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_response_dict_has_all_required_keys_permission_denied(
        self, required, user_perms,
    ):
        """
        For any PermissionDeniedError, to_response_dict always
        contains all 5 required keys.

        **Validates: Requirements 25.6**
        """
        error = PermissionDeniedError(
            required_permissions=required,
            user_permissions=user_perms,
        )
        resp = error.to_response_dict()
        missing = REQUIRED_RESPONSE_KEYS - set(resp.keys())
        assert not missing, f"Missing keys in response: {missing}"

    @given(errors=validation_errors_list_strategy)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_response_dict_has_all_required_keys_data_validation(
        self, errors,
    ):
        """
        For any DataValidationError, to_response_dict always
        contains all 5 required keys.

        **Validates: Requirements 25.6**
        """
        error = DataValidationError(validation_errors=errors)
        resp = error.to_response_dict()
        missing = REQUIRED_RESPONSE_KEYS - set(resp.keys())
        assert not missing, f"Missing keys in response: {missing}"

    @given(
        job_id=job_id_strategy,
        reason=non_empty_text,
        enhancement_type=st.one_of(st.none(), enhancement_type_strategy),
        retry_params=retry_params_strategy,
        supports_rollback=st.booleans(),
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_response_dict_has_all_required_keys_enhancement_job(
        self, job_id, reason, enhancement_type, retry_params, supports_rollback,
    ):
        """
        For any EnhancementJobError, to_response_dict always
        contains all 5 required keys.

        **Validates: Requirements 25.6**
        """
        error = EnhancementJobError(
            job_id=job_id,
            reason=reason,
            enhancement_type=enhancement_type,
            retry_with_params=retry_params,
            supports_rollback=supports_rollback,
        )
        resp = error.to_response_dict()
        missing = REQUIRED_RESPONSE_KEYS - set(resp.keys())
        assert not missing, f"Missing keys in response: {missing}"

    # ------------------------------------------------------------------ #
    # Sub-property 4: EnhancementJobError suggestions always include
    #                 retry guidance
    # ------------------------------------------------------------------ #

    @given(
        job_id=job_id_strategy,
        reason=non_empty_text,
        enhancement_type=st.one_of(st.none(), enhancement_type_strategy),
        retry_params=retry_params_strategy,
        supports_rollback=st.booleans(),
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_enhancement_job_suggestions_include_retry_guidance(
        self, job_id, reason, enhancement_type, retry_params, supports_rollback,
    ):
        """
        For any EnhancementJobError, suggestions always include retry
        guidance (contains the word 'retry' case-insensitively).

        **Validates: Requirements 25.2, 25.6**
        """
        error = EnhancementJobError(
            job_id=job_id,
            reason=reason,
            enhancement_type=enhancement_type,
            retry_with_params=retry_params,
            supports_rollback=supports_rollback,
        )
        resp = error.to_response_dict()
        suggestions = resp["suggestions"]

        assert len(suggestions) > 0, "EnhancementJobError must have suggestions"
        retry_found = any("retry" in s.lower() for s in suggestions)
        assert retry_found, (
            f"No retry guidance found in suggestions: {suggestions}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 5: Any error with non-empty details always has a
    #                 non-empty message
    # ------------------------------------------------------------------ #

    @given(
        current=state_name_strategy,
        attempted=state_name_strategy,
        transitions=valid_transitions_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_non_empty_details_implies_non_empty_message_state(
        self, current, attempted, transitions,
    ):
        """
        For any InvalidStateTransitionError (always has non-empty details),
        the message is always non-empty.

        **Validates: Requirements 25.6**
        """
        error = InvalidStateTransitionError(
            current_state=current,
            attempted_state=attempted,
            valid_transitions=transitions,
        )
        resp = error.to_response_dict()
        if resp["details"]:
            assert resp["message"], "Non-empty details but empty message"

    @given(
        required=permission_list_strategy,
        user_perms=permission_list_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_non_empty_details_implies_non_empty_message_permission(
        self, required, user_perms,
    ):
        """
        For any PermissionDeniedError (always has non-empty details),
        the message is always non-empty.

        **Validates: Requirements 25.6**
        """
        error = PermissionDeniedError(
            required_permissions=required,
            user_permissions=user_perms,
        )
        resp = error.to_response_dict()
        if resp["details"]:
            assert resp["message"], "Non-empty details but empty message"

    @given(errors=validation_errors_list_strategy)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_non_empty_details_implies_non_empty_message_validation(
        self, errors,
    ):
        """
        For any DataValidationError (always has non-empty details),
        the message is always non-empty.

        **Validates: Requirements 25.6**
        """
        error = DataValidationError(validation_errors=errors)
        resp = error.to_response_dict()
        if resp["details"]:
            assert resp["message"], "Non-empty details but empty message"

    @given(
        job_id=job_id_strategy,
        reason=non_empty_text,
        supports_rollback=st.booleans(),
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_non_empty_details_implies_non_empty_message_enhancement(
        self, job_id, reason, supports_rollback,
    ):
        """
        For any EnhancementJobError (always has non-empty details),
        the message is always non-empty.

        **Validates: Requirements 25.6**
        """
        error = EnhancementJobError(
            job_id=job_id,
            reason=reason,
            supports_rollback=supports_rollback,
        )
        resp = error.to_response_dict()
        if resp["details"]:
            assert resp["message"], "Non-empty details but empty message"
