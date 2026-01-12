"""
Rollback Controller for High Availability System.

Provides system rollback capabilities, version management, and safe
rollback procedures for configuration and deployment changes.
"""

import asyncio
import logging
import time
import uuid
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import deque

logger = logging.getLogger(__name__)


class RollbackType(Enum):
    """Types of rollback operations."""
    CONFIGURATION = "configuration"
    DEPLOYMENT = "deployment"
    DATABASE = "database"
    SERVICE = "service"
    FULL_SYSTEM = "full_system"


class RollbackStatus(Enum):
    """Status of a rollback operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VERIFIED = "verified"


@dataclass
class SystemVersion:
    """Represents a system version/state."""
    version_id: str
    version_number: str
    created_at: float
    description: str
    components: Dict[str, str]  # component -> version
    configuration_snapshot: Dict[str, Any]
    is_stable: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class RollbackPoint:
    """A point in time that can be rolled back to."""
    point_id: str
    version: SystemVersion
    created_at: float
    rollback_type: RollbackType
    can_rollback: bool = True
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    rollback_id: str
    from_version: str
    to_version: str
    duration_seconds: float
    components_rolled_back: List[str]
    message: str
    errors: List[str] = field(default_factory=list)


@dataclass
class RollbackConfig:
    """Configuration for rollback controller."""
    max_rollback_points: int = 50
    auto_create_points: bool = True
    verify_after_rollback: bool = True
    backup_before_rollback: bool = True
    rollback_timeout_seconds: float = 300.0
    state_dir: str = "data/rollback_states"


class RollbackController:
    """
    System rollback controller for safe version management.
    
    Features:
    - Automatic rollback point creation
    - Safe rollback procedures
    - Version management
    - Configuration rollback
    - Deployment rollback
    - Rollback verification
    """
    
    def __init__(self, config: Optional[RollbackConfig] = None):
        self.config = config or RollbackConfig()
        self.rollback_points: Dict[str, RollbackPoint] = {}
        self.versions: Dict[str, SystemVersion] = {}
        self.rollback_history: deque = deque(maxlen=500)
        self.current_version: Optional[str] = None
        self.rollback_handlers: Dict[RollbackType, Callable] = {}
        
        # Ensure state directory exists
        self._ensure_state_dir()
        
        # Load existing state
        self._load_state()
        
        # Register default handlers
        self._register_default_handlers()
        
        logger.info("RollbackController initialized")
    
    def _ensure_state_dir(self):
        """Ensure state directory exists."""
        state_path = Path(self.config.state_dir)
        state_path.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self):
        """Load existing rollback state from disk."""
        state_file = Path(self.config.state_dir) / "rollback_state.json"
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load versions
                    for v_data in data.get("versions", []):
                        version = SystemVersion(
                            version_id=v_data["version_id"],
                            version_number=v_data["version_number"],
                            created_at=v_data["created_at"],
                            description=v_data["description"],
                            components=v_data.get("components", {}),
                            configuration_snapshot=v_data.get("configuration_snapshot", {}),
                            is_stable=v_data.get("is_stable", True),
                            tags=v_data.get("tags", {})
                        )
                        self.versions[version.version_id] = version
                    
                    # Load rollback points
                    for rp_data in data.get("rollback_points", []):
                        version = self.versions.get(rp_data["version_id"])
                        if version:
                            point = RollbackPoint(
                                point_id=rp_data["point_id"],
                                version=version,
                                created_at=rp_data["created_at"],
                                rollback_type=RollbackType(rp_data["rollback_type"]),
                                can_rollback=rp_data.get("can_rollback", True),
                                dependencies=rp_data.get("dependencies", []),
                                metadata=rp_data.get("metadata", {})
                            )
                            self.rollback_points[point.point_id] = point
                    
                    self.current_version = data.get("current_version")
                    
                logger.info(f"Loaded {len(self.versions)} versions and {len(self.rollback_points)} rollback points")
            except Exception as e:
                logger.warning(f"Failed to load rollback state: {e}")
    
    def _save_state(self):
        """Save rollback state to disk."""
        state_file = Path(self.config.state_dir) / "rollback_state.json"
        
        try:
            data = {
                "versions": [
                    {
                        "version_id": v.version_id,
                        "version_number": v.version_number,
                        "created_at": v.created_at,
                        "description": v.description,
                        "components": v.components,
                        "configuration_snapshot": v.configuration_snapshot,
                        "is_stable": v.is_stable,
                        "tags": v.tags
                    }
                    for v in self.versions.values()
                ],
                "rollback_points": [
                    {
                        "point_id": rp.point_id,
                        "version_id": rp.version.version_id,
                        "created_at": rp.created_at,
                        "rollback_type": rp.rollback_type.value,
                        "can_rollback": rp.can_rollback,
                        "dependencies": rp.dependencies,
                        "metadata": rp.metadata
                    }
                    for rp in self.rollback_points.values()
                ],
                "current_version": self.current_version,
                "updated_at": time.time()
            }
            
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save rollback state: {e}")
    
    def _register_default_handlers(self):
        """Register default rollback handlers."""
        self.register_handler(RollbackType.CONFIGURATION, self._rollback_configuration)
        self.register_handler(RollbackType.DEPLOYMENT, self._rollback_deployment)
        self.register_handler(RollbackType.DATABASE, self._rollback_database)
        self.register_handler(RollbackType.SERVICE, self._rollback_service)
        self.register_handler(RollbackType.FULL_SYSTEM, self._rollback_full_system)
    
    def register_handler(self, rollback_type: RollbackType, handler: Callable):
        """Register a rollback handler for a specific type."""
        self.rollback_handlers[rollback_type] = handler
        logger.debug(f"Registered rollback handler for {rollback_type.value}")
    
    async def create_version(
        self,
        version_number: str,
        description: str,
        components: Optional[Dict[str, str]] = None,
        configuration: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> SystemVersion:
        """
        Create a new system version.
        
        Args:
            version_number: Version number string
            description: Description of this version
            components: Component versions
            configuration: Configuration snapshot
            tags: Optional tags
        
        Returns:
            Created SystemVersion
        """
        version_id = str(uuid.uuid4())[:8]
        
        version = SystemVersion(
            version_id=version_id,
            version_number=version_number,
            created_at=time.time(),
            description=description,
            components=components or {},
            configuration_snapshot=configuration or await self._capture_configuration(),
            tags=tags or {}
        )
        
        self.versions[version_id] = version
        self.current_version = version_id
        
        # Auto-create rollback point
        if self.config.auto_create_points:
            await self.create_rollback_point(
                version,
                RollbackType.FULL_SYSTEM,
                f"Auto-created for version {version_number}"
            )
        
        self._save_state()
        
        logger.info(f"Created version {version_number} ({version_id})")
        return version
    
    async def _capture_configuration(self) -> Dict[str, Any]:
        """Capture current system configuration."""
        # In real implementation, would capture actual configuration
        return {
            "captured_at": time.time(),
            "settings": {},
            "environment": {}
        }
    
    async def create_rollback_point(
        self,
        version: SystemVersion,
        rollback_type: RollbackType,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> RollbackPoint:
        """
        Create a rollback point for a version.
        
        Args:
            version: System version to create point for
            rollback_type: Type of rollback this point supports
            description: Description of the rollback point
            metadata: Additional metadata
        
        Returns:
            Created RollbackPoint
        """
        point_id = str(uuid.uuid4())[:8]
        
        point = RollbackPoint(
            point_id=point_id,
            version=version,
            created_at=time.time(),
            rollback_type=rollback_type,
            metadata=metadata or {"description": description}
        )
        
        self.rollback_points[point_id] = point
        
        # Cleanup old points if needed
        await self._cleanup_old_points()
        
        self._save_state()
        
        logger.info(f"Created rollback point {point_id} for version {version.version_number}")
        return point
    
    async def _cleanup_old_points(self):
        """Remove old rollback points beyond the limit."""
        if len(self.rollback_points) <= self.config.max_rollback_points:
            return
        
        # Sort by creation time
        sorted_points = sorted(
            self.rollback_points.values(),
            key=lambda p: p.created_at
        )
        
        # Remove oldest points
        points_to_remove = len(sorted_points) - self.config.max_rollback_points
        for point in sorted_points[:points_to_remove]:
            del self.rollback_points[point.point_id]
            logger.debug(f"Removed old rollback point: {point.point_id}")
    
    async def rollback(
        self,
        target: str,
        rollback_type: Optional[RollbackType] = None,
        force: bool = False
    ) -> RollbackResult:
        """
        Perform a rollback operation.
        
        Args:
            target: Target version ID or rollback point ID
            rollback_type: Type of rollback (auto-detected if not specified)
            force: Force rollback even if verification fails
        
        Returns:
            RollbackResult with operation details
        """
        rollback_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        errors = []
        components_rolled_back = []
        
        # Find target
        target_version = None
        target_point = None
        
        if target in self.rollback_points:
            target_point = self.rollback_points[target]
            target_version = target_point.version
            rollback_type = rollback_type or target_point.rollback_type
        elif target in self.versions:
            target_version = self.versions[target]
            rollback_type = rollback_type or RollbackType.FULL_SYSTEM
        else:
            return RollbackResult(
                success=False,
                rollback_id=rollback_id,
                from_version=self.current_version or "unknown",
                to_version=target,
                duration_seconds=0,
                components_rolled_back=[],
                message=f"Target {target} not found",
                errors=["Target version or rollback point not found"]
            )
        
        # Check if rollback is allowed
        if target_point and not target_point.can_rollback and not force:
            return RollbackResult(
                success=False,
                rollback_id=rollback_id,
                from_version=self.current_version or "unknown",
                to_version=target_version.version_id,
                duration_seconds=0,
                components_rolled_back=[],
                message="Rollback not allowed for this point",
                errors=["Rollback point marked as non-rollbackable"]
            )
        
        from_version = self.current_version or "unknown"
        
        logger.info(f"Starting rollback {rollback_id}: {from_version} -> {target_version.version_id}")
        
        try:
            # Backup current state if configured
            if self.config.backup_before_rollback:
                await self._backup_current_state()
            
            # Get rollback handler
            handler = self.rollback_handlers.get(rollback_type)
            if not handler:
                raise ValueError(f"No handler for rollback type: {rollback_type}")
            
            # Execute rollback with timeout
            try:
                result = await asyncio.wait_for(
                    handler(target_version),
                    timeout=self.config.rollback_timeout_seconds
                )
                components_rolled_back = result.get("components", [])
            except asyncio.TimeoutError:
                raise TimeoutError("Rollback operation timed out")
            
            # Update current version
            self.current_version = target_version.version_id
            
            # Verify rollback if configured
            if self.config.verify_after_rollback:
                is_valid = await self._verify_rollback(target_version)
                if not is_valid and not force:
                    errors.append("Rollback verification failed")
            
            duration = time.time() - start_time
            success = len(errors) == 0
            
            # Record in history
            self.rollback_history.append({
                "rollback_id": rollback_id,
                "from_version": from_version,
                "to_version": target_version.version_id,
                "rollback_type": rollback_type.value,
                "success": success,
                "timestamp": time.time()
            })
            
            self._save_state()
            
            return RollbackResult(
                success=success,
                rollback_id=rollback_id,
                from_version=from_version,
                to_version=target_version.version_id,
                duration_seconds=duration,
                components_rolled_back=components_rolled_back,
                message="Rollback completed successfully" if success else "Rollback completed with warnings",
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Rollback {rollback_id} failed: {e}")
            
            return RollbackResult(
                success=False,
                rollback_id=rollback_id,
                from_version=from_version,
                to_version=target_version.version_id,
                duration_seconds=time.time() - start_time,
                components_rolled_back=components_rolled_back,
                message=f"Rollback failed: {str(e)}",
                errors=errors + [str(e)]
            )
    
    async def _backup_current_state(self):
        """Backup current state before rollback."""
        logger.info("Backing up current state before rollback")
        # In real implementation, would create actual backup
        await asyncio.sleep(0.1)
    
    async def _verify_rollback(self, target_version: SystemVersion) -> bool:
        """Verify rollback was successful."""
        logger.info(f"Verifying rollback to version {target_version.version_number}")
        # In real implementation, would verify actual system state
        await asyncio.sleep(0.1)
        return True
    
    # Default rollback handlers
    async def _rollback_configuration(self, version: SystemVersion) -> Dict[str, Any]:
        """Rollback configuration to a previous version."""
        logger.info(f"Rolling back configuration to version {version.version_number}")
        
        # Apply configuration snapshot
        config = version.configuration_snapshot
        
        # Simulate configuration rollback
        await asyncio.sleep(0.2)
        
        return {"components": ["configuration"]}
    
    async def _rollback_deployment(self, version: SystemVersion) -> Dict[str, Any]:
        """Rollback deployment to a previous version."""
        logger.info(f"Rolling back deployment to version {version.version_number}")
        
        components = []
        for component, comp_version in version.components.items():
            logger.info(f"Rolling back {component} to {comp_version}")
            await asyncio.sleep(0.1)
            components.append(component)
        
        return {"components": components}
    
    async def _rollback_database(self, version: SystemVersion) -> Dict[str, Any]:
        """Rollback database to a previous version."""
        logger.info(f"Rolling back database to version {version.version_number}")
        
        # Simulate database rollback
        await asyncio.sleep(0.3)
        
        return {"components": ["database"]}
    
    async def _rollback_service(self, version: SystemVersion) -> Dict[str, Any]:
        """Rollback a service to a previous version."""
        logger.info(f"Rolling back service to version {version.version_number}")
        
        # Simulate service rollback
        await asyncio.sleep(0.2)
        
        return {"components": ["service"]}
    
    async def _rollback_full_system(self, version: SystemVersion) -> Dict[str, Any]:
        """Rollback entire system to a previous version."""
        logger.info(f"Rolling back full system to version {version.version_number}")
        
        components = []
        
        # Rollback configuration
        await self._rollback_configuration(version)
        components.append("configuration")
        
        # Rollback deployment
        result = await self._rollback_deployment(version)
        components.extend(result.get("components", []))
        
        return {"components": components}
    
    def list_versions(self, limit: int = 20) -> List[SystemVersion]:
        """List available versions."""
        versions = list(self.versions.values())
        versions.sort(key=lambda v: v.created_at, reverse=True)
        return versions[:limit]
    
    def list_rollback_points(
        self,
        rollback_type: Optional[RollbackType] = None,
        limit: int = 20
    ) -> List[RollbackPoint]:
        """List available rollback points."""
        points = list(self.rollback_points.values())
        
        if rollback_type:
            points = [p for p in points if p.rollback_type == rollback_type]
        
        points.sort(key=lambda p: p.created_at, reverse=True)
        return points[:limit]
    
    def get_current_version(self) -> Optional[SystemVersion]:
        """Get current system version."""
        if self.current_version:
            return self.versions.get(self.current_version)
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rollback statistics."""
        history = list(self.rollback_history)
        successful = sum(1 for h in history if h.get("success", False))
        
        return {
            "total_versions": len(self.versions),
            "total_rollback_points": len(self.rollback_points),
            "current_version": self.current_version,
            "total_rollbacks": len(history),
            "successful_rollbacks": successful,
            "failed_rollbacks": len(history) - successful,
            "success_rate": successful / len(history) if history else 0,
            "by_type": {
                rt.value: len([p for p in self.rollback_points.values() if p.rollback_type == rt])
                for rt in RollbackType
            }
        }


# Global rollback controller instance
rollback_controller: Optional[RollbackController] = None


def initialize_rollback_controller(config: Optional[RollbackConfig] = None) -> RollbackController:
    """Initialize the global rollback controller."""
    global rollback_controller
    
    rollback_controller = RollbackController(config)
    return rollback_controller


def get_rollback_controller() -> Optional[RollbackController]:
    """Get the global rollback controller instance."""
    return rollback_controller
