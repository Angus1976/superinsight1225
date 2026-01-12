"""
Tests for Data Version Control and Lineage Tracking.

Tests the core functionality of:
- Version creation and retrieval
- Delta calculation
- Lineage tracking
- Impact analysis
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from src.version.models import (
    DataVersion, DataVersionTag, DataVersionBranch,
    DataLineageRecord, VersionStatus, VersionType, LineageRelationType
)
from src.version.version_manager import DeltaCalculator, VersionControlManager
from src.version.query_engine import VersionQueryEngine
from src.lineage.enhanced_tracker import EnhancedLineageTracker
from src.lineage.impact_analyzer import ImpactAnalyzer, RiskLevel
from src.lineage.relationship_mapper import RelationshipMapper


class TestDeltaCalculator:
    """Tests for delta calculation."""
    
    def test_calculate_delta_added_fields(self):
        """Test delta calculation for added fields."""
        calculator = DeltaCalculator()
        old_data = {"name": "test", "value": 1}
        new_data = {"name": "test", "value": 1, "new_field": "added"}
        
        delta = calculator.calculate_delta(old_data, new_data)
        
        assert "new_field" in delta["added"]
        assert delta["added"]["new_field"] == "added"
        assert len(delta["removed"]) == 0
        assert len(delta["modified"]) == 0
    
    def test_calculate_delta_removed_fields(self):
        """Test delta calculation for removed fields."""
        calculator = DeltaCalculator()
        old_data = {"name": "test", "value": 1, "old_field": "removed"}
        new_data = {"name": "test", "value": 1}
        
        delta = calculator.calculate_delta(old_data, new_data)
        
        assert "old_field" in delta["removed"]
        assert len(delta["added"]) == 0
        assert len(delta["modified"]) == 0

    def test_calculate_delta_modified_fields(self):
        """Test delta calculation for modified fields."""
        calculator = DeltaCalculator()
        old_data = {"name": "test", "value": 1}
        new_data = {"name": "test", "value": 2}
        
        delta = calculator.calculate_delta(old_data, new_data)
        
        assert "value" in delta["modified"]
        assert delta["modified"]["value"]["old"] == 1
        assert delta["modified"]["value"]["new"] == 2
    
    def test_apply_delta(self):
        """Test applying delta to reconstruct data."""
        calculator = DeltaCalculator()
        base_data = {"name": "test", "value": 1}
        delta = {
            "added": {"new_field": "added"},
            "removed": {},
            "modified": {"value": {"old": 1, "new": 2}}
        }
        
        result = calculator.apply_delta(base_data, delta)
        
        assert result["name"] == "test"
        assert result["value"] == 2
        assert result["new_field"] == "added"
    
    def test_empty_data_delta(self):
        """Test delta calculation with empty data."""
        calculator = DeltaCalculator()
        
        delta = calculator.calculate_delta({}, {"field": "value"})
        assert "field" in delta["added"]
        
        delta = calculator.calculate_delta({"field": "value"}, {})
        assert "field" in delta["removed"]


class TestVersionModels:
    """Tests for version models."""
    
    def test_data_version_to_dict(self):
        """Test DataVersion to_dict method."""
        version = DataVersion(
            id=uuid4(),
            entity_type="task",
            entity_id=uuid4(),
            version_number=1,
            version_type=VersionType.FULL,
            status=VersionStatus.ACTIVE,
            version_data={"test": "data"},
            checksum="abc123",
            data_size_bytes=100,
            tenant_id="tenant1",
            created_by="user1",
            created_at=datetime.utcnow(),
        )
        
        result = version.to_dict()
        
        assert result["entity_type"] == "task"
        assert result["version_number"] == 1
        assert result["version_type"] == "full"
        assert result["status"] == "active"
        assert result["tenant_id"] == "tenant1"
    
    def test_lineage_record_to_dict(self):
        """Test DataLineageRecord to_dict method."""
        record = DataLineageRecord(
            id=uuid4(),
            source_entity_type="document",
            source_entity_id=uuid4(),
            target_entity_type="task",
            target_entity_id=uuid4(),
            relationship_type=LineageRelationType.DERIVED_FROM,
            transformation_info={"operation": "extract"},
            tenant_id="tenant1",
            created_at=datetime.utcnow(),
        )
        
        result = record.to_dict()
        
        assert result["source_entity_type"] == "document"
        assert result["target_entity_type"] == "task"
        assert result["relationship_type"] == "derived_from"


class TestImpactAnalyzer:
    """Tests for impact analysis."""
    
    def test_risk_assessment_low(self):
        """Test low risk assessment."""
        analyzer = ImpactAnalyzer()
        
        downstream = []
        upstream = []
        critical = []
        
        risk_level, factors = analyzer._assess_risk(downstream, upstream, critical)
        
        assert risk_level == RiskLevel.LOW
    
    def test_risk_assessment_medium(self):
        """Test medium risk assessment."""
        analyzer = ImpactAnalyzer()
        
        downstream = [{"entity_type": "task", "entity_id": str(uuid4())} for _ in range(10)]
        upstream = []
        critical = [{"entity_type": "report", "entity_id": str(uuid4())}]
        
        risk_level, factors = analyzer._assess_risk(downstream, upstream, critical)
        
        assert risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
    
    def test_risk_assessment_critical(self):
        """Test critical risk assessment."""
        analyzer = ImpactAnalyzer()
        
        downstream = [{"entity_type": "task", "entity_id": str(uuid4())} for _ in range(60)]
        upstream = []
        critical = [{"entity_type": "production", "entity_id": str(uuid4())} for _ in range(6)]
        
        risk_level, factors = analyzer._assess_risk(downstream, upstream, critical)
        
        assert risk_level == RiskLevel.CRITICAL
    
    def test_identify_critical_dependencies(self):
        """Test critical dependency identification."""
        analyzer = ImpactAnalyzer()
        
        downstream = [
            {"entity_type": "task", "entity_id": str(uuid4()), "depth": 2},
            {"entity_type": "production_report", "entity_id": str(uuid4()), "depth": 1},
            {"entity_type": "dashboard", "entity_id": str(uuid4()), "depth": 3},
        ]
        
        critical = analyzer._identify_critical_dependencies(downstream)
        
        # Should identify production_report and dashboard as critical
        assert len(critical) >= 2
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        analyzer = ImpactAnalyzer()
        
        # Critical risk should generate specific recommendations
        recommendations = analyzer._generate_recommendations(
            RiskLevel.CRITICAL,
            ["High downstream count"],
            [{"entity_type": "task"} for _ in range(20)]
        )
        
        assert len(recommendations) > 0
        assert any("maintenance" in r.lower() or "rollback" in r.lower() for r in recommendations)


class TestQueryEngine:
    """Tests for version query engine."""
    
    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical data."""
        engine = VersionQueryEngine()
        
        data = {"name": "test", "value": 1}
        similarity = engine._calculate_similarity(data, data)
        
        assert similarity == 1.0
    
    def test_calculate_similarity_different(self):
        """Test similarity calculation for different data."""
        engine = VersionQueryEngine()
        
        data1 = {"name": "test", "value": 1}
        data2 = {"name": "other", "count": 2}
        
        similarity = engine._calculate_similarity(data1, data2)
        
        assert 0 < similarity < 1
    
    def test_calculate_similarity_empty(self):
        """Test similarity calculation with empty data."""
        engine = VersionQueryEngine()
        
        assert engine._calculate_similarity({}, {}) == 1.0
        assert engine._calculate_similarity({}, {"field": "value"}) == 0.0
    
    def test_calculate_differences(self):
        """Test difference calculation."""
        engine = VersionQueryEngine()
        
        data1 = {"name": "test", "value": 1, "old": "removed"}
        data2 = {"name": "test", "value": 2, "new": "added"}
        
        diff = engine._calculate_differences(data1, data2)
        
        assert "new" in diff["added"]
        assert "old" in diff["removed"]
        assert "value" in diff["modified"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
