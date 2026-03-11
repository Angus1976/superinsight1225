"""
PipelineExecutor — async pipeline execution with dependency ordering,
pause/resume/cancel, retry with exponential backoff, progress events,
and intermediate result caching.

Validates Requirements 3.3, 3.4, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4.
"""

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import uuid4

from src.toolkit.models.execution import (
    ExecutionResult,
    ExecutionState,
    ExecutionStatus,
    ProgressEvent,
    StageOutput,
    StageState,
)
from src.toolkit.models.processing_plan import ProcessingPlan, ProcessingStage

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[ProgressEvent], Any]


def topological_sort(stages: List[ProcessingStage]) -> List[ProcessingStage]:
    """Return stages in dependency order using Kahn's algorithm.

    Raises ValueError if a cycle is detected.
    """
    stage_map = {s.stage_id: s for s in stages}
    in_degree: Dict[str, int] = {s.stage_id: 0 for s in stages}
    dependents: Dict[str, List[str]] = defaultdict(list)

    for stage in stages:
        for dep in stage.dependencies:
            if dep not in stage_map:
                continue
            in_degree[stage.stage_id] += 1
            dependents[dep].append(stage.stage_id)

    queue = deque(sid for sid, deg in in_degree.items() if deg == 0)
    ordered: List[ProcessingStage] = []

    while queue:
        sid = queue.popleft()
        ordered.append(stage_map[sid])
        for child in dependents[sid]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(ordered) != len(stages):
        raise ValueError("Cycle detected in stage dependencies")

    return ordered


class _ExecutionContext:
    """Mutable state for a single pipeline execution."""

    def __init__(self, execution_id: str, plan: ProcessingPlan) -> None:
        self.execution_id = execution_id
        self.plan = plan
        self.state = ExecutionState.PENDING
        self.stage_outputs: Dict[str, StageOutput] = {}
        self.cache: Dict[str, Any] = {}
        self.current_stage_id: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused initially

    # --- state helpers ---

    def is_paused(self) -> bool:
        return self.state == ExecutionState.PAUSED

    def is_cancelled(self) -> bool:
        return self.state == ExecutionState.CANCELLED

    def mark_paused(self) -> None:
        self.state = ExecutionState.PAUSED
        self._pause_event.clear()

    def mark_resumed(self) -> None:
        self.state = ExecutionState.RUNNING
        self._pause_event.set()

    async def wait_if_paused(self) -> None:
        """Block until resumed or cancelled."""
        await self._pause_event.wait()


