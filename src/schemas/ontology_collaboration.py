"""
Pydantic Schemas for Ontology Expert Collaboration

This module defines request/response schemas for the Ontology Expert Collaboration API.
All schemas support i18n through field descriptions and validation error messages.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ============================================
# Enums
# ============================================

class ExpertiseArea(str, Enum):
    """Expertise areas for ontology experts."""
    ENTITY_MODELING = "entity_modeling"
    RELATION_DESIGN = "relation_design"
    ATTRIBUTE_DEFINITION = "attribute_definition"
    VALIDATION_RULES = "validation_rules"
    COMPLIANCE = "compliance"
    INDUSTRY_FINANCE = "industry_finance"
    INDUSTRY_HEALTHCARE = "industry_healthcare"
    INDUSTRY_MANUFACTURING = "industry_manufacturing"
    INDUSTRY_RETAIL = "industry_retail"
    INDUSTRY_TECHNOLOGY = "industry_technology"
    DATA_GOVERNANCE = "data_governance"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class AvailabilityStatus(str, Enum):
    """Expert availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class ChangeType(str, Enum):
    """Types of ontology changes."""
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"
    ROLLBACK = "rollback"


class ChangeRequestStatus(str, Enum):
    """Status of change requests."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalType(str, Enum):
    """Types of approval workflows."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class ApprovalAction(str, Enum):
    """Actions that can be taken on a change request."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class ValidationRegion(str, Enum):
    """Regions for validation rules."""
    CN = "CN"  # Mainland China
    HK = "HK"  # Hong Kong
    TW = "TW"  # Taiwan
    INTL = "INTL"  # International


class Industry(str, Enum):
    """Industry categories."""
    GENERAL = "GENERAL"
    FINANCE = "金融"
    HEALTHCARE = "医疗"
    MANUFACTURING = "制造"
    RETAIL = "零售"
    TECHNOLOGY = "科技"
    EDUCATION = "教育"
    GOVERNMENT = "政府"


class Language(str, Enum):
    """Supported languages for i18n."""
    ZH_CN = "zh-CN"
    EN_US = "en-US"
    ZH_TW = "zh-TW"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"


class ContributionType(str, Enum):
    """Types of knowledge contributions."""
    COMMENT = "comment"
    ENTITY_SUGGESTION = "entity_suggestion"
    RELATION_SUGGESTION = "relation_suggestion"
    DOCUMENT = "document"


class DocumentType(str, Enum):
    """Types of document attachments."""
    PDF = "pdf"
    IMAGE = "image"
    LINK = "link"
    WORD = "word"
    EXCEL = "excel"


class TemplateStatus(str, Enum):
    """Status of ontology templates."""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class SessionStatus(str, Enum):
    """Status of collaboration sessions."""
    ACTIVE = "active"
    CLOSED = "closed"


# ============================================
# Expert Profile Schemas
# ============================================

class ExpertProfileBase(BaseModel):
    """Base schema for expert profile."""
    name: str = Field(..., min_length=1, max_length=200, description="Expert name")
    email: EmailStr = Field(..., description="Expert email address")
    expertise_areas: list[ExpertiseArea] = Field(
        ..., 
        min_length=1,
        description="List of expertise areas"
    )
    certifications: Optional[list[str]] = Field(
        default=None,
        description="List of certifications"
    )
    languages: list[Language] = Field(
        default=[Language.ZH_CN],
        description="Languages the expert can work in"
    )
    availability_status: AvailabilityStatus = Field(
        default=AvailabilityStatus.AVAILABLE,
        description="Current availability status"
    )
    max_concurrent_tasks: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent tasks"
    )


class ExpertProfileCreate(ExpertProfileBase):
    """Schema for creating an expert profile."""
    user_id: UUID = Field(..., description="Associated user ID")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata")


class ExpertProfileUpdate(BaseModel):
    """Schema for updating an expert profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    expertise_areas: Optional[list[ExpertiseArea]] = None
    certifications: Optional[list[str]] = None
    languages: Optional[list[Language]] = None
    availability_status: Optional[AvailabilityStatus] = None
    max_concurrent_tasks: Optional[int] = Field(None, ge=1, le=20)
    metadata: Optional[dict[str, Any]] = None


class ExpertMetrics(BaseModel):
    """Schema for expert contribution metrics."""
    contribution_count: int = Field(default=0, description="Total contributions")
    accepted_count: int = Field(default=0, description="Accepted contributions")
    rejected_count: int = Field(default=0, description="Rejected contributions")
    quality_score: float = Field(default=0.0, ge=0.0, le=5.0, description="Quality score (0-5)")
    acceptance_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Acceptance rate (0-1)")
    contribution_score: float = Field(default=0.0, description="Overall contribution score")
    last_contribution_at: Optional[datetime] = None


