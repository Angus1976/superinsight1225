#!/usr/bin/env python3

# Test minimal version of zero leakage prevention
import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

print("Basic imports successful")

try:
    from sqlalchemy.orm import Session
    print("✓ SQLAlchemy import successful")
except Exception as e:
    print(f"✗ SQLAlchemy import failed: {e}")

try:
    from src.database.connection import get_db_session
    print("✓ Database connection import successful")
except Exception as e:
    print(f"✗ Database connection import failed: {e}")

try:
    from src.security.audit_service import AuditService
    print("✓ AuditService import successful")
except Exception as e:
    print(f"✗ AuditService import failed: {e}")

try:
    from src.sync.desensitization import (
        PresidioEngine,
        DesensitizationRuleManager,
        DataClassifier,
        PIIEntityType,
        MaskingStrategy,
        SensitivityLevel
    )
    print("✓ Desensitization imports successful")
except Exception as e:
    print(f"✗ Desensitization imports failed: {e}")

try:
    from src.desensitization.validator import DesensitizationValidator
    print("✓ DesensitizationValidator import successful")
except Exception as e:
    print(f"✗ DesensitizationValidator import failed: {e}")

try:
    from src.quality.desensitization_monitor import DesensitizationQualityMonitor
    print("✓ DesensitizationQualityMonitor import successful")
except Exception as e:
    print(f"✗ DesensitizationQualityMonitor import failed: {e}")

try:
    from src.alerts.desensitization_alerts import DesensitizationAlertManager
    print("✓ DesensitizationAlertManager import successful")
except Exception as e:
    print(f"✗ DesensitizationAlertManager import failed: {e}")

print("\nAll imports successful, creating minimal class...")

class LeakageRiskLevel(Enum):
    """Data leakage risk levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ZeroLeakagePreventionSystem:
    """Minimal test version"""
    
    def __init__(self):
        print("ZeroLeakagePreventionSystem initialized")

print("✓ Class defined successfully")

# Test instantiation
try:
    system = ZeroLeakagePreventionSystem()
    print("✓ Class instantiated successfully")
except Exception as e:
    print(f"✗ Class instantiation failed: {e}")
    import traceback
    traceback.print_exc()