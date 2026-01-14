"""
Property-based tests for Sync Scheduler.

Tests Property 13: Job status tracking
Tests Property 14: Sync history completeness
"""

import pytest
from hypothesis import given, strategies as st, settings
import asyncio
from datetime import datetime, timedelta

from src.sync.pipeline.enums import JobStatus
from src.sync.pipeline.schemas import ScheduleConfig
from src.sync.pipeline.scheduler import SyncScheduler


# ============================================================================
# Test Helpers
# ============================================================================

def create_scheduler():
    """Create a sync scheduler without dependencies."""
    return SyncScheduler()


def create_schedule_config(
    cron_expression: str = "*/5 * * * *",
    priority: int = 0,
    enabled: bool = True
) -> ScheduleConfig:
    """Create a schedule configuration."""
    return ScheduleConfig(
        cron_expression=cron_expression,
        priority=priority,
        enabled=enabled
    )


# ============================================================================
# Property 13: Job Status Tracking
# Validates: Requirements 7.3
# ============================================================================

@settings(max_examples=100)
@given(
    job_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    ),
    source_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    )
)
def test_new_job_status_is_pending(job_id: str, source_id: str):
    """
    Property 13: New job status is PENDING
    
    When a new job is scheduled, its initial status should be PENDING.
    
    **Validates: Requirements 7.3**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        job = await scheduler.schedule(job_id, source_id, config)
        
        assert job.status == JobStatus.PENDING
        
        # Verify via get_status
        status = await scheduler.get_status(job_id)
        assert status == JobStatus.PENDING
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    job_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    )
)
def test_status_update_reflects_correctly(job_id: str):
    """
    Property 13: Status updates are reflected correctly
    
    When a job status is updated, get_status should return the new status.
    
    **Validates: Requirements 7.3**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule(job_id, "source1", config)
        
        # Update to RUNNING
        await scheduler.update_status(job_id, JobStatus.RUNNING)
        assert await scheduler.get_status(job_id) == JobStatus.RUNNING
        
        # Update to COMPLETED
        await scheduler.update_status(job_id, JobStatus.COMPLETED)
        assert await scheduler.get_status(job_id) == JobStatus.COMPLETED
        
        # Update to FAILED
        await scheduler.update_status(job_id, JobStatus.FAILED)
        assert await scheduler.get_status(job_id) == JobStatus.FAILED
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=50)
@given(
    job_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    )
)
def test_manual_trigger_updates_status(job_id: str):
    """
    Property 13: Manual trigger updates status correctly
    
    When a job is manually triggered, status should transition through
    RUNNING and end at COMPLETED or FAILED.
    
    **Validates: Requirements 7.3**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule(job_id, "source1", config)
        
        # Trigger manual sync
        result = await scheduler.trigger_manual(job_id)
        
        # Status should be COMPLETED (no data puller, so simulated success)
        status = await scheduler.get_status(job_id)
        assert status in [JobStatus.COMPLETED, JobStatus.FAILED]
        
        # Result should match status
        if result.success:
            assert status == JobStatus.COMPLETED
        else:
            assert status == JobStatus.FAILED
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_nonexistent_job_status_is_none():
    """
    Property 13: Nonexistent job status is None
    
    **Validates: Requirements 7.3**
    """
    async def run_test():
        scheduler = create_scheduler()
        
        status = await scheduler.get_status("nonexistent_job")
        assert status is None
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Property 14: Sync History Completeness
# Validates: Requirements 7.6
# ============================================================================

@settings(max_examples=50)
@given(
    job_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    ),
    trigger_count=st.integers(min_value=1, max_value=10)
)
def test_history_records_all_executions(job_id: str, trigger_count: int):
    """
    Property 14: History records all executions
    
    Every job execution should create a history record.
    
    **Validates: Requirements 7.6**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule(job_id, "source1", config)
        
        # Trigger multiple times
        for _ in range(trigger_count):
            await scheduler.trigger_manual(job_id)
        
        # Check history count
        history = await scheduler.get_history(job_id)
        assert len(history) == trigger_count
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=50)
@given(
    job_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    )
)
def test_history_record_has_required_fields(job_id: str):
    """
    Property 14: History record has all required fields
    
    Each history record should have started_at, completed_at, status, rows_synced.
    
    **Validates: Requirements 7.6**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule(job_id, "source1", config)
        await scheduler.trigger_manual(job_id)
        
        history = await scheduler.get_history(job_id)
        assert len(history) == 1
        
        record = history[0]
        assert record.job_id == job_id
        assert record.started_at is not None
        assert record.completed_at is not None
        assert record.status in [JobStatus.COMPLETED, JobStatus.FAILED]
        assert record.rows_synced >= 0
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=50)
@given(
    job_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    )
)
def test_history_ordered_by_time(job_id: str):
    """
    Property 14: History is ordered by time (most recent first)
    
    **Validates: Requirements 7.6**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule(job_id, "source1", config)
        
        # Trigger multiple times
        for _ in range(5):
            await scheduler.trigger_manual(job_id)
        
        history = await scheduler.get_history(job_id)
        
        # Verify ordering (most recent first)
        for i in range(len(history) - 1):
            assert history[i].started_at >= history[i + 1].started_at
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=50)
@given(
    limit=st.integers(min_value=1, max_value=10)
)
def test_history_respects_limit(limit: int):
    """
    Property 14: History respects limit parameter
    
    **Validates: Requirements 7.6**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule("job1", "source1", config)
        
        # Trigger more times than limit
        for _ in range(limit + 5):
            await scheduler.trigger_manual("job1")
        
        history = await scheduler.get_history("job1", limit=limit)
        assert len(history) == limit
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_history_empty_for_new_job():
    """
    Property 14: History is empty for new job
    
    **Validates: Requirements 7.6**
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule("job1", "source1", config)
        
        history = await scheduler.get_history("job1")
        assert len(history) == 0
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Priority Management Tests
# ============================================================================

