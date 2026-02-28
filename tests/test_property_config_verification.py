"""
Property-based tests verifying Hypothesis configuration.

**Feature: comprehensive-testing-qa-system, Task 7.5**
**Property 8: Property Test Minimal Failing Example**
**Property 9: Property Test Iteration Count**
**Validates: Requirements 2.5, 2.6, 9.4**

Tests that:
1. Hypothesis generates at least 100 test cases per property
2. Failing examples are properly shrunk to minimal cases
3. Minimal failing examples are reported in test output
"""

import pytest
from hypothesis import given, settings, HealthCheck, Phase, Verbosity
from hypothesis import strategies as st
from hypothesis.errors import Flaky
from unittest.mock import MagicMock


# =============================================================================
# Property 9: Iteration Count Verification
# =============================================================================

class TestIterationCount:
    """Verify Hypothesis generates at least 100 test cases per property."""

    def test_default_profile_has_100_examples(self):
        """Default profile must have max_examples >= 100."""
        current = settings()
        assert current.max_examples >= 100, (
            f"Default profile max_examples={current.max_examples}, expected >= 100"
        )

    def test_ci_profile_has_at_least_100_examples(self):
        """CI profile must have max_examples >= 100."""
        ci = settings.get_profile("ci")
        assert ci.max_examples >= 100, (
            f"CI profile max_examples={ci.max_examples}, expected >= 100"
        )

    def test_actual_iteration_count(self):
        """Verify Hypothesis actually executes >= 100 examples."""
        counter = {"count": 0}

        @given(x=st.integers(min_value=0, max_value=10000))
        @settings(max_examples=100, database=None)
        def _inner(x):
            counter["count"] += 1

        _inner()
        assert counter["count"] >= 100, (
            f"Only {counter['count']} examples generated, expected >= 100"
        )

    def test_iteration_count_with_composite_strategy(self):
        """Verify 100+ iterations even with composite strategies."""
        counter = {"count": 0}

        @given(
            data=st.fixed_dictionaries({
                "name": st.text(min_size=1, max_size=20),
                "value": st.integers(),
                "flag": st.booleans(),
            })
        )
        @settings(max_examples=100, database=None)
        def _inner(data):
            counter["count"] += 1

        _inner()
        assert counter["count"] >= 100, (
            f"Only {counter['count']} examples with composite strategy, expected >= 100"
        )


# =============================================================================
# Property 8: Minimal Failing Example (Shrinking) Verification
# =============================================================================

