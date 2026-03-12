"""
API Router for External API Key Management.

Provides REST endpoints for managing API keys used by external applications
to access SuperInsight AI-friendly data.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.sync.gateway.api_key_service import APIKeyService, APIKeyConfig
from src.sync.models import APIKeyStatus, APICallLogModel
from src.database.connection import db_manager
from src.api.auth import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sync/api-keys", tags=["API Key Management"])


# Request/Response Models

class CreateAPIKeyRequest(BaseModel):
    """Request model for creating an API key."""
    name: str = Field(..., description="API key name")
    description: Optional[str] = Field(None, description="API key description")
    scopes: Dict[str, bool] = Field(..., description="Access scopes")
    expires_in_days: Optional[int] = Field(None, description="Expiration in days")
    rate_limit_per_minute: int = Field(60, description="Rate limit per minute")
    rate_limit_per_day: int = Field(10000, description="Rate limit per day")


class APIKeyResponse(BaseModel):
    """Response model for API key information."""
    id: str
    name: str
    key_prefix: str
    raw_key: Optional[str] = None
    scopes: Dict[str, bool]
    status: str
    rate_limit_per_minute: int
    rate_limit_per_day: int
    expires_at: Optional[str] = None
    created_at: str
    last_used_at: Optional[str] = None
    total_calls: int


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics."""
    key_id: str
    total_calls: int
    calls_by_date: List[Dict[str, Any]]
    calls_by_endpoint: List[Dict[str, Any]]


class TestAPIRequest(BaseModel):
    """Request model for testing API endpoints."""
    endpoint: str = Field(..., description="API endpoint to test")
    api_key: str = Field(..., description="API key to use")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")


# Dependency: Get database session
def get_db() -> Session:
    """Get database session."""
    with db_manager.get_session() as session:
        yield session


# Dependency: Get tenant ID from current user
def get_tenant_id(current_user: Dict = Depends(get_current_user)) -> str:
    """Extract tenant ID from current user."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have a tenant ID"
        )
    return tenant_id


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key.
    
    The raw API key is only returned once in this response.
    Store it securely as it cannot be retrieved later.
    """
    try:
        service = APIKeyService(session=db)
        
        config = APIKeyConfig(
            name=request.name,
            tenant_id=tenant_id,
            scopes=request.scopes,
            description=request.description,
            expires_in_days=request.expires_in_days,
            rate_limit_per_minute=request.rate_limit_per_minute,
            rate_limit_per_day=request.rate_limit_per_day,
            created_by=current_user.get("user_id")
        )
        
        response = service.create_key(config)
        
        return APIKeyResponse(**response.to_dict())
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current tenant.
    
    Raw keys are never returned in list responses.
    """
    try:
        service = APIKeyService(session=db)
        
        # Parse status filter
        status_enum = None
        if status_filter:
            try:
                status_enum = APIKeyStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}"
                )
        
        keys = service.list_keys(tenant_id=tenant_id, status=status_enum)
        
        return [APIKeyResponse(**key.to_dict()) for key in keys]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific API key.
    
    Raw key is never returned after creation.
    """
    try:
        service = APIKeyService(session=db)
        key = service.get_key(key_id=key_id, tenant_id=tenant_id)
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return APIKeyResponse(**key.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API key"
        )


@router.post("/{key_id}/enable", status_code=status.HTTP_200_OK)
async def enable_api_key(
    key_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """Enable a disabled API key."""
    try:
        service = APIKeyService(session=db)
        success = service.enable_key(key_id=key_id, tenant_id=tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or cannot be enabled"
            )
        
        return {"message": "API key enabled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable API key"
        )


@router.post("/{key_id}/disable", status_code=status.HTTP_200_OK)
async def disable_api_key(
    key_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """Disable an active API key."""
    try:
        service = APIKeyService(session=db)
        success = service.disable_key(key_id=key_id, tenant_id=tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or cannot be disabled"
            )
        
        return {"message": "API key disabled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable API key"
        )


@router.post("/{key_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_api_key(
    key_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key (terminal operation).
    
    Revoked keys cannot be re-enabled.
    """
    try:
        service = APIKeyService(session=db)
        success = service.revoke_key(key_id=key_id, tenant_id=tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return {"message": "API key revoked successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.get("/{key_id}/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    key_id: UUID,
    period: str = Query("day", description="Period: day, week, or month"),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics for an API key.
    
    Returns call counts grouped by date and endpoint.
    """
    try:
        # Verify key belongs to tenant
        service = APIKeyService(session=db)
        key = service.get_key(key_id=key_id, tenant_id=tenant_id)
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Query call logs
        from sqlalchemy import func, desc
        from datetime import timedelta
        
        # Calculate date range based on period
        now = datetime.utcnow()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period. Use: day, week, or month"
            )
        
        # Calls by date
        calls_by_date = db.query(
            func.date(APICallLogModel.called_at).label("date"),
            func.count(APICallLogModel.id).label("count")
        ).filter(
            APICallLogModel.key_id == key_id,
            APICallLogModel.called_at >= start_date
        ).group_by(
            func.date(APICallLogModel.called_at)
        ).order_by(
            func.date(APICallLogModel.called_at)
        ).all()
        
        # Calls by endpoint
        calls_by_endpoint = db.query(
            APICallLogModel.endpoint,
            func.count(APICallLogModel.id).label("count")
        ).filter(
            APICallLogModel.key_id == key_id,
            APICallLogModel.called_at >= start_date
        ).group_by(
            APICallLogModel.endpoint
        ).order_by(
            desc(func.count(APICallLogModel.id))
        ).limit(10).all()
        
        return UsageStatsResponse(
            key_id=str(key_id),
            total_calls=key.total_calls or 0,
            calls_by_date=[
                {"date": str(row.date), "count": row.count}
                for row in calls_by_date
            ],
            calls_by_endpoint=[
                {"endpoint": row.endpoint, "count": row.count}
                for row in calls_by_endpoint
            ]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage statistics"
        )
