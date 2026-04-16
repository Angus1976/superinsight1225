"""
Shared schemas for AI integration modules.

This module contains Pydantic models used across AI integration components
to avoid circular imports.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class SkillInfoResponse(BaseModel):
    """Single skill info returned by OpenClaw status endpoint."""
    id: str
    name: str
    version: str
    status: str
    description: Optional[str] = None


class OpenClawStatusResponse(BaseModel):
    """OpenClaw gateway availability and deployed skills."""
    available: bool
    gateway_id: Optional[str] = None
    gateway_name: Optional[str] = None
    skills: list[SkillInfoResponse] = []
    error: Optional[str] = None
    # True when HTTP GET {gateway_base}/health returns 200（与 DB 有网关记录不同）
    gateway_reachable: bool = False


class SkillDetailResponse(SkillInfoResponse):
    """Extended skill detail with gateway and timestamp info."""
    category: Optional[str] = None
    gateway_id: str
    gateway_name: str
    deployed_at: Optional[datetime] = None
    created_at: datetime


class SkillListResponse(BaseModel):
    """Paginated skill list with total count."""
    skills: list[SkillDetailResponse]
    total: int


class SyncResultResponse(BaseModel):
    """Result of a skill sync operation."""
    added: int
    updated: int
    removed: int
    skills: list[SkillDetailResponse]


class ExecuteRequest(BaseModel):
    """Request body for skill execution."""
    parameters: dict = {}


class ExecuteResultResponse(BaseModel):
    """Result of a skill execution."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class StatusToggle(BaseModel):
    """Request body for toggling skill status."""
    status: Literal["deployed", "pending"]

