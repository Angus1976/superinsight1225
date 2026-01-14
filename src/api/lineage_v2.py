"""
Lineage API v2.

REST API endpoints for the new lineage engine:
- Lineage relationship management
- Upstream/downstream queries
- Impact analysis
- Visualization data
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.versioning import (
    lineage_engine, impact_analyzer,
    LineageGraph, ImpactReport
)
from src.models.versioning import LineageRelationType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/lineage/v2", tags=["Lineage v2"])


# Request Models
class AddLineageRequest(BaseModel):
    """Request to add a lineage relationship."""
    source_type: str = Field(..., description="Source entity type")
    source_id: str = Field(..., description="Source entity ID")
    target_type: str = Field(..., description="Target entity type")
    target_id: str = Field(..., description="Target entity ID")
    relationship: str = Field(..., description="Relationship type")
    transformation: Optional[Dict[str, Any]] = Field(None, description="Transformation details")
    source_columns: Optional[List[str]] = Field(None, description="Source columns")
    target_columns: Optional[List[str]] = Field(None, description="Target columns")


class AnalyzeImpactRequest(BaseModel):
    """Request for impact analysis."""
    change_type: str = Field("update", description="Type of change")
    max_depth: int = Field(5, ge=1, le=10, description="Maximum analysis depth")


# Lineage Endpoints
@router.post("")
async def add_lineage(
    request: AddLineageRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Add a lineage relationship."""
    try:
        # Parse relationship type
        try:
            rel_type = LineageRelationType(request.relationship.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship type: {request.relationship}. "
                       f"Valid types: {[t.value for t in LineageRelationType]}"
            )
        
        record = await lineage_engine.add_lineage(
            source_type=request.source_type,
            source_id=request.source_id,
            target_type=request.target_type,
            target_id=request.target_id,
            relationship=rel_type,
            transformation=request.transformation,
            source_columns=request.source_columns,
            target_columns=request.target_columns,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "record": record.to_dict(),
            "message": "Lineage relationship added"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add lineage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}/upstream")
async def get_upstream_lineage(
    entity_type: str,
    entity_id: str,
    depth: int = Query(3, ge=1, le=10),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get upstream lineage for an entity."""
    graph = lineage_engine.get_upstream(
        entity_type=entity_type,
        entity_id=entity_id,
        depth=depth,
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "lineage": graph.to_dict(),
    }


@router.get("/{entity_type}/{entity_id}/downstream")
async def get_downstream_lineage(
    entity_type: str,
    entity_id: str,
    depth: int = Query(3, ge=1, le=10),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get downstream lineage for an entity."""
    graph = lineage_engine.get_downstream(
        entity_type=entity_type,
        entity_id=entity_id,
        depth=depth,
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "lineage": graph.to_dict(),
    }


@router.get("/{entity_type}/{entity_id}/full")
async def get_full_lineage(
    entity_type: str,
    entity_id: str,
    upstream_depth: int = Query(3, ge=1, le=10),
    downstream_depth: int = Query(3, ge=1, le=10),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get full lineage graph (upstream and downstream)."""
    graph = lineage_engine.get_full_lineage(
        entity_type=entity_type,
        entity_id=entity_id,
        upstream_depth=upstream_depth,
        downstream_depth=downstream_depth,
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "lineage": graph.to_dict(),
    }


@router.get("/{entity_type}/{entity_id}/path/{target_type}/{target_id}")
async def find_lineage_path(
    entity_type: str,
    entity_id: str,
    target_type: str,
    target_id: str,
    tenant_id: Optional[str] = Query(None),
    max_depth: int = Query(10, ge=1, le=20)
) -> Dict[str, Any]:
    """Find paths between two entities."""
    paths = lineage_engine.find_path(
        source_type=entity_type,
        source_id=entity_id,
        target_type=target_type,
        target_id=target_id,
        tenant_id=tenant_id,
        max_depth=max_depth,
    )
    
    return {
        "success": True,
        "paths": [p.to_dict() for p in paths],
        "count": len(paths),
    }


# Impact Analysis Endpoints
@router.post("/impact/{entity_type}/{entity_id}/analyze")
async def analyze_impact(
    entity_type: str,
    entity_id: str,
    request: AnalyzeImpactRequest,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Analyze impact of changes to an entity."""
    try:
        report = await impact_analyzer.analyze_impact(
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=request.change_type,
            tenant_id=tenant_id,
            max_depth=request.max_depth,
        )
        
        return {
            "success": True,
            "impact_report": report.to_dict(),
        }
    except Exception as e:
        logger.error(f"Failed to analyze impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/impact/{entity_type}/{entity_id}/visualize")
async def get_impact_visualization(
    entity_type: str,
    entity_id: str,
    change_type: str = Query("update"),
    tenant_id: Optional[str] = Query(None),
    max_depth: int = Query(5, ge=1, le=10)
) -> Dict[str, Any]:
    """Get impact visualization data."""
    try:
        report = await impact_analyzer.analyze_impact(
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            tenant_id=tenant_id,
            max_depth=max_depth,
        )
        
        visualization = impact_analyzer.visualize_impact(report)
        
        return {
            "success": True,
            "visualization": visualization,
            "risk_level": report.risk_level.value,
        }
    except Exception as e:
        logger.error(f"Failed to generate visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Statistics Endpoint
@router.get("/statistics")
async def get_lineage_statistics(
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get lineage statistics."""
    stats = lineage_engine.get_lineage_statistics(tenant_id)
    
    return {
        "success": True,
        "statistics": stats,
    }
