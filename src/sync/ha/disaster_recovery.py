"""
Disaster recovery implementation for high availability.

This module provides disaster recovery capabilities including:
- Cross-region data replication
- Disaster recovery orchestration
- Recovery time objective (RTO) management
- Recovery point objective (RPO) management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from .models import ServiceInstance, ServiceStatus
from .service_discovery import ServiceDiscovery, ServiceRegistry
from .backup_manager import BackupManager, BackupJob
from .failover_manager import FailoverManager


logger = logging.getLogger(__name__)


class DisasterType(Enum):
    """Disaster type enumeration."""
    DATACENTER_OUTAGE = "datacenter_outage"
    NETWORK_PARTITION = "network_partition"
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_CORRUPTION = "software_corruption"
    SECURITY_BREACH = "security_breach"
    NATURAL_DISASTER = "natural_disaster"


class RecoveryPhase(Enum):
    """Recovery phase enumeration."""
    DETECTION = "detection"
    ASSESSMENT = "assessment"
    ACTIVATION = "activation"
    RECOVERY = "recovery"
    VALIDATION = "validation"
    COMPLETION = "completion"


class DisasterRecoveryPlan:
    """Disaster recovery plan."""
    
    def __init__(self, plan_id: str, disaster_type: DisasterType, 
                 rto_minutes: int, rpo_minutes: int):
        self.plan_id = plan_id
        self.disaster_type = disaster_type
        self.rto_minutes = rto_minutes  # Recovery Time Objective
        self.rpo_minutes = rpo_minutes  # Recovery Point Objective
        self.steps: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.active = True


class DisasterRecoveryExecution:
    """Disaster recovery execution instance."""
    
    def __init__(self, execution_id: str, plan: DisasterRecoveryPlan, 
                 disaster_type: DisasterType):
        self.execution_id = execution_id
        self.plan = plan
        self.disaster_type = disaster_type
        self.phase = RecoveryPhase.DETECTION
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.success = False
        self.error_message: Optional[str] = None
        self.steps_completed = 0
        self.total_steps = len(plan.steps)
        self.metadata: Dict[str, Any] = {}
    
    @property
    def duration(self) -> Optional[float]:
        """Get execution duration in minutes."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 60
        return None
    
    @property
    def rto_met(self) -> bool:
        """Check if RTO was met."""
        if self.duration is None:
            return False
        return self.duration <= self.plan.rto_minutes


