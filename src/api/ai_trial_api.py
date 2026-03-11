"""
AI Trial API Router for Data Lifecycle Management.

Provides REST API endpoints for managing AI trials,
including trial creation, execution, result retrieval,
comparison, cancellation, and listing with filters.

Validates: Requirements 7.2, 7.3, 7.6, 16.1, 16.2, 16.3, 16.4, 16.5
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from src.database.connection import get_db_session
from src.services.ai_trial_service import (
    AITrialService,
    TrialConfig,
)
from src.models.data_lifecycle import TrialStatus, DataStage


router = APIRouter(prefix="/api/ai-trials", tags=["AI Trials"])

# Shared in-memory trial storage across requests
_shared_trials: Dict[str, Any] = {}


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CreateTrialRequest(BaseModel):
    """Create AI trial request."""
    name: str = Field(..., min_length=1, description="Trial name")
    data_stage: DataStage = Field(..., description="Data lifecycle stage")
    model_name: str = Field(..., min_length=1, description="AI model name")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Model parameters")
    sample_size: Optional[int] = Field(None, ge=1, description="Sample size limit")
    created_by: str = Field(..., min_length=1, description="User ID who creates the trial")


class ExecuteTrialRequest(BaseModel):
    """Execute trial request."""
    source_data: List[Dict[str, Any]] = Field(..., description="Source data for trial execution")


class CompareTrialsRequest(BaseModel):
    """Compare trials request."""
    trial_ids: List[str] = Field(..., min_length=2, description="Trial IDs to compare")


class TrialMetricsResponse(BaseModel):
    """Trial metrics response."""
    accuracy: float = Field(0.0, description="Accuracy score")
    precision: float = Field(0.0, description="Precision score")
    recall: float = Field(0.0, description="Recall score")
    f1_score: float = Field(0.0, description="F1 score")


class TrialResponse(BaseModel):
    """Trial response."""
    id: str = Field(..., description="Trial ID")
    name: str = Field(..., description="Trial name")
    data_stage: DataStage = Field(..., description="Data stage")
    model_name: str = Field(..., description="AI model name")
    parameters: Dict[str, Any] = Field(..., description="Model parameters")
    sample_size: Optional[int] = Field(None, description="Sample size limit")
    status: TrialStatus = Field(..., description="Trial status")
    created_by: str = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")


class TrialResultResponse(BaseModel):
    """Trial result response."""
    trial_id: str = Field(..., description="Trial ID")
    metrics: TrialMetricsResponse = Field(..., description="Performance metrics")
    predictions: List[Dict[str, Any]] = Field(..., description="Model predictions")
    execution_time: float = Field(..., description="Execution time in seconds")
    data_quality_score: float = Field(..., description="Data quality score (0-1)")
    completed_at: datetime = Field(..., description="Completion timestamp")


class ComparisonEntryResponse(BaseModel):
    """Single trial entry in comparison."""
    trial_id: str = Field(..., description="Trial ID")
    name: str = Field(..., description="Trial name")
    data_stage: str = Field(..., description="Data stage")
    model_name: str = Field(..., description="Model name")
    metrics: Dict[str, float] = Field(..., description="Metrics")
    execution_time: float = Field(..., description="Execution time")
    data_quality_score: float = Field(..., description="Data quality score")


class ComparisonResponse(BaseModel):
    """Trial comparison response."""
    trial_ids: List[str] = Field(..., description="Compared trial IDs")
    metrics_comparison: List[ComparisonEntryResponse] = Field(..., description="Per-trial metrics")
    best_trial_id: Optional[str] = Field(None, description="Best performing trial ID")
    summary: Dict[str, Any] = Field(..., description="Aggregate summary")


class ListTrialsResponse(BaseModel):
    """List trials response."""
    items: List[TrialResponse] = Field(..., description="List of trials")
    total: int = Field(..., description="Total number of trials")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_trial_service(
    db: DBSession = Depends(get_db_session),
) -> AITrialService:
    """Get AI trial service instance with shared trial storage."""
    service = AITrialService(db)
    service._trials = _shared_trials
    return service


# ============================================================================
# Helper Functions
# ============================================================================

def _trial_to_response(trial) -> TrialResponse:
    """Convert Trial to response model."""
    return TrialResponse(
        id=trial.id,
        name=trial.config.name,
        data_stage=trial.config.data_stage,
        model_name=trial.config.model_name,
        parameters=trial.config.parameters,
        sample_size=trial.config.sample_size,
        status=trial.status,
        created_by=trial.created_by,
        created_at=trial.created_at,
        started_at=trial.started_at,
        completed_at=trial.completed_at,
        error=trial.error,
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=TrialResponse, status_code=status.HTTP_201_CREATED)
async def create_trial(
    request: CreateTrialRequest,
    service: AITrialService = Depends(get_trial_service),
):
    """
    Create a new AI trial.

    Validates: Requirements 7.2, 16.1
    """
    try:
        config = TrialConfig(
            name=request.name,
            data_stage=request.data_stage,
            model_name=request.model_name,
            parameters=request.parameters or {},
            sample_size=request.sample_size,
        )
        trial = service.create_trial(config=config, created_by=request.created_by)
        return _trial_to_response(trial)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create trial: {str(e)}",
        )


@router.post("/{trial_id}/execute", response_model=TrialResultResponse)
async def execute_trial(
    trial_id: str,
    request: ExecuteTrialRequest,
    service: AITrialService = Depends(get_trial_service),
):
    """
    Execute an AI trial on provided source data.

    Validates: Requirements 7.3, 16.3
    """
    try:
        result = service.execute_trial(
            trial_id=trial_id, source_data=request.source_data
        )
        return TrialResultResponse(
            trial_id=result.trial_id,
            metrics=TrialMetricsResponse(
                accuracy=result.metrics.get("accuracy", 0.0),
                precision=result.metrics.get("precision", 0.0),
                recall=result.metrics.get("recall", 0.0),
                f1_score=result.metrics.get("f1_score", 0.0),
            ),
            predictions=result.predictions,
            execution_time=result.execution_time,
            data_quality_score=result.data_quality_score,
            completed_at=result.completed_at,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute trial: {str(e)}",
        )


@router.get("/{trial_id}/results", response_model=TrialResultResponse)
async def get_trial_results(
    trial_id: str,
    service: AITrialService = Depends(get_trial_service),
):
    """
    Get results of a completed trial.

    Validates: Requirements 7.6, 16.4
    """
    try:
        result = service.get_trial_result(trial_id)
        return TrialResultResponse(
            trial_id=result.trial_id,
            metrics=TrialMetricsResponse(
                accuracy=result.metrics.get("accuracy", 0.0),
                precision=result.metrics.get("precision", 0.0),
                recall=result.metrics.get("recall", 0.0),
                f1_score=result.metrics.get("f1_score", 0.0),
            ),
            predictions=result.predictions,
            execution_time=result.execution_time,
            data_quality_score=result.data_quality_score,
            completed_at=result.completed_at,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trial results: {str(e)}",
        )


@router.post("/compare", response_model=ComparisonResponse)
async def compare_trials(
    request: CompareTrialsRequest,
    service: AITrialService = Depends(get_trial_service),
):
    """
    Compare multiple completed trials.

    Validates: Requirements 16.5
    """
    try:
        result = service.compare_trials(request.trial_ids)
        entries = [
            ComparisonEntryResponse(**entry)
            for entry in result.metrics_comparison
        ]
        return ComparisonResponse(
            trial_ids=result.trial_ids,
            metrics_comparison=entries,
            best_trial_id=result.best_trial_id,
            summary=result.summary,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare trials: {str(e)}",
        )


@router.post("/{trial_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_trial(
    trial_id: str,
    service: AITrialService = Depends(get_trial_service),
):
    """
    Cancel a created or running trial.

    Validates: Requirements 16.3
    """
    try:
        service.cancel_trial(trial_id)
        return {
            "message": "Trial cancelled successfully",
            "trial_id": trial_id,
        }
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel trial: {str(e)}",
        )


@router.get("", response_model=ListTrialsResponse)
async def list_trials(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[TrialStatus] = Query(None, description="Filter by trial status"),
    data_stage: Optional[DataStage] = Query(None, description="Filter by data stage"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    service: AITrialService = Depends(get_trial_service),
):
    """
    List trials with pagination and filters.

    Validates: Requirements 16.1, 16.2
    """
    try:
        all_trials = service.list_trials()

        # Apply filters
        if status_filter is not None:
            all_trials = [t for t in all_trials if t.status == status_filter]
        if data_stage is not None:
            all_trials = [
                t for t in all_trials
                if t.config.data_stage == data_stage
            ]
        if model_name is not None:
            all_trials = [
                t for t in all_trials
                if t.config.model_name == model_name
            ]

        # Sort by created_at descending (newest first)
        all_trials.sort(
            key=lambda t: t.created_at or datetime.min, reverse=True
        )

        total = len(all_trials)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        offset = (page - 1) * page_size
        page_items = all_trials[offset: offset + page_size]

        return ListTrialsResponse(
            items=[_trial_to_response(t) for t in page_items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list trials: {str(e)}",
        )
