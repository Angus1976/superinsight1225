"""
Approval Workflow Default Configuration.

Externalizes the approval timeout and related settings from ApprovalService
so they can be overridden via environment variables for production customization.

Environment Variables:
    APPROVAL_TIMEOUT_HOURS: Approval expiry time in hours (default: 168 = 7 days)

Usage:
    from src.config.approval_defaults import get_approval_settings

    settings = get_approval_settings()
    expiry_hours = settings.timeout_hours
"""

from dataclasses import dataclass, field
from typing import Optional

from src.config.settings import get_env_int


# Default: 7 days = 168 hours
DEFAULT_TIMEOUT_HOURS = 168


@dataclass
class ApprovalSettings:
    """
    Approval workflow configuration.

    Loading priority:
    1. APPROVAL_TIMEOUT_HOURS environment variable
    2. Built-in default (168 hours = 7 days)
    """

    timeout_hours: int = field(
        default_factory=lambda: get_env_int(
            "APPROVAL_TIMEOUT_HOURS", DEFAULT_TIMEOUT_HOURS
        )
    )

    @property
    def timeout_days(self) -> float:
        """Return the timeout as fractional days for backward compatibility."""
        return self.timeout_hours / 24.0


# ── Module-level singleton ────────────────────────────────────────────────

_settings: Optional[ApprovalSettings] = None


def get_approval_settings() -> ApprovalSettings:
    """Return the cached ApprovalSettings singleton."""
    global _settings
    if _settings is None:
        _settings = ApprovalSettings()
    return _settings


def reset_approval_settings() -> None:
    """Reset the singleton (useful for testing)."""
    global _settings
    _settings = None
