"""
Data Desensitization Module.

Provides PII detection and data masking capabilities using Microsoft Presidio.
"""

from .presidio_engine import PresidioEngine
from .rule_manager import DesensitizationRuleManager
from .data_classifier import DataClassifier
from .models import (
    DesensitizationRule,
    PIIEntity,
    PIIEntityType,
    MaskingStrategy,
    SensitivityLevel,
    ClassificationResult,
    DesensitizationResult,
    DatasetClassification,
    ComplianceReport
)

__all__ = [
    "PresidioEngine",
    "DesensitizationRuleManager", 
    "DataClassifier",
    "DesensitizationRule",
    "PIIEntity",
    "PIIEntityType",
    "MaskingStrategy",
    "SensitivityLevel",
    "ClassificationResult",
    "DesensitizationResult",
    "DatasetClassification",
    "ComplianceReport"
]