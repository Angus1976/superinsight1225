"""
High Availability Manager - Central coordinator for all HA components.

This module provides centralized management of high availability features:
- Service discovery and registration coordination
- Load balancing and failover orchestration
- Health monitoring and recovery automation
- Backup and disaster recovery coordination
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import redis.asyncio as redis

from .models import (
    ServiceInstance, ClusterConfig, ServiceStatus,
    LoadBalancerConfig, FailoverConfig, HealthCheckConfig
)
from .service_discovery import ServiceDiscovery, ServiceRegistry
from .load_balancer import LoadBalancer
from .health_checker import HealthChecker
from .failover_manager import FailoverManager
from .recovery_system import RecoverySystem
from .backup_manager import BackupManager
from .disaster_recovery import DisasterRecoveryManager


logger = logging.getLogger(__name__)


class HAManager:
    """High Availability Manager - Central coordinator for all HA components."""
    
    def __init__(self, redis_url: str, postgres_url: str, config: ClusterConfig):
        """
        Initialize HA Manager.
        
        Args:
            redis_url: Redis connection URL
            postgres_url: PostgreSQL connection URL
            config: Cluster configuration
        """
        self.redis_url = redis_url
        self.postgres_url = postgres_url
        self.config = config
        
        # Initialize Redis client
        self.redis_client = redis.from_url(redis_url)
        
        # Initialize HA components
        self.service_registry = ServiceRegistry(self.redis_client)
        self.service_discovery = ServiceDiscovery(self.service_registry)
        self.health_checker = HealthChecker(self.service_registry, config.load_balancer_config.health_check_config)
        self.load_balancer = LoadBalancer(self.service_discovery, config.load_balancer_config)
        self.failover_manager = FailoverManager(
            self.service_discovery, self.health_checker, 
            self.load_balancer, config.failover_config
        )
        self.recovery_system = RecoverySystem(self.service_discovery, self.health_checker)
        
        # Initialize backup and DR components
        backup_config = {
            'aws_access_key_id': config.load_balancer_config.health_check_config.__dict__.get('aws_access_key_id'),
            'aws_secret_access_key': config.load_balancer_config.health_check_config.__dict__.get('aws_secret_access_key'),
            'aws_region': config.load_balancer_config.health_check_config.__dict__.get('aws_region', 'us-east-1')
        }
        self.backup_manager = BackupManager(postgres_url, redis_url, backup_config)
        self.disaster_recovery = DisasterRecoveryManager(
            self.service_discovery, self.backup_manager, 
            self.failover_manager, {}
        )
        
        self._running = False
        self._management_task: Optional[asyncio.Task] = None
        self._registered_services: Dict[str, ServiceInstance] = {}
    
    async def start(self) -> None:
        """Start all HA components."""
        if self._running:
            return
        
        self._running = True
        
        try:
            # Start all components
            await self.health_checker.start()
            await self.failover_manager.start()
            await self.recovery_system.start()
            await self.backup_manager.start()
            await self.disaster_recovery.start()
            await self.service_discovery.start_watching()
            
            # Start management loop
            self._management_task = asyncio.create_task(self._management_loop())
            
            # Setup callbacks
            self._setup_callbacks()
            
            logger.info("HA Manager started successfully")
        
        except Exception as e:
            logger.error(f"Failed to start HA Manager: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop all HA components."""
        self._running = False
        
        # Stop management loop
        if self._management_task:
            self._management_task.cancel()
            try:
                await self._management_task
            except asyncio.CancelledError:
                pass
        
        # Stop all components
        try:
            await self.service_discovery.stop_watching()
            await self.disaster_recovery.stop()
            await self.backup_manager.stop()
            await self.recovery_system.stop()
            await self.failover_manager.stop()
            await self.health_checker.stop()
        except Exception as e:
            logger.error(f"Error stopping HA components: {e}")
        
        # Close Redis connection
        try:
            await self.redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        
        logger.info("HA Manager stopped")
    
    async def register_service(self, service: ServiceInstance) -> bool:
        """
        Register a service with the HA system.
        
        Args:
            service: Service instance to register
            
        Returns:
            True if registration successful
        """
        try:
            # Register with service registry
            success = await self.service_registry.register_service(service)
            if not success:
                return False
            
            # Add to health checker
            await self.health_checker.add_service(service)
            
            # Store locally
            service_key = f"{service.name}:{service.id}"
            self._registered_services[service_key] = service
            
            logger.info(f"Registered service with HA system: {service_key}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register service {service.name}:{service.id}: {e}")
            return False
    
    async def deregister_service(self, service_name: str, service_id: str) -> bool:
        """
        Deregister a service from the HA system.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            
        Returns:
            True if deregistration successful
        """
        try:
            # Remove from health checker
            await self.health_checker.remove_service(service_name, service_id)
            
            # Deregister from service registry
            success = await self.service_registry.deregister_service(service_name, service_id)
            
            # Remove from local storage
            service_key = f"{service_name}:{service_id}"
            if service_key in self._registered_services:
                del self._registered_services[service_key]
            
            logger.info(f"Deregistered service from HA system: {service_key}")
            return success
        
        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}:{service_id}: {e}")
            return False
    
    async def get_service_instance(self, service_name: str, 
                                 session_id: Optional[str] = None) -> Optional[ServiceInstance]:
        """
        Get a healthy service instance using load balancing.
        
        Args:
            service_name: Name of the service
            session_id: Optional session ID for sticky sessions
            
        Returns:
            Selected service instance or None if none available
        """
        return await self.load_balancer.select_instance(service_name, session_id)
    
    async def execute_request(self, service_name: str, path: str = "/",
                            method: str = "GET", **kwargs) -> Optional[Any]:
        """
        Execute a request with load balancing and failover.
        
        Args:
            service_name: Name of the service
            path: Request path
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response or None if all attempts failed
        """
        async with self.load_balancer as lb:
            return await lb.execute_request(service_name, path, method, **kwargs)
    
    async def trigger_backup(self, strategy: str, source: str, destination: str) -> bool:
        """
        Trigger a backup operation.
        
        Args:
            strategy: Backup strategy
            source: Source identifier
            destination: Destination path
            
        Returns:
            True if backup initiated successfully
        """
        try:
            job = await self.backup_manager.create_backup(strategy, source, destination)
            logger.info(f"Triggered backup: {job.job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to trigger backup: {e}")
            return False
    
    async def get_cluster_health(self) -> Dict[str, Any]:
        """Get overall cluster health status."""
        try:
            # Get service health summaries
            health_summaries = self.health_checker.get_all_health_summaries()
            
            # Calculate overall health
            total_services = len(health_summaries)
            healthy_services = sum(
                1 for summary in health_summaries.values()
                if summary['latest_status']['healthy']
            )
            
            health_percentage = (healthy_services / total_services * 100) if total_services > 0 else 0
            
            # Get component statistics
            failover_stats = self.failover_manager.get_failover_statistics()
            recovery_stats = self.recovery_system.get_recovery_statistics()
            backup_stats = self.backup_manager.get_backup_statistics()
            dr_stats = self.disaster_recovery.get_recovery_statistics()
            
            return {
                'cluster_name': self.config.name,
                'overall_health': {
                    'status': 'healthy' if health_percentage >= 80 else 'degraded' if health_percentage >= 50 else 'unhealthy',
                    'health_percentage': health_percentage,
                    'total_services': total_services,
                    'healthy_services': healthy_services
                },
                'services': health_summaries,
                'failover': failover_stats,
                'recovery': recovery_stats,
                'backup': backup_stats,
                'disaster_recovery': dr_stats,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {
                'cluster_name': self.config.name,
                'overall_health': {
                    'status': 'error',
                    'error': str(e)
                },
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _setup_callbacks(self) -> None:
        """Setup callbacks between HA components."""
        # Setup failover callback to trigger recovery
        def on_failover(failover_event):
            if not failover_event.success:
                # Trigger recovery for failed failover
                asyncio.create_task(
                    self.recovery_system.trigger_recovery(
                        failover_event.metadata.get('service_name', 'unknown'),
                        'failover_failure',
                        {'failover_event_id': failover_event.id}
                    )
                )
        
        self.failover_manager.add_failover_callback(on_failover)
        
        # Setup service discovery callback for health checker
        def on_service_change(services):
            for service in services:
                if service.is_healthy:
                    asyncio.create_task(self.health_checker.add_service(service))
        
        # Add watchers for known services
        for service_name in ['sync-gateway', 'pull-service', 'push-receiver', 
                           'data-transformer', 'conflict-resolver']:
            self.service_discovery.add_service_watcher(service_name, on_service_change)
    
    async def _management_loop(self) -> None:
        """Main management loop for HA operations."""
        while self._running:
            try:
                # Cleanup expired services
                await self.service_registry.cleanup_expired_services()
                
                # Check cluster scaling needs
                await self._check_scaling_needs()
                
                # Trigger scheduled backups
                await self._check_backup_schedules()
                
                # Monitor cluster health
                await self._monitor_cluster_health()
                
                await asyncio.sleep(60)  # Run every minute
            
            except Exception as e:
                logger.error(f"Management loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_scaling_needs(self) -> None:
        """Check if cluster needs scaling up or down."""
        try:
            for service_name in ['sync-gateway', 'pull-service', 'push-receiver']:
                instances = await self.service_discovery.discover_services(service_name)
                
                if len(instances) < self.config.min_instances:
                    logger.warning(f"Service {service_name} below minimum instances: {len(instances)}")
                    # In a real implementation, this would trigger auto-scaling
                
                elif len(instances) > self.config.max_instances:
                    logger.warning(f"Service {service_name} above maximum instances: {len(instances)}")
                    # In a real implementation, this would trigger scale-down
        
        except Exception as e:
            logger.error(f"Scaling check failed: {e}")
    
    async def _check_backup_schedules(self) -> None:
        """Check and execute scheduled backups."""
        # This is handled by the backup manager's scheduler
        pass
    
    async def _monitor_cluster_health(self) -> None:
        """Monitor overall cluster health and trigger alerts if needed."""
        try:
            health = await self.get_cluster_health()
            overall_health = health.get('overall_health', {})
            
            if overall_health.get('status') == 'unhealthy':
                logger.critical(f"Cluster health critical: {overall_health.get('health_percentage', 0):.1f}%")
                
                # In a real implementation, this would trigger alerts
                # await self._send_health_alert(health)
        
        except Exception as e:
            logger.error(f"Health monitoring failed: {e}")
    
    async def get_ha_metrics(self) -> Dict[str, Any]:
        """Get comprehensive HA metrics for monitoring."""
        try:
            cluster_health = await self.get_cluster_health()
            
            # Get load balancer stats
            connection_stats = self.load_balancer.get_connection_stats()
            response_time_stats = self.load_balancer.get_response_time_stats()
            
            return {
                'cluster_health': cluster_health,
                'load_balancer': {
                    'connection_stats': connection_stats,
                    'response_time_stats': response_time_stats
                },
                'registered_services': len(self._registered_services),
                'config': {
                    'min_instances': self.config.min_instances,
                    'max_instances': self.config.max_instances,
                    'target_cpu_utilization': self.config.target_cpu_utilization,
                    'target_memory_utilization': self.config.target_memory_utilization
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to get HA metrics: {e}")
            return {'error': str(e)}


# Convenience function for creating HA Manager with default config
def create_ha_manager(redis_url: str, postgres_url: str, 
                     cluster_name: str = "superinsight-sync-cluster") -> HAManager:
    """
    Create HA Manager with default configuration.
    
    Args:
        redis_url: Redis connection URL
        postgres_url: PostgreSQL connection URL
        cluster_name: Name of the cluster
        
    Returns:
        Configured HA Manager instance
    """
    config = ClusterConfig(name=cluster_name)
    return HAManager(redis_url, postgres_url, config)