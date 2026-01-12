"""
Compliance Tracker for SuperInsight Platform.

Provides quality compliance tracking and monitoring:
- Compliance rule management
- Automated compliance checks
- Alert generation
- Compliance reporting
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid
import asyncio

logger = logging.getLogger(__name__)


class ComplianceCategory(str, Enum):
    """Categories of compliance checks."""
    DATA_PRIVACY = "data_privacy"
    QUALITY_STANDARDS = "quality_standards"
    PROCESS_COMPLIANCE = "process_compliance"
    SECURITY = "security"
    AUDIT = "audit"
    REGULATORY = "regulatory"


class ComplianceStatus(str, Enum):
    """Status of compliance checks."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    PENDING = "pending"


class ComplianceSeverity(str, Enum):
    """Severity levels for compliance issues."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceRule:
    """Defines a compliance rule."""
    rule_id: str
    name: str
    description: str
    category: ComplianceCategory
    severity: ComplianceSeverity
    check_type: str  # threshold, pattern, custom
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    auto_remediate: bool = False
    remediation_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "check_type": self.check_type,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "auto_remediate": self.auto_remediate,
            "remediation_action": self.remediation_action
        }


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check."""
    result_id: str
    rule_id: str
    rule_name: str
    category: ComplianceCategory
    status: ComplianceStatus
    severity: ComplianceSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.now)
    remediated: bool = False
    remediated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category.value,
            "status": self.status.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "checked_at": self.checked_at.isoformat(),
            "remediated": self.remediated,
            "remediated_at": self.remediated_at.isoformat() if self.remediated_at else None
        }


@dataclass
class ComplianceAlert:
    """Represents a compliance alert."""
    alert_id: str
    rule_id: str
    category: ComplianceCategory
    severity: ComplianceSeverity
    title: str
    message: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    status: str = "active"  # active, acknowledged, resolved
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by
        }


@dataclass
class ComplianceSnapshot:
    """Snapshot of compliance status at a point in time."""
    snapshot_id: str
    timestamp: datetime
    overall_score: float
    by_category: Dict[str, Dict[str, int]] = field(default_factory=dict)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    critical_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_score": self.overall_score,
            "by_category": self.by_category,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "critical_issues": self.critical_issues
        }


