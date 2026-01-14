"""
Method Switcher for Text-to-SQL Methods.

Provides unified interface for switching between different SQL generation methods
(template, LLM, hybrid, third-party) with automatic method selection.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from .schemas import (
    SQLGenerationResult,
    MethodInfo,
    MethodType,
    TextToSQLConfig,
)
from .schema_analyzer import DatabaseSchema
from .basic import TemplateFiller, get_template_filler
from .llm_based import LLMSQLGenerator, get_llm_sql_generator
from .hybrid import HybridGenerator, get_hybrid_generator
from .third_party_adapter import ThirdPartyAdapter
from .plugin_manager import PluginManager, get_plugin_manager

logger = logging.getLogger(__name__)


class DBType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MSSQL = "mssql"
    ORACLE = "oracle"


class MethodSwitcher:
    """
    Text-to-SQL Method Switcher.
    
    Features:
    - Unified interface for all SQL generation methods
    - Method routing based on configuration
    - Automatic method selection based on query and database type
    - Fast method switching (< 500ms)
    - Statistics tracking
    """
    
    def __init__(
        self,
        config: Optional[TextToSQLConfig] = None,
        template_filler: Optional[TemplateFiller] = None,
        llm_generator: Optional[LLMSQLGenerator] = None,
        hybrid_generator: Optional[HybridGenerator] = None,
        plugin_manager: Optional[PluginManager] = None,
    ):
        """
        Initialize Method Switcher.
        
        Args:
            config: Text-to-SQL configuration
            template_filler: Template filler instance
            llm_generator: LLM generator instance
            hybrid_generator: Hybrid generator instance
            plugin_manager: Plugin manager for third-party tools
        """
        self.config = config or TextToSQLConfig()
        
        # Lazy-loaded generators
        self._template_filler = template_filler
        self._llm_generator = llm_generator
        self._hybrid_generator = hybrid_generator
        self._plugin_manager = plugin_manager
        self._third_party_adapter: Optional[ThirdPartyAdapter] = None
        
        # Current method
        self._current_method = self.config.default_method
        
        # Statistics
        self._total_calls = 0
        self._method_calls: Dict[str, int] = {}
        self._switch_times: List[float] = []
        self._last_switch_time: Optional[datetime] = None

    
    # ==========================================================================
    # Properties for lazy initialization
    # ==========================================================================
    
    @property
    def template_filler(self) -> TemplateFiller:
        """Get template filler, initializing if needed."""
        if self._template_filler is None:
            self._template_filler = get_template_filler()
        return self._template_filler
    
    @property
    def llm_generator(self) -> LLMSQLGenerator:
        """Get LLM generator, initializing if needed."""
        if self._llm_generator is None:
            self._llm_generator = get_llm_sql_generator()
        return self._llm_generator
    
    @property
    def hybrid_generator(self) -> HybridGenerator:
        """Get hybrid generator, initializing if needed."""
        if self._hybrid_generator is None:
            self._hybrid_generator = get_hybrid_generator()
        return self._hybrid_generator
    
    @property
    def plugin_manager(self) -> PluginManager:
        """Get plugin manager, initializing if needed."""
        if self._plugin_manager is None:
            self._plugin_manager = get_plugin_manager()
        return self._plugin_manager
    
    @property
    def third_party_adapter(self) -> ThirdPartyAdapter:
        """Get third-party adapter, initializing if needed."""
        if self._third_party_adapter is None:
            self._third_party_adapter = ThirdPartyAdapter(
                plugin_manager=self.plugin_manager,
                fallback_generator=self.hybrid_generator,
            )
        return self._third_party_adapter
    
    # ==========================================================================
    # Core Methods
    # ==========================================================================
    
    async def generate_sql(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None,
        method: Optional[MethodType] = None,
        db_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> SQLGenerationResult:
        """
        Generate SQL from natural language query.
        
        Args:
            query: Natural language query
            schema: Database schema for context
            method: Override default method (optional)
            db_type: Database type for auto-selection
            tool_name: Third-party tool name (for third_party method)
            
        Returns:
            SQLGenerationResult with generated SQL
        """
        start_time = time.time()
        self._total_calls += 1
        
        # Determine method to use
        effective_method = method or self._current_method
        
        # Auto-select method if enabled and no explicit method specified
        if method is None and self.config.auto_select_enabled:
            effective_method = self.auto_select_method(query, db_type)
        
        # Track method usage
        method_key = effective_method.value if isinstance(effective_method, MethodType) else str(effective_method)
        self._method_calls[method_key] = self._method_calls.get(method_key, 0) + 1
        
        try:
            # Route to appropriate generator
            result = await self._route_to_generator(
                query, schema, effective_method, db_type, tool_name
            )
            
            # Add routing metadata
            result.metadata["routed_method"] = method_key
            result.metadata["auto_selected"] = method is None and self.config.auto_select_enabled
            result.metadata["routing_time_ms"] = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            
            # Try fallback if enabled
            if self.config.fallback_enabled and effective_method != MethodType.HYBRID:
                logger.info("Attempting fallback to hybrid method")
                try:
                    result = await self.hybrid_generator.generate(query, schema, db_type or "postgresql")
                    result.metadata["fallback_from"] = method_key
                    result.metadata["fallback_reason"] = str(e)
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
            
            # Return error result
            return SQLGenerationResult(
                sql="",
                method_used=method_key,
                confidence=0.0,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "error": str(e),
                    "routed_method": method_key,
                },
            )
    
    async def _route_to_generator(
        self,
        query: str,
        schema: Optional[DatabaseSchema],
        method: MethodType,
        db_type: Optional[str],
        tool_name: Optional[str],
    ) -> SQLGenerationResult:
        """Route request to appropriate generator."""
        db_type = db_type or "postgresql"
        
        if method == MethodType.TEMPLATE:
            return self.template_filler.generate(query, schema)
            
        elif method == MethodType.LLM:
            return await self.llm_generator.generate(query, schema, db_type=db_type)
            
        elif method == MethodType.HYBRID:
            return await self.hybrid_generator.generate(query, schema, db_type)
            
        elif method == MethodType.THIRD_PARTY:
            if not tool_name:
                # Get first available third-party tool
                plugins = await self.plugin_manager.list_plugins()
                enabled_plugins = [p for p in plugins if p.is_healthy]
                if enabled_plugins:
                    tool_name = enabled_plugins[0].name
                else:
                    raise ValueError("No third-party tools available")
            
            return await self.third_party_adapter.generate(query, schema, tool_name)
            
        else:
            # Default to hybrid
            return await self.hybrid_generator.generate(query, schema, db_type)
    
    def switch_method(self, method: MethodType) -> float:
        """
        Switch the default method.
        
        Args:
            method: New default method
            
        Returns:
            Time taken to switch in milliseconds
        """
        start_time = time.time()
        
        old_method = self._current_method
        self._current_method = method
        
        switch_time = (time.time() - start_time) * 1000
        self._switch_times.append(switch_time)
        self._last_switch_time = datetime.utcnow()
        
        logger.info(f"Switched method from {old_method} to {method} in {switch_time:.2f}ms")
        
        return switch_time
    
    def get_current_method(self) -> MethodType:
        """Get the current default method."""
        return self._current_method
    
    def list_available_methods(self) -> List[MethodInfo]:
        """
        List all available methods including third-party tools.
        
        Returns:
            List of MethodInfo for all available methods
        """
        methods = []
        
        # Built-in methods
        methods.append(MethodInfo(
            name="template",
            type=MethodType.TEMPLATE,
            description="基于预定义模板的SQL生成，适用于结构化查询",
            supported_db_types=["postgresql", "mysql", "sqlite"],
            is_available=True,
            is_enabled=True,
            config=self.config.template_config,
            statistics={"templates_count": len(self.template_filler.templates)},
        ))
        
        methods.append(MethodInfo(
            name="llm",
            type=MethodType.LLM,
            description="基于大语言模型的SQL生成，适用于复杂自然语言查询",
            supported_db_types=["postgresql", "mysql", "sqlite", "mssql", "oracle"],
            is_available=True,
            is_enabled=True,
            config=self.config.llm_config,
            statistics=self.llm_generator.get_statistics(),
        ))
        
        methods.append(MethodInfo(
            name="hybrid",
            type=MethodType.HYBRID,
            description="混合方法：模板优先，LLM回退，结合两者优势",
            supported_db_types=["postgresql", "mysql", "sqlite", "mssql", "oracle"],
            is_available=True,
            is_enabled=True,
            config=self.config.hybrid_config,
            statistics=self.hybrid_generator.get_statistics(),
        ))
        
        # Third-party methods
        try:
            # Use synchronous approach to avoid async issues
            for name, plugin in self.plugin_manager._plugins.items():
                info = plugin.get_info()
                methods.append(MethodInfo(
                    name=f"third_party:{name}",
                    type=MethodType.THIRD_PARTY,
                    description=info.description,
                    supported_db_types=info.supported_db_types,
                    is_available=info.is_healthy,
                    is_enabled=self.plugin_manager.is_plugin_enabled(name),
                    config={"connection_type": info.connection_type.value},
                    statistics={},
                ))
        except Exception as e:
            logger.warning(f"Failed to list third-party methods: {e}")
        
        return methods

    
    # ==========================================================================
    # Auto Method Selection
    # ==========================================================================
    
    def auto_select_method(
        self,
        query: str,
        db_type: Optional[str] = None
    ) -> MethodType:
        """
        Automatically select the best method based on query and database type.
        
        Selection criteria:
        1. Simple, structured queries -> Template
        2. Complex queries with specific DB features -> LLM
        3. Default -> Hybrid
        
        Args:
            query: Natural language query
            db_type: Database type
            
        Returns:
            Selected MethodType
        """
        query_lower = query.lower()
        
        # Check for template-friendly patterns
        template_patterns = [
            "统计", "数量", "总数", "个数",  # Count
            "求和", "总额", "合计",  # Sum
            "平均", "均值",  # Average
            "最大", "最高", "最小", "最低",  # Min/Max
            "排序", "降序", "升序",  # Sort
            "前", "条", "个",  # Top N
        ]
        
        # Check for complex query patterns
        complex_patterns = [
            "子查询", "嵌套",  # Subquery
            "窗口函数", "over", "partition",  # Window functions
            "递归", "cte", "with",  # CTE
            "pivot", "unpivot",  # Pivot
            "json", "jsonb", "array",  # JSON/Array operations
            "正则", "regex", "like",  # Pattern matching
            "事务", "transaction",  # Transaction
        ]
        
        # Check for database-specific features
        db_specific_patterns = {
            "postgresql": ["jsonb", "array_agg", "lateral", "returning"],
            "mysql": ["group_concat", "json_extract", "on duplicate"],
            "sqlite": ["json_extract", "group_concat"],
            "mssql": ["top", "pivot", "cross apply"],
            "oracle": ["rownum", "connect by", "listagg"],
        }
        
        # Score each method
        template_score = 0
        llm_score = 0
        
        # Template scoring
        for pattern in template_patterns:
            if pattern in query_lower:
                template_score += 1
        
        # Try template matching
        template_match = self.template_filler.match_template(query)
        if template_match and template_match.match_score > 0.7:
            template_score += 3
        
        # Complex query scoring
        for pattern in complex_patterns:
            if pattern in query_lower:
                llm_score += 2
        
        # Database-specific scoring
        if db_type and db_type.lower() in db_specific_patterns:
            for pattern in db_specific_patterns[db_type.lower()]:
                if pattern in query_lower:
                    llm_score += 1
        
        # Query length scoring (longer queries tend to be more complex)
        if len(query) > 100:
            llm_score += 1
        if len(query) > 200:
            llm_score += 1
        
        # Decision
        if template_score >= 3 and template_score > llm_score:
            return MethodType.TEMPLATE
        elif llm_score >= 3:
            return MethodType.LLM
        else:
            return MethodType.HYBRID
    
    # ==========================================================================
    # Configuration Management
    # ==========================================================================
    
    def update_config(self, config: TextToSQLConfig) -> None:
        """
        Update configuration.
        
        Args:
            config: New configuration
        """
        self.config = config
        self._current_method = config.default_method
        
        # Update hybrid generator threshold if specified
        if "template_confidence_threshold" in config.hybrid_config:
            self.hybrid_generator.set_template_threshold(
                config.hybrid_config["template_confidence_threshold"]
            )
        
        logger.info(f"Configuration updated, default method: {config.default_method}")
    
    def get_config(self) -> TextToSQLConfig:
        """Get current configuration."""
        return self.config
    
    # ==========================================================================
    # Statistics and Monitoring
    # ==========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get switcher statistics."""
        avg_switch_time = (
            sum(self._switch_times) / len(self._switch_times)
            if self._switch_times else 0.0
        )
        
        return {
            "total_calls": self._total_calls,
            "method_calls": self._method_calls,
            "current_method": self._current_method.value,
            "average_switch_time_ms": avg_switch_time,
            "max_switch_time_ms": max(self._switch_times) if self._switch_times else 0.0,
            "last_switch_time": self._last_switch_time.isoformat() if self._last_switch_time else None,
            "config": {
                "default_method": self.config.default_method.value,
                "auto_select_enabled": self.config.auto_select_enabled,
                "fallback_enabled": self.config.fallback_enabled,
            },
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self._total_calls = 0
        self._method_calls.clear()
        self._switch_times.clear()
        self._last_switch_time = None
    
    # ==========================================================================
    # Validation
    # ==========================================================================
    
    def validate_method_available(self, method: MethodType) -> bool:
        """
        Check if a method is available.
        
        Args:
            method: Method to check
            
        Returns:
            True if available, False otherwise
        """
        if method in [MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID]:
            return True
        
        if method == MethodType.THIRD_PARTY:
            # Check if any third-party plugins are available
            return len(self.plugin_manager._plugins) > 0
        
        return False


# =============================================================================
# Global Instance
# =============================================================================

_method_switcher: Optional[MethodSwitcher] = None


def get_method_switcher() -> MethodSwitcher:
    """Get or create global MethodSwitcher instance."""
    global _method_switcher
    if _method_switcher is None:
        _method_switcher = MethodSwitcher()
    return _method_switcher


def reset_method_switcher() -> None:
    """Reset global MethodSwitcher instance."""
    global _method_switcher
    _method_switcher = None
