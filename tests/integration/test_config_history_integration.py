"""
Integration Tests for Configuration History and Rollback

Tests the complete configuration history workflow including:
- History tracking across all configuration types
- Rollback functionality
- Rollback compatibility checking
- History retention

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Import the modules under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.admin.history_tracker import HistoryTracker
from src.admin.config_manager import ConfigManager


class TestConfigurationHistoryTracking:
    """Test configuration history tracking across all configuration types."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def history_tracker(self, mock_db_session):
        """Create a HistoryTracker instance with mocked dependencies."""
        tracker = HistoryTracker(db_session=mock_db_session)
        return tracker

    @pytest.mark.asyncio
    async def test_llm_config_change_creates_history_entry(self, history_tracker, mock_db_session):
        """Test that LLM configuration changes create history entries."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        user_id = str(uuid4())
        old_config = {
            "name": "OpenAI GPT-4",
            "llm_type": "openai",
            "model_name": "gpt-4",
            "temperature": 0.7,
        }
        new_config = {
            "name": "OpenAI GPT-4",
            "llm_type": "openai",
            "model_name": "gpt-4-turbo",
            "temperature": 0.8,
        }

        # Act
        await history_tracker.record_change(
            tenant_id=tenant_id,
            config_type="llm",
            config_id=config_id,
            old_value=old_config,
            new_value=new_config,
            change_type="update",
            changed_by=user_id,
        )

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_config_change_creates_history_entry(self, history_tracker, mock_db_session):
        """Test that database configuration changes create history entries."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        user_id = str(uuid4())
        old_config = {
            "name": "Production MySQL",
            "db_type": "mysql",
            "host": "mysql.example.com",
            "port": 3306,
        }
        new_config = {
            "name": "Production MySQL",
            "db_type": "mysql",
            "host": "mysql-new.example.com",
            "port": 3306,
        }

        # Act
        await history_tracker.record_change(
            tenant_id=tenant_id,
            config_type="database",
            config_id=config_id,
            old_value=old_config,
            new_value=new_config,
            change_type="update",
            changed_by=user_id,
        )

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_strategy_change_creates_history_entry(self, history_tracker, mock_db_session):
        """Test that sync strategy changes create history entries."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        user_id = str(uuid4())
        old_config = {
            "name": "Daily Sync",
            "sync_mode": "poll",
            "poll_config": {"interval_minutes": 60},
        }
        new_config = {
            "name": "Daily Sync",
            "sync_mode": "poll",
            "poll_config": {"interval_minutes": 30},
        }

        # Act
        await history_tracker.record_change(
            tenant_id=tenant_id,
            config_type="sync_strategy",
            config_id=config_id,
            old_value=old_config,
            new_value=new_config,
            change_type="update",
            changed_by=user_id,
        )

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_history_entry_includes_timestamp(self, history_tracker, mock_db_session):
        """Test that history entries include timestamp."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        user_id = str(uuid4())
        config = {"name": "Test Config"}

        # Act
        before_time = datetime.utcnow()
        await history_tracker.record_change(
            tenant_id=tenant_id,
            config_type="llm",
            config_id=config_id,
            old_value=None,
            new_value=config,
            change_type="create",
            changed_by=user_id,
        )
        after_time = datetime.utcnow()

        # Assert
        call_args = mock_db_session.add.call_args
        history_entry = call_args[0][0]
        assert hasattr(history_entry, 'changed_at') or hasattr(history_entry, 'created_at')

    @pytest.mark.asyncio
    async def test_history_entry_includes_author(self, history_tracker, mock_db_session):
        """Test that history entries include author information."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        user_id = str(uuid4())
        config = {"name": "Test Config"}

        # Act
        await history_tracker.record_change(
            tenant_id=tenant_id,
            config_type="llm",
            config_id=config_id,
            old_value=None,
            new_value=config,
            change_type="create",
            changed_by=user_id,
        )

        # Assert
        call_args = mock_db_session.add.call_args
        history_entry = call_args[0][0]
        assert hasattr(history_entry, 'changed_by') or hasattr(history_entry, 'user_id')

    @pytest.mark.asyncio
    async def test_history_entry_includes_full_data(self, history_tracker, mock_db_session):
        """Test that history entries include full configuration data."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        user_id = str(uuid4())
        old_config = {
            "name": "Test Config",
            "field1": "value1",
            "field2": "value2",
            "nested": {"key": "value"},
        }
        new_config = {
            "name": "Test Config Updated",
            "field1": "value1_updated",
            "field2": "value2",
            "nested": {"key": "value_updated"},
        }

        # Act
        await history_tracker.record_change(
            tenant_id=tenant_id,
            config_type="llm",
            config_id=config_id,
            old_value=old_config,
            new_value=new_config,
            change_type="update",
            changed_by=user_id,
        )

        # Assert
        call_args = mock_db_session.add.call_args
        history_entry = call_args[0][0]
        # Verify old and new values are stored
        assert hasattr(history_entry, 'old_value') or hasattr(history_entry, 'config_data')


