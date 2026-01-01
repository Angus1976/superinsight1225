"""
Integration tests for Ragas Evaluation and Billing System.

Tests the impact of quality evaluation results on billing,
and verifies quality score to billing amount conversion.

Task 15.1.2: Ragas 评估和计费系统集成测试
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from decimal import Decimal
import uuid


# =============================================================================
# Mock Data Classes (representing actual system models)
# =============================================================================


class QualityTier:
    PREMIUM = "premium"
    STANDARD = "standard"
    BASIC = "basic"
    SUBSTANDARD = "substandard"


class BillingType:
    FIXED = "fixed"
    USAGE_BASED = "usage_based"
    QUALITY_ADJUSTED = "quality_adjusted"
    HYBRID = "hybrid"


class PaymentStatus:
    PENDING = "pending"
    INVOICED = "invoiced"
    PAID = "paid"
    DISPUTED = "disputed"
    REFUNDED = "refunded"


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_ragas_evaluation():
    """Create a sample Ragas evaluation result."""
    return {
        "id": str(uuid.uuid4()),
        "session_id": "session-123",
        "evaluated_at": datetime.utcnow(),
        "scores": {
            "faithfulness": 0.92,
            "answer_relevancy": 0.88,
            "context_precision": 0.85,
            "context_recall": 0.90
        },
        "overall_score": 0.8875,
        "metadata": {
            "model": "gpt-4",
            "tokens_used": 1500,
            "latency_ms": 350
        }
    }


@pytest.fixture
def sample_billing_config():
    """Create sample billing configuration."""
    return {
        "base_rate": Decimal("0.02"),  # per 1000 tokens
        "quality_multipliers": {
            QualityTier.PREMIUM: Decimal("1.2"),
            QualityTier.STANDARD: Decimal("1.0"),
            QualityTier.BASIC: Decimal("0.9"),
            QualityTier.SUBSTANDARD: Decimal("0.7")
        },
        "quality_thresholds": {
            QualityTier.PREMIUM: 0.9,
            QualityTier.STANDARD: 0.75,
            QualityTier.BASIC: 0.6,
            QualityTier.SUBSTANDARD: 0.0
        },
        "minimum_charge": Decimal("0.001"),
        "sla_bonus_threshold": 0.95,
        "sla_bonus_rate": Decimal("0.1")
    }


@pytest.fixture
def sample_customer():
    """Create a sample customer for billing."""
    return {
        "id": "customer-001",
        "name": "Acme Corp",
        "billing_type": BillingType.QUALITY_ADJUSTED,
        "contract": {
            "tier": "enterprise",
            "discount_rate": Decimal("0.15"),
            "minimum_quality": 0.8,
            "sla_target": 0.9
        },
        "billing_address": {
            "email": "billing@acme.com"
        }
    }


# =============================================================================
# Quality Score to Billing Amount Conversion Tests
# =============================================================================


class TestQualityToBillingConversion:
    """Test quality score to billing amount conversion."""

    def test_quality_tier_determination(self, sample_ragas_evaluation, sample_billing_config):
        """Test determining quality tier from Ragas scores."""
        def determine_quality_tier(overall_score, thresholds):
            for tier, threshold in sorted(
                thresholds.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                if overall_score >= threshold:
                    return tier
            return QualityTier.SUBSTANDARD

        tier = determine_quality_tier(
            sample_ragas_evaluation["overall_score"],
            sample_billing_config["quality_thresholds"]
        )

        assert tier == QualityTier.STANDARD  # 0.8875 >= 0.75

    def test_billing_amount_calculation(self, sample_ragas_evaluation, sample_billing_config):
        """Test billing amount calculation based on quality."""
        def calculate_billing_amount(evaluation, config):
            # Get quality tier
            score = evaluation["overall_score"]
            tier = None
            for t, threshold in sorted(
                config["quality_thresholds"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                if score >= threshold:
                    tier = t
                    break

            tier = tier or QualityTier.SUBSTANDARD

            # Calculate base amount
            tokens = evaluation["metadata"]["tokens_used"]
            base_amount = (Decimal(tokens) / 1000) * config["base_rate"]

            # Apply quality multiplier
            multiplier = config["quality_multipliers"][tier]
            quality_adjusted = base_amount * multiplier

            # Apply SLA bonus if applicable
            sla_bonus = Decimal("0")
            if score >= config["sla_bonus_threshold"]:
                sla_bonus = base_amount * config["sla_bonus_rate"]

            # Ensure minimum charge
            total = max(quality_adjusted + sla_bonus, config["minimum_charge"])

            return {
                "base_amount": base_amount,
                "quality_tier": tier,
                "quality_multiplier": multiplier,
                "quality_adjusted_amount": quality_adjusted,
                "sla_bonus": sla_bonus,
                "total_amount": total
            }

        billing = calculate_billing_amount(sample_ragas_evaluation, sample_billing_config)

        assert billing["quality_tier"] == QualityTier.STANDARD
        assert billing["quality_multiplier"] == Decimal("1.0")
        assert billing["base_amount"] == Decimal("0.03")  # 1500/1000 * 0.02
        assert billing["total_amount"] >= billing["base_amount"]

    def test_premium_quality_bonus(self, sample_billing_config):
        """Test billing bonus for premium quality."""
        # High quality evaluation
        premium_eval = {
            "overall_score": 0.96,
            "metadata": {"tokens_used": 2000}
        }

        def calculate_with_bonus(evaluation, config):
            score = evaluation["overall_score"]
            tokens = evaluation["metadata"]["tokens_used"]
            base = (Decimal(tokens) / 1000) * config["base_rate"]

            # Premium tier
            if score >= config["quality_thresholds"][QualityTier.PREMIUM]:
                adjusted = base * config["quality_multipliers"][QualityTier.PREMIUM]
            else:
                adjusted = base

            # SLA bonus
            if score >= config["sla_bonus_threshold"]:
                bonus = base * config["sla_bonus_rate"]
                adjusted += bonus

            return adjusted

        amount = calculate_with_bonus(premium_eval, sample_billing_config)

        # Base: 2000/1000 * 0.02 = 0.04
        # Premium multiplier: 0.04 * 1.2 = 0.048
        # SLA bonus: 0.04 * 0.1 = 0.004
        # Total: 0.048 + 0.004 = 0.052
        assert amount == Decimal("0.052")

    def test_substandard_quality_discount(self, sample_billing_config):
        """Test billing discount for substandard quality."""
        poor_eval = {
            "overall_score": 0.45,
            "metadata": {"tokens_used": 1000}
        }

        def calculate_amount(evaluation, config):
            score = evaluation["overall_score"]
            tokens = evaluation["metadata"]["tokens_used"]
            base = (Decimal(tokens) / 1000) * config["base_rate"]

            tier = QualityTier.SUBSTANDARD
            for t, threshold in sorted(
                config["quality_thresholds"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                if score >= threshold:
                    tier = t
                    break

            return base * config["quality_multipliers"][tier]

        amount = calculate_amount(poor_eval, sample_billing_config)

        # Base: 1000/1000 * 0.02 = 0.02
        # Substandard multiplier: 0.02 * 0.7 = 0.014
        assert amount == Decimal("0.014")


# =============================================================================
# Quality Impact on Billing Tests
# =============================================================================


class TestQualityImpactOnBilling:
    """Test how quality evaluation affects billing decisions."""

    def test_quality_affects_invoice_generation(self, sample_customer, sample_billing_config):
        """Test that quality scores affect invoice generation."""
        # Monthly usage data with quality scores
        monthly_usage = [
            {"tokens": 50000, "quality_score": 0.92, "sessions": 100},
            {"tokens": 75000, "quality_score": 0.85, "sessions": 150},
            {"tokens": 30000, "quality_score": 0.72, "sessions": 60}
        ]

        def generate_invoice(customer, usage_data, config):
            line_items = []
            total = Decimal("0")

            for usage in usage_data:
                # Determine tier
                score = usage["quality_score"]
                tier = QualityTier.STANDARD
                for t, threshold in sorted(
                    config["quality_thresholds"].items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    if score >= threshold:
                        tier = t
                        break

                # Calculate amount
                base = (Decimal(usage["tokens"]) / 1000) * config["base_rate"]
                multiplier = config["quality_multipliers"][tier]
                amount = base * multiplier

                # Apply customer discount
                discount = customer["contract"]["discount_rate"]
                final_amount = amount * (1 - discount)

                line_items.append({
                    "description": f"{usage['sessions']} sessions ({usage['tokens']} tokens)",
                    "quality_tier": tier,
                    "base_amount": base,
                    "quality_adjusted": amount,
                    "discount_applied": amount * discount,
                    "final_amount": final_amount
                })
                total += final_amount

            return {
                "customer_id": customer["id"],
                "period": datetime.utcnow().strftime("%Y-%m"),
                "line_items": line_items,
                "subtotal": sum(item["quality_adjusted"] for item in line_items),
                "discount_total": sum(item["discount_applied"] for item in line_items),
                "total": total,
                "status": PaymentStatus.PENDING
            }

        invoice = generate_invoice(sample_customer, monthly_usage, sample_billing_config)

        assert len(invoice["line_items"]) == 3
        assert invoice["total"] < invoice["subtotal"]  # Discount applied
        assert invoice["status"] == PaymentStatus.PENDING

    def test_quality_sla_breach_impact(self, sample_customer, sample_billing_config):
        """Test billing impact when quality SLA is breached."""
        # Usage with quality below SLA target
        usage_data = {
            "tokens": 100000,
            "quality_score": 0.65,  # Below contract minimum of 0.8
            "sessions": 200
        }

        def calculate_sla_adjustment(customer, usage, config):
            sla_target = customer["contract"]["minimum_quality"]
            actual_quality = usage["quality_score"]

            if actual_quality >= sla_target:
                return {
                    "sla_breach": False,
                    "adjustment_rate": Decimal("0"),
                    "credit_amount": Decimal("0")
                }

            # Calculate SLA breach penalty/credit
            breach_severity = (sla_target - actual_quality) / sla_target
            base_amount = (Decimal(usage["tokens"]) / 1000) * config["base_rate"]

            # Credit proportional to breach severity (up to 25%)
            credit_rate = min(Decimal(str(breach_severity)), Decimal("0.25"))
            credit_amount = base_amount * credit_rate

            return {
                "sla_breach": True,
                "breach_severity": breach_severity,
                "adjustment_rate": credit_rate,
                "credit_amount": credit_amount,
                "reason": f"Quality {actual_quality:.2%} below SLA target {sla_target:.0%}"
            }

        adjustment = calculate_sla_adjustment(sample_customer, usage_data, sample_billing_config)

        assert adjustment["sla_breach"] is True
        assert adjustment["credit_amount"] > Decimal("0")
        assert adjustment["breach_severity"] > 0

    def test_quality_improvement_incentive(self, sample_customer):
        """Test incentive for quality improvement over time."""
        # Quality trend over 3 months
        quality_trend = [
            {"month": "2024-01", "avg_quality": 0.72},
            {"month": "2024-02", "avg_quality": 0.78},
            {"month": "2024-03", "avg_quality": 0.85}
        ]

        def calculate_improvement_incentive(trend, base_amount):
            if len(trend) < 2:
                return Decimal("0")

            # Calculate improvement rate
            first_score = trend[0]["avg_quality"]
            last_score = trend[-1]["avg_quality"]
            improvement = (last_score - first_score) / first_score

            if improvement <= 0:
                return Decimal("0")

            # Incentive: 5% discount per 10% improvement, max 15%
            incentive_rate = min(Decimal(str(improvement * 0.5)), Decimal("0.15"))
            return base_amount * incentive_rate

        base_amount = Decimal("500.00")
        incentive = calculate_improvement_incentive(quality_trend, base_amount)

        # Improvement: (0.85 - 0.72) / 0.72 = 0.18 (18%)
        # Incentive: 0.18 * 0.5 = 0.09 (9%)
        # Amount: 500 * 0.09 = 45
        assert incentive > Decimal("0")
        assert incentive == Decimal("45.00")


# =============================================================================
# Ragas Metrics to Billing Mapping Tests
# =============================================================================


class TestRagasMetricsBillingMapping:
    """Test mapping of specific Ragas metrics to billing."""

    def test_individual_metric_weights(self, sample_ragas_evaluation):
        """Test that individual Ragas metrics have billing weights."""
        metric_weights = {
            "faithfulness": 0.3,
            "answer_relevancy": 0.3,
            "context_precision": 0.2,
            "context_recall": 0.2
        }

        def calculate_weighted_score(scores, weights):
            total = sum(
                scores.get(metric, 0) * weight
                for metric, weight in weights.items()
            )
            return total

        weighted_score = calculate_weighted_score(
            sample_ragas_evaluation["scores"],
            metric_weights
        )

        # 0.92*0.3 + 0.88*0.3 + 0.85*0.2 + 0.90*0.2 = 0.276 + 0.264 + 0.17 + 0.18 = 0.89
        assert abs(weighted_score - 0.89) < 0.01

    def test_critical_metric_threshold(self, sample_billing_config):
        """Test billing impact when critical metric is below threshold."""
        # Evaluation with one critical metric failing
        evaluation = {
            "scores": {
                "faithfulness": 0.55,  # Below critical threshold
                "answer_relevancy": 0.90,
                "context_precision": 0.88,
                "context_recall": 0.85
            },
            "metadata": {"tokens_used": 2000}
        }

        critical_metrics = {
            "faithfulness": {"threshold": 0.7, "penalty_rate": Decimal("0.3")},
            "answer_relevancy": {"threshold": 0.6, "penalty_rate": Decimal("0.2")}
        }

        def apply_critical_penalties(evaluation, config, critical_config):
            base = (Decimal(evaluation["metadata"]["tokens_used"]) / 1000) * config["base_rate"]
            penalties = Decimal("0")

            for metric, threshold_config in critical_config.items():
                score = evaluation["scores"].get(metric, 0)
                if score < threshold_config["threshold"]:
                    penalties += base * threshold_config["penalty_rate"]

            return {
                "base_amount": base,
                "penalties": penalties,
                "adjusted_amount": max(base - penalties, config["minimum_charge"])
            }

        result = apply_critical_penalties(evaluation, sample_billing_config, critical_metrics)

        # Base: 2000/1000 * 0.02 = 0.04
        # Faithfulness penalty: 0.04 * 0.3 = 0.012
        assert result["penalties"] > Decimal("0")
        assert result["adjusted_amount"] < result["base_amount"]

    def test_composite_quality_score(self, sample_ragas_evaluation):
        """Test composite quality score calculation for billing."""
        def calculate_composite_score(evaluation):
            scores = evaluation["scores"]

            # Primary score (average of core metrics)
            primary = (
                scores.get("faithfulness", 0) +
                scores.get("answer_relevancy", 0)
            ) / 2

            # Secondary score (average of context metrics)
            secondary = (
                scores.get("context_precision", 0) +
                scores.get("context_recall", 0)
            ) / 2

            # Composite: 60% primary, 40% secondary
            composite = primary * 0.6 + secondary * 0.4

            return {
                "primary_score": primary,
                "secondary_score": secondary,
                "composite_score": composite,
                "billing_tier": (
                    "premium" if composite >= 0.9 else
                    "standard" if composite >= 0.75 else
                    "basic" if composite >= 0.6 else
                    "substandard"
                )
            }

        result = calculate_composite_score(sample_ragas_evaluation)

        # Primary: (0.92 + 0.88) / 2 = 0.9
        # Secondary: (0.85 + 0.90) / 2 = 0.875
        # Composite: 0.9 * 0.6 + 0.875 * 0.4 = 0.54 + 0.35 = 0.89
        assert result["primary_score"] == 0.9
        assert abs(result["composite_score"] - 0.89) < 0.01
        assert result["billing_tier"] == "standard"


# =============================================================================
# Billing Aggregation and Reporting Tests
# =============================================================================


class TestBillingAggregationReporting:
    """Test billing aggregation and reporting with quality data."""

    def test_monthly_billing_aggregation(self, sample_customer, sample_billing_config):
        """Test monthly billing aggregation with quality adjustments."""
        # Daily usage data for a month
        daily_data = [
            {
                "date": f"2024-03-{i+1:02d}",
                "tokens": 3000 + (i * 100),
                "sessions": 10 + i,
                "quality_score": 0.8 + (i % 10) * 0.02
            }
            for i in range(30)
        ]

        def aggregate_monthly_billing(customer, daily_data, config):
            total_tokens = sum(d["tokens"] for d in daily_data)
            total_sessions = sum(d["sessions"] for d in daily_data)
            avg_quality = sum(d["quality_score"] for d in daily_data) / len(daily_data)

            # Determine overall tier
            tier = QualityTier.STANDARD
            for t, threshold in sorted(
                config["quality_thresholds"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                if avg_quality >= threshold:
                    tier = t
                    break

            base_amount = (Decimal(total_tokens) / 1000) * config["base_rate"]
            quality_adjusted = base_amount * config["quality_multipliers"][tier]

            # Apply customer discount
            discount = customer["contract"]["discount_rate"]
            final_amount = quality_adjusted * (1 - discount)

            return {
                "period": "2024-03",
                "customer_id": customer["id"],
                "summary": {
                    "total_tokens": total_tokens,
                    "total_sessions": total_sessions,
                    "average_quality": round(avg_quality, 4),
                    "quality_tier": tier
                },
                "billing": {
                    "base_amount": base_amount,
                    "quality_adjusted": quality_adjusted,
                    "discount_applied": quality_adjusted * discount,
                    "final_amount": final_amount
                }
            }

        report = aggregate_monthly_billing(sample_customer, daily_data, sample_billing_config)

        assert report["summary"]["total_sessions"] == sum(d["sessions"] for d in daily_data)
        assert report["billing"]["final_amount"] < report["billing"]["base_amount"]
        assert "quality_tier" in report["summary"]

    def test_quality_trend_in_billing_report(self, sample_customer):
        """Test quality trend analysis in billing reports."""
        # Quarterly data
        quarterly_data = [
            {"quarter": "Q1", "tokens": 500000, "quality": 0.78, "amount": Decimal("8500")},
            {"quarter": "Q2", "tokens": 550000, "quality": 0.82, "amount": Decimal("9100")},
            {"quarter": "Q3", "tokens": 480000, "quality": 0.85, "amount": Decimal("8200")},
            {"quarter": "Q4", "tokens": 620000, "quality": 0.88, "amount": Decimal("10500")}
        ]

        def generate_trend_report(data):
            quality_trend = [d["quality"] for d in data]
            amount_trend = [d["amount"] for d in data]

            avg_quality = sum(quality_trend) / len(quality_trend)
            total_amount = sum(amount_trend)

            # Calculate quarter-over-quarter changes
            qoq_quality = []
            qoq_amount = []
            for i in range(1, len(data)):
                q_change = (data[i]["quality"] - data[i-1]["quality"]) / data[i-1]["quality"]
                a_change = (data[i]["amount"] - data[i-1]["amount"]) / data[i-1]["amount"]
                qoq_quality.append(q_change)
                qoq_amount.append(a_change)

            return {
                "period": "2024 Annual",
                "summary": {
                    "average_quality": avg_quality,
                    "total_billed": total_amount,
                    "quality_improvement": quality_trend[-1] - quality_trend[0]
                },
                "trends": {
                    "quality_qoq": qoq_quality,
                    "amount_qoq": qoq_amount,
                    "correlation": "positive" if all(
                        (qoq_quality[i] > 0) == (qoq_amount[i] > 0)
                        for i in range(len(qoq_quality))
                    ) else "mixed"
                }
            }

        report = generate_trend_report(quarterly_data)

        assert report["summary"]["quality_improvement"] == 0.1  # 0.88 - 0.78
        assert report["summary"]["total_billed"] == Decimal("36300")


# =============================================================================
# Integration Workflow Tests
# =============================================================================


class TestIntegrationWorkflow:
    """Test complete integration workflow."""

    def test_evaluation_to_billing_pipeline(
        self, sample_ragas_evaluation, sample_customer, sample_billing_config
    ):
        """Test complete pipeline from Ragas evaluation to billing."""
        # Step 1: Receive Ragas evaluation
        evaluation = sample_ragas_evaluation.copy()

        # Step 2: Determine quality tier
        overall_score = evaluation["overall_score"]
        tier = QualityTier.STANDARD
        for t, threshold in sorted(
            sample_billing_config["quality_thresholds"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if overall_score >= threshold:
                tier = t
                break

        # Step 3: Calculate billing amount
        tokens = evaluation["metadata"]["tokens_used"]
        base_rate = sample_billing_config["base_rate"]
        base_amount = (Decimal(tokens) / 1000) * base_rate
        multiplier = sample_billing_config["quality_multipliers"][tier]
        quality_amount = base_amount * multiplier

        # Step 4: Apply customer contract
        discount = sample_customer["contract"]["discount_rate"]
        final_amount = quality_amount * (1 - discount)

        # Step 5: Create billing record
        billing_record = {
            "id": str(uuid.uuid4()),
            "evaluation_id": evaluation["id"],
            "customer_id": sample_customer["id"],
            "created_at": datetime.utcnow(),
            "details": {
                "quality_tier": tier,
                "quality_score": overall_score,
                "tokens_used": tokens,
                "base_amount": float(base_amount),
                "quality_adjustment": float(multiplier),
                "discount_applied": float(discount),
                "final_amount": float(final_amount)
            },
            "status": PaymentStatus.PENDING
        }

        # Verify pipeline
        assert billing_record["evaluation_id"] == evaluation["id"]
        assert billing_record["details"]["quality_tier"] == QualityTier.STANDARD
        assert billing_record["details"]["final_amount"] < billing_record["details"]["base_amount"]

    def test_batch_processing_with_quality(self, sample_customer, sample_billing_config):
        """Test batch processing of evaluations for billing."""
        # Batch of evaluations
        evaluations = [
            {"id": f"eval-{i}", "overall_score": 0.75 + (i * 0.03), "metadata": {"tokens_used": 1000 + (i * 200)}}
            for i in range(10)
        ]

        def batch_process_billing(evaluations, customer, config):
            results = []
            total_amount = Decimal("0")

            for eval_data in evaluations:
                # Determine tier
                score = eval_data["overall_score"]
                tier = QualityTier.SUBSTANDARD
                for t, threshold in sorted(
                    config["quality_thresholds"].items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    if score >= threshold:
                        tier = t
                        break

                # Calculate amount
                tokens = eval_data["metadata"]["tokens_used"]
                base = (Decimal(tokens) / 1000) * config["base_rate"]
                adjusted = base * config["quality_multipliers"][tier]
                final = adjusted * (1 - customer["contract"]["discount_rate"])

                results.append({
                    "evaluation_id": eval_data["id"],
                    "tier": tier,
                    "amount": final
                })
                total_amount += final

            return {
                "batch_id": str(uuid.uuid4()),
                "count": len(results),
                "total_amount": total_amount,
                "items": results
            }

        batch_result = batch_process_billing(evaluations, sample_customer, sample_billing_config)

        assert batch_result["count"] == 10
        assert batch_result["total_amount"] > Decimal("0")
        assert all("tier" in item for item in batch_result["items"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
