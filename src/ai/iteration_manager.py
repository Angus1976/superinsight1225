"""
Iteration Manager for AI Annotation Workflow.

Manages iteration records and history for the AI annotation workflow.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================

class IterationConfig(BaseModel):
    """Configuration for starting a new iteration."""
    data_source_id: str = Field(..., description="Data source ID")
    min_samples: int = Field(10, ge=1, description="Minimum samples required")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Confidence threshold")
    test_sample_count: int = Field(50, ge=1, description="Test sample count")


class IterationRecord(BaseModel):
    """Iteration record model."""
    id: str = Field(..., description="Iteration ID")
    project_id: str = Field(..., description="Project ID")
    iteration_number: int = Field(..., description="Iteration number")
    sample_count: int = Field(..., description="Sample count")
    annotation_count: int = Field(..., description="Annotation count")
    accuracy: float = Field(..., description="Accuracy")
    recall: float = Field(..., description="Recall")
    f1_score: float = Field(..., description="F1 score")
    consistency: float = Field(..., description="Consistency")
    duration_seconds: float = Field(..., description="Duration in seconds")
    learning_job_id: Optional[str] = Field(None, description="Learning job ID")
    batch_job_id: Optional[str] = Field(None, description="Batch job ID")
    created_at: datetime = Field(..., description="Created at")


# ============================================================================
# Iteration Manager
# ============================================================================

class IterationManager:
    """
    Iteration manager for AI annotation workflow.
    
    Manages iteration records and history.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: Optional[str] = None
    ):
        self.db = db
        self.tenant_id = tenant_id
    
    async def record_iteration(
        self,
        project_id: str,
        sample_count: int,
        annotation_count: int,
        quality_metrics: Dict[str, float],
        duration_seconds: float,
        learning_job_id: Optional[str] = None,
        batch_job_id: Optional[str] = None
    ) -> IterationRecord:
        """
        Record a completed iteration.
        
        Args:
            project_id: Project ID
            sample_count: Number of samples used
            annotation_count: Number of annotations created
            quality_metrics: Quality metrics (accuracy, recall, f1_score, consistency)
            duration_seconds: Duration in seconds
            learning_job_id: Learning job ID
            batch_job_id: Batch job ID
            
        Returns:
            Iteration record
        """
        # Get next iteration number
        iteration_number = await self._get_next_iteration_number(project_id)
        
        iteration_id = str(uuid4())
        
        record = IterationRecord(
            id=iteration_id,
            project_id=project_id,
            iteration_number=iteration_number,
            sample_count=sample_count,
            annotation_count=annotation_count,
            accuracy=quality_metrics.get("accuracy", 0.0),
            recall=quality_metrics.get("recall", 0.0),
            f1_score=quality_metrics.get("f1_score", 0.0),
            consistency=quality_metrics.get("consistency", 0.0),
            duration_seconds=duration_seconds,
            learning_job_id=learning_job_id,
            batch_job_id=batch_job_id,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        if self.db:
            from src.models.ai_annotation import IterationRecordModel
            
            db_record = IterationRecordModel(
                id=record.id,
                project_id=record.project_id,
                iteration_number=record.iteration_number,
                sample_count=record.sample_count,
                annotation_count=record.annotation_count,
                accuracy=record.accuracy,
                recall=record.recall,
                f1_score=record.f1_score,
                consistency=record.consistency,
                duration_seconds=record.duration_seconds,
                learning_job_id=record.learning_job_id,
                batch_job_id=record.batch_job_id,
            )
            self.db.add(db_record)
            await self.db.commit()
        
        logger.info(
            f"Recorded iteration {iteration_number} for project {project_id}: "
            f"samples={sample_count}, annotations={annotation_count}, "
            f"f1={quality_metrics.get('f1_score', 0.0):.2f}"
        )
        
        return record
    
    async def get_iteration_history(
        self,
        project_id: str,
        limit: int = 100
    ) -> List[IterationRecord]:
        """
        Get iteration history for a project.
        
        Args:
            project_id: Project ID
            limit: Maximum number of records to return
            
        Returns:
            List of iteration records, sorted by iteration number descending
        """
        if self.db:
            from src.models.ai_annotation import IterationRecordModel
            
            result = await self.db.execute(
                select(IterationRecordModel)
                .where(IterationRecordModel.project_id == project_id)
                .order_by(IterationRecordModel.iteration_number.desc())
                .limit(limit)
            )
            records = result.scalars().all()
            
            return [
                IterationRecord(
                    id=r.id,
                    project_id=r.project_id,
                    iteration_number=r.iteration_number,
                    sample_count=r.sample_count,
                    annotation_count=r.annotation_count,
                    accuracy=r.accuracy,
                    recall=r.recall,
                    f1_score=r.f1_score,
                    consistency=r.consistency,
                    duration_seconds=r.duration_seconds,
                    learning_job_id=r.learning_job_id,
                    batch_job_id=r.batch_job_id,
                    created_at=r.created_at,
                )
                for r in records
            ]
        
        # Fallback to mock data
        return [
            IterationRecord(
                id=f"iter_{i}",
                project_id=project_id,
                iteration_number=i,
                sample_count=10 + i * 5,
                annotation_count=100 + i * 50,
                accuracy=0.75 + i * 0.05,
                recall=0.70 + i * 0.05,
                f1_score=0.72 + i * 0.05,
                consistency=0.80 + i * 0.03,
                duration_seconds=300 + i * 50,
                learning_job_id=f"learn_{i}",
                batch_job_id=f"batch_{i}",
                created_at=datetime.utcnow()
            )
            for i in range(1, min(4, limit + 1))
        ]
    
    async def start_new_iteration(
        self,
        project_id: str,
        data_source_id: str,
        config: IterationConfig
    ) -> str:
        """
        Start a new iteration.
        
        Args:
            project_id: Project ID
            data_source_id: Data source ID
            config: Iteration configuration
            
        Returns:
            Iteration ID
        """
        iteration_number = await self._get_next_iteration_number(project_id)
        iteration_id = str(uuid4())
        
        logger.info(
            f"Starting iteration {iteration_number} for project {project_id} "
            f"with data source {data_source_id}"
        )
        
        # In real implementation, create iteration record in database
        # and initialize workflow state
        
        return iteration_id
    
    async def _get_next_iteration_number(self, project_id: str) -> int:
        """Get next iteration number for a project."""
        if self.db:
            from src.models.ai_annotation import IterationRecordModel
            from sqlalchemy import func
            
            result = await self.db.execute(
                select(func.max(IterationRecordModel.iteration_number))
                .where(IterationRecordModel.project_id == project_id)
            )
            max_number = result.scalar()
            return (max_number or 0) + 1
        
        # Fallback
        return 1


# ============================================================================
# Factory Functions
# ============================================================================

def get_iteration_manager(
    db: AsyncSession,
    tenant_id: Optional[str] = None
) -> IterationManager:
    """
    Get iteration manager instance.
    
    Args:
        db: Database session
        tenant_id: Tenant ID for multi-tenancy
        
    Returns:
        Iteration manager instance
    """
    return IterationManager(
        db=db,
        tenant_id=tenant_id
    )
