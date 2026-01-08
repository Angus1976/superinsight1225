"""
Data models for desensitization system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4


class MaskingStrategy(str, Enum):
    """Masking strategy enumeration."""
    REPLACE = "replace"
    REDACT = "redact"
    HASH = "hash"
    ENCRYPT = "encrypt"
    MASK = "mask"
    KEEP = "keep"
    CUSTOM = "custom"


class PIIEntityType(str, Enum):
    """PII entity types supported by Presidio."""
    PERSON = "PERSON"
    PHONE_NUMBER = "PHONE_NUMBER"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    CREDIT_CARD = "CREDIT_CARD"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    LOCATION = "LOCATION"
    DATE_TIME = "DATE_TIME"
    NRP = "NRP"  # Named Recognition Person
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    URL = "URL"
    US_SSN = "US_SSN"
    US_PASSPORT = "US_PASSPORT"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    CRYPTO = "CRYPTO"
    CUSTOM = "CUSTOM"


class SensitivityLevel(str, Enum):
    """Data sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PIIEntity:
    """PII entity detected in data."""
    entity_type: PIIEntityType
    start: int
    end: int
    score: float
    text: str
    recognition_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DesensitizationRule:
    """Desensitization rule configuration."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    entity_type: PIIEntityType = PIIEntityType.PERSON
    field_pattern: Optional[str] = None
    masking_strategy: MaskingStrategy = MaskingStrategy.MASK
    sensitivity_level: SensitivityLevel = SensitivityLevel.MEDIUM
    confidence_threshold: float = 0.8
    enabled: bool = True
    tenant_id: str = ""
    created_by: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Strategy-specific configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default configurations based on strategy."""
        if not self.config:
            if self.masking_strategy == MaskingStrategy.REPLACE:
                self.config = {"replacement": "***"}
            elif self.masking_strategy == MaskingStrategy.MASK:
                self.config = {
                    "mask_char": "*",
                    "chars_to_mask": -1,  # -1 means all
                    "from_end": False
                }
            elif self.masking_strategy == MaskingStrategy.HASH:
                self.config = {
                    "hash_type": "sha256",
                    "salt": ""
                }
            elif self.masking_strategy == MaskingStrategy.ENCRYPT:
                self.config = {
                    "key": "",
                    "algorithm": "AES"
                }


@dataclass
class ClassificationResult:
    """Result of data classification."""
    field_name: str
    entities: List[PIIEntity]
    sensitivity_level: SensitivityLevel
    confidence_score: float
    requires_masking: bool
    suggested_rules: List[DesensitizationRule] = field(default_factory=list)


@dataclass
class DesensitizationResult:
    """Result of desensitization operation."""
    success: bool
    original_text: str
    anonymized_text: str
    entities_found: List[PIIEntity]
    rules_applied: List[str]
    processing_time_ms: float
    errors: List[str] = field(default_factory=list)


@dataclass
class DatasetClassification:
    """Classification result for entire dataset."""
    dataset_id: str
    total_fields: int
    sensitive_fields: int
    field_classifications: List[ClassificationResult]
    overall_sensitivity: SensitivityLevel
    compliance_score: float
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceReport:
    """Compliance assessment report."""
    tenant_id: str
    report_id: str = field(default_factory=lambda: str(uuid4()))
    datasets_analyzed: int = 0
    total_pii_entities: int = 0
    masked_entities: int = 0
    unmasked_entities: int = 0
    compliance_percentage: float = 0.0
    risk_level: SensitivityLevel = SensitivityLevel.LOW
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)