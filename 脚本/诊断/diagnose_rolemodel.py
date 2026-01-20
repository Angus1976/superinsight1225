#!/usr/bin/env python3
"""Diagnose RoleModel registration issue."""

import sys
from sqlalchemy import inspect

# Import the Base
from src.database.connection import Base

# Try to import RoleModel from different places
print("=" * 60)
print("Diagnosing RoleModel Registration Issue")
print("=" * 60)

# Check what's registered in Base
print("\nRegistered tables in Base.metadata:")
for table in Base.metadata.tables.keys():
    print(f"  - {table}")

# Check for RoleModel specifically
print("\nLooking for RoleModel in registry...")
registry = Base.registry
print(f"Registry: {registry}")
print(f"Registry._class_registry: {registry._class_registry if hasattr(registry, '_class_registry') else 'N/A'}")

# Try to import RoleModel
try:
    from src.security.rbac_models import RoleModel as RoleModel1
    print(f"\n✓ Imported RoleModel from src.security.rbac_models: {RoleModel1}")
    print(f"  Module: {RoleModel1.__module__}")
    print(f"  Table: {RoleModel1.__tablename__}")
except Exception as e:
    print(f"\n✗ Failed to import RoleModel from src.security.rbac_models: {e}")

# Check if there are multiple RoleModel classes
print("\nChecking for duplicate RoleModel classes...")
try:
    from src.sync.rbac import RoleModel as RoleModel2
    print(f"✓ Imported RoleModel from src.sync.rbac: {RoleModel2}")
    print(f"  Module: {RoleModel2.__module__}")
    print(f"  Same as RoleModel1? {RoleModel1 is RoleModel2}")
except Exception as e:
    print(f"✗ Failed to import RoleModel from src.sync.rbac: {e}")

print("\n" + "=" * 60)
