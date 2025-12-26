"""
Knowledge Graph REST API.

Provides endpoints for entity/relation CRUD, text extraction, and graph queries.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..core.models import (
    Entity,
    Relation,
    EntityType,
    RelationType,
    GraphStatistics,
    GraphQueryResult,
    EntityCreateRequest,
    RelationCreateRequest,
    TextExtractionRequest,
    TextExtractionResponse,
    ExtractedEntity,
    ExtractedRelation,
)
from ..core.graph_db import GraphDatabase, get_graph_database, init_graph_database
from ..nlp.entity_extractor import EntityExtractor, get_entity_extractor
from ..nlp.relation_extractor import RelationExtractor, get_relation_extractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["Knowledge Graph"])


# ==================== Response Models ====================

class EntityResponse(BaseModel):
    """Entity response model."""
    success: bool = True
    entity: Optional[Entity] = None
    message: str = ""


class EntitiesResponse(BaseModel):
    """Multiple entities response model."""
    success: bool = True
    entities: List[Entity] = []
    total: int = 0
    message: str = ""


class RelationResponse(BaseModel):
    """Relation response model."""
    success: bool = True
    relation: Optional[Relation] = None
    message: str = ""


class RelationsResponse(BaseModel):
    """Multiple relations response model."""
    success: bool = True
    relations: List[Relation] = []
    total: int = 0
    message: str = ""


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str = ""
    details: Dict[str, Any] = {}


# ==================== Dependencies ====================

async def get_db() -> GraphDatabase:
    """Get graph database instance."""
    db = get_graph_database()
    if not db._initialized:
        await db.initialize()
    return db


# ==================== Health Check ====================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check knowledge graph service health."""
    try:
        db = get_graph_database()
        health = await db.health_check()

        if health.get("status") == "healthy":
            return HealthResponse(
                status="healthy",
                message="Knowledge graph service is operational",
                details=health,
            )
        else:
            return HealthResponse(
                status="degraded",
                message="Knowledge graph service has issues",
                details=health,
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            message=str(e),
        )


# ==================== Entity Endpoints ====================

@router.post("/entities", response_model=EntityResponse)
async def create_entity(
    request: EntityCreateRequest,
    db: GraphDatabase = Depends(get_db),
):
    """Create a new entity."""
    try:
        entity = Entity(
            entity_type=request.entity_type,
            name=request.name,
            properties=request.properties,
            aliases=request.aliases,
            description=request.description,
            confidence=request.confidence,
            source=request.source,
        )

        created = await db.create_entity(entity)

        return EntityResponse(
            success=True,
            entity=created,
            message=f"Entity created: {created.id}",
        )
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: UUID,
    tenant_id: Optional[str] = Query(None),
    db: GraphDatabase = Depends(get_db),
):
    """Get an entity by ID."""
    try:
        entity = await db.get_entity(entity_id, tenant_id)

        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        return EntityResponse(
            success=True,
            entity=entity,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: UUID,
    updates: Dict[str, Any],
    db: GraphDatabase = Depends(get_db),
):
    """Update an entity."""
    try:
        updated = await db.update_entity(entity_id, updates)

        if not updated:
            raise HTTPException(status_code=404, detail="Entity not found")

        return EntityResponse(
            success=True,
            entity=updated,
            message=f"Entity updated: {entity_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/entities/{entity_id}")
async def delete_entity(
    entity_id: UUID,
    hard_delete: bool = Query(False),
    db: GraphDatabase = Depends(get_db),
):
    """Delete an entity."""
    try:
        deleted = await db.delete_entity(entity_id, hard_delete)

        if not deleted:
            raise HTTPException(status_code=404, detail="Entity not found")

        return {"success": True, "message": f"Entity deleted: {entity_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities", response_model=EntitiesResponse)
