"""
Property-based tests for serialization round-trip on all Pydantic models.

**Feature: comprehensive-testing-qa-system, Property 4: Serialization Round-Trip Property**
**Validates: Requirements 2.1**

Tests that serializing a model to JSON and deserializing back produces
an equivalent object, using Hypothesis to generate 100+ test cases per model.
"""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from src.models.task import Task
from src.models.annotation import Annotation
from src.models.document import Document
from src.export.models import (
    ExportFormat,
    ExportRequest,
    ExportResult,
    ExportedDocument,
    COCOAnnotation,
    COCOCategory,
    COCOImage,
)

from tests.strategies import valid_email, valid_uuid, json_serializable_data


# =============================================================================
# Hypothesis Strategies for Pydantic Models
# =============================================================================

def _aware_datetime() -> st.SearchStrategy[datetime]:
    """Generate timezone-aware UTC datetimes for Task model."""
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 1, 1),
        timezones=st.just(timezone.utc),
    )


def _naive_datetime() -> st.SearchStrategy[datetime]:
    """Generate naive datetimes for Annotation/Document models."""
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 1, 1),
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
        status=draw(st.sampled_from(["pending", "in_progress", "completed", "failed", "cancelled"])),
        created_at=draw(_aware_datetime()),
        updated_at=draw(_aware_datetime()),
        metadata=draw(st.fixed_dictionaries({}, optional={
            "priority": st.integers(min_value=1, max_value=5),
            "tags": st.lists(st.text(min_size=1, max_size=20), max_size=3),
        })),
    )


def _safe_json_values():
    """JSON-safe primitive values (no NaN/Infinity floats)."""
    return st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=-10000, max_value=10000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        st.booleans(),
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
            min_size=1,
            max_size=5,
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
        source_type=draw(st.sampled_from(["database", "file", "api"])),
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


@st.composite
def export_request_models(draw):
    """Generate valid ExportRequest Pydantic model instances."""
    return ExportRequest(
        project_id=draw(st.one_of(st.none(), st.builds(lambda: str(uuid4())))),
        task_ids=draw(st.one_of(st.none(), st.lists(
            st.builds(lambda: str(uuid4())), min_size=0, max_size=3
        ))),
        document_ids=None,
        format=draw(st.sampled_from(list(ExportFormat))),
        include_annotations=draw(st.booleans()),
        include_ai_predictions=draw(st.booleans()),
        include_metadata=draw(st.booleans()),
        batch_size=draw(st.integers(min_value=1, max_value=10000)),
    )


@st.composite
def export_result_models(draw):
    """Generate valid ExportResult Pydantic model instances."""
    return ExportResult(
        export_id=draw(st.builds(lambda: str(uuid4()))),
        status=draw(st.sampled_from(["pending", "running", "completed", "failed"])),
        format=draw(st.sampled_from(list(ExportFormat))),
        total_records=draw(st.integers(min_value=0, max_value=100000)),
        exported_records=draw(st.integers(min_value=0, max_value=100000)),
        file_path=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        file_size=draw(st.one_of(st.none(), st.integers(min_value=0, max_value=10**9))),
        error=draw(st.one_of(st.none(), st.text(max_size=100))),
        created_at=draw(_naive_datetime()),
        completed_at=draw(st.one_of(st.none(), _naive_datetime())),
        metadata=draw(st.fixed_dictionaries({}, optional={
            "source": st.text(min_size=1, max_size=20),
        })),
    )


@st.composite
def coco_annotation_models(draw):
    """Generate valid COCOAnnotation Pydantic model instances."""
    return COCOAnnotation(
        id=draw(st.integers(min_value=1, max_value=100000)),
        image_id=draw(st.integers(min_value=1, max_value=100000)),
        category_id=draw(st.integers(min_value=1, max_value=100)),
        bbox=draw(st.one_of(
            st.none(),
            st.lists(
                st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
                min_size=4, max_size=4,
            ),
        )),
        area=draw(st.one_of(
            st.none(),
            st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
        )),
        iscrowd=draw(st.sampled_from([0, 1])),
    )


# =============================================================================
# Property 4: Serialization Round-Trip Tests
# =============================================================================

@given(task=task_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_task_serialization_round_trip(task: Task):
    """
    Task model survives JSON round-trip.

    **Validates: Requirements 2.1**
    """
    json_str = task.model_dump_json()
    restored = Task.model_validate_json(json_str)
    assert restored == task


@given(annotation=annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_serialization_round_trip(annotation: Annotation):
    """
    Annotation model survives JSON round-trip via to_dict / from_dict.

    **Validates: Requirements 2.1**
    """
    as_dict = annotation.to_dict()
    json_str = json.dumps(as_dict)
    restored_dict = json.loads(json_str)
    restored = Annotation.from_dict(restored_dict)

    assert str(restored.id) == str(annotation.id)
    assert str(restored.task_id) == str(annotation.task_id)
    assert restored.annotator_id == annotation.annotator_id
    assert restored.annotation_data == annotation.annotation_data
    assert restored.confidence == annotation.confidence
    assert restored.time_spent == annotation.time_spent


@given(annotation=annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_annotation_pydantic_round_trip(annotation: Annotation):
    """
    Annotation model survives Pydantic JSON round-trip.

    **Validates: Requirements 2.1**
    """
    json_str = annotation.model_dump_json()
    restored = Annotation.model_validate_json(json_str)
    assert restored == annotation


@given(doc=document_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_document_serialization_round_trip(doc: Document):
    """
    Document model survives JSON round-trip via to_dict / from_dict.

    **Validates: Requirements 2.1**
    """
    as_dict = doc.to_dict()
    json_str = json.dumps(as_dict)
    restored_dict = json.loads(json_str)
    restored = Document.from_dict(restored_dict)

    assert str(restored.id) == str(doc.id)
    assert restored.source_type == doc.source_type
    assert restored.source_config == doc.source_config
    assert restored.content == doc.content
    assert restored.metadata == doc.metadata


@given(doc=document_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_document_pydantic_round_trip(doc: Document):
    """
    Document model survives Pydantic JSON round-trip.

    **Validates: Requirements 2.1**
    """
    json_str = doc.model_dump_json()
    restored = Document.model_validate_json(json_str)
    assert restored == doc


@given(req=export_request_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_export_request_round_trip(req: ExportRequest):
    """
    ExportRequest model survives Pydantic JSON round-trip.

    **Validates: Requirements 2.1**
    """
    json_str = req.model_dump_json()
    restored = ExportRequest.model_validate_json(json_str)
    assert restored == req


@given(result=export_result_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_export_result_round_trip(result: ExportResult):
    """
    ExportResult model survives Pydantic JSON round-trip.

    **Validates: Requirements 2.1**
    """
    json_str = result.model_dump_json()
    restored = ExportResult.model_validate_json(json_str)
    assert restored == result


@given(coco=coco_annotation_models())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_coco_annotation_round_trip(coco: COCOAnnotation):
    """
    COCOAnnotation model survives Pydantic JSON round-trip.

    **Validates: Requirements 2.1**
    """
    json_str = coco.model_dump_json()
    restored = COCOAnnotation.model_validate_json(json_str)
    assert restored == coco


@given(data=json_serializable_data())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_generic_json_round_trip(data):
    """
    Arbitrary JSON-serializable data survives json.dumps / json.loads round-trip.

    **Validates: Requirements 2.1**
    """
    serialized = json.dumps(data)
    deserialized = json.loads(serialized)
    assert deserialized == data
