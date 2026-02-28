"""
Completeness reporting module for backend-frontend validation.

Generates completeness reports mapping backend endpoints to frontend
UI components, identifies gaps, provides recommendations, and
calculates completeness percentages.

Usage:
    from tests.completeness_reporting import (
        generate_completeness_report,
        export_report_json,
    )

Requirements: 16.2, 16.4, 16.5, 16.6, 16.7
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

from tests.completeness_mapping import map_completeness


# ---------------------------------------------------------------------------
# Data models (from design doc)
# ---------------------------------------------------------------------------

@dataclass
class OperationCoverage:
    """Coverage stats for a single CRUD operation type."""
    total: int = 0
    with_ui: int = 0
    without_ui: int = 0
    missing: list = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        if self.total == 0:
            return 100.0
        return round(self.with_ui / self.total * 100, 1)


@dataclass
class CRUDCompletenessReport:
    """CRUD operation coverage breakdown."""
    create_operations: OperationCoverage = field(default_factory=OperationCoverage)
    read_operations: OperationCoverage = field(default_factory=OperationCoverage)
    update_operations: OperationCoverage = field(default_factory=OperationCoverage)
    delete_operations: OperationCoverage = field(default_factory=OperationCoverage)


@dataclass
class MissingUIRecommendation:
    """Recommendation for a backend endpoint missing frontend UI."""
    method: str
    endpoint: str
    category: str
    recommendation: str
    priority: str  # high, medium, low


@dataclass
class CompletenessReport:
    """Top-level completeness report."""
    total_endpoints: int = 0
    endpoints_with_ui: int = 0
    endpoints_without_ui: int = 0
    completeness_pct: float = 0.0
    missing_ui_endpoints: list = field(default_factory=list)
    crud_completeness: CRUDCompletenessReport = field(
        default_factory=CRUDCompletenessReport,
    )
    recommendations: list = field(default_factory=list)
    completeness_matrix: list = field(default_factory=list)
    generated_at: str = ""


# ---------------------------------------------------------------------------
# Category → CRUD mapping
# ---------------------------------------------------------------------------

_CATEGORY_TO_CRUD = {
    "Create": "create_operations",
    "Read": "read_operations",
    "Update": "update_operations",
    "Delete": "delete_operations",
}


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------

_PRIORITY_BY_CATEGORY = {
    "Create": "high",
    "Read": "high",
    "Update": "medium",
    "Delete": "medium",
    "Business": "high",
}

_RECOMMENDATION_TEMPLATES = {
    "Create": "Add a creation form or dialog for {endpoint}",
    "Read": "Add a list/detail view for {endpoint}",
    "Update": "Add an edit form or inline editing for {endpoint}",
    "Delete": "Add a delete confirmation dialog for {endpoint}",
    "Business": "Add a UI action or page for {endpoint}",
}


def _build_recommendation(orphan: dict) -> MissingUIRecommendation:
    """Build a recommendation for a single orphaned endpoint."""
    category = orphan.get("category", "Business")
    endpoint = orphan.get("backend_path", "")
    template = _RECOMMENDATION_TEMPLATES.get(category, _RECOMMENDATION_TEMPLATES["Business"])

    return MissingUIRecommendation(
        method=orphan.get("method", ""),
        endpoint=endpoint,
        category=category,
        recommendation=template.format(endpoint=endpoint),
        priority=_PRIORITY_BY_CATEGORY.get(category, "low"),
    )


# ---------------------------------------------------------------------------
# CRUD completeness calculation
# ---------------------------------------------------------------------------

def _build_crud_report(
    matched: list[dict],
    orphaned: list[dict],
) -> CRUDCompletenessReport:
    """Calculate CRUD coverage from matched and orphaned endpoints."""
    crud = CRUDCompletenessReport()

    for ep in matched:
        attr = _CATEGORY_TO_CRUD.get(ep.get("category", ""))
        if attr is None:
            continue
        op: OperationCoverage = getattr(crud, attr)
        op.total += 1
        op.with_ui += 1

    for ep in orphaned:
        attr = _CATEGORY_TO_CRUD.get(ep.get("category", ""))
        if attr is None:
            continue
        op = getattr(crud, attr)
        op.total += 1
        op.without_ui += 1
        op.missing.append(ep.get("backend_path", ep.get("endpoint", "")))

    return crud


# ---------------------------------------------------------------------------
# Completeness matrix
# ---------------------------------------------------------------------------

def _build_matrix(matched: list[dict], orphaned: list[dict]) -> list[dict]:
    """Build a completeness matrix: one row per backend endpoint."""
    matrix: list[dict] = []

    for ep in matched:
        matrix.append({
            "method": ep["method"],
            "endpoint": ep["backend_path"],
            "category": ep["category"],
            "has_ui": True,
            "frontend_sources": ep.get("frontend_sources", []),
        })

    for ep in orphaned:
        matrix.append({
            "method": ep["method"],
            "endpoint": ep["backend_path"],
            "category": ep["category"],
            "has_ui": False,
            "frontend_sources": [],
        })

    return matrix


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_completeness_report(
    mapping_report: dict | None = None,
) -> CompletenessReport:
    """
    Generate a completeness report from a mapping report.

    If *mapping_report* is None, runs map_completeness() automatically.
    """
    if mapping_report is None:
        mapping_report = map_completeness()

    matched = mapping_report.get("matched", [])
    orphaned = mapping_report.get("orphaned", [])
    summary = mapping_report.get("summary", {})

    total = summary.get("total_backend_endpoints", 0)
    with_ui = summary.get("matched_count", 0)
    without_ui = summary.get("orphaned_count", 0)
    pct = summary.get("completeness_pct", 0.0)

    crud = _build_crud_report(matched, orphaned)
    recommendations = [_build_recommendation(o) for o in orphaned]
    matrix = _build_matrix(matched, orphaned)

    return CompletenessReport(
        total_endpoints=total,
        endpoints_with_ui=with_ui,
        endpoints_without_ui=without_ui,
        completeness_pct=pct,
        missing_ui_endpoints=orphaned,
        crud_completeness=crud,
        recommendations=recommendations,
        completeness_matrix=matrix,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def _serialise(obj: Any) -> Any:
    """Custom serialiser for dataclass / datetime fields."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return str(obj)


def export_report_json(report: CompletenessReport) -> str:
    """Export a CompletenessReport as a JSON string."""
    data = asdict(report)

    # Inject computed coverage percentages
    for op_key in ("create_operations", "read_operations",
                   "update_operations", "delete_operations"):
        op_cov = getattr(report.crud_completeness, op_key)
        data["crud_completeness"][op_key]["coverage_pct"] = op_cov.coverage_pct

    return json.dumps(data, indent=2, default=_serialise)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    report = generate_completeness_report()
    print(export_report_json(report))
    print(f"\n=== Completeness Report ===")
    print(f"Total endpoints    : {report.total_endpoints}")
    print(f"With UI            : {report.endpoints_with_ui}")
    print(f"Without UI         : {report.endpoints_without_ui}")
    print(f"Completeness       : {report.completeness_pct}%")
    print(f"Recommendations    : {len(report.recommendations)}")
