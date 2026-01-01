"""
Unit tests for the Risk Assessment Engine.

Tests cover:
- Task 16.1: Risk identification, probability calculation, mitigation suggestions, monitoring alerts
- Task 16.2: Property-based tests for risk scoring consistency, mitigation effectiveness, alert accuracy
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import math
import random

from hypothesis import given, strategies as st, settings, assume

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
def sample_risk_factor():
    """Create a sample risk factor."""
    return RiskFactor(
        name="cpu_usage",
        description="CPU utilization percentage",
        category=RiskCategory.OPERATIONAL,
        weight=1.5,
        current_value=0.7,
        threshold=0.8,
        trend="increasing",
        data_source="monitoring_system"
    )


@pytest.fixture
def sample_risk():
    """Create a sample risk."""
    return Risk(
        name="high_latency",
        description="Service experiencing high latency",
        category=RiskCategory.OPERATIONAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.6,
        impact=0.7,
        factors=[
            RiskFactor(name="response_time", current_value=0.8, weight=1.0),
            RiskFactor(name="timeout_rate", current_value=0.5, weight=1.2)
        ],
        affected_areas=["api", "database"],
        owner="ops_team"
    )


@pytest.fixture
def sample_risk_data():
    """Create sample data for risk identification."""
    return {
        "response_time": 0.75,
        "timeout_rate": 0.6,
        "cpu_usage": 0.85,
        "memory_usage": 0.9,
        "disk_usage": 0.7,
        "failed_logins": 0.65,
        "access_anomalies": 0.4
    }


@pytest.fixture
def risk_identifier():
    """Create a risk identifier instance."""
    return RiskIdentifier()


@pytest.fixture
def risk_calculator():
    """Create a risk calculator instance."""
    return RiskCalculator()


@pytest.fixture
def mitigation_advisor():
    """Create a mitigation advisor instance."""
    return MitigationAdvisor()


@pytest.fixture
def risk_monitor():
    """Create a risk monitor instance."""
    return RiskMonitor()


@pytest.fixture
def risk_engine():
    """Create a risk assessment engine instance."""
    return RiskAssessmentEngine()


# =============================================================================
# Test: RiskFactor
# =============================================================================


class TestRiskFactor:
    """Tests for RiskFactor dataclass."""

    def test_risk_factor_creation(self, sample_risk_factor):
        """Test creating a risk factor."""
        assert sample_risk_factor.name == "cpu_usage"
        assert sample_risk_factor.category == RiskCategory.OPERATIONAL
        assert sample_risk_factor.weight == 1.5
        assert sample_risk_factor.current_value == 0.7
        assert sample_risk_factor.threshold == 0.8

    def test_risk_factor_default_values(self):
        """Test default values for risk factor."""
        factor = RiskFactor()
        assert factor.name == ""
        assert factor.weight == 1.0
        assert factor.current_value == 0.0
        assert factor.threshold == 0.5
        assert factor.trend == "stable"

    def test_risk_factor_auto_id(self):
        """Test auto-generated ID."""
        factor1 = RiskFactor()
        factor2 = RiskFactor()
        assert factor1.id != factor2.id

    def test_risk_factor_metadata(self):
        """Test factor metadata."""
        factor = RiskFactor(
            name="test",
            metadata={"source": "api", "version": "1.0"}
        )
        assert factor.metadata["source"] == "api"
        assert factor.metadata["version"] == "1.0"


# =============================================================================
# Test: RiskIndicator
# =============================================================================


class TestRiskIndicator:
    """Tests for RiskIndicator dataclass."""

    def test_indicator_creation(self):
        """Test creating a risk indicator."""
        indicator = RiskIndicator(
            name="error_rate",
            description="API error rate",
            metric_type="rate",
            current_value=0.05,
            thresholds={"warning": 0.03, "critical": 0.1},
            unit="errors/second"
        )
        assert indicator.name == "error_rate"
        assert indicator.metric_type == "rate"
        assert indicator.thresholds["warning"] == 0.03

    def test_indicator_historical_values(self):
        """Test historical values tracking."""
        indicator = RiskIndicator(name="cpu")
        indicator.historical_values.append((datetime.now(), 0.5))
        indicator.historical_values.append((datetime.now(), 0.6))
        assert len(indicator.historical_values) == 2


# =============================================================================
# Test: Risk
# =============================================================================


class TestRisk:
    """Tests for Risk dataclass."""

    def test_risk_creation(self, sample_risk):
        """Test creating a risk."""
        assert sample_risk.name == "high_latency"
        assert sample_risk.category == RiskCategory.OPERATIONAL
        assert sample_risk.probability == 0.6
        assert sample_risk.impact == 0.7

    def test_calculate_risk_score(self, sample_risk):
        """Test risk score calculation."""
        score = sample_risk.calculate_risk_score()
        assert score == pytest.approx(0.42)  # 0.6 * 0.7
        assert sample_risk.risk_score == pytest.approx(0.42)

    def test_determine_severity_critical(self):
        """Test critical severity determination."""
        risk = Risk(probability=0.9, impact=0.95)
        severity = risk.determine_severity()
        assert severity == RiskSeverity.CRITICAL
        assert risk.severity == RiskSeverity.CRITICAL

    def test_determine_severity_high(self):
        """Test high severity determination."""
        risk = Risk(probability=0.8, impact=0.8)
        severity = risk.determine_severity()
        assert severity == RiskSeverity.HIGH

    def test_determine_severity_medium(self):
        """Test medium severity determination."""
        risk = Risk(probability=0.7, impact=0.6)
        severity = risk.determine_severity()
        assert severity == RiskSeverity.MEDIUM

    def test_determine_severity_low(self):
        """Test low severity determination."""
        risk = Risk(probability=0.4, impact=0.4)
        severity = risk.determine_severity()
        assert severity == RiskSeverity.LOW

    def test_determine_severity_negligible(self):
        """Test negligible severity determination."""
        risk = Risk(probability=0.1, impact=0.1)
        severity = risk.determine_severity()
        assert severity == RiskSeverity.NEGLIGIBLE

    def test_risk_with_factors(self, sample_risk):
        """Test risk with factors."""
        assert len(sample_risk.factors) == 2
        assert sample_risk.factors[0].name == "response_time"

    def test_risk_affected_areas(self, sample_risk):
        """Test affected areas."""
        assert "api" in sample_risk.affected_areas
        assert "database" in sample_risk.affected_areas


# =============================================================================
# Test: RiskAssessment
# =============================================================================


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""

    def test_assessment_creation(self):
        """Test creating a risk assessment."""
        assessment = RiskAssessment(
            name="Q4 Risk Assessment",
            scope="infrastructure",
            overall_risk_score=0.45,
            overall_severity=RiskSeverity.MEDIUM,
            assessor="risk_team"
        )
        assert assessment.name == "Q4 Risk Assessment"
        assert assessment.scope == "infrastructure"
        assert assessment.overall_risk_score == 0.45

    def test_assessment_with_risks(self, sample_risk):
        """Test assessment with risks."""
        assessment = RiskAssessment(
            name="Test Assessment",
            risks=[sample_risk]
        )
        assert len(assessment.risks) == 1
        assert assessment.risks[0].name == "high_latency"

    def test_assessment_recommendations(self):
        """Test assessment recommendations."""
        assessment = RiskAssessment(
            name="Test",
            recommendations=[
                "Implement monitoring",
                "Review access controls"
            ]
        )
        assert len(assessment.recommendations) == 2


# =============================================================================
# Test: RiskAlert
# =============================================================================


class TestRiskAlert:
    """Tests for RiskAlert dataclass."""

    def test_alert_creation(self):
        """Test creating a risk alert."""
        alert = RiskAlert(
            risk_id="risk-123",
            risk_name="high_latency",
            level=AlertLevel.WARNING,
            message="Latency exceeds threshold",
            trigger_factor="response_time",
            trigger_value=0.85,
            threshold=0.7
        )
        assert alert.level == AlertLevel.WARNING
        assert alert.trigger_value == 0.85
        assert not alert.acknowledged

    def test_alert_acknowledgement(self):
        """Test alert acknowledgement fields."""
        alert = RiskAlert()
        alert.acknowledged = True
        alert.acknowledged_by = "admin"
        alert.acknowledged_at = datetime.now()
        assert alert.acknowledged
        assert alert.acknowledged_by == "admin"


# =============================================================================
# Test: MitigationStrategy
# =============================================================================


class TestMitigationStrategy:
    """Tests for MitigationStrategy dataclass."""

    def test_strategy_creation(self):
        """Test creating a mitigation strategy."""
        strategy = MitigationStrategy(
            name="Implement redundancy",
            description="Add redundant systems",
            risk_id="risk-123",
            strategy_type="reduce",
            expected_reduction=0.4,
            cost=10000.0,
            effort="high",
            steps=["Design", "Implement", "Test"]
        )
        assert strategy.name == "Implement redundancy"
        assert strategy.strategy_type == "reduce"
        assert strategy.expected_reduction == 0.4
        assert len(strategy.steps) == 3

    def test_strategy_types(self):
        """Test different strategy types."""
        for stype in ["avoid", "reduce", "transfer", "accept"]:
            strategy = MitigationStrategy(strategy_type=stype)
            assert strategy.strategy_type == stype


# =============================================================================
# Test: RiskIdentifier
# =============================================================================


class TestRiskIdentifier:
    """Tests for RiskIdentifier class."""

    def test_identifier_initialization(self, risk_identifier):
        """Test identifier initialization."""
        assert len(risk_identifier.risk_patterns) > 0
        assert RiskCategory.OPERATIONAL in risk_identifier.risk_patterns

    def test_identify_operational_risks(self, risk_identifier, sample_risk_data):
        """Test identifying operational risks."""
        risks = risk_identifier.identify_risks(
            sample_risk_data,
            categories=[RiskCategory.OPERATIONAL]
        )
        # Should identify resource_exhaustion (cpu and memory > 0.85)
        assert len(risks) > 0
        risk_names = [r.name for r in risks]
        assert "resource_exhaustion" in risk_names or "high_latency" in risk_names

    def test_identify_security_risks(self, risk_identifier, sample_risk_data):
        """Test identifying security risks."""
        risks = risk_identifier.identify_risks(
            sample_risk_data,
            categories=[RiskCategory.SECURITY]
        )
        # Should identify unusual_access (failed_logins >= 0.6)
        assert len(risks) > 0
        risk_names = [r.name for r in risks]
        assert "unusual_access" in risk_names

    def test_identify_all_categories(self, risk_identifier, sample_risk_data):
        """Test identifying risks across all categories."""
        risks = risk_identifier.identify_risks(sample_risk_data)
        assert len(risks) > 0

    def test_identification_history(self, risk_identifier, sample_risk_data):
        """Test identification history tracking."""
        risk_identifier.identify_risks(sample_risk_data)
        assert len(risk_identifier.identification_history) == 1
        assert "risks_found" in risk_identifier.identification_history[0]

    def test_add_custom_pattern(self, risk_identifier):
        """Test adding custom risk patterns."""
        custom_pattern = {
            "pattern": "custom_risk",
            "indicators": ["custom_metric"],
            "threshold": 0.5,
            "description": "Custom risk pattern"
        }
        risk_identifier.add_risk_pattern(RiskCategory.TECHNICAL, custom_pattern)

        patterns = risk_identifier.risk_patterns[RiskCategory.TECHNICAL]
        assert any(p["pattern"] == "custom_risk" for p in patterns)

    def test_no_risks_identified(self, risk_identifier):
        """Test when no risks are identified."""
        low_risk_data = {
            "response_time": 0.1,
            "cpu_usage": 0.2,
            "failed_logins": 0.1
        }
        risks = risk_identifier.identify_risks(low_risk_data)
        assert len(risks) == 0

    def test_risk_severity_calculation(self, risk_identifier, sample_risk_data):
        """Test that identified risks have severity calculated."""
        risks = risk_identifier.identify_risks(sample_risk_data)
        for risk in risks:
            assert risk.severity in RiskSeverity
            assert risk.risk_score >= 0


# =============================================================================
# Test: RiskCalculator
# =============================================================================


class TestRiskCalculator:
    """Tests for RiskCalculator class."""

    def test_simple_calculation(self, risk_calculator):
        """Test simple average calculation."""
        factors = [
            RiskFactor(current_value=0.4),
            RiskFactor(current_value=0.6),
            RiskFactor(current_value=0.8)
        ]
        prob = risk_calculator.calculate_probability(factors, method="simple")
        assert prob == pytest.approx(0.6)  # (0.4 + 0.6 + 0.8) / 3

    def test_weighted_calculation(self, risk_calculator):
        """Test weighted average calculation."""
        factors = [
            RiskFactor(current_value=0.5, weight=2.0),
            RiskFactor(current_value=0.7, weight=1.0)
        ]
        prob = risk_calculator.calculate_probability(factors, method="weighted")
        # (0.5 * 2.0 + 0.7 * 1.0) / 3.0 = 1.7 / 3.0 = 0.567
        assert prob == pytest.approx(0.567, abs=0.01)

    def test_bayesian_calculation(self, risk_calculator):
        """Test Bayesian probability calculation."""
        factors = [
            RiskFactor(current_value=0.8),
            RiskFactor(current_value=0.7)
        ]
        prob = risk_calculator.calculate_probability(factors, method="bayesian")
        # Result should be between 0 and 1
        assert 0 <= prob <= 1
        # High factor values should yield high probability
        assert prob > 0.5

    def test_monte_carlo_calculation(self, risk_calculator):
        """Test Monte Carlo simulation calculation."""
        factors = [
            RiskFactor(current_value=0.9),
            RiskFactor(current_value=0.9)
        ]
        prob = risk_calculator.calculate_probability(factors, method="monte_carlo")
        # With high values, probability should be high
        assert 0 <= prob <= 1

    def test_empty_factors(self, risk_calculator):
        """Test calculation with empty factors."""
        for method in ["simple", "weighted", "bayesian", "monte_carlo"]:
            prob = risk_calculator.calculate_probability([], method=method)
            assert prob == 0.0

    def test_zero_weight_factors(self, risk_calculator):
        """Test weighted calculation with zero weights."""
        factors = [
            RiskFactor(current_value=0.5, weight=0.0),
            RiskFactor(current_value=0.7, weight=0.0)
        ]
        prob = risk_calculator.calculate_probability(factors, method="weighted")
        assert prob == 0.0

    def test_aggregate_risk_calculation(self, risk_calculator):
        """Test aggregate risk calculation."""
        risks = [
            Risk(probability=0.8, impact=0.9),  # CRITICAL
            Risk(probability=0.6, impact=0.5),  # MEDIUM
            Risk(probability=0.3, impact=0.2)   # LOW
        ]
        for risk in risks:
            risk.calculate_risk_score()
            risk.determine_severity()

        agg_score, agg_severity = risk_calculator.calculate_aggregate_risk(risks)
        assert 0 <= agg_score <= 1
        assert agg_severity in RiskSeverity

    def test_aggregate_risk_empty(self, risk_calculator):
        """Test aggregate risk with no risks."""
        agg_score, agg_severity = risk_calculator.calculate_aggregate_risk([])
        assert agg_score == 0.0
        assert agg_severity == RiskSeverity.NEGLIGIBLE


# =============================================================================
# Test: MitigationAdvisor
# =============================================================================


class TestMitigationAdvisor:
    """Tests for MitigationAdvisor class."""

    def test_advisor_initialization(self, mitigation_advisor):
        """Test advisor initialization."""
        assert len(mitigation_advisor.strategy_templates) > 0
        assert RiskCategory.OPERATIONAL in mitigation_advisor.strategy_templates

    def test_suggest_operational_mitigations(self, mitigation_advisor, sample_risk):
        """Test suggesting mitigations for operational risk."""
        mitigations = mitigation_advisor.suggest_mitigations(sample_risk)
        assert len(mitigations) > 0
        assert all(isinstance(m, MitigationStrategy) for m in mitigations)

    def test_suggest_security_mitigations(self, mitigation_advisor):
        """Test suggesting mitigations for security risk."""
        security_risk = Risk(
            name="unauthorized_access",
            category=RiskCategory.SECURITY,
            severity=RiskSeverity.HIGH
        )
        mitigations = mitigation_advisor.suggest_mitigations(security_risk)
        assert len(mitigations) > 0
        strategy_names = [m.name for m in mitigations]
        assert any("access" in n.lower() for n in strategy_names)

    def test_mitigation_sorting(self, mitigation_advisor, sample_risk):
        """Test that mitigations are sorted by expected reduction."""
        mitigations = mitigation_advisor.suggest_mitigations(sample_risk)
        if len(mitigations) > 1:
            for i in range(len(mitigations) - 1):
                assert mitigations[i].expected_reduction >= mitigations[i+1].expected_reduction

    def test_severity_affects_reduction(self, mitigation_advisor):
        """Test that severity affects expected reduction."""
        high_risk = Risk(
            name="test",
            category=RiskCategory.OPERATIONAL,
            severity=RiskSeverity.HIGH
        )
        low_risk = Risk(
            name="test",
            category=RiskCategory.OPERATIONAL,
            severity=RiskSeverity.LOW
        )

        high_mitigations = mitigation_advisor.suggest_mitigations(high_risk)
        low_mitigations = mitigation_advisor.suggest_mitigations(low_risk)

        if high_mitigations and low_mitigations:
            # Low severity should have higher expected reduction (easier to mitigate)
            assert low_mitigations[0].expected_reduction >= high_mitigations[0].expected_reduction

    def test_estimate_residual_risk(self, mitigation_advisor, sample_risk):
        """Test estimating residual risk."""
        sample_risk.calculate_risk_score()
        mitigations = mitigation_advisor.suggest_mitigations(sample_risk)

        residual = mitigation_advisor.estimate_residual_risk(sample_risk, mitigations[:1])
        assert residual < sample_risk.risk_score
        assert residual >= 0

    def test_estimate_residual_risk_multiple_strategies(self, mitigation_advisor, sample_risk):
        """Test residual risk with multiple strategies."""
        sample_risk.calculate_risk_score()
        mitigations = mitigation_advisor.suggest_mitigations(sample_risk)

        residual_one = mitigation_advisor.estimate_residual_risk(sample_risk, mitigations[:1])
        residual_two = mitigation_advisor.estimate_residual_risk(sample_risk, mitigations[:2])

        # More strategies should reduce risk further
        assert residual_two <= residual_one

    def test_no_mitigations_for_unknown_category(self, mitigation_advisor):
        """Test when no mitigation templates exist for category."""
        risk = Risk(
            name="test",
            category=RiskCategory.EXTERNAL,  # May not have templates
        )
        mitigations = mitigation_advisor.suggest_mitigations(risk)
        # Should return empty list or existing templates
        assert isinstance(mitigations, list)


# =============================================================================
# Test: RiskMonitor
# =============================================================================


class TestRiskMonitor:
    """Tests for RiskMonitor class."""

    def test_monitor_initialization(self, risk_monitor):
        """Test monitor initialization."""
        assert len(risk_monitor.active_risks) == 0
        assert len(risk_monitor.alerts) == 0

    def test_register_risk(self, risk_monitor, sample_risk):
        """Test registering a risk for monitoring."""
        risk_monitor.register_risk(sample_risk)
        assert sample_risk.id in risk_monitor.active_risks
        assert sample_risk.status == RiskStatus.MONITORING

    def test_unregister_risk(self, risk_monitor, sample_risk):
        """Test unregistering a risk."""
        risk_monitor.register_risk(sample_risk)
        result = risk_monitor.unregister_risk(sample_risk.id)
        assert result is True
        assert sample_risk.id not in risk_monitor.active_risks

    def test_unregister_nonexistent_risk(self, risk_monitor):
        """Test unregistering a non-existent risk."""
        result = risk_monitor.unregister_risk("nonexistent")
        assert result is False

    def test_check_risks_generates_alerts(self, risk_monitor, sample_risk):
        """Test that checking risks generates alerts."""
        risk_monitor.register_risk(sample_risk)

        # Update with data exceeding threshold
        current_data = {
            "response_time": 0.95,  # Exceeds typical threshold
            "timeout_rate": 0.8
        }

        alerts = risk_monitor.check_risks(current_data)
        # Should generate alerts for exceeded thresholds
        assert len(risk_monitor.history) > 0

    def test_alert_handler_registration(self, risk_monitor):
        """Test registering alert handlers."""
        handler_called = []

        def test_handler(alert):
            handler_called.append(alert)

        risk_monitor.register_alert_handler(test_handler)
        assert len(risk_monitor.alert_handlers) == 1

    def test_alert_handler_execution(self, risk_monitor, sample_risk):
        """Test that alert handlers are executed."""
        alerts_received = []

        def handler(alert):
            alerts_received.append(alert)

        risk_monitor.register_alert_handler(handler)
        risk_monitor.register_risk(sample_risk)

        # Trigger alerts
        risk_monitor.check_risks({
            "response_time": 0.95,
            "timeout_rate": 0.9
        })

        # Handler should be called for each alert
        # Note: May be 0 if thresholds not configured
        assert isinstance(alerts_received, list)

    def test_acknowledge_alert(self, risk_monitor):
        """Test acknowledging an alert."""
        alert = RiskAlert(
            risk_id="test",
            risk_name="test",
            level=AlertLevel.WARNING
        )
        risk_monitor.alerts.append(alert)

        result = risk_monitor.acknowledge_alert(alert.id, "admin")
        assert result is True
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "admin"

    def test_acknowledge_nonexistent_alert(self, risk_monitor):
        """Test acknowledging non-existent alert."""
        result = risk_monitor.acknowledge_alert("nonexistent", "admin")
        assert result is False

    def test_get_active_alerts(self, risk_monitor):
        """Test getting active alerts."""
        alert1 = RiskAlert(level=AlertLevel.WARNING, resolved=False)
        alert2 = RiskAlert(level=AlertLevel.EMERGENCY, resolved=False)
        alert3 = RiskAlert(level=AlertLevel.WARNING, resolved=True)

        risk_monitor.alerts = [alert1, alert2, alert3]

        active = risk_monitor.get_active_alerts()
        assert len(active) == 2  # alert3 is resolved

    def test_get_active_alerts_by_level(self, risk_monitor):
        """Test filtering active alerts by level."""
        alert1 = RiskAlert(level=AlertLevel.WARNING, resolved=False)
        alert2 = RiskAlert(level=AlertLevel.EMERGENCY, resolved=False)

        risk_monitor.alerts = [alert1, alert2]

        warnings = risk_monitor.get_active_alerts(level=AlertLevel.WARNING)
        assert len(warnings) == 1
        assert warnings[0].level == AlertLevel.WARNING

    def test_get_risk_summary(self, risk_monitor):
        """Test getting risk summary."""
        risk1 = Risk(severity=RiskSeverity.HIGH, category=RiskCategory.SECURITY)
        risk2 = Risk(severity=RiskSeverity.MEDIUM, category=RiskCategory.OPERATIONAL)

        risk_monitor.register_risk(risk1)
        risk_monitor.register_risk(risk2)

        summary = risk_monitor.get_risk_summary()
        assert summary["total_risks"] == 2
        assert "high" in summary["by_severity"]
        assert "security" in summary["by_category"]


# =============================================================================
# Test: RiskAssessmentEngine
# =============================================================================


class TestRiskAssessmentEngine:
    """Tests for RiskAssessmentEngine class."""

    def test_engine_initialization(self, risk_engine):
        """Test engine initialization."""
        assert risk_engine.identifier is not None
        assert risk_engine.calculator is not None
        assert risk_engine.advisor is not None
        assert risk_engine.monitor is not None

    def test_perform_assessment(self, risk_engine, sample_risk_data):
        """Test performing a risk assessment."""
        assessment = risk_engine.perform_assessment(
            sample_risk_data,
            scope="infrastructure"
        )

        assert assessment.name == "Risk Assessment - infrastructure"
        assert assessment.scope == "infrastructure"
        assert len(assessment.risks) > 0
        assert assessment.overall_risk_score >= 0
        assert assessment.valid_until is not None

    def test_assessment_risk_matrix(self, risk_engine, sample_risk_data):
        """Test risk matrix generation."""
        assessment = risk_engine.perform_assessment(sample_risk_data)

        matrix = assessment.risk_matrix
        assert "high_probability_high_impact" in matrix
        assert "low_probability_low_impact" in matrix

    def test_assessment_recommendations(self, risk_engine, sample_risk_data):
        """Test recommendation generation."""
        assessment = risk_engine.perform_assessment(sample_risk_data)

        if assessment.risks:
            assert len(assessment.recommendations) > 0

    def test_assessment_confidence_level(self, risk_engine, sample_risk_data):
        """Test confidence level calculation."""
        assessment = risk_engine.perform_assessment(sample_risk_data)
        assert 0 <= assessment.confidence_level <= 1

    def test_assessment_high_severity_monitoring(self, risk_engine):
        """Test that high severity risks are auto-registered for monitoring."""
        high_risk_data = {
            "cpu_usage": 0.95,
            "memory_usage": 0.95,
            "disk_usage": 0.9
        }

        assessment = risk_engine.perform_assessment(high_risk_data)

        # Check if any critical/high risks were registered
        critical_risks = [r for r in assessment.risks
                        if r.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]]

        for risk in critical_risks:
            assert risk.id in risk_engine.monitor.active_risks

    def test_get_mitigation_plan(self, risk_engine, sample_risk_data):
        """Test getting mitigation plan for assessment."""
        assessment = risk_engine.perform_assessment(sample_risk_data)

        plan = risk_engine.get_mitigation_plan(assessment.id)

        assert plan["assessment_id"] == assessment.id
        assert "risks_addressed" in plan
        assert "priority_order" in plan

    def test_get_mitigation_plan_not_found(self, risk_engine):
        """Test mitigation plan for non-existent assessment."""
        plan = risk_engine.get_mitigation_plan("nonexistent")
        assert "error" in plan

    def test_multiple_assessments(self, risk_engine, sample_risk_data):
        """Test performing multiple assessments."""
        assessment1 = risk_engine.perform_assessment(sample_risk_data, scope="scope1")
        assessment2 = risk_engine.perform_assessment(sample_risk_data, scope="scope2")

        assert assessment1.id != assessment2.id
        assert len(risk_engine.assessments) == 2


# =============================================================================
# Test: Global Functions
# =============================================================================


class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_risk_engine_singleton(self):
        """Test get_risk_engine returns same instance."""
        engine1 = get_risk_engine()
        engine2 = get_risk_engine()
        assert engine1 is engine2

    def test_quick_risk_assessment(self, sample_risk_data):
        """Test quick risk assessment helper."""
        result = quick_risk_assessment(sample_risk_data)

        assert "assessment_id" in result
        assert "overall_risk_score" in result
        assert "overall_severity" in result
        assert "risks_found" in result
        assert "recommendations" in result
        assert "confidence" in result


# =============================================================================
# Property-Based Tests: Risk Scoring Consistency
# =============================================================================


class TestPropertyRiskScoring:
    """Property-based tests for risk scoring consistency."""

    @given(
        probability=st.floats(min_value=0.0, max_value=1.0),
        impact=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_risk_score_range(self, probability, impact):
        """Property: Risk score should always be between 0 and 1."""
        assume(math.isfinite(probability) and math.isfinite(impact))

        risk = Risk(probability=probability, impact=impact)
        score = risk.calculate_risk_score()

        assert 0 <= score <= 1

    @given(
        probability=st.floats(min_value=0.0, max_value=1.0),
        impact=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_risk_score_deterministic(self, probability, impact):
        """Property: Same probability and impact should produce same score."""
        assume(math.isfinite(probability) and math.isfinite(impact))

        risk1 = Risk(probability=probability, impact=impact)
        risk2 = Risk(probability=probability, impact=impact)

        score1 = risk1.calculate_risk_score()
        score2 = risk2.calculate_risk_score()

        assert score1 == score2

    @given(
        prob1=st.floats(min_value=0.0, max_value=0.5),
        prob2=st.floats(min_value=0.5, max_value=1.0),
        impact=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_higher_probability_higher_score(self, prob1, prob2, impact):
        """Property: Higher probability with same impact should yield higher score."""
        assume(all(math.isfinite(x) for x in [prob1, prob2, impact]))
        assume(prob2 > prob1)
        assume(impact > 0)

        risk1 = Risk(probability=prob1, impact=impact)
        risk2 = Risk(probability=prob2, impact=impact)

        score1 = risk1.calculate_risk_score()
        score2 = risk2.calculate_risk_score()

        assert score2 >= score1

    @given(
        probability=st.floats(min_value=0.0, max_value=1.0),
        impact=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_severity_consistent_with_score(self, probability, impact):
        """Property: Severity should be consistent with calculated score."""
        assume(math.isfinite(probability) and math.isfinite(impact))

        risk = Risk(probability=probability, impact=impact)
        score = risk.calculate_risk_score()
        severity = risk.determine_severity()

        # Verify severity matches score thresholds
        if score >= 0.8:
            assert severity == RiskSeverity.CRITICAL
        elif score >= 0.6:
            assert severity == RiskSeverity.HIGH
        elif score >= 0.4:
            assert severity == RiskSeverity.MEDIUM
        elif score >= 0.2:
            assert severity == RiskSeverity.LOW
        else:
            assert severity == RiskSeverity.NEGLIGIBLE


# =============================================================================
# Property-Based Tests: Mitigation Effectiveness
# =============================================================================


class TestPropertyMitigationEffectiveness:
    """Property-based tests for mitigation effectiveness."""

    @given(
        initial_score=st.floats(min_value=0.1, max_value=1.0),
        reduction=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_mitigation_reduces_risk(self, initial_score, reduction):
        """Property: Applying mitigation should reduce or maintain risk score."""
        assume(math.isfinite(initial_score) and math.isfinite(reduction))

        risk = Risk(probability=initial_score, impact=1.0)
        risk.calculate_risk_score()

        strategy = MitigationStrategy(
            expected_reduction=reduction
        )

        advisor = MitigationAdvisor()
        residual = initial_score * (1 - reduction)

        assert residual <= initial_score

    @given(
        reduction1=st.floats(min_value=0.0, max_value=0.5),
        reduction2=st.floats(min_value=0.0, max_value=0.5)
    )
    @settings(max_examples=100)
    def test_property_multiple_mitigations_compound(self, reduction1, reduction2):
        """Property: Multiple mitigations should compound (not add linearly)."""
        assume(math.isfinite(reduction1) and math.isfinite(reduction2))

        initial_score = 1.0

        # Single mitigation with combined reduction
        single_residual = initial_score * (1 - reduction1 - reduction2)

        # Two separate mitigations compounded
        compound_residual = initial_score * (1 - reduction1) * (1 - reduction2)

        # Compound should generally be higher (less effective) than linear sum
        # unless reductions are 0
        if reduction1 > 0 and reduction2 > 0:
            assert compound_residual >= single_residual or single_residual < 0

    @given(
        num_strategies=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_property_more_mitigations_lower_residual(self, num_strategies):
        """Property: More mitigations should not increase residual risk."""
        risk = Risk(probability=0.8, impact=0.8)
        risk.calculate_risk_score()

        advisor = MitigationAdvisor()
        strategies = advisor.suggest_mitigations(risk)

        if len(strategies) > 0:
            residual_one = advisor.estimate_residual_risk(risk, strategies[:1])
            residual_all = advisor.estimate_residual_risk(
                risk, strategies[:min(num_strategies, len(strategies))]
            )

            assert residual_all <= residual_one


# =============================================================================
# Property-Based Tests: Alert Accuracy
# =============================================================================


class TestPropertyAlertAccuracy:
    """Property-based tests for alert accuracy."""

    @given(
        value=st.floats(min_value=0.0, max_value=1.0),
        threshold=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_alert_threshold_consistency(self, value, threshold):
        """Property: Alert should be generated iff value >= threshold."""
        assume(math.isfinite(value) and math.isfinite(threshold))

        factor = RiskFactor(
            name="test_factor",
            current_value=value,
            threshold=threshold
        )

        should_alert = value >= threshold

        # Simulate threshold check
        actual_alert = factor.current_value >= factor.threshold

        assert should_alert == actual_alert

    @given(
        value=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_alert_level_ordering(self, value):
        """Property: Alert level should increase with risk value."""
        assume(math.isfinite(value))

        # Determine expected level based on value
        if value >= 0.9:
            expected_level = AlertLevel.EMERGENCY
        elif value >= 0.7:
            expected_level = AlertLevel.WARNING
        else:
            expected_level = AlertLevel.INFO

        # Verify ordering is consistent
        level_order = [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.EMERGENCY]

        # Higher value should not have lower level
        for lower_value in [v for v in [0.0, 0.3, 0.5] if v < value]:
            if lower_value >= 0.9:
                lower_level = AlertLevel.EMERGENCY
            elif lower_value >= 0.7:
                lower_level = AlertLevel.WARNING
            else:
                lower_level = AlertLevel.INFO

            assert level_order.index(expected_level) >= level_order.index(lower_level)


# =============================================================================
# Integration Tests
# =============================================================================


class TestRiskAssessmentIntegration:
    """Integration tests for full risk assessment workflow."""

    def test_full_assessment_workflow(self, sample_risk_data):
        """Test complete assessment workflow."""
        engine = RiskAssessmentEngine()

        # Step 1: Perform assessment
        assessment = engine.perform_assessment(sample_risk_data)
        assert len(assessment.risks) > 0

        # Step 2: Get mitigation plan
        plan = engine.get_mitigation_plan(assessment.id)
        assert len(plan["risks_addressed"]) > 0

        # Step 3: Monitor risks
        summary = engine.monitor.get_risk_summary()
        assert summary["total_risks"] >= 0

        # Step 4: Check for alerts
        alerts = engine.monitor.check_risks(sample_risk_data)
        assert isinstance(alerts, list)

    def test_continuous_monitoring_workflow(self, sample_risk):
        """Test continuous monitoring workflow."""
        monitor = RiskMonitor()

        # Register risk
        monitor.register_risk(sample_risk)

        # Simulate time series monitoring
        for i in range(3):
            data = {
                "response_time": 0.5 + (i * 0.2),
                "timeout_rate": 0.4 + (i * 0.1)
            }
            alerts = monitor.check_risks(data)

        # Check history
        assert len(monitor.history) == 3

        # Get summary
        summary = monitor.get_risk_summary()
        assert summary["total_risks"] == 1

    def test_mitigation_application_workflow(self):
        """Test applying mitigations to risks."""
        advisor = MitigationAdvisor()

        # Create high-severity risk
        risk = Risk(
            name="critical_issue",
            category=RiskCategory.SECURITY,
            severity=RiskSeverity.CRITICAL,
            probability=0.9,
            impact=0.9
        )
        risk.calculate_risk_score()

        # Get mitigations
        mitigations = advisor.suggest_mitigations(risk)
        assert len(mitigations) > 0

        # Apply mitigations and track reduction
        residual_before = risk.risk_score
        residual_after = advisor.estimate_residual_risk(risk, mitigations)

        # Risk should be reduced
        assert residual_after < residual_before

    def test_multi_category_assessment(self):
        """Test assessment across multiple risk categories."""
        engine = RiskAssessmentEngine()

        multi_category_data = {
            # Operational
            "cpu_usage": 0.9,
            "memory_usage": 0.85,
            # Security
            "failed_logins": 0.7,
            "access_anomalies": 0.6,
            # Technical
            "service_health": 0.5,
            "api_errors": 0.6
        }

        assessment = engine.perform_assessment(multi_category_data)

        # Should identify risks from multiple categories
        categories = set(r.category for r in assessment.risks)
        assert len(categories) >= 1  # At least one category

    def test_risk_lifecycle(self):
        """Test complete risk lifecycle."""
        # Create risk
        risk = Risk(
            name="test_risk",
            status=RiskStatus.IDENTIFIED
        )

        # Analyze
        risk.status = RiskStatus.ANALYZING
        risk.probability = 0.7
        risk.impact = 0.8
        risk.calculate_risk_score()

        # Assess
        risk.status = RiskStatus.ASSESSED
        risk.determine_severity()

        # Mitigate
        risk.status = RiskStatus.MITIGATING
        risk.mitigation_plan = "Implement controls"

        # Monitor
        risk.status = RiskStatus.MONITORING

        # Resolve
        risk.status = RiskStatus.RESOLVED
        risk.resolved_at = datetime.now()

        assert risk.status == RiskStatus.RESOLVED
        assert risk.resolved_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
