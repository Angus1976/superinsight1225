"""
Traffic Router for High Availability System.

Provides intelligent traffic routing, request distribution,
and routing policies for the high availability infrastructure.
"""

import asyncio
import logging
import time
import re
from typing import Dict, Any, List, Optional, Callable, Pattern
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from src.system.service_registry import ServiceInstance, get_service_registry
from src.system.load_balancer import get_load_balancer

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Traffic routing strategies."""
    DIRECT = "direct"
    LOAD_BALANCED = "load_balanced"
    CANARY = "canary"
    A_B_TEST = "a_b_test"
    HEADER_BASED = "header_based"
    PATH_BASED = "path_based"
    WEIGHTED = "weighted"


class RouteStatus(Enum):
    """Route status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAINING = "draining"


@dataclass
class RouteRule:
    """A routing rule definition."""
    rule_id: str
    name: str
    priority: int
    strategy: RoutingStrategy
    service_name: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    targets: List[Dict[str, Any]] = field(default_factory=list)
    status: RouteStatus = RouteStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    rule_id: str
    target_service: str
    target_instance: Optional[ServiceInstance]
    strategy_used: RoutingStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrafficRouterConfig:
    """Configuration for traffic router."""
    default_strategy: RoutingStrategy = RoutingStrategy.LOAD_BALANCED
    enable_canary: bool = True
    canary_percentage: float = 10.0
    enable_ab_testing: bool = True
    request_timeout_seconds: float = 30.0


