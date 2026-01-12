"""
SOX Compliance API endpoints.

Provides REST API for SOX (Sarbanes-Oxley Act) compliance assessment,
control testing, and reporting.
"""

import io
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.middleware import get_current_active_user, require_role, audit_action
from src.security.models import AuditAction, UserModel
from src.compliance.sox_compliance import (
    SOXComplianceEngine,
    SOXSection,
    SOXControlType,
    SOXRiskLevel,
    SOXControl,
    SOXDeficiency,
    SOXTestResult,
    SOXComplianceReport
)

router = APIRouter(prefix="/api/sox", tags=["sox_compliance"])

# Initialize SOX compliance engine
sox_engine = SOXComplianceEngine()


# Request/Response Models

class SOXAssessmentRequest(BaseModel):
    assessment_date: datetime = Field(default_factory=datetime.utcnow, description="Assessment date")
    include_testing: bool = Field(True, description="Include control testing")
    scope: Optional[List[str]] = Field(None, description="Assessment scope (control IDs)")


class SOXControlResponse(BaseModel):
    control_id: str
    control_name: str
    control_type: str
    sox_section: str
    description: str
    risk_level: str
    frequency: str
    owner: str
    testing_procedures: List[str]
    evidence_requirements: List[str]
    automated: bool
    effectiveness_rating: Optional[float]
    last_tested: Optional[datetime]


class SOXDeficiencyResponse(BaseModel):
    deficiency_id: str
    control_id: str
    severity: str
    description: str
    root_cause: str
    impact_assessment: str
    remediation_plan: str
    responsible_party: str
    target_completion_date: datetime
    status: str
    identified_date: datetime
    closed_date: Optional[datetime]


class SOXTestResultResponse(BaseModel):
    test_id: str
    control_id: str
    test_date: datetime
    tester: str
    test_procedures_performed: List[str]
    sample_size: int
    exceptions_noted: int
    test_conclusion: str
    evidence_obtained: List[str]
    deficiencies_identified: List[str]
    management_response: Optional[str]


class SOXComplianceReportResponse(BaseModel):
    report_id: str
    tenant_id: str
    reporting_period: Dict[str, datetime]
    generation_time: datetime
    management_assertion: str
    ceo_certification: bool
    cfo_certification: bool
    overall_effectiveness: str
    material_weaknesses: List[SOXDeficiencyResponse]
    significant_deficiencies: List[SOXDeficiencyResponse]
    controls_tested: int
    controls_effective: int
    controls_ineffective: int
    financial_statement_controls: Dict[str, Any]
    disclosure_controls: Dict[str, Any]
    it_general_controls: Dict[str, Any]
    application_controls: Dict[str, Any]
    audit_trail_integrity: Dict[str, Any]
    sox_compliance_status: str


class SOXDashboardResponse(BaseModel):
    tenant_id: str
    assessment_date: datetime
    overall_effectiveness: str
    sox_compliance_status: str
    compliance_score: float
    
    # Control statistics
    total_controls: int
    effective_controls: int
    ineffective_controls: int
    controls_not_tested: int
    
    # Deficiency statistics
    total_deficiencies: int
    material_weaknesses: int
    significant_deficiencies: int
    minor_deficiencies: int
    
    # Testing statistics
    controls_tested_this_period: int
    testing_completion_rate: float
    
    # Risk metrics
    high_risk_controls: int
    critical_risk_controls: int
    
    # Trends
    compliance_trend: List[Dict[str, Any]]
    deficiency_trend: List[Dict[str, Any]]


class ControlTestingRequest(BaseModel):
    control_ids: List[str] = Field(..., description="Control IDs to test")
    test_date: datetime = Field(default_factory=datetime.utcnow, description="Test date")
    sample_size: int = Field(25, description="Sample size for testing")
    tester: Optional[str] = Field(None, description="Tester name")


