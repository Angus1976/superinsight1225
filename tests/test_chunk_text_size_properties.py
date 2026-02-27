"""
Property-based test for chunk_text() chunk size upper bound.

Validates that for any non-empty text and valid chunk_size parameter,
every chunk returned by chunk_text has a token count <= chunk_size.

**Validates: Requirements 2.3, 4.2**
"""

from __future__ import annotations

import tiktoken
from hypothesis import given, settings, strategies as st, HealthCheck

from src.services.vectorization_pipeline import chunk_text

_enc = tiktoken.get_encoding("cl100k_base")


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_text_strategy = st.text(min_size=1, max_size=2000).filter(
    lambda t: len(_enc.encode(t)) >= 1
)

# chunk_size and overlap must satisfy: size > overlap > 0.
_chunk_params = st.integers(min_value=2, max_value=256).flatmap(
    lambda size: st.tuples(
        st.just(size),
        st.integers(min_value=1, max_value=size - 1),
    )
)


# ---------------------------------------------------------------------------
# Property 2: 分块大小上限 (Chunk Size Upper Bound)
# ---------------------------------------------------------------------------


class TestChunkSizeUpperBound:
    """Property 2: 分块大小上限

    For any non-empty text and valid chunk_size/overlap parameters,
    every chunk returned by chunk_text must have token count <= chunk_size.

    **Validates: Requirements 2.3, 4.2**
    """

    @given(text=_text_strategy, params=_chunk_params)
    @settings(
        max_examples=200,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_every_chunk_within_size_limit(
        self, text: str, params: tuple[int, int]
    ) -> None:
        """Every chunk's token count must be at most chunk_size."""
        size, overlap = params
        chunks = chunk_text(text, size=size, overlap=overlap)

        assert len(chunks) >= 1, "chunk_text must return at least one chunk"

        for i, chunk in enumerate(chunks):
            token_count = len(_enc.encode(chunk))
            assert token_count <= size, (
                f"Chunk {i} has {token_count} tokens, exceeds limit of {size}"
            )
