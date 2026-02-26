"""Unit tests for src/api/semantic.py endpoints."""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.semantic import (
    SemJobCreateResponse,
    SemJobListItem,
    SemJobListResponse,
    SemJobStatusResponse,
    SemRecordItem,
    SemRecordListResponse,
    _get_file_type,
    _get_sem_job_or_404,
)
from src.models.structuring import ProcessingType


# ---------------------------------------------------------------------------
# _get_file_type tests
# ---------------------------------------------------------------------------


class TestGetFileType:
    """Tests for the semantic _get_file_type helper."""

    @pytest.mark.parametrize(
        "filename, expected_type",
        [
            ("doc.pdf", "pdf"),
            ("data.csv", "csv"),
            ("slides.pptx", "ppt"),
            ("video.mp4", "video"),
            ("audio.mp3", "audio"),
            ("notes.txt", "txt"),
        ],
    )
    def test_supported_extensions(self, filename, expected_type):
        assert _get_file_type(filename) == expected_type

    def test_unsupported_extension_raises(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _get_file_type("archive.zip")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# _get_sem_job_or_404 tests
# ---------------------------------------------------------------------------


class TestGetSemJobOr404:
    """Tests for the _get_sem_job_or_404 helper."""

    def test_invalid_uuid_raises_400(self):
        from fastapi import HTTPException

        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            _get_sem_job_or_404("not-a-uuid", db, "tenant1")
        assert exc_info.value.status_code == 400

    def test_missing_job_raises_404(self):
        from fastapi import HTTPException

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            _get_sem_job_or_404(str(uuid4()), db, "tenant1")
        assert exc_info.value.status_code == 404

    def test_found_job_returned(self):
        job = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = job
        result = _get_sem_job_or_404(str(uuid4()), db, "tenant1")
        assert result is job


# ---------------------------------------------------------------------------
# Response model construction tests
# ---------------------------------------------------------------------------


class TestResponseModels:
    """Verify Pydantic response models can be constructed."""

    def test_sem_job_create_response(self):
        resp = SemJobCreateResponse(
            job_id=str(uuid4()),
            status="pending",
            file_name="test.pdf",
            file_type="pdf",
            created_at=datetime.now(timezone.utc),
            message="Semantic job created",
        )
        assert resp.status == "pending"
        assert resp.message == "Semantic job created"

    def test_sem_job_status_response(self):
        resp = SemJobStatusResponse(
            job_id=str(uuid4()),
            status="completed",
            file_name="test.pdf",
            file_type="pdf",
            record_count=15,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert resp.record_count == 15

    def test_sem_job_status_response_optional_fields(self):
        resp = SemJobStatusResponse(
            job_id=str(uuid4()),
            status="pending",
            file_name="test.pdf",
            file_type="pdf",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert resp.record_count == 0
        assert resp.error_message is None

    def test_sem_job_list_response(self):
        item = SemJobListItem(
            job_id=str(uuid4()),
            status="completed",
            file_name="test.pdf",
            file_type="pdf",
            created_at=datetime.now(timezone.utc),
        )
        resp = SemJobListResponse(items=[item], total=1)
        assert resp.total == 1
        assert len(resp.items) == 1

    def test_sem_record_list_response(self):
        item = SemRecordItem(
            id=str(uuid4()),
            record_type="entity",
            content={"name": "Alice", "type": "person", "properties": {}},
            confidence=0.95,
            created_at=datetime.now(timezone.utc),
        )
        resp = SemRecordListResponse(items=[item], total=1, page=1, size=20)
        assert resp.total == 1
        assert resp.items[0].record_type == "entity"

    def test_sem_record_item_all_types(self):
        """Verify record items for entity, relationship, and summary types."""
        entity = SemRecordItem(
            id=str(uuid4()),
            record_type="entity",
            content={"name": "Acme", "type": "organization", "properties": {}},
            confidence=0.9,
            created_at=datetime.now(timezone.utc),
        )
        relationship = SemRecordItem(
            id=str(uuid4()),
            record_type="relationship",
            content={"source": "Alice", "target": "Acme", "relation": "works_at"},
            confidence=0.85,
            created_at=datetime.now(timezone.utc),
        )
        summary = SemRecordItem(
            id=str(uuid4()),
            record_type="summary",
            content={"text": "Document about Alice working at Acme."},
            confidence=0.92,
            created_at=datetime.now(timezone.utc),
        )
        assert entity.record_type == "entity"
        assert relationship.record_type == "relationship"
        assert summary.record_type == "summary"


# ---------------------------------------------------------------------------
# Processing type validation
# ---------------------------------------------------------------------------


class TestProcessingType:
    """Verify semantic uses correct processing type."""

    def test_semantic_processing_type_value(self):
        assert ProcessingType.SEMANTIC.value == "semantic"
