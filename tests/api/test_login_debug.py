#!/usr/bin/env python3
"""
Debug script to test login functionality
"""
import sys
sys.path.insert(0, '.')

from src.database.connection import db_manager
from src.security.controller import SecurityController
from src.security.models import UserModel

# Initialize database
db_manager.initialize()

# Create security controller
security_controller = SecurityController(secret_key="test-secret-key-for-local-development-only")

# Test with database session
with db_manager.get_session() as db:
    # Get admin user
    user = db.query(UserModel).filter(UserModel.username == "admin").first()
    
    if not user:
        print("❌ User 'admin' not found in database")
        sys.exit(1)
    
    print(f"✅ Found user: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Role: {user.role}")
    print(f"   Active: {user.is_active}")
    print(f"   Password hash: {user.password_hash[:20]}...")
    
    # Test password verification with common passwords
    test_passwords = ["password", "admin", "admin123", "Admin@123456"]
    
    print("\n🔐 Testing password verification:")
    for pwd in test_passwords:
        result = security_controller.verify_password(pwd, user.password_hash)
        print(f"   Password '{pwd}': {'✅ MATCH' if result else '❌ NO MATCH'}")
    
    # Test authentication
    print("\n🔑 Testing authentication:")
    for pwd in test_passwords:
        auth_user = security_controller.authenticate_user("admin", pwd, db)
        if auth_user:
            print(f"   ✅ Authentication successful with password: {pwd}")
            break
    else:
        print("   ❌ Authentication failed with all test passwords")
        print("\n💡 Suggestion: Reset the admin password")
        print("   Run: python reset_admin_password.py")