@settings(max_examples=100)
@given(
    priority=st.integers(min_value=0, max_value=10)
)
def test_priority_set_correctly(priority: int):
    """
    Test that priority is set correctly.
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config(priority=priority)
        
        job = await scheduler.schedule("job1", "source1", config)
        
        assert job.config.priority == priority
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    new_priority=st.integers(min_value=-5, max_value=15)
)
def test_priority_update_clamped(new_priority: int):
    """
    Test that priority updates are clamped to valid range.
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule("job1", "source1", config)
        await scheduler.set_priority("job1", new_priority)
        
        job = scheduler.get_job("job1")
        # Priority should be clamped to 0-10
        assert 0 <= job.config.priority <= 10
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_jobs_sorted_by_priority():
    """
    Test that list_jobs returns jobs sorted by priority.
    """
    async def run_test():
        scheduler = create_scheduler()
        
        # Create jobs with different priorities
        await scheduler.schedule("job_low", "source1", create_schedule_config(priority=1))
        await scheduler.schedule("job_high", "source2", create_schedule_config(priority=9))
        await scheduler.schedule("job_mid", "source3", create_schedule_config(priority=5))
        
        jobs = await scheduler.list_jobs()
        
        # Should be sorted by priority descending
        assert jobs[0].job_id == "job_high"
        assert jobs[1].job_id == "job_mid"
        assert jobs[2].job_id == "job_low"
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Job Management Tests
# ============================================================================

def test_enable_disable_job():
    """
    Test enabling and disabling jobs.
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config(enabled=True)
        
        job = await scheduler.schedule("job1", "source1", config)
        assert job.config.enabled is True
        assert job.next_run_at is not None
        
        # Disable
        await scheduler.disable_job("job1")
        job = scheduler.get_job("job1")
        assert job.config.enabled is False
        assert job.next_run_at is None
        
        # Enable
        await scheduler.enable_job("job1")
        job = scheduler.get_job("job1")
        assert job.config.enabled is True
        assert job.next_run_at is not None
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_delete_job():
    """
    Test deleting a job.
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        await scheduler.schedule("job1", "source1", config)
        assert scheduler.job_count == 1
        
        result = await scheduler.delete_job("job1")
        assert result is True
        assert scheduler.job_count == 0
        assert scheduler.get_job("job1") is None
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_delete_nonexistent_job():
    """
    Test deleting a nonexistent job.
    """
    async def run_test():
        scheduler = create_scheduler()
        
        result = await scheduler.delete_job("nonexistent")
        assert result is False
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_list_jobs_by_status():
    """
    Test filtering jobs by status.
    """
    async def run_test():
        scheduler = create_scheduler()
        
        await scheduler.schedule("job1", "source1", create_schedule_config())
        await scheduler.schedule("job2", "source2", create_schedule_config())
        
        # Trigger one job to change its status
        await scheduler.trigger_manual("job1")
        
        # List all
        all_jobs = await scheduler.list_jobs()
        assert len(all_jobs) == 2
        
        # List by status
        completed_jobs = await scheduler.list_jobs(status=JobStatus.COMPLETED)
        assert len(completed_jobs) == 1
        assert completed_jobs[0].job_id == "job1"
        
        pending_jobs = await scheduler.list_jobs(status=JobStatus.PENDING)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].job_id == "job2"
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Edge Cases
# ============================================================================

def test_trigger_nonexistent_job():
    """
    Test triggering a nonexistent job.
    """
    async def run_test():
        scheduler = create_scheduler()
        
        result = await scheduler.trigger_manual("nonexistent")
        
        assert result.success is False
        assert "not found" in result.error_message
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_job_timestamps_updated():
    """
    Test that job timestamps are updated after execution.
    """
    async def run_test():
        scheduler = create_scheduler()
        config = create_schedule_config()
        
        job = await scheduler.schedule("job1", "source1", config)
        assert job.last_run_at is None
        
        await scheduler.trigger_manual("job1")
        
        job = scheduler.get_job("job1")
        assert job.last_run_at is not None
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_active_job_count():
    """
    Test active job count property.
    """
    async def run_test():
        scheduler = create_scheduler()
        
        await scheduler.schedule("job1", "source1", create_schedule_config(enabled=True))
        await scheduler.schedule("job2", "source2", create_schedule_config(enabled=False))
        await scheduler.schedule("job3", "source3", create_schedule_config(enabled=True))
        
        assert scheduler.job_count == 3
        assert scheduler.active_job_count == 2
    
    asyncio.get_event_loop().run_until_complete(run_test())
