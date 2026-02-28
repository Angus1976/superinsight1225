"""
Property-based tests for metamorphic relationships.

**Feature: comprehensive-testing-qa-system, Property 7: Metamorphic Relationship Property**
**Validates: Requirements 2.4**

Metamorphic testing verifies that when we transform inputs in a known way,
the outputs change (or don't change) in a predictable way.

Relationships tested:
- Weighted score: scaling all weights by same factor doesn't change result
- Cohen's kappa: swapping annotator order doesn't change result (symmetry)
- Serialization: different paths produce equivalent deserialized data
- Annotation time_spent: adding in parts equals adding total (additivity)
- Weighted score: uniform scores are invariant to weight distribution
"""

import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from src.models.task import Task, TaskStatus
from src.models.annotation import Annotation
from src.models.document import Document
from src.quality.quality_scorer import calculate_weighted_score, calculate_cohens_kappa


# =============================================================================
# Strategies
# =============================================================================

QUALITY_DIMS = ["accuracy", "completeness", "timeliness", "consistency"]


@st.composite
def scores_and_weights(draw):
    """Generate score/weight pairs that share at least one dimension."""
    dims = draw(st.lists(
        st.sampled_from(QUALITY_DIMS), min_size=1, max_size=4, unique=True,
    ))
    scores = {
        d: draw(st.floats(min_value=0.0, max_value=1.0))
        for d in dims
    }
    weights = {
        d: draw(st.floats(
            min_value=0.01, max_value=10.0,
            allow_nan=False, allow_infinity=False,
        ))
        for d in dims
    }
    return scores, weights


def annotation_dicts():
    """Generate annotation-like dicts for kappa calculation."""
    keys = st.sampled_from(["label", "sentiment", "category", "intent", "topic"])
    values = st.sampled_from(["positive", "negative", "neutral", "A", "B", "C"])
    return st.dictionaries(keys=keys, values=values, min_size=1, max_size=5)


def _aware_dt():
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 1, 1),
        timezones=st.just(timezone.utc),
    )


def _naive_dt():
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 1, 1),
    )


def _safe_values():
    return st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=-10000, max_value=10000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        st.booleans(),
    )


@st.composite
def task_models(draw):
    return Task(
        task_id=draw(st.uuids()),
        project_id=draw(st.uuids()),
        tenant_id=draw(st.uuids()),
        title=draw(st.text(min_size=1, max_size=80)),
        description=draw(st.one_of(st.none(), st.text(max_size=150))),
        assigned_to=draw(st.one_of(st.none(), st.uuids())),
        status=draw(st.sampled_from([s.value for s in TaskStatus])),
        created_at=draw(_aware_dt()),
        updated_at=draw(_aware_dt()),
        metadata=draw(st.fixed_dictionaries({}, optional={
            "priority": st.integers(min_value=1, max_value=5),
        })),
    )


@st.composite
def annotation_models(draw):
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
            values=_safe_values(),
            min_size=1, max_size=4,
        )),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        time_spent=draw(st.integers(min_value=0, max_value=50000)),
        created_at=draw(_naive_dt()),
    )


@st.composite
def document_models(draw):
    return Document(
        id=draw(st.uuids()),
        source_type=draw(st.sampled_from(["database", "file", "api"])),
        source_config=draw(st.fixed_dictionaries({
            "host": st.text(min_size=1, max_size=20),
        })),
        content=draw(st.text(min_size=1, max_size=200).filter(lambda s: s.strip())),
        metadata=draw(st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=("Ll",)),
                min_size=1, max_size=10,
            ),
            values=st.text(min_size=1, max_size=20),
            max_size=3,
        )),
        created_at=draw(_naive_dt()),
        updated_at=draw(_naive_dt()),
    )


# =============================================================================
# Metamorphic Relationship 1: Weighted Score — Scale Invariance
# Scaling all weights by the same positive factor should not change the result.
# =============================================================================

