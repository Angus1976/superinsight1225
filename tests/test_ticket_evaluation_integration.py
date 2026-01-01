"""
Integration tests for Ticket Dispatch and Evaluation System.

Tests the complete flow from ticket creation to performance evaluation,
verifying data flow and interface consistency.

Task 15.1.1: 工单派发和考核系统集成测试
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
import uuid


# =============================================================================
# Mock Data Classes (representing actual system models)
# =============================================================================


class TicketStatus:
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    CLOSED = "closed"


class TicketPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class EvaluationResult:
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    UNACCEPTABLE = "unacceptable"


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_ticket():
    """Create a sample ticket."""
    return {
        "id": str(uuid.uuid4()),
        "title": "Customer data extraction request",
        "description": "Extract sales data from Q4 reports",
        "priority": TicketPriority.HIGH,
        "status": TicketStatus.CREATED,
        "created_at": datetime.utcnow(),
        "due_date": datetime.utcnow() + timedelta(days=2),
        "assigned_to": None,
        "requester_id": "user-123",
        "tags": ["data-extraction", "priority"],
        "metadata": {"estimated_hours": 4}
    }


@pytest.fixture
def sample_agent():
    """Create a sample agent for assignment."""
    return {
        "id": "agent-001",
        "name": "Data Analyst",
        "skills": ["data-extraction", "sql", "reporting"],
        "workload": 0.6,
        "performance_score": 0.85,
        "available": True
    }


@pytest.fixture
def sample_evaluation_criteria():
    """Create sample evaluation criteria."""
    return {
        "accuracy": {"weight": 0.35, "threshold": 0.8},
        "timeliness": {"weight": 0.25, "threshold": 0.9},
        "completeness": {"weight": 0.25, "threshold": 0.85},
        "customer_satisfaction": {"weight": 0.15, "threshold": 0.8}
    }


# =============================================================================
# Ticket Lifecycle Integration Tests
# =============================================================================


class TestTicketLifecycle:
    """Test complete ticket lifecycle from creation to closure."""

    def test_ticket_creation_and_assignment(self, sample_ticket, sample_agent):
        """Test ticket creation and agent assignment flow."""
        # Step 1: Create ticket
        ticket = sample_ticket.copy()
        assert ticket["status"] == TicketStatus.CREATED
        assert ticket["assigned_to"] is None

        # Step 2: Assignment logic
        def assign_ticket(ticket, agent):
            if not agent["available"]:
                return False, "Agent not available"
            if agent["workload"] >= 1.0:
                return False, "Agent at capacity"

            ticket["assigned_to"] = agent["id"]
            ticket["status"] = TicketStatus.ASSIGNED
            ticket["assigned_at"] = datetime.utcnow()
            return True, "Assignment successful"

        success, message = assign_ticket(ticket, sample_agent)

        assert success is True
        assert ticket["status"] == TicketStatus.ASSIGNED
        assert ticket["assigned_to"] == sample_agent["id"]

    def test_ticket_progress_tracking(self, sample_ticket, sample_agent):
        """Test ticket progress through various stages."""
        ticket = sample_ticket.copy()
        ticket["assigned_to"] = sample_agent["id"]
        ticket["status"] = TicketStatus.ASSIGNED

        # Progress stages
        stages = [
            (TicketStatus.IN_PROGRESS, "Work started"),
            (TicketStatus.COMPLETED, "Work completed"),
            (TicketStatus.REVIEWED, "Quality review done"),
            (TicketStatus.CLOSED, "Ticket closed")
        ]

        history = []
        for status, note in stages:
            ticket["status"] = status
            history.append({
                "status": status,
                "timestamp": datetime.utcnow(),
                "note": note
            })

        assert ticket["status"] == TicketStatus.CLOSED
        assert len(history) == 4

    def test_ticket_with_quality_metrics(self, sample_ticket, sample_agent):
        """Test ticket completion with quality metrics."""
        ticket = sample_ticket.copy()
        ticket["assigned_to"] = sample_agent["id"]
        ticket["status"] = TicketStatus.COMPLETED

        # Quality metrics collected at completion
        quality_metrics = {
            "accuracy_score": 0.92,
            "completeness_score": 0.88,
            "timeliness_score": 1.0,  # Completed before due date
            "errors_found": 0,
            "revisions_needed": 0
        }

        ticket["quality_metrics"] = quality_metrics
        ticket["completed_at"] = datetime.utcnow()

        # Calculate overall quality
        overall_quality = (
            quality_metrics["accuracy_score"] * 0.4 +
            quality_metrics["completeness_score"] * 0.3 +
            quality_metrics["timeliness_score"] * 0.3
        )

        assert overall_quality > 0.8
        assert ticket["quality_metrics"]["errors_found"] == 0


# =============================================================================
# Agent Performance Evaluation Integration Tests
# =============================================================================


class TestAgentPerformanceEvaluation:
    """Test agent performance evaluation based on ticket completion."""

    def test_single_ticket_evaluation(self, sample_ticket, sample_agent, sample_evaluation_criteria):
        """Test evaluation of single ticket completion."""
        # Completed ticket with metrics
        ticket = sample_ticket.copy()
        ticket["status"] = TicketStatus.COMPLETED
        ticket["assigned_to"] = sample_agent["id"]
        ticket["quality_metrics"] = {
            "accuracy_score": 0.95,
            "completeness_score": 0.90,
            "timeliness_score": 1.0,
            "customer_satisfaction": 0.88
        }

        # Evaluate against criteria
        def evaluate_ticket(ticket, criteria):
            scores = ticket["quality_metrics"]
            weighted_score = 0
            details = {}

            for criterion, config in criteria.items():
                if criterion in scores:
                    score = scores[criterion]
                    weighted = score * config["weight"]
                    weighted_score += weighted
                    passed = score >= config["threshold"]
                    details[criterion] = {
                        "score": score,
                        "weighted": weighted,
                        "threshold": config["threshold"],
                        "passed": passed
                    }

            return {
                "overall_score": weighted_score,
                "details": details,
                "passed": weighted_score >= 0.8
            }

        evaluation = evaluate_ticket(ticket, sample_evaluation_criteria)

        assert evaluation["overall_score"] > 0.8
        assert evaluation["passed"] is True
        assert all(d["passed"] for d in evaluation["details"].values())

    def test_multiple_tickets_performance(self, sample_agent, sample_evaluation_criteria):
        """Test performance aggregation across multiple tickets."""
        # Simulate multiple completed tickets
        tickets = []
        for i in range(10):
            ticket = {
                "id": f"ticket-{i}",
                "assigned_to": sample_agent["id"],
                "status": TicketStatus.COMPLETED,
                "quality_metrics": {
                    "accuracy_score": 0.85 + (i * 0.01),
                    "completeness_score": 0.82 + (i * 0.015),
                    "timeliness_score": 0.9 if i % 3 != 0 else 0.75,
                    "customer_satisfaction": 0.8 + (i * 0.02)
                }
            }
            tickets.append(ticket)

        # Aggregate performance
        def calculate_agent_performance(agent_id, tickets, criteria):
            agent_tickets = [t for t in tickets if t["assigned_to"] == agent_id]
            if not agent_tickets:
                return None

            aggregated = {criterion: 0 for criterion in criteria.keys()}

            for ticket in agent_tickets:
                for criterion in criteria.keys():
                    if criterion in ticket["quality_metrics"]:
                        aggregated[criterion] += ticket["quality_metrics"][criterion]

            for criterion in aggregated:
                aggregated[criterion] /= len(agent_tickets)

            overall = sum(
                aggregated[c] * criteria[c]["weight"]
                for c in criteria if c in aggregated
            )

            return {
                "agent_id": agent_id,
                "tickets_completed": len(agent_tickets),
                "average_scores": aggregated,
                "overall_performance": overall,
                "rating": (
                    EvaluationResult.EXCELLENT if overall >= 0.9 else
                    EvaluationResult.GOOD if overall >= 0.8 else
                    EvaluationResult.ACCEPTABLE if overall >= 0.7 else
                    EvaluationResult.NEEDS_IMPROVEMENT
                )
            }

        performance = calculate_agent_performance(
            sample_agent["id"], tickets, sample_evaluation_criteria
        )

        assert performance["tickets_completed"] == 10
        assert performance["overall_performance"] > 0.7
        assert performance["rating"] in [
            EvaluationResult.EXCELLENT,
            EvaluationResult.GOOD,
            EvaluationResult.ACCEPTABLE
        ]

    def test_evaluation_trend_analysis(self, sample_agent):
        """Test trend analysis of agent performance over time."""
        # Performance data over multiple periods
        periods = [
            {"period": "week1", "score": 0.78},
            {"period": "week2", "score": 0.82},
            {"period": "week3", "score": 0.79},
            {"period": "week4", "score": 0.85},
            {"period": "week5", "score": 0.88},
        ]

        def analyze_trend(periods):
            scores = [p["score"] for p in periods]
            avg = sum(scores) / len(scores)

            # Simple trend calculation
            early_avg = sum(scores[:2]) / 2
            late_avg = sum(scores[-2:]) / 2

            if late_avg > early_avg * 1.05:
                trend = "improving"
            elif late_avg < early_avg * 0.95:
                trend = "declining"
            else:
                trend = "stable"

            return {
                "average": avg,
                "trend": trend,
                "min": min(scores),
                "max": max(scores),
                "variance": sum((s - avg) ** 2 for s in scores) / len(scores)
            }

        analysis = analyze_trend(periods)

        assert analysis["trend"] == "improving"
        assert analysis["average"] > 0.8
        assert analysis["max"] == 0.88


# =============================================================================
# Data Flow Integration Tests
# =============================================================================


class TestDataFlowIntegration:
    """Test data flow between ticket and evaluation systems."""

    def test_ticket_to_evaluation_data_transfer(self, sample_ticket, sample_agent):
        """Test data transfer from ticket system to evaluation system."""
        # Complete ticket with all required data
        ticket = sample_ticket.copy()
        ticket.update({
            "assigned_to": sample_agent["id"],
            "status": TicketStatus.COMPLETED,
            "completed_at": datetime.utcnow(),
            "actual_hours": 3.5,
            "quality_metrics": {
                "accuracy_score": 0.92,
                "completeness_score": 0.88
            }
        })

        # Transform ticket data for evaluation
        def prepare_evaluation_data(ticket, agent):
            return {
                "evaluation_id": str(uuid.uuid4()),
                "ticket_id": ticket["id"],
                "agent_id": agent["id"],
                "period": ticket["completed_at"].strftime("%Y-%m"),
                "metrics": {
                    "estimated_hours": ticket["metadata"].get("estimated_hours", 0),
                    "actual_hours": ticket.get("actual_hours", 0),
                    "efficiency": (
                        ticket["metadata"].get("estimated_hours", 0) /
                        ticket.get("actual_hours", 1)
                    ),
                    **ticket.get("quality_metrics", {})
                },
                "context": {
                    "priority": ticket["priority"],
                    "tags": ticket.get("tags", [])
                }
            }

        eval_data = prepare_evaluation_data(ticket, sample_agent)

        assert eval_data["ticket_id"] == ticket["id"]
        assert eval_data["agent_id"] == sample_agent["id"]
        assert "efficiency" in eval_data["metrics"]
        assert eval_data["metrics"]["efficiency"] > 1.0  # Completed faster than estimated

    def test_evaluation_feedback_to_ticket_system(self, sample_ticket):
        """Test feedback from evaluation affecting ticket assignment."""
        # Historical evaluation results
        agent_evaluations = {
            "agent-001": {"score": 0.92, "workload": 0.4, "specialty": ["data-extraction"]},
            "agent-002": {"score": 0.78, "workload": 0.6, "specialty": ["reporting"]},
            "agent-003": {"score": 0.85, "workload": 0.8, "specialty": ["data-extraction", "sql"]}
        }

        ticket = sample_ticket.copy()

        def smart_assignment(ticket, agent_evaluations):
            """Use evaluation data to optimize assignment."""
            best_agent = None
            best_score = 0

            for agent_id, eval_data in agent_evaluations.items():
                # Skip overloaded agents
                if eval_data["workload"] >= 0.9:
                    continue

                # Calculate assignment score
                score = eval_data["score"] * 0.5
                score += (1 - eval_data["workload"]) * 0.3

                # Bonus for matching specialty
                if any(tag in eval_data["specialty"] for tag in ticket.get("tags", [])):
                    score += 0.2

                if score > best_score:
                    best_score = score
                    best_agent = agent_id

            return best_agent, best_score

        assigned_agent, score = smart_assignment(ticket, agent_evaluations)

        # Should assign to agent-001 (high score, low workload, matching specialty)
        assert assigned_agent == "agent-001"
        assert score > 0.7


# =============================================================================
# Interface Consistency Tests
# =============================================================================


class TestInterfaceConsistency:
    """Test interface consistency between systems."""

    def test_ticket_api_contract(self, sample_ticket):
        """Test ticket API contract structure."""
        required_fields = [
            "id", "title", "description", "priority",
            "status", "created_at", "requester_id"
        ]

        for field in required_fields:
            assert field in sample_ticket, f"Missing required field: {field}"

    def test_evaluation_api_contract(self, sample_evaluation_criteria):
        """Test evaluation API contract structure."""
        for criterion, config in sample_evaluation_criteria.items():
            assert "weight" in config, f"Missing weight for {criterion}"
            assert "threshold" in config, f"Missing threshold for {criterion}"
            assert 0 <= config["weight"] <= 1
            assert 0 <= config["threshold"] <= 1

    def test_performance_report_structure(self, sample_agent):
        """Test performance report structure consistency."""
        # Expected report structure
        report_structure = {
            "agent_id": str,
            "period": str,
            "metrics": {
                "tickets_completed": int,
                "average_quality": float,
                "average_timeliness": float,
                "customer_satisfaction": float
            },
            "rating": str,
            "recommendations": list
        }

        # Simulated report
        report = {
            "agent_id": sample_agent["id"],
            "period": "2024-Q4",
            "metrics": {
                "tickets_completed": 45,
                "average_quality": 0.88,
                "average_timeliness": 0.92,
                "customer_satisfaction": 0.85
            },
            "rating": EvaluationResult.GOOD,
            "recommendations": [
                "Focus on accuracy improvement",
                "Consider advanced training"
            ]
        }

        # Validate structure
        assert type(report["agent_id"]) == str
        assert type(report["period"]) == str
        assert type(report["metrics"]["tickets_completed"]) == int
        assert type(report["metrics"]["average_quality"]) == float
        assert type(report["rating"]) == str
        assert type(report["recommendations"]) == list


# =============================================================================
# End-to-End Workflow Tests
# =============================================================================


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    def test_complete_ticket_to_evaluation_flow(
        self, sample_ticket, sample_agent, sample_evaluation_criteria
    ):
        """Test complete flow from ticket creation to evaluation."""
        # Phase 1: Ticket Creation
        ticket = sample_ticket.copy()
        assert ticket["status"] == TicketStatus.CREATED

        # Phase 2: Assignment
        ticket["assigned_to"] = sample_agent["id"]
        ticket["status"] = TicketStatus.ASSIGNED
        ticket["assigned_at"] = datetime.utcnow()

        # Phase 3: Work in Progress
        ticket["status"] = TicketStatus.IN_PROGRESS
        ticket["started_at"] = datetime.utcnow()

        # Phase 4: Completion
        ticket["status"] = TicketStatus.COMPLETED
        ticket["completed_at"] = datetime.utcnow()
        ticket["actual_hours"] = 3.5
        ticket["quality_metrics"] = {
            "accuracy_score": 0.94,
            "completeness_score": 0.91,
            "timeliness_score": 1.0,
            "customer_satisfaction": 0.89
        }

        # Phase 5: Review
        ticket["status"] = TicketStatus.REVIEWED
        ticket["reviewed_at"] = datetime.utcnow()
        ticket["reviewer_notes"] = "Excellent work, ahead of schedule"

        # Phase 6: Evaluation
        evaluation = {
            "ticket_id": ticket["id"],
            "agent_id": sample_agent["id"],
            "scores": ticket["quality_metrics"],
            "overall_score": sum(
                ticket["quality_metrics"][c] * sample_evaluation_criteria[c]["weight"]
                for c in sample_evaluation_criteria
                if c in ticket["quality_metrics"]
            ),
            "evaluated_at": datetime.utcnow()
        }

        # Phase 7: Close
        ticket["status"] = TicketStatus.CLOSED
        ticket["closed_at"] = datetime.utcnow()

        # Verify complete flow
        assert ticket["status"] == TicketStatus.CLOSED
        assert evaluation["overall_score"] > 0.9
        assert ticket["assigned_at"] < ticket["completed_at"]
        assert ticket["completed_at"] < ticket["reviewed_at"]

    def test_batch_evaluation_processing(self, sample_agent, sample_evaluation_criteria):
        """Test batch processing of multiple ticket evaluations."""
        # Generate batch of completed tickets
        tickets = []
        for i in range(25):
            ticket = {
                "id": f"batch-ticket-{i}",
                "assigned_to": sample_agent["id"],
                "status": TicketStatus.COMPLETED,
                "completed_at": datetime.utcnow() - timedelta(days=i),
                "quality_metrics": {
                    "accuracy_score": 0.8 + (i % 10) * 0.02,
                    "completeness_score": 0.75 + (i % 8) * 0.025,
                    "timeliness_score": 0.85 if i % 4 != 0 else 0.7,
                    "customer_satisfaction": 0.82 + (i % 6) * 0.03
                }
            }
            tickets.append(ticket)

        # Batch evaluation
        def batch_evaluate(tickets, criteria):
            results = []
            for ticket in tickets:
                score = sum(
                    ticket["quality_metrics"].get(c, 0) * config["weight"]
                    for c, config in criteria.items()
                )
                results.append({
                    "ticket_id": ticket["id"],
                    "score": score,
                    "passed": score >= 0.8
                })
            return results

        evaluations = batch_evaluate(tickets, sample_evaluation_criteria)

        assert len(evaluations) == 25
        passed = sum(1 for e in evaluations if e["passed"])
        assert passed > 15  # Most should pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
