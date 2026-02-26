"""Unit tests for src/api/structuring.py endpoints."""

import os
import sys
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.structuring import (
    SUPPORTED_EXTENSIONS,
    _EXTENSION_MAP,
    _get_file_type,
    _get_job_or_404,
)
from src.models.structuring import FileType, JobStatus


# ---------------------------------------------------------------------------
# _get_file_type tests
# ---------------------------------------------------------------------------


class TestGetFileType:
    """Tests for the _get_file_type helper."""

    @pytest.mark.parametrize(
        "filename, expected",
        [
            ("data.pdf", FileType.PDF.value),
            ("data.csv", FileType.CSV.value),
            ("data.xlsx", FileType.EXCEL.value),
            ("data.xls", FileType.EXCEL.value),
            ("data.docx", FileType.DOCX.value),
            ("data.html", FileType.HTML.value),
            ("data.htm", FileType.HTML.value),
            ("data.txt", FileType.TXT.value),
            ("UPPER.PDF", FileType.PDF.value),
        ],
    )
    def test_supported_extensions(self, filename, expected):
        assert _get_file_type(filename) == expected

    def test_unsupported_extension_raises(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _get_file_type("data.zip")
        assert exc_info.value.status_code == 400
        assert "Unsupported" in exc_info.value.detail


# ---------------------------------------------------------------------------
# _get_job_or_404 tests
# ---------------------------------------------------------------------------


class TestGetJobOr404:
    """Tests for the _get_job_or_404 helper."""

    def test_invalid_uuid_raises_400(self):
        from fastapi import HTTPException

        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            _get_job_or_404("not-a-uuid", db, "tenant1")
        assert exc_info.value.status_code == 400

    def test_missing_job_raises_404(self):
        from fastapi import HTTPException

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            _get_job_or_404(str(uuid4()), db, "tenant1")
        assert exc_info.value.status_code == 404

    def test_found_job_returned(self):
        job = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = job
        result = _get_job_or_404(str(uuid4()), db, "tenant1")
        assert result is job


# ---------------------------------------------------------------------------
# Extension map completeness
# ---------------------------------------------------------------------------


class TestExtensionMap:
    """Verify extension map covers all FileType enum values."""

    def test_all_file_types_mapped(self):
        mapped_types = set(_EXTENSION_MAP.values())
        for ft in FileType:
            assert ft.value in mapped_types, f"FileType.{ft.name} not in extension map"

    def test_supported_extensions_non_empty(self):
        assert len(SUPPORTED_EXTENSIONS) >= 7  # pdf, csv, xlsx, xls, docx, html, htm, txt


# ---------------------------------------------------------------------------
# Response model construction smoke tests
# ---------------------------------------------------------------------------


class TestResponseModels:
    """Verify Pydantic response models can be constructed."""

    def test_job_create_response(self):
        from src.api.structuring import JobCreateResponse

        resp = JobCreateResponse(
            job_id=str(uuid4()),
            status="pending",
            file_name="test.csv",
            file_type="csv",
            created_at=datetime.now(timezone.utc),
            message="ok",
        )
        assert resp.status == "pending"

    def test_job_status_response(self):
        from src.api.structuring import JobStatusResponse

        resp = JobStatusResponse(
            job_id=str(uuid4()),
            status="completed",
            file_name="test.pdf",
            file_type="pdf",
            record_count=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert resp.record_count == 10

    def test_record_list_response(self):
        from src.api.structuring import RecordItem, RecordListResponse

        item = RecordItem(
            id=str(uuid4()),
            fields={"name": "Alice"},
            confidence=0.95,
            created_at=datetime.now(timezone.utc),
        )
        resp = RecordListResponse(items=[item], total=1, page=1, size=20)
        assert resp.total == 1

    def test_schema_confirm_request_validation(self):
        from src.api.structuring import SchemaConfirmRequest

        req = SchemaConfirmRequest(confirmed_schema={"fields": []})
        assert req.confirmed_schema == {"fields": []}