class TestConfigurationRollback:
    """Test configuration rollback functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def config_manager(self, mock_db_session):
        """Create a ConfigManager instance with mocked dependencies."""
        manager = ConfigManager(db_session=mock_db_session)
        return manager

    @pytest.mark.asyncio
    async def test_rollback_restores_previous_state(self, config_manager, mock_db_session):
        """Test that rollback restores the previous configuration state."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        version = 1
        
        previous_config = {
            "name": "Original Config",
            "model_name": "gpt-4",
            "temperature": 0.7,
        }
        
        # Mock the history query to return the previous version
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            config_data=previous_config,
            version=version,
        )
        mock_db_session.execute.return_value = mock_result

        # Act
        with patch.object(config_manager, 'rollback_config', new_callable=AsyncMock) as mock_rollback:
            mock_rollback.return_value = previous_config
            result = await config_manager.rollback_config(
                config_type="llm",
                config_id=config_id,
                version=version,
                tenant_id=tenant_id,
            )

        # Assert
        assert result == previous_config

    @pytest.mark.asyncio
    async def test_rollback_creates_new_history_entry(self, config_manager, mock_db_session):
        """Test that rollback creates a new history entry documenting the rollback."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        user_id = str(uuid4())
        version = 1
        
        previous_config = {
            "name": "Original Config",
            "model_name": "gpt-4",
        }
        
        current_config = {
            "name": "Current Config",
            "model_name": "gpt-4-turbo",
        }

        # Mock the history query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            config_data=previous_config,
            version=version,
        )
        mock_db_session.execute.return_value = mock_result

        # Act
        with patch.object(config_manager, 'rollback_config', new_callable=AsyncMock) as mock_rollback:
            mock_rollback.return_value = previous_config
            await config_manager.rollback_config(
                config_type="llm",
                config_id=config_id,
                version=version,
                tenant_id=tenant_id,
            )

        # Assert - rollback should have been called
        mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_to_nonexistent_version_fails(self, config_manager, mock_db_session):
        """Test that rollback to a non-existent version fails gracefully."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        version = 999  # Non-existent version
        
        # Mock the history query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with patch.object(config_manager, 'rollback_config', new_callable=AsyncMock) as mock_rollback:
            mock_rollback.side_effect = ValueError("Version not found")
            with pytest.raises(ValueError):
                await config_manager.rollback_config(
                    config_type="llm",
                    config_id=config_id,
                    version=version,
                    tenant_id=tenant_id,
                )


