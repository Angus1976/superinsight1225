"""
Data Sources API for SuperInsight Platform.

Provides RESTful API for managing data sources:
- CRUD operations for data sources
- Connection testing
- Schema discovery
- Source monitoring
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-sources", tags=["Data Sources"])


# ============== Pydantic Models ==============

class DataSourceBase(BaseModel):
    """Base data source model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_type: str = Field(..., description="Type: database, api, file, stream, cloud_storage")
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=100)
    
    # Connection configuration
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Extraction settings
    batch_size: int = Field(default=1000, ge=1, le=100000)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    
    # Schema settings
    schema_mapping: Optional[Dict[str, str]] = None
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    
    # Incremental settings
    incremental_field: Optional[str] = None
    
    # Tags and metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DataSourceCreate(DataSourceBase):
    """Model for creating a data source."""
    pass


class DataSourceUpdate(BaseModel):
    """Model for updating a data source."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    connection_config: Optional[Dict[str, Any]] = None
    batch_size: Optional[int] = Field(None, ge=1, le=100000)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600)
    schema_mapping: Optional[Dict[str, str]] = None
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    incremental_field: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DataSourceResponse(DataSourceBase):
    """Response model for data source."""
    id: str
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    sync_status: str = "idle"
    record_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class ConnectionTestRequest(BaseModel):
    """Request model for connection test."""
    source_type: str
    connection_config: Dict[str, Any]


class ConnectionTestResponse(BaseModel):
    """Response model for connection test."""
    success: bool
    latency_ms: float
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SchemaDiscoveryResponse(BaseModel):
    """Response model for schema discovery."""
    source_id: str
    schema: Dict[str, Any]
    discovered_at: datetime
    sample_count: int


class DataSourceStats(BaseModel):
    """Statistics for a data source."""
    source_id: str
    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    total_records: int = 0
    total_bytes: int = 0
    avg_sync_duration: float = 0.0
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None


# ============== In-Memory Storage (Replace with DB in production) ==============

_data_sources: Dict[str, Dict[str, Any]] = {}
_source_stats: Dict[str, Dict[str, Any]] = {}


# ============== API Endpoints ==============

@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(source: DataSourceCreate) -> DataSourceResponse:
    """
    Create a new data source.
    
    Creates a data source configuration that can be used for data extraction
    and synchronization.
    """
    source_id = str(uuid4())
    now = datetime.utcnow()
    
    source_data = {
        "id": source_id,
        **source.model_dump(),
        "created_at": now,
        "updated_at": now,
        "last_sync_at": None,
        "sync_status": "idle",
        "record_count": None
    }
    
    _data_sources[source_id] = source_data
    
    # Initialize stats
    _source_stats[source_id] = {
        "source_id": source_id,
        "total_syncs": 0,
        "successful_syncs": 0,
        "failed_syncs": 0,
        "total_records": 0,
        "total_bytes": 0,
        "avg_sync_duration": 0.0,
        "last_sync_at": None,
        "last_error": None
    }
    
    logger.info(f"Created data source: {source_id} ({source.name})")
    
    return DataSourceResponse(**source_data)


@router.get("", response_model=List[DataSourceResponse])
async def list_data_sources(
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
) -> List[DataSourceResponse]:
    """
    List all data sources with optional filtering.
    """
    sources = list(_data_sources.values())
    
    # Apply filters
    if source_type:
        sources = [s for s in sources if s["source_type"] == source_type]
    
    if enabled is not None:
        sources = [s for s in sources if s["enabled"] == enabled]
    
    if tag:
        sources = [s for s in sources if tag in s.get("tags", [])]
    
    # Apply pagination
    sources = sources[skip:skip + limit]
    
    return [DataSourceResponse(**s) for s in sources]


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_data_source(source_id: str) -> DataSourceResponse:
    """
    Get a specific data source by ID.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    return DataSourceResponse(**_data_sources[source_id])


