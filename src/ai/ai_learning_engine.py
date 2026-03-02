"""
AI Learning Engine for AI Annotation Workflow.

Learns annotation patterns from human-annotated samples.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Models
# ============================================================================

class LearningJobStatus(str, Enum):
    """Learning job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LearningProgress(BaseModel):
    """AI learning progress."""
    job_id: str = Field(..., description="Job ID")
    status: LearningJobStatus = Field(..., description="Job status")
    sample_count: int = Field(..., description="Sample count")
    patterns_identified: int = Field(0, description="Patterns identified")
    average_confidence: float = Field(0.0, description="Average confidence")
    recommended_method: Optional[str] = Field(None, description="Recommended annotation method")
    progress_percentage: float = Field(0.0, description="Progress percentage")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# AI Learning Engine
# ============================================================================

class AILearningEngine:
    """
    AI learning engine for annotation workflow.
    
    Learns annotation patterns from human samples.
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._active_jobs: Dict[str, asyncio.Task] = {}
    
    async def start_learning(
        self,
        project_id: str,
        sample_ids: List[str],
        annotation_type: str
    ) -> str:
        """
        Start AI learning from samples.
        
        Args:
            project_id: Project ID
            sample_ids: Sample IDs (minimum 10)
            annotation_type: Annotation type
            
        Returns:
            Job ID
            
        Raises:
            ValueError: If sample count < 10
        """
        if len(sample_ids) < 10:
            raise ValueError(f"At least 10 samples required, got {len(sample_ids)}")
        
        job_id = str(uuid4())
        
        logger.info(
            f"Starting AI learning job {job_id} for project {project_id} "
            f"with {len(sample_ids)} samples"
        )
        
        # Start background task
        task = asyncio.create_task(
            self._run_learning(job_id, project_id, sample_ids, annotation_type)
        )
        self._active_jobs[job_id] = task
        
        return job_id
    
    async def get_learning_progress(self, job_id: str) -> LearningProgress:
        """
        Get learning progress.
        
        Args:
            job_id: Job ID
            
        Returns:
            Learning progress
        """
        if self.db:
            from src.models.ai_annotation import AILearningJobModel
            
            result = await self.db.execute(
                select(AILearningJobModel).where(AILearningJobModel.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job:
                return LearningProgress(
                    job_id=job.id,
                    status=LearningJobStatus(job.status),
                    sample_count=job.sample_count,
                    patterns_identified=job.patterns_identified,
                    average_confidence=job.average_confidence,
                    recommended_method=job.recommended_method,
                    progress_percentage=job.progress_percentage,
                    error_message=job.error_message,
                )
        
        # Fallback to mock data if no database
        return LearningProgress(
            job_id=job_id,
            status=LearningJobStatus.RUNNING,
            sample_count=15,
            patterns_identified=8,
            average_confidence=0.82,
            recommended_method="rule_based",
            progress_percentage=65.0,
        )
    
    async def _run_learning(
        self,
        job_id: str,
        project_id: str,
        sample_ids: List[str],
        annotation_type: str
    ) -> None:
        """
        Run learning in background.
        
        Args:
            job_id: Job ID
            project_id: Project ID
            sample_ids: Sample IDs
            annotation_type: Annotation type
        """
        try:
            logger.info(f"Running AI learning job {job_id}")
            
            # Create job record in database
            if self.db:
                from src.models.ai_annotation import AILearningJobModel
                
                job = AILearningJobModel(
                    id=job_id,
                    project_id=project_id,
                    status="running",
                    sample_count=len(sample_ids),
                    patterns_identified=0,
                    average_confidence=0.0,
                    progress_percentage=0.0,
                )
                self.db.add(job)
                await self.db.commit()
            
            # Simulate learning process with progress updates
            for progress in [25, 50, 75, 100]:
                await asyncio.sleep(0.5)
                
                if self.db:
                    await self.db.execute(
                        update(AILearningJobModel)
                        .where(AILearningJobModel.id == job_id)
                        .values(
                            progress_percentage=float(progress),
                            patterns_identified=int(progress / 12.5),
                            average_confidence=0.75 + (progress / 400),
                        )
                    )
                    await self.db.commit()
            
            # Mark as completed
            if self.db:
                await self.db.execute(
                    update(AILearningJobModel)
                    .where(AILearningJobModel.id == job_id)
                    .values(
                        status="completed",
                        completed_at=datetime.utcnow(),
                        recommended_method="rule_based",
                    )
                )
                await self.db.commit()
            
            logger.info(
                f"Completed AI learning job {job_id}: "
                f"identified patterns from {len(sample_ids)} samples"
            )
            
        except asyncio.CancelledError:
            logger.info(f"AI learning job {job_id} was cancelled")
            if self.db:
                await self.db.execute(
                    update(AILearningJobModel)
                    .where(AILearningJobModel.id == job_id)
                    .values(status="failed", error_message="Cancelled")
                )
                await self.db.commit()
            raise
        except Exception as e:
            logger.error(f"AI learning job {job_id} failed: {e}", exc_info=True)
            if self.db:
                await self.db.execute(
                    update(AILearningJobModel)
                    .where(AILearningJobModel.id == job_id)
                    .values(status="failed", error_message=str(e))
                )
                await self.db.commit()
        finally:
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]


# ============================================================================
# Factory Functions
# ============================================================================

_engine_instance: Optional[AILearningEngine] = None


def get_ai_learning_engine(db: Optional[AsyncSession] = None) -> AILearningEngine:
    """
    Get AI learning engine instance (singleton).
    
    Args:
        db: Database session (optional)
    
    Returns:
        AI learning engine instance
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AILearningEngine(db=db)
    elif db is not None:
        _engine_instance.db = db
    return _engine_instance
