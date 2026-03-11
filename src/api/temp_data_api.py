"""
Temporary Data Storage API Router for Data Lifecycle Management.

Provides REST API endpoints for managing temporary data storage,
including document upload, parsing, and temporary data CRUD operations.

Validates: Requirements 1.3, 12.1, 12.2
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select, func

from src.database.connection import get_db_session
from src.models.data_lifecycle import (
    TempDataModel, DataState, ReviewStatus, TempData
)
from src.services.md_document_parser import (
    MDDocumentParser, MDDocument, StructuredData
)


router = APIRouter(prefix="/api/documents", tags=["Temporary Data Storage"])
temp_data_router = APIRouter(prefix="/api/temp-data", tags=["Temporary Data"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class UploadDocumentRequest(BaseModel):
    """Upload document request."""
    filename: str = Field(..., description="Original filename")
    uploaded_by: str = Field(..., description="User ID who uploaded")


class UploadDocumentResponse(BaseModel):
    """Upload document response."""
    temp_data_id: UUID = Field(..., description="Temporary data ID")
    source_document_id: str = Field(..., description="Source document ID")
    state: DataState = Field(..., description="Current data state")
    sections_count: int = Field(..., description="Number of sections parsed")
    metadata: Dict[str, Any] = Field(..., description="Extracted metadata")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class CreateTempDataRequest(BaseModel):
    """Create temp data request."""
    name: str = Field(..., description="Data name")
    content: Dict[str, Any] = Field(..., description="Data content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class CreateTempDataResponse(BaseModel):
    """Create temp data response."""
    id: UUID = Field(..., description="Temporary data ID")
    name: str = Field(..., description="Data name")
    state: DataState = Field(..., description="Current data state")
    created_at: datetime = Field(..., description="Creation timestamp")


class TempDataResponse(BaseModel):
    """Temporary data response."""
    id: UUID
    source_document_id: str
    content: Dict[str, Any]
    state: DataState
    uploaded_by: str
    uploaded_at: datetime
    review_status: Optional[ReviewStatus]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TempDataListResponse(BaseModel):
    """Temporary data list response."""
    items: List[TempDataResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Dependency Injection
# ============================================================================

def get_md_parser() -> MDDocumentParser:
    """Get MD document parser instance."""
    return MDDocumentParser()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/upload", response_model=UploadDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_parse_document(
    file: UploadFile = File(..., description="MD document file to upload"),
    uploaded_by: str = Form(..., description="User ID who uploaded"),
    db: DBSession = Depends(get_db_session),
    parser: MDDocumentParser = Depends(get_md_parser)
):
    """
    Upload and parse MD document.
    
    Accepts an MD document file, parses it into structured data,
    and stores it in the temporary table.
    
    Validates: Requirements 1.3, 12.1
    
    Args:
        file: MD document file
        uploaded_by: User ID who uploaded the document
        db: Database session
        parser: MD document parser
    
    Returns:
        UploadDocumentResponse with temp data ID and parsing results
    
    Raises:
        HTTPException 400: If file is invalid or parsing fails
        HTTPException 500: If storage fails
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith('.md'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .md files are supported"
            )
        
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        if not content_str.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document content cannot be empty"
            )
        
        # Create MD document
        md_document = MDDocument(
            content=content_str,
            filename=file.filename,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow()
        )
        
        # Parse document
        try:
            structured_data = parser.parse_document(md_document)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document parsing failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected parsing error: {str(e)}"
            )
        
        # Validate structure
        validation_result = parser.validate_structure(structured_data)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Structure validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Store in temporary table
        temp_data = TempDataModel(
            source_document_id=structured_data.source_document_id,
            content={
                'sections': [s.model_dump() for s in structured_data.sections],
                'checksum': structured_data.checksum,
                'parsed_at': structured_data.parsed_at.isoformat()
            },
            state=DataState.TEMP_STORED,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            metadata_={
                'filename': file.filename,
                'title': structured_data.metadata.title,
                'author': structured_data.metadata.author,
                'tags': structured_data.metadata.tags,
                'description': structured_data.metadata.description,
                'language': structured_data.metadata.language,
                'sections_count': len(structured_data.sections),
                'validation_warnings': validation_result.warnings
            }
        )
        
        db.add(temp_data)
        db.commit()
        db.refresh(temp_data)
        
        return UploadDocumentResponse(
            temp_data_id=temp_data.id,
            source_document_id=temp_data.source_document_id,
            state=temp_data.state,
            sections_count=len(structured_data.sections),
            metadata=temp_data.metadata_,
            uploaded_at=temp_data.uploaded_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store document: {str(e)}"
        )
