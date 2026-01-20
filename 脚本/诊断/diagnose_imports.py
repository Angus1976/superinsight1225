#!/usr/bin/env python3
"""Diagnose import issues."""

import sys
import importlib

# List of modules to check
modules_to_check = [
    "src.security.rbac_models",
    "src.sync.rbac",
    "src.sync.rbac.permission_manager",
    "src.sync.rbac.rbac_service",
    "src.sync.rbac.field_access_control",
    "src.sync.rbac.audit_service",
    "src.sync.rbac.tenant_isolation",
]

print("=" * 60)
print("Checking Module Imports")
print("=" * 60)

for module_name in modules_to_check:
    try:
        print(f"\nImporting {module_name}...")
        mod = importlib.import_module(module_name)
        print(f"  ✓ Success")
        
        # Check if it has RoleModel
        if hasattr(mod, 'RoleModel'):
            print(f"  - Has RoleModel: {mod.RoleModel}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
