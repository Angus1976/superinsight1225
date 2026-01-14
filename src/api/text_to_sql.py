"""
FastAPI endpoints for Text-to-SQL in SuperInsight Platform.

Provides RESTful API for natural language to SQL query generation,
including method switching, plugin management, and configuration.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.text_to_sql import (
    SQLGenerationRequest,
    SQLGenerationResponse,
    SQLValidationResult,
    QueryPlan,
    TableInfo,
    DatabaseDialect
)
from src.text_to_sql.sql_generator import SQLGenerator, get_sql_generator
from src.text_to_sql.advanced_sql import AdvancedSQLGenerator, get_advanced_sql_generator
from src.text_to_sql.schema_manager import SchemaManager, get_schema_manager

# New imports for Method Switcher and Plugin Manager
from src.text_to_sql import (
    MethodSwitcher,
    get_method_switcher,
    MethodInfo,
    PluginInfo,
    PluginConfig,
    TextToSQLConfig,
    MethodType,
    ConnectionType,
    SQLGenerationResult as NewSQLGenerationResult,
)
from src.text_to_sql.schema_analyzer import DatabaseSchema

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/text-to-sql", tags=["Text-to-SQL"])


# Request/Response Models
class GenerateSQLRequest(BaseModel):
    """Request model for SQL generation."""
    query: str = Field(..., min_length=1, description="Natural language query")
    database_id: Optional[str] = Field(None, description="Target database identifier")
    connection_string: Optional[str] = Field(None, description="Database connection string")
    dialect: DatabaseDialect = Field(default=DatabaseDialect.POSTGRESQL, description="SQL dialect")
    max_results: Optional[int] = Field(None, ge=1, le=10000, description="Maximum rows to return")
    include_explanation: bool = Field(default=True, description="Include query explanation")
    validate_sql: bool = Field(default=True, description="Validate generated SQL")
    use_advanced: bool = Field(default=False, description="Use advanced SQL generation")


class ExecuteSQLRequest(BaseModel):
    """Request model for SQL execution."""
    sql: str = Field(..., min_length=1, description="SQL query to execute")
    connection_string: str = Field(..., description="Database connection string")
    max_rows: int = Field(default=100, ge=1, le=10000, description="Maximum rows to return")
    timeout: int = Field(default=30, ge=1, le=300, description="Query timeout in seconds")


class ValidateSQLRequest(BaseModel):
    """Request model for SQL validation."""
    sql: str = Field(..., min_length=1, description="SQL query to validate")
    dialect: DatabaseDialect = Field(default=DatabaseDialect.POSTGRESQL, description="SQL dialect")


class SchemaRequest(BaseModel):
    """Request model for schema retrieval."""
    connection_string: str = Field(..., description="Database connection string")
    schema_name: Optional[str] = Field(None, description="Schema name to load")
    include_tables: Optional[List[str]] = Field(None, description="Tables to include")
    exclude_tables: Optional[List[str]] = Field(None, description="Tables to exclude")


class GenerateSQLResponse(BaseModel):
    """Response model for SQL generation."""
    success: bool = Field(..., description="Generation success status")
    sql: str = Field(..., description="Generated SQL query")
    formatted_sql: Optional[str] = Field(None, description="Formatted SQL")
    explanation: Optional[str] = Field(None, description="Query explanation")
    confidence: float = Field(..., description="Confidence score")
    processing_time: float = Field(..., description="Processing time in seconds")
    query_plan: Optional[QueryPlan] = Field(None, description="Query execution plan")
    validation: Optional[SQLValidationResult] = Field(None, description="Validation result")
    model_used: Optional[str] = Field(None, description="AI model used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ExecuteSQLResponse(BaseModel):
    """Response model for SQL execution."""
    success: bool = Field(..., description="Execution success status")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    row_count: int = Field(default=0, description="Number of rows returned")
    column_names: List[str] = Field(default_factory=list, description="Column names")
    execution_time: float = Field(default=0.0, description="Execution time in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Execution warnings")


class SchemaResponse(BaseModel):
    """Response model for schema retrieval."""
    success: bool = Field(..., description="Retrieval success status")
    tables: List[TableInfo] = Field(default_factory=list, description="Table information")
    table_count: int = Field(default=0, description="Number of tables")
    relationships: Dict[str, List[str]] = Field(default_factory=dict, description="Table relationships")
    error: Optional[str] = Field(None, description="Error message if failed")


# =============================================================================
# New Request/Response Models for Method Switcher and Plugin Manager
# =============================================================================

class MethodGenerateRequest(BaseModel):
    """Request model for method-based SQL generation."""
    query: str = Field(..., min_length=1, description="Natural language query")
    method: Optional[MethodType] = Field(None, description="Override method (template/llm/hybrid/third_party)")
    db_type: Optional[str] = Field(None, description="Database type (postgresql/mysql/sqlite)")
    tool_name: Optional[str] = Field(None, description="Third-party tool name (for third_party method)")
    include_metadata: bool = Field(default=True, description="Include generation metadata")


class MethodGenerateResponse(BaseModel):
    """Response model for method-based SQL generation."""
    success: bool = Field(..., description="Generation success status")
    sql: str = Field(..., description="Generated SQL query")
    method_used: str = Field(..., description="Method used for generation")
    confidence: float = Field(..., description="Confidence score (0-1)")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TestGenerateRequestModel(BaseModel):
    """Request model for testing SQL generation."""
    query: str = Field(..., min_length=1, description="Natural language query to test")
    method: Optional[MethodType] = Field(None, description="Method to test")
    db_type: str = Field(default="postgresql", description="Database type")


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration update."""
    default_method: Optional[MethodType] = Field(None, description="Default generation method")
    auto_select_enabled: Optional[bool] = Field(None, description="Enable auto method selection")
    fallback_enabled: Optional[bool] = Field(None, description="Enable fallback on failure")
    template_config: Optional[Dict[str, Any]] = Field(None, description="Template method config")
    llm_config: Optional[Dict[str, Any]] = Field(None, description="LLM method config")
    hybrid_config: Optional[Dict[str, Any]] = Field(None, description="Hybrid method config")