async def search_entities(
    q: Optional[str] = Query(None, description="Search query"),
    entity_type: Optional[EntityType] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: GraphDatabase = Depends(get_db),
):
    """Search entities."""
    try:
        entities = await db.search_entities(
            query_text=q,
            entity_type=entity_type,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )

        return EntitiesResponse(
            success=True,
            entities=entities,
            total=len(entities),
        )
    except Exception as e:
        logger.error(f"Failed to search entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Relation Endpoints ====================

@router.post("/relations", response_model=RelationResponse)
async def create_relation(
    request: RelationCreateRequest,
    db: GraphDatabase = Depends(get_db),
):
    """Create a new relation."""
    try:
        relation = Relation(
            source_id=request.source_id,
            target_id=request.target_id,
            relation_type=request.relation_type,
            properties=request.properties,
            weight=request.weight,
            confidence=request.confidence,
            evidence=request.evidence,
        )

        created = await db.create_relation(relation)

        return RelationResponse(
            success=True,
            relation=created,
            message=f"Relation created: {created.id}",
        )
    except Exception as e:
        logger.error(f"Failed to create relation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relations/{relation_id}", response_model=RelationResponse)
async def get_relation(
    relation_id: UUID,
    db: GraphDatabase = Depends(get_db),
):
    """Get a relation by ID."""
    try:
        relation = await db.get_relation(relation_id)

        if not relation:
            raise HTTPException(status_code=404, detail="Relation not found")

        return RelationResponse(
            success=True,
            relation=relation,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get relation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}/relations", response_model=RelationsResponse)
async def get_entity_relations(
    entity_id: UUID,
    direction: str = Query("both", regex="^(outgoing|incoming|both)$"),
    relation_types: Optional[List[RelationType]] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: GraphDatabase = Depends(get_db),
):
    """Get relations for an entity."""
    try:
        relations = await db.get_entity_relations(
            entity_id=entity_id,
            direction=direction,
            relation_types=relation_types,
            limit=limit,
        )

        return RelationsResponse(
            success=True,
            relations=relations,
            total=len(relations),
        )
    except Exception as e:
        logger.error(f"Failed to get entity relations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relations/{relation_id}")
async def delete_relation(
    relation_id: UUID,
    hard_delete: bool = Query(False),
    db: GraphDatabase = Depends(get_db),
):
    """Delete a relation."""
    try:
        deleted = await db.delete_relation(relation_id, hard_delete)

        if not deleted:
            raise HTTPException(status_code=404, detail="Relation not found")

        return {"success": True, "message": f"Relation deleted: {relation_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete relation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== NLP Extraction Endpoints ====================

@router.post("/extract", response_model=TextExtractionResponse)
async def extract_from_text(
    request: TextExtractionRequest,
    background_tasks: BackgroundTasks,
    db: GraphDatabase = Depends(get_db),
):
    """Extract entities and relations from text."""
    try:
        start_time = datetime.now()

        entities: List[ExtractedEntity] = []
        relations: List[ExtractedRelation] = []
        saved_entity_ids: List[UUID] = []
        saved_relation_ids: List[UUID] = []

        # Extract entities
        if request.extract_entities:
            entity_extractor = get_entity_extractor()
            entities = entity_extractor.extract(
                request.text,
                entity_types=request.entity_types,
            )

            # Filter by confidence
            entities = [e for e in entities if e.confidence >= request.min_confidence]

        # Extract relations
        if request.extract_relations and entities:
            relation_extractor = get_relation_extractor()
            relations = relation_extractor.extract(
                request.text,
                entities=entities,
                relation_types=request.relation_types,
            )

            # Filter by confidence
            relations = [r for r in relations if r.confidence >= request.min_confidence]

        # Save to graph if requested
        if request.save_to_graph:
            # Create entity mapping
            entity_map: Dict[str, UUID] = {}

            for extracted in entities:
                entity = extracted.to_entity()
                try:
                    created = await db.create_entity(entity)
                    saved_entity_ids.append(created.id)
                    entity_map[extracted.text] = created.id
                except Exception as e:
                    logger.warning(f"Failed to save entity: {e}")

            for extracted in relations:
                source_id = entity_map.get(extracted.source_entity.text)
                target_id = entity_map.get(extracted.target_entity.text)

                if source_id and target_id:
                    relation = extracted.to_relation(source_id, target_id)
                    try:
                        created = await db.create_relation(relation)
                        saved_relation_ids.append(created.id)
                    except Exception as e:
                        logger.warning(f"Failed to save relation: {e}")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return TextExtractionResponse(
            entities=entities,
            relations=relations,
            text_length=len(request.text),
            processing_time_ms=processing_time,
            saved_entity_ids=saved_entity_ids,
            saved_relation_ids=saved_relation_ids,
        )
    except Exception as e:
        logger.error(f"Failed to extract from text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/entities")
async def extract_entities_only(
    text: str = Query(..., min_length=1),
    entity_types: Optional[List[EntityType]] = Query(None),
    min_confidence: float = Query(0.5, ge=0, le=1),
):
    """Extract entities from text (simplified endpoint)."""
    try:
        entity_extractor = get_entity_extractor()
        entities = entity_extractor.extract(text, entity_types=entity_types)

        # Filter by confidence
        entities = [e for e in entities if e.confidence >= min_confidence]

        return {
            "success": True,
            "entities": [e.model_dump() for e in entities],
            "count": len(entities),
        }
    except Exception as e:
        logger.error(f"Failed to extract entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Graph Query Endpoints ====================

@router.get("/neighbors/{entity_id}", response_model=GraphQueryResult)
async def get_neighbors(
    entity_id: UUID,
    depth: int = Query(1, ge=1, le=5),
    limit: int = Query(100, ge=1, le=1000),
    db: GraphDatabase = Depends(get_db),
):
    """Get neighboring entities."""
    try:
        result = await db.get_neighbors(entity_id, depth=depth, limit=limit)
        return result
    except Exception as e:
        logger.error(f"Failed to get neighbors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/path", response_model=GraphQueryResult)
async def find_path(
    source_id: UUID = Query(...),
    target_id: UUID = Query(...),
    max_depth: int = Query(5, ge=1, le=10),
    db: GraphDatabase = Depends(get_db),
):
    """Find shortest path between entities."""
    try:
        result = await db.find_path(source_id, target_id, max_depth=max_depth)
        return result
    except Exception as e:
        logger.error(f"Failed to find path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/cypher")
async def execute_cypher(
    cypher: str,
    params: Optional[Dict[str, Any]] = None,
    db: GraphDatabase = Depends(get_db),
):
    """Execute a Cypher query (admin only)."""
    try:
        # Security: Only allow read queries
        cypher_upper = cypher.upper().strip()
        if not cypher_upper.startswith("MATCH") and not cypher_upper.startswith("RETURN"):
            raise HTTPException(
                status_code=400,
                detail="Only read queries (MATCH, RETURN) are allowed",
            )

        results = await db.execute_cypher(cypher, params)

        return {
            "success": True,
            "results": results,
            "count": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute Cypher: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Statistics Endpoints ====================

@router.get("/statistics", response_model=GraphStatistics)
async def get_statistics(
    tenant_id: Optional[str] = Query(None),
    db: GraphDatabase = Depends(get_db),
):
    """Get graph statistics."""
    try:
        stats = await db.get_statistics(tenant_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Bulk Operations ====================

@router.post("/bulk/entities")
async def bulk_create_entities(
    entities: List[EntityCreateRequest],
    db: GraphDatabase = Depends(get_db),
):
    """Create multiple entities."""
    try:
        created_ids = []
        errors = []

        for request in entities:
            try:
                entity = Entity(
                    entity_type=request.entity_type,
                    name=request.name,
                    properties=request.properties,
                    aliases=request.aliases,
                    description=request.description,
                    confidence=request.confidence,
                    source=request.source,
                )
                created = await db.create_entity(entity)
                created_ids.append(str(created.id))
            except Exception as e:
                errors.append({"name": request.name, "error": str(e)})

        return {
            "success": len(errors) == 0,
            "created_count": len(created_ids),
            "created_ids": created_ids,
            "errors": errors,
        }
    except Exception as e:
        logger.error(f"Failed to bulk create entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/relations")
async def bulk_create_relations(
    relations: List[RelationCreateRequest],
    db: GraphDatabase = Depends(get_db),
):
    """Create multiple relations."""
    try:
        created_ids = []
        errors = []

        for request in relations:
            try:
                relation = Relation(
                    source_id=request.source_id,
                    target_id=request.target_id,
                    relation_type=request.relation_type,
                    properties=request.properties,
                    weight=request.weight,
                    confidence=request.confidence,
                    evidence=request.evidence,
                )
                created = await db.create_relation(relation)
                created_ids.append(str(created.id))
            except Exception as e:
                errors.append({
                    "source_id": str(request.source_id),
                    "target_id": str(request.target_id),
                    "error": str(e),
                })

        return {
            "success": len(errors) == 0,
            "created_count": len(created_ids),
            "created_ids": created_ids,
            "errors": errors,
        }
    except Exception as e:
        logger.error(f"Failed to bulk create relations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
