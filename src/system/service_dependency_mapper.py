"""
Service Dependency Mapper for SuperInsight Platform.

Provides comprehensive service dependency tracking including:
- Service relationship mapping
- Dependency health monitoring
- Cascade failure prediction
- Impact analysis
- Recovery order optimization
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import networkx as nx
from datetime import datetime, timedelta

from src.system.health_monitor import health_monitor
from src.system.notification import notification_system, NotificationPriority, NotificationChannel
from src.utils.degradation import degradation_manager

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of service dependencies."""
    HARD = "hard"  # Service cannot function without this dependency
    SOFT = "soft"  # Service can function with degraded performance
    OPTIONAL = "optional"  # Service can function normally without this dependency
    CIRCULAR = "circular"  # Mutual dependency


class ServiceStatus(Enum):
    """Service status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceDependency:
    """Service dependency definition."""
    source_service: str
    target_service: str
    dependency_type: DependencyType
    weight: float = 1.0  # Importance weight (0.0 to 1.0)
    timeout_threshold: float = 30.0  # Seconds
    failure_threshold: int = 3  # Number of failures before marking as failed
    recovery_order: int = 0  # Order for recovery (lower = earlier)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceNode:
    """Service node in the dependency graph."""
    service_name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    failure_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    criticality_score: float = 0.0
    recovery_priority: int = 5  # 1 = highest, 10 = lowest


@dataclass
class ImpactAnalysis:
    """Impact analysis result."""
    failed_service: str
    directly_affected: List[str]
    indirectly_affected: List[str]
    cascade_probability: float
    estimated_recovery_time: float
    recovery_order: List[str]


class ServiceDependencyMapper:
    """
    Maps and monitors service dependencies for fault detection and recovery planning.
    
    Features:
    - Dynamic dependency discovery
    - Real-time health monitoring
    - Cascade failure prediction
    - Impact analysis
    - Recovery order optimization
    - Dependency visualization
    """
    
    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.service_nodes: Dict[str, ServiceNode] = {}
        self.dependencies: Dict[str, List[ServiceDependency]] = defaultdict(list)
        self.health_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Analysis cache
        self.impact_cache: Dict[str, ImpactAnalysis] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = 0
        
        # Initialize with default service mappings
        self._setup_default_services()
    
    def _setup_default_services(self):
        """Setup default service mappings for SuperInsight platform."""
        # Core services
        core_services = [
            "database",
            "storage",
            "authentication",
            "api_gateway"
        ]
        
        # Application services
        app_services = [
            "annotation_service",
            "quality_service",
            "export_service",
            "ai_services",
            "label_studio"
        ]
        
        # External services
        external_services = [
            "email_service",
            "monitoring_service",
            "backup_service"
        ]
        
        # Add all services to graph
        all_services = core_services + app_services + external_services
        for service in all_services:
            self.add_service(service)
        
        # Define core dependencies
        self.add_dependency("annotation_service", "database", DependencyType.HARD, weight=1.0)
        self.add_dependency("annotation_service", "authentication", DependencyType.HARD, weight=0.9)
        self.add_dependency("annotation_service", "ai_services", DependencyType.SOFT, weight=0.7)
        self.add_dependency("annotation_service", "label_studio", DependencyType.SOFT, weight=0.6)
        
        self.add_dependency("quality_service", "database", DependencyType.HARD, weight=1.0)
        self.add_dependency("quality_service", "annotation_service", DependencyType.SOFT, weight=0.8)
        
        self.add_dependency("export_service", "database", DependencyType.HARD, weight=1.0)
        self.add_dependency("export_service", "storage", DependencyType.HARD, weight=0.9)
        self.add_dependency("export_service", "quality_service", DependencyType.SOFT, weight=0.7)
        
        # API Gateway dependencies
        self.add_dependency("api_gateway", "authentication", DependencyType.HARD, weight=1.0)
        self.add_dependency("api_gateway", "annotation_service", DependencyType.SOFT, weight=0.8)
        self.add_dependency("api_gateway", "quality_service", DependencyType.SOFT, weight=0.8)
        self.add_dependency("api_gateway", "export_service", DependencyType.SOFT, weight=0.8)
        
        # External service dependencies
        self.add_dependency("monitoring_service", "database", DependencyType.SOFT, weight=0.6)
        self.add_dependency("backup_service", "database", DependencyType.HARD, weight=1.0)
        self.add_dependency("backup_service", "storage", DependencyType.HARD, weight=1.0)
        
        # Calculate initial criticality scores
        self._calculate_criticality_scores()
        
        logger.info(f"Initialized dependency mapper with {len(all_services)} services and {len(self.dependencies)} dependencies")
    
    def add_service(self, service_name: str, **kwargs) -> ServiceNode:
        """Add a service to the dependency graph."""
        if service_name not in self.service_nodes:
            service_node = ServiceNode(
                service_name=service_name,
                **kwargs
            )
            self.service_nodes[service_name] = service_node
            self.dependency_graph.add_node(service_name, **kwargs)
            
            logger.debug(f"Added service: {service_name}")
        
        return self.service_nodes[service_name]
    
    def add_dependency(self, source_service: str, target_service: str, 
                      dependency_type: DependencyType, **kwargs) -> ServiceDependency:
        """Add a dependency between services."""
        # Ensure both services exist
        self.add_service(source_service)
        self.add_service(target_service)
        
        # Create dependency
        dependency = ServiceDependency(
            source_service=source_service,
            target_service=target_service,
            dependency_type=dependency_type,
            **kwargs
        )
        
        # Add to graph
        self.dependency_graph.add_edge(
            source_service, target_service,
            dependency_type=dependency_type.value,
            weight=kwargs.get('weight', 1.0)
        )
        
        # Update service nodes
        self.service_nodes[source_service].dependencies.append(target_service)
        self.service_nodes[target_service].dependents.append(source_service)
        
        # Store dependency
        self.dependencies[source_service].append(dependency)
        
        logger.debug(f"Added dependency: {source_service} -> {target_service} ({dependency_type.value})")
        
        return dependency
    
    def remove_dependency(self, source_service: str, target_service: str) -> bool:
        """Remove a dependency between services."""
        try:
            # Remove from graph
            if self.dependency_graph.has_edge(source_service, target_service):
                self.dependency_graph.remove_edge(source_service, target_service)
            
            # Update service nodes
            if source_service in self.service_nodes:
                if target_service in self.service_nodes[source_service].dependencies:
                    self.service_nodes[source_service].dependencies.remove(target_service)
            
            if target_service in self.service_nodes:
                if source_service in self.service_nodes[target_service].dependents:
                    self.service_nodes[target_service].dependents.remove(source_service)
            
            # Remove from dependencies list
            if source_service in self.dependencies:
                self.dependencies[source_service] = [
                    dep for dep in self.dependencies[source_service]
                    if dep.target_service != target_service
                ]
            
            logger.debug(f"Removed dependency: {source_service} -> {target_service}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing dependency: {e}")
            return False
    
    async def start_monitoring(self):
        """Start dependency monitoring."""
        if self.monitoring_active:
            logger.warning("Dependency monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Service dependency monitoring started")
    
    async def stop_monitoring(self):
        """Stop dependency monitoring."""
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Service dependency monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for service dependencies."""
        while self.monitoring_active:
            try:
                # Update service health status
                await self._update_service_health()
                
                # Check for cascade failures
                await self._check_cascade_failures()
                
                # Update criticality scores
                self._calculate_criticality_scores()
                
                # Clear old cache
                self._clear_old_cache()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in dependency monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _update_service_health(self):
        """Update health status for all services."""
        try:
            # Get health summary from health monitor
            health_summary = health_monitor.get_metrics_summary()
            
            for service_name, service_node in self.service_nodes.items():
                # Check if we have health data for this service
                health_key = f"{service_name}_health"
                if health_key in health_summary.get("metrics", {}):
                    metric_data = health_summary["metrics"][health_key]
                    status_str = metric_data.get("status", "unknown")
                    
                    # Map health monitor status to service status
                    status_mapping = {
                        "healthy": ServiceStatus.HEALTHY,
                        "warning": ServiceStatus.DEGRADED,
                        "unhealthy": ServiceStatus.UNHEALTHY,
                        "unknown": ServiceStatus.UNKNOWN
                    }
                    
                    new_status = status_mapping.get(status_str, ServiceStatus.UNKNOWN)
                    
                    # Update service status
                    if service_node.status != new_status:
                        old_status = service_node.status
                        service_node.status = new_status
                        service_node.last_health_check = datetime.utcnow()
                        
                        # Update failure count
                        if new_status in [ServiceStatus.DEGRADED, ServiceStatus.UNHEALTHY]:
                            service_node.failure_count += 1
                        else:
                            service_node.failure_count = 0
                        
                        logger.info(f"Service {service_name} status changed: {old_status.value} -> {new_status.value}")
                        
                        # Check if this triggers cascade failures
                        if new_status == ServiceStatus.UNHEALTHY:
                            await self._analyze_cascade_impact(service_name)
                
                # Store health history
                self.health_history[service_name].append({
                    "timestamp": time.time(),
                    "status": service_node.status.value,
                    "failure_count": service_node.failure_count
                })
            
        except Exception as e:
            logger.error(f"Error updating service health: {e}")
    
    async def _check_cascade_failures(self):
        """Check for potential cascade failures."""
        try:
            for service_name, service_node in self.service_nodes.items():
                if service_node.status == ServiceStatus.UNHEALTHY:
                    # Check if this service's failure affects others
                    affected_services = self._get_affected_services(service_name)
                    
                    if len(affected_services) > 1:  # More than just the failed service
                        logger.warning(f"Potential cascade failure detected from {service_name}: {affected_services}")
                        
                        # Send cascade failure notification
                        notification_system.send_notification(
                            title=f"Cascade Failure Risk - {service_name}",
                            message=f"Service {service_name} failure may affect {len(affected_services)} other services: {', '.join(affected_services)}",
                            priority=NotificationPriority.HIGH,
                            channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
                        )
            
        except Exception as e:
            logger.error(f"Error checking cascade failures: {e}")
    
    async def _analyze_cascade_impact(self, failed_service: str) -> ImpactAnalysis:
        """Analyze the impact of a service failure."""
        try:
            # Check cache first
            cache_key = f"{failed_service}_{int(time.time() / self.cache_ttl)}"
            if cache_key in self.impact_cache:
                return self.impact_cache[cache_key]
            
            # Get directly affected services (immediate dependents)
            directly_affected = []
            for dependent in self.service_nodes[failed_service].dependents:
                # Check dependency type
                for dep in self.dependencies.get(dependent, []):
                    if dep.target_service == failed_service:
                        if dep.dependency_type in [DependencyType.HARD, DependencyType.SOFT]:
                            directly_affected.append(dependent)
                        break
            
            # Get indirectly affected services (cascade effect)
            indirectly_affected = []
            visited = set([failed_service] + directly_affected)
            
            for affected_service in directly_affected:
                cascade_services = self._get_cascade_services(affected_service, visited)
                indirectly_affected.extend(cascade_services)
            
            # Calculate cascade probability
            cascade_probability = self._calculate_cascade_probability(failed_service, directly_affected)
            
            # Estimate recovery time
            estimated_recovery_time = self._estimate_recovery_time(failed_service, directly_affected + indirectly_affected)
            
            # Generate recovery order
            recovery_order = self._generate_recovery_order([failed_service] + directly_affected + indirectly_affected)
            
            # Create impact analysis
            impact_analysis = ImpactAnalysis(
                failed_service=failed_service,
                directly_affected=directly_affected,
                indirectly_affected=indirectly_affected,
                cascade_probability=cascade_probability,
                estimated_recovery_time=estimated_recovery_time,
                recovery_order=recovery_order
            )
            
            # Cache result
            self.impact_cache[cache_key] = impact_analysis
            
            logger.info(f"Impact analysis for {failed_service}: {len(directly_affected)} direct, {len(indirectly_affected)} indirect")
            
            return impact_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing cascade impact: {e}")
            return ImpactAnalysis(
                failed_service=failed_service,
                directly_affected=[],
                indirectly_affected=[],
                cascade_probability=0.0,
                estimated_recovery_time=0.0,
                recovery_order=[]
            )
    
    def _get_affected_services(self, failed_service: str) -> List[str]:
        """Get all services affected by a failure."""
        affected = [failed_service]
        
        # Get direct dependents
        for dependent in self.service_nodes[failed_service].dependents:
            for dep in self.dependencies.get(dependent, []):
                if dep.target_service == failed_service:
                    if dep.dependency_type in [DependencyType.HARD, DependencyType.SOFT]:
                        affected.append(dependent)
                    break
        
        return affected
    
    def _get_cascade_services(self, service_name: str, visited: Set[str]) -> List[str]:
        """Get services affected by cascade failure."""
        cascade_services = []
        
        for dependent in self.service_nodes[service_name].dependents:
            if dependent not in visited:
                # Check if this dependency would cause cascade failure
                for dep in self.dependencies.get(dependent, []):
                    if dep.target_service == service_name and dep.dependency_type == DependencyType.HARD:
                        cascade_services.append(dependent)
                        visited.add(dependent)
                        
                        # Recursively check for further cascades
                        further_cascades = self._get_cascade_services(dependent, visited)
                        cascade_services.extend(further_cascades)
                        break
        
        return cascade_services
    
    def _calculate_cascade_probability(self, failed_service: str, affected_services: List[str]) -> float:
        """Calculate the probability of cascade failure."""
        try:
            if not affected_services:
                return 0.0
            
            # Base probability based on number of affected services
            base_probability = min(len(affected_services) / 10.0, 0.9)  # Max 90%
            
            # Adjust based on dependency types and weights
            weight_factor = 0.0
            total_dependencies = 0
            
            for affected_service in affected_services:
                for dep in self.dependencies.get(affected_service, []):
                    if dep.target_service == failed_service:
                        total_dependencies += 1
                        
                        # Weight based on dependency type
                        type_weight = {
                            DependencyType.HARD: 1.0,
                            DependencyType.SOFT: 0.6,
                            DependencyType.OPTIONAL: 0.2
                        }.get(dep.dependency_type, 0.5)
                        
                        weight_factor += dep.weight * type_weight
            
            if total_dependencies > 0:
                avg_weight = weight_factor / total_dependencies
                return min(base_probability * avg_weight, 1.0)
            
            return base_probability
            
        except Exception as e:
            logger.error(f"Error calculating cascade probability: {e}")
            return 0.5  # Default 50%
    
    def _estimate_recovery_time(self, failed_service: str, affected_services: List[str]) -> float:
        """Estimate total recovery time for affected services."""
        try:
            # Base recovery times by service type (in seconds)
            base_recovery_times = {
                "database": 300,  # 5 minutes
                "storage": 180,   # 3 minutes
                "authentication": 120,  # 2 minutes
                "api_gateway": 60,      # 1 minute
                "annotation_service": 120,
                "quality_service": 90,
                "export_service": 150,
                "ai_services": 240,     # 4 minutes
                "label_studio": 180
            }
            
            total_time = 0.0
            
            # Add recovery time for failed service
            total_time += base_recovery_times.get(failed_service, 120)
            
            # Add recovery time for affected services (can be done in parallel)
            if affected_services:
                max_affected_time = max(
                    base_recovery_times.get(service, 120) 
                    for service in affected_services
                )
                total_time += max_affected_time * 0.5  # Assume 50% overlap
            
            return total_time
            
        except Exception as e:
            logger.error(f"Error estimating recovery time: {e}")
            return 300.0  # Default 5 minutes
    
    def _generate_recovery_order(self, affected_services: List[str]) -> List[str]:
        """Generate optimal recovery order for affected services."""
        try:
            # Create subgraph with only affected services
            subgraph = self.dependency_graph.subgraph(affected_services)
            
            # Perform topological sort to get dependency order
            try:
                topo_order = list(nx.topological_sort(subgraph))
                # Reverse to get recovery order (dependencies first)
                recovery_order = list(reversed(topo_order))
            except nx.NetworkXError:
                # Handle cycles by using criticality scores
                recovery_order = sorted(
                    affected_services,
                    key=lambda s: (
                        self.service_nodes[s].recovery_priority,
                        -self.service_nodes[s].criticality_score
                    )
                )
            
            return recovery_order
            
        except Exception as e:
            logger.error(f"Error generating recovery order: {e}")
            return affected_services
    
    def _calculate_criticality_scores(self):
        """Calculate criticality scores for all services."""
        try:
            # Calculate PageRank to determine service importance
            pagerank_scores = nx.pagerank(self.dependency_graph, weight='weight')
            
            # Calculate betweenness centrality
            betweenness_scores = nx.betweenness_centrality(self.dependency_graph)
            
            # Combine scores
            for service_name, service_node in self.service_nodes.items():
                pagerank = pagerank_scores.get(service_name, 0.0)
                betweenness = betweenness_scores.get(service_name, 0.0)
                
                # Weighted combination
                criticality_score = (pagerank * 0.7) + (betweenness * 0.3)
                service_node.criticality_score = criticality_score
                
                # Update recovery priority based on criticality
                if criticality_score >= 0.2:
                    service_node.recovery_priority = 1  # Highest priority
                elif criticality_score >= 0.1:
                    service_node.recovery_priority = 2
                elif criticality_score >= 0.05:
                    service_node.recovery_priority = 3
                else:
                    service_node.recovery_priority = 5  # Normal priority
            
        except Exception as e:
            logger.error(f"Error calculating criticality scores: {e}")
    
    def _clear_old_cache(self):
        """Clear old cache entries."""
        current_time = time.time()
        if current_time - self.last_cache_update > self.cache_ttl:
            self.impact_cache.clear()
            self.last_cache_update = current_time
    
    def get_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Get dependencies for a specific service."""
        if service_name not in self.service_nodes:
            return {}
        
        service_node = self.service_nodes[service_name]
        dependencies = self.dependencies.get(service_name, [])
        
        return {
            "service_name": service_name,
            "status": service_node.status.value,
            "criticality_score": service_node.criticality_score,
            "recovery_priority": service_node.recovery_priority,
            "failure_count": service_node.failure_count,
            "dependencies": [
                {
                    "target_service": dep.target_service,
                    "dependency_type": dep.dependency_type.value,
                    "weight": dep.weight,
                    "timeout_threshold": dep.timeout_threshold,
                    "failure_threshold": dep.failure_threshold
                }
                for dep in dependencies
            ],
            "dependents": service_node.dependents
        }
    
    def get_dependency_graph_data(self) -> Dict[str, Any]:
        """Get dependency graph data for visualization."""
        nodes = []
        edges = []
        
        # Add nodes
        for service_name, service_node in self.service_nodes.items():
            nodes.append({
                "id": service_name,
                "label": service_name,
                "status": service_node.status.value,
                "criticality_score": service_node.criticality_score,
                "recovery_priority": service_node.recovery_priority,
                "failure_count": service_node.failure_count
            })
        
        # Add edges
        for source_service, deps in self.dependencies.items():
            for dep in deps:
                edges.append({
                    "source": source_service,
                    "target": dep.target_service,
                    "dependency_type": dep.dependency_type.value,
                    "weight": dep.weight
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "total_services": len(self.service_nodes),
                "total_dependencies": sum(len(deps) for deps in self.dependencies.values()),
                "healthy_services": sum(1 for node in self.service_nodes.values() if node.status == ServiceStatus.HEALTHY),
                "unhealthy_services": sum(1 for node in self.service_nodes.values() if node.status == ServiceStatus.UNHEALTHY)
            }
        }
    
    def get_dependency_statistics(self) -> Dict[str, Any]:
        """Get comprehensive dependency statistics."""
        try:
            total_services = len(self.service_nodes)
            total_dependencies = sum(len(deps) for deps in self.dependencies.values())
            
            # Status distribution
            status_counts = defaultdict(int)
            for service_node in self.service_nodes.values():
                status_counts[service_node.status.value] += 1
            
            # Dependency type distribution
            dep_type_counts = defaultdict(int)
            for deps in self.dependencies.values():
                for dep in deps:
                    dep_type_counts[dep.dependency_type.value] += 1
            
            # Critical services (top 5 by criticality score)
            critical_services = sorted(
                self.service_nodes.items(),
                key=lambda x: x[1].criticality_score,
                reverse=True
            )[:5]
            
            return {
                "total_services": total_services,
                "total_dependencies": total_dependencies,
                "monitoring_active": self.monitoring_active,
                "status_distribution": dict(status_counts),
                "dependency_type_distribution": dict(dep_type_counts),
                "critical_services": [
                    {
                        "service_name": name,
                        "criticality_score": node.criticality_score,
                        "status": node.status.value,
                        "recovery_priority": node.recovery_priority
                    }
                    for name, node in critical_services
                ],
                "cache_size": len(self.impact_cache)
            }
            
        except Exception as e:
            logger.error(f"Error getting dependency statistics: {e}")
            return {}


# Global service dependency mapper instance
service_dependency_mapper = ServiceDependencyMapper()


# Convenience functions
async def start_dependency_monitoring():
    """Start the global dependency monitoring."""
    await service_dependency_mapper.start_monitoring()


async def stop_dependency_monitoring():
    """Stop the global dependency monitoring."""
    await service_dependency_mapper.stop_monitoring()


async def analyze_service_impact(service_name: str) -> ImpactAnalysis:
    """Analyze the impact of a service failure."""
    return await service_dependency_mapper._analyze_cascade_impact(service_name)


def get_dependency_status() -> Dict[str, Any]:
    """Get current dependency mapper status."""
    return {
        "monitoring_active": service_dependency_mapper.monitoring_active,
        "total_services": len(service_dependency_mapper.service_nodes),
        "total_dependencies": sum(len(deps) for deps in service_dependency_mapper.dependencies.values()),
        "statistics": service_dependency_mapper.get_dependency_statistics()
    }


def register_service_dependency(source_service: str, target_service: str, 
                              dependency_type: str, **kwargs) -> bool:
    """Register a new service dependency."""
    try:
        dep_type = DependencyType(dependency_type)
        service_dependency_mapper.add_dependency(source_service, target_service, dep_type, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Error registering service dependency: {e}")
        return False