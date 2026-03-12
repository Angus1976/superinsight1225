"""
Tests for Output Sync Alert Service.

Validates alert triggering and failure rate monitoring.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from src.sync.push.output_sync_alert_service import OutputSyncAlertService
from src.sync.models import (
    SyncJobModel,
    SyncExecutionModel,
    SyncJobStatus,
    SyncExecutionStatus,
    SyncDirection,
    SyncFrequency,
    DataSourceModel,
    DataSourceType
)
from src.sync.monitoring.alert_rules import sync_alert_manager


@pytest.fixture
async def alert_service():
    """Create alert service."""
    return OutputSyncAlertService()


@pytest.fixture
async def output_sync_job(db_session):
    """Create output sync job."""
    # Create source
    source = DataSourceModel(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Test Source",
        source_type=DataSourceType.POSTGRESQL,
        connection_config={},
        created_at=datetime.utcnow()
    )
    db_session.add(source)
    
    # Create target
    target = DataSourceModel(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Test Target",
        source_type=DataSourceType.POSTGRESQL,
        connection_config={
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "user"
        },
        created_at=datetime.utcnow()
    )
    db_session.add(target)
    
    # Create job
    job = SyncJobModel(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Test Output Job",
        source_id=source.id,
        target_source_id=target.id,
        direction=SyncDirection.PUSH,
        frequency=SyncFrequency.MANUAL,
        status=SyncJobStatus.ACTIVE,
        created_at=datetime.utcnow()
    )
    db_session.add(job)
    await db_session.commit()
    
    return job


async def create_execution(
    db_session,
    job_id,
    status,
    started_at=None
):
    """Helper to create execution record."""
    execution = SyncExecutionModel(
        id=uuid4(),
        job_id=job_id,
        tenant_id="test-tenant",
        status=status,
        sync_direction="output",
        started_at=started_at or datetime.utcnow(),
        trigger_type="manual"
    )
    db_session.add(execution)
    await db_session.commit()
    return execution


class TestOutputSyncAlertService:
    """Test output sync alert service."""
    
    @pytest.mark.asyncio
    async def test_evaluate_job_no_executions(
        self,
        alert_service,
        output_sync_job,
        db_session
    ):
        """Test evaluation with no executions."""
        result = await alert_service.evaluate_job_failure_rate(
            output_sync_job.id
        )
        
        assert result["job_id"] == str(output_sync_job.id)
        assert result["total_executions"] == 0
        assert result["failed_executions"] == 0
        assert result["failure_rate"] == 0.0
        assert result["should_alert"] is False
    
    @pytest.mark.asyncio
    async def test_evaluate_job_low_failure_rate(
        self,
        alert_service,
        output_sync_job,
        db_session
    ):
        """Test evaluation with low failure rate."""
        # Create 10 successful executions
        for _ in range(10):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.COMPLETED
            )
        
        # Create 1 failed execution
        await create_execution(
            db_session,
            output_sync_job.id,
            SyncExecutionStatus.FAILED
        )
        
        result = await alert_service.evaluate_job_failure_rate(
            output_sync_job.id
        )
        
        assert result["total_executions"] == 11
        assert result["failed_executions"] == 1
        assert result["failure_rate"] < 0.20  # Below warning threshold
        assert result["should_alert"] is False
    
    @pytest.mark.asyncio
    async def test_evaluate_job_warning_threshold(
        self,
        alert_service,
        output_sync_job,
        db_session
    ):
        """Test evaluation at warning threshold."""
        # Create 8 successful executions
        for _ in range(8):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.COMPLETED
            )
        
        # Create 2 failed executions (20% failure rate)
        for _ in range(2):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.FAILED
            )
        
        result = await alert_service.evaluate_job_failure_rate(
            output_sync_job.id
        )
        
        assert result["total_executions"] == 10
        assert result["failed_executions"] == 2
        assert result["failure_rate"] == 0.20
        assert result["should_alert"] is True
        assert result["alert_level"] == "warning"
    
    @pytest.mark.asyncio
    async def test_evaluate_job_critical_threshold(
        self,
        alert_service,
        output_sync_job,
        db_session
    ):
        """Test evaluation at critical threshold."""
        # Create 5 successful executions
        for _ in range(5):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.COMPLETED
            )
        
        # Create 5 failed executions (50% failure rate)
        for _ in range(5):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.FAILED
            )
        
        result = await alert_service.evaluate_job_failure_rate(
            output_sync_job.id
        )
        
        assert result["total_executions"] == 10
        assert result["failed_executions"] == 5
        assert result["failure_rate"] == 0.50
        assert result["should_alert"] is True
        assert result["alert_level"] == "critical"
    
    @pytest.mark.asyncio
    async def test_evaluate_job_minimum_executions(
        self,
        alert_service,
        output_sync_job,
        db_session
    ):
        """Test that minimum executions required before alerting."""
        # Create only 3 executions (below minimum of 5)
        for _ in range(2):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.COMPLETED
            )
        
        await create_execution(
            db_session,
            output_sync_job.id,
            SyncExecutionStatus.FAILED
        )
        
        result = await alert_service.evaluate_job_failure_rate(
            output_sync_job.id
        )
        
        assert result["total_executions"] == 3
        assert result["failure_rate"] > 0.20  # High rate
        assert result["should_alert"] is False  # But below minimum
    
    @pytest.mark.asyncio
    async def test_evaluate_job_time_window(
        self,
        alert_service,
        output_sync_job,
        db_session
    ):
        """Test evaluation respects time window."""
        # Create old executions (outside window)
        old_time = datetime.utcnow() - timedelta(hours=48)
        for _ in range(5):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.FAILED,
                started_at=old_time
            )
        
        # Create recent successful executions
        for _ in range(10):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.COMPLETED
            )
        
        # Evaluate with 24-hour window
        result = await alert_service.evaluate_job_failure_rate(
            output_sync_job.id,
            window_hours=24
        )
        
        # Should only count recent executions
        assert result["total_executions"] == 10
        assert result["failed_executions"] == 0
        assert result["failure_rate"] == 0.0
    
    @pytest.mark.asyncio
    async def test_evaluate_job_not_found(
        self,
        alert_service
    ):
        """Test evaluation with non-existent job."""
        fake_id = uuid4()
        result = await alert_service.evaluate_job_failure_rate(fake_id)
        
        assert "error" in result
        assert result["error"] == "Job not found"
    
    @pytest.mark.asyncio
    async def test_check_target_connectivity_success(
        self,
        alert_service,
        output_sync_job
    ):
        """Test target connectivity check."""
        result = await alert_service.check_target_connectivity(
            output_sync_job.id
        )
        
        assert result["job_id"] == str(output_sync_job.id)
        assert result["target_id"] == str(output_sync_job.target_source_id)
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_check_target_connectivity_no_target(
        self,
        alert_service,
        db_session
    ):
        """Test connectivity check with no target configured."""
        # Create job without target
        source = DataSourceModel(
            id=uuid4(),
            tenant_id="test-tenant",
            name="Source",
            source_type=DataSourceType.POSTGRESQL,
            connection_config={},
            created_at=datetime.utcnow()
        )
        db_session.add(source)
        
        job = SyncJobModel(
            id=uuid4(),
            tenant_id="test-tenant",
            name="Job Without Target",
            source_id=source.id,
            target_source_id=None,  # No target
            direction=SyncDirection.PUSH,
            frequency=SyncFrequency.MANUAL,
            status=SyncJobStatus.ACTIVE,
            created_at=datetime.utcnow()
        )
        db_session.add(job)
        await db_session.commit()
        
        result = await alert_service.check_target_connectivity(job.id)
        
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_evaluate_all_output_jobs(
        self,
        alert_service,
        output_sync_job,
        db_session
    ):
        """Test evaluating all output jobs."""
        # Create executions for the job
        for _ in range(10):
            await create_execution(
                db_session,
                output_sync_job.id,
                SyncExecutionStatus.COMPLETED
            )
        
        results = await alert_service.evaluate_all_output_jobs(
            tenant_id="test-tenant"
        )
        
        assert len(results) >= 1
        assert any(r["job_id"] == str(output_sync_job.id) for r in results)
    
    def test_alert_rules_registered(self, alert_service):
        """Test that alert rules are registered."""
        # Check that output sync alert rules exist
        assert "output_sync_high_failure_rate" in sync_alert_manager.rules
        assert "output_sync_critical_failure_rate" in sync_alert_manager.rules
        assert "target_database_unreachable" in sync_alert_manager.rules
        
        # Verify rule configuration
        warning_rule = sync_alert_manager.rules["output_sync_high_failure_rate"]
        assert warning_rule.threshold == 0.20
        assert warning_rule.metric == "output_sync_failure_rate"
        
        critical_rule = sync_alert_manager.rules["output_sync_critical_failure_rate"]
        assert critical_rule.threshold == 0.50


class TestAlertThresholds:
    """Test alert threshold configuration."""
    
    def test_default_thresholds(self):
        """Test default threshold values."""
        service = OutputSyncAlertService()
        
        assert service.DEFAULT_FAILURE_RATE_WARNING == 0.20
        assert service.DEFAULT_FAILURE_RATE_CRITICAL == 0.50
        assert service.DEFAULT_EVALUATION_WINDOW_HOURS == 24
        assert service.DEFAULT_MIN_EXECUTIONS == 5
