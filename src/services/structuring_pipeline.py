"""
Structuring pipeline — Celery task orchestration.

Orchestrates the full structuring workflow:
extract content → infer schema → (wait for confirmation) →
extract entities → store records → create annotation task.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from src.database.connection import db_manager
from src.models.structuring import (
    FileType as StructuringFileType,
    JobStateMachine,
    JobStatus,
    StructuredRecord,
    StructuringJob,
)
from src.sync.async_queue.celery_integration import create_celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIPELINE_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
MAX_RETRIES = 3

# File-type routing sets
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

# Celery app singleton (lazy)
_celery_app = None


def get_celery_app():
    """Return (or create) the shared Celery application."""
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app(name="structuring_worker")
    return _celery_app


# ---------------------------------------------------------------------------
# Status helpers — delegate to JobStateMachine (src/models/structuring.py)
# ---------------------------------------------------------------------------

# Keep module-level references for backward compatibility with existing callers.
_VALID_TRANSITIONS = JobStateMachine._FORWARD_TRANSITIONS


def is_valid_transition(current: str, target: str) -> bool:
    """Return True if *current* → *target* is a legal status transition."""
    return JobStateMachine.is_valid_transition(current, target)


def _update_job_status(
    session,
    job: StructuringJob,
    new_status: str,
    error_message: str | None = None,
) -> None:
    """Transition job status with validation."""
    JobStateMachine.validate_transition(job.status, new_status)
    job.status = new_status
    if error_message is not None:
        job.error_message = error_message
    session.flush()


def _fail_job(session, job: StructuringJob, error: str) -> None:
    """Mark a job as failed with an error message."""
    job.status = JobStatus.FAILED.value
    job.error_message = error
    session.flush()


# ---------------------------------------------------------------------------
# Pipeline step functions (each ≤ 40 lines)
# ---------------------------------------------------------------------------

def _extract_content(session, job: StructuringJob) -> str | dict:
    """Step 1: Extract raw content based on file type.

    Returns:
        str for text files, TabularData-like dict for tabular files.
    """
    _update_job_status(session, job, JobStatus.EXTRACTING.value)

    file_type = job.file_type

    if file_type in _TABULAR_TYPES:
        from src.extractors.tabular import TabularParser
        parser = TabularParser()
        tabular_data = parser.parse(job.file_path, file_type)
        # Store a text preview as raw_content for reference
        preview_rows = tabular_data.rows[:20]
        job.raw_content = str(preview_rows)
        session.flush()
        return tabular_data

    if file_type in _TEXT_TYPES:
        from src.extractors.base import FileConfig, FileType as ExtractorFileType
        from src.extractors.file import FileExtractor

        ext_file_type = ExtractorFileType(file_type)
        config = FileConfig(file_path=job.file_path, file_type=ext_file_type)
        extractor = FileExtractor(config)
        result = extractor.extract_data()

        if not result.success or not result.documents:
            raise RuntimeError(
                f"File extraction failed: {result.error or 'no documents extracted'}"
            )

        text = "\n\n".join(doc.content for doc in result.documents)
        job.raw_content = text
        session.flush()
        return text

    if file_type in _PPT_TYPES:
        from src.extractors.ppt import PPTExtractor

        extractor = PPTExtractor()
        text = extractor.extract(job.file_path)
        if not text.strip():
            raise RuntimeError("PPT extraction returned empty content")
        job.raw_content = text
        session.flush()
        return text

    if file_type in _MEDIA_TYPES:
        from src.extractors.media import MediaTranscriber

        transcriber = MediaTranscriber()
        text = asyncio.run(transcriber.transcribe(job.file_path))
        if not text.strip():
            raise RuntimeError("Media transcription returned empty content")
        job.raw_content = text
        session.flush()
        return text

    raise ValueError(f"Unsupported file type: {file_type}")


def _infer_schema(session, job: StructuringJob, content: Any) -> dict:
    """Step 2: Use SchemaInferrer to infer schema from content.

    Returns:
        InferredSchema serialised as dict.
    """
    _update_job_status(session, job, JobStatus.INFERRING.value)

    from src.ai.schema_inferrer import SchemaInferrer
    cloud_config = _load_cloud_config(job.tenant_id)
    inferrer = SchemaInferrer(cloud_config)

    from src.extractors.tabular import TabularData
    if isinstance(content, TabularData):
        schema = asyncio.run(inferrer.infer_from_tabular(content))
    else:
        schema = asyncio.run(inferrer.infer_from_text(str(content)))

    schema_dict = schema.model_dump()
    job.inferred_schema = schema_dict
    session.flush()
    return schema_dict


def _wait_for_confirmation(session, job: StructuringJob) -> dict:
    """Step 3: Transition to confirming and return the schema to use.

    If the user has already confirmed a schema (via API), use it.
    Otherwise, auto-confirm with the inferred schema.
    """
    _update_job_status(session, job, JobStatus.CONFIRMING.value)

    if job.confirmed_schema:
        return job.confirmed_schema

    # Auto-confirm: use inferred schema as-is
    job.confirmed_schema = job.inferred_schema
    session.flush()
    return job.confirmed_schema


def _extract_entities(
    session, job: StructuringJob, schema_dict: dict,
) -> list[dict]:
    """Step 4: Extract structured records using EntityExtractor.

    Returns:
        List of record dicts (fields, confidence, source_span).
    """
    _update_job_status(session, job, JobStatus.EXTRACTING_ENTITIES.value)

    from src.ai.entity_extractor import EntityExtractor
    from src.ai.schema_inferrer import InferredSchema

    cloud_config = _load_cloud_config(job.tenant_id)
    extractor = EntityExtractor(cloud_config)
    schema = InferredSchema.model_validate(schema_dict)

    content = job.raw_content or ""
    if not content.strip():
        raise RuntimeError("No raw content available for entity extraction")

    result = asyncio.run(extractor.extract(content, schema))
    return [r.model_dump() for r in result.records]


def _store_records(
    session, job: StructuringJob, records: list[dict],
) -> int:
    """Step 5: Persist structured records to the database.

    Returns:
        Number of records stored.
    """
    for rec in records:
        db_record = StructuredRecord(
            job_id=job.id,
            fields=rec.get("fields", {}),
            confidence=rec.get("confidence", 0.0),
            source_span=rec.get("source_span"),
        )
        session.add(db_record)

    job.record_count = len(records)
    session.flush()
    return len(records)


def _create_annotation_task(
    session, job: StructuringJob, schema_dict: dict,
) -> dict:
    """Step 6: Create an annotation Task linked to this job.

    Returns:
        Task dict with task_id and metadata.
    """
    from src.models.task import Task

    task = Task(
        task_id=uuid4(),
        project_id=uuid4(),  # placeholder — real project comes from caller
        tenant_id=job.tenant_id if job.tenant_id else str(uuid4()),
        title=f"标注任务: {job.file_name}",
        description=f"基于结构化 Job {job.id} 自动创建的标注任务",
        status="pending",
        metadata={
            "job_id": str(job.id),
            "schema": schema_dict,
            "record_count": job.record_count,
        },
    )
    return task.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Cloud config loader
# ---------------------------------------------------------------------------

def _load_cloud_config(tenant_id: str | None = None):
    """Build a CloudConfig from environment / settings.

    Falls back to env vars when no DB-stored config is available.
    """
    import os
    from src.ai.llm_schemas import CloudConfig

    return CloudConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    )


# ---------------------------------------------------------------------------
# Main Celery task
# ---------------------------------------------------------------------------

celery_app = get_celery_app()


@celery_app.task(
    bind=True,
    name="structuring.run_pipeline",
    max_retries=MAX_RETRIES,
    soft_time_limit=PIPELINE_TIMEOUT_SECONDS,
    time_limit=PIPELINE_TIMEOUT_SECONDS + 60,
    acks_late=True,
)
def run_structuring_pipeline(self, job_id: str) -> dict:
    """Execute the full structuring pipeline for a given job.

    Steps:
        1. Extract content (FileExtractor or TabularParser)
        2. Infer schema via SchemaInferrer
        3. Wait for / auto-confirm schema
        4. Extract entities via EntityExtractor
        5. Store structured records
        6. Create annotation task

    Returns:
        dict with job_id, status, record_count, and task info.
    """
    logger.info("Starting structuring pipeline for job %s", job_id)

    try:
        return _execute_pipeline(job_id)
    except Exception as exc:
        logger.exception("Pipeline failed for job %s: %s", job_id, exc)
        _mark_job_failed(job_id, str(exc))
        # Let Celery retry on transient errors
        if self.request.retries < MAX_RETRIES:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        return {"job_id": job_id, "status": JobStatus.FAILED.value, "error": str(exc)}


def _execute_pipeline(job_id: str) -> dict:
    """Run all pipeline steps inside a single DB session."""
    with db_manager.get_session() as session:
        job = session.query(StructuringJob).filter_by(id=job_id).first()
        if not job:
            raise ValueError(f"StructuringJob not found: {job_id}")
        if job.status != JobStatus.PENDING.value:
            raise ValueError(
                f"Job {job_id} is not pending (current: {job.status})"
            )

        # Step 1 — extract
        content = _extract_content(session, job)

        # Step 2 — infer schema
        schema_dict = _infer_schema(session, job, content)

        # Step 3 — confirm schema
        confirmed = _wait_for_confirmation(session, job)

        # Step 4 — extract entities
        records = _extract_entities(session, job, confirmed)

        # Step 5 — store records
        count = _store_records(session, job, records)

        # Step 6 — create annotation task
        task_info = _create_annotation_task(session, job, confirmed)

        # Mark completed
        _update_job_status(session, job, JobStatus.COMPLETED.value)

        logger.info(
            "Pipeline completed for job %s: %d records", job_id, count,
        )
        return {
            "job_id": str(job.id),
            "status": JobStatus.COMPLETED.value,
            "record_count": count,
            "task": task_info,
        }


def _mark_job_failed(job_id: str, error: str) -> None:
    """Best-effort: mark the job as failed in a fresh session."""
    try:
        with db_manager.get_session() as session:
            job = session.query(StructuringJob).filter_by(id=job_id).first()
            if job and job.status != JobStatus.FAILED.value:
                _fail_job(session, job, error)
    except Exception:
        logger.exception("Could not mark job %s as failed", job_id)
