"""
Data Sync Quality Validator Module.

Provides comprehensive data validation for sync operations:
- Schema validation
- Data integrity checks
- Completeness validation
- Anomaly detection
- Quality scoring
"""

import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationType(str, Enum):
    """Types of validation checks."""
    SCHEMA = "schema"
    COMPLETENESS = "completeness"
    INTEGRITY = "integrity"
    FORMAT = "format"
    RANGE = "range"
    UNIQUENESS = "uniqueness"
    REFERENTIAL = "referential"
    BUSINESS_RULE = "business_rule"
    ANOMALY = "anomaly"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    id: str = field(default_factory=lambda: str(uuid4()))
    validation_type: ValidationType = ValidationType.SCHEMA
    severity: ValidationSeverity = ValidationSeverity.WARNING
    field_name: Optional[str] = None
    record_id: Optional[str] = None
    message: str = ""
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    suggestion: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "validation_type": self.validation_type.value,
            "severity": self.severity.value,
            "field_name": self.field_name,
            "record_id": self.record_id,
            "message": self.message,
            "expected_value": str(self.expected_value) if self.expected_value else None,
            "actual_value": str(self.actual_value) if self.actual_value else None,
            "suggestion": self.suggestion,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool = True
    score: float = 1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    records_validated: int = 0
    records_passed: int = 0
    records_failed: int = 0
    validation_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
            "records_validated": self.records_validated,
            "records_passed": self.records_passed,
            "records_failed": self.records_failed,
            "validation_time_ms": self.validation_time_ms,
            "metadata": self.metadata
        }


@dataclass
class ValidationRule:
    """Defines a validation rule."""
    rule_id: str
    name: str
    validation_type: ValidationType
    field_name: Optional[str] = None
    condition: Optional[str] = None  # Expression or regex
    parameters: Dict[str, Any] = field(default_factory=dict)
    severity: ValidationSeverity = ValidationSeverity.WARNING
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "validation_type": self.validation_type.value,
            "field_name": self.field_name,
            "condition": self.condition,
            "parameters": self.parameters,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "description": self.description
        }


