"""
Data Lineage API.

REST API endpoints for data lineage tracking:
- Lineage recording and retrieval
- Impact analysis
- Relationship mapping
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.lineage.enhanced_tracker import enhanced_lineage_tracker
from src.lineage.impact_analyzer import impact_analyzer
from src.lineage.relationship_mapper import relationship_mapper
from src.version.models import LineageRelationType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/lineage", tags=["Data Lineage"])


# Request Models
class TrackLineageRequest(BaseModel):
    """Request to track a lineage relationship."""
    source_entity_type: str = Field(..., description="Source entity type")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_type: str = Field(..., description="Target entity type")
    target_entity_id: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Relationship type")
    transformation_info: Optional[Dict[str, Any]] = Field(None)
    source_version_id: Optional[str] = Field(None)
    target_version_id: Optional[str] = Field(None)
    source_columns: Optional[List[str]] = Field(None)
    target_columns: Optional[List[str]] = Field(None)
    sync_job_id: Optional[str] = Field(None)
    execution_id: Optional[str] = Field(None)


# API Endpoints
@router.post("/track")
async def track_lineage(
    request: TrackLineageRequest,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Track a data lineage relationship."""
    try:
        # Parse relationship type
        try:
            rel_type = LineageRelationType(request.relationship_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship type: {request.relationship_type}"
            )

        record = enhanced_lineage_tracker.track_transformation(
            source_entity_type=request.source_entity_type,
            source_entity_id=UUID(request.source_entity_id),
            target_entity_type=request.target_entity_type,
            target_entity_id=UUID(request.target_entity_id),
            relationship_type=rel_type,
            transformation_info=request.transformation_info,
            source_version_id=UUID(request.source_version_id) if request.source_version_id else None,
            target_version_id=UUID(request.target_version_id) if request.target_version_id else None,
            source_columns=request.source_columns,
            target_columns=request.target_columns,
            sync_job_id=UUID(request.sync_job_id) if request.sync_job_id else None,
            execution_id=UUID(request.execution_id) if request.execution_id else None,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "record": record.to_dict(),
            "message": "Lineage tracked successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track lineage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_lineage(
    entity_type: str,
    entity_id: str,
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
) -> Dict[str, Any]:
    """Get lineage records for an entity."""
    records = enhanced_lineage_tracker.get_lineage_for_entity(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        direction=direction,
        tenant_id=tenant_id,
        limit=limit,
    )
    
    return {
        "success": True,
        "records": [r.to_dict() for r in records],
        "count": len(records),
    }


@router.get("/entity/{entity_type}/{entity_id}/full-path")
async def get_full_lineage_path(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None),
    max_depth: int = Query(10, ge=1, le=20)
) -> Dict[str, Any]:
    """Get full lineage path (upstream and downstream)."""
    path = enhanced_lineage_tracker.get_full_lineage_path(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        tenant_id=tenant_id,
        max_depth=max_depth,
    )
    
    return {
        "success": True,
        "lineage": path,
    }


@router.get("/entity/{entity_type}/{entity_id}/column/{column_name}")
async def get_column_lineage(
    entity_type: str,
    entity_id: str,
    column_name: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get column-level lineage."""
    lineage = enhanced_lineage_tracker.get_column_lineage(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        column_name=column_name,
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "column": column_name,
        "lineage": lineage,
    }


@router.get("/impact/{entity_type}/{entity_id}")
async def analyze_impact(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None),
    max_depth: int = Query(5, ge=1, le=10)
) -> Dict[str, Any]:
    """Analyze impact of changes to an entity."""
    analysis = impact_analyzer.analyze_impact(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        tenant_id=tenant_id,
        max_depth=max_depth,
    )
    
    return {
        "success": True,
        "impact_analysis": analysis.to_dict(),
    }


@router.get("/relationships/{entity_type}/{entity_id}")
async def get_entity_relationships(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get all relationships for an entity."""
    relationships = relationship_mapper.map_entity_relationships(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "relationships": relationships,
    }


@router.get("/graph")
async def get_lineage_graph(
    tenant_id: Optional[str] = Query(None),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types")
) -> Dict[str, Any]:
    """Get lineage graph for visualization."""
    types_list = entity_types.split(",") if entity_types else None
    
    graph = relationship_mapper.build_relationship_graph(
        tenant_id=tenant_id,
        entity_types=types_list,
    )
    
    return {
        "success": True,
        "graph": graph,
    }


@router.get("/related/{entity_type}/{entity_id}")
async def find_related_entities(
    entity_type: str,
    entity_id: str,
    relationship_types: Optional[str] = Query(None, description="Comma-separated types"),
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Find all entities related to a given entity."""
    rel_types = None
    if relationship_types:
        try:
            rel_types = [LineageRelationType(t.strip()) for t in relationship_types.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid relationship type: {e}")
    
    related = relationship_mapper.find_related_entities(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        relationship_types=rel_types,
        tenant_id=tenant_id,
    )
    
    return {
        "success": True,
        "related_entities": related,
        "count": len(related),
    }


@router.get("/statistics")
async def get_lineage_statistics(
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get lineage statistics."""
    stats = enhanced_lineage_tracker.get_lineage_statistics(tenant_id)
    
    return {
        "success": True,
        "statistics": stats,
    }


@router.get("/relationship-statistics")
async def get_relationship_statistics(
    tenant_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get relationship statistics."""
    stats = relationship_mapper.get_relationship_statistics(tenant_id)
    
    return {
        "success": True,
        "statistics": stats,
    }


@router.get("/visualization/{entity_type}/{entity_id}")
async def get_visualization_data(
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str] = Query(None),
    max_depth: int = Query(3, ge=1, le=10)
) -> Dict[str, Any]:
    """Get lineage data formatted for visualization."""
    # Get full lineage path
    path = enhanced_lineage_tracker.get_full_lineage_path(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        tenant_id=tenant_id,
        max_depth=max_depth,
    )
    
    # Convert to visualization format
    nodes = [{"id": f"{entity_type}:{entity_id}", "type": entity_type, "root": True}]
    edges = []
    
    def add_to_graph(items, direction, parent_id):
        for item in items:
            node_id = f"{item['entity_type']}:{item['entity_id']}"
            if not any(n["id"] == node_id for n in nodes):
                nodes.append({
                    "id": node_id,
                    "type": item["entity_type"],
                    "depth": item.get("depth", 1),
                })
            
            if direction == "upstream":
                edges.append({"source": node_id, "target": parent_id, "type": item["relationship"]})
            else:
                edges.append({"source": parent_id, "target": node_id, "type": item["relationship"]})
            
            if "children" in item:
                add_to_graph(item["children"], direction, node_id)
    
    root_id = f"{entity_type}:{entity_id}"
    add_to_graph(path.get("upstream", []), "upstream", root_id)
    add_to_graph(path.get("downstream", []), "downstream", root_id)
    
    return {
        "success": True,
        "visualization": {
            "nodes": nodes,
            "edges": edges,
            "root": root_id,
        },
    }
