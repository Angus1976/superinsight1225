"""
API tests for LLM endpoints.

Tests the REST API endpoints for LLM operations including:
- Text generation
- Health status monitoring
- Provider activation
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Skip if FastAPI not available
try:
    from fastapi import FastAPI
    from src.api.llm import router
    from src.security.models import UserModel, UserRole
except ImportError:
    pytest.skip("FastAPI or dependencies not available", allow_module_level=True)


# ==================== Test Fixtures ====================

@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock regular user."""
    user = Mock(spec=UserModel)
    user.username = "testuser"
    user.role = UserRole.USER
    user.tenant_id = "test-tenant"
    return user


@pytest.fixture
def mock_admin():
    """Create a mock admin user."""
    user = Mock(spec=UserModel)
    user.username = "admin"
    user.role = UserRole.ADMIN
    user.tenant_id = "test-tenant"
    return user


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    from src.ai.llm_schemas import LLMResponse, TokenUsage

    return LLMResponse(
        content="This is a test response",
        model="test-model",
        provider="local_ollama",
        latency_ms=150.0,
        usage=TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        ),
        cached=False
    )


@pytest.fixture
def mock_health_status():
    """Create a mock health status."""
    from src.ai.llm_schemas import HealthStatus

    return HealthStatus(
        available=True,
        latency_ms=50.0,
        error=None
    )


# ==================== Test POST /api/v1/llm/generate ====================

