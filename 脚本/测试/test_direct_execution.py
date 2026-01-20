#!/usr/bin/env python3

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

print("Testing direct execution of zero leakage prevention...")

# Read and execute the file directly
try:
    with open('src/security/zero_leakage_prevention.py', 'r') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    print(f"File lines: {content.count(chr(10))} lines")
    
    # Create a new namespace
    namespace = {}
    
    # Execute the file content
    exec(content, namespace)
    
    print("File executed successfully")
    
    # Check what's available
    classes = [name for name, obj in namespace.items() 
              if isinstance(obj, type) and not name.startswith('_')]
    
    print(f"Available classes: {classes}")
    
    if 'ZeroLeakagePreventionSystem' in namespace:
        print("✓ ZeroLeakagePreventionSystem found!")
        cls = namespace['ZeroLeakagePreventionSystem']
        print(f"Class: {cls}")
        
        # Try to instantiate
        try:
            instance = cls()
            print("✓ Instance created successfully")
        except Exception as e:
            print(f"✗ Instance creation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("✗ ZeroLeakagePreventionSystem not found")
        print("Available items:", [name for name in namespace.keys() if not name.startswith('_')])

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()