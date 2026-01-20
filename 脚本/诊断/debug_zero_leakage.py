#!/usr/bin/env python3

print("Starting debug of zero leakage prevention...")

# Test each import individually
imports_to_test = [
    "import asyncio",
    "import hashlib", 
    "import logging",
    "import re",
    "from datetime import datetime, timedelta",
    "from typing import Any, Dict, List, Optional, Set, Tuple, Union",
    "from uuid import uuid4",
    "from dataclasses import dataclass",
    "from enum import Enum",
    "from sqlalchemy.orm import Session",
    "from src.database.connection import get_db_session",
    "from src.security.audit_service import AuditService",
    "from src.sync.desensitization import PresidioEngine, DesensitizationRuleManager, DataClassifier, PIIEntityType, MaskingStrategy, SensitivityLevel",
    "from src.desensitization.validator import DesensitizationValidator",
    "from src.quality.desensitization_monitor import DesensitizationQualityMonitor",
    "from src.alerts.desensitization_alerts import DesensitizationAlertManager"
]

for import_stmt in imports_to_test:
    try:
        exec(import_stmt)
        print(f"✓ {import_stmt}")
    except Exception as e:
        print(f"✗ {import_stmt} - Error: {e}")

print("\nAll imports tested. Now testing class definitions...")

# Test enum definitions
try:
    exec('''
class LeakageRiskLevel(Enum):
    """Data leakage risk levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
''')
    print("✓ LeakageRiskLevel enum defined")
except Exception as e:
    print(f"✗ LeakageRiskLevel enum failed: {e}")

try:
    exec('''
class LeakageDetectionMethod(Enum):
    """Methods for detecting data leakage"""
    PATTERN_MATCHING = "pattern_matching"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    MACHINE_LEARNING = "machine_learning"
    HASH_COMPARISON = "hash_comparison"
    ENTROPY_ANALYSIS = "entropy_analysis"
''')
    print("✓ LeakageDetectionMethod enum defined")
except Exception as e:
    print(f"✗ LeakageDetectionMethod enum failed: {e}")

# Test dataclass definitions
try:
    exec('''
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
''')
    print("✓ LeakageDetectionResult dataclass defined")
except Exception as e:
    print(f"✗ LeakageDetectionResult dataclass failed: {e}")

try:
    exec('''
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
''')
    print("✓ LeakagePreventionPolicy dataclass defined")
except Exception as e:
    print(f"✗ LeakagePreventionPolicy dataclass failed: {e}")

# Test minimal class definition
try:
    exec('''
class ZeroLeakagePreventionSystem:
    """
    Comprehensive zero sensitive data leakage prevention system.
    
    Provides real-time detection, prevention, and response to any
    potential sensitive data leakage across the platform.
    """
    
    def __init__(self):
        """Initialize the zero leakage prevention system."""
        print("Initializing ZeroLeakagePreventionSystem...")
        self.presidio_engine = PresidioEngine()
        print("✓ PresidioEngine initialized")
        self.rule_manager = DesensitizationRuleManager()
        print("✓ DesensitizationRuleManager initialized")
        self.data_classifier = DataClassifier(self.presidio_engine)
        print("✓ DataClassifier initialized")
        self.validator = DesensitizationValidator()
        print("✓ DesensitizationValidator initialized")
        self.quality_monitor = DesensitizationQualityMonitor()
        print("✓ DesensitizationQualityMonitor initialized")
        self.alert_manager = DesensitizationAlertManager()
        print("✓ DesensitizationAlertManager initialized")
        self.audit_service = AuditService()
        print("✓ AuditService initialized")
        print("ZeroLeakagePreventionSystem initialization complete")
''')
    print("✓ ZeroLeakagePreventionSystem class defined")
    
    # Test instantiation
    system = ZeroLeakagePreventionSystem()
    print("✓ ZeroLeakagePreventionSystem instantiated successfully")
    
except Exception as e:
    print(f"✗ ZeroLeakagePreventionSystem class failed: {e}")
    import traceback
    traceback.print_exc()

print("\nDebug complete.")