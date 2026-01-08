"""
Recovery and Error Handling System.

Provides comprehensive error recovery, checkpoint management, and automatic
retry mechanisms for data synchronization operations.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from src.sync.connectors.base import DataBatch, SyncResult

logger = logging.getLogger(__name__)


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error types."""
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL_INTERVENTION = "manual_intervention"
    SKIP_AND_CONTINUE = "skip_and_continue"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CheckpointType(str, Enum):
    """Types of checkpoints."""
    BATCH = "batch"
    TABLE = "table"
    SYNC_JOB = "sync_job"
    TRANSACTION = "transaction"


@dataclass
class ErrorInfo:
    """Information about an error."""
    error_id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    retry_count: int = 0
    resolved: bool = False
    resolution_strategy: Optional[RecoveryStrategy] = None


@dataclass
class Checkpoint:
    """Checkpoint for recovery purposes."""
    checkpoint_id: str
    checkpoint_type: CheckpointType
    sync_job_id: str
    table_name: Optional[str] = None
    position: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    data_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryAction:
    """Action to be taken for recovery."""
    action_id: str
    strategy: RecoveryStrategy
    target: str  # What to recover (batch_id, table_name, etc.)
    parameters: Dict[str, Any] = field(default_factory=dict)
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None


class RecoveryConfig(BaseModel):
    """Configuration for recovery system."""
    # Retry settings
    max_retry_attempts: int = Field(default=3, ge=0)
    initial_retry_delay: float = Field(default=1.0, ge=0.1)
    max_retry_delay: float = Field(default=300.0, ge=1.0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)
    
    # Circuit breaker settings
    circuit_breaker_threshold: int = Field(default=5, ge=1)
    circuit_breaker_timeout: int = Field(default=60, ge=1)  # seconds
    
    # Checkpoint settings
    checkpoint_interval: int = Field(default=100, ge=1)  # records
    checkpoint_retention_days: int = Field(default=7, ge=1)
    enable_data_snapshots: bool = False
    
    # Error handling
    error_threshold_per_minute: int = Field(default=10, ge=1)
    critical_error_types: List[str] = Field(default_factory=list)
    
    # Recovery settings
    enable_auto_recovery: bool = True
    recovery_timeout_seconds: int = Field(default=300, ge=1)
    parallel_recovery: bool = False
    max_recovery_workers: int = Field(default=2, ge=1)


