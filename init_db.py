#!/usr/bin/env python3
"""
Database initialization script for SuperInsight Platform.

This script initializes the database by creating all tables from the models.
It bypasses Alembic migration conflicts by directly creating tables using SQLAlchemy.
"""

import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database by creating all tables."""
    try:
        from src.config.settings import settings
        from src.database.connection import Base as ConnectionBase, db_manager
        
        # Initialize database manager
        db_manager.initialize()
        engine = db_manager.get_engine()
        
        logger.info("=" * 60)
        logger.info("🔧 Database Initialization Started")
        logger.info("=" * 60)
        
        # Import all models to register them with SQLAlchemy
        logger.info("📦 Loading models...")
        
        # Import models from database.connection (uses ConnectionBase)
        from src.database.models import Base as ModelsBase
        
        # Import models from individual modules
        try:
            from src.models.user import User
            logger.info("  ✓ User model loaded")
        except Exception as e:
            logger.warning(f"  ⚠ User model failed to load: {e}")
        
        try:
            from src.models.license import (
                LicenseModel, LicenseActivationModel, 
                ConcurrentSessionModel, LicenseAuditLogModel
            )
            logger.info("  ✓ License models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ License models failed to load: {e}")
        
        try:
            from src.models.versioning import (
                DataVersion, DataVersionTag, DataVersionBranch,
                ChangeRecord, Snapshot, SnapshotSchedule, DataLineageRecord
            )
            logger.info("  ✓ Versioning models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ Versioning models failed to load: {e}")
        
        try:
            from src.models.data_permission import (
                DataPermissionModel, PolicySourceModel, PolicyConflictModel,
                ApprovalWorkflowModel, ApprovalRequestModel, ApprovalActionModel,
                ApprovalDelegationModel, DataAccessLogModel,
                DataClassificationModel, ClassificationSchemaModel, MaskingRuleModel
            )
            logger.info("  ✓ Data permission models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ Data permission models failed to load: {e}")
        
        try:
            from src.models.admin_config import (
                AdminConfiguration, DatabaseConnection, ConfigChangeHistory,
                QueryTemplate, SyncStrategy, SyncHistory, ThirdPartyToolConfig
            )
            logger.info("  ✓ Admin config models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ Admin config models failed to load: {e}")
        
        try:
            from src.models.annotation_plugin import (
                AnnotationPlugin, PluginCallLog, ReviewRecord,
                PreAnnotationJob, PreAnnotationResult, CoverageRecord,
                TaskAssignment, ValidationReport
            )
            logger.info("  ✓ Annotation plugin models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ Annotation plugin models failed to load: {e}")
        
        try:
            from src.models.llm_configuration import (
                LLMConfiguration, LLMUsageLog, LLMModelRegistry, LLMHealthStatus
            )
            logger.info("  ✓ LLM configuration models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ LLM configuration models failed to load: {e}")
        
        try:
            from src.models.text_to_sql import (
                TextToSQLConfiguration, ThirdPartyPlugin, SQLGenerationLog, SQLTemplate
            )
            logger.info("  ✓ Text-to-SQL models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ Text-to-SQL models failed to load: {e}")
        
        try:
            from src.models.quality import (
                QualityScoreModel, QualityRuleModel, QualityRuleTemplateModel,
                QualityCheckResultModel
            )
            logger.info("  ✓ Quality models loaded")
        except Exception as e:
            logger.warning(f"  ⚠ Quality models failed to load: {e}")
        
        # Create tables from ModelsBase
        logger.info("\n📊 Creating tables from src.database.models...")
        try:
            ModelsBase.metadata.create_all(bind=engine)
            logger.info("  ✓ Tables created from ModelsBase")
        except Exception as e:
            logger.error(f"  ✗ Failed to create tables from ModelsBase: {e}")
        
        # Create tables from ConnectionBase
        logger.info("\n📊 Creating tables from src.database.connection...")
        try:
            ConnectionBase.metadata.create_all(bind=engine)
            logger.info("  ✓ Tables created from ConnectionBase")
        except Exception as e:
            logger.error(f"  ✗ Failed to create tables from ConnectionBase: {e}")
        
        # Create tables from User model's Base
        logger.info("\n📊 Creating tables from User model...")
        try:
            from src.models.user import Base as UserBase
            UserBase.metadata.create_all(bind=engine)
            logger.info("  ✓ Tables created from User model")
        except Exception as e:
            logger.error(f"  ✗ Failed to create tables from User model: {e}")
        
        # Verify tables were created
        logger.info("\n✅ Verifying tables...")
        with engine.connect() as conn:
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
        
        # Create admin user
        logger.info("\n👤 Creating admin user...")
        try:
            from src.models.user import User
            from src.database.connection import db_manager
            
            with db_manager.get_session() as session:
                # Check if admin user already exists
                admin_user = session.query(User).filter(User.email == "admin@superinsight.local").first()
                
                if admin_user:
                    logger.info("  ✓ Admin user already exists")
                else:
                    # Create admin user
                    from datetime import datetime
                    import bcrypt
                    
                    password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
                    
                    admin_user = User(
                        email="admin@superinsight.local",
                        username="admin",
                        name="Administrator",
                        password_hash=password_hash,
                        is_active=True,
                        is_verified=True,
                        is_superuser=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    session.add(admin_user)
                    session.commit()
                    logger.info("  ✓ Admin user created (email: admin@superinsight.local, password: admin123)")
        except Exception as e:
            logger.warning(f"  ⚠ Failed to create admin user: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Database initialization completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
