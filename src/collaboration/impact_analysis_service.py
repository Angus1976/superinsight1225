"""Impact Analysis Service for ontology change impact assessment.

This module provides comprehensive impact analysis for ontology changes:
- Dependency graph traversal using Neo4j-style queries
- Affected entity and relation counting
- Migration effort estimation
- High-impact approval requirements
- Breaking change detection

Requirements:
- 10.1: Dependency graph traversal
- 10.2: Affected entity identification
- 10.3: Affected relation counting
- 10.4: Migration effort estimation
- 10.5: High-impact approval requirement
"""

import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class MigrationComplexity(str, Enum):
    """Migration complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChangeImpactLevel(str, Enum):
    """Impact level of a change."""
    MINIMAL = "minimal"  # < 10 affected elements
    LOW = "low"  # 10-100 affected elements
    MEDIUM = "medium"  # 100-1000 affected elements
    HIGH = "high"  # 1000-10000 affected elements
    CRITICAL = "critical"  # > 10000 affected elements


@dataclass
class DependencyNode:
    """Node in the dependency graph."""
    node_id: UUID = field(default_factory=uuid4)
    node_type: str = ""  # "entity_type", "relation_type", "attribute"
    name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyRelationship:
    """Relationship in the dependency graph."""
    from_node: UUID = field(default_factory=uuid4)
    to_node: UUID = field(default_factory=uuid4)
    relationship_type: str = ""  # "DEPENDS_ON", "USED_BY", "CONNECTS"
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AffectedElement:
    """Element affected by a change."""
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""
    element_name: str = ""
    impact_reason: str = ""  # Why this element is affected
    distance: int = 0  # Distance from changed element in dependency graph


@dataclass
class ImpactAnalysisResult:
    """Result of impact analysis."""
    analysis_id: UUID = field(default_factory=uuid4)
    change_request_id: UUID = field(default_factory=uuid4)
    changed_element_id: UUID = field(default_factory=uuid4)
    changed_element_type: str = ""
    changed_element_name: str = ""

    # Affected elements
    affected_entities: List[AffectedElement] = field(default_factory=list)
    affected_relations: List[AffectedElement] = field(default_factory=list)
    affected_attributes: List[AffectedElement] = field(default_factory=list)
    affected_projects: List[AffectedElement] = field(default_factory=list)

    # Counts
    total_affected_count: int = 0
    affected_entity_count: int = 0
    affected_relation_count: int = 0
    affected_project_count: int = 0

    # Impact assessment
    impact_level: ChangeImpactLevel = ChangeImpactLevel.MINIMAL
    requires_high_impact_approval: bool = False

    # Migration estimation
    migration_complexity: MigrationComplexity = MigrationComplexity.LOW
    estimated_migration_hours: float = 0.0
    breaking_changes: List[str] = field(default_factory=list)
    migration_recommendations: List[str] = field(default_factory=list)

    # Analysis metadata
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    analysis_duration_ms: float = 0.0


@dataclass
class DependencyGraph:
    """In-memory representation of dependency graph."""
    nodes: Dict[UUID, DependencyNode] = field(default_factory=dict)
    relationships: List[DependencyRelationship] = field(default_factory=list)

    # Adjacency lists for efficient traversal
    outgoing: Dict[UUID, List[UUID]] = field(default_factory=dict)  # node -> [dependent nodes]
    incoming: Dict[UUID, List[UUID]] = field(default_factory=dict)  # node -> [dependency nodes]


class ImpactAnalysisService:
    """Service for analyzing the impact of ontology changes."""

    def __init__(self):
        """Initialize impact analysis service."""
        self._graph = DependencyGraph()
        self._lock = asyncio.Lock()

        # Configuration
        self._high_impact_threshold = 1000  # Elements
        self._max_traversal_depth = 10
        self._hours_per_affected_entity = 0.5
        self._hours_per_affected_relation = 0.3

    async def add_node(
        self,
        node_id: UUID,
        node_type: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a node to the dependency graph.

        Args:
            node_id: Node ID
            node_type: Type of node
            name: Node name
            properties: Optional node properties
        """
        async with self._lock:
            node = DependencyNode(
                node_id=node_id,
                node_type=node_type,
                name=name,
                properties=properties or {}
            )
            self._graph.nodes[node_id] = node

            # Initialize adjacency lists
            if node_id not in self._graph.outgoing:
                self._graph.outgoing[node_id] = []
            if node_id not in self._graph.incoming:
                self._graph.incoming[node_id] = []

    async def add_relationship(
        self,
        from_node: UUID,
        to_node: UUID,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a relationship to the dependency graph.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            relationship_type: Type of relationship
            properties: Optional relationship properties
        """
        async with self._lock:
            relationship = DependencyRelationship(
                from_node=from_node,
                to_node=to_node,
                relationship_type=relationship_type,
                properties=properties or {}
            )
            self._graph.relationships.append(relationship)

            # Update adjacency lists
            if from_node not in self._graph.outgoing:
                self._graph.outgoing[from_node] = []
            self._graph.outgoing[from_node].append(to_node)

            if to_node not in self._graph.incoming:
                self._graph.incoming[to_node] = []
            self._graph.incoming[to_node].append(from_node)

    async def analyze_change(
        self,
        change_request_id: UUID,
        element_id: UUID,
        change_type: str
    ) -> ImpactAnalysisResult:
        """Analyze the impact of a change to an ontology element.

        Args:
            change_request_id: ID of the change request
            element_id: ID of the element being changed
            change_type: Type of change (add, modify, delete)

        Returns:
            Impact analysis result
        """
        start_time = datetime.utcnow()

        async with self._lock:
            # Get element details
            element = self._graph.nodes.get(element_id)
            if not element:
                raise ValueError(f"Element {element_id} not found in graph")

            result = ImpactAnalysisResult(
                change_request_id=change_request_id,
                changed_element_id=element_id,
                changed_element_type=element.node_type,
                changed_element_name=element.name
            )

            # Traverse dependency graph
            affected_nodes = await self._traverse_dependencies(element_id, change_type)

            # Categorize affected elements
            for node_id, distance, reason in affected_nodes:
                node = self._graph.nodes.get(node_id)
                if not node:
                    continue

                affected = AffectedElement(
                    element_id=node_id,
                    element_type=node.node_type,
                    element_name=node.name,
                    impact_reason=reason,
                    distance=distance
                )

                if node.node_type == "entity_type":
                    result.affected_entities.append(affected)
                elif node.node_type == "relation_type":
                    result.affected_relations.append(affected)
                elif node.node_type == "attribute":
                    result.affected_attributes.append(affected)
                elif node.node_type == "project":
                    result.affected_projects.append(affected)

            # Calculate counts
            result.affected_entity_count = len(result.affected_entities)
            result.affected_relation_count = len(result.affected_relations)
            result.affected_project_count = len(result.affected_projects)
            result.total_affected_count = (
                result.affected_entity_count +
                result.affected_relation_count +
                len(result.affected_attributes)
            )

            # Determine impact level
            result.impact_level = self._calculate_impact_level(result.total_affected_count)

            # Check if high-impact approval is required
            result.requires_high_impact_approval = (
                result.total_affected_count > self._high_impact_threshold
            )

            # Estimate migration effort
            await self._estimate_migration(result, change_type)

            # Calculate analysis duration
            end_time = datetime.utcnow()
            result.analysis_duration_ms = (end_time - start_time).total_seconds() * 1000

            return result

    async def _traverse_dependencies(
        self,
        element_id: UUID,
        change_type: str
    ) -> List[Tuple[UUID, int, str]]:
        """Traverse dependency graph to find affected elements.

        Args:
            element_id: Starting element ID
            change_type: Type of change

        Returns:
            List of (node_id, distance, reason) tuples
        """
        affected = []
        visited = set()
        queue = [(element_id, 0)]

        while queue and len(visited) < 10000:  # Limit to prevent infinite loops
            current_id, distance = queue.pop(0)

            if current_id in visited or distance > self._max_traversal_depth:
                continue

            visited.add(current_id)

            # Don't include the original element
            if current_id != element_id:
                reason = self._determine_impact_reason(current_id, element_id, distance, change_type)
                affected.append((current_id, distance, reason))

            # Traverse outgoing relationships (DEPENDS_ON)
            for dependent_id in self._graph.outgoing.get(current_id, []):
                if dependent_id not in visited:
                    queue.append((dependent_id, distance + 1))

            # For deletes, also traverse incoming relationships (USED_BY)
            if change_type == "delete":
                for using_id in self._graph.incoming.get(current_id, []):
                    if using_id not in visited:
                        queue.append((using_id, distance + 1))

        return affected

    def _determine_impact_reason(
        self,
        affected_id: UUID,
        changed_id: UUID,
        distance: int,
        change_type: str
    ) -> str:
        """Determine why an element is affected by a change.

        Args:
            affected_id: Affected element ID
            changed_id: Changed element ID
            distance: Distance in dependency graph
            change_type: Type of change

        Returns:
            Impact reason description
        """
        if distance == 1:
            if change_type == "delete":
                return "Directly references deleted element"
            elif change_type == "modify":
                return "Directly depends on modified element"
            else:
                return "Directly related to new element"
        else:
            return f"Indirectly affected (distance: {distance})"

    def _calculate_impact_level(self, affected_count: int) -> ChangeImpactLevel:
        """Calculate impact level based on affected element count.

        Args:
            affected_count: Number of affected elements

        Returns:
            Impact level
        """
        if affected_count < 10:
            return ChangeImpactLevel.MINIMAL
        elif affected_count < 100:
            return ChangeImpactLevel.LOW
        elif affected_count < 1000:
            return ChangeImpactLevel.MEDIUM
        elif affected_count < 10000:
            return ChangeImpactLevel.HIGH
        else:
            return ChangeImpactLevel.CRITICAL

    async def _estimate_migration(
        self,
        result: ImpactAnalysisResult,
        change_type: str
    ) -> None:
        """Estimate migration effort for the change.

        Args:
            result: Impact analysis result to update
            change_type: Type of change
        """
        # Calculate base hours
        hours = (
            result.affected_entity_count * self._hours_per_affected_entity +
            result.affected_relation_count * self._hours_per_affected_relation
        )

        # Adjust for change type
        if change_type == "delete":
            hours *= 1.5  # Deletes are more complex
            result.breaking_changes.append("Deleting an element may break existing references")
        elif change_type == "modify":
            hours *= 1.2

        result.estimated_migration_hours = round(hours, 1)

        # Determine complexity
        if hours < 8:
            result.migration_complexity = MigrationComplexity.LOW
        elif hours < 40:
            result.migration_complexity = MigrationComplexity.MEDIUM
        else:
            result.migration_complexity = MigrationComplexity.HIGH

        # Generate recommendations
        result.migration_recommendations = self._generate_recommendations(result, change_type)

    def _generate_recommendations(
        self,
        result: ImpactAnalysisResult,
        change_type: str
    ) -> List[str]:
        """Generate migration recommendations.

        Args:
            result: Impact analysis result
            change_type: Type of change

        Returns:
            List of recommendations
        """
        recommendations = []

        if result.total_affected_count > 1000:
            recommendations.append("Consider breaking this change into smaller incremental changes")
            recommendations.append("Implement migration in phases with rollback capability")

        if change_type == "delete":
            recommendations.append("Verify all references are updated before deletion")
            recommendations.append("Consider deprecation period before final deletion")

        if result.affected_project_count > 10:
            recommendations.append("Notify all affected project teams before implementing")
            recommendations.append("Provide migration guide and timeline to teams")

        if result.migration_complexity == MigrationComplexity.HIGH:
            recommendations.append("Allocate dedicated migration team")
            recommendations.append("Set up staging environment for testing")

        return recommendations

    async def get_dependency_path(
        self,
        from_element: UUID,
        to_element: UUID
    ) -> Optional[List[UUID]]:
        """Find dependency path between two elements.

        Args:
            from_element: Starting element
            to_element: Target element

        Returns:
            List of element IDs forming the path, or None if no path exists
        """
        async with self._lock:
            # BFS to find shortest path
            visited = {from_element}
            queue = [(from_element, [from_element])]

            while queue:
                current, path = queue.pop(0)

                if current == to_element:
                    return path

                for neighbor in self._graph.outgoing.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))

            return None

    async def get_element_dependents(
        self,
        element_id: UUID,
        max_depth: int = 5
    ) -> List[AffectedElement]:
        """Get all elements that depend on a given element.

        Args:
            element_id: Element ID
            max_depth: Maximum traversal depth

        Returns:
            List of dependent elements
        """
        async with self._lock:
            dependents = []
            visited = set()
            queue = [(element_id, 0)]

            while queue:
                current_id, depth = queue.pop(0)

                if current_id in visited or depth > max_depth:
                    continue

                visited.add(current_id)

                if current_id != element_id:
                    node = self._graph.nodes.get(current_id)
                    if node:
                        dependents.append(AffectedElement(
                            element_id=current_id,
                            element_type=node.node_type,
                            element_name=node.name,
                            impact_reason=f"Depends on element (depth: {depth})",
                            distance=depth
                        ))

                # Traverse outgoing edges
                for dependent_id in self._graph.outgoing.get(current_id, []):
                    if dependent_id not in visited:
                        queue.append((dependent_id, depth + 1))

            return dependents

    async def count_affected_entities(
        self,
        element_id: UUID
    ) -> int:
        """Count entities affected by a change to an element.

        Args:
            element_id: Element ID

        Returns:
            Number of affected entities
        """
        affected = await self._traverse_dependencies(element_id, "modify")
        return sum(1 for node_id, _, _ in affected
                   if self._graph.nodes.get(node_id, DependencyNode()).node_type == "entity_type")

    async def count_affected_relations(
        self,
        element_id: UUID
    ) -> int:
        """Count relations affected by a change to an element.

        Args:
            element_id: Element ID

        Returns:
            Number of affected relations
        """
        affected = await self._traverse_dependencies(element_id, "modify")
        return sum(1 for node_id, _, _ in affected
                   if self._graph.nodes.get(node_id, DependencyNode()).node_type == "relation_type")

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the dependency graph.

        Returns:
            Dictionary of statistics
        """
        async with self._lock:
            entity_count = sum(1 for node in self._graph.nodes.values()
                             if node.node_type == "entity_type")
            relation_count = sum(1 for node in self._graph.nodes.values()
                               if node.node_type == "relation_type")

            return {
                "total_nodes": len(self._graph.nodes),
                "total_relationships": len(self._graph.relationships),
                "entity_types": entity_count,
                "relation_types": relation_count,
                "average_dependencies": (
                    sum(len(deps) for deps in self._graph.outgoing.values()) / len(self._graph.nodes)
                    if self._graph.nodes else 0
                )
            }
