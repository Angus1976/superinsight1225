"""
SQLAlchemy ORM models for Ragas Evaluation Results.

These models define the database schema for storing Ragas evaluation results.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.connection import Base
from src.config.settings import settings


def get_json_type():
    """Get appropriate JSON type based on database backend"""
    if settings.database.database_url.startswith('sqlite'):
        return JSON  # SQLite uses JSON type
    else:
        return JSONB  # PostgreSQL uses JSONB type


class RagasEvaluationResultDBModel(Base):
    """
    Ragas Evaluation Results table for storing evaluation results.
    
    Stores evaluation metrics, scores, and metadata from Ragas quality assessment.
    Supports both PostgreSQL (with JSONB) and SQLite (with JSON) backends.
    """
    __tablename__ = "ragas_evaluation_results"
    
    # Primary key - using String for compatibility with both SQLite and PostgreSQL
    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    
    # Optional task ID for tracking
    task_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    
    # Annotation IDs that were evaluated (stored as JSON array)
    annotation_ids: Mapped[dict] = mapped_column(get_json_type(), nullable=False, default=list)
    
    # Metric names and their scores (stored as JSON object)
    metrics: Mapped[dict] = mapped_column(get_json_type(), nullable=False, default=dict)
    
    # Individual scores and details (stored as JSON object)
    scores: Mapped[dict] = mapped_column(get_json_type(), nullable=False, default=dict)
    
    # Overall evaluation score (0.0 to 1.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Creation timestamp with index for date range queries
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        index=True
    )
    
    # Additional metadata (stored as JSON object) - using 'extra_metadata' to avoid SQLAlchemy reserved name
    extra_metadata: Mapped[dict] = mapped_column("metadata", get_json_type(), nullable=True, default=None)
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "annotation_ids": self.annotation_ids if self.annotation_ids else [],
            "metrics": self.metrics if self.metrics else {},
            "scores": self.scores if self.scores else {},
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.extra_metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RagasEvaluationResultDBModel':
        """Create model instance from dictionary."""
        return cls(
            id=data.get('id', str(uuid4())),
            task_id=data.get('task_id'),
            annotation_ids=data.get('annotation_ids', []),
            metrics=data.get('metrics', {}),
            scores=data.get('scores', {}),
            overall_score=data.get('overall_score', 0.0),
            created_at=data.get('created_at'),
            extra_metadata=data.get('metadata')
        )
    
    def __repr__(self) -> str:
        return f"<RagasEvaluationResult(id={self.id}, overall_score={self.overall_score})>"
