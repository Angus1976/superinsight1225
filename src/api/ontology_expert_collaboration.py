"""
Ontology Expert Collaboration API Routes (本体专家协作 API)

RESTful API endpoints for ontology expert collaboration, including:
- Expert Management (专家管理)
- Template Management (模板管理)
- Collaboration Sessions (协作会话)
- Approval Workflows (审批流程)
- Validation Rules (验证规则)
- Impact Analysis (影响分析)
- I18n Support (国际化支持)

All endpoints require authentication and enforce tenant isolation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

# Import collaboration services
from src.collaboration.expert_service import (
    ExpertService,
    ExpertProfileCreate,
    ExpertProfileUpdate,
    ExpertiseArea,
    CertificationType,
    ExpertStatus,
    AvailabilityLevel,
)
from src.collaboration.template_service import (
    TemplateService,
    TemplateCustomization,
)
from src.collaboration.collaboration_service import (
    CollaborationService,
    ConflictResolution,
)
from src.collaboration.approval_service import (
    ApprovalService,
    ApprovalType,
)
from src.collaboration.validation_service import (
    ValidationService,
)
from src.collaboration.impact_analysis_service import (
    ImpactAnalysisService,
    ChangeImpactLevel,
    MigrationComplexity,
)
from src.collaboration.ontology_i18n_service import (
    OntologyI18nService,
    Language,
)
from src.collaboration.knowledge_contribution_service import (
    KnowledgeContributionService,
    ContributionType,
    DocumentType,
)
from src.collaboration.compliance_template_service import (
    ComplianceTemplateService,
    ComplianceRegulation as RegulationType,
)
from src.collaboration.best_practice_service import (
    BestPracticeService,
)
from src.collaboration.audit_service import (
    AuditService,
    AuditLogFilter,
    ChangeType,
)

# Create router with prefix and tags
router = APIRouter(
    prefix="/ontology-collaboration",
    tags=["ontology-expert-collaboration"]
)


# =============================================================================
# Service Instances (Singleton pattern for in-memory storage)
# =============================================================================

# Initialize services (in production, use dependency injection)
_expert_service: Optional[ExpertService] = None
_template_service: Optional[TemplateService] = None
_collaboration_service: Optional[CollaborationService] = None
_approval_service: Optional[ApprovalService] = None
_validation_service: Optional[ValidationService] = None
_impact_analysis_service: Optional[ImpactAnalysisService] = None
_i18n_service: Optional[OntologyI18nService] = None
_contribution_service: Optional[KnowledgeContributionService] = None
_compliance_service: Optional[ComplianceTemplateService] = None
_best_practice_service: Optional[BestPracticeService] = None
_audit_service: Optional[AuditService] = None


def get_expert_service() -> ExpertService:
    """Get or create ExpertService instance."""
    global _expert_service
    if _expert_service is None:
        _expert_service = ExpertService()
    return _expert_service


def get_template_service() -> TemplateService:
    """Get or create TemplateService instance."""
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service


def get_collaboration_service() -> CollaborationService:
    """Get or create CollaborationService instance."""
    global _collaboration_service
    if _collaboration_service is None:
        _collaboration_service = CollaborationService()
    return _collaboration_service


def get_approval_service() -> ApprovalService:
    """Get or create ApprovalService instance."""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service


def get_validation_service() -> ValidationService:
    """Get or create ValidationService instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service


def get_impact_analysis_service() -> ImpactAnalysisService:
    """Get or create ImpactAnalysisService instance."""
    global _impact_analysis_service
    if _impact_analysis_service is None:
        _impact_analysis_service = ImpactAnalysisService()
    return _impact_analysis_service


def get_i18n_service() -> OntologyI18nService:
    """Get or create OntologyI18nService instance."""
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = OntologyI18nService()
    return _i18n_service


def get_contribution_service() -> KnowledgeContributionService:
    """Get or create KnowledgeContributionService instance."""
    global _contribution_service
    if _contribution_service is None:
        _contribution_service = KnowledgeContributionService()
    return _contribution_service


def get_compliance_service() -> ComplianceTemplateService:
    """Get or create ComplianceTemplateService instance."""
    global _compliance_service
    if _compliance_service is None:
        _compliance_service = ComplianceTemplateService()
    return _compliance_service


def get_best_practice_service() -> BestPracticeService:
    """Get or create BestPracticeService instance."""
    global _best_practice_service
    if _best_practice_service is None:
        _best_practice_service = BestPracticeService()
    return _best_practice_service


def get_audit_service() -> AuditService:
    """Get or create AuditService instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


# =============================================================================
# Request/Response Schemas
# =============================================================================

# Expert Management Schemas
class ExpertCreateRequest(BaseModel):
    """Request to create an expert profile."""
    name: str = Field(..., min_length=1, max_length=100, description="专家姓名")
    email: EmailStr = Field(..., description="专家邮箱")
    expertise_areas: List[str] = Field(..., min_length=1, description="专业领域列表")
    certifications: List[str] = Field(default_factory=list, description="认证列表")
    languages: List[str] = Field(default_factory=lambda: ["zh-CN"], description="语言偏好")
    department: Optional[str] = Field(None, description="部门")
    title: Optional[str] = Field(None, description="职位")
    bio: Optional[str] = Field(None, description="简介")


class ExpertUpdateRequest(BaseModel):
    """Request to update an expert profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    expertise_areas: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    department: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    status: Optional[str] = None
    availability: Optional[str] = None


class ExpertResponse(BaseModel):
    """Response containing expert profile data."""
    id: str
    name: str
    email: str
    expertise_areas: List[str]
    certifications: List[str]
    languages: List[str]
    department: Optional[str]
    title: Optional[str]
    bio: Optional[str]
    status: str
    availability: str
    contribution_score: float
    created_at: datetime
    updated_at: datetime


class ExpertRecommendationResponse(BaseModel):
    """Response containing expert recommendations."""
    experts: List[Dict[str, Any]]
    ontology_area: str
    total_count: int


class ExpertMetricsResponse(BaseModel):
    """Response containing expert contribution metrics."""
    expert_id: str
    total_contributions: int
    accepted_contributions: int
    rejected_contributions: int
    quality_score: float
    recognition_score: float
    acceptance_rate: float


# Template Management Schemas
class TemplateCreateRequest(BaseModel):
    """Request to create a template."""
    name: str = Field(..., min_length=1, max_length=200)
    industry: str = Field(..., description="行业类型")
    description: Optional[str] = None
    entity_types: List[Dict[str, Any]] = Field(default_factory=list)
    relation_types: List[Dict[str, Any]] = Field(default_factory=list)
    validation_rules: List[Dict[str, Any]] = Field(default_factory=list)


