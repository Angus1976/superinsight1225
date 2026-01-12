"""
Data Lineage Tracker Module.

Provides comprehensive data lineage tracking for sync operations:
- Source-to-target data flow tracking
- Transformation lineage
- Impact analysis
- Lineage visualization data
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
from collections import defaultdict

logger = logging.getLogger(__name__)


class LineageNodeType(str, Enum):
    """Types of lineage nodes."""
    SOURCE = "source"
    TARGET = "target"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    AGGREGATION = "aggregation"
    FILTER = "filter"
    JOIN = "join"
    SPLIT = "split"


class LineageEdgeType(str, Enum):
    """Types of lineage edges."""
    DATA_FLOW = "data_flow"
    TRANSFORMATION = "transformation"
    DERIVATION = "derivation"
    AGGREGATION = "aggregation"
    REFERENCE = "reference"


@dataclass
class LineageNode:
    """Represents a node in the lineage graph."""
    id: str = field(default_factory=lambda: str(uuid4()))
    node_type: LineageNodeType = LineageNodeType.SOURCE
    name: str = ""
    description: str = ""
    source_id: Optional[str] = None
    table_name: Optional[str] = None
    field_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "source_id": self.source_id,
            "table_name": self.table_name,
            "field_name": self.field_name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class LineageEdge:
    """Represents an edge in the lineage graph."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_node_id: str = ""
    target_node_id: str = ""
    edge_type: LineageEdgeType = LineageEdgeType.DATA_FLOW
    transformation_rule: Optional[str] = None
    sync_job_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type.value,
            "transformation_rule": self.transformation_rule,
            "sync_job_id": self.sync_job_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class LineageRecord:
    """Records lineage for a single data record."""
    record_id: str
    source_node_id: str
    target_node_id: str
    sync_job_id: str
    transformation_applied: List[str] = field(default_factory=list)
    source_checksum: Optional[str] = None
    target_checksum: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "sync_job_id": self.sync_job_id,
            "transformation_applied": self.transformation_applied,
            "source_checksum": self.source_checksum,
            "target_checksum": self.target_checksum,
            "timestamp": self.timestamp.isoformat()
        }


