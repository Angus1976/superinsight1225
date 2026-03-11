"""
Property-based tests for Pipeline Execution.

Property 7: Pipeline Dependency Ordering — stages execute in valid topological order.
Property 11: Pipeline Execution Invariants — every stage emits progress, produces output, caches result.

Validates: Requirements 3.3, 5.1, 5.2, 5.3
"""

import asyncio
from typing import Any, Dict, List

import pytest
from hypothesis import given, settings, strategies as st

from src.toolkit.models.execution import (
    ExecutionResult,
    ExecutionState,
    ProgressEvent,
    StageOutput,
    StageState,
)
from src.toolkit.models.processing_plan import ProcessingPlan, ProcessingStage
from src.toolkit.orchestration.pipeline_executor import PipelineExecutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_async(coro):
    """Run an async coroutine synchronously for Hypothesis tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def linear_pipeline(draw):
    """Generate a linear chain of 1-5 stages where each depends on the previous."""
    n = draw(st.integers(min_value=1, max_value=5))
    stages: List[ProcessingStage] = []
    for i in range(n):
        deps = [stages[i - 1].stage_id] if i > 0 else []
        stages.append(ProcessingStage(
            stage_id=f"stage-{i}",
            stage_name=f"Stage {i}",
            tool_chain=[f"tool-{i}"],
            dependencies=deps,
        ))
    return ProcessingPlan(stages=stages, explanation="linear pipeline")


@st.composite
def dag_pipeline(draw):
    """Generate a DAG pipeline with 2-5 stages and valid dependency edges.

    Stages are numbered 0..n-1. Each stage may depend on any earlier stage,
    guaranteeing a valid DAG (no cycles).
    """
    n = draw(st.integers(min_value=2, max_value=5))
    stages: List[ProcessingStage] = []
    for i in range(n):
        # Each stage can depend on any subset of earlier stages
        possible_deps = [f"stage-{j}" for j in range(i)]
        deps = draw(st.lists(
            st.sampled_from(possible_deps) if possible_deps else st.nothing(),
            max_size=min(i, 3),
            unique=True,
        ))
        stages.append(ProcessingStage(
            stage_id=f"stage-{i}",
            stage_name=f"Stage {i}",
            tool_chain=[f"tool-{i}"],
            dependencies=deps,
        ))
    return ProcessingPlan(stages=stages, explanation="dag pipeline")


@st.composite
def any_valid_pipeline(draw):
    """Draw either a linear or DAG pipeline."""
    return draw(st.one_of(linear_pipeline(), dag_pipeline()))


# ---------------------------------------------------------------------------
# Property 7: Pipeline Dependency Ordering
# Validates: Requirement 3.3
#
# For any valid DAG of ProcessingStages, after pipeline execution,
# every stage's dependencies must have completed before it started.
# ---------------------------------------------------------------------------

class TestPipelineDependencyOrdering:
    """**Validates: Requirement 3.3**"""

    @given(plan=any_valid_pipeline())
    @settings(max_examples=50, deadline=10000)
    def test_dependencies_complete_before_dependents(self, plan: ProcessingPlan):
        """For every stage, all its dependencies completed before it started."""
        executor = PipelineExecutor()
        result = run_async(executor.execute_pipeline(plan, data_source="test-input"))

        assert result.state == ExecutionState.COMPLETED

        # Build a map of stage_id → dependencies for quick lookup
        dep_map: Dict[str, List[str]] = {
            s.stage_id: s.dependencies for s in plan.stages
        }

        # Collect execution order from stage_outputs (dict preserves insertion order)
        execution_order = list(result.stage_outputs.keys())

        for stage_id in execution_order:
            stage_idx = execution_order.index(stage_id)
            for dep_id in dep_map.get(stage_id, []):
                dep_idx = execution_order.index(dep_id)
                assert dep_idx < stage_idx, (
                    f"Dependency {dep_id} (index {dep_idx}) must execute "
                    f"before {stage_id} (index {stage_idx})"
                )

        # Also verify via timestamps: dependency completed_at <= stage started_at
        for stage_id, output in result.stage_outputs.items():
            for dep_id in dep_map.get(stage_id, []):
                dep_output = result.stage_outputs[dep_id]
                assert dep_output.completed_at is not None, (
                    f"Dependency {dep_id} must have completed_at"
                )
                assert output.started_at is not None, (
                    f"Stage {stage_id} must have started_at"
                )
                assert dep_output.completed_at <= output.started_at, (
                    f"Dependency {dep_id} completed at {dep_output.completed_at} "
                    f"but {stage_id} started at {output.started_at}"
                )


# ---------------------------------------------------------------------------
# Property 11: Pipeline Execution Invariants
# Validates: Requirements 5.1, 5.2, 5.3
#
# For any valid pipeline:
# - Every stage emits at least one progress event (5.1)
# - Every stage produces non-None output (5.2)
# - Every stage result is cached (5.3)
# ---------------------------------------------------------------------------

class TestPipelineExecutionInvariants:
    """**Validates: Requirements 5.1, 5.2, 5.3**"""

    @given(plan=any_valid_pipeline())
    @settings(max_examples=50, deadline=10000)
    def test_every_stage_emits_progress_produces_output_and_caches(
        self, plan: ProcessingPlan
    ):
        """Every stage emits progress, produces output, and caches result."""
        progress_events: List[ProgressEvent] = []

        def on_progress(event: ProgressEvent):
            progress_events.append(event)

        executor = PipelineExecutor(on_progress=on_progress)
        result = run_async(executor.execute_pipeline(plan, data_source="test-input"))

        assert result.state == ExecutionState.COMPLETED

        stage_ids = {s.stage_id for s in plan.stages}

        # --- Invariant 1: every stage emits at least one progress event ---
        stages_with_progress = {e.stage_id for e in progress_events}
        for sid in stage_ids:
            assert sid in stages_with_progress, (
                f"Stage {sid} must emit at least one progress event"
            )

        # --- Invariant 2: every stage produces non-None output ---
        for sid in stage_ids:
            assert sid in result.stage_outputs, (
                f"Stage {sid} must appear in stage_outputs"
            )
            output = result.stage_outputs[sid]
            assert output.data is not None, (
                f"Stage {sid} must produce non-None output data"
            )
            assert output.state == StageState.COMPLETED, (
                f"Stage {sid} must be in COMPLETED state"
            )

        # --- Invariant 3: every stage result is cached ---
        # Access the internal context to verify caching
        # The executor stores contexts keyed by execution_id
        ctx = executor._contexts.get(result.execution_id)
        assert ctx is not None, "Execution context must be preserved"
        for sid in stage_ids:
            assert sid in ctx.cache, (
                f"Stage {sid} result must be cached"
            )
