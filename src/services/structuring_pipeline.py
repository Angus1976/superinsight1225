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

def _extract_content(session, job: StructuringJob, tracker=None) -> str | dict:
    """Step 1: Extract raw content based on file type.

    Returns:
        str for text files, TabularData-like dict for tabular files.
    """
    logger.info(f"[Job {job.id}] 步骤 1/6: 开始提取文件内容 (file_type={job.file_type})")
    if tracker:
        tracker.start_step(1, f"正在提取 {job.file_type} 文件内容...")
        tracker.save_to_job(session, job)
    _update_job_status(session, job, JobStatus.EXTRACTING.value)

    file_type = job.file_type

    if file_type in _TABULAR_TYPES:
        logger.info(f"[Job {job.id}] 使用 TabularParser 解析表格文件")
        if tracker:
            tracker.update_step(1, 30, "正在解析表格文件...")
            tracker.save_to_job(session, job)
        from src.extractors.tabular import TabularParser
        parser = TabularParser()
        tabular_data = parser.parse(job.file_path, file_type)
        # Store a text preview as raw_content for reference
        preview_rows = tabular_data.rows[:20]
        job.raw_content = str(preview_rows)
        session.flush()
        logger.info(f"[Job {job.id}] 表格文件提取完成: {tabular_data.row_count} 行, {len(tabular_data.headers)} 列")
        if tracker:
            tracker.complete_step(1, f"提取完成: {tabular_data.row_count} 行, {len(tabular_data.headers)} 列")
            tracker.save_to_job(session, job)
        return tabular_data

    if file_type in _TEXT_TYPES:
        logger.info(f"[Job {job.id}] 使用 FileExtractor 解析文本文件")
        if tracker:
            tracker.update_step(1, 30, "正在解析文本文件...")
            tracker.save_to_job(session, job)
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
        if tracker:
            tracker.complete_step(1, f"提取完成: {len(text)} 字符, {len(result.documents)} 个文档")
            tracker.save_to_job(session, job)
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


