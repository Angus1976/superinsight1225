"""
Relationship Mapper.

Maps and manages data entity relationships:
- Automatic relationship detection
- Relationship graph building
- Cross-entity mapping
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.version.models import DataLineageRecord, LineageRelationType

logger = logging.getLogger(__name__)


class RelationshipMapper:
    """
    Maps relationships between data entities.
    
    Provides:
    - Relationship discovery
    - Graph building
    - Cross-entity mapping
    """
    
    def __init__(self):
        self.db_manager = db_manager
        self._relationship_cache: Dict[str, List[Dict]] = {}
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()
    
    def map_entity_relationships(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Map all relationships for an entity.
        
        Returns a comprehensive relationship map including:
        - Direct relationships
        - Indirect relationships
        - Relationship statistics
        """
        with self.get_session() as session:
            # Get outgoing relationships (entity is source)
            outgoing_stmt = select(DataLineageRecord).where(
                DataLineageRecord.source_entity_type == entity_type,
                DataLineageRecord.source_entity_id == entity_id
            )
            if tenant_id:
                outgoing_stmt = outgoing_stmt.where(
                    DataLineageRecord.tenant_id == tenant_id
                )
            outgoing = session.execute(outgoing_stmt).scalars().all()

            # Get incoming relationships (entity is target)
            incoming_stmt = select(DataLineageRecord).where(
                DataLineageRecord.target_entity_type == entity_type,
                DataLineageRecord.target_entity_id == entity_id
            )
            if tenant_id:
                incoming_stmt = incoming_stmt.where(
                    DataLineageRecord.tenant_id == tenant_id
                )
            incoming = session.execute(incoming_stmt).scalars().all()
            
            # Build relationship map
            return {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "outgoing_relationships": [
                    {
                        "target_type": r.target_entity_type,
                        "target_id": str(r.target_entity_id),
                        "relationship": r.relationship_type.value,
                        "columns": r.target_columns,
                    }
                    for r in outgoing
                ],
                "incoming_relationships": [
                    {
                        "source_type": r.source_entity_type,
                        "source_id": str(r.source_entity_id),
                        "relationship": r.relationship_type.value,
                        "columns": r.source_columns,
                    }
                    for r in incoming
                ],
                "outgoing_count": len(outgoing),
                "incoming_count": len(incoming),
                "total_relationships": len(outgoing) + len(incoming),
            }
    
    def build_relationship_graph(
        self,
        tenant_id: Optional[str] = None,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build a complete relationship graph.
        
        Returns graph data suitable for visualization.
        """
        with self.get_session() as session:
            stmt = select(DataLineageRecord)
            
            if tenant_id:
                stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
            if entity_types:
                stmt = stmt.where(
                    DataLineageRecord.source_entity_type.in_(entity_types) |
                    DataLineageRecord.target_entity_type.in_(entity_types)
                )
            
            records = session.execute(stmt).scalars().all()
            
            # Build nodes and edges
            nodes = {}
            edges = []
            
            for record in records:
                # Add source node
                source_key = f"{record.source_entity_type}:{record.source_entity_id}"
                if source_key not in nodes:
                    nodes[source_key] = {
                        "id": source_key,
                        "type": record.source_entity_type,
                        "entity_id": str(record.source_entity_id),
                    }
                
                # Add target node
                target_key = f"{record.target_entity_type}:{record.target_entity_id}"
                if target_key not in nodes:
                    nodes[target_key] = {
                        "id": target_key,
                        "type": record.target_entity_type,
                        "entity_id": str(record.target_entity_id),
                    }
                
                # Add edge
                edges.append({
                    "source": source_key,
                    "target": target_key,
                    "relationship": record.relationship_type.value,
                })
            
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
            }

    def find_related_entities(
        self,
        entity_type: str,
        entity_id: UUID,
        relationship_types: Optional[List[LineageRelationType]] = None,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all entities related to a given entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            relationship_types: Filter by relationship types
            tenant_id: Tenant ID
            
        Returns:
            List of related entities
        """
        with self.get_session() as session:
            # Find as source
            source_stmt = select(DataLineageRecord).where(
                DataLineageRecord.source_entity_type == entity_type,
                DataLineageRecord.source_entity_id == entity_id
            )
            
            # Find as target
            target_stmt = select(DataLineageRecord).where(
                DataLineageRecord.target_entity_type == entity_type,
                DataLineageRecord.target_entity_id == entity_id
            )
            
            if relationship_types:
                source_stmt = source_stmt.where(
                    DataLineageRecord.relationship_type.in_(relationship_types)
                )
                target_stmt = target_stmt.where(
                    DataLineageRecord.relationship_type.in_(relationship_types)
                )
            
            if tenant_id:
                source_stmt = source_stmt.where(
                    DataLineageRecord.tenant_id == tenant_id
                )
                target_stmt = target_stmt.where(
                    DataLineageRecord.tenant_id == tenant_id
                )
            
            source_records = session.execute(source_stmt).scalars().all()
            target_records = session.execute(target_stmt).scalars().all()
            
            related = []
            seen = set()
            
            for r in source_records:
                key = f"{r.target_entity_type}:{r.target_entity_id}"
                if key not in seen:
                    seen.add(key)
                    related.append({
                        "entity_type": r.target_entity_type,
                        "entity_id": str(r.target_entity_id),
                        "relationship": r.relationship_type.value,
                        "direction": "outgoing",
                    })
            
            for r in target_records:
                key = f"{r.source_entity_type}:{r.source_entity_id}"
                if key not in seen:
                    seen.add(key)
                    related.append({
                        "entity_type": r.source_entity_type,
                        "entity_id": str(r.source_entity_id),
                        "relationship": r.relationship_type.value,
                        "direction": "incoming",
                    })
            
            return related
    
    def get_relationship_statistics(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get relationship statistics."""
        with self.get_session() as session:
            base_filter = []
            if tenant_id:
                base_filter.append(DataLineageRecord.tenant_id == tenant_id)
            
            # Count by relationship type
            type_stmt = select(
                DataLineageRecord.relationship_type,
                func.count(DataLineageRecord.id)
            ).group_by(DataLineageRecord.relationship_type)
            if base_filter:
                type_stmt = type_stmt.where(*base_filter)
            type_results = session.execute(type_stmt).all()
            
            # Count by entity type pairs
            pair_stmt = select(
                DataLineageRecord.source_entity_type,
                DataLineageRecord.target_entity_type,
                func.count(DataLineageRecord.id)
            ).group_by(
                DataLineageRecord.source_entity_type,
                DataLineageRecord.target_entity_type
            )
            if base_filter:
                pair_stmt = pair_stmt.where(*base_filter)
            pair_results = session.execute(pair_stmt).all()
            
            return {
                "by_relationship_type": {
                    str(t.value) if t else "unknown": c 
                    for t, c in type_results
                },
                "by_entity_pair": [
                    {"source": s, "target": t, "count": c}
                    for s, t, c in pair_results
                ],
                "generated_at": datetime.utcnow().isoformat(),
            }


# Global instance
relationship_mapper = RelationshipMapper()
