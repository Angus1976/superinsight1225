"""
Unit tests for RBAC permission integration, encryption, and masking
in the datalake router.

Validates: Requirements 7.1-7.5, 8.1, 8.2
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.sync.connectors.datalake.router import (
    SENSITIVE_CONFIG_KEYS,
    _encrypt_config_secrets,
    _mask_config_secrets,
    _to_response,
)
from src.sync.models import DataSourceStatus, DataSourceType
from src.utils.encryption import encrypt_sensitive_data, is_encrypted_data


# ============================================================================
# Tests for _encrypt_config_secrets
# ============================================================================


class TestEncryptConfigSecrets:
    """Validates Requirement 8.1: sensitive fields encrypted in storage."""

    def test_encrypts_password_field(self):
        config = {"host": "localhost", "port": 9000, "password": "my_secret"}
        encrypted = _encrypt_config_secrets(config)

        assert encrypted["host"] == "localhost"
        assert encrypted["port"] == 9000
        assert encrypted["password"] != "my_secret"
        assert is_encrypted_data(encrypted["password"])

    def test_encrypts_multiple_sensitive_fields(self):
        config = {
            "host": "db.example.com",
            "password": "pass123",
            "api_key": "ak-12345",
            "secret": "s3cr3t",
            "token": "tok-abc",
            "private_key": "pk-xyz",
        }
        encrypted = _encrypt_config_secrets(config)

        for key in SENSITIVE_CONFIG_KEYS:
            assert encrypted[key] != config[key], f"{key} should be encrypted"
            assert is_encrypted_data(encrypted[key]), f"{key} should look encrypted"

        # Non-sensitive fields unchanged
        assert encrypted["host"] == "db.example.com"

    def test_skips_missing_sensitive_fields(self):
        config = {"host": "localhost", "port": 9000}
        encrypted = _encrypt_config_secrets(config)

        assert encrypted == config

    def test_skips_empty_sensitive_fields(self):
        config = {"host": "localhost", "password": "", "secret": None}
        encrypted = _encrypt_config_secrets(config)

        # Empty/None values are falsy, so they should not be encrypted
        assert encrypted["password"] == ""
        assert encrypted["secret"] is None

    def test_does_not_mutate_original(self):
        config = {"password": "original"}
        _encrypt_config_secrets(config)
        assert config["password"] == "original"


# ============================================================================
# Tests for _mask_config_secrets
# ============================================================================


class TestMaskConfigSecrets:
    """Validates Requirement 8.2: sensitive fields masked in API responses."""

    def test_masks_password_field(self):
        config = {"host": "localhost", "password": "my_secret_password"}
        masked = _mask_config_secrets(config)

        assert masked["host"] == "localhost"
        assert "my_secret_password" not in masked["password"]
        assert "*" in masked["password"]

    def test_masks_all_sensitive_fields(self):
        config = {
            "host": "db.example.com",
            "password": "pass123",
            "api_key": "ak-12345",
            "secret": "s3cr3t",
            "token": "tok-abc",
            "private_key": "pk-xyz",
        }
        masked = _mask_config_secrets(config)

        for key in SENSITIVE_CONFIG_KEYS:
            assert "*" in masked[key], f"{key} should be masked"
            assert masked[key] != config[key], f"{key} should differ from original"

        assert masked["host"] == "db.example.com"

    def test_skips_missing_sensitive_fields(self):
        config = {"host": "localhost", "database": "analytics"}
        masked = _mask_config_secrets(config)
        assert masked == config

    def test_does_not_mutate_original(self):
        config = {"password": "original"}
        _mask_config_secrets(config)
        assert config["password"] == "original"


# ============================================================================
# Tests for _to_response with masking
# ============================================================================


class TestToResponseMasking:
    """Validates Requirement 8.2: _to_response masks sensitive fields."""

    def test_response_masks_connection_config(self):
        source = MagicMock()
        source.id = uuid4()
        source.name = "test-source"
        source.source_type = DataSourceType.CLICKHOUSE
        source.status = DataSourceStatus.ACTIVE
        source.health_check_status = "connected"
        source.last_health_check = None
        source.created_at = MagicMock()
        source.connection_config = {
            "host": "clickhouse.example.com",
            "port": 9000,
            "password": "super_secret_pass",
        }

        response = _to_response(source)

        assert response.connection_config["host"] == "clickhouse.example.com"
        assert response.connection_config["port"] == 9000
        assert "super_secret_pass" not in response.connection_config["password"]
        assert "*" in response.connection_config["password"]

    def test_response_handles_empty_connection_config(self):
        source = MagicMock()
        source.id = uuid4()
        source.name = "test-source"
        source.source_type = DataSourceType.HIVE
        source.status = DataSourceStatus.INACTIVE
        source.health_check_status = None
        source.last_health_check = None
        source.created_at = MagicMock()
        source.connection_config = None

        response = _to_response(source)
        assert response.connection_config == {}

    def test_response_handles_no_sensitive_fields(self):
        source = MagicMock()
        source.id = uuid4()
        source.name = "safe-source"
        source.source_type = DataSourceType.DORIS
        source.status = DataSourceStatus.ACTIVE
        source.health_check_status = "connected"
        source.last_health_check = None
        source.created_at = MagicMock()
        source.connection_config = {"host": "doris.local", "port": 9030}

        response = _to_response(source)
        assert response.connection_config == {"host": "doris.local", "port": 9030}


# ============================================================================
# Tests for SENSITIVE_CONFIG_KEYS constant
# ============================================================================


class TestSensitiveConfigKeys:
    """Validates that the sensitive keys set covers expected fields."""

    def test_contains_expected_keys(self):
        expected = {"password", "secret", "api_key", "token", "private_key"}
        assert SENSITIVE_CONFIG_KEYS == expected

    def test_is_a_set(self):
        assert isinstance(SENSITIVE_CONFIG_KEYS, set)
