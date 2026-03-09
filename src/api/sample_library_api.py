"""
Sample Library API Router for Data Lifecycle Management.

Provides REST API endpoints for managing the sample library,
including adding samples, searching with filters, and managing sample metadata.

Validates: Requirements 4.1, 4.2, 4.3, 13.1, 13.2, 13.3
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session as DBSession

from src.database.connection import get_db_session
from src.services.sample_library_manager import (
    SampleLibraryManager, SearchCriteria
)


router = APIRouter(prefix="/api/samples", tags=["Sample Library"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class AddSampleRequest(BaseModel):
    """Add sample to library request."""
    data_id: str = Field(..., description="ID of the source data")
    content: Dict[str, Any] = Field(..., description="Sample content (structured data)")
    category: str = Field(..., description="Sample category")
    quality_overall: float = Field(0.8, ge=0.0, le=1.0, description="Overall quality score")
    quality_completeness: float = Field(0.8, ge=0.0, le=1.0, description="Completeness quality score")
    quality_accuracy: float = Field(0.8, ge=0.0, le=1.0, description="Accuracy quality score")
    quality_consistency: float = Field(0.8, ge=0.0, le=1.0, description="Consistency quality score")
    tags: Optional[List[str]] = Field(None, description="List of tags for categorization")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SampleResponse(BaseModel):
    """Sample response."""
    id: UUID = Field(..., description="Sample ID")
    data_id: str = Field(..., description="Source data ID")
    content: Dict[str, Any] = Field(..., description="Sample content")
    category: str = Field(..., description="Sample category")
    quality_overall: float = Field(..., description="Overall quality score")
    quality_completeness: float = Field(..., description="Completeness quality score")
    quality_accuracy: float = Field(..., description="Accuracy quality score")
    quality_consistency: float = Field(..., description="Consistency quality score")
    version: int = Field(..., description="Sample version")
    tags: List[str] = Field(..., description="Sample tags")
    usage_count: int = Field(..., description="Number of times sample was used")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SearchSamplesResponse(BaseModel):
    """Search samples response."""
    items: List[SampleResponse] = Field(..., description="List of matching samples")
    total: int = Field(..., description="Total number of matching samples")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class UpdateSampleRequest(BaseModel):
    """Update sample request."""
    category: Optional[str] = Field(None, description="Updated category")
    tags: Optional[List[str]] = Field(None, description="Updated tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    quality_overall: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated overall quality")
    quality_completeness: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated completeness quality")
    quality_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated accuracy quality")
    quality_consistency: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated consistency quality")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_sample_library_manager(db: DBSession = Depends(get_db_session)) -> SampleLibraryManager:
    """Get sample library manager instance."""
    return SampleLibraryManager(db)


# ============================================================================
# Helper Functions
# ============================================================================

def _sample_model_to_response(sample) -> SampleResponse:
    """Convert SampleModel to SampleResponse."""
    return SampleResponse(
        id=sample.id,
        data_id=sample.data_id,
        content=sample.content,
        category=sample.category,
        quality_overall=sample.quality_overall,
        quality_completeness=sample.quality_completeness,
        quality_accuracy=sample.quality_accuracy,
        quality_consistency=sample.quality_consistency,
        version=sample.version,
        tags=sample.tags,
        usage_count=sample.usage_count,
        last_used_at=sample.last_used_at,
        metadata=sample.metadata_,
        created_at=sample.created_at,
        updated_at=sample.updated_at
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
async def add_sample(
    request: AddSampleRequest,
    manager: SampleLibraryManager = Depends(get_sample_library_manager)
):
    """
    Add a new sample to the library.
    
    Creates a new sample entry in the sample library with quality scores,
    tags, and metadata for categorization and search.
    
    Validates: Requirements 4.1, 13.1
    
    Args:
        request: Add sample request with content, category, quality scores, tags, and metadata
        manager: Sample library manager instance
    
    Returns:
        SampleResponse with created sample details
    
    Raises:
        HTTPException 400: If validation fails or required fields missing
        HTTPException 500: If sample creation fails
    """
    try:
        sample = manager.add_sample(
            data_id=request.data_id,
            content=request.content,
            category=request.category,
            quality_overall=request.quality_overall,
            quality_completeness=request.quality_completeness,
            quality_accuracy=request.quality_accuracy,
            quality_consistency=request.quality_consistency,
            tags=request.tags,
            metadata=request.metadata
        )
        
        return _sample_model_to_response(sample)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add sample: {str(e)}"
        )


@router.get("", response_model=SearchSamplesResponse)
async def search_samples(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags (sample must have ALL tags)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    quality_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum quality score"),
    quality_max: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum quality score"),
    date_from: Optional[datetime] = Query(None, description="Filter samples created from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter samples created until this date"),
    manager: SampleLibraryManager = Depends(get_sample_library_manager)
):
    """
    Search samples with filters and pagination.
    
    Supports filtering by tags, category, quality score range, and date range.
    Returns paginated results with total count.
    
    Validates: Requirements 4.2, 4.3, 13.2
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        tags: Comma-separated list of tags (sample must have ALL tags)
        category: Filter by category
        quality_min: Minimum quality score
        quality_max: Maximum quality score
        date_from: Filter samples created from this date
        date_to: Filter samples created until this date
        manager: Sample library manager instance
    
    Returns:
        SearchSamplesResponse with paginated results
    
    Raises:
        HTTPException 400: If invalid filter parameters
        HTTPException 500: If search fails
    """
    try:
        # Parse tags
        tags_list = None
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Validate quality range
        if quality_min is not None and quality_max is not None:
            if quality_min > quality_max:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="quality_min cannot be greater than quality_max"
                )
        
        # Validate date range
        if date_from and date_to:
            if date_from > date_to:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="date_from cannot be after date_to"
                )
        
        # Create search criteria
        criteria = SearchCriteria(
            tags=tags_list,
            category=category,
            quality_min=quality_min,
            quality_max=quality_max,
            date_from=date_from,
            date_to=date_to,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        
        # Execute search
        samples, total = manager.search_samples(criteria)
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # Convert to response models
        response_items = [_sample_model_to_response(sample) for sample in samples]
        
        return SearchSamplesResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search samples: {str(e)}"
        )


@router.get("/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: UUID,
    manager: SampleLibraryManager = Depends(get_sample_library_manager)
):
    """
    Get a specific sample by ID.
    
    Retrieves detailed information about a sample including its content,
    quality scores, tags, and usage statistics.
    
    Validates: Requirements 4.1, 13.1
    
    Args:
        sample_id: Sample ID
        manager: Sample library manager instance
    
    Returns:
        SampleResponse with sample details
    
    Raises:
        HTTPException 404: If sample not found
        HTTPException 500: If retrieval fails
    """
    try:
        sample = manager.get_sample(str(sample_id))
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample with ID {sample_id} not found"
            )
        
        # Track usage
        manager.track_usage(str(sample_id))
        
        return _sample_model_to_response(sample)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sample: {str(e)}"
        )


@router.put("/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: UUID,
    request: UpdateSampleRequest,
    manager: SampleLibraryManager = Depends(get_sample_library_manager)
):
    """
    Update a sample's metadata, tags, or quality scores.
    
    Allows updating sample category, tags, metadata, and quality scores.
    Content cannot be updated to maintain data integrity.
    
    Validates: Requirements 4.1, 13.3
    
    Args:
        sample_id: Sample ID
        request: Update sample request with fields to update
        manager: Sample library manager instance
    
    Returns:
        SampleResponse with updated sample details
    
    Raises:
        HTTPException 400: If validation fails or invalid updates
        HTTPException 404: If sample not found
        HTTPException 500: If update fails
    """
    try:
        # Build updates dictionary (only include non-None fields)
        updates = {}
        if request.category is not None:
            updates['category'] = request.category
        if request.tags is not None:
            updates['tags'] = request.tags
        if request.metadata is not None:
            updates['metadata_'] = request.metadata
        if request.quality_overall is not None:
            updates['quality_overall'] = request.quality_overall
        if request.quality_completeness is not None:
            updates['quality_completeness'] = request.quality_completeness
        if request.quality_accuracy is not None:
            updates['quality_accuracy'] = request.quality_accuracy
        if request.quality_consistency is not None:
            updates['quality_consistency'] = request.quality_consistency
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        sample = manager.update_sample(str(sample_id), updates)
        
        return _sample_model_to_response(sample)
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sample: {str(e)}"
        )


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    sample_id: UUID,
    manager: SampleLibraryManager = Depends(get_sample_library_manager)
):
    """
    Delete a sample from the library.
    
    Permanently removes a sample from the sample library.
    This operation cannot be undone.
    
    Validates: Requirements 4.1, 13.3
    
    Args:
        sample_id: Sample ID
        manager: Sample library manager instance
    
    Raises:
        HTTPException 404: If sample not found
        HTTPException 500: If deletion fails
    """
    try:
        manager.delete_sample(str(sample_id))
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sample: {str(e)}"
        )


@router.get("/tags/{tag}", response_model=List[SampleResponse])
async def get_samples_by_tag(
    tag: str,
    manager: SampleLibraryManager = Depends(get_sample_library_manager)
):
    """
    Get samples by a specific tag.
    
    Returns all samples that have the specified tag.
    For multiple tags, use the search endpoint with tags parameter.
    
    Validates: Requirements 4.3, 13.2
    
    Args:
        tag: Tag to search for
        manager: Sample library manager instance
    
    Returns:
        List of SampleResponse with matching samples
    
    Raises:
        HTTPException 400: If tag is empty
        HTTPException 500: If search fails
    """
    try:
        if not tag.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag cannot be empty"
            )
        
        samples = manager.get_samples_by_tag([tag])
        
        return [_sample_model_to_response(sample) for sample in samples]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get samples by tag: {str(e)}"
        )
