"""
Sensitive Data Validator for Data Transfer Operations

Detects sensitive data patterns (PII, financial data, health data) in transfer
requests and requires additional validation/approval for sensitive transfers.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models.data_transfer import DataTransferRequest, TransferRecord
from src.sync.desensitization.models import PIIEntityType, SensitivityLevel


logger = logging.getLogger(__name__)


class SensitiveDataPattern:
    """Defines patterns for detecting sensitive data."""
    
    # PII patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
    SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
    
    # Financial patterns
    CREDIT_CARD_PATTERN = r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
    BANK_ACCOUNT_PATTERN = r'\b\d{8,17}\b'
    IBAN_PATTERN = r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b'
    
    # Health data patterns
    MEDICAL_RECORD_PATTERN = r'\b(?:MRN|Medical Record|Patient ID)[\s:]+[A-Z0-9-]+\b'
    DIAGNOSIS_KEYWORDS = {
        'diagnosis', 'disease', 'condition', 'symptom', 'treatment',
        'medication', 'prescription', 'patient', 'medical history'
    }
    
    # Chinese ID card pattern
    CHINESE_ID_PATTERN = r'\b\d{17}[\dXx]\b'
    
    # Sensitive field names
    SENSITIVE_FIELD_NAMES = {
        'password', 'secret', 'token', 'api_key', 'private_key',
        'ssn', 'social_security', 'credit_card', 'bank_account',
        'medical_record', 'health_record', 'diagnosis',
        'id_card', 'passport', 'driver_license'
    }


class SensitiveDataDetectionResult:
    """Result of sensitive data detection."""
    
    def __init__(self):
        self.has_sensitive_data: bool = False
        self.sensitivity_level: SensitivityLevel = SensitivityLevel.LOW
        self.detected_patterns: List[Dict[str, Any]] = []
        self.sensitive_fields: Set[str] = set()
        self.requires_additional_approval: bool = False
        self.risk_score: float = 0.0
        self.recommendations: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'has_sensitive_data': self.has_sensitive_data,
            'sensitivity_level': self.sensitivity_level.value,
            'detected_patterns': self.detected_patterns,
            'sensitive_fields': list(self.sensitive_fields),
            'requires_additional_approval': self.requires_additional_approval,
            'risk_score': self.risk_score,
            'recommendations': self.recommendations
        }


class SensitiveDataValidator:
    """
    Validates data transfer requests for sensitive data.
    
    Detects:
    - PII (email, phone, SSN, ID cards)
    - Financial data (credit cards, bank accounts, IBAN)
    - Health data (medical records, diagnoses)
    
    Requires additional approval for:
    - High sensitivity data (SSN, credit cards, medical records)
    - Multiple types of sensitive data in single transfer
    - Large volumes of sensitive data
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with optional configuration.
        
        Args:
            config: Configuration dict with thresholds and patterns
        """
        self.config = config or {}
        
        # Thresholds for requiring additional approval
        self.high_risk_threshold = self.config.get('high_risk_threshold', 0.7)
        self.max_sensitive_records = self.config.get('max_sensitive_records', 100)
        
        # Pattern weights for risk scoring
        self.pattern_weights = {
            'ssn': 1.0,
            'credit_card': 1.0,
            'medical_record': 1.0,
            'bank_account': 0.8,
            'iban': 0.8,
            'email': 0.3,
            'phone': 0.3,
            'chinese_id': 0.9
        }
    
    async def validate_transfer_request(
        self,
        request: DataTransferRequest
    ) -> SensitiveDataDetectionResult:
        """
        Validate transfer request for sensitive data.
        
        Args:
            request: Data transfer request to validate
            
        Returns:
            Detection result with sensitivity analysis
        """
        result = SensitiveDataDetectionResult()
        
        # Check each record for sensitive data
        for idx, record in enumerate(request.records):
            record_result = await self._check_record(record, idx)
            
            if record_result['has_sensitive_data']:
                result.has_sensitive_data = True
                result.detected_patterns.extend(record_result['patterns'])
                result.sensitive_fields.update(record_result['sensitive_fields'])
        
        # Calculate overall risk score
        result.risk_score = self._calculate_risk_score(
            result.detected_patterns,
            len(request.records)
        )
        
        # Determine sensitivity level
        result.sensitivity_level = self._determine_sensitivity_level(
            result.risk_score,
            result.detected_patterns
        )
        
        # Check if additional approval is required
        result.requires_additional_approval = self._requires_additional_approval(
            result.sensitivity_level,
            result.risk_score,
            len(request.records),
            result.detected_patterns
        )
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        
        # Log detection result
        logger.info(
            f"Sensitive data detection completed: "
            f"has_sensitive={result.has_sensitive_data}, "
            f"level={result.sensitivity_level.value}, "
            f"risk_score={result.risk_score:.2f}, "
            f"requires_approval={result.requires_additional_approval}"
        )
        
        return result
    
    async def _check_record(
        self,
        record: TransferRecord,
        record_idx: int
    ) -> Dict[str, Any]:
        """
        Check a single record for sensitive data.
        
        Args:
            record: Transfer record to check
            record_idx: Index of record in request
            
        Returns:
            Dict with detection results for this record
        """
        patterns_found = []
        sensitive_fields = set()
        
        # Check content fields
        if record.content:
            content_result = self._scan_dict(
                record.content,
                prefix=f"record[{record_idx}].content"
            )
            patterns_found.extend(content_result['patterns'])
            sensitive_fields.update(content_result['sensitive_fields'])
        
        # Check metadata fields
        if record.metadata:
            metadata_result = self._scan_dict(
                record.metadata,
                prefix=f"record[{record_idx}].metadata"
            )
            patterns_found.extend(metadata_result['patterns'])
            sensitive_fields.update(metadata_result['sensitive_fields'])
        
        return {
            'has_sensitive_data': len(patterns_found) > 0,
            'patterns': patterns_found,
            'sensitive_fields': sensitive_fields
        }
    
    def _scan_dict(
        self,
        data: Dict[str, Any],
        prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Recursively scan dictionary for sensitive data patterns.
        
        Args:
            data: Dictionary to scan
            prefix: Field path prefix for logging
            
        Returns:
            Dict with patterns found and sensitive fields
        """
        patterns_found = []
        sensitive_fields = set()
        
        for key, value in data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            
            # Check if field name itself is sensitive
            if self._is_sensitive_field_name(key):
                sensitive_fields.add(field_path)
                patterns_found.append({
                    'type': 'sensitive_field_name',
                    'field': field_path,
                    'pattern': key.lower()
                })
            
            # Check value based on type
            if isinstance(value, str):
                # Scan string value for patterns
                value_patterns = self._scan_string(value, field_path)
                patterns_found.extend(value_patterns)
                
                if value_patterns:
                    sensitive_fields.add(field_path)
            
            elif isinstance(value, dict):
                # Recursively scan nested dict
                nested_result = self._scan_dict(value, field_path)
                patterns_found.extend(nested_result['patterns'])
                sensitive_fields.update(nested_result['sensitive_fields'])
            
            elif isinstance(value, list):
                # Scan list items
                for idx, item in enumerate(value):
                    if isinstance(item, str):
                        item_patterns = self._scan_string(
                            item,
                            f"{field_path}[{idx}]"
                        )
                        patterns_found.extend(item_patterns)
                        
                        if item_patterns:
                            sensitive_fields.add(field_path)
                    
                    elif isinstance(item, dict):
                        nested_result = self._scan_dict(
                            item,
                            f"{field_path}[{idx}]"
                        )
                        patterns_found.extend(nested_result['patterns'])
                        sensitive_fields.update(nested_result['sensitive_fields'])
        
        return {
            'patterns': patterns_found,
            'sensitive_fields': sensitive_fields
        }
    
    def _scan_string(self, text: str, field_path: str) -> List[Dict[str, Any]]:
        """
        Scan string for sensitive data patterns.
        
        Args:
            text: String to scan
            field_path: Field path for logging
            
        Returns:
            List of detected patterns
        """
        patterns_found = []
        
        # Email
        if re.search(SensitiveDataPattern.EMAIL_PATTERN, text):
            patterns_found.append({
                'type': 'email',
                'field': field_path,
                'pattern': 'EMAIL_ADDRESS'
            })
        
        # Phone number
        if re.search(SensitiveDataPattern.PHONE_PATTERN, text):
            patterns_found.append({
                'type': 'phone',
                'field': field_path,
                'pattern': 'PHONE_NUMBER'
            })
        
        # SSN
        if re.search(SensitiveDataPattern.SSN_PATTERN, text):
            patterns_found.append({
                'type': 'ssn',
                'field': field_path,
                'pattern': 'US_SSN'
            })
        
        # Credit card
        if re.search(SensitiveDataPattern.CREDIT_CARD_PATTERN, text):
            patterns_found.append({
                'type': 'credit_card',
                'field': field_path,
                'pattern': 'CREDIT_CARD'
            })
        
        # Bank account
        if re.search(SensitiveDataPattern.BANK_ACCOUNT_PATTERN, text):
            patterns_found.append({
                'type': 'bank_account',
                'field': field_path,
                'pattern': 'BANK_ACCOUNT'
            })
        
        # IBAN
        if re.search(SensitiveDataPattern.IBAN_PATTERN, text):
            patterns_found.append({
                'type': 'iban',
                'field': field_path,
                'pattern': 'IBAN_CODE'
            })
        
        # Medical record
        if re.search(SensitiveDataPattern.MEDICAL_RECORD_PATTERN, text, re.IGNORECASE):
            patterns_found.append({
                'type': 'medical_record',
                'field': field_path,
                'pattern': 'MEDICAL_RECORD'
            })
        
        # Chinese ID card
        if re.search(SensitiveDataPattern.CHINESE_ID_PATTERN, text):
            patterns_found.append({
                'type': 'chinese_id',
                'field': field_path,
                'pattern': 'CHINESE_ID_CARD'
            })
        
        # Health data keywords
        text_lower = text.lower()
        for keyword in SensitiveDataPattern.DIAGNOSIS_KEYWORDS:
            if keyword in text_lower:
                patterns_found.append({
                    'type': 'health_data',
                    'field': field_path,
                    'pattern': f'HEALTH_KEYWORD_{keyword.upper()}'
                })
                break  # Only report once per field
        
        return patterns_found
    
    def _is_sensitive_field_name(self, field_name: str) -> bool:
        """Check if field name indicates sensitive data."""
        field_lower = field_name.lower()
        
        for sensitive_name in SensitiveDataPattern.SENSITIVE_FIELD_NAMES:
            if sensitive_name in field_lower:
                return True
        
        return False
    
    def _calculate_risk_score(
        self,
        patterns: List[Dict[str, Any]],
        record_count: int
    ) -> float:
        """
        Calculate overall risk score based on detected patterns.
        
        Args:
            patterns: List of detected patterns
            record_count: Total number of records
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        if not patterns:
            return 0.0
        
        # Count pattern types
        pattern_counts = {}
        for pattern in patterns:
            pattern_type = pattern['type']
            pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
        
        # Calculate weighted score
        total_weight = 0.0
        for pattern_type, count in pattern_counts.items():
            weight = self.pattern_weights.get(pattern_type, 0.5)
            # Each occurrence adds to the weight
            total_weight += weight * min(count, 5) / 5  # Cap at 5 occurrences
        
        # Normalize by record count (more records = higher risk)
        import math
        volume_factor = min(0.3, math.log10(record_count + 1) / 10)
        
        # Combine factors
        risk_score = min(1.0, total_weight + volume_factor)
        
        return risk_score
    
    def _determine_sensitivity_level(
        self,
        risk_score: float,
        patterns: List[Dict[str, Any]]
    ) -> SensitivityLevel:
        """
        Determine sensitivity level based on risk score and patterns.
        
        Args:
            risk_score: Calculated risk score
            patterns: Detected patterns
            
        Returns:
            Sensitivity level
        """
        # Check for critical patterns
        critical_patterns = {'ssn', 'credit_card', 'medical_record'}
        has_critical = any(
            p['type'] in critical_patterns for p in patterns
        )
        
        if has_critical or risk_score >= 0.8:
            return SensitivityLevel.CRITICAL
        elif risk_score >= 0.6:
            return SensitivityLevel.HIGH
        elif risk_score >= 0.3:
            return SensitivityLevel.MEDIUM
        else:
            return SensitivityLevel.LOW
    
    def _requires_additional_approval(
        self,
        sensitivity_level: SensitivityLevel,
        risk_score: float,
        record_count: int,
        patterns: List[Dict[str, Any]]
    ) -> bool:
        """
        Determine if additional approval is required.
        
        Args:
            sensitivity_level: Determined sensitivity level
            risk_score: Calculated risk score
            record_count: Number of records
            patterns: Detected patterns
            
        Returns:
            True if additional approval is required
        """
        # Always require approval for critical sensitivity
        if sensitivity_level == SensitivityLevel.CRITICAL:
            return True
        
        # Require approval for high risk score
        if risk_score >= self.high_risk_threshold:
            return True
        
        # Require approval for large volumes of sensitive data
        if len(patterns) > self.max_sensitive_records:
            return True
        
        # Require approval for multiple types of sensitive data
        pattern_types = set(p['type'] for p in patterns)
        if len(pattern_types) >= 3:
            return True
        
        return False
    
    def _generate_recommendations(
        self,
        result: SensitiveDataDetectionResult
    ) -> List[str]:
        """
        Generate recommendations based on detection result.
        
        Args:
            result: Detection result
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if not result.has_sensitive_data:
            return recommendations
        
        # Recommend data masking
        if result.sensitivity_level in [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]:
            recommendations.append(
                "Consider applying data masking or encryption before transfer"
            )
        
        # Recommend field-level security
        if result.sensitive_fields:
            recommendations.append(
                f"Apply field-level security to: {', '.join(list(result.sensitive_fields)[:5])}"
            )
        
        # Recommend audit logging
        if result.requires_additional_approval:
            recommendations.append(
                "Enable detailed audit logging for this transfer"
            )
        
        # Recommend compliance review
        pattern_types = set(p['type'] for p in result.detected_patterns)
        if 'medical_record' in pattern_types or 'health_data' in pattern_types:
            recommendations.append(
                "Review HIPAA compliance requirements for health data transfer"
            )
        
        if 'credit_card' in pattern_types or 'bank_account' in pattern_types:
            recommendations.append(
                "Review PCI DSS compliance requirements for financial data transfer"
            )
        
        return recommendations
