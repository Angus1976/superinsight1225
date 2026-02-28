"""
Property-based tests for idempotent operations.

**Feature: comprehensive-testing-qa-system, Property 6: Idempotent Operation Property**
**Validates: Requirements 2.3**

Tests that idempotent operations produce the same result when applied
multiple times: f(f(x)) == f(x).
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from src.models.task import Task, TaskStatus
from src.models.annotation import Annotation
from src.models.document import Document
from src.export.models import (
    ExportFormat,
    ExportRequest,
    ExportResult,
    COCOAnnotation,
)
from src.quality.quality_scorer import calculate_weighted_score

from tests.strategies import json_serializable_data


# =============================================================================
# Hypothesis Strategies
# =============================================================================

VALID_TASK_STATUSES = ["pending", "in_progress", "completed", "failed", "cancelled"]
VALID_SOURCE_TYPES = ["database", "file", "api"]


def _aware_datetime() -> st.SearchStrategy[datetime]:
    """Generate timezone-aware UTC datetimes."""
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 1, 1),
        timezones=st.just(timezone.utc),
    )


def _naive_datetime() -> st.SearchStrategy[datetime]:
    """Generate naive datetimes."""
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 1, 1),
    )


def _safe_json_values():
    """JSON-safe primitive values."""
    return st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=-10000, max_value=10000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        st.booleans(),
    )


@st.composite
def task_models(draw):
    """Generate valid Task Pydantic model instances."""
    return Task(
        task_id=draw(st.uuids()),
        project_id=draw(st.uuids()),
        tenant_id=draw(st.uuids()),
        title=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.one_of(st.none(), st.text(max_size=200))),
        assigned_to=draw(st.one_of(st.none(), st.uuids())),
        status=draw(st.sampled_from(VALID_TASK_STATUSES)),
        created_at=draw(_aware_datetime()),
        updated_at=draw(_aware_datetime()),
        metadata=draw(st.fixed_dictionaries({}, optional={
            "priority": st.integers(min_value=1, max_value=5),
            "tags": st.lists(st.text(min_size=1, max_size=20), max_size=3),
        })),
    )


@st.composite
def annotation_models(draw):
    """Generate valid Annotation Pydantic model instances."""
    return Annotation(
        id=draw(st.uuids()),
        task_id=draw(st.uuids()),
        annotator_id=draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
            min_size=1, max_size=30,
        )),
        annotation_data=draw(st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=("Ll",)),
                min_size=1, max_size=15,
            ),
            values=_safe_json_values(),
            min_size=1, max_size=5,
        )),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        time_spent=draw(st.integers(min_value=0, max_value=100000)),
        created_at=draw(_naive_datetime()),
    )


@st.composite
def document_models(draw):
    """Generate valid Document Pydantic model instances."""
    return Document(
        id=draw(st.uuids()),
        source_type=draw(st.sampled_from(VALID_SOURCE_TYPES)),
        source_config=draw(st.fixed_dictionaries({
            "host": st.text(min_size=1, max_size=20),
        })),
        content=draw(st.text(min_size=1, max_size=200).filter(lambda s: s.strip())),
        metadata=draw(st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=("Ll",)),
                min_size=1, max_size=15,
            ),
            values=st.text(min_size=1, max_size=30),
            max_size=3,
        )),
        created_at=draw(_naive_datetime()),
        updated_at=draw(_naive_datetime()),
    )


# =============================================================================
# Weighted score strategies
# =============================================================================

QUALITY_DIMENSIONS = ["accuracy", "completeness", "timeliness", "consistency"]


@st.composite
def dimension_scores(draw):
    """Generate dimension score dicts with values that may exceed [0,1]."""
    dims = draw(st.lists(
        st.sampled_from(QUALITY_DIMENSIONS), min_size=1, max_size=4, unique=True,
    ))
    return {
        d: draw(st.floats(min_value=-0.5, max_value=1.5, allow_nan=False, allow_infinity=False))
        for d in dims
    }


@st.composite
def dimension_weights(draw):
    """Generate positive dimension weights."""
    dims = draw(st.lists(
        st.sampled_from(QUALITY_DIMENSIONS), min_size=1, max_size=4, unique=True,
    ))
    return {
        d: draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False))
        for d in dims
    }


# =============================================================================
# Property 6: Idempotent Operation Tests
# =============================================================================

@given(task=task_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_validation_idempotent(task: Task):
    """
    Validating a Task model twice produces the same result as once.

    f(x) == f(f(x)) where f = model_validate(model_dump())

    **Validates: Requirements 2.3**
    """
    dumped = task.model_dump()
    once = Task.model_validate(dumped)
    twice = Task.model_validate(once.model_dump())
    assert once == twice


@given(ann=annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_validation_idempotent(ann: Annotation):
    """
    Validating an Annotation model twice produces the same result as once.

    **Validates: Requirements 2.3**
    """
    dumped = ann.model_dump()
    once = Annotation.model_validate(dumped)
    twice = Annotation.model_validate(once.model_dump())
    assert once == twice


@given(doc=document_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_document_validation_idempotent(doc: Document):
    """
    Validating a Document model twice produces the same result as once.

    **Validates: Requirements 2.3**
    """
    dumped = doc.model_dump()
    once = Document.model_validate(dumped)
    twice = Document.model_validate(once.model_dump())
    assert once == twice


@given(data=json_serializable_data())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_json_loads_idempotent(data):
    """
    json.loads(json.dumps(x)) is idempotent: applying it twice
    gives the same result as applying it once.

    **Validates: Requirements 2.3**
    """
    once = json.loads(json.dumps(data))
    twice = json.loads(json.dumps(once))
    assert once == twice


@given(scores=dimension_scores(), weights=dimension_weights())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_weighted_score_normalization_idempotent(scores, weights):
    """
    calculate_weighted_score normalizes inputs to [0,1].
    Feeding the result back as a single-dimension score should
    produce the same value: the output is already normalized.

    **Validates: Requirements 2.3**
    """
    first_result = calculate_weighted_score(scores, weights)

    # Feed the already-normalized result back as a single score
    normalized_input = {"result": first_result}
    uniform_weight = {"result": 1.0}
    second_result = calculate_weighted_score(normalized_input, uniform_weight)

    assert abs(first_result - second_result) < 1e-9


@given(task=task_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_status_set_idempotent(task: Task):
    """
    Setting a task's status to the same value twice is idempotent.

    **Validates: Requirements 2.3**
    """
    original_status = task.status
    task.status = original_status  # set once
    after_first = task.model_dump()
    task.status = original_status  # set again
    after_second = task.model_dump()
    assert after_first == after_second


@given(ann=annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_confidence_set_idempotent(ann: Annotation):
    """
    Setting annotation confidence to the same value twice is idempotent.

    **Validates: Requirements 2.3**
    """
    original_conf = ann.confidence
    ann.update_confidence(original_conf)
    after_first = ann.confidence
    ann.update_confidence(original_conf)
    after_second = ann.confidence
    assert after_first == after_second


@given(ann=annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_to_dict_from_dict_idempotent(ann: Annotation):
    """
    Annotation to_dict/from_dict round-trip is idempotent when repeated.
    Comparing at model level avoids type coercion differences in dicts.

    **Validates: Requirements 2.3**
    """
    model_once = Annotation.from_dict(ann.to_dict())
    model_twice = Annotation.from_dict(model_once.to_dict())

    assert str(model_once.id) == str(model_twice.id)
    assert str(model_once.task_id) == str(model_twice.task_id)
    assert model_once.annotator_id == model_twice.annotator_id
    assert model_once.annotation_data == model_twice.annotation_data
    assert model_once.confidence == model_twice.confidence
    assert model_once.time_spent == model_twice.time_spent


@given(doc=document_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_document_to_dict_from_dict_idempotent(doc: Document):
    """
    Document to_dict/from_dict round-trip is idempotent when repeated.
    Comparing at model level avoids type coercion differences in dicts.

    **Validates: Requirements 2.3**
    """
    model_once = Document.from_dict(doc.to_dict())
    model_twice = Document.from_dict(model_once.to_dict())

    assert str(model_once.id) == str(model_twice.id)
    assert model_once.source_type == model_twice.source_type
    assert model_once.source_config == model_twice.source_config
    assert model_once.content == model_twice.content
    assert model_once.metadata == model_twice.metadata