class PipelineExecutor:
    """Async pipeline executor with pause/resume/cancel and retry.

    Usage::

        executor = PipelineExecutor(on_progress=my_callback)
        result = await executor.execute_pipeline(plan, data_source)
    """

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BASE_DELAY = 0.5  # seconds

    def __init__(
        self,
        on_progress: Optional[ProgressCallback] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
    ) -> None:
        self._on_progress = on_progress
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._contexts: Dict[str, _ExecutionContext] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_pipeline(
        self,
        plan: ProcessingPlan,
        data_source: Any = None,
    ) -> ExecutionResult:
        """Execute all stages in dependency order.

        Returns an ExecutionResult with per-stage outputs and final output.
        """
        execution_id = str(uuid4())
        ctx = _ExecutionContext(execution_id, plan)
        self._contexts[execution_id] = ctx
        ctx.state = ExecutionState.RUNNING
        ctx.started_at = datetime.now()

        try:
            return await self._run_stages(ctx, data_source)
        except Exception as exc:
            return self._build_failure_result(ctx, str(exc))

    async def _run_stages(
        self,
        ctx: _ExecutionContext,
        data_source: Any,
    ) -> ExecutionResult:
        """Iterate stages in topological order, handling pause/cancel."""
        ordered = topological_sort(ctx.plan.stages)

        for stage in ordered:
            # Check pause / cancel before each stage
            if ctx.is_paused():
                await ctx.wait_if_paused()
            if ctx.is_cancelled():
                return self._build_cancelled_result(ctx)

            ctx.current_stage_id = stage.stage_id
            stage_input = self._resolve_input(stage, ctx, data_source)

            self._emit_progress(ctx, stage, StageState.RUNNING, "executing")
            output = await self._execute_stage_with_retry(stage, stage_input)

            # Cache and record
            ctx.stage_outputs[stage.stage_id] = output
            ctx.cache[stage.stage_id] = output.data
            ctx.updated_at = datetime.now()

            if output.state == StageState.FAILED:
                self._emit_progress(ctx, stage, StageState.FAILED, output.error or "failed")
                return self._build_failure_result(ctx, output.error)

            self._emit_progress(ctx, stage, StageState.COMPLETED, "done")

        return self._build_success_result(ctx)

    async def execute_stage(
        self,
        stage: ProcessingStage,
        stage_input: Any = None,
    ) -> StageOutput:
        """Execute a single stage (public convenience method)."""
        return await self._execute_stage_with_retry(stage, stage_input)

    # ------------------------------------------------------------------
    # Pause / Resume / Cancel
    # ------------------------------------------------------------------

    def pause_execution(self, execution_id: str) -> bool:
        """Pause a running execution. Returns False if not found/running."""
        ctx = self._contexts.get(execution_id)
        if ctx is None or ctx.state != ExecutionState.RUNNING:
            return False
        ctx.mark_paused()
        return True

    def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution. Returns False if not paused."""
        ctx = self._contexts.get(execution_id)
        if ctx is None or ctx.state != ExecutionState.PAUSED:
            return False
        ctx.mark_resumed()
        return True

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running or paused execution."""
        ctx = self._contexts.get(execution_id)
        if ctx is None:
            return False
        if ctx.state not in (ExecutionState.RUNNING, ExecutionState.PAUSED):
            return False
        ctx.state = ExecutionState.CANCELLED
        ctx._pause_event.set()  # unblock if paused
        return True

    def get_execution_status(self, execution_id: str) -> Optional[ExecutionStatus]:
        """Return a snapshot of execution status."""
        ctx = self._contexts.get(execution_id)
        if ctx is None:
            return None
        return ExecutionStatus(
            execution_id=ctx.execution_id,
            state=ctx.state,
            total_stages=len(ctx.plan.stages),
            completed_stages=sum(
                1 for o in ctx.stage_outputs.values()
                if o.state == StageState.COMPLETED
            ),
            current_stage_id=ctx.current_stage_id,
            started_at=ctx.started_at,
            updated_at=ctx.updated_at,
        )

    # ------------------------------------------------------------------
    # Stage execution with retry
    # ------------------------------------------------------------------

    async def _execute_stage_with_retry(
        self,
        stage: ProcessingStage,
        stage_input: Any,
    ) -> StageOutput:
        """Execute a stage's tool chain with exponential backoff on failure."""
        output = StageOutput(stage_id=stage.stage_id, started_at=datetime.now())

        for attempt in range(self._max_retries):
            try:
                result = await self._run_tool_chain(stage, stage_input)
                output.data = result
                output.state = StageState.COMPLETED
                output.completed_at = datetime.now()
                return output
            except Exception as exc:
                logger.warning(
                    "Stage %s attempt %d failed: %s",
                    stage.stage_id, attempt + 1, exc,
                )
                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        output.state = StageState.FAILED
        output.error = f"All {self._max_retries} retries exhausted for stage {stage.stage_id}"
        output.completed_at = datetime.now()
        return output

    async def _run_tool_chain(
        self,
        stage: ProcessingStage,
        stage_input: Any,
    ) -> Any:
        """Run the tool chain for a stage. Calls each tool's execute if available."""
        current = stage_input
        for tool_id in stage.tool_chain:
            # Tools are resolved externally; here we pass data through
            current = {"tool_id": tool_id, "input": current, "params": stage.parameters}
        return current

    # ------------------------------------------------------------------
    # Input resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_input(
        stage: ProcessingStage,
        ctx: _ExecutionContext,
        data_source: Any,
    ) -> Any:
        """Collect input from dependencies or fall back to data_source."""
        if not stage.dependencies:
            return data_source
        dep_outputs = {}
        for dep_id in stage.dependencies:
            cached = ctx.cache.get(dep_id)
            if cached is not None:
                dep_outputs[dep_id] = cached
        return dep_outputs if dep_outputs else data_source

    # ------------------------------------------------------------------
    # Progress emission
    # ------------------------------------------------------------------

    def _emit_progress(
        self,
        ctx: _ExecutionContext,
        stage: ProcessingStage,
        state: StageState,
        message: str,
    ) -> None:
        """Emit a progress event via the callback, if registered."""
        if self._on_progress is None:
            return
        completed = sum(
            1 for o in ctx.stage_outputs.values()
            if o.state == StageState.COMPLETED
        )
        total = len(ctx.plan.stages)
        pct = (completed / total * 100) if total > 0 else 0.0

        event = ProgressEvent(
            execution_id=ctx.execution_id,
            stage_id=stage.stage_id,
            stage_name=stage.stage_name,
            state=state,
            progress_pct=pct,
            message=message,
        )
        self._on_progress(event)

    # ------------------------------------------------------------------
    # Result builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_success_result(ctx: _ExecutionContext) -> ExecutionResult:
        """Build a successful ExecutionResult from context."""
        ctx.state = ExecutionState.COMPLETED
        last_output = None
        if ctx.stage_outputs:
            last_key = list(ctx.stage_outputs.keys())[-1]
            last_output = ctx.stage_outputs[last_key].data
        return ExecutionResult(
            execution_id=ctx.execution_id,
            state=ExecutionState.COMPLETED,
            stage_outputs=ctx.stage_outputs,
            final_output=last_output,
            started_at=ctx.started_at,
            completed_at=datetime.now(),
        )

    @staticmethod
    def _build_failure_result(
        ctx: _ExecutionContext,
        error: Optional[str] = None,
    ) -> ExecutionResult:
        """Build a failed ExecutionResult preserving completed stages."""
        ctx.state = ExecutionState.FAILED
        return ExecutionResult(
            execution_id=ctx.execution_id,
            state=ExecutionState.FAILED,
            stage_outputs=ctx.stage_outputs,
            final_output=None,
            started_at=ctx.started_at,
            completed_at=datetime.now(),
            error=error,
        )

    @staticmethod
    def _build_cancelled_result(ctx: _ExecutionContext) -> ExecutionResult:
        """Build a cancelled ExecutionResult preserving completed stages."""
        return ExecutionResult(
            execution_id=ctx.execution_id,
            state=ExecutionState.CANCELLED,
            stage_outputs=ctx.stage_outputs,
            final_output=None,
            started_at=ctx.started_at,
            completed_at=datetime.now(),
        )
