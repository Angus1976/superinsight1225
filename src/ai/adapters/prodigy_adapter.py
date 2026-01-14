"""
Prodigy Annotation Tool Adapter.

Adapter for integrating with Explosion AI's Prodigy annotation tool.
https://prodi.gy/
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from src.ai.annotation_plugin_interface import (
    AnnotationPluginInterface,
    AnnotationType,
    ConnectionType,
    PluginInfo,
    AnnotationTask,
    AnnotationResult,
    PluginHealthStatus,
)

logger = logging.getLogger(__name__)


class ProdigyAdapter(AnnotationPluginInterface):
    """
    Prodigy annotation tool adapter.
    
    Integrates with Prodigy's REST API for text annotation tasks.
    Supports text classification, NER, and sentiment analysis.
    """
    
    def __init__(
        self,
        endpoint: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        timeout: int = 30,
        **kwargs
    ):
        """
        Initialize Prodigy adapter.
        
        Args:
            endpoint: Prodigy API endpoint
            api_key: Optional API key
            timeout: Request timeout in seconds
            **kwargs: Additional configuration
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.extra_config = kwargs
        self._client: Optional[httpx.AsyncClient] = None
        
        # Type mapping from internal to Prodigy types
        self._type_mapping = {
            AnnotationType.TEXT_CLASSIFICATION: "textcat",
            AnnotationType.NER: "ner",
            AnnotationType.SENTIMENT: "textcat",
        }
    
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name="prodigy",
            version="1.0.0",
            description="Prodigy annotation tool adapter by Explosion AI",
            connection_type=ConnectionType.REST_API,
            supported_annotation_types=self.get_supported_types(),
            config_schema={
                "endpoint": {
                    "type": "string",
                    "required": True,
                    "description": "Prodigy API endpoint URL",
                },
                "api_key": {
                    "type": "string",
                    "required": False,
                    "description": "API key for authentication",
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "Request timeout in seconds",
                },
            },
            author="SuperInsight",
            homepage="https://prodi.gy/",
        )
    
    def get_supported_types(self) -> List[AnnotationType]:
        """Get supported annotation types."""
        return [
            AnnotationType.TEXT_CLASSIFICATION,
            AnnotationType.NER,
            AnnotationType.SENTIMENT,
        ]
    
    def to_native_format(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
    ) -> Dict[str, Any]:
        """
        Convert tasks to Prodigy format.
        
        Prodigy uses JSONL format with specific fields.
        """
        prodigy_type = self._type_mapping.get(annotation_type, "textcat")
        
        prodigy_tasks = []
        for task in tasks:
            prodigy_task = {
                "_task_id": task.id,
                "text": task.data.get("text", ""),
                "meta": {
                    "source": "superinsight",
                    "annotation_type": annotation_type.value,
                    **task.metadata,
                },
            }
            
            # Add type-specific fields
            if annotation_type == AnnotationType.NER:
                # For NER, include any existing spans
                if "spans" in task.data:
                    prodigy_task["spans"] = task.data["spans"]
            
            prodigy_tasks.append(prodigy_task)
        
        return {
            "tasks": prodigy_tasks,
            "recipe": prodigy_type,
            "config": {
                "batch_size": len(tasks),
                "auto_accept": True,
            },
        }
    
    async def annotate(self, native_tasks: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute annotation using Prodigy API.
        
        Args:
            native_tasks: Tasks in Prodigy format
            
        Returns:
            Prodigy API response
        """
        if not self._client:
            await self._initialize_client()
        
        start_time = time.time()
        
        try:
            # Call Prodigy batch annotation endpoint
            response = await self._client.post(
                "/api/batch",
                json=native_tasks,
            )
            response.raise_for_status()
            
            result = response.json()
            result["_latency_ms"] = (time.time() - start_time) * 1000
            result["_success"] = True
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Prodigy API error: {e}")
            return {
                "_success": False,
                "_error": str(e),
                "_latency_ms": (time.time() - start_time) * 1000,
                "annotations": [],
            }
    
    def to_label_studio_format(
        self,
        native_results: Dict[str, Any],
    ) -> List[AnnotationResult]:
        """
        Convert Prodigy results to Label Studio format.
        
        Args:
            native_results: Prodigy API response
            
        Returns:
            List of AnnotationResult
        """
        results = []
        latency = native_results.get("_latency_ms", 0)
        
        if not native_results.get("_success", False):
            # Return error results
            return []
        
        annotations = native_results.get("annotations", [])
        
        for ann in annotations:
            task_id = ann.get("_task_id", "unknown")
            
            # Convert Prodigy annotation to internal format
            annotation_data = {}
            confidence = 0.0
            
            # Handle text classification
            if "label" in ann:
                annotation_data["label"] = ann["label"]
                confidence = ann.get("score", 0.8)
            
            # Handle NER spans
            if "spans" in ann:
                entities = []
                for span in ann["spans"]:
                    entities.append({
                        "text": span.get("text", ""),
                        "label": span.get("label", ""),
                        "start": span.get("start", 0),
                        "end": span.get("end", 0),
                    })
                annotation_data["entities"] = entities
                confidence = ann.get("score", 0.8)
            
            # Handle accept/reject
            if "answer" in ann:
                annotation_data["answer"] = ann["answer"]
                if ann["answer"] == "accept":
                    confidence = max(confidence, 0.9)
                elif ann["answer"] == "reject":
                    confidence = 0.1
            
            results.append(AnnotationResult(
                task_id=task_id,
                annotation_data=annotation_data,
                confidence=confidence,
                method_used="prodigy",
                processing_time_ms=latency / max(len(annotations), 1),
                metadata={
                    "prodigy_meta": ann.get("meta", {}),
                },
            ))
        
        return results
    
    async def health_check(self) -> PluginHealthStatus:
        """Check Prodigy API health."""
        if not self._client:
            await self._initialize_client()
        
        start_time = time.time()
        
        try:
            response = await self._client.get("/api/status")
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return PluginHealthStatus(
                    healthy=True,
                    latency_ms=latency,
                    message="Prodigy API is healthy",
                )
            else:
                return PluginHealthStatus(
                    healthy=False,
                    latency_ms=latency,
                    message=f"Prodigy API returned status {response.status_code}",
                )
                
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return PluginHealthStatus(
                healthy=False,
                latency_ms=latency,
                message=f"Prodigy API error: {e}",
            )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration."""
        endpoint = config.get("endpoint", self.endpoint)
        if not endpoint:
            return False
        if not endpoint.startswith(("http://", "https://")):
            return False
        return True
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "endpoint": "http://localhost:8080",
            "timeout": 30,
        }
    
    async def _initialize_client(self) -> None:
        """Initialize HTTP client."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self._client = httpx.AsyncClient(
            base_url=self.endpoint,
            timeout=self.timeout,
            headers=headers,
        )
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Factory function
def create_prodigy_adapter(
    endpoint: str = "http://localhost:8080",
    api_key: Optional[str] = None,
    **kwargs
) -> ProdigyAdapter:
    """
    Create a Prodigy adapter instance.
    
    Args:
        endpoint: Prodigy API endpoint
        api_key: Optional API key
        **kwargs: Additional configuration
        
    Returns:
        ProdigyAdapter instance
    """
    return ProdigyAdapter(endpoint=endpoint, api_key=api_key, **kwargs)