class ExpertProfileResponse(ExpertProfileBase):
    """Schema for expert profile response."""
    id: UUID
    user_id: UUID
    tenant_id: UUID
    metrics: ExpertMetrics
    current_task_count: int = 0
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExpertRecommendation(BaseModel):
    """Schema for expert recommendation."""
    expert: ExpertProfileResponse
    match_score: float = Field(..., ge=0.0, le=1.0, description="Expertise match score")
    quality_score: float = Field(..., ge=0.0, le=5.0, description="Quality score")
    availability_score: float = Field(..., ge=0.0, le=1.0, description="Availability score")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall recommendation score")
    recommendation_reason: str = Field(..., description="Reason for recommendation")


# ============================================
# Template Schemas
# ============================================

class EntityTypeSchema(BaseModel):
    """Schema for entity type in template."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    attributes: list[dict[str, Any]] = Field(default_factory=list)
    constraints: Optional[list[dict[str, Any]]] = None


class RelationTypeSchema(BaseModel):
    """Schema for relation type in template."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_entity_type: str
    target_entity_type: str
    cardinality: str = Field(default="many-to-many")
    attributes: list[dict[str, Any]] = Field(default_factory=list)


class TemplateBase(BaseModel):
    """Base schema for ontology template."""
    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    industry: Industry = Field(..., description="Target industry")
    entity_types: list[EntityTypeSchema] = Field(
        default_factory=list,
        description="Entity types in template"
    )
    relation_types: list[RelationTypeSchema] = Field(
        default_factory=list,
        description="Relation types in template"
    )
    validation_rules: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Validation rules"
    )


class TemplateCreate(TemplateBase):
    """Schema for creating a template."""
    parent_template_id: Optional[UUID] = Field(
        None,
        description="Parent template ID for derived templates"
    )
    is_public: bool = Field(default=False, description="Whether template is public")
    metadata: Optional[dict[str, Any]] = None


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    entity_types: Optional[list[EntityTypeSchema]] = None
    relation_types: Optional[list[RelationTypeSchema]] = None
    validation_rules: Optional[list[dict[str, Any]]] = None
    is_public: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class TemplateResponse(TemplateBase):
    """Schema for template response."""
    id: UUID
    tenant_id: UUID
    version: str
    parent_template_id: Optional[UUID] = None
    lineage: list[UUID] = Field(default_factory=list)
    customization_log: list[dict[str, Any]] = Field(default_factory=list)
    usage_count: int = 0
    author_id: Optional[UUID] = None
    status: TemplateStatus
    is_public: bool = False
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateInstantiateRequest(BaseModel):
    """Schema for template instantiation request."""
    ontology_name: str = Field(..., min_length=1, max_length=200)
    customizations: Optional[dict[str, Any]] = Field(
        None,
        description="Customizations to apply during instantiation"
    )


class TemplateExportFormat(str, Enum):
    """Export formats for templates."""
    JSON = "json"
    YAML = "yaml"


class TemplateImportRequest(BaseModel):
    """Schema for template import request."""
    content: str = Field(..., description="Template content (JSON or YAML)")
    format: TemplateExportFormat = Field(default=TemplateExportFormat.JSON)
    name_override: Optional[str] = Field(None, description="Override template name")



# ============================================
# Change Request Schemas
# ============================================

class ChangeRequestBase(BaseModel):
    """Base schema for change request."""
    title: str = Field(..., min_length=1, max_length=500, description="Change request title")
    description: Optional[str] = Field(None, description="Detailed description")
    ontology_area: str = Field(..., description="Affected ontology area")
    change_type: ChangeType = Field(..., description="Type of change")
    target_element_id: Optional[UUID] = Field(None, description="Target element ID")
    target_element_type: Optional[str] = Field(None, description="Target element type")


class ChangeRequestCreate(ChangeRequestBase):
    """Schema for creating a change request."""
    ontology_id: UUID = Field(..., description="Ontology ID")
    before_state: Optional[dict[str, Any]] = Field(None, description="State before change")
    after_state: Optional[dict[str, Any]] = Field(None, description="State after change")
    metadata: Optional[dict[str, Any]] = None


