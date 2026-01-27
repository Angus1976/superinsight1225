# Label Studio integration module

from .exceptions import (
    LabelStudioIntegrationError,
    LabelStudioAuthenticationError,
    LabelStudioProjectNotFoundError,
    LabelStudioNetworkError,
)
from .integration import (
    LabelStudioIntegration,
    ProjectConfig,
    ImportResult,
    ExportResult,
    ProjectValidationResult,
    label_studio_integration
)
from .config import (
    LabelStudioConfig,
    LabelStudioProject,
    LabelStudioConfigError,
    label_studio_config
)
from .collaboration import (
    CollaborationManager,
    User,
    UserRole,
    Permission,
    TaskAssignment,
    ProgressStats,
    collaboration_manager
)
from .auth import (
    AuthenticationManager,
    AuthenticationError,
    auth_manager,
    create_demo_users
)
from .retry import (
    LabelStudioRetryConfig,
    LabelStudioRetryExecutor,
    label_studio_retry,
    label_studio_retry_with_circuit_breaker,
    create_label_studio_retry_executor,
    LABEL_STUDIO_RETRYABLE_EXCEPTIONS,
    LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS,
)
from .jwt_auth import (
    JWTAuthManager,
    JWTTokenResponse,
)

__all__ = [
    # Integration
    "LabelStudioIntegration",
    "LabelStudioIntegrationError",
    "LabelStudioAuthenticationError",
    "LabelStudioProjectNotFoundError",
    "LabelStudioNetworkError",
    "ProjectConfig",
    "ImportResult",
    "ExportResult",
    "ProjectValidationResult",
    "label_studio_integration",
    # Config
    "LabelStudioConfig",
    "LabelStudioProject",
    "LabelStudioConfigError",
    "label_studio_config",
    # Collaboration
    "CollaborationManager",
    "User",
    "UserRole", 
    "Permission",
    "TaskAssignment",
    "ProgressStats",
    "collaboration_manager",
    # Auth (SuperInsight user authentication)
    "AuthenticationManager",
    "AuthenticationError",
    "auth_manager",
    "create_demo_users",
    # JWT Auth (Label Studio JWT authentication)
    "JWTAuthManager",
    "JWTTokenResponse",
    # Retry
    "LabelStudioRetryConfig",
    "LabelStudioRetryExecutor",
    "label_studio_retry",
    "label_studio_retry_with_circuit_breaker",
    "create_label_studio_retry_executor",
    "LABEL_STUDIO_RETRYABLE_EXCEPTIONS",
    "LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS",
]