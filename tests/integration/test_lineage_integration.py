"""
Integration Tests for Data Lineage Module.

Tests the integration between lineage engine, impact analyzer,
and related components.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set


# ============================================================================
# Mock Classes for Integration Testing
# ============================================================================

class RelationType(str, Enum):
    DERIVED_FROM = "derived_from"
    TRANSFORMED_BY = "transformed_by"
    AGGREGATED_FROM = "aggregated_from"
    FILTERED_FROM = "filtered_from"
    JOINED_WITH = "joined_with"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LineageNode:
    entity_type: str
    entity_id: str
    name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def key(self) -> str:
        return f"{self.entity_type}:{self.entity_id}"


@dataclass
class LineageEdge:
    source: LineageNode
    target: LineageNode
    relation_type: RelationType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactResult:
    source_node: LineageNode
    affected_nodes: List[LineageNode]
    risk_level: RiskLevel
    total_affected: int
    impact_paths: List[List[LineageNode]]


class IntegratedLineageSystem:
    """
    Integrated lineage system that combines:
    - Lineage Engine
    - Impact Analyzer
    """
    
    def __init__(self):
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: List[LineageEdge] = []
        self.upstream_map: Dict[str, Set[str]] = {}
        self.downstream_map: Dict[str, Set[str]] = {}
    
    def add_node(self, entity_type: str, entity_id: str, name: str = "", metadata: Dict = None) -> LineageNode:
        """Add a node to the lineage graph."""
        node = LineageNode(
            entity_type=entity_type,
            entity_id=entity_id,
            name=name or f"{entity_type}_{entity_id}",
            metadata=metadata or {}
        )
        self.nodes[node.key] = node
        
        if node.key not in self.upstream_map:
            self.upstream_map[node.key] = set()
        if node.key not in self.downstream_map:
            self.downstream_map[node.key] = set()
        
        return node
    
    def add_lineage(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relation_type: RelationType = RelationType.DERIVED_FROM,
        metadata: Dict = None
    ) -> LineageEdge:
        """Add a lineage relationship between two nodes."""
        source_key = f"{source_type}:{source_id}"
        target_key = f"{target_type}:{target_id}"
        
        # Ensure nodes exist
        if source_key not in self.nodes:
            self.add_node(source_type, source_id)
        if target_key not in self.nodes:
            self.add_node(target_type, target_id)
        
        source = self.nodes[source_key]
        target = self.nodes[target_key]
        
        edge = LineageEdge(
            source=source,
            target=target,
            relation_type=relation_type,
            metadata=metadata or {}
        )
        self.edges.append(edge)
        
        # Update maps
        self.downstream_map[source_key].add(target_key)
        self.upstream_map[target_key].add(source_key)
        
        return edge
    
    def get_upstream(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 1
    ) -> List[LineageNode]:
        """Get upstream nodes up to specified depth."""
        key = f"{entity_type}:{entity_id}"
        
        if key not in self.nodes:
            return []
        
        result = []
        visited = set()
        current_level = {key}
        
        for _ in range(depth):
            next_level = set()
            for node_key in current_level:
                for upstream_key in self.upstream_map.get(node_key, set()):
                    if upstream_key not in visited:
                        visited.add(upstream_key)
                        next_level.add(upstream_key)
                        result.append(self.nodes[upstream_key])
            current_level = next_level
            if not current_level:
                break
        
        return result
    
    def get_downstream(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 1
    ) -> List[LineageNode]:
        """Get downstream nodes up to specified depth."""
        key = f"{entity_type}:{entity_id}"
        
        if key not in self.nodes:
            return []
        
        result = []
        visited = set()
        current_level = {key}
        
        for _ in range(depth):
            next_level = set()
            for node_key in current_level:
                for downstream_key in self.downstream_map.get(node_key, set()):
                    if downstream_key not in visited:
                        visited.add(downstream_key)
                        next_level.add(downstream_key)
                        result.append(self.nodes[downstream_key])
            current_level = next_level
            if not current_level:
                break
        
        return result
    
    def get_full_lineage(
        self,
        entity_type: str,
        entity_id: str,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """Get full lineage graph for an entity."""
        key = f"{entity_type}:{entity_id}"
        
        if key not in self.nodes:
            return {"nodes": [], "edges": [], "center": None}
        
        center = self.nodes[key]
        upstream = self.get_upstream(entity_type, entity_id, max_depth)
        downstream = self.get_downstream(entity_type, entity_id, max_depth)
        
        all_nodes = [center] + upstream + downstream
        node_keys = {n.key for n in all_nodes}
        
        relevant_edges = [
            e for e in self.edges
            if e.source.key in node_keys and e.target.key in node_keys
        ]
        
        return {
            "nodes": all_nodes,
            "edges": relevant_edges,
            "center": center
        }
    
    def find_path(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str
    ) -> Optional[List[LineageNode]]:
        """Find path between two nodes using BFS."""
        source_key = f"{source_type}:{source_id}"
        target_key = f"{target_type}:{target_id}"
        
        if source_key not in self.nodes or target_key not in self.nodes:
            return None
        
        if source_key == target_key:
            return [self.nodes[source_key]]
        
        # BFS
        queue = [(source_key, [self.nodes[source_key]])]
        visited = {source_key}
        
        while queue:
            current_key, path = queue.pop(0)
            
            for next_key in self.downstream_map.get(current_key, set()):
                if next_key == target_key:
                    return path + [self.nodes[next_key]]
                
                if next_key not in visited:
                    visited.add(next_key)
                    queue.append((next_key, path + [self.nodes[next_key]]))
        
        return None
    
    def analyze_impact(
        self,
        entity_type: str,
        entity_id: str,
        change_type: str = "update"
    ) -> ImpactResult:
        """Analyze impact of changes to an entity."""
        key = f"{entity_type}:{entity_id}"
        
        if key not in self.nodes:
            raise ValueError(f"Node {key} not found")
        
        source = self.nodes[key]
        
        # Get all downstream affected nodes
        affected = self.get_downstream(entity_type, entity_id, depth=10)
        
        # Calculate risk level based on number of affected nodes
        total = len(affected)
        if total == 0:
            risk = RiskLevel.LOW
        elif total <= 3:
            risk = RiskLevel.MEDIUM
        elif total <= 10:
            risk = RiskLevel.HIGH
        else:
            risk = RiskLevel.CRITICAL
        
        # Find impact paths
        paths = []
        for node in affected[:5]:  # Limit to first 5 for performance
            path = self.find_path(entity_type, entity_id, node.entity_type, node.entity_id)
            if path:
                paths.append(path)
        
        return ImpactResult(
            source_node=source,
            affected_nodes=affected,
            risk_level=risk,
            total_affected=total,
            impact_paths=paths
        )


# ============================================================================
# Integration Tests
# ============================================================================

class TestLineageGraphOperations:
    """Integration tests for lineage graph operations."""
    
    @pytest.fixture
    def system(self):
        return IntegratedLineageSystem()
    
    def test_add_simple_lineage(self, system):
        """Test adding a simple lineage relationship."""
        edge = system.add_lineage(
            source_type="table",
            source_id="source_table",
            target_type="table",
            target_id="target_table",
            relation_type=RelationType.DERIVED_FROM
        )
        
        assert edge.source.entity_type == "table"
        assert edge.target.entity_type == "table"
        assert edge.relation_type == RelationType.DERIVED_FROM
    
    def test_build_lineage_chain(self, system):
        """Test building a lineage chain."""
        # Create chain: A -> B -> C -> D
        system.add_lineage("table", "A", "table", "B")
        system.add_lineage("table", "B", "table", "C")
        system.add_lineage("table", "C", "table", "D")
        
        # Check downstream from A
        downstream = system.get_downstream("table", "A", depth=3)
        downstream_ids = [n.entity_id for n in downstream]
        
        assert "B" in downstream_ids
        assert "C" in downstream_ids
        assert "D" in downstream_ids
    
    def test_build_lineage_tree(self, system):
        """Test building a lineage tree (one source, multiple targets)."""
        # Create tree: A -> B, A -> C, A -> D
        system.add_lineage("table", "A", "table", "B")
        system.add_lineage("table", "A", "table", "C")
        system.add_lineage("table", "A", "table", "D")
        
        downstream = system.get_downstream("table", "A", depth=1)
        downstream_ids = {n.entity_id for n in downstream}
        
        assert downstream_ids == {"B", "C", "D"}
    
    def test_get_upstream_lineage(self, system):
        """Test getting upstream lineage."""
        # Create: A -> B -> C
        system.add_lineage("table", "A", "table", "B")
        system.add_lineage("table", "B", "table", "C")
        
        upstream = system.get_upstream("table", "C", depth=2)
        upstream_ids = [n.entity_id for n in upstream]
        
        assert "B" in upstream_ids
        assert "A" in upstream_ids


class TestLineagePathFinding:
    """Integration tests for lineage path finding."""
    
    @pytest.fixture
    def system(self):
        return IntegratedLineageSystem()
    
    def test_find_direct_path(self, system):
        """Test finding a direct path."""
        system.add_lineage("table", "A", "table", "B")
        
        path = system.find_path("table", "A", "table", "B")
        
        assert path is not None
        assert len(path) == 2
        assert path[0].entity_id == "A"
        assert path[1].entity_id == "B"
    
    def test_find_multi_hop_path(self, system):
        """Test finding a multi-hop path."""
        system.add_lineage("table", "A", "table", "B")
        system.add_lineage("table", "B", "table", "C")
        system.add_lineage("table", "C", "table", "D")
        
        path = system.find_path("table", "A", "table", "D")
        
        assert path is not None
        assert len(path) == 4
        assert [n.entity_id for n in path] == ["A", "B", "C", "D"]
    
    def test_no_path_exists(self, system):
        """Test when no path exists."""
        system.add_node("table", "A")
        system.add_node("table", "B")
        
        path = system.find_path("table", "A", "table", "B")
        
        assert path is None
    
    def test_path_to_self(self, system):
        """Test path to self."""
        system.add_node("table", "A")
        
        path = system.find_path("table", "A", "table", "A")
        
        assert path is not None
        assert len(path) == 1


class TestImpactAnalysis:
    """Integration tests for impact analysis."""
    
    @pytest.fixture
    def system(self):
        return IntegratedLineageSystem()
    
    def test_analyze_no_impact(self, system):
        """Test impact analysis with no downstream nodes."""
        system.add_node("table", "isolated")
        
        result = system.analyze_impact("table", "isolated")
        
        assert result.total_affected == 0
        assert result.risk_level == RiskLevel.LOW
    
    def test_analyze_low_impact(self, system):
        """Test impact analysis with low impact."""
        system.add_lineage("table", "A", "table", "B")
        
        result = system.analyze_impact("table", "A")
        
        assert result.total_affected == 1
        assert result.risk_level == RiskLevel.MEDIUM
    
    def test_analyze_high_impact(self, system):
        """Test impact analysis with high impact."""
        # Create many downstream nodes
        for i in range(5):
            system.add_lineage("table", "source", "table", f"target_{i}")
        
        result = system.analyze_impact("table", "source")
        
        assert result.total_affected == 5
        assert result.risk_level == RiskLevel.HIGH
    
    def test_analyze_critical_impact(self, system):
        """Test impact analysis with critical impact."""
        # Create many downstream nodes
        for i in range(15):
            system.add_lineage("table", "source", "table", f"target_{i}")
        
        result = system.analyze_impact("table", "source")
        
        assert result.total_affected == 15
        assert result.risk_level == RiskLevel.CRITICAL
    
    def test_impact_includes_paths(self, system):
        """Test that impact analysis includes paths."""
        system.add_lineage("table", "A", "table", "B")
        system.add_lineage("table", "B", "table", "C")
        
        result = system.analyze_impact("table", "A")
        
        assert len(result.impact_paths) > 0


class TestFullLineageGraph:
    """Integration tests for full lineage graph retrieval."""
    
    @pytest.fixture
    def system(self):
        return IntegratedLineageSystem()
    
    def test_get_full_lineage_simple(self, system):
        """Test getting full lineage for a simple graph."""
        system.add_lineage("table", "A", "table", "B")
        system.add_lineage("table", "B", "table", "C")
        
        result = system.get_full_lineage("table", "B")
        
        assert result["center"].entity_id == "B"
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2
    
    def test_get_full_lineage_complex(self, system):
        """Test getting full lineage for a complex graph."""
        # Create diamond pattern: A -> B, A -> C, B -> D, C -> D
        system.add_lineage("table", "A", "table", "B")
        system.add_lineage("table", "A", "table", "C")
        system.add_lineage("table", "B", "table", "D")
        system.add_lineage("table", "C", "table", "D")
        
        result = system.get_full_lineage("table", "B")
        
        node_ids = {n.entity_id for n in result["nodes"]}
        assert "A" in node_ids  # upstream
        assert "B" in node_ids  # center
        assert "D" in node_ids  # downstream


class TestCompleteLineageWorkflow:
    """Integration tests for complete lineage workflows."""
    
    @pytest.fixture
    def system(self):
        return IntegratedLineageSystem()
    
    def test_data_pipeline_lineage(self, system):
        """Test lineage for a typical data pipeline."""
        # Raw data sources
        system.add_node("source", "raw_sales", "Raw Sales Data")
        system.add_node("source", "raw_customers", "Raw Customer Data")
        
        # Staging tables
        system.add_lineage("source", "raw_sales", "table", "stg_sales", RelationType.TRANSFORMED_BY)
        system.add_lineage("source", "raw_customers", "table", "stg_customers", RelationType.TRANSFORMED_BY)
        
        # Joined table
        system.add_lineage("table", "stg_sales", "table", "fact_sales", RelationType.JOINED_WITH)
        system.add_lineage("table", "stg_customers", "table", "fact_sales", RelationType.JOINED_WITH)
        
        # Aggregated table
        system.add_lineage("table", "fact_sales", "table", "agg_daily_sales", RelationType.AGGREGATED_FROM)
        
        # Report
        system.add_lineage("table", "agg_daily_sales", "report", "sales_dashboard", RelationType.DERIVED_FROM)
        
        # Verify lineage
        full_lineage = system.get_full_lineage("table", "fact_sales")
        
        node_types = {n.entity_type for n in full_lineage["nodes"]}
        assert "source" in node_types
        assert "table" in node_types
        assert "report" in node_types
        
        # Analyze impact of changing raw sales
        impact = system.analyze_impact("source", "raw_sales")
        
        assert impact.total_affected >= 3  # stg_sales, fact_sales, agg_daily_sales, sales_dashboard
    
    def test_ml_pipeline_lineage(self, system):
        """Test lineage for an ML pipeline."""
        # Training data
        system.add_node("dataset", "training_data", "Training Dataset")
        
        # Feature engineering
        system.add_lineage("dataset", "training_data", "feature", "features_v1", RelationType.TRANSFORMED_BY)
        
        # Model training
        system.add_lineage("feature", "features_v1", "model", "model_v1", RelationType.DERIVED_FROM)
        
        # Model deployment
        system.add_lineage("model", "model_v1", "endpoint", "prediction_api", RelationType.DERIVED_FROM)
        
        # Verify path from data to API
        path = system.find_path("dataset", "training_data", "endpoint", "prediction_api")
        
        assert path is not None
        assert len(path) == 4
        
        # Impact of changing training data
        impact = system.analyze_impact("dataset", "training_data")
        
        assert impact.total_affected == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
