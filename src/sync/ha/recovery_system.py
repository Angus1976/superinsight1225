"""
Recovery system implementation for automatic service recovery.

This module provides recovery capabilities including:
- Automatic service restart
- Scaling operations
- Traffic redirection
- Self-healing mechanisms
"""

import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import docker
import kubernetes

from .models import (
    ServiceInstance, RecoveryAction, RecoveryPlan,
    ServiceStatus, ServiceMetrics
)
from .service_discovery import ServiceDiscovery, ServiceRegistry
from .health_checker import HealthChecker


logger = logging.getLogger(__name__)


class RecoverySystem:
    """Automatic recovery system for service failures."""
    
    def __init__(self, service_discovery: ServiceDiscovery,
                 health_checker: HealthChecker):
        """
        Initialize recovery system.
        
        Args:
            service_discovery: Service discovery instance
            health_checker: Health checker instance
        """
        self.discovery = service_discovery
        self.health_checker = health_checker
        
        self.recovery_plans: Dict[str, List[RecoveryPlan]] = {}
        self.active_recoveries: Dict[str, RecoveryPlan] = {}
        self.recovery_history: List[RecoveryPlan] = []
        
        self._running = False
        self._recovery_task: Optional[asyncio.Task] = None
        self._docker_client: Optional[docker.DockerClient] = None
        self._k8s_client: Optional[kubernetes.client.ApiClient] = None
        
        # Recovery action handlers
        self._action_handlers: Dict[RecoveryAction, Callable] = {
            RecoveryAction.RESTART_SERVICE: self._restart_service,
            RecoveryAction.SCALE_UP: self._scale_up_service,
            RecoveryAction.SCALE_DOWN: self._scale_down_service,
            RecoveryAction.REDIRECT_TRAFFIC: self._redirect_traffic,
            RecoveryAction.ALERT_ADMIN: self._alert_admin,
            RecoveryAction.AUTO_HEAL: self._auto_heal_service
        }
    
    async def start(self) -> None:
        """Start recovery system."""
        if self._running:
            return
        
        self._running = True
        
        # Initialize Docker client
        try:
            self._docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Failed to initialize Docker client: {e}")
        
        # Initialize Kubernetes client
        try:
            kubernetes.config.load_incluster_config()
            self._k8s_client = kubernetes.client.ApiClient()
        except Exception:
            try:
                kubernetes.config.load_kube_config()
                self._k8s_client = kubernetes.client.ApiClient()
            except Exception as e:
                logger.warning(f"Failed to initialize Kubernetes client: {e}")
        
        # Start recovery monitoring
        self._recovery_task = asyncio.create_task(self._recovery_loop())
        
        logger.info("Recovery system started")
    
    async def stop(self) -> None:
        """Stop recovery system."""
        self._running = False
        
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
        
        # Close clients
        if self._docker_client:
            self._docker_client.close()
        
        if self._k8s_client:
            await self._k8s_client.close()
        
        logger.info("Recovery system stopped")
    
    def register_recovery_plan(self, service_name: str, plan: RecoveryPlan) -> None:
        """
        Register a recovery plan for a service.
        
        Args:
            service_name: Name of the service
            plan: Recovery plan to register
        """
        if service_name not in self.recovery_plans:
            self.recovery_plans[service_name] = []
        
        self.recovery_plans[service_name].append(plan)
        
        # Sort by priority (lower number = higher priority)
        self.recovery_plans[service_name].sort(key=lambda p: p.priority)
        
        logger.info(f"Registered recovery plan for {service_name}: {plan.id}")
    
    def unregister_recovery_plan(self, service_name: str, plan_id: str) -> bool:
        """
        Unregister a recovery plan.
        
        Args:
            service_name: Name of the service
            plan_id: ID of the recovery plan
            
        Returns:
            True if plan was found and removed
        """
        if service_name not in self.recovery_plans:
            return False
        
        plans = self.recovery_plans[service_name]
        for i, plan in enumerate(plans):
            if plan.id == plan_id:
                del plans[i]
                logger.info(f"Unregistered recovery plan {plan_id} for {service_name}")
                return True
        
        return False
    
    async def trigger_recovery(self, service_name: str, failure_type: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Optional[RecoveryPlan]:
        """
        Trigger recovery for a service failure.
        
        Args:
            service_name: Name of the failed service
            failure_type: Type of failure
            metadata: Additional failure metadata
            
        Returns:
            Recovery plan being executed or None if no suitable plan found
        """
        # Check if recovery already in progress
        if service_name in self.active_recoveries:
            logger.warning(f"Recovery already in progress for {service_name}")
            return self.active_recoveries[service_name]
        
        # Find suitable recovery plan
        recovery_plan = self._find_recovery_plan(service_name, failure_type)
        if not recovery_plan:
            logger.error(f"No recovery plan found for {service_name} failure: {failure_type}")
            return None
        
        # Execute recovery plan
        success = await self._execute_recovery_plan(service_name, recovery_plan, metadata)
        
        # Update plan status
        recovery_plan.executed_at = datetime.utcnow()
        recovery_plan.completed_at = datetime.utcnow()
        recovery_plan.success = success
        
        # Add to history
        self.recovery_history.append(recovery_plan)
        
        # Remove from active recoveries
        if service_name in self.active_recoveries:
            del self.active_recoveries[service_name]
        
        return recovery_plan
    
    async def _recovery_loop(self) -> None:
        """Main recovery monitoring loop."""
        while self._running:
            try:
                await self._check_for_recovery_needs()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_for_recovery_needs(self) -> None:
        """Check for services that need recovery."""
        health_summaries = self.health_checker.get_all_health_summaries()
        
        for service_key, summary in health_summaries.items():
            try:
                parts = service_key.split(':', 1)
                if len(parts) != 2:
                    continue
                
                service_name, service_id = parts
                
                # Check if recovery is needed
                if await self._needs_recovery(service_name, service_id, summary):
                    failure_type = self._determine_failure_type(summary)
                    await self.trigger_recovery(service_name, failure_type, {
                        'service_id': service_id,
                        'health_summary': summary
                    })
            
            except Exception as e:
                logger.error(f"Error checking recovery need for {service_key}: {e}")
    
    async def _needs_recovery(self, service_name: str, service_id: str,
                            health_summary: Dict[str, Any]) -> bool:
        """
        Determine if a service needs recovery.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            health_summary: Health summary from health checker
            
        Returns:
            True if recovery is needed
        """
        # Check if already in recovery
        if service_name in self.active_recoveries:
            return False
        
        # Check failure count
        failure_count = health_summary.get('failure_count', 0)
        if failure_count < 5:  # Threshold for recovery
            return False
        
        # Check recent health rate
        recent_health_rate = health_summary.get('recent_health_rate', 1.0)
        if recent_health_rate > 0.1:  # Still some success
            return False
        
        # Check if service is marked as unhealthy
        service = await self.discovery.registry.get_service(service_name, service_id)
        if not service or service.status != ServiceStatus.UNHEALTHY:
            return False
        
        return True
    
    def _determine_failure_type(self, health_summary: Dict[str, Any]) -> str:
        """Determine the type of failure based on health summary."""
        latest_status = health_summary.get('latest_status', {})
        message = latest_status.get('message', '').lower()
        
        if 'timeout' in message:
            return 'timeout'
        elif 'connection' in message:
            return 'connection_failure'
        elif 'status code' in message:
            return 'http_error'
        else:
            return 'unknown_failure'
    
    def _find_recovery_plan(self, service_name: str, failure_type: str) -> Optional[RecoveryPlan]:
        """Find the best recovery plan for a service failure."""
        if service_name not in self.recovery_plans:
            return None
        
        plans = self.recovery_plans[service_name]
        
        # Find plan matching failure type
        for plan in plans:
            if plan.failure_type == failure_type or plan.failure_type == 'any':
                if plan.retry_count < plan.max_retries:
                    return plan
        
        # Fallback to generic plan
        for plan in plans:
            if plan.failure_type == 'any' and plan.retry_count < plan.max_retries:
                return plan
        
        return None
    
    async def _execute_recovery_plan(self, service_name: str, plan: RecoveryPlan,
                                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute a recovery plan.
        
        Args:
            service_name: Name of the service
            plan: Recovery plan to execute
            metadata: Additional metadata
            
        Returns:
            True if recovery successful
        """
        try:
            # Add to active recoveries
            self.active_recoveries[service_name] = plan
            plan.retry_count += 1
            
            logger.info(f"Executing recovery plan {plan.id} for {service_name}")
            
            # Execute each action in the plan
            for action in plan.actions:
                success = await self._execute_recovery_action(
                    service_name, action, plan, metadata
                )
                
                if not success:
                    plan.error_message = f"Recovery action {action.value} failed"
                    return False
            
            logger.info(f"Recovery plan {plan.id} completed successfully for {service_name}")
            return True
        
        except Exception as e:
            logger.error(f"Recovery plan execution failed: {e}")
            plan.error_message = str(e)
            return False
    
    async def _execute_recovery_action(self, service_name: str, action: RecoveryAction,
                                     plan: RecoveryPlan,
                                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Execute a specific recovery action."""
        try:
            handler = self._action_handlers.get(action)
            if not handler:
                logger.error(f"No handler for recovery action: {action}")
                return False
            
            return await handler(service_name, plan, metadata)
        
        except Exception as e:
            logger.error(f"Recovery action {action.value} failed: {e}")
            return False
    
    async def _restart_service(self, service_name: str, plan: RecoveryPlan,
                             metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Restart a service instance."""
        try:
            service_id = metadata.get('service_id') if metadata else None
            if not service_id:
                logger.error("Service ID not provided for restart action")
                return False
            
            # Try Docker restart first
            if self._docker_client:
                try:
                    container = self._docker_client.containers.get(service_id)
                    container.restart()
                    logger.info(f"Restarted Docker container {service_id}")
                    
                    # Wait for service to come back up
                    await asyncio.sleep(10)
                    return True
                
                except docker.errors.NotFound:
                    logger.debug(f"Container {service_id} not found in Docker")
                except Exception as e:
                    logger.error(f"Docker restart failed: {e}")
            
            # Try Kubernetes restart
            if self._k8s_client:
                try:
                    apps_v1 = kubernetes.client.AppsV1Api(self._k8s_client)
                    
                    # Find deployment by service name
                    deployments = apps_v1.list_deployment_for_all_namespaces(
                        label_selector=f"app={service_name}"
                    )
                    
                    for deployment in deployments.items:
                        # Restart by updating annotation
                        deployment.spec.template.metadata.annotations = {
                            'kubectl.kubernetes.io/restartedAt': datetime.utcnow().isoformat()
                        }
                        
                        apps_v1.patch_namespaced_deployment(
                            name=deployment.metadata.name,
                            namespace=deployment.metadata.namespace,
                            body=deployment
                        )
                        
                        logger.info(f"Restarted Kubernetes deployment {deployment.metadata.name}")
                        
                        # Wait for rollout
                        await asyncio.sleep(30)
                        return True
                
                except Exception as e:
                    logger.error(f"Kubernetes restart failed: {e}")
            
            # Fallback to process restart (if running as process)
            try:
                # This is a simplified example - in practice you'd need
                # more sophisticated process management
                result = subprocess.run(
                    ['systemctl', 'restart', service_name],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    logger.info(f"Restarted system service {service_name}")
                    await asyncio.sleep(10)
                    return True
                else:
                    logger.error(f"System service restart failed: {result.stderr}")
            
            except Exception as e:
                logger.error(f"System service restart failed: {e}")
            
            return False
        
        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            return False
    
    async def _scale_up_service(self, service_name: str, plan: RecoveryPlan,
                              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Scale up a service."""
        try:
            if not self._k8s_client:
                logger.error("Kubernetes client not available for scaling")
                return False
            
            apps_v1 = kubernetes.client.AppsV1Api(self._k8s_client)
            
            # Find deployment
            deployments = apps_v1.list_deployment_for_all_namespaces(
                label_selector=f"app={service_name}"
            )
            
            for deployment in deployments.items:
                current_replicas = deployment.spec.replicas or 1
                new_replicas = min(current_replicas + 1, 10)  # Max 10 replicas
                
                # Update replica count
                deployment.spec.replicas = new_replicas
                
                apps_v1.patch_namespaced_deployment(
                    name=deployment.metadata.name,
                    namespace=deployment.metadata.namespace,
                    body=deployment
                )
                
                logger.info(
                    f"Scaled up {deployment.metadata.name} from {current_replicas} "
                    f"to {new_replicas} replicas"
                )
                
                return True
            
            logger.error(f"No deployment found for service {service_name}")
            return False
        
        except Exception as e:
            logger.error(f"Scale up failed: {e}")
            return False
    
    async def _scale_down_service(self, service_name: str, plan: RecoveryPlan,
                                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Scale down a service."""
        try:
            if not self._k8s_client:
                logger.error("Kubernetes client not available for scaling")
                return False
            
            apps_v1 = kubernetes.client.AppsV1Api(self._k8s_client)
            
            # Find deployment
            deployments = apps_v1.list_deployment_for_all_namespaces(
                label_selector=f"app={service_name}"
            )
            
            for deployment in deployments.items:
                current_replicas = deployment.spec.replicas or 1
                new_replicas = max(current_replicas - 1, 1)  # Min 1 replica
                
                # Update replica count
                deployment.spec.replicas = new_replicas
                
                apps_v1.patch_namespaced_deployment(
                    name=deployment.metadata.name,
                    namespace=deployment.metadata.namespace,
                    body=deployment
                )
                
                logger.info(
                    f"Scaled down {deployment.metadata.name} from {current_replicas} "
                    f"to {new_replicas} replicas"
                )
                
                return True
            
            logger.error(f"No deployment found for service {service_name}")
            return False
        
        except Exception as e:
            logger.error(f"Scale down failed: {e}")
            return False
    
    async def _redirect_traffic(self, service_name: str, plan: RecoveryPlan,
                              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Redirect traffic away from failed instances."""
        try:
            # Get all instances of the service
            instances = await self.discovery.discover_services(service_name, healthy_only=False)
            
            # Mark unhealthy instances
            for instance in instances:
                if not instance.is_healthy:
                    await self.discovery.registry.update_service_status(
                        service_name, instance.id, ServiceStatus.UNHEALTHY
                    )
            
            logger.info(f"Redirected traffic for service {service_name}")
            return True
        
        except Exception as e:
            logger.error(f"Traffic redirection failed: {e}")
            return False
    
    async def _alert_admin(self, service_name: str, plan: RecoveryPlan,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert to administrators."""
        try:
            # This is a placeholder - implement actual alerting mechanism
            # (email, Slack, PagerDuty, etc.)
            
            alert_message = (
                f"ALERT: Service {service_name} requires manual intervention. "
                f"Recovery plan {plan.id} executed. "
                f"Failure type: {plan.failure_type}"
            )
            
            logger.critical(alert_message)
            
            # In a real implementation, you would send this to your alerting system
            # await send_alert(alert_message)
            
            return True
        
        except Exception as e:
            logger.error(f"Admin alert failed: {e}")
            return False
    
    async def _auto_heal_service(self, service_name: str, plan: RecoveryPlan,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Perform automatic healing actions."""
        try:
            # Combine multiple recovery actions
            success = True
            
            # First try to restart
            success &= await self._restart_service(service_name, plan, metadata)
            
            # If restart fails, try scaling up
            if not success:
                success = await self._scale_up_service(service_name, plan, metadata)
            
            # Redirect traffic regardless
            await self._redirect_traffic(service_name, plan, metadata)
            
            return success
        
        except Exception as e:
            logger.error(f"Auto-heal failed: {e}")
            return False
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery system statistics."""
        total_recoveries = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r.success)
        
        if total_recoveries == 0:
            return {
                "total_recoveries": 0,
                "success_rate": 0.0,
                "active_recoveries": len(self.active_recoveries),
                "registered_plans": sum(len(plans) for plans in self.recovery_plans.values())
            }
        
        return {
            "total_recoveries": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "success_rate": successful_recoveries / total_recoveries,
            "active_recoveries": len(self.active_recoveries),
            "registered_plans": sum(len(plans) for plans in self.recovery_plans.values()),
            "recent_recoveries": [
                {
                    "id": r.id,
                    "service_name": r.service_name,
                    "failure_type": r.failure_type,
                    "actions": [a.value for a in r.actions],
                    "success": r.success,
                    "retry_count": r.retry_count,
                    "created_at": r.created_at.isoformat()
                }
                for r in self.recovery_history[-10:]  # Last 10 recoveries
            ]
        }