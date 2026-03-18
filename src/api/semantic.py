"""
Semantic API — FastAPI endpoints for AI semantic analysis processing.

Provides endpoints for creating semantic jobs, querying status,
and retrieving semantic records (entities, relationships, summaries).
"""

import logging
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth_simple import SimpleUser, get_current_user
from src.config.settings import settings
from src.database.connection import get_db_session
from src.models.structuring import (
    JobStatus,
    ProcessingType,
    SemanticRecord,
    StructuringJob,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/semantic", tags=["Semantic"])

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Extension → FileType mapping (reuse from structuring)
from src.api.structuring import _EXTENSION_MAP, SUPPORTED_EXTENSIONS


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class SemJobCreateResponse(BaseModel):
    """Response for POST /jobs."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    created_at: datetime
    message: str


class SemJobStatusResponse(BaseModel):
    """Response for GET /jobs/{id}."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    record_count: int = 0
    error_message: Optional[str] = None
    progress_info: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class SemJobListItem(BaseModel):
    """Single item in the job list."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    progress_info: Optional[dict] = None
    created_at: datetime


class SemJobListResponse(BaseModel):
    """Response for GET /jobs."""
    items: list[SemJobListItem]
    total: int


class SemRecordItem(BaseModel):
    """Single semantic record."""
    id: str
    record_type: str
    content: dict
    confidence: float
    created_at: datetime


class SemRecordListResponse(BaseModel):
    """Paginated response for GET /jobs/{id}/records."""
    items: list[SemRecordItem]
    total: int
    page: int
    size: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_file_type(filename: str) -> str:
    """Resolve file extension to FileType value."""
    ext = os.path.splitext(filename)[1].lower()
    file_type = _EXTENSION_MAP.get(ext)
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )
    return file_type


def _get_sem_job_or_404(
    job_id: str,
    db: Session,
    tenant_id: str,
) -> StructuringJob:
    """Fetch a semantic job by id + tenant, or raise 404."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    job = (
        db.query(StructuringJob)
        .filter(
            StructuringJob.id == job_uuid,
            StructuringJob.tenant_id == tenant_id,
            StructuringJob.processing_type == ProcessingType.SEMANTIC.value,
        )
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semantic job not found",
        )
    return job


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=SemJobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_semantic_job(
    file: UploadFile = File(...),
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SemJobCreateResponse:
    """Upload a file and create a new semantic analysis job.

    Creates a StructuringJob with processing_type='semantic'
    and submits to the Celery pipeline.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided",
        )

    file_type = _get_file_type(file.filename)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty or corrupted",
        )

    # Persist file to disk
    upload_dir = getattr(settings.app, "upload_dir", "./uploads")
    sem_dir = os.path.join(upload_dir, "semantic")
    os.makedirs(sem_dir, exist_ok=True)

    import uuid as _uuid
    safe_name = f"{_uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(sem_dir, safe_name)

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except OSError as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )

    # Create DB record with processing_type=semantic
    job = StructuringJob(
        tenant_id=current_user.tenant_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type,
        processing_type=ProcessingType.SEMANTIC.value,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.flush()

    # Submit Celery task
    try:
        from src.services.semantic_pipeline import run_semantic_pipeline
        run_semantic_pipeline.delay(str(job.id))
    except Exception as exc:
        logger.warning(
            "Could not submit Celery task (will need manual trigger): %s", exc,
        )

    return SemJobCreateResponse(
        job_id=str(job.id),
        status=job.status,
        file_name=job.file_name,
        file_type=job.file_type,
        created_at=job.created_at or datetime.utcnow(),
        message="Semantic job created",
    )


@router.get("/jobs", response_model=SemJobListResponse)
def list_semantic_jobs(
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SemJobListResponse:
    """List all semantic jobs for the current tenant."""
    query = (
        db.query(StructuringJob)
        .filter(
            StructuringJob.tenant_id == current_user.tenant_id,
            StructuringJob.processing_type == ProcessingType.SEMANTIC.value,
        )
        .order_by(StructuringJob.created_at.desc())
    )
    total = query.count()
    jobs = query.all()

    items = [
        SemJobListItem(
            job_id=str(j.id),
            status=j.status,
            file_name=j.file_name,
            file_type=j.file_type,
            progress_info=j.progress_info,
            created_at=j.created_at,
        )
        for j in jobs
    ]
    return SemJobListResponse(items=items, total=total)


@router.get("/jobs/{job_id}", response_model=SemJobStatusResponse)
def get_semantic_job(
    job_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SemJobStatusResponse:
    """Get semantic job status and semantic record count."""
    job = _get_sem_job_or_404(job_id, db, current_user.tenant_id)

    record_count = (
        db.query(SemanticRecord)
        .filter(SemanticRecord.job_id == job.id)
        .count()
    )

    return SemJobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        file_name=job.file_name,
        file_type=job.file_type,
        record_count=record_count,
        error_message=job.error_message,
        progress_info=job.progress_info,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/records", response_model=SemRecordListResponse)
def get_semantic_records(
    job_id: str,
    record_type: Optional[str] = Query(
        None, description="Filter by record type: entity, relationship, summary",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SemRecordListResponse:
    """Return paginated semantic records for a job, with optional record_type filter."""
    job = _get_sem_job_or_404(job_id, db, current_user.tenant_id)

    query = db.query(SemanticRecord).filter(SemanticRecord.job_id == job.id)

    if record_type:
        valid_types = {"entity", "relationship", "summary"}
        if record_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid record_type '{record_type}'. Must be one of: {sorted(valid_types)}",
            )
        query = query.filter(SemanticRecord.record_type == record_type)

    total = query.count()

    records = (
        query.order_by(SemanticRecord.created_at)
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = [
        SemRecordItem(
            id=str(r.id),
            record_type=r.record_type,
            content=r.content,
            confidence=r.confidence,
            created_at=r.created_at,
        )
        for r in records
    ]
    return SemRecordListResponse(items=items, total=total, page=page, size=size)
