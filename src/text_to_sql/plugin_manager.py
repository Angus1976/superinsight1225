"""
Plugin Manager for Third-Party Text-to-SQL Tools.

Manages registration, configuration, and lifecycle of third-party plugins.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Type
from uuid import uuid4

from .schemas import (
    PluginInfo,
    PluginConfig,
    PluginHealthStatus,
    PluginStatistics,
    ConnectionType,
)
from .plugin_interface import (
    PluginInterface,
    BasePlugin,
    PluginNotFoundError,
    PluginValidationError,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manager for third-party Text-to-SQL plugins.
    
    Features:
    - Plugin registration and unregistration
    - Configuration management
    - Health monitoring
    - Interface validation
    - Statistics tracking
    """
    
    def __init__(self):
        """Initialize Plugin Manager."""
        self._plugins: Dict[str, PluginInterface] = {}
        self._configs: Dict[str, PluginConfig] = {}
        self._plugin_classes: Dict[str, Type[PluginInterface]] = {}
        
        # Health check settings
        self._health_check_interval = 60  # seconds
        self._last_health_check: Dict[str, datetime] = {}
    
    async def register_plugin(
        self,
        config: PluginConfig,
        plugin_class: Optional[Type[PluginInterface]] = None
    ) -> PluginInfo:
        """
        Register a new plugin.
        
        Args:
            config: Plugin configuration
            plugin_class: Optional plugin class (for custom plugins)
            
        Returns:
            PluginInfo for the registered plugin
            
        Raises:
            PluginValidationError: If plugin validation fails
        """
        # Validate configuration
        errors = self._validate_config(config)
        if errors:
            raise PluginValidationError(errors)
        
        # Create plugin instance
        if plugin_class:
            plugin = plugin_class(config)
        else:
            plugin = self._create_plugin_from_config(config)
        
        # Validate interface
        interface_errors = self._validate_interface(plugin)
        if interface_errors:
            raise PluginValidationError(interface_errors)
        
        # Store plugin
        self._plugins[config.name] = plugin
        self._configs[config.name] = config
        
        if plugin_class:
            self._plugin_classes[config.name] = plugin_class
        
        logger.info(f"Registered plugin: {config.name}")
        
        return plugin.get_info()
    
    async def unregister_plugin(self, name: str) -> None:
        """
        Unregister a plugin.
        
        Args:
            name: Plugin name
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)
        
        del self._plugins[name]
        del self._configs[name]
        self._plugin_classes.pop(name, None)
        self._last_health_check.pop(name, None)
        
        logger.info(f"Unregistered plugin: {name}")
    
    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """
        Get a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)
    
    async def list_plugins(self) -> List[PluginInfo]:
        """
        List all registered plugins.
        
        Returns:
            List of PluginInfo for all plugins
        """
        return [plugin.get_info() for plugin in self._plugins.values()]
    
    async def update_plugin_config(
        self,
        name: str,
        config: PluginConfig
    ) -> PluginInfo:
        """
        Update plugin configuration.
        
        Args:
            name: Plugin name
            config: New configuration
            
        Returns:
            Updated PluginInfo
            
        Raises:
            PluginNotFoundError: If plugin not found
            PluginValidationError: If validation fails
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)
        
        # Validate new config
        errors = self._validate_config(config)
        if errors:
            raise PluginValidationError(errors)
        
        # Re-create plugin with new config
        plugin_class = self._plugin_classes.get(name)
        if plugin_class:
            plugin = plugin_class(config)
        else:
            plugin = self._create_plugin_from_config(config)
        
        # Update stored plugin
        self._plugins[name] = plugin
        self._configs[name] = config
        
        logger.info(f"Updated plugin config: {name}")
        
        return plugin.get_info()
    
    async def enable_plugin(self, name: str) -> None:
        """
        Enable a plugin.
        
        Args:
            name: Plugin name
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._configs:
            raise PluginNotFoundError(name)
        
        self._configs[name].enabled = True
        logger.info(f"Enabled plugin: {name}")
    
    async def disable_plugin(self, name: str) -> None:
        """
        Disable a plugin.
        
        Args:
            name: Plugin name
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._configs:
            raise PluginNotFoundError(name)
        
        self._configs[name].enabled = False
        logger.info(f"Disabled plugin: {name}")
    
    def is_plugin_enabled(self, name: str) -> bool:
        """
        Check if a plugin is enabled.
        
        Args:
            name: Plugin name
            
        Returns:
            True if enabled, False otherwise
        """
        config = self._configs.get(name)
        return config.enabled if config else False
    
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
        plugin = self._plugins.get(name)
        if not plugin:
            raise PluginNotFoundError(name)
        
        import time
        start_time = time.time()
        
        try:
            is_healthy = await plugin.health_check()
            response_time = (time.time() - start_time) * 1000
            
            self._last_health_check[name] = datetime.utcnow()
            
            return PluginHealthStatus(
                name=name,
                is_healthy=is_healthy,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return PluginHealthStatus(
                name=name,
                is_healthy=False,
                response_time_ms=response_time,
                error=str(e),
                last_check=datetime.utcnow(),
            )
    
    async def health_check_all(self) -> Dict[str, PluginHealthStatus]:
        """
        Check health of all plugins.
        
        Returns:
            Dictionary mapping plugin names to health status
        """
        results = {}
        
        for name in self._plugins:
            results[name] = await self.health_check(name)
        
        return results
    
    def get_plugin_statistics(self, name: str) -> Optional[PluginStatistics]:
        """
        Get statistics for a plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            PluginStatistics or None if not found
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return None
        
        if hasattr(plugin, 'get_statistics'):
            stats = plugin.get_statistics()
            return PluginStatistics(
                name=name,
                total_calls=stats.get("total_calls", 0),
                successful_calls=stats.get("successful_calls", 0),
                failed_calls=stats.get("failed_calls", 0),
                average_response_time_ms=stats.get("average_response_time_ms", 0.0),
            )
        
        return PluginStatistics(name=name)
    
    def _validate_config(self, config: PluginConfig) -> List[str]:
        """Validate plugin configuration."""
        errors = []
        
        if not config.name:
            errors.append("Plugin name is required")
        
        if not config.name.replace("_", "").replace("-", "").isalnum():
            errors.append("Plugin name must be alphanumeric (with underscores/hyphens)")
        
        if config.connection_type in [ConnectionType.REST_API, ConnectionType.GRPC]:
            if not config.endpoint:
                errors.append("Endpoint is required for REST API and gRPC connections")
        
        if config.timeout < 1 or config.timeout > 300:
            errors.append("Timeout must be between 1 and 300 seconds")
        
        return errors
    
    def _validate_interface(self, plugin: PluginInterface) -> List[str]:
        """Validate that plugin implements required interface methods."""
        errors = []
        
        required_methods = [
            "get_info",
            "to_native_format",
            "call",
            "from_native_format",
            "health_check",
        ]
        
        for method in required_methods:
            if not hasattr(plugin, method):
                errors.append(f"Plugin missing required method: {method}")
            elif not callable(getattr(plugin, method)):
                errors.append(f"Plugin method is not callable: {method}")
        
        # Validate get_info returns correct type
        try:
            info = plugin.get_info()
            if not isinstance(info, PluginInfo):
                errors.append("get_info() must return PluginInfo")
        except Exception as e:
            errors.append(f"get_info() raised exception: {e}")
        
        return errors
    
    def _create_plugin_from_config(self, config: PluginConfig) -> PluginInterface:
        """Create a plugin instance from configuration."""
        # Import adapters dynamically
        if config.connection_type == ConnectionType.REST_API:
            from .adapters.rest_adapter import RESTAPIPlugin
            return RESTAPIPlugin(config)
        elif config.connection_type == ConnectionType.GRPC:
            from .adapters.grpc_adapter import GRPCPlugin
            return GRPCPlugin(config)
        else:
            # Default to base plugin
            return BasePlugin(config)


# Global instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get or create global PluginManager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
