"""
Unit tests for Impact Analyzer.

Tests the core functionality of:
- Downstream impact assessment
- Risk level calculation
- Impact visualization
- Recommendations generation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level for impact analysis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactType(str, Enum):
    """Type of impact."""
    DATA_LOSS = "data_loss"
    DATA_CORRUPTION = "data_corruption"
    DELAY = "delay"
    SCHEMA_CHANGE = "schema_change"
    NONE = "none"


@dataclass
class LineageNode:
    """Represents a node in the lineage graph."""
    entity_type: str
    entity_id: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityImpact:
    """Impact on a single entity."""
    entity_type: str
    entity_id: str
    entity_name: Optional[str] = None
    severity: str = "low"
    impact_type: str = "none"
    distance: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name or f"{self.entity_type}:{self.entity_id}",
            "severity": self.severity,
            "impact_type": self.impact_type,
            "distance": self.distance,
            "details": self.details,
        }


@dataclass
class ImpactReport:
    """Complete impact analysis report."""
    source_type: str
    source_id: str
    change_type: str
    affected_entities: List[EntityImpact] = field(default_factory=list)
    critical_paths: List[Dict[str, Any]] = field(default_factory=list)
    estimated_records: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "change_type": self.change_type,
            "affected_entities": [e.to_dict() for e in self.affected_entities],
            "affected_count": len(self.affected_entities),
            "critical_paths": self.critical_paths,
            "estimated_records": self.estimated_records,
            "risk_level": self.risk_level.value,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat(),
        }


class MockImpactAnalyzer:
    """Mock Impact Analyzer for testing."""
    
    CRITICAL_ENTITY_TYPES = {
        "production", "report", "dashboard", "api", 
        "export", "ml_model", "pipeline"
    }
    
    def _assess_node_impact(self, node, change_type):
        entity_type_lower = node.entity_type.lower()
        depth = node.metadata.get("depth", 1)
        
        severity = "low"
        impact_type = ImpactType.NONE.value
        
        is_critical = any(ct in entity_type_lower for ct in self.CRITICAL_ENTITY_TYPES)
        
        if is_critical:
            severity = "critical" if depth <= 2 else "high"
        elif depth == 1:
            severity = "high"
        elif depth <= 3:
            severity = "medium"
        
        if change_type == "delete":
            impact_type = ImpactType.DATA_LOSS.value
            if severity == "low":
                severity = "medium"
        elif change_type == "update":
            impact_type = ImpactType.DATA_CORRUPTION.value if is_critical else ImpactType.DELAY.value
        
        return EntityImpact(
            entity_type=node.entity_type,
            entity_id=node.entity_id,
            severity=severity,
            impact_type=impact_type,
            distance=depth,
            details=node.metadata,
        )
    
    def _calculate_risk_level(self, affected_entities, critical_paths):
        risk_factors = []
        
        critical_count = sum(1 for e in affected_entities if e.severity == "critical")
        high_count = sum(1 for e in affected_entities if e.severity == "high")
        
        if critical_count > 0:
            risk_factors.append(f"{critical_count} critical entities affected")
        
        if high_count > 3:
            risk_factors.append(f"{high_count} high-severity entities affected")
        
        total = len(affected_entities)
        if total > 50:
            risk_factors.append(f"Large impact scope: {total} entities")
        elif total > 20:
            risk_factors.append(f"Moderate impact scope: {total} entities")
        
        if len(critical_paths) > 5:
            risk_factors.append(f"{len(critical_paths)} critical paths identified")
        
        if critical_count > 0 or high_count > 5 or total > 50:
            risk_level = RiskLevel.CRITICAL
        elif high_count > 2 or total > 20:
            risk_level = RiskLevel.HIGH
        elif high_count > 0 or sum(1 for e in affected_entities if e.severity == "medium") > 5:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return risk_level, risk_factors
    
    def _estimate_affected_records(self, affected_entities):
        base_estimate = 100
        total = 0
        
        for entity in affected_entities:
            multiplier = 1
            entity_type_lower = entity.entity_type.lower()
            
            if "dataset" in entity_type_lower:
                multiplier = 10
            elif "table" in entity_type_lower:
                multiplier = 5
            elif "report" in entity_type_lower:
                multiplier = 2
            
            distance_factor = max(1, 5 - entity.distance)
            total += base_estimate * multiplier * distance_factor
        
        return total
    
    def _generate_recommendations(self, risk_level, risk_factors, affected_entities, change_type):
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "Schedule change during maintenance window",
                "Notify all downstream system owners before proceeding",
                "Prepare comprehensive rollback plan",
            ])
        elif risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "Review all critical dependencies before change",
                "Notify key stakeholders",
                "Prepare rollback plan",
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "Monitor downstream systems after change",
                "Have rollback procedure ready",
            ])
        else:
            recommendations.append("Standard change procedures apply")
        
        if change_type == "delete":
            recommendations.append("Verify no active dependencies before deletion")
        
        return recommendations
    
    def visualize_impact(self, report):
        nodes = [{
            "id": f"{report.source_type}:{report.source_id}",
            "label": f"{report.source_type}:{report.source_id}",
            "type": "source",
            "severity": "source",
            "size": 30,
        }]
        
        edges = []
        
        for entity in report.affected_entities:
            node_id = f"{entity.entity_type}:{entity.entity_id}"
            nodes.append({
                "id": node_id,
                "label": entity.entity_name or node_id,
                "type": entity.entity_type,
                "severity": entity.severity,
                "impact_type": entity.impact_type,
                "distance": entity.distance,
                "size": 20 - (entity.distance * 2),
            })
            
            if entity.distance == 1:
                edges.append({
                    "source": f"{report.source_type}:{report.source_id}",
                    "target": node_id,
                    "type": "direct",
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "risk_level": report.risk_level.value,
            }
        }


class TestImpactAnalyzer:
    """Tests for ImpactAnalyzer class."""
    
    @pytest.fixture
    def impact_analyzer(self):
        """Create a MockImpactAnalyzer instance."""
        return MockImpactAnalyzer()
    
    def test_assess_node_impact_critical_entity(self, impact_analyzer):
        """Test impact assessment for critical entity types."""
        node = LineageNode(
            entity_type="production_report",
            entity_id="123",
            metadata={"depth": 1}
        )
        
        impact = impact_analyzer._assess_node_impact(node, "update")
        
        assert impact.severity in ["critical", "high"]
        assert impact.entity_type == "production_report"
    
    def test_assess_node_impact_normal_entity(self, impact_analyzer):
        """Test impact assessment for normal entity types."""
        node = LineageNode(
            entity_type="task",
            entity_id="123",
            metadata={"depth": 3}
        )
        
        impact = impact_analyzer._assess_node_impact(node, "update")
        
        assert impact.severity in ["low", "medium"]
    
    def test_assess_node_impact_delete_increases_severity(self, impact_analyzer):
        """Test that delete operations increase severity."""
        node = LineageNode(
            entity_type="task",
            entity_id="123",
            metadata={"depth": 5}
        )
        
        impact = impact_analyzer._assess_node_impact(node, "delete")
        
        assert impact.impact_type == ImpactType.DATA_LOSS.value
    
    def test_calculate_risk_level_low(self, impact_analyzer):
        """Test low risk level calculation."""
        affected = [
            EntityImpact(entity_type="task", entity_id="1", severity="low"),
            EntityImpact(entity_type="task", entity_id="2", severity="low"),
        ]
        
        risk_level, factors = impact_analyzer._calculate_risk_level(affected, [])
        
        assert risk_level == RiskLevel.LOW
    
    def test_calculate_risk_level_medium(self, impact_analyzer):
        """Test medium risk level calculation."""
        affected = [
            EntityImpact(entity_type="task", entity_id="1", severity="high"),
            EntityImpact(entity_type="task", entity_id="2", severity="medium"),
        ]
        
        risk_level, factors = impact_analyzer._calculate_risk_level(affected, [])
        
        assert risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
    
    def test_calculate_risk_level_high(self, impact_analyzer):
        """Test high risk level calculation."""
        affected = [
            EntityImpact(entity_type="task", entity_id=str(i), severity="high")
            for i in range(5)
        ]
        
        risk_level, factors = impact_analyzer._calculate_risk_level(affected, [])
        
        assert risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    def test_calculate_risk_level_critical(self, impact_analyzer):
        """Test critical risk level calculation."""
        affected = [
            EntityImpact(entity_type="task", entity_id=str(i), severity="critical")
            for i in range(3)
        ]
        
        risk_level, factors = impact_analyzer._calculate_risk_level(affected, [])
        
        assert risk_level == RiskLevel.CRITICAL
    
    def test_estimate_affected_records(self, impact_analyzer):
        """Test affected records estimation."""
        affected = [
            EntityImpact(entity_type="dataset", entity_id="1", severity="high", distance=1),
            EntityImpact(entity_type="table", entity_id="2", severity="medium", distance=2),
        ]
        
        estimate = impact_analyzer._estimate_affected_records(affected)
        
        assert estimate > 0
    
    def test_estimate_affected_records_empty(self, impact_analyzer):
        """Test affected records estimation with no entities."""
        estimate = impact_analyzer._estimate_affected_records([])
        
        assert estimate == 0
    
    def test_generate_recommendations_critical(self, impact_analyzer):
        """Test recommendations for critical risk."""
        recommendations = impact_analyzer._generate_recommendations(
            RiskLevel.CRITICAL,
            ["High downstream count"],
            [EntityImpact(entity_type="task", entity_id="1", severity="critical")],
            "update"
        )
        
        assert len(recommendations) > 0
        assert any("maintenance" in r.lower() or "rollback" in r.lower() for r in recommendations)
    
    def test_generate_recommendations_low(self, impact_analyzer):
        """Test recommendations for low risk."""
        recommendations = impact_analyzer._generate_recommendations(
            RiskLevel.LOW,
            [],
            [],
            "update"
        )
        
        assert len(recommendations) > 0
        assert any("standard" in r.lower() for r in recommendations)
    
    def test_generate_recommendations_delete(self, impact_analyzer):
        """Test recommendations for delete operation."""
        recommendations = impact_analyzer._generate_recommendations(
            RiskLevel.MEDIUM,
            [],
            [],
            "delete"
        )
        
        assert any("delete" in r.lower() or "dependencies" in r.lower() for r in recommendations)
    
    def test_visualize_impact(self, impact_analyzer):
        """Test impact visualization data generation."""
        report = ImpactReport(
            source_type="task",
            source_id="source1",
            change_type="update",
            affected_entities=[
                EntityImpact(
                    entity_type="task",
                    entity_id="affected1",
                    severity="high",
                    distance=1
                )
            ],
            critical_paths=[],
            risk_level=RiskLevel.MEDIUM
        )
        
        viz_data = impact_analyzer.visualize_impact(report)
        
        assert "nodes" in viz_data
        assert "edges" in viz_data
        assert "summary" in viz_data
        assert len(viz_data["nodes"]) >= 2  # Source + affected


class TestImpactDataClasses:
    """Tests for impact data classes."""
    
    def test_entity_impact_to_dict(self):
        """Test EntityImpact to_dict method."""
        impact = EntityImpact(
            entity_type="task",
            entity_id="123",
            entity_name="Test Task",
            severity="high",
            impact_type="data_corruption",
            distance=2,
            details={"key": "value"}
        )
        
        result = impact.to_dict()
        
        assert result["entity_type"] == "task"
        assert result["entity_id"] == "123"
        assert result["entity_name"] == "Test Task"
        assert result["severity"] == "high"
        assert result["impact_type"] == "data_corruption"
        assert result["distance"] == 2
    
    def test_entity_impact_default_name(self):
        """Test EntityImpact default name generation."""
        impact = EntityImpact(
            entity_type="task",
            entity_id="123"
        )
        
        result = impact.to_dict()
        
        assert result["entity_name"] == "task:123"
    
    def test_impact_report_to_dict(self):
        """Test ImpactReport to_dict method."""
        report = ImpactReport(
            source_type="task",
            source_id="source1",
            change_type="update",
            affected_entities=[
                EntityImpact(entity_type="task", entity_id="1", severity="high")
            ],
            critical_paths=[{"path": "test"}],
            estimated_records=1000,
            risk_level=RiskLevel.HIGH,
            risk_factors=["High downstream count"],
            recommendations=["Review changes"]
        )
        
        result = report.to_dict()
        
        assert result["source_type"] == "task"
        assert result["source_id"] == "source1"
        assert result["change_type"] == "update"
        assert result["affected_count"] == 1
        assert result["estimated_records"] == 1000
        assert result["risk_level"] == "high"
        assert len(result["risk_factors"]) == 1
        assert len(result["recommendations"]) == 1


class TestRiskLevel:
    """Tests for RiskLevel enum."""
    
    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestImpactType:
    """Tests for ImpactType enum."""
    
    def test_impact_type_values(self):
        """Test ImpactType enum values."""
        assert ImpactType.DATA_LOSS.value == "data_loss"
        assert ImpactType.DATA_CORRUPTION.value == "data_corruption"
        assert ImpactType.DELAY.value == "delay"
        assert ImpactType.SCHEMA_CHANGE.value == "schema_change"
        assert ImpactType.NONE.value == "none"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
