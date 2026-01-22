"""
LLM Request Batch Processor for SuperInsight platform.

Provides batch processing capabilities for LLM requests with:
- Grouping compatible requests by provider
- Async batch processing with progress tracking
- Error handling without failing entire batch

Implements Requirements 10.1 and 10.5 from the LLM Integration spec.
"""

import asyncio
import time
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Awaitable, Tuple, Union
from uuid import uuid4
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from src.ai.llm_schemas import (
        LLMMethod, GenerateOptions, LLMResponse, LLMError, LLMErrorCode
    )
except ImportError:
    from ai.llm_schemas import (
        LLMMethod, GenerateOptions, LLMResponse, LLMError, LLMErrorCode
    )

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """Enumeration of batch processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class LLMRequest:
    """
    Represents a single LLM request in a batch.
    
    Attributes:
        request_id: Unique identifier for this request
        prompt: The input prompt
        options: Generation options
        method: Target LLM method/provider (optional, uses default if not specified)
        model: Model override (optional)
        system_prompt: System prompt for chat models (optional)
        metadata: Additional metadata for tracking
    """
    prompt: str
    request_id: str = field(default_factory=lambda: str(uuid4()))
    options: Optional[GenerateOptions] = None
    method: Optional[LLMMethod] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_provider_key(self) -> str:
        """
        Generate a key for grouping compatible requests.
        
        Requests are compatible if they target the same provider/method.
        """
        method_value = self.method.value if self.method else "default"
        return f"{method_value}:{self.model or 'default'}"


@dataclass
class LLMRequestResult:
    """
    Result of processing a single LLM request.
    
    Attributes:
        request_id: ID of the original request
        success: Whether the request succeeded
        response: LLM response if successful
        error: Error message if failed
        latency_ms: Processing time in milliseconds
    """
    request_id: str
    success: bool
    response: Optional[LLMResponse] = None
    error: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class BatchProgress:
    """
    Progress tracking for batch processing.
    
    Provides real-time progress updates showing completed/total requests.
    
    **Validates: Requirements 10.5**
    """
    batch_id: str
    total_requests: int
    completed_requests: int = 0
    failed_requests: int = 0
    status: BatchStatus = BatchStatus.PENDING
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def pending_requests(self) -> int:
        """Number of requests still pending."""
        return self.total_requests - self.completed_requests - self.failed_requests
    
    @property
    def progress_percentage(self) -> float:
        """Progress as a percentage (0-100)."""
        if self.total_requests == 0:
            return 100.0
        return ((self.completed_requests + self.failed_requests) / self.total_requests) * 100
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)."""
        processed = self.completed_requests + self.failed_requests
        if processed == 0:
            return 0.0
        return (self.completed_requests / processed) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "batch_id": self.batch_id,
            "total_requests": self.total_requests,
            "completed_requests": self.completed_requests,
            "failed_requests": self.failed_requests,
            "pending_requests": self.pending_requests,
            "progress_percentage": round(self.progress_percentage, 2),
            "success_rate": round(self.success_rate, 2),
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class BatchResult:
    """
    Complete result of batch processing.
    
    Attributes:
        batch_id: Unique identifier for this batch
        progress: Final progress state
        results: List of individual request results
        errors: List of batch-level errors
        processing_time_ms: Total processing time
    """
    batch_id: str
    progress: BatchProgress
    results: List[LLMRequestResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "batch_id": self.batch_id,
            "progress": self.progress.to_dict(),
            "results": [
                {
                    "request_id": r.request_id,
                    "success": r.success,
                    "response": r.response.model_dump() if r.response else None,
                    "error": r.error,
                    "latency_ms": r.latency_ms,
                }
                for r in self.results
            ],
            "errors": self.errors,
            "processing_time_ms": self.processing_time_ms,
        }


# Type alias for progress callback
ProgressCallback = Callable[[BatchProgress], Awaitable[None]]


