"""
SQLAlchemy ORM models for SuperInsight Platform database tables.

These models define the database schema using SQLAlchemy ORM.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List

from src.database.connection import Base
from src.config.settings import settings
from src.database.json_types import get_json_type


def get_uuid_type():
    """Get appropriate UUID type based on database backend"""
    if settings.database.database_url.startswith('sqlite'):
        return String(36)  # SQLite uses string for UUID
    else:
        return UUID(as_uuid=True)  # PostgreSQL uses UUID type


def get_uuid_default():
    """Get appropriate UUID default based on database backend"""
    if settings.database.database_url.startswith('sqlite'):
        return lambda: str(uuid4())  # SQLite needs string UUID
    else:
        return uuid4  # PostgreSQL can use UUID directly


class TaskStatus(str, enum.Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AnnotationType(str, enum.Enum):
    """Annotation type enumeration."""
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"
    QA = "qa"
    CUSTOM = "custom"


class IssueSeverity(str, enum.Enum):
    """Quality issue severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, enum.Enum):
    """Quality issue status enumeration."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SyncStatus(str, enum.Enum):
    """Document sync status enumeration."""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"


class LabelStudioSyncStatus(str, enum.Enum):
    """Label Studio synchronization status enumeration."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


class DocumentModel(Base):
    """
    Document table for storing source documents.

    Stores documents from various sources (database, file, API) with JSONB support.
    Extended with sync-related fields for data synchronization system.
    """
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_config: Mapped[dict] = mapped_column(get_json_type(), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    document_metadata: Mapped[dict] = mapped_column("metadata", get_json_type(), default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Sync-related fields (Phase 1.2 extension)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sync_status: Mapped[Optional[SyncStatus]] = mapped_column(SQLEnum(SyncStatus), nullable=True, default=None)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)
    sync_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256 content hash
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_source_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # External source record ID
    sync_job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # UUID of sync job
    is_from_sync: Mapped[bool] = mapped_column(Boolean, default=False)  # Whether document came from sync
    sync_metadata: Mapped[dict] = mapped_column(get_json_type(), default={})  # Additional sync-related metadata

    # Relationship to tasks
    tasks: Mapped[List["TaskModel"]] = relationship("TaskModel", back_populates="document")


class TaskModel(Base):
    """
    Task table for managing annotation tasks.

    Extended model supporting:
    - Task management (name, description, priority, annotation_type)
    - Assignment and progress tracking
    - Label Studio integration
    - Sync-related fields for data synchronization
    """
    __tablename__ = "tasks"

    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Basic task information
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Task")
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Task")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    priority: Mapped[TaskPriority] = mapped_column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    annotation_type: Mapped[AnnotationType] = mapped_column(SQLEnum(AnnotationType), default=AnnotationType.CUSTOM)

    # Document and project association
    document_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Assignment and ownership
    assignee_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # Fixed: UUID type to match DB
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, default="default_tenant")

    # Progress tracking
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 percentage
    total_items: Mapped[int] = mapped_column(Integer, default=1)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Annotation data (JSON / JSONB)
    annotations: Mapped[list] = mapped_column(get_json_type(), default=[])
    ai_predictions: Mapped[list] = mapped_column(get_json_type(), default=[])
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    tags: Mapped[list] = mapped_column(get_json_type(), default=[])
    task_metadata: Mapped[dict] = mapped_column(get_json_type(), default={})

    # Sync-related fields (Phase 1.2 extension)
    sync_status: Mapped[Optional[SyncStatus]] = mapped_column(SQLEnum(SyncStatus), nullable=True, default=None)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_execution_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    is_from_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_metadata: Mapped[dict] = mapped_column(get_json_type(), default={})

    # Label Studio integration fields
    label_studio_project_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    label_studio_project_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    label_studio_sync_status: Mapped[Optional[LabelStudioSyncStatus]] = mapped_column(
        SQLEnum(LabelStudioSyncStatus),
        default=LabelStudioSyncStatus.PENDING,
        nullable=True
    )
    label_studio_last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    label_studio_task_count: Mapped[int] = mapped_column(Integer, default=0)
    label_studio_annotation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    document: Mapped[Optional["DocumentModel"]] = relationship("DocumentModel", back_populates="tasks")
    assignee: Mapped[Optional["UserModel"]] = relationship("UserModel", foreign_keys=[assignee_id])
    quality_issues: Mapped[List["QualityIssueModel"]] = relationship("QualityIssueModel", back_populates="task")
    billing_records: Mapped[List["BillingRecordModel"]] = relationship("BillingRecordModel", back_populates="task")


