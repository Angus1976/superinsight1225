"""Tests for the endpoint-to-UI completeness mapping system."""

import pytest
from tests.completeness_mapping import (
    normalize_path,
    map_completeness,
    _collect_frontend_calls,
    _build_frontend_index,
)


# ---------------------------------------------------------------------------
# Unit tests for path normalisation
# ---------------------------------------------------------------------------

class TestNormalizePath:
    def test_fastapi_param(self):
        assert normalize_path("/api/tasks/{task_id}") == "/api/tasks/:param"

    def test_colon_param(self):
        assert normalize_path("/api/tasks/:taskId") == "/api/tasks/:param"

    def test_mixed_params_match(self):
        a = normalize_path("/api/tasks/{id}/annotations/{ann_id}")
        b = normalize_path("/api/tasks/:id/annotations/:annId")
        assert a == b

    def test_trailing_slash_stripped(self):
        assert normalize_path("/api/tasks/") == "/api/tasks"

    def test_case_insensitive(self):
        assert normalize_path("/API/Tasks") == "/api/tasks"

    def test_no_params(self):
        assert normalize_path("/api/health") == "/api/health"


# ---------------------------------------------------------------------------
# Unit tests for mapping with synthetic data
# ---------------------------------------------------------------------------

def _make_be_report(endpoints):
    """Helper to build a minimal backend report."""
    return {
        "endpoints": [
            {"method": m, "path": p, "full_path": fp, "handler": h,
             "category": c, "source_file": "test.py"}
            for m, p, fp, h, c in endpoints
        ],
    }


def _make_fe_report(service_calls, component_calls=None):
    """Helper to build a minimal frontend report."""
    return {
        "service_api_calls": [
            {"method": m, "endpoint": ep, "source_file": sf}
            for m, ep, sf in service_calls
        ],
        "component_api_calls": component_calls or {},
    }


class TestMapCompleteness:
    def test_full_match(self):
        be = _make_be_report([("GET", "", "/api/tasks", "list_tasks", "Read")])
        fe = _make_fe_report([("GET", "/api/tasks", "taskService.ts")])
        report = map_completeness(be, fe)
        assert report["summary"]["matched_count"] == 1
        assert report["summary"]["orphaned_count"] == 0
        assert report["completeness"] == 100.0

    def test_orphaned_endpoint(self):
        be = _make_be_report([
            ("GET", "", "/api/tasks", "list_tasks", "Read"),
            ("DELETE", "/{id}", "/api/tasks/{id}", "delete_task", "Delete"),
        ])
        fe = _make_fe_report([("GET", "/api/tasks", "taskService.ts")])
        report = map_completeness(be, fe)
        assert report["summary"]["matched_count"] == 1
        assert report["summary"]["orphaned_count"] == 1
        assert report["orphaned"][0]["method"] == "DELETE"

    def test_frontend_only_call(self):
        be = _make_be_report([("GET", "", "/api/tasks", "list_tasks", "Read")])
        fe = _make_fe_report([
            ("GET", "/api/tasks", "taskService.ts"),
            ("POST", "/api/unknown", "misc.ts"),
        ])
        report = map_completeness(be, fe)
        assert report["summary"]["frontend_only_count"] == 1
        assert report["frontend_only"][0]["endpoint"] == "/api/unknown"

    def test_param_style_matching(self):
        """FastAPI {id} should match frontend :id."""
        be = _make_be_report([("GET", "/{task_id}", "/api/tasks/{task_id}", "get_task", "Read")])
        fe = _make_fe_report([("GET", "/api/tasks/:taskId", "taskService.ts")])
        report = map_completeness(be, fe)
        assert report["summary"]["matched_count"] == 1
        assert report["summary"]["orphaned_count"] == 0

    def test_empty_reports(self):
        be = _make_be_report([])
        fe = _make_fe_report([])
        report = map_completeness(be, fe)
        assert report["completeness"] == 0.0
        assert report["summary"]["total_backend_endpoints"] == 0

    def test_constant_endpoints_skipped(self):
        """Frontend calls using API_ENDPOINTS.X.Y constants are skipped."""
        be = _make_be_report([("GET", "", "/api/tasks", "list_tasks", "Read")])
        fe = _make_fe_report([("GET", "API_ENDPOINTS.TASKS.BASE", "taskService.ts")])
        report = map_completeness(be, fe)
        assert report["summary"]["matched_count"] == 0
        assert report["summary"]["frontend_only_count"] == 0

    def test_report_structure(self):
        report = map_completeness(_make_be_report([]), _make_fe_report([]))
        assert "matched" in report
        assert "orphaned" in report
        assert "frontend_only" in report
        assert "completeness" in report
        assert "summary" in report

    def test_completeness_percentage(self):
        be = _make_be_report([
            ("GET", "", "/api/a", "a", "Read"),
            ("GET", "", "/api/b", "b", "Read"),
            ("GET", "", "/api/c", "c", "Read"),
            ("GET", "", "/api/d", "d", "Read"),
        ])
        fe = _make_fe_report([
            ("GET", "/api/a", "s.ts"),
            ("GET", "/api/b", "s.ts"),
            ("GET", "/api/c", "s.ts"),
        ])
        report = map_completeness(be, fe)
        assert report["completeness"] == 75.0


# ---------------------------------------------------------------------------
# Integration test against actual project
# ---------------------------------------------------------------------------

class TestMapCompletenessIntegration:
    def test_runs_against_project(self):
        report = map_completeness()
        s = report["summary"]
        assert s["total_backend_endpoints"] > 0
        assert s["matched_count"] + s["orphaned_count"] == s["total_backend_endpoints"]
        assert 0.0 <= report["completeness"] <= 100.0
