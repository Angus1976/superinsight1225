"""
Unit tests for Audit Middleware.

Tests the automatic audit logging functionality for state-changing operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.middleware.audit_middleware import (
    AuditMiddleware,
    create_audit_middleware,
    STATE_CHANGING_METHODS
)
from src.models.data_lifecycle import (
    OperationType,
    OperationResult,
    ResourceType,
    Action
)


class TestAuditMiddleware:
    """Test suite for AuditMiddleware"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_get_db(self, mock_db):
        """Create a mock get_db function"""
        def get_db():
            yield mock_db
        return get_db
    
    @pytest.fixture
    def app(self, mock_get_db):
        """Create a test FastAPI application with audit middleware"""
        app = FastAPI()
        
        # Add audit middleware
        app.add_middleware(
            create_audit_middleware(get_db=mock_get_db)
        )
        
        # Add test endpoints
        @app.post("/samples/{sample_id}")
        async def create_sample(sample_id: str):
            return {"id": sample_id, "status": "created"}
        
        @app.put("/samples/{sample_id}")
        async def update_sample(sample_id: str):
            return {"id": sample_id, "status": "updated"}
        
        @app.delete("/samples/{sample_id}")
        async def delete_sample(sample_id: str):
            return {"id": sample_id, "status": "deleted"}
        
        @app.get("/samples/{sample_id}")
        async def get_sample(sample_id: str):
            return {"id": sample_id, "status": "retrieved"}
        
        @app.post("/temp-data/{data_id}/review")
        async def review_data(data_id: str):
            return {"id": data_id, "status": "reviewed"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client"""
        return TestClient(app)
    
    def test_logs_post_request(self, client, mock_db):
        """Test that POST requests are logged"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make POST request
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify response
            assert response.status_code == 200
            
            # Verify audit log was called
            mock_logger_instance.log_operation.assert_called_once()
            call_args = mock_logger_instance.log_operation.call_args[1]
            
            assert call_args["operation_type"] == OperationType.CREATE
            assert call_args["user_id"] == "user-456"
            assert call_args["resource_type"] == ResourceType.SAMPLE
            assert call_args["resource_id"] == "sample-123"
            assert call_args["result"] == OperationResult.SUCCESS
            assert call_args["duration"] >= 0
    
    def test_logs_put_request(self, client, mock_db):
        """Test that PUT requests are logged"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make PUT request
            response = client.put(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify response
            assert response.status_code == 200
            
            # Verify audit log was called
            mock_logger_instance.log_operation.assert_called_once()
            call_args = mock_logger_instance.log_operation.call_args[1]
            
            assert call_args["operation_type"] == OperationType.UPDATE
            assert call_args["user_id"] == "user-456"
    
    def test_logs_delete_request(self, client, mock_db):
        """Test that DELETE requests are logged"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make DELETE request
            response = client.delete(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify response
            assert response.status_code == 200
            
            # Verify audit log was called
            mock_logger_instance.log_operation.assert_called_once()
            call_args = mock_logger_instance.log_operation.call_args[1]
            
            assert call_args["operation_type"] == OperationType.DELETE
            assert call_args["action"] == Action.DELETE
    
    def test_does_not_log_get_request(self, client, mock_db):
        """Test that GET requests are not logged (not state-changing)"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make GET request
            response = client.get(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify response
            assert response.status_code == 200
            
            # Verify audit log was NOT called
            mock_logger_instance.log_operation.assert_not_called()
    
    def test_extracts_user_from_header(self, client, mock_db):
        """Test that user ID is extracted from X-User-ID header"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request with user header
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-789"}
            )
            
            # Verify user ID was extracted
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert call_args["user_id"] == "user-789"
    
    def test_uses_anonymous_when_no_user(self, client, mock_db):
        """Test that 'anonymous' is used when no user ID is available"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request without user header
            response = client.post("/samples/sample-123")
            
            # Verify anonymous user was used
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert call_args["user_id"] == "anonymous"
    
    def test_extracts_resource_type_from_url(self, client, mock_db):
        """Test that resource type is extracted from URL pattern"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request to samples endpoint
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify resource type
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert call_args["resource_type"] == ResourceType.SAMPLE
    
    def test_extracts_resource_id_from_path(self, client, mock_db):
        """Test that resource ID is extracted from path parameters"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request with resource ID in path
            response = client.post(
                "/samples/sample-456",
                headers={"X-User-ID": "user-123"}
            )
            
            # Verify resource ID
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert call_args["resource_id"] == "sample-456"
    
    def test_extracts_action_from_url(self, client, mock_db):
        """Test that action is extracted from URL pattern"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request to review endpoint
            response = client.post(
                "/temp-data/data-123/review",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify action
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert call_args["action"] == Action.REVIEW
    
    def test_records_duration(self, client, mock_db):
        """Test that operation duration is recorded"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify duration is recorded
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert "duration" in call_args
            assert call_args["duration"] >= 0
            assert isinstance(call_args["duration"], int)
    
    def test_records_success_result(self, client, mock_db):
        """Test that successful operations are recorded with SUCCESS result"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make successful request
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify success result
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert call_args["result"] == OperationResult.SUCCESS
            assert call_args["error"] is None
    
    def test_records_failure_result_on_error(self, client, mock_db):
        """Test that failed operations are recorded with FAILURE result"""
        app = FastAPI()
        
        # Add middleware
        app.add_middleware(
            create_audit_middleware(get_db=lambda: iter([mock_db]))
        )
        
        # Add endpoint that raises error
        @app.post("/samples/{sample_id}")
        async def failing_endpoint(sample_id: str):
            raise ValueError("Test error")
        
        client = TestClient(app, raise_server_exceptions=False)
        
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request that will fail
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify failure result
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert call_args["result"] == OperationResult.FAILURE
            assert call_args["error"] is not None
    
    def test_skips_excluded_paths(self, mock_get_db):
        """Test that excluded paths are not logged"""
        app = FastAPI()
        
        # Add middleware with excluded paths
        app.add_middleware(
            create_audit_middleware(
                get_db=mock_get_db,
                excluded_paths=["/health", "/metrics"]
            )
        )
        
        @app.post("/health")
        async def health():
            return {"status": "ok"}
        
        @app.post("/samples/{sample_id}")
        async def create_sample(sample_id: str):
            return {"id": sample_id}
        
        client = TestClient(app)
        
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request to excluded path
            response = client.post("/health")
            assert response.status_code == 200
            
            # Verify audit log was NOT called
            mock_logger_instance.log_operation.assert_not_called()
            
            # Make request to non-excluded path
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            assert response.status_code == 200
            
            # Verify audit log WAS called
            mock_logger_instance.log_operation.assert_called_once()
    
    def test_includes_request_details(self, client, mock_db):
        """Test that request details are included in audit log"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make request with query parameters
            response = client.post(
                "/samples/sample-123?filter=active&sort=name",
                headers={
                    "X-User-ID": "user-456",
                    "User-Agent": "TestClient/1.0"
                }
            )
            
            # Verify request details
            call_args = mock_logger_instance.log_operation.call_args[1]
            assert "details" in call_args
            details = call_args["details"]
            assert details["method"] == "POST"
            assert details["path"] == "/samples/sample-123"
            assert "query_params" in details
            
            # Verify user agent
            assert call_args["user_agent"] == "TestClient/1.0"
    
    def test_handles_logging_errors_gracefully(self, client, mock_db):
        """Test that logging errors don't break the request"""
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            # Make logger raise an exception
            mock_logger.side_effect = Exception("Database error")
            
            # Make request - should still succeed
            response = client.post(
                "/samples/sample-123",
                headers={"X-User-ID": "user-456"}
            )
            
            # Verify request succeeded despite logging error
            assert response.status_code == 200
            assert response.json() == {"id": "sample-123", "status": "created"}


class TestAuditMiddlewareIntegration:
    """Integration tests for audit middleware with real audit logger"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock(spec=Session)
        return db
    
    def test_end_to_end_audit_logging(self, mock_db):
        """Test complete audit logging flow"""
        # Create app with middleware
        app = FastAPI()
        
        def get_db():
            yield mock_db
        
        app.add_middleware(create_audit_middleware(get_db=get_db))
        
        @app.post("/samples/{sample_id}")
        async def create_sample(sample_id: str):
            return {"id": sample_id, "status": "created"}
        
        client = TestClient(app)
        
        with patch('src.middleware.audit_middleware.AuditLogger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Make multiple requests
            client.post("/samples/sample-1", headers={"X-User-ID": "user-1"})
            client.put("/samples/sample-2", headers={"X-User-ID": "user-2"})
            client.delete("/samples/sample-3", headers={"X-User-ID": "user-3"})
            
            # Verify all operations were logged
            assert mock_logger_instance.log_operation.call_count == 3
            
            # Verify different operation types
            calls = mock_logger_instance.log_operation.call_args_list
            assert calls[0][1]["operation_type"] == OperationType.CREATE
            assert calls[1][1]["operation_type"] == OperationType.UPDATE
            assert calls[2][1]["operation_type"] == OperationType.DELETE
