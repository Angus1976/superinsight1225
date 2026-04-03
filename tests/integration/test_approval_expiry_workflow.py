"""
Integration tests for Approval Expiry Workflow.

Tests the complete workflow of automatic approval expiry including:
- Creating approval requests
- Waiting for expiry
- Running scheduler to mark as expired
- Verifying expired status
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.services.approval_service import ApprovalService
from src.services.approval_scheduler import (
    ApprovalExpiryScheduler,
    ApprovalScheduleConfig
)
from src.models.approval import ApprovalStatus
from src.models.data_transfer import DataTransferRequest, DataAttributes
from src.services.permission_service import UserRole


@pytest.mark.integration
class TestApprovalExpiryWorkflow:
    """Integration tests for approval expiry workflow."""
    
    @pytest.fixture
    async def db_session(self):
        """Create a test database session."""
        # This would use your actual test database setup
        # For now, using a mock
        from unittest.mock import Mock
        session = Mock(spec=Session)
        yield session
    
    @pytest.fixture
    def approval_service(self, db_session):
        """Create ApprovalService instance."""
        return ApprovalService(db_session)
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        config = ApprovalScheduleConfig(
            use_interval=True,
            interval_hours=1,
            enable_expiry_check=True
        )
        return ApprovalExpiryScheduler(config)
    
    @pytest.fixture
    def sample_transfer_request(self):
        """Create a sample transfer request."""
        return DataTransferRequest(
            source_type="structuring",
            source_id="test-source-123",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="test_category",
                tags=["test"],
                quality_score=0.9,
                description="Test transfer"
            ),
            records=[
                {
                    "id": "record-1",
                    "content": {"field": "value"},
                    "metadata": {}
                }
            ]
        )
    
    @pytest.mark.asyncio
    async def test_create_and_expire_approval(
        self,
        approval_service,
        sample_transfer_request,
        db_session
    ):
        """Test creating an approval and expiring it."""
        # Mock database operations
        from unittest.mock import patch, Mock

        approval_id = None

        with patch.object(
            approval_service, "_get_eligible_approvers", return_value=[]
        ):
            with patch.object(db_session, 'execute') as mock_execute:
                with patch.object(db_session, 'commit'):
                    mock_execute.return_value = Mock()

                    # Create approval request
                    approval = await approval_service.create_approval_request(
                        transfer_request=sample_transfer_request,
                        requester_id="user-123",
                        requester_role=UserRole.DATA_ANALYST
                    )

                    approval_id = approval.id
                    assert approval.status == ApprovalStatus.PENDING

                    approval.expires_at = datetime.utcnow() - timedelta(days=1)

                    mock_execute.return_value = Mock(rowcount=1)
                    expired_count = approval_service.expire_old_approvals()

                    assert expired_count == 1

    @pytest.mark.asyncio
    async def test_scheduler_expires_old_approvals(
        self,
        scheduler,
        approval_service,
        sample_transfer_request,
        db_session
    ):
        """Test that scheduler correctly expires old approvals."""
        from unittest.mock import patch, Mock
        
        # Start scheduler
        await scheduler.start_scheduler()
        
        try:
            # Mock database session
            with patch('src.services.approval_scheduler.db_manager') as mock_db_manager:
                mock_db_manager.get_session.return_value.__aenter__.return_value = db_session
                
                # Mock ApprovalService
                with patch('src.services.approval_service.ApprovalService') as mock_service_class:
                    mock_service = Mock()
                    mock_service.expire_old_approvals.return_value = 3
                    mock_service_class.return_value = mock_service
                    
                    # Manually trigger expiry check
                    await scheduler._run_expiry_check()
                    
                    # Verify service was called
                    mock_service.expire_old_approvals.assert_called_once()
                    
                    # Verify statistics
                    assert scheduler.last_expired_count == 3
                    assert scheduler.total_runs == 1
                    assert scheduler.total_expired == 3
        
        finally:
            await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_multiple_approvals_expiry(
        self,
        approval_service,
        sample_transfer_request,
        db_session
    ):
        """Test expiring multiple approvals at once."""
        from unittest.mock import patch

        with patch.object(approval_service, "_get_eligible_approvers", return_value=[]):
            with patch.object(db_session, 'execute') as mock_execute:
                with patch.object(db_session, 'commit'):
                    # Create multiple approval requests
                    approvals = []
                    for i in range(5):
                        approval = await approval_service.create_approval_request(
                            transfer_request=sample_transfer_request,
                            requester_id=f"user-{i}",
                            requester_role=UserRole.DATA_ANALYST
                        )
                        approvals.append(approval)

                    # Mock all as expired
                    mock_execute.return_value.rowcount = 5

                    # Run expiry check
                    expired_count = approval_service.expire_old_approvals()

                    assert expired_count == 5
    
    @pytest.mark.asyncio
    async def test_no_approvals_to_expire(
        self,
        approval_service,
        db_session
    ):
        """Test expiry check when no approvals need expiring."""
        from unittest.mock import patch
        
        with patch.object(db_session, 'execute') as mock_execute:
            with patch.object(db_session, 'commit'):
                # Mock no expired approvals
                mock_execute.return_value.rowcount = 0
                
                # Run expiry check
                expired_count = approval_service.expire_old_approvals()
                
                assert expired_count == 0
    
    @pytest.mark.asyncio
    async def test_scheduler_manual_check(
        self,
        scheduler,
        db_session
    ):
        """Test manual expiry check via scheduler."""
        from unittest.mock import patch, Mock
        
        await scheduler.start_scheduler()
        
        try:
            with patch('src.services.approval_scheduler.db_manager') as mock_db_manager:
                mock_db_manager.get_session.return_value.__aenter__.return_value = db_session
                
                with patch('src.services.approval_service.ApprovalService') as mock_service_class:
                    mock_service = Mock()
                    mock_service.expire_old_approvals.return_value = 2
                    mock_service_class.return_value = mock_service
                    
                    # Run manual check
                    result = await scheduler.run_manual_check()
                    
                    assert result["success"] is True
                    assert result["expired_count"] == 2
                    assert "duration_seconds" in result
                    assert "timestamp" in result
        
        finally:
            await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_scheduler_status_tracking(
        self,
        scheduler,
        db_session
    ):
        """Test that scheduler tracks status correctly."""
        from unittest.mock import patch, Mock
        
        await scheduler.start_scheduler()
        
        try:
            # Get initial status
            status = scheduler.get_scheduler_status()
            assert status["is_running"] is True
            assert status["statistics"]["total_runs"] == 0
            
            # Run expiry check
            with patch('src.services.approval_scheduler.db_manager') as mock_db_manager:
                mock_db_manager.get_session.return_value.__aenter__.return_value = db_session
                
                with patch('src.services.approval_service.ApprovalService') as mock_service_class:
                    mock_service = Mock()
                    mock_service.expire_old_approvals.return_value = 4
                    mock_service_class.return_value = mock_service
                    
                    await scheduler._run_expiry_check()
            
            # Get updated status
            status = scheduler.get_scheduler_status()
            assert status["statistics"]["total_runs"] == 1
            assert status["statistics"]["last_expired_count"] == 4
            assert status["statistics"]["total_expired"] == 4
            assert status["statistics"]["last_run"] is not None
        
        finally:
            await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_expired_approval_cannot_be_approved(
        self,
        approval_service,
        sample_transfer_request,
        db_session
    ):
        """Test that expired approvals cannot be approved."""
        from unittest.mock import patch, Mock
        from sqlalchemy import text
        import json
        
        with patch.object(approval_service, "_get_eligible_approvers", return_value=[]):
            with patch.object(db_session, 'execute') as mock_execute:
                with patch.object(db_session, 'commit'):
                    # Create approval
                    approval = await approval_service.create_approval_request(
                        transfer_request=sample_transfer_request,
                        requester_id="user-123",
                        requester_role=UserRole.DATA_ANALYST
                    )

                    # Set as expired
                    approval.expires_at = datetime.utcnow() - timedelta(days=1)

                    # Mock fetching the approval
                    mock_result = Mock()
                    mock_result.fetchone.return_value = (
                        approval.id,
                        sample_transfer_request.model_dump_json(),
                        approval.requester_id,
                        approval.requester_role,
                        ApprovalStatus.PENDING.value,
                        approval.created_at,
                        approval.expires_at,
                        None,
                        None,
                        None
                    )
                    mock_execute.return_value = mock_result

                    # Try to approve expired approval
                    with pytest.raises(ValueError, match="expired"):
                        await approval_service.approve_request(
                            approval_id=approval.id,
                            approver_id="admin-123",
                            approver_role=UserRole.ADMIN,
                            approved=True
                        )
    
    @pytest.mark.asyncio
    async def test_scheduler_handles_errors_gracefully(
        self,
        scheduler,
        db_session
    ):
        """Test that scheduler handles errors without crashing."""
        from unittest.mock import patch, Mock
        
        await scheduler.start_scheduler()
        
        try:
            with patch('src.services.approval_scheduler.db_manager') as mock_db_manager:
                mock_db_manager.get_session.return_value.__aenter__.return_value = db_session
                
                with patch('src.services.approval_service.ApprovalService') as mock_service_class:
                    mock_service = Mock()
                    mock_service.expire_old_approvals.side_effect = Exception("Database error")
                    mock_service_class.return_value = mock_service
                    
                    # Should raise exception
                    with pytest.raises(Exception, match="Database error"):
                        await scheduler._run_expiry_check()
                    
                    # Scheduler should still be running
                    assert scheduler.is_running is True
        
        finally:
            await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_scheduler_interval_configuration(self):
        """Test scheduler with different interval configurations."""
        # Test with 2-hour interval
        config = ApprovalScheduleConfig(
            use_interval=True,
            interval_hours=2
        )
        scheduler = ApprovalExpiryScheduler(config)
        
        await scheduler.start_scheduler()
        
        try:
            status = scheduler.get_scheduler_status()
            assert status["config"]["use_interval"] is True
            assert status["config"]["interval_hours"] == 2
            assert len(status["jobs"]) == 1
        
        finally:
            await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_scheduler_cron_configuration(self):
        """Test scheduler with cron configuration."""
        config = ApprovalScheduleConfig(
            use_interval=False,
            expiry_check_hour=3,
            expiry_check_minute=30
        )
        scheduler = ApprovalExpiryScheduler(config)
        
        await scheduler.start_scheduler()
        
        try:
            status = scheduler.get_scheduler_status()
            assert status["config"]["use_interval"] is False
            assert status["config"]["expiry_check_hour"] == 3
            assert status["config"]["expiry_check_minute"] == 30
            assert len(status["jobs"]) == 1
        
        finally:
            await scheduler.stop_scheduler()
