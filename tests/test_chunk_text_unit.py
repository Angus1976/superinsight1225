"""
Unit tests for chunk_text() in src/services/vectorization_pipeline.py.

Validates token-level chunking with overlap using tiktoken (cl100k_base).
"""

from __future__ import annotations

import pytest
import tiktoken

from src.services.vectorization_pipeline import chunk_text

_enc = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_enc.encode(text))


# ---------------------------------------------------------------------------
# Precondition validation
# ---------------------------------------------------------------------------


class TestPreconditions:
    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="text must be non-empty"):
            chunk_text("")

    def test_overlap_zero_raises(self):
        with pytest.raises(ValueError, match="overlap must be > 0"):
            chunk_text("hello", overlap=0)

    def test_overlap_negative_raises(self):
        with pytest.raises(ValueError, match="overlap must be > 0"):
            chunk_text("hello", overlap=-1)

    def test_size_lte_overlap_raises(self):
        with pytest.raises(ValueError, match="size must be > overlap"):
            chunk_text("hello", size=50, overlap=50)

    def test_size_less_than_overlap_raises(self):
        with pytest.raises(ValueError, match="size must be > overlap"):
            chunk_text("hello", size=30, overlap=50)


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------


class TestBasicBehaviour:
    def test_short_text_returns_single_chunk(self):
        """Text shorter than chunk_size → exactly one chunk."""
        text = "Hello world"
        result = chunk_text(text, size=512, overlap=50)
        assert len(result) == 1
        assert result[0] == text

    def test_each_chunk_within_size_limit(self):
        """Every chunk must have ≤ size tokens."""
        text = "word " * 2000  # ~2000 tokens
        size = 100
        chunks = chunk_text(text, size=size, overlap=20)
        for chunk in chunks:
            assert _token_count(chunk) <= size

    def test_non_empty_text_returns_at_least_one_chunk(self):
        """Requirement 4.3: non-empty input → at least one chunk."""
        result = chunk_text("a", size=512, overlap=50)
        assert len(result) >= 1

    def test_default_parameters(self):
        """Default size=512, overlap=50 should work."""
        text = "token " * 100
        result = chunk_text(text)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Overlap correctness
# ---------------------------------------------------------------------------


class TestOverlap:
    def test_adjacent_chunks_share_overlap_tokens(self):
        """Requirement 4.4: adjacent chunks overlap by exactly `overlap` tokens."""
        text = "word " * 2000
        size = 100
        overlap = 20
        chunks = chunk_text(text, size=size, overlap=overlap)

        assert len(chunks) > 1, "Need multiple chunks to test overlap"

        for i in range(len(chunks) - 1):
            tokens_a = _enc.encode(chunks[i])
            tokens_b = _enc.encode(chunks[i + 1])
            # The last `overlap` tokens of chunk[i] should equal
            # the first `overlap` tokens of chunk[i+1]
            assert tokens_a[-overlap:] == tokens_b[:overlap]


# ---------------------------------------------------------------------------
# Coverage completeness
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_all_tokens_covered(self):
        """Requirement 4.1: all original tokens appear in the chunks."""
        text = "The quick brown fox jumps over the lazy dog. " * 200
        size = 80
        overlap = 15
        chunks = chunk_text(text, size=size, overlap=overlap)

        original_tokens = _enc.encode(text)

        # Reconstruct tokens from chunks accounting for overlap
        reconstructed: list[int] = []
        for i, chunk in enumerate(chunks):
            chunk_tokens = _enc.encode(chunk)
            if i == 0:
                reconstructed.extend(chunk_tokens)
            else:
                # Skip the overlap portion (already in reconstructed)
                reconstructed.extend(chunk_tokens[overlap:])

        assert reconstructed == original_tokens

    def test_single_token_text(self):
        """Edge case: text that encodes to a single token."""
        text = "Hi"
        chunks = chunk_text(text, size=512, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text
