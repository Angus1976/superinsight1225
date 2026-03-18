"""
Pydantic schemas for the AI Workflow Engine.

Defines request/response models for workflow CRUD, permission chain results,
error responses, and reserved authorization structures.

Python 3.9.6 compatible: uses Optional[List[str]] instead of list[str] | None.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Workflow CRUD Schemas
# ---------------------------------------------------------------------------


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a new workflow."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    skill_ids: Optional[List[str]] = Field(default_factory=list)
    data_source_auth: Optional[List[dict]] = Field(default_factory=list)
    output_modes: Optional[List[str]] = Field(default_factory=list)
    visible_roles: List[str] = Field(..., min_length=1)
    preset_prompt: Optional[str] = None
    name_en: Optional[str] = None
    description_en: Optional[str] = None


class WorkflowUpdateRequest(BaseModel):
    """Request body for updating an existing workflow. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    skill_ids: Optional[List[str]] = None
    data_source_auth: Optional[List[dict]] = None
    output_modes: Optional[List[str]] = None
    visible_roles: Optional[List[str]] = None
    status: Optional[str] = None
    preset_prompt: Optional[str] = None
    name_en: Optional[str] = None
    description_en: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Response body representing a full workflow object."""

    id: str
    name: str
    description: Optional[str] = None
    status: str
    is_preset: bool
    skill_ids: List[str]
    data_source_auth: List[dict]
    output_modes: List[str]
    visible_roles: List[str]
    preset_prompt: Optional[str] = None
    name_en: Optional[str] = None
    description_en: Optional[str] = None
    created_at: str
    updated_at: str
    created_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Permission Chain Result
# ---------------------------------------------------------------------------


class EffectivePermissions(BaseModel):
    """Effective permissions after permission chain validation.

    Represents the intersection of role permissions, workflow config,
    and API parameter overrides.
    """

    allowed_skill_ids: List[str]
    allowed_data_sources: List[dict]  # same structure as data_source_auth
    allowed_output_modes: List[str]


# ---------------------------------------------------------------------------
# Error Response
# ---------------------------------------------------------------------------


class WorkflowErrorResponse(BaseModel):
    """Unified error response for workflow-related API errors.

    Frontend maps error_code to i18n translation text; message is for
    debugging only and should not be displayed directly.
    """

    success: bool = False
    error_code: str
    message: str
    details: Optional[dict] = None


# ---------------------------------------------------------------------------
# Reserved: Dynamic Authorization Structures (Requirements 14.1, 14.5)
# ---------------------------------------------------------------------------


class MissingPermissions(BaseModel):
    """Details of permissions that are missing for workflow execution."""

    skills: Optional[List[str]] = None
    data_sources: Optional[List[str]] = None
    data_tables: Optional[List[dict]] = None  # [{source_id, tables}]


class AuthorizationRequest(BaseModel):
    """Authorization request structure returned when permissions are insufficient.

    Included in 403 response details to enable dynamic authorization flow.
    Reserved for future implementation.
    """

    request_id: str
    workflow_id: str
    missing_permissions: MissingPermissions
    requested_scope: str
    callback_url: str


class AuthorizationCallback(BaseModel):
    """Callback request format from customer systems granting/denying authorization.

    Reserved for future implementation (POST /api/v1/service/authorization-callback).
    """

    request_id: str
    granted: bool
    granted_permissions: Optional[dict] = None
    expires_at: Optional[str] = None  # ISO-8601
    reason: Optional[str] = None      # rejection reason when granted=False