class TrafficRouter:
    """
    Intelligent traffic router for request distribution.
    
    Features:
    - Multiple routing strategies
    - Path-based routing
    - Header-based routing
    - Canary deployments
    - A/B testing support
    - Weighted routing
    """
    
    def __init__(self, config: Optional[TrafficRouterConfig] = None):
        self.config = config or TrafficRouterConfig()
        self.rules: Dict[str, RouteRule] = {}
        self.routing_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.path_patterns: Dict[str, Pattern] = {}
        
        # Setup default routes
        self._setup_default_routes()
        
        logger.info("TrafficRouter initialized")
    
    def _setup_default_routes(self):
        """Setup default routing rules."""
        default_routes = [
            RouteRule(
                rule_id="api_default",
                name="API Default Route",
                priority=100,
                strategy=RoutingStrategy.LOAD_BALANCED,
                service_name="api_server",
                conditions={"path_prefix": "/api/"}
            ),
            RouteRule(
                rule_id="health_check",
                name="Health Check Route",
                priority=1000,
                strategy=RoutingStrategy.DIRECT,
                service_name="api_server",
                conditions={"path": "/health"}
            ),
            RouteRule(
                rule_id="label_studio",
                name="Label Studio Route",
                priority=200,
                strategy=RoutingStrategy.LOAD_BALANCED,
                service_name="label_studio",
                conditions={"path_prefix": "/label-studio/"}
            ),
            RouteRule(
                rule_id="ai_service",
                name="AI Service Route",
                priority=200,
                strategy=RoutingStrategy.LOAD_BALANCED,
                service_name="ai_service",
                conditions={"path_prefix": "/api/v1/ai/"}
            ),
            RouteRule(
                rule_id="quality_service",
                name="Quality Service Route",
                priority=200,
                strategy=RoutingStrategy.LOAD_BALANCED,
                service_name="quality_service",
                conditions={"path_prefix": "/api/v1/quality/"}
            ),
        ]
        
        for route in default_routes:
            self.add_rule(route)
    
    def add_rule(self, rule: RouteRule) -> bool:
        """Add a routing rule."""
        self.rules[rule.rule_id] = rule
        
        # Compile path patterns
        if "path_pattern" in rule.conditions:
            try:
                self.path_patterns[rule.rule_id] = re.compile(rule.conditions["path_pattern"])
            except re.error as e:
                logger.error(f"Invalid path pattern in rule {rule.rule_id}: {e}")
        
        logger.info(f"Added routing rule: {rule.name}")
        return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a routing rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            if rule_id in self.path_patterns:
                del self.path_patterns[rule_id]
            logger.info(f"Removed routing rule: {rule_id}")
            return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a routing rule."""
        if rule_id in self.rules:
            self.rules[rule_id].status = RouteStatus.ACTIVE
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a routing rule."""
        if rule_id in self.rules:
            self.rules[rule_id].status = RouteStatus.INACTIVE
            return True
        return False
    
    async def route(
        self,
        path: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        client_ip: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[RoutingDecision]:
        """
        Route a request to the appropriate service.
        
        Args:
            path: Request path
            method: HTTP method
            headers: Request headers
            query_params: Query parameters
            client_ip: Client IP address
            session_id: Session ID for sticky routing
        
        Returns:
            RoutingDecision with target information
        """
        headers = headers or {}
        query_params = query_params or {}
        
        # Find matching rule
        matching_rule = self._find_matching_rule(path, method, headers, query_params)
        
        if not matching_rule:
            logger.debug(f"No matching rule for path: {path}")
            return None
        
        # Get target instance based on strategy
        target_instance = await self._get_target_instance(
            matching_rule, headers, client_ip, session_id
        )
        
        # Record stats
        self.routing_stats[matching_rule.rule_id]["total"] += 1
        if target_instance:
            self.routing_stats[matching_rule.rule_id]["success"] += 1
        else:
            self.routing_stats[matching_rule.rule_id]["no_target"] += 1
        
        return RoutingDecision(
            rule_id=matching_rule.rule_id,
            target_service=matching_rule.service_name,
            target_instance=target_instance,
            strategy_used=matching_rule.strategy,
            metadata={"path": path, "method": method}
        )
    
    def _find_matching_rule(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        query_params: Dict[str, str]
    ) -> Optional[RouteRule]:
        """Find the best matching routing rule."""
        matching_rules = []
        
        for rule in self.rules.values():
            if rule.status != RouteStatus.ACTIVE:
                continue
            
            if self._rule_matches(rule, path, method, headers, query_params):
                matching_rules.append(rule)
        
        if not matching_rules:
            return None
        
        # Sort by priority (higher priority first)
        matching_rules.sort(key=lambda r: r.priority, reverse=True)
        return matching_rules[0]
    
    def _rule_matches(
        self,
        rule: RouteRule,
        path: str,
        method: str,
        headers: Dict[str, str],
        query_params: Dict[str, str]
    ) -> bool:
        """Check if a rule matches the request."""
        conditions = rule.conditions
        
        # Check exact path match
        if "path" in conditions:
            if path != conditions["path"]:
                return False
        
        # Check path prefix
        if "path_prefix" in conditions:
            if not path.startswith(conditions["path_prefix"]):
                return False
        
        # Check path pattern
        if rule.rule_id in self.path_patterns:
            if not self.path_patterns[rule.rule_id].match(path):
                return False
        
        # Check method
        if "methods" in conditions:
            if method not in conditions["methods"]:
                return False
        
        # Check headers
        if "headers" in conditions:
            for header_name, header_value in conditions["headers"].items():
                if headers.get(header_name) != header_value:
                    return False
        
        # Check query params
        if "query_params" in conditions:
            for param_name, param_value in conditions["query_params"].items():
                if query_params.get(param_name) != param_value:
                    return False
        
        return True
    
    async def _get_target_instance(
        self,
        rule: RouteRule,
        headers: Dict[str, str],
        client_ip: Optional[str],
        session_id: Optional[str]
    ) -> Optional[ServiceInstance]:
        """Get target instance based on routing strategy."""
        load_balancer = get_load_balancer()
        
        if rule.strategy == RoutingStrategy.DIRECT:
            return await self._direct_routing(rule)
        
        elif rule.strategy == RoutingStrategy.LOAD_BALANCED:
            if load_balancer:
                return await load_balancer.get_instance(
                    rule.service_name, session_id, client_ip
                )
            return await self._direct_routing(rule)
        
        elif rule.strategy == RoutingStrategy.CANARY:
            return await self._canary_routing(rule, headers)
        
        elif rule.strategy == RoutingStrategy.A_B_TEST:
            return await self._ab_test_routing(rule, headers, client_ip)
        
        elif rule.strategy == RoutingStrategy.HEADER_BASED:
            return await self._header_based_routing(rule, headers)
        
        elif rule.strategy == RoutingStrategy.WEIGHTED:
            return await self._weighted_routing(rule)
        
        else:
            return await self._direct_routing(rule)
    
    async def _direct_routing(self, rule: RouteRule) -> Optional[ServiceInstance]:
        """Direct routing to primary instance."""
        service_registry = get_service_registry()
        if service_registry:
            return service_registry.get_primary_instance(rule.service_name)
        return None
    
    async def _canary_routing(
        self,
        rule: RouteRule,
        headers: Dict[str, str]
    ) -> Optional[ServiceInstance]:
        """Canary routing - send percentage to canary."""
        import random
        
        service_registry = get_service_registry()
        if not service_registry:
            return None
        
        # Check for canary header override
        if headers.get("X-Canary") == "true":
            instances = service_registry.get_instances(rule.service_name, tags={"canary"})
            if instances:
                return instances[0]
        
        # Random selection based on percentage
        canary_percentage = rule.metadata.get("canary_percentage", self.config.canary_percentage)
        
        if random.random() * 100 < canary_percentage:
            instances = service_registry.get_instances(rule.service_name, tags={"canary"})
            if instances:
                return instances[0]
        
        return service_registry.get_primary_instance(rule.service_name)
    
    async def _ab_test_routing(
        self,
        rule: RouteRule,
        headers: Dict[str, str],
        client_ip: Optional[str]
    ) -> Optional[ServiceInstance]:
        """A/B test routing based on user segment."""
        service_registry = get_service_registry()
        if not service_registry:
            return None
        
        # Determine variant based on header or IP hash
        variant = headers.get("X-AB-Variant")
        
        if not variant and client_ip:
            # Hash IP to determine variant
            variant = "A" if hash(client_ip) % 2 == 0 else "B"
        
        variant = variant or "A"
        
        # Get instances for variant
        instances = service_registry.get_instances(rule.service_name, tags={f"variant_{variant}"})
        
        if instances:
            return instances[0]
        
        return service_registry.get_primary_instance(rule.service_name)
    
    async def _header_based_routing(
        self,
        rule: RouteRule,
        headers: Dict[str, str]
    ) -> Optional[ServiceInstance]:
        """Route based on header values."""
        service_registry = get_service_registry()
        if not service_registry:
            return None
        
        # Check routing headers
        routing_header = rule.metadata.get("routing_header", "X-Route-To")
        target_tag = headers.get(routing_header)
        
        if target_tag:
            instances = service_registry.get_instances(rule.service_name, tags={target_tag})
            if instances:
                return instances[0]
        
        return service_registry.get_primary_instance(rule.service_name)
    
    async def _weighted_routing(self, rule: RouteRule) -> Optional[ServiceInstance]:
        """Weighted routing based on target weights."""
        import random
        
        service_registry = get_service_registry()
        if not service_registry:
            return None
        
        targets = rule.targets
        if not targets:
            return service_registry.get_primary_instance(rule.service_name)
        
        # Calculate total weight
        total_weight = sum(t.get("weight", 100) for t in targets)
        
        # Random selection based on weight
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for target in targets:
            cumulative += target.get("weight", 100)
            if r <= cumulative:
                instance_id = target.get("instance_id")
                if instance_id:
                    return service_registry.get_instance(instance_id)
        
        return service_registry.get_primary_instance(rule.service_name)
    
    def setup_canary(
        self,
        service_name: str,
        canary_percentage: float,
        canary_instance_id: str
    ) -> str:
        """Setup canary deployment routing."""
        rule_id = f"canary_{service_name}"
        
        rule = RouteRule(
            rule_id=rule_id,
            name=f"Canary for {service_name}",
            priority=500,
            strategy=RoutingStrategy.CANARY,
            service_name=service_name,
            conditions={"path_prefix": "/"},
            metadata={
                "canary_percentage": canary_percentage,
                "canary_instance_id": canary_instance_id
            }
        )
        
        self.add_rule(rule)
        logger.info(f"Setup canary routing for {service_name} at {canary_percentage}%")
        return rule_id
    
    def setup_ab_test(
        self,
        service_name: str,
        variant_a_instance: str,
        variant_b_instance: str,
        split_percentage: float = 50.0
    ) -> str:
        """Setup A/B test routing."""
        rule_id = f"ab_test_{service_name}"
        
        rule = RouteRule(
            rule_id=rule_id,
            name=f"A/B Test for {service_name}",
            priority=500,
            strategy=RoutingStrategy.A_B_TEST,
            service_name=service_name,
            conditions={"path_prefix": "/"},
            targets=[
                {"instance_id": variant_a_instance, "variant": "A", "weight": split_percentage},
                {"instance_id": variant_b_instance, "variant": "B", "weight": 100 - split_percentage}
            ]
        )
        
        self.add_rule(rule)
        logger.info(f"Setup A/B test routing for {service_name}")
        return rule_id
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            "total_rules": len(self.rules),
            "active_rules": len([r for r in self.rules.values() if r.status == RouteStatus.ACTIVE]),
            "by_strategy": {
                s.value: len([r for r in self.rules.values() if r.strategy == s])
                for s in RoutingStrategy
            },
            "routing_stats": dict(self.routing_stats)
        }


# Global traffic router instance
traffic_router: Optional[TrafficRouter] = None


def initialize_traffic_router(config: Optional[TrafficRouterConfig] = None) -> TrafficRouter:
    """Initialize the global traffic router."""
    global traffic_router
    traffic_router = TrafficRouter(config)
    return traffic_router


def get_traffic_router() -> Optional[TrafficRouter]:
    """Get the global traffic router instance."""
    return traffic_router
