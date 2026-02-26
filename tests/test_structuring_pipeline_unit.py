"""
Unit tests for src/services/structuring_pipeline.py.

Tests status transitions, file-type routing, and pipeline orchestration
using mocks for DB, extractors, and AI modules.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

from src.models.structuring import JobStatus, FileType as StructuringFileType
from src.services.structuring_pipeline import (
    is_valid_transition,
    _update_job_status,
    _fail_job,
    _TABULAR_TYPES,
    _TEXT_TYPES,
    _PPT_TYPES,
    _MEDIA_TYPES,
    _VALID_TRANSITIONS,
)


# ---------------------------------------------------------------------------
# is_valid_transition
# ---------------------------------------------------------------------------

class TestIsValidTransition:
    """Tests for the status transition validator."""

    def test_valid_forward_transitions(self):
        for src, dst in _VALID_TRANSITIONS.items():
            assert is_valid_transition(src, dst) is True

    def test_any_state_can_transition_to_failed(self):
        for status in JobStatus:
            assert is_valid_transition(status.value, JobStatus.FAILED.value) is True

    def test_invalid_backward_transition(self):
        assert is_valid_transition(
            JobStatus.INFERRING.value, JobStatus.EXTRACTING.value,
        ) is False

    def test_skip_transition_is_invalid(self):
        assert is_valid_transition(
            JobStatus.PENDING.value, JobStatus.INFERRING.value,
        ) is False

    def test_completed_cannot_go_forward(self):
        assert is_valid_transition(
            JobStatus.COMPLETED.value, JobStatus.PENDING.value,
        ) is False


# ---------------------------------------------------------------------------
# _update_job_status / _fail_job
# ---------------------------------------------------------------------------

class TestUpdateJobStatus:
    """Tests for status update helpers."""

    def _make_job(self, status: str = JobStatus.PENDING.value) -> MagicMock:
        job = MagicMock()
        job.status = status
        job.error_message = None
        return job

    def test_valid_transition_updates_status(self):
        session = MagicMock()
        job = self._make_job(JobStatus.PENDING.value)
        _update_job_status(session, job, JobStatus.EXTRACTING.value)
        assert job.status == JobStatus.EXTRACTING.value
        session.flush.assert_called_once()

    def test_invalid_transition_raises(self):
        session = MagicMock()
        job = self._make_job(JobStatus.PENDING.value)
        with pytest.raises(ValueError, match="Invalid status transition"):
            _update_job_status(session, job, JobStatus.COMPLETED.value)

    def test_fail_job_sets_error(self):
        session = MagicMock()
        job = self._make_job(JobStatus.EXTRACTING.value)
        _fail_job(session, job, "something broke")
        assert job.status == JobStatus.FAILED.value
        assert job.error_message == "something broke"
        session.flush.assert_called_once()


# ---------------------------------------------------------------------------
# File-type routing constants
# ---------------------------------------------------------------------------

class TestFileTypeRouting:
    """Verify file-type routing sets match the design spec."""

    def test_tabular_types(self):
        assert _TABULAR_TYPES == {"csv", "excel"}

    def test_text_types(self):
        assert _TEXT_TYPES == {"pdf", "docx", "txt", "html"}

    def test_ppt_types(self):
        assert _PPT_TYPES == {"ppt"}

    def test_media_types(self):
        assert _MEDIA_TYPES == {"video", "audio"}

    def test_no_overlap(self):
        all_sets = [_TABULAR_TYPES, _TEXT_TYPES, _PPT_TYPES, _MEDIA_TYPES]
        for i, a in enumerate(all_sets):
            for b in all_sets[i + 1:]:
                assert a & b == set()

    def test_all_structuring_file_types_covered(self):
        all_types = {ft.value for ft in StructuringFileType}
        covered = _TABULAR_TYPES | _TEXT_TYPES | _PPT_TYPES | _MEDIA_TYPES
        assert all_types == covered


# ---------------------------------------------------------------------------
# _extract_content routing
# ---------------------------------------------------------------------------

class TestExtractContent:
    """Tests for the content extraction step."""

    def _make_job(self, file_type: str, file_path: str = "/tmp/test.csv"):
        job = MagicMock()
        job.file_type = file_type
        job.file_path = file_path
        job.status = JobStatus.PENDING.value
        job.raw_content = None
        return job

    @patch("src.services.structuring_pipeline._update_job_status")
    @patch("src.services.structuring_pipeline.TabularParser", create=True)
    def test_csv_routes_to_tabular_parser(self, mock_parser_cls, mock_update):
        from src.services.structuring_pipeline import _extract_content
        from src.extractors.tabular import TabularData

        mock_parser = MagicMock()
        tabular = TabularData(
            headers=["a", "b"], rows=[{"a": 1, "b": 2}],
            row_count=1, file_type="csv",
        )
        mock_parser.parse.return_value = tabular

        # Patch the import inside _extract_content
        with patch("src.extractors.tabular.TabularParser", return_value=mock_parser):
            session = MagicMock()
            job = self._make_job("csv")
            result = _extract_content(session, job)

        assert result.headers == ["a", "b"]
        assert result.row_count == 1

    @patch("src.services.structuring_pipeline._update_job_status")
    @patch("src.extractors.ppt.PPTExtractor.extract", return_value="Slide 1 text\n\nSlide 2 text")
    def test_ppt_routes_to_ppt_extractor(self, mock_extract, mock_update):
        from src.services.structuring_pipeline import _extract_content

        session = MagicMock()
        job = self._make_job("ppt", "/tmp/test.pptx")
        result = _extract_content(session, job)

        assert result == "Slide 1 text\n\nSlide 2 text"
        assert job.raw_content == "Slide 1 text\n\nSlide 2 text"
        mock_extract.assert_called_once_with("/tmp/test.pptx")

    @patch("src.services.structuring_pipeline._update_job_status")
    @patch("src.extractors.ppt.PPTExtractor.extract", return_value="  ")
    def test_ppt_empty_content_raises(self, mock_extract, mock_update):
        from src.services.structuring_pipeline import _extract_content

        session = MagicMock()
        job = self._make_job("ppt", "/tmp/empty.pptx")
        with pytest.raises(RuntimeError, match="PPT extraction returned empty content"):
            _extract_content(session, job)

    @patch("src.services.structuring_pipeline._update_job_status")
    @patch("src.services.structuring_pipeline.asyncio")
    def test_video_routes_to_media_transcriber(self, mock_asyncio, mock_update):
        from src.services.structuring_pipeline import _extract_content

        mock_asyncio.run.return_value = "transcribed video text"
        session = MagicMock()
        job = self._make_job("video", "/tmp/test.mp4")
        result = _extract_content(session, job)

        assert result == "transcribed video text"
        assert job.raw_content == "transcribed video text"
        mock_asyncio.run.assert_called_once()

    @patch("src.services.structuring_pipeline._update_job_status")
    @patch("src.services.structuring_pipeline.asyncio")
    def test_audio_routes_to_media_transcriber(self, mock_asyncio, mock_update):
        from src.services.structuring_pipeline import _extract_content

        mock_asyncio.run.return_value = "transcribed audio text"
        session = MagicMock()
        job = self._make_job("audio", "/tmp/test.mp3")
        result = _extract_content(session, job)

        assert result == "transcribed audio text"
        assert job.raw_content == "transcribed audio text"
        mock_asyncio.run.assert_called_once()

    @patch("src.services.structuring_pipeline._update_job_status")
    @patch("src.services.structuring_pipeline.asyncio")
    def test_media_empty_transcription_raises(self, mock_asyncio, mock_update):
        from src.services.structuring_pipeline import _extract_content

        mock_asyncio.run.return_value = "  "
        session = MagicMock()
        job = self._make_job("video", "/tmp/test.mp4")
        with pytest.raises(RuntimeError, match="Media transcription returned empty"):
            _extract_content(session, job)

    @patch("src.services.structuring_pipeline._update_job_status")
    def test_unsupported_type_raises(self, mock_update):
        from src.services.structuring_pipeline import _extract_content

        session = MagicMock()
        job = self._make_job("unknown_format")
        with pytest.raises(ValueError, match="Unsupported file type"):
            _extract_content(session, job)


# ---------------------------------------------------------------------------
# _store_records
# ---------------------------------------------------------------------------

class TestStoreRecords:
    """Tests for the record storage step."""

    def test_stores_records_and_updates_count(self):
        from src.services.structuring_pipeline import _store_records

        session = MagicMock()
        job = MagicMock()
        job.id = uuid4()
        job.record_count = 0

        records = [
            {"fields": {"name": "Alice"}, "confidence": 0.9, "source_span": "line 1"},
            {"fields": {"name": "Bob"}, "confidence": 0.8, "source_span": None},
        ]

        count = _store_records(session, job, records)
        assert count == 2
        assert job.record_count == 2
        assert session.add.call_count == 2

    def test_empty_records(self):
        from src.services.structuring_pipeline import _store_records

        session = MagicMock()
        job = MagicMock()
        job.id = uuid4()

        count = _store_records(session, job, [])
        assert count == 0
        assert job.record_count == 0