def test_generate_success(client, mock_user, mock_llm_response):
    """Test successful text generation."""
    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        # Setup mock switcher
        mock_switcher = AsyncMock()
        mock_switcher.generate = AsyncMock(return_value=mock_llm_response)
        mock_switcher._current_method = Mock(value="local_ollama")
        mock_get_switcher.return_value = mock_switcher

        # Make request
        response = client.post(
            "/api/v1/llm/generate",
            json={
                "prompt": "Hello, world!",
                "max_tokens": 100,
                "temperature": 0.7
            }
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "This is a test response"
        assert data["model"] == "test-model"
        assert data["provider_id"] == "local_ollama"
        assert data["usage"]["total_tokens"] == 30
        assert data["cached"] == False


def test_generate_minimal_request(client, mock_user, mock_llm_response):
    """Test generation with minimal request parameters."""
    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        mock_switcher = AsyncMock()
        mock_switcher.generate = AsyncMock(return_value=mock_llm_response)
        mock_switcher._current_method = Mock(value="cloud_openai")
        mock_get_switcher.return_value = mock_switcher

        # Minimal request - only prompt required
        response = client.post(
            "/api/v1/llm/generate",
            json={"prompt": "Test"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert data["provider_id"] == "cloud_openai"


def test_generate_with_system_prompt(client, mock_user, mock_llm_response):
    """Test generation with system prompt."""
    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        mock_switcher = AsyncMock()
        mock_switcher.generate = AsyncMock(return_value=mock_llm_response)
        mock_switcher._current_method = Mock(value="local_ollama")
        mock_get_switcher.return_value = mock_switcher

        response = client.post(
            "/api/v1/llm/generate",
            json={
                "prompt": "Write a poem",
                "system_prompt": "You are a helpful assistant"
            }
        )

        assert response.status_code == 200
        # Verify system_prompt was passed to switcher
        mock_switcher.generate.assert_called_once()
        call_kwargs = mock_switcher.generate.call_args[1]
        assert call_kwargs["system_prompt"] == "You are a helpful assistant"


def test_generate_empty_prompt(client, mock_user):
    """Test generation with empty prompt returns validation error."""
    with patch('src.api.llm.get_current_user', return_value=mock_user):

        response = client.post(
            "/api/v1/llm/generate",
            json={"prompt": ""}
        )

        # Should fail validation
        assert response.status_code == 422


def test_generate_service_unavailable(client, mock_user):
    """Test generation when LLM service is unavailable."""
    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        # Simulate service unavailable
        mock_get_switcher.side_effect = Exception("Service down")

        response = client.post(
            "/api/v1/llm/generate",
            json={"prompt": "Test"}
        )

        # Should return 503
        assert response.status_code == 503
        assert "error_code" in response.json()["detail"]


def test_generate_generation_failed(client, mock_user):
    """Test generation when generation fails."""
    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        mock_switcher = AsyncMock()
        mock_switcher.generate = AsyncMock(side_effect=Exception("Generation error"))
        mock_get_switcher.return_value = mock_switcher

        response = client.post(
            "/api/v1/llm/generate",
            json={"prompt": "Test"}
        )

        # Should return 500
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error_code"] == "GENERATION_FAILED"


# ==================== Test GET /api/v1/llm/health ====================

def test_health_success(client, mock_user, mock_health_status):
    """Test successful health status retrieval."""
    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher, \
         patch('src.api.llm.get_health_monitor_instance') as mock_get_monitor:

        # Setup mock switcher
        mock_switcher = AsyncMock()
        mock_switcher._current_method = Mock(value="local_ollama")
        mock_switcher._fallback_method = Mock(value="cloud_openai")
        mock_get_switcher.return_value = mock_switcher

        # Setup mock monitor
        mock_monitor = AsyncMock()
        mock_monitor.get_all_health_status = AsyncMock(return_value={
            "local_ollama": {
                "is_healthy": True,
                "last_error": None,
                "consecutive_failures": 0
            },
            "cloud_openai": {
                "is_healthy": True,
                "last_error": None,
                "consecutive_failures": 0
            }
        })
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/v1/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_healthy"] == True
        assert data["active_provider_id"] == "local_ollama"
        assert data["fallback_provider_id"] == "cloud_openai"
        assert len(data["providers"]) == 2


def test_health_no_monitor(client, mock_user, mock_health_status):
    """Test health status when monitor is not available."""
    from src.ai.llm_schemas import LLMMethod

    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher, \
         patch('src.api.llm.get_health_monitor_instance') as mock_get_monitor:

        # Mock provider with health_check method
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=mock_health_status)

        mock_switcher = AsyncMock()
        mock_switcher._current_method = LLMMethod.LOCAL_OLLAMA
        mock_switcher._fallback_method = None
        mock_switcher._providers = {LLMMethod.LOCAL_OLLAMA: mock_provider}
        mock_get_switcher.return_value = mock_switcher

        # No monitor available
        mock_get_monitor.return_value = None

        response = client.get("/api/v1/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert len(data["providers"]) == 1
        assert data["providers"][0]["is_healthy"] == True


def test_health_unhealthy_providers(client, mock_user):
    """Test health status with unhealthy providers."""
    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher, \
         patch('src.api.llm.get_health_monitor_instance') as mock_get_monitor:

        mock_switcher = AsyncMock()
        mock_switcher._current_method = Mock(value="local_ollama")
        mock_switcher._fallback_method = None
        mock_get_switcher.return_value = mock_switcher

        # All providers unhealthy
        mock_monitor = AsyncMock()
        mock_monitor.get_all_health_status = AsyncMock(return_value={
            "local_ollama": {
                "is_healthy": False,
                "last_error": "Connection failed",
                "consecutive_failures": 3
            }
        })
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/v1/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_healthy"] == False
        assert data["providers"][0]["is_healthy"] == False
        assert data["providers"][0]["last_error"] == "Connection failed"


# ==================== Test POST /api/v1/llm/providers/{id}/activate ====================

def test_activate_provider_success_admin(client, mock_admin, mock_health_status):
    """Test successful provider activation by admin."""
    from src.ai.llm_schemas import LLMMethod

    with patch('src.api.llm.get_current_user', return_value=mock_admin), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=mock_health_status)

        mock_switcher = AsyncMock()
        mock_switcher._current_method = LLMMethod.LOCAL_OLLAMA
        mock_switcher._providers = {
            LLMMethod.LOCAL_OLLAMA: mock_provider,
            LLMMethod.CLOUD_OPENAI: mock_provider
        }
        mock_get_switcher.return_value = mock_switcher

        response = client.post(
            "/api/v1/llm/providers/cloud_openai/activate",
            json={"set_as_fallback": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["provider_id"] == "cloud_openai"
        assert "activated as primary" in data["message"].lower()
        assert data["previous_active_id"] == "local_ollama"


def test_activate_provider_as_fallback(client, mock_admin, mock_health_status):
    """Test setting provider as fallback."""
    from src.ai.llm_schemas import LLMMethod

    with patch('src.api.llm.get_current_user', return_value=mock_admin), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=mock_health_status)

        mock_switcher = AsyncMock()
        mock_switcher._current_method = LLMMethod.LOCAL_OLLAMA
        mock_switcher._providers = {LLMMethod.CLOUD_OPENAI: mock_provider}
        mock_switcher.set_fallback_provider = AsyncMock()
        mock_get_switcher.return_value = mock_switcher

        response = client.post(
            "/api/v1/llm/providers/cloud_openai/activate",
            json={"set_as_fallback": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "fallback" in data["message"].lower()

        # Verify set_fallback_provider was called
        mock_switcher.set_fallback_provider.assert_called_once()


def test_activate_provider_non_admin(client, mock_user):
    """Test provider activation by non-admin returns 403."""
    with patch('src.api.llm.get_current_user', return_value=mock_user):

        response = client.post(
            "/api/v1/llm/providers/cloud_openai/activate",
            json={"set_as_fallback": False}
        )

        # Should deny access
        assert response.status_code == 403
        assert "ADMIN_REQUIRED" in response.json()["detail"]["error_code"]


def test_activate_provider_not_found(client, mock_admin):
    """Test activation of non-existent provider."""
    with patch('src.api.llm.get_current_user', return_value=mock_admin), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        mock_switcher = AsyncMock()
        mock_switcher._providers = {}
        mock_get_switcher.return_value = mock_switcher

        response = client.post(
            "/api/v1/llm/providers/nonexistent/activate",
            json={}
        )

        assert response.status_code == 404
        assert "PROVIDER_NOT_FOUND" in response.json()["detail"]["error_code"]


def test_activate_provider_unhealthy(client, mock_admin):
    """Test activation of unhealthy provider returns 400."""
    from src.ai.llm_schemas import LLMMethod, HealthStatus

    with patch('src.api.llm.get_current_user', return_value=mock_admin), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher:

        # Create unhealthy status
        unhealthy_status = HealthStatus(
            available=False,
            latency_ms=0.0,
            error="Connection failed"
        )

        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=unhealthy_status)

        mock_switcher = AsyncMock()
        mock_switcher._providers = {LLMMethod.CLOUD_OPENAI: mock_provider}
        mock_get_switcher.return_value = mock_switcher

        response = client.post(
            "/api/v1/llm/providers/cloud_openai/activate",
            json={"set_as_fallback": False}
        )

        assert response.status_code == 400
        assert "PROVIDER_UNHEALTHY" in response.json()["detail"]["error_code"]


# ==================== Test GET /api/v1/llm/providers/{id}/api-key ====================

def test_get_api_key_admin(client, mock_admin):
    """Test API key retrieval by admin."""
    with patch('src.api.llm.get_current_user', return_value=mock_admin), \
         patch('src.api.llm.get_config_manager') as mock_get_config:

        # Mock config manager
        mock_config = Mock()
        mock_config.api_key = "sk-test123456789"

        mock_manager = AsyncMock()
        mock_manager.get_llm_config = AsyncMock(return_value=mock_config)
        mock_get_config.return_value = mock_manager

        response = client.get("/api/v1/llm/providers/cloud_openai/api-key")

        assert response.status_code == 200
        data = response.json()
        assert data["provider_id"] == "cloud_openai"
        assert data["has_api_key"] == True
        assert "masked" in data["api_key_masked"]


def test_get_api_key_non_admin(client, mock_user):
    """Test API key retrieval by non-admin returns 403."""
    with patch('src.api.llm.get_current_user', return_value=mock_user):

        response = client.get("/api/v1/llm/providers/cloud_openai/api-key")

        # Should deny access
        assert response.status_code == 403
        assert "ADMIN_REQUIRED" in response.json()["detail"]["error_code"]


# ==================== Integration Tests ====================

@pytest.mark.integration
def test_full_workflow_generate_and_health(client, mock_user, mock_llm_response, mock_health_status):
    """Test complete workflow: check health, then generate."""
    from src.ai.llm_schemas import LLMMethod

    with patch('src.api.llm.get_current_user', return_value=mock_user), \
         patch('src.api.llm.get_llm_switcher_instance') as mock_get_switcher, \
         patch('src.api.llm.get_health_monitor_instance') as mock_get_monitor:

        # Setup mocks
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=mock_health_status)

        mock_switcher = AsyncMock()
        mock_switcher.generate = AsyncMock(return_value=mock_llm_response)
        mock_switcher._current_method = LLMMethod.LOCAL_OLLAMA
        mock_switcher._providers = {LLMMethod.LOCAL_OLLAMA: mock_provider}
        mock_get_switcher.return_value = mock_switcher

        mock_monitor = AsyncMock()
        mock_monitor.get_all_health_status = AsyncMock(return_value={
            "local_ollama": {"is_healthy": True, "last_error": None}
        })
        mock_get_monitor.return_value = mock_monitor

        # 1. Check health
        health_response = client.get("/api/v1/llm/health")
        assert health_response.status_code == 200
        assert health_response.json()["overall_healthy"] == True

        # 2. Generate text
        generate_response = client.post(
            "/api/v1/llm/generate",
            json={"prompt": "Hello"}
        )
        assert generate_response.status_code == 200
        assert "text" in generate_response.json()
