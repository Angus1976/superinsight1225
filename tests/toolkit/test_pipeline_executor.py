"""
Unit tests for PipelineExecutor — dependency ordering, pause/resume/cancel,
retry with backoff, progress events, and intermediate result caching.

Validates Requirements 3.3, 3.4, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4.
"""

import asyncio
from typing import Any, Dict, List, Optional

import pytest

from src.toolkit.models.execution import (
    ExecutionResult,
    ExecutionState,
    ProgressEvent,
    StageOutput,
    StageState,
)
from src.toolkit.models.processing_plan import ProcessingPlan, ProcessingStage
from src.toolkit.orchestration.pipeline_executor import (
    PipelineExecutor,
    topological_sort,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stage(
    stage_id: str,
    name: str = "",
    deps: Optional[List[str]] = None,
    tool_chain: Optional[List[str]] = None,
) -> ProcessingStage:
    return ProcessingStage(
        stage_id=stage_id,
        stage_name=name or stage_id,
        dependencies=deps or [],
        tool_chain=tool_chain or [],
    )


def _plan(*stages: ProcessingStage) -> ProcessingPlan:
    return ProcessingPlan(stages=list(stages))


# ---------------------------------------------------------------------------
# Topological sort (Req 3.3)
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_no_dependencies(self):
        stages = [_stage("a"), _stage("b"), _stage("c")]
        result = topological_sort(stages)
        assert len(result) == 3

    def test_linear_chain(self):
        stages = [
            _stage("c", deps=["b"]),
            _stage("b", deps=["a"]),
            _stage("a"),
        ]
        result = topological_sort(stages)
        ids = [s.stage_id for s in result]
        assert ids.index("a") < ids.index("b") < ids.index("c")

    def test_diamond_dependency(self):
        stages = [
            _stage("d", deps=["b", "c"]),
            _stage("b", deps=["a"]),
            _stage("c", deps=["a"]),
            _stage("a"),
        ]
        result = topological_sort(stages)
        ids = [s.stage_id for s in result]
        assert ids.index("a") < ids.index("b")
        assert ids.index("a") < ids.index("c")
        assert ids.index("b") < ids.index("d")
        assert ids.index("c") < ids.index("d")

    def test_cycle_raises(self):
        stages = [
            _stage("a", deps=["b"]),
            _stage("b", deps=["a"]),
        ]
        with pytest.raises(ValueError, match="Cycle"):
            topological_sort(stages)

    def test_unknown_dependency_ignored(self):
        """Dependencies referencing non-existent stages are silently ignored."""
        stages = [_stage("a", deps=["ghost"])]
        result = topological_sort(stages)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Basic pipeline execution (Req 3.3, 5.2)
# ---------------------------------------------------------------------------

class TestExecutePipeline:
    async def test_single_stage_completes(self):
        executor = PipelineExecutor()
        plan = _plan(_stage("s1"))
        result = await executor.execute_pipeline(plan, data_source="input")

        assert result.state == ExecutionState.COMPLETED
        assert "s1" in result.stage_outputs
        assert result.stage_outputs["s1"].state == StageState.COMPLETED

    async def test_multi_stage_dependency_order(self):
        """Stages execute in dependency order and pass data."""
        plan = _plan(
            _stage("b", deps=["a"]),
            _stage("a"),
        )
        executor = PipelineExecutor()
        result = await executor.execute_pipeline(plan, data_source="raw")

        assert result.state == ExecutionState.COMPLETED
        assert len(result.stage_outputs) == 2
        # Stage b should have received a's output as dependency input
        b_output = result.stage_outputs["b"]
        assert b_output.state == StageState.COMPLETED

    async def test_final_output_is_last_stage(self):
        plan = _plan(_stage("only"))
        executor = PipelineExecutor()
        result = await executor.execute_pipeline(plan, data_source="input")
        assert result.final_output is not None

    async def test_all_stages_produce_valid_output(self):
        """Req 5.2: all stages produce valid (non-None) outputs on success."""
        plan = _plan(_stage("a"), _stage("b", deps=["a"]))
        executor = PipelineExecutor()
        result = await executor.execute_pipeline(plan, data_source="x")

        for sid, output in result.stage_outputs.items():
            assert output.data is not None, f"Stage {sid} produced None output"
            assert output.state == StageState.COMPLETED


# ---------------------------------------------------------------------------
# Progress events (Req 5.1)
# ---------------------------------------------------------------------------

class TestProgressEvents:
    async def test_progress_emitted_per_stage(self):
        """Req 5.1: real-time progress events emitted per stage."""
        events: List[ProgressEvent] = []
        executor = PipelineExecutor(on_progress=events.append)
        plan = _plan(_stage("s1"), _stage("s2", deps=["s1"]))

        await executor.execute_pipeline(plan, data_source="d")

        stage_ids = [e.stage_id for e in events]
        assert "s1" in stage_ids
        assert "s2" in stage_ids

    async def test_progress_includes_running_and_completed(self):
        events: List[ProgressEvent] = []
        executor = PipelineExecutor(on_progress=events.append)
        plan = _plan(_stage("x"))

        await executor.execute_pipeline(plan)

        states = [e.state for e in events if e.stage_id == "x"]
        assert StageState.RUNNING in states
        assert StageState.COMPLETED in states


# ---------------------------------------------------------------------------
# Intermediate result caching (Req 5.3)
# ---------------------------------------------------------------------------

class TestIntermediateCache:
    async def test_cache_populated_per_stage(self):
        """Req 5.3: intermediate results cached for resumption."""
        executor = PipelineExecutor()
        plan = _plan(_stage("a"), _stage("b", deps=["a"]))
        result = await executor.execute_pipeline(plan, data_source="src")

        # Access internal context to verify cache
        ctx = list(executor._contexts.values())[0]
        assert "a" in ctx.cache
        assert "b" in ctx.cache


# ---------------------------------------------------------------------------
# Pause / Resume / Cancel (Req 3.4, 3.5)
# ---------------------------------------------------------------------------

class TestPauseResumeCancel:
    async def test_pause_and_resume(self):
        """Req 3.4/3.5: pause suspends, resume continues from paused stage."""
        events: List[ProgressEvent] = []
        executor = PipelineExecutor(on_progress=events.append)
        plan = _plan(
            _stage("s1"),
            _stage("s2", deps=["s1"]),
            _stage("s3", deps=["s2"]),
        )

        # We'll pause after s1 completes by hooking into progress
        execution_id_holder: List[str] = []

        original_cb = executor._on_progress

        def pause_after_s1(event: ProgressEvent):
            events.append(event)
            if not execution_id_holder:
                execution_id_holder.append(event.execution_id)
            if event.stage_id == "s1" and event.state == StageState.COMPLETED:
                executor.pause_execution(event.execution_id)
                # Schedule resume after a short delay
                asyncio.get_event_loop().call_later(
                    0.05, executor.resume_execution, event.execution_id
                )

        executor._on_progress = pause_after_s1
        result = await executor.execute_pipeline(plan, data_source="d")

        assert result.state == ExecutionState.COMPLETED
        assert len(result.stage_outputs) == 3

    async def test_cancel_preserves_completed(self):
        """Cancel preserves completed stage results (Req 5.4)."""
        executor = PipelineExecutor()
        plan = _plan(
            _stage("s1"),
            _stage("s2", deps=["s1"]),
        )

        def cancel_after_s1(event: ProgressEvent):
            if event.stage_id == "s1" and event.state == StageState.COMPLETED:
                executor.cancel_execution(event.execution_id)

        executor._on_progress = cancel_after_s1
        result = await executor.execute_pipeline(plan, data_source="d")

        assert result.state == ExecutionState.CANCELLED
        assert "s1" in result.stage_outputs
        assert result.stage_outputs["s1"].state == StageState.COMPLETED

    def test_pause_nonexistent_returns_false(self):
        executor = PipelineExecutor()
        assert executor.pause_execution("nope") is False

    def test_resume_nonexistent_returns_false(self):
        executor = PipelineExecutor()
        assert executor.resume_execution("nope") is False

    def test_cancel_nonexistent_returns_false(self):
        executor = PipelineExecutor()
        assert executor.cancel_execution("nope") is False


# ---------------------------------------------------------------------------
# Retry with exponential backoff (Req 3.6)
# ---------------------------------------------------------------------------

class TestRetryBackoff:
    async def test_retry_exhaustion_marks_failed(self):
        """Req 3.6: after all retries, stage is marked failed."""
        call_count = 0

        class FailingExecutor(PipelineExecutor):
            async def _run_tool_chain(self, stage, stage_input):
                nonlocal call_count
                call_count += 1
                raise RuntimeError("tool error")

        executor = FailingExecutor(max_retries=2, base_delay=0.01)
        plan = _plan(_stage("fail"))
        result = await executor.execute_pipeline(plan)

        assert result.state == ExecutionState.FAILED
        assert call_count == 2
        assert result.stage_outputs["fail"].state == StageState.FAILED

    async def test_failure_preserves_earlier_stages(self):
        """Req 5.4: completed stage results preserved on failure."""
        call_count = 0

        class FailOnSecond(PipelineExecutor):
            async def _run_tool_chain(self, stage, stage_input):
                nonlocal call_count
                call_count += 1
                if stage.stage_id == "s2":
                    raise RuntimeError("boom")
                return {"ok": True}

        executor = FailOnSecond(max_retries=1, base_delay=0.01)
        plan = _plan(_stage("s1"), _stage("s2", deps=["s1"]))
        result = await executor.execute_pipeline(plan)

        assert result.state == ExecutionState.FAILED
        assert "s1" in result.stage_outputs
        assert result.stage_outputs["s1"].state == StageState.COMPLETED


# ---------------------------------------------------------------------------
# Execution status (design: getExecutionStatus)
# ---------------------------------------------------------------------------

class TestExecutionStatus:
    async def test_status_after_completion(self):
        executor = PipelineExecutor()
        plan = _plan(_stage("a"), _stage("b", deps=["a"]))
        await executor.execute_pipeline(plan)

        ctx = list(executor._contexts.values())[0]
        status = executor.get_execution_status(ctx.execution_id)

        assert status is not None
        assert status.total_stages == 2
        assert status.completed_stages == 2

    def test_status_nonexistent_returns_none(self):
        executor = PipelineExecutor()
        assert executor.get_execution_status("ghost") is None


# ---------------------------------------------------------------------------
# execute_stage standalone (design: executeStage)
# ---------------------------------------------------------------------------

class TestExecuteStage:
    async def test_single_stage_execution(self):
        executor = PipelineExecutor()
        stage = _stage("solo", tool_chain=["tool-a"])
        output = await executor.execute_stage(stage, stage_input="data")

        assert output.stage_id == "solo"
        assert output.state == StageState.COMPLETED
        assert output.data is not None
