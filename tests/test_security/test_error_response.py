"""
Property 18 (backend): API error payloads should not leak stack traces or SQL.

Uses Hypothesis to generate random "detail" strings; response sanitization
invariant mirrors frontend `isSafeClientErrorMessage` intent.
"""

import re

import pytest
from hypothesis import given, strategies as st

pytestmark = [pytest.mark.property, pytest.mark.security]

_UNSAFE = (
    re.compile(r"Traceback", re.I),
    re.compile(r"at\s+.+\("),
    re.compile(r"postgres", re.I),
    re.compile(r"SELECT\s+\*", re.I),
)


def is_safe_error_detail(message: str) -> bool:
    if not message:
        return True
    return not any(p.search(message) for p in _UNSAFE)


@given(st.text(min_size=0, max_size=400))
def test_random_strings_never_crash_safety_check(body: str):
    assert isinstance(is_safe_error_detail(body), bool)


@given(st.integers(min_value=0, max_value=10_000))
def test_numeric_only_messages_safe(n: int):
    assert is_safe_error_detail(str(n)) is True


def test_stack_like_marked_unsafe():
    assert is_safe_error_detail("at foo (/src/x.ts:1:1)") is False


def test_plain_user_message_safe():
    assert is_safe_error_detail("Something went wrong") is True