@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_data_source(
    source_id: str,
    update: DataSourceUpdate
) -> DataSourceResponse:
    """
    Update a data source.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    source_data = _data_sources[source_id]
    
    # Update only provided fields
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        source_data[key] = value
    
    source_data["updated_at"] = datetime.utcnow()
    
    logger.info(f"Updated data source: {source_id}")
    
    return DataSourceResponse(**source_data)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(source_id: str) -> None:
    """
    Delete a data source.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    del _data_sources[source_id]
    
    if source_id in _source_stats:
        del _source_stats[source_id]
    
    logger.info(f"Deleted data source: {source_id}")


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection(request: ConnectionTestRequest) -> ConnectionTestResponse:
    """
    Test connection to a data source without creating it.
    
    Validates the connection configuration and returns connection details.
    """
    import time
    start_time = time.time()
    
    try:
        # Simulate connection test based on source type
        # In production, use actual connectors
        
        if request.source_type == "database":
            # Validate database config
            required = ["host", "port", "database"]
            for field in required:
                if field not in request.connection_config:
                    return ConnectionTestResponse(
                        success=False,
                        latency_ms=(time.time() - start_time) * 1000,
                        error=f"Missing required field: {field}"
                    )
            
            # Simulate connection
            await asyncio.sleep(0.1)
            
            return ConnectionTestResponse(
                success=True,
                latency_ms=(time.time() - start_time) * 1000,
                details={
                    "host": request.connection_config.get("host"),
                    "database": request.connection_config.get("database"),
                    "version": "15.0"
                }
            )
        
        elif request.source_type == "api":
            # Validate API config
            if "base_url" not in request.connection_config:
                return ConnectionTestResponse(
                    success=False,
                    latency_ms=(time.time() - start_time) * 1000,
                    error="Missing required field: base_url"
                )
            
            # Simulate API test
            await asyncio.sleep(0.05)
            
            return ConnectionTestResponse(
                success=True,
                latency_ms=(time.time() - start_time) * 1000,
                details={
                    "base_url": request.connection_config.get("base_url"),
                    "status": "reachable"
                }
            )
        
        elif request.source_type in ["file", "cloud_storage"]:
            # Validate file/storage config
            if "path" not in request.connection_config and "bucket" not in request.connection_config:
                return ConnectionTestResponse(
                    success=False,
                    latency_ms=(time.time() - start_time) * 1000,
                    error="Missing required field: path or bucket"
                )
            
            return ConnectionTestResponse(
                success=True,
                latency_ms=(time.time() - start_time) * 1000,
                details={
                    "accessible": True
                }
            )
        
        else:
            return ConnectionTestResponse(
                success=False,
                latency_ms=(time.time() - start_time) * 1000,
                error=f"Unsupported source type: {request.source_type}"
            )
    
    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            latency_ms=(time.time() - start_time) * 1000,
            error=str(e)
        )


@router.post("/{source_id}/test", response_model=ConnectionTestResponse)
async def test_source_connection(source_id: str) -> ConnectionTestResponse:
    """
    Test connection for an existing data source.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    source = _data_sources[source_id]
    
    return await test_connection(ConnectionTestRequest(
        source_type=source["source_type"],
        connection_config=source["connection_config"]
    ))


@router.get("/{source_id}/schema", response_model=SchemaDiscoveryResponse)
async def discover_schema(source_id: str) -> SchemaDiscoveryResponse:
    """
    Discover schema from a data source.
    
    Samples data from the source and infers the schema structure.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    source = _data_sources[source_id]
    
    # Simulate schema discovery
    # In production, use actual extractors
    schema = {
        "source_type": source["source_type"],
        "fields": [
            {"name": "id", "type": "string", "nullable": False},
            {"name": "content", "type": "string", "nullable": True},
            {"name": "created_at", "type": "datetime", "nullable": False},
            {"name": "metadata", "type": "object", "nullable": True}
        ],
        "estimated_records": 10000
    }
    
    return SchemaDiscoveryResponse(
        source_id=source_id,
        schema=schema,
        discovered_at=datetime.utcnow(),
        sample_count=100
    )


@router.get("/{source_id}/stats", response_model=DataSourceStats)
async def get_source_stats(source_id: str) -> DataSourceStats:
    """
    Get statistics for a data source.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    stats = _source_stats.get(source_id, {
        "source_id": source_id,
        "total_syncs": 0,
        "successful_syncs": 0,
        "failed_syncs": 0,
        "total_records": 0,
        "total_bytes": 0,
        "avg_sync_duration": 0.0,
        "last_sync_at": None,
        "last_error": None
    })
    
    return DataSourceStats(**stats)


@router.post("/{source_id}/enable", response_model=DataSourceResponse)
async def enable_source(source_id: str) -> DataSourceResponse:
    """
    Enable a data source.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    _data_sources[source_id]["enabled"] = True
    _data_sources[source_id]["updated_at"] = datetime.utcnow()
    
    logger.info(f"Enabled data source: {source_id}")
    
    return DataSourceResponse(**_data_sources[source_id])


@router.post("/{source_id}/disable", response_model=DataSourceResponse)
async def disable_source(source_id: str) -> DataSourceResponse:
    """
    Disable a data source.
    """
    if source_id not in _data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {source_id}"
        )
    
    _data_sources[source_id]["enabled"] = False
    _data_sources[source_id]["updated_at"] = datetime.utcnow()
    
    logger.info(f"Disabled data source: {source_id}")
    
    return DataSourceResponse(**_data_sources[source_id])


@router.get("/types/supported")
async def get_supported_types() -> Dict[str, Any]:
    """
    Get list of supported data source types.
    """
    return {
        "types": [
            {
                "type": "database",
                "name": "Database",
                "description": "Relational and NoSQL databases",
                "subtypes": ["postgresql", "mysql", "mongodb", "oracle"]
            },
            {
                "type": "api",
                "name": "API",
                "description": "REST and GraphQL APIs",
                "subtypes": ["rest", "graphql", "webhook"]
            },
            {
                "type": "file",
                "name": "File System",
                "description": "Local and remote file systems",
                "subtypes": ["local", "ftp", "sftp"]
            },
            {
                "type": "cloud_storage",
                "name": "Cloud Storage",
                "description": "Cloud object storage services",
                "subtypes": ["s3", "azure_blob", "gcs"]
            },
            {
                "type": "stream",
                "name": "Stream",
                "description": "Message queues and event streams",
                "subtypes": ["kafka", "rabbitmq", "redis_stream"]
            }
        ]
    }


# Import asyncio for async operations
import asyncio


__all__ = ["router"]