@temp_data_router.post("", response_model=CreateTempDataResponse, status_code=status.HTTP_201_CREATED)
async def create_temp_data(
    request: CreateTempDataRequest,
    db: DBSession = Depends(get_db_session)
):
    """
    Create temporary data directly from JSON.

    Accepts JSON data and stores it in the temporary table.

    Args:
        request: Create temp data request
        db: Database session

    Returns:
        CreateTempDataResponse with temp data ID

    Raises:
        HTTPException 400: If request is invalid
        HTTPException 500: If storage fails
    """
    try:
        # Create temp data
        temp_data = TempDataModel(
            source_document_id=request.name,  # Use name as source_document_id
            content=request.content,
            state=DataState.TEMP_STORED,
            uploaded_by="system",  # TODO: Get from auth context
            uploaded_at=datetime.utcnow(),
            metadata_=request.metadata or {}
        )

        db.add(temp_data)
        db.commit()
        db.refresh(temp_data)

        return CreateTempDataResponse(
            id=temp_data.id,
            name=request.name,
            state=temp_data.state,
            created_at=temp_data.created_at
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create temp data: {str(e)}"
        )


@temp_data_router.get("", response_model=TempDataListResponse)
async def list_temporary_data(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    state: Optional[DataState] = Query(None, description="Filter by state"),
    uploaded_by: Optional[str] = Query(None, description="Filter by uploader"),
    review_status: Optional[ReviewStatus] = Query(None, description="Filter by review status"),
    db: DBSession = Depends(get_db_session)
):
    """
    List temporary data with pagination and filtering.
    
    Validates: Requirements 12.1, 12.2
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        state: Optional state filter
        uploaded_by: Optional uploader filter
        review_status: Optional review status filter
        db: Database session
    
    Returns:
        TempDataListResponse with paginated results
    """
    try:
        # Build query
        query = select(TempDataModel)
        
        # Apply filters
        if state:
            query = query.where(TempDataModel.state == state)
        if uploaded_by:
            query = query.where(TempDataModel.uploaded_by == uploaded_by)
        if review_status:
            query = query.where(TempDataModel.review_status == review_status)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar_one()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(TempDataModel.created_at.desc())
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = db.execute(query)
        items = result.scalars().all()
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        # Convert to response models
        response_items = [
            TempDataResponse(
                id=item.id,
                source_document_id=item.source_document_id,
                content=item.content,
                state=item.state,
                uploaded_by=item.uploaded_by,
                uploaded_at=item.uploaded_at,
                review_status=item.review_status,
                reviewed_by=item.reviewed_by,
                reviewed_at=item.reviewed_at,
                rejection_reason=item.rejection_reason,
                metadata=item.metadata_,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            for item in items
        ]
        
        return TempDataListResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list temporary data: {str(e)}"
        )


@temp_data_router.get("/{temp_data_id}", response_model=TempDataResponse)
async def get_temporary_data(
    temp_data_id: UUID,
    db: DBSession = Depends(get_db_session)
):
    """
    Get specific temporary data by ID.
    
    Validates: Requirements 12.1
    
    Args:
        temp_data_id: Temporary data ID
        db: Database session
    
    Returns:
        TempDataResponse with data details
    
    Raises:
        HTTPException 404: If temp data not found
    """
    try:
        # Query temp data
        query = select(TempDataModel).where(TempDataModel.id == temp_data_id)
        result = db.execute(query)
        temp_data = result.scalar_one_or_none()
        
        if not temp_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporary data with ID {temp_data_id} not found"
            )
        
        return TempDataResponse(
            id=temp_data.id,
            source_document_id=temp_data.source_document_id,
            content=temp_data.content,
            state=temp_data.state,
            uploaded_by=temp_data.uploaded_by,
            uploaded_at=temp_data.uploaded_at,
            review_status=temp_data.review_status,
            reviewed_by=temp_data.reviewed_by,
            reviewed_at=temp_data.reviewed_at,
            rejection_reason=temp_data.rejection_reason,
            metadata=temp_data.metadata_,
            created_at=temp_data.created_at,
            updated_at=temp_data.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get temporary data: {str(e)}"
        )


@temp_data_router.delete("/{temp_data_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_temporary_data(
    temp_data_id: UUID,
    db: DBSession = Depends(get_db_session)
):
    """
    Delete temporary data by ID.
    
    Validates: Requirements 12.2
    
    Args:
        temp_data_id: Temporary data ID
        db: Database session
    
    Raises:
        HTTPException 404: If temp data not found
        HTTPException 500: If deletion fails
    """
    try:
        # Query temp data
        query = select(TempDataModel).where(TempDataModel.id == temp_data_id)
        result = db.execute(query)
        temp_data = result.scalar_one_or_none()
        
        if not temp_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporary data with ID {temp_data_id} not found"
            )
        
        # Delete temp data
        db.delete(temp_data)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete temporary data: {str(e)}"
        )
