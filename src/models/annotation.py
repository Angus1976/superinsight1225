"""Pydantic Annotation model for AI pre-annotation and RAGAS evaluation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Annotation(BaseModel):
    """In-memory annotation payload (not the full SQLAlchemy ORM entity)."""

    annotation_id: UUID = Field(default_factory=uuid4)
    task_id: UUID = Field(default_factory=uuid4)
    project_id: Optional[UUID] = None
    annotation_type: str = "text"
    annotation_data: Dict[str, Any] = Field(default_factory=dict)
    labels: List[Any] = Field(default_factory=list)
    confidence: float = 0.0
    sample_id: Optional[str] = None
    annotator_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    class Config:
        from_attributes = True