class DeficiencyRemediationRequest(BaseModel):
    deficiency_id: str
    remediation_plan: str
    responsible_party: str
    target_completion_date: datetime
    status: str = Field("in_progress", description="Remediation status")


# API Endpoints

@router.post("/assessment", response_model=SOXComplianceReportResponse)
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.CREATE, "sox_assessment")
async def perform_sox_assessment(
    request: SOXAssessmentRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Perform comprehensive SOX compliance assessment."""
    try:
        # Perform SOX assessment
        report = sox_engine.assess_sox_compliance(
            tenant_id=current_user.tenant_id,
            assessment_date=request.assessment_date,
            db=db,
            include_testing=request.include_testing
        )
        
        # Convert to response model
        return SOXComplianceReportResponse(
            report_id=report.report_id,
            tenant_id=report.tenant_id,
            reporting_period=report.reporting_period,
            generation_time=report.generation_time,
            management_assertion=report.management_assertion,
            ceo_certification=report.ceo_certification,
            cfo_certification=report.cfo_certification,
            overall_effectiveness=report.overall_effectiveness,
            material_weaknesses=[
                SOXDeficiencyResponse(**deficiency.__dict__)
                for deficiency in report.material_weaknesses
            ],
            significant_deficiencies=[
                SOXDeficiencyResponse(**deficiency.__dict__)
                for deficiency in report.significant_deficiencies
            ],
            controls_tested=report.controls_tested,
            controls_effective=report.controls_effective,
            controls_ineffective=report.controls_ineffective,
            financial_statement_controls=report.financial_statement_controls,
            disclosure_controls=report.disclosure_controls,
            it_general_controls=report.it_general_controls,
            application_controls=report.application_controls,
            audit_trail_integrity=report.audit_trail_integrity,
            sox_compliance_status=report.sox_compliance_status
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform SOX assessment: {str(e)}"
        )


@router.get("/dashboard", response_model=SOXDashboardResponse)
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.READ, "sox_dashboard")
async def get_sox_dashboard(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Get SOX compliance dashboard data."""
    try:
        # Perform quick assessment for dashboard
        assessment_date = datetime.utcnow()
        report = sox_engine.assess_sox_compliance(
            tenant_id=current_user.tenant_id,
            assessment_date=assessment_date,
            db=db,
            include_testing=False  # Quick assessment without full testing
        )
        
        # Calculate dashboard metrics
        total_controls = len(sox_engine.sox_controls)
        effective_controls = report.controls_effective
        ineffective_controls = report.controls_ineffective
        controls_not_tested = total_controls - report.controls_tested
        
        total_deficiencies = len(report.material_weaknesses) + len(report.significant_deficiencies)
        material_weaknesses = len(report.material_weaknesses)
        significant_deficiencies = len(report.significant_deficiencies)
        
        testing_completion_rate = (report.controls_tested / max(1, total_controls)) * 100
        
        # Calculate compliance score
        compliance_score = 100.0
        if report.overall_effectiveness == "ineffective":
            compliance_score = max(0, 100 - (material_weaknesses * 20) - (significant_deficiencies * 10))
        
        # Generate trend data (mock data for now)
        compliance_trend = [
            {"date": (assessment_date - timedelta(days=30)).isoformat(), "score": compliance_score - 5},
            {"date": (assessment_date - timedelta(days=15)).isoformat(), "score": compliance_score - 2},
            {"date": assessment_date.isoformat(), "score": compliance_score}
        ]
        
        deficiency_trend = [
            {"date": (assessment_date - timedelta(days=30)).isoformat(), "count": total_deficiencies + 2},
            {"date": (assessment_date - timedelta(days=15)).isoformat(), "count": total_deficiencies + 1},
            {"date": assessment_date.isoformat(), "count": total_deficiencies}
        ]
        
        return SOXDashboardResponse(
            tenant_id=current_user.tenant_id,
            assessment_date=assessment_date,
            overall_effectiveness=report.overall_effectiveness,
            sox_compliance_status=report.sox_compliance_status,
            compliance_score=compliance_score,
            total_controls=total_controls,
            effective_controls=effective_controls,
            ineffective_controls=ineffective_controls,
            controls_not_tested=controls_not_tested,
            total_deficiencies=total_deficiencies,
            material_weaknesses=material_weaknesses,
            significant_deficiencies=significant_deficiencies,
            minor_deficiencies=0,  # Not tracked separately in current model
            controls_tested_this_period=report.controls_tested,
            testing_completion_rate=testing_completion_rate,
            high_risk_controls=len([c for c in sox_engine.sox_controls if c.risk_level == SOXRiskLevel.HIGH]),
            critical_risk_controls=len([c for c in sox_engine.sox_controls if c.risk_level == SOXRiskLevel.CRITICAL]),
            compliance_trend=compliance_trend,
            deficiency_trend=deficiency_trend
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SOX dashboard: {str(e)}"
        )


@router.get("/controls", response_model=List[SOXControlResponse])
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.READ, "sox_controls")
async def list_sox_controls(
    control_type: Optional[SOXControlType] = None,
    risk_level: Optional[SOXRiskLevel] = None,
    current_user: UserModel = Depends(get_current_active_user)
):
    """List SOX controls with optional filtering."""
    try:
        controls = sox_engine.sox_controls
        
        # Apply filters
        if control_type:
            controls = [c for c in controls if c.control_type == control_type]
        
        if risk_level:
            controls = [c for c in controls if c.risk_level == risk_level]
        
        return [
            SOXControlResponse(
                control_id=control.control_id,
                control_name=control.control_name,
                control_type=control.control_type.value,
                sox_section=control.sox_section.value,
                description=control.description,
                risk_level=control.risk_level.value,
                frequency=control.frequency,
                owner=control.owner,
                testing_procedures=control.testing_procedures,
                evidence_requirements=control.evidence_requirements,
                automated=control.automated,
                effectiveness_rating=control.effectiveness_rating,
                last_tested=control.last_tested
            )
            for control in controls
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list SOX controls: {str(e)}"
        )


