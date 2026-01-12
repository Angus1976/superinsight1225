"""
ISO 27001 Compliance API endpoints.

Provides REST API endpoints for ISO 27001 compliance assessment,
control evaluation, and reporting functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.database.connection import get_db_session
from src.compliance.iso27001_compliance import (
    ISO27001ComplianceChecker,
    ISO27001Assessment,
    ISO27001Control,
    ISO27001ControlDomain,
    ISO27001ControlStatus
)
from src.security.middleware import get_current_user
from src.security.rbac_controller import RBACController
from src.security.models import UserModel

logger = logging.getLogger(__name__)

# Pydantic models for API
class ISO27001ControlResponse(BaseModel):
    """ISO 27001 控制项响应模型"""
    control_id: str
    domain: str
    title: str
    description: str
    status: str
    effectiveness_score: float
    evidence: List[str]
    gaps: List[str]
    recommendations: List[str]

class ISO27001AssessmentResponse(BaseModel):
    """ISO 27001 评估响应模型"""
    assessment_id: str
    tenant_id: str
    assessment_date: datetime
    overall_maturity_level: int
    overall_compliance_score: float
    domain_scores: Dict[str, float]
    control_count: int
    implemented_controls: int
    partially_implemented_controls: int
    not_implemented_controls: int
    high_priority_recommendations: List[str]

class ISO27001DomainSummary(BaseModel):
    """ISO 27001 域摘要模型"""
    domain_code: str
    domain_name: str
    control_count: int
    average_score: float
    implemented_count: int
    gaps_count: int
    priority_level: str

class ISO27001ComplianceRequest(BaseModel):
    """ISO 27001 合规评估请求模型"""
    tenant_id: str = Field(..., description="租户ID")
    include_risk_assessment: bool = Field(True, description="是否包含风险评估")
    assessment_scope: Optional[List[str]] = Field(None, description="评估范围（控制域列表）")

# Create router
router = APIRouter(prefix="/api/iso27001", tags=["ISO 27001 Compliance"])

# Initialize compliance checker
compliance_checker = ISO27001ComplianceChecker()
rbac_controller = RBACController()


@router.post("/assessment", response_model=ISO27001AssessmentResponse)
async def conduct_iso27001_assessment(
    request: ISO27001ComplianceRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    执行ISO 27001合规性评估
    
    对指定租户进行完整的ISO 27001合规性评估，
    包括所有控制域和控制项的评估。
    """
    try:
        # 权限检查
        if not rbac_controller.check_permission(
            current_user.id, "compliance:assess", request.tenant_id
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions for compliance assessment")
        
        # 执行评估
        assessment = compliance_checker.assess_iso27001_compliance(
            tenant_id=request.tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_risk_assessment=request.include_risk_assessment
        )
        
        # 统计控制项状态
        implemented_count = sum(1 for c in assessment.control_assessments 
                              if c.status == ISO27001ControlStatus.IMPLEMENTED)
        partially_implemented_count = sum(1 for c in assessment.control_assessments 
                                        if c.status == ISO27001ControlStatus.PARTIALLY_IMPLEMENTED)
        not_implemented_count = sum(1 for c in assessment.control_assessments 
                                  if c.status == ISO27001ControlStatus.NOT_IMPLEMENTED)
        
        # 构建响应
        response = ISO27001AssessmentResponse(
            assessment_id=assessment.assessment_id,
            tenant_id=assessment.tenant_id,
            assessment_date=assessment.assessment_date,
            overall_maturity_level=assessment.overall_maturity_level,
            overall_compliance_score=assessment.overall_compliance_score,
            domain_scores=assessment.domain_scores,
            control_count=len(assessment.control_assessments),
            implemented_controls=implemented_count,
            partially_implemented_controls=partially_implemented_count,
            not_implemented_controls=not_implemented_count,
            high_priority_recommendations=assessment.priority_recommendations[:5]
        )
        
        logger.info(f"ISO 27001 assessment completed for tenant {request.tenant_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to conduct ISO 27001 assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


@router.get("/domains", response_model=List[ISO27001DomainSummary])
async def get_domain_summary(
    tenant_id: str = Query(..., description="租户ID"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    获取ISO 27001控制域摘要
    
    返回所有控制域的概览信息，包括得分、
    控制项数量和实施状态。
    """
    try:
        # 权限检查
        if not rbac_controller.check_permission(
            current_user.id, "compliance:view", tenant_id
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions to view compliance data")
        
        # 执行快速评估获取域摘要
        assessment = compliance_checker.assess_iso27001_compliance(
            tenant_id=tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_risk_assessment=False
        )
        
        # 构建域摘要
        domain_summaries = []
        
        for domain in ISO27001ControlDomain:
            domain_controls = [c for c in assessment.control_assessments if c.domain == domain]
            
            if domain_controls:
                implemented_count = sum(1 for c in domain_controls 
                                     if c.status == ISO27001ControlStatus.IMPLEMENTED)
                gaps_count = sum(1 for c in domain_controls 
                               if c.status != ISO27001ControlStatus.IMPLEMENTED)
                
                average_score = sum(c.effectiveness_score for c in domain_controls) / len(domain_controls)
                
                # 确定优先级
                if average_score < 50:
                    priority_level = "Critical"
                elif average_score < 70:
                    priority_level = "High"
                elif average_score < 85:
                    priority_level = "Medium"
                else:
                    priority_level = "Low"
                
                domain_summaries.append(ISO27001DomainSummary(
                    domain_code=domain.value,
                    domain_name=domain.name.replace("_", " ").title(),
                    control_count=len(domain_controls),
                    average_score=round(average_score, 2),
                    implemented_count=implemented_count,
                    gaps_count=gaps_count,
                    priority_level=priority_level
                ))
        
        return domain_summaries
        
    except Exception as e:
        logger.error(f"Failed to get domain summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get domain summary: {str(e)}")


@router.get("/controls/{domain}", response_model=List[ISO27001ControlResponse])
async def get_domain_controls(
    domain: str = Path(..., description="控制域代码 (e.g., A.5, A.9)"),
    tenant_id: str = Query(..., description="租户ID"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    获取指定域的控制项详情
    
    返回指定控制域内所有控制项的详细信息，
    包括实施状态、有效性得分和改进建议。
    """
    try:
        # 权限检查
        if not rbac_controller.check_permission(
            current_user.id, "compliance:view", tenant_id
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions to view compliance data")
        
        # 验证域代码
        try:
            domain_enum = next(d for d in ISO27001ControlDomain if d.value == domain)
        except StopIteration:
            raise HTTPException(status_code=400, detail=f"Invalid domain code: {domain}")
        
        # 执行评估
        assessment = compliance_checker.assess_iso27001_compliance(
            tenant_id=tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_risk_assessment=False
        )
        
        # 筛选指定域的控制项
        domain_controls = [c for c in assessment.control_assessments if c.domain == domain_enum]
        
        # 构建响应
        control_responses = []
        for control in domain_controls:
            control_responses.append(ISO27001ControlResponse(
                control_id=control.control_id,
                domain=control.domain.value,
                title=control.title,
                description=control.description,
                status=control.status.value,
                effectiveness_score=control.effectiveness_score,
                evidence=control.evidence,
                gaps=control.gaps,
                recommendations=control.recommendations
            ))
        
        return control_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get domain controls: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get domain controls: {str(e)}")


@router.get("/maturity-assessment", response_model=Dict[str, Any])
async def get_maturity_assessment(
    tenant_id: str = Query(..., description="租户ID"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    获取ISO 27001成熟度评估
    
    返回组织的信息安全管理成熟度等级评估，
    包括各个维度的成熟度分析。
    """
    try:
        # 权限检查
        if not rbac_controller.check_permission(
            current_user.id, "compliance:assess", tenant_id
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions for maturity assessment")
        
        # 执行评估
        assessment = compliance_checker.assess_iso27001_compliance(
            tenant_id=tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_risk_assessment=True
        )
        
        # 计算各维度成熟度
        policy_maturity = assessment.domain_scores.get("A.5", 0) / 20  # 转换为1-5等级
        access_control_maturity = assessment.domain_scores.get("A.9", 0) / 20
        operations_maturity = assessment.domain_scores.get("A.12", 0) / 20
        incident_maturity = assessment.domain_scores.get("A.16", 0) / 20
        
        # 构建成熟度评估响应
        maturity_response = {
            "overall_maturity_level": assessment.overall_maturity_level,
            "maturity_description": compliance_checker.maturity_levels.get(
                assessment.overall_maturity_level, "Unknown"
            ),
            "dimension_maturity": {
                "policy_governance": {
                    "level": min(5, max(1, int(policy_maturity))),
                    "score": assessment.domain_scores.get("A.5", 0),
                    "description": "Information security policies and governance"
                },
                "access_control": {
                    "level": min(5, max(1, int(access_control_maturity))),
                    "score": assessment.domain_scores.get("A.9", 0),
                    "description": "Access control and user management"
                },
                "operations_security": {
                    "level": min(5, max(1, int(operations_maturity))),
                    "score": assessment.domain_scores.get("A.12", 0),
                    "description": "Operational security controls"
                },
                "incident_management": {
                    "level": min(5, max(1, int(incident_maturity))),
                    "score": assessment.domain_scores.get("A.16", 0),
                    "description": "Security incident management"
                }
            },
            "improvement_roadmap": assessment.implementation_roadmap,
            "next_level_requirements": [
                f"Achieve {assessment.overall_maturity_level + 1} maturity level",
                "Implement missing critical controls",
                "Enhance monitoring and measurement",
                "Establish continuous improvement processes"
            ]
        }
        
        return maturity_response
        
    except Exception as e:
        logger.error(f"Failed to get maturity assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Maturity assessment failed: {str(e)}")


@router.get("/risk-assessment", response_model=Dict[str, Any])
async def get_risk_assessment(
    tenant_id: str = Query(..., description="租户ID"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    获取ISO 27001风险评估
    
    返回基于控制项实施状态的风险评估结果，
    包括识别的风险和处理计划。
    """
    try:
        # 权限检查
        if not rbac_controller.check_permission(
            current_user.id, "compliance:assess", tenant_id
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions for risk assessment")
        
        # 执行包含风险评估的完整评估
        assessment = compliance_checker.assess_iso27001_compliance(
            tenant_id=tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_risk_assessment=True
        )
        
        # 统计风险分布
        risk_distribution = {"High": 0, "Medium": 0, "Low": 0}
        for risk in assessment.identified_risks:
            risk_level = risk.get("risk_level", "Medium")
            risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
        
        # 构建风险评估响应
        risk_response = {
            "assessment_id": assessment.assessment_id,
            "risk_summary": {
                "total_risks": len(assessment.identified_risks),
                "high_risks": risk_distribution.get("High", 0),
                "medium_risks": risk_distribution.get("Medium", 0),
                "low_risks": risk_distribution.get("Low", 0)
            },
            "identified_risks": assessment.identified_risks[:10],  # 返回前10个风险
            "risk_treatment_plan": assessment.risk_treatment_plan,
            "risk_heat_map": {
                "critical_areas": [
                    domain for domain, score in assessment.domain_scores.items() 
                    if score < 50
                ],
                "improvement_areas": [
                    domain for domain, score in assessment.domain_scores.items() 
                    if 50 <= score < 70
                ]
            },
            "recommendations": assessment.priority_recommendations
        }
        
        return risk_response
        
    except Exception as e:
        logger.error(f"Failed to get risk assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {str(e)}")


@router.get("/compliance-report", response_model=Dict[str, Any])
async def generate_compliance_report(
    tenant_id: str = Query(..., description="租户ID"),
    format: str = Query("json", description="报告格式 (json, summary)"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    生成ISO 27001合规报告
    
    生成完整的ISO 27001合规性报告，
    包括评估结果、风险分析和改进建议。
    """
    try:
        # 权限检查
        if not rbac_controller.check_permission(
            current_user.id, "compliance:report", tenant_id
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions to generate compliance reports")
        
        # 执行完整评估
        assessment = compliance_checker.assess_iso27001_compliance(
            tenant_id=tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_risk_assessment=True
        )
        
        if format == "summary":
            # 生成摘要报告
            report = {
                "executive_summary": {
                    "assessment_date": assessment.assessment_date.isoformat(),
                    "overall_compliance_score": assessment.overall_compliance_score,
                    "maturity_level": assessment.overall_maturity_level,
                    "total_controls_assessed": len(assessment.control_assessments),
                    "compliant_controls": sum(1 for c in assessment.control_assessments 
                                            if c.status == ISO27001ControlStatus.IMPLEMENTED),
                    "critical_gaps": sum(1 for c in assessment.control_assessments 
                                       if c.effectiveness_score < 50)
                },
                "key_findings": assessment.priority_recommendations[:5],
                "next_steps": [step["action_plan"] for step in assessment.risk_treatment_plan[:3]]
            }
        else:
            # 生成完整报告
            report = {
                "assessment_metadata": {
                    "assessment_id": assessment.assessment_id,
                    "tenant_id": assessment.tenant_id,
                    "assessment_date": assessment.assessment_date.isoformat(),
                    "assessor": current_user.username,
                    "scope": "Full ISO 27001:2022 Assessment"
                },
                "compliance_summary": {
                    "overall_score": assessment.overall_compliance_score,
                    "maturity_level": assessment.overall_maturity_level,
                    "domain_scores": assessment.domain_scores
                },
                "control_assessment": [
                    {
                        "control_id": c.control_id,
                        "title": c.title,
                        "domain": c.domain.value,
                        "status": c.status.value,
                        "effectiveness_score": c.effectiveness_score,
                        "evidence_count": len(c.evidence),
                        "gaps_count": len(c.gaps)
                    }
                    for c in assessment.control_assessments
                ],
                "risk_assessment": {
                    "identified_risks": assessment.identified_risks,
                    "treatment_plan": assessment.risk_treatment_plan
                },
                "improvement_plan": {
                    "priority_recommendations": assessment.priority_recommendations,
                    "implementation_roadmap": assessment.implementation_roadmap
                }
            }
        
        logger.info(f"ISO 27001 compliance report generated for tenant {tenant_id}")
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/health")
async def health_check():
    """
    ISO 27001合规模块健康检查
    
    检查ISO 27001合规评估模块的运行状态。
    """
    try:
        # 检查合规检查器状态
        checker_status = "healthy" if compliance_checker else "unhealthy"
        
        # 检查控制项定义
        control_definitions_count = len(compliance_checker.control_definitions)
        
        return {
            "status": "healthy",
            "module": "ISO 27001 Compliance",
            "checker_status": checker_status,
            "control_definitions_loaded": control_definitions_count,
            "supported_domains": len(ISO27001ControlDomain),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )