"""Property-based tests for Impact Analysis Service.

This module tests the universal correctness properties of the impact analysis service:
- Property 32: Dependency Graph Traversal
- Property 33: Impact Report Completeness

Requirements validated:
- 10.1: Dependency graph traversal
- 10.2: Affected entity identification
- 10.3: Affected relation counting
- 10.4: Migration effort estimation
- 10.5: High-impact approval requirement
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from uuid import uuid4
from src.collaboration.impact_analysis_service import (
    ImpactAnalysisService,
    ChangeImpactLevel,
    MigrationComplexity
)


# ============================================================================
# Property 32: Dependency Graph Traversal
# ============================================================================

class TestDependencyGraphTraversal:
    """Test dependency graph traversal.

    Property: Dependency graph traversal must correctly identify all dependent
    elements through DEPENDS_ON, USED_BY, and CONNECTS relationships.

    Requirements: 10.1, 10.2, 10.3
    """

    @pytest.mark.asyncio
    async def test_direct_dependencies_found(self):
        """Test that direct dependencies are found."""
        service = ImpactAnalysisService()

        # Create nodes
        entity1_id = uuid4()
        entity2_id = uuid4()
        entity3_id = uuid4()

        await service.add_node(entity1_id, "entity_type", "Entity1")
        await service.add_node(entity2_id, "entity_type", "Entity2")
        await service.add_node(entity3_id, "entity_type", "Entity3")

        # Create relationships: Entity2 depends on Entity1, Entity3 depends on Entity2
        await service.add_relationship(entity2_id, entity1_id, "DEPENDS_ON")
        await service.add_relationship(entity3_id, entity2_id, "DEPENDS_ON")

        # Analyze change to Entity1
        result = await service.analyze_change(
            change_request_id=uuid4(),
            element_id=entity1_id,
            change_type="modify"
        )

        # Should find Entity2 as direct dependent
        affected_ids = [e.element_id for e in result.affected_entities]
        assert entity2_id in affected_ids

    @pytest.mark.asyncio
    async def test_transitive_dependencies_found(self):
        """Test that transitive dependencies are found."""
        service = ImpactAnalysisService()

        # Create chain: A -> B -> C -> D
        node_a = uuid4()
        node_b = uuid4()
        node_c = uuid4()
        node_d = uuid4()

        await service.add_node(node_a, "entity_type", "A")
        await service.add_node(node_b, "entity_type", "B")
        await service.add_node(node_c, "entity_type", "C")
        await service.add_node(node_d, "entity_type", "D")

        await service.add_relationship(node_b, node_a, "DEPENDS_ON")
        await service.add_relationship(node_c, node_b, "DEPENDS_ON")
        await service.add_relationship(node_d, node_c, "DEPENDS_ON")

        # Change to A should affect B, C, D
        result = await service.analyze_change(
            change_request_id=uuid4(),
            element_id=node_a,
            change_type="modify"
        )

        affected_ids = [e.element_id for e in result.affected_entities]
        assert node_b in affected_ids
        assert node_c in affected_ids
        assert node_d in affected_ids
        assert len(result.affected_entities) == 3

    @pytest.mark.asyncio
    async def test_delete_traverses_both_directions(self):
        """Test that delete operations traverse both incoming and outgoing relationships."""
        service = ImpactAnalysisService()

        # Create bidirectional relationships
        center_id = uuid4()
        dependent_id = uuid4()
        dependency_id = uuid4()

        await service.add_node(center_id, "entity_type", "Center")
        await service.add_node(dependent_id, "entity_type", "Dependent")
        await service.add_node(dependency_id, "entity_type", "Dependency")

        # Dependent uses Center, Center uses Dependency
        await service.add_relationship(dependent_id, center_id, "DEPENDS_ON")
        await service.add_relationship(center_id, dependency_id, "DEPENDS_ON")

        # Delete Center should affect both Dependent and Dependency
        result = await service.analyze_change(
            change_request_id=uuid4(),
            element_id=center_id,
            change_type="delete"
        )

        affected_ids = [e.element_id for e in result.affected_entities]
        assert dependent_id in affected_ids
        assert dependency_id in affected_ids

    @pytest.mark.asyncio
    async def test_dependency_distance_calculated(self):
        """Test that dependency distance is correctly calculated."""
        service = ImpactAnalysisService()

        # Create chain with known distances
        root = uuid4()
        level1 = uuid4()
        level2 = uuid4()

        await service.add_node(root, "entity_type", "Root")
        await service.add_node(level1, "entity_type", "Level1")
        await service.add_node(level2, "entity_type", "Level2")

        await service.add_relationship(level1, root, "DEPENDS_ON")
        await service.add_relationship(level2, level1, "DEPENDS_ON")

        # Analyze change to root
        result = await service.analyze_change(
            change_request_id=uuid4(),
            element_id=root,
            change_type="modify"
        )

        # Check distances
        level1_element = next(e for e in result.affected_entities if e.element_id == level1)
        level2_element = next(e for e in result.affected_entities if e.element_id == level2)

        assert level1_element.distance == 1
        assert level2_element.distance == 2

    @pytest.mark.asyncio
    async def test_count_affected_entities(self):
        """Test counting affected entities."""
        service = ImpactAnalysisService()

        # Create multiple entities depending on one
        root_id = uuid4()
        entity_ids = [uuid4() for _ in range(5)]

        await service.add_node(root_id, "entity_type", "Root")
        for i, entity_id in enumerate(entity_ids):
            await service.add_node(entity_id, "entity_type", f"Entity{i}")
            await service.add_relationship(entity_id, root_id, "DEPENDS_ON")

        # Count should match
        count = await service.count_affected_entities(root_id)
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_affected_relations(self):
        """Test counting affected relations."""
        service = ImpactAnalysisService()

        # Create entity with multiple relations depending on it
        entity_id = uuid4()
        relation_ids = [uuid4() for _ in range(3)]

        await service.add_node(entity_id, "entity_type", "Entity")
        for i, relation_id in enumerate(relation_ids):
            await service.add_node(relation_id, "relation_type", f"Relation{i}")
            await service.add_relationship(relation_id, entity_id, "DEPENDS_ON")

        # Count should match
        count = await service.count_affected_relations(entity_id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_circular_dependencies_handled(self):
        """Test that circular dependencies don't cause infinite loops."""
        service = ImpactAnalysisService()

        # Create circular dependency: A -> B -> C -> A
        node_a = uuid4()
        node_b = uuid4()
        node_c = uuid4()

        await service.add_node(node_a, "entity_type", "A")
        await service.add_node(node_b, "entity_type", "B")
        await service.add_node(node_c, "entity_type", "C")

        await service.add_relationship(node_b, node_a, "DEPENDS_ON")
        await service.add_relationship(node_c, node_b, "DEPENDS_ON")
        await service.add_relationship(node_a, node_c, "DEPENDS_ON")  # Creates cycle

        # Should complete without hanging
        result = await service.analyze_change(
            change_request_id=uuid4(),
            element_id=node_a,
            change_type="modify"
        )

        # Should find all nodes in the cycle
        affected_ids = [e.element_id for e in result.affected_entities]
        assert node_b in affected_ids
        assert node_c in affected_ids


