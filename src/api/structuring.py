"""
Structuring API — FastAPI endpoints for AI data structuring.

Provides 6 endpoints for the full structuring workflow:
create job, query status, confirm schema, extract entities,
get records, and create annotation tasks.
"""

import logging
import os
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth_simple import SimpleUser, get_current_user
from src.config.settings import settings
from src.database.connection import get_db_session
from src.models.structuring import (
    FileType,
    JobStatus,
    StructuredRecord,
    StructuringJob,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/structuring", tags=["Data Structuring"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Extension → FileType mapping
_EXTENSION_MAP: dict[str, str] = {
    ".pdf": FileType.PDF.value,
    ".csv": FileType.CSV.value,
    ".xlsx": FileType.EXCEL.value,
    ".xls": FileType.EXCEL.value,
    ".docx": FileType.DOCX.value,
    ".html": FileType.HTML.value,
    ".htm": FileType.HTML.value,
    ".txt": FileType.TXT.value,
    ".md": FileType.MARKDOWN.value,
    ".pptx": FileType.PPT.value,
    ".ppt": FileType.PPT.value,
    ".mp4": FileType.VIDEO.value,
    ".avi": FileType.VIDEO.value,
    ".mov": FileType.VIDEO.value,
    ".mkv": FileType.VIDEO.value,
    ".webm": FileType.VIDEO.value,
    ".mp3": FileType.AUDIO.value,
    ".wav": FileType.AUDIO.value,
    ".flac": FileType.AUDIO.value,
    ".ogg": FileType.AUDIO.value,
    ".m4a": FileType.AUDIO.value,
}

SUPPORTED_EXTENSIONS = set(_EXTENSION_MAP.keys())


# ---------------------------------------------------------------------------
# Pydantic response / request models
# ---------------------------------------------------------------------------


class JobCreateResponse(BaseModel):
    """Response for POST /jobs."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    created_at: datetime
    message: str


class JobStatusResponse(BaseModel):
    """Response for GET /jobs/{id}."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    record_count: int
    raw_content: Optional[str] = None
    inferred_schema: Optional[dict] = None
    confirmed_schema: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SchemaConfirmRequest(BaseModel):
    """Request body for PUT /jobs/{id}/schema."""
    confirmed_schema: dict = Field(..., description="User-confirmed schema (InferredSchema format)")


class SchemaConfirmResponse(BaseModel):
    """Response for PUT /jobs/{id}/schema."""
    job_id: str
    confirmed_schema: dict
    message: str


class ExtractResponse(BaseModel):
    """Response for POST /jobs/{id}/extract."""
    job_id: str
    status: str
    message: str


class RecordItem(BaseModel):
    """Single structured record."""
    id: str
    fields: dict
    confidence: float
    source_span: Optional[str] = None
    created_at: datetime


class RecordListResponse(BaseModel):
    """Paginated response for GET /jobs/{id}/records."""
    items: list[RecordItem]
    total: int
    page: int
    size: int


class CreateTaskResponse(BaseModel):
    """Response for POST /jobs/{id}/create-tasks."""
    job_id: str
    task: dict
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_file_type(filename: str) -> str:
    """Resolve file extension to FileType value. Raises HTTPException on unsupported."""
    ext = os.path.splitext(filename)[1].lower()
    file_type = _EXTENSION_MAP.get(ext)
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )
    return file_type


