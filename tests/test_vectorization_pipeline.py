"""
Unit tests for run_vectorization_pipeline() in
src/services/vectorization_pipeline.py.

Tests the full pipeline orchestration (extract → chunk → embed → store)
using mocks for DB, extractors, and LLM switcher.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

from src.models.structuring import JobStatus, FileType as StructuringFileType
from src.services.vectorization_pipeline import (
    run_vectorization_pipeline,
    _extract_text,
    _embed_chunks,
    _store_vector_records,
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
    job.chunk_count = None
    job.error_message = None
    return job


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------


class TestExtractText:
    """Tests for _extract_text routing to correct extractors."""

    @patch("src.extractors.file.FileExtractor")
    @patch("src.extractors.base.FileConfig")
    def test_txt_routes_to_file_extractor(self, mock_config_cls, mock_ext_cls):
        job = _make_job(file_type=StructuringFileType.TXT.value)
        mock_doc = MagicMock()
        mock_doc.content = "Hello world"
        mock_result = MagicMock(success=True, documents=[mock_doc])
        mock_ext_cls.return_value.extract_data.return_value = mock_result

        text = _extract_text(job)

        assert text == "Hello world"
        mock_ext_cls.return_value.extract_data.assert_called_once()

    @patch("src.extractors.file.FileExtractor")
    @patch("src.extractors.base.FileConfig")
    def test_text_extraction_failure_raises(self, mock_config_cls, mock_ext_cls):
        job = _make_job(file_type=StructuringFileType.PDF.value)
        mock_ext_cls.return_value.extract_data.return_value = MagicMock(
            success=False, documents=[], error="parse error",
        )

        with pytest.raises(RuntimeError, match="File extraction failed"):
            _extract_text(job)

    @patch("src.extractors.tabular.TabularParser.parse")
    def test_csv_routes_to_tabular_parser(self, mock_parse):
        job = _make_job(file_type=StructuringFileType.CSV.value)
        mock_parse.return_value = MagicMock(rows=[["a", "b"], ["c", "d"]])

        text = _extract_text(job)

        assert "a" in text
        mock_parse.assert_called_once()

    @patch("src.extractors.ppt.PPTExtractor.extract")
    def test_ppt_routes_to_ppt_extractor(self, mock_extract):
        job = _make_job(file_type=StructuringFileType.PPT.value)
        mock_extract.return_value = "Slide 1 content"

        text = _extract_text(job)

        assert text == "Slide 1 content"

    @patch("src.extractors.ppt.PPTExtractor.extract")
    def test_ppt_empty_raises(self, mock_extract):
        job = _make_job(file_type=StructuringFileType.PPT.value)
        mock_extract.return_value = "   "

        with pytest.raises(RuntimeError, match="PPT extraction returned empty"):
            _extract_text(job)

    @patch("asyncio.run")
    @patch("src.extractors.media.MediaTranscriber.transcribe")
    def test_video_routes_to_media_transcriber(self, mock_transcribe, mock_asyncio):
        job = _make_job(file_type=StructuringFileType.VIDEO.value)
        mock_asyncio.return_value = "Transcribed text"

        text = _extract_text(job)

        assert text == "Transcribed text"

    def test_unsupported_type_raises(self):
        job = _make_job(file_type="unknown")

        with pytest.raises(ValueError, match="Unsupported file type"):
            _extract_text(job)


# ---------------------------------------------------------------------------
# _embed_chunks
# ---------------------------------------------------------------------------


class TestEmbedChunks:
    """Tests for _embed_chunks calling LLMSwitcher.embed()."""

    @patch("src.ai.llm_switcher.get_llm_switcher")
    def test_embeds_each_chunk(self, mock_get_switcher):
        mock_switcher = MagicMock()
        mock_get_switcher.return_value = mock_switcher

        fake_embedding = [0.1] * 1536
        fake_response = MagicMock(embedding=fake_embedding)

        # _embed_chunks calls asyncio.run(switcher.embed(chunk)) for each chunk.
        # Since get_llm_switcher is imported inside the function, we patch at source.
        # We also need to patch asyncio.run to just call the coroutine result.
        with patch("asyncio.run", return_value=fake_response) as mock_arun:
            chunks = ["chunk 1", "chunk 2", "chunk 3"]
            result = _embed_chunks(chunks, tenant_id="t1")

        assert len(result) == 3
        assert all(len(e) == 1536 for e in result)
        assert mock_arun.call_count == 3

    @patch("src.ai.llm_switcher.get_llm_switcher")
    def test_empty_chunks_returns_empty(self, mock_get_switcher):
        result = _embed_chunks([], tenant_id="t1")

        assert result == []


# ---------------------------------------------------------------------------
# _store_vector_records
# ---------------------------------------------------------------------------


class TestStoreVectorRecords:
    """Tests for _store_vector_records batch writing."""

    def test_stores_records_and_updates_count(self):
        session = MagicMock()
        job = _make_job()
        chunks = ["chunk A", "chunk B"]
        embeddings = [[0.1] * 1536, [0.2] * 1536]

        count = _store_vector_records(session, job, chunks, embeddings)

        assert count == 2
        assert job.chunk_count == 2
        assert session.add.call_count == 2
        session.flush.assert_called_once()

    def test_empty_chunks_stores_nothing(self):
        session = MagicMock()
        job = _make_job()

        count = _store_vector_records(session, job, [], [])

        assert count == 0
        assert job.chunk_count == 0
        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# run_vectorization_pipeline (integration-level with mocks)
# ---------------------------------------------------------------------------


class TestRunVectorizationPipeline:
    """Tests for the main pipeline orchestration."""

    @patch("src.services.vectorization_pipeline._mark_job_failed")
    @patch("src.services.vectorization_pipeline.db_manager")
    def test_job_not_found_returns_failed(self, mock_db, mock_mark_failed):
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        result = run_vectorization_pipeline("nonexistent-id")

        assert result["status"] == JobStatus.FAILED.value
        assert "error" in result

    @patch("src.services.vectorization_pipeline._mark_job_failed")
    @patch("src.services.vectorization_pipeline.db_manager")
    def test_non_pending_job_returns_failed(self, mock_db, mock_mark_failed):
        job = _make_job(status=JobStatus.COMPLETED.value)
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = job

        result = run_vectorization_pipeline(str(job.id))

        assert result["status"] == JobStatus.FAILED.value

    @patch("src.services.vectorization_pipeline._store_vector_records")
    @patch("src.services.vectorization_pipeline._embed_chunks")
    @patch("src.services.vectorization_pipeline.chunk_text")
    @patch("src.services.vectorization_pipeline._extract_text")
    @patch("src.services.vectorization_pipeline.db_manager")
    def test_successful_pipeline(
        self, mock_db, mock_extract, mock_chunk, mock_embed, mock_store,
    ):
        job = _make_job()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter_by.return_value.first.return_value = job

        mock_extract.return_value = "Some extracted text"
        mock_chunk.return_value = ["chunk1", "chunk2"]
        mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock_store.return_value = 2

        result = run_vectorization_pipeline(str(job.id))

        assert result["status"] == JobStatus.COMPLETED.value
        assert result["chunk_count"] == 2
        mock_extract.assert_called_once_with(job)
        mock_chunk.assert_called_once_with("Some extracted text", size=512, overlap=50)
        mock_embed.assert_called_once_with(["chunk1", "chunk2"], job.tenant_id)
        mock_store.assert_called_once()

    @patch("src.services.vectorization_pipeline._mark_job_failed")
    @patch("src.services.vectorization_pipeline._extract_text")
    @patch("src.services.vectorization_pipeline.db_manager")
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

        result = run_vectorization_pipeline(str(job.id))

        assert result["status"] == JobStatus.FAILED.value
        assert "extraction boom" in result["error"]
        mock_mark_failed.assert_called_once()
