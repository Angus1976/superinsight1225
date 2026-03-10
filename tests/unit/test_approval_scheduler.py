"""
Unit tests for Approval Expiry Scheduler.

Tests the scheduling mechanism for automatic approval expiry.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from src.services.approval_scheduler import (
    ApprovalExpiryScheduler,
    ApprovalScheduleConfig,
    get_approval_scheduler,
    start_approval_scheduler,
    stop_approval_scheduler
)


class TestApprovalScheduleConfig:
    """Test ApprovalScheduleConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ApprovalScheduleConfig()
        
        assert config.expiry_check_hour == 1
        assert config.expiry_check_minute == 0
        assert config.use_interval is False
        assert config.interval_hours == 6
        assert config.enable_expiry_check is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ApprovalScheduleConfig(
            expiry_check_hour=3,
            expiry_check_minute=30,
            use_interval=True,
            interval_hours=12,
            enable_expiry_check=False
        )
        
        assert config.expiry_check_hour == 3
        assert config.expiry_check_minute == 30
        assert config.use_interval is True
        assert config.interval_hours == 12
        assert config.enable_expiry_check is False


class TestApprovalExpiryScheduler:
    """Test ApprovalExpiryScheduler class."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance for testing."""
        return ApprovalExpiryScheduler()
    
    @pytest.fixture
    def custom_scheduler(self):
        """Create a scheduler with custom config."""
        config = ApprovalScheduleConfig(
            expiry_check_hour=2,
            expiry_check_minute=15,
            use_interval=False
        )
        return ApprovalExpiryScheduler(config)
    
    def test_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.is_running is False
        assert scheduler.last_run is None
        assert scheduler.last_expired_count == 0
        assert scheduler.total_runs == 0
        assert scheduler.total_expired == 0
        assert scheduler.schedule_config is not None
    
    def test_initialization_with_custom_config(self, custom_scheduler):
        """Test scheduler initialization with custom config."""
        assert custom_scheduler.schedule_config.expiry_check_hour == 2
        assert custom_scheduler.schedule_config.expiry_check_minute == 15
        assert custom_scheduler.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_scheduler_cron_mode(self, scheduler):
        """Test starting scheduler in cron mode."""
        await scheduler.start_scheduler()
        
        assert scheduler.is_running is True
        assert scheduler.scheduler.running is True
        
        # Check that job was added
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == 'approval_expiry_check'
        assert jobs[0].name == 'Approval Expiry Check'
        
        # Cleanup
        await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_interval_mode(self):
        """Test starting scheduler in interval mode."""
        config = ApprovalScheduleConfig(
            use_interval=True,
            interval_hours=4
        )
        scheduler = ApprovalExpiryScheduler(config)
        
        await scheduler.start_scheduler()
        
        assert scheduler.is_running is True
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        
        # Cleanup
        await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_disabled(self):
        """Test starting scheduler when disabled in config."""
        config = ApprovalScheduleConfig(enable_expiry_check=False)
        scheduler = ApprovalExpiryScheduler(config)
        
        await scheduler.start_scheduler()
        
        # Should not start when disabled
        assert scheduler.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self, scheduler):
        """Test starting scheduler when already running."""
        await scheduler.start_scheduler()
        assert scheduler.is_running is True
        
        # Try to start again
        await scheduler.start_scheduler()
        
        # Should still be running with only one job
        assert scheduler.is_running is True
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        
        # Cleanup
        await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler):
        """Test stopping the scheduler."""
        await scheduler.start_scheduler()
        assert scheduler.is_running is True
        
        await scheduler.stop_scheduler()
        
        assert scheduler.is_running is False
        # Note: APScheduler may take a moment to fully stop
        # We only check our internal flag
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self, scheduler):
        """Test stopping scheduler when not running."""
        assert scheduler.is_running is False
        
        # Should not raise error
        await scheduler.stop_scheduler()
        
        assert scheduler.is_running is False
    
    @pytest.mark.asyncio
    @patch('src.services.approval_scheduler.db_manager')
    @patch('src.services.approval_service.ApprovalService')
    async def test_run_expiry_check(self, mock_service_class, mock_db_manager, scheduler):
        """Test running the expiry check task."""
        # Mock database session
        mock_session = Mock(spec=Session)
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock ApprovalService
        mock_service = Mock()
        mock_service.expire_old_approvals.return_value = 5
        mock_service_class.return_value = mock_service
        
        # Run the check
        await scheduler._run_expiry_check()
        
        # Verify service was called
        mock_service_class.assert_called_once_with(mock_session)
        mock_service.expire_old_approvals.assert_called_once()
        
        # Verify statistics updated
        assert scheduler.last_run is not None
        assert scheduler.last_expired_count == 5
        assert scheduler.total_runs == 1
        assert scheduler.total_expired == 5
    
    @pytest.mark.asyncio
    @patch('src.services.approval_scheduler.db_manager')
    @patch('src.services.approval_service.ApprovalService')
    async def test_run_expiry_check_no_expired(self, mock_service_class, mock_db_manager, scheduler):
        """Test running expiry check when no approvals expired."""
        mock_session = Mock(spec=Session)
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        mock_service = Mock()
        mock_service.expire_old_approvals.return_value = 0
        mock_service_class.return_value = mock_service
        
        await scheduler._run_expiry_check()
        
        assert scheduler.last_expired_count == 0
        assert scheduler.total_runs == 1
        assert scheduler.total_expired == 0
    
    @pytest.mark.asyncio
    @patch('src.services.approval_scheduler.db_manager')
    @patch('src.services.approval_service.ApprovalService')
    async def test_run_expiry_check_multiple_runs(self, mock_service_class, mock_db_manager, scheduler):
        """Test running expiry check multiple times."""
        mock_session = Mock(spec=Session)
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        mock_service = Mock()
        mock_service.expire_old_approvals.side_effect = [3, 5, 2]
        mock_service_class.return_value = mock_service
        
        # Run three times
        await scheduler._run_expiry_check()
        await scheduler._run_expiry_check()
        await scheduler._run_expiry_check()
        
        # Verify cumulative statistics
        assert scheduler.total_runs == 3
        assert scheduler.total_expired == 10  # 3 + 5 + 2
        assert scheduler.last_expired_count == 2
    
    @pytest.mark.asyncio
    @patch('src.services.approval_scheduler.db_manager')
    @patch('src.services.approval_service.ApprovalService')
    async def test_run_expiry_check_error_handling(self, mock_service_class, mock_db_manager, scheduler):
        """Test error handling in expiry check."""
        mock_session = Mock(spec=Session)
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        mock_service = Mock()
        mock_service.expire_old_approvals.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        # Should raise exception
        with pytest.raises(Exception, match="Database error"):
            await scheduler._run_expiry_check()
    
    @pytest.mark.asyncio
    @patch('src.services.approval_scheduler.db_manager')
    @patch('src.services.approval_service.ApprovalService')
    async def test_run_manual_check(self, mock_service_class, mock_db_manager, scheduler):
        """Test manual expiry check."""
        await scheduler.start_scheduler()
        
        mock_session = Mock(spec=Session)
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        mock_service = Mock()
        mock_service.expire_old_approvals.return_value = 7
        mock_service_class.return_value = mock_service
        
        result = await scheduler.run_manual_check()
        
        assert result["success"] is True
        assert result["expired_count"] == 7
        assert "duration_seconds" in result
        assert "timestamp" in result
        
        await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_run_manual_check_not_running(self, scheduler):
        """Test manual check when scheduler not running."""
        with pytest.raises(RuntimeError, match="Scheduler is not running"):
            await scheduler.run_manual_check()
    
    @pytest.mark.asyncio
    @patch('src.services.approval_scheduler.db_manager')
    @patch('src.services.approval_service.ApprovalService')
    async def test_run_manual_check_error(self, mock_service_class, mock_db_manager, scheduler):
        """Test manual check error handling."""
        await scheduler.start_scheduler()
        
        mock_session = Mock(spec=Session)
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        mock_service = Mock()
        mock_service.expire_old_approvals.side_effect = Exception("Test error")
        mock_service_class.return_value = mock_service
        
        result = await scheduler.run_manual_check()
        
        assert result["success"] is False
        assert "Test error" in result["error"]
        assert "timestamp" in result
        
        await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_get_scheduler_status_not_running(self, scheduler):
        """Test getting status when scheduler not running."""
        status = scheduler.get_scheduler_status()
        
        assert status["is_running"] is False
        assert status["config"]["expiry_check_hour"] == 1
        assert status["config"]["expiry_check_minute"] == 0
        assert status["config"]["use_interval"] is False
        assert status["statistics"]["last_run"] is None
        assert status["statistics"]["total_runs"] == 0
        assert status["jobs"] == []
    
    @pytest.mark.asyncio
    async def test_get_scheduler_status_running(self, scheduler):
        """Test getting status when scheduler is running."""
        await scheduler.start_scheduler()
        
        status = scheduler.get_scheduler_status()
        
        assert status["is_running"] is True
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == "approval_expiry_check"
        assert status["jobs"][0]["name"] == "Approval Expiry Check"
        assert status["jobs"][0]["next_run"] is not None
        
        await scheduler.stop_scheduler()
    
    @pytest.mark.asyncio
    @patch('src.services.approval_scheduler.db_manager')
    @patch('src.services.approval_service.ApprovalService')
    async def test_get_scheduler_status_after_run(self, mock_service_class, mock_db_manager, scheduler):
        """Test getting status after running expiry check."""
        mock_session = Mock(spec=Session)
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        mock_service = Mock()
        mock_service.expire_old_approvals.return_value = 3
        mock_service_class.return_value = mock_service
        
        await scheduler._run_expiry_check()
        
        status = scheduler.get_scheduler_status()
        
        assert status["statistics"]["last_run"] is not None
        assert status["statistics"]["last_expired_count"] == 3
        assert status["statistics"]["total_runs"] == 1
        assert status["statistics"]["total_expired"] == 3


