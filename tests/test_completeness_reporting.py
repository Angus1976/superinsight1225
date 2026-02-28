"""Tests for the completeness reporting module.

Validates:
- Property 43: Backend-Frontend Completeness Mapping
- Property 44: Completeness Report Generation
- Requirements: 16.2, 16.4, 16.5, 16.6, 16.7
"""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.completeness_reporting import (
    CompletenessReport,
    CRUDCompletenessReport,
    MissingUIRecommendation,
    OperationCoverage,
    export_report_json,
    generate_completeness_report,
    _build_crud_report,
    _build_matrix,
    _build_recommendation,
)


# ---------------------------------------------------------------------------
# Helpers – synthetic mapping reports
# ---------------------------------------------------------------------------

CATEGORIES = ("Create", "Read", "Update", "Delete", "Business")


def _make_mapping_report(
    matched=None,
    orphaned=None,
    frontend_only=None,
):
    """Build a synthetic mapping report for testing."""
    matched = matched or []
    orphaned = orphaned or []
    frontend_only = frontend_only or []
    total = len(matched) + len(orphaned)
    pct = round(len(matched) / total * 100, 1) if total else 0.0
    return {
        "matched": matched,
        "orphaned": orphaned,
        "frontend_only": frontend_only,
        "completeness": pct,
        "summary": {
            "total_backend_endpoints": total,
            "matched_count": len(matched),
            "orphaned_count": len(orphaned),
            "frontend_only_count": len(frontend_only),
            "completeness_pct": pct,
        },
    }


def _ep(method: str, path: str, category: str, *, matched: bool = True) -> dict:
    """Build a single endpoint dict for matched or orphaned lists."""
    base = {
        "method": method,
        "backend_path": path,
        "handler": "handler",
        "category": category,
    }
    if matched:
        base["frontend_sources"] = ["service.ts"]
    else:
        base["source_file"] = "router.py"
    return base


# ---------------------------------------------------------------------------
# Unit tests – OperationCoverage
# ---------------------------------------------------------------------------

class TestOperationCoverage:
    def test_coverage_pct_full(self):
        oc = OperationCoverage(total=5, with_ui=5)
        assert oc.coverage_pct == 100.0

    def test_coverage_pct_partial(self):
        oc = OperationCoverage(total=4, with_ui=3)
        assert oc.coverage_pct == 75.0

    def test_coverage_pct_zero_total(self):
        oc = OperationCoverage(total=0, with_ui=0)
        assert oc.coverage_pct == 100.0

    def test_coverage_pct_none_covered(self):
        oc = OperationCoverage(total=3, with_ui=0)
        assert oc.coverage_pct == 0.0


# ---------------------------------------------------------------------------
# Unit tests – _build_recommendation
# ---------------------------------------------------------------------------

class TestBuildRecommendation:
    def test_create_recommendation(self):
        rec = _build_recommendation(_ep("POST", "/api/tasks", "Create", matched=False))
        assert "creation form" in rec.recommendation.lower() or "form" in rec.recommendation.lower()
        assert rec.priority == "high"

    def test_read_recommendation(self):
        rec = _build_recommendation(_ep("GET", "/api/tasks", "Read", matched=False))
        assert "list" in rec.recommendation.lower() or "view" in rec.recommendation.lower()

    def test_delete_recommendation(self):
        rec = _build_recommendation(_ep("DELETE", "/api/tasks/{id}", "Delete", matched=False))
        assert "delete" in rec.recommendation.lower()
        assert rec.priority == "medium"

    def test_business_recommendation(self):
        rec = _build_recommendation(_ep("POST", "/api/sync", "Business", matched=False))
        assert rec.category == "Business"
        assert rec.priority == "high"


# ---------------------------------------------------------------------------
# Unit tests – _build_crud_report
# ---------------------------------------------------------------------------

class TestBuildCrudReport:
    def test_all_matched(self):
        matched = [
            _ep("POST", "/api/tasks", "Create"),
            _ep("GET", "/api/tasks", "Read"),
            _ep("PUT", "/api/tasks/{id}", "Update"),
            _ep("DELETE", "/api/tasks/{id}", "Delete"),
        ]
        crud = _build_crud_report(matched, [])
        assert crud.create_operations.with_ui == 1
        assert crud.read_operations.with_ui == 1
        assert crud.update_operations.with_ui == 1
        assert crud.delete_operations.with_ui == 1

    def test_all_orphaned(self):
        orphaned = [
            _ep("POST", "/api/tasks", "Create", matched=False),
            _ep("GET", "/api/tasks", "Read", matched=False),
        ]
        crud = _build_crud_report([], orphaned)
        assert crud.create_operations.without_ui == 1
        assert crud.read_operations.without_ui == 1
        assert len(crud.create_operations.missing) == 1

    def test_business_category_skipped(self):
        matched = [_ep("POST", "/api/sync", "Business")]
        crud = _build_crud_report(matched, [])
        # Business endpoints don't map to CRUD
        assert crud.create_operations.total == 0

    def test_empty_inputs(self):
        crud = _build_crud_report([], [])
        assert crud.create_operations.total == 0
        assert crud.read_operations.total == 0


