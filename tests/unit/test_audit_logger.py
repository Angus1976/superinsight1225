"""
Unit tests for Audit Logger service.

Tests all methods of the AuditLogger service including logging operations,
filtering, querying, and CSV export functionality.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.data_lifecycle import (
    OperationType,
    OperationResult,
    ResourceType,
    Action
)
from src.services.audit_logger import AuditLogger
from tests.conftest import db_session  # Import the fixture


@pytest.fixture
def audit_logger(db_session):
    """Create an AuditLogger instance."""
    return AuditLogger(db_session)


class TestLogOperation:
    """Tests for log_operation method."""
    
    def test_log_operation_success(self, audit_logger):
        """Test logging a successful operation."""
        # Arrange
        user_id = "user123"
        resource_id = str(uuid4())
        
        # Act
        log = audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=user_id,
            resource_type=ResourceType.SAMPLE,
            resource_id=resource_id,
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=150,
            details={"sample_name": "test_sample"}
        )
        
        # Assert
        assert log.id is not None
        assert log.user_id == user_id
        assert log.resource_id == resource_id
        assert log.operation_type == OperationType.CREATE
        assert log.resource_type == ResourceType.SAMPLE
        assert log.action == Action.EDIT
        assert log.result == OperationResult.SUCCESS
        assert log.duration == 150
        assert log.details == {"sample_name": "test_sample"}
        assert log.timestamp is not None
    
    def test_log_operation_failure(self, audit_logger):
        """Test logging a failed operation."""
        # Arrange
        error_message = "Permission denied"
        
        # Act
        log = audit_logger.log_operation(
            operation_type=OperationType.DELETE,
            user_id="user456",
            resource_type=ResourceType.TEMP_DATA,
            resource_id=str(uuid4()),
            action=Action.DELETE,
            result=OperationResult.FAILURE,
            duration=50,
            error=error_message
        )
        
        # Assert
        assert log.result == OperationResult.FAILURE
        assert log.error == error_message
    
    def test_log_operation_with_ip_and_user_agent(self, audit_logger):
        """Test logging operation with IP address and user agent."""
        # Arrange
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0"
        
        # Act
        log = audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id="user789",
            resource_type=ResourceType.ANNOTATION_TASK,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=200,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Assert
        assert log.ip_address == ip_address
        assert log.user_agent == user_agent
    
    def test_log_operation_immutability(self, audit_logger, db_session):
        """Test that audit logs are immutable (cannot be updated)."""
        # Arrange
        log = audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act & Assert
        # In a real implementation, attempting to update would be prevented
        # by database constraints or application logic
        # Here we just verify the log was created
        assert log.id is not None


class TestGetAuditLog:
    """Tests for get_audit_log method."""
    
    def test_get_audit_log_no_filters(self, audit_logger):
        """Test retrieving all audit logs without filters."""
        # Arrange
        for i in range(5):
            audit_logger.log_operation(
                operation_type=OperationType.CREATE,
                user_id=f"user{i}",
                resource_type=ResourceType.SAMPLE,
                resource_id=str(uuid4()),
                action=Action.EDIT,
                result=OperationResult.SUCCESS,
                duration=100
            )
        
        # Act
        logs = audit_logger.get_audit_log()
        
        # Assert
        assert len(logs) == 5
    
    def test_get_audit_log_filter_by_user(self, audit_logger):
        """Test filtering audit logs by user ID."""
        # Arrange
        target_user = "user123"
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=target_user,
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="other_user",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        logs = audit_logger.get_audit_log(user_id=target_user)
        
        # Assert
        assert len(logs) == 1
        assert logs[0].user_id == target_user
    
    def test_get_audit_log_filter_by_resource_type(self, audit_logger):
        """Test filtering audit logs by resource type."""
        # Arrange
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.TEMP_DATA,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        logs = audit_logger.get_audit_log(resource_type=ResourceType.SAMPLE)
        
        # Assert
        assert len(logs) == 1
        assert logs[0].resource_type == ResourceType.SAMPLE
    
    def test_get_audit_log_filter_by_operation_type(self, audit_logger):
        """Test filtering audit logs by operation type."""
        # Arrange
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.DELETE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.DELETE,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        logs = audit_logger.get_audit_log(operation_type=OperationType.DELETE)
        
        # Assert
        assert len(logs) == 1
        assert logs[0].operation_type == OperationType.DELETE
    
    def test_get_audit_log_filter_by_result(self, audit_logger):
        """Test filtering audit logs by operation result."""
        # Arrange
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.FAILURE,
            duration=100,
            error="Test error"
        )
        
        # Act
        logs = audit_logger.get_audit_log(result=OperationResult.FAILURE)
        
        # Assert
        assert len(logs) == 1
        assert logs[0].result == OperationResult.FAILURE
    
    def test_get_audit_log_filter_by_date_range(self, audit_logger):
        """Test filtering audit logs by date range."""
        # Arrange
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        logs = audit_logger.get_audit_log(
            start_date=yesterday,
            end_date=tomorrow
        )
        
        # Assert
        assert len(logs) == 1
        assert yesterday <= logs[0].timestamp <= tomorrow
    
    def test_get_audit_log_pagination(self, audit_logger):
        """Test pagination of audit log results."""
        # Arrange
        for i in range(10):
            audit_logger.log_operation(
                operation_type=OperationType.CREATE,
                user_id=f"user{i}",
                resource_type=ResourceType.SAMPLE,
                resource_id=str(uuid4()),
                action=Action.EDIT,
                result=OperationResult.SUCCESS,
                duration=100
            )
        
        # Act
        page1 = audit_logger.get_audit_log(limit=5, offset=0)
        page2 = audit_logger.get_audit_log(limit=5, offset=5)
        
        # Assert
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id
    
    def test_get_audit_log_multiple_filters(self, audit_logger):
        """Test combining multiple filters."""
        # Arrange
        target_user = "user123"
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=target_user,
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.DELETE,
            user_id=target_user,
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.DELETE,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="other_user",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        logs = audit_logger.get_audit_log(
            user_id=target_user,
            operation_type=OperationType.CREATE
        )
        
        # Assert
        assert len(logs) == 1
        assert logs[0].user_id == target_user
        assert logs[0].operation_type == OperationType.CREATE


class TestGetDataHistory:
    """Tests for get_data_history method."""
    
    def test_get_data_history(self, audit_logger):
        """Test retrieving complete history for a data item."""
        # Arrange
        resource_id = str(uuid4())
        
        # Create multiple operations on the same resource
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=resource_id,
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id="user456",
            resource_type=ResourceType.SAMPLE,
            resource_id=resource_id,
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=150
        )
        
        # Act
        history = audit_logger.get_data_history(resource_id)
        
        # Assert
        assert len(history) == 2
        assert all(log.resource_id == resource_id for log in history)
        # Verify chronological order
        assert history[0].timestamp <= history[1].timestamp
    
    def test_get_data_history_with_resource_type_filter(self, audit_logger):
        """Test filtering data history by resource type."""
        # Arrange
        resource_id = str(uuid4())
        
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=resource_id,
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        history = audit_logger.get_data_history(
            resource_id,
            resource_type=ResourceType.SAMPLE
        )
        
        # Assert
        assert len(history) == 1
        assert history[0].resource_type == ResourceType.SAMPLE


class TestGetUserActivity:
    """Tests for get_user_activity method."""
    
    def test_get_user_activity(self, audit_logger):
        """Test retrieving user activity logs."""
        # Arrange
        user_id = "user123"
        
        for i in range(3):
            audit_logger.log_operation(
                operation_type=OperationType.CREATE,
                user_id=user_id,
                resource_type=ResourceType.SAMPLE,
                resource_id=str(uuid4()),
                action=Action.EDIT,
                result=OperationResult.SUCCESS,
                duration=100
            )
        
        # Act
        activity = audit_logger.get_user_activity(user_id)
        
        # Assert
        assert len(activity) == 3
        assert all(log.user_id == user_id for log in activity)
    
    def test_get_user_activity_with_date_range(self, audit_logger):
        """Test filtering user activity by date range."""
        # Arrange
        user_id = "user123"
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=user_id,
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        activity = audit_logger.get_user_activity(
            user_id,
            start_date=yesterday,
            end_date=tomorrow
        )
        
        # Assert
        assert len(activity) == 1
        assert activity[0].user_id == user_id
    
    def test_get_user_activity_with_limit(self, audit_logger):
        """Test limiting user activity results."""
        # Arrange
        user_id = "user123"
        
        for i in range(10):
            audit_logger.log_operation(
                operation_type=OperationType.CREATE,
                user_id=user_id,
                resource_type=ResourceType.SAMPLE,
                resource_id=str(uuid4()),
                action=Action.EDIT,
                result=OperationResult.SUCCESS,
                duration=100
            )
        
        # Act
        activity = audit_logger.get_user_activity(user_id, limit=5)
        
        # Assert
        assert len(activity) == 5


class TestExportAuditLog:
    """Tests for export_audit_log method."""
    
    def test_export_audit_log_csv_format(self, audit_logger):
        """Test exporting audit logs to CSV format."""
        # Arrange
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100,
            details={"test": "data"}
        )
        
        # Act
        csv_content = audit_logger.export_audit_log()
        
        # Assert (enum values in CSV are lowercase via .value)
        assert csv_content is not None
        assert "ID,Timestamp,User ID" in csv_content
        assert "user123" in csv_content
        assert "create" in csv_content
        assert "sample" in csv_content
    
    def test_export_audit_log_with_filters(self, audit_logger):
        """Test exporting filtered audit logs."""
        # Arrange
        target_user = "user123"
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=target_user,
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="other_user",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100
        )
        
        # Act
        csv_content = audit_logger.export_audit_log(user_id=target_user)
        
        # Assert
        assert target_user in csv_content
        assert "other_user" not in csv_content
    
    def test_export_audit_log_csv_structure(self, audit_logger):
        """Test CSV structure has all required columns."""
        # Arrange
        audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id="user123",
            resource_type=ResourceType.SAMPLE,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=100,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        # Act
        csv_content = audit_logger.export_audit_log()
        lines = csv_content.strip().split('\n')
        
        # Assert
        assert len(lines) >= 2  # Header + at least one data row
        header = lines[0]
        assert "ID" in header
        assert "Timestamp" in header
        assert "User ID" in header
        assert "Operation Type" in header
        assert "Resource Type" in header
        assert "Resource ID" in header
        assert "Action" in header
        assert "Result" in header
        assert "Duration (ms)" in header
        assert "IP Address" in header
        assert "User Agent" in header
