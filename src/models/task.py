"""Task model placeholder for AI annotation services."""

from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def get_utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Task model for annotation assignments."""

    task_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    tenant_id: UUID
    title: str
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
