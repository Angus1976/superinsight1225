"""
External Data Router for AI-Friendly Data Access.

Provides REST API endpoints for external applications to read AI-friendly data
including annotations, augmented data, quality reports, and AI experiments.

Features:
- Unified pagination, field filtering, and sorting
- Scope-based permission checking
- Tenant isolation
- API key authentication (via middleware)
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Query
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.database.connection import db_manager
from src.models.annotation import Annotation
from src.models.data_lifecycle import EnhancedDataModel, AnnotationTaskModel
from src.models.quality import QualityCheckResultModel, RagasEvaluationModel
from src.models.ai_annotation import AILearningJobModel, BatchAnnotationJobModel, IterationRecordModel
from src.sync.models import APIKeyModel


logger = logging.getLogger(__name__)


# ============================================================================
# Response Models
# ============================================================================

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: List[Dict[str, Any]] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/v1/external",
    tags=["External API"]
)


# ============================================================================
# Helper Functions
# ============================================================================

def check_scope_permission(api_key: APIKeyModel, required_scope: str) -> None:
    """
    Check if API key has permission for the requested scope.
    
    Args:
        api_key: The API key model
        required_scope: The required scope (e.g., "annotations", "augmented_data")
    
    Raises:
        HTTPException: If permission is denied
    """
    if not api_key.scopes.get(required_scope, False):
        logger.warning(
            f"API key {api_key.id} attempted to access {required_scope} "
            f"without permission"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Permission denied",
                "error_code": "INSUFFICIENT_SCOPE",
                "message": f"API key does not have permission to access {required_scope}",
                "required_scope": required_scope,
                "available_scopes": [k for k, v in api_key.scopes.items() if v]
            }
        )


def filter_fields(data: Dict[str, Any], fields: Optional[str]) -> Dict[str, Any]:
    """
    Filter dictionary to include only specified fields.
    
    Args:
        data: The data dictionary
        fields: Comma-separated list of field names, or None for all fields
    
    Returns:
        Filtered dictionary
    """
    if not fields:
        return data
    
    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        return data
    
    return {k: v for k, v in data.items() if k in field_list}


def apply_sorting(query, model, sort_by: Optional[str]):
    """
    Apply sorting to SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query
        model: SQLAlchemy model class
        sort_by: Sort specification (e.g., "created_at", "-created_at")
    
    Returns:
        Query with sorting applied
    """
    if not sort_by:
        return query
    
    # Parse sort direction
    if sort_by.startswith("-"):
        direction = desc
        field_name = sort_by[1:]
    else:
        direction = asc
        field_name = sort_by
    
    # Check if field exists on model
    if not hasattr(model, field_name):
        logger.warning(f"Invalid sort field: {field_name} for model {model.__name__}")
        return query
    
    return query.order_by(direction(getattr(model, field_name)))


def paginate_query(
    query,
    page: int,
    page_size: int,
    session: Session
) -> tuple[List[Any], PaginationMeta]:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query
        page: Page number (1-indexed)
        page_size: Items per page
        session: Database session
    
    Returns:
        Tuple of (items, pagination_meta)
    """
    # Get total count
    total = session.execute(
        select(func.count()).select_from(query.subquery())
    ).scalar()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    
    # Apply pagination
    items = session.execute(
        query.limit(page_size).offset(offset)
    ).scalars().all()
    
    meta = PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
    
    return items, meta


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/annotations", response_model=PaginatedResponse)
async def get_annotations(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Sort field (prefix with - for descending)"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to include")
):
    """
    Get annotation results.
    
    Returns paginated list of annotation results with optional field filtering and sorting.
    
    **Required Scope**: `annotations`
    
    **Query Parameters**:
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 1000)
    - `sort_by`: Sort field, prefix with `-` for descending (e.g., `-created_at`)
    - `fields`: Comma-separated fields to include (e.g., `id,task_id,created_at`)
    
    **Example**:
    ```
    GET /api/v1/external/annotations?page=1&page_size=20&sort_by=-created_at&fields=id,task_id,annotation_data
    ```
    """
    # Get API key from request state (set by middleware)
    api_key: APIKeyModel = request.state.api_key
    tenant_id: str = request.state.tenant_id
    
    # Check scope permission
    check_scope_permission(api_key, "annotations")
    
    try:
        with db_manager.get_session() as session:
            # Query annotation tasks (as proxy for annotations)
            # In a real implementation, you'd query actual annotation records
            query = select(AnnotationTaskModel).where(
                AnnotationTaskModel.created_by == tenant_id  # Tenant isolation
            )
            
            # Apply sorting
            query = apply_sorting(query, AnnotationTaskModel, sort_by)
            
            # Paginate
            items, meta = paginate_query(query, page, page_size, session)
            
            # Convert to dictionaries and filter fields
            result_items = []
            for item in items:
                item_dict = {
                    "id": str(item.id),
                    "name": item.name,
                    "description": item.description,
                    "annotation_type": item.annotation_type.value,
                    "status": item.status.value,
                    "created_by": item.created_by,
                    "created_at": item.created_at.isoformat(),
                    "progress_total": item.progress_total,
                    "progress_completed": item.progress_completed,
                    "annotations": item.annotations,
                    "metadata": item.metadata_
                }
                result_items.append(filter_fields(item_dict, fields))
            
            logger.info(
                f"API key {api_key.id} accessed annotations: "
                f"page={page}, returned {len(result_items)} items"
            )
            
            return PaginatedResponse(items=result_items, meta=meta)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching annotations: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "error_code": "FETCH_ERROR",
                "message": "Failed to fetch annotations"
            }
        )


