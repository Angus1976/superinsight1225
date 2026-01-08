"""
Data Desensitization API endpoints.

Provides REST API for PII detection, data masking, and compliance management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.middleware import get_current_active_user, require_role, audit_action
from src.security.models import AuditAction
from src.sync.desensitization import (
    PresidioEngine,
    DesensitizationRuleManager,
    DataClassifier,
    DesensitizationRule,
    PIIEntityType,
    MaskingStrategy,
    SensitivityLevel
)
from src.sync.desensitization.compliance_checker import ComplianceChecker

router = APIRouter(prefix="/api/desensitization", tags=["desensitization"])

# Initialize services
presidio_engine = PresidioEngine()
rule_manager = DesensitizationRuleManager()
data_classifier = DataClassifier(presidio_engine)
compliance_checker = ComplianceChecker()


# Request/Response Models

class PIIDetectionRequest(BaseModel):
    text: str = Field(..., description="Text to analyze for PII")
    entities: Optional[List[str]] = Field(None, description="Specific entity types to detect")
    language: Optional[str] = Field("en", description="Language code")
    score_threshold: float = Field(0.6, ge=0.0, le=1.0, description="Minimum confidence score")


class PIIEntityResponse(BaseModel):
    entity_type: str
    start: int
    end: int
    score: float
    text: str
    recognition_metadata: Dict[str, Any]


class PIIDetectionResponse(BaseModel):
    entities: List[PIIEntityResponse]
    processing_time_ms: float


class AnonymizationRequest(BaseModel):
    text: str = Field(..., description="Text to anonymize")
    rules: List[str] = Field(..., description="Rule IDs to apply")
    entities: Optional[List[PIIEntityResponse]] = Field(None, description="Pre-detected entities")


class AnonymizationResponse(BaseModel):
    success: bool
    original_text: str
    anonymized_text: str
    entities_found: List[PIIEntityResponse]
    rules_applied: List[str]
    processing_time_ms: float
    errors: List[str] = []


class CreateRuleRequest(BaseModel):
    name: str = Field(..., description="Rule name")
    entity_type: PIIEntityType = Field(..., description="PII entity type")
    masking_strategy: MaskingStrategy = Field(..., description="Masking strategy")
    sensitivity_level: SensitivityLevel = Field(SensitivityLevel.MEDIUM, description="Sensitivity level")
    confidence_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Confidence threshold")
    field_pattern: Optional[str] = Field(None, description="Field name pattern")
    config: Optional[Dict[str, Any]] = Field(None, description="Strategy configuration")


class RuleResponse(BaseModel):
    id: str
    name: str
    entity_type: str
    masking_strategy: str
    sensitivity_level: str
    confidence_threshold: float
    field_pattern: Optional[str]
    config: Dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class FieldClassificationRequest(BaseModel):
    field_name: str = Field(..., description="Field name")
    sample_values: List[Any] = Field(..., description="Sample values")
    max_samples: int = Field(100, ge=1, le=1000, description="Maximum samples to analyze")


class ClassificationResponse(BaseModel):
    field_name: str
    entities: List[PIIEntityResponse]
    sensitivity_level: str
    confidence_score: float
    requires_masking: bool
    suggested_rules: List[RuleResponse]


class DatasetClassificationRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset identifier")
    field_data: Dict[str, List[Any]] = Field(..., description="Field data mapping")
    max_samples_per_field: int = Field(100, ge=1, le=1000, description="Max samples per field")


class DatasetClassificationResponse(BaseModel):
    dataset_id: str
    total_fields: int
    sensitive_fields: int
    field_classifications: List[ClassificationResponse]
    overall_sensitivity: str
    compliance_score: float
    recommendations: List[str]
    created_at: datetime


class ComplianceAssessmentRequest(BaseModel):
    dataset_ids: List[str] = Field(..., description="Dataset IDs to assess")
    regulation: str = Field("GDPR", description="Regulation to assess against")


class ComplianceReportResponse(BaseModel):
    tenant_id: str
    report_id: str
    datasets_analyzed: int
    total_pii_entities: int
    masked_entities: int
    unmasked_entities: int
    compliance_percentage: float
    risk_level: str
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime


# PII Detection Endpoints

@router.post("/detect-pii", response_model=PIIDetectionResponse)
@audit_action(AuditAction.READ, "pii_detection")
async def detect_pii(
    request: PIIDetectionRequest,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Detect PII entities in text."""
    try:
        entities = presidio_engine.detect_pii(
            text=request.text,
            entities=request.entities,
            language=request.language,
            score_threshold=request.score_threshold
        )
        
        entity_responses = [
            PIIEntityResponse(
                entity_type=entity.entity_type.value,
                start=entity.start,
                end=entity.end,
                score=entity.score,
                text=entity.text,
                recognition_metadata=entity.recognition_metadata
            )
            for entity in entities
        ]
        
        return PIIDetectionResponse(
            entities=entity_responses,
            processing_time_ms=0.0  # Would be calculated in real implementation
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PII detection failed: {str(e)}"
        )


