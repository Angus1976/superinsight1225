"""
Unit tests for permission_defaults configuration module.

Verifies that:
- Default matrices match the original hardcoded values
- JSON config file override works
- Environment variable override for batch_threshold works
- Singleton reset works for test isolation
"""

import json
import os
import tempfile

import pytest

from src.config.permission_defaults import (
    DEFAULT_CRUD_MATRIX,
    DEFAULT_TRANSFER_MATRIX,
    PermissionSettings,
    get_permission_settings,
    reset_permission_settings,
)
from src.services.permission_service import PermissionService, UserRole


class TestDefaultMatricesMatchOriginal:
    """Ensure the externalised defaults are identical to the old hardcoded values."""

    def test_transfer_matrix_has_all_roles(self):
        for role in UserRole:
            assert role.value in DEFAULT_TRANSFER_MATRIX

    def test_crud_matrix_has_all_roles(self):
        for role in UserRole:
            assert role.value in DEFAULT_CRUD_MATRIX

    def test_admin_transfer_all_allowed_no_approval(self):
        admin = DEFAULT_TRANSFER_MATRIX["admin"]
        for op in admin.values():
            assert op["allowed"] is True
            assert op["requires_approval"] is False

    def test_data_manager_cross_project_denied(self):
        entry = DEFAULT_TRANSFER_MATRIX["data_manager"]["cross_project"]
        assert entry["allowed"] is False

    def test_user_crud_read_allowed_no_approval(self):
        entry = DEFAULT_CRUD_MATRIX["user"]["read"]
        assert entry == {"allowed": True, "requires_approval": False}

    def test_user_crud_create_needs_approval(self):
        entry = DEFAULT_CRUD_MATRIX["user"]["create"]
        assert entry == {"allowed": True, "requires_approval": True}


class TestPermissionSettingsDefaults:
    """PermissionSettings loads correct defaults when no env overrides."""

    def setup_method(self):
        reset_permission_settings()

    def teardown_method(self):
        reset_permission_settings()

    def test_default_batch_threshold(self):
        settings = PermissionSettings()
        assert settings.batch_threshold == 1000

    def test_default_transfer_matrix_loaded(self):
        settings = PermissionSettings()
        assert settings.transfer_matrix == DEFAULT_TRANSFER_MATRIX

    def test_default_crud_matrix_loaded(self):
        settings = PermissionSettings()
        assert settings.crud_matrix == DEFAULT_CRUD_MATRIX


class TestPermissionSettingsJsonOverride:
    """PermissionSettings can load matrices from a JSON config file."""

    def setup_method(self):
        reset_permission_settings()

    def teardown_method(self):
        os.environ.pop("PERMISSION_MATRIX_CONFIG_FILE", None)
        reset_permission_settings()

    def test_json_override_transfer_matrix(self):
        custom = {
            "transfer_matrix": {
                "admin": {
                    "temp_stored": {"allowed": True, "requires_approval": True},
                },
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(custom, f)
            f.flush()
            os.environ["PERMISSION_MATRIX_CONFIG_FILE"] = f.name

        try:
            settings = PermissionSettings()
            # transfer_matrix overridden
            assert settings.transfer_matrix["admin"]["temp_stored"]["requires_approval"] is True
            # crud_matrix falls back to default
            assert settings.crud_matrix == DEFAULT_CRUD_MATRIX
        finally:
            os.unlink(f.name)

    def test_invalid_json_falls_back_to_defaults(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("NOT VALID JSON {{{")
            f.flush()
            os.environ["PERMISSION_MATRIX_CONFIG_FILE"] = f.name

        try:
            settings = PermissionSettings()
            assert settings.transfer_matrix == DEFAULT_TRANSFER_MATRIX
        finally:
            os.unlink(f.name)

    def test_missing_file_falls_back_to_defaults(self):
        os.environ["PERMISSION_MATRIX_CONFIG_FILE"] = "/nonexistent/path.json"
        settings = PermissionSettings()
        assert settings.transfer_matrix == DEFAULT_TRANSFER_MATRIX


class TestBatchThresholdEnvOverride:
    """Batch threshold can be overridden via PERMISSION_BATCH_THRESHOLD."""

    def setup_method(self):
        reset_permission_settings()

    def teardown_method(self):
        os.environ.pop("PERMISSION_BATCH_THRESHOLD", None)
        reset_permission_settings()

    def test_custom_batch_threshold(self):
        os.environ["PERMISSION_BATCH_THRESHOLD"] = "500"
        settings = PermissionSettings()
        assert settings.batch_threshold == 500

    def test_custom_threshold_used_by_service(self):
        os.environ["PERMISSION_BATCH_THRESHOLD"] = "500"
        service = PermissionService()
        # 501 records should now trigger batch_transfer check
        result = service.check_permission(
            UserRole.DATA_ANALYST, "temp_stored", record_count=501
        )
        assert result.allowed is False  # DATA_ANALYST can't batch_transfer


class TestSingletonBehavior:
    """get_permission_settings returns a cached singleton."""

    def setup_method(self):
        reset_permission_settings()

    def teardown_method(self):
        reset_permission_settings()

    def test_same_instance_returned(self):
        a = get_permission_settings()
        b = get_permission_settings()
        assert a is b

    def test_reset_clears_singleton(self):
        a = get_permission_settings()
        reset_permission_settings()
        b = get_permission_settings()
        assert a is not b
