"""
Enhanced Lineage Tracker.

Extends the existing sync lineage tracker with:
- Persistent database storage
- Version integration
- Column-level lineage
- Advanced querying
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.database.cache_service import get_cache_service
from src.version.models import DataLineageRecord, LineageRelationType
from src.sync.lineage.lineage_tracker import (
    LineageTracker, LineageGraph, LineageNode, LineageEdge,
    LineageNodeType, LineageEdgeType
)

logger = logging.getLogger(__name__)


class EnhancedLineageTracker(LineageTracker):
    """
    Enhanced lineage tracker with persistent storage.
    
    Extends the in-memory LineageTracker with:
    - Database persistence for lineage records
    - Version control integration
    - Column-level lineage tracking
    - Advanced impact analysis
    """
    
    def __init__(self):
        super().__init__()
        self.db_manager = db_manager
        self.cache_service = get_cache_service()
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()

    def track_transformation(
        self,
        source_entity_type: str,
        source_entity_id: UUID,
        target_entity_type: str,
        target_entity_id: UUID,
        relationship_type: LineageRelationType,
        transformation_info: Optional[Dict[str, Any]] = None,
        source_version_id: Optional[UUID] = None,
        target_version_id: Optional[UUID] = None,
        source_columns: Optional[List[str]] = None,
        target_columns: Optional[List[str]] = None,
        sync_job_id: Optional[UUID] = None,
        execution_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> DataLineageRecord:
        """
        Track a data transformation with persistent storage.
        
        Args:
            source_entity_type: Type of source entity
            source_entity_id: ID of source entity
            target_entity_type: Type of target entity
            target_entity_id: ID of target entity
            relationship_type: Type of lineage relationship
            transformation_info: Details about the transformation
            source_version_id: Version ID of source (optional)
            target_version_id: Version ID of target (optional)
            source_columns: Source columns involved
            target_columns: Target columns affected
            sync_job_id: Associated sync job ID
            execution_id: Associated execution ID
            tenant_id: Tenant ID for isolation
            user_id: User performing the operation
            
        Returns:
            Created DataLineageRecord
        """
        with self.get_session() as session:
            record = DataLineageRecord(
                source_entity_type=source_entity_type,
                source_entity_id=source_entity_id,
                source_version_id=source_version_id,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                target_version_id=target_version_id,
                relationship_type=relationship_type,
                transformation_info=transformation_info or {},
                source_columns=source_columns,
                target_columns=target_columns,
                sync_job_id=sync_job_id,
                execution_id=execution_id,
                tenant_id=tenant_id,
                created_by=user_id,
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            # Also update in-memory graph
            self._update_graph(record)
            
            logger.info(
                f"Tracked lineage: {source_entity_type}/{source_entity_id} "
                f"-> {target_entity_type}/{target_entity_id} ({relationship_type.value})"
            )
            
            return record

    def _update_graph(self, record: DataLineageRecord):
        """Update in-memory graph with lineage record."""
        # Create source node if not exists
        source_node_id = f"{record.source_entity_type}_{record.source_entity_id}"
        if source_node_id not in self.graph.nodes:
            source_node = LineageNode(
                id=source_node_id,
                node_type=LineageNodeType.SOURCE,
                name=f"{record.source_entity_type}:{record.source_entity_id}",
                source_id=str(record.source_entity_id),
            )
            self.graph.add_node(source_node)
        
        # Create target node if not exists
        target_node_id = f"{record.target_entity_type}_{record.target_entity_id}"
        if target_node_id not in self.graph.nodes:
            target_node = LineageNode(
                id=target_node_id,
                node_type=LineageNodeType.TARGET,
                name=f"{record.target_entity_type}:{record.target_entity_id}",
                source_id=str(record.target_entity_id),
            )
            self.graph.add_node(target_node)
        
        # Create edge
        edge = LineageEdge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=LineageEdgeType.TRANSFORMATION,
            transformation_rule=record.relationship_type.value,
            sync_job_id=str(record.sync_job_id) if record.sync_job_id else None,
        )
        self.graph.add_edge(edge)
    
    def get_lineage_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        direction: str = "both",  # "upstream", "downstream", "both"
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[DataLineageRecord]:
        """
        Get lineage records for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            direction: Direction to search (upstream, downstream, both)
            tenant_id: Tenant ID for isolation
            limit: Maximum records to return
            
        Returns:
            List of lineage records
        """
        with self.get_session() as session:
            conditions = []
            
            if direction in ("upstream", "both"):
                conditions.append(and_(
                    DataLineageRecord.target_entity_type == entity_type,
                    DataLineageRecord.target_entity_id == entity_id
                ))
            
            if direction in ("downstream", "both"):
                conditions.append(and_(
                    DataLineageRecord.source_entity_type == entity_type,
                    DataLineageRecord.source_entity_id == entity_id
                ))
            
            stmt = select(DataLineageRecord).where(or_(*conditions))
            
            if tenant_id:
                stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
            
            stmt = stmt.order_by(DataLineageRecord.created_at.desc()).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())

    def get_full_lineage_path(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str] = None,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Get full lineage path for an entity (both upstream and downstream).
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            tenant_id: Tenant ID
            max_depth: Maximum traversal depth
            
        Returns:
            Dictionary with upstream and downstream lineage
        """
        upstream = self._traverse_lineage(
            entity_type, entity_id, "upstream", tenant_id, max_depth
        )
        downstream = self._traverse_lineage(
            entity_type, entity_id, "downstream", tenant_id, max_depth
        )
        
        return {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "upstream": upstream,
            "downstream": downstream,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
        }
    
    def _traverse_lineage(
        self,
        entity_type: str,
        entity_id: UUID,
        direction: str,
        tenant_id: Optional[str],
        max_depth: int,
        visited: Optional[Set[str]] = None,
        current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """Recursively traverse lineage in specified direction."""
        if visited is None:
            visited = set()
        
        if current_depth >= max_depth:
            return []
        
        key = f"{entity_type}:{entity_id}"
        if key in visited:
            return []
        visited.add(key)
        
        records = self.get_lineage_for_entity(
            entity_type, entity_id, direction, tenant_id, limit=50
        )
        
        result = []
        for record in records:
            if direction == "upstream":
                next_type = record.source_entity_type
                next_id = record.source_entity_id
            else:
                next_type = record.target_entity_type
                next_id = record.target_entity_id
            
            entry = {
                "entity_type": next_type,
                "entity_id": str(next_id),
                "relationship": record.relationship_type.value,
                "depth": current_depth + 1,
                "transformation_info": record.transformation_info,
            }
            
            # Recursively get children
            children = self._traverse_lineage(
                next_type, next_id, direction, tenant_id,
                max_depth, visited, current_depth + 1
            )
            if children:
                entry["children"] = children
            
            result.append(entry)
        
        return result

    def get_column_lineage(
        self,
        entity_type: str,
        entity_id: UUID,
        column_name: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get column-level lineage for a specific column.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            column_name: Column name to trace
            tenant_id: Tenant ID
            
        Returns:
            List of column lineage entries
        """
        with self.get_session() as session:
            # Find records where this column is in source or target
            stmt = select(DataLineageRecord).where(
                or_(
                    and_(
                        DataLineageRecord.source_entity_type == entity_type,
                        DataLineageRecord.source_entity_id == entity_id,
                        DataLineageRecord.source_columns.contains([column_name])
                    ),
                    and_(
                        DataLineageRecord.target_entity_type == entity_type,
                        DataLineageRecord.target_entity_id == entity_id,
                        DataLineageRecord.target_columns.contains([column_name])
                    )
                )
            )
            
            if tenant_id:
                stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            records = result.scalars().all()
            
            return [
                {
                    "record_id": str(r.id),
                    "source": f"{r.source_entity_type}:{r.source_entity_id}",
                    "target": f"{r.target_entity_type}:{r.target_entity_id}",
                    "source_columns": r.source_columns,
                    "target_columns": r.target_columns,
                    "relationship": r.relationship_type.value,
                }
                for r in records
            ]
    
    def get_lineage_statistics(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get lineage statistics."""
        with self.get_session() as session:
            base_filter = []
            if tenant_id:
                base_filter.append(DataLineageRecord.tenant_id == tenant_id)
            
            # Total records
            total_stmt = select(func.count(DataLineageRecord.id))
            if base_filter:
                total_stmt = total_stmt.where(*base_filter)
            total = session.execute(total_stmt).scalar() or 0
            
            # By relationship type
            type_stmt = select(
                DataLineageRecord.relationship_type,
                func.count(DataLineageRecord.id)
            ).group_by(DataLineageRecord.relationship_type)
            if base_filter:
                type_stmt = type_stmt.where(*base_filter)
            type_results = session.execute(type_stmt).all()
            by_type = {str(t.value) if t else "unknown": c for t, c in type_results}
            
            # By entity type
            source_stmt = select(
                DataLineageRecord.source_entity_type,
                func.count(DataLineageRecord.id)
            ).group_by(DataLineageRecord.source_entity_type)
            if base_filter:
                source_stmt = source_stmt.where(*base_filter)
            source_results = session.execute(source_stmt).all()
            by_source = {t: c for t, c in source_results}
            
            return {
                "total_records": total,
                "by_relationship_type": by_type,
                "by_source_entity_type": by_source,
                "generated_at": datetime.utcnow().isoformat(),
            }


# Global instance
enhanced_lineage_tracker = EnhancedLineageTracker()
