"""
REST API adapter for third-party annotation tools.

Provides a base implementation for tools that expose REST APIs.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
import httpx

from src.ai.annotation_schemas import (
    AnnotationType,
    AnnotationTask,
    PreAnnotationResult,
    PluginInfo,
    ConnectionType,
)
from .base_adapter import BaseAnnotationAdapter


class RESTAnnotationAdapter(BaseAnnotationAdapter):
    """
    REST API adapter for annotation tools.
    
    Provides common functionality for tools that expose REST APIs.
    Subclasses should override format conversion methods.
    """
    
    def __init__(
        self,
        name: str,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Initialize REST adapter.
        
        Args:
            name: Adapter name
            endpoint: Base API endpoint URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
            headers: Additional HTTP headers
            **kwargs: Additional configuration
        """
        super().__init__(name, endpoint, api_key, timeout, **kwargs)
        self.headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None
        
        # Set up authentication header if API key provided
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    async def initialize(self) -> None:
        """Initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.endpoint,
                timeout=self.timeout,
                headers=self.headers,
            )
        await super().initialize()
    
    async def cleanup(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        await super().cleanup()
    
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name=self.name,
            version=self.extra_config.get("version", "1.0.0"),
            description=self.extra_config.get("description", f"REST adapter for {self.name}"),
            connection_type=ConnectionType.REST_API,
            supported_annotation_types=self.get_supported_types(),
            config_schema={
                "endpoint": {"type": "string", "required": True},
                "api_key": {"type": "string", "required": False},
                "timeout": {"type": "integer", "default": 30},
            },
            enabled=True,
            priority=self.extra_config.get("priority", 0),
        )
    
    def get_supported_types(self) -> List[AnnotationType]:
        """Get supported annotation types."""
        # Default: support all types, subclasses can override
        return list(AnnotationType)
    
    def to_native_format(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType
    ) -> Dict[str, Any]:
        """
        Convert tasks to REST API format.
        
        Default implementation - subclasses should override for specific tools.
        """
        return {
            "tasks": [
                {
                    "id": task.id,
                    "data": task.data,
                    "metadata": task.metadata,
                }
                for task in tasks
            ],
            "annotation_type": self.map_annotation_type(annotation_type),
        }
    
    async def annotate(self, native_tasks: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute annotation via REST API.
        
        Args:
            native_tasks: Tasks in API format
            
        Returns:
            API response
        """
        if not self._client:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            response = await self._client.post(
                "/annotate",
                json=native_tasks,
            )
            response.raise_for_status()
            
            result = response.json()
            result["_latency_ms"] = (time.time() - start_time) * 1000
            return result
            
        except httpx.HTTPError as e:
            return {
                "error": str(e),
                "success": False,
                "_latency_ms": (time.time() - start_time) * 1000,
            }
    
    def to_label_studio_format(
        self,
        native_results: Dict[str, Any]
    ) -> List[PreAnnotationResult]:
        """
        Convert API results to Label Studio format.
        
        Default implementation - subclasses should override for specific tools.
        """
        results = []
        latency = native_results.get("_latency_ms", 0)
        
        if native_results.get("error"):
            # Return error result
            return [
                PreAnnotationResult(
                    task_id="unknown",
                    annotation={},
                    confidence=0.0,
                    needs_review=True,
                    method_used=self.name,
                    processing_time_ms=latency,
                    error=native_results.get("error"),
                )
            ]
        
        for item in native_results.get("results", []):
            results.append(
                PreAnnotationResult(
                    task_id=item.get("task_id", "unknown"),
                    annotation=item.get("annotation", {}),
                    confidence=item.get("confidence", 0.0),
                    needs_review=item.get("confidence", 0.0) < 0.7,
                    method_used=self.name,
                    processing_time_ms=latency / len(native_results.get("results", [1])),
                )
            )
        
        return results
    
    async def health_check(self) -> bool:
        """Check if the REST API is available."""
        if not self._client:
            await self.initialize()
        
        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    def validate_config(self) -> bool:
        """Validate REST adapter configuration."""
        if not self.endpoint:
            return False
        if not self.endpoint.startswith(("http://", "https://")):
            return False
        return True
