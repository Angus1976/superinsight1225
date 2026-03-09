"""
Unit tests for Temporary Data Storage API endpoints.

Tests the API endpoints for document upload, parsing, and temporary data management.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.api.temp_data_api import (
    upload_and_parse_document,
    list_temporary_data,
    get_temporary_data,
    delete_temporary_data
)
from src.models.data_lifecycle import (
    TempDataModel, DataState, ReviewStatus
)
from src.services.md_document_parser import (
    MDDocumentParser, StructuredData, Section, Metadata, ValidationResult
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.delete = Mock()
    db.rollback = Mock()
    db.execute = Mock()
    return db


@pytest.fixture
def mock_parser():
    """Mock MD document parser."""
    parser = Mock(spec=MDDocumentParser)
    return parser


@pytest.fixture
def sample_md_content():
    """Sample MD document content."""
    return """# Test Document

## Introduction

This is a test document.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""


@pytest.fixture
def sample_structured_data():
    """Sample structured data."""
    return StructuredData(
        source_document_id=str(uuid4()),
        sections=[
            Section(title="Test Document", content="", level=1, order=0),
            Section(title="Introduction", content="This is a test document.", level=2, order=1),
            Section(title="Section 1", content="Content for section 1.", level=2, order=2),
            Section(title="Section 2", content="Content for section 2.", level=2, order=3)
        ],
        metadata=Metadata(
            title="Test Document",
            author="Test Author",
            tags=["test", "document"]
        ),
        parsed_at=datetime.utcnow(),
        checksum="abc123"
    )