class TemplateInstantiateRequest(BaseModel):
    """Request to instantiate a template."""
    project_id: str = Field(..., description="项目ID")
    customizations: Optional[Dict[str, Any]] = None


class TemplateCustomizeRequest(BaseModel):
    """Request to customize a template."""
    add_entity_types: List[Dict[str, Any]] = Field(default_factory=list)
    remove_entity_types: List[str] = Field(default_factory=list)
    add_relation_types: List[Dict[str, Any]] = Field(default_factory=list)
    remove_relation_types: List[str] = Field(default_factory=list)


# Collaboration Schemas
class SessionCreateRequest(BaseModel):
    """Request to create a collaboration session."""
    ontology_id: str = Field(..., description="本体ID")


class SessionJoinRequest(BaseModel):
    """Request to join a collaboration session."""
    expert_id: str = Field(..., description="专家ID")


class ElementLockRequest(BaseModel):
    """Request to lock an element."""
    element_id: str = Field(..., description="元素ID")
    expert_id: str = Field(..., description="专家ID")


class ChangeRequestCreate(BaseModel):
    """Request to create a change request."""
    ontology_id: str = Field(..., description="本体ID")
    change_type: str = Field(..., description="变更类型: ADD, MODIFY, DELETE")
    target_element: str = Field(..., description="目标元素")
    proposed_changes: Dict[str, Any] = Field(..., description="提议的变更")
    description: Optional[str] = None


class ConflictResolveRequest(BaseModel):
    """Request to resolve a conflict."""
    resolution: str = Field(..., description="解决方案: accept_theirs, accept_mine, manual_merge")
    merged_content: Optional[Dict[str, Any]] = None


# Approval Workflow Schemas
class ApprovalChainCreateRequest(BaseModel):
    """Request to create an approval chain."""
    name: str = Field(..., min_length=1, max_length=200)
    ontology_area: str = Field(..., description="本体领域")
    levels: List[Dict[str, Any]] = Field(..., min_length=1, max_length=5)
    approval_type: str = Field(default="SEQUENTIAL", description="审批类型: PARALLEL, SEQUENTIAL")


class ApprovalActionRequest(BaseModel):
    """Request to perform an approval action."""
    expert_id: str = Field(..., description="专家ID")
    action: str = Field(..., description="操作: approve, reject, request_changes")
    reason: Optional[str] = None
    feedback: Optional[str] = None


# Validation Schemas
class ValidationRuleCreateRequest(BaseModel):
    """Request to create a validation rule."""
    name: str = Field(..., min_length=1, max_length=200)
    rule_type: str = Field(..., description="规则类型")
    target_entity_type: str = Field(..., description="目标实体类型")
    target_field: Optional[str] = None
    validation_logic: str = Field(..., description="验证逻辑")
    error_message_key: str = Field(..., description="错误消息i18n键")
    region: str = Field(default="CN", description="地区: CN, HK, TW, INTL")
    industry: Optional[str] = None


class ValidationRequest(BaseModel):
    """Request to validate an entity."""
    entity: Dict[str, Any] = Field(..., description="要验证的实体")
    entity_type: str = Field(..., description="实体类型")
    region: str = Field(default="CN", description="地区")
    industry: Optional[str] = None


# Impact Analysis Schemas
class ImpactAnalyzeRequest(BaseModel):
    """Request to analyze change impact."""
    ontology_id: str = Field(..., description="本体ID")
    element_id: str = Field(..., description="元素ID")
    change_type: str = Field(..., description="变更类型: ADD, MODIFY, DELETE")
    proposed_changes: Optional[Dict[str, Any]] = None


# I18n Schemas
class TranslationAddRequest(BaseModel):
    """Request to add a translation."""
    language: str = Field(..., description="语言代码: zh-CN, en-US, etc.")
    name: str = Field(..., description="名称翻译")
    description: Optional[str] = None
    help_text: Optional[str] = None


class TranslationImportRequest(BaseModel):
    """Request to import translations."""
    translations: Dict[str, Dict[str, str]] = Field(..., description="翻译数据")
    format: str = Field(default="json", description="格式: json, csv")


# =============================================================================
# Expert Management API Endpoints (Task 15.1)
# =============================================================================

