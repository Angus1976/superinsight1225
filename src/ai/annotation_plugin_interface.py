"""
Annotation Plugin Interface for SuperInsight platform.

Defines the abstract interface that all third-party annotation tool plugins must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"
    RELATION_EXTRACTION = "relation_extraction"
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    IMAGE_CLASSIFICATION = "image_classification"
    OBJECT_DETECTION = "object_detection"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"


class ConnectionType(str, Enum):
    """Plugin connection types."""
    REST_API = "rest_api"
    GRPC = "grpc"
    WEBHOOK = "webhook"
    SDK = "sdk"


class PluginInfo(BaseModel):
    """Plugin information."""
    name: str = Field(..., description="Plugin name")
    version: str = Field(default="1.0.0", description="Plugin version")
    description: str = Field(default="", description="Plugin description")
    connection_type: ConnectionType = Field(..., description="Connection type")
    supported_annotation_types: List[AnnotationType] = Field(
        default_factory=list, description="Supported annotation types"
    )
    config_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration schema"
    )
    author: str = Field(default="", description="Plugin author")
    homepage: str = Field(default="", description="Plugin homepage URL")


class AnnotationTask(BaseModel):
    """Annotation task to be processed."""
    id: str = Field(..., description="Task ID")
    data: Dict[str, Any] = Field(..., description="Task data")
    annotation_type: AnnotationType = Field(..., description="Annotation type")
    config: Dict[str, Any] = Field(default_factory=dict, description="Task config")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")


class AnnotationResult(BaseModel):
    """Annotation result from plugin."""
    task_id: str = Field(..., description="Task ID")
    annotation_data: Dict[str, Any] = Field(..., description="Annotation data")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    method_used: str = Field(default="", description="Method used for annotation")
    processing_time_ms: float = Field(default=0.0, description="Processing time in ms")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Result metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class PluginHealthStatus(BaseModel):
    """Plugin health status."""
    healthy: bool = Field(..., description="Is plugin healthy")
    latency_ms: float = Field(default=0.0, description="Health check latency")
    message: str = Field(default="", description="Status message")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last check time")


class AnnotationPluginInterface(ABC):
    """
    Abstract interface for annotation tool plugins.
    
    All third-party annotation tool plugins must implement this interface
    to be compatible with the SuperInsight platform.
    """
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """
        Get plugin information.
        
        Returns:
            PluginInfo with plugin details
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
        annotation_type: AnnotationType,
    ) -> Dict[str, Any]:
        """
        Convert tasks to tool-specific native format.
        
        Args:
            tasks: List of annotation tasks
            annotation_type: Type of annotation
            
        Returns:
            Dictionary in tool's native format
        """
        pass
    
    @abstractmethod
    async def annotate(self, native_tasks: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute annotation using the tool.
        
        Args:
            native_tasks: Tasks in tool's native format
            
        Returns:
            Results in tool's native format
        """
        pass
    
    @abstractmethod
    def to_label_studio_format(
        self,
        native_results: Dict[str, Any],
    ) -> List[AnnotationResult]:
        """
        Convert results to Label Studio compatible format.
        
        Args:
            native_results: Results in tool's native format
            
        Returns:
            List of AnnotationResult in Label Studio format
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> PluginHealthStatus:
        """
        Check plugin health status.
        
        Returns:
            PluginHealthStatus with health information
        """
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if configuration is valid
        """
        return True
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default plugin configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {}


class PluginError(Exception):
    """Base exception for plugin errors."""
    pass


class PluginNotFoundError(PluginError):
    """Plugin not found error."""
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin not found: {plugin_name}")


class PluginConnectionError(PluginError):
    """Plugin connection error."""
    def __init__(self, plugin_name: str, message: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin connection error ({plugin_name}): {message}")


class PluginAnnotationError(PluginError):
    """Plugin annotation error."""
    def __init__(self, plugin_name: str, message: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin annotation error ({plugin_name}): {message}")


class PluginValidationError(PluginError):
    """Plugin validation error."""
    def __init__(self, plugin_name: str, message: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin validation error ({plugin_name}): {message}")