class DisasterRecoveryManager:
    """Disaster recovery manager for orchestrating recovery operations."""
    
    def __init__(self, service_discovery: ServiceDiscovery,
                 backup_manager: BackupManager,
                 failover_manager: FailoverManager,
                 config: Dict[str, Any]):
        """
        Initialize disaster recovery manager.
        
        Args:
            service_discovery: Service discovery instance
            backup_manager: Backup manager instance
            failover_manager: Failover manager instance
            config: DR configuration
        """
        self.discovery = service_discovery
        self.backup_manager = backup_manager
        self.failover_manager = failover_manager
        self.config = config
        
        self.recovery_plans: Dict[DisasterType, DisasterRecoveryPlan] = {}
        self.active_executions: Dict[str, DisasterRecoveryExecution] = {}
        self.execution_history: List[DisasterRecoveryExecution] = []
        
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[DisasterRecoveryExecution], None]] = []
        
        # Initialize default recovery plans
        self._initialize_default_plans()
    
    async def start(self) -> None:
        """Start disaster recovery manager."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("Disaster recovery manager started")
    
    async def stop(self) -> None:
        """Stop disaster recovery manager."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Disaster recovery manager stopped")
    
    def register_recovery_plan(self, plan: DisasterRecoveryPlan) -> None:
        """
        Register a disaster recovery plan.
        
        Args:
            plan: Recovery plan to register
        """
        self.recovery_plans[plan.disaster_type] = plan
        logger.info(f"Registered DR plan for {plan.disaster_type.value}: {plan.plan_id}")
    
    def add_callback(self, callback: Callable[[DisasterRecoveryExecution], None]) -> None:
        """Add callback for DR execution events."""
        self._callbacks.append(callback)
    
    async def trigger_disaster_recovery(self, disaster_type: DisasterType,
                                      metadata: Optional[Dict[str, Any]] = None) -> Optional[DisasterRecoveryExecution]:
        """
        Trigger disaster recovery for a specific disaster type.
        
        Args:
            disaster_type: Type of disaster
            metadata: Additional metadata
            
        Returns:
            Recovery execution instance or None if no plan available
        """
        # Check if recovery already in progress
        for execution in self.active_executions.values():
            if execution.disaster_type == disaster_type:
                logger.warning(f"DR already in progress for {disaster_type.value}")
                return execution
        
        # Find recovery plan
        plan = self.recovery_plans.get(disaster_type)
        if not plan or not plan.active:
            logger.error(f"No active DR plan found for {disaster_type.value}")
            return None
        
        # Create execution instance
        execution_id = f"dr_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{disaster_type.value}"
        execution = DisasterRecoveryExecution(execution_id, plan, disaster_type)
        
        if metadata:
            execution.metadata.update(metadata)
        
        # Add to active executions
        self.active_executions[execution_id] = execution
        
        # Execute recovery plan asynchronously
        asyncio.create_task(self._execute_recovery_plan(execution))
        
        logger.critical(f"Triggered disaster recovery: {disaster_type.value} (ID: {execution_id})")
        return execution
    
    async def _execute_recovery_plan(self, execution: DisasterRecoveryExecution) -> None:
        """Execute a disaster recovery plan."""
        try:
            logger.critical(f"Starting DR execution: {execution.execution_id}")
            
            # Phase 1: Assessment
            execution.phase = RecoveryPhase.ASSESSMENT
            await self._assess_disaster_impact(execution)
            
            # Phase 2: Activation
            execution.phase = RecoveryPhase.ACTIVATION
            await self._activate_recovery_procedures(execution)
            
            # Phase 3: Recovery
            execution.phase = RecoveryPhase.RECOVERY
            await self._execute_recovery_steps(execution)
            
            # Phase 4: Validation
            execution.phase = RecoveryPhase.VALIDATION
            await self._validate_recovery(execution)
            
            # Phase 5: Completion
            execution.phase = RecoveryPhase.COMPLETION
            execution.success = True
            execution.completed_at = datetime.utcnow()
            
            logger.critical(f"DR execution completed successfully: {execution.execution_id}")
        
        except Exception as e:
            execution.success = False
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            
            logger.error(f"DR execution failed: {execution.execution_id} - {e}")
        
        finally:
            # Move to history
            if execution.execution_id in self.active_executions:
                del self.active_executions[execution.execution_id]
            
            self.execution_history.append(execution)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(execution)
                except Exception as e:
                    logger.error(f"Error in DR callback: {e}")
    
    async def _assess_disaster_impact(self, execution: DisasterRecoveryExecution) -> None:
        """Assess the impact of the disaster."""
        logger.info(f"Assessing disaster impact for {execution.execution_id}")
        
        # Get all service instances
        all_services = {}
        for service_name in ['sync-gateway', 'pull-service', 'push-receiver', 
                           'data-transformer', 'conflict-resolver']:
            try:
                instances = await self.discovery.discover_services(service_name, healthy_only=False)
                all_services[service_name] = instances
            except Exception as e:
                logger.error(f"Failed to discover {service_name}: {e}")
                all_services[service_name] = []
        
        # Assess service health
        healthy_services = 0
        total_services = 0
        
        for service_name, instances in all_services.items():
            for instance in instances:
                total_services += 1
                if instance.is_healthy:
                    healthy_services += 1
        
        # Calculate impact
        if total_services > 0:
            health_percentage = (healthy_services / total_services) * 100
        else:
            health_percentage = 0
        
        execution.metadata['impact_assessment'] = {
            'total_services': total_services,
            'healthy_services': healthy_services,
            'health_percentage': health_percentage,
            'services': all_services
        }
        
        logger.warning(f"Disaster impact: {health_percentage:.1f}% services healthy")
    
    async def _activate_recovery_procedures(self, execution: DisasterRecoveryExecution) -> None:
        """Activate recovery procedures."""
        logger.info(f"Activating recovery procedures for {execution.execution_id}")
        
        # Notify stakeholders
        await self._send_disaster_notification(execution)
        
        # Activate backup systems
        await self._activate_backup_systems(execution)
        
        # Prepare failover targets
        await self._prepare_failover_targets(execution)
    
    async def _execute_recovery_steps(self, execution: DisasterRecoveryExecution) -> None:
        """Execute recovery steps from the plan."""
        logger.info(f"Executing recovery steps for {execution.execution_id}")
        
        for i, step in enumerate(execution.plan.steps):
            try:
                step_type = step.get('type')
                step_config = step.get('config', {})
                
                logger.info(f"Executing step {i+1}/{len(execution.plan.steps)}: {step_type}")
                
                if step_type == 'failover_services':
                    await self._step_failover_services(execution, step_config)
                
                elif step_type == 'restore_from_backup':
                    await self._step_restore_from_backup(execution, step_config)
                
                elif step_type == 'scale_services':
                    await self._step_scale_services(execution, step_config)
                
                elif step_type == 'redirect_traffic':
                    await self._step_redirect_traffic(execution, step_config)
                
                elif step_type == 'validate_services':
                    await self._step_validate_services(execution, step_config)
                
                else:
                    logger.warning(f"Unknown recovery step type: {step_type}")
                
                execution.steps_completed += 1
                
            except Exception as e:
                logger.error(f"Recovery step {i+1} failed: {e}")
                raise
    
    async def _validate_recovery(self, execution: DisasterRecoveryExecution) -> None:
        """Validate that recovery was successful."""
        logger.info(f"Validating recovery for {execution.execution_id}")
        
        # Wait for services to stabilize
        await asyncio.sleep(30)
        
        # Check service health
        validation_results = {}
        
        for service_name in ['sync-gateway', 'pull-service', 'push-receiver']:
            try:
                instances = await self.discovery.discover_services(service_name, healthy_only=True)
                validation_results[service_name] = {
                    'healthy_instances': len(instances),
                    'status': 'healthy' if instances else 'unhealthy'
                }
            except Exception as e:
                validation_results[service_name] = {
                    'healthy_instances': 0,
                    'status': 'error',
                    'error': str(e)
                }
        
        execution.metadata['validation_results'] = validation_results
        
        # Check if recovery meets requirements
        healthy_services = sum(1 for r in validation_results.values() 
                             if r['status'] == 'healthy')
        total_services = len(validation_results)
        
        if healthy_services < total_services * 0.8:  # 80% threshold
            raise Exception(f"Recovery validation failed: only {healthy_services}/{total_services} services healthy")
        
        logger.info(f"Recovery validation passed: {healthy_services}/{total_services} services healthy")
    
    async def _step_failover_services(self, execution: DisasterRecoveryExecution,
                                    config: Dict[str, Any]) -> None:
        """Execute failover services step."""
        services = config.get('services', [])
        
        for service_name in services:
            try:
                # Get unhealthy instances
                instances = await self.discovery.discover_services(service_name, healthy_only=False)
                unhealthy_instances = [i for i in instances if not i.is_healthy]
                
                # Trigger failover for each unhealthy instance
                for instance in unhealthy_instances:
                    await self.failover_manager.trigger_failover(
                        service_name, instance.id, 
                        f"DR failover: {execution.disaster_type.value}"
                    )
                
                logger.info(f"Triggered failover for {len(unhealthy_instances)} instances of {service_name}")
                
            except Exception as e:
                logger.error(f"Failover failed for {service_name}: {e}")
                raise
    
    async def _step_restore_from_backup(self, execution: DisasterRecoveryExecution,
                                      config: Dict[str, Any]) -> None:
        """Execute restore from backup step."""
        backup_sources = config.get('sources', [])
        
        for source_config in backup_sources:
            source_type = source_config.get('type')
            target = source_config.get('target')
            
            try:
                # Find latest successful backup
                latest_backup = None
                for job in reversed(self.backup_manager.job_history):
                    if (job.source.startswith(f"{source_type}:") and 
                        job.status == 'completed'):
                        latest_backup = job
                        break
                
                if not latest_backup:
                    logger.warning(f"No backup found for {source_type}")
                    continue
                
                # Check RPO compliance
                backup_age = (datetime.utcnow() - latest_backup.completed_at).total_seconds() / 60
                if backup_age > execution.plan.rpo_minutes:
                    logger.warning(f"Backup age ({backup_age:.1f}min) exceeds RPO ({execution.plan.rpo_minutes}min)")
                
                # Restore backup
                success = await self.backup_manager.restore_backup(latest_backup.job_id, target)
                if not success:
                    raise Exception(f"Backup restoration failed for {source_type}")
                
                logger.info(f"Restored backup for {source_type} from {latest_backup.job_id}")
                
            except Exception as e:
                logger.error(f"Backup restoration failed for {source_type}: {e}")
                raise
    
    async def _step_scale_services(self, execution: DisasterRecoveryExecution,
                                 config: Dict[str, Any]) -> None:
        """Execute scale services step."""
        # This would integrate with Kubernetes or Docker Swarm
        # For now, just log the action
        services = config.get('services', {})
        
        for service_name, scale_config in services.items():
            target_replicas = scale_config.get('replicas', 2)
            logger.info(f"Scaling {service_name} to {target_replicas} replicas")
            
            # In a real implementation, this would call Kubernetes API
            # or Docker Swarm API to scale services
    
    async def _step_redirect_traffic(self, execution: DisasterRecoveryExecution,
                                   config: Dict[str, Any]) -> None:
        """Execute redirect traffic step."""
        # Update load balancer configuration or DNS records
        # For now, just mark unhealthy instances
        
        services = config.get('services', [])
        
        for service_name in services:
            instances = await self.discovery.discover_services(service_name, healthy_only=False)
            
            for instance in instances:
                if not instance.is_healthy:
                    await self.discovery.registry.update_service_status(
                        service_name, instance.id, ServiceStatus.UNHEALTHY
                    )
            
            logger.info(f"Redirected traffic for {service_name}")
    
    async def _step_validate_services(self, execution: DisasterRecoveryExecution,
                                    config: Dict[str, Any]) -> None:
        """Execute validate services step."""
        services = config.get('services', [])
        timeout = config.get('timeout', 300)  # 5 minutes default
        
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            all_healthy = True
            
            for service_name in services:
                instances = await self.discovery.discover_services(service_name, healthy_only=True)
                if not instances:
                    all_healthy = False
                    break
            
            if all_healthy:
                logger.info("All services validated successfully")
                return
            
            await asyncio.sleep(10)  # Wait 10 seconds before retry
        
        raise Exception(f"Service validation timeout after {timeout} seconds")
    
    async def _send_disaster_notification(self, execution: DisasterRecoveryExecution) -> None:
        """Send disaster notification to stakeholders."""
        # This would integrate with notification systems (email, Slack, PagerDuty)
        message = (
            f"DISASTER RECOVERY ACTIVATED\n"
            f"Type: {execution.disaster_type.value}\n"
            f"Execution ID: {execution.execution_id}\n"
            f"RTO: {execution.plan.rto_minutes} minutes\n"
            f"RPO: {execution.plan.rpo_minutes} minutes\n"
            f"Started: {execution.started_at.isoformat()}"
        )
        
        logger.critical(message)
    
    async def _activate_backup_systems(self, execution: DisasterRecoveryExecution) -> None:
        """Activate backup systems."""
        # Ensure backup systems are running
        logger.info("Activating backup systems")
        
        # This could trigger immediate backups of critical data
        # or ensure backup replication is active
    
    async def _prepare_failover_targets(self, execution: DisasterRecoveryExecution) -> None:
        """Prepare failover targets."""
        # Ensure failover targets are ready
        logger.info("Preparing failover targets")
        
        # This could pre-warm standby instances or
        # ensure secondary data centers are ready
    
    async def _monitor_loop(self) -> None:
        """Monitor for disaster conditions."""
        while self._running:
            try:
                await self._check_disaster_conditions()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"DR monitor loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_disaster_conditions(self) -> None:
        """Check for conditions that might trigger disaster recovery."""
        # This is a simplified implementation
        # In practice, you'd have more sophisticated monitoring
        
        # Check service health across all services
        total_services = 0
        healthy_services = 0
        
        for service_name in ['sync-gateway', 'pull-service', 'push-receiver']:
            try:
                instances = await self.discovery.discover_services(service_name, healthy_only=False)
                for instance in instances:
                    total_services += 1
                    if instance.is_healthy:
                        healthy_services += 1
            except Exception:
                pass
        
        if total_services > 0:
            health_percentage = (healthy_services / total_services) * 100
            
            # Trigger DR if less than 50% of services are healthy
            if health_percentage < 50:
                logger.warning(f"Low service health detected: {health_percentage:.1f}%")
                
                # Check if DR already in progress
                if not self.active_executions:
                    await self.trigger_disaster_recovery(
                        DisasterType.DATACENTER_OUTAGE,
                        {'trigger': 'automatic', 'health_percentage': health_percentage}
                    )
    
    def _initialize_default_plans(self) -> None:
        """Initialize default disaster recovery plans."""
        # Datacenter outage plan
        datacenter_plan = DisasterRecoveryPlan(
            "datacenter_outage_v1",
            DisasterType.DATACENTER_OUTAGE,
            rto_minutes=30,  # 30 minutes RTO
            rpo_minutes=15   # 15 minutes RPO
        )
        
        datacenter_plan.steps = [
            {
                'type': 'failover_services',
                'config': {
                    'services': ['sync-gateway', 'pull-service', 'push-receiver']
                }
            },
            {
                'type': 'restore_from_backup',
                'config': {
                    'sources': [
                        {'type': 'postgres', 'target': 'postgres:superinsight'},
                        {'type': 'redis', 'target': 'redis:0'}
                    ]
                }
            },
            {
                'type': 'scale_services',
                'config': {
                    'services': {
                        'sync-gateway': {'replicas': 3},
                        'pull-service': {'replicas': 2},
                        'push-receiver': {'replicas': 2}
                    }
                }
            },
            {
                'type': 'validate_services',
                'config': {
                    'services': ['sync-gateway', 'pull-service', 'push-receiver'],
                    'timeout': 300
                }
            }
        ]
        
        self.register_recovery_plan(datacenter_plan)
        
        # Network partition plan
        network_plan = DisasterRecoveryPlan(
            "network_partition_v1",
            DisasterType.NETWORK_PARTITION,
            rto_minutes=15,  # 15 minutes RTO
            rpo_minutes=5    # 5 minutes RPO
        )
        
        network_plan.steps = [
            {
                'type': 'redirect_traffic',
                'config': {
                    'services': ['sync-gateway', 'pull-service', 'push-receiver']
                }
            },
            {
                'type': 'validate_services',
                'config': {
                    'services': ['sync-gateway'],
                    'timeout': 180
                }
            }
        ]
        
        self.register_recovery_plan(network_plan)
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get disaster recovery statistics."""
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for e in self.execution_history if e.success)
        
        if total_executions == 0:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_recovery_time": 0.0,
                "rto_compliance_rate": 0.0,
                "active_executions": len(self.active_executions),
                "registered_plans": len(self.recovery_plans)
            }
        
        # Calculate average recovery time
        completed_executions = [e for e in self.execution_history if e.duration is not None]
        avg_time = 0.0
        if completed_executions:
            avg_time = sum(e.duration for e in completed_executions) / len(completed_executions)
        
        # Calculate RTO compliance rate
        rto_compliant = sum(1 for e in completed_executions if e.rto_met)
        rto_compliance_rate = rto_compliant / len(completed_executions) if completed_executions else 0.0
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions,
            "avg_recovery_time": avg_time,
            "rto_compliance_rate": rto_compliance_rate,
            "active_executions": len(self.active_executions),
            "registered_plans": len(self.recovery_plans),
            "recent_executions": [
                {
                    "execution_id": e.execution_id,
                    "disaster_type": e.disaster_type.value,
                    "phase": e.phase.value,
                    "success": e.success,
                    "duration": e.duration,
                    "rto_met": e.rto_met,
                    "started_at": e.started_at.isoformat()
                }
                for e in self.execution_history[-10:]  # Last 10 executions
            ]
        }