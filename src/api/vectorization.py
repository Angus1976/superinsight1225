"""
Vectorization API — FastAPI endpoints for AI vectorization processing.

Provides endpoints for creating vectorization jobs, querying status,
and retrieving vector records.
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
    StructuringJob,
    VectorRecord,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vectorization", tags=["Vectorization"])

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Extension → FileType mapping (reuse from structuring)
from src.api.structuring import _EXTENSION_MAP, SUPPORTED_EXTENSIONS


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class VecJobCreateResponse(BaseModel):
    """Response for POST /jobs."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    created_at: datetime
    message: str


class VecJobStatusResponse(BaseModel):
    """Response for GET /jobs/{id}."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VecJobListItem(BaseModel):
    """Single item in the job list."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    chunk_count: Optional[int] = None
    created_at: datetime


class VecJobListResponse(BaseModel):
    """Response for GET /jobs."""
    items: list[VecJobListItem]
    total: int


class VecRecordItem(BaseModel):
    """Single vector record."""
    id: str
    chunk_index: int
    chunk_text: str
    metadata: Optional[dict] = None
    created_at: datetime


class VecRecordListResponse(BaseModel):
    """Paginated response for GET /jobs/{id}/records."""
    items: list[VecRecordItem]
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


def _get_vec_job_or_404(
    job_id: str,
    db: Session,
    tenant_id: str,
) -> StructuringJob:
    """Fetch a vectorization job by id + tenant, or raise 404."""
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
            StructuringJob.processing_type == ProcessingType.VECTORIZATION.value,
        )
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vectorization job not found",
        )
    return job


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=VecJobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_vectorization_job(
    file: UploadFile = File(...),
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> VecJobCreateResponse:
    """Upload a file and create a new vectorization job.

    Accepts all supported file types. Creates a StructuringJob with
    processing_type='vectorization' and submits to the Celery pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    file_type = _get_file_type(file.filename)

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
    vec_dir = os.path.join(upload_dir, "vectorization")
    os.makedirs(vec_dir, exist_ok=True)

    import uuid as _uuid
    safe_name = f"{_uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(vec_dir, safe_name)

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except OSError as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )

    # Create DB record with processing_type=vectorization
    job = StructuringJob(
        tenant_id=current_user.tenant_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type,
        processing_type=ProcessingType.VECTORIZATION.value,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.flush()

    # Submit Celery task
    try:
        from src.services.vectorization_pipeline import run_vectorization_pipeline
        run_vectorization_pipeline.delay(str(job.id))
    except Exception as exc:
        logger.warning("Could not submit Celery task (will need manual trigger): %s", exc)

    return VecJobCreateResponse(
        job_id=str(job.id),
        status=job.status,
        file_name=job.file_name,
        file_type=job.file_type,
        created_at=job.created_at or datetime.utcnow(),
        message="Vectorization job created",
    )


@router.get("/jobs", response_model=VecJobListResponse)
def list_vectorization_jobs(
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> VecJobListResponse:
    """List all vectorization jobs for the current tenant."""
    query = (
        db.query(StructuringJob)
        .filter(
            StructuringJob.tenant_id == current_user.tenant_id,
            StructuringJob.processing_type == ProcessingType.VECTORIZATION.value,
        )
        .order_by(StructuringJob.created_at.desc())
    )
    total = query.count()
    jobs = query.all()

    items = [
        VecJobListItem(
            job_id=str(j.id),
            status=j.status,
            file_name=j.file_name,
            file_type=j.file_type,
            chunk_count=j.chunk_count,
            created_at=j.created_at,
        )
        for j in jobs
    ]
    return VecJobListResponse(items=items, total=total)


@router.get("/jobs/{job_id}", response_model=VecJobStatusResponse)
def get_vectorization_job(
    job_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> VecJobStatusResponse:
    """Get vectorization job status and vector record count."""
    job = _get_vec_job_or_404(job_id, db, current_user.tenant_id)

    return VecJobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        file_name=job.file_name,
        file_type=job.file_type,
        chunk_count=job.chunk_count,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/records", response_model=VecRecordListResponse)
def get_vector_records(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> VecRecordListResponse:
    """Return paginated vector records for a vectorization job."""
    job = _get_vec_job_or_404(job_id, db, current_user.tenant_id)

    query = db.query(VectorRecord).filter(VectorRecord.job_id == job.id)
    total = query.count()

    records = (
        query.order_by(VectorRecord.chunk_index)
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = [
        VecRecordItem(
            id=str(r.id),
            chunk_index=r.chunk_index,
            chunk_text=r.chunk_text,
            metadata=r.metadata_,
            created_at=r.created_at,
        )
        for r in records
    ]
    return VecRecordListResponse(items=items, total=total, page=page, size=size)
