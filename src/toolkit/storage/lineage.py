"""
Lineage tracking for data transformations.

Records the full provenance chain from source data through
every transformation stage to final storage.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LineageNode(BaseModel):
    """A single node in the lineage graph (source, stage, or storage)."""

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="source | transformation | storage")
    label: str = Field(default="", description="Human-readable label")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class LineageEdge(BaseModel):
    """Directed edge connecting two lineage nodes."""

    source_id: str = Field(..., description="Origin node ID")
    target_id: str = Field(..., description="Destination node ID")
    label: str = Field(default="", description="Edge description")


class LineageGraph(BaseModel):
    """Complete lineage graph for a data item."""

    data_id: str = Field(..., description="ID of the tracked data")
    nodes: List[LineageNode] = Field(default_factory=list)
    edges: List[LineageEdge] = Field(default_factory=list)

    @property
    def source_node(self) -> Optional[LineageNode]:
        """Return the root source node, if any."""
        for node in self.nodes:
            if node.node_type == "source":
                return node
        return None

    @property
    def transformation_nodes(self) -> List[LineageNode]:
        """Return all transformation nodes in order."""
        return [n for n in self.nodes if n.node_type == "transformation"]

    @property
    def storage_node(self) -> Optional[LineageNode]:
        """Return the final storage node, if any."""
        for node in self.nodes:
            if node.node_type == "storage":
                return node
        return None


class LineageTracker:
    """Tracks data lineage from source through transformations to storage."""

    def __init__(self) -> None:
        self._graphs: Dict[str, LineageGraph] = {}

    def record_source(self, data_id: str, source_label: str, **meta: Any) -> None:
        """Record the original data source as the root of the lineage."""
        node = LineageNode(
            node_id=f"{data_id}:source",
            node_type="source",
            label=source_label,
            metadata=dict(meta),
        )
        graph = LineageGraph(data_id=data_id, nodes=[node], edges=[])
        self._graphs[data_id] = graph

    def record_transformation(
        self, data_id: str, stage_name: str, **meta: Any,
    ) -> None:
        """Append a transformation stage to the lineage chain."""
        graph = self._graphs.get(data_id)
        if graph is None:
            return

        idx = len(graph.nodes)
        node = LineageNode(
            node_id=f"{data_id}:stage-{idx}",
            node_type="transformation",
            label=stage_name,
            metadata=dict(meta),
        )
        prev_id = graph.nodes[-1].node_id
        edge = LineageEdge(source_id=prev_id, target_id=node.node_id, label=stage_name)
        graph.nodes.append(node)
        graph.edges.append(edge)

    def record_storage(
        self, data_id: str, storage_label: str, **meta: Any,
    ) -> None:
        """Record the final storage destination."""
        graph = self._graphs.get(data_id)
        if graph is None:
            return

        node = LineageNode(
            node_id=f"{data_id}:storage",
            node_type="storage",
            label=storage_label,
            metadata=dict(meta),
        )
        prev_id = graph.nodes[-1].node_id
        edge = LineageEdge(source_id=prev_id, target_id=node.node_id, label="store")
        graph.nodes.append(node)
        graph.edges.append(edge)

    def get_lineage(self, data_id: str) -> Optional[LineageGraph]:
        """Return the full lineage graph for a data item."""
        return self._graphs.get(data_id)

    def has_lineage(self, data_id: str) -> bool:
        return data_id in self._graphs