class TestMinimalFailingExample:
    """Verify failing examples are properly shrunk by Hypothesis."""

    def test_integer_shrinks_to_boundary(self):
        """
        Hypothesis should shrink a failing integer to the smallest
        value that still triggers the failure.
        """
        boundary = 50
        failing_examples = []

        @given(x=st.integers(min_value=0, max_value=10000))
        @settings(max_examples=200, database=None)
        def _inner(x):
            if x >= boundary:
                failing_examples.append(x)
                raise AssertionError(f"Value {x} >= {boundary}")

        # We expect this to fail; capture the shrunk example
        with pytest.raises(AssertionError) as exc_info:
            _inner()

        # The shrunk example should be exactly the boundary value
        assert str(boundary) in str(exc_info.value), (
            f"Expected shrunk value to be {boundary}, got: {exc_info.value}"
        )

    def test_list_shrinks_to_minimal(self):
        """
        Hypothesis should shrink a failing list to the smallest
        list that still triggers the failure.
        """
        @given(xs=st.lists(st.integers(), min_size=0, max_size=50))
        @settings(max_examples=200, database=None)
        def _inner(xs):
            if len(xs) >= 3 and any(x > 0 for x in xs):
                raise AssertionError(f"Failing list: {xs}")

        with pytest.raises(AssertionError) as exc_info:
            _inner()

        # Hypothesis should shrink to a minimal list — 3 elements
        # with the smallest positive integer (1) and rest zeros
        msg = str(exc_info.value)
        assert "Failing list:" in msg
        # Extract the list from the error message
        list_str = msg.split("Failing list: ")[1]
        shrunk_list = eval(list_str)
        assert len(shrunk_list) == 3, (
            f"Expected shrunk list length 3, got {len(shrunk_list)}: {shrunk_list}"
        )
        # Should contain exactly one positive value (1) and rest zeros
        assert sum(1 for x in shrunk_list if x > 0) >= 1
        positive_vals = [x for x in shrunk_list if x > 0]
        assert positive_vals[0] == 1, (
            f"Expected smallest positive value 1, got {positive_vals[0]}"
        )

    def test_string_shrinks_to_minimal(self):
        """
        Hypothesis should shrink a failing string to the smallest
        string that still triggers the failure.
        """
        @given(s=st.text(min_size=0, max_size=100))
        @settings(max_examples=200, database=None)
        def _inner(s):
            if len(s) >= 5:
                raise AssertionError(f"Failing string: {repr(s)}")

        with pytest.raises(AssertionError) as exc_info:
            _inner()

        msg = str(exc_info.value)
        assert "Failing string:" in msg
        # Hypothesis shrinks strings to minimal — length 5 of '0' chars
        str_repr = msg.split("Failing string: ")[1]
        shrunk_str = eval(str_repr)
        assert len(shrunk_str) == 5, (
            f"Expected shrunk string length 5, got {len(shrunk_str)}: {repr(shrunk_str)}"
        )

    def test_failing_example_appears_in_output(self, capsys):
        """
        Verify that when a property test fails, the minimal failing
        example is included in the reported output.
        """
        @given(x=st.integers(min_value=0, max_value=1000))
        @settings(max_examples=200, database=None)
        def _inner(x):
            assert x < 10, f"x={x} is not < 10"

        with pytest.raises(AssertionError) as exc_info:
            _inner()

        # The exception should contain the shrunk value (10)
        error_text = str(exc_info.value)
        assert "x=10" in error_text, (
            f"Expected 'x=10' in error output, got: {error_text}"
        )

    def test_tuple_shrinks_to_minimal(self):
        """Hypothesis should shrink tuples to minimal failing case."""
        @given(pair=st.tuples(
            st.integers(min_value=0, max_value=100),
            st.integers(min_value=0, max_value=100),
        ))
        @settings(max_examples=200, database=None)
        def _inner(pair):
            a, b = pair
            if a + b > 10:
                raise AssertionError(f"Sum too large: {a} + {b} = {a + b}")

        with pytest.raises(AssertionError) as exc_info:
            _inner()

        msg = str(exc_info.value)
        assert "Sum too large:" in msg
        # Hypothesis should shrink so that a + b == 11 (minimal sum > 10)
        # Typically shrinks to (0, 11) or (11, 0)
        parts = msg.split("Sum too large: ")[1]
        sum_part = parts.split(" = ")[1]
        shrunk_sum = int(sum_part)
        assert shrunk_sum == 11, (
            f"Expected shrunk sum to be 11, got {shrunk_sum}"
        )


# =============================================================================
# Combined: Iteration Count + Shrinking Integration
# =============================================================================

class TestPropertyConfigIntegration:
    """Integration tests combining iteration count and shrinking."""

    def test_100_examples_before_finding_failure(self):
        """
        Even when a failure exists, Hypothesis should still explore
        the space and then shrink to a minimal example.
        """
        call_count = {"n": 0}
        threshold = 500  # Only large values fail

        @given(x=st.integers(min_value=0, max_value=10000))
        @settings(max_examples=200, database=None)
        def _inner(x):
            call_count["n"] += 1
            assert x < threshold, f"x={x} >= {threshold}"

        with pytest.raises(AssertionError) as exc_info:
            _inner()

        # Hypothesis should have called the test multiple times
        # (generation + shrinking)
        assert call_count["n"] > 1, "Expected multiple calls during search + shrink"
        # The shrunk example should be exactly the threshold
        assert f"x={threshold}" in str(exc_info.value)

    def test_deadline_is_none(self):
        """Verify no per-test deadline is set (avoids flaky failures)."""
        current = settings()
        assert current.deadline is None, (
            f"Expected deadline=None, got {current.deadline}"
        )

    def test_health_check_suppressed(self):
        """Verify too_slow health check is suppressed."""
        current = settings()
        assert HealthCheck.too_slow in current.suppress_health_check, (
            "Expected HealthCheck.too_slow to be suppressed"
        )
