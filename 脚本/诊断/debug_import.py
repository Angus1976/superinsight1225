#!/usr/bin/env python3

import sys
import traceback

print("Starting debug import...")

try:
    # Import each dependency individually
    print("Importing dependencies...")
    
    from src.database.connection import get_db_session
    print("✓ get_db_session")
    
    from src.security.audit_service import AuditService
    print("✓ AuditService")
    
    from src.sync.desensitization import (
        PresidioEngine,
        DesensitizationRuleManager,
        DataClassifier,
        PIIEntityType,
        MaskingStrategy,
        SensitivityLevel
    )
    print("✓ desensitization imports")
    
    from src.desensitization.validator import DesensitizationValidator
    print("✓ DesensitizationValidator")
    
    from src.quality.desensitization_monitor import DesensitizationQualityMonitor
    print("✓ DesensitizationQualityMonitor")
    
    from src.alerts.desensitization_alerts import DesensitizationAlertManager
    print("✓ DesensitizationAlertManager")
    
    print("All dependencies imported successfully")
    
    # Now try to execute the file line by line
    print("Reading zero leakage prevention file...")
    
    with open('src/security/zero_leakage_prevention.py', 'r') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    
    # Execute the file
    print("Executing file...")
    exec(content, globals())
    
    print("File executed successfully")
    
    # Check if class is now available
    if 'ZeroLeakagePreventionSystem' in globals():
        print("✓ ZeroLeakagePreventionSystem is available")
    else:
        print("✗ ZeroLeakagePreventionSystem not found in globals")
        print("Available classes:", [name for name in globals() if 'System' in name])
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()