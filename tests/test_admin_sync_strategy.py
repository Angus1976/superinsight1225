"""
Tests for Sync Strategy Service.

Tests the data synchronization strategy management functionality.

**Feature: admin-configuration**
**Validates: Requirements 4.1, 4.2, 4.3, 4.6, 4.7**
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from uuid import uuid4

from src.admin.sync_strategy import SyncStrategyService, get_sync_strategy_service
from src.admin.schemas import (
    SyncMode,
    SyncStrategyCreate,
    SyncStrategyUpdate,
    FilterCondition,
)


# ========== Custom Strategies ==========

def sync_strategy_create_strategy():
    """Strategy for generating sync strategy create requests."""
    return st.builds(
        SyncStrategyCreate,
        db_config_id=st.uuids().map(str),
        mode=st.sampled_from(list(SyncMode)),
        batch_size=st.integers(min_value=1, max_value=100000),
        enabled=st.booleans(),
    )


class TestSyncStrategyServiceCRUD:
    """Tests for sync strategy CRUD operations."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        service = SyncStrategyService()
        service.clear_in_memory_storage()
        return service
    
    @given(strategy=sync_strategy_create_strategy())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_save_and_get_strategy(self, strategy: SyncStrategyCreate):
        """Saved strategy should be retrievable."""
        service = SyncStrategyService()
        service.clear_in_memory_storage()
        
        # Add incremental_field if mode is incremental
        if strategy.mode == SyncMode.INCREMENTAL:
            strategy = SyncStrategyCreate(
                db_config_id=strategy.db_config_id,
                mode=strategy.mode,
                incremental_field="updated_at",
                batch_size=strategy.batch_size,
                enabled=strategy.enabled,
            )
        
        user_id = str(uuid4())
        
        saved = await service.save_strategy(
            strategy=strategy,
            user_id=user_id,
            user_name="Test User",
        )
        
        assert saved.id is not None
        assert saved.db_config_id == strategy.db_config_id
        assert saved.mode == strategy.mode
        
        retrieved = await service.get_strategy(saved.id)
        
        assert retrieved is not None
        assert retrieved.id == saved.id
    
    @pytest.mark.asyncio
    async def test_save_strategy_validates(self, service):
        """Invalid strategy should raise error."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.INCREMENTAL,
            # Missing incremental_field for incremental mode
        )
        
        with pytest.raises(ValueError) as exc_info:
            await service.save_strategy(strategy=strategy, user_id="user-1")
        
        assert "Invalid sync strategy" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_strategies(self, service):
        """Should list all strategies."""
        db_config_id = str(uuid4())
        
        for i in range(3):
            strategy = SyncStrategyCreate(
                db_config_id=db_config_id,
                mode=SyncMode.FULL,
                name=f"Strategy {i}",
            )
            await service.save_strategy(strategy=strategy, user_id="user-1")
        
        strategies = await service.list_strategies()
        
        assert len(strategies) == 3
    
    @pytest.mark.asyncio
    async def test_list_strategies_enabled_only(self, service):
        """Should filter by enabled status."""
        # Create enabled strategy
        enabled = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            enabled=True,
        )
        await service.save_strategy(strategy=enabled, user_id="user-1")
        
        # Create disabled strategy
        disabled = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            enabled=False,
        )
        await service.save_strategy(strategy=disabled, user_id="user-1")
        
        # List enabled only
        strategies = await service.list_strategies(enabled_only=True)
        
        assert len(strategies) == 1
        assert strategies[0].enabled is True
    
    @pytest.mark.asyncio
    async def test_delete_strategy(self, service):
        """Should delete strategy."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
        )
        
        saved = await service.save_strategy(strategy=strategy, user_id="user-1")
        
        result = await service.delete_strategy(
            strategy_id=saved.id,
            user_id="user-1",
        )
        
        assert result is True
        
        retrieved = await service.get_strategy(saved.id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_strategy(self, service):
        """Deleting non-existent strategy should return False."""
        result = await service.delete_strategy(
            strategy_id="nonexistent",
            user_id="user-1",
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_strategy_by_db_config(self, service):
        """Should get strategy by db_config_id."""
        db_config_id = str(uuid4())
        
        strategy = SyncStrategyCreate(
            db_config_id=db_config_id,
            mode=SyncMode.FULL,
        )
        
        await service.save_strategy(strategy=strategy, user_id="user-1")
        
        retrieved = await service.get_strategy_by_db_config(db_config_id)
        
        assert retrieved is not None
        assert retrieved.db_config_id == db_config_id


class TestSyncStrategyServiceUpdate:
    """Tests for sync strategy updates."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        service = SyncStrategyService()
        service.clear_in_memory_storage()
        return service
    
    @pytest.mark.asyncio
    async def test_update_strategy(self, service):
        """Should update existing strategy."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            batch_size=1000,
        )
        
        saved = await service.save_strategy(strategy=strategy, user_id="user-1")
        
        update = SyncStrategyUpdate(
            batch_size=5000,
            enabled=False,
        )
        
        updated = await service.save_strategy(
            strategy=update,
            user_id="user-1",
            strategy_id=saved.id,
        )
        
        assert updated.id == saved.id
        assert updated.batch_size == 5000
        assert updated.enabled is False
        # Unchanged fields should remain
        assert updated.mode == SyncMode.FULL
    
    @pytest.mark.asyncio
    async def test_update_records_history(self, service):
        """Update should record history."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
        )
        
        saved = await service.save_strategy(strategy=strategy, user_id="user-1")
        
        update = SyncStrategyUpdate(batch_size=5000)
        
        await service.save_strategy(
            strategy=update,
            user_id="user-2",
            strategy_id=saved.id,
        )
        
        # Check history
        from src.admin.schemas import ConfigType
        history = await service._history_tracker.get_history(
            config_type=ConfigType.SYNC_STRATEGY
        )
        
        assert len(history) == 2  # Create and update


class TestSyncStrategyServiceSync:
    """Tests for sync triggering and history."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        service = SyncStrategyService()
        service.clear_in_memory_storage()
        return service
    
    @pytest.mark.asyncio
    async def test_trigger_sync(self, service):
        """Should trigger sync job."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            enabled=True,
        )
        
        saved = await service.save_strategy(strategy=strategy, user_id="user-1")
        
        job = await service.trigger_sync(
            strategy_id=saved.id,
            user_id="user-1",
        )
        
        assert job.job_id is not None
        assert job.strategy_id == saved.id
        assert job.status == "running"
    
    @pytest.mark.asyncio
    async def test_trigger_sync_disabled_strategy(self, service):
        """Should not trigger sync for disabled strategy."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            enabled=False,
        )
        
        saved = await service.save_strategy(strategy=strategy, user_id="user-1")
        
        with pytest.raises(ValueError) as exc_info:
            await service.trigger_sync(strategy_id=saved.id, user_id="user-1")
        
        assert "disabled" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_trigger_sync_nonexistent_strategy(self, service):
        """Should raise error for non-existent strategy."""
        with pytest.raises(ValueError) as exc_info:
            await service.trigger_sync(strategy_id="nonexistent", user_id="user-1")
        
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_sync_history(self, service):
        """Should get sync history."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            enabled=True,
        )
        
        saved = await service.save_strategy(strategy=strategy, user_id="user-1")
        
        # Trigger some syncs
        await service.trigger_sync(strategy_id=saved.id, user_id="user-1")
        await service.trigger_sync(strategy_id=saved.id, user_id="user-1")
        
        history = await service.get_sync_history(saved.id)
        
        assert len(history) == 2
    
    @pytest.mark.asyncio
    async def test_retry_sync(self, service):
        """Should retry failed sync."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            enabled=True,
        )
        
        saved = await service.save_strategy(strategy=strategy, user_id="user-1")
        
        # Trigger initial sync
        job = await service.trigger_sync(strategy_id=saved.id, user_id="user-1")
        
        # Retry
        retry_job = await service.retry_sync(job_id=job.job_id, user_id="user-1")
        
        assert retry_job.job_id != job.job_id  # New job ID
        assert retry_job.strategy_id == saved.id