@router.post("/experts", response_model=ExpertResponse, status_code=status.HTTP_201_CREATED)
async def create_expert(
    request: ExpertCreateRequest,
    service: ExpertService = Depends(get_expert_service)
):
    """
    创建专家档案 (Create expert profile)
    
    Creates a new expert profile with the specified information.
    Validates expertise areas against defined industry categories.
    
    Requirements: 1.1, 9.1
    """
    try:
        # Convert string expertise areas to enum
        expertise_areas = [ExpertiseArea(area) for area in request.expertise_areas]
        certifications = [CertificationType(cert) for cert in request.certifications] if request.certifications else []
        
        profile = ExpertProfileCreate(
            name=request.name,
            email=request.email,
            expertise_areas=expertise_areas,
            certifications=certifications,
            languages=request.languages,
            department=request.department,
            title=request.title,
            bio=request.bio,
        )
        
        result = await service.create_expert(profile)
        
        return ExpertResponse(
            id=str(result.id),
            name=result.name,
            email=result.email,
            expertise_areas=[area.value for area in result.expertise_areas],
            certifications=[cert.value for cert in result.certifications],
            languages=result.languages,
            department=result.department,
            title=result.title,
            bio=result.bio,
            status=result.status.value,
            availability=result.availability.value,
            contribution_score=result.contribution_metrics.recognition_score,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/experts/{expert_id}", response_model=ExpertResponse)
async def get_expert(
    expert_id: str,
    service: ExpertService = Depends(get_expert_service)
):
    """
    获取专家详情 (Get expert details)
    
    Retrieves the expert profile by ID.
    
    Requirements: 1.1
    """
    try:
        result = await service.get_expert(expert_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expert not found")
        
        return ExpertResponse(
            id=str(result.id),
            name=result.name,
            email=result.email,
            expertise_areas=[area.value for area in result.expertise_areas],
            certifications=[cert.value for cert in result.certifications],
            languages=result.languages,
            department=result.department,
            title=result.title,
            bio=result.bio,
            status=result.status.value,
            availability=result.availability.value,
            contribution_score=result.contribution_metrics.recognition_score,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/experts/{expert_id}", response_model=ExpertResponse)
async def update_expert(
    expert_id: str,
    request: ExpertUpdateRequest,
    service: ExpertService = Depends(get_expert_service)
):
    """
    更新专家档案 (Update expert profile)
    
    Updates the expert profile with the specified changes.
    
    Requirements: 1.1
    """
    try:
        # Convert string values to enums where needed
        expertise_areas = None
        if request.expertise_areas:
            expertise_areas = [ExpertiseArea(area) for area in request.expertise_areas]
        
        certifications = None
        if request.certifications:
            certifications = [CertificationType(cert) for cert in request.certifications]
        
        expert_status = None
        if request.status:
            expert_status = ExpertStatus(request.status)
        
        availability = None
        if request.availability:
            availability = AvailabilityLevel(request.availability)
        
        update = ExpertProfileUpdate(
            name=request.name,
            expertise_areas=expertise_areas,
            certifications=certifications,
            languages=request.languages,
            department=request.department,
            title=request.title,
            bio=request.bio,
            status=expert_status,
            availability=availability,
        )
        
        result = await service.update_expert(expert_id, update)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expert not found")
        
        return ExpertResponse(
            id=str(result.id),
            name=result.name,
            email=result.email,
            expertise_areas=[area.value for area in result.expertise_areas],
            certifications=[cert.value for cert in result.certifications],
            languages=result.languages,
            department=result.department,
            title=result.title,
            bio=result.bio,
            status=result.status.value,
            availability=result.availability.value,
            contribution_score=result.contribution_metrics.recognition_score,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/experts/recommend", response_model=ExpertRecommendationResponse)
async def recommend_experts(
    ontology_area: str = Query(..., description="本体领域"),
    limit: int = Query(default=5, ge=1, le=20, description="返回数量限制"),
    service: ExpertService = Depends(get_expert_service)
):
    """
    推荐专家 (Recommend experts)
    
    Recommends experts based on expertise area matching and past contribution quality.
    
    Requirements: 9.1, 9.2
    """
    try:
        experts = await service.recommend_experts(ontology_area, limit=limit)
        
        return ExpertRecommendationResponse(
            experts=[
                {
                    "id": str(e.id),
                    "name": e.name,
                    "expertise_areas": [area.value for area in e.expertise_areas],
                    "contribution_score": e.contribution_metrics.recognition_score,
                    "availability": e.availability.value,
                    "match_score": getattr(e, "match_score", 0.0),
                }
                for e in experts
            ],
            ontology_area=ontology_area,
            total_count=len(experts),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/experts/{expert_id}/metrics", response_model=ExpertMetricsResponse)
async def get_expert_metrics(
    expert_id: str,
    service: ExpertService = Depends(get_expert_service)
):
    """
    获取专家贡献指标 (Get expert contribution metrics)
    
    Retrieves the contribution metrics for an expert.
    
    Requirements: 6.5
    """
    try:
        metrics = await service.get_contribution_metrics(expert_id)
        if metrics is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expert not found")
        
        return ExpertMetricsResponse(
            expert_id=expert_id,
            total_contributions=metrics.total_contributions,
            accepted_contributions=metrics.accepted_contributions,
            rejected_contributions=metrics.rejected_contributions,
            quality_score=metrics.quality_score,
            recognition_score=metrics.recognition_score,
            acceptance_rate=metrics.acceptance_rate,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/experts")
async def list_experts(
    expertise_area: Optional[str] = Query(None, description="按专业领域筛选"),
    language: Optional[str] = Query(None, description="按语言筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=20, ge=1, le=100, description="分页限制"),
    service: ExpertService = Depends(get_expert_service)
):
    """
    列出专家 (List experts)
    
    Lists experts with optional filtering by expertise area, language, and status.
    
    Requirements: 9.4
    """
    try:
        # Build filter criteria
        filters = {}
        if expertise_area:
            filters["expertise_area"] = ExpertiseArea(expertise_area)
        if language:
            filters["language"] = language
        if status:
            filters["status"] = ExpertStatus(status)
        
        experts = await service.search_experts(filters, offset=offset, limit=limit)
        
        return {
            "experts": [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "email": e.email,
                    "expertise_areas": [area.value for area in e.expertise_areas],
                    "status": e.status.value,
                    "availability": e.availability.value,
                }
                for e in experts
            ],
            "offset": offset,
            "limit": limit,
            "total": len(experts),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Template Management API Endpoints (Task 15.2)
# =============================================================================

@router.get("/templates")
async def list_templates(
    industry: Optional[str] = Query(None, description="按行业筛选"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=20, ge=1, le=100, description="分页限制"),
    service: TemplateService = Depends(get_template_service)
):
    """
    列出模板 (List templates)
    
    Lists available ontology templates with optional industry filtering.
    
    Requirements: 2.1
    """
    try:
        templates = await service.list_templates(industry=industry)
        
        # Apply pagination
        paginated = templates[offset:offset + limit]
        
        return {
            "templates": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "industry": t.industry,
                    "version": t.version,
                    "description": t.description,
                    "usage_count": t.usage_count,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in paginated
            ],
            "offset": offset,
            "limit": limit,
            "total": len(templates),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service)
):
    """
    获取模板详情 (Get template details)
    
    Retrieves the template by ID with all entity types, relation types, and validation rules.
    
    Requirements: 2.1, 2.4
    """
    try:
        template = await service.get_template(template_id)
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        
        return {
            "id": str(template.id),
            "name": template.name,
            "industry": template.industry,
            "version": template.version,
            "description": template.description,
            "entity_types": template.entity_types,
            "relation_types": template.relation_types,
            "validation_rules": template.validation_rules,
            "usage_count": template.usage_count,
            "parent_template_id": str(template.parent_template_id) if template.parent_template_id else None,
            "lineage": template.lineage,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/templates/{template_id}/instantiate", status_code=status.HTTP_201_CREATED)
async def instantiate_template(
    template_id: str,
    request: TemplateInstantiateRequest,
    service: TemplateService = Depends(get_template_service)
):
    """
    实例化模板 (Instantiate template)
    
    Creates an ontology instance from a template with optional customizations.
    
    Requirements: 2.2
    """
    try:
        result = await service.instantiate_template(
            template_id=template_id,
            project_id=request.project_id,
            customizations=request.customizations,
        )
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        
        return {
            "instance_id": str(result.get("instance_id")),
            "template_id": template_id,
            "project_id": request.project_id,
            "entity_types": result.get("entity_types", []),
            "relation_types": result.get("relation_types", []),
            "validation_rules": result.get("validation_rules", []),
            "created_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/templates/{template_id}/customize", status_code=status.HTTP_201_CREATED)
async def customize_template(
    template_id: str,
    request: TemplateCustomizeRequest,
    service: TemplateService = Depends(get_template_service)
):
    """
    定制模板 (Customize template)
    
    Creates a customized template derived from the original.
    
    Requirements: 12.1, 12.2, 12.3
    """
    try:
        customization = TemplateCustomization(
            add_entity_types=request.add_entity_types,
            remove_entity_types=request.remove_entity_types,
            add_relation_types=request.add_relation_types,
            remove_relation_types=request.remove_relation_types,
        )
        
        result = await service.customize_template(template_id, customization)
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        
        return {
            "id": str(result.id),
            "name": result.name,
            "industry": result.industry,
            "version": result.version,
            "parent_template_id": str(result.parent_template_id) if result.parent_template_id else None,
            "lineage": result.lineage,
            "customization_log": result.customization_log,
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/templates/import", status_code=status.HTTP_201_CREATED)
async def import_template(
    template_data: Dict[str, Any],
    format: str = Query(default="json", description="格式: json, yaml"),
    service: TemplateService = Depends(get_template_service)
):
    """
    导入模板 (Import template)
    
    Imports a template from JSON or YAML format.
    
    Requirements: 12.4
    """
    try:
        result = await service.import_template(template_data, format=format)
        
        return {
            "id": str(result.id),
            "name": result.name,
            "industry": result.industry,
            "version": result.version,
            "imported_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/templates/{template_id}/export")
async def export_template(
    template_id: str,
    format: str = Query(default="json", description="格式: json, yaml"),
    service: TemplateService = Depends(get_template_service)
):
    """
    导出模板 (Export template)
    
    Exports a template to JSON or YAML format.
    
    Requirements: 12.4
    """
    try:
        result = await service.export_template(template_id, format=format)
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Collaboration API Endpoints (Task 15.3)
# =============================================================================

@router.post("/collaboration/sessions", status_code=status.HTTP_201_CREATED)
async def create_collaboration_session(
    request: SessionCreateRequest,
    expert_id: str = Query(..., description="创建者专家ID"),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    创建协作会话 (Create collaboration session)
    
    Creates a new collaboration session for an ontology.
    
    Requirements: 7.1
    """
    try:
        session = await service.create_session(
            ontology_id=request.ontology_id,
            expert_id=expert_id,
        )
        
        return {
            "session_id": str(session.id),
            "ontology_id": session.ontology_id,
            "participants": session.participants,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/collaboration/sessions/{session_id}/join")
async def join_collaboration_session(
    session_id: str,
    request: SessionJoinRequest,
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    加入协作会话 (Join collaboration session)
    
    Joins an existing collaboration session.
    
    Requirements: 7.1
    """
    try:
        session = await service.join_session(session_id, request.expert_id)
        
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
        return {
            "session_id": str(session.id),
            "participants": session.participants,
            "active_locks": session.active_locks,
            "joined_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/collaboration/sessions/{session_id}/leave")
async def leave_collaboration_session(
    session_id: str,
    expert_id: str = Query(..., description="专家ID"),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    离开协作会话 (Leave collaboration session)
    
    Leaves a collaboration session and releases any held locks.
    
    Requirements: 7.1
    """
    try:
        result = await service.leave_session(session_id, expert_id)
        
        return {
            "success": result,
            "session_id": session_id,
            "left_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/collaboration/sessions/{session_id}/lock")
async def lock_element(
    session_id: str,
    request: ElementLockRequest,
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    锁定元素 (Lock element)
    
    Locks an ontology element for exclusive editing.
    
    Requirements: 7.4
    """
    try:
        lock = await service.lock_element(
            session_id=session_id,
            element_id=request.element_id,
            expert_id=request.expert_id,
        )
        
        if lock is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Element is already locked by another user"
            )
        
        return {
            "element_id": lock.element_id,
            "locked_by": lock.locked_by,
            "locked_at": lock.locked_at.isoformat() if lock.locked_at else None,
            "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/collaboration/sessions/{session_id}/lock/{element_id}")
async def unlock_element(
    session_id: str,
    element_id: str,
    expert_id: str = Query(..., description="专家ID"),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    解锁元素 (Unlock element)
    
    Releases the lock on an ontology element.
    
    Requirements: 7.4
    """
    try:
        result = await service.unlock_element(
            session_id=session_id,
            element_id=element_id,
            expert_id=expert_id,
        )
        
        return {
            "success": result,
            "element_id": element_id,
            "unlocked_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/collaboration/change-requests", status_code=status.HTTP_201_CREATED)
async def create_change_request(
    request: ChangeRequestCreate,
    requester_id: str = Query(..., description="请求者ID"),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    创建变更请求 (Create change request)
    
    Creates a new change request for ontology modification.
    
    Requirements: 4.1
    """
    try:
        change_request = await service.create_change_request(
            ontology_id=request.ontology_id,
            requester_id=requester_id,
            change_type=request.change_type,
            target_element=request.target_element,
            proposed_changes=request.proposed_changes,
            description=request.description,
        )
        
        return {
            "id": str(change_request.id),
            "ontology_id": change_request.ontology_id,
            "requester_id": change_request.requester_id,
            "change_type": change_request.change_type,
            "target_element": change_request.target_element,
            "status": change_request.status,
            "created_at": change_request.created_at.isoformat() if change_request.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/collaboration/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    request: ConflictResolveRequest,
    expert_id: str = Query(..., description="解决者专家ID"),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    解决冲突 (Resolve conflict)
    
    Resolves an edit conflict with the specified resolution strategy.
    
    Requirements: 1.4, 7.3
    """
    try:
        resolution = ConflictResolution(request.resolution)
        
        result = await service.resolve_conflict(
            conflict_id=conflict_id,
            expert_id=expert_id,
            resolution=resolution,
            merged_content=request.merged_content,
        )
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
        
        return {
            "conflict_id": conflict_id,
            "resolution": request.resolution,
            "resolved_by": expert_id,
            "resolved_at": datetime.utcnow().isoformat(),
            "new_version": result.get("new_version"),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/collaboration/sessions/{session_id}/versions")
async def get_version_history(
    session_id: str,
    element_id: Optional[str] = Query(None, description="元素ID"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    获取版本历史 (Get version history)
    
    Retrieves the version history for a collaboration session or specific element.
    
    Requirements: 7.5
    """
    try:
        versions = await service.get_version_history(
            session_id=session_id,
            element_id=element_id,
            limit=limit,
        )
        
        return {
            "versions": versions,
            "session_id": session_id,
            "element_id": element_id,
            "total": len(versions),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Approval Workflow API Endpoints (Task 15.4)
# =============================================================================

@router.post("/workflow/approval-chains", status_code=status.HTTP_201_CREATED)
async def create_approval_chain(
    request: ApprovalChainCreateRequest,
    created_by: str = Query(..., description="创建者ID"),
    service: ApprovalService = Depends(get_approval_service)
):
    """
    创建审批链 (Create approval chain)
    
    Creates a new approval chain with 1-5 levels.
    
    Requirements: 13.1, 13.5
    """
    try:
        approval_type = ApprovalType(request.approval_type)
        
        chain = await service.create_approval_chain(
            name=request.name,
            ontology_area=request.ontology_area,
            levels=request.levels,
            approval_type=approval_type,
            created_by=created_by,
        )
        
        return {
            "id": str(chain.id),
            "name": chain.name,
            "ontology_area": chain.ontology_area,
            "levels": chain.levels,
            "approval_type": chain.approval_type.value,
            "created_by": chain.created_by,
            "created_at": chain.created_at.isoformat() if chain.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/workflow/approval-chains")
async def list_approval_chains(
    ontology_area: Optional[str] = Query(None, description="按本体领域筛选"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=20, ge=1, le=100, description="分页限制"),
    service: ApprovalService = Depends(get_approval_service)
):
    """
    列出审批链 (List approval chains)
    
    Lists all approval chains with optional filtering.
    
    Requirements: 13.1
    """
    try:
        chains = await service.list_approval_chains(ontology_area=ontology_area)
        
        # Apply pagination
        paginated = chains[offset:offset + limit]
        
        return {
            "approval_chains": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "ontology_area": c.ontology_area,
                    "levels_count": len(c.levels),
                    "approval_type": c.approval_type.value,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in paginated
            ],
            "offset": offset,
            "limit": limit,
            "total": len(chains),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/workflow/approval-chains/{chain_id}")
async def get_approval_chain(
    chain_id: str,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    获取审批链详情 (Get approval chain details)
    
    Retrieves the approval chain by ID.
    
    Requirements: 13.1
    """
    try:
        chain = await service.get_approval_chain(chain_id)
        
        if chain is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval chain not found")
        
        return {
            "id": str(chain.id),
            "name": chain.name,
            "ontology_area": chain.ontology_area,
            "levels": chain.levels,
            "approval_type": chain.approval_type.value,
            "created_by": chain.created_by,
            "created_at": chain.created_at.isoformat() if chain.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/workflow/change-requests/{request_id}/approve")
async def approve_change_request(
    request_id: str,
    request: ApprovalActionRequest,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    审批通过 (Approve change request)
    
    Approves a change request and advances to the next approval level.
    
    Requirements: 4.3, 13.2, 13.4
    """
    try:
        result = await service.approve(
            change_request_id=request_id,
            expert_id=request.expert_id,
            reason=request.reason,
        )
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
        
        return {
            "change_request_id": request_id,
            "action": "approved",
            "approved_by": request.expert_id,
            "current_level": result.get("current_level"),
            "status": result.get("status"),
            "approved_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/workflow/change-requests/{request_id}/reject")
async def reject_change_request(
    request_id: str,
    request: ApprovalActionRequest,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    审批驳回 (Reject change request)
    
    Rejects a change request with a required reason.
    
    Requirements: 4.4, 13.4
    """
    try:
        if not request.reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        
        result = await service.reject(
            change_request_id=request_id,
            expert_id=request.expert_id,
            reason=request.reason,
        )
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
        
        return {
            "change_request_id": request_id,
            "action": "rejected",
            "rejected_by": request.expert_id,
            "reason": request.reason,
            "status": result.get("status"),
            "rejected_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/workflow/change-requests/{request_id}/request-changes")
async def request_changes(
    request_id: str,
    request: ApprovalActionRequest,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    请求修改 (Request changes)
    
    Requests changes to a change request and returns it to the requester.
    
    Requirements: 4.4, 13.4
    """
    try:
        if not request.feedback:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback is required when requesting changes"
            )
        
        result = await service.request_changes(
            change_request_id=request_id,
            expert_id=request.expert_id,
            feedback=request.feedback,
        )
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
        
        return {
            "change_request_id": request_id,
            "action": "changes_requested",
            "requested_by": request.expert_id,
            "feedback": request.feedback,
            "status": result.get("status"),
            "requested_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/workflow/pending-approvals")
async def get_pending_approvals(
    expert_id: str = Query(..., description="专家ID"),
    ontology_area: Optional[str] = Query(None, description="按本体领域筛选"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=20, ge=1, le=100, description="分页限制"),
    service: ApprovalService = Depends(get_approval_service)
):
    """
    获取待审批列表 (Get pending approvals)
    
    Retrieves pending approvals for an expert, sorted by deadline.
    
    Requirements: 4.1, 13.2
    """
    try:
        pending = await service.get_pending_approvals(
            expert_id=expert_id,
            ontology_area=ontology_area,
        )
        
        # Apply pagination
        paginated = pending[offset:offset + limit]
        
        return {
            "pending_approvals": [
                {
                    "id": str(p.id),
                    "ontology_id": p.ontology_id,
                    "change_type": p.change_type,
                    "target_element": p.target_element,
                    "requester_id": p.requester_id,
                    "current_level": p.current_level,
                    "deadline": p.deadline.isoformat() if p.deadline else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in paginated
            ],
            "expert_id": expert_id,
            "offset": offset,
            "limit": limit,
            "total": len(pending),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/workflow/change-requests/{request_id}")
async def get_change_request(
    request_id: str,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    获取变更请求详情 (Get change request details)
    
    Retrieves the change request by ID with approval history.
    
    Requirements: 4.2
    """
    try:
        change_request = await service.get_change_request(request_id)
        
        if change_request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
        
        return {
            "id": str(change_request.id),
            "ontology_id": change_request.ontology_id,
            "requester_id": change_request.requester_id,
            "change_type": change_request.change_type,
            "target_element": change_request.target_element,
            "proposed_changes": change_request.proposed_changes,
            "status": change_request.status,
            "current_level": change_request.current_level,
            "approval_history": change_request.approval_history,
            "created_at": change_request.created_at.isoformat() if change_request.created_at else None,
            "updated_at": change_request.updated_at.isoformat() if change_request.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Validation API Endpoints (Task 15.5)
# =============================================================================

@router.get("/validation/rules")
async def list_validation_rules(
    entity_type: Optional[str] = Query(None, description="按实体类型筛选"),
    region: Optional[str] = Query(None, description="按地区筛选: CN, HK, TW, INTL"),
    industry: Optional[str] = Query(None, description="按行业筛选"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=50, ge=1, le=200, description="分页限制"),
    service: ValidationService = Depends(get_validation_service)
):
    """
    列出验证规则 (List validation rules)
    
    Lists validation rules with optional filtering.
    
    Requirements: 5.1, 5.4
    """
    try:
        rules = await service.get_rules(
            entity_type=entity_type,
            region=region,
            industry=industry,
        )
        
        # Apply pagination
        paginated = rules[offset:offset + limit]
        
        return {
            "rules": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "rule_type": r.rule_type,
                    "target_entity_type": r.target_entity_type,
                    "target_field": r.target_field,
                    "region": r.region,
                    "industry": r.industry,
                    "error_message_key": r.error_message_key,
                }
                for r in paginated
            ],
            "offset": offset,
            "limit": limit,
            "total": len(rules),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/validation/rules", status_code=status.HTTP_201_CREATED)
async def create_validation_rule(
    request: ValidationRuleCreateRequest,
    created_by: str = Query(..., description="创建者ID"),
    service: ValidationService = Depends(get_validation_service)
):
    """
    创建验证规则 (Create validation rule)
    
    Creates a new validation rule for entity validation.
    
    Requirements: 5.1, 5.4
    """
    try:
        rule = await service.create_rule(
            name=request.name,
            rule_type=request.rule_type,
            target_entity_type=request.target_entity_type,
            target_field=request.target_field,
            validation_logic=request.validation_logic,
            error_message_key=request.error_message_key,
            region=request.region,
            industry=request.industry,
            created_by=created_by,
        )
        
        return {
            "id": str(rule.id),
            "name": rule.name,
            "rule_type": rule.rule_type,
            "target_entity_type": rule.target_entity_type,
            "region": rule.region,
            "industry": rule.industry,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/validation/validate")
async def validate_entity(
    request: ValidationRequest,
    service: ValidationService = Depends(get_validation_service)
):
    """
    验证实体 (Validate entity)
    
    Validates an entity against applicable validation rules.
    
    Requirements: 5.1, 5.4, 5.5
    """
    try:
        result = await service.validate(
            entity=request.entity,
            entity_type=request.entity_type,
            region=request.region,
            industry=request.industry,
        )
        
        return {
            "valid": result.is_valid,
            "errors": [
                {
                    "rule_id": str(e.rule_id),
                    "field": e.field,
                    "message": e.message,
                    "message_key": e.message_key,
                    "suggestion": e.suggestion,
                }
                for e in result.errors
            ],
            "warnings": result.warnings,
            "validated_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/validation/chinese-business")
async def get_chinese_business_validators(
    service: ValidationService = Depends(get_validation_service)
):
    """
    获取中国业务验证器 (Get Chinese business validators)
    
    Retrieves validation rules for Chinese business identifiers.
    
    Requirements: 5.1, 5.2
    """
    try:
        validators = await service.get_chinese_business_validators()
        
        return {
            "validators": [
                {
                    "id": str(v.id),
                    "name": v.name,
                    "description": v.description,
                    "identifier_type": v.identifier_type,
                    "format_pattern": v.format_pattern,
                    "example": v.example,
                }
                for v in validators
            ],
            "total": len(validators),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Impact Analysis API Endpoints (Task 15.6)
# =============================================================================

@router.post("/impact/analyze")
async def analyze_impact(
    request: ImpactAnalyzeRequest,
    service: ImpactAnalysisService = Depends(get_impact_analysis_service)
):
    """
    分析变更影响 (Analyze change impact)
    
    Analyzes the impact of a proposed ontology change.
    
    Requirements: 10.1, 10.4
    """
    try:
        change_type = ChangeType(request.change_type)
        
        report = await service.analyze_change(
            ontology_id=request.ontology_id,
            element_id=request.element_id,
            change_type=change_type,
            proposed_changes=request.proposed_changes,
        )
        
        return {
            "element_id": request.element_id,
            "change_type": request.change_type,
            "affected_entity_count": report.affected_entity_count,
            "affected_relation_count": report.affected_relation_count,
            "affected_attribute_count": report.affected_attribute_count,
            "affected_projects": report.affected_projects,
            "impact_level": report.impact_level.value,
            "migration_complexity": report.migration_complexity.value,
            "estimated_migration_hours": report.estimated_migration_hours,
            "breaking_changes": report.breaking_changes,
            "recommendations": report.recommendations,
            "requires_high_impact_approval": report.requires_high_impact_approval,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/impact/reports/{change_request_id}")
async def get_impact_report(
    change_request_id: str,
    service: ImpactAnalysisService = Depends(get_impact_analysis_service)
):
    """
    获取影响报告 (Get impact report)
    
    Retrieves the impact report for a change request.
    
    Requirements: 10.4
    """
    try:
        report = await service.get_report(change_request_id)
        
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impact report not found")
        
        return {
            "change_request_id": change_request_id,
            "affected_entity_count": report.affected_entity_count,
            "affected_relation_count": report.affected_relation_count,
            "affected_attribute_count": report.affected_attribute_count,
            "affected_projects": report.affected_projects,
            "impact_level": report.impact_level.value,
            "migration_complexity": report.migration_complexity.value,
            "estimated_migration_hours": report.estimated_migration_hours,
            "breaking_changes": report.breaking_changes,
            "recommendations": report.recommendations,
            "requires_high_impact_approval": report.requires_high_impact_approval,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/impact/affected-entities")
async def count_affected_entities(
    entity_type: str = Query(..., description="实体类型"),
    service: ImpactAnalysisService = Depends(get_impact_analysis_service)
):
    """
    统计受影响实体 (Count affected entities)
    
    Counts entities that would be affected by changes to an entity type.
    
    Requirements: 10.2
    """
    try:
        count = await service.count_affected_entities(entity_type)
        
        return {
            "entity_type": entity_type,
            "affected_count": count,
            "counted_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/impact/affected-relations")
async def count_affected_relations(
    relation_type: str = Query(..., description="关系类型"),
    service: ImpactAnalysisService = Depends(get_impact_analysis_service)
):
    """
    统计受影响关系 (Count affected relations)
    
    Counts relations that would be affected by changes to a relation type.
    
    Requirements: 10.3
    """
    try:
        count = await service.count_affected_relations(relation_type)
        
        return {
            "relation_type": relation_type,
            "affected_count": count,
            "counted_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# I18n API Endpoints (Task 15.7)
# =============================================================================

@router.post("/i18n/ontology/{element_id}/translations", status_code=status.HTTP_201_CREATED)
async def add_translation(
    element_id: str,
    request: TranslationAddRequest,
    service: OntologyI18nService = Depends(get_i18n_service)
):
    """
    添加翻译 (Add translation)
    
    Adds a translation for an ontology element.
    
    Requirements: 3.1
    """
    try:
        language = Language(request.language)
        
        result = await service.add_translation(
            element_id=element_id,
            language=language,
            name=request.name,
            description=request.description,
            help_text=request.help_text,
        )
        
        return {
            "element_id": element_id,
            "language": request.language,
            "name": request.name,
            "added_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/i18n/ontology/{element_id}/translations/{lang}")
async def get_translation(
    element_id: str,
    lang: str,
    fallback: bool = Query(default=True, description="是否使用回退语言"),
    service: OntologyI18nService = Depends(get_i18n_service)
):
    """
    获取翻译 (Get translation)
    
    Retrieves the translation for an ontology element in the specified language.
    
    Requirements: 3.2, 3.3
    """
    try:
        language = Language(lang)
        
        translation = await service.get_translation(
            element_id=element_id,
            language=language,
            fallback=fallback,
        )
        
        if translation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found")
        
        return {
            "element_id": element_id,
            "language": lang,
            "name": translation.name,
            "description": translation.description,
            "help_text": translation.help_text,
            "is_fallback": translation.is_fallback if hasattr(translation, "is_fallback") else False,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/i18n/ontology/{ontology_id}/missing/{lang}")
async def get_missing_translations(
    ontology_id: str,
    lang: str,
    service: OntologyI18nService = Depends(get_i18n_service)
):
    """
    获取缺失翻译 (Get missing translations)
    
    Retrieves a list of ontology elements missing translations for the specified language.
    
    Requirements: 3.3
    """
    try:
        language = Language(lang)
        
        missing = await service.get_missing_translations(
            ontology_id=ontology_id,
            language=language,
        )
        
        return {
            "ontology_id": ontology_id,
            "language": lang,
            "missing_elements": missing,
            "total_missing": len(missing),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/i18n/ontology/{ontology_id}/export/{lang}")
async def export_translations(
    ontology_id: str,
    lang: str,
    format: str = Query(default="json", description="格式: json, csv"),
    service: OntologyI18nService = Depends(get_i18n_service)
):
    """
    导出翻译 (Export translations)
    
    Exports all translations for an ontology in the specified language.
    
    Requirements: 3.4
    """
    try:
        language = Language(lang)
        
        result = await service.export_translations(
            ontology_id=ontology_id,
            language=language,
            format=format,
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/i18n/ontology/{ontology_id}/import/{lang}")
async def import_translations(
    ontology_id: str,
    lang: str,
    request: TranslationImportRequest,
    service: OntologyI18nService = Depends(get_i18n_service)
):
    """
    导入翻译 (Import translations)
    
    Imports translations for an ontology from JSON or CSV format.
    
    Requirements: 3.4
    """
    try:
        language = Language(lang)
        
        result = await service.import_translations(
            ontology_id=ontology_id,
            language=language,
            translations=request.translations,
            format=request.format,
        )
        
        return {
            "ontology_id": ontology_id,
            "language": lang,
            "imported_count": result.get("imported_count", 0),
            "skipped_count": result.get("skipped_count", 0),
            "imported_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/i18n/ontology/{ontology_id}/coverage")
async def get_translation_coverage(
    ontology_id: str,
    service: OntologyI18nService = Depends(get_i18n_service)
):
    """
    获取翻译覆盖率 (Get translation coverage)
    
    Retrieves translation coverage statistics for an ontology.
    
    Requirements: 3.1
    """
    try:
        coverage = await service.get_translation_coverage(ontology_id)
        
        return {
            "ontology_id": ontology_id,
            "coverage_by_language": coverage.coverage_by_language,
            "total_elements": coverage.total_elements,
            "bilingual_complete": coverage.bilingual_complete,
            "calculated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Knowledge Contribution API Endpoints
# =============================================================================

@router.post("/contributions/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    element_id: str = Query(..., description="元素ID"),
    expert_id: str = Query(..., description="专家ID"),
    content: str = Query(..., description="评论内容"),
    parent_comment_id: Optional[str] = Query(None, description="父评论ID"),
    service: KnowledgeContributionService = Depends(get_contribution_service)
):
    """
    添加评论 (Add comment)
    
    Adds a comment to an ontology element.
    
    Requirements: 6.1, 6.3
    """
    try:
        comment = await service.add_comment(
            element_id=element_id,
            expert_id=expert_id,
            content=content,
            parent_comment_id=parent_comment_id,
        )
        
        return {
            "id": str(comment.id),
            "element_id": element_id,
            "expert_id": expert_id,
            "content": content,
            "parent_comment_id": parent_comment_id,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/contributions/suggestions/entity", status_code=status.HTTP_201_CREATED)
async def suggest_entity(
    expert_id: str = Query(..., description="专家ID"),
    entity_data: Dict[str, Any] = None,
    service: KnowledgeContributionService = Depends(get_contribution_service)
):
    """
    建议实体 (Suggest entity)
    
    Suggests a new entity type for the ontology.
    
    Requirements: 6.2
    """
    try:
        suggestion = await service.suggest_entity(
            expert_id=expert_id,
            entity_data=entity_data or {},
        )
        
        return {
            "id": str(suggestion.id),
            "expert_id": expert_id,
            "contribution_type": "entity_suggestion",
            "status": suggestion.status,
            "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/contributions/expert/{expert_id}")
async def get_expert_contributions(
    expert_id: str,
    contribution_type: Optional[str] = Query(None, description="贡献类型"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=20, ge=1, le=100, description="分页限制"),
    service: KnowledgeContributionService = Depends(get_contribution_service)
):
    """
    获取专家贡献 (Get expert contributions)
    
    Retrieves all contributions made by an expert.
    
    Requirements: 6.5
    """
    try:
        contributions = await service.get_expert_contributions(
            expert_id=expert_id,
            contribution_type=contribution_type,
        )
        
        # Apply pagination
        paginated = contributions[offset:offset + limit]
        
        return {
            "contributions": [
                {
                    "id": str(c.id),
                    "contribution_type": c.contribution_type,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in paginated
            ],
            "expert_id": expert_id,
            "offset": offset,
            "limit": limit,
            "total": len(contributions),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Compliance Template API Endpoints
# =============================================================================

@router.get("/compliance/templates")
async def list_compliance_templates(
    regulation_type: Optional[str] = Query(None, description="法规类型"),
    service: ComplianceTemplateService = Depends(get_compliance_service)
):
    """
    列出合规模板 (List compliance templates)
    
    Lists available compliance templates for Chinese regulations.
    
    Requirements: 8.1
    """
    try:
        templates = await service.list_templates(regulation_type=regulation_type)
        
        return {
            "templates": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "regulation_type": t.regulation_type.value,
                    "description": t.description,
                    "version": t.version,
                }
                for t in templates
            ],
            "total": len(templates),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/compliance/classify")
async def classify_entity(
    entity: Dict[str, Any],
    service: ComplianceTemplateService = Depends(get_compliance_service)
):
    """
    分类实体 (Classify entity)
    
    Classifies an entity according to data sensitivity levels.
    
    Requirements: 8.2
    """
    try:
        result = await service.classify_entity(entity)
        
        return {
            "classification": result.classification.value,
            "matched_rules": result.matched_rules,
            "recommendations": result.recommendations,
            "article_references": result.article_references,
            "classified_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/compliance/validate-pipl")
async def validate_pipl(
    entity: Dict[str, Any],
    service: ComplianceTemplateService = Depends(get_compliance_service)
):
    """
    验证PIPL合规 (Validate PIPL compliance)
    
    Validates an entity against PIPL requirements.
    
    Requirements: 8.3
    """
    try:
        result = await service.validate_pipl(entity)
        
        return {
            "compliant": result.is_compliant,
            "violations": result.violations,
            "recommendations": result.recommendations,
            "validated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/compliance/report")
async def generate_compliance_report(
    ontology_id: str = Query(..., description="本体ID"),
    regulation_type: str = Query(..., description="法规类型"),
    service: ComplianceTemplateService = Depends(get_compliance_service)
):
    """
    生成合规报告 (Generate compliance report)
    
    Generates a compliance report for an ontology.
    
    Requirements: 8.5
    """
    try:
        reg_type = RegulationType(regulation_type)
        
        report = await service.generate_compliance_report(
            ontology_id=ontology_id,
            regulation_type=reg_type,
        )
        
        return {
            "ontology_id": ontology_id,
            "regulation_type": regulation_type,
            "compliance_score": report.compliance_score,
            "entity_mappings": report.entity_mappings,
            "violations": report.violations,
            "recommendations": report.recommendations,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Best Practices API Endpoints
# =============================================================================

@router.get("/best-practices")
async def search_best_practices(
    industry: Optional[str] = Query(None, description="按行业筛选"),
    use_case: Optional[str] = Query(None, description="按用例筛选"),
    query: Optional[str] = Query(None, description="搜索关键词"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=20, ge=1, le=100, description="分页限制"),
    service: BestPracticeService = Depends(get_best_practice_service)
):
    """
    搜索最佳实践 (Search best practices)
    
    Searches best practices with optional filtering.
    
    Requirements: 11.1
    """
    try:
        practices = await service.search_best_practices(
            industry=industry,
            use_case=use_case,
            query=query,
        )
        
        # Apply pagination
        paginated = practices[offset:offset + limit]
        
        return {
            "best_practices": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "industry": p.industry,
                    "use_case": p.use_case,
                    "description": p.description,
                    "usage_count": p.usage_count,
                    "is_promoted": p.is_promoted,
                    "rating": p.rating,
                }
                for p in paginated
            ],
            "offset": offset,
            "limit": limit,
            "total": len(practices),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/best-practices/{practice_id}")
async def get_best_practice(
    practice_id: str,
    service: BestPracticeService = Depends(get_best_practice_service)
):
    """
    获取最佳实践详情 (Get best practice details)
    
    Retrieves the best practice by ID with configuration steps.
    
    Requirements: 11.2
    """
    try:
        practice = await service.get_best_practice(practice_id)
        
        if practice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Best practice not found")
        
        return {
            "id": str(practice.id),
            "name": practice.name,
            "industry": practice.industry,
            "use_case": practice.use_case,
            "description": practice.description,
            "configuration_steps": practice.configuration_steps,
            "benefits": practice.benefits,
            "examples": practice.examples,
            "usage_count": practice.usage_count,
            "is_promoted": practice.is_promoted,
            "rating": practice.rating,
            "created_at": practice.created_at.isoformat() if practice.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/best-practices/{practice_id}/apply", status_code=status.HTTP_201_CREATED)
async def apply_best_practice(
    practice_id: str,
    expert_id: str = Query(..., description="专家ID"),
    service: BestPracticeService = Depends(get_best_practice_service)
):
    """
    应用最佳实践 (Apply best practice)
    
    Starts applying a best practice with step-by-step guidance.
    
    Requirements: 11.3
    """
    try:
        session = await service.apply_best_practice(
            practice_id=practice_id,
            expert_id=expert_id,
        )
        
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Best practice not found")
        
        return {
            "session_id": str(session.id),
            "practice_id": practice_id,
            "current_step": session.current_step,
            "total_steps": session.total_steps,
            "started_at": session.started_at.isoformat() if session.started_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# Audit API Endpoints
# =============================================================================

@router.get("/audit/logs")
async def get_audit_logs(
    ontology_id: Optional[str] = Query(None, description="本体ID"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    change_type: Optional[str] = Query(None, description="变更类型"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    limit: int = Query(default=50, ge=1, le=200, description="分页限制"),
    service: AuditService = Depends(get_audit_service)
):
    """
    获取审计日志 (Get audit logs)
    
    Retrieves audit logs with optional filtering.
    
    Requirements: 14.1, 14.2
    """
    try:
        filter_params = AuditLogFilter(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=change_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        logs = await service.get_logs(
            filter_params=filter_params,
            offset=offset,
            limit=limit,
        )
        
        return {
            "logs": [
                {
                    "id": str(log.id),
                    "ontology_id": log.ontology_id,
                    "user_id": log.user_id,
                    "change_type": log.change_type,
                    "affected_element": log.affected_element,
                    "changes": log.changes,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "offset": offset,
            "limit": limit,
            "total": len(logs),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/audit/rollback")
async def rollback_to_version(
    ontology_id: str = Query(..., description="本体ID"),
    target_version: str = Query(..., description="目标版本"),
    user_id: str = Query(..., description="执行者ID"),
    service: AuditService = Depends(get_audit_service)
):
    """
    回滚到版本 (Rollback to version)
    
    Rolls back an ontology to a previous version.
    
    Requirements: 14.3, 14.4
    """
    try:
        result = await service.rollback_to_version(
            ontology_id=ontology_id,
            target_version=target_version,
            user_id=user_id,
        )
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        
        return {
            "ontology_id": ontology_id,
            "target_version": target_version,
            "new_version": result.new_version,
            "affected_users": result.affected_users,
            "rolled_back_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/audit/logs/{log_id}/verify")
async def verify_audit_log_integrity(
    log_id: str,
    service: AuditService = Depends(get_audit_service)
):
    """
    验证审计日志完整性 (Verify audit log integrity)
    
    Verifies the cryptographic integrity of an audit log entry.
    
    Requirements: 14.5
    """
    try:
        result = await service.verify_integrity(log_id)
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
        
        return {
            "log_id": log_id,
            "integrity_valid": result.is_valid,
            "verified_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/audit/export")
async def export_audit_logs(
    ontology_id: str = Query(..., description="本体ID"),
    format: str = Query(default="json", description="格式: json, csv"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    service: AuditService = Depends(get_audit_service)
):
    """
    导出审计日志 (Export audit logs)
    
    Exports audit logs in JSON or CSV format.
    
    Requirements: 14.2
    """
    try:
        result = await service.export_logs(
            ontology_id=ontology_id,
            format=format,
            start_date=start_date,
            end_date=end_date,
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