def _get_job_or_404(
    job_id: str,
    db: Session,
    tenant_id: str,
) -> StructuringJob:
    """Fetch a StructuringJob by id + tenant, or raise 404."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    job = (
        db.query(StructuringJob)
        .filter(StructuringJob.id == job_uuid, StructuringJob.tenant_id == tenant_id)
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structuring job not found",
        )
    return job


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_structuring_job(
    file: UploadFile = File(...),
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> JobCreateResponse:
    """Upload a file and create a new structuring job.

    Supported formats: PDF, CSV, Excel (.xlsx/.xls), DOCX, HTML, TXT, Markdown (.md).
    Max file size: 100 MB.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    file_type = _get_file_type(file.filename)

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty or corrupted")

    # Persist file to disk
    upload_dir = getattr(settings.app, "upload_dir", "./uploads")
    structuring_dir = os.path.join(upload_dir, "structuring")
    os.makedirs(structuring_dir, exist_ok=True)

    import uuid as _uuid
    safe_name = f"{_uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(structuring_dir, safe_name)

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except OSError as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )

    # Create DB record
    job = StructuringJob(
        tenant_id=current_user.tenant_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.flush()

    # Submit Celery task
    try:
        from src.services.structuring_pipeline import run_structuring_pipeline
        run_structuring_pipeline.delay(str(job.id))
    except Exception as exc:
        logger.warning("Could not submit Celery task (will need manual trigger): %s", exc)

    return JobCreateResponse(
        job_id=str(job.id),
        status=job.status,
        file_name=job.file_name,
        file_type=job.file_type,
        created_at=job.created_at or datetime.utcnow(),
        message="Structuring job created",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_structuring_job(
    job_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> JobStatusResponse:
    """Query job status, schema, record count, and error message."""
    job = _get_job_or_404(job_id, db, current_user.tenant_id)

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        file_name=job.file_name,
        file_type=job.file_type,
        record_count=job.record_count,
        raw_content=job.raw_content,
        inferred_schema=job.inferred_schema,
        confirmed_schema=job.confirmed_schema,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.put("/jobs/{job_id}/schema", response_model=SchemaConfirmResponse)
def confirm_schema(
    job_id: str,
    body: SchemaConfirmRequest,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SchemaConfirmResponse:
    """User confirms or edits the inferred schema."""
    job = _get_job_or_404(job_id, db, current_user.tenant_id)

    if job.status not in (JobStatus.CONFIRMING.value, JobStatus.INFERRING.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm schema when job status is '{job.status}'. Expected 'confirming' or 'inferring'.",
        )

    job.confirmed_schema = body.confirmed_schema
    db.flush()

    return SchemaConfirmResponse(
        job_id=str(job.id),
        confirmed_schema=job.confirmed_schema,
        message="Schema confirmed",
    )


@router.post("/jobs/{job_id}/extract", response_model=ExtractResponse)
def trigger_extraction(
    job_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ExtractResponse:
    """Trigger entity extraction after schema confirmation.

    The job must have a confirmed_schema and be in 'confirming' status.
    Submits a Celery task for the extraction phase.
    """
    job = _get_job_or_404(job_id, db, current_user.tenant_id)

    if not job.confirmed_schema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schema must be confirmed before extraction",
        )

    if job.status != JobStatus.CONFIRMING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot extract when job status is '{job.status}'. Expected 'confirming'.",
        )

    # Submit Celery task for extraction phase
    try:
        from src.services.structuring_pipeline import run_structuring_pipeline
        run_structuring_pipeline.delay(str(job.id))
    except Exception as exc:
        logger.warning("Could not submit extraction Celery task: %s", exc)

    return ExtractResponse(
        job_id=str(job.id),
        status=job.status,
        message="Entity extraction triggered",
    )


@router.get("/jobs/{job_id}/records", response_model=RecordListResponse)
def get_structuring_records(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RecordListResponse:
    """Return paginated structured records for a job."""
    job = _get_job_or_404(job_id, db, current_user.tenant_id)

    query = db.query(StructuredRecord).filter(StructuredRecord.job_id == job.id)
    total = query.count()

    records = (
        query.order_by(StructuredRecord.created_at)
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = [
        RecordItem(
            id=str(r.id),
            fields=r.fields,
            confidence=r.confidence,
            source_span=r.source_span,
            created_at=r.created_at,
        )
        for r in records
    ]

    return RecordListResponse(items=items, total=total, page=page, size=size)


@router.post("/jobs/{job_id}/create-tasks", response_model=CreateTaskResponse)
def create_annotation_task(
    job_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CreateTaskResponse:
    """Create an annotation task from a completed structuring job."""
    job = _get_job_or_404(job_id, db, current_user.tenant_id)

    if job.status != JobStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create tasks when job status is '{job.status}'. Expected 'completed'.",
        )

    schema_dict = job.confirmed_schema or job.inferred_schema or {}

    from src.services.structuring_pipeline import _create_annotation_task
    task_info = _create_annotation_task(db, job, schema_dict)

    return CreateTaskResponse(
        job_id=str(job.id),
        task=task_info,
        message="Annotation task created",
    )
