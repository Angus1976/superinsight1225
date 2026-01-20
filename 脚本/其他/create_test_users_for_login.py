#!/usr/bin/env python3
"""
Create test users with different roles for login testing.

This script creates test users in the database with various roles:
- admin: Full system access
- business_expert: Business operations and analysis
- technical_expert: Technical operations and system management
- contractor: Limited access for external contractors
- viewer: Read-only access

Usage:
    python create_test_users_for_login.py
"""

import sys
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.connection import db_manager, Base
from src.security.controller import SecurityController
from src.security.models import UserRole, UserModel

# Test user credentials
TEST_USERS = [
    {
        "username": "admin_user",
        "email": "admin@superinsight.local",
        "password": "Admin@123456",
        "full_name": "Admin User",
        "role": UserRole.ADMIN,
        "tenant_id": "default_tenant",
    },
    {
        "username": "business_expert",
        "email": "business@superinsight.local",
        "password": "Business@123456",
        "full_name": "Business Expert",
        "role": UserRole.BUSINESS_EXPERT,
        "tenant_id": "default_tenant",
    },
    {
        "username": "technical_expert",
        "email": "technical@superinsight.local",
        "password": "Technical@123456",
        "full_name": "Technical Expert",
        "role": UserRole.TECHNICAL_EXPERT,
        "tenant_id": "default_tenant",
    },
    {
        "username": "contractor",
        "email": "contractor@superinsight.local",
        "password": "Contractor@123456",
        "full_name": "Contractor User",
        "role": UserRole.CONTRACTOR,
        "tenant_id": "default_tenant",
    },
    {
        "username": "viewer",
        "email": "viewer@superinsight.local",
        "password": "Viewer@123456",
        "full_name": "Viewer User",
        "role": UserRole.VIEWER,
        "tenant_id": "default_tenant",
    },
]


def create_test_users():
    """Create test users in the database."""
    print("Creating test users for login testing...")
    print("-" * 60)
    
    # Initialize database connection
    db_manager.initialize()
    
    # Initialize database tables
    engine = db_manager.get_engine()
    Base.metadata.create_all(bind=engine)
    
    security_controller = SecurityController()
    
    # Get database session
    with db_manager.get_session() as db:
        try:
            created_count = 0
            skipped_count = 0
            
            for user_data in TEST_USERS:
                # Check if user already exists
                existing_user = db.query(UserModel).filter(
                    UserModel.username == user_data["username"]
                ).first()
                
                if existing_user:
                    print(f"⊘ Skipped: {user_data['username']} (already exists)")
                    skipped_count += 1
                    continue
                
                # Create user
                user = security_controller.create_user(
                    username=user_data["username"],
                    email=user_data["email"],
                    password=user_data["password"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    tenant_id=user_data["tenant_id"],
                    db=db,
                )
                
                if user:
                    print(f"✓ Created: {user_data['username']} ({user_data['role'].value})")
                    created_count += 1
                else:
                    print(f"✗ Failed: {user_data['username']}")
            
            print("-" * 60)
            print(f"Summary: {created_count} created, {skipped_count} skipped")
            print("\nTest User Credentials:")
            print("-" * 60)
            
            for user_data in TEST_USERS:
                print(f"Role: {user_data['role'].value}")
                print(f"  Username: {user_data['username']}")
                print(f"  Password: {user_data['password']}")
                print(f"  Email: {user_data['email']}")
                print()
            
            print("Frontend Login URL: http://localhost:5173/login")
            print("Backend API: http://localhost:8000")
            print("-" * 60)
            
        except Exception as e:
            print(f"Error creating test users: {e}")
            sys.exit(1)


if __name__ == "__main__":
    create_test_users()