class TestSyncStrategyServiceValidation:
    """Tests for strategy validation."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        return SyncStrategyService()
    
    def test_validate_valid_full_strategy(self, service):
        """Valid full sync strategy should pass."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            batch_size=1000,
        )
        
        result = service.validate_strategy(strategy)
        
        assert result.is_valid
    
    def test_validate_valid_incremental_strategy(self, service):
        """Valid incremental strategy should pass."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.INCREMENTAL,
            incremental_field="updated_at",
            batch_size=1000,
        )
        
        result = service.validate_strategy(strategy)
        
        assert result.is_valid
    
    def test_validate_incremental_without_field(self, service):
        """Incremental without field should fail."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.INCREMENTAL,
            # Missing incremental_field
        )
        
        result = service.validate_strategy(strategy)
        
        assert not result.is_valid
        assert any(e.field == "incremental_field" for e in result.errors)
    
    def test_validate_invalid_batch_size(self, service):
        """Invalid batch size should fail."""
        strategy = {
            "db_config_id": str(uuid4()),
            "mode": "full",
            "batch_size": 0,  # Invalid
        }
        
        result = service.validate_strategy(strategy)
        
        assert not result.is_valid
        assert any(e.field == "batch_size" for e in result.errors)
    
    def test_validate_valid_schedule(self, service):
        """Valid cron schedule should pass."""
        strategy = SyncStrategyCreate(
            db_config_id=str(uuid4()),
            mode=SyncMode.FULL,
            schedule="0 * * * *",  # Every hour
        )
        
        result = service.validate_strategy(strategy)
        
        assert result.is_valid
    
    def test_validate_invalid_schedule(self, service):
        """Invalid cron schedule should fail."""
        strategy = {
            "db_config_id": str(uuid4()),
            "mode": "full",
            "schedule": "invalid cron",
        }
        
        result = service.validate_strategy(strategy)
        
        assert not result.is_valid
        assert any(e.field == "schedule" for e in result.errors)


class TestSyncStrategyServiceSingleton:
    """Tests for singleton behavior."""
    
    def test_get_sync_strategy_service_singleton(self):
        """get_sync_strategy_service should return the same instance."""
        service1 = get_sync_strategy_service()
        service2 = get_sync_strategy_service()
        
        assert service1 is service2
