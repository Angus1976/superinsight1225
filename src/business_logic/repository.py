"""
Business Logic Repository Classes.

Provides data access layer for business rules, patterns, and insights with support for
CRUD operations, filtering, and pagination.

Implements Requirements 5.1-5.9 for business logic service database operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import select, and_, desc, func, update, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.database.business_logic_models import (
    BusinessRuleDBModel,
    BusinessPatternDBModel,
    BusinessInsightDBModel
)
from src.i18n import get_translation

logger = logging.getLogger(__name__)


class BusinessRuleRepository:
    """
    Repository for business rules.
    
    Provides CRUD operations for business rules with support for
    filtering by project, type, and active status.
    
    Implements Requirements 5.1, 5.5, 5.7, 5.8, 5.9
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    async def find_by_project(
        self,
        project_id: str,
        tenant_id: str = "default",
        rule_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find business rules by project ID with optional filtering.
        
        Args:
            project_id: The project identifier
            tenant_id: The tenant identifier (default: "default")
            rule_type: Optional rule type filter
            active_only: If True, only return active rules
            
        Returns:
            List of business rule dictionaries
            
        Implements Requirement 5.1: Query business rules from database with filtering
        """
        try:
            query = select(BusinessRuleDBModel)
            
            conditions = [
                BusinessRuleDBModel.project_id == project_id,
                BusinessRuleDBModel.tenant_id == tenant_id
            ]
            
            if rule_type:
                conditions.append(BusinessRuleDBModel.rule_type == rule_type)
            
            if active_only:
                conditions.append(BusinessRuleDBModel.is_active == True)
            
            query = query.where(and_(*conditions))
            query = query.order_by(desc(BusinessRuleDBModel.confidence))
            
            results = self.db.execute(query).scalars().all()
            
            logger.debug(
                get_translation(
                    "business_logic.repository.rules_found",
                    default="Business rules found"
                ),
                extra={
                    "project_id": project_id,
                    "count": len(results),
                    "rule_type": rule_type,
                    "active_only": active_only
                }
            )
            
            return [result.to_dict() for result in results]
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation(
                    "business_logic.repository.rules_query_error",
                    default="Failed to query business rules"
                ),
                extra={"project_id": project_id, "error": str(e)}
            )
            raise
    
    async def save(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a business rule to the database.
        
        Args:
            rule: Dictionary containing business rule data
            
        Returns:
            The saved business rule as a dictionary
            
        Implements Requirement 5.5: Persist extracted rules to database
        """
        try:
            rule_id = rule.get('id') or str(uuid4())
            
            db_model = BusinessRuleDBModel(
                id=rule_id,
                tenant_id=rule.get('tenant_id', 'default'),
                project_id=rule.get('project_id'),
                name=rule.get('name'),
                description=rule.get('description'),
                pattern=rule.get('pattern'),
                rule_type=rule.get('rule_type'),
                confidence=rule.get('confidence', 0.0),
                frequency=rule.get('frequency', 0),
                examples=rule.get('examples', []),
                is_active=rule.get('is_active', True),
                created_at=rule.get('created_at') or datetime.utcnow(),
                updated_at=rule.get('updated_at') or datetime.utcnow()
            )
            
            self.db.add(db_model)
            self.db.commit()
            self.db.refresh(db_model)
            
            logger.info(
                get_translation(
                    "business_logic.repository.rule_saved",
                    default="Business rule saved successfully"
                ),
                extra={"rule_id": rule_id, "name": rule.get('name')}
            )
            
            return db_model.to_dict()
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.rule_save_error",
                    default="Failed to save business rule"
                ),
                extra={"error": str(e)}
            )
            raise
    
    async def update_confidence(self, rule_id: str, confidence: float) -> bool:
        """
        Update the confidence score of a business rule.
        
        Args:
            rule_id: The rule identifier
            confidence: The new confidence score (0.0 to 1.0)
            
        Returns:
            True if updated successfully, False if rule not found
            
        Implements Requirement 5.7: Update rule confidence in database
        """
        try:
            result = self.db.execute(
                update(BusinessRuleDBModel)
                .where(BusinessRuleDBModel.id == rule_id)
                .values(confidence=confidence, updated_at=datetime.utcnow())
            )
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(
                    get_translation(
                        "business_logic.repository.confidence_updated",
                        default="Rule confidence updated"
                    ),
                    extra={"rule_id": rule_id, "confidence": confidence}
                )
                return True
            
            logger.debug(
                get_translation(
                    "business_logic.repository.rule_not_found",
                    default="Rule not found for confidence update"
                ),
                extra={"rule_id": rule_id}
            )
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.confidence_update_error",
                    default="Failed to update rule confidence"
                ),
                extra={"rule_id": rule_id, "error": str(e)}
            )
            raise
    
    async def delete(self, rule_id: str) -> bool:
        """
        Delete a business rule from the database.
        
        Args:
            rule_id: The rule identifier
            
        Returns:
            True if deleted successfully, False if rule not found
            
        Implements Requirement 5.8: Delete rule from database
        """
        try:
            result = self.db.execute(
                delete(BusinessRuleDBModel)
                .where(BusinessRuleDBModel.id == rule_id)
            )
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(
                    get_translation(
                        "business_logic.repository.rule_deleted",
                        default="Business rule deleted"
                    ),
                    extra={"rule_id": rule_id}
                )
                return True
            
            logger.debug(
                get_translation(
                    "business_logic.repository.rule_not_found_delete",
                    default="Rule not found for deletion"
                ),
                extra={"rule_id": rule_id}
            )
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.rule_delete_error",
                    default="Failed to delete business rule"
                ),
                extra={"rule_id": rule_id, "error": str(e)}
            )
            raise
    
    async def toggle_active(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Toggle the active status of a business rule.
        
        Args:
            rule_id: The rule identifier
            
        Returns:
            The updated rule as a dictionary, or None if not found
            
        Implements Requirement 5.9: Update is_active field in database
        """
        try:
            # First, get the current rule
            rule = self.db.execute(
                select(BusinessRuleDBModel)
                .where(BusinessRuleDBModel.id == rule_id)
            ).scalar_one_or_none()
            
            if not rule:
                logger.debug(
                    get_translation(
                        "business_logic.repository.rule_not_found_toggle",
                        default="Rule not found for status toggle"
                    ),
                    extra={"rule_id": rule_id}
                )
                return None
            
            # Toggle the status
            new_status = not rule.is_active
            rule.is_active = new_status
            rule.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(rule)
            
            logger.info(
                get_translation(
                    "business_logic.repository.rule_status_toggled",
                    default="Rule status toggled"
                ),
                extra={"rule_id": rule_id, "is_active": new_status}
            )
            
            return rule.to_dict()
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.rule_toggle_error",
                    default="Failed to toggle rule status"
                ),
                extra={"rule_id": rule_id, "error": str(e)}
            )
            raise
    
    async def get_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a business rule by its ID.
        
        Args:
            rule_id: The rule identifier
            
        Returns:
            The rule as a dictionary, or None if not found
        """
        try:
            result = self.db.execute(
                select(BusinessRuleDBModel)
                .where(BusinessRuleDBModel.id == rule_id)
            ).scalar_one_or_none()
            
            if result:
                return result.to_dict()
            return None
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation(
                    "business_logic.repository.rule_get_error",
                    default="Failed to get business rule"
                ),
                extra={"rule_id": rule_id, "error": str(e)}
            )
            raise