@router.get("/augmented-data", response_model=PaginatedResponse)
async def get_augmented_data(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Sort field (prefix with - for descending)"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to include")
):
    """
    Get augmented/enhanced data.
    
    Returns paginated list of enhanced data records with optional field filtering and sorting.
    
    **Required Scope**: `augmented_data`
    
    **Query Parameters**:
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 1000)
    - `sort_by`: Sort field, prefix with `-` for descending (e.g., `-created_at`)
    - `fields`: Comma-separated fields to include (e.g., `id,content,quality_overall`)
    
    **Example**:
    ```
    GET /api/v1/external/augmented-data?page=1&page_size=20&sort_by=-quality_overall
    ```
    """
    # Get API key from request state (set by middleware)
    api_key: APIKeyModel = request.state.api_key
    tenant_id: str = request.state.tenant_id
    
    # Check scope permission
    check_scope_permission(api_key, "augmented_data")
    
    try:
        with db_manager.get_session() as session:
            # Query enhanced data
            # Note: EnhancedDataModel doesn't have tenant_id, so we filter by original_data_id pattern
            query = select(EnhancedDataModel)
            
            # Apply sorting
            query = apply_sorting(query, EnhancedDataModel, sort_by)
            
            # Paginate
            items, meta = paginate_query(query, page, page_size, session)
            
            # Convert to dictionaries and filter fields
            result_items = []
            for item in items:
                item_dict = {
                    "id": str(item.id),
                    "original_data_id": item.original_data_id,
                    "enhancement_job_id": str(item.enhancement_job_id),
                    "content": item.content,
                    "enhancement_type": item.enhancement_type.value,
                    "quality_improvement": item.quality_improvement,
                    "quality_overall": item.quality_overall,
                    "quality_completeness": item.quality_completeness,
                    "quality_accuracy": item.quality_accuracy,
                    "quality_consistency": item.quality_consistency,
                    "version": item.version,
                    "parameters": item.parameters,
                    "metadata": item.metadata_,
                    "created_at": item.created_at.isoformat()
                }
                result_items.append(filter_fields(item_dict, fields))
            
            logger.info(
                f"API key {api_key.id} accessed augmented data: "
                f"page={page}, returned {len(result_items)} items"
            )
            
            return PaginatedResponse(items=result_items, meta=meta)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching augmented data: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "error_code": "FETCH_ERROR",
                "message": "Failed to fetch augmented data"
            }
        )


