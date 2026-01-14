"""
Lineage Engine.

Provides data lineage tracking and querying:
- Add lineage relationships
- Query upstream/downstream lineage
- Full lineage graph construction
- Path finding between entities
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.models.versioning import DataLineageRecord, LineageRelationType

logger = logging.getLogger(__name__)


@dataclass
class LineageNode:
    """Represents a node in the lineage graph."""
    entity_type: str
    entity_id: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "name": self.name or f"{self.entity_type}:{self.entity_id}",
            "metadata": self.metadata,
        }


@dataclass
class LineageEdge:
    """Represents an edge in the lineage graph."""
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str
    transformation: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "transformation": self.transformation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class LineageGraph:
    """Represents a lineage graph."""
    nodes: List[LineageNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


@dataclass
class LineagePath:
    """Represents a path between two entities."""
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    path: List[Dict[str, Any]] = field(default_factory=list)
    length: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "path": self.path,
            "length": self.length,
        }


class LineageEngine:
    """
    Lineage Engine for data lineage tracking.
    
    Provides:
    - Lineage relationship management
    - Upstream/downstream queries
    - Full lineage graph construction
    - Path finding between entities
    """
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()
    
    async def add_lineage(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relationship: LineageRelationType,
        transformation: Optional[Dict[str, Any]] = None,
        source_version_id: Optional[UUID] = None,
        target_version_id: Optional[UUID] = None,
        source_columns: Optional[List[str]] = None,
        target_columns: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> DataLineageRecord:
        """
        Add a lineage relationship.
        
        Args:
            source_type: Type of source entity
            source_id: Source entity ID
            target_type: Type of target entity
            target_id: Target entity ID
            relationship: Type of relationship
            transformation: Transformation details
            source_version_id: Source version ID
            target_version_id: Target version ID
            source_columns: Source columns involved
            target_columns: Target columns affected
            tenant_id: Tenant ID for isolation
            user_id: User creating the relationship
            
        Returns:
            Created DataLineageRecord
        """
        with self.get_session() as session:
            record = DataLineageRecord(
                source_entity_type=source_type,
                source_entity_id=source_id,
                source_version_id=source_version_id,
                target_entity_type=target_type,
                target_entity_id=target_id,
                target_version_id=target_version_id,
                relationship_type=relationship,
                transformation_info=transformation or {},
                source_columns=source_columns,
                target_columns=target_columns,
                tenant_id=tenant_id,
                created_by=user_id,
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            logger.info(
                f"Added lineage: {source_type}/{source_id} -> "
                f"{target_type}/{target_id} ({relationship.value})"
            )
            
            return record
    
    def add_lineage_sync(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relationship: LineageRelationType,
        transformation: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> DataLineageRecord:
        """Synchronous version of add_lineage."""
        with self.get_session() as session:
            record = DataLineageRecord(
                source_entity_type=source_type,
                source_entity_id=source_id,
                target_entity_type=target_type,
                target_entity_id=target_id,
                relationship_type=relationship,
                transformation_info=transformation or {},
                tenant_id=tenant_id,
                created_by=user_id,
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record
    
    def get_upstream(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 3,
        tenant_id: Optional[str] = None
    ) -> LineageGraph:
        """
        Get upstream lineage for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            depth: Maximum traversal depth
            tenant_id: Tenant ID for isolation
            
        Returns:
            LineageGraph with upstream nodes and edges
        """
        nodes = []
        edges = []
        visited = set()
        
        self._traverse_upstream(
            entity_type, entity_id, depth, tenant_id,
            nodes, edges, visited, 0
        )
        
        return LineageGraph(nodes=nodes, edges=edges)
    
    def _traverse_upstream(
        self,
        entity_type: str,
        entity_id: str,
        max_depth: int,
        tenant_id: Optional[str],
        nodes: List[LineageNode],
        edges: List[LineageEdge],
        visited: Set[str],
        current_depth: int
    ):
        """Recursively traverse upstream lineage."""
        if current_depth >= max_depth:
            return
        
        key = f"{entity_type}:{entity_id}"
        if key in visited:
            return
        visited.add(key)
        
        # Add current node
        nodes.append(LineageNode(
            entity_type=entity_type,
            entity_id=entity_id,
            metadata={"depth": current_depth}
        ))
        
        with self.get_session() as session:
            stmt = select(DataLineageRecord).where(
                DataLineageRecord.target_entity_type == entity_type,
                DataLineageRecord.target_entity_id == entity_id
            )
            
            if tenant_id:
                stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            records = result.scalars().all()
            
            for record in records:
                # Add edge
                edges.append(LineageEdge(
                    source_type=record.source_entity_type,
                    source_id=record.source_entity_id,
                    target_type=record.target_entity_type,
                    target_id=record.target_entity_id,
                    relationship=record.relationship_type.value,
                    transformation=record.transformation_info,
                    created_at=record.created_at,
                ))
                
                # Recurse
                self._traverse_upstream(
                    record.source_entity_type,
                    record.source_entity_id,
                    max_depth,
                    tenant_id,
                    nodes,
                    edges,
                    visited,
                    current_depth + 1
                )
    
    def get_downstream(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 3,
        tenant_id: Optional[str] = None
    ) -> LineageGraph:
        """
        Get downstream lineage for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            depth: Maximum traversal depth
            tenant_id: Tenant ID for isolation
            
        Returns:
            LineageGraph with downstream nodes and edges
        """
        nodes = []
        edges = []
        visited = set()
        
        self._traverse_downstream(
            entity_type, entity_id, depth, tenant_id,
            nodes, edges, visited, 0
        )
        
        return LineageGraph(nodes=nodes, edges=edges)
    
    def _traverse_downstream(
        self,
        entity_type: str,
        entity_id: str,
        max_depth: int,
        tenant_id: Optional[str],
        nodes: List[LineageNode],
        edges: List[LineageEdge],
        visited: Set[str],
        current_depth: int
    ):
        """Recursively traverse downstream lineage."""
        if current_depth >= max_depth:
            return
        
        key = f"{entity_type}:{entity_id}"
        if key in visited:
            return
        visited.add(key)
        
        # Add current node
        nodes.append(LineageNode(
            entity_type=entity_type,
            entity_id=entity_id,
            metadata={"depth": current_depth}
        ))
        
        with self.get_session() as session:
            stmt = select(DataLineageRecord).where(
                DataLineageRecord.source_entity_type == entity_type,
                DataLineageRecord.source_entity_id == entity_id
            )
            
            if tenant_id:
                stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            records = result.scalars().all()
            
            for record in records:
                # Add edge
                edges.append(LineageEdge(
                    source_type=record.source_entity_type,
                    source_id=record.source_entity_id,
                    target_type=record.target_entity_type,
                    target_id=record.target_entity_id,
                    relationship=record.relationship_type.value,
                    transformation=record.transformation_info,
                    created_at=record.created_at,
                ))
                
                # Recurse
                self._traverse_downstream(
                    record.target_entity_type,
                    record.target_entity_id,
                    max_depth,
                    tenant_id,
                    nodes,
                    edges,
                    visited,
                    current_depth + 1
                )
    
    def get_full_lineage(
        self,
        entity_type: str,
        entity_id: str,
        upstream_depth: int = 3,
        downstream_depth: int = 3,
        tenant_id: Optional[str] = None
    ) -> LineageGraph:
        """
        Get full lineage graph (both upstream and downstream).
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            upstream_depth: Maximum upstream depth
            downstream_depth: Maximum downstream depth
            tenant_id: Tenant ID for isolation
            
        Returns:
            Combined LineageGraph
        """
        upstream = self.get_upstream(entity_type, entity_id, upstream_depth, tenant_id)
        downstream = self.get_downstream(entity_type, entity_id, downstream_depth, tenant_id)
        
        # Merge graphs (deduplicate nodes)
        node_keys = set()
        merged_nodes = []
        
        for node in upstream.nodes + downstream.nodes:
            key = f"{node.entity_type}:{node.entity_id}"
            if key not in node_keys:
                node_keys.add(key)
                merged_nodes.append(node)
        
        # Merge edges (deduplicate)
        edge_keys = set()
        merged_edges = []
        
        for edge in upstream.edges + downstream.edges:
            key = f"{edge.source_type}:{edge.source_id}->{edge.target_type}:{edge.target_id}"
            if key not in edge_keys:
                edge_keys.add(key)
                merged_edges.append(edge)
        
        return LineageGraph(nodes=merged_nodes, edges=merged_edges)
    
    def find_path(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        tenant_id: Optional[str] = None,
        max_depth: int = 10
    ) -> List[LineagePath]:
        """
        Find paths between two entities.
        
        Args:
            source_type: Source entity type
            source_id: Source entity ID
            target_type: Target entity type
            target_id: Target entity ID
            tenant_id: Tenant ID for isolation
            max_depth: Maximum path length
            
        Returns:
            List of LineagePath objects
        """
        paths = []
        current_path = []
        visited = set()
        
        self._find_paths_dfs(
            source_type, source_id,
            target_type, target_id,
            tenant_id, max_depth,
            current_path, visited, paths
        )
        
        return paths
    
    def _find_paths_dfs(
        self,
        current_type: str,
        current_id: str,
        target_type: str,
        target_id: str,
        tenant_id: Optional[str],
        max_depth: int,
        current_path: List[Dict[str, Any]],
        visited: Set[str],
        paths: List[LineagePath]
    ):
        """DFS to find all paths."""
        if len(current_path) > max_depth:
            return
        
        key = f"{current_type}:{current_id}"
        if key in visited:
            return
        
        visited.add(key)
        current_path.append({
            "entity_type": current_type,
            "entity_id": current_id,
        })
        
        # Check if we reached target
        if current_type == target_type and current_id == target_id:
            paths.append(LineagePath(
                source_type=current_path[0]["entity_type"],
                source_id=current_path[0]["entity_id"],
                target_type=target_type,
                target_id=target_id,
                path=list(current_path),
                length=len(current_path) - 1
            ))
        else:
            # Continue searching downstream
            with self.get_session() as session:
                stmt = select(DataLineageRecord).where(
                    DataLineageRecord.source_entity_type == current_type,
                    DataLineageRecord.source_entity_id == current_id
                )
                
                if tenant_id:
                    stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
                
                result = session.execute(stmt)
                records = result.scalars().all()
                
                for record in records:
                    self._find_paths_dfs(
                        record.target_entity_type,
                        record.target_entity_id,
                        target_type, target_id,
                        tenant_id, max_depth,
                        current_path, visited, paths
                    )
        
        current_path.pop()
        visited.remove(key)
    
    def get_lineage_statistics(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get lineage statistics."""
        with self.get_session() as session:
            conditions = []
            if tenant_id:
                conditions.append(DataLineageRecord.tenant_id == tenant_id)
            
            # Total count
            total_stmt = select(func.count(DataLineageRecord.id))
            if conditions:
                total_stmt = total_stmt.where(and_(*conditions))
            total = session.execute(total_stmt).scalar() or 0
            
            # By relationship type
            type_stmt = select(
                DataLineageRecord.relationship_type,
                func.count(DataLineageRecord.id)
            ).group_by(DataLineageRecord.relationship_type)
            if conditions:
                type_stmt = type_stmt.where(and_(*conditions))
            type_results = session.execute(type_stmt).all()
            by_type = {
                t.value if t else "unknown": c 
                for t, c in type_results
            }
            
            return {
                "total_relationships": total,
                "by_relationship_type": by_type,
                "generated_at": datetime.utcnow().isoformat(),
            }


# Global instance
lineage_engine = LineageEngine()
