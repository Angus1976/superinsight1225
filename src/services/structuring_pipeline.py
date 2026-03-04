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
    logger.info(f"[Job {job.id}] 步骤 1/6: 开始提取文件内容 (file_type={job.file_type})")
    _update_job_status(session, job, JobStatus.EXTRACTING.value)

    file_type = job.file_type

    if file_type in _TABULAR_TYPES:
        logger.info(f"[Job {job.id}] 使用 TabularParser 解析表格文件")
        from src.extractors.tabular import TabularParser
        parser = TabularParser()
        tabular_data = parser.parse(job.file_path, file_type)
        # Store a text preview as raw_content for reference
        preview_rows = tabular_data.rows[:20]
        job.raw_content = str(preview_rows)
        session.flush()
        logger.info(f"[Job {job.id}] 表格文件提取完成: {tabular_data.row_count} 行, {len(tabular_data.headers)} 列")
        return tabular_data

    if file_type in _TEXT_TYPES:
        logger.info(f"[Job {job.id}] 使用 FileExtractor 解析文本文件")
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
        logger.info(f"[Job {job.id}] 文本文件提取完成: {len(text)} 字符, {len(result.documents)} 个文档")
        return text

    if file_type in _PPT_TYPES:
        logger.info(f"[Job {job.id}] 使用 PPTExtractor 解析 PPT 文件")
        from src.extractors.ppt import PPTExtractor

        extractor = PPTExtractor()
        text = extractor.extract(job.file_path)
        if not text.strip():
            raise RuntimeError("PPT extraction returned empty content")
        job.raw_content = text
        session.flush()
        logger.info(f"[Job {job.id}] PPT 文件提取完成: {len(text)} 字符")
        return text

    if file_type in _MEDIA_TYPES:
        logger.info(f"[Job {job.id}] 使用 MediaTranscriber 转录媒体文件")
        from src.extractors.media import MediaTranscriber

        transcriber = MediaTranscriber()
        text = asyncio.run(transcriber.transcribe(job.file_path))
        if not text.strip():
            raise RuntimeError("Media transcription returned empty content")
        job.raw_content = text
        session.flush()
        logger.info(f"[Job {job.id}] 媒体文件转录完成: {len(text)} 字符")
        return text

    raise ValueError(f"Unsupported file type: {file_type}")


def _infer_schema(session, job: StructuringJob, content: Any) -> dict:
    """Step 2: Use SchemaInferrer to infer schema from content.

    Returns:
        InferredSchema serialised as dict.
    """
    logger.info(f"[Job {job.id}] 步骤 2/6: 开始推断数据结构 Schema")
    _update_job_status(session, job, JobStatus.INFERRING.value)

    from src.ai.schema_inferrer import SchemaInferrer
    logger.info(f"[Job {job.id}] 正在加载 LLM 配置...")
    cloud_config = asyncio.run(_load_cloud_config(job.tenant_id))
    logger.info(f"[Job {job.id}] LLM 配置加载完成: model={cloud_config.openai_model}, base_url={cloud_config.openai_base_url}")
    
    inferrer = SchemaInferrer(cloud_config)

    from src.extractors.tabular import TabularData
    if isinstance(content, TabularData):
        logger.info(f"[Job {job.id}] 正在调用 LLM 推断表格数据 Schema...")
        schema = asyncio.run(inferrer.infer_from_tabular(content))
    else:
        content_preview = str(content)[:200] + "..." if len(str(content)) > 200 else str(content)
        logger.info(f"[Job {job.id}] 正在调用 LLM 推断文本数据 Schema (内容预览: {content_preview})")
        schema = asyncio.run(inferrer.infer_from_text(str(content)))

    schema_dict = schema.model_dump()
    job.inferred_schema = schema_dict
    session.flush()
    logger.info(f"[Job {job.id}] Schema 推断完成: {len(schema_dict.get('fields', []))} 个字段, 置信度={schema_dict.get('confidence', 0)}")
    return schema_dict


def _wait_for_confirmation(session, job: StructuringJob) -> dict:
    """Step 3: Transition to confirming and return the schema to use.

    If the user has already confirmed a schema (via API), use it.
    Otherwise, auto-confirm with the inferred schema.
    """
    logger.info(f"[Job {job.id}] 步骤 3/6: 等待 Schema 确认")
    _update_job_status(session, job, JobStatus.CONFIRMING.value)

    if job.confirmed_schema:
        logger.info(f"[Job {job.id}] 使用用户已确认的 Schema")
        return job.confirmed_schema

    # Auto-confirm: use inferred schema as-is
    logger.info(f"[Job {job.id}] 自动确认推断的 Schema")
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
    logger.info(f"[Job {job.id}] 步骤 4/6: 开始提取结构化实体")
    _update_job_status(session, job, JobStatus.EXTRACTING_ENTITIES.value)

    from src.ai.entity_extractor import EntityExtractor
    from src.ai.schema_inferrer import InferredSchema

    logger.info(f"[Job {job.id}] 正在加载 LLM 配置...")
    cloud_config = asyncio.run(_load_cloud_config(job.tenant_id))
    extractor = EntityExtractor(cloud_config)
    schema = InferredSchema.model_validate(schema_dict)

    content = job.raw_content or ""
    if not content.strip():
        raise RuntimeError("No raw content available for entity extraction")

    logger.info(f"[Job {job.id}] 正在调用 LLM 提取实体 (内容长度: {len(content)} 字符)...")
    result = asyncio.run(extractor.extract(content, schema))
    logger.info(f"[Job {job.id}] 实体提取完成: {len(result.records)} 条记录")
    return [r.model_dump() for r in result.records]


def _store_records(
    session, job: StructuringJob, records: list[dict],
) -> int:
    """Step 5: Persist structured records to the database.

    Returns:
        Number of records stored.
    """
    logger.info(f"[Job {job.id}] 步骤 5/6: 开始存储结构化记录")
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
    logger.info(f"[Job {job.id}] 记录存储完成: {len(records)} 条")
    return len(records)


def _create_annotation_task(
    session, job: StructuringJob, schema_dict: dict,
) -> dict:
    """Step 6: Create an annotation Task linked to this job.

    Returns:
        Task dict with task_id and metadata.
    """
    logger.info(f"[Job {job.id}] 步骤 6/6: 创建标注任务")
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
    logger.info(f"[Job {job.id}] 标注任务创建完成: task_id={task.task_id}")
    return task.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Cloud config loader
# ---------------------------------------------------------------------------

async def _load_cloud_config(
    tenant_id: str | None = None,
    application_code: str = "structuring"
):
    """Build a CloudConfig from environment variables or database.

    Priority order:
    1. Environment variables (for simplicity and reliability)
    2. Database bindings for the application (future enhancement)
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant isolation.
        application_code: Application code (default: "structuring").
    
    Returns:
        CloudConfig instance.
    """
    import os
    from src.ai.llm_schemas import CloudConfig
    
    # Load from environment variables
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # If using Ollama, the API key can be any non-empty string
    if "ollama" in base_url.lower() and not api_key:
        api_key = "ollama"
    
    if not api_key:
        raise ValueError(
            "No LLM configuration found. Please set OPENAI_API_KEY environment variable."
        )
    
    logger.info(f"Using LLM config: model={model}, base_url={base_url}")
    
    return CloudConfig(
        openai_api_key=api_key,
        openai_base_url=base_url,
        openai_model=model,
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
