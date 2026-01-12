"""
Zero Sensitive Data Leakage Prevention System

Comprehensive system to ensure zero leakage of sensitive data across
all SuperInsight platform operations with real-time monitoring,
prevention, and automated response capabilities.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.audit_service import AuditService
from src.sync.desensitization import (
    PresidioEngine,
    DesensitizationRuleManager,
    DataClassifier,
    PIIEntityType,
    MaskingStrategy,
    SensitivityLevel
)
from src.desensitization.validator import DesensitizationValidator
from src.quality.desensitization_monitor import DesensitizationQualityMonitor
from src.alerts.desensitization_alerts import DesensitizationAlertManager

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
    Comprehensive zero sensitive data leakage prevention system.
    
    Provides real-time detection, prevention, and response to any
    potential sensitive data leakage across the platform.
    """
    
    def __init__(self):
        """Initialize the zero leakage prevention system."""
        self.presidio_engine = PresidioEngine()
        self.rule_manager = DesensitizationRuleManager()
        self.data_classifier = DataClassifier(self.presidio_engine)
        self.validator = DesensitizationValidator()
        self.quality_monitor = DesensitizationQualityMonitor()
        self.alert_manager = DesensitizationAlertManager()
        self.audit_service = AuditService()
        
        # Advanced detection patterns
        self.sensitive_patterns = self._initialize_sensitive_patterns()
        self.entropy_thresholds = self._initialize_entropy_thresholds()
        
        # Prevention policies cache
        self._policy_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Real-time monitoring
        self.monitoring_enabled = True
        self.real_time_blocking = True
        self.auto_quarantine = True
        
        # Performance settings
        self.max_concurrent_scans = 20
        self.scan_timeout_seconds = 30
        self.batch_scan_size = 100
        
    def _initialize_sensitive_patterns(self) -> Dict[str, List[str]]:
        """Initialize comprehensive sensitive data patterns."""
        return {
            "credit_card": [
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
            ],
            "ssn": [
                r'\b\d{3}-?\d{2}-?\d{4}\b',
                r'\b\d{9}\b'
            ],
            "phone": [
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                r'\b1[3-9]\d{9}\b'  # Chinese mobile
            ],
            "email": [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            "id_card": [
                r'\b\d{15}|\d{18}\b',  # Chinese ID
                r'\b[A-Z]{1,2}\d{6,8}[A-Z]?\b'  # International ID patterns
            ],
            "bank_account": [
                r'\b\d{10,19}\b'
            ],
            "ip_address": [
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ],
            "api_key": [
                r'\b[A-Za-z0-9]{32,}\b',
                r'\bsk-[A-Za-z0-9]{48}\b',  # OpenAI style
                r'\bAKIA[A-Z0-9]{16}\b'    # AWS style
            ],
            "password_hash": [
                r'\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}',  # bcrypt
                r'\{SHA\}[A-Za-z0-9+/]{27}=',           # SHA1
                r'\$6\$[A-Za-z0-9./]{86}'               # SHA512
            ]
        }
    
    def _initialize_entropy_thresholds(self) -> Dict[str, float]:
        """Initialize entropy thresholds for different data types."""
        return {
            "high_entropy": 4.5,      # Likely encrypted/hashed data
            "medium_entropy": 3.5,    # Potentially sensitive
            "low_entropy": 2.5,       # Regular text
            "min_length": 8           # Minimum length for entropy analysis
        }
    
    async def scan_for_leakage(
        self,
        data: Union[str, Dict[str, Any], List[Any]],
        tenant_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        operation_type: str = "data_scan"
    ) -> LeakageDetectionResult:
        """
        Comprehensive scan for sensitive data leakage.
        
        Args:
            data: Data to scan for leakage
            tenant_id: Tenant identifier
            user_id: User identifier
            context: Additional context information
            operation_type: Type of operation being performed
            
        Returns:
            LeakageDetectionResult with detailed analysis
        """
        scan_id = str(uuid4())
        start_time = datetime.utcnow()
        
        try:
            # Log scan start
            await self.audit_service.log_event(
                event_type="leakage_scan_start",
                user_id=user_id,
                resource="sensitive_data",
                action="leakage_scan",
                details={
                    "scan_id": scan_id,
                    "operation_type": operation_type,
                    "data_type": type(data).__name__,
                    "tenant_id": tenant_id
                }
            )
            
            # Get prevention policy for tenant
            policy = await self._get_prevention_policy(tenant_id)
            
            # Perform multi-method detection
            detection_results = await self._perform_comprehensive_detection(
                data, policy, scan_id
            )
            
            # Analyze results and determine risk level
            final_result = await self._analyze_detection_results(
                detection_results, policy, scan_id
            )
            
            # Log scan completion
            await self.audit_service.log_event(
                event_type="leakage_scan_complete",
                user_id=user_id,
                resource="sensitive_data",
                action="leakage_scan",
                details={
                    "scan_id": scan_id,
                    "has_leakage": final_result.has_leakage,
                    "risk_level": final_result.risk_level.value,
                    "confidence_score": final_result.confidence_score,
                    "detected_entities": len(final_result.detected_entities),
                    "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
                }
            )
            
            # Handle leakage if detected
            if final_result.has_leakage:
                await self._handle_leakage_detection(
                    final_result, tenant_id, user_id, scan_id, context
                )
            
            return final_result
            
        except Exception as e:
            logger.error(f"Leakage scan failed for scan {scan_id}: {e}")
            
            # Log error
            await self.audit_service.log_event(
                event_type="leakage_scan_error",
                user_id=user_id,
                resource="sensitive_data",
                action="leakage_scan",
                details={
                    "scan_id": scan_id,
                    "error": str(e),
                    "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
                }
            )
            
            # Return error result
            return LeakageDetectionResult(
                has_leakage=True,  # Assume leakage on error for safety
                risk_level=LeakageRiskLevel.HIGH,
                confidence_score=0.0,
                detected_entities=[],
                leakage_patterns=[],
                detection_methods=[],
                recommendations=["Scan failed - manual review required"],
                metadata={
                    "scan_id": scan_id,
                    "error": str(e),
                    "scan_failed": True
                }
            )
    
    async def _get_prevention_policy(self, tenant_id: str) -> LeakagePreventionPolicy:
        """Get leakage prevention policy for tenant."""
        
        cache_key = f"policy_{tenant_id}"
        
        # Check cache first
        if cache_key in self._policy_cache:
            cached_data = self._policy_cache[cache_key]
            if (datetime.utcnow() - cached_data["timestamp"]).total_seconds() < self._cache_ttl:
                return cached_data["policy"]
        
        # Create default policy if none exists
        default_policy = LeakagePreventionPolicy(
            tenant_id=tenant_id,
            policy_name="default_zero_leakage_policy",
            enabled=True,
            strict_mode=True,
            auto_block=True,
            detection_threshold=0.8,
            allowed_exposure_ratio=0.0,  # Zero tolerance
            whitelist_patterns=[],
            blacklist_patterns=[],
            notification_settings={
                "email_alerts": True,
                "sms_alerts": True,
                "webhook_alerts": True
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Cache the policy
        self._policy_cache[cache_key] = {
            "policy": default_policy,
            "timestamp": datetime.utcnow()
        }
        
        return default_policy