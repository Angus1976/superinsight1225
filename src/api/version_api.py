"""
Version Control API.

REST API endpoints for data version control:
- Version creation and retrieval
- Version history and comparison
- Tag and branch management
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.version.version_manager import version_manager
from src.version.query_engine import version_query_engine
from src.version.models import VersionStatus, VersionType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/versions", tags=["Version Control"])


# Request/Response Models
class CreateVersionRequest(BaseModel):
    """Request to create a new version."""
    entity_type: str = Field(..., description="Type of entity")
    entity_id: str = Field(..., description="Entity ID (UUID)")
    data: Dict[str, Any] = Field(..., description="Version data")
    comment: Optional[str] = Field(None, description="Version comment")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    branch_id: Optional[str] = Field(None, description="Branch ID")
    use_delta: bool = Field(True, description="Use delta storage")


class CreateTagRequest(BaseModel):
    """Request to create a version tag."""
    version_id: str = Field(..., description="Version ID")
    tag_name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")


class CreateBranchRequest(BaseModel):
    """Request to create a branch."""
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")
    branch_name: str = Field(..., description="Branch name")
    base_version_id: Optional[str] = Field(None, description="Base version ID")
    description: Optional[str] = Field(None, description="Branch description")


# API Endpoints
@router.post("/create")
async def create_version(
    request: CreateVersionRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new version for an entity."""
    try:
        version = await version_manager.create_version(
            entity_type=request.entity_type,
            entity_id=UUID(request.entity_id),
            data=request.data,
            user_id=user_id,
            tenant_id=tenant_id,
            branch_id=UUID(request.branch_id) if request.branch_id else None,
            comment=request.comment,
            metadata=request.metadata,
            use_delta=request.use_delta,
        )
        return {
            "success": True,
            "version": version.to_dict(),
            "message": f"Created version {version.version_number}"
        }
    except Exception as e:
        logger.error(f"Failed to create version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{version_id}")
async def get_version(
    version_id: str,
    tenant_id: Optional[str] = Query(None),
    include_data: bool = Query(True)
) -> Dict[str, Any]:
    """Get a specific version by ID."""
    version = version_manager.get_version(UUID(version_id), tenant_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    result = version.to_dict()
    if include_data:
        result["version_data"] = version_manager.reconstruct_version_data(version)
    
    return {"success": True, "version": result}


@router.get("/entity/{entity_type}/{entity_id}/history")
async def get_version_history(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False)
) -> Dict[str, Any]:
    """Get version history for an entity."""
    versions = version_manager.get_version_history(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        branch_id=UUID(branch_id) if branch_id else None,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )
    
    return {
        "success": True,
        "versions": [v.to_dict() for v in versions],
        "count": len(versions),
    }


@router.get("/entity/{entity_type}/{entity_id}/latest")
async def get_latest_version(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    include_data: bool = Query(True)
) -> Dict[str, Any]:
    """Get the latest version for an entity."""
    version = version_manager.get_latest_version(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        branch_id=UUID(branch_id) if branch_id else None,
        tenant_id=tenant_id,
    )
    
    if not version:
        raise HTTPException(status_code=404, detail="No versions found")
    
    result = version.to_dict()
    if include_data:
        result["version_data"] = version_manager.reconstruct_version_data(version)
    
    return {"success": True, "version": result}


@router.get("/compare/{version1_id}/{version2_id}")
async def compare_versions(
    version1_id: str,
    version2_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Compare two versions."""
    comparison = version_query_engine.compare_versions(
        UUID(version1_id),
        UUID(version2_id),
        tenant_id
    )
    
    if not comparison:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    
    return {
        "success": True,
        "comparison": comparison.to_dict(),
    }


@router.get("/at-time/{entity_type}/{entity_id}")
async def get_version_at_time(
    entity_type: str,
    entity_id: str,
    timestamp: datetime,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get the version that was active at a specific time."""
    version = version_query_engine.query_version_at_time(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        timestamp=timestamp,
        tenant_id=tenant_id,
    )
    
    if not version:
        raise HTTPException(status_code=404, detail="No version found at specified time")
    
    return {
        "success": True,
        "version": version.to_dict(),
        "version_data": version_manager.reconstruct_version_data(version),
    }


@router.post("/tags")
async def create_tag(
    request: CreateTagRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a tag for a version."""
    try:
        tag = version_manager.create_tag(
            version_id=UUID(request.version_id),
            tag_name=request.tag_name,
            description=request.description,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        return {
            "success": True,
            "tag_id": str(tag.id),
            "message": f"Created tag '{request.tag_name}'"
        }
    except Exception as e:
        logger.error(f"Failed to create tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-tag/{tag_name}")
async def get_version_by_tag(
    tag_name: str,
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get version by tag name."""
    version = version_manager.get_version_by_tag(
        tag_name=tag_name,
        entity_type=entity_type,
        entity_id=UUID(entity_id) if entity_id else None,
        tenant_id=tenant_id,
    )
    
    if not version:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_name}' not found")
    
    return {
        "success": True,
        "version": version.to_dict(),
    }


@router.post("/branches")
async def create_branch(
    request: CreateBranchRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new branch."""
    try:
        branch = version_manager.create_branch(
            entity_type=request.entity_type,
            entity_id=UUID(request.entity_id),
            branch_name=request.branch_name,
            base_version_id=UUID(request.base_version_id) if request.base_version_id else None,
            description=request.description,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        return {
            "success": True,
            "branch_id": str(branch.id),
            "message": f"Created branch '{request.branch_name}'"
        }
    except Exception as e:
        logger.error(f"Failed to create branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branches/{entity_type}/{entity_id}")
async def get_branches(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get all branches for an entity."""
    branches = version_manager.get_branches(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "branches": [
            {
                "id": str(b.id),
                "name": b.name,
                "description": b.description,
                "is_default": b.is_default,
                "is_merged": b.is_merged,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in branches
        ],
    }


@router.delete("/{version_id}")
async def archive_version(
    version_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Archive a version (soft delete)."""
    success = version_manager.archive_version(UUID(version_id), tenant_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "success": True,
        "message": "Version archived"
    }


@router.get("/statistics")
async def get_version_statistics(
    entity_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get version statistics."""
    stats = version_query_engine.get_version_statistics(
        entity_type=entity_type,
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "statistics": stats,
    }


@router.get("/entity/{entity_type}/{entity_id}/summary")
async def get_entity_version_summary(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get version summary for an entity."""
    summary = version_query_engine.get_entity_version_summary(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "summary": summary,
    }


@router.get("/search")
async def search_versions(
    entity_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    comment_contains: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Search versions with filters."""
    versions = version_query_engine.search_versions(
        entity_type=entity_type,
        tenant_id=tenant_id,
        created_by=created_by,
        start_date=start_date,
        end_date=end_date,
        comment_contains=comment_contains,
        limit=limit,
        offset=offset,
    )
    
    return {
        "success": True,
        "versions": [v.to_dict() for v in versions],
        "count": len(versions),
    }