def _infer_schema(session, job: StructuringJob, content: Any, tracker=None) -> dict:
    """Step 2: Use SchemaInferrer to infer schema from content.

    Returns:
        InferredSchema serialised as dict.
    """
    logger.info(f"[Job {job.id}] 步骤 2/6: 开始推断数据结构 Schema")
    if tracker:
        tracker.start_step(2, "正在加载 LLM 配置...")
        tracker.save_to_job(session, job)
    _update_job_status(session, job, JobStatus.INFERRING.value)

    from src.ai.schema_inferrer import SchemaInferrer
    logger.info(f"[Job {job.id}] 正在加载 LLM 配置...")
    cloud_config = asyncio.run(_load_cloud_config(job.tenant_id))
    logger.info(f"[Job {job.id}] LLM 配置加载完成: model={cloud_config.openai_model}, base_url={cloud_config.openai_base_url}")
    
    if tracker:
        tracker.update_step(2, 30, f"正在调用 LLM ({cloud_config.openai_model})...")
        tracker.save_to_job(session, job)
    
    inferrer = SchemaInferrer(cloud_config)

    from src.extractors.tabular import TabularData
    if isinstance(content, TabularData):
        logger.info(f"[Job {job.id}] 正在调用 LLM 推断表格数据 Schema...")
        if tracker:
            tracker.update_step(2, 50, "正在推断表格 Schema...")
            tracker.save_to_job(session, job)
        schema = asyncio.run(inferrer.infer_from_tabular(content))
    else:
        content_preview = str(content)[:200] + "..." if len(str(content)) > 200 else str(content)
        logger.info(f"[Job {job.id}] 正在调用 LLM 推断文本数据 Schema (内容预览: {content_preview})")
        if tracker:
            tracker.update_step(2, 50, "正在推断文本 Schema...")
            tracker.save_to_job(session, job)
        schema = asyncio.run(inferrer.infer_from_text(str(content)))

    schema_dict = schema.model_dump()
    job.inferred_schema = schema_dict
    session.flush()
    logger.info(f"[Job {job.id}] Schema 推断完成: {len(schema_dict.get('fields', []))} 个字段, 置信度={schema_dict.get('confidence', 0)}")
    if tracker:
        tracker.complete_step(2, f"推断完成: {len(schema_dict.get('fields', []))} 个字段")
        tracker.save_to_job(session, job)
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
    session, job: StructuringJob, schema_dict: dict, tracker=None,
) -> list[dict]:
    """Step 4: Extract structured records using EntityExtractor.

    Returns:
        List of record dicts (fields, confidence, source_span).
    """
    logger.info(f"[Job {job.id}] 步骤 4/6: 开始提取结构化实体")
    if tracker:
        tracker.start_step(4, "正在加载 LLM 配置...")
        tracker.save_to_job(session, job)
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
    if tracker:
        tracker.update_step(4, 50, f"正在提取实体 (内容: {len(content)} 字符)...")
        tracker.save_to_job(session, job)
    result = asyncio.run(extractor.extract(content, schema))
    logger.info(f"[Job {job.id}] 实体提取完成: {len(result.records)} 条记录")
    if tracker:
        tracker.complete_step(4, f"提取完成: {len(result.records)} 条记录")
        tracker.save_to_job(session, job)
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

    Persists an AnnotationTaskModel row so the task appears in task management.

    Returns:
        Task dict with task_id and metadata.
    """
    logger.info(f"[Job {job.id}] 步骤 6/6: 创建标注任务")
    from src.models.data_lifecycle import AnnotationTaskModel, AnnotationType, TaskStatus

    task_id = uuid4()
    created_by = str(job.tenant_id) if job.tenant_id else "system"

    task = AnnotationTaskModel(
        id=task_id,
        name=f"标注任务: {job.file_name}",
        description=f"基于结构化 Job {job.id} 自动创建的标注任务",
        sample_ids=[str(job.id)],
        annotation_type=AnnotationType.CUSTOM,
        instructions=f"请对 {job.file_name} 的结构化结果进行标注",
        status=TaskStatus.CREATED,
        created_by=created_by,
        progress_total=job.record_count or 0,
        metadata_={
            "job_id": str(job.id),
            "schema": schema_dict,
            "record_count": job.record_count,
            "file_name": job.file_name,
        },
    )
    session.add(task)

    logger.info(f"[Job {job.id}] 标注任务创建完成: task_id={task_id}")
    return {
        "task_id": str(task_id),
        "name": task.name,
        "status": TaskStatus.CREATED.value,
        "record_count": job.record_count,
    }


# ---------------------------------------------------------------------------
# Cloud config loader
# ---------------------------------------------------------------------------

async def _load_cloud_config(
    tenant_id: str | None = None,
    application_code: str = "structuring"
):
    """Build a CloudConfig from database or environment variables.

    Priority order:
    1. Database bindings for the application (highest priority)
    2. Environment variables (fallback only if database has no config)
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant isolation.
        application_code: Application code (default: "structuring").
    
    Returns:
        CloudConfig instance.
    
    Raises:
        ValueError: If no valid LLM configuration is found or decryption fails.
    """
    import os
    from src.ai.llm_schemas import CloudConfig
    from src.database.connection import get_db_session
    from src.models.llm_configuration import LLMConfiguration
    from src.models.llm_application import LLMApplication, LLMApplicationBinding
    from src.ai.encryption_service import get_encryption_service
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    logger.info(f"Loading LLM config for application: {application_code}")
    
    # Step 1: Check database for configuration
    db = next(get_db_session())
    has_db_config = False
    
    try:
        # Get application
        stmt = select(LLMApplication).where(LLMApplication.code == application_code)
        result = db.execute(stmt)
        app = result.scalar_one_or_none()
        
        if not app:
            logger.info(f"Application '{application_code}' not found in database")
        else:
            # Get bindings ordered by priority
            stmt = (
                select(LLMApplicationBinding)
                .options(selectinload(LLMApplicationBinding.llm_config))
                .where(
                    LLMApplicationBinding.application_id == app.id,
                    LLMApplicationBinding.is_active == True
                )
                .join(LLMConfiguration)
                .where(LLMConfiguration.is_active == True)
                .order_by(LLMApplicationBinding.priority.asc())
            )
            
            # Apply tenant filter with fallback to global
            if tenant_id:
                # Try to convert tenant_id to UUID if it's a string
                from uuid import UUID as UUIDType
                try:
                    # If tenant_id is a valid UUID string, convert it
                    if isinstance(tenant_id, str):
                        tenant_uuid = UUIDType(tenant_id)
                    else:
                        tenant_uuid = tenant_id
                    
                    tenant_stmt = stmt.where(LLMConfiguration.tenant_id == tenant_uuid)
                    result = db.execute(tenant_stmt)
                    bindings = result.scalars().all()
                except (ValueError, AttributeError):
                    # tenant_id is not a valid UUID (e.g., "system"), skip tenant filter
                    logger.info(f"tenant_id '{tenant_id}' is not a valid UUID, using global config")
                    bindings = []
                
                if not bindings:
                    # Fallback to global config
                    global_stmt = stmt.where(LLMConfiguration.tenant_id == None)
                    result = db.execute(global_stmt)
                    bindings = result.scalars().all()
            else:
                global_stmt = stmt.where(LLMConfiguration.tenant_id == None)
                result = db.execute(global_stmt)
                bindings = result.scalars().all()
            
            if bindings:
                has_db_config = True
                binding = bindings[0]
                llm_config = binding.llm_config
                
                logger.info(
                    f"Found database config: {llm_config.name} "
                    f"(priority={binding.priority}, provider={llm_config.provider})"
                )
                
                # Step 2: If database has config, decrypt and use it (no fallback)
                try:
                    encryption_service = get_encryption_service()
                    config_data = llm_config.config_data or {}
                    api_key_encrypted = config_data.get("api_key_encrypted")
                    
                    if api_key_encrypted:
                        api_key = encryption_service.decrypt(api_key_encrypted)
                        logger.info(f"✓ API key decrypted successfully (length={len(api_key)})")
                    else:
                        api_key = config_data.get("api_key", "")
                        logger.warning("No encrypted API key found, using plain text key")
                    
                    base_url = config_data.get("base_url", "https://api.openai.com/v1")
                    model_name = config_data.get("model_name", "gpt-3.5-turbo")
                    timeout = binding.timeout_seconds or 60
                    max_retries = binding.max_retries or 3
                    
                    config = CloudConfig(
                        openai_api_key=api_key,
                        openai_base_url=base_url,
                        openai_model=model_name,
                        timeout=timeout,
                        max_retries=max_retries
                    )
                    
                    logger.info(
                        f"✓ Using database LLM config: model={config.openai_model}, "
                        f"base_url={config.openai_base_url}, priority={binding.priority}"
                    )
                    return config
                    
                except Exception as decrypt_error:
                    # Database has config but decryption failed - DO NOT fallback
                    error_msg = (
                        f"Database has LLM configuration but failed to decrypt: {decrypt_error}. "
                        f"Please check LLM_ENCRYPTION_KEY environment variable."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg) from decrypt_error
            else:
                logger.info(f"No active bindings found for application: {application_code}")
    
    finally:
        db.close()
    
    # Step 3: No database config found, fallback to environment variables
    if not has_db_config:
        logger.info("No database config found, falling back to environment variables")
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # If using Ollama, the API key can be any non-empty string
        if "ollama" in base_url.lower() and not api_key:
            api_key = "ollama"
        
        if not api_key:
            raise ValueError(
                "No LLM configuration found. Please configure in 'Management Console → "
                "Configuration Management → LLM Configuration' or set OPENAI_API_KEY "
                "environment variable."
            )
        
        logger.info(
            f"✓ Using environment variable LLM config: model={model}, base_url={base_url}"
        )
        
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
    from src.services.progress_tracker import ProgressTracker
    
    with db_manager.get_session() as session:
        job = session.query(StructuringJob).filter_by(id=job_id).first()
        if not job:
            raise ValueError(f"StructuringJob not found: {job_id}")
        if job.status != JobStatus.PENDING.value:
            raise ValueError(
                f"Job {job_id} is not pending (current: {job.status})"
            )

        # Initialize progress tracker
        tracker = ProgressTracker(job_id)
        tracker.save_to_job(session, job)

        try:
            # Step 1 — extract
            content = _extract_content(session, job, tracker)

            # Step 2 — infer schema
            schema_dict = _infer_schema(session, job, content, tracker)

            # Step 3 — confirm schema
            tracker.start_step(3, "正在确认 Schema...")
            tracker.save_to_job(session, job)
            confirmed = _wait_for_confirmation(session, job)
            tracker.complete_step(3, "Schema 已确认")
            tracker.save_to_job(session, job)

            # Step 4 — extract entities
            records = _extract_entities(session, job, confirmed, tracker)

            # Step 5 — store records
            tracker.start_step(5, f"正在存储 {len(records)} 条记录...")
            tracker.save_to_job(session, job)
            count = _store_records(session, job, records)
            tracker.complete_step(5, f"已存储 {count} 条记录")
            tracker.save_to_job(session, job)

            # Step 6 — create annotation task
            tracker.start_step(6, "正在创建标注任务...")
            tracker.save_to_job(session, job)
            task_info = _create_annotation_task(session, job, confirmed)
            tracker.complete_step(6, "标注任务已创建")
            tracker.save_to_job(session, job)

            # Mark completed
            _update_job_status(session, job, JobStatus.COMPLETED.value)
            tracker.complete_pipeline()
            tracker.save_to_job(session, job)

            logger.info(
                "Pipeline completed for job %s: %d records", job_id, count,
            )
            return {
                "job_id": str(job.id),
                "status": JobStatus.COMPLETED.value,
                "record_count": count,
                "task": task_info,
            }
        except Exception as exc:
            # Mark current step as failed
            if tracker.progress.current_step > 0:
                tracker.fail_step(tracker.progress.current_step, str(exc))
            tracker.fail_pipeline(str(exc))
            tracker.save_to_job(session, job)
            raise


def _mark_job_failed(job_id: str, error: str) -> None:
    """Best-effort: mark the job as failed in a fresh session."""
    try:
        with db_manager.get_session() as session:
            job = session.query(StructuringJob).filter_by(id=job_id).first()
            if job and job.status != JobStatus.FAILED.value:
                _fail_job(session, job, error)
    except Exception:
        logger.exception("Could not mark job %s as failed", job_id)
