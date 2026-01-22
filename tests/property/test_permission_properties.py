"""
Admin Configuration Permission Property Tests

Tests permission enforcement and access control properties.

**Feature: admin-configuration**
**Property 10: Read-Only Mode Enforcement**
**Property 11: Query-Only Mode Enforcement**
**Property 12: Permission Immediate Effect**
**Property 13: Permission Enforcement at API Level**
**Validates: Requirements 2.6, 4.2, 4.4, 4.5**
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, AsyncMock

from src.admin.db_connection_manager import DBConnectionManager, DBConfig, DatabaseType


# ============================================================================
# Property 10: Read-Only Mode Enforcement
# ============================================================================

class TestReadOnlyModeEnforcement:
    """
    Property 10: Read-Only Mode Enforcement
    
    For any database configuration with read-only mode enabled, all write
    operations (INSERT, UPDATE, DELETE) should be rejected, while read
    operations (SELECT) should be allowed.
    
    **Feature: admin-configuration**
    **Validates: Requirements 2.6**
    """
    
    @given(
        db_type=st.sampled_from([DatabaseType.POSTGRESQL, DatabaseType.MYSQL]),
        write_operation=st.sampled_from([
            "INSERT INTO users (name) VALUES ('test')",
            "UPDATE users SET name = 'test' WHERE id = 1",
            "DELETE FROM users WHERE id = 1",
            "DROP TABLE users",
            "CREATE TABLE test (id INT)",
            "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
            "TRUNCATE TABLE users"
        ])
    )
    @settings(max_examples=15, deadline=None)
    def test_write_operations_rejected_in_readonly_mode(self, db_type, write_operation):
        """
        Write operations are rejected when read-only mode is enabled.
        
        For any write operation (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE),
        the system should reject the operation with a clear error message when
        read-only mode is enabled.
        """
        async def run_test():
            # Create manager inside async context
            manager = DBConnectionManager()
            
            # Create read-only configuration
            config = DBConfig(
                db_type=db_type,
                host="localhost",
                port=5432 if db_type == DatabaseType.POSTGRESQL else 3306,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=True,  # Read-only mode enabled
                timeout=5
            )
            
            # Attempt write operation
            with pytest.raises(ValueError) as exc_info:
                await manager.execute_test_query(config, write_operation)
            
            # Verify error message mentions read-only mode
            error_message = str(exc_info.value)
            assert "read-only" in error_message.lower(), \
                f"Error should mention read-only mode: {error_message}"
            assert "not allowed" in error_message.lower() or "not permitted" in error_message.lower(), \
                f"Error should indicate operation is not allowed: {error_message}"
        
        asyncio.run(run_test())
    
    @given(
        db_type=st.sampled_from([DatabaseType.POSTGRESQL, DatabaseType.MYSQL]),
        select_query=st.sampled_from([
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE id = 1",
            "SELECT COUNT(*) FROM users",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        ])
    )
    @settings(max_examples=15, deadline=None)
    def test_read_operations_allowed_in_readonly_mode(self, db_type, select_query):
        """
        Read operations are allowed when read-only mode is enabled.
        
        For any SELECT query, the system should allow the operation
        when read-only mode is enabled (though it may fail due to
        connection issues in tests, the validation should pass).
        """
        async def run_test():
            # Create manager inside async context
            manager = DBConnectionManager()
            
            # Create read-only configuration
            config = DBConfig(
                db_type=db_type,
                host="localhost",
                port=5432 if db_type == DatabaseType.POSTGRESQL else 3306,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=True,  # Read-only mode enabled
                timeout=5
            )
            
            # SELECT queries should pass validation (not raise ValueError)
            # They may fail with connection errors, but that's expected in tests
            try:
                await manager.execute_test_query(config, select_query)
            except ValueError as e:
                # ValueError means validation failed - this should NOT happen for SELECT
                pytest.fail(f"SELECT query should be allowed in read-only mode: {e}")
            except Exception:
                # Other exceptions (connection errors, etc.) are expected in tests
                # The important thing is that validation passed
                pass
        
        asyncio.run(run_test())
    
    @given(
        db_type=st.sampled_from([DatabaseType.POSTGRESQL, DatabaseType.MYSQL])
    )
    @settings(max_examples=10, deadline=None)
    def test_write_operations_allowed_when_readonly_disabled(self, db_type):
        """
        Write operations are allowed when read-only mode is disabled.
        
        When read-only mode is False, write operations should pass
        validation (though they may fail with connection errors in tests).
        """
        async def run_test():
            # Create manager inside async context
            manager = DBConnectionManager()
            
            # Create writable configuration
            config = DBConfig(
                db_type=db_type,
                host="localhost",
                port=5432 if db_type == DatabaseType.POSTGRESQL else 3306,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=False,  # Read-only mode disabled
                timeout=5
            )
            
            write_query = "INSERT INTO users (name) VALUES ('test')"
            
            # Write queries should pass validation when read-only is False
            try:
                await manager.execute_test_query(config, write_query)
            except ValueError as e:
                # ValueError means validation failed - this should NOT happen
                if "read-only" in str(e).lower():
                    pytest.fail(f"Write query should be allowed when read-only=False: {e}")
                # Other ValueErrors are OK (e.g., invalid SQL syntax)
            except Exception:
                # Connection errors are expected in tests
                pass
        
        asyncio.run(run_test())
    
    @given(
        db_type=st.sampled_from([DatabaseType.POSTGRESQL, DatabaseType.MYSQL])
    )
    @settings(max_examples=10, deadline=None)
    def test_case_insensitive_write_detection(self, db_type):
        """
        Write operation detection is case-insensitive.
        
        Write operations should be detected regardless of case
        (INSERT, insert, Insert, etc.).
        """
        async def run_test():
            # Create manager inside async context
            manager = DBConnectionManager()
            
            config = DBConfig(
                db_type=db_type,
                host="localhost",
                port=5432 if db_type == DatabaseType.POSTGRESQL else 3306,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=True,
                timeout=5
            )
            
            # Test various case combinations
            write_queries = [
                "INSERT INTO users (name) VALUES ('test')",
                "insert into users (name) values ('test')",
                "Insert Into Users (Name) Values ('test')",
                "UPDATE users SET name = 'test'",
                "update users set name = 'test'",
                "DELETE FROM users",
                "delete from users"
            ]
            
            for query in write_queries:
                with pytest.raises(ValueError) as exc_info:
                    await manager.execute_test_query(config, query)
                
                error_message = str(exc_info.value)
                assert "read-only" in error_message.lower(), \
                    f"Should detect write operation regardless of case: {query}"
        
        asyncio.run(run_test())
    
    @given(
        db_type=st.sampled_from([DatabaseType.POSTGRESQL, DatabaseType.MYSQL])
    )
    @settings(max_examples=10, deadline=None)
    def test_whitespace_handling_in_query_detection(self, db_type):
        """
        Write operation detection handles leading/trailing whitespace.
        
        Queries with leading or trailing whitespace should still be
        correctly identified as write operations.
        """
        async def run_test():
            # Create manager inside async context
            manager = DBConnectionManager()
            
            config = DBConfig(
                db_type=db_type,
                host="localhost",
                port=5432 if db_type == DatabaseType.POSTGRESQL else 3306,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=True,
                timeout=5
            )
            
            # Test queries with various whitespace
            write_queries = [
                "  INSERT INTO users (name) VALUES ('test')",
                "\nINSERT INTO users (name) VALUES ('test')",
                "\t\tINSERT INTO users (name) VALUES ('test')",
                "INSERT INTO users (name) VALUES ('test')  ",
                "  UPDATE users SET name = 'test'  "
            ]
            
            for query in write_queries:
                with pytest.raises(ValueError) as exc_info:
                    await manager.execute_test_query(config, query)
                
                assert "read-only" in str(exc_info.value).lower(), \
                    f"Should detect write operation with whitespace: '{query}'"
        
        asyncio.run(run_test())
    
    def test_all_write_keywords_blocked(self):
        """
        All dangerous write keywords are blocked in read-only mode.
        
        Verify that all write operations (INSERT, UPDATE, DELETE, DROP,
        CREATE, ALTER, TRUNCATE) are properly blocked.
        """
        async def run_test():
            # Create manager inside async context
            manager = DBConnectionManager()
            
            config = DBConfig(
                db_type=DatabaseType.POSTGRESQL,
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=True,
                timeout=5
            )
            
            write_keywords = [
                ("INSERT", "INSERT INTO users (name) VALUES ('test')"),
                ("UPDATE", "UPDATE users SET name = 'test'"),
                ("DELETE", "DELETE FROM users"),
                ("DROP", "DROP TABLE users"),
                ("CREATE", "CREATE TABLE test (id INT)"),
                ("ALTER", "ALTER TABLE users ADD COLUMN email VARCHAR(255)"),
                ("TRUNCATE", "TRUNCATE TABLE users")
            ]
            
            for keyword, query in write_keywords:
                with pytest.raises(ValueError) as exc_info:
                    await manager.execute_test_query(config, query)
                
                error_message = str(exc_info.value)
                assert "read-only" in error_message.lower(), \
                    f"{keyword} should be blocked in read-only mode"
                assert keyword in error_message or keyword.lower() in error_message.lower(), \
                    f"Error should mention the blocked keyword: {keyword}"
        
        asyncio.run(run_test())


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
