"""
Sync Strategy Service for SuperInsight Platform Admin Configuration.

Provides data synchronization strategy management with:
- Strategy CRUD operations
- Sync triggering and retry
- Sync history tracking
- Strategy validation

**Feature: admin-configuration**
**Validates: Requirements 4.1, 4.2, 4.3, 4.6, 4.7**
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from uuid import uuid4

from sqlalchemy import select, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.schemas import (
    SyncMode,
    ValidationResult,
    SyncStrategyCreate,
    SyncStrategyUpdate,
    SyncStrategyResponse,
    SyncHistoryResponse,
    SyncJobResponse,
)
from src.admin.config_validator import ConfigValidator, get_config_validator
from src.admin.history_tracker import HistoryTracker, get_history_tracker
from src.admin.schemas import ConfigType

logger = logging.getLogger(__name__)


class SyncStrategyService:
    """
    Sync Strategy Service for managing data synchronization.
    
    Provides strategy management, sync triggering, and history tracking.
    
    **Feature: admin-configuration**
    **Validates: Requirements 4.1, 4.2, 4.3, 4.6, 4.7**
    """
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        validator: Optional[ConfigValidator] = None,
        history_tracker: Optional[HistoryTracker] = None,
    ):
        """
        Initialize the sync strategy service.
        
        Args:
            db: Optional async database session
            validator: Config validator
            history_tracker: History tracker
        """
        self._db = db
        self._validator = validator or get_config_validator()
        self._history_tracker = history_tracker or get_history_tracker()
        
        # In-memory storage for testing
        self._in_memory_strategies: Dict[str, Dict[str, Any]] = {}
        self._in_memory_history: List[Dict[str, Any]] = []
        self._in_memory_jobs: Dict[str, Dict[str, Any]] = {}
    
    @property
    def db(self) -> Optional[AsyncSession]:
        """Get the database session."""
        return self._db
    
    @db.setter
    def db(self, session: AsyncSession) -> None:
        """Set the database session."""
        self._db = session
        self._history_tracker.db = session
    
    async def get_strategy(
        self,
        strategy_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[SyncStrategyResponse]:
        """
        Get sync strategy by ID.
        
        Args:
            strategy_id: Strategy ID
            tenant_id: Optional tenant ID
            
        Returns:
            SyncStrategyResponse if found, None otherwise
            
        **Feature: admin-configuration**
        **Validates: Requirements 4.1**
        """
        if self._db is not None:
            return await self._get_from_db(strategy_id, tenant_id)
        else:
            strategy = self._in_memory_strategies.get(strategy_id)
            if strategy:
                return self._to_response(strategy)
            return None
    
    async def get_strategy_by_db_config(
        self,
        db_config_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[SyncStrategyResponse]:
        """
        Get sync strategy by database config ID.
        
        Args:
            db_config_id: Database configuration ID
            tenant_id: Optional tenant ID
            
        Returns:
            SyncStrategyResponse if found, None otherwise
        """
        if self._db is not None:
            return await self._get_by_db_config_from_db(db_config_id, tenant_id)
        else:
            for strategy in self._in_memory_strategies.values():
                if strategy.get("db_config_id") == db_config_id:
                    if tenant_id is None or strategy.get("tenant_id") == tenant_id:
                        return self._to_response(strategy)
            return None
    
    async def list_strategies(
        self,
        tenant_id: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[SyncStrategyResponse]:
        """
        List all sync strategies.
        
        Args:
            tenant_id: Optional tenant ID filter
            enabled_only: Only return enabled strategies
            
        Returns:
            List of SyncStrategyResponse
        """
        if self._db is not None:
            return await self._list_from_db(tenant_id, enabled_only)
        else:
            strategies = list(self._in_memory_strategies.values())
            if tenant_id:
                strategies = [s for s in strategies if s.get("tenant_id") == tenant_id]
            if enabled_only:
                strategies = [s for s in strategies if s.get("enabled", True)]
            return [self._to_response(s) for s in strategies]
    
    async def save_strategy(
        self,
        strategy: Union[SyncStrategyCreate, SyncStrategyUpdate],
        user_id: str,
        user_name: str = "Unknown",
        strategy_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> SyncStrategyResponse:
        """
        Save sync strategy (create or update).
        
        Args:
            strategy: Strategy data
            user_id: User making the change
            user_name: User name for history
            strategy_id: Existing strategy ID for update
            tenant_id: Tenant ID for multi-tenant
            
        Returns:
            Saved SyncStrategyResponse
            
        **Feature: admin-configuration**
        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        # Validate strategy
        validation = self._validator.validate_sync_config(strategy)
        if not validation.is_valid:
            raise ValueError(f"Invalid sync strategy: {validation.errors}")
        
        # Get old value for history
        old_value = None
        existing_strategy = None
        if strategy_id:
            if self._db is not None:
                existing_strategy = await self._get_raw_from_db(strategy_id, tenant_id)
            else:
                existing_strategy = self._in_memory_strategies.get(strategy_id)
            
            if existing_strategy:
                old_value = existing_strategy.copy()
        
        # Prepare strategy data
        strategy_dict = strategy.model_dump(exclude_unset=True) if hasattr(strategy, 'model_dump') else strategy.dict(exclude_unset=True)
        
        # For updates, merge with existing
        if strategy_id and existing_strategy:
            merged = existing_strategy.copy()
            merged.update(strategy_dict)
            strategy_dict = merged
        
        # Set timestamps and IDs
        now = datetime.utcnow()
        if strategy_id:
            strategy_dict["id"] = strategy_id
            strategy_dict["updated_at"] = now
        else:
            strategy_dict["id"] = str(uuid4())
            strategy_dict["created_at"] = now
            strategy_dict["updated_at"] = now
        
        strategy_dict["tenant_id"] = tenant_id
        
        # Save to storage
        if self._db is not None:
            saved = await self._save_to_db(strategy_dict, strategy_id is not None)
        else:
            self._in_memory_strategies[strategy_dict["id"]] = strategy_dict
            saved = strategy_dict
        
        # Record history
        await self._history_tracker.record_change(
            config_type=ConfigType.SYNC_STRATEGY,
            old_value=old_value,
            new_value=strategy_dict,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            config_id=strategy_dict["id"],
        )
        
        return self._to_response(saved)
    
    async def delete_strategy(
        self,
        strategy_id: str,
        user_id: str,
        user_name: str = "Unknown",
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        Delete sync strategy.
        
        Args:
            strategy_id: Strategy ID to delete
            user_id: User making the change
            user_name: User name for history
            tenant_id: Tenant ID for multi-tenant
            
        Returns:
            True if deleted, False if not found
        """
        existing = await self.get_strategy(strategy_id, tenant_id)
        if not existing:
            return False
        
        old_value = existing.model_dump()
        
        if self._db is not None:
            await self._delete_from_db(strategy_id, tenant_id)
        else:
            if strategy_id in self._in_memory_strategies:
                del self._in_memory_strategies[strategy_id]
        
        await self._history_tracker.record_change(
            config_type=ConfigType.SYNC_STRATEGY,
            old_value=old_value,
            new_value={"_deleted": True, "id": strategy_id},
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            config_id=strategy_id,
        )
        
        return True
    
    async def trigger_sync(
        self,
        strategy_id: str,
        user_id: str,
    ) -> SyncJobResponse:
        """
        Trigger a sync job for a strategy.
        
        Args:
            strategy_id: Strategy ID to trigger
            user_id: User triggering the sync
            
        Returns:
            SyncJobResponse with job details
            
        **Feature: admin-configuration**
        **Validates: Requirements 4.6**
        """
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        if not strategy.enabled:
            raise ValueError(f"Strategy is disabled: {strategy_id}")
        
        job_id = str(uuid4())
        now = datetime.utcnow()
        
        job = {
            "job_id": job_id,
            "strategy_id": strategy_id,
            "status": "running",
            "started_at": now,
            "triggered_by": user_id,
        }
        
        # In a real implementation, this would queue a Celery task
        # For now, we just record the job
        if self._db is not None:
            await self._create_sync_history(strategy_id, job_id, "running")
        else:
            self._in_memory_jobs[job_id] = job
            self._in_memory_history.append({
                "id": str(uuid4()),
                "strategy_id": strategy_id,
                "status": "running",
                "started_at": now,
                "records_synced": 0,
            })
        
        logger.info(f"Triggered sync job {job_id} for strategy {strategy_id}")
        
        return SyncJobResponse(
            job_id=job_id,
            strategy_id=strategy_id,
            status="running",
            started_at=now,
            message=f"Sync job started for strategy {strategy_id}",
        )
    
    async def retry_sync(
        self,
        job_id: str,
        user_id: str,
    ) -> SyncJobResponse:
        """
        Retry a failed sync job.
        
        Args:
            job_id: Job ID to retry
            user_id: User retrying the sync
            
        Returns:
            SyncJobResponse with new job details
            
        **Feature: admin-configuration**
        **Validates: Requirements 4.7**
        """
        # Find the original job
        original_job = None
        if self._db is not None:
            original_job = await self._get_sync_history_by_id(job_id)
        else:
            original_job = self._in_memory_jobs.get(job_id)
        
        if not original_job:
            raise ValueError(f"Job not found: {job_id}")
        
        strategy_id = original_job.get("strategy_id")
        
        # Trigger a new sync
        return await self.trigger_sync(strategy_id, user_id)
    
    async def get_sync_history(
        self,
        strategy_id: str,
        limit: int = 50,
    ) -> List[SyncHistoryResponse]:
        """
        Get sync history for a strategy.
        
        Args:
            strategy_id: Strategy ID
            limit: Maximum records to return
            
        Returns:
            List of SyncHistoryResponse
        """
        if self._db is not None:
            return await self._get_sync_history_from_db(strategy_id, limit)
        else:
            history = [
                h for h in self._in_memory_history
                if h.get("strategy_id") == strategy_id
            ]
            history.sort(key=lambda x: x.get("started_at", datetime.min), reverse=True)
            history = history[:limit]
            
            return [
                SyncHistoryResponse(
                    id=h["id"],
                    strategy_id=h["strategy_id"],
                    status=h["status"],
                    started_at=h["started_at"],
                    completed_at=h.get("completed_at"),
                    records_synced=h.get("records_synced", 0),
                    error_message=h.get("error_message"),
                    details=h.get("details"),
                )
                for h in history
            ]
    
    def validate_strategy(
        self,
        strategy: Union[SyncStrategyCreate, SyncStrategyUpdate, Dict[str, Any]],
    ) -> ValidationResult:
        """
        Validate sync strategy without saving.
        
        Args:
            strategy: Strategy to validate
            
        Returns:
            ValidationResult with validation status
        """
        return self._validator.validate_sync_config(strategy)
    
    def clear_in_memory_storage(self) -> None:
        """Clear in-memory storage (for testing)."""
        self._in_memory_strategies.clear()
        self._in_memory_history.clear()
        self._in_memory_jobs.clear()
        self._history_tracker.clear_in_memory_history()
    
    # ========== Private helper methods ==========
    
    def _to_response(self, strategy: Dict[str, Any]) -> SyncStrategyResponse:
        """Convert strategy dict to SyncStrategyResponse."""
        return SyncStrategyResponse(
            id=str(strategy.get("id", "")),
            db_config_id=str(strategy.get("db_config_id", "")),
            name=strategy.get("name"),
            mode=SyncMode(strategy.get("mode", "full")),
            incremental_field=strategy.get("incremental_field"),
            schedule=strategy.get("schedule"),
            filter_conditions=strategy.get("filter_conditions", []),
            batch_size=strategy.get("batch_size", 1000),
            enabled=strategy.get("enabled", True),
            last_sync_at=strategy.get("last_sync_at"),
            last_sync_status=strategy.get("last_sync_status"),
            created_at=strategy.get("created_at", datetime.utcnow()),
            updated_at=strategy.get("updated_at", datetime.utcnow()),
        )
    
    async def _get_from_db(
        self,
        strategy_id: str,
        tenant_id: Optional[str],
    ) -> Optional[SyncStrategyResponse]:
        """Get strategy from database."""
        from src.models.admin_config import SyncStrategy
        
        conditions = [SyncStrategy.id == strategy_id]
        if tenant_id:
            conditions.append(SyncStrategy.tenant_id == tenant_id)
        
        query = select(SyncStrategy).where(and_(*conditions))
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            return self._to_response(record.to_dict())
        return None
    
    async def _get_raw_from_db(
        self,
        strategy_id: str,
        tenant_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Get raw strategy dict from database."""
        from src.models.admin_config import SyncStrategy
        
        conditions = [SyncStrategy.id == strategy_id]
        if tenant_id:
            conditions.append(SyncStrategy.tenant_id == tenant_id)
        
        query = select(SyncStrategy).where(and_(*conditions))
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            return record.to_dict()
        return None
    
    async def _get_by_db_config_from_db(
        self,
        db_config_id: str,
        tenant_id: Optional[str],
    ) -> Optional[SyncStrategyResponse]:
        """Get strategy by db_config_id from database."""
        from src.models.admin_config import SyncStrategy
        
        conditions = [SyncStrategy.db_config_id == db_config_id]
        if tenant_id:
            conditions.append(SyncStrategy.tenant_id == tenant_id)
        
        query = select(SyncStrategy).where(and_(*conditions))
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            return self._to_response(record.to_dict())
        return None
    
    async def _list_from_db(
        self,
        tenant_id: Optional[str],
        enabled_only: bool,
    ) -> List[SyncStrategyResponse]:
        """List strategies from database."""
        from src.models.admin_config import SyncStrategy
        
        conditions = []
        if tenant_id:
            conditions.append(SyncStrategy.tenant_id == tenant_id)
        if enabled_only:
            conditions.append(SyncStrategy.enabled == True)
        
        query = select(SyncStrategy)
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self._db.execute(query)
        records = result.scalars().all()
        
        return [self._to_response(r.to_dict()) for r in records]
    
    async def _save_to_db(
        self,
        strategy: Dict[str, Any],
        is_update: bool,
    ) -> Dict[str, Any]:
        """Save strategy to database."""
        from src.models.admin_config import SyncStrategy
        
        if is_update:
            query = update(SyncStrategy).where(
                SyncStrategy.id == strategy["id"]
            ).values(**{k: v for k, v in strategy.items() if k != "id"})
            await self._db.execute(query)
        else:
            record = SyncStrategy(**strategy)
            self._db.add(record)
        
        await self._db.commit()
        return strategy
    
    async def _delete_from_db(
        self,
        strategy_id: str,
        tenant_id: Optional[str],
    ) -> None:
        """Delete strategy from database."""
        from src.models.admin_config import SyncStrategy
        
        conditions = [SyncStrategy.id == strategy_id]
        if tenant_id:
            conditions.append(SyncStrategy.tenant_id == tenant_id)
        
        query = delete(SyncStrategy).where(and_(*conditions))
        await self._db.execute(query)
        await self._db.commit()
    
    async def _create_sync_history(
        self,
        strategy_id: str,
        job_id: str,
        status: str,
    ) -> None:
        """Create sync history record in database."""
        from src.models.admin_config import SyncHistory
        
        record = SyncHistory(
            id=job_id,
            strategy_id=strategy_id,
            status=status,
            started_at=datetime.utcnow(),
        )
        self._db.add(record)
        await self._db.commit()
    
    async def _get_sync_history_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get sync history by job ID."""
        from src.models.admin_config import SyncHistory
        
        query = select(SyncHistory).where(SyncHistory.id == job_id)
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            return record.to_dict()
        return None
    
    async def _get_sync_history_from_db(
        self,
        strategy_id: str,
        limit: int,
    ) -> List[SyncHistoryResponse]:
        """Get sync history from database."""
        from src.models.admin_config import SyncHistory
        from sqlalchemy import desc
        
        query = select(SyncHistory).where(
            SyncHistory.strategy_id == strategy_id
        ).order_by(desc(SyncHistory.started_at)).limit(limit)
        
        result = await self._db.execute(query)
        records = result.scalars().all()
        
        return [
            SyncHistoryResponse(
                id=str(r.id),
                strategy_id=str(r.strategy_id),
                status=r.status,
                started_at=r.started_at,
                completed_at=r.completed_at,
                records_synced=r.records_synced,
                error_message=r.error_message,
                details=r.details,
            )
            for r in records
        ]


# Global service instance
_sync_strategy_service: Optional[SyncStrategyService] = None


def get_sync_strategy_service() -> SyncStrategyService:
    """Get the global sync strategy service instance."""
    global _sync_strategy_service
    if _sync_strategy_service is None:
        _sync_strategy_service = SyncStrategyService()
    return _sync_strategy_service
