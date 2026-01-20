#!/usr/bin/env python3

# Test imports step by step
print("Testing imports...")

try:
    from src.security.audit_service import AuditService
    print("✓ AuditService imported")
except Exception as e:
    print(f"✗ AuditService failed: {e}")

try:
    from src.sync.desensitization import PresidioEngine
    print("✓ PresidioEngine imported")
except Exception as e:
    print(f"✗ PresidioEngine failed: {e}")

try:
    from src.desensitization.validator import DesensitizationValidator
    print("✓ DesensitizationValidator imported")
except Exception as e:
    print(f"✗ DesensitizationValidator failed: {e}")

try:
    from src.quality.desensitization_monitor import DesensitizationQualityMonitor
    print("✓ DesensitizationQualityMonitor imported")
except Exception as e:
    print(f"✗ DesensitizationQualityMonitor failed: {e}")

try:
    from src.alerts.desensitization_alerts import DesensitizationAlertManager
    print("✓ DesensitizationAlertManager imported")
except Exception as e:
    print(f"✗ DesensitizationAlertManager failed: {e}")

print("\nTesting zero leakage prevention module...")
try:
    import src.security.zero_leakage_prevention as zlp
    print("✓ Module imported")
    print(f"Module attributes: {[attr for attr in dir(zlp) if not attr.startswith('_')]}")
except Exception as e:
    print(f"✗ Module import failed: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting class import...")
try:
    from src.security.zero_leakage_prevention import ZeroLeakagePreventionSystem
    print("✓ ZeroLeakagePreventionSystem imported")
except Exception as e:
    print(f"✗ ZeroLeakagePreventionSystem import failed: {e}")
    import traceback
    traceback.print_exc()