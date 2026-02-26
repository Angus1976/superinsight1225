"""
Unit tests for run_semantic_pipeline() in
src/services/semantic_pipeline.py.

Tests the full pipeline orchestration (extract → LLM entities →
LLM relationships → LLM summary → store) using mocks for DB and LLM.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.models.structuring import JobStatus, FileType as StructuringFileType
from src.services.semantic_pipeline import (
    run_semantic_pipeline,
    _call_llm,
    _parse_json,
    _extract_entities,
    _extract_relationships,
    _generate_summary,
    _store_semantic_records,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    file_type: str = StructuringFileType.TXT.value,
    status: str = JobStatus.PENDING.value,
    file_path: str = "/tmp/test.txt",
    tenant_id: str = "tenant-1",
) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.file_type = file_type
    job.file_path = file_path
    job.status = status
    job.tenant_id = tenant_id
    job.file_name = "test.txt"
    job.raw_content = None
    job.error_message = None
    return job


# ---------------------------------------------------------------------------
# _parse_json
# ---------------------------------------------------------------------------


class TestParseJson:
    """Tests for JSON parsing with markdown fence stripping."""

    def test_plain_json_array(self):
        result = _parse_json('[{"name": "Alice"}]')
        assert result == [{"name": "Alice"}]

    def test_plain_json_object(self):
        result = _parse_json('{"text": "summary"}')
        assert result == {"text": "summary"}

    def test_strips_markdown_fences(self):
        raw = '```json\n[{"name": "Bob"}]\n```'
        result = _parse_json(raw)
        assert result == [{"name": "Bob"}]

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("not json at all")


# ---------------------------------------------------------------------------
# _extract_entities
# ---------------------------------------------------------------------------


class TestExtractEntities:
    """Tests for LLM entity extraction."""

    @patch("src.services.semantic_pipeline._call_llm")
    def test_returns_entity_list(self, mock_llm):
        entities = [
            {"name": "Alice", "type": "person", "properties": {}, "confidence": 0.9},
        ]
        mock_llm.return_value = json.dumps(entities)

        result = _extract_entities("some text", "t1")

        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    @patch("src.services.semantic_pipeline._call_llm")
    def test_non_array_raises(self, mock_llm):
        mock_llm.return_value = '{"name": "Alice"}'

        with pytest.raises(ValueError, match="not a JSON array"):
            _extract_entities("some text", "t1")


# ---------------------------------------------------------------------------
# _extract_relationships
# ---------------------------------------------------------------------------


class TestExtractRelationships:
    """Tests for LLM relationship extraction."""

    @patch("src.services.semantic_pipeline._call_llm")
    def test_returns_relationship_list(self, mock_llm):
        rels = [
            {"source": "Alice", "target": "Bob", "relation": "knows", "confidence": 0.8},
        ]
        mock_llm.return_value = json.dumps(rels)

        result = _extract_relationships("some text", "t1")

        assert len(result) == 1
        assert result[0]["relation"] == "knows"

    @patch("src.services.semantic_pipeline._call_llm")
    def test_non_array_raises(self, mock_llm):
        mock_llm.return_value = '"just a string"'

        with pytest.raises(ValueError, match="not a JSON array"):
            _extract_relationships("some text", "t1")


# ---------------------------------------------------------------------------
# _generate_summary
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    """Tests for LLM summary generation."""

    @patch("src.services.semantic_pipeline._call_llm")
    def test_returns_summary_dict(self, mock_llm):
        summary = {"text": "A concise summary.", "confidence": 0.95}
        mock_llm.return_value = json.dumps(summary)

        result = _generate_summary("some text", "t1")

        assert result["text"] == "A concise summary."

    @patch("src.services.semantic_pipeline._call_llm")
    def test_non_object_raises(self, mock_llm):
        mock_llm.return_value = '["not", "an", "object"]'

        with pytest.raises(ValueError, match="not a JSON object"):
            _generate_summary("some text", "t1")


# ---------------------------------------------------------------------------
# _store_semantic_records
# ---------------------------------------------------------------------------


class TestStoreSemanticRecords:
    """Tests for batch writing semantic records."""

    def test_stores_all_record_types(self):
        session = MagicMock()
        job = _make_job()
        entities = [
            {"name": "Alice", "type": "person", "properties": {}, "confidence": 0.9},
            {"name": "Acme", "type": "organization", "properties": {}, "confidence": 0.85},
        ]
        relationships = [
            {"source": "Alice", "target": "Acme", "relation": "works_at", "confidence": 0.8},
        ]
        summary = {"text": "Alice works at Acme.", "confidence": 0.95}

        count = _store_semantic_records(session, job, entities, relationships, summary)

        # 2 entities + 1 relationship + 1 summary = 4
        assert count == 4
        assert session.add.call_count == 4
        session.flush.assert_called_once()

    def test_empty_entities_and_relationships(self):
        session = MagicMock()
        job = _make_job()
        summary = {"text": "Nothing found.", "confidence": 0.5}

        count = _store_semantic_records(session, job, [], [], summary)

        # Only the summary record
        assert count == 1
        assert session.add.call_count == 1

    def test_missing_confidence_defaults_to_zero(self):
        session = MagicMock()
        job = _make_job()
        entities = [{"name": "X", "type": "thing"}]  # no confidence key
        summary = {"text": "Summary"}  # no confidence key

        count = _store_semantic_records(session, job, entities, [], summary)

        assert count == 2
        # Verify the SemanticRecord objects were created with default confidence
        calls = session.add.call_args_list
        entity_record = calls[0][0][0]
        assert entity_record.confidence == 0.0


# ---------------------------------------------------------------------------
# run_semantic_pipeline (integration-level with mocks)
# ---------------------------------------------------------------------------


class TestRunSemanticPipeline:
    """Tests for the main pipeline orchestration."""

    @patch("src.services.semantic_pipeline._mark_job_failed")
    @patch("src.services.semantic_pipeline.db_manager")
    def test_job_not_found_returns_failed(self, mock_db, mock_mark_failed):
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        result = run_semantic_pipeline("nonexistent-id")

        assert result["status"] == JobStatus.FAILED.value
        assert "error" in result

    @patch("src.services.semantic_pipeline._mark_job_failed")
    @patch("src.services.semantic_pipeline.db_manager")
    def test_non_pending_job_returns_failed(self, mock_db, mock_mark_failed):
        job = _make_job(status=JobStatus.COMPLETED.value)
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = job

        result = run_semantic_pipeline(str(job.id))

        assert result["status"] == JobStatus.FAILED.value

    @patch("src.services.semantic_pipeline._store_semantic_records")
    @patch("src.services.semantic_pipeline._generate_summary")
    @patch("src.services.semantic_pipeline._extract_relationships")
    @patch("src.services.semantic_pipeline._extract_entities")
    @patch("src.services.vectorization_pipeline._extract_text")
    @patch("src.services.semantic_pipeline.db_manager")
    def test_successful_pipeline(
        self, mock_db, mock_extract, mock_entities,
        mock_rels, mock_summary, mock_store,
    ):
        job = _make_job()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = job

        mock_extract.return_value = "Some extracted text"
        mock_entities.return_value = [{"name": "A", "type": "person", "properties": {}, "confidence": 0.9}]
        mock_rels.return_value = [{"source": "A", "target": "B", "relation": "knows", "confidence": 0.8}]
        mock_summary.return_value = {"text": "Summary", "confidence": 0.95}
        mock_store.return_value = 3

        result = run_semantic_pipeline(str(job.id))

        assert result["status"] == JobStatus.COMPLETED.value
        assert result["record_count"] == 3
        mock_extract.assert_called_once_with(job)
        mock_entities.assert_called_once_with("Some extracted text", job.tenant_id)
        mock_rels.assert_called_once_with("Some extracted text", job.tenant_id)
        mock_summary.assert_called_once_with("Some extracted text", job.tenant_id)
        mock_store.assert_called_once()

    @patch("src.services.semantic_pipeline._mark_job_failed")
    @patch("src.services.vectorization_pipeline._extract_text")
    @patch("src.services.semantic_pipeline.db_manager")
    def test_extraction_error_marks_failed(
        self, mock_db, mock_extract, mock_mark_failed,
    ):
        job = _make_job()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = job

        mock_extract.side_effect = RuntimeError("extraction boom")

        result = run_semantic_pipeline(str(job.id))

        assert result["status"] == JobStatus.FAILED.value
        assert "extraction boom" in result["error"]
        mock_mark_failed.assert_called_once()

    @patch("src.services.semantic_pipeline._mark_job_failed")
    @patch("src.services.semantic_pipeline._extract_entities")
    @patch("src.services.vectorization_pipeline._extract_text")
    @patch("src.services.semantic_pipeline.db_manager")
    def test_llm_error_marks_failed(
        self, mock_db, mock_extract, mock_entities, mock_mark_failed,
    ):
        job = _make_job()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = job

        mock_extract.return_value = "Some text"
        mock_entities.side_effect = ValueError("LLM returned garbage")

        result = run_semantic_pipeline(str(job.id))

        assert result["status"] == JobStatus.FAILED.value
        assert "LLM returned garbage" in result["error"]
        mock_mark_failed.assert_called_once()