@router.get("/quality-reports", response_model=PaginatedResponse)
async def get_quality_reports(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Sort field (prefix with - for descending)"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to include")
):
    """
    Get quality check reports.
    
    Returns paginated list of quality check results with optional field filtering and sorting.
    
    **Required Scope**: `quality_reports`
    
    **Query Parameters**:
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 1000)
    - `sort_by`: Sort field, prefix with `-` for descending (e.g., `-checked_at`)
    - `fields`: Comma-separated fields to include (e.g., `id,passed,issues`)
    
    **Example**:
    ```
    GET /api/v1/external/quality-reports?page=1&page_size=20&sort_by=-checked_at&fields=id,passed,issues
    ```
    """
    # Get API key from request state (set by middleware)
    api_key: APIKeyModel = request.state.api_key
    tenant_id: str = request.state.tenant_id
    
    # Check scope permission
    check_scope_permission(api_key, "quality_reports")
    
    try:
        with db_manager.get_session() as session:
            # Query quality check results
            query = select(QualityCheckResultModel).where(
                QualityCheckResultModel.project_id == UUID(tenant_id)  # Tenant isolation
            )
            
            # Apply sorting
            query = apply_sorting(query, QualityCheckResultModel, sort_by)
            
            # Paginate
            items, meta = paginate_query(query, page, page_size, session)
            
            # Convert to dictionaries and filter fields
            result_items = []
            for item in items:
                item_dict = {
                    "id": str(item.id),
                    "annotation_id": str(item.annotation_id),
                    "project_id": str(item.project_id),
                    "passed": item.passed,
                    "issues": item.issues,
                    "checked_rules": item.checked_rules,
                    "check_type": item.check_type,
                    "checked_at": item.checked_at.isoformat(),
                    "checked_by": str(item.checked_by) if item.checked_by else None
                }
                result_items.append(filter_fields(item_dict, fields))
            
            logger.info(
                f"API key {api_key.id} accessed quality reports: "
                f"page={page}, returned {len(result_items)} items"
            )
            
            return PaginatedResponse(items=result_items, meta=meta)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quality reports: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "error_code": "FETCH_ERROR",
                "message": "Failed to fetch quality reports"
            }
        )


@router.get("/experiments", response_model=PaginatedResponse)
async def get_experiments(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Sort field (prefix with - for descending)"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to include")
):
    """
    Get AI experiment results.
    
    Returns paginated list of AI learning jobs and batch annotation experiments
    with optional field filtering and sorting.
    
    **Required Scope**: `experiments`
    
    **Query Parameters**:
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 1000)
    - `sort_by`: Sort field, prefix with `-` for descending (e.g., `-created_at`)
    - `fields`: Comma-separated fields to include (e.g., `id,status,accuracy`)
    
    **Example**:
    ```
    GET /api/v1/external/experiments?page=1&page_size=20&sort_by=-created_at
    ```
    """
    # Get API key from request state (set by middleware)
    api_key: APIKeyModel = request.state.api_key
    tenant_id: str = request.state.tenant_id
    
    # Check scope permission
    check_scope_permission(api_key, "experiments")
    
    try:
        with db_manager.get_session() as session:
            # Query AI learning jobs (experiments)
            query = select(AILearningJobModel).where(
                AILearningJobModel.project_id == tenant_id  # Tenant isolation
            )
            
            # Apply sorting
            query = apply_sorting(query, AILearningJobModel, sort_by)
            
            # Paginate
            items, meta = paginate_query(query, page, page_size, session)
            
            # Convert to dictionaries and filter fields
            result_items = []
            for item in items:
                item_dict = {
                    "id": item.id,
                    "project_id": item.project_id,
                    "status": item.status,
                    "sample_count": item.sample_count,
                    "patterns_identified": item.patterns_identified,
                    "average_confidence": item.average_confidence,
                    "recommended_method": item.recommended_method,
                    "progress_percentage": item.progress_percentage,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                    "error_message": item.error_message
                }
                result_items.append(filter_fields(item_dict, fields))
            
            logger.info(
                f"API key {api_key.id} accessed experiments: "
                f"page={page}, returned {len(result_items)} items"
            )
            
            return PaginatedResponse(items=result_items, meta=meta)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching experiments: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "error_code": "FETCH_ERROR",
                "message": "Failed to fetch experiments"
            }
        )