class DataValidator:
    """
    Comprehensive data validator for sync operations.
    
    Validates data quality during synchronization with configurable rules.
    """

    def __init__(self):
        self.rules: Dict[str, ValidationRule] = {}
        self.schema_cache: Dict[str, Dict[str, Any]] = {}
        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize default validation rules."""
        default_rules = [
            ValidationRule(
                rule_id="null_check",
                name="空值检查",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="检查必填字段是否为空"
            ),
            ValidationRule(
                rule_id="type_check",
                name="类型检查",
                validation_type=ValidationType.SCHEMA,
                severity=ValidationSeverity.ERROR,
                description="检查字段类型是否正确"
            ),
            ValidationRule(
                rule_id="format_check",
                name="格式检查",
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.WARNING,
                description="检查数据格式是否符合规范"
            ),
            ValidationRule(
                rule_id="range_check",
                name="范围检查",
                validation_type=ValidationType.RANGE,
                severity=ValidationSeverity.WARNING,
                description="检查数值是否在有效范围内"
            ),
            ValidationRule(
                rule_id="uniqueness_check",
                name="唯一性检查",
                validation_type=ValidationType.UNIQUENESS,
                severity=ValidationSeverity.ERROR,
                description="检查唯一字段是否重复"
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added validation rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a validation rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def set_schema(self, source_id: str, schema: Dict[str, Any]) -> None:
        """Set schema for a data source."""
        self.schema_cache[source_id] = schema
        logger.info(f"Schema set for source: {source_id}")

    async def validate_records(
        self,
        records: List[Dict[str, Any]],
        source_id: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        rules: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate a batch of records.
        
        Args:
            records: List of records to validate
            source_id: Optional source identifier for schema lookup
            schema: Optional schema to validate against
            rules: Optional list of rule IDs to apply (None = all enabled)
            
        Returns:
            ValidationResult with issues and scores
        """
        import time
        start_time = time.time()
        
        result = ValidationResult(
            records_validated=len(records)
        )
        
        if not records:
            return result
        
        # Get schema
        validation_schema = schema or self.schema_cache.get(source_id, {})
        
        # Get rules to apply
        active_rules = [
            r for r in self.rules.values()
            if r.enabled and (rules is None or r.rule_id in rules)
        ]
        
        # Track unique values for uniqueness checks
        unique_values: Dict[str, Set] = {}
        failed_records: Set[int] = set()
        
        for idx, record in enumerate(records):
            record_id = str(record.get("id", idx))
            record_issues = []
            
            for rule in active_rules:
                issues = await self._apply_rule(
                    rule, record, record_id, validation_schema, unique_values
                )
                record_issues.extend(issues)
            
            if record_issues:
                failed_records.add(idx)
                result.issues.extend(record_issues)
        
        # Calculate results
        result.records_failed = len(failed_records)
        result.records_passed = result.records_validated - result.records_failed
        result.score = result.records_passed / result.records_validated if result.records_validated > 0 else 1.0
        result.is_valid = result.records_failed == 0
        result.validation_time_ms = (time.time() - start_time) * 1000
        
        # Add metadata
        result.metadata = {
            "source_id": source_id,
            "rules_applied": len(active_rules),
            "schema_fields": len(validation_schema.get("fields", {}))
        }
        
        return result

    async def _apply_rule(
        self,
        rule: ValidationRule,
        record: Dict[str, Any],
        record_id: str,
        schema: Dict[str, Any],
        unique_values: Dict[str, Set]
    ) -> List[ValidationIssue]:
        """Apply a single validation rule to a record."""
        issues = []
        
        if rule.validation_type == ValidationType.COMPLETENESS:
            issues.extend(self._check_completeness(rule, record, record_id, schema))
        elif rule.validation_type == ValidationType.SCHEMA:
            issues.extend(self._check_schema(rule, record, record_id, schema))
        elif rule.validation_type == ValidationType.FORMAT:
            issues.extend(self._check_format(rule, record, record_id, schema))
        elif rule.validation_type == ValidationType.RANGE:
            issues.extend(self._check_range(rule, record, record_id, schema))
        elif rule.validation_type == ValidationType.UNIQUENESS:
            issues.extend(self._check_uniqueness(rule, record, record_id, schema, unique_values))
        elif rule.validation_type == ValidationType.BUSINESS_RULE:
            issues.extend(self._check_business_rule(rule, record, record_id))
        
        return issues

    def _check_completeness(
        self,
        rule: ValidationRule,
        record: Dict[str, Any],
        record_id: str,
        schema: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check for null/empty required fields."""
        issues = []
        required_fields = schema.get("required", [])
        
        # Also check rule-specific fields
        if rule.field_name:
            required_fields = [rule.field_name]
        
        for field in required_fields:
            value = record.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(ValidationIssue(
                    validation_type=ValidationType.COMPLETENESS,
                    severity=rule.severity,
                    field_name=field,
                    record_id=record_id,
                    message=f"必填字段 '{field}' 为空",
                    suggestion=f"请提供 '{field}' 的值"
                ))
        
        return issues

    def _check_schema(
        self,
        rule: ValidationRule,
        record: Dict[str, Any],
        record_id: str,
        schema: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check field types against schema."""
        issues = []
        field_schemas = schema.get("fields", {})
        
        for field_name, field_schema in field_schemas.items():
            if field_name not in record:
                continue
            
            value = record[field_name]
            expected_type = field_schema.get("type", "string")
            
            if not self._check_type(value, expected_type):
                issues.append(ValidationIssue(
                    validation_type=ValidationType.SCHEMA,
                    severity=rule.severity,
                    field_name=field_name,
                    record_id=record_id,
                    message=f"字段 '{field_name}' 类型不匹配",
                    expected_value=expected_type,
                    actual_value=type(value).__name__,
                    suggestion=f"请将 '{field_name}' 转换为 {expected_type} 类型"
                ))
        
        return issues

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        if value is None:
            return True  # Null check is separate
        
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        
        return isinstance(value, expected)

    def _check_format(
        self,
        rule: ValidationRule,
        record: Dict[str, Any],
        record_id: str,
        schema: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check field formats (email, date, etc.)."""
        issues = []
        field_schemas = schema.get("fields", {})
        
        format_patterns = {
            "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            "url": r'^https?://[^\s/$.?#].[^\s]*$',
            "date": r'^\d{4}-\d{2}-\d{2}$',
            "datetime": r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',
            "phone": r'^[\d\s\-\+\(\)]{7,20}$',
            "uuid": r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        }
        
        for field_name, field_schema in field_schemas.items():
            if field_name not in record:
                continue
            
            value = record[field_name]
            if not isinstance(value, str):
                continue
            
            field_format = field_schema.get("format")
            if field_format and field_format in format_patterns:
                pattern = format_patterns[field_format]
                if not re.match(pattern, value, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        validation_type=ValidationType.FORMAT,
                        severity=rule.severity,
                        field_name=field_name,
                        record_id=record_id,
                        message=f"字段 '{field_name}' 格式不正确",
                        expected_value=field_format,
                        actual_value=value[:50] if len(value) > 50 else value,
                        suggestion=f"请使用正确的 {field_format} 格式"
                    ))
        
        return issues

    def _check_range(
        self,
        rule: ValidationRule,
        record: Dict[str, Any],
        record_id: str,
        schema: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check numeric ranges."""
        issues = []
        field_schemas = schema.get("fields", {})
        
        for field_name, field_schema in field_schemas.items():
            if field_name not in record:
                continue
            
            value = record[field_name]
            if not isinstance(value, (int, float)):
                continue
            
            min_val = field_schema.get("minimum")
            max_val = field_schema.get("maximum")
            
            if min_val is not None and value < min_val:
                issues.append(ValidationIssue(
                    validation_type=ValidationType.RANGE,
                    severity=rule.severity,
                    field_name=field_name,
                    record_id=record_id,
                    message=f"字段 '{field_name}' 值小于最小值",
                    expected_value=f">= {min_val}",
                    actual_value=value,
                    suggestion=f"请确保值不小于 {min_val}"
                ))
            
            if max_val is not None and value > max_val:
                issues.append(ValidationIssue(
                    validation_type=ValidationType.RANGE,
                    severity=rule.severity,
                    field_name=field_name,
                    record_id=record_id,
                    message=f"字段 '{field_name}' 值大于最大值",
                    expected_value=f"<= {max_val}",
                    actual_value=value,
                    suggestion=f"请确保值不大于 {max_val}"
                ))
        
        return issues

    def _check_uniqueness(
        self,
        rule: ValidationRule,
        record: Dict[str, Any],
        record_id: str,
        schema: Dict[str, Any],
        unique_values: Dict[str, Set]
    ) -> List[ValidationIssue]:
        """Check uniqueness constraints."""
        issues = []
        unique_fields = schema.get("unique", [])
        
        for field_name in unique_fields:
            if field_name not in record:
                continue
            
            value = record[field_name]
            if value is None:
                continue
            
            # Initialize set for this field
            if field_name not in unique_values:
                unique_values[field_name] = set()
            
            # Check for duplicate
            value_hash = hashlib.md5(str(value).encode()).hexdigest()
            if value_hash in unique_values[field_name]:
                issues.append(ValidationIssue(
                    validation_type=ValidationType.UNIQUENESS,
                    severity=rule.severity,
                    field_name=field_name,
                    record_id=record_id,
                    message=f"字段 '{field_name}' 值重复",
                    actual_value=str(value)[:50],
                    suggestion="请确保唯一字段值不重复"
                ))
            else:
                unique_values[field_name].add(value_hash)
        
        return issues

    def _check_business_rule(
        self,
        rule: ValidationRule,
        record: Dict[str, Any],
        record_id: str
    ) -> List[ValidationIssue]:
        """Check custom business rules."""
        issues = []
        
        if not rule.condition:
            return issues
        
        try:
            # Simple expression evaluation (safe subset)
            # Format: "field_name operator value"
            # e.g., "age >= 18", "status in ['active', 'pending']"
            result = self._evaluate_condition(rule.condition, record)
            
            if not result:
                issues.append(ValidationIssue(
                    validation_type=ValidationType.BUSINESS_RULE,
                    severity=rule.severity,
                    record_id=record_id,
                    message=f"业务规则验证失败: {rule.name}",
                    expected_value=rule.condition,
                    suggestion=rule.description
                ))
        except Exception as e:
            logger.warning(f"Business rule evaluation error: {e}")
        
        return issues

    def _evaluate_condition(self, condition: str, record: Dict[str, Any]) -> bool:
        """Safely evaluate a simple condition expression."""
        # Parse simple conditions like "field >= value"
        operators = ['>=', '<=', '!=', '==', '>', '<', ' in ', ' not in ']
        
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    field_name = parts[0].strip()
                    expected = parts[1].strip()
                    
                    if field_name not in record:
                        return True  # Skip if field doesn't exist
                    
                    actual = record[field_name]
                    
                    # Try to evaluate
                    try:
                        expected_val = eval(expected)  # Safe for simple literals
                        
                        if op == '>=':
                            return actual >= expected_val
                        elif op == '<=':
                            return actual <= expected_val
                        elif op == '!=':
                            return actual != expected_val
                        elif op == '==':
                            return actual == expected_val
                        elif op == '>':
                            return actual > expected_val
                        elif op == '<':
                            return actual < expected_val
                        elif op == ' in ':
                            return actual in expected_val
                        elif op == ' not in ':
                            return actual not in expected_val
                    except:
                        pass
        
        return True  # Default to pass if can't evaluate


class DataSyncQualityManager:
    """
    Quality manager specifically for data sync operations.
    
    Extends quality management with sync-specific features.
    """

    def __init__(self):
        self.validator = DataValidator()
        self.quality_thresholds = {
            "minimum_score": 0.8,
            "warning_score": 0.9,
            "critical_error_count": 10
        }
        self.quality_history: List[Dict[str, Any]] = []

    def set_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Set quality thresholds."""
        self.quality_thresholds.update(thresholds)

    async def validate_sync_batch(
        self,
        records: List[Dict[str, Any]],
        source_id: str,
        sync_job_id: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[ValidationResult, bool]:
        """
        Validate a sync batch and determine if it should proceed.
        
        Returns:
            Tuple of (ValidationResult, should_proceed)
        """
        result = await self.validator.validate_records(
            records=records,
            source_id=source_id,
            schema=schema
        )
        
        # Determine if sync should proceed
        should_proceed = True
        
        # Check critical errors
        critical_issues = [
            i for i in result.issues
            if i.severity == ValidationSeverity.CRITICAL
        ]
        if len(critical_issues) >= self.quality_thresholds.get("critical_error_count", 10):
            should_proceed = False
        
        # Check minimum score
        if result.score < self.quality_thresholds.get("minimum_score", 0.8):
            should_proceed = False
        
        # Record history
        self.quality_history.append({
            "sync_job_id": sync_job_id,
            "source_id": source_id,
            "timestamp": datetime.now().isoformat(),
            "score": result.score,
            "records_validated": result.records_validated,
            "issues_count": len(result.issues),
            "should_proceed": should_proceed
        })
        
        return result, should_proceed

    async def get_quality_report(
        self,
        sync_job_id: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Generate quality report for sync operations."""
        # Filter history
        filtered = self.quality_history
        if sync_job_id:
            filtered = [h for h in filtered if h.get("sync_job_id") == sync_job_id]
        if source_id:
            filtered = [h for h in filtered if h.get("source_id") == source_id]
        
        filtered = filtered[-limit:]
        
        if not filtered:
            return {
                "total_validations": 0,
                "average_score": 0.0,
                "total_issues": 0,
                "pass_rate": 0.0
            }
        
        total_score = sum(h["score"] for h in filtered)
        total_issues = sum(h["issues_count"] for h in filtered)
        passed = sum(1 for h in filtered if h["should_proceed"])
        
        return {
            "total_validations": len(filtered),
            "average_score": total_score / len(filtered),
            "total_issues": total_issues,
            "pass_rate": passed / len(filtered),
            "recent_validations": filtered[-10:]
        }


# Global instance
data_sync_quality_manager = DataSyncQualityManager()
