"""
Third Party Adapter for Text-to-SQL Tools.

Provides unified interface for calling third-party Text-to-SQL tools
with automatic format conversion and fallback mechanisms.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .schemas import (
    SQLGenerationResult,
    MethodType,
)
from .schema_analyzer import DatabaseSchema
from .plugin_interface import (
    PluginInterface,
    PluginNotFoundError,
    PluginCallError,
)
from .plugin_manager import PluginManager, get_plugin_manager

logger = logging.getLogger(__name__)


class ThirdPartyAdapter:
    """
    Adapter for third-party Text-to-SQL tools.
    
    Features:
    - Unified interface for all third-party tools
    - Automatic request/response format conversion
    - Fallback to built-in methods on failure
    - Timeout handling and retry logic
    """
    
    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        fallback_generator: Optional[Any] = None,
        default_timeout: int = 30,
        max_retries: int = 2,
    ):
        """
        Initialize Third Party Adapter.
        
        Args:
            plugin_manager: Plugin manager instance
            fallback_generator: Fallback generator for failures
            default_timeout: Default timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.plugin_manager = plugin_manager or get_plugin_manager()
        self.fallback_generator = fallback_generator
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        
        # Statistics
        self._total_calls = 0
        self._successful_calls = 0
        self._fallback_calls = 0
    
    async def generate(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None,
        tool_name: str = None,
        timeout: Optional[int] = None,
    ) -> SQLGenerationResult:
        """
        Generate SQL using a third-party tool.
        
        Args:
            query: Natural language query
            schema: Database schema
            tool_name: Name of the tool to use
            timeout: Request timeout in seconds
            
        Returns:
            SQLGenerationResult
            
        Raises:
            PluginNotFoundError: If tool not found
            PluginCallError: If call fails and no fallback
        """
        self._total_calls += 1
        start_time = time.time()
        
        # Get plugin
        plugin = self.plugin_manager.get_plugin(tool_name)
        if not plugin:
            raise PluginNotFoundError(tool_name)
        
        # Check if plugin is enabled
        if not self.plugin_manager.is_plugin_enabled(tool_name):
            logger.warning(f"Plugin {tool_name} is disabled, using fallback")
            return await self._fallback_to_builtin(query, schema, "plugin_disabled")
        
        # Try to call the plugin
        timeout = timeout or self.default_timeout
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._call_plugin(
                    plugin, query, schema, tool_name, timeout
                )
                
                # Record success
                self._successful_calls += 1
                execution_time = (time.time() - start_time) * 1000
                
                if hasattr(plugin, 'record_call'):
                    plugin.record_call(True, execution_time)
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning(
                    f"Plugin {tool_name} timed out (attempt {attempt + 1}/{self.max_retries + 1})"
                )
                if attempt == self.max_retries:
                    return await self._fallback_to_builtin(query, schema, "timeout")
                    
            except Exception as e:
                logger.error(
                    f"Plugin {tool_name} error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )
                if attempt == self.max_retries:
                    return await self._fallback_to_builtin(query, schema, str(e))
        
        # Should not reach here, but fallback just in case
        return await self._fallback_to_builtin(query, schema, "unknown_error")
    
    async def _call_plugin(
        self,
        plugin: PluginInterface,
        query: str,
        schema: Optional[DatabaseSchema],
        tool_name: str,
        timeout: int,
    ) -> SQLGenerationResult:
        """Call a plugin with timeout."""
        # Convert to native format
        native_request = plugin.to_native_format(query, schema)
        
        # Call with timeout
        native_response = await asyncio.wait_for(
            plugin.call(native_request),
            timeout=timeout
        )
        
        # Convert response
        result = plugin.from_native_format(native_response)
        
        # Ensure method_used is set correctly
        if not result.method_used.startswith("third_party:"):
            result.method_used = f"third_party:{tool_name}"
        
        return result
    
    async def fallback_to_builtin(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None,
    ) -> SQLGenerationResult:
        """
        Fallback to built-in method.
        
        Public method for explicit fallback.
        
        Args:
            query: Natural language query
            schema: Database schema
            
        Returns:
            SQLGenerationResult from built-in method
        """
        return await self._fallback_to_builtin(query, schema, "explicit_fallback")
    
    async def _fallback_to_builtin(
        self,
        query: str,
        schema: Optional[DatabaseSchema],
        reason: str,
    ) -> SQLGenerationResult:
        """
        Internal fallback to built-in method.
        
        Args:
            query: Natural language query
            schema: Database schema
            reason: Reason for fallback
            
        Returns:
            SQLGenerationResult from built-in method
        """
        self._fallback_calls += 1
        
        if self.fallback_generator:
            try:
                result = await self.fallback_generator.generate(query, schema)
                result.metadata["fallback_reason"] = reason
                result.metadata["fallback_from"] = "third_party"
                return result
            except Exception as e:
                logger.error(f"Fallback generator failed: {e}")
        
        # Return empty result if no fallback available
        return SQLGenerationResult(
            sql="",
            method_used="fallback:none",
            confidence=0.0,
            execution_time_ms=0.0,
            metadata={
                "fallback_reason": reason,
                "error": "No fallback generator available",
            },
        )
    
    async def call_multiple(
        self,
        query: str,
        schema: Optional[DatabaseSchema],
        tool_names: List[str],
        strategy: str = "first_success",
    ) -> SQLGenerationResult:
        """
        Call multiple tools and combine results.
        
        Args:
            query: Natural language query
            schema: Database schema
            tool_names: List of tool names to try
            strategy: Combination strategy (first_success, best_confidence, all)
            
        Returns:
            SQLGenerationResult
        """
        if strategy == "first_success":
            return await self._first_success_strategy(query, schema, tool_names)
        elif strategy == "best_confidence":
            return await self._best_confidence_strategy(query, schema, tool_names)
        else:
            # Default to first success
            return await self._first_success_strategy(query, schema, tool_names)
    
    async def _first_success_strategy(
        self,
        query: str,
        schema: Optional[DatabaseSchema],
        tool_names: List[str],
    ) -> SQLGenerationResult:
        """Try tools in order, return first successful result."""
        for tool_name in tool_names:
            try:
                result = await self.generate(query, schema, tool_name)
                if result.sql and result.confidence > 0:
                    return result
            except Exception as e:
                logger.warning(f"Tool {tool_name} failed: {e}")
                continue
        
        # All tools failed, use fallback
        return await self._fallback_to_builtin(query, schema, "all_tools_failed")
    
    async def _best_confidence_strategy(
        self,
        query: str,
        schema: Optional[DatabaseSchema],
        tool_names: List[str],
    ) -> SQLGenerationResult:
        """Try all tools, return result with highest confidence."""
        results = []
        
        for tool_name in tool_names:
            try:
                result = await self.generate(query, schema, tool_name)
                if result.sql:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Tool {tool_name} failed: {e}")
                continue
        
        if not results:
            return await self._fallback_to_builtin(query, schema, "all_tools_failed")
        
        # Return result with highest confidence
        return max(results, key=lambda r: r.confidence)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            "total_calls": self._total_calls,
            "successful_calls": self._successful_calls,
            "fallback_calls": self._fallback_calls,
            "success_rate": self._successful_calls / max(1, self._total_calls),
            "fallback_rate": self._fallback_calls / max(1, self._total_calls),
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self._total_calls = 0
        self._successful_calls = 0
        self._fallback_calls = 0