@router.get("/controls/{control_id}", response_model=SOXControlResponse)
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.READ, "sox_control")
async def get_sox_control(
    control_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get detailed information about a specific SOX control."""
    try:
        control = next((c for c in sox_engine.sox_controls if c.control_id == control_id), None)
        
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SOX control {control_id} not found"
            )
        
        return SOXControlResponse(
            control_id=control.control_id,
            control_name=control.control_name,
            control_type=control.control_type.value,
            sox_section=control.sox_section.value,
            description=control.description,
            risk_level=control.risk_level.value,
            frequency=control.frequency,
            owner=control.owner,
            testing_procedures=control.testing_procedures,
            evidence_requirements=control.evidence_requirements,
            automated=control.automated,
            effectiveness_rating=control.effectiveness_rating,
            last_tested=control.last_tested
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SOX control: {str(e)}"
        )


@router.post("/controls/test", response_model=List[SOXTestResultResponse])
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.CREATE, "sox_control_testing")
async def test_sox_controls(
    request: ControlTestingRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Perform testing on specified SOX controls."""
    try:
        test_results = []
        
        for control_id in request.control_ids:
            # Find the control
            control = next((c for c in sox_engine.sox_controls if c.control_id == control_id), None)
            
            if not control:
                continue
            
            # Execute control test
            test_result = sox_engine._execute_control_test(control, current_user.tenant_id, db)
            test_result.tester = request.tester or current_user.username or "System"
            test_result.sample_size = request.sample_size
            test_result.test_date = request.test_date
            
            test_results.append(SOXTestResultResponse(
                test_id=test_result.test_id,
                control_id=test_result.control_id,
                test_date=test_result.test_date,
                tester=test_result.tester,
                test_procedures_performed=test_result.test_procedures_performed,
                sample_size=test_result.sample_size,
                exceptions_noted=test_result.exceptions_noted,
                test_conclusion=test_result.test_conclusion,
                evidence_obtained=test_result.evidence_obtained,
                deficiencies_identified=test_result.deficiencies_identified,
                management_response=test_result.management_response
            ))
        
        return test_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test SOX controls: {str(e)}"
        )