@router.post("/anonymize", response_model=AnonymizationResponse)
@audit_action(AuditAction.UPDATE, "data_anonymization")
async def anonymize_text(
    request: AnonymizationRequest,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Anonymize text using desensitization rules."""
    try:
        # Get rules for tenant
        rules = []
        for rule_id in request.rules:
            rule = rule_manager.get_rule_by_id(rule_id, current_user.tenant_id, db)
            if rule:
                rules.append(rule)
        
        if not rules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid rules found"
            )
        
        # Convert entities if provided
        entities = None
        if request.entities:
            from src.sync.desensitization.models import PIIEntity
            entities = [
                PIIEntity(
                    entity_type=PIIEntityType(e.entity_type),
                    start=e.start,
                    end=e.end,
                    score=e.score,
                    text=e.text,
                    recognition_metadata=e.recognition_metadata
                )
                for e in request.entities
            ]
        
        # Anonymize text
        result = presidio_engine.anonymize_text(
            text=request.text,
            rules=rules,
            entities=entities
        )
        
        entity_responses = [
            PIIEntityResponse(
                entity_type=entity.entity_type.value,
                start=entity.start,
                end=entity.end,
                score=entity.score,
                text=entity.text,
                recognition_metadata=entity.recognition_metadata
            )
            for entity in result.entities_found
        ]
        
        return AnonymizationResponse(
            success=result.success,
            original_text=result.original_text,
            anonymized_text=result.anonymized_text,
            entities_found=entity_responses,
            rules_applied=result.rules_applied,
            processing_time_ms=result.processing_time_ms,
            errors=result.errors
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anonymization failed: {str(e)}"
        )


# Rule Management Endpoints

@router.post("/rules", response_model=RuleResponse)
@require_role(["admin", "data_manager"])
@audit_action(AuditAction.CREATE, "desensitization_rule")
async def create_rule(
    request: CreateRuleRequest,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Create a new desensitization rule."""
    try:
        rule = rule_manager.create_rule(
            tenant_id=current_user.tenant_id,
            name=request.name,
            entity_type=request.entity_type,
            masking_strategy=request.masking_strategy,
            sensitivity_level=request.sensitivity_level,
            confidence_threshold=request.confidence_threshold,
            field_pattern=request.field_pattern,
            config=request.config,
            created_by=current_user.id,
            db=db
        )
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create rule"
            )
        
        return RuleResponse(
            id=rule.id,
            name=rule.name,
            entity_type=rule.entity_type.value,
            masking_strategy=rule.masking_strategy.value,
            sensitivity_level=rule.sensitivity_level.value,
            confidence_threshold=rule.confidence_threshold,
            field_pattern=rule.field_pattern,
            config=rule.config,
            enabled=rule.enabled,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rule creation failed: {str(e)}"
        )


