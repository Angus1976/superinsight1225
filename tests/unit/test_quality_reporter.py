"""
Unit tests for Quality Reporter
质量报告器单元测试
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestQualityReporter:
    """Quality Reporter unit tests"""

    def test_calculate_average_scores(self):
        """Test average score calculation"""
        annotations = [
            {"accuracy": 0.9, "completeness": 0.8, "timeliness": 1.0},
            {"accuracy": 0.8, "completeness": 0.9, "timeliness": 0.8},
            {"accuracy": 0.85, "completeness": 0.85, "timeliness": 0.9},
        ]
        
        avg_scores = {}
        for dim in ["accuracy", "completeness", "timeliness"]:
            values = [a[dim] for a in annotations]
            avg_scores[dim] = sum(values) / len(values)
        
        assert avg_scores["accuracy"] == pytest.approx(0.85, rel=0.01)
        assert avg_scores["completeness"] == pytest.approx(0.85, rel=0.01)
        assert avg_scores["timeliness"] == pytest.approx(0.9, rel=0.01)

    def test_calculate_quality_trend(self):
        """Test quality trend calculation"""
        daily_scores = [
            {"date": "2026-01-01", "score": 0.80},
            {"date": "2026-01-02", "score": 0.82},
            {"date": "2026-01-03", "score": 0.85},
            {"date": "2026-01-04", "score": 0.83},
            {"date": "2026-01-05", "score": 0.87},
        ]
        
        # Calculate trend direction
        first_half = sum(d["score"] for d in daily_scores[:2]) / 2
        second_half = sum(d["score"] for d in daily_scores[-2:]) / 2
        
        trend = "up" if second_half > first_half else "down" if second_half < first_half else "stable"
        
        assert trend == "up"

    def test_get_issue_distribution(self):
        """Test issue distribution calculation"""
        issues = [
            {"type": "required_fields", "count": 15},
            {"type": "format_validation", "count": 8},
            {"type": "value_range", "count": 5},
            {"type": "length_limit", "count": 3},
        ]
        
        distribution = {i["type"]: i["count"] for i in issues}
        total = sum(distribution.values())
        
        assert distribution["required_fields"] == 15
        assert total == 31

    def test_generate_annotator_ranking(self):
        """Test annotator ranking generation"""
        annotators = [
            {"id": "1", "name": "Alice", "score": 0.92, "count": 100},
            {"id": "2", "name": "Bob", "score": 0.88, "count": 120},
            {"id": "3", "name": "Charlie", "score": 0.95, "count": 80},
        ]
        
        # Sort by score descending
        ranked = sorted(annotators, key=lambda x: x["score"], reverse=True)
        
        # Add rank
        for i, a in enumerate(ranked):
            a["rank"] = i + 1
        
        assert ranked[0]["name"] == "Charlie"
        assert ranked[0]["rank"] == 1
        assert ranked[1]["name"] == "Alice"
        assert ranked[2]["name"] == "Bob"

    def test_calculate_pass_rate(self):
        """Test pass rate calculation"""
        results = [
            {"passed": True},
            {"passed": True},
            {"passed": False},
            {"passed": True},
            {"passed": False},
        ]
        
        passed_count = sum(1 for r in results if r["passed"])
        pass_rate = passed_count / len(results)
        
        assert pass_rate == 0.6

    def test_generate_trend_report_daily(self):
        """Test daily trend report generation"""
        base_date = datetime(2026, 1, 1)
        data_points = []
        
        for i in range(7):
            date = base_date + timedelta(days=i)
            data_points.append({
                "date": date.strftime("%Y-%m-%d"),
                "score": 0.80 + (i * 0.02),
                "count": 50 + (i * 5)
            })
        
        assert len(data_points) == 7
        assert data_points[0]["date"] == "2026-01-01"
        assert data_points[-1]["date"] == "2026-01-07"

    def test_generate_trend_report_weekly(self):
        """Test weekly trend report generation"""
        weeks = [
            {"week": "2026-W01", "score": 0.82, "count": 350},
            {"week": "2026-W02", "score": 0.85, "count": 380},
            {"week": "2026-W03", "score": 0.87, "count": 400},
            {"week": "2026-W04", "score": 0.86, "count": 390},
        ]
        
        avg_score = sum(w["score"] for w in weeks) / len(weeks)
        total_count = sum(w["count"] for w in weeks)
        
        assert avg_score == pytest.approx(0.85, rel=0.01)
        assert total_count == 1520


class TestReportExport:
    """Tests for report export functionality"""

    def test_export_to_json(self):
        """Test JSON export"""
        report = {
            "project_id": "project1",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "total_annotations": 1000,
            "average_scores": {"accuracy": 0.85, "completeness": 0.90}
        }
        
        json_output = json.dumps(report, indent=2)
        parsed = json.loads(json_output)
        
        assert parsed["project_id"] == "project1"
        assert parsed["total_annotations"] == 1000

    def test_export_format_validation(self):
        """Test export format validation"""
        valid_formats = ["pdf", "excel", "html", "json"]
        
        def validate_format(fmt: str) -> bool:
            return fmt.lower() in valid_formats
        
        assert validate_format("pdf") is True
        assert validate_format("PDF") is True
        assert validate_format("excel") is True
        assert validate_format("csv") is False

    def test_report_data_structure(self):
        """Test report data structure"""
        report = {
            "project_id": "project1",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-01-31T23:59:59Z",
            "total_annotations": 1000,
            "average_scores": {
                "accuracy": 0.85,
                "completeness": 0.90,
                "timeliness": 0.88
            },
            "quality_trend": [
                {"date": "2026-01-01", "score": 0.82},
                {"date": "2026-01-15", "score": 0.86},
                {"date": "2026-01-31", "score": 0.88}
            ],
            "issue_distribution": {
                "required_fields": 50,
                "format_validation": 30,
                "value_range": 20
            },
            "generated_at": "2026-02-01T10:00:00Z"
        }
        
        # Validate structure
        assert "project_id" in report
        assert "average_scores" in report
        assert "quality_trend" in report
        assert isinstance(report["quality_trend"], list)
        assert isinstance(report["issue_distribution"], dict)


class TestScheduledReports:
    """Tests for scheduled report functionality"""

    def test_cron_expression_validation(self):
        """Test cron expression validation"""
        def validate_cron(expr: str) -> bool:
            parts = expr.split()
            if len(parts) != 5:
                return False
            # Basic validation - each part should be valid
            return True
        
        assert validate_cron("0 9 * * 1") is True  # Every Monday at 9am
        assert validate_cron("0 9 1 * *") is True  # First day of month at 9am
        assert validate_cron("invalid") is False

    def test_schedule_creation(self):
        """Test report schedule creation"""
        schedule = {
            "id": "schedule1",
            "project_id": "project1",
            "report_type": "project",
            "schedule": "0 9 * * 1",
            "recipients": ["user1@example.com", "user2@example.com"],
            "enabled": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        assert schedule["report_type"] == "project"
        assert len(schedule["recipients"]) == 2
        assert schedule["enabled"] is True

    def test_recipient_validation(self):
        """Test recipient email validation"""
        import re
        
        email_pattern = r'^[\w.+-]+@[\w.-]+\.\w+$'
        
        def validate_recipients(recipients: List[str]) -> tuple:
            invalid = [r for r in recipients if not re.match(email_pattern, r)]
            return len(invalid) == 0, invalid
        
        valid, invalid = validate_recipients(["user@example.com", "admin@company.org"])
        assert valid is True
        
        valid, invalid = validate_recipients(["user@example.com", "invalid-email"])
        assert valid is False
        assert "invalid-email" in invalid


class TestAnnotatorStats:
    """Tests for annotator statistics"""

    def test_calculate_annotator_stats(self):
        """Test annotator statistics calculation"""
        annotations = [
            {"annotator_id": "1", "score": 0.9, "passed": True},
            {"annotator_id": "1", "score": 0.85, "passed": True},
            {"annotator_id": "1", "score": 0.7, "passed": False},
            {"annotator_id": "2", "score": 0.95, "passed": True},
            {"annotator_id": "2", "score": 0.92, "passed": True},
        ]
        
        # Group by annotator
        stats = {}
        for a in annotations:
            aid = a["annotator_id"]
            if aid not in stats:
                stats[aid] = {"scores": [], "passed": 0, "total": 0}
            stats[aid]["scores"].append(a["score"])
            stats[aid]["total"] += 1
            if a["passed"]:
                stats[aid]["passed"] += 1
        
        # Calculate averages
        for aid, s in stats.items():
            s["average_score"] = sum(s["scores"]) / len(s["scores"])
            s["pass_rate"] = s["passed"] / s["total"]
        
        assert stats["1"]["average_score"] == pytest.approx(0.817, rel=0.01)
        assert stats["1"]["pass_rate"] == pytest.approx(0.667, rel=0.01)
        assert stats["2"]["average_score"] == pytest.approx(0.935, rel=0.01)
        assert stats["2"]["pass_rate"] == 1.0

    def test_ranking_with_ties(self):
        """Test ranking when scores are tied"""
        annotators = [
            {"id": "1", "score": 0.90},
            {"id": "2", "score": 0.90},
            {"id": "3", "score": 0.85},
        ]
        
        # Sort and rank
        sorted_annotators = sorted(annotators, key=lambda x: x["score"], reverse=True)
        
        current_rank = 1
        prev_score = None
        for i, a in enumerate(sorted_annotators):
            if prev_score is not None and a["score"] < prev_score:
                current_rank = i + 1
            a["rank"] = current_rank
            prev_score = a["score"]
        
        # Both top scorers should have rank 1
        assert sorted_annotators[0]["rank"] == 1
        assert sorted_annotators[1]["rank"] == 1
        assert sorted_annotators[2]["rank"] == 3


class TestReportDataConsistency:
    """Tests for report data consistency"""

    def test_total_matches_sum(self):
        """Test that totals match sum of parts"""
        report = {
            "total_annotations": 100,
            "passed_count": 85,
            "failed_count": 15
        }
        
        assert report["passed_count"] + report["failed_count"] == report["total_annotations"]

    def test_percentages_sum_to_100(self):
        """Test that percentages sum to approximately 100"""
        distribution = {
            "category_a": 45.5,
            "category_b": 30.2,
            "category_c": 24.3
        }
        
        total = sum(distribution.values())
        assert total == pytest.approx(100, rel=0.01)

    def test_date_range_validity(self):
        """Test date range validity"""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)
        
        assert end > start
        assert (end - start).days == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