class ChangeRequestUpdate(BaseModel):
    """Schema for updating a change request."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class ChangeRequestSubmit(BaseModel):
    """Schema for submitting a change request."""
    approval_chain_id: Optional[UUID] = Field(
        None,
        description="Approval chain to use (auto-selected if not provided)"
    )


class ImpactReport(BaseModel):
    """Schema for impact analysis report."""
    affected_entities: int = 0
    affected_relations: int = 0
    affected_attributes: int = 0
    affected_projects: int = 0
    impact_level: str = Field(default="LOW", description="MINIMAL/LOW/MEDIUM/HIGH/CRITICAL")
    requires_high_impact_approval: bool = False
    migration_complexity: str = Field(default="LOW", description="LOW/MEDIUM/HIGH")
    estimated_hours: float = 0.0
    breaking_changes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    affected_elements: list[dict[str, Any]] = Field(default_factory=list)


class ChangeRequestResponse(ChangeRequestBase):
    """Schema for change request response."""
    id: UUID
    tenant_id: UUID
    ontology_id: UUID
    requester_id: UUID
    status: ChangeRequestStatus
    current_level: int = 0
    approval_chain_id: Optional[UUID] = None
    deadline: Optional[datetime] = None
    is_escalated: bool = False
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    impact_report: Optional[ImpactReport] = None
    metadata: Optional[dict[str, Any]] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Approval Workflow Schemas
# ============================================

class ApprovalLevelConfig(BaseModel):
    """Schema for approval level configuration."""
    level: int = Field(..., ge=1, le=5, description="Approval level (1-5)")
    approvers: list[UUID] = Field(..., min_length=1, description="Approver IDs")
    min_approvals: int = Field(default=1, ge=1, description="Minimum approvals required")
    deadline_hours: int = Field(default=48, ge=1, description="Deadline in hours")


class ApprovalChainBase(BaseModel):
    """Base schema for approval chain."""
    name: str = Field(..., min_length=1, max_length=200, description="Chain name")
    description: Optional[str] = Field(None, description="Chain description")
    ontology_area: str = Field(..., description="Ontology area this chain applies to")
    approval_type: ApprovalType = Field(
        default=ApprovalType.SEQUENTIAL,
        description="Approval type"
    )
    level_configs: list[ApprovalLevelConfig] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Level configurations"
    )

    @field_validator('level_configs')
    @classmethod
    def validate_levels(cls, v: list[ApprovalLevelConfig]) -> list[ApprovalLevelConfig]:
        """Validate that levels are sequential starting from 1."""
        expected_level = 1
        for config in sorted(v, key=lambda x: x.level):
            if config.level != expected_level:
                raise ValueError(f"Levels must be sequential starting from 1, got {config.level}")
            expected_level += 1
        return v


class ApprovalChainCreate(ApprovalChainBase):
    """Schema for creating an approval chain."""
    is_active: bool = Field(default=True, description="Whether chain is active")
    metadata: Optional[dict[str, Any]] = None


class ApprovalChainUpdate(BaseModel):
    """Schema for updating an approval chain."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    level_configs: Optional[list[ApprovalLevelConfig]] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class ApprovalChainResponse(ApprovalChainBase):
    """Schema for approval chain response."""
    id: UUID
    tenant_id: UUID
    levels: int
    is_active: bool = True
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    """Schema for approval action request."""
    action: ApprovalAction = Field(..., description="Action to take")
    reason: Optional[str] = Field(None, description="Reason for action (required for reject/request_changes)")

    @model_validator(mode='after')
    def validate_reason(self) -> 'ApprovalActionRequest':
        """Validate that reason is provided for reject and request_changes."""
        if self.action in [ApprovalAction.REJECT, ApprovalAction.REQUEST_CHANGES]:
            if not self.reason:
                raise ValueError(f"Reason is required for {self.action.value} action")
        return self


class ApprovalRecordResponse(BaseModel):
    """Schema for approval record response."""
    id: UUID
    change_request_id: UUID
    approver_id: UUID
    level: int
    action: ApprovalAction
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PendingApprovalResponse(BaseModel):
    """Schema for pending approval response."""
    change_request: ChangeRequestResponse
    current_level: int
    deadline: Optional[datetime] = None
    is_escalated: bool = False
    approval_chain: ApprovalChainResponse


# ============================================
# Validation Rule Schemas
# ============================================

class ValidationRuleBase(BaseModel):
    """Base schema for validation rule."""
    name: str = Field(..., min_length=1, max_length=200, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    rule_type: str = Field(..., description="Rule type (format, range, reference, custom)")
    region: ValidationRegion = Field(default=ValidationRegion.INTL, description="Region")
    industry: Industry = Field(default=Industry.GENERAL, description="Industry")
    target_field: Optional[str] = Field(None, description="Target field for validation")
    validation_logic: str = Field(..., description="Validation logic (regex or Python expression)")
    error_message_key: str = Field(..., description="I18n key for error message")
    severity: str = Field(default="error", description="Severity (error, warning, info)")


class ValidationRuleCreate(ValidationRuleBase):
    """Schema for creating a validation rule."""
    is_active: bool = Field(default=True, description="Whether rule is active")
    metadata: Optional[dict[str, Any]] = None


class ValidationRuleResponse(ValidationRuleBase):
    """Schema for validation rule response."""
    id: UUID
    tenant_id: UUID
    is_active: bool = True
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidationRequest(BaseModel):
    """Schema for validation request."""
    entity_type: str = Field(..., description="Entity type to validate")
    data: dict[str, Any] = Field(..., description="Data to validate")
    region: ValidationRegion = Field(default=ValidationRegion.INTL)
    industry: Industry = Field(default=Industry.GENERAL)


class ValidationError(BaseModel):
    """Schema for validation error."""
    field: str
    rule_name: str
    error_message: str
    severity: str
    suggestions: Optional[list[str]] = None


class ValidationResponse(BaseModel):
    """Schema for validation response."""
    is_valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)