@router.get("/rules", response_model=List[RuleResponse])
async def get_rules(
    entity_type: Optional[PIIEntityType] = None,
    enabled_only: bool = True,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Get desensitization rules for tenant."""
    try:
        rules = rule_manager.get_rules_for_tenant(
            tenant_id=current_user.tenant_id,
            entity_type=entity_type,
            enabled_only=enabled_only,
            db=db
        )
        
        return [
            RuleResponse(
                id=rule.id,
                name=rule.name,
                entity_type=rule.entity_type.value,
                masking_strategy=rule.masking_strategy.value,
                sensitivity_level=rule.sensitivity_level.value,
                confidence_threshold=rule.confidence_threshold,
                field_pattern=rule.field_pattern,
                config=rule.config,
                enabled=rule.enabled,
                created_at=rule.created_at,
                updated_at=rule.updated_at
            )
            for rule in rules
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rules: {str(e)}"
        )


@router.put("/rules/{rule_id}/enable")
@require_role(["admin", "data_manager"])
@audit_action(AuditAction.UPDATE, "desensitization_rule", "rule_id")
async def enable_rule(
    rule_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Enable a desensitization rule."""
    try:
        success = rule_manager.enable_rule(rule_id, current_user.tenant_id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        
        return {"message": "Rule enabled successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable rule: {str(e)}"
        )


@router.put("/rules/{rule_id}/disable")
@require_role(["admin", "data_manager"])
@audit_action(AuditAction.UPDATE, "desensitization_rule", "rule_id")
async def disable_rule(
    rule_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Disable a desensitization rule."""
    try:
        success = rule_manager.disable_rule(rule_id, current_user.tenant_id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        
        return {"message": "Rule disabled successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable rule: {str(e)}"
        )


# Data Classification Endpoints

@router.post("/classify-field", response_model=ClassificationResponse)
@audit_action(AuditAction.READ, "field_classification")
async def classify_field(
    request: FieldClassificationRequest,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Classify a data field for PII content."""
    try:
        classification = data_classifier.classify_field(
            field_name=request.field_name,
            sample_values=request.sample_values,
            max_samples=request.max_samples
        )
        
        entity_responses = [
            PIIEntityResponse(
                entity_type=entity.entity_type.value,
                start=entity.start,
                end=entity.end,
                score=entity.score,
                text=entity.text,
                recognition_metadata=entity.recognition_metadata
            )
            for entity in classification.entities
        ]
        
        suggested_rule_responses = [
            RuleResponse(
                id=rule.id,
                name=rule.name,
                entity_type=rule.entity_type.value,
                masking_strategy=rule.masking_strategy.value,
                sensitivity_level=rule.sensitivity_level.value,
                confidence_threshold=rule.confidence_threshold,
                field_pattern=rule.field_pattern,
                config=rule.config,
                enabled=rule.enabled,
                created_at=rule.created_at,
                updated_at=rule.updated_at
            )
            for rule in classification.suggested_rules
        ]
        
        return ClassificationResponse(
            field_name=classification.field_name,
            entities=entity_responses,
            sensitivity_level=classification.sensitivity_level.value,
            confidence_score=classification.confidence_score,
            requires_masking=classification.requires_masking,
            suggested_rules=suggested_rule_responses
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Field classification failed: {str(e)}"
        )


@router.post("/classify-dataset", response_model=DatasetClassificationResponse)
@audit_action(AuditAction.READ, "dataset_classification")
async def classify_dataset(
    request: DatasetClassificationRequest,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Classify an entire dataset for PII content."""
    try:
        classification = data_classifier.classify_dataset(
            dataset_id=request.dataset_id,
            field_data=request.field_data,
            max_samples_per_field=request.max_samples_per_field
        )
        
        field_classification_responses = []
        for field_classification in classification.field_classifications:
            entity_responses = [
                PIIEntityResponse(
                    entity_type=entity.entity_type.value,
                    start=entity.start,
                    end=entity.end,
                    score=entity.score,
                    text=entity.text,
                    recognition_metadata=entity.recognition_metadata
                )
                for entity in field_classification.entities
            ]
            
            suggested_rule_responses = [
                RuleResponse(
                    id=rule.id,
                    name=rule.name,
                    entity_type=rule.entity_type.value,
                    masking_strategy=rule.masking_strategy.value,
                    sensitivity_level=rule.sensitivity_level.value,
                    confidence_threshold=rule.confidence_threshold,
                    field_pattern=rule.field_pattern,
                    config=rule.config,
                    enabled=rule.enabled,
                    created_at=rule.created_at,
                    updated_at=rule.updated_at
                )
                for rule in field_classification.suggested_rules
            ]
            
            field_classification_responses.append(
                ClassificationResponse(
                    field_name=field_classification.field_name,
                    entities=entity_responses,
                    sensitivity_level=field_classification.sensitivity_level.value,
                    confidence_score=field_classification.confidence_score,
                    requires_masking=field_classification.requires_masking,
                    suggested_rules=suggested_rule_responses
                )
            )
        
        return DatasetClassificationResponse(
            dataset_id=classification.dataset_id,
            total_fields=classification.total_fields,
            sensitive_fields=classification.sensitive_fields,
            field_classifications=field_classification_responses,
            overall_sensitivity=classification.overall_sensitivity.value,
            compliance_score=classification.compliance_score,
            recommendations=classification.recommendations,
            created_at=classification.created_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset classification failed: {str(e)}"
        )


# Compliance Endpoints

@router.post("/compliance/assess", response_model=ComplianceReportResponse)
@require_role(["admin", "compliance_officer"])
@audit_action(AuditAction.READ, "compliance_assessment")
async def assess_compliance(
    request: ComplianceAssessmentRequest,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Assess compliance for datasets."""
    try:
        # In a real implementation, we would fetch dataset classifications
        # For now, we'll create a mock assessment
        from src.sync.desensitization.models import DatasetClassification
        
        dataset_classifications = []  # Would be fetched from database
        
        report = compliance_checker.assess_compliance(
            tenant_id=current_user.tenant_id,
            dataset_classifications=dataset_classifications,
            regulation=request.regulation
        )
        
        return ComplianceReportResponse(
            tenant_id=report.tenant_id,
            report_id=report.report_id,
            datasets_analyzed=report.datasets_analyzed,
            total_pii_entities=report.total_pii_entities,
            masked_entities=report.masked_entities,
            unmasked_entities=report.unmasked_entities,
            compliance_percentage=report.compliance_percentage,
            risk_level=report.risk_level.value,
            violations=report.violations,
            recommendations=report.recommendations,
            generated_at=report.generated_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance assessment failed: {str(e)}"
        )


# Configuration Endpoints

@router.get("/config/validate")
@require_role(["admin"])
async def validate_configuration(
    current_user = Depends(get_current_active_user)
):
    """Validate Presidio configuration."""
    try:
        config_result = presidio_engine.validate_configuration()
        return config_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration validation failed: {str(e)}"
        )


@router.get("/config/entities")
async def get_supported_entities(
    current_user = Depends(get_current_active_user)
):
    """Get supported PII entity types."""
    try:
        return {
            "entities": [entity.value for entity in PIIEntityType],
            "strategies": [strategy.value for strategy in MaskingStrategy],
            "sensitivity_levels": [level.value for level in SensitivityLevel]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported entities: {str(e)}"
        )