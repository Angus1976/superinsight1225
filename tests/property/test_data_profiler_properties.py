"""
Property-based tests for DataProfiler.

Validates: Requirements 1.1, 1.2, 1.3, 1.4
"""

import asyncio

import pytest
from hypothesis import given, settings, strategies as st

from src.toolkit.interfaces.profiler import DataSource
from src.toolkit.profiling.simple_profiler import SimpleDataProfiler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_async(coro):
    """Run an async coroutine synchronously for Hypothesis tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def valid_data_sources(draw):
    """Generate valid DataSource objects with non-empty content."""
    name = draw(st.sampled_from([
        "data.csv", "report.json", "sheet.xlsx", "notes.txt",
        "doc.pdf", "page.html", "config.xml", "file.parquet",
    ]))
    content = draw(st.binary(min_size=1, max_size=4096))
    return DataSource(name=name, content=content)


@st.composite
def text_data_sources(draw):
    """Generate DataSource objects containing readable text content."""
    name = draw(st.sampled_from(["notes.txt", "report.csv", "data.json"]))
    text = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
        min_size=5,
        max_size=500,
    ).filter(lambda t: any(c.isalpha() for c in t)))
    return DataSource(name=name, content=text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Property 1: Data Profile Completeness
# Validates: Requirements 1.1, 1.2
#
# For any valid DataSource, analyze_data returns a DataProfile with
# non-null basic_info and quality_metrics.
# ---------------------------------------------------------------------------

class TestDataProfileCompleteness:
    """**Validates: Requirements 1.1, 1.2**"""

    @given(source=valid_data_sources())
    @settings(max_examples=50, deadline=5000)
    def test_profile_has_basic_info_and_quality_metrics(self, source: DataSource):
        profiler = SimpleDataProfiler()
        profile = run_async(profiler.analyze_data(source))

        assert profile.basic_info is not None, "basic_info must not be None"
        assert profile.quality_metrics is not None, "quality_metrics must not be None"
        assert profile.basic_info.file_size >= 0
        assert 0.0 <= profile.quality_metrics.completeness_score <= 1.0
        assert 0.0 <= profile.quality_metrics.consistency_score <= 1.0
        assert profile.quality_metrics.anomaly_count >= 0


# ---------------------------------------------------------------------------
# Property 2: Fingerprint Determinism
# Validates: Requirement 1.4
#
# For any DataSource, calling generate_fingerprint twice produces
# identical fingerprints.
# ---------------------------------------------------------------------------

class TestFingerprintDeterminism:
    """**Validates: Requirement 1.4**"""

    @given(source=valid_data_sources())
    @settings(max_examples=50, deadline=5000)
    def test_same_source_produces_identical_fingerprints(self, source: DataSource):
        profiler = SimpleDataProfiler()
        fp1 = run_async(profiler.generate_fingerprint(source))
        fp2 = run_async(profiler.generate_fingerprint(source))

        assert fp1.fingerprint_id == fp2.fingerprint_id, (
            "Fingerprints must be identical for the same data source"
        )
        assert fp1.algorithm == fp2.algorithm


# ---------------------------------------------------------------------------
# Property 3: Semantic Detection for Text
# Validates: Requirement 1.3
#
# For any DataSource with text content, the resulting profile has
# non-null language and domain in semantic_info.
# ---------------------------------------------------------------------------

class TestSemanticDetectionForText:
    """**Validates: Requirement 1.3**"""

    @given(source=text_data_sources())
    @settings(max_examples=50, deadline=5000)
    def test_text_source_has_language_and_domain(self, source: DataSource):
        profiler = SimpleDataProfiler()
        profile = run_async(profiler.analyze_data(source))

        assert profile.semantic_info is not None, "semantic_info must not be None"
        assert profile.semantic_info.language is not None, (
            "language must be detected for text content"
        )
        assert profile.semantic_info.domain is not None, (
            "domain must be detected for text content"
        )
