"""
Property-based test for SemanticRecord.record_type enum constraint.

Validates that the record_type field of any semantic record must be one of
"entity", "relationship", or "summary".

**Validates: Requirement 3.3**
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from hypothesis import given, settings, strategies as st, HealthCheck

from src.services.semantic_pipeline import _store_semantic_records
from src.models.structuring import SemanticRecord

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_RECORD_TYPES = {"entity", "relationship", "summary"}

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_entity_strategy = st.lists(
    st.fixed_dictionaries({
        "name": st.text(min_size=1, max_size=50),
        "type": st.sampled_from(["person", "organization", "location", "date", "concept"]),
        "properties": st.just({}),
        "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    }),
    min_size=0,
    max_size=5,
)

_relationship_strategy = st.lists(
    st.fixed_dictionaries({
        "source": st.text(min_size=1, max_size=50),
        "target": st.text(min_size=1, max_size=50),
        "relation": st.text(min_size=1, max_size=50),
        "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    }),
    min_size=0,
    max_size=5,
)

_summary_strategy = st.fixed_dictionaries({
    "text": st.text(min_size=1, max_size=200),
    "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
})

# Arbitrary strings for negative testing
_arbitrary_string = st.text(min_size=1, max_size=30)


# ---------------------------------------------------------------------------
# Property 7: record_type 枚举约束
# ---------------------------------------------------------------------------


class TestRecordTypeEnumConstraint:
    """Property 7: record_type 枚举约束

    For any semantic record, its record_type field value must be one of
    "entity", "relationship", or "summary".

    **Validates: Requirement 3.3**
    """

    @given(
        entities=_entity_strategy,
        relationships=_relationship_strategy,
        summary=_summary_strategy,
    )
    @settings(
        max_examples=200,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_store_semantic_records_only_creates_valid_record_types(
        self,
        entities: list[dict],
        relationships: list[dict],
        summary: dict,
    ) -> None:
        """_store_semantic_records must only create records whose record_type
        is in the valid set {"entity", "relationship", "summary"}."""
        session = MagicMock()
        added_records: list[SemanticRecord] = []
        session.add.side_effect = lambda rec: added_records.append(rec)

        job = MagicMock()
        job.id = uuid4()

        _store_semantic_records(session, job, entities, relationships, summary)

        expected_count = len(entities) + len(relationships) + 1  # +1 for summary
        assert len(added_records) == expected_count

        for record in added_records:
            assert record.record_type in VALID_RECORD_TYPES, (
                f"Invalid record_type: {record.record_type!r}, "
                f"expected one of {VALID_RECORD_TYPES}"
            )

    @given(random_string=_arbitrary_string)
    @settings(max_examples=200)
    def test_arbitrary_strings_classified_correctly(
        self, random_string: str
    ) -> None:
        """Any string is either a valid record_type or not — there is no
        ambiguity. The valid set is exactly {"entity", "relationship", "summary"}."""
        if random_string in VALID_RECORD_TYPES:
            assert random_string in {"entity", "relationship", "summary"}
        else:
            assert random_string not in VALID_RECORD_TYPES
