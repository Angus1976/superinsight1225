"""
Admin Configuration Module for SuperInsight Platform.

This module provides administrative configuration management including:
- Credential encryption and masking
- Configuration validation
- History tracking and rollback
- Config management with caching
- SQL builder service
- Sync strategy management
"""

from src.admin.schemas import (
    ConfigType,
    DatabaseType,
    SyncMode,
    LLMType,
    ThirdPartyToolType,
    ValidationResult,
    ValidationError,
    ConnectionTestResult,
    ConfigHistoryResponse,
    ConfigDiff,
)

from src.admin.credential_encryptor import (
    CredentialEncryptor,
    get_credential_encryptor,
    encrypt_credential,
    decrypt_credential,
    mask_credential,
)

from src.admin.config_validator import (
    ConfigValidator,
    get_config_validator,
)

from src.admin.history_tracker import (
    HistoryTracker,
    get_history_tracker,
)

from src.admin.config_manager import (
    ConfigManager,
    get_config_manager,
)

from src.admin.sql_builder import (
    SQLBuilderService,
    get_sql_builder_service,
)

from src.admin.sync_strategy import (
    SyncStrategyService,
    get_sync_strategy_service,
)

__all__ = [
    # Enums
    "ConfigType",
    "DatabaseType",
    "SyncMode",
    "LLMType",
    "ThirdPartyToolType",
    # Results
    "ValidationResult",
    "ValidationError",
    "ConnectionTestResult",
    "ConfigHistoryResponse",
    "ConfigDiff",
    # Credential Encryptor
    "CredentialEncryptor",
    "get_credential_encryptor",
    "encrypt_credential",
    "decrypt_credential",
    "mask_credential",
    # Config Validator
    "ConfigValidator",
    "get_config_validator",
    # History Tracker
    "HistoryTracker",
    "get_history_tracker",
    # Config Manager
    "ConfigManager",
    "get_config_manager",
    # SQL Builder
    "SQLBuilderService",
    "get_sql_builder_service",
    # Sync Strategy
    "SyncStrategyService",
    "get_sync_strategy_service",
]
