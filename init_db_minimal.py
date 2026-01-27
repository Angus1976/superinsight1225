#!/usr/bin/env python3
"""
Minimal database initialization for SuperInsight Platform.

Creates only the essential tables needed for basic functionality.
"""

import sys
import logging
from sqlalchemy import create_engine, text
from datetime import datetime
import bcrypt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_minimal_database():
    """Initialize database with minimal tables."""
    try:
        from src.config.settings import settings
        from src.database.connection import db_manager
        
        # Initialize database manager
        db_manager.initialize()
        engine = db_manager.get_engine()
        
        logger.info("=" * 60)
        logger.info("🔧 Minimal Database Initialization Started")
        logger.info("=" * 60)
        
        with engine.connect() as conn:
            # Create users table if not exists
            logger.info("\n📊 Creating users table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) UNIQUE,
                    name VARCHAR(200),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    is_superuser BOOLEAN DEFAULT FALSE,
                    password_hash VARCHAR(255),
                    sso_id VARCHAR(255),
                    sso_provider VARCHAR(50),
                    sso_attributes JSON,
                    avatar_url VARCHAR(500),
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    language VARCHAR(10) DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP,
                    user_metadata JSON
                )
            """))
            conn.commit()
            logger.info("  ✓ Users table created")
            
            # Create audit_logs table if not exists
            logger.info("\n📊 Creating audit_logs table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID,
                    tenant_id VARCHAR(255) DEFAULT 'system',
                    action VARCHAR(100),
                    resource_type VARCHAR(100),
                    resource_id VARCHAR(255),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    details JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("  ✓ Audit logs table created")
            
            # Create tasks table if not exists
            logger.info("\n📊 Creating tasks table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by UUID,
                    tenant_id VARCHAR(255) DEFAULT 'system'
                )
            """))
            conn.commit()
            logger.info("  ✓ Tasks table created")
            
            # Create label_studio_projects table if not exists
            logger.info("\n📊 Creating label_studio_projects table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS label_studio_projects (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task_id UUID,
                    label_studio_project_id INTEGER,
                    label_studio_project_name VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tenant_id VARCHAR(255) DEFAULT 'system'
                )
            """))
            conn.commit()
            logger.info("  ✓ Label Studio projects table created")
            
            # Check if admin user exists
            logger.info("\n👤 Checking admin user...")
            result = conn.execute(text(
                "SELECT COUNT(*) FROM users WHERE email = 'admin@superinsight.local'"
            ))
            count = result.scalar()
            
            if count == 0:
                logger.info("  Creating admin user...")
                password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
                
                conn.execute(text("""
                    INSERT INTO users (email, username, name, password_hash, is_active, is_verified, is_superuser)
                    VALUES (:email, :username, :name, :password_hash, :is_active, :is_verified, :is_superuser)
                """), {
                    "email": "admin@superinsight.local",
                    "username": "admin",
                    "name": "Administrator",
                    "password_hash": password_hash,
                    "is_active": True,
                    "is_verified": True,
                    "is_superuser": True
                })
                conn.commit()
                logger.info("  ✓ Admin user created (email: admin@superinsight.local, password: admin123)")
            else:
                logger.info("  ✓ Admin user already exists")
            
            # Verify tables
            logger.info("\n✅ Verifying tables...")
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = result.fetchall()
            
            if tables:
                logger.info(f"  ✓ Found {len(tables)} tables:")
                for table in tables:
                    logger.info(f"    - {table[0]}")
            else:
                logger.warning("  ⚠ No tables found in database")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Minimal database initialization completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_minimal_database()
    sys.exit(0 if success else 1)
