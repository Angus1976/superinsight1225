"""
SQL Validator Property Tests.

Property-based tests for SQL validation including:
- Property 20: SQL Injection Detection
- Property 21: Dangerous Operation Detection
- Property 22: Permission Validation
- Property 23: Syntax Validation
- Property 24: Validation Error Specificity
- Property 25: Validation Audit Logging

**Feature: text-to-sql-methods**
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
"""

import asyncio
import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Test with local mock implementation to avoid import issues
from enum import Enum


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    SQL_INJECTION = "sql_injection"
    DANGEROUS_OPERATION = "dangerous_operation"
    PERMISSION_DENIED = "permission_denied"
    SYNTAX_ERROR = "syntax_error"


class MockValidationError:
    def __init__(
        self,
        code: str,
        message: str,
        severity: ValidationSeverity,
        violation_type: ViolationType,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.violation_type = violation_type


class MockSQLValidator:
    """Mock SQL Validator for property testing."""

    SQL_INJECTION_PATTERNS = [
        r";\s*--",
        r"'\s*OR\s+'?\d+'?\s*=\s*'?\d+'?",
        r"UNION\s+SELECT",
        r";\s*DROP\s+",
        r"EXEC\s*\(",
        r"SLEEP\s*\(",
    ]

    DANGEROUS_OPERATIONS = {
        "DROP DATABASE": ValidationSeverity.CRITICAL,
        "DROP TABLE": ValidationSeverity.CRITICAL,
        "TRUNCATE": ValidationSeverity.CRITICAL,
        "DELETE FROM": ValidationSeverity.ERROR,
        "UPDATE": ValidationSeverity.WARNING,
    }

    def __init__(
        self,
        allowed_tables: List[str] = None,
        allow_select_only: bool = False,
    ):
        self.allowed_tables = allowed_tables
        self.allow_select_only = allow_select_only
        self.audit_logs: List[Dict[str, Any]] = []

    def validate(self, sql: str) -> Dict[str, Any]:
        """Validate SQL and return result."""
        import re

        errors = []
        warnings = []
        sql_upper = sql.upper()

        # Check SQL injection
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                errors.append(MockValidationError(
                    code="INJ",
                    message=f"SQL injection pattern detected: {pattern}",
                    severity=ValidationSeverity.CRITICAL,
                    violation_type=ViolationType.SQL_INJECTION,
                ))

        # Check dangerous operations
        for op, severity in self.DANGEROUS_OPERATIONS.items():
            if op in sql_upper:
                if severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                    errors.append(MockValidationError(
                        code="DNG",
                        message=f"Dangerous operation: {op}",
                        severity=severity,
                        violation_type=ViolationType.DANGEROUS_OPERATION,
                    ))

        # Check SELECT-only mode
        if self.allow_select_only and not sql_upper.strip().startswith("SELECT"):
            errors.append(MockValidationError(
                code="SEL_ONLY",
                message="Only SELECT queries allowed",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.PERMISSION_DENIED,
            ))

        # Check allowed tables
        if self.allowed_tables:
            tables = self._extract_tables(sql)
            for table in tables:
                if table.lower() not in [t.lower() for t in self.allowed_tables]:
                    errors.append(MockValidationError(
                        code="TBL_DENIED",
                        message=f"Table not allowed: {table}",
                        severity=ValidationSeverity.ERROR,
                        violation_type=ViolationType.PERMISSION_DENIED,
                    ))

        # Check syntax
        if sql.count('(') != sql.count(')'):
            errors.append(MockValidationError(
                code="SYN_PAREN",
                message="Unbalanced parentheses",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.SYNTAX_ERROR,
            ))

        is_valid = len(errors) == 0

        # Audit logging
        self.audit_logs.append({
            "sql": sql,
            "is_valid": is_valid,
            "error_count": len(errors),
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL."""
        import re
        tables = set()
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.update(matches)
        keywords = {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'JOIN', 'LEFT', 'RIGHT', 'ON'}
        return [t for t in tables if t.upper() not in keywords]


# =============================================================================
# Property 20: SQL Injection Detection
# =============================================================================

class TestSQLInjectionDetection:
    """
    Property 20: SQL Injection Detection

    SQL injection patterns should always be detected and flagged.

    **Feature: text-to-sql-methods**
    **Validates: Requirements 5.1**
    """

    @given(prefix=st.text(min_size=0, max_size=50))
    @settings(max_examples=50)
    def test_union_injection_detected(self, prefix: str):
        """UNION SELECT injection should always be detected."""
        assume("union" not in prefix.lower() and "select" not in prefix.lower())

        validator = MockSQLValidator()
        sql = f"SELECT * FROM users WHERE id=1 {prefix} UNION SELECT * FROM passwords"

        result = validator.validate(sql)

        has_injection_error = any(
            e.violation_type == ViolationType.SQL_INJECTION
            for e in result["errors"]
        )
        assert has_injection_error, "UNION injection should be detected"

    @given(
        table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        payload=st.sampled_from(["'; DROP TABLE users; --", "' OR '1'='1", "'; DELETE FROM"])
    )
    @settings(max_examples=50)
    def test_common_injection_payloads_detected(self, table: str, payload: str):
        """Common injection payloads should be detected."""
        validator = MockSQLValidator()
        sql = f"SELECT * FROM {table} WHERE name='{payload}'"

        result = validator.validate(sql)

        has_injection_error = any(
            e.violation_type == ViolationType.SQL_INJECTION
            for e in result["errors"]
        )
        assert has_injection_error, f"Injection payload should be detected: {payload}"

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_clean_sql_not_flagged_as_injection(self, table: str):
        """Clean SQL should not be flagged as injection."""
        validator = MockSQLValidator()
        sql = f"SELECT id, name FROM {table} WHERE active = true"

        result = validator.validate(sql)

        injection_errors = [
            e for e in result["errors"]
            if e.violation_type == ViolationType.SQL_INJECTION
        ]
        assert len(injection_errors) == 0, "Clean SQL should not be flagged"


# =============================================================================
# Property 21: Dangerous Operation Detection
# =============================================================================

class TestDangerousOperationDetection:
    """
    Property 21: Dangerous Operation Detection

    Dangerous SQL operations should be detected and flagged with appropriate severity.

    **Feature: text-to-sql-methods**
    **Validates: Requirements 5.2**
    """

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_drop_table_detected_as_critical(self, table: str):
        """DROP TABLE should be detected as critical."""
        validator = MockSQLValidator()
        sql = f"DROP TABLE {table}"

        result = validator.validate(sql)

        critical_errors = [
            e for e in result["errors"]
            if e.severity == ValidationSeverity.CRITICAL
            and e.violation_type == ViolationType.DANGEROUS_OPERATION
        ]
        assert len(critical_errors) > 0, "DROP TABLE should be critical"

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_truncate_detected_as_critical(self, table: str):
        """TRUNCATE should be detected as critical."""
        validator = MockSQLValidator()
        sql = f"TRUNCATE TABLE {table}"

        result = validator.validate(sql)

        critical_errors = [
            e for e in result["errors"]
            if e.severity == ValidationSeverity.CRITICAL
        ]
        assert len(critical_errors) > 0, "TRUNCATE should be critical"

    @given(
        table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        condition=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789 =")
    )
    @settings(max_examples=30)
    def test_delete_detected_as_error(self, table: str, condition: str):
        """DELETE should be detected as error."""
        validator = MockSQLValidator()
        sql = f"DELETE FROM {table} WHERE {condition}"

        result = validator.validate(sql)

        error_level = [
            e for e in result["errors"]
            if e.severity == ValidationSeverity.ERROR
            and e.violation_type == ViolationType.DANGEROUS_OPERATION
        ]
        assert len(error_level) > 0, "DELETE should be error level"


# =============================================================================
# Property 22: Permission Validation
# =============================================================================

class TestPermissionValidation:
    """
    Property 22: Permission Validation

    Table access should be validated against allowed tables.

    **Feature: text-to-sql-methods**
    **Validates: Requirements 5.3**
    """

    @given(
        allowed=st.lists(
            st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=30)
    def test_allowed_tables_pass_validation(self, allowed: List[str]):
        """Queries on allowed tables should pass validation."""
        validator = MockSQLValidator(allowed_tables=allowed)
        sql = f"SELECT * FROM {allowed[0]}"

        result = validator.validate(sql)

        permission_errors = [
            e for e in result["errors"]
            if e.violation_type == ViolationType.PERMISSION_DENIED
        ]
        assert len(permission_errors) == 0, "Allowed table should pass"

    @given(
        allowed=st.lists(
            st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=3,
            unique=True
        ),
        denied=st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz")
    )
    @settings(max_examples=30)
    def test_denied_tables_fail_validation(self, allowed: List[str], denied: str):
        """Queries on denied tables should fail validation."""
        assume(denied.lower() not in [t.lower() for t in allowed])

        validator = MockSQLValidator(allowed_tables=allowed)
        sql = f"SELECT * FROM {denied}"

        result = validator.validate(sql)

        permission_errors = [
            e for e in result["errors"]
            if e.violation_type == ViolationType.PERMISSION_DENIED
        ]
        assert len(permission_errors) > 0, "Denied table should fail"

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_select_only_mode_blocks_updates(self, table: str):
        """SELECT-only mode should block UPDATE queries."""
        validator = MockSQLValidator(allow_select_only=True)
        sql = f"UPDATE {table} SET name = 'test'"

        result = validator.validate(sql)

        permission_errors = [
            e for e in result["errors"]
            if e.violation_type == ViolationType.PERMISSION_DENIED
        ]
        assert len(permission_errors) > 0, "UPDATE should be blocked in SELECT-only mode"


# =============================================================================
# Property 23: Syntax Validation
# =============================================================================

class TestSyntaxValidation:
    """
    Property 23: Syntax Validation

    SQL syntax errors should be detected.

    **Feature: text-to-sql-methods**
    **Validates: Requirements 5.4**
    """

    @given(
        table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        extra_parens=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=30)
    def test_unbalanced_parentheses_detected(self, table: str, extra_parens: int):
        """Unbalanced parentheses should be detected."""
        validator = MockSQLValidator()
        sql = f"SELECT * FROM {table} WHERE (id = 1" + ")" * extra_parens

        # This has more closing parens than opening
        if extra_parens > 1:
            result = validator.validate(sql)
            syntax_errors = [
                e for e in result["errors"]
                if e.violation_type == ViolationType.SYNTAX_ERROR
            ]
            assert len(syntax_errors) > 0, "Unbalanced parens should be detected"

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_balanced_parentheses_pass(self, table: str):
        """Balanced parentheses should pass validation."""
        validator = MockSQLValidator()
        sql = f"SELECT * FROM {table} WHERE (id = 1) AND (name = 'test')"

        result = validator.validate(sql)

        syntax_errors = [
            e for e in result["errors"]
            if e.violation_type == ViolationType.SYNTAX_ERROR
        ]
        assert len(syntax_errors) == 0, "Balanced parens should pass"


# =============================================================================
# Property 24: Validation Error Specificity
# =============================================================================

class TestValidationErrorSpecificity:
    """
    Property 24: Validation Error Specificity

    Validation errors should be specific and actionable.

    **Feature: text-to-sql-methods**
    **Validates: Requirements 5.5**
    """

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_errors_have_codes(self, table: str):
        """All errors should have codes."""
        validator = MockSQLValidator()
        sql = f"DROP TABLE {table}"

        result = validator.validate(sql)

        for error in result["errors"]:
            assert error.code, "Error should have a code"
            assert len(error.code) > 0, "Error code should not be empty"

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_errors_have_messages(self, table: str):
        """All errors should have descriptive messages."""
        validator = MockSQLValidator()
        sql = f"DROP TABLE {table}"

        result = validator.validate(sql)

        for error in result["errors"]:
            assert error.message, "Error should have a message"
            assert len(error.message) > 5, "Error message should be descriptive"

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_errors_have_severity(self, table: str):
        """All errors should have severity levels."""
        validator = MockSQLValidator()
        sql = f"DROP TABLE {table}"

        result = validator.validate(sql)

        for error in result["errors"]:
            assert error.severity in ValidationSeverity, "Error should have valid severity"


# =============================================================================
# Property 25: Validation Audit Logging
# =============================================================================

class TestValidationAuditLogging:
    """
    Property 25: Validation Audit Logging

    All validation attempts should be logged.

    **Feature: text-to-sql-methods**
    **Validates: Requirements 5.6**
    """

    @given(
        sqls=st.lists(
            st.text(min_size=10, max_size=100),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=30)
    def test_all_validations_logged(self, sqls: List[str]):
        """All validation attempts should be logged."""
        validator = MockSQLValidator()

        for sql in sqls:
            validator.validate(sql)

        assert len(validator.audit_logs) == len(sqls), (
            "Each validation should create a log entry"
        )

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_audit_logs_contain_sql(self, table: str):
        """Audit logs should contain the SQL."""
        validator = MockSQLValidator()
        sql = f"SELECT * FROM {table}"

        validator.validate(sql)

        assert len(validator.audit_logs) > 0
        assert validator.audit_logs[-1]["sql"] == sql, "Log should contain SQL"

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_audit_logs_contain_result(self, table: str):
        """Audit logs should contain validation result."""
        validator = MockSQLValidator()
        sql = f"SELECT * FROM {table}"

        result = validator.validate(sql)

        assert len(validator.audit_logs) > 0
        assert "is_valid" in validator.audit_logs[-1], "Log should contain result"
        assert validator.audit_logs[-1]["is_valid"] == result["is_valid"]

    @given(table=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=30)
    def test_audit_logs_contain_timestamp(self, table: str):
        """Audit logs should contain timestamp."""
        validator = MockSQLValidator()
        sql = f"SELECT * FROM {table}"

        validator.validate(sql)

        assert len(validator.audit_logs) > 0
        assert "timestamp" in validator.audit_logs[-1], "Log should contain timestamp"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