class BusinessPatternRepository:
    """
    Repository for business patterns.
    
    Provides CRUD operations for business patterns with support for
    filtering by project, type, and strength.
    
    Implements Requirements 5.2, 5.4
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    async def find_by_project(
        self,
        project_id: str,
        tenant_id: str = "default",
        pattern_type: Optional[str] = None,
        min_strength: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Find business patterns by project ID with optional filtering.
        
        Args:
            project_id: The project identifier
            tenant_id: The tenant identifier (default: "default")
            pattern_type: Optional pattern type filter
            min_strength: Minimum strength threshold (default: 0.0)
            
        Returns:
            List of business pattern dictionaries
            
        Implements Requirement 5.2: Query business patterns from database with strength filtering
        """
        try:
            query = select(BusinessPatternDBModel)
            
            conditions = [
                BusinessPatternDBModel.project_id == project_id,
                BusinessPatternDBModel.tenant_id == tenant_id,
                BusinessPatternDBModel.strength >= min_strength
            ]
            
            if pattern_type:
                conditions.append(BusinessPatternDBModel.pattern_type == pattern_type)
            
            query = query.where(and_(*conditions))
            query = query.order_by(desc(BusinessPatternDBModel.strength))
            
            results = self.db.execute(query).scalars().all()
            
            logger.debug(
                get_translation(
                    "business_logic.repository.patterns_found",
                    default="Business patterns found"
                ),
                extra={
                    "project_id": project_id,
                    "count": len(results),
                    "pattern_type": pattern_type,
                    "min_strength": min_strength
                }
            )
            
            return [result.to_dict() for result in results]
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation(
                    "business_logic.repository.patterns_query_error",
                    default="Failed to query business patterns"
                ),
                extra={"project_id": project_id, "error": str(e)}
            )
            raise
    
    async def save(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a business pattern to the database.
        
        Args:
            pattern: Dictionary containing business pattern data
            
        Returns:
            The saved business pattern as a dictionary
            
        Implements Requirement 5.4: Persist pattern analysis results to database
        """
        try:
            pattern_id = pattern.get('id') or str(uuid4())
            
            db_model = BusinessPatternDBModel(
                id=pattern_id,
                tenant_id=pattern.get('tenant_id', 'default'),
                project_id=pattern.get('project_id'),
                pattern_type=pattern.get('pattern_type'),
                description=pattern.get('description'),
                strength=pattern.get('strength', 0.0),
                evidence=pattern.get('evidence', []),
                detected_at=pattern.get('detected_at') or datetime.utcnow(),
                last_seen=pattern.get('last_seen') or datetime.utcnow()
            )
            
            self.db.add(db_model)
            self.db.commit()
            self.db.refresh(db_model)
            
            logger.info(
                get_translation(
                    "business_logic.repository.pattern_saved",
                    default="Business pattern saved successfully"
                ),
                extra={"pattern_id": pattern_id, "type": pattern.get('pattern_type')}
            )
            
            return db_model.to_dict()
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.pattern_save_error",
                    default="Failed to save business pattern"
                ),
                extra={"error": str(e)}
            )
            raise
    
    async def save_batch(self, patterns: List[Dict[str, Any]]) -> int:
        """
        Save multiple business patterns to the database in a batch.
        
        Args:
            patterns: List of dictionaries containing business pattern data
            
        Returns:
            Number of patterns saved successfully
            
        Implements Requirement 5.4: Persist pattern analysis results to database (batch)
        """
        try:
            saved_count = 0
            
            for pattern in patterns:
                pattern_id = pattern.get('id') or str(uuid4())
                
                db_model = BusinessPatternDBModel(
                    id=pattern_id,
                    tenant_id=pattern.get('tenant_id', 'default'),
                    project_id=pattern.get('project_id'),
                    pattern_type=pattern.get('pattern_type'),
                    description=pattern.get('description'),
                    strength=pattern.get('strength', 0.0),
                    evidence=pattern.get('evidence', []),
                    detected_at=pattern.get('detected_at') or datetime.utcnow(),
                    last_seen=pattern.get('last_seen') or datetime.utcnow()
                )
                
                self.db.add(db_model)
                saved_count += 1
            
            self.db.commit()
            
            logger.info(
                get_translation(
                    "business_logic.repository.patterns_batch_saved",
                    default="Business patterns batch saved successfully"
                ),
                extra={"count": saved_count}
            )
            
            return saved_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.patterns_batch_save_error",
                    default="Failed to save business patterns batch"
                ),
                extra={"error": str(e)}
            )
            raise
    
    async def get_by_id(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a business pattern by its ID.
        
        Args:
            pattern_id: The pattern identifier
            
        Returns:
            The pattern as a dictionary, or None if not found
        """
        try:
            result = self.db.execute(
                select(BusinessPatternDBModel)
                .where(BusinessPatternDBModel.id == pattern_id)
            ).scalar_one_or_none()
            
            if result:
                return result.to_dict()
            return None
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation(
                    "business_logic.repository.pattern_get_error",
                    default="Failed to get business pattern"
                ),
                extra={"pattern_id": pattern_id, "error": str(e)}
            )
            raise
    
    async def delete(self, pattern_id: str) -> bool:
        """
        Delete a business pattern from the database.
        
        Args:
            pattern_id: The pattern identifier
            
        Returns:
            True if deleted successfully, False if pattern not found
        """
        try:
            result = self.db.execute(
                delete(BusinessPatternDBModel)
                .where(BusinessPatternDBModel.id == pattern_id)
            )
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(
                    get_translation(
                        "business_logic.repository.pattern_deleted",
                        default="Business pattern deleted"
                    ),
                    extra={"pattern_id": pattern_id}
                )
                return True
            
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.pattern_delete_error",
                    default="Failed to delete business pattern"
                ),
                extra={"pattern_id": pattern_id, "error": str(e)}
            )
            raise


