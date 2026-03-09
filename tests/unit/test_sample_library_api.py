"""
Unit tests for Sample Library API endpoints.

Tests all sample library API endpoints including add, search, get, update,
delete, and tag-based retrieval operations.

Validates: Requirements 4.1, 4.2, 4.3, 13.1, 13.2, 13.3
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.sample_library_api import router, get_sample_library_manager
from src.models.data_lifecycle import SampleModel


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_manager():
    """Create a mock sample library manager."""
    return Mock()


@pytest.fixture
def client(mock_manager):
    """Create test client with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)
    
    def override_get_manager():
        return mock_manager
    
    app.dependency_overrides[get_sample_library_manager] = override_get_manager
    return TestClient(app)


@pytest.fixture
def sample_data():
    """Sample test data."""
    return {
        "data_id": str(uuid4()),
        "content": {
            "sections": [
                {"title": "Introduction", "content": "Test content"}
            ]
        },
        "category": "technical",
        "quality_overall": 0.85,
        "quality_completeness": 0.9,
        "quality_accuracy": 0.8,
        "quality_consistency": 0.85,
        "tags": ["test", "sample"],
        "metadata": {"source": "test"}
    }


@pytest.fixture
def mock_sample():
    """Create a mock sample model."""
    def _create(
        sample_id=None,
        data_id=None,
        category="technical",
        quality_overall=0.8,
        tags=None,
        created_at=None
    ):
        sample = MagicMock(spec=SampleModel)
        sample.id = sample_id or uuid4()
        sample.data_id = data_id or str(uuid4())
        sample.content = {"test": "content"}
        sample.category = category
        sample.quality_overall = quality_overall
        sample.quality_completeness = 0.8
        sample.quality_accuracy = 0.8
        sample.quality_consistency = 0.8
        sample.version = 1
        sample.tags = tags or []
        sample.usage_count = 0
        sample.last_used_at = None
        sample.metadata_ = {}
        sample.created_at = created_at or datetime.utcnow()
        sample.updated_at = datetime.utcnow()
        return sample
    return _create


# ============================================================================
# POST /api/samples - Add Sample Tests
# ============================================================================

def test_add_sample_success(client, mock_manager, sample_data, mock_sample):
    """Test successfully adding a sample to the library."""
    created_sample = mock_sample(data_id=sample_data["data_id"])
    mock_manager.add_sample.return_value = created_sample
    
    response = client.post("/api/samples", json=sample_data)
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["data_id"] == sample_data["data_id"]
    assert data["category"] == sample_data["category"]
    assert data["version"] == 1
    assert data["usage_count"] == 0
    
    mock_manager.add_sample.assert_called_once()


def test_add_sample_with_defaults(client, mock_manager, mock_sample):
    """Test adding a sample with default quality scores."""
    request_data = {
        "data_id": str(uuid4()),
        "content": {"test": "content"},
        "category": "technical"
    }
    
    created_sample = mock_sample(data_id=request_data["data_id"])
    mock_manager.add_sample.return_value = created_sample
    
    response = client.post("/api/samples", json=request_data)
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["quality_overall"] == 0.8
    assert data["tags"] == []
    assert data["metadata"] == {}


def test_add_sample_invalid_quality_score(client):
    """Test adding a sample with invalid quality score."""
    request_data = {
        "data_id": str(uuid4()),
        "content": {"test": "content"},
        "category": "technical",
        "quality_overall": 1.5  # Invalid: > 1.0
    }
    
    response = client.post("/api/samples", json=request_data)
    
    assert response.status_code == 422  # Validation error


def test_add_sample_missing_required_fields(client):
    """Test adding a sample with missing required fields."""
    request_data = {
        "content": {"test": "content"}
        # Missing data_id and category
    }
    
    response = client.post("/api/samples", json=request_data)
    
    assert response.status_code == 422  # Validation error


def test_add_sample_empty_data_id(client, mock_manager):
    """Test adding a sample with empty data_id."""
    request_data = {
        "data_id": "",
        "content": {"test": "content"},
        "category": "technical"
    }
    
    mock_manager.add_sample.side_effect = ValueError("data_id is required")
    
    response = client.post("/api/samples", json=request_data)
    
    assert response.status_code == 400
    assert "data_id is required" in response.json()["detail"]


# ============================================================================
# GET /api/samples - Search Samples Tests
# ============================================================================

def test_search_samples_no_filters(client, mock_manager, mock_sample):
    """Test searching samples without filters."""
    samples = [mock_sample() for _ in range(3)]
    mock_manager.search_samples.return_value = (samples, 3)
    
    response = client.get("/api/samples")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_search_samples_with_category_filter(client, mock_manager, mock_sample):
    """Test searching samples with category filter."""
    samples = [mock_sample(category="technical") for _ in range(2)]
    mock_manager.search_samples.return_value = (samples, 2)
    
    response = client.get("/api/samples?category=technical")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 2
    assert all(item["category"] == "technical" for item in data["items"])


def test_search_samples_with_tags_filter(client, mock_manager, mock_sample):
    """Test searching samples with tags filter."""
    sample = mock_sample(tags=["python", "api"])
    mock_manager.search_samples.return_value = ([sample], 1)
    
    response = client.get("/api/samples?tags=python,api")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 1
    assert "python" in data["items"][0]["tags"]
    assert "api" in data["items"][0]["tags"]


def test_search_samples_with_quality_range(client, mock_manager, mock_sample):
    """Test searching samples with quality score range."""
    sample = mock_sample(quality_overall=0.8)
    mock_manager.search_samples.return_value = ([sample], 1)
    
    response = client.get("/api/samples?quality_min=0.75&quality_max=0.85")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 1
    assert data["items"][0]["quality_overall"] == 0.8


