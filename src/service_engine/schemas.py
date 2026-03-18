"""
Pydantic schemas for the Smart Service Engine unified API.

Defines ServiceRequest, ServiceResponse, ErrorResponse, and ResponseMetadata
used across all request types (query / chat / decision / skill).
"""

import json
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request type enum values
# ---------------------------------------------------------------------------
VALID_REQUEST_TYPES = ("query", "chat", "decision", "skill")


# ---------------------------------------------------------------------------
# Response metadata
# ---------------------------------------------------------------------------
class ResponseMetadata(BaseModel):
    """Metadata attached to every successful response."""

    request_id: str          # UUID string
    timestamp: str           # ISO-8601 format
    processing_time_ms: int


# ---------------------------------------------------------------------------
# Unified request
# ---------------------------------------------------------------------------
class ServiceRequest(BaseModel):
    """Unified request body accepted by POST /api/v1/service/request."""

    request_type: Literal["query", "chat", "decision", "skill"]
    user_id: str

    # Optional cross-cutting fields
    business_context: Optional[dict] = None   # ≤ 100 KB when serialised
    include_memory: bool = True
    extensions: Optional[dict] = None         # reserved for future use

    # --- query-specific ---
    data_type: Optional[str] = None
    page: int = 1
    page_size: int = 50
    sort_by: Optional[str] = None
    fields: Optional[str] = None
    filters: Optional[dict] = None

    # --- chat-specific ---
    messages: Optional[list] = None

    # --- decision-specific ---
    question: Optional[str] = None
    context_data: Optional[dict] = None

    # --- skill-specific ---
    skill_id: Optional[str] = None
    parameters: Optional[dict] = None

    # --- workflow routing (shared across chat/query) ---
    workflow_id: Optional[str] = None

    # -- validators ----------------------------------------------------------

    @field_validator("user_id")
    @classmethod
    def user_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_id must be a non-empty string")
        return v

    @field_validator("business_context")
    @classmethod
    def business_context_size_limit(cls, v: Optional[dict]) -> Optional[dict]:
        if v is None:
            return v
        serialised = json.dumps(v, ensure_ascii=False)
        max_bytes = 100 * 1024  # 100 KB
        if len(serialised.encode("utf-8")) > max_bytes:
            raise ValueError(
                "business_context exceeds 100KB size limit"
            )
        return v


# ---------------------------------------------------------------------------
# Unified success response
# ---------------------------------------------------------------------------
class ServiceResponse(BaseModel):
    """Unified response returned for all non-SSE successful requests."""

    success: bool
    request_type: str
    data: dict
    metadata: ResponseMetadata


# ---------------------------------------------------------------------------
# Unified error response
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    """Unified error response returned for all error scenarios."""

    success: bool = False
    error: str
    error_code: str
    details: Optional[dict] = None
