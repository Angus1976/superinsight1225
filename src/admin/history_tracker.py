"""
History Tracker for SuperInsight Platform Admin Configuration.

Provides configuration change history tracking with:
- Recording configuration changes
- Retrieving change history
- Computing configuration diffs
- Rolling back to previous versions

**Feature: admin-configuration**
**Validates: Requirements 6.1, 6.2, 6.3, 6.4**
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from uuid import uuid4

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.schemas import (
    ConfigType,
    ConfigHistoryResponse,
    ConfigDiff,
)

logger = logging.getLogger(__name__)


class HistoryTracker:
    """
    Configuration history tracker.
    
    Records all configuration changes and supports rollback operations.
    
    **Feature: admin-configuration**
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize the history tracker.
        
        Args:
            db: Optional async database session
        """
        self._db = db
        self._in_memory_history: List[Dict[str, Any]] = []
    
    @property
    def db(self) -> Optional[AsyncSession]:
        """Get the database session."""
        return self._db
    
    @db.setter
    def db(self, session: AsyncSession) -> None:
        """Set the database session."""
        self._db = session
    
    async def record_change(
        self,
        config_type: Union[ConfigType, str],
        old_value: Optional[Dict[str, Any]],
        new_value: Dict[str, Any],
        user_id: str,
        user_name: str = "Unknown",
        tenant_id: Optional[str] = None,
        config_id: Optional[str] = None,
    ) -> ConfigHistoryResponse:
        """
        Record a configuration change.
        
        Args:
            config_type: Type of configuration being changed
            old_value: Previous configuration value (None for new configs)
            new_value: New configuration value
            user_id: ID of user making the change
            user_name: Name of user making the change
            tenant_id: Optional tenant ID for multi-tenant support
            config_id: Optional ID of the specific config being changed
            
        Returns:
            ConfigHistoryResponse with the recorded change
            
        **Feature: admin-configuration**
        **Validates: Requirements 6.1, 6.2**
        """
        # Normalize config_type
        if isinstance(config_type, str):
            config_type = ConfigType(config_type)
        
        history_id = str(uuid4())
        created_at = datetime.utcnow()
        
        # Sanitize values - remove sensitive fields for history
        sanitized_old = self._sanitize_for_history(old_value) if old_value else None
        sanitized_new = self._sanitize_for_history(new_value)
        
        history_record = {
            "id": history_id,
            "config_type": config_type.value,
            "config_id": config_id,
            "old_value": sanitized_old,
            "new_value": sanitized_new,
            "user_id": user_id,
            "user_name": user_name,
            "tenant_id": tenant_id,
            "created_at": created_at,
        }
        
        if self._db is not None:
            await self._save_to_database(history_record)
        else:
            # In-memory storage for testing
            self._in_memory_history.append(history_record)
        
        logger.info(
            f"Recorded config change: type={config_type.value}, "
            f"user={user_id}, history_id={history_id}"
        )
        
        return ConfigHistoryResponse(
            id=history_id,
            config_type=config_type,
            old_value=sanitized_old,
            new_value=sanitized_new,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            created_at=created_at,
        )
    
    async def get_history(
        self,
        config_type: Optional[Union[ConfigType, str]] = None,
        config_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConfigHistoryResponse]:
        """
        Get configuration change history.
        
        Args:
            config_type: Filter by configuration type
            config_id: Filter by specific config ID
            start_time: Filter changes after this time
            end_time: Filter changes before this time
            user_id: Filter by user who made changes
            tenant_id: Filter by tenant
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of ConfigHistoryResponse records
            
        **Feature: admin-configuration**
        **Validates: Requirements 6.1, 6.3**
        """
        # Normalize config_type
        if isinstance(config_type, str):
            config_type = ConfigType(config_type)
        
        if self._db is not None:
            return await self._get_from_database(
                config_type=config_type,
                config_id=config_id,
                start_time=start_time,
                end_time=end_time,
                user_id=user_id,
                tenant_id=tenant_id,
                limit=limit,
                offset=offset,
            )
        else:
            return self._get_from_memory(
                config_type=config_type,
                config_id=config_id,
                start_time=start_time,
                end_time=end_time,
                user_id=user_id,
                tenant_id=tenant_id,
                limit=limit,
                offset=offset,
            )
    
    async def get_history_by_id(self, history_id: str) -> Optional[ConfigHistoryResponse]:
        """
        Get a specific history record by ID.
        
        Args:
            history_id: The history record ID
            
        Returns:
            ConfigHistoryResponse if found, None otherwise
        """
        if self._db is not None:
            return await self._get_by_id_from_database(history_id)
        else:
            for record in self._in_memory_history:
                if record["id"] == history_id:
                    return self._record_to_response(record)
            return None
    
    def get_diff(
        self,
        old_value: Optional[Dict[str, Any]],
        new_value: Dict[str, Any],
    ) -> ConfigDiff:
        """
        Compute the difference between two configuration values.
        
        Args:
            old_value: Previous configuration value
            new_value: New configuration value
            
        Returns:
            ConfigDiff with added, removed, and modified fields
            
        **Feature: admin-configuration**
        **Validates: Requirements 6.2**
        """
        if old_value is None:
            # All fields are new
            return ConfigDiff(
                added=new_value,
                removed={},
                modified={},
            )
        
        added = {}
        removed = {}
        modified = {}
        
        old_keys = set(old_value.keys())
        new_keys = set(new_value.keys())
        
        # Find added keys
        for key in new_keys - old_keys:
            added[key] = new_value[key]
        
        # Find removed keys
        for key in old_keys - new_keys:
            removed[key] = old_value[key]
        
        # Find modified keys
        for key in old_keys & new_keys:
            if old_value[key] != new_value[key]:
                modified[key] = {
                    "old": old_value[key],
                    "new": new_value[key],
                }
        
        return ConfigDiff(
            added=added,
            removed=removed,
            modified=modified,
        )
    
    async def get_diff_by_history_id(self, history_id: str) -> Optional[ConfigDiff]:
        """
        Get the diff for a specific history record.
        
        Args:
            history_id: The history record ID
            
        Returns:
            ConfigDiff if found, None otherwise
        """
        history = await self.get_history_by_id(history_id)
        if history is None:
            return None
        
        return self.get_diff(history.old_value, history.new_value)
    
    async def rollback(
        self,
        history_id: str,
        user_id: str,
        user_name: str = "Unknown",
    ) -> Optional[Dict[str, Any]]:
        """
        Rollback configuration to a previous version.
        
        This creates a new history record for the rollback operation.
        
        Args:
            history_id: ID of the history record to rollback to
            user_id: ID of user performing the rollback
            user_name: Name of user performing the rollback
            
        Returns:
            The rolled-back configuration value, or None if not found
            
        **Feature: admin-configuration**
        **Validates: Requirements 6.4**
        """
        # Get the history record
        history = await self.get_history_by_id(history_id)
        if history is None:
            logger.warning(f"History record not found: {history_id}")
            return None
        
        # The rollback target is the old_value from the history record
        rollback_value = history.old_value
        if rollback_value is None:
            logger.warning(f"Cannot rollback to None value: {history_id}")
            return None
        
        # Get the current value (most recent for this config type)
        current_history = await self.get_history(
            config_type=history.config_type,
            limit=1,
        )
        
        current_value = current_history[0].new_value if current_history else None
        
        # Record the rollback as a new change
        await self.record_change(
            config_type=history.config_type,
            old_value=current_value,
            new_value=rollback_value,
            user_id=user_id,
            user_name=user_name,
            tenant_id=history.tenant_id,
        )
        
        logger.info(
            f"Rolled back config: type={history.config_type}, "
            f"history_id={history_id}, user={user_id}"
        )
        
        return rollback_value
    
    def clear_in_memory_history(self) -> None:
        """Clear in-memory history (for testing)."""
        self._in_memory_history.clear()
    
    # ========== Private helper methods ==========
    
    def _sanitize_for_history(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize configuration value for history storage.
        
        Removes or masks sensitive fields like passwords and API keys.
        """
        if value is None:
            return {}
        
        sanitized = value.copy()
        sensitive_fields = [
            "password", "api_key", "secret", "token",
            "password_encrypted", "api_key_encrypted",
        ]
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "[REDACTED]"
        
        return sanitized
    
    def _record_to_response(self, record: Dict[str, Any]) -> ConfigHistoryResponse:
        """Convert a history record dict to ConfigHistoryResponse."""
        return ConfigHistoryResponse(
            id=record["id"],
            config_type=ConfigType(record["config_type"]),
            old_value=record.get("old_value"),
            new_value=record["new_value"],
            user_id=record["user_id"],
            user_name=record.get("user_name", "Unknown"),
            tenant_id=record.get("tenant_id"),
            created_at=record["created_at"],
        )
    
    def _get_from_memory(
        self,
        config_type: Optional[ConfigType] = None,
        config_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConfigHistoryResponse]:
        """Get history from in-memory storage."""
        filtered = []
        
        for record in self._in_memory_history:
            # Apply filters
            if config_type and record["config_type"] != config_type.value:
                continue
            if config_id and record.get("config_id") != config_id:
                continue
            if start_time and record["created_at"] < start_time:
                continue
            if end_time and record["created_at"] > end_time:
                continue
            if user_id and record["user_id"] != user_id:
                continue
            if tenant_id and record.get("tenant_id") != tenant_id:
                continue
            
            filtered.append(record)
        
        # Sort by created_at descending
        filtered.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        paginated = filtered[offset:offset + limit]
        
        return [self._record_to_response(r) for r in paginated]
    
    async def _save_to_database(self, record: Dict[str, Any]) -> None:
        """Save history record to database."""
        from src.models.admin_config import ConfigChangeHistory
        
        history = ConfigChangeHistory(
            id=record["id"],
            config_type=record["config_type"],
            config_id=record.get("config_id"),
            old_value=record.get("old_value"),
            new_value=record["new_value"],
            user_id=record["user_id"],
            user_name=record.get("user_name", "Unknown"),
            tenant_id=record.get("tenant_id"),
            created_at=record["created_at"],
        )
        
        self._db.add(history)
        await self._db.commit()
    
    async def _get_from_database(
        self,
        config_type: Optional[ConfigType] = None,
        config_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConfigHistoryResponse]:
        """Get history from database."""
        from src.models.admin_config import ConfigChangeHistory
        
        conditions = []
        
        if config_type:
            conditions.append(ConfigChangeHistory.config_type == config_type.value)
        if config_id:
            conditions.append(ConfigChangeHistory.config_id == config_id)
        if start_time:
            conditions.append(ConfigChangeHistory.created_at >= start_time)
        if end_time:
            conditions.append(ConfigChangeHistory.created_at <= end_time)
        if user_id:
            conditions.append(ConfigChangeHistory.user_id == user_id)
        if tenant_id:
            conditions.append(ConfigChangeHistory.tenant_id == tenant_id)
        
        query = select(ConfigChangeHistory)
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(ConfigChangeHistory.created_at))
        query = query.offset(offset).limit(limit)
        
        result = await self._db.execute(query)
        records = result.scalars().all()
        
        return [
            ConfigHistoryResponse(
                id=str(r.id),
                config_type=ConfigType(r.config_type),
                old_value=r.old_value,
                new_value=r.new_value,
                user_id=str(r.user_id),
                user_name=r.user_name or "Unknown",
                tenant_id=str(r.tenant_id) if r.tenant_id else None,
                created_at=r.created_at,
            )
            for r in records
        ]
    
    async def _get_by_id_from_database(
        self, history_id: str
    ) -> Optional[ConfigHistoryResponse]:
        """Get a specific history record from database."""
        from src.models.admin_config import ConfigChangeHistory
        
        query = select(ConfigChangeHistory).where(
            ConfigChangeHistory.id == history_id
        )
        
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record is None:
            return None
        
        return ConfigHistoryResponse(
            id=str(record.id),
            config_type=ConfigType(record.config_type),
            old_value=record.old_value,
            new_value=record.new_value,
            user_id=str(record.user_id),
            user_name=record.user_name or "Unknown",
            tenant_id=str(record.tenant_id) if record.tenant_id else None,
            created_at=record.created_at,
        )


# Global tracker instance
_history_tracker: Optional[HistoryTracker] = None


def get_history_tracker() -> HistoryTracker:
    """Get the global history tracker instance."""
    global _history_tracker
    if _history_tracker is None:
        _history_tracker = HistoryTracker()
    return _history_tracker