# ============================================================================
# Property 33: Impact Report Completeness
# ============================================================================

class TestImpactReportCompleteness:
    """Test impact report completeness.

    Property: Impact reports must include all required information:
    - Affected element counts
    - Migration effort estimation
    - Breaking change detection
    - Recommendations

    Requirements: 10.4
    """

    @pytest.mark.asyncio
    async def test_impact_report_has_all_fields(self):
        """Test that impact report includes all required fields."""
        service = ImpactAnalysisService()

        # Create simple graph
        element_id = uuid4()
        dependent_id = uuid4()

        await service.add_node(element_id, "entity_type", "Element")
        await service.add_node(dependent_id, "entity_type", "Dependent")
        await service.add_relationship(dependent_id, element_id, "DEPENDS_ON")

        # Analyze change
        result = await service.analyze_change(
            change_request_id=uuid4(),
            element_id=element_id,
            change_type="modify"
        )

        # Check all required fields present
        assert result.analysis_id is not None
        assert result.changed_element_id == element_id
        assert result.changed_element_type == "entity_type"
        assert result.changed_element_name == "Element"
        assert result.total_affected_count >= 0
        assert result.affected_entity_count >= 0
        assert result.impact_level is not None
        assert result.migration_complexity is not None
        assert result.estimated_migration_hours >= 0
        assert isinstance(result.breaking_changes, list)
        assert isinstance(result.migration_recommendations, list)
        assert result.analyzed_at is not None

    @pytest.mark.asyncio
    async def test_impact_level_categorization(self):
        """Test that impact level is correctly categorized."""
        service = ImpactAnalysisService()

        # Minimal impact (< 10 elements)
        root = uuid4()
        await service.add_node(root, "entity_type", "Root")
        for i in range(5):
            node_id = uuid4()
            await service.add_node(node_id, "entity_type", f"Node{i}")
            await service.add_relationship(node_id, root, "DEPENDS_ON")

        result = await service.analyze_change(uuid4(), root, "modify")
        assert result.impact_level == ChangeImpactLevel.MINIMAL

        # Low impact (10-100 elements)
        root2 = uuid4()
        await service.add_node(root2, "entity_type", "Root2")
        for i in range(50):
            node_id = uuid4()
            await service.add_node(node_id, "entity_type", f"Node2_{i}")
            await service.add_relationship(node_id, root2, "DEPENDS_ON")

        result2 = await service.analyze_change(uuid4(), root2, "modify")
        assert result2.impact_level == ChangeImpactLevel.LOW

    @pytest.mark.asyncio
    async def test_migration_effort_estimation(self):
        """Test that migration effort is estimated."""
        service = ImpactAnalysisService()

        # Create graph with known number of affected elements
        root_id = uuid4()
        await service.add_node(root_id, "entity_type", "Root")

        # Add 10 entities (10 * 0.5 = 5 hours)
        for i in range(10):
            entity_id = uuid4()
            await service.add_node(entity_id, "entity_type", f"Entity{i}")
            await service.add_relationship(entity_id, root_id, "DEPENDS_ON")

        # Add 10 relations (10 * 0.3 = 3 hours)
        for i in range(10):
            relation_id = uuid4()
            await service.add_node(relation_id, "relation_type", f"Relation{i}")
            await service.add_relationship(relation_id, root_id, "DEPENDS_ON")

        result = await service.analyze_change(uuid4(), root_id, "modify")

        # Expected: (10 * 0.5 + 10 * 0.3) * 1.2 (modify multiplier) = 9.6 hours
        assert result.estimated_migration_hours > 0
        assert result.migration_complexity in [MigrationComplexity.LOW, MigrationComplexity.MEDIUM]

    @pytest.mark.asyncio
    async def test_delete_has_breaking_changes(self):
        """Test that delete operations include breaking changes."""
        service = ImpactAnalysisService()

        element_id = uuid4()
        await service.add_node(element_id, "entity_type", "ToDelete")

        result = await service.analyze_change(
            uuid4(),
            element_id,
            "delete"
        )

        # Delete should have breaking changes
        assert len(result.breaking_changes) > 0
        assert any("break" in bc.lower() for bc in result.breaking_changes)

    @pytest.mark.asyncio
    async def test_high_impact_requires_approval(self):
        """Test that high-impact changes require special approval."""
        service = ImpactAnalysisService()
        service._high_impact_threshold = 10  # Lower threshold for testing

        # Create high-impact change (>10 affected elements)
        root_id = uuid4()
        await service.add_node(root_id, "entity_type", "Root")

        for i in range(15):
            node_id = uuid4()
            await service.add_node(node_id, "entity_type", f"Node{i}")
            await service.add_relationship(node_id, root_id, "DEPENDS_ON")

        result = await service.analyze_change(uuid4(), root_id, "modify")

        assert result.requires_high_impact_approval
        assert result.total_affected_count > 10

    @pytest.mark.asyncio
    async def test_recommendations_provided(self):
        """Test that recommendations are provided for complex changes."""
        service = ImpactAnalysisService()

        # Create complex change
        root_id = uuid4()
        await service.add_node(root_id, "entity_type", "Root")

        # Add many affected elements
        for i in range(100):
            node_id = uuid4()
            await service.add_node(node_id, "entity_type", f"Node{i}")
            await service.add_relationship(node_id, root_id, "DEPENDS_ON")

        result = await service.analyze_change(uuid4(), root_id, "delete")

        # Should have recommendations
        assert len(result.migration_recommendations) > 0

        # Delete should suggest verification and deprecation
        recommendations_text = " ".join(result.migration_recommendations).lower()
        assert "verify" in recommendations_text or "deprecation" in recommendations_text

    @pytest.mark.asyncio
    async def test_analysis_duration_tracked(self):
        """Test that analysis duration is tracked."""
        service = ImpactAnalysisService()

        element_id = uuid4()
        await service.add_node(element_id, "entity_type", "Element")

        result = await service.analyze_change(uuid4(), element_id, "modify")

        # Duration should be recorded
        assert result.analysis_duration_ms >= 0