class BillingRecordModel(Base):
    """
    Billing records table for tracking annotation costs.
    
    Stores billing information per tenant, user, and task.
    """
    __tablename__ = "billing_records"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    task_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    annotation_count: Mapped[int] = mapped_column(Integer, default=0)
    time_spent: Mapped[int] = mapped_column(Integer, default=0)  # in seconds
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    billing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    task: Mapped[Optional["TaskModel"]] = relationship("TaskModel", back_populates="billing_records")


class QualityIssueModel(Base):
    """
    Quality issues table for tracking quality problems and work orders.
    
    Manages quality issues found during annotation review.
    """
    __tablename__ = "quality_issues"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[IssueSeverity] = mapped_column(SQLEnum(IssueSeverity), default=IssueSeverity.MEDIUM)
    status: Mapped[IssueStatus] = mapped_column(SQLEnum(IssueStatus), default=IssueStatus.OPEN)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    task: Mapped["TaskModel"] = relationship("TaskModel", back_populates="quality_issues")

# Import security models to ensure they are registered with SQLAlchemy
from src.security.models import (
    UserModel, ProjectPermissionModel, IPWhitelistModel,
    SecurityAuditLogModel, DataMaskingRuleModel
)

# Import sync models to ensure they are registered with SQLAlchemy
from src.sync.models import (
    DataSourceModel, SyncJobModel, SyncExecutionModel,
    DataConflictModel, SyncRuleModel, TransformationRuleModel,
    IndustryDatasetModel, SyncAuditLogModel, DataQualityScoreModel
)

# Import Label Studio workspace models to ensure they are registered with SQLAlchemy
from src.label_studio.workspace_models import (
    LabelStudioWorkspaceModel, LabelStudioWorkspaceMemberModel,
    WorkspaceProjectModel, ProjectMemberModel
)

# Import AI integration models to ensure they are registered with SQLAlchemy
from src.models.ai_integration import (
    AIGateway, AISkill, AIAuditLog
)

# AI workflow presets (ai_workflows table)
from src.models.ai_workflow import AIWorkflow  # noqa: F401

# Data lifecycle approval_requests (Alembic 029)
from src.models.approval_request_db import ApprovalRequestRow  # noqa: F401
from src.models.notification_db import InternalMessageRow  # noqa: F401

# Import structuring models to ensure they are registered with SQLAlchemy
from src.models.structuring import (  # noqa: F401
    StructuringJob, StructuredRecord, ProcessingType,
    VectorRecord, SemanticRecord,
)

# Data lifecycle tables used by transfer / integration tests (ensure create_all includes them)
from src.models.data_lifecycle import (  # noqa: F401
    TempDataModel,
    SampleModel,
    TransferAuditLogModel,
)

# Import datalake metrics model to ensure it is registered with SQLAlchemy
from src.sync.connectors.datalake.models import DatalakeMetricsModel  # noqa: F401

# Multi-tenant core (LLM tables reference tenants.id)
from src.database.multi_tenant_models import TenantModel  # noqa: F401

# LLM application binding tables (used by integration tests and admin LLM APIs)
from src.models.llm_configuration import LLMConfiguration, LLMUsageLog  # noqa: F401
from src.models.llm_application import LLMApplication, LLMApplicationBinding  # noqa: F401
