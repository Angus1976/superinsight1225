"""
Property-based tests for data transformation invariant preservation.

**Feature: comprehensive-testing-qa-system, Property 5: Data Transformation Invariant Preservation**
**Validates: Requirements 2.2**

Tests that data transformations preserve invariants:
- Weighted score calculation always produces results in [0, 1]
- Cohen's kappa always produces results in [-1, 1]
- Annotation confidence constraints preserved through updates
- Task model transformations preserve required fields and metadata
- ExportRequest validation preserves batch_size constraints
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from src.quality.quality_scorer import calculate_weighted_score, calculate_cohens_kappa
from src.models.task import Task, TaskStatus
from src.models.annotation import Annotation
from src.export.models import ExportFormat, ExportRequest


# =============================================================================
# Hypothesis Strategies
# =============================================================================

VALID_DIMENSIONS = ["accuracy", "completeness", "timeliness", "consistency"]


def dimension_scores() -> st.SearchStrategy[dict]:
    """Generate dimension score dicts with float values."""
    return st.dictionaries(
        keys=st.sampled_from(VALID_DIMENSIONS),
        values=st.floats(min_value=-0.5, max_value=1.5),
        min_size=1,
        max_size=4,
    )


def dimension_weights() -> st.SearchStrategy[dict]:
    """Generate dimension weight dicts with positive floats."""
    return st.dictionaries(
        keys=st.sampled_from(VALID_DIMENSIONS),
        values=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=4,
    )


def annotation_dicts() -> st.SearchStrategy[dict]:
    """Generate annotation-like dicts for kappa calculation."""
    keys = st.sampled_from(["label", "sentiment", "category", "intent", "topic"])
    values = st.sampled_from(["positive", "negative", "neutral", "A", "B", "C"])
    return st.dictionaries(keys=keys, values=values, min_size=0, max_size=5)


def _aware_datetime() -> st.SearchStrategy[datetime]:
    """Generate timezone-aware UTC datetimes."""
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 1, 1),
        timezones=st.just(timezone.utc),
    )


# =============================================================================
# Property 5: Weighted Score Invariant — result always in [0, 1]
# =============================================================================

@given(scores=dimension_scores(), weights=dimension_weights())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_weighted_score_bounded_invariant(scores, weights):
    """
    Weighted score transformation always produces a result in [0, 1].

    The calculate_weighted_score function normalizes input scores to [0, 1]
    and computes a weighted average, so the output must always be bounded.

    **Validates: Requirements 2.2**
    """
    result = calculate_weighted_score(scores, weights)
    assert 0.0 <= result <= 1.0, (
        f"Weighted score {result} out of [0, 1] for scores={scores}, weights={weights}"
    )


@given(weights=dimension_weights())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_weighted_score_empty_scores_invariant(weights):
    """
    Empty scores always produce 0.0 regardless of weights.

    **Validates: Requirements 2.2**
    """
    result = calculate_weighted_score({}, weights)
    assert result == 0.0, f"Expected 0.0 for empty scores, got {result}"


@given(
    scores=st.dictionaries(
        keys=st.sampled_from(VALID_DIMENSIONS),
        values=st.floats(min_value=0.0, max_value=1.0),
        min_size=1,
        max_size=4,
    ),
    weights=st.dictionaries(
        keys=st.sampled_from(VALID_DIMENSIONS),
        values=st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=4,
    ),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_weighted_score_uniform_scores_invariant(scores, weights):
    """
    When all scores are the same valid value, the weighted result equals that value.

    If every dimension has the same score s (already in [0,1]), the weighted
    average must also be s, regardless of weight distribution.

    **Validates: Requirements 2.2**
    """
    if not scores:
        return

    # Make all scores the same value
    uniform_value = list(scores.values())[0]
    uniform_scores = {k: uniform_value for k in scores}

    # Only use weights that overlap with scores
    overlapping_weights = {k: v for k, v in weights.items() if k in uniform_scores}
    if not overlapping_weights or sum(overlapping_weights.values()) <= 0:
        return

    result = calculate_weighted_score(uniform_scores, overlapping_weights)
    assert abs(result - uniform_value) < 1e-9, (
        f"Uniform score {uniform_value} should produce {uniform_value}, got {result}"
    )


# =============================================================================
# Property 5: Cohen's Kappa Invariant — result always in [-1, 1]
# =============================================================================

@given(ann1=annotation_dicts(), ann2=annotation_dicts())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_cohens_kappa_bounded_invariant(ann1, ann2):
    """
    Cohen's kappa transformation always produces a result in [-1, 1].

    **Validates: Requirements 2.2**
    """
    result = calculate_cohens_kappa(ann1, ann2)
    assert -1.0 <= result <= 1.0, (
        f"Kappa {result} out of [-1, 1] for ann1={ann1}, ann2={ann2}"
    )


@given(ann=annotation_dicts())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_cohens_kappa_identical_annotations_invariant(ann):
    """
    Identical annotations always produce kappa = 1.0 (perfect agreement).

    **Validates: Requirements 2.2**
    """
    result = calculate_cohens_kappa(ann, ann)
    assert result == 1.0, (
        f"Identical annotations should produce kappa=1.0, got {result}"
    )


# =============================================================================
# Property 5: Task Model Transformation — fields preserved through dump/validate
# =============================================================================

@st.composite
def task_models(draw):
    """Generate valid Task Pydantic model instances."""
    return Task(
        task_id=draw(st.uuids()),
        project_id=draw(st.uuids()),
        tenant_id=draw(st.uuids()),
        title=draw(st.text(min_size=1, max_size=80)),
        description=draw(st.one_of(st.none(), st.text(max_size=150))),
        assigned_to=draw(st.one_of(st.none(), st.uuids())),
        status=draw(st.sampled_from([s.value for s in TaskStatus])),
        created_at=draw(_aware_datetime()),
        updated_at=draw(_aware_datetime()),
        metadata=draw(st.fixed_dictionaries({}, optional={
            "priority": st.integers(min_value=1, max_value=5),
            "tags": st.lists(st.text(min_size=1, max_size=15), max_size=3),
        })),
    )


@given(task=task_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_transformation_preserves_required_fields(task: Task):
    """
    Task model_dump transformation preserves all required fields.

    Converting a Task to dict and back must retain task_id, project_id,
    tenant_id, title, and status.

    **Validates: Requirements 2.2**
    """
    dumped = task.model_dump()

    assert dumped["task_id"] == task.task_id
    assert dumped["project_id"] == task.project_id
    assert dumped["tenant_id"] == task.tenant_id
    assert dumped["title"] == task.title
    assert dumped["status"] == task.status


@given(task=task_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_transformation_preserves_metadata(task: Task):
    """
    Task model_dump transformation preserves metadata dict exactly.

    **Validates: Requirements 2.2**
    """
    dumped = task.model_dump()
    assert dumped["metadata"] == task.metadata


@given(task=task_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_status_valid_after_transformation(task: Task):
    """
    Task status remains a valid TaskStatus value after model_dump.

    **Validates: Requirements 2.2**
    """
    dumped = task.model_dump()
    valid_statuses = {s.value for s in TaskStatus}
    assert dumped["status"] in valid_statuses, (
        f"Status '{dumped['status']}' not in valid set {valid_statuses}"
    )


# =============================================================================
# Property 5: Annotation Confidence Constraint Preservation
# =============================================================================

@st.composite
def annotation_models(draw):
    """Generate valid Annotation Pydantic model instances."""
    return Annotation(
        id=draw(st.uuids()),
        task_id=draw(st.uuids()),
        annotator_id=draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
            min_size=1, max_size=20,
        )),
        annotation_data=draw(st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=("Ll",)),
                min_size=1, max_size=10,
            ),
            values=st.one_of(
                st.text(min_size=1, max_size=30),
                st.integers(min_value=-1000, max_value=1000),
                st.booleans(),
            ),
            min_size=1,
            max_size=4,
        )),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        time_spent=draw(st.integers(min_value=0, max_value=100000)),
    )


@given(ann=annotation_models(), new_conf=st.floats(min_value=0.0, max_value=1.0))
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_confidence_constraint_preserved(ann, new_conf):
    """
    Updating annotation confidence preserves the [0, 1] constraint.

    After update_confidence, the value must still be in [0, 1].

    **Validates: Requirements 2.2**
    """
    ann.update_confidence(new_conf)
    assert 0.0 <= ann.confidence <= 1.0


@given(ann=annotation_models(), extra=st.integers(min_value=0, max_value=50000))
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_time_spent_monotonic(ann, extra):
    """
    Adding time_spent is monotonically increasing (never decreases).

    **Validates: Requirements 2.2**
    """
    original = ann.time_spent
    ann.add_time_spent(extra)
    assert ann.time_spent >= original
    assert ann.time_spent == original + extra


@given(ann=annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_to_dict_preserves_data(ann):
    """
    Annotation to_dict transformation preserves annotation_data exactly.

    The annotation_data dict must survive the to_dict transformation unchanged.

    **Validates: Requirements 2.2**
    """
    result = ann.to_dict()
    assert result["annotation_data"] == ann.annotation_data
    assert result["annotator_id"] == ann.annotator_id
    assert result["confidence"] == ann.confidence
    assert result["time_spent"] == ann.time_spent


# =============================================================================
# Property 5: ExportRequest Batch Size Constraint Preservation
# =============================================================================

@given(
    batch_size=st.integers(min_value=1, max_value=10000),
    fmt=st.sampled_from(list(ExportFormat)),
    include_ann=st.booleans(),
    include_ai=st.booleans(),
    include_meta=st.booleans(),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_export_request_constraints_preserved(batch_size, fmt, include_ann, include_ai, include_meta):
    """
    ExportRequest validation preserves batch_size in [1, 10000] and format enum.

    After constructing an ExportRequest, the constraints must hold.

    **Validates: Requirements 2.2**
    """
    req = ExportRequest(
        format=fmt,
        batch_size=batch_size,
        include_annotations=include_ann,
        include_ai_predictions=include_ai,
        include_metadata=include_meta,
    )

    assert 1 <= req.batch_size <= 10000
    assert req.format in ExportFormat
    assert req.include_annotations == include_ann
    assert req.include_ai_predictions == include_ai
    assert req.include_metadata == include_meta