class PluginRegisterRequest(BaseModel):
    """Request model for plugin registration."""
    name: str = Field(..., min_length=1, max_length=100, description="Plugin name")
    connection_type: ConnectionType = Field(..., description="Connection type (rest_api/grpc/local_sdk)")
    endpoint: Optional[str] = Field(None, description="API endpoint URL")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    enabled: bool = Field(default=True, description="Enable plugin on registration")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


# Service instances
_sql_generator: Optional[SQLGenerator] = None
_advanced_generator: Optional[AdvancedSQLGenerator] = None
_schema_manager: Optional[SchemaManager] = None


def get_generator() -> SQLGenerator:
    """Get SQL generator instance."""
    global _sql_generator
    if _sql_generator is None:
        _sql_generator = get_sql_generator()
    return _sql_generator


def get_advanced() -> AdvancedSQLGenerator:
    """Get advanced SQL generator instance."""
    global _advanced_generator
    if _advanced_generator is None:
        _advanced_generator = get_advanced_sql_generator()
    return _advanced_generator


def get_manager() -> SchemaManager:
    """Get schema manager instance."""
    global _schema_manager
    if _schema_manager is None:
        _schema_manager = get_schema_manager()
    return _schema_manager


# Endpoints
@router.post("/generate", response_model=GenerateSQLResponse)
async def generate_sql(request: GenerateSQLRequest) -> GenerateSQLResponse:
    """
    Generate SQL from natural language query.

    Converts a natural language query into SQL using AI models.
    """
    try:
        logger.info(f"Generating SQL for query: {request.query[:50]}...")
        start_time = time.time()

        # Get appropriate generator
        if request.use_advanced:
            generator = get_advanced()
        else:
            generator = get_generator()

        # Set connection if provided
        if request.connection_string:
            generator.set_connection(request.connection_string)

        # Create generation request
        gen_request = SQLGenerationRequest(
            query=request.query,
            database_id=request.database_id,
            dialect=request.dialect,
            max_results=request.max_results,
            include_explanation=request.include_explanation,
            validate_sql=request.validate_sql
        )

        # Generate SQL
        response = await generator.generate_sql(gen_request)

        return GenerateSQLResponse(
            success=bool(response.sql),
            sql=response.sql,
            formatted_sql=response.formatted_sql,
            explanation=response.explanation,
            confidence=response.confidence,
            processing_time=response.processing_time,
            query_plan=response.query_plan,
            validation=response.validation,
            model_used=response.model_used,
            metadata=response.metadata
        )

    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        return GenerateSQLResponse(
            success=False,
            sql="",
            confidence=0.0,
            processing_time=time.time() - start_time,
            metadata={"error": str(e)}
        )


