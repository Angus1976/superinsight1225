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
from .workspace_models import (
    LabelStudioWorkspaceModel,
    LabelStudioWorkspaceMemberModel,
    WorkspaceProjectModel,
    ProjectMemberModel,
    WorkspaceMemberRole,
    ProjectMemberRole,
)
from .metadata_codec import (
    MetadataCodec,
    WorkspaceMetadata,
    MetadataCodecError,
    MetadataDecodeError,
    MetadataEncodeError,
    get_metadata_codec,
    encode_metadata,
    decode_metadata,
    has_metadata,
)
from .workspace_service import (
    WorkspaceService,
    WorkspaceInfo,
    MemberInfo,
    WorkspaceServiceError,
    WorkspaceNotFoundError,
    WorkspaceAlreadyExistsError,
    MemberNotFoundError,
    MemberAlreadyExistsError,
    InsufficientPermissionError,
    CannotRemoveOwnerError,
    WorkspaceHasProjectsError,
    get_workspace_service,
)
from .rbac_service import (
    RBACService,
    Permission as RBACPermission,
    ROLE_PERMISSIONS,
    ROLE_HIERARCHY,
    RBACError,
    PermissionDeniedError,
    NotAMemberError,
    get_rbac_service,
)
from .proxy import (
    LabelStudioProxy,
    ProxyResponse,
    ProxyError,
    LabelStudioConnectionError,
    LabelStudioAPIError,
    ProxyPermissionError,
    create_label_studio_proxy,
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
    # Workspace Models
    "LabelStudioWorkspaceModel",
    "LabelStudioWorkspaceMemberModel",
    "WorkspaceProjectModel",
    "ProjectMemberModel",
    "WorkspaceMemberRole",
    "ProjectMemberRole",
    # Metadata Codec
    "MetadataCodec",
    "WorkspaceMetadata",
    "MetadataCodecError",
    "MetadataDecodeError",
    "MetadataEncodeError",
    "get_metadata_codec",
    "encode_metadata",
    "decode_metadata",
    "has_metadata",
    # Workspace Service
    "WorkspaceService",
    "WorkspaceInfo",
    "MemberInfo",
    "WorkspaceServiceError",
    "WorkspaceNotFoundError",
    "WorkspaceAlreadyExistsError",
    "MemberNotFoundError",
    "MemberAlreadyExistsError",
    "InsufficientPermissionError",
    "CannotRemoveOwnerError",
    "WorkspaceHasProjectsError",
    "get_workspace_service",
    # RBAC Service
    "RBACService",
    "RBACPermission",
    "ROLE_PERMISSIONS",
    "ROLE_HIERARCHY",
    "RBACError",
    "PermissionDeniedError",
    "NotAMemberError",
    "get_rbac_service",
    # Label Studio Proxy
    "LabelStudioProxy",
    "ProxyResponse",
    "ProxyError",
    "LabelStudioConnectionError",
    "LabelStudioAPIError",
    "ProxyPermissionError",
    "create_label_studio_proxy",
]