"""
Blue-Green Deployer for Zero-Downtime Deployments.

Provides blue-green deployment strategy with traffic shifting,
health validation, and automatic rollback capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    """Deployment strategies."""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    IMMEDIATE = "immediate"


class DeploymentPhase(Enum):
    """Phases of a deployment."""
    PREPARING = "preparing"
    BUILDING = "building"
    DEPLOYING = "deploying"
    VALIDATING = "validating"
    SHIFTING_TRAFFIC = "shifting_traffic"
    COMPLETED = "completed"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


class EnvironmentColor(Enum):
    """Environment colors for blue-green deployment."""
    BLUE = "blue"
    GREEN = "green"


@dataclass
class DeploymentEnvironment:
    """A deployment environment (blue or green)."""
    color: EnvironmentColor
    version: str
    is_active: bool = False
    is_healthy: bool = False
    traffic_percentage: int = 0
    instance_count: int = 0
    deployed_at: Optional[float] = None
    health_check_url: str = ""


@dataclass
class BlueGreenConfig:
    """Configuration for blue-green deployer."""
    health_check_timeout: float = 300.0
    health_check_interval: float = 10.0
    traffic_shift_steps: List[int] = field(default_factory=lambda: [10, 25, 50, 75, 100])
    traffic_shift_interval: float = 60.0
    rollback_on_failure: bool = True
    validation_timeout: float = 120.0


@dataclass
class DeploymentEvent:
    """An event during deployment."""
    event_type: str
    phase: DeploymentPhase
    timestamp: float
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    """Result of a deployment."""
    success: bool
    deployment_id: str
    version: str
    strategy: DeploymentStrategy
    phase: DeploymentPhase
    active_environment: EnvironmentColor
    started_at: float
    completed_at: Optional[float] = None
    duration_seconds: Optional[float] = None
    events: List[DeploymentEvent] = field(default_factory=list)
    error_message: Optional[str] = None


class BlueGreenDeployer:
    """
    Blue-Green deployment manager.
    
    Features:
    - Zero-downtime deployments
    - Gradual traffic shifting
    - Health validation before traffic shift
    - Automatic rollback on failure
    - Deployment event tracking
    """
    
    def __init__(self, config: Optional[BlueGreenConfig] = None):
        self.config = config or BlueGreenConfig()
        
        # Initialize environments
        self.environments: Dict[EnvironmentColor, DeploymentEnvironment] = {
            EnvironmentColor.BLUE: DeploymentEnvironment(
                color=EnvironmentColor.BLUE,
                version="",
                is_active=True,
                traffic_percentage=100
            ),
            EnvironmentColor.GREEN: DeploymentEnvironment(
                color=EnvironmentColor.GREEN,
                version="",
                is_active=False,
                traffic_percentage=0
            )
        }
        
        self.deployment_history: deque = deque(maxlen=100)
        self.current_deployment: Optional[DeploymentResult] = None
        self._health_check_callback: Optional[Callable] = None
        self._deploy_callback: Optional[Callable] = None
        
        logger.info("BlueGreenDeployer initialized")
    
    def set_health_check_callback(self, callback: Callable):
        """Set the health check callback function."""
        self._health_check_callback = callback
    
    def set_deploy_callback(self, callback: Callable):
        """Set the deployment callback function."""
        self._deploy_callback = callback
    
    def get_active_environment(self) -> DeploymentEnvironment:
        """Get the currently active environment."""
        for env in self.environments.values():
            if env.is_active and env.traffic_percentage == 100:
                return env
        return self.environments[EnvironmentColor.BLUE]
    
    def get_inactive_environment(self) -> DeploymentEnvironment:
        """Get the inactive environment for new deployments."""
        active = self.get_active_environment()
        return self.environments[
            EnvironmentColor.GREEN if active.color == EnvironmentColor.BLUE else EnvironmentColor.BLUE
        ]
    
    async def deploy(
        self,
        version: str,
        strategy: DeploymentStrategy = DeploymentStrategy.BLUE_GREEN,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeploymentResult:
        """Execute a deployment."""
        deployment_id = f"deploy_{int(time.time())}_{version}"
        
        result = DeploymentResult(
            success=False,
            deployment_id=deployment_id,
            version=version,
            strategy=strategy,
            phase=DeploymentPhase.PREPARING,
            active_environment=self.get_active_environment().color,
            started_at=time.time()
        )
        
        self.current_deployment = result
        
        logger.info(f"Starting {strategy.value} deployment: {deployment_id}")
        self._record_event(result, "deployment_started", f"Starting deployment of version {version}")
        
        try:
            if strategy == DeploymentStrategy.BLUE_GREEN:
                await self._execute_blue_green_deployment(result, metadata)
            elif strategy == DeploymentStrategy.CANARY:
                await self._execute_canary_deployment(result, metadata)
            elif strategy == DeploymentStrategy.ROLLING:
                await self._execute_rolling_deployment(result, metadata)
            else:
                await self._execute_immediate_deployment(result, metadata)
            
        except Exception as e:
            result.phase = DeploymentPhase.FAILED
            result.error_message = str(e)
            self._record_event(result, "deployment_failed", f"Deployment failed: {e}")
            
            if self.config.rollback_on_failure:
                await self._rollback(result)
        
        result.completed_at = time.time()
        result.duration_seconds = result.completed_at - result.started_at
        
        self.deployment_history.append(result)
        self.current_deployment = None
        
        return result
    
    async def _execute_blue_green_deployment(
        self,
        result: DeploymentResult,
        metadata: Optional[Dict[str, Any]]
    ):
        """Execute blue-green deployment strategy."""
        target_env = self.get_inactive_environment()
        
        # Phase 1: Deploy to inactive environment
        result.phase = DeploymentPhase.DEPLOYING
        self._record_event(result, "deploying", f"Deploying to {target_env.color.value} environment")
        
        if self._deploy_callback:
            deploy_success = await self._deploy_callback(
                target_env.color.value,
                result.version,
                metadata
            )
            if not deploy_success:
                raise Exception(f"Failed to deploy to {target_env.color.value}")
        
        target_env.version = result.version
        target_env.deployed_at = time.time()
        
        # Phase 2: Validate health
        result.phase = DeploymentPhase.VALIDATING
        self._record_event(result, "validating", "Validating deployment health")
        
        is_healthy = await self._validate_health(target_env)
        if not is_healthy:
            raise Exception("Health validation failed")
        
        target_env.is_healthy = True
        
        # Phase 3: Shift traffic gradually
        result.phase = DeploymentPhase.SHIFTING_TRAFFIC
        await self._shift_traffic_gradually(result, target_env)
        
        # Phase 4: Complete
        result.phase = DeploymentPhase.COMPLETED
        result.success = True
        result.active_environment = target_env.color
        
        # Update environment states
        for env in self.environments.values():
            env.is_active = (env.color == target_env.color)
        
        self._record_event(result, "deployment_completed", f"Deployment completed successfully")
        logger.info(f"Deployment {result.deployment_id} completed successfully")
    
    async def _execute_canary_deployment(
        self,
        result: DeploymentResult,
        metadata: Optional[Dict[str, Any]]
    ):
        """Execute canary deployment strategy."""
        # Similar to blue-green but with smaller initial traffic percentage
        target_env = self.get_inactive_environment()
        
        result.phase = DeploymentPhase.DEPLOYING
        if self._deploy_callback:
            await self._deploy_callback(target_env.color.value, result.version, metadata)
        
        target_env.version = result.version
        target_env.deployed_at = time.time()
        
        # Start with small traffic percentage
        result.phase = DeploymentPhase.SHIFTING_TRAFFIC
        canary_steps = [5, 10, 25, 50, 75, 100]
        
        for percentage in canary_steps:
            self._record_event(result, "traffic_shift", f"Shifting {percentage}% traffic to canary")
            
            target_env.traffic_percentage = percentage
            active_env = self.get_active_environment()
            active_env.traffic_percentage = 100 - percentage
            
            # Validate health at each step
            await asyncio.sleep(self.config.traffic_shift_interval)
            
            if not await self._validate_health(target_env):
                raise Exception(f"Canary failed at {percentage}% traffic")
        
        result.phase = DeploymentPhase.COMPLETED
        result.success = True
        result.active_environment = target_env.color
        
        for env in self.environments.values():
            env.is_active = (env.color == target_env.color)
    
    async def _execute_rolling_deployment(
        self,
        result: DeploymentResult,
        metadata: Optional[Dict[str, Any]]
    ):
        """Execute rolling deployment strategy."""
        # For rolling deployment, we update instances one by one
        result.phase = DeploymentPhase.DEPLOYING
        self._record_event(result, "rolling_update", "Starting rolling update")
        
        if self._deploy_callback:
            await self._deploy_callback("rolling", result.version, metadata)
        
        result.phase = DeploymentPhase.VALIDATING
        active_env = self.get_active_environment()
        
        if await self._validate_health(active_env):
            active_env.version = result.version
            result.phase = DeploymentPhase.COMPLETED
            result.success = True
        else:
            raise Exception("Rolling update health check failed")
    
    async def _execute_immediate_deployment(
        self,
        result: DeploymentResult,
        metadata: Optional[Dict[str, Any]]
    ):
        """Execute immediate deployment (no gradual traffic shift)."""
        target_env = self.get_inactive_environment()
        
        result.phase = DeploymentPhase.DEPLOYING
        if self._deploy_callback:
            await self._deploy_callback(target_env.color.value, result.version, metadata)
        
        target_env.version = result.version
        target_env.deployed_at = time.time()
        
        # Immediate traffic switch
        result.phase = DeploymentPhase.SHIFTING_TRAFFIC
        target_env.traffic_percentage = 100
        self.get_active_environment().traffic_percentage = 0
        
        result.phase = DeploymentPhase.COMPLETED
        result.success = True
        result.active_environment = target_env.color
        
        for env in self.environments.values():
            env.is_active = (env.color == target_env.color)
    
    async def _validate_health(self, env: DeploymentEnvironment) -> bool:
        """Validate environment health."""
        if self._health_check_callback:
            start_time = time.time()
            
            while time.time() - start_time < self.config.health_check_timeout:
                try:
                    is_healthy = await self._health_check_callback(env.color.value)
                    if is_healthy:
                        return True
                except Exception as e:
                    logger.warning(f"Health check error: {e}")
                
                await asyncio.sleep(self.config.health_check_interval)
            
            return False
        
        # Default: assume healthy if no callback
        return True
    
    async def _shift_traffic_gradually(
        self,
        result: DeploymentResult,
        target_env: DeploymentEnvironment
    ):
        """Gradually shift traffic to target environment."""
        source_env = self.get_active_environment()
        
        for percentage in self.config.traffic_shift_steps:
            self._record_event(
                result,
                "traffic_shift",
                f"Shifting traffic: {target_env.color.value}={percentage}%, {source_env.color.value}={100-percentage}%"
            )
            
            target_env.traffic_percentage = percentage
            source_env.traffic_percentage = 100 - percentage
            
            # Wait and validate
            await asyncio.sleep(self.config.traffic_shift_interval)
            
            if not await self._validate_health(target_env):
                raise Exception(f"Health check failed at {percentage}% traffic")
    
    async def _rollback(self, result: DeploymentResult):
        """Rollback a failed deployment."""
        result.phase = DeploymentPhase.ROLLING_BACK
        self._record_event(result, "rollback_started", "Starting rollback")
        
        logger.warning(f"Rolling back deployment {result.deployment_id}")
        
        # Restore traffic to original environment
        active_env = self.get_active_environment()
        inactive_env = self.get_inactive_environment()
        
        active_env.traffic_percentage = 100
        inactive_env.traffic_percentage = 0
        inactive_env.is_healthy = False
        
        self._record_event(result, "rollback_completed", "Rollback completed")
    
    async def manual_rollback(self) -> bool:
        """Manually trigger a rollback to the previous version."""
        active = self.get_active_environment()
        inactive = self.get_inactive_environment()
        
        if not inactive.version:
            logger.error("No previous version to rollback to")
            return False
        
        logger.info(f"Manual rollback from {active.version} to {inactive.version}")
        
        # Swap traffic
        active.traffic_percentage = 0
        active.is_active = False
        
        inactive.traffic_percentage = 100
        inactive.is_active = True
        
        return True
    
    def _record_event(
        self,
        result: DeploymentResult,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a deployment event."""
        event = DeploymentEvent(
            event_type=event_type,
            phase=result.phase,
            timestamp=time.time(),
            message=message,
            metadata=metadata or {}
        )
        result.events.append(event)
        logger.info(f"[{result.deployment_id}] {message}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current deployment state."""
        return {
            "environments": {
                color.value: {
                    "version": env.version,
                    "is_active": env.is_active,
                    "is_healthy": env.is_healthy,
                    "traffic_percentage": env.traffic_percentage,
                    "deployed_at": env.deployed_at
                }
                for color, env in self.environments.items()
            },
            "current_deployment": {
                "id": self.current_deployment.deployment_id,
                "phase": self.current_deployment.phase.value,
                "version": self.current_deployment.version
            } if self.current_deployment else None
        }
    
    def get_deployment_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get deployment history."""
        history = list(self.deployment_history)[-limit:]
        return [
            {
                "deployment_id": d.deployment_id,
                "version": d.version,
                "strategy": d.strategy.value,
                "success": d.success,
                "phase": d.phase.value,
                "duration_seconds": d.duration_seconds,
                "started_at": d.started_at,
                "completed_at": d.completed_at
            }
            for d in history
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get deployer statistics."""
        history = list(self.deployment_history)
        successful = sum(1 for d in history if d.success)
        
        return {
            "total_deployments": len(history),
            "successful_deployments": successful,
            "failed_deployments": len(history) - successful,
            "success_rate": successful / len(history) if history else 0,
            "avg_duration_seconds": (
                sum(d.duration_seconds for d in history if d.duration_seconds) / len(history)
                if history else 0
            ),
            "current_active_environment": self.get_active_environment().color.value,
            "current_version": self.get_active_environment().version
        }


# Global blue-green deployer instance
blue_green_deployer: Optional[BlueGreenDeployer] = None


def initialize_blue_green_deployer(
    config: Optional[BlueGreenConfig] = None
) -> BlueGreenDeployer:
    """Initialize the global blue-green deployer."""
    global blue_green_deployer
    blue_green_deployer = BlueGreenDeployer(config)
    return blue_green_deployer


def get_blue_green_deployer() -> Optional[BlueGreenDeployer]:
    """Get the global blue-green deployer instance."""
    return blue_green_deployer
