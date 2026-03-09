"""
Property-Based Tests for Input Sanitization

Tests Property 34: Input Sanitization

**Validates: Requirements 24.3**

For any user input, malicious content (SQL injection, XSS attempts)
must be sanitized before processing.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.services.security_service import sanitize_input, SanitizationResult


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for arbitrary text that may contain XSS payloads
text_strategy = st.text(min_size=0, max_size=500)

# Strategy for inputs that always contain <script> tags
script_tag_strategy = st.tuples(
    st.text(min_size=0, max_size=100),
    st.text(min_size=0, max_size=100),
    st.text(min_size=0, max_size=100),
).map(lambda t: f"{t[0]}<script>{t[1]}</script>{t[2]}")

# Strategy for inputs that always contain event handlers
event_handler_names = st.sampled_from([
    "onclick", "onerror", "onload", "onmouseover", "onfocus", "onblur",
])
event_handler_strategy = st.tuples(
    st.text(min_size=0, max_size=100),
    event_handler_names,
    st.text(min_size=0, max_size=50),
    st.text(min_size=0, max_size=100),
).map(lambda t: f'{t[0]} {t[1]}="{t[2]}" {t[3]}')

# Strategy for max_length values
max_length_strategy = st.integers(min_value=1, max_value=500)


# ============================================================================
# Property 34: Input Sanitization
# **Validates: Requirements 24.3**
# ============================================================================


@pytest.mark.property
class TestInputSanitization:
    """
    Property 34: Input Sanitization

    Verifies that sanitize_input strips script tags, event handlers,
    respects max_length, always returns a valid SanitizationResult,
    and correctly reports was_modified for clean inputs.
    """

    # ------------------------------------------------------------------ #
    # Sub-property 1: Output never contains <script> tags
    # ------------------------------------------------------------------ #

    @given(input_with_script=script_tag_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_script_tags_always_removed(self, input_with_script: str):
        """
        For any input containing <script> tags, the output never
        contains <script>.

        **Validates: Requirements 24.3**
        """
        result = sanitize_input(input_with_script)

        assert "<script" not in result.value.lower(), (
            f"Output still contains script tag: {result.value!r}"
        )
        assert "</script>" not in result.value.lower(), (
            f"Output still contains closing script tag: {result.value!r}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 2: Output never contains event handlers
    # ------------------------------------------------------------------ #

    @given(input_with_handler=event_handler_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_event_handlers_always_removed(self, input_with_handler: str):
        """
        For any input containing event handlers (onclick=, onerror=, etc.),
        the output never contains them.

        **Validates: Requirements 24.3**
        """
        result = sanitize_input(input_with_handler)

        # The output should not contain any on<event>= pattern
        import re
        assert not re.search(r"\bon\w+=", result.value, re.IGNORECASE), (
            f"Output still contains event handler: {result.value!r}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 3: Output length bounded by max_length
    # ------------------------------------------------------------------ #

    @given(
        value=text_strategy,
        max_length=max_length_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_output_length_bounded(self, value: str, max_length: int):
        """
        For any input, the pre-escape value is truncated to max_length.
        After HTML escaping, the output may be slightly larger due to
        entity encoding (e.g. & -> &amp;), but the pre-escape truncation
        ensures reasonable bounds.

        **Validates: Requirements 24.3**
        """
        result = sanitize_input(value, max_length=max_length)

        # The output length after HTML escaping can exceed max_length
        # because entities like &amp; expand single chars. However,
        # the number of *logical characters* fed into html.escape
        # is at most max_length. We verify a generous upper bound:
        # each char can expand to at most 6 chars (& -> &amp; is 5,
        # but worst case is &#x27; which is 6).
        assert len(result.value) <= max_length * 6, (
            f"Output length {len(result.value)} exceeds "
            f"reasonable bound {max_length * 6}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 4: Always returns valid SanitizationResult
    # ------------------------------------------------------------------ #

    @given(value=text_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_always_returns_valid_result(self, value: str):
        """
        For any input, sanitize_input always returns a SanitizationResult
        with all required fields: value (str), was_modified (bool),
        violations (list).

        **Validates: Requirements 24.3**
        """
        result = sanitize_input(value)

        assert isinstance(result, SanitizationResult), (
            f"Expected SanitizationResult, got {type(result)}"
        )
        assert isinstance(result.value, str), (
            f"Expected value to be str, got {type(result.value)}"
        )
        assert isinstance(result.was_modified, bool), (
            f"Expected was_modified to be bool, got {type(result.was_modified)}"
        )
        assert isinstance(result.violations, list), (
            f"Expected violations to be list, got {type(result.violations)}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 5: Clean input was_modified reflects escaping only
    # ------------------------------------------------------------------ #

    @given(
        value=st.from_regex(r"[a-zA-Z0-9 ]{0,100}", fullmatch=True),
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_clean_input_not_modified(self, value: str):
        """
        For any clean input (no HTML, no scripts, within default length),
        was_modified should be False because there is nothing to strip
        or escape.

        **Validates: Requirements 24.3**
        """
        result = sanitize_input(value)

        # Clean alphanumeric + space input should pass through unchanged
        assert result.was_modified is False, (
            f"Clean input was unexpectedly modified: "
            f"input={value!r}, output={result.value!r}"
        )
        assert result.violations == [], (
            f"Clean input had unexpected violations: {result.violations}"
        )
        assert result.value == value, (
            f"Clean input value changed: {value!r} -> {result.value!r}"
        )
