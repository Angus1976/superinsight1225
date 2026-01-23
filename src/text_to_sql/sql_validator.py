"""
SQL Validator for Text-to-SQL Methods module.

Provides comprehensive SQL validation including:
- SQL injection detection
- Dangerous operation detection
- Permission validation
- Syntax validation
- Audit logging
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Set
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    """Types of SQL validation violations."""
    SQL_INJECTION = "sql_injection"
    DANGEROUS_OPERATION = "dangerous_operation"
    PERMISSION_DENIED = "permission_denied"
    SYNTAX_ERROR = "syntax_error"
    SCHEMA_VIOLATION = "schema_violation"
    RESOURCE_LIMIT = "resource_limit"
    DEPRECATED_SYNTAX = "deprecated_syntax"


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"


# SQL Injection patterns
SQL_INJECTION_PATTERNS: List[str] = [
    r";\s*--",  # Comment after semicolon
    r"'\s*OR\s+'?\d+'?\s*=\s*'?\d+'?",  # OR 1=1 pattern
    r"'\s*OR\s+'\w+'\s*=\s*'\w+'",  # OR 'a'='a' pattern
    r"UNION\s+SELECT",  # UNION injection
    r";\s*DROP\s+",  # Drop after statement
    r";\s*DELETE\s+",  # Delete after statement
    r";\s*UPDATE\s+",  # Update after statement
    r";\s*INSERT\s+",  # Insert after statement
    r"EXEC\s*\(",  # EXEC function
    r"xp_\w+",  # SQL Server extended procedures
    r"BENCHMARK\s*\(",  # MySQL benchmark
    r"SLEEP\s*\(",  # Time-based injection
    r"WAITFOR\s+DELAY",  # SQL Server delay
    r"pg_sleep\s*\(",  # PostgreSQL sleep
    r"LOAD_FILE\s*\(",  # File access
    r"INTO\s+OUTFILE",  # File write
    r"INTO\s+DUMPFILE",  # File dump
]

# Dangerous operations
DANGEROUS_OPERATIONS: Dict[str, ValidationSeverity] = {
    "DROP DATABASE": ValidationSeverity.CRITICAL,
    "DROP TABLE": ValidationSeverity.CRITICAL,
    "DROP SCHEMA": ValidationSeverity.CRITICAL,
    "TRUNCATE": ValidationSeverity.CRITICAL,
    "DELETE FROM": ValidationSeverity.ERROR,
    "UPDATE": ValidationSeverity.WARNING,
    "INSERT": ValidationSeverity.WARNING,
    "ALTER TABLE": ValidationSeverity.ERROR,
    "CREATE TABLE": ValidationSeverity.WARNING,
    "GRANT": ValidationSeverity.ERROR,
    "REVOKE": ValidationSeverity.ERROR,
    "DROP INDEX": ValidationSeverity.ERROR,
    "DROP VIEW": ValidationSeverity.ERROR,
    "DROP PROCEDURE": ValidationSeverity.ERROR,
    "DROP FUNCTION": ValidationSeverity.ERROR,
}


# =============================================================================
# Data Models
# =============================================================================

class ValidationError(BaseModel):
    """Single validation error."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    severity: ValidationSeverity = Field(..., description="Error severity")
    violation_type: ViolationType = Field(..., description="Violation type")
    location: Optional[Dict[str, int]] = Field(None, description="Error location (line, column)")
    context: Optional[str] = Field(None, description="SQL context around error")
    suggestion: Optional[str] = Field(None, description="Fix suggestion")


class ValidationWarning(BaseModel):
    """Single validation warning."""
    code: str = Field(..., description="Warning code")
    message: str = Field(..., description="Warning message")
    severity: ValidationSeverity = Field(default=ValidationSeverity.WARNING)
    location: Optional[Dict[str, int]] = Field(None, description="Warning location")
    suggestion: Optional[str] = Field(None, description="Improvement suggestion")


class SQLValidationResult(BaseModel):
    """Complete SQL validation result."""
    validation_id: str = Field(default_factory=lambda: str(uuid4()))
    is_valid: bool = Field(..., description="Overall validation status")
    sql: str = Field(..., description="Validated SQL")
    sql_hash: str = Field(..., description="SQL hash for tracking")
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    execution_allowed: bool = Field(default=False, description="Whether execution is allowed")
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validation_time_ms: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TablePermission(BaseModel):
    """Table-level permission."""
    table_name: str
    can_select: bool = True
    can_insert: bool = False
    can_update: bool = False
    can_delete: bool = False
    allowed_columns: Optional[List[str]] = None


