"""
Data Classification Engine for SuperInsight Platform.

Implements data classification and sensitivity management:
- Custom classification schemas
- Rule-based auto-classification
- AI-based auto-classification
- Batch operations and reporting
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from src.models.data_permission import (
    DataClassificationModel, ClassificationSchemaModel,
    SensitivityLevel, ClassificationMethod
)
from src.schemas.data_permission import (
    ClassificationSchema, ClassificationRule, ClassificationResult,
    FieldClassification, ClassificationUpdate, BatchUpdateResult,
    ClassificationReport
)

logger = logging.getLogger(__name__)


# Default classification rules
DEFAULT_CLASSIFICATION_RULES = [
    {
        "name": "email_pattern",
        "pattern": r"email|e-mail|mail",
        "category": "contact_info",
        "sensitivity_level": "confidential",
        "priority": 10
    },
    {
        "name": "phone_pattern",
        "pattern": r"phone|mobile|tel|telephone",
        "category": "contact_info",
        "sensitivity_level": "confidential",
        "priority": 10
    },
    {
        "name": "ssn_pattern",
        "pattern": r"ssn|social_security|身份证",
        "category": "pii",
        "sensitivity_level": "top_secret",
        "priority": 20
    },
    {
        "name": "credit_card_pattern",
        "pattern": r"credit_card|card_number|cvv|信用卡",
        "category": "financial",
        "sensitivity_level": "top_secret",
        "priority": 20
    },
    {
        "name": "password_pattern",
        "pattern": r"password|passwd|pwd|secret|密码",
        "category": "credentials",
        "sensitivity_level": "top_secret",
        "priority": 30
    },
    {
        "name": "address_pattern",
        "pattern": r"address|street|city|zip|postal|地址",
        "category": "contact_info",
        "sensitivity_level": "confidential",
        "priority": 10
    },
    {
        "name": "name_pattern",
        "pattern": r"first_name|last_name|full_name|姓名",
        "category": "pii",
        "sensitivity_level": "internal",
        "priority": 5
    },
    {
        "name": "salary_pattern",
        "pattern": r"salary|wage|income|compensation|薪资",
        "category": "financial",
        "sensitivity_level": "confidential",
        "priority": 15
    }
]


class DataClassificationEngine:
    """
    Data Classification Engine.
    
    Manages data classification and sensitivity levels:
    - Custom classification schemas
    - Rule-based classification
    - AI-based classification
    - Batch operations
    """
    
    def __init__(self, ai_service=None):
        self.logger = logging.getLogger(__name__)
        self._ai_service = ai_service
        self._default_rules = DEFAULT_CLASSIFICATION_RULES
    
    # ========================================================================
    # Schema Management
    # ========================================================================
    
    async def define_classification_schema(
        self,
        schema: ClassificationSchema,
        tenant_id: str,
        created_by: UUID,
        db: Session
    ) -> ClassificationSchemaModel:
        """
        Define a classification schema.
        
        Args:
            schema: Schema definition
            tenant_id: Tenant context
            created_by: User creating the schema
            db: Database session
            
        Returns:
            Created ClassificationSchemaModel
        """
        # Check for existing schema with same name
        existing = db.query(ClassificationSchemaModel).filter(
            and_(
                ClassificationSchemaModel.tenant_id == tenant_id,
                ClassificationSchemaModel.name == schema.name
            )
        ).first()
        
        if existing:
            # Update existing
            existing.description = schema.description
            existing.categories = schema.categories
            existing.rules = schema.rules
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        
        # Create new
        schema_model = ClassificationSchemaModel(
            tenant_id=tenant_id,
            name=schema.name,
            description=schema.description,
            categories=schema.categories,
            rules=schema.rules,
            created_by=created_by
        )
        
        db.add(schema_model)
        db.commit()
        db.refresh(schema_model)
        
        self.logger.info(f"Created classification schema: {schema.name}")
        return schema_model
    
    async def get_schema(
        self,
        schema_id: UUID,
        tenant_id: str,
        db: Session
    ) -> Optional[ClassificationSchemaModel]:
        """Get schema by ID."""
        return db.query(ClassificationSchemaModel).filter(
            and_(
                ClassificationSchemaModel.id == schema_id,
                ClassificationSchemaModel.tenant_id == tenant_id
            )
        ).first()
    
    async def get_default_schema(
        self,
        tenant_id: str,
        db: Session
    ) -> Optional[ClassificationSchemaModel]:
        """Get default schema for tenant."""
        return db.query(ClassificationSchemaModel).filter(
            and_(
                ClassificationSchemaModel.tenant_id == tenant_id,
                ClassificationSchemaModel.is_default == True,
                ClassificationSchemaModel.is_active == True
            )
        ).first()
    
    async def list_schemas(
        self,
        tenant_id: str,
        db: Session
    ) -> List[ClassificationSchemaModel]:
        """List all schemas for tenant."""
        return db.query(ClassificationSchemaModel).filter(
            and_(
                ClassificationSchemaModel.tenant_id == tenant_id,
                ClassificationSchemaModel.is_active == True
            )
        ).all()
    
    # ========================================================================
    # Auto Classification
    # ========================================================================
    
    async def auto_classify(
        self,
        dataset_id: str,
        tenant_id: str,
        db: Session,
        field_names: Optional[List[str]] = None,
        use_ai: bool = True,
        schema_id: Optional[UUID] = None
    ) -> ClassificationResult:
        """
        Automatically classify data fields.
        
        Args:
            dataset_id: Dataset to classify
            tenant_id: Tenant context
            db: Database session
            field_names: Optional list of specific fields to classify
            use_ai: Whether to use AI classification
            schema_id: Optional schema to use
            
        Returns:
            ClassificationResult with classifications
        """
        classifications = []
        errors = []
        
        # Get schema rules
        rules = await self._get_classification_rules(schema_id, tenant_id, db)
        
        # If no field names provided, we'd normally fetch from dataset metadata
        # For now, use provided fields or empty list
        fields_to_classify = field_names or []
        
        for field_name in fields_to_classify:
            try:
                # Try rule-based classification first
                classification = await self._classify_by_rules(field_name, rules)
                
                # If no match and AI enabled, try AI classification
                if not classification and use_ai and self._ai_service:
                    classification = await self._classify_by_ai(field_name)
                
                if classification:
                    # Save classification
                    await self._save_classification(
                        dataset_id=dataset_id,
                        field_name=field_name,
                        category=classification["category"],
                        sensitivity_level=SensitivityLevel(classification["sensitivity_level"]),
                        method=classification["method"],
                        confidence=classification.get("confidence"),
                        tenant_id=tenant_id,
                        db=db
                    )
                    
                    classifications.append(FieldClassification(
                        field_name=field_name,
                        category=classification["category"],
                        sensitivity_level=SensitivityLevel(classification["sensitivity_level"]),
                        method=classification["method"],
                        confidence_score=classification.get("confidence")
                    ))
                else:
                    # Default to public/general
                    await self._save_classification(
                        dataset_id=dataset_id,
                        field_name=field_name,
                        category="general",
                        sensitivity_level=SensitivityLevel.PUBLIC,
                        method=ClassificationMethod.RULE_BASED,
                        tenant_id=tenant_id,
                        db=db
                    )
                    
                    classifications.append(FieldClassification(
                        field_name=field_name,
                        category="general",
                        sensitivity_level=SensitivityLevel.PUBLIC,
                        method=ClassificationMethod.RULE_BASED
                    ))
                    
            except Exception as e:
                errors.append(f"Failed to classify {field_name}: {str(e)}")
        
        return ClassificationResult(
            dataset_id=dataset_id,
            total_fields=len(fields_to_classify),
            classified_count=len(classifications),
            classifications=classifications,
            errors=errors
        )
    
    async def _classify_by_rules(
        self,
        field_name: str,
        rules: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Classify field using rules."""
        field_lower = field_name.lower()
        
        # Sort rules by priority (higher first)
        sorted_rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)
        
        for rule in sorted_rules:
            pattern = rule.get("pattern", "")
            try:
                if re.search(pattern, field_lower, re.IGNORECASE):
                    return {
                        "category": rule.get("category", "general"),
                        "sensitivity_level": rule.get("sensitivity_level", "public"),
                        "method": ClassificationMethod.RULE_BASED,
                        "rule_name": rule.get("name")
                    }
            except re.error:
                continue
        
        return None
    
    async def _classify_by_ai(
        self,
        field_name: str
    ) -> Optional[Dict[str, Any]]:
        """Classify field using AI."""
        if not self._ai_service:
            return None
        
        try:
            # In production, call AI service
            # result = await self._ai_service.classify_field(field_name)
            # return {
            #     "category": result.category,
            #     "sensitivity_level": result.sensitivity_level,
            #     "method": ClassificationMethod.AI_BASED,
            #     "confidence": result.confidence
            # }
            return None
        except Exception as e:
            self.logger.warning(f"AI classification failed for {field_name}: {e}")
            return None
    
    async def _get_classification_rules(
        self,
        schema_id: Optional[UUID],
        tenant_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get classification rules from schema or defaults."""
        if schema_id:
            schema = await self.get_schema(schema_id, tenant_id, db)
            if schema and schema.rules:
                return schema.rules
        
        # Try default schema
        default_schema = await self.get_default_schema(tenant_id, db)
        if default_schema and default_schema.rules:
            return default_schema.rules
        
        # Use built-in defaults
        return self._default_rules
    
    async def _save_classification(
        self,
        dataset_id: str,
        field_name: str,
        category: str,
        sensitivity_level: SensitivityLevel,
        method: ClassificationMethod,
        tenant_id: str,
        db: Session,
        confidence: Optional[float] = None,
        rule_id: Optional[UUID] = None
    ) -> DataClassificationModel:
        """Save or update a classification."""
        existing = db.query(DataClassificationModel).filter(
            and_(
                DataClassificationModel.tenant_id == tenant_id,
                DataClassificationModel.dataset_id == dataset_id,
                DataClassificationModel.field_name == field_name
            )
        ).first()
        
        if existing:
            existing.category = category
            existing.sensitivity_level = sensitivity_level
            existing.classified_by = method
            existing.confidence_score = confidence
            existing.classification_rule_id = rule_id
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        
        classification = DataClassificationModel(
            tenant_id=tenant_id,
            dataset_id=dataset_id,
            field_name=field_name,
            category=category,
            sensitivity_level=sensitivity_level,
            classified_by=method,
            confidence_score=confidence,
            classification_rule_id=rule_id
        )
        
        db.add(classification)
        db.commit()
        db.refresh(classification)
        
        return classification
    
    # ========================================================================
    # Batch Operations
    # ========================================================================
    
    async def batch_update_classification(
        self,
        updates: List[ClassificationUpdate],
        tenant_id: str,
        verified_by: UUID,
        db: Session
    ) -> BatchUpdateResult:
        """
        Batch update classifications.
        
        Args:
            updates: List of classification updates
            tenant_id: Tenant context
            verified_by: User performing the update
            db: Database session
            
        Returns:
            BatchUpdateResult with statistics
        """
        updated_count = 0
        failed_count = 0
        errors = []
        
        for update in updates:
            try:
                existing = db.query(DataClassificationModel).filter(
                    and_(
                        DataClassificationModel.tenant_id == tenant_id,
                        DataClassificationModel.dataset_id == update.dataset_id,
                        or_(
                            DataClassificationModel.field_name == update.field_name,
                            DataClassificationModel.field_name.is_(None) if not update.field_name else False
                        )
                    )
                ).first()
                
                if existing:
                    existing.category = update.category
                    existing.sensitivity_level = update.sensitivity_level
                    existing.manually_verified = True
                    existing.verified_by = verified_by
                    existing.verified_at = datetime.utcnow()
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new classification
                    classification = DataClassificationModel(
                        tenant_id=tenant_id,
                        dataset_id=update.dataset_id,
                        field_name=update.field_name,
                        category=update.category,
                        sensitivity_level=update.sensitivity_level,
                        classified_by=ClassificationMethod.MANUAL,
                        manually_verified=True,
                        verified_by=verified_by,
                        verified_at=datetime.utcnow()
                    )
                    db.add(classification)
                    updated_count += 1
                    
            except Exception as e:
                failed_count += 1
                errors.append(f"Failed to update {update.dataset_id}/{update.field_name}: {str(e)}")
        
        db.commit()
        
        return BatchUpdateResult(
            success=failed_count == 0,
            updated_count=updated_count,
            failed_count=failed_count,
            errors=errors
        )
    
    # ========================================================================
    # Reporting
    # ========================================================================
    
    async def generate_classification_report(
        self,
        tenant_id: str,
        db: Session,
        dataset_id: Optional[str] = None
    ) -> ClassificationReport:
        """
        Generate classification report.
        
        Args:
            tenant_id: Tenant context
            db: Database session
            dataset_id: Optional specific dataset
            
        Returns:
            ClassificationReport with statistics
        """
        base_query = db.query(DataClassificationModel).filter(
            DataClassificationModel.tenant_id == tenant_id
        )
        
        if dataset_id:
            base_query = base_query.filter(
                DataClassificationModel.dataset_id == dataset_id
            )
        
        # Total counts
        total_fields = base_query.count()
        
        # Count unique datasets
        total_datasets = db.query(
            func.count(func.distinct(DataClassificationModel.dataset_id))
        ).filter(
            DataClassificationModel.tenant_id == tenant_id
        ).scalar() or 0
        
        # By sensitivity level
        by_sensitivity = {}
        for level in SensitivityLevel:
            count = base_query.filter(
                DataClassificationModel.sensitivity_level == level
            ).count()
            by_sensitivity[level.value] = count
        
        # By category
        categories = db.query(
            DataClassificationModel.category,
            func.count(DataClassificationModel.id)
        ).filter(
            DataClassificationModel.tenant_id == tenant_id
        ).group_by(DataClassificationModel.category).all()
        
        by_category = {cat: count for cat, count in categories}
        
        # By method
        by_method = {}
        for method in ClassificationMethod:
            count = base_query.filter(
                DataClassificationModel.classified_by == method
            ).count()
            by_method[method.value] = count
        
        # Unclassified (fields without classification)
        # This would require comparing with actual dataset fields
        unclassified_count = 0
        
        return ClassificationReport(
            tenant_id=tenant_id,
            generated_at=datetime.utcnow(),
            total_datasets=total_datasets,
            total_fields=total_fields,
            by_sensitivity=by_sensitivity,
            by_category=by_category,
            by_method=by_method,
            unclassified_count=unclassified_count
        )
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    async def get_classification(
        self,
        dataset_id: str,
        tenant_id: str,
        db: Session,
        field_name: Optional[str] = None
    ) -> Optional[DataClassificationModel]:
        """Get classification for a dataset/field."""
        query = db.query(DataClassificationModel).filter(
            and_(
                DataClassificationModel.tenant_id == tenant_id,
                DataClassificationModel.dataset_id == dataset_id
            )
        )
        
        if field_name:
            query = query.filter(DataClassificationModel.field_name == field_name)
        else:
            query = query.filter(DataClassificationModel.field_name.is_(None))
        
        return query.first()
    
    async def get_dataset_classifications(
        self,
        dataset_id: str,
        tenant_id: str,
        db: Session
    ) -> List[DataClassificationModel]:
        """Get all classifications for a dataset."""
        return db.query(DataClassificationModel).filter(
            and_(
                DataClassificationModel.tenant_id == tenant_id,
                DataClassificationModel.dataset_id == dataset_id
            )
        ).all()
    
    async def get_sensitive_fields(
        self,
        dataset_id: str,
        tenant_id: str,
        db: Session,
        min_sensitivity: SensitivityLevel = SensitivityLevel.CONFIDENTIAL
    ) -> List[DataClassificationModel]:
        """Get fields with sensitivity at or above threshold."""
        sensitivity_order = {
            SensitivityLevel.PUBLIC: 0,
            SensitivityLevel.INTERNAL: 1,
            SensitivityLevel.CONFIDENTIAL: 2,
            SensitivityLevel.TOP_SECRET: 3
        }
        
        min_level = sensitivity_order.get(min_sensitivity, 2)
        
        all_classifications = db.query(DataClassificationModel).filter(
            and_(
                DataClassificationModel.tenant_id == tenant_id,
                DataClassificationModel.dataset_id == dataset_id
            )
        ).all()
        
        return [
            c for c in all_classifications
            if sensitivity_order.get(c.sensitivity_level, 0) >= min_level
        ]


# Global instance
_data_classification_engine: Optional[DataClassificationEngine] = None


def get_data_classification_engine() -> DataClassificationEngine:
    """Get or create the global data classification engine instance."""
    global _data_classification_engine
    if _data_classification_engine is None:
        _data_classification_engine = DataClassificationEngine()
    return _data_classification_engine
