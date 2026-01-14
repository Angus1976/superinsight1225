"""
License Management Module for SuperInsight Platform.

This module provides comprehensive license management functionality including:
- License lifecycle management (create, activate, renew, upgrade, revoke)
- License validation and signature verification
- Concurrent user control
- Time-based validity control
- Resource (CPU, storage) control
- Feature module control
- Remote and offline activation
- Audit logging and reporting
"""

from src.license.license_manager import LicenseManager
from src.license.license_validator import LicenseValidator
from src.license.concurrent_user_controller import ConcurrentUserController
from src.license.time_controller import TimeController
from src.license.resource_controller import ResourceController
from src.license.feature_controller import FeatureController
from src.license.license_audit_logger import LicenseAuditLogger

__all__ = [
    "LicenseManager",
    "LicenseValidator",
    "ConcurrentUserController",
    "TimeController",
    "ResourceController",
    "FeatureController",
    "LicenseAuditLogger",
]