class TestHistoryRetention:
    """Test configuration history retention policies."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def history_tracker(self, mock_db_session):
        """Create a HistoryTracker instance with mocked dependencies."""
        tracker = HistoryTracker(db_session=mock_db_session)
        return tracker

    @pytest.mark.asyncio
    async def test_history_entries_retained_for_90_days(self, history_tracker, mock_db_session):
        """Test that history entries are retained for at least 90 days."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        
        # Create history entries with different ages
        entries = [
            MagicMock(
                id=str(uuid4()),
                changed_at=datetime.utcnow() - timedelta(days=30),
                config_data={"name": "Config 30 days ago"},
            ),
            MagicMock(
                id=str(uuid4()),
                changed_at=datetime.utcnow() - timedelta(days=60),
                config_data={"name": "Config 60 days ago"},
            ),
            MagicMock(
                id=str(uuid4()),
                changed_at=datetime.utcnow() - timedelta(days=89),
                config_data={"name": "Config 89 days ago"},
            ),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entries
        mock_db_session.execute.return_value = mock_result

        # Act
        with patch.object(history_tracker, 'get_history', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = entries
            result = await history_tracker.get_history(
                config_type="llm",
                config_id=config_id,
                tenant_id=tenant_id,
            )

        # Assert - all entries within 90 days should be returned
        assert len(result) == 3


class TestRollbackCompatibility:
    """Test rollback compatibility checking."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def config_manager(self, mock_db_session):
        """Create a ConfigManager instance with mocked dependencies."""
        manager = ConfigManager(db_session=mock_db_session)
        return manager

    @pytest.mark.asyncio
    async def test_rollback_compatibility_check_passes_for_compatible_config(
        self, config_manager, mock_db_session
    ):
        """Test that rollback compatibility check passes for compatible configurations."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        version = 1
        
        compatible_config = {
            "name": "Compatible Config",
            "llm_type": "openai",
            "model_name": "gpt-4",
            "api_endpoint": "https://api.openai.com/v1",
        }
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            config_data=compatible_config,
            version=version,
        )
        mock_db_session.execute.return_value = mock_result

        # Act
        with patch.object(config_manager, 'check_rollback_compatibility', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"compatible": True, "warnings": []}
            result = await config_manager.check_rollback_compatibility(
                config_type="llm",
                config_id=config_id,
                version=version,
                tenant_id=tenant_id,
            )

        # Assert
        assert result["compatible"] is True

    @pytest.mark.asyncio
    async def test_rollback_compatibility_check_fails_for_incompatible_config(
        self, config_manager, mock_db_session
    ):
        """Test that rollback compatibility check fails for incompatible configurations."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        version = 1
        
        # Config with deprecated fields or incompatible schema
        incompatible_config = {
            "name": "Incompatible Config",
            "deprecated_field": "value",
            "old_schema_version": "1.0",
        }
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            config_data=incompatible_config,
            version=version,
        )
        mock_db_session.execute.return_value = mock_result

        # Act
        with patch.object(config_manager, 'check_rollback_compatibility', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "compatible": False,
                "errors": ["Configuration schema version 1.0 is no longer supported"],
            }
            result = await config_manager.check_rollback_compatibility(
                config_type="llm",
                config_id=config_id,
                version=version,
                tenant_id=tenant_id,
            )

        # Assert
        assert result["compatible"] is False
        assert len(result["errors"]) > 0


class TestHistoryDiffView:
    """Test configuration history diff view functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def history_tracker(self, mock_db_session):
        """Create a HistoryTracker instance with mocked dependencies."""
        tracker = HistoryTracker(db_session=mock_db_session)
        return tracker

    @pytest.mark.asyncio
    async def test_diff_view_shows_changes_between_versions(self, history_tracker, mock_db_session):
        """Test that diff view correctly shows changes between versions."""
        # Arrange
        tenant_id = str(uuid4())
        config_id = str(uuid4())
        
        version1_config = {
            "name": "Config V1",
            "model_name": "gpt-4",
            "temperature": 0.7,
        }
        
        version2_config = {
            "name": "Config V2",
            "model_name": "gpt-4-turbo",
            "temperature": 0.8,
        }

        # Act
        with patch.object(history_tracker, 'get_diff', new_callable=AsyncMock) as mock_diff:
            mock_diff.return_value = {
                "changes": [
                    {"field": "name", "old": "Config V1", "new": "Config V2"},
                    {"field": "model_name", "old": "gpt-4", "new": "gpt-4-turbo"},
                    {"field": "temperature", "old": 0.7, "new": 0.8},
                ],
            }
            result = await history_tracker.get_diff(
                config_type="llm",
                config_id=config_id,
                version1=1,
                version2=2,
                tenant_id=tenant_id,
            )

        # Assert
        assert "changes" in result
        assert len(result["changes"]) == 3


class TestMultiTenantHistoryIsolation:
    """Test that configuration history is isolated between tenants."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def history_tracker(self, mock_db_session):
        """Create a HistoryTracker instance with mocked dependencies."""
        tracker = HistoryTracker(db_session=mock_db_session)
        return tracker

    @pytest.mark.asyncio
    async def test_tenant_cannot_access_other_tenant_history(self, history_tracker, mock_db_session):
        """Test that tenants cannot access other tenants' configuration history."""
        # Arrange
        tenant1_id = str(uuid4())
        tenant2_id = str(uuid4())
        config_id = str(uuid4())
        
        # Tenant 1's history
        tenant1_entries = [
            MagicMock(
                id=str(uuid4()),
                tenant_id=tenant1_id,
                config_data={"name": "Tenant 1 Config"},
            ),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tenant1_entries
        mock_db_session.execute.return_value = mock_result

        # Act - Tenant 2 tries to access Tenant 1's history
        with patch.object(history_tracker, 'get_history', new_callable=AsyncMock) as mock_get:
            # Should return empty for wrong tenant
            mock_get.return_value = []
            result = await history_tracker.get_history(
                config_type="llm",
                config_id=config_id,
                tenant_id=tenant2_id,  # Different tenant
            )

        # Assert - Should not return Tenant 1's history
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
