"""
Ragas Evaluation Result Repository.

Provides data access layer for Ragas evaluation results with support for
save, retrieve, list operations with pagination and date filtering.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.database.ragas_models import RagasEvaluationResultDBModel
from src.i18n import get_translation

logger = logging.getLogger(__name__)


class EvaluationResultRepository:
    """
    Repository for Ragas evaluation results.
    
    Provides CRUD operations for evaluation results with support for
    pagination and date filtering.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    async def save(self, result: Dict[str, Any]) -> str:
        """
        Save an evaluation result to the database.
        
        Args:
            result: Dictionary containing evaluation result data
            
        Returns:
            The ID of the saved evaluation result
            
        Raises:
            ValueError: If required fields are missing
            SQLAlchemyError: If database operation fails
        """
        try:
            # Generate ID if not provided
            evaluation_id = result.get('id') or result.get('evaluation_id') or str(uuid4())
            
            # Create database model instance
            db_model = RagasEvaluationResultDBModel(
                id=evaluation_id,
                task_id=result.get('task_id'),
                annotation_ids=result.get('annotation_ids', []),
                metrics=result.get('metrics', {}),
                scores=result.get('scores', {}),
                overall_score=result.get('overall_score', 0.0),
                created_at=result.get('created_at') or result.get('evaluation_date') or datetime.utcnow(),
                extra_metadata=result.get('metadata')
            )
            
            # Add to session and commit
            self.db.add(db_model)
            self.db.commit()
            self.db.refresh(db_model)
            
            logger.info(
                get_translation("ragas.repository.save_success", default="Evaluation result saved successfully"),
                extra={"evaluation_id": evaluation_id}
            )
            
            return evaluation_id
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation("ragas.repository.save_error", default="Failed to save evaluation result"),
                extra={"error": str(e)}
            )
            raise
    
    async def get_by_id(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an evaluation result by its ID.
        
        Args:
            evaluation_id: The unique identifier of the evaluation result
            
        Returns:
            Dictionary containing the evaluation result, or None if not found
        """
        try:
            result = self.db.execute(
                select(RagasEvaluationResultDBModel).where(
                    RagasEvaluationResultDBModel.id == evaluation_id
                )
            ).scalar_one_or_none()
            
            if result:
                logger.debug(
                    get_translation("ragas.repository.get_success", default="Evaluation result retrieved"),
                    extra={"evaluation_id": evaluation_id}
                )
                return result.to_dict()
            
            logger.debug(
                get_translation("ragas.repository.not_found", default="Evaluation result not found"),
                extra={"evaluation_id": evaluation_id}
            )
            return None
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation("ragas.repository.get_error", default="Failed to retrieve evaluation result"),
                extra={"evaluation_id": evaluation_id, "error": str(e)}
            )
            raise
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List evaluation results with pagination and optional date filtering.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            start_date: Optional start date for filtering (inclusive)
            end_date: Optional end date for filtering (inclusive)
            task_id: Optional task ID for filtering
            
        Returns:
            List of evaluation result dictionaries
        """
        try:
            # Build query with filters
            query = select(RagasEvaluationResultDBModel)
            
            conditions = []
            
            if start_date:
                conditions.append(RagasEvaluationResultDBModel.created_at >= start_date)
            
            if end_date:
                conditions.append(RagasEvaluationResultDBModel.created_at <= end_date)
            
            if task_id:
                conditions.append(RagasEvaluationResultDBModel.task_id == task_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Order by created_at descending (newest first)
            query = query.order_by(desc(RagasEvaluationResultDBModel.created_at))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Execute query
            results = self.db.execute(query).scalars().all()
            
            logger.debug(
                get_translation("ragas.repository.list_success", default="Evaluation results listed"),
                extra={
                    "count": len(results),
                    "skip": skip,
                    "limit": limit,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            )
            
            return [result.to_dict() for result in results]
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation("ragas.repository.list_error", default="Failed to list evaluation results"),
                extra={"error": str(e)}
            )
            raise
    
    async def count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> int:
        """
        Count evaluation results with optional filtering.
        
        Args:
            start_date: Optional start date for filtering (inclusive)
            end_date: Optional end date for filtering (inclusive)
            task_id: Optional task ID for filtering
            
        Returns:
            Total count of matching evaluation results
        """
        try:
            from sqlalchemy import func
            
            query = select(func.count(RagasEvaluationResultDBModel.id))
            
            conditions = []
            
            if start_date:
                conditions.append(RagasEvaluationResultDBModel.created_at >= start_date)
            
            if end_date:
                conditions.append(RagasEvaluationResultDBModel.created_at <= end_date)
            
            if task_id:
                conditions.append(RagasEvaluationResultDBModel.task_id == task_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = self.db.execute(query).scalar()
            
            return result or 0
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation("ragas.repository.count_error", default="Failed to count evaluation results"),
                extra={"error": str(e)}
            )
            raise
    
    async def delete(self, evaluation_id: str) -> bool:
        """
        Delete an evaluation result by its ID.
        
        Args:
            evaluation_id: The unique identifier of the evaluation result
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            result = self.db.execute(
                select(RagasEvaluationResultDBModel).where(
                    RagasEvaluationResultDBModel.id == evaluation_id
                )
            ).scalar_one_or_none()
            
            if result:
                self.db.delete(result)
                self.db.commit()
                
                logger.info(
                    get_translation("ragas.repository.delete_success", default="Evaluation result deleted"),
                    extra={"evaluation_id": evaluation_id}
                )
                return True
            
            logger.debug(
                get_translation("ragas.repository.delete_not_found", default="Evaluation result not found for deletion"),
                extra={"evaluation_id": evaluation_id}
            )
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation("ragas.repository.delete_error", default="Failed to delete evaluation result"),
                extra={"evaluation_id": evaluation_id, "error": str(e)}
            )
            raise


# Synchronous versions for non-async contexts
class SyncEvaluationResultRepository:
    """
    Synchronous repository for Ragas evaluation results.
    
    Provides the same functionality as EvaluationResultRepository but
    with synchronous methods for use in non-async contexts.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def save(self, result: Dict[str, Any]) -> str:
        """Save an evaluation result to the database (sync version)."""
        try:
            evaluation_id = result.get('id') or result.get('evaluation_id') or str(uuid4())
            
            db_model = RagasEvaluationResultDBModel(
                id=evaluation_id,
                task_id=result.get('task_id'),
                annotation_ids=result.get('annotation_ids', []),
                metrics=result.get('metrics', {}),
                scores=result.get('scores', {}),
                overall_score=result.get('overall_score', 0.0),
                created_at=result.get('created_at') or result.get('evaluation_date') or datetime.utcnow(),
                extra_metadata=result.get('metadata')
            )
            
            self.db.add(db_model)
            self.db.commit()
            self.db.refresh(db_model)
            
            logger.info(
                get_translation("ragas.repository.save_success", default="Evaluation result saved successfully"),
                extra={"evaluation_id": evaluation_id}
            )
            
            return evaluation_id
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation("ragas.repository.save_error", default="Failed to save evaluation result"),
                extra={"error": str(e)}
            )
            raise
    
    def get_by_id(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an evaluation result by its ID (sync version)."""
        try:
            result = self.db.execute(
                select(RagasEvaluationResultDBModel).where(
                    RagasEvaluationResultDBModel.id == evaluation_id
                )
            ).scalar_one_or_none()
            
            if result:
                return result.to_dict()
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation("ragas.repository.get_error", default="Failed to retrieve evaluation result"),
                extra={"evaluation_id": evaluation_id, "error": str(e)}
            )
            raise
    
    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List evaluation results with pagination and optional date filtering (sync version)."""
        try:
            query = select(RagasEvaluationResultDBModel)
            
            conditions = []
            
            if start_date:
                conditions.append(RagasEvaluationResultDBModel.created_at >= start_date)
            
            if end_date:
                conditions.append(RagasEvaluationResultDBModel.created_at <= end_date)
            
            if task_id:
                conditions.append(RagasEvaluationResultDBModel.task_id == task_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(desc(RagasEvaluationResultDBModel.created_at))
            query = query.offset(skip).limit(limit)
            
            results = self.db.execute(query).scalars().all()
            
            return [result.to_dict() for result in results]
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation("ragas.repository.list_error", default="Failed to list evaluation results"),
                extra={"error": str(e)}
            )
            raise
