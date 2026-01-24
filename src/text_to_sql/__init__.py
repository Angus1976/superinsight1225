"""
Text-to-SQL Module for SuperInsight Platform.

Provides natural language to SQL query generation capabilities
using multiple methods: template-based, LLM-based, hybrid, and third-party tools.
"""

from .models import (
    SQLGenerationRequest,
    SQLGenerationResponse,
    QueryPlan,
    SQLValidationResult,
    TableInfo,
    ColumnInfo,
    QueryComplexity,
    DatabaseDialect
)
from .schemas import (
    SQLGenerationResult,
    MethodInfo,
    PluginInfo,
    PluginConfig,
    SQLTemplate,
    TemplateMatch,
    ValidationResult,
    TextToSQLConfig,
    GenerateSQLRequest,
    TestGenerateRequest,
    MethodType,
    ConnectionType,
    TemplateCategory,
    ParamType,
    PluginHealthStatus,
    PluginStatistics,
)
from .schema_manager import SchemaManager
from .llm_adapter import LLMAdapter, get_llm_adapter
from .sql_generator import SQLGenerator
from .advanced_sql import AdvancedSQLGenerator
from .switcher import MethodSwitcher, get_method_switcher, reset_method_switcher
from .basic import TemplateFiller, get_template_filler
from .llm_based import LLMSQLGenerator, get_llm_sql_generator
from .hybrid import HybridGenerator, get_hybrid_generator
from .plugin_manager import PluginManager, get_plugin_manager
from .third_party_adapter import ThirdPartyAdapter

__all__ = [
    # Legacy Models
    "SQLGenerationRequest",
    "SQLGenerationResponse",
    "QueryPlan",
    "SQLValidationResult",
    "TableInfo",
    "ColumnInfo",
    "QueryComplexity",
    "DatabaseDialect",
    # New Schemas
    "SQLGenerationResult",
    "MethodInfo",
    "PluginInfo",
    "PluginConfig",
    "SQLTemplate",
    "TemplateMatch",
    "ValidationResult",
    "TextToSQLConfig",
    "GenerateSQLRequest",
    "TestGenerateRequest",
    "MethodType",
    "ConnectionType",
    "TemplateCategory",
    "ParamType",
    "PluginHealthStatus",
    "PluginStatistics",
    # Core Classes
    "SchemaManager",
    "LLMAdapter",
    "get_llm_adapter",
    "SQLGenerator",
    "AdvancedSQLGenerator",
    # New Method Switcher
    "MethodSwitcher",
    "get_method_switcher",
    "reset_method_switcher",
    # Generators
    "TemplateFiller",
    "get_template_filler",
    "LLMSQLGenerator",
    "get_llm_sql_generator",
    "HybridGenerator",
    "get_hybrid_generator",
    # Plugin System
    "PluginManager",
    "get_plugin_manager",
    "ThirdPartyAdapter",
]

__version__ = "2.0.0"
