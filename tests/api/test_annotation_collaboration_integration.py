"""
Integration tests for AI Annotation Collaboration API.

Tests the full API integration including:
- Request/response flow
- Error handling
- Rate limiting
- WebSocket connections
- Data validation
"""

import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app
try:
    from src.app import app
except ImportError:
    from app import app


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Task Management Endpoint Tests
# =============================================================================

class TestTaskManagement:
    """Test task management endpoints."""

    def test_list_tasks_default(self, client):
        """Test listing tasks with default parameters."""
        response = client.get("/api/v1/annotation/tasks")

        assert response.status_code == 200
        data = response.json()

        assert "tasks" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["tasks"], list)

    def test_list_tasks_with_filters(self, client):
        """Test listing tasks with filters."""
        response = client.get(
            "/api/v1/annotation/tasks",
            params={
                "project_id": "test_project",
                "status": "in_progress",
                "page": 1,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_tasks_pagination(self, client):
        """Test task pagination."""
        # Page 1
        response1 = client.get(
            "/api/v1/annotation/tasks",
            params={"page": 1, "page_size": 5},
        )
        assert response1.status_code == 200

        # Page 2
        response2 = client.get(
            "/api/v1/annotation/tasks",
            params={"page": 2, "page_size": 5},
        )
        assert response2.status_code == 200

    def test_list_tasks_invalid_page(self, client):
        """Test listing tasks with invalid page number."""
        response = client.get(
            "/api/v1/annotation/tasks",
            params={"page": 0},
        )

        # Should return validation error
        assert response.status_code in [400, 422]


# =============================================================================
# Metrics Endpoint Tests
# =============================================================================

class TestMetrics:
    """Test metrics endpoints."""

    def test_get_ai_metrics(self, client):
        """Test getting AI metrics."""
        response = client.get("/api/v1/annotation/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check all required fields
        assert "total_annotations" in data
        assert "human_annotations" in data
        assert "ai_pre_annotations" in data
        assert "ai_suggestions" in data
        assert "ai_acceptance_rate" in data
        assert "time_saved_hours" in data
        assert "quality_score" in data

        # Check data types
        assert isinstance(data["total_annotations"], int)
        assert isinstance(data["ai_acceptance_rate"], float)
        assert 0 <= data["ai_acceptance_rate"] <= 1

    def test_get_ai_metrics_with_project(self, client):
        """Test getting AI metrics filtered by project."""
        response = client.get(
            "/api/v1/annotation/metrics",
            params={"project_id": "test_project"},
        )

        assert response.status_code == 200

    def test_get_quality_metrics(self, client):
        """Test getting quality metrics."""
        response = client.get(
            "/api/v1/annotation/quality-metrics",
            params={"project_id": "test_project"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "overview" in data
        assert "accuracy_trend" in data
        assert "confidence_distribution" in data
        assert "engine_performance" in data
        assert "degradation_alerts" in data

        # Check overview data
        assert "ai_accuracy" in data["overview"]
        assert "agreement_rate" in data["overview"]
        assert "total_samples" in data["overview"]
        assert "active_alerts" in data["overview"]

        # Check accuracy trend is a list
        assert isinstance(data["accuracy_trend"], list)
        if len(data["accuracy_trend"]) > 0:
            trend_point = data["accuracy_trend"][0]
            assert "date" in trend_point
            assert "ai_accuracy" in trend_point
            assert "human_accuracy" in trend_point

    def test_get_quality_metrics_missing_project(self, client):
        """Test getting quality metrics without project ID."""
        response = client.get("/api/v1/annotation/quality-metrics")

        # Should return validation error (project_id is required)
        assert response.status_code in [400, 422]


# =============================================================================
# Routing Configuration Tests
# =============================================================================

class TestRoutingConfiguration:
    """Test routing configuration endpoints."""

    def test_get_routing_config(self, client):
        """Test getting routing configuration."""
        response = client.get("/api/v1/annotation/routing/config")

        assert response.status_code == 200
        data = response.json()

        assert "config" in data
        assert "status" in data
        assert "message" in data

        config = data["config"]
        assert "low_confidence_threshold" in config
        assert "high_confidence_threshold" in config
        assert "auto_assign_high_confidence" in config
        assert "skill_based_routing" in config
        assert "workload_balancing" in config

    def test_update_routing_config_valid(self, client):
        """Test updating routing configuration with valid data."""
        response = client.put(
            "/api/v1/annotation/routing/config",
            json={
                "low_confidence_threshold": 0.5,
                "high_confidence_threshold": 0.9,
                "auto_assign_high_confidence": True,
                "skill_based_routing": True,
                "workload_balancing": True,
                "review_levels": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "config" in data

    def test_update_routing_config_invalid_thresholds(self, client):
        """Test updating routing config with invalid thresholds."""
        response = client.put(
            "/api/v1/annotation/routing/config",
            json={
                "low_confidence_threshold": 0.9,  # Higher than high threshold
                "high_confidence_threshold": 0.5,
                "auto_assign_high_confidence": False,
                "skill_based_routing": True,
                "workload_balancing": True,
                "review_levels": 2,
            },
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_update_routing_config_out_of_range(self, client):
        """Test updating routing config with out-of-range values."""
        response = client.put(
            "/api/v1/annotation/routing/config",
            json={
                "low_confidence_threshold": 1.5,  # Out of range
                "high_confidence_threshold": 0.9,
                "auto_assign_high_confidence": False,
                "skill_based_routing": True,
                "workload_balancing": True,
                "review_levels": 2,
            },
        )

        # Should return validation error
        assert response.status_code in [400, 422]


# =============================================================================
# Pre-Annotation Endpoint Tests
# =============================================================================

class TestPreAnnotation:
    """Test pre-annotation endpoints."""

    def test_submit_pre_annotation(self, client):
        """Test submitting pre-annotation task."""
        response = client.post(
            "/api/v1/annotation/pre-annotate",
            json={
                "project_id": "test_project",
                "document_ids": ["doc1", "doc2", "doc3"],
                "annotation_type": "ner",
                "confidence_threshold": 0.7,
                "batch_size": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert "status" in data
        assert "message" in data
        assert "total_documents" in data
        assert data["total_documents"] == 3

    def test_get_pre_annotation_progress(self, client):
        """Test getting pre-annotation progress."""
        response = client.get("/api/v1/annotation/pre-annotate/test_task/progress")

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert "status" in data
        assert "progress" in data


# =============================================================================
# Mid-Coverage Endpoint Tests
# =============================================================================

class TestMidCoverage:
    """Test mid-coverage endpoints."""

    def test_get_suggestion(self, client):
        """Test getting real-time suggestion."""
        response = client.post(
            "/api/v1/annotation/suggestion",
            json={
                "document_id": "doc1",
                "text": "Apple Inc. is located in Cupertino.",
                "annotation_type": "ner",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "suggestion_id" in data
        assert "document_id" in data
        assert "annotations" in data
        assert "confidence" in data
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))

    def test_submit_feedback(self, client):
        """Test submitting feedback."""
        response = client.post(
            "/api/v1/annotation/feedback",
            json={
                "suggestion_id": "sug_123",
                "accepted": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "status" in data


# =============================================================================
# Engine Management Tests
# =============================================================================

class TestEngineManagement:
    """Test engine management endpoints."""

    def test_list_engines(self, client):
        """Test listing available engines."""
        response = client.get("/api/v1/annotation/engines")

        assert response.status_code == 200
        data = response.json()

        assert "engines" in data
        assert "count" in data
        assert isinstance(data["engines"], list)

    def test_compare_engines(self, client):
        """Test comparing engines."""
        response = client.post(
            "/api/v1/annotation/engines/compare",
            json={
                "engine_ids": ["engine1", "engine2"],
                "test_documents": ["doc1", "doc2"],
                "annotation_type": "ner",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "comparison_id" in data
        assert "results" in data


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling."""

    def test_correlation_id_in_response(self, client):
        """Test that correlation ID is included in responses."""
        response = client.get("/api/v1/annotation/tasks")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

    def test_error_response_format(self, client):
        """Test error response format."""
        # Trigger a validation error
        response = client.put(
            "/api/v1/annotation/routing/config",
            json={
                "invalid_field": "value",
            },
        )

        assert response.status_code in [400, 422]
        data = response.json()

        # Check error format
        assert "error" in data
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "correlation_id" in error
        assert "timestamp" in error


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/api/v1/annotation/tasks")

        assert response.status_code == 200
        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.skip(reason="Requires actual rate limiter with low limits")
    def test_rate_limit_exceeded(self, client):
        """Test rate limit exceeded response."""
        # Make many requests to exceed rate limit
        for _ in range(150):
            response = client.get("/api/v1/annotation/tasks")
            if response.status_code == 429:
                # Rate limit exceeded
                data = response.json()
                assert "error" in data
                assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
                return

        pytest.fail("Rate limit was not enforced")


# =============================================================================
# Content Type Validation Tests
# =============================================================================

class TestContentTypeValidation:
    """Test content type validation."""

    def test_invalid_content_type_post(self, client):
        """Test POST with invalid content type."""
        response = client.post(
            "/api/v1/annotation/suggestion",
            data="plain text data",
            headers={"Content-Type": "text/plain"},
        )

        # Should return 415 Unsupported Media Type
        assert response.status_code == 415

    def test_valid_content_type_post(self, client):
        """Test POST with valid content type."""
        response = client.post(
            "/api/v1/annotation/suggestion",
            json={
                "document_id": "doc1",
                "text": "Test text",
                "annotation_type": "ner",
            },
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Test performance characteristics."""

    def test_response_time_header(self, client):
        """Test that response time header is present."""
        response = client.get("/api/v1/annotation/tasks")

        assert response.status_code == 200
        assert "X-Response-Time" in response.headers

        # Parse response time
        response_time = response.headers["X-Response-Time"]
        assert "ms" in response_time

    @pytest.mark.asyncio
    async def test_suggestion_latency(self, async_client):
        """Test that suggestions have acceptable latency."""
        start_time = datetime.utcnow()

        response = await async_client.post(
            "/api/v1/annotation/suggestion",
            json={
                "document_id": "doc1",
                "text": "Test text for annotation",
                "annotation_type": "ner",
            },
        )

        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        assert response.status_code == 200
        data = response.json()

        # Check returned latency
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))

        # Latency should be reasonable (< 5 seconds for test)
        assert latency_ms < 5000
