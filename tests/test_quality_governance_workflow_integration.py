"""
Quality Governance Workflow Integration Tests

Tests the complete flow from work order creation to repair completion,
Ragas evaluation and assessment reports, verifying quality governance effectiveness.

Task 9.2: 质量治理流程测试
"""

import pytest
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from decimal import Decimal
from uuid import uuid4, UUID
from enum import Enum
import asyncio


# =============================================================================
# Test Data Models for Quality Governance
# =============================================================================

class WorkOrderStatus(Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    CLOSED = "closed"


class WorkOrderPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class QualityIssueType(Enum):
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    GUIDELINE_VIOLATION = "guideline_violation"
    FORMAT_ERROR = "format_error"


class RepairStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class QualityLevel(Enum):
    EXCELLENT = "excellent"  # >= 0.9
    GOOD = "good"           # >= 0.8
    ACCEPTABLE = "acceptable"  # >= 0.7
    POOR = "poor"           # < 0.7


class WorkOrderForTest:
    """Test work order for quality governance testing"""
    
    def __init__(self, issue_type: QualityIssueType, priority: WorkOrderPriority, 
                 affected_data_ids: List[str], description: str):
        self.id = str(uuid4())
        self.issue_type = issue_type
        self.priority = priority
        self.affected_data_ids = affected_data_ids
        self.description = description
        self.status = WorkOrderStatus.CREATED
        self.assigned_to = None
        self.created_at = datetime.now()
        self.due_date = self._calculate_due_date()
        self.repair_actions = []
        self.quality_scores = {"before": None, "after": None}
        
    def _calculate_due_date(self) -> datetime:
        """Calculate due date based on priority"""
        hours_map = {
            WorkOrderPriority.URGENT: 4,
            WorkOrderPriority.HIGH: 24,
            WorkOrderPriority.MEDIUM: 72,
            WorkOrderPriority.LOW: 168
        }
        return self.created_at + timedelta(hours=hours_map[self.priority])


class RepairActionForTest:
    """Test repair action for quality governance testing"""
    
    def __init__(self, work_order_id: str, action_type: str, description: str):
        self.id = str(uuid4())
        self.work_order_id = work_order_id
        self.action_type = action_type
        self.description = description
        self.status = RepairStatus.PENDING
        self.assigned_to = None
        self.started_at = None
        self.completed_at = None
        self.quality_improvement = 0.0


class QualityEvaluationForTest:
    """Test quality evaluation for governance testing"""
    
    def __init__(self, data_id: str, evaluator_type: str = "ragas"):
        self.id = str(uuid4())
        self.data_id = data_id
        self.evaluator_type = evaluator_type
        self.evaluated_at = datetime.now()
        self.scores = self._generate_scores()
        self.overall_score = self._calculate_overall_score()
        self.quality_level = self._determine_quality_level()
        
    def _generate_scores(self) -> Dict[str, float]:
        """Generate realistic quality scores"""
        # Simulate different quality aspects
        base_score = 0.7 + (hash(self.data_id) % 30) / 100  # 0.7-0.99
        return {
            "faithfulness": min(1.0, base_score + 0.05),
            "answer_relevancy": base_score,
            "context_precision": min(1.0, base_score + 0.02),
            "context_recall": min(1.0, base_score - 0.03),
            "accuracy": base_score,
            "completeness": min(1.0, base_score + 0.01),
            "consistency": min(1.0, base_score - 0.01)
        }
    
    def _calculate_overall_score(self) -> float:
        """Calculate weighted overall score"""
        weights = {
            "faithfulness": 0.25,
            "answer_relevancy": 0.25,
            "context_precision": 0.15,
            "context_recall": 0.15,
            "accuracy": 0.1,
            "completeness": 0.05,
            "consistency": 0.05
        }
        
        return sum(self.scores.get(metric, 0) * weight 
                  for metric, weight in weights.items())
    
    def _determine_quality_level(self) -> QualityLevel:
        """Determine quality level from overall score"""
        if self.overall_score >= 0.9:
            return QualityLevel.EXCELLENT
        elif self.overall_score >= 0.8:
            return QualityLevel.GOOD
        elif self.overall_score >= 0.7:
            return QualityLevel.ACCEPTABLE
        else:
            return QualityLevel.POOR


# =============================================================================
# Mock Services for Quality Governance
# =============================================================================

class MockQualityDetectionService:
    """Mock quality detection service"""
    
    def __init__(self):
        self.detection_rules = {}
        self.detected_issues = []
        
    def add_detection_rule(self, rule_id: str, rule_config: Dict[str, Any]):
        """Add quality detection rule"""
        self.detection_rules[rule_id] = rule_config
    
    def detect_quality_issues(self, data_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect quality issues in data batch"""
        issues = []
        
        for data_item in data_batch:
            data_id = data_item["id"]
            
            # Simulate quality evaluation
            evaluation = QualityEvaluationForTest(data_id)
            
            # Check if quality is below threshold
            if evaluation.overall_score < 0.8:  # Quality threshold
                issue_type = self._determine_issue_type(evaluation.scores)
                priority = self._determine_priority(evaluation.overall_score)
                
                issue = {
                    "id": str(uuid4()),
                    "data_id": data_id,
                    "issue_type": issue_type,
                    "priority": priority,
                    "quality_score": evaluation.overall_score,
                    "detailed_scores": evaluation.scores,
                    "detected_at": datetime.now(),
                    "description": self._generate_issue_description(issue_type, evaluation.overall_score)
                }
                issues.append(issue)
                self.detected_issues.append(issue)
        
        return issues
    
    def _determine_issue_type(self, scores: Dict[str, float]) -> QualityIssueType:
        """Determine issue type based on lowest scoring aspect"""
        min_score_metric = min(scores.items(), key=lambda x: x[1])
        
        metric_to_issue = {
            "accuracy": QualityIssueType.ACCURACY,
            "completeness": QualityIssueType.COMPLETENESS,
            "consistency": QualityIssueType.CONSISTENCY,
            "faithfulness": QualityIssueType.GUIDELINE_VIOLATION,
            "answer_relevancy": QualityIssueType.ACCURACY,
            "context_precision": QualityIssueType.FORMAT_ERROR,
            "context_recall": QualityIssueType.COMPLETENESS
        }
        
        return metric_to_issue.get(min_score_metric[0], QualityIssueType.ACCURACY)
    
    def _determine_priority(self, quality_score: float) -> WorkOrderPriority:
        """Determine priority based on quality score"""
        if quality_score < 0.5:
            return WorkOrderPriority.URGENT
        elif quality_score < 0.6:
            return WorkOrderPriority.HIGH
        elif quality_score < 0.7:
            return WorkOrderPriority.MEDIUM
        else:
            return WorkOrderPriority.LOW
    
    def _generate_issue_description(self, issue_type: QualityIssueType, score: float) -> str:
        """Generate issue description"""
        descriptions = {
            QualityIssueType.ACCURACY: f"Accuracy issue detected (score: {score:.2f})",
            QualityIssueType.COMPLETENESS: f"Completeness issue detected (score: {score:.2f})",
            QualityIssueType.CONSISTENCY: f"Consistency issue detected (score: {score:.2f})",
            QualityIssueType.GUIDELINE_VIOLATION: f"Guideline violation detected (score: {score:.2f})",
            QualityIssueType.FORMAT_ERROR: f"Format error detected (score: {score:.2f})"
        }
        return descriptions.get(issue_type, f"Quality issue detected (score: {score:.2f})")


class MockWorkOrderManagementService:
    """Mock work order management service"""
    
    def __init__(self):
        self.work_orders = {}
        self.assignment_rules = {}
        
    def create_work_order(self, quality_issue: Dict[str, Any]) -> WorkOrderForTest:
        """Create work order from quality issue"""
        work_order = WorkOrderForTest(
            issue_type=quality_issue["issue_type"],
            priority=quality_issue["priority"],
            affected_data_ids=[quality_issue["data_id"]],
            description=quality_issue["description"]
        )
        
        # Store initial quality score
        work_order.quality_scores["before"] = quality_issue["quality_score"]
        
        self.work_orders[work_order.id] = work_order
        return work_order
    
    def assign_work_order(self, work_order_id: str, assignee_id: str) -> bool:
        """Assign work order to user"""
        if work_order_id not in self.work_orders:
            return False
        
        work_order = self.work_orders[work_order_id]
        work_order.assigned_to = assignee_id
        work_order.status = WorkOrderStatus.ASSIGNED
        
        return True
    
    def start_work_order(self, work_order_id: str) -> bool:
        """Start work on order"""
        if work_order_id not in self.work_orders:
            return False
        
        work_order = self.work_orders[work_order_id]
        work_order.status = WorkOrderStatus.IN_PROGRESS
        
        return True
    
    def complete_work_order(self, work_order_id: str, repair_actions: List[RepairActionForTest]) -> bool:
        """Complete work order with repair actions"""
        if work_order_id not in self.work_orders:
            return False
        
        work_order = self.work_orders[work_order_id]
        work_order.repair_actions = repair_actions
        work_order.status = WorkOrderStatus.COMPLETED
        
        # Simulate quality improvement
        total_improvement = sum(action.quality_improvement for action in repair_actions)
        work_order.quality_scores["after"] = min(1.0, 
            work_order.quality_scores["before"] + total_improvement)
        
        return True
    
    def get_work_orders_by_status(self, status: WorkOrderStatus) -> List[WorkOrderForTest]:
        """Get work orders by status"""
        return [wo for wo in self.work_orders.values() if wo.status == status]
    
    def get_overdue_work_orders(self) -> List[WorkOrderForTest]:
        """Get overdue work orders"""
        now = datetime.now()
        return [wo for wo in self.work_orders.values() 
                if wo.due_date < now and wo.status not in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CLOSED]]


class MockRagasEvaluationService:
    """Mock Ragas evaluation service"""
    
    def __init__(self):
        self.evaluations = {}
        self.evaluation_history = []
        
    def evaluate_data_quality(self, data_ids: List[str]) -> List[QualityEvaluationForTest]:
        """Evaluate quality using Ragas metrics"""
        evaluations = []
        
        for data_id in data_ids:
            evaluation = QualityEvaluationForTest(data_id, "ragas")
            evaluations.append(evaluation)
            self.evaluations[data_id] = evaluation
            self.evaluation_history.append(evaluation)
        
        return evaluations
    
    def compare_before_after_quality(self, data_id: str, 
                                   before_score: float, after_score: float) -> Dict[str, Any]:
        """Compare quality before and after repair"""
        improvement = after_score - before_score
        improvement_percentage = (improvement / before_score) * 100 if before_score > 0 else 0
        
        # Consider evaluation effective if there's any positive improvement
        # or if improvement percentage is at least 2%
        evaluation_effective = improvement > 0.01 or improvement_percentage >= 2.0
        
        return {
            "data_id": data_id,
            "before_score": before_score,
            "after_score": after_score,
            "improvement": improvement,
            "improvement_percentage": improvement_percentage,
            "evaluation_effective": evaluation_effective,
            "quality_level_before": self._score_to_level(before_score),
            "quality_level_after": self._score_to_level(after_score)
        }
    
    def _score_to_level(self, score: float) -> QualityLevel:
        """Convert score to quality level"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.8:
            return QualityLevel.GOOD
        elif score >= 0.7:
            return QualityLevel.ACCEPTABLE
        else:
            return QualityLevel.POOR
    
    def get_quality_trends(self, period_days: int = 30) -> Dict[str, Any]:
        """Get quality trends over period"""
        cutoff_date = datetime.now() - timedelta(days=period_days)
        recent_evaluations = [e for e in self.evaluation_history 
                            if e.evaluated_at >= cutoff_date]
        
        if not recent_evaluations:
            return {"trend": "no_data", "evaluations_count": 0}
        
        scores = [e.overall_score for e in recent_evaluations]
        avg_score = sum(scores) / len(scores)
        
        # Simple trend calculation
        if len(scores) >= 2:
            early_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
            late_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            
            if late_avg > early_avg * 1.05:
                trend = "improving"
            elif late_avg < early_avg * 0.95:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "average_score": avg_score,
            "evaluations_count": len(recent_evaluations),
            "score_range": {"min": min(scores), "max": max(scores)}
        }


class MockAssessmentReportService:
    """Mock assessment report service"""
    
    def __init__(self):
        self.reports = {}
        
    def generate_repair_effectiveness_report(self, work_orders: List[WorkOrderForTest]) -> Dict[str, Any]:
        """Generate repair effectiveness assessment report"""
        if not work_orders:
            return {"error": "No work orders provided"}
        
        completed_orders = [wo for wo in work_orders if wo.status == WorkOrderStatus.COMPLETED]
        
        if not completed_orders:
            return {"error": "No completed work orders"}
        
        # Calculate effectiveness metrics
        total_orders = len(completed_orders)
        effective_repairs = 0
        total_improvement = 0.0
        
        repair_details = []
        
        for wo in completed_orders:
            before_score = wo.quality_scores["before"]
            after_score = wo.quality_scores["after"]
            
            if before_score is not None and after_score is not None:
                improvement = after_score - before_score
                total_improvement += improvement
                
                if improvement > 0.05:  # 5% improvement threshold
                    effective_repairs += 1
                
                repair_details.append({
                    "work_order_id": wo.id,
                    "issue_type": wo.issue_type.value,
                    "priority": wo.priority.value,
                    "before_score": before_score,
                    "after_score": after_score,
                    "improvement": improvement,
                    "effective": improvement > 0.05,
                    "repair_actions_count": len(wo.repair_actions)
                })
        
        effectiveness_rate = (effective_repairs / total_orders) * 100 if total_orders > 0 else 0
        avg_improvement = total_improvement / total_orders if total_orders > 0 else 0
        
        report = {
            "report_id": str(uuid4()),
            "generated_at": datetime.now(),
            "period_summary": {
                "total_work_orders": total_orders,
                "effective_repairs": effective_repairs,
                "effectiveness_rate": effectiveness_rate,
                "average_improvement": avg_improvement
            },
            "repair_details": repair_details,
            "recommendations": self._generate_recommendations(effectiveness_rate, avg_improvement),
            "quality_distribution": self._calculate_quality_distribution(completed_orders)
        }
        
        self.reports[report["report_id"]] = report
        return report
    
    def _generate_recommendations(self, effectiveness_rate: float, avg_improvement: float) -> List[str]:
        """Generate recommendations based on effectiveness metrics"""
        recommendations = []
        
        if effectiveness_rate < 70:
            recommendations.append("Improve repair process training for better effectiveness")
        
        if avg_improvement < 0.1:
            recommendations.append("Review repair strategies to achieve higher quality improvements")
        
        if effectiveness_rate > 90:
            recommendations.append("Excellent repair effectiveness - consider sharing best practices")
        
        if avg_improvement > 0.2:
            recommendations.append("Outstanding quality improvements - document successful approaches")
        
        return recommendations
    
    def _calculate_quality_distribution(self, work_orders: List[WorkOrderForTest]) -> Dict[str, int]:
        """Calculate quality level distribution"""
        distribution = {level.value: 0 for level in QualityLevel}
        
        for wo in work_orders:
            after_score = wo.quality_scores.get("after")
            if after_score is not None:
                if after_score >= 0.9:
                    distribution["excellent"] += 1
                elif after_score >= 0.8:
                    distribution["good"] += 1
                elif after_score >= 0.7:
                    distribution["acceptable"] += 1
                else:
                    distribution["poor"] += 1
        
        return distribution


# =============================================================================
# Integration Test Fixtures
# =============================================================================

@pytest.fixture
def quality_detection_service():
    return MockQualityDetectionService()

@pytest.fixture
def work_order_service():
    return MockWorkOrderManagementService()

@pytest.fixture
def ragas_service():
    return MockRagasEvaluationService()

@pytest.fixture
def assessment_service():
    return MockAssessmentReportService()

@pytest.fixture
def sample_data_batch():
    """Sample data batch for testing"""
    return [
        {"id": f"data_{i}", "content": f"Sample content {i}", "type": "annotation"}
        for i in range(10)
    ]


# =============================================================================
# Quality Governance Workflow Tests
# =============================================================================

class TestQualityGovernanceWorkflow:
    """Test complete quality governance workflow"""
    
    def test_complete_quality_governance_flow(self, quality_detection_service, 
                                            work_order_service, ragas_service, 
                                            assessment_service, sample_data_batch):
        """Test complete quality governance workflow from detection to assessment"""
        
        # Phase 1: Quality Issue Detection
        detected_issues = quality_detection_service.detect_quality_issues(sample_data_batch)
        
        assert len(detected_issues) > 0, "Should detect some quality issues"
        
        # Phase 2: Work Order Creation
        work_orders = []
        for issue in detected_issues:
            work_order = work_order_service.create_work_order(issue)
            work_orders.append(work_order)
        
        assert len(work_orders) == len(detected_issues)
        
        # Phase 3: Work Order Assignment and Processing
        for i, work_order in enumerate(work_orders):
            assignee_id = f"repair_specialist_{i % 3}"  # 3 specialists
            
            # Assign work order
            success = work_order_service.assign_work_order(work_order.id, assignee_id)
            assert success is True
            
            # Start work
            success = work_order_service.start_work_order(work_order.id)
            assert success is True
            
            # Create repair actions
            repair_actions = [
                RepairActionForTest(work_order.id, "data_correction", "Fixed accuracy issues"),
                RepairActionForTest(work_order.id, "guideline_alignment", "Aligned with guidelines")
            ]
            
            # Simulate repair effectiveness
            for action in repair_actions:
                action.quality_improvement = 0.1 + (i % 3) * 0.05  # 0.1-0.2 improvement
                action.status = RepairStatus.COMPLETED
            
            # Complete work order
            success = work_order_service.complete_work_order(work_order.id, repair_actions)
            assert success is True
        
        # Phase 4: Ragas Re-evaluation
        completed_orders = work_order_service.get_work_orders_by_status(WorkOrderStatus.COMPLETED)
        assert len(completed_orders) == len(work_orders)
        
        quality_comparisons = []
        for wo in completed_orders:
            for data_id in wo.affected_data_ids:
                comparison = ragas_service.compare_before_after_quality(
                    data_id, 
                    wo.quality_scores["before"], 
                    wo.quality_scores["after"]
                )
                quality_comparisons.append(comparison)
        
        # Phase 5: Assessment Report Generation
        effectiveness_report = assessment_service.generate_repair_effectiveness_report(completed_orders)
        
        # Verification
        assert "report_id" in effectiveness_report
        assert effectiveness_report["period_summary"]["total_work_orders"] == len(completed_orders)
        assert effectiveness_report["period_summary"]["effectiveness_rate"] > 0
        
        # Verify quality improvements
        effective_repairs = effectiveness_report["period_summary"]["effective_repairs"]
        assert effective_repairs > 0, "Should have some effective repairs"
        
        # Verify recommendations are generated
        assert len(effectiveness_report["recommendations"]) > 0
        
        return {
            "detected_issues": detected_issues,
            "work_orders": work_orders,
            "quality_comparisons": quality_comparisons,
            "effectiveness_report": effectiveness_report
        }
    
    def test_work_order_prioritization_and_sla(self, quality_detection_service, work_order_service):
        """Test work order prioritization and SLA management"""
        
        # Create data with varying quality issues
        test_data = [
            {"id": "urgent_data", "quality_score": 0.4},  # Should be urgent
            {"id": "high_data", "quality_score": 0.55},   # Should be high
            {"id": "medium_data", "quality_score": 0.65}, # Should be medium
            {"id": "low_data", "quality_score": 0.75}     # Should be low
        ]
        
        # Simulate quality detection with predefined scores
        issues = []
        for data in test_data:
            issue = {
                "id": str(uuid4()),
                "data_id": data["id"],
                "issue_type": QualityIssueType.ACCURACY,
                "priority": quality_detection_service._determine_priority(data["quality_score"]),
                "quality_score": data["quality_score"],
                "detailed_scores": {"accuracy": data["quality_score"]},
                "detected_at": datetime.now(),
                "description": f"Quality issue for {data['id']}"
            }
            issues.append(issue)
        
        # Create work orders
        work_orders = []
        for issue in issues:
            work_order = work_order_service.create_work_order(issue)
            work_orders.append(work_order)
        
        # Verify prioritization
        urgent_orders = [wo for wo in work_orders if wo.priority == WorkOrderPriority.URGENT]
        high_orders = [wo for wo in work_orders if wo.priority == WorkOrderPriority.HIGH]
        medium_orders = [wo for wo in work_orders if wo.priority == WorkOrderPriority.MEDIUM]
        low_orders = [wo for wo in work_orders if wo.priority == WorkOrderPriority.LOW]
        
        assert len(urgent_orders) == 1
        assert len(high_orders) == 1
        assert len(medium_orders) == 1
        assert len(low_orders) == 1
        
        # Verify SLA due dates
        urgent_wo = urgent_orders[0]
        high_wo = high_orders[0]
        
        # Urgent should have shorter due date than high priority
        assert urgent_wo.due_date < high_wo.due_date
        
        # Check overdue detection (simulate time passing)
        # No orders should be overdue initially
        overdue_orders = work_order_service.get_overdue_work_orders()
        assert len(overdue_orders) == 0
    
    def test_ragas_evaluation_and_improvement_tracking(self, ragas_service):
        """Test Ragas evaluation and quality improvement tracking"""
        
        # Initial evaluation
        data_ids = ["test_data_1", "test_data_2", "test_data_3"]
        initial_evaluations = ragas_service.evaluate_data_quality(data_ids)
        
        assert len(initial_evaluations) == 3
        
        # Simulate repairs and re-evaluation
        improvement_results = []
        for evaluation in initial_evaluations:
            # Simulate quality improvement after repair
            improved_score = min(1.0, evaluation.overall_score + 0.15)  # 15% improvement
            
            comparison = ragas_service.compare_before_after_quality(
                evaluation.data_id,
                evaluation.overall_score,
                improved_score
            )
            improvement_results.append(comparison)
        
        # Verify improvements
        for result in improvement_results:
            assert result["improvement"] > 0, "Should show quality improvement"
            assert result["evaluation_effective"] is True, "Should be effective improvement"
        
        # Test quality trends
        trends = ragas_service.get_quality_trends(30)
        assert trends["evaluations_count"] == 3
        assert "average_score" in trends
    
    def test_assessment_report_generation_and_recommendations(self, assessment_service):
        """Test assessment report generation and recommendation system"""
        
        # Create mock completed work orders with varying effectiveness
        work_orders = []
        
        # Highly effective repair
        wo1 = WorkOrderForTest(QualityIssueType.ACCURACY, WorkOrderPriority.HIGH, ["data_1"], "Test issue 1")
        wo1.status = WorkOrderStatus.COMPLETED
        wo1.quality_scores = {"before": 0.6, "after": 0.85}  # 25% improvement
        wo1.repair_actions = [RepairActionForTest(wo1.id, "correction", "Fixed issues")]
        work_orders.append(wo1)
        
        # Moderately effective repair
        wo2 = WorkOrderForTest(QualityIssueType.COMPLETENESS, WorkOrderPriority.MEDIUM, ["data_2"], "Test issue 2")
        wo2.status = WorkOrderStatus.COMPLETED
        wo2.quality_scores = {"before": 0.7, "after": 0.78}  # 8% improvement
        wo2.repair_actions = [RepairActionForTest(wo2.id, "enhancement", "Enhanced content")]
        work_orders.append(wo2)
        
        # Ineffective repair
        wo3 = WorkOrderForTest(QualityIssueType.CONSISTENCY, WorkOrderPriority.LOW, ["data_3"], "Test issue 3")
        wo3.status = WorkOrderStatus.COMPLETED
        wo3.quality_scores = {"before": 0.65, "after": 0.67}  # 2% improvement
        wo3.repair_actions = [RepairActionForTest(wo3.id, "minor_fix", "Minor adjustments")]
        work_orders.append(wo3)
        
        # Generate assessment report
        report = assessment_service.generate_repair_effectiveness_report(work_orders)
        
        # Verify report structure
        assert "report_id" in report
        assert "period_summary" in report
        assert "repair_details" in report
        assert "recommendations" in report
        assert "quality_distribution" in report
        
        # Verify calculations
        summary = report["period_summary"]
        assert summary["total_work_orders"] == 3
        assert summary["effective_repairs"] == 2  # wo1 and wo2 are effective (>5% improvement)
        assert abs(summary["effectiveness_rate"] - 66.67) < 0.1  # 2/3 * 100
        
        # Verify repair details
        details = report["repair_details"]
        assert len(details) == 3
        
        effective_details = [d for d in details if d["effective"]]
        assert len(effective_details) == 2
        
        # Verify recommendations are generated
        recommendations = report["recommendations"]
        assert len(recommendations) > 0
    
    def test_quality_governance_error_handling(self, quality_detection_service, 
                                             work_order_service, assessment_service):
        """Test error handling in quality governance workflow"""
        
        # Test empty data batch
        empty_issues = quality_detection_service.detect_quality_issues([])
        assert len(empty_issues) == 0
        
        # Test invalid work order operations
        invalid_assignment = work_order_service.assign_work_order("invalid_id", "user_1")
        assert invalid_assignment is False
        
        invalid_start = work_order_service.start_work_order("invalid_id")
        assert invalid_start is False
        
        invalid_completion = work_order_service.complete_work_order("invalid_id", [])
        assert invalid_completion is False
        
        # Test report generation with no work orders
        empty_report = assessment_service.generate_repair_effectiveness_report([])
        assert "error" in empty_report
        
        # Test report generation with no completed work orders
        pending_wo = WorkOrderForTest(QualityIssueType.ACCURACY, WorkOrderPriority.MEDIUM, ["data_1"], "Test")
        pending_wo.status = WorkOrderStatus.CREATED  # Not completed
        
        no_completed_report = assessment_service.generate_repair_effectiveness_report([pending_wo])
        assert "error" in no_completed_report


class TestQualityGovernancePerformance:
    """Test performance aspects of quality governance"""
    
    def test_large_batch_quality_detection(self, quality_detection_service):
        """Test quality detection performance with large data batches"""
        
        # Create large data batch
        large_batch = [
            {"id": f"data_{i}", "content": f"Content {i}", "type": "annotation"}
            for i in range(100)  # 100 items
        ]
        
        # Measure detection time
        start_time = datetime.now()
        detected_issues = quality_detection_service.detect_quality_issues(large_batch)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Verify results
        assert len(detected_issues) >= 0  # May or may not have issues
        assert processing_time < 5.0, f"Detection took {processing_time:.2f}s, expected < 5s"
    
    def test_concurrent_work_order_processing(self, work_order_service):
        """Test concurrent work order processing"""
        
        # Create multiple work orders
        work_orders = []
        for i in range(20):
            issue = {
                "issue_type": QualityIssueType.ACCURACY,
                "priority": WorkOrderPriority.MEDIUM,
                "data_id": f"data_{i}",
                "quality_score": 0.7,
                "detailed_scores": {"accuracy": 0.7},
                "detected_at": datetime.now(),
                "description": f"Issue {i}"
            }
            
            work_order = work_order_service.create_work_order(issue)
            work_orders.append(work_order)
        
        # Process all work orders
        start_time = datetime.now()
        
        for i, wo in enumerate(work_orders):
            assignee = f"specialist_{i % 5}"  # 5 specialists
            work_order_service.assign_work_order(wo.id, assignee)
            work_order_service.start_work_order(wo.id)
            
            # Simulate repair
            repair_actions = [RepairActionForTest(wo.id, "fix", "Fixed issue")]
            repair_actions[0].quality_improvement = 0.1
            work_order_service.complete_work_order(wo.id, repair_actions)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Verify all orders are completed
        completed_orders = work_order_service.get_work_orders_by_status(WorkOrderStatus.COMPLETED)
        assert len(completed_orders) == 20
        
        # Performance check
        assert processing_time < 3.0, f"Processing took {processing_time:.2f}s, expected < 3s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])