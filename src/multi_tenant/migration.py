"""
Multi-tenant migration utilities for existing data.

This module provides utilities to migrate existing single-tenant data
to the new multi-tenant structure with backward compatibility.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.database.connection import get_db_session
from src.multi_tenant.services import TenantManager, WorkspaceManager, UserTenantManager
from src.database.multi_tenant_models import TenantRole
from src.database.rls_policies import apply_rls_policies, set_tenant_context

logger = logging.getLogger(__name__)


class TenantMigrationService:
    """Service for migrating existing data to multi-tenant structure."""
    
    def __init__(self, session: Session):
        self.session = session
        self.tenant_manager = TenantManager(session)
        self.workspace_manager = WorkspaceManager(session)
        self.user_tenant_manager = UserTenantManager(session)
    
    def create_default_tenant(
        self,
        tenant_id: str = "default",
        name: str = "Default Organization",
        display_name: str = "Default Organization"
    ) -> str:
        """
        Create a default tenant for existing data.
        
        Args:
            tenant_id: Default tenant ID
            name: Tenant name
            display_name: Display name
            
        Returns:
            Created tenant ID
        """
        try:
            # Check if default tenant already exists
            existing_tenant = self.tenant_manager.get_tenant(tenant_id)
            if existing_tenant:
                logger.info(f"Default tenant {tenant_id} already exists")
                return tenant_id
            
            # Create default tenant with generous quotas
            tenant = self.tenant_manager.create_tenant(
                tenant_id=tenant_id,
                name=name,
                display_name=display_name,
                description="Default tenant for existing data migration",
                max_users=1000,
                max_workspaces=100,
                max_storage_gb=1000.0,
                max_api_calls_per_hour=100000,
                billing_plan="enterprise"
            )
            
            logger.info(f"Created default tenant: {tenant_id}")
            return tenant.id
            
        except Exception as e:
            logger.error(f"Error creating default tenant: {e}")
            raise
    
    def migrate_existing_users(
        self,
        tenant_id: str = "default",
        default_role: TenantRole = TenantRole.MEMBER
    ) -> int:
        """
        Migrate existing users to the default tenant.
        
        Args:
            tenant_id: Target tenant ID
            default_role: Default role for migrated users
            
        Returns:
            Number of users migrated
        """
        try:
            # Get all existing users
            users_query = text("SELECT id, email, is_superuser FROM users WHERE id NOT IN (SELECT user_id FROM user_tenant_associations)")
            result = self.session.execute(users_query)
            users = result.fetchall()
            
            migrated_count = 0
            
            for user in users:
                user_id = UUID(user.id) if isinstance(user.id, str) else user.id
                
                # Determine role based on user type
                role = TenantRole.OWNER if user.is_superuser else default_role
                is_default = True  # First tenant is default
                
                try:
                    self.user_tenant_manager.invite_user_to_tenant(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        role=role,
                        is_default_tenant=is_default
                    )
                    migrated_count += 1
                    logger.debug(f"Migrated user {user.email} to tenant {tenant_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate user {user.email}: {e}")
                    continue
            
            logger.info(f"Migrated {migrated_count} users to tenant {tenant_id}")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Error migrating users: {e}")
            raise
    
    def migrate_existing_data_to_tenant(
        self,
        tenant_id: str = "default",
        workspace_name: str = "default"
    ) -> Dict[str, int]:
        """
        Migrate existing data (tasks, annotations, etc.) to tenant/workspace.
        
        Args:
            tenant_id: Target tenant ID
            workspace_name: Target workspace name
            
        Returns:
            Dictionary with migration counts
        """
        try:
            # Get the default workspace
            workspace = self.workspace_manager.get_workspace_by_name(tenant_id, workspace_name)
            if not workspace:
                logger.error(f"Workspace {workspace_name} not found in tenant {tenant_id}")
                return {}
            
            migration_counts = {}
            
            # Set tenant context for the migration
            set_tenant_context(self.session, tenant_id, str(workspace.id))
            
            # Migrate tables that need tenant_id and workspace_id
            tables_to_migrate = [
                ("documents", "workspace_id"),
                ("tasks", "workspace_id"),
                ("quality_issues", "workspace_id"),
                ("billing_records", "workspace_id"),
                ("audit_logs", "tenant_id"),
                ("ip_whitelist", "tenant_id"),
                ("data_masking_rules", "tenant_id")
            ]
            
            for table_name, id_column in tables_to_migrate:
                try:
                    # Check if table exists and has the required column
                    check_query = text(f"""
                        SELECT COUNT(*) as count 
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' 
                        AND column_name = '{id_column}'
                    """)
                    result = self.session.execute(check_query)
                    if result.fetchone().count == 0:
                        logger.warning(f"Table {table_name} or column {id_column} not found, skipping")
                        continue
                    
                    # Update records that don't have tenant/workspace ID set
                    if id_column == "tenant_id":
                        update_query = text(f"""
                            UPDATE {table_name} 
                            SET {id_column} = :tenant_id 
                            WHERE {id_column} IS NULL
                        """)
                        result = self.session.execute(update_query, {"tenant_id": tenant_id})
                    else:  # workspace_id
                        update_query = text(f"""
                            UPDATE {table_name} 
                            SET {id_column} = :workspace_id, tenant_id = :tenant_id
                            WHERE {id_column} IS NULL
                        """)
                        result = self.session.execute(update_query, {
                            "workspace_id": str(workspace.id),
                            "tenant_id": tenant_id
                        })
                    
                    migration_counts[table_name] = result.rowcount
                    logger.info(f"Migrated {result.rowcount} records in {table_name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate table {table_name}: {e}")
                    migration_counts[table_name] = 0
            
            self.session.commit()
            logger.info(f"Data migration completed: {migration_counts}")
            return migration_counts
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error migrating data: {e}")
            raise
    
    def create_tenant_from_existing_data(
        self,
        tenant_id: str,
        user_emails: List[str],
        admin_emails: List[str] = None
    ) -> str:
        """
        Create a new tenant and migrate specific users to it.
        
        Args:
            tenant_id: New tenant ID
            user_emails: List of user emails to migrate
            admin_emails: List of admin user emails
            
        Returns:
            Created tenant ID
        """
        try:
            admin_emails = admin_emails or []
            
            # Create tenant
            tenant = self.tenant_manager.create_tenant(
                tenant_id=tenant_id,
                name=tenant_id.replace("-", "_"),
                display_name=tenant_id.replace("-", " ").title(),
                description=f"Tenant created from existing data migration"
            )
            
            # Get users by email
            user_query = text("SELECT id, email, is_superuser FROM users WHERE email = ANY(:emails)")
            result = self.session.execute(user_query, {"emails": user_emails})
            users = result.fetchall()
            
            migrated_count = 0
            
            for user in users:
                user_id = UUID(user.id) if isinstance(user.id, str) else user.id
                
                # Determine role
                if user.email in admin_emails or user.is_superuser:
                    role = TenantRole.ADMIN
                else:
                    role = TenantRole.MEMBER
                
                try:
                    self.user_tenant_manager.invite_user_to_tenant(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        role=role,
                        is_default_tenant=False  # Not default for new tenants
                    )
                    migrated_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to add user {user.email} to tenant {tenant_id}: {e}")
            
            logger.info(f"Created tenant {tenant_id} with {migrated_count} users")
            return tenant.id
            
        except Exception as e:
            logger.error(f"Error creating tenant from existing data: {e}")
            raise
    
    def validate_migration(self, tenant_id: str = "default") -> Dict[str, Any]:
        """
        Validate the migration results.
        
        Args:
            tenant_id: Tenant ID to validate
            
        Returns:
            Validation results
        """
        try:
            results = {
                "tenant_exists": False,
                "workspace_count": 0,
                "user_count": 0,
                "data_migration": {},
                "issues": []
            }
            
            # Check tenant exists
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if tenant:
                results["tenant_exists"] = True
                
                # Count workspaces
                workspaces = self.workspace_manager.list_workspaces(tenant_id)
                results["workspace_count"] = len(workspaces)
                
                # Count users
                user_associations = self.user_tenant_manager.get_tenant_users(tenant_id)
                results["user_count"] = len(user_associations)
                
                # Check data migration
                tables_to_check = [
                    ("documents", "workspace_id"),
                    ("tasks", "workspace_id"),
                    ("audit_logs", "tenant_id")
                ]
                
                for table_name, id_column in tables_to_check:
                    try:
                        if id_column == "tenant_id":
                            query = text(f"SELECT COUNT(*) as count FROM {table_name} WHERE {id_column} = :tenant_id")
                            result = self.session.execute(query, {"tenant_id": tenant_id})
                        else:
                            # For workspace_id, check any workspace in the tenant
                            workspace_ids = [str(w.id) for w in workspaces]
                            if workspace_ids:
                                query = text(f"SELECT COUNT(*) as count FROM {table_name} WHERE {id_column} = ANY(:workspace_ids)")
                                result = self.session.execute(query, {"workspace_ids": workspace_ids})
                            else:
                                results["data_migration"][table_name] = 0
                                continue
                        
                        count = result.fetchone().count
                        results["data_migration"][table_name] = count
                        
                    except Exception as e:
                        results["issues"].append(f"Failed to check {table_name}: {e}")
                        results["data_migration"][table_name] = -1
            else:
                results["issues"].append(f"Tenant {tenant_id} not found")
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating migration: {e}")
            return {"error": str(e)}
    
    def rollback_migration(self, tenant_id: str = "default") -> bool:
        """
        Rollback migration changes (use with caution).
        
        Args:
            tenant_id: Tenant ID to rollback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.warning(f"Rolling back migration for tenant {tenant_id}")
            
            # Remove tenant/workspace IDs from data tables
            tables_to_rollback = [
                ("documents", "workspace_id"),
                ("tasks", "workspace_id"),
                ("quality_issues", "workspace_id"),
                ("billing_records", "workspace_id"),
                ("audit_logs", "tenant_id"),
                ("ip_whitelist", "tenant_id"),
                ("data_masking_rules", "tenant_id")
            ]
            
            for table_name, id_column in tables_to_rollback:
                try:
                    if id_column == "tenant_id":
                        update_query = text(f"UPDATE {table_name} SET {id_column} = NULL WHERE {id_column} = :tenant_id")
                        self.session.execute(update_query, {"tenant_id": tenant_id})
                    else:
                        # Get workspace IDs for this tenant
                        workspaces = self.workspace_manager.list_workspaces(tenant_id)
                        workspace_ids = [str(w.id) for w in workspaces]
                        if workspace_ids:
                            update_query = text(f"UPDATE {table_name} SET {id_column} = NULL, tenant_id = NULL WHERE {id_column} = ANY(:workspace_ids)")
                            self.session.execute(update_query, {"workspace_ids": workspace_ids})
                    
                    logger.info(f"Rolled back {table_name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to rollback {table_name}: {e}")
            
            # Remove user associations
            user_associations = self.user_tenant_manager.get_tenant_users(tenant_id)
            for assoc in user_associations:
                self.user_tenant_manager.remove_user_from_tenant(assoc.user_id, tenant_id)
            
            # Remove tenant (this will cascade to workspaces)
            self.tenant_manager.deactivate_tenant(tenant_id)
            
            self.session.commit()
            logger.info(f"Migration rollback completed for tenant {tenant_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error rolling back migration: {e}")
            return False


def run_full_migration(
    tenant_id: str = "default",
    tenant_name: str = "Default Organization",
    apply_rls: bool = True
) -> Dict[str, Any]:
    """
    Run complete migration process.
    
    Args:
        tenant_id: Default tenant ID
        tenant_name: Default tenant name
        apply_rls: Whether to apply RLS policies
        
    Returns:
        Migration results
    """
    logger.info("🚀 Starting full multi-tenant migration...")
    
    session = next(get_db_session())
    migration_service = TenantMigrationService(session)
    
    try:
        results = {
            "tenant_created": False,
            "users_migrated": 0,
            "data_migrated": {},
            "rls_applied": False,
            "validation": {},
            "success": False
        }
        
        # Step 1: Create default tenant
        logger.info("📝 Step 1: Creating default tenant...")
        created_tenant_id = migration_service.create_default_tenant(
            tenant_id=tenant_id,
            name=tenant_name,
            display_name=tenant_name
        )
        results["tenant_created"] = True
        logger.info(f"✅ Default tenant created: {created_tenant_id}")
        
        # Step 2: Migrate existing users
        logger.info("👥 Step 2: Migrating existing users...")
        users_migrated = migration_service.migrate_existing_users(tenant_id)
        results["users_migrated"] = users_migrated
        logger.info(f"✅ Migrated {users_migrated} users")
        
        # Step 3: Migrate existing data
        logger.info("📊 Step 3: Migrating existing data...")
        data_migrated = migration_service.migrate_existing_data_to_tenant(tenant_id)
        results["data_migrated"] = data_migrated
        logger.info(f"✅ Data migration completed: {data_migrated}")
        
        # Step 4: Apply RLS policies
        if apply_rls:
            logger.info("🔒 Step 4: Applying RLS policies...")
            try:
                apply_rls_policies(session)
                results["rls_applied"] = True
                logger.info("✅ RLS policies applied")
            except Exception as e:
                logger.warning(f"⚠️ RLS policies failed: {e}")
                results["rls_applied"] = False
        
        # Step 5: Validate migration
        logger.info("🔍 Step 5: Validating migration...")
        validation = migration_service.validate_migration(tenant_id)
        results["validation"] = validation
        
        if validation.get("tenant_exists") and validation.get("user_count", 0) > 0:
            results["success"] = True
            logger.info("🎉 Migration completed successfully!")
        else:
            logger.warning("⚠️ Migration completed with issues")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return {"error": str(e), "success": False}
    
    finally:
        session.close()


if __name__ == "__main__":
    # Run migration when script is executed directly
    import sys
    
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    tenant_name = sys.argv[2] if len(sys.argv) > 2 else "Default Organization"
    
    results = run_full_migration(tenant_id, tenant_name)
    
    print("\n📋 Migration Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")
    
    if results.get("success"):
        print("\n🎉 Migration completed successfully!")
        exit(0)
    else:
        print("\n❌ Migration failed!")
        exit(1)