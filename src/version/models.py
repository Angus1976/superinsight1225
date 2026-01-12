"""
Data Version Control Models.

SQLAlchemy ORM models for version control system:
- DataVersion: Core version records
- DataVersionTag: Version tagging
- DataVersionBranch: Version branching support
- DataLineageRecord: Persistent lineage records
"""

import enum
from datetime import datetime
from uuid import uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Text, Float, Integer, DateTime, ForeignKey, 
    Enum as SQLEnum, Boolean, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.connection import Base


class VersionStatus(str, enum.Enum):
    """Version status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PENDING = "pending"


class VersionType(str, enum.Enum):
    """Version type enumeration."""
    FULL = "full"           # Full snapshot
    DELTA = "delta"         # Incremental delta
    CHECKPOINT = "checkpoint"  # Checkpoint version


class LineageRelationType(str, enum.Enum):
    """Lineage relationship type enumeration."""
    DERIVED_FROM = "derived_from"
    TRANSFORMED_TO = "transformed_to"
    COPIED_FROM = "copied_from"
    AGGREGATED_FROM = "aggregated_from"
    FILTERED_FROM = "filtered_from"
    JOINED_FROM = "joined_from"
    ENRICHED_BY = "enriched_by"


class DataVersion(Base):
    """
    Data Version Model.
    
    Stores version history for all data entities with support for:
    - Full snapshots and incremental deltas
    - Version branching and tagging
    - Multi-tenant isolation
    - Audit trail integration
    """
    __tablename__ = "data_versions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    
    # Entity identification
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="Type of entity: task, annotation, dataset, document"
    )
    entity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
        comment="ID of the versioned entity"
    )
    
    # Version information
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Sequential version number"
    )
    version_type: Mapped[VersionType] = mapped_column(
        SQLEnum(VersionType), default=VersionType.FULL,
        comment="Type of version: full, delta, checkpoint"
    )
    status: Mapped[VersionStatus] = mapped_column(
        SQLEnum(VersionStatus), default=VersionStatus.ACTIVE,
        comment="Version status"
    )

    # Parent version for delta tracking
    parent_version_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_versions.id"), nullable=True,
        comment="Parent version ID for delta versions"
    )
    
    # Branch support
    branch_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_version_branches.id"), nullable=True,
        comment="Branch this version belongs to"
    )
    
    # Version data storage using PostgreSQL JSONB
    version_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default={},
        comment="Full version data snapshot"
    )
    delta_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Incremental delta from parent version"
    )
    
    # Metadata and checksums
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        comment="SHA-256 checksum of version data"
    )
    data_size_bytes: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Size of version data in bytes"
    )
    version_metadata: Mapped[dict] = mapped_column(
        JSONB, default={},
        comment="Additional version metadata"
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Version comment or description"
    )

    # Multi-tenant support
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True,
        comment="Tenant ID for multi-tenant isolation"
    )
    workspace_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="Workspace ID"
    )
    
    # Audit fields
    created_by: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="User who created this version"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        comment="Version creation timestamp"
    )
    
    # Relationships
    parent_version: Mapped[Optional["DataVersion"]] = relationship(
        "DataVersion", remote_side="DataVersion.id",
        foreign_keys=[parent_version_id]
    )
    tags: Mapped[List["DataVersionTag"]] = relationship(
        "DataVersionTag", back_populates="version"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        Index('idx_data_versions_entity', 'entity_type', 'entity_id'),
        Index('idx_data_versions_tenant', 'tenant_id', 'workspace_id'),
        Index('idx_data_versions_created', 'created_at'),
        Index('idx_data_versions_entity_version', 'entity_type', 'entity_id', 'version_number'),
        UniqueConstraint('entity_type', 'entity_id', 'version_number', 'branch_id',
                        name='uq_entity_version_branch'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "version_number": self.version_number,
            "version_type": self.version_type.value if self.version_type else None,
            "status": self.status.value if self.status else None,
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "checksum": self.checksum,
            "data_size_bytes": self.data_size_bytes,
            "metadata": self.version_metadata,
            "comment": self.comment,
            "tenant_id": self.tenant_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DataVersionTag(Base):
    """
    Version Tag Model.
    
    Allows tagging specific versions for easy reference.
    """
    __tablename__ = "data_version_tags"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    version_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_versions.id"), nullable=False
    )
    tag_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Tag name (e.g., v1.0, release-2024)"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Tag description"
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    version: Mapped["DataVersion"] = relationship(
        "DataVersion", back_populates="tags"
    )
    
    __table_args__ = (
        Index('idx_version_tags_tenant', 'tenant_id'),
        UniqueConstraint('version_id', 'tag_name', name='uq_version_tag'),
    )


class DataVersionBranch(Base):
    """
    Version Branch Model.
    
    Supports branching for parallel version development.
    """
    __tablename__ = "data_version_branches"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Branch name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    
    # Entity this branch belongs to
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    # Branch point
    base_version_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_versions.id"), nullable=True,
        comment="Version this branch was created from"
    )
    
    # Branch status
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_merged: Mapped[bool] = mapped_column(Boolean, default=False)
    merged_to_branch_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    merged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Multi-tenant
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    
    # Audit
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    __table_args__ = (
        Index('idx_branches_entity', 'entity_type', 'entity_id'),
        Index('idx_branches_tenant', 'tenant_id'),
        UniqueConstraint('entity_type', 'entity_id', 'name', 'tenant_id',
                        name='uq_entity_branch_name'),
    )


class DataLineageRecord(Base):
    """
    Persistent Data Lineage Record Model.
    
    Stores data lineage relationships in the database for:
    - Source-to-target tracking
    - Transformation history
    - Impact analysis
    - Audit compliance
    """
    __tablename__ = "data_lineage_records"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    
    # Source entity
    source_entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Source entity type"
    )
    source_entity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
        comment="Source entity ID"
    )
    source_version_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_versions.id"), nullable=True,
        comment="Source version ID"
    )
    
    # Target entity
    target_entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Target entity type"
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
        comment="Target entity ID"
    )
    target_version_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_versions.id"), nullable=True,
        comment="Target version ID"
    )
    
    # Relationship details
    relationship_type: Mapped[LineageRelationType] = mapped_column(
        SQLEnum(LineageRelationType), nullable=False,
        comment="Type of lineage relationship"
    )
    transformation_info: Mapped[dict] = mapped_column(
        JSONB, default={},
        comment="Transformation details"
    )
    
    # Column-level lineage
    source_columns: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="Source columns involved"
    )
    target_columns: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="Target columns affected"
    )

    # Processing context
    sync_job_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="Associated sync job ID"
    )
    execution_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="Associated execution ID"
    )
    
    # Multi-tenant
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    __table_args__ = (
        Index('idx_lineage_source', 'source_entity_type', 'source_entity_id'),
        Index('idx_lineage_target', 'target_entity_type', 'target_entity_id'),
        Index('idx_lineage_tenant', 'tenant_id'),
        Index('idx_lineage_created', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert lineage record to dictionary."""
        return {
            "id": str(self.id),
            "source_entity_type": self.source_entity_type,
            "source_entity_id": str(self.source_entity_id),
            "source_version_id": str(self.source_version_id) if self.source_version_id else None,
            "target_entity_type": self.target_entity_type,
            "target_entity_id": str(self.target_entity_id),
            "target_version_id": str(self.target_version_id) if self.target_version_id else None,
            "relationship_type": self.relationship_type.value if self.relationship_type else None,
            "transformation_info": self.transformation_info,
            "source_columns": self.source_columns,
            "target_columns": self.target_columns,
            "sync_job_id": str(self.sync_job_id) if self.sync_job_id else None,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