# ============================================================================
# Dependency Path Tests
# ============================================================================

class TestDependencyPath:
    """Test dependency path finding.

    Requirements: 10.1
    """

    @pytest.mark.asyncio
    async def test_find_direct_path(self):
        """Test finding direct path between elements."""
        service = ImpactAnalysisService()

        node_a = uuid4()
        node_b = uuid4()

        await service.add_node(node_a, "entity_type", "A")
        await service.add_node(node_b, "entity_type", "B")
        await service.add_relationship(node_b, node_a, "DEPENDS_ON")

        path = await service.get_dependency_path(node_a, node_b)

        assert path is not None
        assert len(path) == 2
        assert path[0] == node_a
        assert path[1] == node_b

    @pytest.mark.asyncio
    async def test_find_indirect_path(self):
        """Test finding indirect path through multiple nodes."""
        service = ImpactAnalysisService()

        node_a = uuid4()
        node_b = uuid4()
        node_c = uuid4()

        await service.add_node(node_a, "entity_type", "A")
        await service.add_node(node_b, "entity_type", "B")
        await service.add_node(node_c, "entity_type", "C")

        await service.add_relationship(node_b, node_a, "DEPENDS_ON")
        await service.add_relationship(node_c, node_b, "DEPENDS_ON")

        path = await service.get_dependency_path(node_a, node_c)

        assert path is not None
        assert len(path) == 3
        assert path == [node_a, node_b, node_c]

    @pytest.mark.asyncio
    async def test_no_path_returns_none(self):
        """Test that non-existent paths return None."""
        service = ImpactAnalysisService()

        node_a = uuid4()
        node_b = uuid4()

        await service.add_node(node_a, "entity_type", "A")
        await service.add_node(node_b, "entity_type", "B")

        # No relationship between A and B
        path = await service.get_dependency_path(node_a, node_b)

        assert path is None


# ============================================================================
# Graph Statistics Tests
# ============================================================================

class TestGraphStatistics:
    """Test graph statistics."""

    @pytest.mark.asyncio
    async def test_graph_statistics(self):
        """Test getting graph statistics."""
        service = ImpactAnalysisService()

        # Create known graph structure
        entity1 = uuid4()
        entity2 = uuid4()
        relation1 = uuid4()

        await service.add_node(entity1, "entity_type", "Entity1")
        await service.add_node(entity2, "entity_type", "Entity2")
        await service.add_node(relation1, "relation_type", "Relation1")

        await service.add_relationship(entity2, entity1, "DEPENDS_ON")
        await service.add_relationship(relation1, entity1, "DEPENDS_ON")

        stats = await service.get_graph_statistics()

        assert stats["total_nodes"] == 3
        assert stats["total_relationships"] == 2
        assert stats["entity_types"] == 2
        assert stats["relation_types"] == 1
        assert stats["average_dependencies"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
