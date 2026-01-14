"""
Data Permission Schemas for SuperInsight Platform.

Pydantic schemas for data permission control API requests and responses.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================================
# Enumerations
# ============================================================================

class DataPermissionAction(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"
    ANNOTATE = "annotate"
    REVIEW = "review"


class ResourceLevel(str, Enum):
    DATASET = "dataset"
    RECORD = "record"
    FIELD = "field"


class PolicySourceType(str, Enum):
    LDAP = "ldap"
    OAUTH = "oauth"
    OIDC = "oidc"
    CUSTOM_JSON = "custom_json"
    CUSTOM_YAML = "custom_yaml"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    TOP_SECRET = "top_secret"


class ClassificationMethod(str, Enum):
    MANUAL = "manual"
    RULE_BASED = "rule_based"
    AI_BASED = "ai_based"


class MaskingAlgorithmType(str, Enum):
    REPLACEMENT = "replacement"
    PARTIAL = "partial"
    ENCRYPTION = "encryption"
    HASH = "hash"
    NULLIFY = "nullify"


class AccessLogOperation(str, Enum):
    READ = "read"
    MODIFY = "modify"
    EXPORT = "export"
    API_CALL = "api_call"


# ============================================================================
# Permission Schemas
# ============================================================================

class PermissionResult(BaseModel):
    """Permission check result."""
    allowed: bool
    reason: Optional[str] = None
    requires_approval: bool = False
    masked_fields: List[str] = Field(default_factory=list)
    conditions_applied: Optional[Dict[str, Any]] = None


class PermissionCheckRequest(BaseModel):
    """Permission check request."""
    user_id: UUID
    resource_type: str
    resource_id: str
    action: DataPermissionAction
    field_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class GrantPermissionRequest(BaseModel):
    """Grant permission request."""
    user_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    resource_level: ResourceLevel
    resource_type: str
    resource_id: str
    field_name: Optional[str] = None
    action: DataPermissionAction
    conditions: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    is_temporary: bool = False


class RevokePermissionRequest(BaseModel):
    """Revoke permission request."""
    user_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    resource_type: str
    resource_id: str
    action: DataPermissionAction
    field_name: Optional[str] = None


class DataPermissionResponse(BaseModel):
    """Data permission response."""
    id: UUID
    tenant_id: str
    resource_level: ResourceLevel
    resource_type: str
    resource_id: str
    field_name: Optional[str] = None
    user_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    action: DataPermissionAction
    conditions: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    granted_by: UUID
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    is_temporary: bool

    class Config:
        from_attributes = True


class TemporaryGrant(BaseModel):
    """Temporary permission grant."""
    permission_id: UUID
    user_id: UUID
    resource: str
    action: str
    granted_at: datetime
    expires_at: datetime


# ============================================================================
# Policy Schemas
# ============================================================================

class LDAPConfig(BaseModel):
    """LDAP connection configuration."""
    url: str
    base_dn: str
    bind_dn: str
    bind_password: str
    user_filter: Optional[str] = "(objectClass=person)"
    group_filter: Optional[str] = "(objectClass=group)"
    attribute_mapping: Dict[str, str] = Field(default_factory=dict)
    use_ssl: bool = True
    timeout: int = 30


class OAuthConfig(BaseModel):
    """OAuth/OIDC configuration."""
    provider_url: str
    client_id: str
    client_secret: str
    scopes: List[str] = Field(default_factory=lambda: ["openid", "profile"])
    claims_mapping: Dict[str, str] = Field(default_factory=dict)
    use_pkce: bool = True


class CustomPolicyConfig(BaseModel):
    """Custom policy configuration."""
    format: str = "json"  # json or yaml
    content: str
    validation_schema: Optional[Dict[str, Any]] = None


class ImportResult(BaseModel):
    """Policy import result."""
    success: bool
    imported_count: int
    updated_count: int = 0
    skipped_count: int = 0
    conflicts: List["PolicyConflict"] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class PolicyConflict(BaseModel):
    """Policy conflict details."""
    id: UUID
    conflict_type: str
    description: str
    existing_policy: Dict[str, Any]
    new_policy: Dict[str, Any]
    suggested_resolution: Optional[str] = None


class ConflictResolution(BaseModel):
    """Conflict resolution request."""
    conflict_id: UUID
    resolution: str  # keep_existing, use_new, merge
    merge_config: Optional[Dict[str, Any]] = None


class SyncSchedule(BaseModel):
    """Sync schedule configuration."""
    source_id: UUID
    cron_expression: str
    enabled: bool = True
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None


class SyncResult(BaseModel):
    """Sync result."""
    success: bool
    source_id: UUID
    synced_at: datetime
    added_count: int = 0
    updated_count: int = 0
    removed_count: int = 0
    errors: List[str] = Field(default_factory=list)


class PolicySourceResponse(BaseModel):
    """Policy source response."""
    id: UUID
    tenant_id: str
    name: str
    description: Optional[str] = None
    source_type: PolicySourceType
    is_active: bool
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Approval Schemas
# ============================================================================

class CreateApprovalRequest(BaseModel):
    """Create approval request."""
    resource: str
    resource_type: str
    action: str
    reason: str
    sensitivity_level: Optional[SensitivityLevel] = None


class ApprovalDecision(BaseModel):
    """Approval decision."""
    decision: str  # approved, rejected
    comments: Optional[str] = None


class ApprovalResult(BaseModel):
    """Approval result."""
    request_id: UUID
    status: ApprovalStatus
    decision: Optional[str] = None
    decided_by: Optional[UUID] = None
    decided_at: Optional[datetime] = None
    comments: Optional[str] = None
    next_approver: Optional[UUID] = None


class ApprovalRequestResponse(BaseModel):
    """Approval request response."""
    id: UUID
    tenant_id: str
    requester_id: UUID
    resource: str
    resource_type: str
    action: str
    reason: str
    sensitivity_level: SensitivityLevel
    status: ApprovalStatus
    current_level: int
    created_at: datetime
    expires_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalActionResponse(BaseModel):
    """Approval action response."""
    id: UUID
    request_id: UUID
    approver_id: UUID
    approval_level: int
    decision: str
    comments: Optional[str] = None
    delegated_from: Optional[UUID] = None
    action_at: datetime

    class Config:
        from_attributes = True


class DelegationRequest(BaseModel):
    """Delegation request."""
    delegate_to: UUID
    start_date: datetime
    end_date: datetime


class DelegationResponse(BaseModel):
    """Delegation response."""
    id: UUID
    delegator_id: UUID
    delegate_id: UUID
    start_date: datetime
    end_date: datetime
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalWorkflowConfig(BaseModel):
    """Approval workflow configuration."""
    name: str
    description: Optional[str] = None
    sensitivity_levels: List[SensitivityLevel]
    approval_levels: List[Dict[str, Any]]
    timeout_hours: int = 72
    auto_approve_conditions: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# Access Log Schemas
# ============================================================================

class AccessContext(BaseModel):
    """Access context information."""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_info: Dict[str, Any] = Field(default_factory=dict)


class AccessLogFilter(BaseModel):
    """Access log filter."""
    user_id: Optional[UUID] = None
    resource: Optional[str] = None
    resource_type: Optional[str] = None
    operation_type: Optional[AccessLogOperation] = None
    sensitivity_level: Optional[SensitivityLevel] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    ip_address: Optional[str] = None
    limit: int = 100
    offset: int = 0


class AccessLogResponse(BaseModel):
    """Access log response."""
    id: UUID
    tenant_id: str
    user_id: UUID
    operation_type: AccessLogOperation
    resource: str
    resource_type: str
    fields_accessed: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None
    record_count: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    sensitivity_level: Optional[SensitivityLevel] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AccessStatistics(BaseModel):
    """Access statistics."""
    total_accesses: int
    by_operation: Dict[str, int]
    by_resource_type: Dict[str, int]
    by_sensitivity: Dict[str, int]
    by_user: Dict[str, int]
    time_range: Dict[str, datetime]


# ============================================================================
# Classification Schemas
# ============================================================================

class ClassificationSchema(BaseModel):
    """Classification schema definition."""
    name: str
    description: Optional[str] = None
    categories: List[Dict[str, Any]]
    rules: Optional[List[Dict[str, Any]]] = None


class ClassificationRule(BaseModel):
    """Classification rule."""
    name: str
    pattern: str  # Regex pattern
    category: str
    sensitivity_level: SensitivityLevel
    priority: int = 0


class ClassificationResult(BaseModel):
    """Classification result."""
    dataset_id: str
    total_fields: int
    classified_count: int
    classifications: List["FieldClassification"]
    errors: List[str] = Field(default_factory=list)


class FieldClassification(BaseModel):
    """Field classification."""
    field_name: str
    category: str
    sensitivity_level: SensitivityLevel
    method: ClassificationMethod
    confidence_score: Optional[float] = None


class ClassificationUpdate(BaseModel):
    """Classification update request."""
    dataset_id: str
    field_name: Optional[str] = None
    category: str
    sensitivity_level: SensitivityLevel


class BatchUpdateResult(BaseModel):
    """Batch update result."""
    success: bool
    updated_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)


class ClassificationReport(BaseModel):
    """Classification report."""
    tenant_id: str
    generated_at: datetime
    total_datasets: int
    total_fields: int
    by_sensitivity: Dict[str, int]
    by_category: Dict[str, int]
    by_method: Dict[str, int]
    unclassified_count: int


class DataClassificationResponse(BaseModel):
    """Data classification response."""
    id: UUID
    tenant_id: str
    dataset_id: str
    field_name: Optional[str] = None
    category: str
    sensitivity_level: SensitivityLevel
    classified_by: ClassificationMethod
    confidence_score: Optional[float] = None
    manually_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Masking Schemas
# ============================================================================

class MaskingRule(BaseModel):
    """Masking rule configuration."""
    name: str
    description: Optional[str] = None
    field_pattern: str
    algorithm: MaskingAlgorithmType
    algorithm_config: Optional[Dict[str, Any]] = None
    applicable_roles: Optional[List[str]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    priority: int = 0


class MaskingRuleResponse(BaseModel):
    """Masking rule response."""
    id: UUID
    tenant_id: str
    name: str
    description: Optional[str] = None
    field_pattern: str
    algorithm: MaskingAlgorithmType
    algorithm_config: Optional[Dict[str, Any]] = None
    applicable_roles: Optional[List[str]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    priority: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ExportConfig(BaseModel):
    """Export configuration for static masking."""
    format: str = "csv"  # csv, json, excel
    include_headers: bool = True
    masking_rules: Optional[List[UUID]] = None  # Specific rules to apply
    exclude_fields: Optional[List[str]] = None


class MaskingPreview(BaseModel):
    """Masking preview result."""
    original_value: str
    masked_value: str
    algorithm: MaskingAlgorithmType
    rule_name: str


# ============================================================================
# Context Permission Schemas
# ============================================================================

class ScenarioType(str, Enum):
    MANAGEMENT = "management"
    ANNOTATION = "annotation"
    QUERY = "query"
    API = "api"


class ScenarioPermission(BaseModel):
    """Scenario-based permission."""
    scenario: ScenarioType
    permissions: List[str]
    conditions: Optional[List[Dict[str, Any]]] = None


class ContextPermissionCheck(BaseModel):
    """Context-aware permission check request."""
    user_id: UUID
    scenario: ScenarioType
    resource: Optional[str] = None
    action: str
    context: Optional[Dict[str, Any]] = None


# Update forward references
ImportResult.model_rebuild()
ClassificationResult.model_rebuild()
