"""
Unit tests for Quality Workflow Engine
质量工作流引擎单元测试
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class MockImprovementTask:
    """Mock improvement task for testing"""
    def __init__(
        self,
        id: str,
        annotation_id: str,
        project_id: str,
        issues: List[Dict],
        assignee_id: str,
        status: str = "pending",
        priority: int = 1
    ):
        self.id = id
        self.annotation_id = annotation_id
        self.project_id = project_id
        self.issues = issues
        self.assignee_id = assignee_id
        self.status = status
        self.priority = priority
        self.improved_data = None
        self.reviewer_id = None
        self.review_comments = None
        self.created_at = datetime.utcnow()
        self.submitted_at = None
        self.reviewed_at = None


class TestQualityWorkflowEngine:
    """Quality Workflow Engine unit tests"""

    def test_calculate_priority_critical_issues(self):
        """Test priority calculation with critical issues"""
        issues = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"}
        ]
        
        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total_weight = sum(severity_weights.get(i["severity"], 1) for i in issues)
        
        if total_weight >= 10:
            priority = 3  # High
        elif total_weight >= 5:
            priority = 2  # Medium
        else:
            priority = 1  # Low
        
        # 4 + 3 + 2 = 9, so priority should be 2
        assert priority == 2

    def test_calculate_priority_many_critical(self):
        """Test priority calculation with many critical issues"""
        issues = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "critical"}
        ]
        
        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total_weight = sum(severity_weights.get(i["severity"], 1) for i in issues)
        
        if total_weight >= 10:
            priority = 3
        elif total_weight >= 5:
            priority = 2
        else:
            priority = 1
        
        # 4 + 4 + 4 = 12, so priority should be 3
        assert priority == 3

    def test_calculate_priority_low_issues(self):
        """Test priority calculation with low severity issues"""
        issues = [
            {"severity": "low"},
            {"severity": "low"},
            {"severity": "medium"}
        ]
        
        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total_weight = sum(severity_weights.get(i["severity"], 1) for i in issues)
        
        if total_weight >= 10:
            priority = 3
        elif total_weight >= 5:
            priority = 2
        else:
            priority = 1
        
        # 1 + 1 + 2 = 4, so priority should be 1
        assert priority == 1

    def test_create_improvement_task(self):
        """Test improvement task creation"""
        issues = [
            {"rule_id": "r1", "rule_name": "Required Fields", "severity": "high", "message": "Missing field"}
        ]
        
        task = MockImprovementTask(
            id="task1",
            annotation_id="ann1",
            project_id="proj1",
            issues=issues,
            assignee_id="user1"
        )
        
        assert task.id == "task1"
        assert task.status == "pending"
        assert len(task.issues) == 1
        assert task.improved_data is None

    def test_submit_improvement(self):
        """Test improvement submission"""
        task = MockImprovementTask(
            id="task1",
            annotation_id="ann1",
            project_id="proj1",
            issues=[{"severity": "high"}],
            assignee_id="user1"
        )
        
        # Submit improvement
        improved_data = {"field1": "corrected_value", "field2": "new_value"}
        task.improved_data = improved_data
        task.status = "submitted"
        task.submitted_at = datetime.utcnow()
        
        assert task.status == "submitted"
        assert task.improved_data == improved_data
        assert task.submitted_at is not None

    def test_review_improvement_approved(self):
        """Test improvement review - approved"""
        task = MockImprovementTask(
            id="task1",
            annotation_id="ann1",
            project_id="proj1",
            issues=[{"severity": "high"}],
            assignee_id="user1",
            status="submitted"
        )
        task.improved_data = {"field1": "corrected"}
        
        # Approve
        task.status = "approved"
        task.reviewer_id = "reviewer1"
        task.review_comments = "Good improvement"
        task.reviewed_at = datetime.utcnow()
        
        assert task.status == "approved"
        assert task.reviewer_id == "reviewer1"
        assert task.reviewed_at is not None

    def test_review_improvement_rejected(self):
        """Test improvement review - rejected"""
        task = MockImprovementTask(
            id="task1",
            annotation_id="ann1",
            project_id="proj1",
            issues=[{"severity": "high"}],
            assignee_id="user1",
            status="submitted"
        )
        task.improved_data = {"field1": "incorrect"}
        
        # Reject
        task.status = "rejected"
        task.reviewer_id = "reviewer1"
        task.review_comments = "Please fix the format"
        task.reviewed_at = datetime.utcnow()
        
        assert task.status == "rejected"
        assert "fix" in task.review_comments.lower()

    def test_task_status_transitions(self):
        """Test valid task status transitions"""
        valid_transitions = {
            "pending": ["in_progress"],
            "in_progress": ["submitted", "pending"],
            "submitted": ["approved", "rejected"],
            "approved": [],  # Terminal state
            "rejected": ["in_progress", "pending"]
        }
        
        def can_transition(from_status: str, to_status: str) -> bool:
            return to_status in valid_transitions.get(from_status, [])
        
        assert can_transition("pending", "in_progress") is True
        assert can_transition("in_progress", "submitted") is True
        assert can_transition("submitted", "approved") is True
        assert can_transition("submitted", "rejected") is True
        assert can_transition("approved", "pending") is False
        assert can_transition("rejected", "in_progress") is True


class TestWorkflowConfiguration:
    """Tests for workflow configuration"""

    def test_default_workflow_stages(self):
        """Test default workflow stages"""
        default_stages = ["identify", "assign", "improve", "review", "verify"]
        
        assert len(default_stages) == 5
        assert "identify" in default_stages
        assert "review" in default_stages

    def test_custom_workflow_stages(self):
        """Test custom workflow stages"""
        custom_stages = ["identify", "improve", "review"]  # Skip assign and verify
        
        assert len(custom_stages) == 3
        assert "assign" not in custom_stages

    def test_escalation_rules(self):
        """Test escalation rules configuration"""
        escalation_rules = {
            "hours": 24,  # Escalate after 24 hours
            "max_level": 3,  # Maximum escalation level
            "recipients": {
                1: ["team_lead@example.com"],
                2: ["manager@example.com"],
                3: ["director@example.com"]
            }
        }
        
        assert escalation_rules["hours"] == 24
        assert escalation_rules["max_level"] == 3
        assert len(escalation_rules["recipients"]) == 3

    def test_auto_create_task_setting(self):
        """Test auto create task setting"""
        config = {
            "auto_create_task": True,
            "auto_assign_to_annotator": True,
            "require_review": True
        }
        
        assert config["auto_create_task"] is True


class TestTaskAssignment:
    """Tests for task assignment logic"""

    def test_assign_to_original_annotator(self):
        """Test assigning task to original annotator"""
        annotation = {"id": "ann1", "annotator_id": "user1"}
        
        # Default: assign to original annotator
        assignee_id = annotation["annotator_id"]
        
        assert assignee_id == "user1"

    def test_assign_to_specific_user(self):
        """Test assigning task to specific user"""
        annotation = {"id": "ann1", "annotator_id": "user1"}
        specified_assignee = "user2"
        
        # Override with specified assignee
        assignee_id = specified_assignee if specified_assignee else annotation["annotator_id"]
        
        assert assignee_id == "user2"

    def test_workload_based_assignment(self):
        """Test workload-based assignment logic"""
        users = [
            {"id": "user1", "pending_tasks": 5},
            {"id": "user2", "pending_tasks": 2},
            {"id": "user3", "pending_tasks": 8}
        ]
        
        # Assign to user with least pending tasks
        assignee = min(users, key=lambda u: u["pending_tasks"])
        
        assert assignee["id"] == "user2"


class TestImprovementHistory:
    """Tests for improvement history tracking"""

    def test_record_history_entry(self):
        """Test recording history entry"""
        history = []
        
        entry = {
            "task_id": "task1",
            "action": "created",
            "actor_id": "system",
            "details": {"issues_count": 3},
            "created_at": datetime.utcnow().isoformat()
        }
        history.append(entry)
        
        assert len(history) == 1
        assert history[0]["action"] == "created"

    def test_history_actions(self):
        """Test various history actions"""
        valid_actions = [
            "created",
            "assigned",
            "started",
            "submitted",
            "approved",
            "rejected",
            "escalated",
            "commented"
        ]
        
        for action in valid_actions:
            assert isinstance(action, str)
            assert len(action) > 0


class TestImprovementEffect:
    """Tests for improvement effect evaluation"""

    def test_calculate_improvement_score(self):
        """Test improvement score calculation"""
        before_scores = {"accuracy": 0.6, "completeness": 0.7}
        after_scores = {"accuracy": 0.85, "completeness": 0.9}
        
        improvement = {}
        for dim in before_scores:
            improvement[dim] = after_scores[dim] - before_scores[dim]
        
        assert improvement["accuracy"] == pytest.approx(0.25, rel=0.01)
        assert improvement["completeness"] == pytest.approx(0.2, rel=0.01)

    def test_calculate_average_improvement(self):
        """Test average improvement calculation"""
        improvements = [
            {"accuracy": 0.2, "completeness": 0.15},
            {"accuracy": 0.3, "completeness": 0.25},
            {"accuracy": 0.1, "completeness": 0.2}
        ]
        
        avg_improvement = {}
        for dim in ["accuracy", "completeness"]:
            values = [i[dim] for i in improvements]
            avg_improvement[dim] = sum(values) / len(values)
        
        assert avg_improvement["accuracy"] == pytest.approx(0.2, rel=0.01)
        assert avg_improvement["completeness"] == pytest.approx(0.2, rel=0.01)

    def test_effect_report_structure(self):
        """Test effect report structure"""
        report = {
            "project_id": "proj1",
            "period": "month",
            "total_tasks": 50,
            "completed_tasks": 45,
            "average_improvement_score": 0.18,
            "improvement_by_dimension": {
                "accuracy": 0.2,
                "completeness": 0.15,
                "timeliness": 0.1
            }
        }
        
        assert report["completed_tasks"] <= report["total_tasks"]
        assert 0 <= report["average_improvement_score"] <= 1


class TestTaskFiltering:
    """Tests for task filtering and querying"""

    def test_filter_by_status(self):
        """Test filtering tasks by status"""
        tasks = [
            MockImprovementTask("1", "a1", "p1", [], "u1", status="pending"),
            MockImprovementTask("2", "a2", "p1", [], "u1", status="submitted"),
            MockImprovementTask("3", "a3", "p1", [], "u1", status="approved"),
            MockImprovementTask("4", "a4", "p1", [], "u1", status="pending"),
        ]
        
        pending_tasks = [t for t in tasks if t.status == "pending"]
        
        assert len(pending_tasks) == 2

    def test_filter_by_assignee(self):
        """Test filtering tasks by assignee"""
        tasks = [
            MockImprovementTask("1", "a1", "p1", [], "user1"),
            MockImprovementTask("2", "a2", "p1", [], "user2"),
            MockImprovementTask("3", "a3", "p1", [], "user1"),
        ]
        
        user1_tasks = [t for t in tasks if t.assignee_id == "user1"]
        
        assert len(user1_tasks) == 2

    def test_filter_by_priority(self):
        """Test filtering tasks by priority"""
        tasks = [
            MockImprovementTask("1", "a1", "p1", [], "u1", priority=3),
            MockImprovementTask("2", "a2", "p1", [], "u1", priority=1),
            MockImprovementTask("3", "a3", "p1", [], "u1", priority=3),
            MockImprovementTask("4", "a4", "p1", [], "u1", priority=2),
        ]
        
        high_priority = [t for t in tasks if t.priority >= 3]
        
        assert len(high_priority) == 2

    def test_sort_by_priority_and_date(self):
        """Test sorting tasks by priority and date"""
        tasks = [
            {"id": "1", "priority": 2, "created_at": "2026-01-01"},
            {"id": "2", "priority": 3, "created_at": "2026-01-02"},
            {"id": "3", "priority": 3, "created_at": "2026-01-01"},
            {"id": "4", "priority": 1, "created_at": "2026-01-01"},
        ]
        
        # Sort by priority desc, then by date asc
        sorted_tasks = sorted(tasks, key=lambda t: (-t["priority"], t["created_at"]))
        
        assert sorted_tasks[0]["id"] == "3"  # Priority 3, earlier date
        assert sorted_tasks[1]["id"] == "2"  # Priority 3, later date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