@given(
    data=scores_and_weights(),
    scale=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_weighted_score_scale_invariance(data, scale):
    """
    Scaling all weights by the same positive factor must not change the result.

    If W' = k * W for all dimensions, then weighted_score(S, W') == weighted_score(S, W).

    **Validates: Requirements 2.4**
    """
    scores, weights = data
    original = calculate_weighted_score(scores, weights)

    scaled_weights = {dim: w * scale for dim, w in weights.items()}
    scaled = calculate_weighted_score(scores, scaled_weights)

    assert abs(original - scaled) < 1e-9, (
        f"Scale invariance violated: original={original}, scaled={scaled}, factor={scale}"
    )


# =============================================================================
# Metamorphic Relationship 2: Cohen's Kappa — Symmetry
# Swapping annotator order should not change the kappa value.
# =============================================================================

@given(ann1=annotation_dicts(), ann2=annotation_dicts())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_cohens_kappa_symmetry(ann1, ann2):
    """
    Cohen's kappa must be symmetric: kappa(A, B) == kappa(B, A).

    Swapping the two annotators should produce the same agreement score.

    **Validates: Requirements 2.4**
    """
    kappa_ab = calculate_cohens_kappa(ann1, ann2)
    kappa_ba = calculate_cohens_kappa(ann2, ann1)

    assert abs(kappa_ab - kappa_ba) < 1e-9, (
        f"Symmetry violated: kappa(A,B)={kappa_ab}, kappa(B,A)={kappa_ba}"
    )


# =============================================================================
# Metamorphic Relationship 3: Serialization Path Equivalence
# model_dump_json() and json.dumps(model_dump()) should produce equivalent data.
# =============================================================================

@given(task=task_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_serialization_path_equivalence(task: Task):
    """
    Two serialization paths for Task must produce equivalent deserialized data.

    Path A: model_dump_json() -> json.loads()
    Path B: model_dump(mode='json') directly

    **Validates: Requirements 2.4**
    """
    path_a = json.loads(task.model_dump_json())
    path_b = task.model_dump(mode="json")

    assert path_a == path_b, (
        f"Serialization paths diverge for Task"
    )


@given(ann=annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_serialization_path_equivalence(ann: Annotation):
    """
    Two serialization paths for Annotation must produce equivalent data.

    Path A: model_dump_json() -> json.loads()
    Path B: model_dump(mode='json') directly

    **Validates: Requirements 2.4**
    """
    path_a = json.loads(ann.model_dump_json())
    path_b = ann.model_dump(mode="json")

    assert path_a == path_b, (
        f"Serialization paths diverge for Annotation"
    )


@given(doc=document_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_document_serialization_path_equivalence(doc: Document):
    """
    Two serialization paths for Document must produce equivalent data.

    Path A: model_dump_json() -> json.loads()
    Path B: model_dump(mode='json') directly

    **Validates: Requirements 2.4**
    """
    path_a = json.loads(doc.model_dump_json())
    path_b = doc.model_dump(mode="json")

    assert path_a == path_b, (
        f"Serialization paths diverge for Document"
    )


# =============================================================================
# Metamorphic Relationship 4: Annotation time_spent Additivity
# Adding time in two parts must equal adding the total at once.
# =============================================================================

@given(
    ann=annotation_models(),
    part1=st.integers(min_value=0, max_value=10000),
    part2=st.integers(min_value=0, max_value=10000),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_time_spent_additivity(ann, part1, part2):
    """
    Adding time_spent in two parts must equal adding the total at once.

    ann.add_time_spent(a); ann.add_time_spent(b) == ann.add_time_spent(a + b)

    **Validates: Requirements 2.4**
    """
    base_time = ann.time_spent

    # Path A: add in two parts
    ann_parts = ann.model_copy(deep=True)
    ann_parts.add_time_spent(part1)
    ann_parts.add_time_spent(part2)

    # Path B: add total at once
    ann_total = ann.model_copy(deep=True)
    ann_total.add_time_spent(part1 + part2)

    assert ann_parts.time_spent == ann_total.time_spent, (
        f"Additivity violated: parts={ann_parts.time_spent}, total={ann_total.time_spent}"
    )
    assert ann_parts.time_spent == base_time + part1 + part2


# =============================================================================
# Metamorphic Relationship 5: Weighted Score — Uniform Score Invariance
# If all dimensions have the same score, the result equals that score
# regardless of how many dimensions or what weights are used.
# =============================================================================

@given(
    value=st.floats(min_value=0.0, max_value=1.0),
    dims=st.lists(
        st.sampled_from(QUALITY_DIMS), min_size=1, max_size=4, unique=True,
    ),
    extra_dim=st.sampled_from(QUALITY_DIMS),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_weighted_score_uniform_dimension_invariance(value, dims, extra_dim):
    """
    With uniform scores, adding or removing dimensions doesn't change the result.

    If score(d) = v for all d, then weighted_score == v regardless of
    which dimensions are included or what weights are used.

    **Validates: Requirements 2.4**
    """
    weights_small = {d: 1.0 for d in dims}
    scores_small = {d: value for d in dims}
    result_small = calculate_weighted_score(scores_small, weights_small)

    # Add an extra dimension with the same score
    all_dims = list(set(dims + [extra_dim]))
    weights_large = {d: 1.0 for d in all_dims}
    scores_large = {d: value for d in all_dims}
    result_large = calculate_weighted_score(scores_large, weights_large)

    assert abs(result_small - value) < 1e-9, (
        f"Uniform score {value} should produce {value}, got {result_small}"
    )
    assert abs(result_large - value) < 1e-9, (
        f"Uniform score {value} with extra dim should produce {value}, got {result_large}"
    )
    assert abs(result_small - result_large) < 1e-9


# =============================================================================
# Metamorphic Relationship 6: Task Field Update Order Independence
# Updating multiple independent fields in different orders produces same state.
# =============================================================================

@given(
    task=task_models(),
    new_status=st.sampled_from([s.value for s in TaskStatus]),
    new_desc=st.one_of(st.none(), st.text(max_size=100)),
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_field_update_order_independence(task, new_status, new_desc):
    """
    Updating independent Task fields in different orders produces the same state.

    Order A: set status, then description
    Order B: set description, then status

    **Validates: Requirements 2.4**
    """
    # Order A: status first, then description
    task_a = task.model_copy(deep=True)
    task_a.status = new_status
    task_a.description = new_desc

    # Order B: description first, then status
    task_b = task.model_copy(deep=True)
    task_b.description = new_desc
    task_b.status = new_status

    assert task_a.status == task_b.status
    assert task_a.description == task_b.description
    assert task_a.model_dump() == task_b.model_dump()
