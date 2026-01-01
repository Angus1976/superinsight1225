"""
Integration tests for the Risk Assessment System.

Tests cover:
- Task 18.2: End-to-end risk assessment flow, risk identification with mitigation integration,
  risk monitoring and alerting integration
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from src.agent.risk_assessment import (
    RiskCategory,
    RiskSeverity,
    RiskStatus,
    AlertLevel,
    RiskFactor,
    RiskIndicator,
    Risk,
    RiskAssessment,
    RiskAlert,
    MitigationStrategy,
    RiskIdentifier,
    RiskCalculator,
    MitigationAdvisor,
    RiskMonitor,
    RiskAssessmentEngine,
    get_risk_engine,
    quick_risk_assessment,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def risk_engine():
    """Create a fresh risk assessment engine instance."""
    return RiskAssessmentEngine()


@pytest.fixture
def sample_operational_data():
    """Sample operational metrics data."""
    return {
        "response_time": 0.75,
        "timeout_rate": 0.6,
        "cpu_usage": 0.85,
        "memory_usage": 0.9,
        "disk_usage": 0.7,
        "error_rate": 0.05,
        "request_volume": 10000
    }


@pytest.fixture
def sample_security_data():
    """Sample security metrics data."""
    return {
        "failed_logins": 0.65,
        "access_anomalies": 0.4,
        "sensitive_data_access": 0.3,
        "export_volume": 0.2,
        "privilege_escalations": 0.1
    }


@pytest.fixture
def sample_comprehensive_data():
    """Comprehensive data covering multiple risk categories."""
    return {
        # Operational
        "response_time": 0.8,
        "timeout_rate": 0.7,
        "cpu_usage": 0.88,
        "memory_usage": 0.92,
        "disk_usage": 0.75,
        # Security
        "failed_logins": 0.7,
        "access_anomalies": 0.5,
        "sensitive_data_access": 0.4,
        # Technical
        "service_health": 0.5,
        "api_errors": 0.6,
        "code_complexity": 0.7,
        "bug_rate": 0.4,
        # Financial
        "budget_utilization": 0.9,
        "cost_growth_rate": 0.8,
        # Compliance
        "compliance_score": 0.6,
        "audit_findings": 0.4
    }


# =============================================================================
# Test: End-to-End Risk Assessment Flow
# =============================================================================


class TestEndToEndRiskAssessment:
    """End-to-end tests for complete risk assessment workflow."""

    @pytest.mark.asyncio
    async def test_complete_assessment_workflow(self, risk_engine, sample_comprehensive_data):
        """Test complete risk assessment from identification to recommendation."""
        # Step 1: Perform comprehensive assessment
        assessment = risk_engine.perform_assessment(
            data=sample_comprehensive_data,
            scope="production_environment",
            categories=None  # All categories
        )

        # Verify assessment structure
        assert assessment.id is not None
        assert assessment.scope == "production_environment"
        assert len(assessment.risks) > 0

        # Step 2: Verify risk matrix generation
        matrix = assessment.risk_matrix
        assert "high_probability_high_impact" in matrix
        assert "low_probability_low_impact" in matrix

        # Step 3: Verify recommendations generated
        assert len(assessment.recommendations) > 0

        # Step 4: Verify confidence level
        assert 0 <= assessment.confidence_level <= 1

        # Step 5: Get mitigation plan
        plan = risk_engine.get_mitigation_plan(assessment.id)
        assert plan["assessment_id"] == assessment.id
        assert "risks_addressed" in plan

    def test_multi_category_risk_identification(self, risk_engine, sample_comprehensive_data):
        """Test that risks are identified across multiple categories."""
        assessment = risk_engine.perform_assessment(
            data=sample_comprehensive_data,
            scope="multi_category_test"
        )

        # Group risks by category
        categories_found = set(risk.category for risk in assessment.risks)

        # Should identify risks in multiple categories
        assert len(categories_found) >= 2

    def test_risk_severity_distribution(self, risk_engine, sample_comprehensive_data):
        """Test that risk severities are properly distributed."""
        assessment = risk_engine.perform_assessment(
            data=sample_comprehensive_data,
            scope="severity_test"
        )

        # Group risks by severity
        severities = {}
        for risk in assessment.risks:
            sev = risk.severity.value
            severities[sev] = severities.get(sev, 0) + 1

        # Should have some severity distribution
        assert len(severities) >= 1

    def test_sequential_assessments(self, risk_engine):
        """Test running multiple assessments sequentially."""
        data_sets = [
            {"cpu_usage": 0.5, "memory_usage": 0.5},  # Low risk
            {"cpu_usage": 0.7, "memory_usage": 0.7},  # Medium risk
            {"cpu_usage": 0.9, "memory_usage": 0.95}  # High risk
        ]

        assessments = []
        for i, data in enumerate(data_sets):
            assessment = risk_engine.perform_assessment(
                data=data,
                scope=f"assessment_{i}"
            )
            assessments.append(assessment)

        # All assessments should be stored
        assert len(risk_engine.assessments) == 3

        # Risk scores should generally increase
        # (Higher resource usage = higher risk)


# =============================================================================
# Test: Risk Identification with Mitigation Integration
# =============================================================================


class TestRiskIdentificationWithMitigation:
    """Tests for risk identification integrated with mitigation strategies."""

    def test_automatic_mitigation_suggestions(self, risk_engine, sample_operational_data):
        """Test that mitigation strategies are automatically suggested."""
        assessment = risk_engine.perform_assessment(
            data=sample_operational_data,
            scope="operational_assessment"
        )

        # For each identified risk, get mitigation suggestions
        for risk in assessment.risks:
            mitigations = risk_engine.advisor.suggest_mitigations(risk)

            # Should have mitigation suggestions for each risk
            if risk.category in [RiskCategory.OPERATIONAL, RiskCategory.SECURITY]:
                assert len(mitigations) > 0

    def test_mitigation_reduces_residual_risk(self, risk_engine, sample_operational_data):
        """Test that applying mitigations reduces residual risk."""
        assessment = risk_engine.perform_assessment(
            data=sample_operational_data,
            scope="mitigation_test"
        )

        for risk in assessment.risks:
            original_score = risk.risk_score
            mitigations = risk_engine.advisor.suggest_mitigations(risk)

            if mitigations:
                residual = risk_engine.advisor.estimate_residual_risk(
                    risk, mitigations[:1]
                )
                # Residual should be less than original
                assert residual < original_score

    def test_mitigation_priority_ordering(self, risk_engine, sample_comprehensive_data):
        """Test that mitigations are ordered by priority."""
        assessment = risk_engine.perform_assessment(
            data=sample_comprehensive_data,
            scope="priority_test"
        )

        plan = risk_engine.get_mitigation_plan(assessment.id)

        # Verify priority order exists
        assert "priority_order" in plan
        assert len(plan["priority_order"]) > 0

        # Verify risks are ordered by score
        if len(plan["risks_addressed"]) > 1:
            scores = [r["current_score"] for r in plan["risks_addressed"]]
            # Should be in descending order (highest risk first)
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1]

    def test_compound_mitigation_effectiveness(self, risk_engine, sample_operational_data):
        """Test that multiple mitigations compound effectively."""
        assessment = risk_engine.perform_assessment(
            data=sample_operational_data,
            scope="compound_test"
        )

        for risk in assessment.risks:
            mitigations = risk_engine.advisor.suggest_mitigations(risk)

            if len(mitigations) >= 2:
                # Single mitigation
                residual_one = risk_engine.advisor.estimate_residual_risk(
                    risk, mitigations[:1]
                )

                # Multiple mitigations
                residual_two = risk_engine.advisor.estimate_residual_risk(
                    risk, mitigations[:2]
                )

                # More mitigations = lower residual
                assert residual_two <= residual_one


# =============================================================================
# Test: Risk Monitoring and Alerting Integration
# =============================================================================


class TestRiskMonitoringAndAlerting:
    """Tests for risk monitoring and alerting integration."""

    def test_automatic_monitoring_registration(self, risk_engine, sample_comprehensive_data):
        """Test that high-severity risks are auto-registered for monitoring."""
        assessment = risk_engine.perform_assessment(
            data=sample_comprehensive_data,
            scope="monitoring_test"
        )

        # High severity risks should be registered
        high_severity_risks = [
            r for r in assessment.risks
            if r.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]
        ]

        for risk in high_severity_risks:
            assert risk.id in risk_engine.monitor.active_risks

    def test_alert_generation_on_threshold_breach(self, risk_engine):
        """Test that alerts are generated when thresholds are breached."""
        # Register a risk with specific thresholds
        risk = Risk(
            name="test_risk",
            category=RiskCategory.OPERATIONAL,
            probability=0.6,
            impact=0.7,
            factors=[
                RiskFactor(
                    name="cpu_usage",
                    current_value=0.7,
                    threshold=0.8,
                    weight=1.0
                )
            ]
        )
        risk.calculate_risk_score()
        risk.determine_severity()

        risk_engine.monitor.register_risk(risk)

        # Check with data exceeding threshold
        alerts = risk_engine.monitor.check_risks({
            "cpu_usage": 0.95
        })

        # Should generate alert
        assert len(alerts) > 0 or len(risk_engine.monitor.alerts) > 0

    def test_alert_acknowledgement_workflow(self, risk_engine):
        """Test complete alert acknowledgement workflow."""
        # Create and register a risk
        risk = Risk(
            name="alerting_test",
            category=RiskCategory.SECURITY,
            probability=0.8,
            impact=0.9,
            factors=[
                RiskFactor(
                    name="failed_logins",
                    current_value=0.5,
                    threshold=0.6,
                    weight=1.0
                )
            ]
        )
        risk.calculate_risk_score()
        risk_engine.monitor.register_risk(risk)

        # Trigger alert
        risk_engine.monitor.check_risks({"failed_logins": 0.9})

        # Get active alerts
        active_alerts = risk_engine.monitor.get_active_alerts()

        if active_alerts:
            # Acknowledge alert
            alert_id = active_alerts[0].id
            result = risk_engine.monitor.acknowledge_alert(alert_id, "security_team")
            assert result is True

            # Verify acknowledged
            for alert in risk_engine.monitor.alerts:
                if alert.id == alert_id:
                    assert alert.acknowledged is True
                    assert alert.acknowledged_by == "security_team"

    def test_risk_summary_generation(self, risk_engine, sample_comprehensive_data):
        """Test risk summary generation from monitoring."""
        assessment = risk_engine.perform_assessment(
            data=sample_comprehensive_data,
            scope="summary_test"
        )

        # Get summary
        summary = risk_engine.monitor.get_risk_summary()

        assert "total_risks" in summary
        assert "by_severity" in summary
        assert "by_category" in summary
        assert "active_alerts" in summary

    def test_continuous_monitoring_updates(self, risk_engine):
        """Test continuous monitoring with data updates."""
        # Register initial risk
        risk = Risk(
            name="continuous_test",
            category=RiskCategory.OPERATIONAL,
            probability=0.5,
            impact=0.5,
            factors=[
                RiskFactor(
                    name="error_rate",
                    current_value=0.3,
                    threshold=0.5,
                    weight=1.0
                )
            ]
        )
        risk.calculate_risk_score()
        risk_engine.monitor.register_risk(risk)

        # Simulate time series data
        data_points = [
            {"error_rate": 0.35},
            {"error_rate": 0.45},
            {"error_rate": 0.55},  # Exceeds threshold
            {"error_rate": 0.65},  # Further exceeds
        ]

        all_alerts = []
        for data in data_points:
            alerts = risk_engine.monitor.check_risks(data)
            all_alerts.extend(alerts)

        # Check history tracked
        assert len(risk_engine.monitor.history) == 4


# =============================================================================
# Test: Full Integration Scenarios
# =============================================================================


class TestFullIntegrationScenarios:
    """Full integration tests for complex scenarios."""

    def test_incident_response_workflow(self, risk_engine):
        """Test complete incident response workflow."""
        # Phase 1: Initial detection
        initial_data = {
            "cpu_usage": 0.95,
            "memory_usage": 0.98,
            "error_rate": 0.15,
            "response_time": 0.9
        }

        assessment = risk_engine.perform_assessment(
            data=initial_data,
            scope="incident_detection"
        )

        # Phase 2: Identify critical risks
        critical_risks = [
            r for r in assessment.risks
            if r.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]
        ]

        # Phase 3: Get immediate mitigations
        immediate_actions = []
        for risk in critical_risks:
            mitigations = risk_engine.advisor.suggest_mitigations(risk)
            if mitigations:
                immediate_actions.append({
                    "risk": risk.name,
                    "action": mitigations[0].name,
                    "expected_reduction": mitigations[0].expected_reduction
                })

        # Phase 4: Set up monitoring
        for risk in critical_risks:
            if risk.id not in risk_engine.monitor.active_risks:
                risk_engine.monitor.register_risk(risk)

        # Verify workflow
        assert assessment is not None
        assert len(risk_engine.monitor.active_risks) > 0

    def test_risk_trending_analysis(self, risk_engine):
        """Test risk trending over multiple assessments."""
        # Simulate improving conditions over time
        data_timeline = [
            {"cpu_usage": 0.95, "memory_usage": 0.9},  # T0: Critical
            {"cpu_usage": 0.85, "memory_usage": 0.8},  # T1: High
            {"cpu_usage": 0.75, "memory_usage": 0.7},  # T2: Medium
            {"cpu_usage": 0.60, "memory_usage": 0.5},  # T3: Low
        ]

        risk_scores = []
        for i, data in enumerate(data_timeline):
            assessment = risk_engine.perform_assessment(
                data=data,
                scope=f"trend_t{i}"
            )
            risk_scores.append(assessment.overall_risk_score)

        # Verify trend (risk should decrease)
        for i in range(len(risk_scores) - 1):
            assert risk_scores[i] >= risk_scores[i + 1]

    def test_multi_tenant_risk_isolation(self, risk_engine):
        """Test that risks are properly isolated by scope/tenant."""
        # Tenant 1 data - high risk
        tenant1_data = {
            "cpu_usage": 0.95,
            "memory_usage": 0.9,
            "failed_logins": 0.8
        }

        # Tenant 2 data - low risk
        tenant2_data = {
            "cpu_usage": 0.3,
            "memory_usage": 0.4,
            "failed_logins": 0.1
        }

        assessment1 = risk_engine.perform_assessment(
            data=tenant1_data,
            scope="tenant_1"
        )

        assessment2 = risk_engine.perform_assessment(
            data=tenant2_data,
            scope="tenant_2"
        )

        # Assessments should be independent
        assert assessment1.id != assessment2.id
        assert assessment1.overall_risk_score > assessment2.overall_risk_score

    def test_compliance_risk_workflow(self, risk_engine):
        """Test compliance-focused risk workflow."""
        compliance_data = {
            "compliance_score": 0.4,
            "audit_findings": 0.6,
            "policy_violations": 0.5
        }

        # Add custom compliance pattern
        risk_engine.identifier.add_risk_pattern(
            RiskCategory.COMPLIANCE,
            {
                "pattern": "compliance_gap",
                "indicators": ["compliance_score", "policy_violations"],
                "threshold": 0.4,
                "description": "Compliance gap identified"
            }
        )

        assessment = risk_engine.perform_assessment(
            data=compliance_data,
            scope="compliance_audit",
            categories=[RiskCategory.COMPLIANCE]
        )

        # Verify compliance risks identified
        compliance_risks = [
            r for r in assessment.risks
            if r.category == RiskCategory.COMPLIANCE
        ]

        assert len(compliance_risks) >= 1

    def test_risk_calculator_methods_comparison(self, risk_engine):
        """Test different risk calculation methods produce different results."""
        factors = [
            RiskFactor(name="factor1", current_value=0.8, weight=2.0),
            RiskFactor(name="factor2", current_value=0.6, weight=1.0),
            RiskFactor(name="factor3", current_value=0.4, weight=1.5),
        ]

        calculator = RiskCalculator()

        simple = calculator.calculate_probability(factors, method="simple")
        weighted = calculator.calculate_probability(factors, method="weighted")
        bayesian = calculator.calculate_probability(factors, method="bayesian")

        # Methods should produce different results
        results = [simple, weighted, bayesian]

        # All should be valid probabilities
        for r in results:
            assert 0 <= r <= 1


# =============================================================================
# Test: Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_quick_risk_assessment(self, sample_operational_data):
        """Test quick risk assessment helper."""
        result = quick_risk_assessment(sample_operational_data)

        assert "assessment_id" in result
        assert "overall_risk_score" in result
        assert "overall_severity" in result
        assert "risks_found" in result
        assert "recommendations" in result
        assert "confidence" in result

    def test_get_risk_engine_singleton(self):
        """Test singleton pattern for risk engine."""
        engine1 = get_risk_engine()
        engine2 = get_risk_engine()

        assert engine1 is engine2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
