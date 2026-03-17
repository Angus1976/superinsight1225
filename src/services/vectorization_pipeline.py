"""
Vectorization pipeline — text chunking and embedding.

Provides token-level text chunking with overlap using tiktoken,
and orchestrates the vectorization workflow:
extract content → chunk text → embed → store vector records.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import tiktoken

from src.database.connection import db_manager
from src.models.structuring import (
    FileType as StructuringFileType,
    JobStatus,
    StructuringJob,
    VectorRecord,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tokenizer (cl100k_base — GPT-4 encoding)
# ---------------------------------------------------------------------------

_encoding = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, size: int = 512, overlap: int = 50) -> list[str]:
    """Split *text* into chunks of at most *size* tokens with *overlap* token
    overlap between adjacent chunks.

    Pre-conditions:
        - *text* is non-empty
        - *size* > *overlap* > 0

    Post-conditions:
        - Returns at least one chunk when *text* is non-empty
        - Every chunk has ≤ *size* tokens
        - Adjacent chunks share exactly *overlap* tokens
        - All chunks concatenated (accounting for overlap) cover the full text

    Algorithm:
        1. Encode the full text into tokens via tiktoken.
        2. Slide a window of *size* tokens, stepping by ``size - overlap``.
        3. Decode each window back to text.
    """
    if not text:
        raise ValueError("text must be non-empty")
    if overlap <= 0:
        raise ValueError("overlap must be > 0")
    if size <= overlap:
        raise ValueError("size must be > overlap")

    tokens: list[int] = _encoding.encode(text)
    total = len(tokens)

    if total == 0:
        # Edge case: text is non-empty but encodes to zero tokens (unlikely)
        return [text]

    step = size - overlap
    chunks: list[str] = []
    pos = 0

    while pos < total:
        window = tokens[pos : pos + size]
        chunks.append(_encoding.decode(window))

        # If this window already reaches the end, we're done
        if pos + size >= total:
            break

        pos += step

    return chunks


# ---------------------------------------------------------------------------
# File-type routing sets (mirrors structuring_pipeline.py)
# ---------------------------------------------------------------------------

_TABULAR_TYPES = {StructuringFileType.CSV.value, StructuringFileType.EXCEL.value}
_TEXT_TYPES = {
    StructuringFileType.PDF.value,
    StructuringFileType.DOCX.value,
    StructuringFileType.TXT.value,
    StructuringFileType.HTML.value,
    StructuringFileType.MARKDOWN.value,
    StructuringFileType.JSON.value,
}
_PPT_TYPES = {StructuringFileType.PPT.value}
_MEDIA_TYPES = {StructuringFileType.VIDEO.value, StructuringFileType.AUDIO.value}

# ---------------------------------------------------------------------------
# Content extraction (reuses existing extractors)
# ---------------------------------------------------------------------------


def _extract_text(job: StructuringJob) -> str:
    """Extract plain text from the file associated with *job*.

    Tabular files are converted to a text representation.
    Raises ``RuntimeError`` on extraction failure.
    """
    file_type = job.file_type

    if file_type in _TEXT_TYPES:
        from src.extractors.base import FileConfig, FileType as ExtractorFileType
        from src.extractors.file import FileExtractor

        config = FileConfig(
            file_path=job.file_path,
            file_type=ExtractorFileType(file_type),
        )
        result = FileExtractor(config).extract_data()
        if not result.success or not result.documents:
            raise RuntimeError(
                f"File extraction failed: {result.error or 'no documents'}"
            )
        return "\n\n".join(doc.content for doc in result.documents)

    if file_type in _TABULAR_TYPES:
        from src.extractors.tabular import TabularParser

        data = TabularParser().parse(job.file_path, file_type)
        # Build text: header line + data rows (dict values, not keys)
        header_line = ", ".join(data.headers)
        rows_text = [", ".join(str(v) for v in row.values()) for row in data.rows[:500]]
        return header_line + "\n" + "\n".join(rows_text)

    if file_type in _PPT_TYPES:
        from src.extractors.ppt import PPTExtractor

        text = PPTExtractor().extract(job.file_path)
        if not text.strip():
            raise RuntimeError("PPT extraction returned empty content")
        return text

    if file_type in _MEDIA_TYPES:
        from src.extractors.media import MediaTranscriber

        text = asyncio.run(MediaTranscriber().transcribe(job.file_path))
        if not text.strip():
            raise RuntimeError("Media transcription returned empty content")
        return text

    raise ValueError(f"Unsupported file type: {file_type}")


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------


def _embed_chunks(chunks: list[str], tenant_id: str | None) -> list[list[float]]:
    """Generate embeddings for each chunk via LLMSwitcher.embed().

    Returns a list of 1536-dim float vectors, one per chunk.
    """
    from src.ai.llm_switcher import get_llm_switcher

    switcher = get_llm_switcher(tenant_id=tenant_id)
    embeddings: list[list[float]] = []
    for chunk in chunks:
        response = asyncio.run(switcher.embed(chunk))
        embeddings.append(response.embedding)
    return embeddings


# ---------------------------------------------------------------------------
# Batch store
# ---------------------------------------------------------------------------


def _store_vector_records(
    session: Any,
    job: StructuringJob,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    """Write VectorRecord rows for every chunk/embedding pair.

    Returns the number of records stored.
    """
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        record = VectorRecord(
            job_id=job.id,
            chunk_index=idx,
            chunk_text=chunk,
            embedding=embedding,
            metadata_={"chunk_size": 512, "overlap": 50},
        )
        session.add(record)

    count = len(chunks)
    job.chunk_count = count
    session.flush()
    return count


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------


def run_vectorization_pipeline(job_id: str) -> dict:
    """Execute the vectorization pipeline for a given job.

    Steps:
        1. Extract text content from the source file
        2. Chunk text (512 tokens, 50 overlap)
        3. Generate embeddings via LLMSwitcher.embed()
        4. Batch write VectorRecord entries

    Returns:
        dict with job_id, status, and chunk_count.
    """
    logger.info("Starting vectorization pipeline for job %s", job_id)

    try:
        return _execute_vectorization(job_id)
    except Exception as exc:
        logger.exception("Vectorization pipeline failed for job %s: %s", job_id, exc)
        _mark_job_failed(job_id, str(exc))
        return {
            "job_id": job_id,
            "status": JobStatus.FAILED.value,
            "error": str(exc),
        }


def _execute_vectorization(job_id: str) -> dict:
    """Run all vectorization steps inside a single DB session."""
    with db_manager.get_session() as session:
        job = session.query(StructuringJob).filter_by(id=job_id).first()
        if not job:
            raise ValueError(f"StructuringJob not found: {job_id}")
        if job.status != JobStatus.PENDING.value:
            raise ValueError(
                f"Job {job_id} is not pending (current: {job.status})"
            )

        # Step 1 — extract text
        job.status = JobStatus.EXTRACTING.value
        session.flush()
        text = _extract_text(job)
        job.raw_content = text
        session.flush()

        # Step 2 — chunk
        chunks = chunk_text(text, size=512, overlap=50)

        # Step 3 — embed
        embeddings = _embed_chunks(chunks, job.tenant_id)

        # Step 4 — store
        count = _store_vector_records(session, job, chunks, embeddings)

        # Mark completed
        job.status = JobStatus.COMPLETED.value
        session.flush()

        logger.info(
            "Vectorization completed for job %s: %d chunks", job_id, count,
        )
        return {
            "job_id": str(job.id),
            "status": JobStatus.COMPLETED.value,
            "chunk_count": count,
        }


def _mark_job_failed(job_id: str, error: str) -> None:
    """Best-effort: mark the job as failed in a fresh session."""
    try:
        with db_manager.get_session() as session:
            job = session.query(StructuringJob).filter_by(id=job_id).first()
            if job and job.status != JobStatus.FAILED.value:
                job.status = JobStatus.FAILED.value
                job.error_message = error
                session.flush()
    except Exception:
        logger.exception("Could not mark job %s as failed", job_id)
