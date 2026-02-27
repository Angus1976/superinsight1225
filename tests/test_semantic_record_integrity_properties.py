"""
Property-based test for SemanticRecord data integrity.

Validates that SemanticRecord's required fields (job_id, record_type,
content, confidence) are all non-nullable, and that the
_store_semantic_records function always produces records with all
required fields populated.

**Validates: Requirement 5.4**
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from hypothesis import given, settings, strategies as st, HealthCheck

from src.models.structuring import SemanticRecord, StructuringJob
from src.services.semantic_pipeline import _store_semantic_records

VALID_RECORD_TYPES = {"entity", "relationship", "summary"}


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def entity_lists(draw: st.DrawFn) -> list[dict]:
    """Generate a list of entity dicts with name, type, properties, confidence."""
    return draw(
        st.lists(
            st.fixed_dictionaries({
                "name": st.text(min_size=1, max_size=50),
                "type": st.sampled_from(["person", "organization", "location", "date", "concept"]),
                "properties": st.just({}),
                "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            }),
            min_size=0,
            max_size=5,
        )
    )


@st.composite
def relationship_lists(draw: st.DrawFn) -> list[dict]:
    """Generate a list of relationship dicts with source, target, relation, confidence."""
    return draw(
        st.lists(
            st.fixed_dictionaries({
                "source": st.text(min_size=1, max_size=50),
                "target": st.text(min_size=1, max_size=50),
                "relation": st.text(min_size=1, max_size=50),
                "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            }),
            min_size=0,
            max_size=5,
        )
    )


@st.composite
def summary_dicts(draw: st.DrawFn) -> dict:
    """Generate a summary dict with text and confidence."""
    return draw(
        st.fixed_dictionaries({
            "text": st.text(min_size=1, max_size=200),
            "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        })
    )


# ---------------------------------------------------------------------------
# Property 9: 语义记录数据完整性 (Semantic Record Data Integrity)
# ---------------------------------------------------------------------------


class TestSemanticRecordDataIntegrity:
    """Property 9: 语义记录数据完整性

    For any semantic record, its job_id, record_type, content, and confidence
    fields must all be non-null values.

    **Validates: Requirement 5.4**
    """

    # --- Schema-level checks ---

    def test_job_id_column_is_not_nullable(self) -> None:
        col = SemanticRecord.__table__.columns["job_id"]
        assert not col.nullable, "job_id column must be NOT NULL"

    def test_record_type_column_is_not_nullable(self) -> None:
        col = SemanticRecord.__table__.columns["record_type"]
        assert not col.nullable, "record_type column must be NOT NULL"

    def test_content_column_is_not_nullable(self) -> None:
        col = SemanticRecord.__table__.columns["content"]
        assert not col.nullable, "content column must be NOT NULL"

    def test_confidence_column_is_not_nullable(self) -> None:
        col = SemanticRecord.__table__.columns["confidence"]
        assert not col.nullable, "confidence column must be NOT NULL"

    # --- _store_semantic_records produces complete records ---

    @given(data=st.data())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_store_semantic_records_populates_all_required_fields(
        self, data: st.DataObject
    ) -> None:
        """_store_semantic_records must create SemanticRecord instances where
        job_id, record_type, content, and confidence are all non-None."""
        entities = data.draw(entity_lists())
        relationships = data.draw(relationship_lists())
        summary = data.draw(summary_dicts())

        added_records: list[SemanticRecord] = []
        session = MagicMock()
        session.add = lambda rec: added_records.append(rec)

        job = MagicMock(spec=StructuringJob)
        job.id = uuid4()

        expected_count = len(entities) + len(relationships) + 1  # +1 for summary
        result_count = _store_semantic_records(session, job, entities, relationships, summary)

        assert result_count == expected_count
        assert len(added_records) == expected_count

        for idx, record in enumerate(added_records):
            assert record.job_id is not None, f"record[{idx}].job_id is None"
            assert record.record_type is not None, f"record[{idx}].record_type is None"
            assert record.content is not None, f"record[{idx}].content is None"
            assert record.confidence is not None, f"record[{idx}].confidence is None"
            # record_type must be valid
            assert record.record_type in VALID_RECORD_TYPES, (
                f"record[{idx}].record_type={record.record_type!r} not in {VALID_RECORD_TYPES}"
            )
            # job_id must match
            assert record.job_id == job.id
