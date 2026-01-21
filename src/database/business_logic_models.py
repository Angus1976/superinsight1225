"""
SQLAlchemy ORM models for Business Logic Service.

These models define the database schema for storing business rules, patterns, and insights.
Implements Requirements 5.1-5.9 for business logic service database operations.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, JSON
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


class BusinessRuleDBModel(Base):
    """
    Business Rules table for storing extracted business rules.
    
    Stores rule definitions, patterns, confidence scores, and metadata.
    Supports both PostgreSQL (with JSONB) and SQLite (with JSON) backends.
    
    Implements Requirements 5.1, 5.5, 5.7, 5.8, 5.9
    """
    __tablename__ = "business_rules"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    
    # Tenant and project identification
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Rule definition
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Metrics
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Examples (stored as JSON array)
    examples: Mapped[dict] = mapped_column(get_json_type(), nullable=False, default=list)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "pattern": self.pattern,
            "rule_type": self.rule_type,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "examples": self.examples if self.examples else [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BusinessRuleDBModel':
        """Create model instance from dictionary."""
        return cls(
            id=data.get('id', str(uuid4())),
            tenant_id=data.get('tenant_id', 'default'),
            project_id=data.get('project_id'),
            name=data.get('name'),
            description=data.get('description'),
            pattern=data.get('pattern'),
            rule_type=data.get('rule_type'),
            confidence=data.get('confidence', 0.0),
            frequency=data.get('frequency', 0),
            examples=data.get('examples', []),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def __repr__(self) -> str:
        return f"<BusinessRule(id={self.id}, name={self.name}, confidence={self.confidence})>"


class BusinessPatternDBModel(Base):
    """
    Business Patterns table for storing detected business patterns.
    
    Stores pattern definitions, strength scores, and evidence.
    Supports both PostgreSQL (with JSONB) and SQLite (with JSON) backends.
    
    Implements Requirements 5.2, 5.4
    """
    __tablename__ = "business_patterns"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    
    # Tenant and project identification
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Pattern definition
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Metrics
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Evidence (stored as JSON array)
    evidence: Mapped[dict] = mapped_column(get_json_type(), nullable=False, default=list)
    
    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "strength": self.strength,
            "evidence": self.evidence if self.evidence else [],
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BusinessPatternDBModel':
        """Create model instance from dictionary."""
        return cls(
            id=data.get('id', str(uuid4())),
            tenant_id=data.get('tenant_id', 'default'),
            project_id=data.get('project_id'),
            pattern_type=data.get('pattern_type'),
            description=data.get('description'),
            strength=data.get('strength', 0.0),
            evidence=data.get('evidence', []),
            detected_at=data.get('detected_at'),
            last_seen=data.get('last_seen')
        )
    
    def __repr__(self) -> str:
        return f"<BusinessPattern(id={self.id}, type={self.pattern_type}, strength={self.strength})>"


class BusinessInsightDBModel(Base):
    """
    Business Insights table for storing generated business insights.
    
    Stores insight definitions, impact scores, recommendations, and acknowledgment status.
    Supports both PostgreSQL (with JSONB) and SQLite (with JSON) backends.
    
    Implements Requirements 5.3, 5.6
    """
    __tablename__ = "business_insights"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    
    # Tenant and project identification
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Insight definition
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Metrics
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Recommendations and data points (stored as JSON arrays)
    recommendations: Mapped[dict] = mapped_column(get_json_type(), nullable=False, default=list)
    data_points: Mapped[dict] = mapped_column(get_json_type(), nullable=False, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        index=True
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "insight_type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "impact_score": self.impact_score,
            "recommendations": self.recommendations if self.recommendations else [],
            "data_points": self.data_points if self.data_points else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BusinessInsightDBModel':
        """Create model instance from dictionary."""
        return cls(
            id=data.get('id', str(uuid4())),
            tenant_id=data.get('tenant_id', 'default'),
            project_id=data.get('project_id'),
            insight_type=data.get('insight_type'),
            title=data.get('title'),
            description=data.get('description'),
            impact_score=data.get('impact_score', 0.0),
            recommendations=data.get('recommendations', []),
            data_points=data.get('data_points', []),
            created_at=data.get('created_at'),
            acknowledged_at=data.get('acknowledged_at')
        )
    
    def __repr__(self) -> str:
        return f"<BusinessInsight(id={self.id}, title={self.title}, impact={self.impact_score})>"
