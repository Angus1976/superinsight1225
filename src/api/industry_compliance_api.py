"""
Industry-Specific Compliance API Endpoints.

Provides REST API endpoints for industry-specific compliance assessments
including HIPAA, PCI-DSS, PIPL, and other regulatory frameworks.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.compliance.industry_specific_compliance import (
    IndustryComplianceManager,
    IndustryType,
    ComplianceFramework,
    ComplianceStatus,
    HIPAAComplianceChecker,
    PCIDSSComplianceChecker,
    PIPLComplianceChecker
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/compliance/industry", tags=["Industry Compliance"])


# Request/Response Models
class IndustryComplianceRequest(BaseModel):
    """行业合规评估请求"""
    tenant_id: str = Field(..., description="租户ID")
    industry_type: str = Field(..., description="行业类型")
    frameworks: Optional[List[str]] = Field(None, description="指定的合规框架")
    data_types: Optional[List[str]] = Field(None, description="处理的数据类型")
    geographic_regions: Optional[List[str]] = Field(None, description="运营地区")


class FrameworkAssessmentRequest(BaseModel):
    """框架评估请求"""
    tenant_id: str = Field(..., description="租户ID")
    framework: str = Field(..., description="合规框架")


class ComplianceResponse(BaseModel):
    """合规评估响应"""
    success: bool
    assessment_id: Optional[str] = None
    overall_score: Optional[float] = None
    status: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None


# API Endpoints
@router.post("/assess", response_model=ComplianceResponse)
async def assess_industry_compliance(
    request: IndustryComplianceRequest,
    db: Session = Depends(get_db_session)
):
    """
    执行行业特定合规评估
    
    根据行业类型和指定的合规框架执行全面的合规评估。
    """
    try:
        manager = IndustryComplianceManager()
        
        # 解析行业类型
        try:
            industry_type = IndustryType(request.industry_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid industry type: {request.industry_type}"
            )
        
        # 解析合规框架
        frameworks = None
        if request.frameworks:
            frameworks = []
            for f in request.frameworks:
                try:
                    frameworks.append(ComplianceFramework(f))
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid compliance framework: {f}"
                    )
        
        # 执行评估
        assessment = manager.assess_industry_compliance(
            tenant_id=request.tenant_id,
            industry_type=industry_type,
            assessment_date=datetime.utcnow(),
            db=db,
            frameworks=frameworks
        )
        
        # 生成摘要
        summary = manager.generate_compliance_summary(assessment)
        
        return ComplianceResponse(
            success=True,
            assessment_id=assessment.assessment_id,
            overall_score=assessment.overall_compliance_score,
            status=assessment.overall_status.value,
            message="Industry compliance assessment completed successfully",
            data=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Industry compliance assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hipaa/assess", response_model=ComplianceResponse)
async def assess_hipaa_compliance(
    request: FrameworkAssessmentRequest,
    db: Session = Depends(get_db_session)
):
    """
    执行HIPAA合规评估
    
    评估医疗保健行业的HIPAA合规性，包括隐私规则、安全规则和违规通知规则。
    """
    try:
        checker = HIPAAComplianceChecker()
        assessment = checker.assess_hipaa_compliance(
            tenant_id=request.tenant_id,
            assessment_date=datetime.utcnow(),
            db=db
        )
        
        return ComplianceResponse(
            success=True,
            overall_score=assessment.get("overall_score", 0),
            status=assessment.get("status", "unknown"),
            message="HIPAA compliance assessment completed",
            data=assessment
        )
        
    except Exception as e:
        logger.error(f"HIPAA assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pci-dss/assess", response_model=ComplianceResponse)
async def assess_pci_dss_compliance(
    request: FrameworkAssessmentRequest,
    db: Session = Depends(get_db_session)
):
    """
    执行PCI-DSS合规评估
    
    评估支付卡行业数据安全标准合规性，包括12项主要要求。
    """
    try:
        checker = PCIDSSComplianceChecker()
        assessment = checker.assess_pci_compliance(
            tenant_id=request.tenant_id,
            assessment_date=datetime.utcnow(),
            db=db
        )
        
        return ComplianceResponse(
            success=True,
            overall_score=assessment.get("overall_score", 0),
            status=assessment.get("status", "unknown"),
            message="PCI-DSS compliance assessment completed",
            data=assessment
        )
        
    except Exception as e:
        logger.error(f"PCI-DSS assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipl/assess", response_model=ComplianceResponse)
async def assess_pipl_compliance(
    request: FrameworkAssessmentRequest,
    db: Session = Depends(get_db_session)
):
    """
    执行PIPL合规评估
    
    评估中国《个人信息保护法》合规性，包括个人信息处理规则、
    敏感数据处理、跨境传输等要求。
    """
    try:
        checker = PIPLComplianceChecker()
        assessment = checker.assess_pipl_compliance(
            tenant_id=request.tenant_id,
            assessment_date=datetime.utcnow(),
            db=db
        )
        
        return ComplianceResponse(
            success=True,
            overall_score=assessment.get("overall_score", 0),
            status=assessment.get("status", "unknown"),
            message="PIPL compliance assessment completed",
            data=assessment
        )
        
    except Exception as e:
        logger.error(f"PIPL assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frameworks", response_model=dict)
async def get_applicable_frameworks(
    industry_type: str = Query(..., description="行业类型"),
    data_types: Optional[str] = Query(None, description="数据类型，逗号分隔"),
    geographic_regions: Optional[str] = Query(None, description="地区，逗号分隔")
):
    """
    获取适用的合规框架
    
    根据行业类型、数据类型和运营地区返回适用的合规框架列表。
    """
    try:
        manager = IndustryComplianceManager()
        
        # 解析行业类型
        try:
            industry = IndustryType(industry_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid industry type: {industry_type}"
            )
        
        # 解析数据类型和地区
        data_type_list = data_types.split(",") if data_types else None
        region_list = geographic_regions.split(",") if geographic_regions else None
        
        frameworks = manager.get_applicable_frameworks(
            industry_type=industry,
            data_types=data_type_list,
            geographic_regions=region_list
        )
        
        return {
            "success": True,
            "industry_type": industry_type,
            "applicable_frameworks": [f.value for f in frameworks],
            "framework_details": [
                {
                    "framework": f.value,
                    "description": _get_framework_description(f)
                }
                for f in frameworks
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get applicable frameworks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industries", response_model=dict)
async def list_supported_industries():
    """
    列出支持的行业类型
    
    返回系统支持的所有行业类型及其默认合规框架。
    """
    manager = IndustryComplianceManager()
    
    industries = []
    for industry in IndustryType:
        frameworks = manager.industry_frameworks.get(industry, [])
        industries.append({
            "industry_type": industry.value,
            "display_name": _get_industry_display_name(industry),
            "default_frameworks": [f.value for f in frameworks]
        })
    
    return {
        "success": True,
        "industries": industries
    }


@router.get("/frameworks/list", response_model=dict)
async def list_supported_frameworks():
    """
    列出支持的合规框架
    
    返回系统支持的所有合规框架及其描述。
    """
    frameworks = []
    for framework in ComplianceFramework:
        frameworks.append({
            "framework": framework.value,
            "display_name": _get_framework_display_name(framework),
            "description": _get_framework_description(framework)
        })
    
    return {
        "success": True,
        "frameworks": frameworks
    }


@router.get("/health", response_model=dict)
async def health_check():
    """
    健康检查
    
    检查行业合规服务的健康状态。
    """
    return {
        "status": "healthy",
        "service": "industry_compliance",
        "timestamp": datetime.utcnow().isoformat(),
        "supported_frameworks": [f.value for f in ComplianceFramework],
        "supported_industries": [i.value for i in IndustryType]
    }


# Helper functions
def _get_framework_description(framework: ComplianceFramework) -> str:
    """获取框架描述"""
    descriptions = {
        ComplianceFramework.HIPAA: "Health Insurance Portability and Accountability Act - 美国医疗保健数据保护法规",
        ComplianceFramework.PCI_DSS: "Payment Card Industry Data Security Standard - 支付卡行业数据安全标准",
        ComplianceFramework.PIPL: "Personal Information Protection Law - 中国个人信息保护法",
        ComplianceFramework.FERPA: "Family Educational Rights and Privacy Act - 美国教育隐私法",
        ComplianceFramework.GLBA: "Gramm-Leach-Bliley Act - 美国金融服务现代化法",
        ComplianceFramework.NIST_CSF: "NIST Cybersecurity Framework - 美国国家标准与技术研究院网络安全框架",
        ComplianceFramework.SOC2: "Service Organization Control 2 - 服务组织控制报告"
    }
    return descriptions.get(framework, "No description available")


def _get_framework_display_name(framework: ComplianceFramework) -> str:
    """获取框架显示名称"""
    names = {
        ComplianceFramework.HIPAA: "HIPAA",
        ComplianceFramework.PCI_DSS: "PCI-DSS",
        ComplianceFramework.PIPL: "PIPL (个人信息保护法)",
        ComplianceFramework.FERPA: "FERPA",
        ComplianceFramework.GLBA: "GLBA",
        ComplianceFramework.NIST_CSF: "NIST CSF",
        ComplianceFramework.SOC2: "SOC 2"
    }
    return names.get(framework, framework.value)


def _get_industry_display_name(industry: IndustryType) -> str:
    """获取行业显示名称"""
    names = {
        IndustryType.HEALTHCARE: "医疗保健 (Healthcare)",
        IndustryType.FINANCIAL_SERVICES: "金融服务 (Financial Services)",
        IndustryType.EDUCATION: "教育 (Education)",
        IndustryType.GOVERNMENT: "政府 (Government)",
        IndustryType.RETAIL: "零售 (Retail)",
        IndustryType.TECHNOLOGY: "科技 (Technology)",
        IndustryType.MANUFACTURING: "制造业 (Manufacturing)"
    }
    return names.get(industry, industry.value)
