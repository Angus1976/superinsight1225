#!/usr/bin/env python3
"""
Reset admin user password
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

# New password
NEW_PASSWORD = "password"

print("🔄 Resetting admin password...")

with db_manager.get_session() as db:
    # Get admin user
    user = db.query(UserModel).filter(UserModel.username == "admin").first()
    
    if not user:
        print("❌ User 'admin' not found")
        sys.exit(1)
    
    # Hash new password
    new_hash = security_controller.hash_password(NEW_PASSWORD)
    
    print(f"   Old hash: {user.password_hash[:30]}...")
    print(f"   New hash: {new_hash[:30]}...")
    
    # Update password
    user.password_hash = new_hash
    db.commit()
    
    print(f"✅ Password reset successful!")
    print(f"   Username: admin")
    print(f"   Password: {NEW_PASSWORD}")
    
    # Verify the new password works
    test_user = security_controller.authenticate_user("admin", NEW_PASSWORD, db)
    if test_user:
        print("✅ Password verification successful!")
    else:
        print("❌ Password verification failed!")
