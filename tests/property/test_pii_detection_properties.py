"""
Property-based tests for PII Detection.

**Validates: Requirement 8.2**

WHEN data contains detected PII, THE DataProfiler SHALL flag the
sensitive fields and offer masking options.
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
# Strategies — generate data containing PII patterns
# ---------------------------------------------------------------------------

@st.composite
def email_text(draw):
    """Generate text containing a valid email address."""
    user = draw(st.from_regex(r"[a-z]{3,8}", fullmatch=True))
    domain = draw(st.from_regex(r"[a-z]{3,6}", fullmatch=True))
    tld = draw(st.sampled_from(["com", "org", "net", "io"]))
    filler = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "Z")),
        min_size=0, max_size=50,
    ))
    return f"{filler} {user}@{domain}.{tld} {filler}"


@st.composite
def phone_text(draw):
    """Generate text containing a phone number pattern."""
    area = draw(st.integers(min_value=200, max_value=999))
    mid = draw(st.integers(min_value=100, max_value=999))
    last = draw(st.integers(min_value=1000, max_value=9999))
    sep = draw(st.sampled_from(["-", ".", " "]))
    filler = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "Z")),
        min_size=0, max_size=30,
    ))
    return f"{filler} {area}{sep}{mid}{sep}{last} {filler}"


@st.composite
def ssn_text(draw):
    """Generate text containing an SSN-like pattern (XXX-XX-XXXX)."""
    a = draw(st.integers(min_value=100, max_value=999))
    b = draw(st.integers(min_value=10, max_value=99))
    c = draw(st.integers(min_value=1000, max_value=9999))
    filler = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "Z")),
        min_size=0, max_size=30,
    ))
    return f"{filler} {a}-{b}-{c} {filler}"


@st.composite
def pii_data_source(draw):
    """Generate a DataSource whose text contains at least one PII pattern."""
    pii_text = draw(st.one_of(email_text(), phone_text(), ssn_text()))
    return DataSource(name="data.csv", content=pii_text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Property 13: PII Detection
# Validates: Requirement 8.2
#
# For any DataSource containing PII patterns, analyze_data returns a
# DataProfile with non-empty sensitive_fields in semantic_info.
# ---------------------------------------------------------------------------

class TestPIIDetection:
    """**Validates: Requirement 8.2**"""

    @given(source=pii_data_source())
    @settings(max_examples=50, deadline=5000)
    def test_pii_data_flags_sensitive_fields(self, source: DataSource):
        """Data with PII patterns → profiler flags sensitive_fields as non-empty."""
        profiler = SimpleDataProfiler()
        profile = run_async(profiler.analyze_data(source))

        assert profile.semantic_info is not None, "semantic_info must not be None"
        assert len(profile.semantic_info.sensitive_fields) > 0, (
            f"sensitive_fields should be non-empty for PII data, "
            f"got: {profile.semantic_info.sensitive_fields}"
        )