class LLMBatchProcessor:
    """
    Batch processor for LLM requests with async processing and progress tracking.
    
    Features:
    - Groups compatible requests by provider (Requirement 10.1)
    - Processes batches asynchronously with progress tracking (Requirement 10.5)
    - Handles errors gracefully without failing entire batch
    - Supports concurrent request processing with configurable limits
    
    **Validates: Requirements 10.1, 10.5**
    """
    
    def __init__(
        self,
        llm_switcher: Any = None,
        max_concurrent_requests: int = 10,
        batch_timeout_seconds: float = 300.0,
        enable_batching: bool = True,
    ):
        """
        Initialize the LLM batch processor.
        
        Args:
            llm_switcher: LLMSwitcher instance for making LLM calls
            max_concurrent_requests: Maximum concurrent requests per batch
            batch_timeout_seconds: Timeout for entire batch processing
            enable_batching: Whether to enable request batching by provider
        """
        self._llm_switcher = llm_switcher
        self._max_concurrent = max_concurrent_requests
        self._batch_timeout = batch_timeout_seconds
        self._enable_batching = enable_batching
        
        # Active batch tracking
        self._active_batches: Dict[str, BatchProgress] = {}
        self._batch_results: Dict[str, BatchResult] = {}
        self._lock = asyncio.Lock()
        
        # Cancellation tokens
        self._cancelled_batches: set = set()
    
    def set_llm_switcher(self, llm_switcher: Any) -> None:
        """Set or update the LLM switcher instance."""
        self._llm_switcher = llm_switcher
    
    def enable_batching(self, enabled: bool = True) -> None:
        """Enable or disable request batching by provider."""
        self._enable_batching = enabled
        logger.info(f"Request batching {'enabled' if enabled else 'disabled'}")
    
    def is_batching_enabled(self) -> bool:
        """Check if batching is enabled."""
        return self._enable_batching
    
    async def process_batch(
        self,
        requests: List[LLMRequest],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> BatchResult:
        """
        Process a batch of LLM requests.
        
        Groups compatible requests by provider and processes them asynchronously
        with progress tracking.
        
        Args:
            requests: List of LLM requests to process
            progress_callback: Optional async callback for progress updates
            
        Returns:
            BatchResult with all request results and progress information
            
        **Validates: Requirements 10.1, 10.5**
        """
        if not self._llm_switcher:
            raise ValueError("LLM switcher not configured")
        
        batch_id = str(uuid4())
        start_time = time.time()
        
        # Initialize progress tracking
        progress = BatchProgress(
            batch_id=batch_id,
            total_requests=len(requests),
            status=BatchStatus.PENDING,
            started_at=datetime.now(),
        )
        
        # Store active batch
        async with self._lock:
            self._active_batches[batch_id] = progress
        
        # Initialize result
        result = BatchResult(
            batch_id=batch_id,
            progress=progress,
        )
        
        try:
            # Update status to processing
            progress.status = BatchStatus.PROCESSING
            progress.updated_at = datetime.now()
            
            if progress_callback:
                await progress_callback(progress)
            
            # Group requests by provider if batching is enabled
            if self._enable_batching:
                grouped_requests = self._group_requests_by_provider(requests)
                logger.info(
                    f"Batch {batch_id}: Grouped {len(requests)} requests into "
                    f"{len(grouped_requests)} provider groups"
                )
            else:
                # Process all requests without grouping
                grouped_requests = {"all": requests}
            
            # Process each group
            all_results = []
            for group_key, group_requests in grouped_requests.items():
                if batch_id in self._cancelled_batches:
                    logger.info(f"Batch {batch_id} cancelled, stopping processing")
                    break
                
                group_results = await self._process_request_group(
                    batch_id=batch_id,
                    requests=group_requests,
                    progress=progress,
                    progress_callback=progress_callback,
                )
                all_results.extend(group_results)
            
            result.results = all_results
            
            # Determine final status
            if batch_id in self._cancelled_batches:
                progress.status = BatchStatus.CANCELLED
            elif progress.failed_requests == 0:
                progress.status = BatchStatus.COMPLETED
            elif progress.completed_requests == 0:
                progress.status = BatchStatus.FAILED
            else:
                progress.status = BatchStatus.PARTIALLY_COMPLETED
            
        except asyncio.TimeoutError:
            progress.status = BatchStatus.FAILED
            result.errors.append(f"Batch timeout after {self._batch_timeout}s")
            logger.error(f"Batch {batch_id} timed out")
            
        except Exception as e:
            progress.status = BatchStatus.FAILED
            result.errors.append(f"Batch processing error: {str(e)}")
            logger.error(f"Batch {batch_id} failed: {e}")
            
        finally:
            # Finalize progress
            progress.completed_at = datetime.now()
            progress.updated_at = datetime.now()
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Store final result
            async with self._lock:
                self._batch_results[batch_id] = result
                if batch_id in self._active_batches:
                    del self._active_batches[batch_id]
                if batch_id in self._cancelled_batches:
                    self._cancelled_batches.remove(batch_id)
            
            # Final progress callback
            if progress_callback:
                await progress_callback(progress)
        
        return result
    
    def _group_requests_by_provider(
        self,
        requests: List[LLMRequest]
    ) -> Dict[str, List[LLMRequest]]:
        """
        Group compatible requests by provider.
        
        Requests are grouped by their target provider/method to enable
        efficient batch processing.
        
        **Validates: Requirements 10.1**
        """
        groups: Dict[str, List[LLMRequest]] = defaultdict(list)
        
        for request in requests:
            key = request.get_provider_key()
            groups[key].append(request)
        
        return dict(groups)
    
    async def _process_request_group(
        self,
        batch_id: str,
        requests: List[LLMRequest],
        progress: BatchProgress,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[LLMRequestResult]:
        """
        Process a group of requests with concurrency control.
        
        Uses a semaphore to limit concurrent requests and provides
        progress updates as requests complete.
        """
        semaphore = asyncio.Semaphore(self._max_concurrent)
        results: List[LLMRequestResult] = []
        
        async def process_single(request: LLMRequest) -> LLMRequestResult:
            async with semaphore:
                # Check for cancellation
                if batch_id in self._cancelled_batches:
                    return LLMRequestResult(
                        request_id=request.request_id,
                        success=False,
                        error="Batch cancelled",
                    )
                
                return await self._process_single_request(request)
        
        # Create tasks for all requests
        tasks = [process_single(req) for req in requests]
        
        # Process with progress tracking
        for coro in asyncio.as_completed(tasks):
            try:
                result = await asyncio.wait_for(
                    coro,
                    timeout=self._batch_timeout
                )
                results.append(result)
                
                # Update progress
                if result.success:
                    progress.completed_requests += 1
                else:
                    progress.failed_requests += 1
                
                progress.updated_at = datetime.now()
                
                # Notify progress
                if progress_callback:
                    await progress_callback(progress)
                    
            except asyncio.TimeoutError:
                # Individual request timeout
                progress.failed_requests += 1
                progress.updated_at = datetime.now()
                
                if progress_callback:
                    await progress_callback(progress)
        
        return results
    
    async def _process_single_request(
        self,
        request: LLMRequest
    ) -> LLMRequestResult:
        """
        Process a single LLM request.
        
        Handles errors gracefully without failing the entire batch.
        """
        start_time = time.time()
        
        try:
            # Ensure switcher is initialized
            await self._llm_switcher.initialize()
            
            # Make the LLM call
            response = await self._llm_switcher.generate(
                prompt=request.prompt,
                options=request.options,
                method=request.method,
                model=request.model,
                system_prompt=request.system_prompt,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return LLMRequestResult(
                request_id=request.request_id,
                success=True,
                response=response,
                latency_ms=latency_ms,
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Request {request.request_id} failed: {e}")
            
            return LLMRequestResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )
    
    async def submit_batch(
        self,
        requests: List[LLMRequest],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Submit a batch for async processing and return immediately.
        
        Args:
            requests: List of LLM requests to process
            progress_callback: Optional async callback for progress updates
            
        Returns:
            Batch ID for tracking the batch
        """
        batch_id = str(uuid4())
        
        # Initialize progress
        progress = BatchProgress(
            batch_id=batch_id,
            total_requests=len(requests),
            status=BatchStatus.PENDING,
        )
        
        async with self._lock:
            self._active_batches[batch_id] = progress
        
        # Start processing in background
        asyncio.create_task(
            self._process_batch_async(batch_id, requests, progress_callback)
        )
        
        return batch_id
    
    async def _process_batch_async(
        self,
        batch_id: str,
        requests: List[LLMRequest],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        """Background task for async batch processing."""
        try:
            # Create a modified request list with the pre-assigned batch_id
            result = await self.process_batch(requests, progress_callback)
            
            # Update stored result with correct batch_id
            async with self._lock:
                self._batch_results[batch_id] = result
                
        except Exception as e:
            logger.error(f"Async batch {batch_id} failed: {e}")
    
    async def get_batch_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """
        Get current progress of a batch.
        
        Args:
            batch_id: ID of the batch to check
            
        Returns:
            BatchProgress if found, None otherwise
        """
        async with self._lock:
            # Check active batches first
            if batch_id in self._active_batches:
                return self._active_batches[batch_id]
            
            # Check completed batches
            if batch_id in self._batch_results:
                return self._batch_results[batch_id].progress
        
        return None
    
    async def get_batch_result(self, batch_id: str) -> Optional[BatchResult]:
        """
        Get the result of a completed batch.
        
        Args:
            batch_id: ID of the batch
            
        Returns:
            BatchResult if completed, None if still processing or not found
        """
        async with self._lock:
            return self._batch_results.get(batch_id)
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a batch that is currently processing.
        
        Args:
            batch_id: ID of the batch to cancel
            
        Returns:
            True if cancellation was initiated, False if batch not found
        """
        async with self._lock:
            if batch_id in self._active_batches:
                self._cancelled_batches.add(batch_id)
                self._active_batches[batch_id].status = BatchStatus.CANCELLED
                logger.info(f"Batch {batch_id} cancellation requested")
                return True
        
        return False
    
    async def list_active_batches(self) -> List[BatchProgress]:
        """Get list of all active batch progresses."""
        async with self._lock:
            return list(self._active_batches.values())
    
    async def cleanup_completed_batches(self, max_age_seconds: float = 3600) -> int:
        """
        Clean up completed batch results older than specified age.
        
        Args:
            max_age_seconds: Maximum age in seconds for completed batches
            
        Returns:
            Number of batches cleaned up
        """
        cutoff_time = datetime.now()
        cleaned_count = 0
        
        async with self._lock:
            batches_to_remove = []
            
            for batch_id, result in self._batch_results.items():
                if result.progress.completed_at:
                    age = (cutoff_time - result.progress.completed_at).total_seconds()
                    if age > max_age_seconds:
                        batches_to_remove.append(batch_id)
            
            for batch_id in batches_to_remove:
                del self._batch_results[batch_id]
                cleaned_count += 1
        
        return cleaned_count


# ==================== Singleton Instance ====================

_batch_processor_instance: Optional[LLMBatchProcessor] = None


def get_batch_processor(
    llm_switcher: Any = None,
    max_concurrent_requests: int = 10,
) -> LLMBatchProcessor:
    """
    Get or create the LLM batch processor instance.
    
    Args:
        llm_switcher: LLMSwitcher instance
        max_concurrent_requests: Maximum concurrent requests
        
    Returns:
        LLMBatchProcessor instance
    """
    global _batch_processor_instance
    
    if _batch_processor_instance is None:
        _batch_processor_instance = LLMBatchProcessor(
            llm_switcher=llm_switcher,
            max_concurrent_requests=max_concurrent_requests,
        )
    elif llm_switcher is not None:
        _batch_processor_instance.set_llm_switcher(llm_switcher)
    
    return _batch_processor_instance
