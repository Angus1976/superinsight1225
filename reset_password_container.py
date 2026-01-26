#!/usr/bin/env python3
"""Reset admin password in container"""
import sys
sys.path.insert(0, '/app')

from src.database.connection import db_manager
from src.security.controller import SecurityController
from src.security.models import UserModel

db_manager.initialize()
security_controller = SecurityController(secret_key="test-secret-key-for-local-development-only")

NEW_PASSWORD = "password"

with db_manager.get_session() as db:
    user = db.query(UserModel).filter(UserModel.username == "admin").first()
    if user:
        user.password_hash = security_controller.hash_password(NEW_PASSWORD)
        db.commit()
        print(f"✅ Password reset for user: {user.username}")
    else:
        print("❌ User not found")