@router.post("/execute", response_model=ExecuteSQLResponse)
async def execute_sql(request: ExecuteSQLRequest) -> ExecuteSQLResponse:
    """
    Execute a SQL query and return results.

    Executes the provided SQL query against the specified database.
    Only SELECT queries are allowed for security.
    """
    try:
        logger.info(f"Executing SQL query: {request.sql[:50]}...")
        start_time = time.time()

        # Validate SQL is SELECT only
        sql_upper = request.sql.upper().strip()
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return ExecuteSQLResponse(
                success=False,
                error="Only SELECT queries are allowed",
                execution_time=time.time() - start_time
            )

        # Check for dangerous operations
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
        for keyword in forbidden:
            if keyword in sql_upper:
                return ExecuteSQLResponse(
                    success=False,
                    error=f"Forbidden operation: {keyword}",
                    execution_time=time.time() - start_time
                )

        # Execute query using schema manager
        manager = get_manager()
        engine = manager.get_engine(request.connection_string)

        from sqlalchemy import text

        data = []
        column_names = []
        warnings = []

        with engine.connect() as conn:
            # Set timeout (PostgreSQL specific)
            try:
                conn.execute(text(f"SET statement_timeout = {request.timeout * 1000}"))
            except Exception:
                pass  # Not all databases support this

            result = conn.execute(text(request.sql))

            # Get column names
            column_names = list(result.keys())

            # Fetch rows
            rows = result.fetchmany(request.max_rows)
            data = [dict(zip(column_names, row)) for row in rows]

            # Check if more rows available
            if result.fetchone() is not None:
                warnings.append(f"Result truncated to {request.max_rows} rows")

        execution_time = time.time() - start_time

        return ExecuteSQLResponse(
            success=True,
            data=data,
            row_count=len(data),
            column_names=column_names,
            execution_time=execution_time,
            warnings=warnings
        )

    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        return ExecuteSQLResponse(
            success=False,
            error=str(e),
            execution_time=time.time() - start_time
        )


@router.post("/validate", response_model=SQLValidationResult)
async def validate_sql(request: ValidateSQLRequest) -> SQLValidationResult:
    """
    Validate a SQL query.

    Checks SQL syntax, safety, and provides optimization suggestions.
    """
    try:
        logger.info(f"Validating SQL: {request.sql[:50]}...")

        generator = get_generator()
        result = generator._validate_sql(request.sql, request.dialect)

        return result

    except Exception as e:
        logger.error(f"SQL validation failed: {e}")
        return SQLValidationResult(
            is_valid=False,
            errors=[str(e)],
            is_safe=False
        )


@router.post("/schema", response_model=SchemaResponse)
async def get_schema(request: SchemaRequest) -> SchemaResponse:
    """
    Get database schema information.

    Retrieves table and column information from the database.
    """
    try:
        logger.info("Loading database schema...")

        manager = get_manager()
        context = manager.load_schema(
            request.connection_string,
            schema_name=request.schema_name,
            include_tables=request.include_tables,
            exclude_tables=request.exclude_tables
        )

        return SchemaResponse(
            success=True,
            tables=context.tables,
            table_count=len(context.tables),
            relationships=context.relationships
        )

    except Exception as e:
        logger.error(f"Schema loading failed: {e}")
        return SchemaResponse(
            success=False,
            error=str(e)
        )


@router.get("/schema/tables", response_model=List[str])
async def list_tables(connection_string: str = Query(..., description="Database connection string")) -> List[str]:
    """
    List all tables in the database.
    """
    try:
        manager = get_manager()
        context = manager.load_schema(connection_string)
        return [table.name for table in context.tables]

    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tables: {str(e)}"
        )


