"""
Admin Configuration API Routes for SuperInsight Platform.

Provides REST API endpoints for admin configuration management including:
- Dashboard data
- LLM configuration
- Database connections
- Sync strategies
- SQL builder
- Configuration history
- Third-party tools

**Feature: admin-configuration**
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.admin.schemas import (
    ConfigType,
    ValidationResult,
    ConnectionTestResult,
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse,
    DBConfigCreate,
    DBConfigUpdate,
    DBConfigResponse,
    SyncStrategyCreate,
    SyncStrategyUpdate,
    SyncStrategyResponse,
    SyncHistoryResponse,
    SyncJobResponse,
    QueryConfig,
    QueryResult,
    QueryTemplateCreate,
    QueryTemplateResponse,
    DatabaseSchema,
    ExecuteSQLRequest,
    ConfigHistoryResponse,
    ConfigDiff,
    RollbackRequest,
    ThirdPartyConfigCreate,
    ThirdPartyConfigUpdate,
    ThirdPartyConfigResponse,
    DashboardData,
)
from src.admin.config_manager import get_config_manager
from src.admin.sql_builder import get_sql_builder_service
from src.admin.sync_strategy import get_sync_strategy_service
from src.admin.history_tracker import get_history_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Configuration"])


# ========== Dashboard ==========

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard() -> DashboardData:
    """
    Get admin dashboard data.
    
    Returns system health, key metrics, recent alerts, and quick actions.
    
    **Requirement 1.1, 1.2: Dashboard**
    """
    # In a real implementation, this would aggregate data from various services
    return DashboardData(
        system_health={
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "label_studio": "connected",
        },
        key_metrics={
            "total_annotations": 0,
            "active_users": 0,
            "pending_tasks": 0,
            "sync_jobs_today": 0,
        },
        recent_alerts=[],
        quick_actions=[
            {"name": "Create LLM Config", "path": "/admin/llm"},
            {"name": "Add Database", "path": "/admin/databases"},
            {"name": "View History", "path": "/admin/history"},
        ],
        config_summary={
            "llm_configs": 0,
            "db_connections": 0,
            "sync_strategies": 0,
            "third_party_tools": 0,
        },
    )


# ========== LLM Configuration ==========

@router.get("/config/llm", response_model=List[LLMConfigResponse])
async def list_llm_configs(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    active_only: bool = Query(True, description="Only return active configs"),
) -> List[LLMConfigResponse]:
    """
    List all LLM configurations.
    
    **Requirement 2.1: LLM Configuration**
    """
    manager = get_config_manager()
    return await manager.list_llm_configs(tenant_id=tenant_id, active_only=active_only)


@router.get("/config/llm/{config_id}", response_model=LLMConfigResponse)
async def get_llm_config(
    config_id: str,
    tenant_id: Optional[str] = Query(None),
) -> LLMConfigResponse:
    """
    Get LLM configuration by ID.
    
    **Requirement 2.1: LLM Configuration**
    """
    manager = get_config_manager()
    config = await manager.get_llm_config(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM configuration not found")
    return config


@router.post("/config/llm", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    config: LLMConfigCreate,
    user_id: str = Query(..., description="User ID making the change"),
    user_name: str = Query("Unknown", description="User name"),
    tenant_id: Optional[str] = Query(None),
) -> LLMConfigResponse:
    """
    Create new LLM configuration.
    
    **Requirement 2.1, 2.4: LLM Configuration**
    """
    manager = get_config_manager()
    try:
        return await manager.save_llm_config(
            config=config,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/config/llm/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    config_id: str,
    config: LLMConfigUpdate,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> LLMConfigResponse:
    """
    Update LLM configuration.
    
    **Requirement 2.4: LLM Configuration**
    """
    manager = get_config_manager()
    try:
        return await manager.save_llm_config(
            config=config,
            user_id=user_id,
            user_name=user_name,
            config_id=config_id,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/config/llm/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    config_id: str,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> None:
    """
    Delete LLM configuration.
    
    **Requirement 2.4: LLM Configuration**
    """
    manager = get_config_manager()
    deleted = await manager.delete_llm_config(
        config_id=config_id,
        user_id=user_id,
        user_name=user_name,
        tenant_id=tenant_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="LLM configuration not found")


@router.post("/config/llm/{config_id}/test", response_model=ConnectionTestResult)
async def test_llm_connection(config_id: str) -> ConnectionTestResult:
    """
    Test LLM connection.
    
    **Requirement 2.5: LLM Connection Test**
    """
    # In a real implementation, this would test the LLM API connection
    return ConnectionTestResult(
        success=True,
        latency_ms=150.0,
        details={"model": "available"},
    )


# ========== Database Configuration ==========

@router.get("/config/databases", response_model=List[DBConfigResponse])
async def list_db_configs(
    tenant_id: Optional[str] = Query(None),
    active_only: bool = Query(True),
) -> List[DBConfigResponse]:
    """
    List all database configurations.
    
    **Requirement 3.1: Database Configuration**
    """
    manager = get_config_manager()
    return await manager.list_db_configs(tenant_id=tenant_id, active_only=active_only)


@router.get("/config/databases/{config_id}", response_model=DBConfigResponse)
async def get_db_config(
    config_id: str,
    tenant_id: Optional[str] = Query(None),
) -> DBConfigResponse:
    """
    Get database configuration by ID.
    
    **Requirement 3.1: Database Configuration**
    """
    manager = get_config_manager()
    config = await manager.get_db_config(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Database configuration not found")
    return config


@router.post("/config/databases", response_model=DBConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_db_config(
    config: DBConfigCreate,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> DBConfigResponse:
    """
    Create new database configuration.
    
    **Requirement 3.1, 3.3: Database Configuration**
    """
    manager = get_config_manager()
    try:
        return await manager.save_db_config(
            config=config,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/config/databases/{config_id}", response_model=DBConfigResponse)
async def update_db_config(
    config_id: str,
    config: DBConfigUpdate,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> DBConfigResponse:
    """
    Update database configuration.
    
    **Requirement 3.3: Database Configuration**
    """
    manager = get_config_manager()
    try:
        return await manager.save_db_config(
            config=config,
            user_id=user_id,
            user_name=user_name,
            config_id=config_id,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/config/databases/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_db_config(
    config_id: str,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> None:
    """
    Delete database configuration.
    
    **Requirement 3.3: Database Configuration**
    """
    manager = get_config_manager()
    deleted = await manager.delete_db_config(
        config_id=config_id,
        user_id=user_id,
        user_name=user_name,
        tenant_id=tenant_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Database configuration not found")


@router.post("/config/databases/{config_id}/test", response_model=ConnectionTestResult)
async def test_db_connection(
    config_id: str,
    tenant_id: Optional[str] = Query(None),
) -> ConnectionTestResult:
    """
    Test database connection.
    
    **Requirement 3.5: Database Connection Test**
    """
    manager = get_config_manager()
    return await manager.test_db_connection(config_id, tenant_id)


# ========== Sync Strategy ==========

@router.get("/config/sync", response_model=List[SyncStrategyResponse])
async def list_sync_strategies(
    tenant_id: Optional[str] = Query(None),
    enabled_only: bool = Query(False),
) -> List[SyncStrategyResponse]:
    """
    List all sync strategies.
    
    **Requirement 4.1: Sync Strategy**
    """
    service = get_sync_strategy_service()
    return await service.list_strategies(tenant_id=tenant_id, enabled_only=enabled_only)


@router.get("/config/sync/{strategy_id}", response_model=SyncStrategyResponse)
async def get_sync_strategy(
    strategy_id: str,
    tenant_id: Optional[str] = Query(None),
) -> SyncStrategyResponse:
    """
    Get sync strategy by ID.
    
    **Requirement 4.1: Sync Strategy**
    """
    service = get_sync_strategy_service()
    strategy = await service.get_strategy(strategy_id, tenant_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Sync strategy not found")
    return strategy


@router.get("/config/sync/db/{db_config_id}", response_model=SyncStrategyResponse)
async def get_sync_strategy_by_db(
    db_config_id: str,
    tenant_id: Optional[str] = Query(None),
) -> SyncStrategyResponse:
    """
    Get sync strategy by database config ID.
    
    **Requirement 4.1: Sync Strategy**
    """
    service = get_sync_strategy_service()
    strategy = await service.get_strategy_by_db_config(db_config_id, tenant_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Sync strategy not found")
    return strategy


@router.post("/config/sync", response_model=SyncStrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_sync_strategy(
    strategy: SyncStrategyCreate,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> SyncStrategyResponse:
    """
    Create new sync strategy.
    
    **Requirement 4.1, 4.2, 4.3: Sync Strategy**
    """
    service = get_sync_strategy_service()
    try:
        return await service.save_strategy(
            strategy=strategy,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/config/sync/{strategy_id}", response_model=SyncStrategyResponse)
async def update_sync_strategy(
    strategy_id: str,
    strategy: SyncStrategyUpdate,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> SyncStrategyResponse:
    """
    Update sync strategy.
    
    **Requirement 4.4: Sync Strategy**
    """
    service = get_sync_strategy_service()
    try:
        return await service.save_strategy(
            strategy=strategy,
            user_id=user_id,
            user_name=user_name,
            strategy_id=strategy_id,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/config/sync/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sync_strategy(
    strategy_id: str,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
    tenant_id: Optional[str] = Query(None),
) -> None:
    """
    Delete sync strategy.
    """
    service = get_sync_strategy_service()
    deleted = await service.delete_strategy(
        strategy_id=strategy_id,
        user_id=user_id,
        user_name=user_name,
        tenant_id=tenant_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Sync strategy not found")


@router.post("/config/sync/{strategy_id}/trigger", response_model=SyncJobResponse)
async def trigger_sync(
    strategy_id: str,
    user_id: str = Query(...),
) -> SyncJobResponse:
    """
    Trigger sync job.
    
    **Requirement 4.6: Sync Trigger**
    """
    service = get_sync_strategy_service()
    try:
        return await service.trigger_sync(strategy_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/config/sync/retry/{job_id}", response_model=SyncJobResponse)
async def retry_sync(
    job_id: str,
    user_id: str = Query(...),
) -> SyncJobResponse:
    """
    Retry failed sync job.
    
    **Requirement 4.7: Sync Retry**
    """
    service = get_sync_strategy_service()
    try:
        return await service.retry_sync(job_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/config/sync/{strategy_id}/history", response_model=List[SyncHistoryResponse])
async def get_sync_history(
    strategy_id: str,
    limit: int = Query(50, ge=1, le=200),
) -> List[SyncHistoryResponse]:
    """
    Get sync history for a strategy.
    """
    service = get_sync_strategy_service()
    return await service.get_sync_history(strategy_id, limit)


# ========== SQL Builder ==========

@router.get("/sql-builder/schema/{db_config_id}", response_model=DatabaseSchema)
async def get_db_schema(db_config_id: str) -> DatabaseSchema:
    """
    Get database schema.
    
    **Requirement 5.1: SQL Builder Schema**
    """
    service = get_sql_builder_service()
    return await service.get_schema(db_config_id)


class BuildSQLRequest(BaseModel):
    """Request for building SQL."""
    query_config: QueryConfig
    db_type: str = "postgresql"


class BuildSQLResponse(BaseModel):
    """Response with built SQL."""
    sql: str
    validation: ValidationResult


@router.post("/sql-builder/build", response_model=BuildSQLResponse)
async def build_sql(request: BuildSQLRequest) -> BuildSQLResponse:
    """
    Build SQL from query configuration.
    
    **Requirement 5.4: SQL Builder**
    """
    service = get_sql_builder_service()
    try:
        sql = service.build_sql(request.query_config, request.db_type)
        validation = service.validate_sql(sql, request.db_type)
        return BuildSQLResponse(sql=sql, validation=validation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sql-builder/validate", response_model=ValidationResult)
async def validate_sql(
    sql: str = Query(..., description="SQL to validate"),
    db_type: str = Query("postgresql"),
) -> ValidationResult:
    """
    Validate SQL query.
    
    **Requirement 5.5: SQL Validation**
    """
    service = get_sql_builder_service()
    return service.validate_sql(sql, db_type)


@router.post("/sql-builder/execute", response_model=QueryResult)
async def execute_sql(request: ExecuteSQLRequest) -> QueryResult:
    """
    Execute SQL query with preview limit.
    
    **Requirement 5.6: SQL Execution**
    """
    service = get_sql_builder_service()
    try:
        return await service.execute_preview(
            sql=request.sql,
            db_connection=request.db_config_id,
            limit=request.limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sql-builder/templates", response_model=List[QueryTemplateResponse])
async def list_query_templates(
    db_config_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
) -> List[QueryTemplateResponse]:
    """
    List query templates.
    
    **Requirement 5.7: Query Templates**
    """
    service = get_sql_builder_service()
    return await service.list_templates(db_config_id, tenant_id)


@router.post("/sql-builder/templates", response_model=QueryTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_query_template(
    template: QueryTemplateCreate,
    user_id: str = Query(...),
    tenant_id: Optional[str] = Query(None),
) -> QueryTemplateResponse:
    """
    Create query template.
    
    **Requirement 5.7: Query Templates**
    """
    service = get_sql_builder_service()
    try:
        return await service.save_template(template, user_id, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sql-builder/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query_template(template_id: str) -> None:
    """
    Delete query template.
    """
    service = get_sql_builder_service()
    deleted = await service.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")


# ========== Configuration History ==========

@router.get("/config/history", response_model=List[ConfigHistoryResponse])
async def get_config_history(
    config_type: Optional[ConfigType] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[ConfigHistoryResponse]:
    """
    Get configuration change history.
    
    **Requirement 6.1, 6.3: Configuration History**
    """
    tracker = get_history_tracker()
    return await tracker.get_history(
        config_type=config_type,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )


@router.get("/config/history/{history_id}", response_model=ConfigHistoryResponse)
async def get_config_history_by_id(history_id: str) -> ConfigHistoryResponse:
    """
    Get specific history record.
    """
    tracker = get_history_tracker()
    history = await tracker.get_history_by_id(history_id)
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")
    return history


@router.get("/config/history/{history_id}/diff", response_model=ConfigDiff)
async def get_config_diff(history_id: str) -> ConfigDiff:
    """
    Get configuration diff for a history record.
    
    **Requirement 6.2: Configuration Diff**
    """
    tracker = get_history_tracker()
    diff = await tracker.get_diff_by_history_id(history_id)
    if not diff:
        raise HTTPException(status_code=404, detail="History record not found")
    return diff


@router.post("/config/history/{history_id}/rollback", response_model=Dict[str, Any])
async def rollback_config(
    history_id: str,
    request: RollbackRequest,
    user_id: str = Query(...),
    user_name: str = Query("Unknown"),
) -> Dict[str, Any]:
    """
    Rollback configuration to a previous version.
    
    **Requirement 6.4, 6.5: Configuration Rollback**
    """
    tracker = get_history_tracker()
    result = await tracker.rollback(history_id, user_id, user_name)
    if not result:
        raise HTTPException(status_code=404, detail="History record not found or cannot rollback")
    return {"success": True, "rolled_back_config": result}


# ========== Third-Party Tools ==========

@router.get("/config/third-party", response_model=List[ThirdPartyConfigResponse])
async def list_third_party_configs(
    tenant_id: Optional[str] = Query(None),
) -> List[ThirdPartyConfigResponse]:
    """
    List third-party tool configurations.
    
    **Requirement 7.1: Third-Party Tools**
    """
    # Placeholder - would be implemented with a ThirdPartyConfigService
    return []


@router.post("/config/third-party", response_model=ThirdPartyConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_third_party_config(
    config: ThirdPartyConfigCreate,
    user_id: str = Query(...),
    tenant_id: Optional[str] = Query(None),
) -> ThirdPartyConfigResponse:
    """
    Create third-party tool configuration.
    
    **Requirement 7.1: Third-Party Tools**
    """
    # Placeholder implementation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/config/third-party/{config_id}", response_model=ThirdPartyConfigResponse)
async def update_third_party_config(
    config_id: str,
    config: ThirdPartyConfigUpdate,
    user_id: str = Query(...),
    tenant_id: Optional[str] = Query(None),
) -> ThirdPartyConfigResponse:
    """
    Update third-party tool configuration.
    
    **Requirement 7.3: Third-Party Tools**
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/config/third-party/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_third_party_config(
    config_id: str,
    user_id: str = Query(...),
) -> None:
    """
    Delete third-party tool configuration.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/config/third-party/{config_id}/health", response_model=ConnectionTestResult)
async def check_third_party_health(config_id: str) -> ConnectionTestResult:
    """
    Check third-party tool health.
    
    **Requirement 7.4: Third-Party Health Check**
    """
    raise HTTPException(status_code=501, detail="Not implemented")


# ========== Validation Endpoints ==========

@router.post("/validate/llm", response_model=ValidationResult)
async def validate_llm_config(config: LLMConfigCreate) -> ValidationResult:
    """
    Validate LLM configuration without saving.
    """
    manager = get_config_manager()
    return manager.validate_config(ConfigType.LLM, config.model_dump())


@router.post("/validate/database", response_model=ValidationResult)
async def validate_db_config(config: DBConfigCreate) -> ValidationResult:
    """
    Validate database configuration without saving.
    """
    manager = get_config_manager()
    return manager.validate_config(ConfigType.DATABASE, config.model_dump())


@router.post("/validate/sync", response_model=ValidationResult)
async def validate_sync_config(config: SyncStrategyCreate) -> ValidationResult:
    """
    Validate sync strategy without saving.
    """
    service = get_sync_strategy_service()
    return service.validate_strategy(config)
