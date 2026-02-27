"""
Property-based test for VectorRecord embedding dimension consistency.

Validates that the VectorRecord embedding field is always defined with
dimension 1536, and that generated embedding vectors must match this dimension.

**Validates: Requirements 2.4, 5.5**
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings, strategies as st, HealthCheck

from src.models.structuring import VectorRecord

EXPECTED_DIM = 1536


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Use numpy to generate embedding vectors efficiently instead of st.lists,
# which is too expensive for 1536-element lists.
@st.composite
def embedding_vectors(draw: st.DrawFn) -> np.ndarray:
    """Generate a random 1536-dim float32 vector using a seed."""
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    rng = np.random.RandomState(seed)
    return rng.uniform(-1.0, 1.0, size=EXPECTED_DIM).astype(np.float32)


@st.composite
def wrong_dimension_vectors(draw: st.DrawFn) -> np.ndarray:
    """Generate a random vector with dimension != 1536."""
    dim = draw(
        st.integers(min_value=1, max_value=3000).filter(lambda d: d != EXPECTED_DIM)
    )
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    rng = np.random.RandomState(seed)
    return rng.uniform(-1.0, 1.0, size=dim).astype(np.float32)


# ---------------------------------------------------------------------------
# Property 4: Embedding 维度一致性 (Embedding Dimension Consistency)
# ---------------------------------------------------------------------------


class TestEmbeddingDimensionConsistency:
    """Property 4: Embedding 维度一致性

    For any vector record, its embedding field dimension must always equal 1536.

    **Validates: Requirements 2.4, 5.5**
    """

    def test_vector_record_embedding_column_dimension_is_1536(self) -> None:
        """The VectorRecord model's embedding column must be defined as Vector(1536)."""
        col = VectorRecord.__table__.columns["embedding"]
        assert col.type.dim == EXPECTED_DIM, (
            f"Expected embedding dimension {EXPECTED_DIM}, got {col.type.dim}"
        )

    def test_vector_record_embedding_column_is_not_nullable(self) -> None:
        """The embedding column must be non-nullable to ensure every record has a vector."""
        col = VectorRecord.__table__.columns["embedding"]
        assert not col.nullable, "embedding column must be NOT NULL"

    @given(vec=embedding_vectors())
    @settings(
        max_examples=200,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_generated_embeddings_have_correct_dimension(
        self, vec: np.ndarray
    ) -> None:
        """Any generated embedding vector must have exactly 1536 dimensions,
        matching the VectorRecord schema definition."""
        assert vec.shape == (EXPECTED_DIM,), (
            f"Expected shape ({EXPECTED_DIM},), got {vec.shape}"
        )
        # Cross-check against the model's declared dimension
        col = VectorRecord.__table__.columns["embedding"]
        assert vec.shape[0] == col.type.dim

    @given(vec=wrong_dimension_vectors())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_wrong_dimension_vectors_do_not_match_schema(
        self, vec: np.ndarray
    ) -> None:
        """Vectors with dimension != 1536 must not match the schema dimension."""
        col = VectorRecord.__table__.columns["embedding"]
        assert vec.shape[0] != col.type.dim, (
            f"Vector dimension {vec.shape[0]} should not equal schema dim {col.type.dim}"
        )