class TestGlobalSchedulerFunctions:
    """Test global scheduler management functions."""
    
    @pytest.mark.asyncio
    async def test_get_approval_scheduler(self):
        """Test getting global scheduler instance."""
        # Reset global instance
        import src.services.approval_scheduler as scheduler_module
        scheduler_module._approval_scheduler = None
        
        scheduler = await get_approval_scheduler()
        
        assert scheduler is not None
        assert scheduler.is_running is True
        
        # Get again - should return same instance
        scheduler2 = await get_approval_scheduler()
        assert scheduler2 is scheduler
        
        # Cleanup
        await stop_approval_scheduler()
    
    @pytest.mark.asyncio
    async def test_start_approval_scheduler(self):
        """Test starting global scheduler."""
        import src.services.approval_scheduler as scheduler_module
        scheduler_module._approval_scheduler = None
        
        config = ApprovalScheduleConfig(expiry_check_hour=3)
        await start_approval_scheduler(config)
        
        assert scheduler_module._approval_scheduler is not None
        assert scheduler_module._approval_scheduler.is_running is True
        assert scheduler_module._approval_scheduler.schedule_config.expiry_check_hour == 3
        
        # Cleanup
        await stop_approval_scheduler()
    
    @pytest.mark.asyncio
    async def test_start_approval_scheduler_already_running(self):
        """Test starting scheduler when already running."""
        import src.services.approval_scheduler as scheduler_module
        scheduler_module._approval_scheduler = None
        
        await start_approval_scheduler()
        first_scheduler = scheduler_module._approval_scheduler
        
        # Try to start again
        await start_approval_scheduler()
        
        # Should be same instance
        assert scheduler_module._approval_scheduler is first_scheduler
        
        # Cleanup
        await stop_approval_scheduler()
    
    @pytest.mark.asyncio
    async def test_stop_approval_scheduler(self):
        """Test stopping global scheduler."""
        import src.services.approval_scheduler as scheduler_module
        scheduler_module._approval_scheduler = None
        
        await start_approval_scheduler()
        assert scheduler_module._approval_scheduler is not None
        
        await stop_approval_scheduler()
        
        assert scheduler_module._approval_scheduler is None
    
    @pytest.mark.asyncio
    async def test_stop_approval_scheduler_not_started(self):
        """Test stopping scheduler when not started."""
        import src.services.approval_scheduler as scheduler_module
        scheduler_module._approval_scheduler = None
        
        # Should not raise error
        await stop_approval_scheduler()
        
        assert scheduler_module._approval_scheduler is None
