"""
Property-based tests for Sensitive Data Protection.

Tests Property 12: Sensitive data protection
**Validates: Requirements 8.1, 8.2**

For any data source with password or secret key fields, the stored value in
the database should be encrypted (not plaintext), and any API response should
contain masked values for these fields.
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.sync.connectors.datalake.router import (
    SENSITIVE_CONFIG_KEYS,
    _encrypt_config_secrets,
    _mask_config_secrets,
)
from src.utils.encryption import is_encrypted_data


# ============================================================================
# Strategies
# ============================================================================

# Non-empty plaintext values for sensitive fields.
# Exclude strings composed solely of '*' because the mask function uses '*'
# as its mask character, so such inputs would be identical after masking.
sensitive_value_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip("*") != "")

# Non-sensitive key names (guaranteed not in SENSITIVE_CONFIG_KEYS)
non_sensitive_key_strategy = st.sampled_from(
    ["host", "port", "database", "username", "use_ssl", "cluster"]
)

non_sensitive_value_strategy = st.one_of(
    st.text(min_size=1, max_size=50),
    st.integers(min_value=1, max_value=65535),
    st.booleans(),
)


def config_with_sensitive_fields_strategy():
    """Generate a connection config dict containing at least one sensitive key."""
    return st.fixed_dictionaries(
        {},
        optional={
            key: sensitive_value_strategy for key in SENSITIVE_CONFIG_KEYS
        },
    ).filter(lambda d: len(d) > 0)  # at least one sensitive field


def config_with_mixed_fields_strategy():
    """Generate a config with both sensitive and non-sensitive fields."""
    sensitive_part = st.fixed_dictionaries(
        {"password": sensitive_value_strategy},
        optional={
            key: sensitive_value_strategy
            for key in SENSITIVE_CONFIG_KEYS
            if key != "password"
        },
    )
    non_sensitive_part = st.fixed_dictionaries(
        {"host": st.just("localhost")},
        optional={
            "port": st.integers(min_value=1, max_value=65535),
            "database": st.text(min_size=1, max_size=30),
            "use_ssl": st.booleans(),
        },
    )
    return st.tuples(sensitive_part, non_sensitive_part).map(
        lambda parts: {**parts[0], **parts[1]}
    )


# ============================================================================
# Property Tests
# ============================================================================


class TestEncryptConfigSecrets:
    """**Validates: Requirement 8.1**"""

    @settings(max_examples=100)
    @given(config=config_with_sensitive_fields_strategy())
    def test_sensitive_fields_are_encrypted(self, config):
        """_encrypt_config_secrets produces encrypted values for all sensitive keys.

        **Validates: Requirement 8.1**
        """
        encrypted = _encrypt_config_secrets(config)

        for key in SENSITIVE_CONFIG_KEYS:
            if key in config and config[key]:
                assert is_encrypted_data(encrypted[key]), (
                    f"Field '{key}' should be encrypted but got: {encrypted[key]!r}"
                )

    @settings(max_examples=100)
    @given(config=config_with_sensitive_fields_strategy())
    def test_encrypted_value_differs_from_plaintext(self, config):
        """The encrypted value is never equal to the original plaintext.

        **Validates: Requirement 8.1**
        """
        encrypted = _encrypt_config_secrets(config)

        for key in SENSITIVE_CONFIG_KEYS:
            if key in config and config[key]:
                assert encrypted[key] != config[key], (
                    f"Encrypted value for '{key}' must differ from plaintext"
                )


class TestMaskConfigSecrets:
    """**Validates: Requirement 8.2**"""

    @settings(max_examples=100)
    @given(config=config_with_sensitive_fields_strategy())
    def test_sensitive_fields_are_masked_with_asterisks(self, config):
        """_mask_config_secrets produces masked values containing asterisks.

        **Validates: Requirement 8.2**
        """
        masked = _mask_config_secrets(config)

        for key in SENSITIVE_CONFIG_KEYS:
            if key in config and config[key]:
                assert "*" in masked[key], (
                    f"Masked value for '{key}' should contain asterisks, "
                    f"got: {masked[key]!r}"
                )

    @settings(max_examples=100)
    @given(config=config_with_sensitive_fields_strategy())
    def test_masked_value_differs_from_plaintext(self, config):
        """The masked value is never equal to the original plaintext.

        **Validates: Requirement 8.2**
        """
        masked = _mask_config_secrets(config)

        for key in SENSITIVE_CONFIG_KEYS:
            if key in config and config[key]:
                assert masked[key] != config[key], (
                    f"Masked value for '{key}' must differ from plaintext"
                )


class TestNonSensitiveFieldsUnchanged:
    """**Validates: Requirements 8.1, 8.2**"""

    @settings(max_examples=100)
    @given(config=config_with_mixed_fields_strategy())
    def test_encrypt_preserves_non_sensitive_fields(self, config):
        """Non-sensitive fields are never modified by _encrypt_config_secrets.

        **Validates: Requirements 8.1, 8.2**
        """
        encrypted = _encrypt_config_secrets(config)

        for key, value in config.items():
            if key not in SENSITIVE_CONFIG_KEYS:
                assert encrypted[key] == value, (
                    f"Non-sensitive field '{key}' was modified: "
                    f"{value!r} -> {encrypted[key]!r}"
                )

    @settings(max_examples=100)
    @given(config=config_with_mixed_fields_strategy())
    def test_mask_preserves_non_sensitive_fields(self, config):
        """Non-sensitive fields are never modified by _mask_config_secrets.

        **Validates: Requirements 8.1, 8.2**
        """
        masked = _mask_config_secrets(config)

        for key, value in config.items():
            if key not in SENSITIVE_CONFIG_KEYS:
                assert masked[key] == value, (
                    f"Non-sensitive field '{key}' was modified: "
                    f"{value!r} -> {masked[key]!r}"
                )
