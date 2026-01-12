"""
Data Protection Compliance API Endpoints.

Provides REST API endpoints for comprehensive data protection regulation compliance
assessment and reporting across multiple international regulations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.database.connection import get_db_session
from src.compliance.data_protection_compliance import (
    DataProtectionComplianceEngine,
    DataProtectionRegulation,
    DataProtectionComplianceReport,
    ComplianceStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-protection-compliance", tags=["Data Protection Compliance"])


# Request/Response Models

class ComplianceAssessmentRequest(BaseModel):
    """数据保护合规评估请求"""
    tenant_id: str = Field(..., description="Tenant identifier")
    regulations: List[str] = Field(..., description="List of regulations to assess")
    assessment_date: Optional[datetime] = Field(None, description="Assessment date (defaults to now)")
    include_cross_regulation_analysis: bool = Field(True, description="Include cross-regulation analysis")


class ComplianceAssessmentResponse(BaseModel):
    """数据保护合规评估响应"""
    success: bool
    message: str
    report_id: str
    overall_compliance_score: float
    overall_status: str
    regulations_assessed: List[str]
    assessment_date: datetime
    next_assessment_due: datetime


class RegulationComplianceDetail(BaseModel):
    """法规合规详情"""
    regulation: str
    compliance_score: float
    status: str
    assessments_count: int
    high_risk_gaps: int
    recommendations: List[str]


class ComplianceReportSummary(BaseModel):
    """合规报告摘要"""
    report_id: str
    tenant_id: str
    assessment_date: datetime
    overall_compliance_score: float
    overall_status: str
    regulations_assessed: List[str]
    high_risk_gaps_count: int
    critical_violations_count: int
    priority_recommendations_count: int


class DataSubjectRightsStatus(BaseModel):
    """数据主体权利状态"""
    right: str
    implemented: bool
    effectiveness_score: float
    response_time_hours: float
    applicable_regulations: List[str]
    evidence: List[str]
    gaps: List[str]
    recommendations: List[str]


class CompliancePrincipleStatus(BaseModel):
    """合规原则状态"""
    principle: str
    compliance_score: float
    assessments_count: int
    compliant_assessments: int
    non_compliant_assessments: int
    recommendations: List[str]


# API Endpoints

@router.post("/assess", response_model=ComplianceAssessmentResponse)
async def assess_data_protection_compliance(
    request: ComplianceAssessmentRequest,
    assessed_by: str = Query(..., description="User performing the assessment"),
    db: Session = Depends(get_db_session)
):
    """
    执行数据保护法规合规评估
    
    支持多种国际数据保护法规的并行评估，包括GDPR、CCPA、PIPEDA、LGPD等。
    """
    try:
        # 验证法规列表
        valid_regulations = []
        for reg_str in request.regulations:
            try:
                regulation = DataProtectionRegulation(reg_str.lower())
                valid_regulations.append(regulation)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid regulation: {reg_str}. Supported: {[r.value for r in DataProtectionRegulation]}"
                )
        
        if not valid_regulations:
            raise HTTPException(
                status_code=400,
                detail="At least one valid regulation must be specified"
            )
        
        # 设置评估日期
        assessment_date = request.assessment_date or datetime.utcnow()
        
        # 创建合规引擎
        compliance_engine = DataProtectionComplianceEngine()
        
        # 执行评估
        report = compliance_engine.assess_data_protection_compliance(
            tenant_id=request.tenant_id,
            regulations=valid_regulations,
            assessment_date=assessment_date,
            assessed_by=UUID(assessed_by) if assessed_by else UUID("00000000-0000-0000-0000-000000000000"),
            db=db,
            include_cross_regulation_analysis=request.include_cross_regulation_analysis
        )
        
        return ComplianceAssessmentResponse(
            success=True,
            message="Data protection compliance assessment completed successfully",
            report_id=report.report_id,
            overall_compliance_score=report.overall_compliance_score,
            overall_status=report.overall_status.value,
            regulations_assessed=[reg.value for reg in report.regulations_assessed],
            assessment_date=report.assessment_date,
            next_assessment_due=report.next_assessment_due
        )
        
    except Exception as e:
        logger.error(f"Failed to assess data protection compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{report_id}", response_model=Dict[str, Any])
async def get_compliance_report(
    report_id: str,
    tenant_id: str = Query(..., description="Tenant identifier"),
    include_details: bool = Query(True, description="Include detailed assessments"),
    db: Session = Depends(get_db_session)
):
    """
    获取数据保护合规报告详情
    
    返回完整的合规评估报告，包括各法规的详细评估结果、
    数据主体权利实现状态、合规原则评估等。
    """
    try:
        # 注意：在实际实现中，这里应该从数据库中检索报告
        # 目前返回模拟数据作为示例
        
        return {
            "report_id": report_id,
            "tenant_id": tenant_id,
            "assessment_date": datetime.utcnow().isoformat(),
            "overall_compliance_score": 85.5,
            "overall_status": "partially_compliant",
            "regulations_assessed": ["gdpr", "ccpa"],
            "regulation_scores": {
                "gdpr": 88.0,
                "ccpa": 83.0
            },
            "principle_scores": {
                "lawfulness": 90.0,
                "transparency": 85.0,
                "security": 92.0,
                "accountability": 80.0
            },
            "high_risk_gaps_count": 3,
            "critical_violations_count": 1,
            "priority_recommendations": [
                "Implement automated data deletion procedures",
                "Enhance consent management system",
                "Improve data subject request response times"
            ],
            "next_assessment_due": (datetime.utcnow() + timedelta(days=90)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regulations", response_model=List[Dict[str, Any]])
async def get_supported_regulations():
    """
    获取支持的数据保护法规列表
    
    返回系统支持的所有数据保护法规及其基本信息。
    """
    try:
        regulations = []
        
        for regulation in DataProtectionRegulation:
            regulation_info = {
                "code": regulation.value,
                "name": _get_regulation_name(regulation),
                "jurisdiction": _get_regulation_jurisdiction(regulation),
                "description": _get_regulation_description(regulation),
                "key_principles": _get_regulation_principles(regulation),
                "data_subject_rights": _get_regulation_rights(regulation)
            }
            regulations.append(regulation_info)
        
        return regulations
        
    except Exception as e:
        logger.error(f"Failed to get supported regulations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regulations/{regulation}/requirements", response_model=List[Dict[str, Any]])
async def get_regulation_requirements(
    regulation: str,
    include_verification_criteria: bool = Query(True, description="Include verification criteria")
):
    """
    获取特定法规的要求列表
    
    返回指定数据保护法规的所有要求及其验证标准。
    """
    try:
        # 验证法规
        try:
            reg_enum = DataProtectionRegulation(regulation.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid regulation: {regulation}"
            )
        
        # 创建合规引擎并获取要求
        compliance_engine = DataProtectionComplianceEngine()
        requirements = compliance_engine.regulation_requirements.get(reg_enum, [])
        
        result = []
        for req in requirements:
            req_dict = {
                "requirement_id": req.requirement_id,
                "title": req.title,
                "description": req.description,
                "principle": req.principle.value,
                "mandatory": req.mandatory,
                "applicable_rights": [right.value for right in req.applicable_rights],
                "penalty_severity": req.penalty_severity
            }
            
            if include_verification_criteria:
                req_dict["verification_criteria"] = req.verification_criteria
            
            result.append(req_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get regulation requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenant/{tenant_id}/status", response_model=Dict[str, Any])
async def get_tenant_compliance_status(
    tenant_id: str,
    regulations: Optional[List[str]] = Query(None, description="Specific regulations to check"),
    db: Session = Depends(get_db_session)
):
    """
    获取租户的数据保护合规状态概览
    
    返回租户当前的合规状态、最近评估结果、待处理问题等。
    """
    try:
        # 执行快速合规状态检查
        compliance_engine = DataProtectionComplianceEngine()
        
        # 如果未指定法规，使用默认法规集
        if not regulations:
            target_regulations = [DataProtectionRegulation.GDPR, DataProtectionRegulation.CCPA]
        else:
            target_regulations = []
            for reg_str in regulations:
                try:
                    regulation = DataProtectionRegulation(reg_str.lower())
                    target_regulations.append(regulation)
                except ValueError:
                    continue
        
        # 执行快速评估
        report = compliance_engine.assess_data_protection_compliance(
            tenant_id=tenant_id,
            regulations=target_regulations,
            assessment_date=datetime.utcnow(),
            assessed_by=UUID("00000000-0000-0000-0000-000000000000"),
            db=db,
            include_cross_regulation_analysis=False
        )
        
        return {
            "tenant_id": tenant_id,
            "last_assessment_date": report.assessment_date.isoformat(),
            "overall_compliance_score": report.overall_compliance_score,
            "overall_status": report.overall_status.value,
            "regulations_status": {
                reg: {
                    "score": report.regulation_scores.get(reg, 0),
                    "status": "compliant" if report.regulation_scores.get(reg, 0) >= 90 else "needs_attention"
                }
                for reg in [r.value for r in target_regulations]
            },
            "high_risk_gaps_count": len(report.high_risk_gaps),
            "critical_violations_count": len(report.critical_violations),
            "next_assessment_due": report.next_assessment_due.isoformat(),
            "priority_actions": report.priority_recommendations[:3]
        }
        
    except Exception as e:
        logger.error(f"Failed to get tenant compliance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenant/{tenant_id}/rights-status", response_model=List[DataSubjectRightsStatus])
async def get_data_subject_rights_status(
    tenant_id: str,
    regulations: Optional[List[str]] = Query(None, description="Filter by regulations"),
    db: Session = Depends(get_db_session)
):
    """
    获取数据主体权利实现状态
    
    返回各项数据主体权利的实现状态、有效性评分、响应时间等。
    """
    try:
        compliance_engine = DataProtectionComplianceEngine()
        
        # 确定目标法规
        if regulations:
            target_regulations = []
            for reg_str in regulations:
                try:
                    regulation = DataProtectionRegulation(reg_str.lower())
                    target_regulations.append(regulation)
                except ValueError:
                    continue
        else:
            target_regulations = [DataProtectionRegulation.GDPR, DataProtectionRegulation.CCPA]
        
        # 评估数据主体权利
        rights_implementation = compliance_engine._assess_data_subject_rights(
            tenant_id, target_regulations, db
        )
        
        result = []
        for right, status in rights_implementation.items():
            result.append(DataSubjectRightsStatus(
                right=right,
                implemented=status["implemented"],
                effectiveness_score=status["effectiveness_score"],
                response_time_hours=status["response_time_hours"],
                applicable_regulations=status["applicable_regulations"],
                evidence=status["evidence"],
                gaps=status["gaps"],
                recommendations=status["recommendations"]
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get data subject rights status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenant/{tenant_id}/principles-status", response_model=List[CompliancePrincipleStatus])
async def get_compliance_principles_status(
    tenant_id: str,
    regulations: Optional[List[str]] = Query(None, description="Filter by regulations"),
    db: Session = Depends(get_db_session)
):
    """
    获取数据保护原则合规状态
    
    返回各项数据保护原则的合规评估结果和改进建议。
    """
    try:
        compliance_engine = DataProtectionComplianceEngine()
        
        # 确定目标法规
        if regulations:
            target_regulations = []
            for reg_str in regulations:
                try:
                    regulation = DataProtectionRegulation(reg_str.lower())
                    target_regulations.append(regulation)
                except ValueError:
                    continue
        else:
            target_regulations = [DataProtectionRegulation.GDPR, DataProtectionRegulation.CCPA]
        
        # 执行评估
        report = compliance_engine.assess_data_protection_compliance(
            tenant_id=tenant_id,
            regulations=target_regulations,
            assessment_date=datetime.utcnow(),
            assessed_by=UUID("00000000-0000-0000-0000-000000000000"),
            db=db,
            include_cross_regulation_analysis=False
        )
        
        result = []
        for principle, score in report.principle_scores.items():
            # 统计该原则下的评估
            principle_assessments = report.principle_assessments.get(principle, [])
            compliant_count = len([a for a in principle_assessments if a.status == ComplianceStatus.COMPLIANT])
            non_compliant_count = len([a for a in principle_assessments if a.status == ComplianceStatus.NON_COMPLIANT])
            
            # 收集建议
            recommendations = []
            for assessment in principle_assessments:
                recommendations.extend(assessment.recommendations)
            unique_recommendations = list(set(recommendations))[:3]  # 取前3个唯一建议
            
            result.append(CompliancePrincipleStatus(
                principle=principle,
                compliance_score=score,
                assessments_count=len(principle_assessments),
                compliant_assessments=compliant_count,
                non_compliant_assessments=non_compliant_count,
                recommendations=unique_recommendations
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get compliance principles status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenant/{tenant_id}/quick-assessment", response_model=Dict[str, Any])
async def perform_quick_compliance_assessment(
    tenant_id: str,
    regulations: List[str] = Body(..., description="Regulations to assess"),
    db: Session = Depends(get_db_session)
):
    """
    执行快速合规评估
    
    提供快速的合规状态检查，适用于日常监控和快速决策。
    """
    try:
        # 验证法规
        valid_regulations = []
        for reg_str in regulations:
            try:
                regulation = DataProtectionRegulation(reg_str.lower())
                valid_regulations.append(regulation)
            except ValueError:
                continue
        
        if not valid_regulations:
            raise HTTPException(
                status_code=400,
                detail="No valid regulations specified"
            )
        
        compliance_engine = DataProtectionComplianceEngine()
        
        # 执行快速评估（不包含跨法规分析以提高速度）
        report = compliance_engine.assess_data_protection_compliance(
            tenant_id=tenant_id,
            regulations=valid_regulations,
            assessment_date=datetime.utcnow(),
            assessed_by=UUID("00000000-0000-0000-0000-000000000000"),
            db=db,
            include_cross_regulation_analysis=False
        )
        
        # 返回简化的结果
        return {
            "assessment_id": report.report_id,
            "tenant_id": tenant_id,
            "assessment_time": report.assessment_date.isoformat(),
            "overall_score": report.overall_compliance_score,
            "overall_status": report.overall_status.value,
            "regulation_scores": report.regulation_scores,
            "critical_issues": len(report.critical_violations),
            "high_risk_gaps": len(report.high_risk_gaps),
            "immediate_actions": report.priority_recommendations[:3],
            "compliance_summary": {
                reg: "compliant" if score >= 90 else "needs_attention" if score >= 70 else "non_compliant"
                for reg, score in report.regulation_scores.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to perform quick compliance assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
async def get_compliance_service_health():
    """
    获取数据保护合规服务健康状态
    
    返回服务状态、支持的法规数量、系统配置等信息。
    """
    try:
        compliance_engine = DataProtectionComplianceEngine()
        
        return {
            "service": "data_protection_compliance",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "supported_regulations": len(DataProtectionRegulation),
            "regulation_list": [reg.value for reg in DataProtectionRegulation],
            "total_requirements": sum(
                len(reqs) for reqs in compliance_engine.regulation_requirements.values()
            ),
            "compliance_thresholds": compliance_engine.compliance_thresholds,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Failed to get compliance service health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def _get_regulation_name(regulation: DataProtectionRegulation) -> str:
    """获取法规名称"""
    names = {
        DataProtectionRegulation.GDPR: "General Data Protection Regulation",
        DataProtectionRegulation.CCPA: "California Consumer Privacy Act",
        DataProtectionRegulation.PIPEDA: "Personal Information Protection and Electronic Documents Act",
        DataProtectionRegulation.LGPD: "Lei Geral de Proteção de Dados",
        DataProtectionRegulation.PDPA_SG: "Personal Data Protection Act (Singapore)",
        DataProtectionRegulation.DPA_UK: "Data Protection Act (UK)",
        DataProtectionRegulation.PRIVACY_ACT_AU: "Privacy Act (Australia)",
        DataProtectionRegulation.APPI: "Act on Protection of Personal Information (Japan)"
    }
    return names.get(regulation, regulation.value.upper())


def _get_regulation_jurisdiction(regulation: DataProtectionRegulation) -> str:
    """获取法规管辖区域"""
    jurisdictions = {
        DataProtectionRegulation.GDPR: "European Union",
        DataProtectionRegulation.CCPA: "California, USA",
        DataProtectionRegulation.PIPEDA: "Canada",
        DataProtectionRegulation.LGPD: "Brazil",
        DataProtectionRegulation.PDPA_SG: "Singapore",
        DataProtectionRegulation.DPA_UK: "United Kingdom",
        DataProtectionRegulation.PRIVACY_ACT_AU: "Australia",
        DataProtectionRegulation.APPI: "Japan"
    }
    return jurisdictions.get(regulation, "Unknown")


def _get_regulation_description(regulation: DataProtectionRegulation) -> str:
    """获取法规描述"""
    descriptions = {
        DataProtectionRegulation.GDPR: "Comprehensive data protection regulation for EU residents",
        DataProtectionRegulation.CCPA: "Consumer privacy rights for California residents",
        DataProtectionRegulation.PIPEDA: "Federal privacy law for private sector organizations in Canada",
        DataProtectionRegulation.LGPD: "Brazilian data protection law similar to GDPR",
        DataProtectionRegulation.PDPA_SG: "Singapore's comprehensive data protection framework",
        DataProtectionRegulation.DPA_UK: "UK's data protection law post-Brexit",
        DataProtectionRegulation.PRIVACY_ACT_AU: "Australian privacy protection for personal information",
        DataProtectionRegulation.APPI: "Japan's personal information protection law"
    }
    return descriptions.get(regulation, "Data protection regulation")


def _get_regulation_principles(regulation: DataProtectionRegulation) -> List[str]:
    """获取法规核心原则"""
    principles = {
        DataProtectionRegulation.GDPR: [
            "lawfulness", "fairness", "transparency", "purpose_limitation",
            "data_minimization", "accuracy", "storage_limitation", "security", "accountability"
        ],
        DataProtectionRegulation.CCPA: [
            "transparency", "consumer_rights", "non_discrimination", "security"
        ],
        DataProtectionRegulation.PIPEDA: [
            "accountability", "identifying_purposes", "consent", "limiting_collection",
            "limiting_use", "accuracy", "safeguards", "openness", "individual_access", "challenging_compliance"
        ]
    }
    return principles.get(regulation, ["transparency", "security", "accountability"])


def _get_regulation_rights(regulation: DataProtectionRegulation) -> List[str]:
    """获取法规保护的数据主体权利"""
    rights = {
        DataProtectionRegulation.GDPR: [
            "access", "rectification", "erasure", "restriction", "portability", "objection", "automated_decision"
        ],
        DataProtectionRegulation.CCPA: [
            "access", "erasure", "objection", "portability"
        ],
        DataProtectionRegulation.PIPEDA: [
            "access", "rectification", "consent_withdrawal"
        ]
    }
    return rights.get(regulation, ["access", "rectification"])