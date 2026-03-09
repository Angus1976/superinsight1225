"""
Property-Based Tests for Data Validation

Tests Property 29: Data Validation

**Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**

For any data storage or modification operation, the data must pass all
validation rules (UUID format, foreign key references, quality score range,
version number format) or be rejected with descriptive error messages.
"""

import uuid

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.services.data_validator import DataValidator


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for valid UUID strings
valid_uuid_strategy = st.builds(lambda: str(uuid.uuid4()))

# Strategy for non-UUID strings: alphanumeric text that won't accidentally
# be a valid UUID
non_uuid_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=100,
).filter(lambda s: not _is_valid_uuid(s))

# Strategy for quality scores in valid range [0, 1]
valid_quality_score_strategy = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)

# Strategy for quality scores outside valid range
invalid_quality_score_below = st.floats(
    max_value=-0.0001, allow_nan=False, allow_infinity=False,
    min_value=-1e6,
)
invalid_quality_score_above = st.floats(
    min_value=1.0001, allow_nan=False, allow_infinity=False,
    max_value=1e6,
)
invalid_quality_score_strategy = st.one_of(
    invalid_quality_score_below, invalid_quality_score_above
)

# Strategy for valid positive version numbers
valid_version_strategy = st.integers(min_value=1, max_value=10_000)

# Strategy for field names
field_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=30,
)

# Strategy for arbitrary data payloads (always a dict)
data_payload_strategy = st.fixed_dictionaries({}, optional={
    "id": st.one_of(valid_uuid_strategy, st.just("not-a-uuid")),
    "data_id": st.one_of(valid_uuid_strategy, st.just("bad")),
    "version": st.one_of(st.integers(min_value=1, max_value=100), st.just(-1)),
    "quality_overall": st.one_of(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        st.just(5.0),
    ),
    "extra_field": st.text(max_size=20),
})


def _is_valid_uuid(s: str) -> bool:
    """Helper to check if a string is a valid UUID."""
    try:
        uuid.UUID(s)
        return True
    except (ValueError, AttributeError):
        return False


# ============================================================================
# Property 29: Data Validation
# **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
# ============================================================================


@pytest.mark.property
class TestDataValidation:
    """
    Property 29: Data Validation

    Verifies that the DataValidator correctly validates UUID format,
    quality score ranges, version number monotonicity, and always
    returns descriptive error messages for invalid data.
    """

    # ------------------------------------------------------------------ #
    # Sub-property 1: Valid UUIDs always accepted
    # ------------------------------------------------------------------ #

    @given(uuid_str=valid_uuid_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_valid_uuid_always_accepted(self, uuid_str: str):
        """
        For any valid UUID string, validate_uuid always returns True.

        **Validates: Requirements 20.1**
        """
        assert DataValidator.validate_uuid(uuid_str) is True, (
            f"Valid UUID was rejected: {uuid_str!r}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 2: Non-UUID strings always rejected
    # ------------------------------------------------------------------ #

    @given(non_uuid=non_uuid_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_non_uuid_always_rejected(self, non_uuid: str):
        """
        For any non-UUID string, validate_uuid always returns False.

        **Validates: Requirements 20.1**
        """
        assert DataValidator.validate_uuid(non_uuid) is False, (
            f"Non-UUID string was accepted: {non_uuid!r}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 3: Quality scores in [0,1] never raise
    # ------------------------------------------------------------------ #

    @given(score=valid_quality_score_strategy, field=field_name_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_valid_quality_score_never_raises(self, score: float, field: str):
        """
        For any float in [0, 1], validate_quality_score never raises.

        **Validates: Requirements 20.3**
        """
        # Should not raise
        DataValidator.validate_quality_score(score, field)

    # ------------------------------------------------------------------ #
    # Sub-property 4: Quality scores outside [0,1] always raise ValueError
    # ------------------------------------------------------------------ #

    @given(score=invalid_quality_score_strategy, field=field_name_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_invalid_quality_score_always_raises(self, score: float, field: str):
        """
        For any float outside [0, 1], validate_quality_score always raises
        ValueError with a descriptive message.

        **Validates: Requirements 20.3, 20.5**
        """
        with pytest.raises(ValueError) as exc_info:
            DataValidator.validate_quality_score(score, field)

        error_msg = str(exc_info.value)
        assert field in error_msg, (
            f"Error message should include field name '{field}': {error_msg}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 5: Valid version > current_version never raises
    # ------------------------------------------------------------------ #

    @given(
        current=valid_version_strategy,
        delta=st.integers(min_value=1, max_value=100),
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_valid_version_monotonic_never_raises(
        self, current: int, delta: int
    ):
        """
        For any positive integer version > current_version,
        validate_version_number never raises.

        **Validates: Requirements 20.4**
        """
        new_version = current + delta
        # Should not raise
        DataValidator.validate_version_number(new_version, current)

    # ------------------------------------------------------------------ #
    # Sub-property 6: validate_data_payload always returns a list
    # ------------------------------------------------------------------ #

    @given(data=data_payload_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_validate_data_payload_always_returns_list(self, data: dict):
        """
        validate_data_payload always returns a list (never None, never raises).

        **Validates: Requirements 20.2, 20.5**
        """
        result = DataValidator.validate_data_payload(data)

        assert isinstance(result, list), (
            f"Expected list, got {type(result)}: {result!r}"
        )
        for item in result:
            assert isinstance(item, str), (
                f"Each error should be a string, got {type(item)}: {item!r}"
            )