@pytest.fixture
def sample_temp_data():
    """Sample temporary data model."""
    return TempDataModel(
        id=uuid4(),
        source_document_id=str(uuid4()),
        content={
            'sections': [
                {'title': 'Test', 'content': 'Content', 'level': 1, 'order': 0}
            ],
            'checksum': 'abc123',
            'parsed_at': datetime.utcnow().isoformat()
        },
        state=DataState.TEMP_STORED,
        uploaded_by='user123',
        uploaded_at=datetime.utcnow(),
        metadata_={
            'filename': 'test.md',
            'title': 'Test Document',
            'sections_count': 1
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


# ============================================================================
# Test upload_and_parse_document
# ============================================================================

@pytest.mark.asyncio
async def test_upload_document_success(
    mock_db, mock_parser, sample_md_content, sample_structured_data
):
    """Test successful document upload and parsing."""
    # Setup
    file_content = sample_md_content.encode('utf-8')
    file = UploadFile(
        filename="test.md",
        file=BytesIO(file_content)
    )
    
    mock_parser.parse_document.return_value = sample_structured_data
    mock_parser.validate_structure.return_value = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[]
    )
    
    # Mock db.refresh to set the ID
    def refresh_side_effect(obj):
        if not obj.id:
            obj.id = uuid4()
    mock_db.refresh.side_effect = refresh_side_effect
    
    # Execute
    response = await upload_and_parse_document(
        file=file,
        uploaded_by="user123",
        db=mock_db,
        parser=mock_parser
    )
    
    # Verify
    assert response.source_document_id == sample_structured_data.source_document_id
    assert response.state == DataState.TEMP_STORED
    assert response.sections_count == 4
    assert response.metadata['title'] == "Test Document"
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_parser.parse_document.assert_called_once()
    mock_parser.validate_structure.assert_called_once()


@pytest.mark.asyncio
async def test_upload_document_invalid_file_type(mock_db, mock_parser):
    """Test upload with invalid file type."""
    # Setup
    file = UploadFile(
        filename="test.txt",
        file=BytesIO(b"content")
    )
    
    # Execute & Verify
    with pytest.raises(Exception) as exc_info:
        await upload_and_parse_document(
            file=file,
            uploaded_by="user123",
            db=mock_db,
            parser=mock_parser
        )
    
    assert "Only .md files are supported" in str(exc_info.value)
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_upload_document_empty_content(mock_db, mock_parser):
    """Test upload with empty content."""
    # Setup
    file = UploadFile(
        filename="test.md",
        file=BytesIO(b"")
    )
    
    # Execute & Verify
    with pytest.raises(Exception) as exc_info:
        await upload_and_parse_document(
            file=file,
            uploaded_by="user123",
            db=mock_db,
            parser=mock_parser
        )
    
    assert "cannot be empty" in str(exc_info.value)
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_upload_document_parsing_error(
    mock_db, mock_parser, sample_md_content
):
    """Test upload with parsing error."""
    # Setup
    file = UploadFile(
        filename="test.md",
        file=BytesIO(sample_md_content.encode('utf-8'))
    )
    
    mock_parser.parse_document.side_effect = ValueError("Invalid MD format")
    
    # Execute & Verify
    with pytest.raises(Exception) as exc_info:
        await upload_and_parse_document(
            file=file,
            uploaded_by="user123",
            db=mock_db,
            parser=mock_parser
        )
    
    assert "parsing failed" in str(exc_info.value).lower()
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_upload_document_validation_error(
    mock_db, mock_parser, sample_md_content, sample_structured_data
):
    """Test upload with structure validation error."""
    # Setup
    file = UploadFile(
        filename="test.md",
        file=BytesIO(sample_md_content.encode('utf-8'))
    )
    
    mock_parser.parse_document.return_value = sample_structured_data
    mock_parser.validate_structure.return_value = ValidationResult(
        is_valid=False,
        errors=["Invalid section order"],
        warnings=[]
    )
    
    # Execute & Verify
    with pytest.raises(Exception) as exc_info:
        await upload_and_parse_document(
            file=file,
            uploaded_by="user123",
            db=mock_db,
            parser=mock_parser
        )
    
    assert "validation failed" in str(exc_info.value).lower()
    mock_db.add.assert_not_called()


# ============================================================================
# Test list_temporary_data
# ============================================================================

@pytest.mark.asyncio
async def test_list_temporary_data_success(mock_db, sample_temp_data):
    """Test successful listing of temporary data."""
    # Setup
    items = [sample_temp_data]
    
    # Mock execute for items query
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = items
    
    # Mock execute for count query
    mock_count_result = Mock()
    mock_count_result.scalar_one.return_value = 1
    
    mock_db.execute.side_effect = [mock_count_result, mock_result]
    
    # Execute
    response = await list_temporary_data(
        page=1,
        page_size=20,
        db=mock_db
    )
    
    # Verify
    assert response.total == 1
    assert response.page == 1
    assert response.page_size == 20
    assert response.total_pages == 1
    assert len(response.items) == 1
    assert response.items[0].id == sample_temp_data.id
    assert response.items[0].state == DataState.TEMP_STORED


@pytest.mark.asyncio
async def test_list_temporary_data_with_filters(mock_db):
    """Test listing with filters."""
    # Setup
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = []
    
    mock_count_result = Mock()
    mock_count_result.scalar_one.return_value = 0
    
    mock_db.execute.side_effect = [mock_count_result, mock_result]
    
    # Execute
    response = await list_temporary_data(
        page=1,
        page_size=20,
        state=DataState.UNDER_REVIEW,
        uploaded_by="user123",
        review_status=ReviewStatus.PENDING,
        db=mock_db
    )
    
    # Verify
    assert response.total == 0
    assert len(response.items) == 0


@pytest.mark.asyncio
async def test_list_temporary_data_pagination(mock_db, sample_temp_data):
    """Test pagination."""
    # Setup
    items = [sample_temp_data] * 5
    
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = items
    
    mock_count_result = Mock()
    mock_count_result.scalar_one.return_value = 25
    
    mock_db.execute.side_effect = [mock_count_result, mock_result]
    
    # Execute
    response = await list_temporary_data(
        page=2,
        page_size=5,
        db=mock_db
    )
    
    # Verify
    assert response.total == 25
    assert response.page == 2
    assert response.page_size == 5
    assert response.total_pages == 5
    assert len(response.items) == 5


# ============================================================================
# Test get_temporary_data
# ============================================================================

@pytest.mark.asyncio
async def test_get_temporary_data_success(mock_db, sample_temp_data):
    """Test successful retrieval of temporary data."""
    # Setup
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_temp_data
    mock_db.execute.return_value = mock_result
    
    # Execute
    response = await get_temporary_data(
        temp_data_id=sample_temp_data.id,
        db=mock_db
    )
    
    # Verify
    assert response.id == sample_temp_data.id
    assert response.source_document_id == sample_temp_data.source_document_id
    assert response.state == sample_temp_data.state
    assert response.uploaded_by == sample_temp_data.uploaded_by


@pytest.mark.asyncio
async def test_get_temporary_data_not_found(mock_db):
    """Test retrieval of non-existent temporary data."""
    # Setup
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    temp_data_id = uuid4()
    
    # Execute & Verify
    with pytest.raises(Exception) as exc_info:
        await get_temporary_data(
            temp_data_id=temp_data_id,
            db=mock_db
        )
    
    assert "not found" in str(exc_info.value).lower()


# ============================================================================
# Test delete_temporary_data
# ============================================================================

@pytest.mark.asyncio
async def test_delete_temporary_data_success(mock_db, sample_temp_data):
    """Test successful deletion of temporary data."""
    # Setup
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_temp_data
    mock_db.execute.return_value = mock_result
    
    # Execute
    await delete_temporary_data(
        temp_data_id=sample_temp_data.id,
        db=mock_db
    )
    
    # Verify
    mock_db.delete.assert_called_once_with(sample_temp_data)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_temporary_data_not_found(mock_db):
    """Test deletion of non-existent temporary data."""
    # Setup
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    temp_data_id = uuid4()
    
    # Execute & Verify
    with pytest.raises(Exception) as exc_info:
        await delete_temporary_data(
            temp_data_id=temp_data_id,
            db=mock_db
        )
    
    assert "not found" in str(exc_info.value).lower()
    mock_db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_temporary_data_rollback_on_error(mock_db, sample_temp_data):
    """Test rollback on deletion error."""
    # Setup
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_temp_data
    mock_db.execute.return_value = mock_result
    mock_db.commit.side_effect = Exception("Database error")
    
    # Execute & Verify
    with pytest.raises(Exception):
        await delete_temporary_data(
            temp_data_id=sample_temp_data.id,
            db=mock_db
        )
    
    mock_db.rollback.assert_called_once()
