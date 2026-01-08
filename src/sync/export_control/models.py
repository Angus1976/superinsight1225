"""
Data Export Control models for secure export management.

Provides comprehensive models for export requests, approvals, watermarking,
tracking, and behavior monitoring.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List, Dict, Any

from src.database.connection import Base


class ExportRequestStatus(str, enum.Enum):
    """Export request status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, enum.Enum):
    """Export format enumeration."""
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    EXCEL = "excel"
    PDF = "pdf"
    PARQUET = "parquet"


class ExportScope(str, enum.Enum):
    """Export scope enumeration."""
    FULL_TABLE = "full_table"
    FILTERED_DATA = "filtered_data"
    SPECIFIC_RECORDS = "specific_records"
    AGGREGATED_DATA = "aggregated_data"


class ApprovalStatus(str, enum.Enum):
    """Approval status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class WatermarkType(str, enum.Enum):
    """Watermark type enumeration."""
    VISIBLE = "visible"
    INVISIBLE = "invisible"
    DIGITAL_SIGNATURE = "digital_signature"
    METADATA = "metadata"


class ExportBehaviorType(str, enum.Enum):
    """Export behavior type enumeration."""
    DOWNLOAD = "download"
    VIEW = "view"
    SHARE = "share"
    COPY = "copy"
    PRINT = "print"
    FORWARD = "forward"


class ExportRequestModel(Base):
    """
    Export request table for data export management.
    
    Stores export requests with detailed metadata and approval requirements.
    """
    __tablename__ = "export_requests"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Request details
    requester_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    request_title: Mapped[str] = mapped_column(String(200), nullable=False)
    request_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_justification: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Export configuration
    export_format: Mapped[ExportFormat] = mapped_column(SQLEnum(ExportFormat), nullable=False)
    export_scope: Mapped[ExportScope] = mapped_column(SQLEnum(ExportScope), nullable=False)
    
    # Data selection
    table_names: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    field_names: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    filter_conditions: Mapped[dict] = mapped_column(JSONB, default={})
    record_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Approval requirements
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_level: Mapped[int] = mapped_column(Integer, default=1)  # 1=manager, 2=senior, 3=executive
    auto_approve_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max records for auto-approve
    
    # Security settings
    enable_watermark: Mapped[bool] = mapped_column(Boolean, default=True)
    watermark_config: Mapped[dict] = mapped_column(JSONB, default={})
    enable_tracking: Mapped[bool] = mapped_column(Boolean, default=True)
    access_restrictions: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Expiry and retention
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    
    # Status and processing
    status: Mapped[ExportRequestStatus] = mapped_column(SQLEnum(ExportRequestStatus), default=ExportRequestStatus.PENDING)
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, higher is more urgent
    
    # Processing details
    estimated_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_size_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Output details
    output_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    download_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    approvals: Mapped[List["ExportApprovalModel"]] = relationship("ExportApprovalModel", back_populates="export_request")
    watermarks: Mapped[List["ExportWatermarkModel"]] = relationship("ExportWatermarkModel", back_populates="export_request")
    tracking_records: Mapped[List["ExportTrackingModel"]] = relationship("ExportTrackingModel", back_populates="export_request")
    behavior_records: Mapped[List["ExportBehaviorModel"]] = relationship("ExportBehaviorModel", back_populates="export_request")


class ExportApprovalModel(Base):
    """
    Export approval table for approval workflow management.
    
    Tracks approval process for export requests with multi-level approval support.
    """
    __tablename__ = "export_approvals"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    export_request_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("export_requests.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Approval details
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, etc.
    approver_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Status and decision
    status: Mapped[ApprovalStatus] = mapped_column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conditions: Mapped[dict] = mapped_column(JSONB, default={})  # Additional conditions or restrictions
    
    # Timing
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Escalation
    escalated_to: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    export_request: Mapped["ExportRequestModel"] = relationship("ExportRequestModel", back_populates="approvals")


class ExportWatermarkModel(Base):
    """
    Export watermark table for data watermarking and tracking.
    
    Stores watermark information for exported data files.
    """
    __tablename__ = "export_watermarks"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    export_request_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("export_requests.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Watermark details
    watermark_type: Mapped[WatermarkType] = mapped_column(SQLEnum(WatermarkType), nullable=False)
    watermark_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # Unique watermark identifier
    
    # Watermark content
    watermark_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    watermark_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    digital_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Positioning and styling (for visible watermarks)
    position_config: Mapped[dict] = mapped_column(JSONB, default={})
    style_config: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Metadata watermark (for invisible watermarks)
    metadata_fields: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Verification
    verification_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_algorithm: Mapped[str] = mapped_column(String(50), default="SHA-256")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    export_request: Mapped["ExportRequestModel"] = relationship("ExportRequestModel", back_populates="watermarks")


class ExportTrackingModel(Base):
    """
    Export tracking table for monitoring exported data access.
    
    Tracks all access and usage of exported data files.
    """
    __tablename__ = "export_tracking"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    export_request_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("export_requests.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Access details
    accessor_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)  # download, view, share, etc.
    
    # Session information
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Geographic information
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Access context
    access_method: Mapped[str] = mapped_column(String(50), nullable=False)  # web, api, mobile, etc.
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # File information
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bytes_transferred: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timing
    access_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Security flags
    suspicious_activity: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    anomaly_flags: Mapped[List[str]] = mapped_column(JSONB, default=[])
    
    # Timestamps
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    export_request: Mapped["ExportRequestModel"] = relationship("ExportRequestModel", back_populates="tracking_records")


class ExportBehaviorModel(Base):
    """
    Export behavior table for monitoring user behavior with exported data.
    
    Tracks detailed user interactions and behavior patterns with exported files.
    """
    __tablename__ = "export_behavior"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    export_request_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("export_requests.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # User and session
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Behavior details
    behavior_type: Mapped[ExportBehaviorType] = mapped_column(SQLEnum(ExportBehaviorType), nullable=False)
    behavior_details: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Context information
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    browser_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    operating_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Interaction metrics
    interaction_count: Mapped[int] = mapped_column(Integer, default=1)
    total_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Sharing and forwarding
    shared_with: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)  # Email addresses or user IDs
    forwarded_to: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    
    # Security analysis
    compliance_status: Mapped[str] = mapped_column(String(50), default="compliant")
    policy_violations: Mapped[List[str]] = mapped_column(JSONB, default=[])
    risk_indicators: Mapped[List[str]] = mapped_column(JSONB, default=[])
    
    # Timestamps
    first_interaction: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_interaction: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    export_request: Mapped["ExportRequestModel"] = relationship("ExportRequestModel", back_populates="behavior_records")


class ExportPolicyModel(Base):
    """
    Export policy table for defining export rules and restrictions.
    
    Stores tenant-specific export policies and restrictions.
    """
    __tablename__ = "export_policies"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Policy details
    policy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Scope
    applies_to_tables: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    applies_to_roles: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    applies_to_users: Mapped[Optional[List[UUID]]] = mapped_column(JSONB, nullable=True)
    
    # Restrictions
    max_records_per_export: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_exports_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_exports_per_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Allowed formats
    allowed_formats: Mapped[List[str]] = mapped_column(JSONB, default=["csv", "json"])
    
    # Approval requirements
    requires_manager_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_senior_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_approve_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Security requirements
    mandatory_watermark: Mapped[bool] = mapped_column(Boolean, default=True)
    mandatory_tracking: Mapped[bool] = mapped_column(Boolean, default=True)
    max_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    
    # Conditions
    time_restrictions: Mapped[dict] = mapped_column(JSONB, default={})  # Business hours, etc.
    ip_restrictions: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Higher priority policies override lower
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)