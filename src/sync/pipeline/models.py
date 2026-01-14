"""
Database models for Data Sync Pipeline.

SQLAlchemy models for persisting sync pipeline data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.database.base import Base


class DataSource(Base):
    """Data source configuration table."""
    __tablename__ = "sync_data_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Connection details
    db_type = Column(String(50), nullable=False)  # postgresql, mysql, sqlite, etc.
    host = Column(String(500), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(200), nullable=False)
    username = Column(String(200), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    connection_method = Column(String(20), default="jdbc")
    extra_params = Column(JSONB, default={})
    
    # Save strategy
    save_strategy = Column(String(20), default="persistent")
    save_config = Column(JSONB, default={})
    
    # Status
    is_active = Column(Boolean, default=True)
    last_connected_at = Column(DateTime, nullable=True)
    connection_status = Column(String(50), default="unknown")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    checkpoints = relationship("SyncCheckpoint", back_populates="data_source", cascade="all, delete-orphan")
    jobs = relationship("SyncJob", back_populates="data_source", cascade="all, delete-orphan")
    export_records = relationship("ExportRecord", back_populates="data_source", cascade="all, delete-orphan")


class SyncCheckpoint(Base):
    """Sync checkpoint table for incremental pulls."""
    __tablename__ = "sync_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sync_data_sources.id"), nullable=False, index=True)
    
    # Checkpoint data
    checkpoint_field = Column(String(200), nullable=False)
    last_value = Column(Text, nullable=True)
    last_value_type = Column(String(50), default="string")  # string, integer, datetime
    last_pull_at = Column(DateTime, nullable=True)
    rows_pulled = Column(Integer, default=0)
    
    # Metadata
    query_hash = Column(String(64), nullable=True)  # Hash of the query for validation
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    data_source = relationship("DataSource", back_populates="checkpoints")
    
    __table_args__ = (
        UniqueConstraint("source_id", "checkpoint_field", name="uq_checkpoint_source_field"),
    )


class SyncJob(Base):
    """Sync job table for scheduled tasks."""
    __tablename__ = "sync_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sync_data_sources.id"), nullable=False, index=True)
    
    # Job configuration
    name = Column(String(200), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    
    # Pull configuration
    pull_config = Column(JSONB, default={})
    
    # Status
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Statistics
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    total_rows_synced = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    data_source = relationship("DataSource", back_populates="jobs")
    history = relationship("SyncHistory", back_populates="job", cascade="all, delete-orphan")


class SyncHistory(Base):
    """Sync history table for execution records."""
    __tablename__ = "sync_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("sync_jobs.id"), nullable=False, index=True)
    
    # Execution details
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # running, completed, failed
    
    # Results
    rows_synced = Column(Integer, default=0)
    bytes_processed = Column(Integer, default=0)
    duration_ms = Column(Float, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Checkpoint at completion
    checkpoint_value = Column(Text, nullable=True)
    
    # Relationships
    job = relationship("SyncJob", back_populates="history")


class SemanticCache(Base):
    """Semantic cache table for LLM refinement results."""
    __tablename__ = "sync_semantic_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Cache key
    cache_key = Column(String(64), nullable=False, unique=True, index=True)
    
    # Cached data
    refinement_result = Column(JSONB, nullable=False)
    
    # Metadata
    data_hash = Column(String(64), nullable=True)  # Hash of input data
    config_hash = Column(String(64), nullable=True)  # Hash of config
    
    # TTL
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=0)
    last_hit_at = Column(DateTime, nullable=True)


class ExportRecord(Base):
    """Export record table for tracking exports."""
    __tablename__ = "sync_export_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sync_data_sources.id"), nullable=True, index=True)
    
    # Export configuration
    export_format = Column(String(20), nullable=False)  # json, csv, jsonl, coco, pascal_voc
    config = Column(JSONB, default={})
    
    # Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    
    # Results
    file_paths = Column(JSONB, default=[])
    statistics = Column(JSONB, default={})
    
    # Metadata
    total_rows = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    duration_ms = Column(Float, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    data_source = relationship("DataSource", back_populates="export_records")


class IdempotencyRecord(Base):
    """Idempotency record table for webhook deduplication."""
    __tablename__ = "sync_idempotency_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Idempotency key
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    
    # Request metadata
    source_id = Column(UUID(as_uuid=True), nullable=True)
    request_hash = Column(String(64), nullable=True)
    
    # Result
    rows_received = Column(Integer, default=0)
    
    # TTL
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class SyncedData(Base):
    """Synced data table for storing pulled/received data."""
    __tablename__ = "sync_synced_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sync_data_sources.id"), nullable=False, index=True)
    
    # Batch information
    batch_id = Column(String(64), nullable=False, index=True)
    batch_sequence = Column(Integer, default=0)
    
    # Data
    data = Column(JSONB, nullable=False)
    row_count = Column(Integer, default=0)
    
    # Metadata
    sync_type = Column(String(20), default="pull")  # pull, push, read
    checkpoint_value = Column(Text, nullable=True)
    
    # Semantic enrichment
    is_refined = Column(Boolean, default=False)
    refinement_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("batch_id", "batch_sequence", name="uq_synced_data_batch_seq"),
    )