# ---------------------------------------------------------------------------
# Unit tests – _build_matrix
# ---------------------------------------------------------------------------

class TestBuildMatrix:
    def test_matrix_includes_all_endpoints(self):
        matched = [_ep("GET", "/api/a", "Read")]
        orphaned = [_ep("POST", "/api/b", "Create", matched=False)]
        matrix = _build_matrix(matched, orphaned)
        assert len(matrix) == 2
        assert matrix[0]["has_ui"] is True
        assert matrix[1]["has_ui"] is False

    def test_empty_matrix(self):
        assert _build_matrix([], []) == []


# ---------------------------------------------------------------------------
# Unit tests – generate_completeness_report
# ---------------------------------------------------------------------------

class TestGenerateCompletenessReport:
    def test_full_coverage(self):
        mapping = _make_mapping_report(
            matched=[_ep("GET", "/api/tasks", "Read")],
        )
        report = generate_completeness_report(mapping)
        assert report.total_endpoints == 1
        assert report.endpoints_with_ui == 1
        assert report.endpoints_without_ui == 0
        assert report.completeness_pct == 100.0
        assert len(report.recommendations) == 0

    def test_no_coverage(self):
        mapping = _make_mapping_report(
            orphaned=[_ep("GET", "/api/tasks", "Read", matched=False)],
        )
        report = generate_completeness_report(mapping)
        assert report.total_endpoints == 1
        assert report.endpoints_with_ui == 0
        assert report.endpoints_without_ui == 1
        assert report.completeness_pct == 0.0
        assert len(report.recommendations) == 1

    def test_partial_coverage(self):
        mapping = _make_mapping_report(
            matched=[_ep("GET", "/api/a", "Read")],
            orphaned=[_ep("POST", "/api/b", "Create", matched=False)],
        )
        report = generate_completeness_report(mapping)
        assert report.completeness_pct == 50.0
        assert len(report.completeness_matrix) == 2

    def test_empty_report(self):
        mapping = _make_mapping_report()
        report = generate_completeness_report(mapping)
        assert report.total_endpoints == 0
        assert report.completeness_pct == 0.0
        assert report.generated_at != ""

    def test_generated_at_populated(self):
        mapping = _make_mapping_report()
        report = generate_completeness_report(mapping)
        assert len(report.generated_at) > 0

    def test_crud_completeness_populated(self):
        mapping = _make_mapping_report(
            matched=[_ep("POST", "/api/tasks", "Create")],
            orphaned=[_ep("DELETE", "/api/tasks/{id}", "Delete", matched=False)],
        )
        report = generate_completeness_report(mapping)
        assert report.crud_completeness.create_operations.with_ui == 1
        assert report.crud_completeness.delete_operations.without_ui == 1


# ---------------------------------------------------------------------------
# Unit tests – export_report_json
# ---------------------------------------------------------------------------

class TestExportReportJson:
    def test_valid_json(self):
        mapping = _make_mapping_report(
            matched=[_ep("GET", "/api/tasks", "Read")],
        )
        report = generate_completeness_report(mapping)
        raw = export_report_json(report)
        data = json.loads(raw)
        assert data["total_endpoints"] == 1
        assert "crud_completeness" in data

    def test_crud_coverage_pct_in_json(self):
        mapping = _make_mapping_report(
            matched=[_ep("GET", "/api/a", "Read")],
            orphaned=[_ep("GET", "/api/b", "Read", matched=False)],
        )
        report = generate_completeness_report(mapping)
        data = json.loads(export_report_json(report))
        assert "coverage_pct" in data["crud_completeness"]["read_operations"]
        assert data["crud_completeness"]["read_operations"]["coverage_pct"] == 50.0

    def test_recommendations_in_json(self):
        mapping = _make_mapping_report(
            orphaned=[_ep("POST", "/api/x", "Create", matched=False)],
        )
        report = generate_completeness_report(mapping)
        data = json.loads(export_report_json(report))
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["priority"] == "high"


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_methods = st.sampled_from(["GET", "POST", "PUT", "PATCH", "DELETE"])
_categories = st.sampled_from(["Create", "Read", "Update", "Delete", "Business"])
_paths = st.from_regex(r"/api/[a-z]{1,10}(/[a-z]{1,10}){0,2}", fullmatch=True)


def _matched_ep_st():
    return st.fixed_dictionaries({
        "method": _methods,
        "backend_path": _paths,
        "handler": st.just("handler"),
        "category": _categories,
        "frontend_sources": st.just(["service.ts"]),
    })


