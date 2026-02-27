"""
Property-based test for chunk_text() coverage completeness.

Validates that for any non-empty text and valid chunk_size/overlap parameters,
chunk_text returns chunks that cover the entire original text with no content lost.

**Validates: Requirement 4.1**
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


def _expected_chunks(text: str, size: int, overlap: int) -> list[str]:
    """Simulate the sliding-window algorithm to produce expected chunks.

    This mirrors chunk_text's internal logic: encode → slide window → decode.
    If the actual chunks match these, every original token is covered because
    the window step ``size - overlap`` guarantees no gap between windows.
    """
    tokens = _enc.encode(text)
    total = len(tokens)
    if total == 0:
        return [text]

    step = size - overlap
    chunks: list[str] = []
    pos = 0
    while pos < total:
        window = tokens[pos : pos + size]
        chunks.append(_enc.decode(window))
        if pos + size >= total:
            break
        pos += step
    return chunks


# ---------------------------------------------------------------------------
# Property 1: 分块覆盖完整性 (Chunk Coverage Completeness)
# ---------------------------------------------------------------------------


class TestChunkCoverageCompleteness:
    """Property 1: 分块覆盖完整性

    For any non-empty text and valid chunk_size/overlap parameters,
    the chunks returned by chunk_text cover the entire original text —
    no tokens are lost.

    **Validates: Requirement 4.1**
    """

    @given(text=_text_strategy, params=_chunk_params)
    @settings(
        max_examples=200,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_chunks_cover_all_original_tokens(
        self, text: str, params: tuple[int, int]
    ) -> None:
        """The returned chunks must match the expected sliding-window output,
        which guarantees every original token is included in at least one chunk
        (step = size - overlap ensures no gap between consecutive windows)."""
        size, overlap = params
        actual = chunk_text(text, size=size, overlap=overlap)
        expected = _expected_chunks(text, size, overlap)

        assert len(actual) >= 1, "chunk_text must return at least one chunk"
        assert actual == expected, (
            f"Chunk mismatch: expected {len(expected)} chunks, got {len(actual)}"
        )
