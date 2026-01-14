"""
Third Party Annotation Adapter for SuperInsight platform.

Provides unified interface for calling third-party annotation tools
with format conversion and automatic fallback mechanisms.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from uuid import uuid4

from src.ai.annotation_plugin_interface import (
    AnnotationPluginInterface,
    AnnotationType,
    AnnotationTask,
    AnnotationResult,
    PluginInfo,
    PluginNotFoundError,
    PluginConnectionError,
    PluginAnnotationError,
)
from src.ai.annotation_plugin_manager import (
    AnnotationPluginManager,
    get_plugin_manager,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Label Studio Format Converters
# ============================================================================

class LabelStudioFormatConverter:
    """
    Converts between internal format and Label Studio format.
    """
    
    @staticmethod
    def to_label_studio_task(task: AnnotationTask) -> Dict[str, Any]:
        """
        Convert AnnotationTask to Label Studio task format.
        
        Args:
            task: Internal annotation task
            
        Returns:
            Label Studio task dictionary
        """
        return {
            "id": task.id,
            "data": task.data,
            "meta": {
                "annotation_type": task.annotation_type.value,
                **task.metadata,
            },
        }
    
    @staticmethod
    def from_label_studio_annotation(
        ls_annotation: Dict[str, Any],
        task_id: str,
    ) -> AnnotationResult:
        """
        Convert Label Studio annotation to AnnotationResult.
        
        Args:
            ls_annotation: Label Studio annotation dictionary
            task_id: Task ID
            
        Returns:
            AnnotationResult
        """
        # Extract result from Label Studio format
        result_data = ls_annotation.get("result", [])
        
        # Convert to internal format
        annotation_data = {}
        
        for item in result_data:
            item_type = item.get("type", "")
            value = item.get("value", {})
            
            if item_type == "choices":
                annotation_data["label"] = value.get("choices", [])
            elif item_type == "labels":
                if "entities" not in annotation_data:
                    annotation_data["entities"] = []
                annotation_data["entities"].append({
                    "text": value.get("text", ""),
                    "label": value.get("labels", []),
                    "start": value.get("start", 0),
                    "end": value.get("end", 0),
                })
            elif item_type == "textarea":
                annotation_data["text"] = value.get("text", [""])[0]
            else:
                annotation_data[item_type] = value
        
        return AnnotationResult(
            task_id=task_id,
            annotation_data=annotation_data,
            confidence=ls_annotation.get("score", 0.0),
            method_used=ls_annotation.get("model_version", "label_studio"),
            metadata=ls_annotation.get("meta", {}),
        )
    
    @staticmethod
    def to_label_studio_annotation(
        result: AnnotationResult,
        annotation_type: AnnotationType,
    ) -> Dict[str, Any]:
        """
        Convert AnnotationResult to Label Studio annotation format.
        
        Args:
            result: Internal annotation result
            annotation_type: Type of annotation
            
        Returns:
            Label Studio annotation dictionary
        """
        ls_result = []
        annotation_data = result.annotation_data
        
        if annotation_type == AnnotationType.TEXT_CLASSIFICATION:
            if "label" in annotation_data:
                labels = annotation_data["label"]
                if isinstance(labels, str):
                    labels = [labels]
                ls_result.append({
                    "type": "choices",
                    "value": {"choices": labels},
                    "from_name": "label",
                    "to_name": "text",
                })
        
        elif annotation_type == AnnotationType.NER:
            entities = annotation_data.get("entities", [])
            for entity in entities:
                ls_result.append({
                    "type": "labels",
                    "value": {
                        "text": entity.get("text", ""),
                        "labels": entity.get("label", []),
                        "start": entity.get("start", 0),
                        "end": entity.get("end", 0),
                    },
                    "from_name": "label",
                    "to_name": "text",
                })
        
        elif annotation_type == AnnotationType.SENTIMENT:
            sentiment = annotation_data.get("sentiment", "neutral")
            ls_result.append({
                "type": "choices",
                "value": {"choices": [sentiment]},
                "from_name": "sentiment",
                "to_name": "text",
            })
        
        return {
            "result": ls_result,
            "score": result.confidence,
            "model_version": result.method_used,
            "meta": result.metadata,
        }


# ============================================================================
# Third Party Annotation Adapter
# ============================================================================

class ThirdPartyAnnotationAdapter:
    """
    Third-party annotation tool adapter.
    
    Provides unified interface for calling third-party annotation tools
    with automatic format conversion and fallback mechanisms.
    """
    
    def __init__(
        self,
        plugin_manager: Optional[AnnotationPluginManager] = None,
        fallback_handler: Optional[Callable] = None,
    ):
        """
        Initialize the adapter.
        
        Args:
            plugin_manager: Plugin manager instance
            fallback_handler: Optional fallback handler for failed calls
        """
        self.plugin_manager = plugin_manager or get_plugin_manager()
        self.fallback_handler = fallback_handler
        self.format_converter = LabelStudioFormatConverter()
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        tool_name: str,
        annotation_type: AnnotationType,
        use_fallback: bool = True,
    ) -> List[AnnotationResult]:
        """
        Call third-party tool for annotation.
        
        Args:
            tasks: List of annotation tasks
            tool_name: Name of the tool/plugin to use
            annotation_type: Type of annotation
            use_fallback: Whether to use fallback on failure
            
        Returns:
            List of annotation results
            
        Raises:
            PluginNotFoundError: If plugin not found
            PluginAnnotationError: If annotation fails and no fallback
        """
        # Get plugin
        plugin = self.plugin_manager.get_plugin(tool_name)
        if not plugin:
            if use_fallback and self.fallback_handler:
                logger.warning(f"Plugin {tool_name} not found, using fallback")
                return await self.fallback_to_builtin(tasks, annotation_type)
            raise PluginNotFoundError(tool_name)
        
        # Check if plugin supports annotation type
        supported_types = plugin.get_supported_types()
        if annotation_type not in supported_types:
            if use_fallback and self.fallback_handler:
                logger.warning(
                    f"Plugin {tool_name} doesn't support {annotation_type}, using fallback"
                )
                return await self.fallback_to_builtin(tasks, annotation_type)
            raise PluginAnnotationError(
                tool_name,
                f"Annotation type {annotation_type} not supported"
            )
        
        start_time = time.time()
        
        try:
            # Convert to native format
            native_tasks = plugin.to_native_format(tasks, annotation_type)
            
            # Call plugin
            native_results = await plugin.annotate(native_tasks)
            
            # Convert to Label Studio format
            results = plugin.to_label_studio_format(native_results)
            
            # Record success
            latency_ms = (time.time() - start_time) * 1000
            self.plugin_manager.record_call(
                tool_name,
                success=True,
                latency_ms=latency_ms,
            )
            
            logger.info(
                f"Annotated {len(tasks)} tasks with {tool_name} "
                f"in {latency_ms:.2f}ms"
            )
            
            return results
            
        except Exception as e:
            # Record failure
            latency_ms = (time.time() - start_time) * 1000
            self.plugin_manager.record_call(
                tool_name,
                success=False,
                latency_ms=latency_ms,
                error=str(e),
            )
            
            logger.error(f"Plugin {tool_name} annotation failed: {e}")
            
            # Try fallback
            if use_fallback and self.fallback_handler:
                logger.info(f"Falling back to builtin method")
                return await self.fallback_to_builtin(tasks, annotation_type)
            
            raise PluginAnnotationError(tool_name, str(e))
    
    async def annotate_with_best_plugin(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        use_fallback: bool = True,
    ) -> List[AnnotationResult]:
        """
        Annotate using the best available plugin for the annotation type.
        
        Args:
            tasks: List of annotation tasks
            annotation_type: Type of annotation
            use_fallback: Whether to use fallback on failure
            
        Returns:
            List of annotation results
        """
        # Get best plugin
        plugin = await self.plugin_manager.get_best_plugin(annotation_type)
        
        if not plugin:
            if use_fallback and self.fallback_handler:
                logger.warning(
                    f"No plugin found for {annotation_type}, using fallback"
                )
                return await self.fallback_to_builtin(tasks, annotation_type)
            raise PluginNotFoundError(f"No plugin for {annotation_type}")
        
        # Get plugin name
        info = plugin.get_info()
        return await self.annotate(
            tasks, info.name, annotation_type, use_fallback
        )
    
    async def fallback_to_builtin(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
    ) -> List[AnnotationResult]:
        """
        Fallback to builtin annotation method.
        
        Args:
            tasks: List of annotation tasks
            annotation_type: Type of annotation
            
        Returns:
            List of annotation results
        """
        if self.fallback_handler:
            return await self.fallback_handler(tasks, annotation_type)
        
        # Default fallback: return empty results with low confidence
        logger.warning("No fallback handler, returning empty results")
        return [
            AnnotationResult(
                task_id=task.id,
                annotation_data={},
                confidence=0.0,
                method_used="fallback_empty",
            )
            for task in tasks
        ]
    
    def set_fallback_handler(
        self,
        handler: Callable,
    ) -> None:
        """
        Set the fallback handler.
        
        Args:
            handler: Async function that takes (tasks, annotation_type)
                    and returns List[AnnotationResult]
        """
        self.fallback_handler = handler
    
    # ========================================================================
    # Format Conversion Utilities
    # ========================================================================
    
    def convert_to_label_studio(
        self,
        results: List[AnnotationResult],
        annotation_type: AnnotationType,
    ) -> List[Dict[str, Any]]:
        """
        Convert results to Label Studio format.
        
        Args:
            results: List of annotation results
            annotation_type: Type of annotation
            
        Returns:
            List of Label Studio annotation dictionaries
        """
        return [
            self.format_converter.to_label_studio_annotation(r, annotation_type)
            for r in results
        ]
    
    def convert_from_label_studio(
        self,
        ls_annotations: List[Dict[str, Any]],
        task_ids: List[str],
    ) -> List[AnnotationResult]:
        """
        Convert Label Studio annotations to internal format.
        
        Args:
            ls_annotations: List of Label Studio annotations
            task_ids: List of task IDs
            
        Returns:
            List of AnnotationResult
        """
        results = []
        for ls_ann, task_id in zip(ls_annotations, task_ids):
            result = self.format_converter.from_label_studio_annotation(
                ls_ann, task_id
            )
            results.append(result)
        return results
    
    # ========================================================================
    # Health and Status
    # ========================================================================
    
    async def check_tool_health(self, tool_name: str) -> bool:
        """
        Check if a tool is healthy.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if tool is healthy
        """
        try:
            status = await self.plugin_manager.health_check(tool_name)
            return status.healthy
        except Exception:
            return False
    
    async def get_available_tools(
        self,
        annotation_type: Optional[AnnotationType] = None,
    ) -> List[PluginInfo]:
        """
        Get list of available tools.
        
        Args:
            annotation_type: Optional filter by annotation type
            
        Returns:
            List of PluginInfo for available tools
        """
        if annotation_type:
            plugins = await self.plugin_manager.get_plugins_by_type(annotation_type)
            return [p.get_info() for p in plugins]
        else:
            return await self.plugin_manager.list_enabled_plugins()


# ============================================================================
# Singleton Instance
# ============================================================================

_adapter_instance: Optional[ThirdPartyAnnotationAdapter] = None


def get_third_party_adapter() -> ThirdPartyAnnotationAdapter:
    """
    Get or create the third-party adapter instance.
    
    Returns:
        ThirdPartyAnnotationAdapter instance
    """
    global _adapter_instance
    
    if _adapter_instance is None:
        _adapter_instance = ThirdPartyAnnotationAdapter()
    
    return _adapter_instance