class BusinessInsightRepository:
    """
    Repository for business insights.
    
    Provides CRUD operations for business insights with support for
    filtering by project, type, and acknowledgment status.
    
    Implements Requirements 5.3, 5.6
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    async def find_by_project(
        self,
        project_id: str,
        tenant_id: str = "default",
        insight_type: Optional[str] = None,
        unacknowledged_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find business insights by project ID with optional filtering.
        
        Args:
            project_id: The project identifier
            tenant_id: The tenant identifier (default: "default")
            insight_type: Optional insight type filter
            unacknowledged_only: If True, only return unacknowledged insights
            
        Returns:
            List of business insight dictionaries
            
        Implements Requirement 5.3: Query business insights from database
        """
        try:
            query = select(BusinessInsightDBModel)
            
            conditions = [
                BusinessInsightDBModel.project_id == project_id,
                BusinessInsightDBModel.tenant_id == tenant_id
            ]
            
            if insight_type:
                conditions.append(BusinessInsightDBModel.insight_type == insight_type)
            
            if unacknowledged_only:
                conditions.append(BusinessInsightDBModel.acknowledged_at == None)
            
            query = query.where(and_(*conditions))
            query = query.order_by(desc(BusinessInsightDBModel.impact_score))
            
            results = self.db.execute(query).scalars().all()
            
            logger.debug(
                get_translation(
                    "business_logic.repository.insights_found",
                    default="Business insights found"
                ),
                extra={
                    "project_id": project_id,
                    "count": len(results),
                    "insight_type": insight_type,
                    "unacknowledged_only": unacknowledged_only
                }
            )
            
            return [result.to_dict() for result in results]
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation(
                    "business_logic.repository.insights_query_error",
                    default="Failed to query business insights"
                ),
                extra={"project_id": project_id, "error": str(e)}
            )
            raise
    
    async def save(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a business insight to the database.
        
        Args:
            insight: Dictionary containing business insight data
            
        Returns:
            The saved business insight as a dictionary
        """
        try:
            insight_id = insight.get('id') or str(uuid4())
            
            db_model = BusinessInsightDBModel(
                id=insight_id,
                tenant_id=insight.get('tenant_id', 'default'),
                project_id=insight.get('project_id'),
                insight_type=insight.get('insight_type'),
                title=insight.get('title'),
                description=insight.get('description'),
                impact_score=insight.get('impact_score', 0.0),
                recommendations=insight.get('recommendations', []),
                data_points=insight.get('data_points', []),
                created_at=insight.get('created_at') or datetime.utcnow(),
                acknowledged_at=insight.get('acknowledged_at')
            )
            
            self.db.add(db_model)
            self.db.commit()
            self.db.refresh(db_model)
            
            logger.info(
                get_translation(
                    "business_logic.repository.insight_saved",
                    default="Business insight saved successfully"
                ),
                extra={"insight_id": insight_id, "title": insight.get('title')}
            )
            
            return db_model.to_dict()
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.insight_save_error",
                    default="Failed to save business insight"
                ),
                extra={"error": str(e)}
            )
            raise
    
    async def acknowledge(self, insight_id: str) -> bool:
        """
        Acknowledge a business insight by updating its acknowledged_at timestamp.
        
        Args:
            insight_id: The insight identifier
            
        Returns:
            True if acknowledged successfully, False if insight not found
            
        Implements Requirement 5.6: Update acknowledged_at timestamp
        """
        try:
            result = self.db.execute(
                update(BusinessInsightDBModel)
                .where(BusinessInsightDBModel.id == insight_id)
                .values(acknowledged_at=datetime.utcnow())
            )
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(
                    get_translation(
                        "business_logic.repository.insight_acknowledged",
                        default="Business insight acknowledged"
                    ),
                    extra={"insight_id": insight_id}
                )
                return True
            
            logger.debug(
                get_translation(
                    "business_logic.repository.insight_not_found_ack",
                    default="Insight not found for acknowledgment"
                ),
                extra={"insight_id": insight_id}
            )
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.insight_ack_error",
                    default="Failed to acknowledge business insight"
                ),
                extra={"insight_id": insight_id, "error": str(e)}
            )
            raise
    
    async def get_by_id(self, insight_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a business insight by its ID.
        
        Args:
            insight_id: The insight identifier
            
        Returns:
            The insight as a dictionary, or None if not found
        """
        try:
            result = self.db.execute(
                select(BusinessInsightDBModel)
                .where(BusinessInsightDBModel.id == insight_id)
            ).scalar_one_or_none()
            
            if result:
                return result.to_dict()
            return None
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation(
                    "business_logic.repository.insight_get_error",
                    default="Failed to get business insight"
                ),
                extra={"insight_id": insight_id, "error": str(e)}
            )
            raise
    
    async def delete(self, insight_id: str) -> bool:
        """
        Delete a business insight from the database.
        
        Args:
            insight_id: The insight identifier
            
        Returns:
            True if deleted successfully, False if insight not found
        """
        try:
            result = self.db.execute(
                delete(BusinessInsightDBModel)
                .where(BusinessInsightDBModel.id == insight_id)
            )
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(
                    get_translation(
                        "business_logic.repository.insight_deleted",
                        default="Business insight deleted"
                    ),
                    extra={"insight_id": insight_id}
                )
                return True
            
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                get_translation(
                    "business_logic.repository.insight_delete_error",
                    default="Failed to delete business insight"
                ),
                extra={"insight_id": insight_id, "error": str(e)}
            )
            raise
    
    async def count_unacknowledged(
        self,
        project_id: str,
        tenant_id: str = "default"
    ) -> int:
        """
        Count unacknowledged insights for a project.
        
        Args:
            project_id: The project identifier
            tenant_id: The tenant identifier (default: "default")
            
        Returns:
            Number of unacknowledged insights
        """
        try:
            result = self.db.execute(
                select(func.count(BusinessInsightDBModel.id))
                .where(and_(
                    BusinessInsightDBModel.project_id == project_id,
                    BusinessInsightDBModel.tenant_id == tenant_id,
                    BusinessInsightDBModel.acknowledged_at == None
                ))
            ).scalar()
            
            return result or 0
            
        except SQLAlchemyError as e:
            logger.error(
                get_translation(
                    "business_logic.repository.insight_count_error",
                    default="Failed to count unacknowledged insights"
                ),
                extra={"project_id": project_id, "error": str(e)}
            )
            raise
