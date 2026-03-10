"""
Permission Matrix Default Configuration.

Externalizes the permission matrices from PermissionService so they can be
overridden via environment variables or a JSON config file for production
customization.

Usage:
    from src.config.permission_defaults import get_permission_settings

    settings = get_permission_settings()
    transfer_matrix = settings.build_transfer_matrix()
    crud_matrix = settings.build_crud_matrix()
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

from src.config.settings import get_env, get_env_int


# ── Type aliases ──────────────────────────────────────────────────────────
PermissionEntry = Dict[str, bool]  # {"allowed": bool, "requires_approval": bool}
OperationMap = Dict[str, PermissionEntry]
PermissionMatrix = Dict[str, OperationMap]  # role_value -> operation -> entry


# ── Default matrices (match the original hardcoded values) ────────────────

DEFAULT_TRANSFER_MATRIX: PermissionMatrix = {
    "admin": {
        "temp_stored": {"allowed": True, "requires_approval": False},
        "in_sample_library": {"allowed": True, "requires_approval": False},
        "annotation_pending": {"allowed": True, "requires_approval": False},
        "batch_transfer": {"allowed": True, "requires_approval": False},
        "cross_project": {"allowed": True, "requires_approval": False},
    },
    "data_manager": {
        "temp_stored": {"allowed": True, "requires_approval": False},
        "in_sample_library": {"allowed": True, "requires_approval": False},
        "annotation_pending": {"allowed": True, "requires_approval": False},
        "batch_transfer": {"allowed": True, "requires_approval": False},
        "cross_project": {"allowed": False, "requires_approval": False},
    },
    "data_analyst": {
        "temp_stored": {"allowed": True, "requires_approval": False},
        "in_sample_library": {"allowed": True, "requires_approval": True},
        "annotation_pending": {"allowed": True, "requires_approval": True},
        "batch_transfer": {"allowed": False, "requires_approval": False},
        "cross_project": {"allowed": False, "requires_approval": False},
    },
    "user": {
        "temp_stored": {"allowed": True, "requires_approval": False},
        "in_sample_library": {"allowed": True, "requires_approval": True},
        "annotation_pending": {"allowed": True, "requires_approval": True},
        "batch_transfer": {"allowed": False, "requires_approval": False},
        "cross_project": {"allowed": False, "requires_approval": False},
    },
}

DEFAULT_CRUD_MATRIX: PermissionMatrix = {
    "admin": {
        "create": {"allowed": True, "requires_approval": False},
        "read": {"allowed": True, "requires_approval": False},
        "update": {"allowed": True, "requires_approval": False},
        "delete": {"allowed": True, "requires_approval": False},
        "merge": {"allowed": True, "requires_approval": False},
        "split": {"allowed": True, "requires_approval": False},
    },
    "data_manager": {
        "create": {"allowed": True, "requires_approval": False},
        "read": {"allowed": True, "requires_approval": False},
        "update": {"allowed": True, "requires_approval": False},
        "delete": {"allowed": True, "requires_approval": True},
        "merge": {"allowed": True, "requires_approval": False},
        "split": {"allowed": True, "requires_approval": False},
    },
    "data_analyst": {
        "create": {"allowed": True, "requires_approval": False},
        "read": {"allowed": True, "requires_approval": False},
        "update": {"allowed": True, "requires_approval": True},
        "delete": {"allowed": False, "requires_approval": False},
        "merge": {"allowed": False, "requires_approval": False},
        "split": {"allowed": False, "requires_approval": False},
    },
    "user": {
        "create": {"allowed": True, "requires_approval": True},
        "read": {"allowed": True, "requires_approval": False},
        "update": {"allowed": False, "requires_approval": False},
        "delete": {"allowed": False, "requires_approval": False},
        "merge": {"allowed": False, "requires_approval": False},
        "split": {"allowed": False, "requires_approval": False},
    },
}


@dataclass
class PermissionSettings:
    """
    Permission matrix configuration.

    Loading priority:
    1. JSON file pointed to by PERMISSION_MATRIX_CONFIG_FILE env var
    2. Inline env var overrides (PERMISSION_BATCH_THRESHOLD, etc.)
    3. Built-in defaults defined above
    """

    batch_threshold: int = field(
        default_factory=lambda: get_env_int("PERMISSION_BATCH_THRESHOLD", 1000)
    )
    transfer_matrix: PermissionMatrix = field(default_factory=dict)
    crud_matrix: PermissionMatrix = field(default_factory=dict)

    def __post_init__(self) -> None:
        loaded = self._load_from_config_file()
        if not self.transfer_matrix:
            self.transfer_matrix = (
                loaded.get("transfer_matrix", DEFAULT_TRANSFER_MATRIX)
            )
        if not self.crud_matrix:
            self.crud_matrix = (
                loaded.get("crud_matrix", DEFAULT_CRUD_MATRIX)
            )

    # ── Public helpers ────────────────────────────────────────────────────

    def get_transfer_matrix_for_role(self, role_value: str) -> OperationMap:
        """Return the transfer operation map for a given role value."""
        return self.transfer_matrix.get(role_value, {})

    def get_crud_matrix_for_role(self, role_value: str) -> OperationMap:
        """Return the CRUD operation map for a given role value."""
        return self.crud_matrix.get(role_value, {})

    # ── Private ───────────────────────────────────────────────────────────

    @staticmethod
    def _load_from_config_file() -> dict:
        """
        Optionally load matrices from a JSON config file.

        Set PERMISSION_MATRIX_CONFIG_FILE=/path/to/file.json to override.
        The JSON structure should be:
        {
            "transfer_matrix": { ... },
            "crud_matrix": { ... }
        }
        """
        config_path = get_env("PERMISSION_MATRIX_CONFIG_FILE")
        if not config_path or not os.path.isfile(config_path):
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}


# ── Module-level singleton ────────────────────────────────────────────────

_settings: Optional[PermissionSettings] = None


def get_permission_settings() -> PermissionSettings:
    """Return the cached PermissionSettings singleton."""
    global _settings
    if _settings is None:
        _settings = PermissionSettings()
    return _settings


def reset_permission_settings() -> None:
    """Reset the singleton (useful for testing)."""
    global _settings
    _settings = None