def test_search_samples_pagination(client, mock_manager, mock_sample):
    """Test searching samples with pagination."""
    samples = [mock_sample() for _ in range(10)]
    mock_manager.search_samples.return_value = (samples, 25)
    
    response = client.get("/api/samples?page=1&page_size=10")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["total_pages"] == 3


def test_search_samples_invalid_quality_range(client):
    """Test searching with invalid quality range."""
    response = client.get("/api/samples?quality_min=0.9&quality_max=0.5")
    
    assert response.status_code == 400
    assert "quality_min cannot be greater than quality_max" in response.json()["detail"]


# ============================================================================
# GET /api/samples/{sample_id} - Get Sample Tests
# ============================================================================

def test_get_sample_success(client, mock_manager, mock_sample):
    """Test successfully getting a sample by ID."""
    sample = mock_sample()
    mock_manager.get_sample.return_value = sample
    mock_manager.track_usage.return_value = None
    
    response = client.get(f"/api/samples/{sample.id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == str(sample.id)
    assert data["category"] == sample.category
    
    mock_manager.track_usage.assert_called_once_with(str(sample.id))


def test_get_sample_not_found(client, mock_manager):
    """Test getting a non-existent sample."""
    non_existent_id = uuid4()
    mock_manager.get_sample.return_value = None
    
    response = client.get(f"/api/samples/{non_existent_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# PUT /api/samples/{sample_id} - Update Sample Tests
# ============================================================================

def test_update_sample_category(client, mock_manager, mock_sample):
    """Test updating a sample's category."""
    sample = mock_sample(category="business")
    mock_manager.update_sample.return_value = sample
    
    update_data = {"category": "business"}
    response = client.put(f"/api/samples/{sample.id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["category"] == "business"


def test_update_sample_tags(client, mock_manager, mock_sample):
    """Test updating a sample's tags."""
    sample = mock_sample(tags=["new", "tags", "updated"])
    mock_manager.update_sample.return_value = sample
    
    update_data = {"tags": ["new", "tags", "updated"]}
    response = client.put(f"/api/samples/{sample.id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["tags"] == ["new", "tags", "updated"]


def test_update_sample_not_found(client, mock_manager):
    """Test updating a non-existent sample."""
    non_existent_id = uuid4()
    mock_manager.update_sample.side_effect = ValueError(f"Sample {non_existent_id} not found")
    
    update_data = {"category": "updated"}
    response = client.put(f"/api/samples/{non_existent_id}", json=update_data)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_sample_no_fields(client):
    """Test updating a sample with no fields."""
    sample_id = uuid4()
    
    update_data = {}
    response = client.put(f"/api/samples/{sample_id}", json=update_data)
    
    assert response.status_code == 400
    assert "No fields to update" in response.json()["detail"]


# ============================================================================
# DELETE /api/samples/{sample_id} - Delete Sample Tests
# ============================================================================

def test_delete_sample_success(client, mock_manager):
    """Test successfully deleting a sample."""
    sample_id = uuid4()
    mock_manager.delete_sample.return_value = None
    
    response = client.delete(f"/api/samples/{sample_id}")
    
    assert response.status_code == 204
    mock_manager.delete_sample.assert_called_once_with(str(sample_id))


def test_delete_sample_not_found(client, mock_manager):
    """Test deleting a non-existent sample."""
    non_existent_id = uuid4()
    mock_manager.delete_sample.side_effect = ValueError(f"Sample {non_existent_id} not found")
    
    response = client.delete(f"/api/samples/{non_existent_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# GET /api/samples/tags/{tag} - Get Samples by Tag Tests
# ============================================================================

def test_get_samples_by_tag_success(client, mock_manager, mock_sample):
    """Test getting samples by a specific tag."""
    samples = [mock_sample(tags=["python"]) for _ in range(2)]
    mock_manager.get_samples_by_tag.return_value = samples
    
    response = client.get("/api/samples/tags/python")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert all("python" in item["tags"] for item in data)


def test_get_samples_by_tag_no_matches(client, mock_manager):
    """Test getting samples by a tag with no matches."""
    mock_manager.get_samples_by_tag.return_value = []
    
    response = client.get("/api/samples/tags/ruby")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 0


def test_get_samples_by_tag_empty_tag(client):
    """Test getting samples with empty tag."""
    response = client.get("/api/samples/tags/ ")
    
    assert response.status_code == 400
    assert "Tag cannot be empty" in response.json()["detail"]


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_sample_lifecycle(client, mock_manager, sample_data, mock_sample):
    """Test complete sample lifecycle: create, get, update, delete."""
    # Create sample
    created_sample = mock_sample(data_id=sample_data["data_id"])
    mock_manager.add_sample.return_value = created_sample
    
    create_response = client.post("/api/samples", json=sample_data)
    assert create_response.status_code == 201
    sample_id = create_response.json()["id"]
    
    # Get sample
    mock_manager.get_sample.return_value = created_sample
    mock_manager.track_usage.return_value = None
    
    get_response = client.get(f"/api/samples/{sample_id}")
    assert get_response.status_code == 200
    
    # Update sample
    updated_sample = mock_sample(data_id=sample_data["data_id"], category="updated")
    mock_manager.update_sample.return_value = updated_sample
    
    update_data = {"category": "updated"}
    update_response = client.put(f"/api/samples/{sample_id}", json=update_data)
    assert update_response.status_code == 200
    
    # Delete sample
    mock_manager.delete_sample.return_value = None
    
    delete_response = client.delete(f"/api/samples/{sample_id}")
    assert delete_response.status_code == 204
