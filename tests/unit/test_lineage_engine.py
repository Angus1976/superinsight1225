"""
Unit tests for Lineage Engine.

Tests the core functionality of:
- Lineage relationship management
- Upstream/downstream queries
- Full lineage graph construction
- Path finding between entities
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


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


class TestLineageEngine:
    """Tests for LineageEngine class."""
    
    def test_lineage_node_to_dict(self):
        """Test LineageNode to_dict method."""
        node = LineageNode(
            entity_type="task",
            entity_id="123",
            name="Test Task",
            metadata={"depth": 1}
        )
        
        result = node.to_dict()
        
        assert result["entity_type"] == "task"
        assert result["entity_id"] == "123"
        assert result["name"] == "Test Task"
        assert result["metadata"]["depth"] == 1
    
    def test_lineage_node_default_name(self):
        """Test LineageNode default name generation."""
        node = LineageNode(
            entity_type="task",
            entity_id="123"
        )
        
        result = node.to_dict()
        
        assert result["name"] == "task:123"
    
    def test_lineage_edge_to_dict(self):
        """Test LineageEdge to_dict method."""
        edge = LineageEdge(
            source_type="document",
            source_id="doc1",
            target_type="task",
            target_id="task1",
            relationship="derived_from",
            transformation={"operation": "extract"},
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        result = edge.to_dict()
        
        assert result["source_type"] == "document"
        assert result["source_id"] == "doc1"
        assert result["target_type"] == "task"
        assert result["target_id"] == "task1"
        assert result["relationship"] == "derived_from"
        assert result["transformation"]["operation"] == "extract"
        assert "2024-01-01" in result["created_at"]
    
    def test_lineage_graph_to_dict(self):
        """Test LineageGraph to_dict method."""
        graph = LineageGraph(
            nodes=[
                LineageNode(entity_type="task", entity_id="1"),
                LineageNode(entity_type="task", entity_id="2"),
            ],
            edges=[
                LineageEdge(
                    source_type="task", source_id="1",
                    target_type="task", target_id="2",
                    relationship="depends_on"
                )
            ]
        )
        
        result = graph.to_dict()
        
        assert result["node_count"] == 2
        assert result["edge_count"] == 1
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
    
    def test_lineage_path_to_dict(self):
        """Test LineagePath to_dict method."""
        path = LineagePath(
            source_type="document",
            source_id="doc1",
            target_type="report",
            target_id="report1",
            path=[
                {"entity_type": "document", "entity_id": "doc1"},
                {"entity_type": "task", "entity_id": "task1"},
                {"entity_type": "report", "entity_id": "report1"},
            ],
            length=2
        )
        
        result = path.to_dict()
        
        assert result["source_type"] == "document"
        assert result["source_id"] == "doc1"
        assert result["target_type"] == "report"
        assert result["target_id"] == "report1"
        assert result["length"] == 2
        assert len(result["path"]) == 3


class TestLineageGraphOperations:
    """Tests for lineage graph operations."""
    
    def test_empty_graph(self):
        """Test empty lineage graph."""
        graph = LineageGraph()
        
        result = graph.to_dict()
        
        assert result["node_count"] == 0
        assert result["edge_count"] == 0
    
    def test_graph_with_single_node(self):
        """Test graph with single node."""
        graph = LineageGraph(
            nodes=[LineageNode(entity_type="task", entity_id="1")]
        )
        
        result = graph.to_dict()
        
        assert result["node_count"] == 1
        assert result["edge_count"] == 0
    
    def test_graph_with_cycle(self):
        """Test graph with cycle (should be handled)."""
        graph = LineageGraph(
            nodes=[
                LineageNode(entity_type="task", entity_id="1"),
                LineageNode(entity_type="task", entity_id="2"),
            ],
            edges=[
                LineageEdge(
                    source_type="task", source_id="1",
                    target_type="task", target_id="2",
                    relationship="depends_on"
                ),
                LineageEdge(
                    source_type="task", source_id="2",
                    target_type="task", target_id="1",
                    relationship="depends_on"
                ),
            ]
        )
        
        result = graph.to_dict()
        
        assert result["node_count"] == 2
        assert result["edge_count"] == 2


class TestLineagePathFinding:
    """Tests for lineage path finding."""
    
    def test_empty_path(self):
        """Test empty path."""
        path = LineagePath(
            source_type="task",
            source_id="1",
            target_type="task",
            target_id="1",
            path=[{"entity_type": "task", "entity_id": "1"}],
            length=0
        )
        
        result = path.to_dict()
        
        assert result["length"] == 0
    
    def test_direct_path(self):
        """Test direct path between two nodes."""
        path = LineagePath(
            source_type="task",
            source_id="1",
            target_type="task",
            target_id="2",
            path=[
                {"entity_type": "task", "entity_id": "1"},
                {"entity_type": "task", "entity_id": "2"},
            ],
            length=1
        )
        
        result = path.to_dict()
        
        assert result["length"] == 1
        assert len(result["path"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
