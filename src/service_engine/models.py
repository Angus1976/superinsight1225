"""
SQLAlchemy models for Smart Service Engine.

Defines UserMemory and WebhookConfig tables.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.connection import Base


class UserMemory(Base):
    """User memory table for cross-request interaction history."""

    __tablename__ = "user_memories"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    memory_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # interaction / summary
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_user_memories_user_tenant", "user_id", "tenant_id"),
    )


class WebhookConfig(Base):
    """Webhook configuration table for event push (MVP reserved)."""

    __tablename__ = "webhook_configs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    api_key_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    webhook_url: Mapped[str] = mapped_column(String(500), nullable=False)
    webhook_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_events: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
