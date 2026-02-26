"""
Property-based tests for Invalid Type Rejection.

Tests Property 2: Invalid type rejection
**Validates: Requirement 1.3**

For any string that is not a registered connector type,
ConnectorFactory.create() should raise a type error.
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.sync.connectors.base import ConnectorFactory


# ============================================================================
# Constants
# ============================================================================

# Collect all registered types at module level so the strategy can exclude them
REGISTERED_TYPES = set(ConnectorFactory.list_types())


# ============================================================================
# Strategies
# ============================================================================

def unregistered_type_strategy():
    """Strategy that generates strings guaranteed NOT to be registered types.

    Uses text generation with a filter to exclude any string that happens
    to match a registered connector type.
    """
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
        min_size=1,
        max_size=50,
    ).filter(lambda s: s not in REGISTERED_TYPES)


def valid_config_strategy():
    """Strategy that generates plausible config dicts."""
    return st.fixed_dictionaries({
        "host": st.just("localhost"),
        "port": st.just(5432),
        "database": st.just("test"),
        "username": st.just("user"),
        "password": st.just("pass"),
    })


# ============================================================================
# Property 2: Invalid type rejection
# **Validates: Requirement 1.3**
# ============================================================================

class TestInvalidTypeRejection:
    """Property 2: Invalid type rejection."""

    @settings(max_examples=100)
    @given(
        invalid_type=unregistered_type_strategy(),
        config=valid_config_strategy(),
    )
    def test_unregistered_type_raises_value_error(self, invalid_type, config):
        """For any string not in registered types, create() raises ValueError.

        **Validates: Requirement 1.3**
        """
        with pytest.raises(ValueError, match="Unknown connector type"):
            ConnectorFactory.create(invalid_type, config)

    @settings(max_examples=50)
    @given(
        invalid_type=st.from_regex(r"[a-z_]{1,30}", fullmatch=True).filter(
            lambda s: s not in REGISTERED_TYPES
        ),
    )
    def test_plausible_but_invalid_types_rejected(self, invalid_type):
        """Strings that look like valid type names but aren't registered
        should still be rejected.

        **Validates: Requirement 1.3**
        """
        with pytest.raises(ValueError):
            ConnectorFactory.create(invalid_type, {})

    def test_empty_string_rejected(self):
        """Empty string is not a valid connector type.

        **Validates: Requirement 1.3**
        """
        with pytest.raises(ValueError, match="Unknown connector type"):
            ConnectorFactory.create("", {})
