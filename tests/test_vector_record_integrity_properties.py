"""
Property-based test for VectorRecord data integrity.

Validates that VectorRecord's required fields (job_id, chunk_index,
chunk_text, embedding) are all non-nullable, and that the
_store_vector_records function always produces records with all
required fields populated.

**Validates: Requirement 5.3**
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import numpy as np
from hypothesis import given, settings, strategies as st, HealthCheck

from src.models.structuring import VectorRecord, StructuringJob
from src.services.vectorization_pipeline import _store_vector_records

EMBEDDING_DIM = 1536


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def chunk_lists(draw: st.DrawFn) -> list[str]:
    """Generate a non-empty list of non-empty chunk strings."""
    chunks = draw(
        st.lists(
            st.text(min_size=1, max_size=200, alphabet=st.characters(categories=("L", "N", "P", "Z"))),
            min_size=1,
            max_size=10,
        )
    )
    return chunks


@st.composite
def embedding_lists(draw: st.DrawFn, count: int) -> list[list[float]]:
    """Generate *count* embedding vectors of dimension 1536."""
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    rng = np.random.RandomState(seed)
    return [
        rng.uniform(-1.0, 1.0, size=EMBEDDING_DIM).astype(np.float32).tolist()
        for _ in range(count)
    ]


# ---------------------------------------------------------------------------
# Property 8: 向量记录数据完整性 (Vector Record Data Integrity)
# ---------------------------------------------------------------------------


class TestVectorRecordDataIntegrity:
    """Property 8: 向量记录数据完整性

    For any vector record, its job_id, chunk_index, chunk_text, and embedding
    fields must all be non-null values.

    **Validates: Requirement 5.3**
    """

    # --- Schema-level checks ---

    def test_job_id_column_is_not_nullable(self) -> None:
        """The job_id column must be NOT NULL."""
        col = VectorRecord.__table__.columns["job_id"]
        assert not col.nullable, "job_id column must be NOT NULL"

    def test_chunk_index_column_is_not_nullable(self) -> None:
        """The chunk_index column must be NOT NULL."""
        col = VectorRecord.__table__.columns["chunk_index"]
        assert not col.nullable, "chunk_index column must be NOT NULL"

    def test_chunk_text_column_is_not_nullable(self) -> None:
        """The chunk_text column must be NOT NULL."""
        col = VectorRecord.__table__.columns["chunk_text"]
        assert not col.nullable, "chunk_text column must be NOT NULL"

    def test_embedding_column_is_not_nullable(self) -> None:
        """The embedding column must be NOT NULL."""
        col = VectorRecord.__table__.columns["embedding"]
        assert not col.nullable, "embedding column must be NOT NULL"

    # --- _store_vector_records produces complete records ---

    @given(data=st.data())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_store_vector_records_populates_all_required_fields(
        self, data: st.DataObject
    ) -> None:
        """_store_vector_records must create VectorRecord instances where
        job_id, chunk_index, chunk_text, and embedding are all non-None."""
        chunks = data.draw(chunk_lists())
        count = len(chunks)

        seed = data.draw(st.integers(min_value=0, max_value=2**32 - 1))
        rng = np.random.RandomState(seed)
        embeddings = [
            rng.uniform(-1.0, 1.0, size=EMBEDDING_DIM).astype(np.float32).tolist()
            for _ in range(count)
        ]

        # Mock session and job
        added_records: list[VectorRecord] = []
        session = MagicMock()
        session.add = lambda rec: added_records.append(rec)

        job = MagicMock(spec=StructuringJob)
        job.id = uuid4()

        result_count = _store_vector_records(session, job, chunks, embeddings)

        assert result_count == count
        assert len(added_records) == count

        for idx, record in enumerate(added_records):
            assert record.job_id is not None, f"record[{idx}].job_id is None"
            assert record.chunk_index is not None, f"record[{idx}].chunk_index is None"
            assert record.chunk_text is not None, f"record[{idx}].chunk_text is None"
            assert record.embedding is not None, f"record[{idx}].embedding is None"
            # Verify values match inputs
            assert record.job_id == job.id
            assert record.chunk_index == idx
            assert record.chunk_text == chunks[idx]
            assert len(record.embedding) == EMBEDDING_DIM
