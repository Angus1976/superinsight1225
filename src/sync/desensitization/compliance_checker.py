"""
Compliance checking and reporting system.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .models import (
    ComplianceReport,
    DatasetClassification,
    SensitivityLevel,
    PIIEntityType
)

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """
    Compliance checker for data privacy and protection regulations.
    
    Provides compliance assessment, violation detection, and reporting
    capabilities for various data protection regulations.
    """
    
    def __init__(self):
        """Initialize compliance checker."""
        self._compliance_rules = self._initialize_compliance_rules()
        self._regulation_requirements = self._initialize_regulation_requirements()
    
    def assess_compliance(
        self,
        tenant_id: str,
        dataset_classifications: List[DatasetClassification],
        regulation: str = "GDPR"
    ) -> ComplianceReport:
        """
        Assess compliance for a set of datasets.
        
        Args:
            tenant_id: Tenant identifier
            dataset_classifications: List of dataset classifications
            regulation: Regulation to assess against (GDPR, CCPA, HIPAA, etc.)
            
        Returns:
            ComplianceReport with assessment results
        """
        try:
            report = ComplianceReport(tenant_id=tenant_id)
            
            # Basic statistics
            report.datasets_analyzed = len(dataset_classifications)
            
            # Count PII entities
            total_pii = 0
            masked_pii = 0
            violations = []
            
            for dataset in dataset_classifications:
                for field_classification in dataset.field_classifications:
                    entity_count = len(field_classification.entities)
                    total_pii += entity_count
                    
                    # Check if field is properly protected
                    if field_classification.requires_masking:
                        # In a real implementation, we would check if masking rules are applied
                        # For now, assume fields requiring masking are violations if not masked
                        violation = {
                            "dataset_id": dataset.dataset_id,
                            "field_name": field_classification.field_name,
                            "violation_type": "unmasked_sensitive_data",
                            "severity": field_classification.sensitivity_level.value,
                            "entities": [e.entity_type.value for e in field_classification.entities],
                            "recommendation": "Apply appropriate data masking rules"
                        }
                        violations.append(violation)
                    else:
                        masked_pii += entity_count
            
            report.total_pii_entities = total_pii
            report.masked_entities = masked_pii
            report.unmasked_entities = total_pii - masked_pii
            report.violations = violations
            
            # Calculate compliance percentage
            if total_pii > 0:
                report.compliance_percentage = (masked_pii / total_pii) * 100
            else:
                report.compliance_percentage = 100.0
            
            # Determine risk level
            report.risk_level = self._calculate_risk_level(
                report.compliance_percentage,
                violations,
                dataset_classifications
            )
            
            # Generate recommendations
            report.recommendations = self._generate_compliance_recommendations(
                violations,
                report.compliance_percentage,
                regulation
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Compliance assessment failed: {e}")
            return ComplianceReport(tenant_id=tenant_id)
    
    def check_gdpr_compliance(
        self,
        dataset_classification: DatasetClassification
    ) -> Dict[str, Any]:
        """
        Check GDPR compliance for a dataset.
        
        Args:
            dataset_classification: Dataset classification result
            
        Returns:
            GDPR compliance assessment
        """
        compliance_result = {
            "compliant": True,
            "violations": [],
            "requirements_met": [],
            "requirements_failed": [],
            "score": 100.0
        }
        
        # GDPR Article 32 - Security of processing
        security_violations = self._check_security_requirements(dataset_classification)
        if security_violations:
            compliance_result["violations"].extend(security_violations)
            compliance_result["compliant"] = False
            compliance_result["requirements_failed"].append("Article 32 - Security of processing")
        else:
            compliance_result["requirements_met"].append("Article 32 - Security of processing")
        
        # GDPR Article 25 - Data protection by design and by default
        design_violations = self._check_data_protection_by_design(dataset_classification)
        if design_violations:
            compliance_result["violations"].extend(design_violations)
            compliance_result["compliant"] = False
            compliance_result["requirements_failed"].append("Article 25 - Data protection by design")
        else:
            compliance_result["requirements_met"].append("Article 25 - Data protection by design")
        
        # Calculate compliance score
        total_requirements = len(compliance_result["requirements_met"]) + len(compliance_result["requirements_failed"])
        if total_requirements > 0:
            compliance_result["score"] = (len(compliance_result["requirements_met"]) / total_requirements) * 100
        
        return compliance_result
    
    def check_ccpa_compliance(
        self,
        dataset_classification: DatasetClassification
    ) -> Dict[str, Any]:
        """
        Check CCPA compliance for a dataset.
        
        Args:
            dataset_classification: Dataset classification result
            
        Returns:
            CCPA compliance assessment
        """
        compliance_result = {
            "compliant": True,
            "violations": [],
            "requirements_met": [],
            "requirements_failed": [],
            "score": 100.0
        }
        
        # CCPA Section 1798.100 - Consumer's right to know
        transparency_violations = self._check_transparency_requirements(dataset_classification)
        if transparency_violations:
            compliance_result["violations"].extend(transparency_violations)
            compliance_result["compliant"] = False
            compliance_result["requirements_failed"].append("Section 1798.100 - Right to know")
        else:
            compliance_result["requirements_met"].append("Section 1798.100 - Right to know")
        
        # CCPA Section 1798.105 - Consumer's right to delete
        deletion_violations = self._check_deletion_requirements(dataset_classification)
        if deletion_violations:
            compliance_result["violations"].extend(deletion_violations)
            compliance_result["compliant"] = False
            compliance_result["requirements_failed"].append("Section 1798.105 - Right to delete")
        else:
            compliance_result["requirements_met"].append("Section 1798.105 - Right to delete")
        
        # Calculate compliance score
        total_requirements = len(compliance_result["requirements_met"]) + len(compliance_result["requirements_failed"])
        if total_requirements > 0:
            compliance_result["score"] = (len(compliance_result["requirements_met"]) / total_requirements) * 100
        
        return compliance_result
    
    def check_hipaa_compliance(
        self,
        dataset_classification: DatasetClassification
    ) -> Dict[str, Any]:
        """
        Check HIPAA compliance for a dataset.
        
        Args:
            dataset_classification: Dataset classification result
            
        Returns:
            HIPAA compliance assessment
        """
        compliance_result = {
            "compliant": True,
            "violations": [],
            "requirements_met": [],
            "requirements_failed": [],
            "score": 100.0
        }
        
        # HIPAA Security Rule - Administrative safeguards
        admin_violations = self._check_administrative_safeguards(dataset_classification)
        if admin_violations:
            compliance_result["violations"].extend(admin_violations)
            compliance_result["compliant"] = False
            compliance_result["requirements_failed"].append("Administrative Safeguards")
        else:
            compliance_result["requirements_met"].append("Administrative Safeguards")
        
        # HIPAA Security Rule - Physical safeguards
        physical_violations = self._check_physical_safeguards(dataset_classification)
        if physical_violations:
            compliance_result["violations"].extend(physical_violations)
            compliance_result["compliant"] = False
            compliance_result["requirements_failed"].append("Physical Safeguards")
        else:
            compliance_result["requirements_met"].append("Physical Safeguards")
        
        # HIPAA Security Rule - Technical safeguards
        technical_violations = self._check_technical_safeguards(dataset_classification)
        if technical_violations:
            compliance_result["violations"].extend(technical_violations)
            compliance_result["compliant"] = False
            compliance_result["requirements_failed"].append("Technical Safeguards")
        else:
            compliance_result["requirements_met"].append("Technical Safeguards")
        
        # Calculate compliance score
        total_requirements = len(compliance_result["requirements_met"]) + len(compliance_result["requirements_failed"])
        if total_requirements > 0:
            compliance_result["score"] = (len(compliance_result["requirements_met"]) / total_requirements) * 100
        
        return compliance_result
    
    def _check_security_requirements(
        self,
        dataset_classification: DatasetClassification
    ) -> List[Dict[str, Any]]:
        """Check security requirements for data protection."""
        violations = []
        
        # Check for unprotected sensitive data
        for field_classification in dataset_classification.field_classifications:
            if (field_classification.sensitivity_level in [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL] and
                not field_classification.requires_masking):
                violations.append({
                    "type": "insufficient_protection",
                    "field": field_classification.field_name,
                    "severity": field_classification.sensitivity_level.value,
                    "description": "Sensitive data lacks appropriate protection measures"
                })
        
        return violations
    
    def _check_data_protection_by_design(
        self,
        dataset_classification: DatasetClassification
    ) -> List[Dict[str, Any]]:
        """Check data protection by design requirements."""
        violations = []
        
        # Check if privacy measures are implemented by default
        sensitive_fields = [
            f for f in dataset_classification.field_classifications
            if f.sensitivity_level != SensitivityLevel.LOW
        ]
        
        unprotected_fields = [
            f for f in sensitive_fields
            if not f.requires_masking
        ]
        
        if len(unprotected_fields) > len(sensitive_fields) * 0.5:  # More than 50% unprotected
            violations.append({
                "type": "insufficient_default_protection",
                "description": "More than 50% of sensitive fields lack default protection",
                "affected_fields": [f.field_name for f in unprotected_fields]
            })
        
        return violations
    
    def _check_transparency_requirements(
        self,
        dataset_classification: DatasetClassification
    ) -> List[Dict[str, Any]]:
        """Check transparency requirements."""
        violations = []
        
        # Check if personal data is properly identified
        personal_data_fields = [
            f for f in dataset_classification.field_classifications
            if any(e.entity_type == PIIEntityType.PERSON for e in f.entities)
        ]
        
        if personal_data_fields and dataset_classification.compliance_score < 80:
            violations.append({
                "type": "insufficient_transparency",
                "description": "Personal data processing lacks sufficient transparency measures",
                "affected_fields": [f.field_name for f in personal_data_fields]
            })
        
        return violations
    
    def _check_deletion_requirements(
        self,
        dataset_classification: DatasetClassification
    ) -> List[Dict[str, Any]]:
        """Check data deletion requirements."""
        violations = []
        
        # Check if deletion capabilities are supported
        # This would typically check if the system supports data deletion
        # For now, we'll assume it's a configuration issue
        if dataset_classification.overall_sensitivity in [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]:
            violations.append({
                "type": "deletion_capability_required",
                "description": "High sensitivity data requires deletion capability implementation",
                "recommendation": "Implement data deletion mechanisms for consumer rights"
            })
        
        return violations
    
    def _check_administrative_safeguards(
        self,
        dataset_classification: DatasetClassification
    ) -> List[Dict[str, Any]]:
        """Check HIPAA administrative safeguards."""
        violations = []
        
        # Check for PHI (Protected Health Information)
        phi_fields = [
            f for f in dataset_classification.field_classifications
            if f.sensitivity_level == SensitivityLevel.CRITICAL
        ]
        
        if phi_fields:
            violations.append({
                "type": "administrative_safeguards_required",
                "description": "PHI data requires administrative safeguards implementation",
                "affected_fields": [f.field_name for f in phi_fields]
            })
        
        return violations
    
    def _check_physical_safeguards(
        self,
        dataset_classification: DatasetClassification
    ) -> List[Dict[str, Any]]:
        """Check HIPAA physical safeguards."""
        violations = []
        
        # Physical safeguards are typically infrastructure-related
        # For data classification, we focus on data handling requirements
        if dataset_classification.overall_sensitivity == SensitivityLevel.CRITICAL:
            violations.append({
                "type": "physical_safeguards_required",
                "description": "Critical health data requires physical safeguards",
                "recommendation": "Implement physical access controls and secure storage"
            })
        
        return violations
    
    def _check_technical_safeguards(
        self,
        dataset_classification: DatasetClassification
    ) -> List[Dict[str, Any]]:
        """Check HIPAA technical safeguards."""
        violations = []
        
        # Check for unencrypted sensitive health data
        critical_fields = [
            f for f in dataset_classification.field_classifications
            if f.sensitivity_level == SensitivityLevel.CRITICAL and not f.requires_masking
        ]
        
        if critical_fields:
            violations.append({
                "type": "technical_safeguards_insufficient",
                "description": "Critical health data lacks technical safeguards",
                "affected_fields": [f.field_name for f in critical_fields],
                "recommendation": "Implement encryption and access controls"
            })
        
        return violations
    
    def _calculate_risk_level(
        self,
        compliance_percentage: float,
        violations: List[Dict[str, Any]],
        dataset_classifications: List[DatasetClassification]
    ) -> SensitivityLevel:
        """Calculate overall risk level."""
        # Count critical violations
        critical_violations = len([
            v for v in violations
            if v.get("severity") == SensitivityLevel.CRITICAL.value
        ])
        
        # Check for critical datasets
        critical_datasets = len([
            d for d in dataset_classifications
            if d.overall_sensitivity == SensitivityLevel.CRITICAL
        ])
        
        if critical_violations > 0 or compliance_percentage < 50:
            return SensitivityLevel.CRITICAL
        elif compliance_percentage < 70 or critical_datasets > 0:
            return SensitivityLevel.HIGH
        elif compliance_percentage < 85:
            return SensitivityLevel.MEDIUM
        else:
            return SensitivityLevel.LOW
    
    def _generate_compliance_recommendations(
        self,
        violations: List[Dict[str, Any]],
        compliance_percentage: float,
        regulation: str
    ) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []
        
        if compliance_percentage < 70:
            recommendations.append(
                f"URGENT: Compliance score ({compliance_percentage:.1f}%) is below acceptable threshold"
            )
        
        # Group violations by type
        violation_types = {}
        for violation in violations:
            v_type = violation.get("violation_type", "unknown")
            if v_type not in violation_types:
                violation_types[v_type] = 0
            violation_types[v_type] += 1
        
        # Generate specific recommendations
        if "unmasked_sensitive_data" in violation_types:
            count = violation_types["unmasked_sensitive_data"]
            recommendations.append(
                f"Apply data masking to {count} sensitive fields to protect PII"
            )
        
        # Regulation-specific recommendations
        if regulation == "GDPR":
            recommendations.extend([
                "Implement data protection by design and by default",
                "Ensure lawful basis for processing personal data",
                "Provide data subject rights mechanisms"
            ])
        elif regulation == "CCPA":
            recommendations.extend([
                "Implement consumer rights request handling",
                "Provide clear privacy notices",
                "Establish data deletion procedures"
            ])
        elif regulation == "HIPAA":
            recommendations.extend([
                "Implement administrative, physical, and technical safeguards",
                "Ensure PHI encryption and access controls",
                "Establish audit logging for PHI access"
            ])
        
        return recommendations
    
    def _initialize_compliance_rules(self) -> Dict[str, Any]:
        """Initialize compliance rules."""
        return {
            "gdpr": {
                "required_protections": [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL],
                "min_compliance_score": 85.0,
                "mandatory_rights": ["access", "rectification", "erasure", "portability"]
            },
            "ccpa": {
                "required_protections": [SensitivityLevel.MEDIUM, SensitivityLevel.HIGH, SensitivityLevel.CRITICAL],
                "min_compliance_score": 80.0,
                "mandatory_rights": ["know", "delete", "opt_out"]
            },
            "hipaa": {
                "required_protections": [SensitivityLevel.CRITICAL],
                "min_compliance_score": 95.0,
                "mandatory_safeguards": ["administrative", "physical", "technical"]
            }
        }
    
    def _initialize_regulation_requirements(self) -> Dict[str, List[str]]:
        """Initialize regulation requirements."""
        return {
            "GDPR": [
                "Lawfulness, fairness and transparency",
                "Purpose limitation",
                "Data minimisation",
                "Accuracy",
                "Storage limitation",
                "Integrity and confidentiality",
                "Accountability"
            ],
            "CCPA": [
                "Right to know",
                "Right to delete",
                "Right to opt-out",
                "Right to non-discrimination"
            ],
            "HIPAA": [
                "Administrative safeguards",
                "Physical safeguards", 
                "Technical safeguards"
            ]
        }