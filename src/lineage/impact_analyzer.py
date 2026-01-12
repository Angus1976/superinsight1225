"""
Impact Analyzer.

Analyzes the impact of data changes on downstream systems:
- Dependency identification
- Risk assessment
- Change propagation analysis
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.version.models import DataLineageRecord, LineageRelationType

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level for impact analysis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ImpactAnalysis:
    """Result of impact analysis."""
    entity_type: str
    entity_id: str
    downstream_count: int
    upstream_count: int
    critical_dependencies: List[Dict[str, Any]] = field(default_factory=list)
    affected_entities: List[Dict[str, Any]] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "downstream_count": self.downstream_count,
            "upstream_count": self.upstream_count,
            "critical_dependencies": self.critical_dependencies,
            "affected_entities": self.affected_entities,
            "risk_level": self.risk_level.value,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
        }


class ImpactAnalyzer:
    """
    Analyzes impact of data changes.
    
    Provides:
    - Downstream impact analysis
    - Risk assessment
    - Change recommendations
    """
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()
    
    def analyze_impact(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str] = None,
        max_depth: int = 5
    ) -> ImpactAnalysis:
        """
        Analyze the impact of changes to an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            tenant_id: Tenant ID for isolation
            max_depth: Maximum traversal depth
            
        Returns:
            ImpactAnalysis with detailed impact information
        """
        # Get downstream entities
        downstream = self._get_downstream_entities(
            entity_type, entity_id, tenant_id, max_depth
        )
        
        # Get upstream entities
        upstream = self._get_upstream_entities(
            entity_type, entity_id, tenant_id, max_depth
        )
        
        # Identify critical dependencies
        critical = self._identify_critical_dependencies(downstream)
        
        # Assess risk
        risk_level, risk_factors = self._assess_risk(
            downstream, upstream, critical
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            risk_level, risk_factors, downstream
        )
        
        return ImpactAnalysis(
            entity_type=entity_type,
            entity_id=str(entity_id),
            downstream_count=len(downstream),
            upstream_count=len(upstream),
            critical_dependencies=critical,
            affected_entities=downstream,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )

    def _get_downstream_entities(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str],
        max_depth: int,
        visited: Optional[Set[str]] = None,
        current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all downstream entities recursively."""
        if visited is None:
            visited = set()
        
        if current_depth >= max_depth:
            return []
        
        key = f"{entity_type}:{entity_id}"
        if key in visited:
            return []
        visited.add(key)
        
        with self.get_session() as session:
            stmt = select(DataLineageRecord).where(
                DataLineageRecord.source_entity_type == entity_type,
                DataLineageRecord.source_entity_id == entity_id
            )
            if tenant_id:
                stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            records = result.scalars().all()
            
            entities = []
            for record in records:
                entity = {
                    "entity_type": record.target_entity_type,
                    "entity_id": str(record.target_entity_id),
                    "relationship": record.relationship_type.value,
                    "depth": current_depth + 1,
                }
                entities.append(entity)
                
                # Recursively get downstream
                children = self._get_downstream_entities(
                    record.target_entity_type,
                    record.target_entity_id,
                    tenant_id,
                    max_depth,
                    visited,
                    current_depth + 1
                )
                entities.extend(children)
            
            return entities
    
    def _get_upstream_entities(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str],
        max_depth: int,
        visited: Optional[Set[str]] = None,
        current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all upstream entities recursively."""
        if visited is None:
            visited = set()
        
        if current_depth >= max_depth:
            return []
        
        key = f"{entity_type}:{entity_id}"
        if key in visited:
            return []
        visited.add(key)
        
        with self.get_session() as session:
            stmt = select(DataLineageRecord).where(
                DataLineageRecord.target_entity_type == entity_type,
                DataLineageRecord.target_entity_id == entity_id
            )
            if tenant_id:
                stmt = stmt.where(DataLineageRecord.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            records = result.scalars().all()
            
            entities = []
            for record in records:
                entity = {
                    "entity_type": record.source_entity_type,
                    "entity_id": str(record.source_entity_id),
                    "relationship": record.relationship_type.value,
                    "depth": current_depth + 1,
                }
                entities.append(entity)
                
                # Recursively get upstream
                parents = self._get_upstream_entities(
                    record.source_entity_type,
                    record.source_entity_id,
                    tenant_id,
                    max_depth,
                    visited,
                    current_depth + 1
                )
                entities.extend(parents)
            
            return entities

    def _identify_critical_dependencies(
        self,
        downstream: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify critical dependencies from downstream entities."""
        critical = []
        
        # Critical entity types
        critical_types = {"production", "report", "dashboard", "api", "export"}
        
        for entity in downstream:
            entity_type = entity.get("entity_type", "").lower()
            if any(ct in entity_type for ct in critical_types):
                critical.append({
                    **entity,
                    "reason": f"Critical entity type: {entity_type}"
                })
            elif entity.get("depth", 0) == 1:
                # Direct dependencies are more critical
                critical.append({
                    **entity,
                    "reason": "Direct dependency"
                })
        
        return critical
    
    def _assess_risk(
        self,
        downstream: List[Dict[str, Any]],
        upstream: List[Dict[str, Any]],
        critical: List[Dict[str, Any]]
    ) -> tuple[RiskLevel, List[str]]:
        """Assess risk level based on impact analysis."""
        risk_factors = []
        
        # Factor 1: Number of downstream dependencies
        if len(downstream) > 50:
            risk_factors.append(f"High downstream count: {len(downstream)} entities")
        elif len(downstream) > 20:
            risk_factors.append(f"Moderate downstream count: {len(downstream)} entities")
        
        # Factor 2: Critical dependencies
        if len(critical) > 5:
            risk_factors.append(f"Multiple critical dependencies: {len(critical)}")
        elif len(critical) > 0:
            risk_factors.append(f"Has critical dependencies: {len(critical)}")
        
        # Factor 3: Depth of impact
        max_depth = max((e.get("depth", 0) for e in downstream), default=0)
        if max_depth > 3:
            risk_factors.append(f"Deep impact chain: {max_depth} levels")
        
        # Determine risk level
        if len(critical) > 5 or len(downstream) > 50:
            risk_level = RiskLevel.CRITICAL
        elif len(critical) > 2 or len(downstream) > 20:
            risk_level = RiskLevel.HIGH
        elif len(critical) > 0 or len(downstream) > 5:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return risk_level, risk_factors
    
    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        risk_factors: List[str],
        downstream: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on risk assessment."""
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("Schedule change during maintenance window")
            recommendations.append("Notify all downstream system owners")
            recommendations.append("Prepare rollback plan before proceeding")
        elif risk_level == RiskLevel.HIGH:
            recommendations.append("Review all critical dependencies before change")
            recommendations.append("Consider staged rollout")
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("Monitor downstream systems after change")
        
        if len(downstream) > 10:
            recommendations.append("Consider batching changes to reduce impact")
        
        return recommendations


# Global instance
impact_analyzer = ImpactAnalyzer()
