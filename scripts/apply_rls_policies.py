#!/usr/bin/env python3
"""
Script to apply Row-Level Security policies to the database.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import db_manager
from src.database.rls_policies import apply_rls_policies, test_rls_isolation


def main():
    """Apply RLS policies to the database."""
    print("Applying Row-Level Security policies...")
    
    try:
        with db_manager.get_session() as session:
            apply_rls_policies(session)
            print("✅ RLS policies applied successfully")
            
            # Test RLS isolation
            if test_rls_isolation(session):
                print("✅ RLS isolation test passed")
            else:
                print("❌ RLS isolation test failed")
                return 1
                
    except Exception as e:
        print(f"❌ Error applying RLS policies: {e}")
        return 1
    
    print("🎉 Row-Level Security setup completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())