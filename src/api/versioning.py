"""
Versioning API.

REST API endpoints for the new versioning module:
- Version management with semantic versioning
- Change tracking
- Diff computation and merging
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.versioning import (
    version_manager, change_tracker, diff_engine,
    VersionType, DiffLevel, ChangeType
)
from src.models.versioning import ChangeType as ModelChangeType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/versioning", tags=["Versioning"])


# Request Models
class CreateVersionRequest(BaseModel):
    """Request to create a new version."""
    data: Dict[str, Any] = Field(..., description="Version data")
    message: str = Field(..., description="Version message")
    version_type: str = Field("patch", description="Version type: major, minor, patch")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class RollbackRequest(BaseModel):
    """Request to rollback to a version."""
    target_version: str = Field(..., description="Target version string")


class AddTagRequest(BaseModel):
    """Request to add a tag."""
    tag: str = Field(..., description="Tag name")


class ComputeDiffRequest(BaseModel):
    """Request to compute diff."""
    old_data: Dict[str, Any] = Field(..., description="Old data")
    new_data: Dict[str, Any] = Field(..., description="New data")
    diff_level: str = Field("field", description="Diff level: field or line")


class MergeRequest(BaseModel):
    """Request for three-way merge."""
    base: Dict[str, Any] = Field(..., description="Base version data")
    ours: Dict[str, Any] = Field(..., description="Our changes")
    theirs: Dict[str, Any] = Field(..., description="Their changes")


class ResolveConflictRequest(BaseModel):
    """Request to resolve a conflict."""
    merged: Dict[str, Any] = Field(..., description="Current merged data")
    conflicts: List[Dict[str, Any]] = Field(..., description="Current conflicts")
    field: str = Field(..., description="Field to resolve")
    resolution: str = Field(..., description="Resolution: ours, theirs, base, custom")
    custom_value: Optional[Any] = Field(None, description="Custom value if resolution is custom")


# Version Management Endpoints
@router.post("/{entity_type}/{entity_id}")
async def create_version(
    entity_type: str,
    entity_id: str,
    request: CreateVersionRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new version for an entity."""
    try:
        # Parse version type
        try:
            vtype = VersionType(request.version_type.lower())
        except ValueError:
            vtype = VersionType.PATCH
        
        version = await version_manager.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data=request.data,
            message=request.message,
            user_id=user_id or "system",
            version_type=vtype,
            tenant_id=tenant_id,
            metadata=request.metadata,
        )
        
        return {
            "success": True,
            "version": version,
            "message": f"Created version {version.get('version')}"
        }
    except Exception as e:
        logger.error(f"Failed to create version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}")
async def get_version_history(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """Get version history for an entity."""
    versions = version_manager.get_version_history(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
        limit=limit,
    )
    
    return {
        "success": True,
        "versions": versions,
        "count": len(versions),
    }


@router.get("/{entity_type}/{entity_id}/{version}")
async def get_version(
    entity_type: str,
    entity_id: str,
    version: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get a specific version."""
    ver = version_manager.get_version(
        entity_type=entity_type,
        entity_id=entity_id,
        version=version,
        tenant_id=tenant_id,
    )
    
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "success": True,
        "version": ver,
    }


@router.post("/{entity_type}/{entity_id}/rollback")
async def rollback_version(
    entity_type: str,
    entity_id: str,
    request: RollbackRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Rollback to a specific version."""
    try:
        version = await version_manager.rollback(
            entity_type=entity_type,
            entity_id=entity_id,
            target_version=request.target_version,
            user_id=user_id or "system",
            tenant_id=tenant_id,
        )
        
        return {
            "success": True,
            "version": version,
            "message": f"Rolled back to version {request.target_version}"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rollback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{version_id}/tags")
async def add_version_tag(
    version_id: str,
    request: AddTagRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Add a tag to a version."""
    try:
        version = await version_manager.add_tag(
            version_id=version_id,
            tag=request.tag,
            user_id=user_id or "system",
            tenant_id=tenant_id,
        )
        
        return {
            "success": True,
            "version": version,
            "message": f"Added tag '{request.tag}'"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Change Tracking Endpoints
@router.get("/changes")
async def get_changes(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    change_type: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Query change history."""
    # Parse change type
    ct = None
    if change_type:
        try:
            ct = ModelChangeType(change_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid change type: {change_type}")
    
    changes = change_tracker.get_changes(
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        change_type=ct,
        start_time=start_time,
        end_time=end_time,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )
    
    return {
        "success": True,
        "changes": [c.to_dict() for c in changes],
        "count": len(changes),
    }


@router.get("/changes/{entity_type}/{entity_id}/timeline")
async def get_entity_timeline(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
) -> Dict[str, Any]:
    """Get change timeline for an entity."""
    timeline = change_tracker.get_entity_timeline(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
        limit=limit,
    )
    
    return {
        "success": True,
        "timeline": timeline,
        "count": len(timeline),
    }


@router.get("/changes/statistics")
async def get_change_statistics(
    entity_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None)
) -> Dict[str, Any]:
    """Get change statistics."""
    stats = change_tracker.get_change_statistics(
        entity_type=entity_type,
        tenant_id=tenant_id,
        start_time=start_time,
        end_time=end_time,
    )
    
    return {
        "success": True,
        "statistics": stats,
    }


# Diff and Merge Endpoints
@router.post("/diff")
async def compute_diff(request: ComputeDiffRequest) -> Dict[str, Any]:
    """Compute difference between two data versions."""
    try:
        level = DiffLevel(request.diff_level.lower())
    except ValueError:
        level = DiffLevel.FIELD
    
    result = diff_engine.compute_diff(
        old_data=request.old_data,
        new_data=request.new_data,
        diff_level=level,
    )
    
    return {
        "success": True,
        "diff": result.to_dict(),
    }


@router.post("/merge")
async def three_way_merge(request: MergeRequest) -> Dict[str, Any]:
    """Perform three-way merge."""
    result = diff_engine.three_way_merge(
        base=request.base,
        ours=request.ours,
        theirs=request.theirs,
    )
    
    return {
        "success": True,
        "merge_result": result.to_dict(),
    }


@router.post("/merge/resolve")
async def resolve_conflict(request: ResolveConflictRequest) -> Dict[str, Any]:
    """Resolve a merge conflict."""
    from src.versioning.diff_engine import MergeResult, MergeConflict
    
    # Reconstruct MergeResult
    conflicts = [
        MergeConflict(
            field=c["field"],
            base_value=c.get("base_value"),
            ours_value=c.get("ours_value"),
            theirs_value=c.get("theirs_value"),
        )
        for c in request.conflicts
    ]
    
    merge_result = MergeResult(
        merged=request.merged,
        conflicts=conflicts,
        has_conflicts=len(conflicts) > 0,
    )
    
    result = diff_engine.resolve_conflict(
        merge_result=merge_result,
        field=request.field,
        resolution=request.resolution,
        custom_value=request.custom_value,
    )
    
    return {
        "success": True,
        "merge_result": result.to_dict(),
    }
