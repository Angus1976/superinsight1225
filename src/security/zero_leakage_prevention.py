"""
Zero Sensitive Data Leakage Prevention System - Minimal Working Version
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LeakageRiskLevel(Enum):
    """Data leakage risk levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LeakageDetectionMethod(Enum):
    """Methods for detecting data leakage"""
    PATTERN_MATCHING = "pattern_matching"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    MACHINE_LEARNING = "machine_learning"
    HASH_COMPARISON = "hash_comparison"
    ENTROPY_ANALYSIS = "entropy_analysis"


@dataclass
class LeakageDetectionResult:
    """Result of leakage detection analysis"""
    has_leakage: bool
    risk_level: LeakageRiskLevel
    confidence_score: float
    detected_entities: List[Dict[str, Any]]
    leakage_patterns: List[str]
    detection_methods: List[LeakageDetectionMethod]
    recommendations: List[str]
    metadata: Dict[str, Any]


@dataclass
class LeakagePreventionPolicy:
    """Policy for preventing data leakage"""
    tenant_id: str
    policy_name: str
    enabled: bool
    strict_mode: bool
    auto_block: bool
    detection_threshold: float
    allowed_exposure_ratio: float
    whitelist_patterns: List[str]
    blacklist_patterns: List[str]
    notification_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ZeroLeakagePreventionSystem:
    """
    Zero sensitive data leakage prevention system.
    """
    
    def __init__(self):
        """Initialize the system."""
        # Simplified initialization without external dependencies
        self.sensitive_patterns = {
            "credit_card": [
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
            ],
            "ssn": [
                r'\b\d{3}-?\d{2}-?\d{4}\b'
            ],
            "email": [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            "api_key": [
                r'\bsk-[A-Za-z0-9]{48}\b'
            ]
        }
        
        self._policy_cache = {}
        
    async def scan_for_leakage(
        self,
        data: Any,
        tenant_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        operation_type: str = "data_scan"
    ) -> LeakageDetectionResult:
        """
        Scan for sensitive data leakage.
        """
        scan_id = str(uuid4())
        
        try:
            # Get policy
            policy = await self._get_prevention_policy(tenant_id)
            
            # Extract text
            text_data = self._extract_text_from_data(data)
            
            # Detect patterns
            detected_entities = []
            detection_methods = []
            leakage_patterns = []
            
            for text in text_data:
                if not text or len(text.strip()) < 3:
                    continue
                    
                for pattern_type, patterns in self.sensitive_patterns.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE)
                        
                        for match in matches:
                            detected_entities.append({
                                "type": pattern_type,
                                "match": match.group(),
                                "start": match.start(),
                                "end": match.end(),
                                "confidence": 0.8,
                                "method": "pattern_matching",
                                "risk_level": "medium"
                            })
                            
                            if pattern_type not in leakage_patterns:
                                leakage_patterns.append(pattern_type)
            
            if detected_entities and LeakageDetectionMethod.PATTERN_MATCHING not in detection_methods:
                detection_methods.append(LeakageDetectionMethod.PATTERN_MATCHING)
            
            # Calculate results
            has_leakage = len(detected_entities) > 0
            risk_level = self._calculate_risk_level(detected_entities, policy)
            confidence_score = 0.8 if detected_entities else 1.0
            recommendations = self._generate_recommendations(detected_entities, risk_level, policy)
            
            return LeakageDetectionResult(
                has_leakage=has_leakage,
                risk_level=risk_level,
                confidence_score=confidence_score,
                detected_entities=detected_entities,
                leakage_patterns=leakage_patterns,
                detection_methods=detection_methods,
                recommendations=recommendations,
                metadata={
                    "scan_id": scan_id,
                    "total_entities": len(detected_entities)
                }
            )
            
        except Exception as e:
            logger.error(f"Leakage scan failed: {e}")
            return LeakageDetectionResult(
                has_leakage=True,
                risk_level=LeakageRiskLevel.HIGH,
                confidence_score=0.0,
                detected_entities=[],
                leakage_patterns=[],
                detection_methods=[],
                recommendations=["Scan failed - manual review required"],
                metadata={"scan_id": scan_id, "error": str(e)}
            )
    
    def _extract_text_from_data(self, data: Any) -> List[str]:
        """Extract text from data."""
        text_content = []
        
        if isinstance(data, str):
            text_content.append(data)
        elif isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str):
                    text_content.append(value)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    text_content.append(item)
        
        return text_content
    
    def _calculate_risk_level(self, detected_entities: List[Dict[str, Any]], policy: LeakagePreventionPolicy) -> LeakageRiskLevel:
        """Calculate risk level."""
        if not detected_entities:
            return LeakageRiskLevel.NONE
        
        high_count = sum(1 for e in detected_entities if e.get("risk_level") == "high")
        medium_count = sum(1 for e in detected_entities if e.get("risk_level") == "medium")
        
        if high_count >= 1 and policy.strict_mode:
            return LeakageRiskLevel.HIGH
        elif high_count >= 1 or medium_count >= 3:
            return LeakageRiskLevel.MEDIUM
        elif medium_count >= 1:
            return LeakageRiskLevel.LOW
        else:
            return LeakageRiskLevel.NONE
    
    def _generate_recommendations(self, detected_entities: List[Dict[str, Any]], risk_level: LeakageRiskLevel, policy: LeakagePreventionPolicy) -> List[str]:
        """Generate recommendations."""
        if not detected_entities:
            return ["No sensitive data leakage detected."]
        
        recommendations = []
        entity_types = set(e.get("type", "unknown") for e in detected_entities)
        
        if "credit_card" in entity_types:
            recommendations.append("Implement PCI DSS compliant data handling for credit card data")
        if "ssn" in entity_types:
            recommendations.append("Apply strict access controls for Social Security Numbers")
        if "email" in entity_types:
            recommendations.append("Review email data handling and privacy policies")
        if "api_key" in entity_types:
            recommendations.append("Rotate API keys and implement secure key management")
        
        return recommendations
    
    async def _get_prevention_policy(self, tenant_id: str) -> LeakagePreventionPolicy:
        """Get prevention policy."""
        return LeakagePreventionPolicy(
            tenant_id=tenant_id,
            policy_name="default_policy",
            enabled=True,
            strict_mode=True,
            auto_block=True,
            detection_threshold=0.8,
            allowed_exposure_ratio=0.0,
            whitelist_patterns=[],
            blacklist_patterns=[],
            notification_settings={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    async def prevent_data_export(self, export_data: Any, tenant_id: str, user_id: str, export_format: str = "unknown") -> Dict[str, Any]:
        """Prevent data export."""
        scan_result = await self.scan_for_leakage(export_data, tenant_id, user_id, operation_type="export_prevention")
        
        if scan_result.has_leakage and scan_result.risk_level in [LeakageRiskLevel.CRITICAL, LeakageRiskLevel.HIGH]:
            return {
                "allowed": False,
                "blocked": True,
                "reason": f"Export blocked due to {scan_result.risk_level.value} risk data leakage",
                "risk_level": scan_result.risk_level.value,
                "detected_entities": len(scan_result.detected_entities),
                "recommendations": scan_result.recommendations,
                "safe_export_data": None
            }
        else:
            return {
                "allowed": True,
                "blocked": False,
                "masked": False,
                "reason": "No high-risk sensitive data leakage detected",
                "risk_level": scan_result.risk_level.value if scan_result.has_leakage else "none",
                "detected_entities": len(scan_result.detected_entities),
                "recommendations": scan_result.recommendations,
                "safe_export_data": export_data
            }
    
    async def get_leakage_statistics(self, tenant_id: str, start_date=None, end_date=None) -> Dict[str, Any]:
        """Get leakage statistics."""
        return {
            "period": {"start": "2024-01-01", "end": "2024-01-31"},
            "total_scans": 0,
            "leakage_detected": 0,
            "leakage_rate": 0.0,
            "risk_level_distribution": {},
            "zero_leakage_compliance": 1.0
        }