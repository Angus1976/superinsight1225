"""
Property-based test for ProcessingType enum constraint.

Validates that the processing_type field of any processing job must be one of
"structuring", "vectorization", or "semantic".

**Validates: Requirement 5.1**
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from src.models.structuring import ProcessingType, StructuringJob

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PROCESSING_TYPES = {"structuring", "vectorization", "semantic"}


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_arbitrary_string = st.text(min_size=1, max_size=30)


# ---------------------------------------------------------------------------
# Property 6: processing_type 枚举约束
# ---------------------------------------------------------------------------


class TestProcessingTypeEnumConstraint:
    """Property 6: processing_type 枚举约束

    For any processing job, its processing_type field value must be one of
    "structuring", "vectorization", or "semantic".

    **Validates: Requirement 5.1**
    """

    def test_enum_has_exactly_three_members(self) -> None:
        """ProcessingType enum must have exactly 3 members."""
        members = list(ProcessingType)
        assert len(members) == 3, (
            f"Expected 3 members, got {len(members)}: {[m.value for m in members]}"
        )

    def test_enum_values_match_valid_set(self) -> None:
        """All ProcessingType enum values must match the valid set."""
        enum_values = {member.value for member in ProcessingType}
        assert enum_values == VALID_PROCESSING_TYPES, (
            f"Enum values {enum_values} != expected {VALID_PROCESSING_TYPES}"
        )

    def test_structuring_job_default_processing_type(self) -> None:
        """StructuringJob.processing_type default must be 'structuring'."""
        col = StructuringJob.__table__.columns["processing_type"]
        default_value = col.default.arg
        assert default_value == "structuring", (
            f"Default processing_type is {default_value!r}, expected 'structuring'"
        )

    @given(random_string=_arbitrary_string)
    @settings(max_examples=200)
    def test_arbitrary_strings_classified_correctly(
        self, random_string: str
    ) -> None:
        """Any string is either a valid processing_type or not.
        The valid set is exactly {"structuring", "vectorization", "semantic"}."""
        is_valid = random_string in VALID_PROCESSING_TYPES
        try:
            ProcessingType(random_string)
            assert is_valid, (
                f"{random_string!r} was accepted by ProcessingType but is not "
                f"in {VALID_PROCESSING_TYPES}"
            )
        except ValueError:
            assert not is_valid, (
                f"{random_string!r} was rejected by ProcessingType but is "
                f"in {VALID_PROCESSING_TYPES}"
            )

    @given(valid_type=st.sampled_from(list(ProcessingType)))
    @settings(max_examples=50)
    def test_all_enum_values_are_valid_processing_types(
        self, valid_type: ProcessingType
    ) -> None:
        """All ProcessingType enum values must be in the valid set."""
        assert valid_type.value in VALID_PROCESSING_TYPES, (
            f"Enum value {valid_type.value!r} not in {VALID_PROCESSING_TYPES}"
        )
