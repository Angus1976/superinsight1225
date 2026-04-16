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
from src.services.structuring_pipeline import get_celery_app
from src.ai.llm_schemas import openai_compatible_chat_headers

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


def _embed_chunks(
    chunks: list[str],
    tenant_id: str | None,
    session: Any = None,
    job: Any = None,
) -> list[list[float]]:
    """Generate embeddings for each chunk via DB-configured providers.

    Uses ``_load_all_cloud_configs(application_code="embedding")`` so the
    model is controlled entirely from the LLM configuration tables.
    Falls back to env vars only when no DB config exists.
    """
    from src.services.structuring_pipeline import _load_all_cloud_configs

    configs = asyncio.run(
        _load_all_cloud_configs(tenant_id=tenant_id, application_code="embedding")
    )

    total = len(chunks)
    embeddings: list[list[float]] = []

    for idx, chunk in enumerate(chunks):
        embedding = _embed_single_with_fallback(chunk, configs)
        embeddings.append(embedding)

        if session and job:
            job.progress_info = {
                "stage": "embedding",
                "current": idx + 1,
                "total": total,
                "percent": round((idx + 1) / total * 100),
            }
            session.flush()

    return embeddings


def _embed_single_with_fallback(text: str, configs: list) -> list[float]:
    """Try each config in priority order until embedding succeeds.

    DeepSeek doesn't support embeddings so it is skipped.  For Ollama
    we use ``/api/embeddings``; for OpenAI-compatible providers the
    standard ``/embeddings`` endpoint.  The model name comes from the
    DB config (``cfg.openai_model``), no hardcoded defaults.
    """
    import httpx

    last_error: Exception | None = None
    for cfg in configs:
        base_url = cfg.openai_base_url

        # DeepSeek has no embedding endpoint — skip
        if "deepseek" in base_url.lower():
            logger.info("Skipping DeepSeek for embedding (not supported)")
            continue

        try:
            # Ollama uses a different endpoint
            if "ollama" in base_url.lower() or ":11434" in base_url:
                ollama_base = base_url.rstrip("/")
                if ollama_base.endswith("/v1"):
                    ollama_base = ollama_base[:-3]
                resp = httpx.post(
                    f"{ollama_base}/api/embeddings",
                    json={"model": cfg.openai_model, "prompt": text},
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json()["embedding"]

            # Standard OpenAI-compatible embedding endpoint
            embed_url = base_url.rstrip("/") + "/embeddings"
            h = openai_compatible_chat_headers(cfg)
            resp = httpx.post(
                embed_url,
                headers=h,
                json={"input": text, "model": cfg.openai_model},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Embedding failed for %s (%s): %s — trying next",
                           cfg.openai_model, base_url, exc)
            last_error = exc

    raise RuntimeError(f"All embedding configs failed. Last error: {last_error}")


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

_app = get_celery_app()


@_app.task(
    bind=True,
    name="vectorization.run_pipeline",
    max_retries=2,
    soft_time_limit=600,
    time_limit=660,
    acks_late=True,
)
def run_vectorization_pipeline(self, job_id: str) -> dict:
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
        job.progress_info = {"stage": "extracting", "current": 0, "total": 0, "percent": 0}
        session.flush()
        text = _extract_text(job)
        job.raw_content = text
        session.flush()

        # Step 2 — chunk
        chunks = chunk_text(text, size=512, overlap=50)
        job.status = "processing"
        job.progress_info = {"stage": "chunking", "current": 0, "total": len(chunks), "percent": 0}
        session.flush()

        # Step 3 — embed (progress updated per-chunk inside helper)
        embeddings = _embed_chunks(chunks, job.tenant_id, session=session, job=job)

        # Step 4 — store
        job.progress_info = {"stage": "storing", "current": len(chunks), "total": len(chunks), "percent": 99}
        session.flush()
        count = _store_vector_records(session, job, chunks, embeddings)

        # Mark completed
        job.status = JobStatus.COMPLETED.value
        job.progress_info = {"stage": "completed", "current": count, "total": count, "percent": 100}
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
