"""
FastAPI router for AI Integration data access endpoints.

Provides thin wrappers around existing export APIs for OpenClaw integration.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.ai_integration.data_bridge import OpenClawDataBridge
from src.ai_integration.auth import JWTTokenService, TokenClaims
from src.ai_integration.authorization import (
    AuthorizationService,
    PermissionDeniedError,
    CrossTenantAccessError
)
from src.export.service import ExportService
from src.sync.pipeline.ai_exporter import AIFriendlyExporter

router = APIRouter(prefix="/api/v1/ai-integration/data", tags=["ai-integration-data"])

# Initialize services (will be properly injected in production)
jwt_service = JWTTokenService()


# Request/Response Models
class DataQueryRequest(BaseModel):
    """Request model for data query."""
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)


class DataQueryResponse(BaseModel):
    """Response model for data query."""
    data: Dict[str, Any]
    total_records: int
    page: int
    page_size: int


class ExportForSkillRequest(BaseModel):
    """Request model for skill export."""
    data_query: Dict[str, Any]
    format: str = Field(default="json", pattern="^(json|csv|jsonl|coco|pascal_voc)$")
    include_semantics: bool = True
    desensitize: bool = False


class QualityMetricsResponse(BaseModel):
    """Response model for quality metrics."""
    dataset_id: str
    overall_score: float
    metrics: Dict[str, float]
    sample_size: int
    issues: List[str]
    recommendations: List[str]


# Dependency: Extract and validate JWT token
async def get_current_gateway(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> TokenClaims:
    """
    Extract and validate JWT token from Authorization header.
    
    Args:
        authorization: Authorization header (Bearer token)
        db: Database session
        
    Returns:
        TokenClaims with gateway and tenant information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        claims = jwt_service.validate_token(token)
        return claims
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(e)}"
        )


# Dependency: Get data bridge
def get_data_bridge(db: Session = Depends(get_db)) -> OpenClawDataBridge:
    """Get OpenClawDataBridge instance."""
    export_service = ExportService()
    ai_exporter = AIFriendlyExporter(db)
    return OpenClawDataBridge(export_service, ai_exporter)


# Dependency: Get authorization service
def get_auth_service(db: Session = Depends(get_db)) -> AuthorizationService:
    """Get AuthorizationService instance."""
    return AuthorizationService(db)


@router.get("/query", response_model=DataQueryResponse)
async def query_governed_data(
    filters: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    claims: TokenClaims = Depends(get_current_gateway),
    data_bridge: OpenClawDataBridge = Depends(get_data_bridge),
    auth_service: AuthorizationService = Depends(get_auth_service)
):
    """
    Query governed data with authentication and tenant filtering.
    
    Wraps existing export API with authentication and authorization.
    
    Args:
        filters: JSON string of filter parameters
        page: Page number for pagination
        page_size: Number of records per page
        claims: JWT token claims (injected)
        data_bridge: Data bridge instance (injected)
        auth_service: Authorization service (injected)
        
    Returns:
        DataQueryResponse with governed data
        
    Validates: Requirements 3.3, 3.4, 3.5, 11.1
    """
    # Check permission
    if not auth_service.check_permission(
        claims.gateway_id, "data", "read"
    ):
        raise HTTPException(
            status_code=403,
            detail="Gateway does not have permission to read data"
        )
    
    # Parse filters
    import json
    filter_dict = json.loads(filters) if filters else {}
    
    # Add pagination to filters
    filter_dict["page"] = page
    filter_dict["page_size"] = page_size
    
    # Query data with tenant filtering
    try:
        result = await data_bridge.query_governed_data(
            gateway_id=claims.gateway_id,
            tenant_id=claims.tenant_id,
            filters=filter_dict
        )
        
        return DataQueryResponse(
            data=result,
            total_records=result.get("total_records", 0),
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query data: {str(e)}"
        )


@router.post("/export-for-skill")
async def export_for_skill(
    request: ExportForSkillRequest,
    claims: TokenClaims = Depends(get_current_gateway),
    data_bridge: OpenClawDataBridge = Depends(get_data_bridge),
    auth_service: AuthorizationService = Depends(get_auth_service)
):
    """
    Export data in format suitable for OpenClaw skill.
    
    Wraps AIFriendlyExporter with authentication and authorization.
    
    Args:
        request: Export request parameters
        claims: JWT token claims (injected)
        data_bridge: Data bridge instance (injected)
        auth_service: Authorization service (injected)
        
    Returns:
        Exported data as bytes
        
    Validates: Requirements 3.3, 11.1
    """
    # Check permission
    if not auth_service.check_permission(
        claims.gateway_id, "data", "read"
    ):
        raise HTTPException(
            status_code=403,
            detail="Gateway does not have permission to export data"
        )
    
    # Export data
    try:
        # Add tenant filtering to data query
        request.data_query["tenant_id"] = claims.tenant_id
        request.data_query["include_semantics"] = request.include_semantics
        request.data_query["desensitize"] = request.desensitize
        
        exported_data = await data_bridge.export_for_skill(
            gateway_id=claims.gateway_id,
            data_query=request.data_query,
            format=request.format
        )
        
        return {
            "format": request.format,
            "size": len(exported_data),
            "data": exported_data.decode("utf-8") if request.format == "json" else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export data: {str(e)}"
        )


@router.get("/quality-metrics", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    dataset_id: str = Query(...),
    sample_size: int = Query(1000, ge=100, le=10000),
    claims: TokenClaims = Depends(get_current_gateway),
    data_bridge: OpenClawDataBridge = Depends(get_data_bridge),
    auth_service: AuthorizationService = Depends(get_auth_service)
):
    """
    Get quality metrics for a dataset.
    
    Wraps dataset quality API with authentication and authorization.
    
    Args:
        dataset_id: Dataset ID to get metrics for
        sample_size: Sample size for quality assessment
        claims: JWT token claims (injected)
        data_bridge: Data bridge instance (injected)
        auth_service: Authorization service (injected)
        
    Returns:
        QualityMetricsResponse with quality metrics
        
    Validates: Requirements 3.3
    """
    # Check permission
    if not auth_service.check_permission(
        claims.gateway_id, "data", "read"
    ):
        raise HTTPException(
            status_code=403,
            detail="Gateway does not have permission to read quality metrics"
        )
    
    # Get quality metrics
    try:
        metrics = await data_bridge.get_quality_metrics(
            gateway_id=claims.gateway_id,
            dataset_id=dataset_id,
            sample_size=sample_size
        )
        
        return QualityMetricsResponse(**metrics)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quality metrics: {str(e)}"
        )
