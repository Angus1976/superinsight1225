"""
Snapshots API.

REST API endpoints for snapshot management:
- Snapshot creation and retrieval
- Snapshot restoration
- Scheduled snapshots
- Retention policy management
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.versioning import snapshot_manager, RetentionPolicy
from src.models.versioning import SnapshotType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/snapshots", tags=["Snapshots"])


# Request Models
class CreateSnapshotRequest(BaseModel):
    """Request to create a snapshot."""
    data: Dict[str, Any] = Field(..., description="Data to snapshot")
    snapshot_type: str = Field("full", description="Snapshot type: full or incremental")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class CreateScheduleRequest(BaseModel):
    """Request to create a snapshot schedule."""
    schedule: str = Field(..., description="Cron expression")
    snapshot_type: str = Field("full", description="Snapshot type")
    retention_days: int = Field(90, ge=1, le=365, description="Days to retain")
    max_snapshots: int = Field(100, ge=1, le=1000, description="Max snapshots to keep")


class ApplyRetentionRequest(BaseModel):
    """Request to apply retention policy."""
    max_age_days: int = Field(90, ge=1, le=365)
    max_count: int = Field(100, ge=1, le=1000)
    keep_tagged: bool = Field(True)


# Snapshot Endpoints
@router.post("/{entity_type}/{entity_id}")
async def create_snapshot(
    entity_type: str,
    entity_id: str,
    request: CreateSnapshotRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a snapshot for an entity."""
    try:
        # Parse snapshot type
        try:
            stype = SnapshotType(request.snapshot_type.lower())
        except ValueError:
            stype = SnapshotType.FULL
        
        snapshot = await snapshot_manager.create_snapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            data=request.data,
            snapshot_type=stype,
            user_id=user_id,
            tenant_id=tenant_id,
            metadata=request.metadata,
            expires_at=request.expires_at,
        )
        
        return {
            "success": True,
            "snapshot": snapshot.to_dict(),
            "message": f"Created {stype.value} snapshot"
        }
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_snapshots(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """List snapshots with optional filters."""
    snapshots = snapshot_manager.list_snapshots(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )
    
    return {
        "success": True,
        "snapshots": [s.to_dict() for s in snapshots],
        "count": len(snapshots),
    }


@router.get("/{snapshot_id}")
async def get_snapshot(
    snapshot_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get a specific snapshot."""
    snapshot = snapshot_manager.get_snapshot(snapshot_id, tenant_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return {
        "success": True,
        "snapshot": snapshot.to_dict(),
    }


@router.get("/{entity_type}/{entity_id}/latest")
async def get_latest_snapshot(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get the latest snapshot for an entity."""
    snapshot = snapshot_manager.get_latest_snapshot(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
    )
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="No snapshots found")
    
    return {
        "success": True,
        "snapshot": snapshot.to_dict(),
    }


@router.post("/{snapshot_id}/restore")
async def restore_snapshot(
    snapshot_id: str,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Restore data from a snapshot."""
    try:
        result = await snapshot_manager.restore_from_snapshot(
            snapshot_id=snapshot_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        
        return {
            "success": True,
            "restore_result": result.to_dict(),
            "data": result.data,
            "message": "Snapshot restored successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{snapshot_id}")
async def delete_snapshot(
    snapshot_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Delete a snapshot."""
    success = snapshot_manager.delete_snapshot(snapshot_id, tenant_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return {
        "success": True,
        "message": "Snapshot deleted"
    }


# Schedule Endpoints
@router.post("/schedules")
async def create_schedule(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    request: CreateScheduleRequest = ...,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a snapshot schedule."""
    try:
        # Parse snapshot type
        try:
            stype = SnapshotType(request.snapshot_type.lower())
        except ValueError:
            stype = SnapshotType.FULL
        
        schedule = await snapshot_manager.create_scheduled_snapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            schedule=request.schedule,
            snapshot_type=stype,
            retention_days=request.retention_days,
            max_snapshots=request.max_snapshots,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        
        return {
            "success": True,
            "schedule": schedule.to_dict(),
            "message": f"Created schedule: {request.schedule}"
        }
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Retention Policy Endpoints
@router.post("/{entity_type}/{entity_id}/retention")
async def apply_retention_policy(
    entity_type: str,
    entity_id: str,
    request: ApplyRetentionRequest,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Apply retention policy to snapshots."""
    policy = RetentionPolicy(
        max_age_days=request.max_age_days,
        max_count=request.max_count,
        keep_tagged=request.keep_tagged,
    )
    
    deleted_count = snapshot_manager.apply_retention_policy(
        entity_type=entity_type,
        entity_id=entity_id,
        policy=policy,
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} snapshots per retention policy"
    }


# Statistics Endpoint
@router.get("/statistics")
async def get_snapshot_statistics(
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get snapshot statistics."""
    stats = snapshot_manager.get_snapshot_statistics(tenant_id)
    
    return {
        "success": True,
        "statistics": stats,
    }
