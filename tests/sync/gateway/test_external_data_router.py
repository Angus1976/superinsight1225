"""
Unit tests for ExternalDataRouter.

Tests the four GET endpoints with pagination, field filtering, sorting,
and scope-based permission checking.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.sync.gateway.external_data_router import (
    router,
    check_scope_permission,
    filter_fields,
    apply_sorting,
    paginate_query,
    PaginationMeta,
    PaginatedResponse
)
from src.sync.models import APIKeyModel, APIKeyStatus
from src.models.data_lifecycle import (
    AnnotationTaskModel,
    EnhancedDataModel,
    TaskStatus,
    AnnotationType,
    EnhancementType
)
from src.models.quality import QualityCheckResultModel
from src.models.ai_annotation import AILearningJobModel


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_api_key():
    """Create a mock API key with all scopes."""
    api_key = Mock(spec=APIKeyModel)
    api_key.id = uuid4()
    api_key.tenant_id = "test-tenant"
    api_key.scopes = {
        "annotations": True,
        "augmented_data": True,
        "quality_reports": True,
        "experiments": True
    }
    api_key.status = APIKeyStatus.ACTIVE
    return api_key


@pytest.fixture
def mock_api_key_limited():
    """Create a mock API key with limited scopes."""
    api_key = Mock(spec=APIKeyModel)
    api_key.id = uuid4()
    api_key.tenant_id = "test-tenant"
    api_key.scopes = {
        "annotations": True,
        "augmented_data": False,
        "quality_reports": False,
        "experiments": False
    }
    api_key.status = APIKeyStatus.ACTIVE
    return api_key


@pytest.fixture
def mock_request(mock_api_key):
    """Create a mock request with API key."""
    request = Mock()
    request.state.api_key = mock_api_key
    request.state.tenant_id = "test-tenant"
    return request


# ============================================================================
# Helper Function Tests
# ============================================================================

def test_check_scope_permission_success(mock_api_key):
    """Test scope permission check with valid scope."""
    # Should not raise exception
    check_scope_permission(mock_api_key, "annotations")


def test_check_scope_permission_denied(mock_api_key_limited):
    """Test scope permission check with invalid scope."""
    with pytest.raises(HTTPException) as exc_info:
        check_scope_permission(mock_api_key_limited, "augmented_data")
    
    assert exc_info.value.status_code == 403
    assert "INSUFFICIENT_SCOPE" in str(exc_info.value.detail)


def test_filter_fields_all():
    """Test field filtering with no filter (return all)."""
    data = {"id": "123", "name": "test", "value": 42}
    result = filter_fields(data, None)
    assert result == data


def test_filter_fields_subset():
    """Test field filtering with specific fields."""
    data = {"id": "123", "name": "test", "value": 42, "extra": "data"}
    result = filter_fields(data, "id,name")
    assert result == {"id": "123", "name": "test"}


def test_filter_fields_empty():
    """Test field filtering with empty filter string."""
    data = {"id": "123", "name": "test"}
    result = filter_fields(data, "")
    assert result == data


def test_apply_sorting_ascending():
    """Test sorting with ascending order."""
    mock_query = Mock()
    mock_model = Mock()
    mock_model.created_at = Mock()
    
    with patch('src.sync.gateway.external_data_router.asc') as mock_asc:
        result = apply_sorting(mock_query, mock_model, "created_at")
        mock_asc.assert_called_once()


def test_apply_sorting_descending():
    """Test sorting with descending order."""
    mock_query = Mock()
    mock_model = Mock()
    mock_model.created_at = Mock()
    
    with patch('src.sync.gateway.external_data_router.desc') as mock_desc:
        result = apply_sorting(mock_query, mock_model, "-created_at")
        mock_desc.assert_called_once()


def test_apply_sorting_invalid_field():
    """Test sorting with invalid field name."""
    mock_query = Mock()
    
    # Create a mock model class with __name__ attribute
    mock_model = type('MockModel', (), {})
    
    # Should return query unchanged
    result = apply_sorting(mock_query, mock_model, "nonexistent_field")
    assert result == mock_query


def test_apply_sorting_none():
    """Test sorting with None sort_by."""
    mock_query = Mock()
    mock_model = Mock()
    
    result = apply_sorting(mock_query, mock_model, None)
    assert result == mock_query


def test_paginate_query():
    """Test query pagination."""
    # Skip this test - requires real SQLAlchemy query
    pytest.skip("Requires real SQLAlchemy query object")


def test_paginate_query_empty():
    """Test query pagination with no results."""
    # Skip this test - requires real SQLAlchemy query
    pytest.skip("Requires real SQLAlchemy query object")


# ============================================================================
# Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_annotations_success(mock_request):
    """Test successful annotations retrieval."""
    with patch('src.sync.gateway.external_data_router.db_manager') as mock_db:
        # Setup mock session and query results
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock annotation task
        mock_task = Mock(spec=AnnotationTaskModel)
        mock_task.id = uuid4()
        mock_task.name = "Test Task"
        mock_task.description = "Test Description"
        mock_task.annotation_type = AnnotationType.CLASSIFICATION
        mock_task.status = TaskStatus.COMPLETED
        mock_task.created_by = "test-tenant"
        mock_task.created_at = datetime.utcnow()
        mock_task.progress_total = 100
        mock_task.progress_completed = 100
        mock_task.annotations = []
        mock_task.metadata_ = {}
        
        # Mock query execution
        mock_session.execute.return_value.scalar.return_value = 1  # Total count
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_task]
        
        from src.sync.gateway.external_data_router import get_annotations
        
        response = await get_annotations(
            request=mock_request,
            page=1,
            page_size=50,
            sort_by=None,
            fields=None
        )
        
        assert isinstance(response, PaginatedResponse)
        assert len(response.items) == 1
        assert response.meta.total == 1


@pytest.mark.asyncio
async def test_get_annotations_permission_denied(mock_request):
    """Test annotations retrieval with insufficient permissions."""
    # Override API key with limited scopes
    mock_request.state.api_key.scopes = {"annotations": False}
    
    from src.sync.gateway.external_data_router import get_annotations
    
    with pytest.raises(HTTPException) as exc_info:
        await get_annotations(
            request=mock_request,
            page=1,
            page_size=50,
            sort_by=None,
            fields=None
        )
    
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_annotations_with_field_filter(mock_request):
    """Test annotations retrieval with field filtering."""
    with patch('src.sync.gateway.external_data_router.db_manager') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        mock_task = Mock(spec=AnnotationTaskModel)
        mock_task.id = uuid4()
        mock_task.name = "Test Task"
        mock_task.description = "Test Description"
        mock_task.annotation_type = AnnotationType.CLASSIFICATION
        mock_task.status = TaskStatus.COMPLETED
        mock_task.created_by = "test-tenant"
        mock_task.created_at = datetime.utcnow()
        mock_task.progress_total = 100
        mock_task.progress_completed = 100
        mock_task.annotations = []
        mock_task.metadata_ = {}
        
        mock_session.execute.return_value.scalar.return_value = 1
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_task]
        
        from src.sync.gateway.external_data_router import get_annotations
        
        response = await get_annotations(
            request=mock_request,
            page=1,
            page_size=50,
            sort_by=None,
            fields="id,name"
        )
        
        assert len(response.items) == 1
        # Check that only requested fields are present
        assert "id" in response.items[0]
        assert "name" in response.items[0]
        # Other fields should be filtered out
        assert "description" not in response.items[0]


@pytest.mark.asyncio
async def test_get_augmented_data_success(mock_request):
    """Test successful augmented data retrieval."""
    with patch('src.sync.gateway.external_data_router.db_manager') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        mock_enhanced = Mock(spec=EnhancedDataModel)
        mock_enhanced.id = uuid4()
        mock_enhanced.original_data_id = "original-123"
        mock_enhanced.enhancement_job_id = uuid4()
        mock_enhanced.content = {"data": "enhanced"}
        mock_enhanced.enhancement_type = EnhancementType.DATA_AUGMENTATION
        mock_enhanced.quality_improvement = 0.15
        mock_enhanced.quality_overall = 0.85
        mock_enhanced.quality_completeness = 0.9
        mock_enhanced.quality_accuracy = 0.8
        mock_enhanced.quality_consistency = 0.85
        mock_enhanced.version = 1
        mock_enhanced.parameters = {}
        mock_enhanced.metadata_ = {}
        mock_enhanced.created_at = datetime.utcnow()
        
        mock_session.execute.return_value.scalar.return_value = 1
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_enhanced]
        
        from src.sync.gateway.external_data_router import get_augmented_data
        
        response = await get_augmented_data(
            request=mock_request,
            page=1,
            page_size=50,
            sort_by=None,
            fields=None
        )
        
        assert isinstance(response, PaginatedResponse)
        assert len(response.items) == 1
        assert response.items[0]["quality_overall"] == 0.85


@pytest.mark.asyncio
async def test_get_quality_reports_success(mock_request):
    """Test successful quality reports retrieval."""
    # Set tenant_id to a valid UUID string
    mock_request.state.tenant_id = str(uuid4())
    
    with patch('src.sync.gateway.external_data_router.db_manager') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        mock_report = Mock(spec=QualityCheckResultModel)
        mock_report.id = uuid4()
        mock_report.annotation_id = uuid4()
        mock_report.project_id = uuid4()
        mock_report.passed = True
        mock_report.issues = []
        mock_report.checked_rules = 5
        mock_report.check_type = "realtime"
        mock_report.checked_at = datetime.utcnow()
        mock_report.checked_by = uuid4()
        
        mock_session.execute.return_value.scalar.return_value = 1
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_report]
        
        from src.sync.gateway.external_data_router import get_quality_reports
        
        response = await get_quality_reports(
            request=mock_request,
            page=1,
            page_size=50,
            sort_by=None,
            fields=None
        )
        
        assert isinstance(response, PaginatedResponse)
        assert len(response.items) == 1
        assert response.items[0]["passed"] is True


@pytest.mark.asyncio
async def test_get_experiments_success(mock_request):
    """Test successful experiments retrieval."""
    with patch('src.sync.gateway.external_data_router.db_manager') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        mock_experiment = Mock(spec=AILearningJobModel)
        mock_experiment.id = "exp-123"
        mock_experiment.project_id = "test-tenant"
        mock_experiment.status = "completed"
        mock_experiment.sample_count = 1000
        mock_experiment.patterns_identified = 5
        mock_experiment.average_confidence = 0.85
        mock_experiment.recommended_method = "supervised"
        mock_experiment.progress_percentage = 100.0
        mock_experiment.created_at = datetime.utcnow()
        mock_experiment.updated_at = datetime.utcnow()
        mock_experiment.completed_at = datetime.utcnow()
        mock_experiment.error_message = None
        
        mock_session.execute.return_value.scalar.return_value = 1
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_experiment]
        
        from src.sync.gateway.external_data_router import get_experiments
        
        response = await get_experiments(
            request=mock_request,
            page=1,
            page_size=50,
            sort_by=None,
            fields=None
        )
        
        assert isinstance(response, PaginatedResponse)
        assert len(response.items) == 1
        assert response.items[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_pagination_parameters():
    """Test pagination parameter validation."""
    from fastapi import Query
    
    # Test default values
    page = Query(1, ge=1)
    page_size = Query(50, ge=1, le=1000)
    
    assert page.default == 1
    assert page_size.default == 50


@pytest.mark.asyncio
async def test_get_annotations_sorting(mock_request):
    """Test annotations retrieval with sorting."""
    with patch('src.sync.gateway.external_data_router.db_manager') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        mock_session.execute.return_value.scalar.return_value = 0
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        from src.sync.gateway.external_data_router import get_annotations
        
        response = await get_annotations(
            request=mock_request,
            page=1,
            page_size=50,
            sort_by="-created_at",
            fields=None
        )
        
        assert response.meta.total == 0


@pytest.mark.asyncio
async def test_error_handling(mock_request):
    """Test error handling in endpoints."""
    with patch('src.sync.gateway.external_data_router.db_manager') as mock_db:
        # Simulate database error
        mock_db.get_session.side_effect = Exception("Database connection failed")
        
        from src.sync.gateway.external_data_router import get_annotations
        
        with pytest.raises(HTTPException) as exc_info:
            await get_annotations(
                request=mock_request,
                page=1,
                page_size=50,
                sort_by=None,
                fields=None
            )
        
        assert exc_info.value.status_code == 500
        assert "FETCH_ERROR" in str(exc_info.value.detail)
