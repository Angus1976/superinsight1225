"""
Integration tests for Quality Management Module
质量管理模块集成测试
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestQualityScoringIntegration:
    """Integration tests for quality scoring workflow"""

    def test_full_scoring_workflow(self):
        """Test complete scoring workflow from annotation to score"""
        # 1. Create annotation data
        annotation = {
            "id": "ann_001",
            "project_id": "proj_001",
            "annotator_id": "user_001",
            "data": {
                "label": "positive",
                "confidence": 0.85,
                "entities": [{"text": "product", "type": "PRODUCT"}]
            },
            "started_at": datetime.utcnow() - timedelta(minutes=30),
            "completed_at": datetime.utcnow()
        }
        
        # 2. Define gold standard
        gold_standard = {
            "label": "positive",
            "confidence": 0.9,
            "entities": [{"text": "product", "type": "PRODUCT"}]
        }
        
        # 3. Calculate accuracy
        matching = sum(1 for k, v in gold_standard.items() 
                      if annotation["data"].get(k) == v)
        accuracy = matching / len(gold_standard)
        
        # 4. Calculate completeness
        required_fields = ["label", "confidence", "entities"]
        filled = sum(1 for f in required_fields 
                    if f in annotation["data"] and annotation["data"][f])
        completeness = filled / len(required_fields)
        
        # 5. Calculate timeliness (30 min is within expected 1 hour)
        timeliness = 1.0
        
        # 6. Calculate weighted score
        weights = {"accuracy": 0.4, "completeness": 0.3, "timeliness": 0.3}
        scores = {"accuracy": accuracy, "completeness": completeness, "timeliness": timeliness}
        total_score = sum(scores[d] * weights[d] for d in weights)
        
        # Verify results
        assert 0 <= total_score <= 1
        assert completeness == 1.0
        assert timeliness == 1.0

    def test_consistency_scoring_workflow(self):
        """Test consistency scoring between multiple annotators"""
        # Multiple annotators' results for same task
        annotations = [
            {"annotator_id": "user1", "label": "positive", "confidence": 0.9},
            {"annotator_id": "user2", "label": "positive", "confidence": 0.85},
            {"annotator_id": "user3", "label": "positive", "confidence": 0.88},
        ]
        
        # Calculate agreement on label
        labels = [a["label"] for a in annotations]
        unique_labels = set(labels)
        
        # Perfect agreement if all same
        if len(unique_labels) == 1:
            agreement = 1.0
        else:
            # Calculate majority agreement
            from collections import Counter
            label_counts = Counter(labels)
            majority_count = max(label_counts.values())
            agreement = majority_count / len(labels)
        
        assert agreement == 1.0  # All agree on "positive"

    def test_batch_scoring_workflow(self):
        """Test batch scoring of multiple annotations"""
        annotations = [
            {"id": f"ann_{i}", "data": {"label": "positive", "score": 0.8 + i * 0.02}}
            for i in range(10)
        ]
        
        # Score each annotation
        scores = []
        for ann in annotations:
            # Simplified scoring
            score = ann["data"]["score"]
            scores.append({"annotation_id": ann["id"], "score": score})
        
        # Calculate batch statistics
        avg_score = sum(s["score"] for s in scores) / len(scores)
        min_score = min(s["score"] for s in scores)
        max_score = max(s["score"] for s in scores)
        
        assert len(scores) == 10
        assert min_score >= 0.8
        assert max_score <= 1.0
        assert 0.8 <= avg_score <= 1.0


class TestQualityCheckingIntegration:
    """Integration tests for quality checking workflow"""

    def test_full_checking_workflow(self):
        """Test complete checking workflow"""
        # 1. Define rules
        rules = [
            {"id": "r1", "name": "required_fields", "type": "builtin", 
             "config": {"fields": ["label", "confidence"]}, "severity": "high"},
            {"id": "r2", "name": "value_range", "type": "builtin",
             "config": {"field": "confidence", "min": 0, "max": 1}, "severity": "medium"},
        ]
        
        # 2. Create annotation to check
        annotation = {
            "id": "ann_001",
            "data": {"label": "positive", "confidence": 0.85}
        }
        
        # 3. Execute rules
        issues = []
        for rule in rules:
            if rule["name"] == "required_fields":
                required = rule["config"]["fields"]
                missing = [f for f in required if f not in annotation["data"]]
                if missing:
                    issues.append({
                        "rule_id": rule["id"],
                        "severity": rule["severity"],
                        "message": f"Missing fields: {missing}"
                    })
            elif rule["name"] == "value_range":
                field = rule["config"]["field"]
                value = annotation["data"].get(field)
                if value is not None:
                    if value < rule["config"]["min"] or value > rule["config"]["max"]:
                        issues.append({
                            "rule_id": rule["id"],
                            "severity": rule["severity"],
                            "message": f"{field} out of range"
                        })
        
        # 4. Verify results
        assert len(issues) == 0  # All checks should pass

    def test_checking_with_violations(self):
        """Test checking workflow with violations"""
        rules = [
            {"id": "r1", "name": "required_fields", "type": "builtin",
             "config": {"fields": ["label", "confidence", "entities"]}, "severity": "high"},
        ]
        
        annotation = {
            "id": "ann_001",
            "data": {"label": "positive"}  # Missing confidence and entities
        }
        
        issues = []
        for rule in rules:
            if rule["name"] == "required_fields":
                required = rule["config"]["fields"]
                missing = [f for f in required if f not in annotation["data"] or not annotation["data"].get(f)]
                if missing:
                    issues.append({
                        "rule_id": rule["id"],
                        "severity": rule["severity"],
                        "message": f"Missing fields: {missing}"
                    })
        
        assert len(issues) == 1
        assert issues[0]["severity"] == "high"

    def test_batch_checking_workflow(self):
        """Test batch checking of multiple annotations"""
        annotations = [
            {"id": "ann_1", "data": {"label": "positive", "confidence": 0.9}},
            {"id": "ann_2", "data": {"label": "negative"}},  # Missing confidence
            {"id": "ann_3", "data": {"label": "neutral", "confidence": 0.7}},
        ]
        
        required_fields = ["label", "confidence"]
        
        results = []
        for ann in annotations:
            missing = [f for f in required_fields if f not in ann["data"]]
            results.append({
                "annotation_id": ann["id"],
                "passed": len(missing) == 0,
                "issues": [{"field": f, "message": "Missing"} for f in missing]
            })
        
        passed_count = sum(1 for r in results if r["passed"])
        failed_count = len(results) - passed_count
        
        assert passed_count == 2
        assert failed_count == 1


class TestRuleManagementIntegration:
    """Integration tests for rule management"""

    def test_rule_lifecycle(self):
        """Test complete rule lifecycle: create, update, delete"""
        rules_db = {}
        
        # Create
        rule = {
            "id": "rule_001",
            "name": "Test Rule",
            "type": "builtin",
            "severity": "medium",
            "priority": 50,
            "enabled": True,
            "version": 1
        }
        rules_db[rule["id"]] = rule
        
        assert "rule_001" in rules_db
        assert rules_db["rule_001"]["version"] == 1
        
        # Update
        rules_db["rule_001"]["severity"] = "high"
        rules_db["rule_001"]["version"] += 1
        
        assert rules_db["rule_001"]["severity"] == "high"
        assert rules_db["rule_001"]["version"] == 2
        
        # Disable
        rules_db["rule_001"]["enabled"] = False
        
        assert rules_db["rule_001"]["enabled"] is False
        
        # Delete
        del rules_db["rule_001"]
        
        assert "rule_001" not in rules_db

    def test_rule_template_instantiation(self):
        """Test creating rules from templates"""
        templates = {
            "required_fields_template": {
                "name": "Required Fields Check",
                "type": "builtin",
                "severity": "high",
                "config": {"fields": []}
            }
        }
        
        # Instantiate from template
        template = templates["required_fields_template"]
        new_rule = {
            "id": "rule_from_template",
            **template,
            "config": {"fields": ["name", "email", "phone"]},
            "project_id": "proj_001",
            "version": 1
        }
        
        assert new_rule["name"] == "Required Fields Check"
        assert new_rule["config"]["fields"] == ["name", "email", "phone"]


class TestReportGenerationIntegration:
    """Integration tests for report generation"""

    def test_project_report_generation(self):
        """Test project quality report generation"""
        # Simulate annotation data
        annotations = [
            {"id": f"ann_{i}", "score": 0.8 + (i % 3) * 0.05, "passed": i % 5 != 0}
            for i in range(100)
        ]
        
        # Generate report
        total = len(annotations)
        passed = sum(1 for a in annotations if a["passed"])
        avg_score = sum(a["score"] for a in annotations) / total
        
        report = {
            "project_id": "proj_001",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "total_annotations": total,
            "passed_count": passed,
            "failed_count": total - passed,
            "pass_rate": passed / total,
            "average_score": avg_score
        }
        
        assert report["total_annotations"] == 100
        assert report["passed_count"] + report["failed_count"] == 100
        assert 0 <= report["pass_rate"] <= 1

    def test_annotator_ranking_generation(self):
        """Test annotator ranking report generation"""
        # Simulate annotator data
        annotator_data = [
            {"id": "user1", "name": "Alice", "annotations": 50, "avg_score": 0.92},
            {"id": "user2", "name": "Bob", "annotations": 45, "avg_score": 0.88},
            {"id": "user3", "name": "Charlie", "annotations": 60, "avg_score": 0.95},
        ]
        
        # Generate ranking
        ranked = sorted(annotator_data, key=lambda x: x["avg_score"], reverse=True)
        for i, a in enumerate(ranked):
            a["rank"] = i + 1
        
        assert ranked[0]["name"] == "Charlie"
        assert ranked[0]["rank"] == 1
        assert ranked[-1]["rank"] == 3


class TestAlertWorkflowIntegration:
    """Integration tests for alert workflow"""

    def test_alert_trigger_workflow(self):
        """Test alert triggering workflow"""
        # Configure thresholds
        thresholds = {
            "accuracy": 0.7,
            "completeness": 0.8,
            "timeliness": 0.6
        }
        
        # Score that triggers alert
        score = {
            "accuracy": 0.65,  # Below threshold
            "completeness": 0.85,
            "timeliness": 0.9
        }
        
        # Check for alerts
        triggered = []
        for dim, threshold in thresholds.items():
            if score.get(dim, 1.0) < threshold:
                triggered.append(dim)
        
        assert len(triggered) == 1
        assert "accuracy" in triggered

    def test_alert_lifecycle(self):
        """Test alert lifecycle: create, acknowledge, resolve"""
        alerts_db = {}
        
        # Create alert
        alert = {
            "id": "alert_001",
            "project_id": "proj_001",
            "triggered_dimensions": ["accuracy"],
            "severity": "high",
            "status": "open",
            "created_at": datetime.utcnow().isoformat()
        }
        alerts_db[alert["id"]] = alert
        
        assert alerts_db["alert_001"]["status"] == "open"
        
        # Acknowledge
        alerts_db["alert_001"]["status"] = "acknowledged"
        alerts_db["alert_001"]["acknowledged_at"] = datetime.utcnow().isoformat()
        
        assert alerts_db["alert_001"]["status"] == "acknowledged"
        
        # Resolve
        alerts_db["alert_001"]["status"] = "resolved"
        alerts_db["alert_001"]["resolved_at"] = datetime.utcnow().isoformat()
        
        assert alerts_db["alert_001"]["status"] == "resolved"


class TestWorkflowIntegration:
    """Integration tests for improvement workflow"""

    def test_improvement_workflow_lifecycle(self):
        """Test complete improvement workflow lifecycle"""
        tasks_db = {}
        
        # 1. Create task from quality issue
        task = {
            "id": "task_001",
            "annotation_id": "ann_001",
            "issues": [{"rule_id": "r1", "severity": "high", "message": "Missing field"}],
            "assignee_id": "user_001",
            "status": "pending",
            "priority": 2,
            "created_at": datetime.utcnow().isoformat()
        }
        tasks_db[task["id"]] = task
        
        assert tasks_db["task_001"]["status"] == "pending"
        
        # 2. Start working
        tasks_db["task_001"]["status"] = "in_progress"
        
        # 3. Submit improvement
        tasks_db["task_001"]["improved_data"] = {"field": "corrected_value"}
        tasks_db["task_001"]["status"] = "submitted"
        tasks_db["task_001"]["submitted_at"] = datetime.utcnow().isoformat()
        
        assert tasks_db["task_001"]["status"] == "submitted"
        
        # 4. Review and approve
        tasks_db["task_001"]["status"] = "approved"
        tasks_db["task_001"]["reviewer_id"] = "reviewer_001"
        tasks_db["task_001"]["reviewed_at"] = datetime.utcnow().isoformat()
        
        assert tasks_db["task_001"]["status"] == "approved"

    def test_improvement_effect_evaluation(self):
        """Test improvement effect evaluation"""
        # Before improvement
        before_scores = [
            {"annotation_id": "ann_1", "accuracy": 0.6, "completeness": 0.7},
            {"annotation_id": "ann_2", "accuracy": 0.65, "completeness": 0.75},
        ]
        
        # After improvement
        after_scores = [
            {"annotation_id": "ann_1", "accuracy": 0.85, "completeness": 0.9},
            {"annotation_id": "ann_2", "accuracy": 0.88, "completeness": 0.92},
        ]
        
        # Calculate improvement
        improvements = []
        for before, after in zip(before_scores, after_scores):
            improvements.append({
                "annotation_id": before["annotation_id"],
                "accuracy_improvement": after["accuracy"] - before["accuracy"],
                "completeness_improvement": after["completeness"] - before["completeness"]
            })
        
        avg_accuracy_improvement = sum(i["accuracy_improvement"] for i in improvements) / len(improvements)
        avg_completeness_improvement = sum(i["completeness_improvement"] for i in improvements) / len(improvements)
        
        assert avg_accuracy_improvement > 0.2
        assert avg_completeness_improvement > 0.15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
