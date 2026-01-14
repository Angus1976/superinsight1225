"""
License Schemas for SuperInsight Platform.

Pydantic schemas for license management API requests and responses.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================================
# Enumerations
# ============================================================================

class LicenseType(str, Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class SubscriptionType(str, Enum):
    PERPETUAL = "perpetual"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ActivationType(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class ActivationStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ValidityStatus(str, Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    EXPIRED = "expired"


class LicenseEventType(str, Enum):
    CREATED = "created"
    ACTIVATED = "activated"
    RENEWED = "renewed"
    UPGRADED = "upgraded"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    CONCURRENT_CHECK = "concurrent_check"
    RESOURCE_CHECK = "resource_check"
    FEATURE_ACCESS = "feature_access"
    SESSION_CREATED = "session_created"
    SESSION_RELEASED = "session_released"
    SESSION_FORCED_LOGOUT = "session_forced_logout"


# ============================================================================
# License Limits and Validity
# ============================================================================

class LicenseLimits(BaseModel):
    """License limits configuration."""
    max_concurrent_users: int = Field(default=10, ge=1)
    max_cpu_cores: int = Field(default=4, ge=1)
    max_storage_gb: int = Field(default=100, ge=1)
    max_projects: int = Field(default=10, ge=1)
    max_datasets: int = Field(default=100, ge=1)


class LicenseValidity(BaseModel):
    """License validity configuration."""
    start_date: datetime
    end_date: datetime
    subscription_type: SubscriptionType = SubscriptionType.YEARLY
    grace_period_days: int = Field(default=7, ge=0)
    auto_renew: bool = False


# ============================================================================
# License Schemas
# ============================================================================

class CreateLicenseRequest(BaseModel):
    """Create license request."""
    license_type: LicenseType
    features: List[str] = Field(default_factory=list)
    limits: LicenseLimits = Field(default_factory=LicenseLimits)
    validity: LicenseValidity
    metadata: Optional[Dict[str, Any]] = None


class LicenseResponse(BaseModel):
    """License response."""
    id: UUID
    license_key: str
    license_type: LicenseType
    features: List[str]
    limits: LicenseLimits
    validity_start: datetime
    validity_end: datetime
    subscription_type: SubscriptionType
    grace_period_days: int
    auto_renew: bool
    hardware_id: Optional[str] = None
    status: LicenseStatus
    created_at: datetime
    activated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class LicenseStatusResponse(BaseModel):
    """License status response."""
    license_id: UUID
    license_key: str
    license_type: LicenseType
    status: LicenseStatus
    validity_status: ValidityStatus
    days_remaining: Optional[int] = None
    days_until_start: Optional[int] = None
    features: List[str]
    limits: LicenseLimits
    current_usage: Optional["UsageInfo"] = None
    warnings: List[str] = Field(default_factory=list)


class RenewLicenseRequest(BaseModel):
    """Renew license request."""
    new_end_date: datetime
    subscription_type: Optional[SubscriptionType] = None


class UpgradeLicenseRequest(BaseModel):
    """Upgrade license request."""
    new_type: Optional[LicenseType] = None
    new_features: Optional[List[str]] = None
    new_limits: Optional[LicenseLimits] = None


class RevokeLicenseRequest(BaseModel):
    """Revoke license request."""
    reason: str


# ============================================================================
# Activation Schemas
# ============================================================================

class ActivateLicenseRequest(BaseModel):
    """Activate license request."""
    license_key: str
    hardware_fingerprint: Optional[str] = None


class OfflineActivationRequest(BaseModel):
    """Offline activation request."""
    request_code: str
    hardware_fingerprint: str
    license_key: str


class OfflineActivationResponse(BaseModel):
    """Offline activation response."""
    request_code: str
    hardware_fingerprint: str
    license_key: str
    expires_at: datetime


class ActivationResult(BaseModel):
    """Activation result."""
    success: bool
    license: Optional[LicenseResponse] = None
    activation_id: Optional[UUID] = None
    error: Optional[str] = None


class ActivationResponse(BaseModel):
    """Activation response."""
    id: UUID
    license_id: UUID
    hardware_fingerprint: str
    activation_type: ActivationType
    status: ActivationStatus
    activated_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Validation Schemas
# ============================================================================

class ValidationResult(BaseModel):
    """License validation result."""
    valid: bool
    reason: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    license_id: Optional[UUID] = None
    license_type: Optional[LicenseType] = None
    status: Optional[LicenseStatus] = None


# ============================================================================
# Concurrent User Schemas
# ============================================================================

class ConcurrentCheckResult(BaseModel):
    """Concurrent user check result."""
    allowed: bool
    reason: Optional[str] = None
    current: int = 0
    max: int = 0


class UserSession(BaseModel):
    """User session information."""
    id: UUID
    user_id: str
    session_id: str
    priority: int
    login_time: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class RegisterSessionRequest(BaseModel):
    """Register session request."""
    user_id: str
    session_id: str
    priority: int = 0
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ForceLogoutRequest(BaseModel):
    """Force logout request."""
    user_id: str
    reason: str


# ============================================================================
# Resource Schemas
# ============================================================================

class ResourceCheckResult(BaseModel):
    """Resource check result."""
    allowed: bool
    reason: Optional[str] = None
    warning: Optional[str] = None
    current: Optional[int] = None
    max: Optional[int] = None


class ResourceUsage(BaseModel):
    """Resource usage information."""
    cpu_cores: int
    storage_gb: float
    projects_count: int
    datasets_count: int


# ============================================================================
# Feature Schemas
# ============================================================================

class FeatureInfo(BaseModel):
    """Feature information."""
    name: str
    enabled: bool
    description: Optional[str] = None
    requires_upgrade: bool = False
    trial_available: bool = False
    trial_days_remaining: Optional[int] = None


class FeatureAccessResult(BaseModel):
    """Feature access check result."""
    allowed: bool
    feature: str
    reason: Optional[str] = None
    requires_upgrade: bool = False
    upgrade_to: Optional[LicenseType] = None


# ============================================================================
# Usage Schemas
# ============================================================================

class UsageInfo(BaseModel):
    """Current usage information."""
    concurrent_users: int
    max_concurrent_users: int
    cpu_cores: int
    max_cpu_cores: int
    storage_gb: float
    max_storage_gb: int
    projects: int
    max_projects: int
    datasets: int
    max_datasets: int


class ConcurrentUsageInfo(BaseModel):
    """Concurrent usage information."""
    current_users: int
    max_users: int
    utilization_percent: float
    active_sessions: List[UserSession] = Field(default_factory=list)


class ResourceUsageInfo(BaseModel):
    """Resource usage information."""
    cpu_cores: int
    max_cpu_cores: int
    cpu_utilization_percent: float
    storage_gb: float
    max_storage_gb: int
    storage_utilization_percent: float


# ============================================================================
# Report Schemas
# ============================================================================

class UsageReportRequest(BaseModel):
    """Usage report request."""
    start_date: datetime
    end_date: datetime
    include_sessions: bool = True
    include_resources: bool = True
    include_features: bool = True


class LicenseUsageReport(BaseModel):
    """License usage report."""
    license_id: UUID
    license_type: LicenseType
    report_period: Dict[str, datetime]
    concurrent_user_stats: Dict[str, Any]
    resource_usage_stats: Dict[str, Any]
    feature_usage_stats: Dict[str, Any]
    audit_summary: Dict[str, int]
    generated_at: datetime


# ============================================================================
# Audit Schemas
# ============================================================================

class AuditLogFilter(BaseModel):
    """Audit log filter."""
    license_id: Optional[UUID] = None
    event_type: Optional[LicenseEventType] = None
    user_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: Optional[bool] = None
    limit: int = 100
    offset: int = 0


class AuditLogResponse(BaseModel):
    """Audit log response."""
    id: UUID
    license_id: Optional[UUID] = None
    event_type: LicenseEventType
    details: Dict[str, Any]
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Alert Schemas
# ============================================================================

class AlertType(str, Enum):
    EXPIRY_WARNING = "expiry_warning"
    CONCURRENT_LIMIT = "concurrent_limit"
    RESOURCE_LIMIT = "resource_limit"
    LICENSE_VIOLATION = "license_violation"
    ACTIVATION_FAILED = "activation_failed"


class AlertConfig(BaseModel):
    """Alert configuration."""
    alert_type: AlertType
    enabled: bool = True
    threshold: Optional[int] = None
    notification_channels: List[str] = Field(default_factory=lambda: ["email"])
    recipients: List[str] = Field(default_factory=list)


class Alert(BaseModel):
    """Alert information."""
    id: UUID
    alert_type: AlertType
    severity: str
    message: str
    details: Dict[str, Any]
    created_at: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


# Update forward references
LicenseStatusResponse.model_rebuild()
