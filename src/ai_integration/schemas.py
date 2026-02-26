"""
Shared schemas for AI integration modules.

This module contains Pydantic models used across AI integration components
to avoid circular imports.
"""

from typing import Optional
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
