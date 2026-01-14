"""
Annotation Plugin Manager for SuperInsight platform.

Manages third-party annotation tool plugins with registration, lifecycle,
priority management, and statistics tracking.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from uuid import uuid4
from collections import defaultdict
import statistics

from src.ai.annotation_plugin_interface import (
    AnnotationPluginInterface,
    AnnotationType,
    PluginInfo,
    PluginHealthStatus,
    PluginNotFoundError,
    PluginValidationError,
    PluginConnectionError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Plugin Configuration and Statistics Models
# ============================================================================

class PluginConfig:
    """Plugin configuration."""
    
    def __init__(
        self,
        name: str,
        connection_type: str,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        enabled: bool = True,
        priority: int = 0,
        type_mapping: Optional[Dict[str, str]] = None,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.connection_type = connection_type
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.enabled = enabled
        self.priority = priority
        self.type_mapping = type_mapping or {}
        self.extra_config = extra_config or {}


class PluginStatistics:
    """Plugin call statistics."""
    
    def __init__(self):
        self.total_calls: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.latencies: List[float] = []
        self.total_cost: float = 0.0
        self.last_call_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.success_count / self.total_calls
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return statistics.mean(self.latencies)
    
    def record_call(
        self,
        success: bool,
        latency_ms: float,
        cost: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        """Record a plugin call."""
        self.total_calls += 1
        self.latencies.append(latency_ms)
        self.total_cost += cost
        self.last_call_at = datetime.utcnow()
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            self.last_error = error
        
        # Keep only last 1000 latencies
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_calls": self.total_calls,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "total_cost": self.total_cost,
            "last_call_at": self.last_call_at.isoformat() if self.last_call_at else None,
            "last_error": self.last_error,
        }


# ============================================================================
# Plugin Registry Entry
# ============================================================================

class PluginRegistryEntry:
    """Registry entry for a plugin."""
    
    def __init__(
        self,
        plugin: AnnotationPluginInterface,
        config: PluginConfig,
    ):
        self.plugin = plugin
        self.config = config
        self.statistics = PluginStatistics()
        self.health_status: Optional[PluginHealthStatus] = None
        self.registered_at = datetime.utcnow()
        self.last_health_check: Optional[datetime] = None


# ============================================================================
# Plugin Manager
# ============================================================================

class AnnotationPluginManager:
    """
    Annotation Plugin Manager.
    
    Manages third-party annotation tool plugins with:
    - Plugin registration and unregistration
    - Enable/disable functionality
    - Priority-based plugin selection
    - Health monitoring
    - Call statistics tracking
    """
    
    def __init__(self):
        """Initialize the plugin manager."""
        self._plugins: Dict[str, PluginRegistryEntry] = {}
        self._plugin_classes: Dict[str, Type[AnnotationPluginInterface]] = {}
        self._lock = asyncio.Lock()
    
    # ========================================================================
    # Plugin Registration
    # ========================================================================
    
    async def register_plugin(
        self,
        plugin: AnnotationPluginInterface,
        config: PluginConfig,
    ) -> PluginInfo:
        """
        Register a plugin.
        
        Args:
            plugin: Plugin instance implementing AnnotationPluginInterface
            config: Plugin configuration
            
        Returns:
            PluginInfo for the registered plugin
            
        Raises:
            PluginValidationError: If plugin validation fails
        """
        async with self._lock:
            # Validate plugin implements required interface
            self._validate_plugin_interface(plugin, config.name)
            
            # Get plugin info
            info = plugin.get_info()
            
            # Validate config
            if not plugin.validate_config(config.extra_config):
                raise PluginValidationError(
                    config.name,
                    "Invalid plugin configuration"
                )
            
            # Create registry entry
            entry = PluginRegistryEntry(plugin, config)
            
            # Store in registry
            self._plugins[config.name] = entry
            
            logger.info(f"Registered plugin: {config.name} (v{info.version})")
            
            return info
    
    async def unregister_plugin(self, name: str) -> None:
        """
        Unregister a plugin.
        
        Args:
            name: Plugin name
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        async with self._lock:
            if name not in self._plugins:
                raise PluginNotFoundError(name)
            
            del self._plugins[name]
            logger.info(f"Unregistered plugin: {name}")
    
    def register_plugin_class(
        self,
        name: str,
        plugin_class: Type[AnnotationPluginInterface],
    ) -> None:
        """
        Register a plugin class for later instantiation.
        
        Args:
            name: Plugin class name
            plugin_class: Plugin class type
        """
        self._plugin_classes[name] = plugin_class
    
    # ========================================================================
    # Plugin Access
    # ========================================================================
    
    def get_plugin(self, name: str) -> Optional[AnnotationPluginInterface]:
        """
        Get a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found
        """
        entry = self._plugins.get(name)
        if entry and entry.config.enabled:
            return entry.plugin
        return None
    
    def get_plugin_entry(self, name: str) -> Optional[PluginRegistryEntry]:
        """
        Get plugin registry entry.
        
        Args:
            name: Plugin name
            
        Returns:
            PluginRegistryEntry or None
        """
        return self._plugins.get(name)
    
    async def list_plugins(self) -> List[PluginInfo]:
        """
        List all registered plugins.
        
        Returns:
            List of PluginInfo for all plugins
        """
        result = []
        for entry in self._plugins.values():
            info = entry.plugin.get_info()
            result.append(info)
        return result
    
    async def list_enabled_plugins(self) -> List[PluginInfo]:
        """
        List all enabled plugins.
        
        Returns:
            List of PluginInfo for enabled plugins
        """
        result = []
        for entry in self._plugins.values():
            if entry.config.enabled:
                info = entry.plugin.get_info()
                result.append(info)
        return result
    
    # ========================================================================
    # Plugin Lifecycle
    # ========================================================================
    
    async def enable_plugin(self, name: str) -> None:
        """
        Enable a plugin.
        
        Args:
            name: Plugin name
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        async with self._lock:
            if name not in self._plugins:
                raise PluginNotFoundError(name)
            
            self._plugins[name].config.enabled = True
            logger.info(f"Enabled plugin: {name}")
    
    async def disable_plugin(self, name: str) -> None:
        """
        Disable a plugin.
        
        Args:
            name: Plugin name
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        async with self._lock:
            if name not in self._plugins:
                raise PluginNotFoundError(name)
            
            self._plugins[name].config.enabled = False
            logger.info(f"Disabled plugin: {name}")
    
    def is_plugin_enabled(self, name: str) -> bool:
        """
        Check if plugin is enabled.
        
        Args:
            name: Plugin name
            
        Returns:
            True if plugin is enabled
        """
        entry = self._plugins.get(name)
        return entry is not None and entry.config.enabled
    
    # ========================================================================
    # Priority Management
    # ========================================================================
    
    async def set_priority(self, name: str, priority: int) -> None:
        """
        Set plugin priority.
        
        Args:
            name: Plugin name
            priority: Priority value (higher = more preferred)
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        async with self._lock:
            if name not in self._plugins:
                raise PluginNotFoundError(name)
            
            self._plugins[name].config.priority = priority
            logger.info(f"Set priority for {name}: {priority}")
    
    async def get_best_plugin(
        self,
        annotation_type: AnnotationType,
    ) -> Optional[AnnotationPluginInterface]:
        """
        Get the best plugin for an annotation type based on priority.
        
        Args:
            annotation_type: Type of annotation
            
        Returns:
            Best plugin or None if no suitable plugin found
        """
        candidates = []
        
        for entry in self._plugins.values():
            if not entry.config.enabled:
                continue
            
            supported_types = entry.plugin.get_supported_types()
            if annotation_type in supported_types:
                candidates.append(entry)
        
        if not candidates:
            return None
        
        # Sort by priority (descending) and return best
        candidates.sort(key=lambda e: e.config.priority, reverse=True)
        return candidates[0].plugin
    
    async def get_plugins_by_type(
        self,
        annotation_type: AnnotationType,
    ) -> List[AnnotationPluginInterface]:
        """
        Get all plugins supporting an annotation type.
        
        Args:
            annotation_type: Type of annotation
            
        Returns:
            List of plugins sorted by priority
        """
        candidates = []
        
        for entry in self._plugins.values():
            if not entry.config.enabled:
                continue
            
            supported_types = entry.plugin.get_supported_types()
            if annotation_type in supported_types:
                candidates.append(entry)
        
        # Sort by priority (descending)
        candidates.sort(key=lambda e: e.config.priority, reverse=True)
        return [e.plugin for e in candidates]
    
    # ========================================================================
    # Health Monitoring
    # ========================================================================
    
    async def health_check(self, name: str) -> PluginHealthStatus:
        """
        Check health of a specific plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            PluginHealthStatus
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)
        
        entry = self._plugins[name]
        
        try:
            start_time = time.time()
            status = await entry.plugin.health_check()
            latency = (time.time() - start_time) * 1000
            
            status.latency_ms = latency
            entry.health_status = status
            entry.last_health_check = datetime.utcnow()
            
            return status
            
        except Exception as e:
            status = PluginHealthStatus(
                healthy=False,
                message=str(e),
                last_check=datetime.utcnow(),
            )
            entry.health_status = status
            entry.last_health_check = datetime.utcnow()
            return status
    
    async def health_check_all(self) -> Dict[str, PluginHealthStatus]:
        """
        Check health of all plugins.
        
        Returns:
            Dictionary mapping plugin names to health status
        """
        results = {}
        
        for name in self._plugins:
            try:
                status = await self.health_check(name)
                results[name] = status
            except Exception as e:
                results[name] = PluginHealthStatus(
                    healthy=False,
                    message=str(e),
                )
        
        return results
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    async def get_statistics(self, name: str) -> Dict[str, Any]:
        """
        Get plugin call statistics.
        
        Args:
            name: Plugin name
            
        Returns:
            Statistics dictionary
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)
        
        entry = self._plugins[name]
        return entry.statistics.to_dict()
    
    async def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all plugins.
        
        Returns:
            Dictionary mapping plugin names to statistics
        """
        return {
            name: entry.statistics.to_dict()
            for name, entry in self._plugins.items()
        }
    
    def record_call(
        self,
        name: str,
        success: bool,
        latency_ms: float,
        cost: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a plugin call for statistics.
        
        Args:
            name: Plugin name
            success: Whether call succeeded
            latency_ms: Call latency in milliseconds
            cost: Call cost
            error: Error message if failed
        """
        entry = self._plugins.get(name)
        if entry:
            entry.statistics.record_call(success, latency_ms, cost, error)
    
    # ========================================================================
    # Validation
    # ========================================================================
    
    def _validate_plugin_interface(
        self,
        plugin: AnnotationPluginInterface,
        name: str,
    ) -> None:
        """
        Validate that plugin implements required interface methods.
        
        Args:
            plugin: Plugin to validate
            name: Plugin name for error messages
            
        Raises:
            PluginValidationError: If validation fails
        """
        required_methods = [
            "get_info",
            "get_supported_types",
            "to_native_format",
            "annotate",
            "to_label_studio_format",
            "health_check",
        ]
        
        for method_name in required_methods:
            if not hasattr(plugin, method_name):
                raise PluginValidationError(
                    name,
                    f"Missing required method: {method_name}"
                )
            
            method = getattr(plugin, method_name)
            if not callable(method):
                raise PluginValidationError(
                    name,
                    f"Method is not callable: {method_name}"
                )
        
        # Validate get_info returns PluginInfo
        try:
            info = plugin.get_info()
            if not isinstance(info, PluginInfo):
                raise PluginValidationError(
                    name,
                    "get_info() must return PluginInfo"
                )
        except Exception as e:
            raise PluginValidationError(
                name,
                f"get_info() failed: {e}"
            )
        
        # Validate get_supported_types returns list
        try:
            types = plugin.get_supported_types()
            if not isinstance(types, list):
                raise PluginValidationError(
                    name,
                    "get_supported_types() must return a list"
                )
        except Exception as e:
            raise PluginValidationError(
                name,
                f"get_supported_types() failed: {e}"
            )


# ============================================================================
# Singleton Instance
# ============================================================================

_manager_instance: Optional[AnnotationPluginManager] = None


def get_plugin_manager() -> AnnotationPluginManager:
    """
    Get or create the plugin manager instance.
    
    Returns:
        AnnotationPluginManager instance
    """
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = AnnotationPluginManager()
    
    return _manager_instance