class LineageGraph:
    """
    In-memory lineage graph for tracking data flow.
    
    Provides graph operations for lineage analysis.
    """

    def __init__(self):
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: Dict[str, LineageEdge] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)  # node_id -> set of edge_ids
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: LineageNode) -> str:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        return node.id

    def add_edge(self, edge: LineageEdge) -> str:
        """Add an edge to the graph."""
        self.edges[edge.id] = edge
        self.adjacency[edge.source_node_id].add(edge.id)
        self.reverse_adjacency[edge.target_node_id].add(edge.id)
        return edge.id

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[LineageEdge]:
        """Get an edge by ID."""
        return self.edges.get(edge_id)

    def get_downstream(self, node_id: str, depth: int = -1) -> List[LineageNode]:
        """Get all downstream nodes from a given node."""
        visited = set()
        result = []
        self._traverse_downstream(node_id, visited, result, depth, 0)
        return result

    def _traverse_downstream(
        self,
        node_id: str,
        visited: Set[str],
        result: List[LineageNode],
        max_depth: int,
        current_depth: int
    ):
        """Recursively traverse downstream nodes."""
        if node_id in visited:
            return
        if max_depth >= 0 and current_depth > max_depth:
            return
        
        visited.add(node_id)
        
        for edge_id in self.adjacency.get(node_id, set()):
            edge = self.edges.get(edge_id)
            if edge:
                target_node = self.nodes.get(edge.target_node_id)
                if target_node and target_node.id not in visited:
                    result.append(target_node)
                    self._traverse_downstream(
                        target_node.id, visited, result, max_depth, current_depth + 1
                    )

    def get_upstream(self, node_id: str, depth: int = -1) -> List[LineageNode]:
        """Get all upstream nodes from a given node."""
        visited = set()
        result = []
        self._traverse_upstream(node_id, visited, result, depth, 0)
        return result

    def _traverse_upstream(
        self,
        node_id: str,
        visited: Set[str],
        result: List[LineageNode],
        max_depth: int,
        current_depth: int
    ):
        """Recursively traverse upstream nodes."""
        if node_id in visited:
            return
        if max_depth >= 0 and current_depth > max_depth:
            return
        
        visited.add(node_id)
        
        for edge_id in self.reverse_adjacency.get(node_id, set()):
            edge = self.edges.get(edge_id)
            if edge:
                source_node = self.nodes.get(edge.source_node_id)
                if source_node and source_node.id not in visited:
                    result.append(source_node)
                    self._traverse_upstream(
                        source_node.id, visited, result, max_depth, current_depth + 1
                    )

    def get_path(self, source_id: str, target_id: str) -> List[LineageEdge]:
        """Find path between two nodes using BFS."""
        if source_id == target_id:
            return []
        
        visited = {source_id}
        queue = [(source_id, [])]
        
        while queue:
            current_id, path = queue.pop(0)
            
            for edge_id in self.adjacency.get(current_id, set()):
                edge = self.edges.get(edge_id)
                if not edge:
                    continue
                
                if edge.target_node_id == target_id:
                    return path + [edge]
                
                if edge.target_node_id not in visited:
                    visited.add(edge.target_node_id)
                    queue.append((edge.target_node_id, path + [edge]))
        
        return []  # No path found

    def to_visualization_data(self) -> Dict[str, Any]:
        """Export graph data for visualization."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.name,
                    "type": node.node_type.value,
                    "data": node.to_dict()
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source": edge.source_node_id,
                    "target": edge.target_node_id,
                    "type": edge.edge_type.value,
                    "label": edge.transformation_rule or ""
                }
                for edge in self.edges.values()
            ]
        }


class LineageTracker:
    """
    Comprehensive lineage tracker for data sync operations.
    
    Tracks data flow, transformations, and provides impact analysis.
    """

    def __init__(self):
        self.graph = LineageGraph()
        self.record_lineage: Dict[str, List[LineageRecord]] = defaultdict(list)
        self.sync_job_lineage: Dict[str, List[str]] = defaultdict(list)  # job_id -> record_ids

    def register_source(
        self,
        source_id: str,
        name: str,
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a data source in the lineage graph."""
        node = LineageNode(
            id=f"source_{source_id}",
            node_type=LineageNodeType.SOURCE,
            name=name,
            source_id=source_id,
            table_name=table_name,
            metadata=metadata or {}
        )
        return self.graph.add_node(node)

    def register_target(
        self,
        target_id: str,
        name: str,
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a data target in the lineage graph."""
        node = LineageNode(
            id=f"target_{target_id}",
            node_type=LineageNodeType.TARGET,
            name=name,
            source_id=target_id,
            table_name=table_name,
            metadata=metadata or {}
        )
        return self.graph.add_node(node)

    def register_transformation(
        self,
        transform_id: str,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a transformation step in the lineage graph."""
        node = LineageNode(
            id=f"transform_{transform_id}",
            node_type=LineageNodeType.TRANSFORMATION,
            name=name,
            description=description,
            metadata=metadata or {}
        )
        return self.graph.add_node(node)

    def add_data_flow(
        self,
        source_node_id: str,
        target_node_id: str,
        sync_job_id: Optional[str] = None,
        transformation_rule: Optional[str] = None,
        edge_type: LineageEdgeType = LineageEdgeType.DATA_FLOW
    ) -> str:
        """Add a data flow edge between nodes."""
        edge = LineageEdge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            transformation_rule=transformation_rule,
            sync_job_id=sync_job_id
        )
        return self.graph.add_edge(edge)

    def track_record(
        self,
        record_id: str,
        source_node_id: str,
        target_node_id: str,
        sync_job_id: str,
        source_data: Optional[Dict[str, Any]] = None,
        target_data: Optional[Dict[str, Any]] = None,
        transformations: Optional[List[str]] = None
    ) -> LineageRecord:
        """Track lineage for a single record."""
        # Calculate checksums
        source_checksum = None
        target_checksum = None
        
        if source_data:
            source_checksum = hashlib.md5(
                str(sorted(source_data.items())).encode()
            ).hexdigest()
        
        if target_data:
            target_checksum = hashlib.md5(
                str(sorted(target_data.items())).encode()
            ).hexdigest()
        
        record = LineageRecord(
            record_id=record_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            sync_job_id=sync_job_id,
            transformation_applied=transformations or [],
            source_checksum=source_checksum,
            target_checksum=target_checksum
        )
        
        self.record_lineage[record_id].append(record)
        self.sync_job_lineage[sync_job_id].append(record_id)
        
        return record

    def track_batch(
        self,
        records: List[Dict[str, Any]],
        source_node_id: str,
        target_node_id: str,
        sync_job_id: str,
        id_field: str = "id",
        transformations: Optional[List[str]] = None
    ) -> List[LineageRecord]:
        """Track lineage for a batch of records."""
        lineage_records = []
        
        for record in records:
            record_id = str(record.get(id_field, uuid4()))
            lineage_record = self.track_record(
                record_id=record_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                sync_job_id=sync_job_id,
                source_data=record,
                transformations=transformations
            )
            lineage_records.append(lineage_record)
        
        return lineage_records

    def get_record_lineage(self, record_id: str) -> List[LineageRecord]:
        """Get all lineage records for a specific record."""
        return self.record_lineage.get(record_id, [])

    def get_job_lineage(self, sync_job_id: str) -> List[str]:
        """Get all record IDs processed by a sync job."""
        return self.sync_job_lineage.get(sync_job_id, [])

    def get_downstream_impact(self, node_id: str) -> Dict[str, Any]:
        """Analyze downstream impact of a node."""
        downstream = self.graph.get_downstream(node_id)
        
        return {
            "source_node": self.graph.get_node(node_id).to_dict() if self.graph.get_node(node_id) else None,
            "impacted_nodes": [n.to_dict() for n in downstream],
            "impact_count": len(downstream),
            "impact_by_type": self._count_by_type(downstream)
        }

    def get_upstream_sources(self, node_id: str) -> Dict[str, Any]:
        """Get all upstream sources for a node."""
        upstream = self.graph.get_upstream(node_id)
        
        return {
            "target_node": self.graph.get_node(node_id).to_dict() if self.graph.get_node(node_id) else None,
            "source_nodes": [n.to_dict() for n in upstream],
            "source_count": len(upstream),
            "sources_by_type": self._count_by_type(upstream)
        }

    def _count_by_type(self, nodes: List[LineageNode]) -> Dict[str, int]:
        """Count nodes by type."""
        counts = defaultdict(int)
        for node in nodes:
            counts[node.node_type.value] += 1
        return dict(counts)

    def get_data_flow_path(
        self,
        source_id: str,
        target_id: str
    ) -> Dict[str, Any]:
        """Get the data flow path between source and target."""
        path = self.graph.get_path(source_id, target_id)
        
        if not path:
            return {
                "path_exists": False,
                "source_id": source_id,
                "target_id": target_id,
                "edges": [],
                "nodes": []
            }
        
        # Collect nodes in path
        node_ids = {source_id}
        for edge in path:
            node_ids.add(edge.target_node_id)
        
        nodes = [
            self.graph.get_node(nid).to_dict()
            for nid in node_ids
            if self.graph.get_node(nid)
        ]
        
        return {
            "path_exists": True,
            "source_id": source_id,
            "target_id": target_id,
            "edges": [e.to_dict() for e in path],
            "nodes": nodes,
            "hop_count": len(path)
        }

    def get_visualization_data(
        self,
        filter_job_id: Optional[str] = None,
        filter_source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get lineage data formatted for visualization."""
        viz_data = self.graph.to_visualization_data()
        
        # Apply filters if specified
        if filter_job_id:
            relevant_edges = [
                e for e in viz_data["edges"]
                if self.graph.get_edge(e["id"]) and 
                self.graph.get_edge(e["id"]).sync_job_id == filter_job_id
            ]
            relevant_node_ids = set()
            for e in relevant_edges:
                relevant_node_ids.add(e["source"])
                relevant_node_ids.add(e["target"])
            
            viz_data["edges"] = relevant_edges
            viz_data["nodes"] = [
                n for n in viz_data["nodes"]
                if n["id"] in relevant_node_ids
            ]
        
        if filter_source_id:
            source_node_id = f"source_{filter_source_id}"
            downstream = self.graph.get_downstream(source_node_id)
            downstream_ids = {n.id for n in downstream}
            downstream_ids.add(source_node_id)
            
            viz_data["nodes"] = [
                n for n in viz_data["nodes"]
                if n["id"] in downstream_ids
            ]
            viz_data["edges"] = [
                e for e in viz_data["edges"]
                if e["source"] in downstream_ids and e["target"] in downstream_ids
            ]
        
        return viz_data

    def generate_lineage_report(
        self,
        sync_job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive lineage report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "nodes_by_type": {},
            "edges_by_type": {},
            "sync_jobs": {}
        }
        
        # Count nodes by type
        for node in self.graph.nodes.values():
            node_type = node.node_type.value
            report["nodes_by_type"][node_type] = report["nodes_by_type"].get(node_type, 0) + 1
        
        # Count edges by type
        for edge in self.graph.edges.values():
            edge_type = edge.edge_type.value
            report["edges_by_type"][edge_type] = report["edges_by_type"].get(edge_type, 0) + 1
        
        # Sync job statistics
        for job_id, record_ids in self.sync_job_lineage.items():
            if sync_job_id and job_id != sync_job_id:
                continue
            
            report["sync_jobs"][job_id] = {
                "records_tracked": len(record_ids),
                "unique_records": len(set(record_ids))
            }
        
        return report


# Global instance
lineage_tracker = LineageTracker()
