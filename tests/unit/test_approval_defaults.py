"""
Unit tests for approval_defaults configuration module.

Tests that approval timeout is configurable via environment variables
and falls back to the correct default value.
"""

import pytest
from unittest.mock import patch, Mock

from src.config.approval_defaults import (
    ApprovalSettings,
    get_approval_settings,
    reset_approval_settings,
    DEFAULT_TIMEOUT_HOURS,
)


@pytest.fixture(autouse=True)
def _reset():
    """Reset the singleton before and after each test."""
    reset_approval_settings()
    yield
    reset_approval_settings()


class TestApprovalSettings:
    """Tests for ApprovalSettings dataclass."""

    def test_default_timeout_hours(self):
        """Default timeout should be 168 hours (7 days)."""
        settings = ApprovalSettings()
        assert settings.timeout_hours == 168

    def test_default_timeout_days_property(self):
        """timeout_days should return 7.0 for the default 168 hours."""
        settings = ApprovalSettings()
        assert settings.timeout_days == 7.0

    def test_custom_timeout_hours(self):
        """Custom timeout_hours should be reflected in timeout_days."""
        settings = ApprovalSettings(timeout_hours=48)
        assert settings.timeout_hours == 48
        assert settings.timeout_days == 2.0

    @patch.dict("os.environ", {"APPROVAL_TIMEOUT_HOURS": "72"})
    def test_env_var_override(self):
        """APPROVAL_TIMEOUT_HOURS env var should override the default."""
        settings = ApprovalSettings()
        assert settings.timeout_hours == 72
        assert settings.timeout_days == 3.0


class TestGetApprovalSettings:
    """Tests for the singleton accessor."""

    def test_returns_settings_instance(self):
        settings = get_approval_settings()
        assert isinstance(settings, ApprovalSettings)

    def test_singleton_returns_same_instance(self):
        a = get_approval_settings()
        b = get_approval_settings()
        assert a is b

    def test_reset_clears_singleton(self):
        a = get_approval_settings()
        reset_approval_settings()
        b = get_approval_settings()
        assert a is not b


class TestApprovalServiceIntegration:
    """Verify ApprovalService picks up the configurable timeout."""

    def test_service_uses_default_timeout(self):
        """ApprovalService.default_expiry_days should match config default."""
        from src.services.approval_service import ApprovalService

        db = Mock()
        service = ApprovalService(db)
        assert service.default_expiry_days == 7.0

    @patch.dict("os.environ", {"APPROVAL_TIMEOUT_HOURS": "48"})
    def test_service_uses_env_timeout(self):
        """ApprovalService should respect APPROVAL_TIMEOUT_HOURS env var."""
        from src.services.approval_service import ApprovalService

        db = Mock()
        service = ApprovalService(db)
        assert service.default_expiry_days == 2.0