@router.get("/schema/table/{table_name}", response_model=TableInfo)
async def get_table_info(
    table_name: str,
    connection_string: str = Query(..., description="Database connection string")
) -> TableInfo:
    """
    Get information for a specific table.
    """
    try:
        manager = get_manager()
        table = manager.get_table_info(connection_string, table_name)

        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table not found: {table_name}"
            )

        return table

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get table info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get table info: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics() -> JSONResponse:
    """
    Get Text-to-SQL service metrics.
    """
    try:
        generator = get_generator()
        gen_stats = generator.get_statistics()

        from src.text_to_sql.llm_adapter import get_llm_adapter
        llm_adapter = get_llm_adapter()
        llm_stats = llm_adapter.get_statistics()

        return JSONResponse(content={
            "success": True,
            "metrics": {
                "generator": gen_stats,
                "llm_adapter": llm_stats
            }
        })

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for Text-to-SQL service.
    """
    try:
        from src.text_to_sql.llm_adapter import get_llm_adapter
        llm_adapter = get_llm_adapter()
        llm_available = await llm_adapter.check_availability()

        return JSONResponse(content={
            "status": "healthy" if llm_available else "degraded",
            "components": {
                "sql_generator": "available",
                "schema_manager": "available",
                "llm_adapter": "available" if llm_available else "unavailable"
            }
        })

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@router.post("/analyze")
async def analyze_query(
    query: str = Query(..., description="Natural language query to analyze")
) -> JSONResponse:
    """
    Analyze a natural language query without generating SQL.

    Returns intent analysis and complexity estimation.
    """
    try:
        generator = get_generator()

        # Parse intent
        intent = generator._parse_intent(query)

        # Estimate complexity
        complexity = generator._estimate_complexity(intent)

        # Extract keywords
        keywords = generator._extract_keywords(query)

        return JSONResponse(content={
            "success": True,
            "query": query,
            "analysis": {
                "intent": intent,
                "complexity": complexity.value,
                "keywords": keywords
            }
        })

    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/dialects")
async def get_supported_dialects() -> JSONResponse:
    """
    Get list of supported SQL dialects.
    """
    return JSONResponse(content={
        "dialects": [d.value for d in DatabaseDialect]
    })


# =============================================================================
# Method Switcher Endpoints (Task 11.1)
# =============================================================================

@router.post("/methods/generate", response_model=MethodGenerateResponse)
async def generate_sql_with_method(request: MethodGenerateRequest) -> MethodGenerateResponse:
    """
    Generate SQL using the Method Switcher.
    
    Supports multiple methods: template, llm, hybrid, third_party.
    If no method specified, uses configured default or auto-selection.
    """
    try:
        logger.info(f"Generating SQL with method switcher: {request.query[:50]}...")
        
        switcher = get_method_switcher()
        
        result = await switcher.generate_sql(
            query=request.query,
            method=request.method,
            db_type=request.db_type,
            tool_name=request.tool_name,
        )
        
        return MethodGenerateResponse(
            success=bool(result.sql),
            sql=result.sql,
            method_used=result.method_used,
            confidence=result.confidence,
            execution_time_ms=result.execution_time_ms,
            metadata=result.metadata if request.include_metadata else {},
        )
        
    except Exception as e:
        logger.error(f"Method-based SQL generation failed: {e}")
        return MethodGenerateResponse(
            success=False,
            sql="",
            method_used="error",
            confidence=0.0,
            execution_time_ms=0.0,
            metadata={"error": str(e)},
        )


@router.get("/methods", response_model=List[MethodInfo])
async def list_methods() -> List[MethodInfo]:
    """
    List all available SQL generation methods.
    
    Returns built-in methods (template, llm, hybrid) and registered third-party tools.
    """
    try:
        switcher = get_method_switcher()
        return switcher.list_available_methods()
        
    except Exception as e:
        logger.error(f"Failed to list methods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list methods: {str(e)}"
        )


@router.post("/methods/test", response_model=MethodGenerateResponse)
async def test_generate(request: TestGenerateRequestModel) -> MethodGenerateResponse:
    """
    Test SQL generation without persisting results.
    
    Useful for previewing SQL before actual use.
    """
    try:
        logger.info(f"Testing SQL generation: {request.query[:50]}...")
        
        switcher = get_method_switcher()
        
        result = await switcher.generate_sql(
            query=request.query,
            method=request.method,
            db_type=request.db_type,
        )
        
        return MethodGenerateResponse(
            success=bool(result.sql),
            sql=result.sql,
            method_used=result.method_used,
            confidence=result.confidence,
            execution_time_ms=result.execution_time_ms,
            metadata={
                **result.metadata,
                "test_mode": True,
            },
        )
        
    except Exception as e:
        logger.error(f"Test generation failed: {e}")
        return MethodGenerateResponse(
            success=False,
            sql="",
            method_used="error",
            confidence=0.0,
            execution_time_ms=0.0,
            metadata={"error": str(e), "test_mode": True},
        )


@router.post("/methods/switch")
async def switch_method(method: MethodType) -> JSONResponse:
    """
    Switch the default SQL generation method.
    
    Returns the time taken to switch (should be < 500ms).
    """
    try:
        switcher = get_method_switcher()
        switch_time = switcher.switch_method(method)
        
        return JSONResponse(content={
            "success": True,
            "new_method": method.value,
            "switch_time_ms": switch_time,
            "message": f"Switched to {method.value} method in {switch_time:.2f}ms"
        })
        
    except Exception as e:
        logger.error(f"Failed to switch method: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/methods/current")
async def get_current_method() -> JSONResponse:
    """
    Get the current default SQL generation method.
    """
    try:
        switcher = get_method_switcher()
        current = switcher.get_current_method()
        
        return JSONResponse(content={
            "method": current.value,
            "description": _get_method_description(current),
        })
        
    except Exception as e:
        logger.error(f"Failed to get current method: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


def _get_method_description(method: MethodType) -> str:
    """Get description for a method type."""
    descriptions = {
        MethodType.TEMPLATE: "基于预定义模板的SQL生成，适用于结构化查询",
        MethodType.LLM: "基于大语言模型的SQL生成，适用于复杂自然语言查询",
        MethodType.HYBRID: "混合方法：模板优先，LLM回退，结合两者优势",
        MethodType.THIRD_PARTY: "第三方专业工具生成",
    }
    return descriptions.get(method, "Unknown method")


# =============================================================================
# Configuration Endpoints (Task 11.2)
# =============================================================================

@router.get("/config")
async def get_config() -> JSONResponse:
    """
    Get current Text-to-SQL configuration.
    """
    try:
        switcher = get_method_switcher()
        config = switcher.get_config()
        
        return JSONResponse(content={
            "success": True,
            "config": {
                "default_method": config.default_method.value,
                "auto_select_enabled": config.auto_select_enabled,
                "fallback_enabled": config.fallback_enabled,
                "template_config": config.template_config,
                "llm_config": config.llm_config,
                "hybrid_config": config.hybrid_config,
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.put("/config")
async def update_config(request: ConfigUpdateRequest) -> JSONResponse:
    """
    Update Text-to-SQL configuration.
    """
    try:
        switcher = get_method_switcher()
        current_config = switcher.get_config()
        
        # Build new config with updates
        new_config = TextToSQLConfig(
            default_method=request.default_method or current_config.default_method,
            auto_select_enabled=request.auto_select_enabled if request.auto_select_enabled is not None else current_config.auto_select_enabled,
            fallback_enabled=request.fallback_enabled if request.fallback_enabled is not None else current_config.fallback_enabled,
            template_config=request.template_config or current_config.template_config,
            llm_config=request.llm_config or current_config.llm_config,
            hybrid_config=request.hybrid_config or current_config.hybrid_config,
        )
        
        switcher.update_config(new_config)
        
        return JSONResponse(content={
            "success": True,
            "message": "Configuration updated successfully",
            "config": {
                "default_method": new_config.default_method.value,
                "auto_select_enabled": new_config.auto_select_enabled,
                "fallback_enabled": new_config.fallback_enabled,
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/statistics")
async def get_switcher_statistics() -> JSONResponse:
    """
    Get Method Switcher statistics.
    """
    try:
        switcher = get_method_switcher()
        stats = switcher.get_statistics()
        
        return JSONResponse(content={
            "success": True,
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


# =============================================================================
# Plugin Management Endpoints (Task 11.3)
# =============================================================================

@router.get("/plugins", response_model=List[PluginInfo])
async def list_plugins() -> List[PluginInfo]:
    """
    List all registered third-party plugins.
    """
    try:
        switcher = get_method_switcher()
        plugins = await switcher.plugin_manager.list_plugins()
        return plugins
        
    except Exception as e:
        logger.error(f"Failed to list plugins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list plugins: {str(e)}"
        )


@router.post("/plugins", response_model=PluginInfo)
async def register_plugin(request: PluginRegisterRequest) -> PluginInfo:
    """
    Register a new third-party plugin.
    """
    try:
        switcher = get_method_switcher()
        
        config = PluginConfig(
            name=request.name,
            connection_type=request.connection_type,
            endpoint=request.endpoint,
            api_key=request.api_key,
            timeout=request.timeout,
            enabled=request.enabled,
            extra_config=request.extra_config,
        )
        
        info = await switcher.plugin_manager.register_plugin(config)
        return info
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to register plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register plugin: {str(e)}"
        )


@router.put("/plugins/{name}", response_model=PluginInfo)
async def update_plugin(name: str, request: PluginRegisterRequest) -> PluginInfo:
    """
    Update an existing plugin configuration.
    """
    try:
        switcher = get_method_switcher()
        
        config = PluginConfig(
            name=request.name,
            connection_type=request.connection_type,
            endpoint=request.endpoint,
            api_key=request.api_key,
            timeout=request.timeout,
            enabled=request.enabled,
            extra_config=request.extra_config,
        )
        
        await switcher.plugin_manager.update_plugin_config(name, config)
        
        # Get updated info
        plugin = switcher.plugin_manager.get_plugin(name)
        if plugin:
            return plugin.get_info()
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update plugin: {str(e)}"
        )


@router.delete("/plugins/{name}")
async def unregister_plugin(name: str) -> JSONResponse:
    """
    Unregister a third-party plugin.
    """
    try:
        switcher = get_method_switcher()
        await switcher.plugin_manager.unregister_plugin(name)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Plugin '{name}' unregistered successfully"
        })
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to unregister plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister plugin: {str(e)}"
        )


@router.post("/plugins/{name}/enable")
async def enable_plugin(name: str) -> JSONResponse:
    """
    Enable a third-party plugin.
    """
    try:
        switcher = get_method_switcher()
        await switcher.plugin_manager.enable_plugin(name)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Plugin '{name}' enabled successfully"
        })
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to enable plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable plugin: {str(e)}"
        )


@router.post("/plugins/{name}/disable")
async def disable_plugin(name: str) -> JSONResponse:
    """
    Disable a third-party plugin.
    """
    try:
        switcher = get_method_switcher()
        await switcher.plugin_manager.disable_plugin(name)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Plugin '{name}' disabled successfully"
        })
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to disable plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable plugin: {str(e)}"
        )


@router.get("/plugins/health")
async def plugins_health() -> JSONResponse:
    """
    Check health status of all registered plugins.
    """
    try:
        switcher = get_method_switcher()
        health_status = await switcher.plugin_manager.health_check_all()
        
        return JSONResponse(content={
            "success": True,
            "health": health_status,
            "summary": {
                "total": len(health_status),
                "healthy": sum(1 for v in health_status.values() if v),
                "unhealthy": sum(1 for v in health_status.values() if not v),
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to check plugins health: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/plugins/{name}/health")
async def plugin_health(name: str) -> JSONResponse:
    """
    Check health status of a specific plugin.
    """
    try:
        switcher = get_method_switcher()
        plugin = switcher.plugin_manager.get_plugin(name)
        
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin not found: {name}"
            )
        
        is_healthy = await plugin.health_check()
        
        return JSONResponse(content={
            "success": True,
            "plugin": name,
            "healthy": is_healthy,
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check plugin health: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )
