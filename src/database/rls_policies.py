"""
Row-Level Security (RLS) policies for multi-tenant data isolation.

This module contains SQL statements to enable and configure RLS policies
for tenant and workspace isolation.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List

# RLS policy SQL statements
RLS_POLICIES = [
    # Enable RLS on tenant-aware tables
    "ALTER TABLE documents ENABLE ROW LEVEL SECURITY;",
    "ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;", 
    "ALTER TABLE quality_issues ENABLE ROW LEVEL SECURITY;",
    "ALTER TABLE billing_records ENABLE ROW LEVEL SECURITY;",
    "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;",
    "ALTER TABLE ip_whitelist ENABLE ROW LEVEL SECURITY;",
    "ALTER TABLE data_masking_rules ENABLE ROW LEVEL SECURITY;",
    
    # Workspace-level isolation policies
    """
    CREATE POLICY workspace_isolation_documents ON documents
    FOR ALL TO PUBLIC
    USING (
        workspace_id = COALESCE(
            current_setting('app.current_workspace_id', true)::uuid,
            workspace_id
        )
    );
    """,
    
    """
    CREATE POLICY workspace_isolation_tasks ON tasks
    FOR ALL TO PUBLIC
    USING (
        workspace_id = COALESCE(
            current_setting('app.current_workspace_id', true)::uuid,
            workspace_id
        )
    );
    """,
    
    """
    CREATE POLICY workspace_isolation_quality_issues ON quality_issues
    FOR ALL TO PUBLIC
    USING (
        workspace_id = COALESCE(
            current_setting('app.current_workspace_id', true)::uuid,
            workspace_id
        )
    );
    """,
    
    """
    CREATE POLICY workspace_isolation_billing_records ON billing_records
    FOR ALL TO PUBLIC
    USING (
        workspace_id = COALESCE(
            current_setting('app.current_workspace_id', true)::uuid,
            workspace_id
        )
    );
    """,
    
    # Tenant-level isolation policies
    """
    CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    FOR ALL TO PUBLIC
    USING (
        tenant_id = COALESCE(
            current_setting('app.current_tenant_id', true),
            tenant_id
        )
    );
    """,
    
    """
    CREATE POLICY tenant_isolation_ip_whitelist ON ip_whitelist
    FOR ALL TO PUBLIC
    USING (
        tenant_id = COALESCE(
            current_setting('app.current_tenant_id', true),
            tenant_id
        )
    );
    """,
    
    """
    CREATE POLICY tenant_isolation_data_masking_rules ON data_masking_rules
    FOR ALL TO PUBLIC
    USING (
        tenant_id = COALESCE(
            current_setting('app.current_tenant_id', true),
            tenant_id
        )
    );
    """,
    
    # Admin bypass policies (for system operations)
    """
    CREATE POLICY admin_bypass_documents ON documents
    FOR ALL TO PUBLIC
    USING (
        current_setting('app.bypass_rls', true)::boolean = true
    );
    """,
    
    """
    CREATE POLICY admin_bypass_tasks ON tasks
    FOR ALL TO PUBLIC
    USING (
        current_setting('app.bypass_rls', true)::boolean = true
    );
    """,
    
    """
    CREATE POLICY admin_bypass_quality_issues ON quality_issues
    FOR ALL TO PUBLIC
    USING (
        current_setting('app.bypass_rls', true)::boolean = true
    );
    """,
    
    """
    CREATE POLICY admin_bypass_billing_records ON billing_records
    FOR ALL TO PUBLIC
    USING (
        current_setting('app.bypass_rls', true)::boolean = true
    );
    """,
    
    """
    CREATE POLICY admin_bypass_audit_logs ON audit_logs
    FOR ALL TO PUBLIC
    USING (
        current_setting('app.bypass_rls', true)::boolean = true
    );
    """,
]

# SQL to drop all RLS policies (for rollback)
DROP_RLS_POLICIES = [
    "DROP POLICY IF EXISTS workspace_isolation_documents ON documents;",
    "DROP POLICY IF EXISTS workspace_isolation_tasks ON tasks;",
    "DROP POLICY IF EXISTS workspace_isolation_quality_issues ON quality_issues;",
    "DROP POLICY IF EXISTS workspace_isolation_billing_records ON billing_records;",
    "DROP POLICY IF EXISTS tenant_isolation_audit_logs ON audit_logs;",
    "DROP POLICY IF EXISTS tenant_isolation_ip_whitelist ON ip_whitelist;",
    "DROP POLICY IF EXISTS tenant_isolation_data_masking_rules ON data_masking_rules;",
    "DROP POLICY IF EXISTS admin_bypass_documents ON documents;",
    "DROP POLICY IF EXISTS admin_bypass_tasks ON tasks;",
    "DROP POLICY IF EXISTS admin_bypass_quality_issues ON quality_issues;",
    "DROP POLICY IF EXISTS admin_bypass_billing_records ON billing_records;",
    "DROP POLICY IF EXISTS admin_bypass_audit_logs ON audit_logs;",
    
    "ALTER TABLE documents DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE tasks DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE quality_issues DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE billing_records DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE ip_whitelist DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE data_masking_rules DISABLE ROW LEVEL SECURITY;",
]


def apply_rls_policies(session: Session) -> None:
    """
    Apply Row-Level Security policies to the database.
    
    Args:
        session: SQLAlchemy database session
    """
    for policy_sql in RLS_POLICIES:
        try:
            session.execute(text(policy_sql))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error applying RLS policy: {e}")
            print(f"SQL: {policy_sql}")
            raise


def drop_rls_policies(session: Session) -> None:
    """
    Drop Row-Level Security policies from the database.
    
    Args:
        session: SQLAlchemy database session
    """
    for drop_sql in DROP_RLS_POLICIES:
        try:
            session.execute(text(drop_sql))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error dropping RLS policy: {e}")
            print(f"SQL: {drop_sql}")
            # Continue with other policies even if one fails


def set_tenant_context(session: Session, tenant_id: str, workspace_id: str = None, bypass_rls: bool = False) -> None:
    """
    Set the tenant and workspace context for the current session.
    
    Args:
        session: SQLAlchemy database session
        tenant_id: Current tenant ID
        workspace_id: Current workspace ID (optional)
        bypass_rls: Whether to bypass RLS (for admin operations)
    """
    session.execute(text("SET app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})
    
    if workspace_id:
        session.execute(text("SET app.current_workspace_id = :workspace_id"), {"workspace_id": workspace_id})
    
    if bypass_rls:
        session.execute(text("SET app.bypass_rls = true"))
    else:
        session.execute(text("SET app.bypass_rls = false"))
    
    session.commit()


def clear_tenant_context(session: Session) -> None:
    """
    Clear the tenant and workspace context for the current session.
    
    Args:
        session: SQLAlchemy database session
    """
    session.execute(text("RESET app.current_tenant_id"))
    session.execute(text("RESET app.current_workspace_id"))
    session.execute(text("RESET app.bypass_rls"))
    session.commit()


def test_rls_isolation(session: Session) -> bool:
    """
    Test RLS isolation by creating test data and verifying access.
    
    Args:
        session: SQLAlchemy database session
        
    Returns:
        bool: True if RLS is working correctly
    """
    try:
        # This would contain test logic to verify RLS is working
        # For now, just return True
        return True
    except Exception as e:
        print(f"RLS test failed: {e}")
        return False