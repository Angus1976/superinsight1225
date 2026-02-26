"""Unit tests for src/api/vectorization.py endpoints."""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.vectorization import (
    VecJobCreateResponse,
    VecJobListItem,
    VecJobListResponse,
    VecJobStatusResponse,
    VecRecordItem,
    VecRecordListResponse,
    _get_file_type,
    _get_vec_job_or_404,
)
from src.models.structuring import ProcessingType


# ---------------------------------------------------------------------------
# _get_file_type tests
# ---------------------------------------------------------------------------


class TestGetFileType:
    """Tests for the vectorization _get_file_type helper."""

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
# _get_vec_job_or_404 tests
# ---------------------------------------------------------------------------


class TestGetVecJobOr404:
    """Tests for the _get_vec_job_or_404 helper."""

    def test_invalid_uuid_raises_400(self):
        from fastapi import HTTPException

        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            _get_vec_job_or_404("not-a-uuid", db, "tenant1")
        assert exc_info.value.status_code == 400

    def test_missing_job_raises_404(self):
        from fastapi import HTTPException

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            _get_vec_job_or_404(str(uuid4()), db, "tenant1")
        assert exc_info.value.status_code == 404

    def test_found_job_returned(self):
        job = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = job
        result = _get_vec_job_or_404(str(uuid4()), db, "tenant1")
        assert result is job


# ---------------------------------------------------------------------------
# Response model construction tests
# ---------------------------------------------------------------------------


class TestResponseModels:
    """Verify Pydantic response models can be constructed."""

    def test_vec_job_create_response(self):
        resp = VecJobCreateResponse(
            job_id=str(uuid4()),
            status="pending",
            file_name="test.pdf",
            file_type="pdf",
            created_at=datetime.now(timezone.utc),
            message="Vectorization job created",
        )
        assert resp.status == "pending"
        assert resp.message == "Vectorization job created"

    def test_vec_job_status_response(self):
        resp = VecJobStatusResponse(
            job_id=str(uuid4()),
            status="completed",
            file_name="test.pdf",
            file_type="pdf",
            chunk_count=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert resp.chunk_count == 10

    def test_vec_job_status_response_optional_fields(self):
        resp = VecJobStatusResponse(
            job_id=str(uuid4()),
            status="pending",
            file_name="test.pdf",
            file_type="pdf",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert resp.chunk_count is None
        assert resp.error_message is None

    def test_vec_job_list_response(self):
        item = VecJobListItem(
            job_id=str(uuid4()),
            status="completed",
            file_name="test.pdf",
            file_type="pdf",
            chunk_count=5,
            created_at=datetime.now(timezone.utc),
        )
        resp = VecJobListResponse(items=[item], total=1)
        assert resp.total == 1
        assert len(resp.items) == 1

    def test_vec_record_list_response(self):
        item = VecRecordItem(
            id=str(uuid4()),
            chunk_index=0,
            chunk_text="Hello world",
            metadata={"chunk_size": 512},
            created_at=datetime.now(timezone.utc),
        )
        resp = VecRecordListResponse(items=[item], total=1, page=1, size=20)
        assert resp.total == 1
        assert resp.items[0].chunk_text == "Hello world"

    def test_vec_record_item_optional_metadata(self):
        item = VecRecordItem(
            id=str(uuid4()),
            chunk_index=0,
            chunk_text="Some text",
            created_at=datetime.now(timezone.utc),
        )
        assert item.metadata is None


# ---------------------------------------------------------------------------
# Processing type validation
# ---------------------------------------------------------------------------


class TestProcessingType:
    """Verify vectorization uses correct processing type."""

    def test_vectorization_processing_type_value(self):
        assert ProcessingType.VECTORIZATION.value == "vectorization"