class ValidationConfig(BaseModel):
    """Validation configuration."""
    check_sql_injection: bool = True
    check_dangerous_operations: bool = True
    check_permissions: bool = True
    check_syntax: bool = True
    allow_select_only: bool = False
    max_tables: int = 10
    max_joins: int = 5
    max_subqueries: int = 3
    blocked_keywords: List[str] = Field(default_factory=list)
    allowed_tables: Optional[List[str]] = None
    table_permissions: Dict[str, TablePermission] = Field(default_factory=dict)


class ValidationAuditLog(BaseModel):
    """Audit log entry for validation."""
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: Optional[str] = None
    sql: str
    sql_hash: str
    validation_result: bool
    errors: List[str] = Field(default_factory=list)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    database_type: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# =============================================================================
# SQL Validator Class
# =============================================================================

class SQLValidator:
    """
    Comprehensive SQL Validator.

    Features:
    - SQL injection detection
    - Dangerous operation detection
    - Permission validation
    - Database-specific syntax validation
    - Audit logging
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        audit_enabled: bool = True,
    ):
        """
        Initialize SQL Validator.

        Args:
            config: Validation configuration
            audit_enabled: Whether to enable audit logging
        """
        self.config = config or ValidationConfig()
        self.audit_enabled = audit_enabled

        # Compile injection patterns
        self._injection_patterns: List[Pattern] = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for pattern in SQL_INJECTION_PATTERNS
        ]

        # Audit log storage (in production, use database)
        self._audit_logs: List[ValidationAuditLog] = []
        self._lock = asyncio.Lock()

    async def validate(
        self,
        sql: str,
        database_type: DatabaseType = DatabaseType.POSTGRESQL,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SQLValidationResult:
        """
        Validate SQL query comprehensively.

        Args:
            sql: SQL query to validate
            database_type: Target database type
            user_id: User performing the validation
            tenant_id: Tenant ID for multi-tenancy
            correlation_id: Correlation ID for tracking

        Returns:
            SQLValidationResult with validation details
        """
        start_time = datetime.utcnow()
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []

        # Generate SQL hash
        sql_hash = hashlib.md5(sql.encode()).hexdigest()

        # Run validations
        if self.config.check_sql_injection:
            injection_errors = self._check_sql_injection(sql)
            errors.extend(injection_errors)

        if self.config.check_dangerous_operations:
            dangerous_errors, dangerous_warnings = self._check_dangerous_operations(sql)
            errors.extend(dangerous_errors)
            warnings.extend(dangerous_warnings)

        if self.config.check_permissions:
            permission_errors = self._check_permissions(sql)
            errors.extend(permission_errors)

        if self.config.check_syntax:
            syntax_errors = self._check_syntax(sql, database_type)
            errors.extend(syntax_errors)

        # Check resource limits
        resource_warnings = self._check_resource_limits(sql)
        warnings.extend(resource_warnings)

        # Calculate validation time
        validation_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Determine if execution is allowed
        is_valid = len(errors) == 0
        has_critical = any(e.severity == ValidationSeverity.CRITICAL for e in errors)
        execution_allowed = is_valid and not has_critical

        result = SQLValidationResult(
            is_valid=is_valid,
            sql=sql,
            sql_hash=sql_hash,
            errors=errors,
            warnings=warnings,
            execution_allowed=execution_allowed,
            validation_time_ms=validation_time_ms,
            metadata={
                "database_type": database_type.value,
                "correlation_id": correlation_id,
            }
        )

        # Audit logging
        if self.audit_enabled:
            await self._log_validation(
                sql=sql,
                sql_hash=sql_hash,
                result=is_valid,
                errors=[e.message for e in errors],
                user_id=user_id,
                tenant_id=tenant_id,
                database_type=database_type.value,
                correlation_id=correlation_id,
            )

        return result

    def _check_sql_injection(self, sql: str) -> List[ValidationError]:
        """Check for SQL injection patterns."""
        errors = []

        for i, pattern in enumerate(self._injection_patterns):
            match = pattern.search(sql)
            if match:
                # Find location
                start = match.start()
                line = sql[:start].count('\n') + 1
                col = start - sql[:start].rfind('\n')

                errors.append(ValidationError(
                    code=f"INJ_{i+1:03d}",
                    message=f"Potential SQL injection detected: {SQL_INJECTION_PATTERNS[i]}",
                    severity=ValidationSeverity.CRITICAL,
                    violation_type=ViolationType.SQL_INJECTION,
                    location={"line": line, "column": col},
                    context=sql[max(0, start-20):min(len(sql), start+50)],
                    suggestion="Remove or sanitize the suspicious pattern"
                ))

        return errors

    def _check_dangerous_operations(
        self,
        sql: str
    ) -> tuple[List[ValidationError], List[ValidationWarning]]:
        """Check for dangerous SQL operations."""
        errors = []
        warnings = []
        sql_upper = sql.upper()

        for operation, severity in DANGEROUS_OPERATIONS.items():
            if operation in sql_upper:
                # Find location
                idx = sql_upper.find(operation)
                line = sql[:idx].count('\n') + 1
                col = idx - sql[:idx].rfind('\n')

                if severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                    errors.append(ValidationError(
                        code=f"DNG_{operation.replace(' ', '_')}",
                        message=f"Dangerous operation detected: {operation}",
                        severity=severity,
                        violation_type=ViolationType.DANGEROUS_OPERATION,
                        location={"line": line, "column": col},
                        suggestion=f"Review and confirm {operation} is intentional"
                    ))
                else:
                    warnings.append(ValidationWarning(
                        code=f"DNG_{operation.replace(' ', '_')}",
                        message=f"Data modification operation: {operation}",
                        severity=severity,
                        location={"line": line, "column": col},
                        suggestion="Ensure proper authorization for data modification"
                    ))

        # Check for SELECT-only mode
        if self.config.allow_select_only:
            if not sql_upper.strip().startswith("SELECT"):
                errors.append(ValidationError(
                    code="SEL_ONLY",
                    message="Only SELECT queries are allowed",
                    severity=ValidationSeverity.ERROR,
                    violation_type=ViolationType.PERMISSION_DENIED,
                    suggestion="Modify query to be a SELECT statement"
                ))

        return errors, warnings

    def _check_permissions(self, sql: str) -> List[ValidationError]:
        """Check table and column permissions."""
        errors = []

        # Extract tables from SQL (simplified)
        tables = self._extract_tables(sql)

        # Check against allowed tables
        if self.config.allowed_tables is not None:
            for table in tables:
                if table.lower() not in [t.lower() for t in self.config.allowed_tables]:
                    errors.append(ValidationError(
                        code="TBL_DENIED",
                        message=f"Access to table '{table}' is not permitted",
                        severity=ValidationSeverity.ERROR,
                        violation_type=ViolationType.PERMISSION_DENIED,
                        suggestion=f"Use one of the allowed tables: {self.config.allowed_tables}"
                    ))

        # Check table-specific permissions
        sql_upper = sql.upper()
        for table in tables:
            perm = self.config.table_permissions.get(table.lower())
            if perm:
                if "INSERT" in sql_upper and not perm.can_insert:
                    errors.append(ValidationError(
                        code="INS_DENIED",
                        message=f"INSERT permission denied for table '{table}'",
                        severity=ValidationSeverity.ERROR,
                        violation_type=ViolationType.PERMISSION_DENIED,
                    ))
                if "UPDATE" in sql_upper and not perm.can_update:
                    errors.append(ValidationError(
                        code="UPD_DENIED",
                        message=f"UPDATE permission denied for table '{table}'",
                        severity=ValidationSeverity.ERROR,
                        violation_type=ViolationType.PERMISSION_DENIED,
                    ))
                if "DELETE" in sql_upper and not perm.can_delete:
                    errors.append(ValidationError(
                        code="DEL_DENIED",
                        message=f"DELETE permission denied for table '{table}'",
                        severity=ValidationSeverity.ERROR,
                        violation_type=ViolationType.PERMISSION_DENIED,
                    ))

        return errors

    def _check_syntax(
        self,
        sql: str,
        database_type: DatabaseType
    ) -> List[ValidationError]:
        """Check SQL syntax for database type."""
        errors = []
        sql_upper = sql.upper()

        # Basic syntax checks
        # Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            errors.append(ValidationError(
                code="SYN_PAREN",
                message="Unbalanced parentheses in SQL",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.SYNTAX_ERROR,
                suggestion="Check and balance all parentheses"
            ))

        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            errors.append(ValidationError(
                code="SYN_QUOTE",
                message="Unbalanced single quotes in SQL",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.SYNTAX_ERROR,
                suggestion="Check and balance all single quotes"
            ))

        # Database-specific syntax
        if database_type == DatabaseType.POSTGRESQL:
            errors.extend(self._check_postgresql_syntax(sql))
        elif database_type == DatabaseType.MYSQL:
            errors.extend(self._check_mysql_syntax(sql))
        elif database_type == DatabaseType.ORACLE:
            errors.extend(self._check_oracle_syntax(sql))
        elif database_type == DatabaseType.SQLSERVER:
            errors.extend(self._check_sqlserver_syntax(sql))

        return errors

    def _check_postgresql_syntax(self, sql: str) -> List[ValidationError]:
        """PostgreSQL-specific syntax validation."""
        errors = []
        sql_upper = sql.upper()

        # Check for MySQL-specific syntax in PostgreSQL
        if "LIMIT" in sql_upper and "OFFSET" in sql_upper:
            # Check order: PostgreSQL uses LIMIT before OFFSET
            limit_idx = sql_upper.find("LIMIT")
            offset_idx = sql_upper.find("OFFSET")
            if offset_idx < limit_idx:
                errors.append(ValidationError(
                    code="PG_SYN_LIMIT",
                    message="PostgreSQL uses LIMIT before OFFSET",
                    severity=ValidationSeverity.WARNING,
                    violation_type=ViolationType.SYNTAX_ERROR,
                    suggestion="Reorder to: LIMIT n OFFSET m"
                ))

        # Check for backticks (MySQL style)
        if '`' in sql:
            errors.append(ValidationError(
                code="PG_SYN_BACKTICK",
                message="PostgreSQL uses double quotes, not backticks for identifiers",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.SYNTAX_ERROR,
                suggestion="Replace backticks with double quotes"
            ))

        return errors

    def _check_mysql_syntax(self, sql: str) -> List[ValidationError]:
        """MySQL-specific syntax validation."""
        errors = []

        # Check for PostgreSQL-specific syntax
        if '::' in sql:
            errors.append(ValidationError(
                code="MY_SYN_CAST",
                message="MySQL does not support :: casting syntax",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.SYNTAX_ERROR,
                suggestion="Use CAST(value AS type) instead"
            ))

        return errors

    def _check_oracle_syntax(self, sql: str) -> List[ValidationError]:
        """Oracle-specific syntax validation."""
        errors = []
        sql_upper = sql.upper()

        # Check for LIMIT (Oracle uses ROWNUM or FETCH)
        if "LIMIT" in sql_upper:
            errors.append(ValidationError(
                code="ORA_SYN_LIMIT",
                message="Oracle does not support LIMIT clause",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.SYNTAX_ERROR,
                suggestion="Use ROWNUM or FETCH FIRST n ROWS ONLY"
            ))

        return errors

    def _check_sqlserver_syntax(self, sql: str) -> List[ValidationError]:
        """SQL Server-specific syntax validation."""
        errors = []
        sql_upper = sql.upper()

        # Check for LIMIT (SQL Server uses TOP or OFFSET FETCH)
        if "LIMIT" in sql_upper and "TOP" not in sql_upper:
            errors.append(ValidationError(
                code="SS_SYN_LIMIT",
                message="SQL Server does not support LIMIT clause",
                severity=ValidationSeverity.ERROR,
                violation_type=ViolationType.SYNTAX_ERROR,
                suggestion="Use TOP or OFFSET...FETCH instead"
            ))

        return errors

    def _check_resource_limits(self, sql: str) -> List[ValidationWarning]:
        """Check SQL against resource limits."""
        warnings = []
        sql_upper = sql.upper()

        # Count tables
        tables = self._extract_tables(sql)
        if len(tables) > self.config.max_tables:
            warnings.append(ValidationWarning(
                code="RES_TABLES",
                message=f"Query references {len(tables)} tables (max: {self.config.max_tables})",
                severity=ValidationSeverity.WARNING,
                suggestion="Consider reducing the number of tables"
            ))

        # Count JOINs
        join_count = sql_upper.count(" JOIN ")
        if join_count > self.config.max_joins:
            warnings.append(ValidationWarning(
                code="RES_JOINS",
                message=f"Query contains {join_count} JOINs (max: {self.config.max_joins})",
                severity=ValidationSeverity.WARNING,
                suggestion="Consider simplifying the query or using CTEs"
            ))

        # Count subqueries
        subquery_count = sql_upper.count("SELECT") - 1
        if subquery_count > self.config.max_subqueries:
            warnings.append(ValidationWarning(
                code="RES_SUBQUERY",
                message=f"Query contains {subquery_count} subqueries (max: {self.config.max_subqueries})",
                severity=ValidationSeverity.WARNING,
                suggestion="Consider using CTEs or simplifying the query"
            ))

        # Check for SELECT *
        if "SELECT *" in sql_upper or "SELECT  *" in sql_upper:
            warnings.append(ValidationWarning(
                code="RES_SELECTALL",
                message="SELECT * can be inefficient for large tables",
                severity=ValidationSeverity.INFO,
                suggestion="Specify only needed columns"
            ))

        # Check for missing WHERE on UPDATE/DELETE
        if ("UPDATE" in sql_upper or "DELETE" in sql_upper) and "WHERE" not in sql_upper:
            warnings.append(ValidationWarning(
                code="RES_NOWHERE",
                message="UPDATE/DELETE without WHERE clause affects all rows",
                severity=ValidationSeverity.WARNING,
                suggestion="Add WHERE clause to limit affected rows"
            ))

        return warnings

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL (simplified)."""
        tables = set()
        sql_upper = sql.upper()

        # Match FROM and JOIN clauses
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.update(matches)

        # Remove SQL keywords that might be matched
        keywords = {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE',
                    'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AS', 'SET'}
        tables = {t for t in tables if t.upper() not in keywords}

        return list(tables)

    async def _log_validation(
        self,
        sql: str,
        sql_hash: str,
        result: bool,
        errors: List[str],
        user_id: Optional[str],
        tenant_id: Optional[str],
        database_type: Optional[str],
        correlation_id: Optional[str],
    ) -> None:
        """Log validation to audit trail."""
        log = ValidationAuditLog(
            correlation_id=correlation_id,
            sql=sql,
            sql_hash=sql_hash,
            validation_result=result,
            errors=errors,
            user_id=user_id,
            tenant_id=tenant_id,
            database_type=database_type,
        )

        async with self._lock:
            self._audit_logs.append(log)
            # Keep only last 10000 logs in memory
            if len(self._audit_logs) > 10000:
                self._audit_logs = self._audit_logs[-10000:]

        logger.info(
            f"SQL validation: valid={result}, hash={sql_hash[:8]}, "
            f"user={user_id}, tenant={tenant_id}"
        )

    async def get_audit_logs(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ValidationAuditLog]:
        """Get audit logs with optional filtering."""
        async with self._lock:
            logs = self._audit_logs.copy()

        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]

        return logs[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = len(self._audit_logs)
        valid = sum(1 for l in self._audit_logs if l.validation_result)

        return {
            "total_validations": total,
            "valid_count": valid,
            "invalid_count": total - valid,
            "success_rate": valid / total if total > 0 else 0.0,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_validator_instance: Optional[SQLValidator] = None


def get_sql_validator() -> SQLValidator:
    """Get or create the SQL validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SQLValidator()
    return _validator_instance


def set_sql_validator(validator: SQLValidator) -> None:
    """Set the SQL validator instance."""
    global _validator_instance
    _validator_instance = validator


__all__ = [
    "SQLValidator",
    "SQLValidationResult",
    "ValidationError",
    "ValidationWarning",
    "ValidationConfig",
    "ValidationAuditLog",
    "ValidationSeverity",
    "ViolationType",
    "DatabaseType",
    "TablePermission",
    "get_sql_validator",
    "set_sql_validator",
]
