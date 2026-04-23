"""Document model for extractors and enhancement APIs."""

from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Structured document produced by extractors or used in enhancement flows."""

    id: UUID = Field(default_factory=uuid4)
    source_type: str
    source_config: Dict[str, Any] = Field(default_factory=dict)
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True
