"""
Impact Analyzer.

Analyzes the impact of data changes:
- Downstream impact assessment
- Risk level calculation
- Impact visualization
- Alert generation
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum

from src.versioning.lineage_engine import lineage_engine, LineageGraph

logger = logging.getLogger(__name__)


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


class ImpactAnalyzer:
    """
    Impact Analyzer for data change assessment.
    
    Provides:
    - Downstream impact analysis
    - Risk level calculation
    - Impact visualization data
    - Recommendations generation
    """
    
    # Critical entity types that increase risk
    CRITICAL_ENTITY_TYPES = {
        "production", "report", "dashboard", "api", 
        "export", "ml_model", "pipeline"
    }
    
    def __init__(self):
        self.lineage_engine = lineage_engine
    
    async def analyze_impact(
        self,
        entity_type: str,
        entity_id: str,
        change_type: str = "update",
        tenant_id: Optional[str] = None,
        max_depth: int = 5
    ) -> ImpactReport:
        """
        Analyze the impact of changes to an entity.
        
        Args:
            entity_type: Type of entity being changed
            entity_id: Entity ID
            change_type: Type of change (create, update, delete)
            tenant_id: Tenant ID for isolation
            max_depth: Maximum traversal depth
            
        Returns:
            ImpactReport with detailed analysis
        """
        # Get downstream lineage
        downstream = self.lineage_engine.get_downstream(
            entity_type, entity_id, max_depth, tenant_id
        )
        
        # Analyze each affected entity
        affected_entities = []
        for node in downstream.nodes:
            if node.entity_type == entity_type and node.entity_id == entity_id:
                continue  # Skip source entity
            
            impact = self._assess_node_impact(node, change_type)
            affected_entities.append(impact)
        
        # Identify critical paths
        critical_paths = self._identify_critical_paths(
            entity_type, entity_id, affected_entities, tenant_id
        )
        
        # Estimate affected records
        estimated_records = self._estimate_affected_records(affected_entities)
        
        # Calculate risk level
        risk_level, risk_factors = self._calculate_risk_level(
            affected_entities, critical_paths
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            risk_level, risk_factors, affected_entities, change_type
        )
        
        return ImpactReport(
            source_type=entity_type,
            source_id=entity_id,
            change_type=change_type,
            affected_entities=affected_entities,
            critical_paths=critical_paths,
            estimated_records=estimated_records,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )
    
    def analyze_impact_sync(
        self,
        entity_type: str,
        entity_id: str,
        change_type: str = "update",
        tenant_id: Optional[str] = None,
        max_depth: int = 5
    ) -> ImpactReport:
        """Synchronous version of analyze_impact."""
        downstream = self.lineage_engine.get_downstream(
            entity_type, entity_id, max_depth, tenant_id
        )
        
        affected_entities = []
        for node in downstream.nodes:
            if node.entity_type == entity_type and node.entity_id == entity_id:
                continue
            
            impact = self._assess_node_impact(node, change_type)
            affected_entities.append(impact)
        
        critical_paths = self._identify_critical_paths(
            entity_type, entity_id, affected_entities, tenant_id
        )
        
        estimated_records = self._estimate_affected_records(affected_entities)
        
        risk_level, risk_factors = self._calculate_risk_level(
            affected_entities, critical_paths
        )
        
        recommendations = self._generate_recommendations(
            risk_level, risk_factors, affected_entities, change_type
        )
        
        return ImpactReport(
            source_type=entity_type,
            source_id=entity_id,
            change_type=change_type,
            affected_entities=affected_entities,
            critical_paths=critical_paths,
            estimated_records=estimated_records,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )
    
    def _assess_node_impact(
        self,
        node,
        change_type: str
    ) -> EntityImpact:
        """Assess impact on a single node."""
        entity_type_lower = node.entity_type.lower()
        depth = node.metadata.get("depth", 1)
        
        # Determine severity based on entity type and distance
        severity = "low"
        impact_type = ImpactType.NONE.value
        
        # Check if critical entity type
        is_critical = any(
            ct in entity_type_lower 
            for ct in self.CRITICAL_ENTITY_TYPES
        )
        
        if is_critical:
            severity = "critical" if depth <= 2 else "high"
        elif depth == 1:
            severity = "high"
        elif depth <= 3:
            severity = "medium"
        
        # Determine impact type based on change type
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
    
    def _identify_critical_paths(
        self,
        source_type: str,
        source_id: str,
        affected_entities: List[EntityImpact],
        tenant_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Identify critical paths to high-impact entities."""
        critical_paths = []
        
        # Find paths to critical/high severity entities
        for entity in affected_entities:
            if entity.severity in ("critical", "high"):
                paths = self.lineage_engine.find_path(
                    source_type, source_id,
                    entity.entity_type, entity.entity_id,
                    tenant_id, max_depth=10
                )
                
                for path in paths:
                    critical_paths.append({
                        "target": f"{entity.entity_type}:{entity.entity_id}",
                        "severity": entity.severity,
                        "path": path.to_dict(),
                    })
        
        return critical_paths
    
    def _estimate_affected_records(
        self,
        affected_entities: List[EntityImpact]
    ) -> int:
        """Estimate total affected records."""
        # Simple estimation based on entity count and type
        base_estimate = 100  # Base records per entity
        
        total = 0
        for entity in affected_entities:
            multiplier = 1
            
            # Adjust based on entity type
            entity_type_lower = entity.entity_type.lower()
            if "dataset" in entity_type_lower:
                multiplier = 10
            elif "table" in entity_type_lower:
                multiplier = 5
            elif "report" in entity_type_lower:
                multiplier = 2
            
            # Adjust based on distance (closer = more impact)
            distance_factor = max(1, 5 - entity.distance)
            
            total += base_estimate * multiplier * distance_factor
        
        return total
    
    def _calculate_risk_level(
        self,
        affected_entities: List[EntityImpact],
        critical_paths: List[Dict[str, Any]]
    ) -> tuple[RiskLevel, List[str]]:
        """Calculate overall risk level."""
        risk_factors = []
        
        # Count by severity
        critical_count = sum(1 for e in affected_entities if e.severity == "critical")
        high_count = sum(1 for e in affected_entities if e.severity == "high")
        medium_count = sum(1 for e in affected_entities if e.severity == "medium")
        
        # Factor 1: Critical entities
        if critical_count > 0:
            risk_factors.append(f"{critical_count} critical entities affected")
        
        # Factor 2: High severity entities
        if high_count > 3:
            risk_factors.append(f"{high_count} high-severity entities affected")
        
        # Factor 3: Total affected count
        total = len(affected_entities)
        if total > 50:
            risk_factors.append(f"Large impact scope: {total} entities")
        elif total > 20:
            risk_factors.append(f"Moderate impact scope: {total} entities")
        
        # Factor 4: Critical paths
        if len(critical_paths) > 5:
            risk_factors.append(f"{len(critical_paths)} critical paths identified")
        
        # Determine risk level
        if critical_count > 0 or high_count > 5 or total > 50:
            risk_level = RiskLevel.CRITICAL
        elif high_count > 2 or total > 20:
            risk_level = RiskLevel.HIGH
        elif high_count > 0 or medium_count > 5:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return risk_level, risk_factors
    
    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        risk_factors: List[str],
        affected_entities: List[EntityImpact],
        change_type: str
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "Schedule change during maintenance window",
                "Notify all downstream system owners before proceeding",
                "Prepare comprehensive rollback plan",
                "Consider staged rollout with monitoring",
                "Ensure backup of all affected data",
            ])
        elif risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "Review all critical dependencies before change",
                "Notify key stakeholders",
                "Prepare rollback plan",
                "Monitor downstream systems after change",
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "Monitor downstream systems after change",
                "Have rollback procedure ready",
            ])
        else:
            recommendations.append("Standard change procedures apply")
        
        # Change type specific recommendations
        if change_type == "delete":
            recommendations.append("Verify no active dependencies before deletion")
            recommendations.append("Consider soft delete with grace period")
        
        # Entity count specific
        if len(affected_entities) > 10:
            recommendations.append("Consider batching changes to reduce impact")
        
        return recommendations
    
    def visualize_impact(
        self,
        report: ImpactReport
    ) -> Dict[str, Any]:
        """
        Generate visualization data for impact report.
        
        Returns data suitable for rendering impact graphs.
        """
        # Build nodes for visualization
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
                "size": 20 - (entity.distance * 2),  # Smaller for distant nodes
            })
            
            # Add edge from source or parent
            if entity.distance == 1:
                edges.append({
                    "source": f"{report.source_type}:{report.source_id}",
                    "target": node_id,
                    "type": "direct",
                })
        
        # Add edges from critical paths
        for path_info in report.critical_paths:
            path = path_info.get("path", {}).get("path", [])
            for i in range(len(path) - 1):
                source = f"{path[i]['entity_type']}:{path[i]['entity_id']}"
                target = f"{path[i+1]['entity_type']}:{path[i+1]['entity_id']}"
                
                edge = {"source": source, "target": target, "type": "critical"}
                if edge not in edges:
                    edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "risk_level": report.risk_level.value,
                "critical_count": sum(1 for e in report.affected_entities if e.severity == "critical"),
                "high_count": sum(1 for e in report.affected_entities if e.severity == "high"),
            }
        }
    
    async def send_impact_alert(
        self,
        report: ImpactReport,
        notification_service=None
    ) -> bool:
        """
        Send alert for high-risk impact.
        
        Args:
            report: Impact report
            notification_service: Optional notification service
            
        Returns:
            True if alert was sent
        """
        if report.risk_level not in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            return False
        
        alert_message = (
            f"Data Change Impact Alert - {report.risk_level.value.upper()}\n"
            f"Entity: {report.source_type}/{report.source_id}\n"
            f"Change Type: {report.change_type}\n"
            f"Affected Entities: {len(report.affected_entities)}\n"
            f"Risk Factors: {', '.join(report.risk_factors)}"
        )
        
        logger.warning(alert_message)
        
        if notification_service:
            try:
                await notification_service.send_alert(
                    title=f"Impact Alert: {report.risk_level.value.upper()}",
                    message=alert_message,
                    severity=report.risk_level.value,
                )
            except Exception as e:
                logger.error(f"Failed to send impact alert: {e}")
        
        return True


# Global instance
impact_analyzer = ImpactAnalyzer()
