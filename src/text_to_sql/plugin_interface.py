"""
Plugin Interface for Third-Party Text-to-SQL Tools.

Defines the abstract interface that all third-party plugins must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from .schemas import (
    SQLGenerationResult,
    PluginInfo,
    PluginConfig,
    ConnectionType,
)
from .schema_analyzer import DatabaseSchema

logger = logging.getLogger(__name__)


class PluginInterface(ABC):
    """
    Abstract interface for third-party Text-to-SQL plugins.
    
    All third-party tool adapters must implement this interface
    to be compatible with the plugin system.
    """
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """
        Get plugin information.
        
        Returns:
            PluginInfo with plugin metadata
        """
        pass
    
    @abstractmethod
    def to_native_format(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None
    ) -> Dict[str, Any]:
        """
        Convert query and schema to tool-specific format.
        
        Args:
            query: Natural language query
            schema: Database schema
            
        Returns:
            Dictionary in tool's native request format
        """
        pass
    
    @abstractmethod
    async def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the third-party tool.
        
        Args:
            request: Request in tool's native format
            
        Returns:
            Response in tool's native format
        """
        pass
    
    @abstractmethod
    def from_native_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        """
        Convert tool's response to unified format.
        
        Args:
            response: Response in tool's native format
            
        Returns:
            SQLGenerationResult in unified format
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the plugin is healthy and available.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def validate_config(self, config: PluginConfig) -> List[str]:
        """
        Validate plugin configuration.
        
        Args:
            config: Plugin configuration
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not config.name:
            errors.append("Plugin name is required")
        
        if config.connection_type in [ConnectionType.REST_API, ConnectionType.GRPC]:
            if not config.endpoint:
                errors.append("Endpoint is required for REST API and gRPC connections")
        
        return errors
    
    def get_supported_db_types(self) -> List[str]:
        """
        Get list of supported database types.
        
        Returns:
            List of supported database type strings
        """
        info = self.get_info()
        return info.supported_db_types
    
    def supports_db_type(self, db_type: str) -> bool:
        """
        Check if plugin supports a database type.
        
        Args:
            db_type: Database type to check
            
        Returns:
            True if supported, False otherwise
        """
        supported = self.get_supported_db_types()
        if not supported:
            return True  # Empty list means all types supported
        return db_type.lower() in [t.lower() for t in supported]


class BasePlugin(PluginInterface):
    """
    Base implementation of PluginInterface with common functionality.
    
    Provides default implementations for common methods.
    Subclasses should override abstract methods.
    """
    
    def __init__(self, config: PluginConfig):
        """
        Initialize base plugin.
        
        Args:
            config: Plugin configuration
        """
        self.config = config
        self._is_initialized = False
        self._last_health_check: Optional[datetime] = None
        self._is_healthy = True
        
        # Statistics
        self._total_calls = 0
        self._successful_calls = 0
        self._failed_calls = 0
        self._total_response_time_ms = 0.0
    
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name=self.config.name,
            version="1.0.0",
            description=f"Plugin for {self.config.name}",
            connection_type=self.config.connection_type,
            supported_db_types=[],
            config_schema={},
            is_healthy=self._is_healthy,
            last_health_check=self._last_health_check,
        )
    
    def to_native_format(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None
    ) -> Dict[str, Any]:
        """Convert to native format - must be overridden."""
        return {
            "query": query,
            "schema": self._schema_to_dict(schema) if schema else None,
        }
    
    async def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call the tool - must be overridden."""
        raise NotImplementedError("Subclass must implement call()")
    
    def from_native_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        """Convert from native format - must be overridden."""
        return SQLGenerationResult(
            sql=response.get("sql", ""),
            method_used=f"third_party:{self.config.name}",
            confidence=response.get("confidence", 0.8),
            execution_time_ms=response.get("execution_time_ms", 0.0),
            metadata={"plugin": self.config.name},
        )
    
    async def health_check(self) -> bool:
        """Check plugin health."""
        self._last_health_check = datetime.utcnow()
        # Default implementation - subclasses should override
        self._is_healthy = True
        return self._is_healthy
    
    def _schema_to_dict(self, schema: DatabaseSchema) -> Dict[str, Any]:
        """Convert schema to dictionary for serialization."""
        return {
            "tables": schema.tables,
            "relationships": schema.relationships,
            "db_type": schema.db_type,
        }
    
    def record_call(self, success: bool, response_time_ms: float) -> None:
        """Record a call for statistics."""
        self._total_calls += 1
        self._total_response_time_ms += response_time_ms
        
        if success:
            self._successful_calls += 1
        else:
            self._failed_calls += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get plugin statistics."""
        return {
            "total_calls": self._total_calls,
            "successful_calls": self._successful_calls,
            "failed_calls": self._failed_calls,
            "success_rate": self._successful_calls / max(1, self._total_calls),
            "average_response_time_ms": self._total_response_time_ms / max(1, self._total_calls),
        }


class PluginNotFoundError(Exception):
    """Exception raised when a plugin is not found."""
    
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin not found: {plugin_name}")


class PluginValidationError(Exception):
    """Exception raised when plugin validation fails."""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Plugin validation failed: {', '.join(errors)}")


class PluginCallError(Exception):
    """Exception raised when a plugin call fails."""
    
    def __init__(self, plugin_name: str, error: str):
        self.plugin_name = plugin_name
        self.error = error
        super().__init__(f"Plugin {plugin_name} call failed: {error}")
