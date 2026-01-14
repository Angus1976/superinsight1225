"""
Base adapter for third-party annotation tools.

Defines the abstract interface that all annotation tool adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.ai.annotation_schemas import (
    AnnotationType,
    AnnotationTask,
    PreAnnotationResult,
    PluginInfo,
    ConnectionType,
)


class BaseAnnotationAdapter(ABC):
    """
    Abstract base class for annotation tool adapters.
    
    All third-party annotation tool adapters must inherit from this class
    and implement the required methods.
    """
    
    def __init__(
        self,
        name: str,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        **kwargs
    ):
        """
        Initialize the adapter.
        
        Args:
            name: Adapter/plugin name
            endpoint: API endpoint URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
            **kwargs: Additional configuration
        """
        self.name = name
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.extra_config = kwargs
        self._initialized = False
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """
        Get plugin information.
        
        Returns:
            PluginInfo with adapter details
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[AnnotationType]:
        """
        Get supported annotation types.
        
        Returns:
            List of supported AnnotationType values
        """
        pass
    
    @abstractmethod
    def to_native_format(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType
    ) -> Dict[str, Any]:
        """
        Convert tasks to tool-specific format.
        
        Args:
            tasks: List of annotation tasks
            annotation_type: Type of annotation
            
        Returns:
            Dictionary in tool-specific format
        """
        pass
    
    @abstractmethod
    async def annotate(self, native_tasks: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute annotation using the tool.
        
        Args:
            native_tasks: Tasks in tool-specific format
            
        Returns:
            Results in tool-specific format
        """
        pass
    
    @abstractmethod
    def to_label_studio_format(
        self,
        native_results: Dict[str, Any]
    ) -> List[PreAnnotationResult]:
        """
        Convert results to Label Studio compatible format.
        
        Args:
            native_results: Results in tool-specific format
            
        Returns:
            List of PreAnnotationResult objects
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the tool is available and healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    async def initialize(self) -> None:
        """
        Initialize the adapter (optional override).
        
        Called before first use to set up connections, validate config, etc.
        """
        self._initialized = True
    
    async def cleanup(self) -> None:
        """
        Clean up resources (optional override).
        
        Called when adapter is being unregistered or shutdown.
        """
        self._initialized = False
    
    def validate_config(self) -> bool:
        """
        Validate adapter configuration.
        
        Returns:
            True if configuration is valid
        """
        # Base validation - subclasses can override
        return True
    
    def get_type_mapping(self) -> Dict[str, str]:
        """
        Get mapping from internal types to tool-specific types.
        
        Returns:
            Dictionary mapping internal type names to tool type names
        """
        return self.extra_config.get("type_mapping", {})
    
    def map_annotation_type(self, annotation_type: AnnotationType) -> str:
        """
        Map internal annotation type to tool-specific type.
        
        Args:
            annotation_type: Internal annotation type
            
        Returns:
            Tool-specific type name
        """
        mapping = self.get_type_mapping()
        return mapping.get(annotation_type.value, annotation_type.value)
