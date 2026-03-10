"""
Enhancement API Router for Data Lifecycle Management.

Provides REST API endpoints for managing enhancement jobs,
including job creation, status tracking, applying enhancements,
rollback, cancellation, and listing with filters.

Validates: Requirements 6.1, 6.2, 6.3, 6.5, 15.1, 15.3
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import logging

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, Response
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from src.database.connection import get_db_session
from src.services.enhancement_service import (
    EnhancementService,
    EnhancementConfig,
)
from src.models.data_lifecycle import EnhancementType, JobStatus
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord,
)
from src.services.data_transfer_service import DataTransferService, User
from src.models.data_lifecycle import EnhancedDataModel


router = APIRouter(prefix="/api/enhancements", tags=["Enhancements"])
logger = logging.getLogger(__name__)

# Shared in-memory job storage across requests (service instances are per-request)
_shared_jobs: Dict[str, Any] = {}


# ============================================================================
# Custom Exception with Headers
# ============================================================================

class DeprecatedEndpointException(HTTPException):
    """HTTPException that preserves deprecation headers."""
    
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)
        self.headers = {
            "X-Deprecated-Endpoint": "true",
            "X-New-Endpoint": "/api/data-lifecycle/transfer",
            "X-Deprecation-Date": "2026-06-10",
            "X-Deprecation-Info": "https://docs.example.com/migration/data-transfer"
        }


# ============================================================================
# Deprecation Header Helper
# ============================================================================

def _add_deprecation_headers(response: Response) -> None:
    """Add deprecation headers to response."""
    response.headers["X-Deprecated-Endpoint"] = "true"
    response.headers["X-New-Endpoint"] = "/api/data-lifecycle/transfer"
    response.headers["X-Deprecation-Date"] = "2026-06-10"
    response.headers["X-Deprecation-Info"] = "https://docs.example.com/migration/data-transfer"


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CreateEnhancementRequest(BaseModel):
    """Create enhancement job request."""
    data_id: str = Field(..., min_length=1, description="ID of data to enhance")
    enhancement_type: EnhancementType = Field(..., description="Type of enhancement")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Enhancement parameters")
    target_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Target quality (0-1)")
    created_by: str = Field(..., min_length=1, description="User ID who creates the job")


class EnhancementJobResponse(BaseModel):
    """Enhancement job response."""
    id: str = Field(..., description="Job ID")
    data_id: str = Field(..., description="Source data ID")
    enhancement_type: EnhancementType = Field(..., description="Enhancement type")
    parameters: Dict[str, Any] = Field(..., description="Enhancement parameters")
    target_quality: Optional[float] = Field(None, description="Target quality score")
    status: JobStatus = Field(..., description="Job status")
    created_by: str = Field(..., description="Creator user ID")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    enhanced_data_id: Optional[str] = Field(None, description="ID of enhanced data")


class ApplyEnhancementRequest(BaseModel):
    """Apply enhancement request."""
    source_content: Dict[str, Any] = Field(..., description="Source content to enhance")


class EnhancedDataResponse(BaseModel):
    """Enhanced data response."""
    id: str = Field(..., description="Enhanced data ID")
    original_data_id: str = Field(..., description="Original data ID")
    enhancement_job_id: str = Field(..., description="Enhancement job ID")
    content: Dict[str, Any] = Field(..., description="Enhanced content")
    enhancement_type: str = Field(..., description="Enhancement type")
    quality_improvement: float = Field(..., description="Quality improvement score")
    quality_overall: float = Field(..., description="Overall quality score")
    quality_completeness: float = Field(..., description="Completeness score")
    quality_accuracy: float = Field(..., description="Accuracy score")
    quality_consistency: float = Field(..., description="Consistency score")
    version: int = Field(..., description="Version number")
    parameters: Dict[str, Any] = Field(..., description="Parameters used")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")


class ListEnhancementsResponse(BaseModel):
    """List enhancement jobs response."""
    items: List[EnhancementJobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


async def _convert_to_new_api(
    job_id: str,
    user_id: str,
    service: EnhancementService,
    db: DBSession
) -> Dict[str, Any]:
    """
    Convert old add-to-library request to new unified data transfer API.
    
    This function bridges the old endpoint to the new unified API, ensuring
    consistency and reducing code duplication.
    
    Args:
        job_id: Enhancement job ID
        user_id: User performing the operation
        service: Enhancement service instance
        db: Database session
        
    Returns:
        Dictionary matching AddToLibraryResponse format
        
    Raises:
        ValueError: If job not found, not completed, or validation fails
    """
    # Validate job exists and is completed
    job = service._jobs.get(job_id)
    if not job:
        raise ValueError(f"Enhancement job {job_id} not found")
    if job.status != JobStatus.COMPLETED:
        raise ValueError(
            f"Cannot add to library: job is {job.status.value}, expected completed"
        )
    if not job.enhanced_data_id:
        raise ValueError("No enhanced data available for this job")
    
    # Retrieve enhanced data from database
    enhanced_record = db.query(EnhancedDataModel).filter(
        EnhancedDataModel.id == UUID(job.enhanced_data_id)
    ).first()
    if not enhanced_record:
        raise ValueError(
            f"Enhanced data {job.enhanced_data_id} not found in database"
        )
    
    # Build transfer request in new format
    transfer_request = DataTransferRequest(
        source_type="augmentation",
        source_id=job_id,
        target_state="in_sample_library",
        data_attributes=DataAttributes(
            category="enhanced",
            tags=["enhanced", enhanced_record.enhancement_type.value],
            quality_score=enhanced_record.quality_overall,
            description=f"Enhanced data from job {job_id}"
        ),
        records=[
            TransferRecord(
                id=str(enhanced_record.id),
                content=enhanced_record.content,
                metadata={
                    "original_data_id": enhanced_record.original_data_id,
                    "enhancement_job_id": str(enhanced_record.enhancement_job_id),
                    "enhancement_type": enhanced_record.enhancement_type.value,
                    "augmentation_method": enhanced_record.enhancement_type.value,
                    "augmentation_params": job.config.parameters,
                    "target_quality": job.config.target_quality,
                }
            )
        ]
    )
    
    # Create mock user for transfer service
    mock_user = User(id=user_id, role="admin")
    
    # Call new unified transfer API
    transfer_service = DataTransferService(db)
    result = await transfer_service.transfer(transfer_request, mock_user)
    
    # Convert new API response back to old format
    if result.get("approval_required"):
        raise ValueError(
            "Transfer requires approval. Please use the new API endpoint "
            "POST /api/data-lifecycle/transfer for approval workflow support."
        )
    
    # Map to old response format
    return {
        "id": result["lifecycle_ids"][0],
        "data_id": str(enhanced_record.id),
        "content": enhanced_record.content,
        "category": "enhanced",
        "quality_overall": enhanced_record.quality_overall,
        "quality_completeness": enhanced_record.quality_completeness,
        "quality_accuracy": enhanced_record.quality_accuracy,
        "quality_consistency": enhanced_record.quality_consistency,
        "version": 1,
        "tags": ["enhanced", enhanced_record.enhancement_type.value],
        "metadata": {
            "original_data_id": enhanced_record.original_data_id,
            "enhancement_job_id": str(enhanced_record.enhancement_job_id),
            "enhancement_type": enhanced_record.enhancement_type.value,
            "augmentation_method": enhanced_record.enhancement_type.value,
            "augmentation_params": job.config.parameters,
            "target_quality": job.config.target_quality,
            "transferred_by": user_id,
        },
        "created_at": datetime.utcnow().isoformat(),
    }


class AddToLibraryRequest(BaseModel):
    """Request to add enhanced data to sample library."""
    user_id: str = Field(..., min_length=1, description="User ID performing the operation")


class AddToLibraryResponse(BaseModel):
    """Response after adding enhanced data to sample library."""
    id: str = Field(..., description="New sample ID")
    data_id: str = Field(..., description="Source enhanced data ID")
    content: Dict[str, Any] = Field(..., description="Sample content")
    category: str = Field(..., description="Sample category")
    quality_overall: float = Field(..., description="Overall quality score")
    quality_completeness: float = Field(..., description="Completeness score")
    quality_accuracy: float = Field(..., description="Accuracy score")
    quality_consistency: float = Field(..., description="Consistency score")
    version: int = Field(..., description="Version number")
    tags: List[str] = Field(..., description="Sample tags")
    metadata: Dict[str, Any] = Field(..., description="Sample metadata")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")



# ============================================================================
# Dependency Injection
# ============================================================================

def get_enhancement_service(
    db: DBSession = Depends(get_db_session),
) -> EnhancementService:
    """Get enhancement service instance with shared job storage."""
    service = EnhancementService(db)
    service._jobs = _shared_jobs
    return service


# ============================================================================
# Helper Functions
# ============================================================================

def _job_to_response(job) -> EnhancementJobResponse:
    """Convert EnhancementJob to response model."""
    return EnhancementJobResponse(
        id=job.id,
        data_id=job.config.data_id,
        enhancement_type=job.config.enhancement_type,
        parameters=job.config.parameters,
        target_quality=job.config.target_quality,
        status=job.status,
        created_by=job.created_by,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        enhanced_data_id=job.enhanced_data_id,
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=EnhancementJobResponse, status_code=status.HTTP_201_CREATED)
async def create_enhancement_job(
    request: CreateEnhancementRequest,
    service: EnhancementService = Depends(get_enhancement_service),
):
    """
    Create a new enhancement job.

    Validates: Requirements 6.1, 15.1
    """
    try:
        config = EnhancementConfig(
            data_id=request.data_id,
            enhancement_type=request.enhancement_type,
            parameters=request.parameters or {},
            target_quality=request.target_quality,
        )
        job = service.create_enhancement_job(
            config=config, created_by=request.created_by
        )
        return _job_to_response(job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create enhancement job: {str(e)}",
        )


@router.get("/{job_id}", response_model=EnhancementJobResponse)
async def get_enhancement_job(
    job_id: str,
    service: EnhancementService = Depends(get_enhancement_service),
):
    """
    Get enhancement job status and details.

    Validates: Requirements 6.2, 15.1
    """
    try:
        job = service._jobs.get(job_id)
        if not job:
            raise ValueError(f"Enhancement job {job_id} not found")
        return _job_to_response(job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get enhancement job: {str(e)}",
        )


@router.post("/{job_id}/apply", response_model=EnhancedDataResponse)
async def apply_enhancement(
    job_id: str,
    request: ApplyEnhancementRequest,
    service: EnhancementService = Depends(get_enhancement_service),
):
    """
    Apply enhancement algorithm to source content.

    Validates: Requirements 6.2, 6.3
    """
    try:
        result = service.apply_enhancement(
            job_id=job_id, source_content=request.source_content
        )
        return EnhancedDataResponse(
            id=result["id"],
            original_data_id=result["original_data_id"],
            enhancement_job_id=result["enhancement_job_id"],
            content=result["content"],
            enhancement_type=result["enhancement_type"],
            quality_improvement=result["quality_improvement"],
            quality_overall=result["quality_overall"],
            quality_completeness=result["quality_completeness"],
            quality_accuracy=result["quality_accuracy"],
            quality_consistency=result["quality_consistency"],
            version=result["version"],
            parameters=result["parameters"],
            metadata=result["metadata"],
            created_at=datetime.fromisoformat(result["created_at"]),
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply enhancement: {str(e)}",
        )


@router.post("/{job_id}/rollback", status_code=status.HTTP_200_OK)
async def rollback_enhancement(
    job_id: str,
    service: EnhancementService = Depends(get_enhancement_service),
):
    """
    Rollback an enhancement, restoring original data.

    Validates: Requirements 6.5
    """
    try:
        service.rollback_enhancement(job_id=job_id)
        return {
            "message": "Enhancement rolled back successfully",
            "job_id": job_id,
        }
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback enhancement: {str(e)}",
        )


@router.post("/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_enhancement_job(
    job_id: str,
    service: EnhancementService = Depends(get_enhancement_service),
):
    """
    Cancel a running or queued enhancement job.

    Validates: Requirements 15.3
    """
    try:
        job = service._jobs.get(job_id)
        if not job:
            raise ValueError(f"Enhancement job {job_id} not found")
        if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
            raise ValueError(
                f"Cannot cancel job in {job.status.value} status. "
                f"Only QUEUED or RUNNING jobs can be cancelled."
            )
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        return {
            "message": "Enhancement job cancelled successfully",
            "job_id": job_id,
        }
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel enhancement job: {str(e)}",
        )


@router.post(
    "/{job_id}/add-to-library",
    response_model=AddToLibraryResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def add_to_library(
    job_id: str,
    request: AddToLibraryRequest,
    response: Response,
    service: EnhancementService = Depends(get_enhancement_service),
    db: DBSession = Depends(get_db_session),
):
    """
    Add enhanced data to the sample library for iterative optimization.

    **DEPRECATED**: This endpoint is deprecated and will be removed after 2026-06-10.
    Please use POST /api/data-lifecycle/transfer instead.
    
    The new unified data transfer API provides:
    - Consistent interface across all data sources
    - Enhanced permission control
    - Approval workflow support
    - Complete internationalization
    
    Migration guide: See documentation at /docs/migration/data-transfer

    Validates: Requirements 21.1
    
    **Implementation Note**: This endpoint now internally calls the new unified
    data transfer API to ensure consistency and reduce code duplication.
    """
    # Add deprecation headers to response (will be present on all responses)
    _add_deprecation_headers(response)
    
    # Log deprecation warning
    logger.warning(
        f"DEPRECATED ENDPOINT USED: /api/enhancements/{job_id}/add-to-library "
        f"by user {request.user_id}. This endpoint will be removed after 2026-06-10. "
        f"Please migrate to POST /api/data-lifecycle/transfer"
    )
    
    try:
        # Convert old request to new unified format
        result = await _convert_to_new_api(
            job_id=job_id,
            user_id=request.user_id,
            service=service,
            db=db
        )
        return AddToLibraryResponse(**result)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise DeprecatedEndpointException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise DeprecatedEndpointException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise DeprecatedEndpointException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add enhanced data to library: {str(e)}",
        )


@router.get("", response_model=ListEnhancementsResponse)
async def list_enhancement_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[JobStatus] = Query(None, description="Filter by job status"),
    enhancement_type: Optional[EnhancementType] = Query(None, description="Filter by enhancement type"),
    data_id: Optional[str] = Query(None, description="Filter by source data ID"),
    service: EnhancementService = Depends(get_enhancement_service),
):
    """
    List enhancement jobs with pagination and filters.

    Validates: Requirements 15.1, 15.5
    """
    try:
        all_jobs = list(service._jobs.values())

        # Apply filters
        if status_filter is not None:
            all_jobs = [j for j in all_jobs if j.status == status_filter]
        if enhancement_type is not None:
            all_jobs = [
                j for j in all_jobs
                if j.config.enhancement_type == enhancement_type
            ]
        if data_id is not None:
            all_jobs = [j for j in all_jobs if j.config.data_id == data_id]

        # Sort by started_at descending (newest first)
        all_jobs.sort(
            key=lambda j: j.started_at or datetime.min, reverse=True
        )

        total = len(all_jobs)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        offset = (page - 1) * page_size
        page_items = all_jobs[offset : offset + page_size]

        return ListEnhancementsResponse(
            items=[_job_to_response(j) for j in page_items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list enhancement jobs: {str(e)}",
        )