# ============================================
# Collaboration Session Schemas
# ============================================

class CollaborationSessionCreate(BaseModel):
    """Schema for creating a collaboration session."""
    ontology_id: UUID = Field(..., description="Ontology ID")
    name: Optional[str] = Field(None, max_length=200, description="Session name")
    metadata: Optional[dict[str, Any]] = None


class CollaborationSessionResponse(BaseModel):
    """Schema for collaboration session response."""
    id: UUID
    tenant_id: UUID
    ontology_id: UUID
    name: Optional[str] = None
    created_by: UUID
    status: SessionStatus
    participants: list[dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ElementLockRequest(BaseModel):
    """Schema for element lock request."""
    element_id: UUID = Field(..., description="Element ID to lock")
    ttl_seconds: int = Field(default=300, ge=60, le=3600, description="Lock TTL in seconds")


class ElementLockResponse(BaseModel):
    """Schema for element lock response."""
    element_id: UUID
    locked_by: UUID
    locked_by_name: str
    locked_at: datetime
    expires_at: datetime


class ConflictResolutionRequest(BaseModel):
    """Schema for conflict resolution request."""
    resolution_strategy: str = Field(
        ...,
        description="Resolution strategy (accept_theirs, accept_mine, manual_merge)"
    )
    merged_content: Optional[dict[str, Any]] = Field(
        None,
        description="Merged content for manual_merge strategy"
    )

    @model_validator(mode='after')
    def validate_merged_content(self) -> 'ConflictResolutionRequest':
        """Validate that merged_content is provided for manual_merge."""
        if self.resolution_strategy == "manual_merge" and not self.merged_content:
            raise ValueError("merged_content is required for manual_merge strategy")
        return self


# ============================================
# I18n Schemas
# ============================================

class TranslationCreate(BaseModel):
    """Schema for creating a translation."""
    element_id: UUID = Field(..., description="Element ID")
    element_type: str = Field(..., description="Element type")
    field_name: str = Field(..., description="Field name")
    language: Language = Field(..., description="Language code")
    translation: str = Field(..., min_length=1, description="Translation text")


class TranslationResponse(BaseModel):
    """Schema for translation response."""
    id: UUID
    element_id: UUID
    element_type: str
    field_name: str
    language: Language
    translation: str
    is_verified: bool = False
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TranslationCoverageResponse(BaseModel):
    """Schema for translation coverage response."""
    ontology_id: UUID
    language: Language
    total_elements: int
    translated_elements: int
    coverage_percentage: float
    missing_elements: list[UUID] = Field(default_factory=list)


# ============================================
# Knowledge Contribution Schemas
# ============================================

class ContributionCreate(BaseModel):
    """Schema for creating a knowledge contribution."""
    ontology_id: UUID = Field(..., description="Ontology ID")
    element_id: Optional[UUID] = Field(None, description="Related element ID")
    contribution_type: ContributionType = Field(..., description="Contribution type")
    parent_id: Optional[UUID] = Field(None, description="Parent contribution ID for threading")
    content: dict[str, Any] = Field(..., description="Contribution content")


class ContributionResponse(BaseModel):
    """Schema for contribution response."""
    id: UUID
    tenant_id: UUID
    ontology_id: UUID
    element_id: Optional[UUID] = None
    expert_id: UUID
    contribution_type: ContributionType
    parent_id: Optional[UUID] = None
    content: dict[str, Any]
    status: str
    quality_score: Optional[float] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentAttachmentCreate(BaseModel):
    """Schema for creating a document attachment."""
    contribution_id: UUID = Field(..., description="Contribution ID")
    document_type: DocumentType = Field(..., description="Document type")
    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    url: Optional[str] = Field(None, description="Document URL")
    file_path: Optional[str] = Field(None, description="File path")

    @model_validator(mode='after')
    def validate_url_or_path(self) -> 'DocumentAttachmentCreate':
        """Validate that URL or file_path is provided."""
        if self.document_type == DocumentType.LINK:
            if not self.url:
                raise ValueError("URL is required for link documents")
        elif not self.url and not self.file_path:
            raise ValueError("Either URL or file_path is required")
        return self


# ============================================
# Pagination Schemas
# ============================================

class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel):
    """Schema for paginated response."""
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