def _orphaned_ep_st():
    return st.fixed_dictionaries({
        "method": _methods,
        "backend_path": _paths,
        "handler": st.just("handler"),
        "category": _categories,
        "source_file": st.just("router.py"),
    })


def _mapping_report_st():
    """Strategy that generates a valid mapping report."""
    return st.fixed_dictionaries({
        "matched": st.lists(_matched_ep_st(), min_size=0, max_size=10),
        "orphaned": st.lists(_orphaned_ep_st(), min_size=0, max_size=10),
    }).map(lambda d: _make_mapping_report(
        matched=d["matched"],
        orphaned=d["orphaned"],
    ))


# ---------------------------------------------------------------------------
# Property 43: Backend-Frontend Completeness Mapping
# **Validates: Requirements 16.2, 16.4, 16.5, 16.6**
# ---------------------------------------------------------------------------

class TestProperty43CompletenessMapping:
    """
    Property 43: For any backend API endpoint or functional operation,
    there SHALL exist a corresponding frontend UI component that provides
    access to that operation, including all CRUD operations and business
    logic operations.

    **Validates: Requirements 16.2, 16.4, 16.5, 16.6**
    """

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_every_endpoint_classified(self, mapping):
        """Every backend endpoint appears in either matched or orphaned."""
        report = generate_completeness_report(mapping)
        total = len(mapping["matched"]) + len(mapping["orphaned"])
        assert report.total_endpoints == total

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_matched_plus_orphaned_equals_total(self, mapping):
        """with_ui + without_ui == total_endpoints."""
        report = generate_completeness_report(mapping)
        assert report.endpoints_with_ui + report.endpoints_without_ui == report.total_endpoints

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_crud_operations_accounted(self, mapping):
        """All CRUD-category endpoints appear in the CRUD report."""
        report = generate_completeness_report(mapping)
        crud = report.crud_completeness
        crud_total = (
            crud.create_operations.total
            + crud.read_operations.total
            + crud.update_operations.total
            + crud.delete_operations.total
        )
        # Count non-Business endpoints
        all_eps = mapping["matched"] + mapping["orphaned"]
        expected = sum(1 for e in all_eps if e["category"] != "Business")
        assert crud_total == expected

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_missing_endpoints_get_recommendations(self, mapping):
        """Every orphaned endpoint gets a recommendation."""
        report = generate_completeness_report(mapping)
        assert len(report.recommendations) == len(mapping["orphaned"])


# ---------------------------------------------------------------------------
# Property 44: Completeness Report Generation
# **Validates: Requirements 16.7**
# ---------------------------------------------------------------------------

class TestProperty44ReportGeneration:
    """
    Property 44: For any backend-frontend completeness check execution,
    a completeness report SHALL be generated that maps backend operations
    to frontend UI components and identifies any gaps.

    **Validates: Requirements 16.7**
    """

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_report_always_generated(self, mapping):
        """A report is always produced regardless of input."""
        report = generate_completeness_report(mapping)
        assert isinstance(report, CompletenessReport)
        assert report.generated_at != ""

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_matrix_covers_all_endpoints(self, mapping):
        """Completeness matrix has one row per backend endpoint."""
        report = generate_completeness_report(mapping)
        total = len(mapping["matched"]) + len(mapping["orphaned"])
        assert len(report.completeness_matrix) == total

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_gaps_identified_in_matrix(self, mapping):
        """Orphaned endpoints are marked has_ui=False in the matrix."""
        report = generate_completeness_report(mapping)
        no_ui = [r for r in report.completeness_matrix if not r["has_ui"]]
        assert len(no_ui) == len(mapping["orphaned"])

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_json_export_roundtrip(self, mapping):
        """Report can be exported to JSON and parsed back."""
        report = generate_completeness_report(mapping)
        raw = export_report_json(report)
        data = json.loads(raw)
        assert data["total_endpoints"] == report.total_endpoints
        assert data["endpoints_with_ui"] == report.endpoints_with_ui
        assert data["endpoints_without_ui"] == report.endpoints_without_ui

    @given(mapping=_mapping_report_st())
    @settings(max_examples=100)
    def test_completeness_pct_bounded(self, mapping):
        """Completeness percentage is always between 0 and 100."""
        report = generate_completeness_report(mapping)
        assert 0.0 <= report.completeness_pct <= 100.0


# ---------------------------------------------------------------------------
# Integration test against actual project
# ---------------------------------------------------------------------------

class TestCompletenessReportingIntegration:
    def test_runs_against_project(self):
        """Generate a report from the actual project sources."""
        report = generate_completeness_report()
        assert isinstance(report, CompletenessReport)
        assert report.generated_at != ""
        assert report.total_endpoints >= 0
        # JSON export works
        raw = export_report_json(report)
        data = json.loads(raw)
        assert data["total_endpoints"] == report.total_endpoints