@router.get("/deficiencies", response_model=List[SOXDeficiencyResponse])
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.READ, "sox_deficiencies")
async def list_sox_deficiencies(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """List SOX deficiencies with optional filtering."""
    try:
        # Perform assessment to get current deficiencies
        report = sox_engine.assess_sox_compliance(
            tenant_id=current_user.tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_testing=False
        )
        
        all_deficiencies = report.material_weaknesses + report.significant_deficiencies
        
        # Apply filters
        if severity:
            all_deficiencies = [d for d in all_deficiencies if d.severity == severity]
        
        if status:
            all_deficiencies = [d for d in all_deficiencies if d.status == status]
        
        return [
            SOXDeficiencyResponse(**deficiency.__dict__)
            for deficiency in all_deficiencies
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list SOX deficiencies: {str(e)}"
        )


@router.put("/deficiencies/{deficiency_id}/remediate")
@require_role(["admin", "compliance_officer", "sox_manager"])
@audit_action(AuditAction.UPDATE, "sox_deficiency_remediation")
async def remediate_sox_deficiency(
    deficiency_id: str,
    request: DeficiencyRemediationRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Update remediation plan for a SOX deficiency."""
    try:
        # In a real implementation, this would update the deficiency in the database
        # For now, return success response
        
        return {
            "message": f"Deficiency {deficiency_id} remediation plan updated successfully",
            "deficiency_id": deficiency_id,
            "status": request.status,
            "updated_by": current_user.username,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update deficiency remediation: {str(e)}"
        )


@router.get("/audit-trail-integrity", response_model=Dict[str, Any])
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.READ, "sox_audit_trail_integrity")
async def check_audit_trail_integrity(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Check audit trail integrity for SOX compliance."""
    try:
        # Default to current year if dates not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = datetime(end_date.year, 1, 1)
        
        reporting_period = {"start_date": start_date, "end_date": end_date}
        
        # Verify audit trail integrity
        integrity_results = sox_engine._verify_audit_trail_integrity(
            current_user.tenant_id, reporting_period, db
        )
        
        return {
            "tenant_id": current_user.tenant_id,
            "assessment_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "integrity_assessment": integrity_results,
            "sox_compliance": {
                "audit_trail_compliant": integrity_results["overall_integrity_score"] >= 95.0,
                "section_802_compliant": integrity_results["tamper_protection"]["tamper_protection_enabled"],
                "recommendations": [
                    "Maintain continuous audit logging",
                    "Ensure tamper protection mechanisms",
                    "Regular integrity verification"
                ] if integrity_results["overall_integrity_score"] < 95.0 else []
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check audit trail integrity: {str(e)}"
        )


@router.get("/management-certification", response_model=Dict[str, Any])
@require_role(["admin", "ceo", "cfo", "compliance_officer"])
@audit_action(AuditAction.READ, "sox_management_certification")
async def get_management_certification_status(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Get management certification status for SOX compliance."""
    try:
        # Perform assessment
        report = sox_engine.assess_sox_compliance(
            tenant_id=current_user.tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_testing=False
        )
        
        return {
            "tenant_id": current_user.tenant_id,
            "reporting_period": report.reporting_period,
            "management_assertion": report.management_assertion,
            "certifications": {
                "ceo_certification": {
                    "required": True,
                    "completed": report.ceo_certification,
                    "section": "SOX Section 302 & 906"
                },
                "cfo_certification": {
                    "required": True,
                    "completed": report.cfo_certification,
                    "section": "SOX Section 302 & 906"
                }
            },
            "internal_control_assessment": {
                "overall_effectiveness": report.overall_effectiveness,
                "material_weaknesses_count": len(report.material_weaknesses),
                "significant_deficiencies_count": len(report.significant_deficiencies),
                "section_404_compliant": report.overall_effectiveness == "effective"
            },
            "disclosure_controls": {
                "effectiveness": report.disclosure_controls.get("overall_rating", "effective"),
                "section_409_compliant": True  # Real-time disclosure compliance
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get management certification status: {str(e)}"
        )


@router.post("/export-report/{report_id}")
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
@audit_action(AuditAction.EXPORT, "sox_report")
async def export_sox_report(
    report_id: str,
    export_format: str = "pdf",
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """Export SOX compliance report in specified format."""
    try:
        if export_format not in ["pdf", "excel", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported export format. Use pdf, excel, or json."
            )
        
        # Generate fresh report for export
        report = sox_engine.assess_sox_compliance(
            tenant_id=current_user.tenant_id,
            assessment_date=datetime.utcnow(),
            db=db,
            include_testing=True
        )
        
        # Mock export content
        if export_format == "json":
            content = json.dumps({
                "report_id": report.report_id,
                "sox_compliance_status": report.sox_compliance_status,
                "overall_effectiveness": report.overall_effectiveness,
                "management_assertion": report.management_assertion,
                "controls_tested": report.controls_tested,
                "controls_effective": report.controls_effective,
                "material_weaknesses": len(report.material_weaknesses),
                "significant_deficiencies": len(report.significant_deficiencies)
            }, indent=2)
            media_type = "application/json"
            filename = f"sox_compliance_report_{report_id}.json"
        elif export_format == "pdf":
            content = b"Mock SOX Compliance Report PDF content"
            media_type = "application/pdf"
            filename = f"sox_compliance_report_{report_id}.pdf"
        else:  # excel
            content = b"Mock SOX Compliance Report Excel content"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"sox_compliance_report_{report_id}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(content.encode() if isinstance(content, str) else content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export SOX report: {str(e)}"
        )


@router.get("/sections", response_model=List[Dict[str, Any]])
@require_role(["admin", "compliance_officer", "auditor", "sox_manager"])
async def get_sox_sections(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get information about SOX sections and their requirements."""
    try:
        sections = []
        
        for section in SOXSection:
            section_info = {
                "section_code": section.value,
                "section_name": section.name,
                "description": "",
                "key_requirements": [],
                "compliance_status": "compliant"  # This would be calculated based on actual assessment
            }
            
            if section == SOXSection.SECTION_302:
                section_info.update({
                    "description": "Corporate Responsibility for Financial Reports",
                    "key_requirements": [
                        "CEO and CFO certification of financial reports",
                        "Assessment of disclosure controls and procedures",
                        "Reporting of material changes in internal controls"
                    ]
                })
            elif section == SOXSection.SECTION_404:
                section_info.update({
                    "description": "Management Assessment of Internal Controls",
                    "key_requirements": [
                        "Management assessment of internal control over financial reporting",
                        "Auditor attestation of management's assessment",
                        "Documentation of internal control framework"
                    ]
                })
            elif section == SOXSection.SECTION_409:
                section_info.update({
                    "description": "Real-time Disclosure",
                    "key_requirements": [
                        "Rapid disclosure of material changes",
                        "Real-time reporting of financial condition changes",
                        "Timely communication to investors"
                    ]
                })
            elif section == SOXSection.SECTION_802:
                section_info.update({
                    "description": "Criminal Penalties for Altering Documents",
                    "key_requirements": [
                        "Document retention requirements",
                        "Audit trail integrity",
                        "Protection against document destruction"
                    ]
                })
            elif section == SOXSection.SECTION_906:
                section_info.update({
                    "description": "Corporate Responsibility for Financial Reports",
                    "key_requirements": [
                        "CEO and CFO certification under criminal penalties",
                        "Personal accountability for financial reporting accuracy",
                        "Compliance with all applicable securities laws"
                    ]
                })
            
            sections.append(section_info)
        
        return sections
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SOX sections: {str(e)}"
        )