class ComplianceChecker:
    """Executes compliance checks."""

    def __init__(self):
        self.check_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default check handlers."""
        self.check_handlers["threshold"] = self._check_threshold
        self.check_handlers["pattern"] = self._check_pattern
        self.check_handlers["existence"] = self._check_existence
        self.check_handlers["range"] = self._check_range

    def register_handler(self, check_type: str, handler: Callable):
        """Register a custom check handler."""
        self.check_handlers[check_type] = handler

    async def execute_check(
        self,
        rule: ComplianceRule,
        data: Dict[str, Any]
    ) -> ComplianceCheckResult:
        """Execute a compliance check."""
        handler = self.check_handlers.get(rule.check_type)
        
        if not handler:
            return ComplianceCheckResult(
                result_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                category=rule.category,
                status=ComplianceStatus.SKIPPED,
                severity=rule.severity,
                message=f"Unknown check type: {rule.check_type}"
            )
        
        try:
            status, message, details = await handler(rule, data)
            
            return ComplianceCheckResult(
                result_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                category=rule.category,
                status=status,
                severity=rule.severity,
                message=message,
                details=details,
                entity_id=data.get("entity_id"),
                entity_type=data.get("entity_type")
            )
        except Exception as e:
            logger.error(f"Check execution failed for {rule.rule_id}: {e}")
            return ComplianceCheckResult(
                result_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                category=rule.category,
                status=ComplianceStatus.FAILED,
                severity=rule.severity,
                message=f"Check execution error: {str(e)}"
            )

    async def _check_threshold(
        self,
        rule: ComplianceRule,
        data: Dict[str, Any]
    ) -> Tuple[ComplianceStatus, str, Dict[str, Any]]:
        """Check if value meets threshold."""
        params = rule.parameters
        metric_name = params.get("metric")
        threshold = params.get("threshold", 0)
        operator = params.get("operator", "gte")  # gte, lte, gt, lt, eq
        
        value = data.get(metric_name)
        if value is None:
            return ComplianceStatus.SKIPPED, f"Metric {metric_name} not found", {}
        
        passed = False
        if operator == "gte":
            passed = value >= threshold
        elif operator == "lte":
            passed = value <= threshold
        elif operator == "gt":
            passed = value > threshold
        elif operator == "lt":
            passed = value < threshold
        elif operator == "eq":
            passed = abs(value - threshold) < 0.001
        
        status = ComplianceStatus.PASSED if passed else ComplianceStatus.FAILED
        message = f"{metric_name}: {value} {'meets' if passed else 'does not meet'} threshold {operator} {threshold}"
        
        return status, message, {"value": value, "threshold": threshold, "operator": operator}

    async def _check_pattern(
        self,
        rule: ComplianceRule,
        data: Dict[str, Any]
    ) -> Tuple[ComplianceStatus, str, Dict[str, Any]]:
        """Check if value matches pattern."""
        import re
        
        params = rule.parameters
        field_name = params.get("field")
        pattern = params.get("pattern")
        
        value = data.get(field_name, "")
        if not value:
            return ComplianceStatus.SKIPPED, f"Field {field_name} not found", {}
        
        try:
            match = re.match(pattern, str(value))
            passed = match is not None
            status = ComplianceStatus.PASSED if passed else ComplianceStatus.FAILED
            message = f"{field_name} {'matches' if passed else 'does not match'} pattern"
            return status, message, {"value": value, "pattern": pattern}
        except Exception as e:
            return ComplianceStatus.FAILED, f"Pattern check error: {e}", {}

    async def _check_existence(
        self,
        rule: ComplianceRule,
        data: Dict[str, Any]
    ) -> Tuple[ComplianceStatus, str, Dict[str, Any]]:
        """Check if required fields exist."""
        params = rule.parameters
        required_fields = params.get("required_fields", [])
        
        missing = [f for f in required_fields if f not in data or data[f] is None]
        
        if missing:
            return (
                ComplianceStatus.FAILED,
                f"Missing required fields: {', '.join(missing)}",
                {"missing_fields": missing}
            )
        
        return ComplianceStatus.PASSED, "All required fields present", {}

    async def _check_range(
        self,
        rule: ComplianceRule,
        data: Dict[str, Any]
    ) -> Tuple[ComplianceStatus, str, Dict[str, Any]]:
        """Check if value is within range."""
        params = rule.parameters
        metric_name = params.get("metric")
        min_value = params.get("min")
        max_value = params.get("max")
        
        value = data.get(metric_name)
        if value is None:
            return ComplianceStatus.SKIPPED, f"Metric {metric_name} not found", {}
        
        in_range = True
        if min_value is not None and value < min_value:
            in_range = False
        if max_value is not None and value > max_value:
            in_range = False
        
        status = ComplianceStatus.PASSED if in_range else ComplianceStatus.FAILED
        message = f"{metric_name}: {value} {'is' if in_range else 'is not'} within range [{min_value}, {max_value}]"
        
        return status, message, {"value": value, "min": min_value, "max": max_value}


class ComplianceTracker:
    """
    Compliance tracking and monitoring system.
    
    Provides:
    - Compliance rule management
    - Automated compliance checks
    - Alert generation and management
    - Compliance reporting
    """

    def __init__(self):
        self.rules: Dict[str, ComplianceRule] = {}
        self.check_results: List[ComplianceCheckResult] = []
        self.alerts: Dict[str, ComplianceAlert] = {}
        self.snapshots: List[ComplianceSnapshot] = []
        self.checker = ComplianceChecker()
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default compliance rules."""
        default_rules = [
            # Data Privacy Rules
            ComplianceRule(
                rule_id="dp_001",
                name="数据脱敏检查",
                description="确保敏感数据已脱敏处理",
                category=ComplianceCategory.DATA_PRIVACY,
                severity=ComplianceSeverity.HIGH,
                check_type="existence",
                parameters={"required_fields": ["desensitized", "pii_removed"]}
            ),
            ComplianceRule(
                rule_id="dp_002",
                name="数据保留期限",
                description="检查数据是否超过保留期限",
                category=ComplianceCategory.DATA_PRIVACY,
                severity=ComplianceSeverity.MEDIUM,
                check_type="threshold",
                parameters={"metric": "data_age_days", "threshold": 365, "operator": "lte"}
            ),
            
            # Quality Standards Rules
            ComplianceRule(
                rule_id="qs_001",
                name="标注准确率",
                description="标注准确率必须达到最低标准",
                category=ComplianceCategory.QUALITY_STANDARDS,
                severity=ComplianceSeverity.HIGH,
                check_type="threshold",
                parameters={"metric": "accuracy", "threshold": 0.85, "operator": "gte"}
            ),
            ComplianceRule(
                rule_id="qs_002",
                name="标注一致性",
                description="多标注员一致性必须达到标准",
                category=ComplianceCategory.QUALITY_STANDARDS,
                severity=ComplianceSeverity.MEDIUM,
                check_type="threshold",
                parameters={"metric": "agreement_rate", "threshold": 0.75, "operator": "gte"}
            ),
            ComplianceRule(
                rule_id="qs_003",
                name="质量评分范围",
                description="质量评分必须在有效范围内",
                category=ComplianceCategory.QUALITY_STANDARDS,
                severity=ComplianceSeverity.LOW,
                check_type="range",
                parameters={"metric": "quality_score", "min": 0, "max": 1}
            ),
            
            # Process Compliance Rules
            ComplianceRule(
                rule_id="pc_001",
                name="审核流程完整性",
                description="确保所有标注都经过审核",
                category=ComplianceCategory.PROCESS_COMPLIANCE,
                severity=ComplianceSeverity.HIGH,
                check_type="threshold",
                parameters={"metric": "review_rate", "threshold": 1.0, "operator": "gte"}
            ),
            ComplianceRule(
                rule_id="pc_002",
                name="SLA合规",
                description="任务完成时间符合SLA要求",
                category=ComplianceCategory.PROCESS_COMPLIANCE,
                severity=ComplianceSeverity.MEDIUM,
                check_type="threshold",
                parameters={"metric": "sla_compliance_rate", "threshold": 0.95, "operator": "gte"}
            ),
            
            # Security Rules
            ComplianceRule(
                rule_id="sec_001",
                name="访问控制检查",
                description="确保访问控制正确配置",
                category=ComplianceCategory.SECURITY,
                severity=ComplianceSeverity.CRITICAL,
                check_type="existence",
                parameters={"required_fields": ["access_control", "permissions"]}
            ),
            
            # Audit Rules
            ComplianceRule(
                rule_id="aud_001",
                name="审计日志完整性",
                description="确保审计日志完整记录",
                category=ComplianceCategory.AUDIT,
                severity=ComplianceSeverity.HIGH,
                check_type="threshold",
                parameters={"metric": "audit_coverage", "threshold": 1.0, "operator": "gte"}
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule

    def add_rule(self, rule: ComplianceRule):
        """Add a compliance rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added compliance rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a compliance rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a compliance rule."""
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a compliance rule."""
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    async def run_compliance_check(
        self,
        data: Dict[str, Any],
        categories: Optional[List[ComplianceCategory]] = None,
        rule_ids: Optional[List[str]] = None
    ) -> List[ComplianceCheckResult]:
        """
        Run compliance checks on provided data.
        
        Args:
            data: Data to check
            categories: Filter by categories
            rule_ids: Filter by specific rule IDs
            
        Returns:
            List of check results
        """
        results = []
        
        for rule in self.rules.values():
            # Skip disabled rules
            if not rule.enabled:
                continue
            
            # Filter by category
            if categories and rule.category not in categories:
                continue
            
            # Filter by rule ID
            if rule_ids and rule.rule_id not in rule_ids:
                continue
            
            # Execute check
            result = await self.checker.execute_check(rule, data)
            results.append(result)
            self.check_results.append(result)
            
            # Generate alert for failures
            if result.status == ComplianceStatus.FAILED:
                await self._generate_alert(result)
            
            # Auto-remediate if configured
            if result.status == ComplianceStatus.FAILED and rule.auto_remediate:
                await self._auto_remediate(rule, result)
        
        # Trim history
        if len(self.check_results) > 10000:
            self.check_results = self.check_results[-10000:]
        
        return results

    async def _generate_alert(self, result: ComplianceCheckResult):
        """Generate alert for compliance failure."""
        alert = ComplianceAlert(
            alert_id=str(uuid.uuid4()),
            rule_id=result.rule_id,
            category=result.category,
            severity=result.severity,
            title=f"合规检查失败: {result.rule_name}",
            message=result.message,
            entity_id=result.entity_id,
            entity_type=result.entity_type
        )
        
        self.alerts[alert.alert_id] = alert
        logger.warning(f"Compliance alert generated: {alert.title}")
        
        # TODO: Integrate with notification system

    async def _auto_remediate(
        self,
        rule: ComplianceRule,
        result: ComplianceCheckResult
    ):
        """Auto-remediate compliance failure."""
        if not rule.remediation_action:
            return
        
        logger.info(f"Auto-remediating {rule.rule_id}: {rule.remediation_action}")
        
        # TODO: Integrate with remediation system
        result.remediated = True
        result.remediated_at = datetime.now()

    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> bool:
        """Acknowledge a compliance alert."""
        alert = self.alerts.get(alert_id)
        if not alert or alert.status != "active":
            return False
        
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = acknowledged_by
        
        return True

    def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str
    ) -> bool:
        """Resolve a compliance alert."""
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = "resolved"
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by
        
        return True

    def create_snapshot(self) -> ComplianceSnapshot:
        """Create a compliance status snapshot."""
        # Get recent results (last 24 hours)
        cutoff = datetime.now() - timedelta(hours=24)
        recent_results = [r for r in self.check_results if r.checked_at >= cutoff]
        
        # Calculate statistics
        by_category: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        passed = 0
        failed = 0
        warning = 0
        critical_issues = []
        
        for result in recent_results:
            by_category[result.category.value][result.status.value] += 1
            
            if result.status == ComplianceStatus.PASSED:
                passed += 1
            elif result.status == ComplianceStatus.FAILED:
                failed += 1
                if result.severity in [ComplianceSeverity.CRITICAL, ComplianceSeverity.HIGH]:
                    critical_issues.append(result.result_id)
            elif result.status == ComplianceStatus.WARNING:
                warning += 1
        
        total = passed + failed + warning
        score = passed / total if total > 0 else 1.0
        
        snapshot = ComplianceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            overall_score=score,
            by_category={k: dict(v) for k, v in by_category.items()},
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            warning_checks=warning,
            critical_issues=critical_issues
        )
        
        self.snapshots.append(snapshot)
        
        # Trim snapshots
        if len(self.snapshots) > 1000:
            self.snapshots = self.snapshots[-1000:]
        
        return snapshot

    def get_compliance_score(
        self,
        category: Optional[ComplianceCategory] = None,
        period_hours: int = 24
    ) -> float:
        """Get compliance score for a period."""
        cutoff = datetime.now() - timedelta(hours=period_hours)
        results = [r for r in self.check_results if r.checked_at >= cutoff]
        
        if category:
            results = [r for r in results if r.category == category]
        
        if not results:
            return 1.0
        
        passed = sum(1 for r in results if r.status == ComplianceStatus.PASSED)
        return passed / len(results)

    def get_active_alerts(
        self,
        category: Optional[ComplianceCategory] = None,
        severity: Optional[ComplianceSeverity] = None
    ) -> List[ComplianceAlert]:
        """Get active compliance alerts."""
        alerts = [a for a in self.alerts.values() if a.status == "active"]
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def get_check_history(
        self,
        rule_id: Optional[str] = None,
        category: Optional[ComplianceCategory] = None,
        status: Optional[ComplianceStatus] = None,
        limit: int = 100
    ) -> List[ComplianceCheckResult]:
        """Get compliance check history."""
        results = self.check_results
        
        if rule_id:
            results = [r for r in results if r.rule_id == rule_id]
        if category:
            results = [r for r in results if r.category == category]
        if status:
            results = [r for r in results if r.status == status]
        
        return sorted(results, key=lambda r: r.checked_at, reverse=True)[:limit]

    def get_statistics(
        self,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """Get compliance statistics."""
        cutoff = datetime.now() - timedelta(hours=period_hours)
        results = [r for r in self.check_results if r.checked_at >= cutoff]
        
        by_category = defaultdict(lambda: {"passed": 0, "failed": 0, "warning": 0})
        by_severity = defaultdict(int)
        
        for result in results:
            if result.status == ComplianceStatus.PASSED:
                by_category[result.category.value]["passed"] += 1
            elif result.status == ComplianceStatus.FAILED:
                by_category[result.category.value]["failed"] += 1
                by_severity[result.severity.value] += 1
            elif result.status == ComplianceStatus.WARNING:
                by_category[result.category.value]["warning"] += 1
        
        total = len(results)
        passed = sum(1 for r in results if r.status == ComplianceStatus.PASSED)
        
        active_alerts = len([a for a in self.alerts.values() if a.status == "active"])
        
        return {
            "period_hours": period_hours,
            "total_checks": total,
            "passed_checks": passed,
            "compliance_score": passed / total if total > 0 else 1.0,
            "by_category": {k: dict(v) for k, v in by_category.items()},
            "failures_by_severity": dict(by_severity),
            "active_alerts": active_alerts,
            "rules_count": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "generated_at": datetime.now().isoformat()
        }

    def get_trend_data(
        self,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get compliance trend data."""
        trend = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            
            day_results = [
                r for r in self.check_results
                if start <= r.checked_at < end
            ]
            
            if day_results:
                passed = sum(1 for r in day_results if r.status == ComplianceStatus.PASSED)
                score = passed / len(day_results)
            else:
                score = None
            
            trend.append({
                "date": start.strftime("%Y-%m-%d"),
                "score": score,
                "checks": len(day_results)
            })
        
        return list(reversed(trend))


# Global instance
compliance_tracker = ComplianceTracker()