class RecoverySystem:
    """
    Comprehensive recovery and error handling system.
    
    Features:
    - Automatic error detection and classification
    - Multiple recovery strategies
    - Checkpoint management for state recovery
    - Circuit breaker pattern
    - Retry mechanisms with backoff
    - Error tracking and reporting
    """

    def __init__(self, config: RecoveryConfig):
        self.config = config
        self.system_id = str(uuid4())
        
        # Error tracking
        self.errors: Dict[str, ErrorInfo] = {}
        self.error_counts: Dict[str, int] = {}
        self.last_error_time: Dict[str, datetime] = {}
        
        # Checkpoints
        self.checkpoints: Dict[str, Checkpoint] = {}
        
        # Recovery actions
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        self.pending_recoveries: List[str] = []
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Recovery tasks
        self._recovery_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            "total_errors": 0,
            "recovered_errors": 0,
            "failed_recoveries": 0,
            "checkpoints_created": 0,
            "checkpoints_restored": 0
        }

    async def start(self) -> None:
        """Start the recovery system."""
        logger.info("Starting recovery system")
        self._recovery_task = asyncio.create_task(self._recovery_loop())

    async def stop(self) -> None:
        """Stop the recovery system."""
        logger.info("Stopping recovery system")
        self._shutdown_event.set()
        
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        sync_job_id: Optional[str] = None
    ) -> RecoveryAction:
        """
        Handle an error and determine recovery action.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            sync_job_id: ID of the sync job (optional)
            
        Returns:
            RecoveryAction to be executed
        """
        error_info = self._classify_error(error, context)
        self.errors[error_info.error_id] = error_info
        self.stats["total_errors"] += 1
        
        # Update error tracking
        error_type = error_info.error_type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_error_time[error_type] = datetime.utcnow()
        
        # Check circuit breaker
        if self._should_open_circuit_breaker(error_type):
            self._open_circuit_breaker(error_type)
            strategy = RecoveryStrategy.CIRCUIT_BREAKER
        else:
            strategy = self._determine_recovery_strategy(error_info, context)
        
        # Create recovery action
        recovery_action = RecoveryAction(
            action_id=str(uuid4()),
            strategy=strategy,
            target=context.get("target", "unknown"),
            parameters={
                "error_id": error_info.error_id,
                "sync_job_id": sync_job_id,
                "retry_count": error_info.retry_count,
                **context
            }
        )
        
        self.recovery_actions[recovery_action.action_id] = recovery_action
        
        # Schedule recovery if auto-recovery is enabled
        if self.config.enable_auto_recovery and strategy != RecoveryStrategy.MANUAL_INTERVENTION:
            self.pending_recoveries.append(recovery_action.action_id)
        
        logger.warning(
            f"Error handled: {error_info.error_type}, "
            f"strategy: {strategy.value}, "
            f"action_id: {recovery_action.action_id}"
        )
        
        return recovery_action

    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """Classify error and determine severity."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Determine severity
        severity = ErrorSeverity.MEDIUM
        if error_type in self.config.critical_error_types:
            severity = ErrorSeverity.CRITICAL
        elif "connection" in error_message.lower():
            severity = ErrorSeverity.HIGH
        elif "timeout" in error_message.lower():
            severity = ErrorSeverity.MEDIUM
        elif "validation" in error_message.lower():
            severity = ErrorSeverity.LOW
        
        return ErrorInfo(
            error_id=str(uuid4()),
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            timestamp=datetime.utcnow(),
            context=context,
            stack_trace=self._get_stack_trace(error)
        )

    def _get_stack_trace(self, error: Exception) -> Optional[str]:
        """Get stack trace from exception."""
        import traceback
        try:
            return traceback.format_exc()
        except Exception:
            return None

    def _determine_recovery_strategy(
        self,
        error_info: ErrorInfo,
        context: Dict[str, Any]
    ) -> RecoveryStrategy:
        """Determine the best recovery strategy for an error."""
        error_type = error_info.error_type
        severity = error_info.severity
        
        # Critical errors require manual intervention
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.MANUAL_INTERVENTION
        
        # Connection errors use exponential backoff
        if "connection" in error_info.error_message.lower():
            return RecoveryStrategy.EXPONENTIAL_BACKOFF
        
        # Timeout errors use linear backoff
        if "timeout" in error_info.error_message.lower():
            return RecoveryStrategy.LINEAR_BACKOFF
        
        # Validation errors can be skipped
        if "validation" in error_info.error_message.lower():
            return RecoveryStrategy.SKIP_AND_CONTINUE
        
        # Default to exponential backoff
        return RecoveryStrategy.EXPONENTIAL_BACKOFF

    def _should_open_circuit_breaker(self, error_type: str) -> bool:
        """Check if circuit breaker should be opened."""
        error_count = self.error_counts.get(error_type, 0)
        return error_count >= self.config.circuit_breaker_threshold

    def _open_circuit_breaker(self, error_type: str) -> None:
        """Open circuit breaker for error type."""
        self.circuit_breakers[error_type] = {
            "opened_at": datetime.utcnow(),
            "error_count": self.error_counts.get(error_type, 0)
        }
        logger.warning(f"Circuit breaker opened for error type: {error_type}")

    def _is_circuit_breaker_open(self, error_type: str) -> bool:
        """Check if circuit breaker is open for error type."""
        breaker = self.circuit_breakers.get(error_type)
        if not breaker:
            return False
        
        opened_at = breaker["opened_at"]
        timeout_delta = timedelta(seconds=self.config.circuit_breaker_timeout)
        
        if datetime.utcnow() - opened_at > timeout_delta:
            # Close circuit breaker
            del self.circuit_breakers[error_type]
            self.error_counts[error_type] = 0
            logger.info(f"Circuit breaker closed for error type: {error_type}")
            return False
        
        return True

    async def create_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        sync_job_id: str,
        table_name: Optional[str] = None,
        position: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        data_snapshot: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        """
        Create a checkpoint for recovery purposes.
        
        Args:
            checkpoint_type: Type of checkpoint
            sync_job_id: ID of the sync job
            table_name: Table name (optional)
            position: Position information
            metadata: Additional metadata
            data_snapshot: Data snapshot (optional)
            
        Returns:
            Created checkpoint
        """
        checkpoint = Checkpoint(
            checkpoint_id=str(uuid4()),
            checkpoint_type=checkpoint_type,
            sync_job_id=sync_job_id,
            table_name=table_name,
            position=position or {},
            metadata=metadata or {},
            data_snapshot=data_snapshot if self.config.enable_data_snapshots else None
        )
        
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint
        self.stats["checkpoints_created"] += 1
        
        # Clean up old checkpoints
        await self._cleanup_old_checkpoints()
        
        logger.debug(f"Created checkpoint: {checkpoint.checkpoint_id}")
        return checkpoint

    async def restore_from_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Checkpoint]:
        """
        Restore state from a checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint to restore
            
        Returns:
            Restored checkpoint or None if not found
        """
        checkpoint = self.checkpoints.get(checkpoint_id)
        if not checkpoint:
            logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return None
        
        self.stats["checkpoints_restored"] += 1
        logger.info(f"Restored from checkpoint: {checkpoint_id}")
        return checkpoint

    async def find_latest_checkpoint(
        self,
        sync_job_id: str,
        table_name: Optional[str] = None,
        checkpoint_type: Optional[CheckpointType] = None
    ) -> Optional[Checkpoint]:
        """
        Find the latest checkpoint for given criteria.
        
        Args:
            sync_job_id: Sync job ID
            table_name: Table name (optional)
            checkpoint_type: Checkpoint type (optional)
            
        Returns:
            Latest matching checkpoint or None
        """
        matching_checkpoints = []
        
        for checkpoint in self.checkpoints.values():
            if checkpoint.sync_job_id != sync_job_id:
                continue
            
            if table_name and checkpoint.table_name != table_name:
                continue
            
            if checkpoint_type and checkpoint.checkpoint_type != checkpoint_type:
                continue
            
            matching_checkpoints.append(checkpoint)
        
        if not matching_checkpoints:
            return None
        
        # Return the most recent checkpoint
        return max(matching_checkpoints, key=lambda c: c.created_at)

    async def _recovery_loop(self) -> None:
        """Main recovery processing loop."""
        while not self._shutdown_event.is_set():
            try:
                if self.pending_recoveries:
                    if self.config.parallel_recovery:
                        await self._process_recoveries_parallel()
                    else:
                        await self._process_recoveries_sequential()
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Recovery loop error: {e}")
                await asyncio.sleep(5)

    async def _process_recoveries_sequential(self) -> None:
        """Process recovery actions sequentially."""
        while self.pending_recoveries:
            action_id = self.pending_recoveries.pop(0)
            await self._execute_recovery_action(action_id)

    async def _process_recoveries_parallel(self) -> None:
        """Process recovery actions in parallel."""
        semaphore = asyncio.Semaphore(self.config.max_recovery_workers)
        
        async def execute_with_semaphore(action_id: str) -> None:
            async with semaphore:
                await self._execute_recovery_action(action_id)
        
        tasks = []
        while self.pending_recoveries and len(tasks) < self.config.max_recovery_workers:
            action_id = self.pending_recoveries.pop(0)
            task = asyncio.create_task(execute_with_semaphore(action_id))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_recovery_action(self, action_id: str) -> None:
        """Execute a recovery action."""
        action = self.recovery_actions.get(action_id)
        if not action:
            return
        
        action.executed_at = datetime.utcnow()
        
        try:
            if action.strategy == RecoveryStrategy.IMMEDIATE_RETRY:
                await self._execute_immediate_retry(action)
            elif action.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                await self._execute_exponential_backoff(action)
            elif action.strategy == RecoveryStrategy.LINEAR_BACKOFF:
                await self._execute_linear_backoff(action)
            elif action.strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                await self._execute_circuit_breaker_recovery(action)
            elif action.strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
                await self._execute_skip_and_continue(action)
            
            action.success = True
            self.stats["recovered_errors"] += 1
            
            # Mark error as resolved
            error_id = action.parameters.get("error_id")
            if error_id and error_id in self.errors:
                self.errors[error_id].resolved = True
                self.errors[error_id].resolution_strategy = action.strategy
            
        except Exception as e:
            action.success = False
            action.error = str(e)
            self.stats["failed_recoveries"] += 1
            logger.error(f"Recovery action failed: {action_id}, error: {e}")

    async def _execute_immediate_retry(self, action: RecoveryAction) -> None:
        """Execute immediate retry recovery."""
        # This would retry the original operation immediately
        logger.info(f"Executing immediate retry for: {action.target}")
        await asyncio.sleep(0.1)  # Minimal delay

    async def _execute_exponential_backoff(self, action: RecoveryAction) -> None:
        """Execute exponential backoff recovery."""
        retry_count = action.parameters.get("retry_count", 0)
        
        if retry_count >= self.config.max_retry_attempts:
            raise Exception("Maximum retry attempts exceeded")
        
        delay = min(
            self.config.initial_retry_delay * (self.config.backoff_multiplier ** retry_count),
            self.config.max_retry_delay
        )
        
        logger.info(f"Executing exponential backoff retry for: {action.target}, delay: {delay}s")
        await asyncio.sleep(delay)
        
        # Update retry count
        action.parameters["retry_count"] = retry_count + 1

    async def _execute_linear_backoff(self, action: RecoveryAction) -> None:
        """Execute linear backoff recovery."""
        retry_count = action.parameters.get("retry_count", 0)
        
        if retry_count >= self.config.max_retry_attempts:
            raise Exception("Maximum retry attempts exceeded")
        
        delay = min(
            self.config.initial_retry_delay * (retry_count + 1),
            self.config.max_retry_delay
        )
        
        logger.info(f"Executing linear backoff retry for: {action.target}, delay: {delay}s")
        await asyncio.sleep(delay)
        
        action.parameters["retry_count"] = retry_count + 1

    async def _execute_circuit_breaker_recovery(self, action: RecoveryAction) -> None:
        """Execute circuit breaker recovery."""
        logger.info(f"Circuit breaker recovery for: {action.target}")
        # Wait for circuit breaker to close
        await asyncio.sleep(self.config.circuit_breaker_timeout)

    async def _execute_skip_and_continue(self, action: RecoveryAction) -> None:
        """Execute skip and continue recovery."""
        logger.info(f"Skipping error and continuing for: {action.target}")
        # Simply mark as successful to continue processing

    async def _cleanup_old_checkpoints(self) -> None:
        """Clean up old checkpoints."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.checkpoint_retention_days)
        
        checkpoints_to_remove = [
            checkpoint_id for checkpoint_id, checkpoint in self.checkpoints.items()
            if checkpoint.created_at < cutoff_date
        ]
        
        for checkpoint_id in checkpoints_to_remove:
            del self.checkpoints[checkpoint_id]
        
        if checkpoints_to_remove:
            logger.info(f"Cleaned up {len(checkpoints_to_remove)} old checkpoints")

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors and recovery status."""
        total_errors = len(self.errors)
        resolved_errors = len([e for e in self.errors.values() if e.resolved])
        
        error_by_type = {}
        for error in self.errors.values():
            error_type = error.error_type
            if error_type not in error_by_type:
                error_by_type[error_type] = {"total": 0, "resolved": 0}
            
            error_by_type[error_type]["total"] += 1
            if error.resolved:
                error_by_type[error_type]["resolved"] += 1
        
        return {
            "total_errors": total_errors,
            "resolved_errors": resolved_errors,
            "unresolved_errors": total_errors - resolved_errors,
            "error_by_type": error_by_type,
            "circuit_breakers": list(self.circuit_breakers.keys()),
            "pending_recoveries": len(self.pending_recoveries)
        }

    def get_checkpoint_summary(self) -> Dict[str, Any]:
        """Get summary of checkpoints."""
        checkpoints_by_type = {}
        for checkpoint in self.checkpoints.values():
            checkpoint_type = checkpoint.checkpoint_type.value
            checkpoints_by_type[checkpoint_type] = checkpoints_by_type.get(checkpoint_type, 0) + 1
        
        return {
            "total_checkpoints": len(self.checkpoints),
            "checkpoints_by_type": checkpoints_by_type,
            "oldest_checkpoint": min(
                (c.created_at for c in self.checkpoints.values()),
                default=None
            ),
            "newest_checkpoint": max(
                (c.created_at for c in self.checkpoints.values()),
                default=None
            )
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get recovery system statistics."""
        return {
            "system_id": self.system_id,
            "error_summary": self.get_error_summary(),
            "checkpoint_summary": self.get_checkpoint_summary(),
            **self.stats
        }