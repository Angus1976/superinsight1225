"""
High Availability (HA) module for SuperInsight data sync system.

This module provides enterprise-grade high availability features including:
- Service discovery and registration
- Load balancing and failover
- Health checking and monitoring
- Automatic recovery mechanisms
"""

from .service_discovery import ServiceDiscovery, ServiceRegistry
from .load_balancer import LoadBalancer, LoadBalancingStrategy
from .health_checker import HealthChecker, HealthStatus
from .failover_manager import FailoverManager, FailoverStrategy
from .recovery_system import RecoverySystem, RecoveryAction

__all__ = [
    'ServiceDiscovery',
    'ServiceRegistry', 
    'LoadBalancer',
    'LoadBalancingStrategy',
    'HealthChecker',
    'HealthStatus',
    'FailoverManager',
    'FailoverStrategy',
    'RecoverySystem',
    'RecoveryAction'
]