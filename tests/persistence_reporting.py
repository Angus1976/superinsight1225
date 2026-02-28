"""
Persistence validation reporting module.

Generates reports on frontend-to-database data persistence,
tracking success rates per form, identifying failing fields,
and recording data integrity violations.

Usage:
    from tests.persistence_reporting import (
        PersistenceReport, PersistenceFailure,
        validate_persistence, generate_persistence_report,
    )

Requirements: 15.3, 15.4, 15.7
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PersistenceFailure:
    """A single field that failed to persist correctly."""
    form_id: str
    field_name: str
    submitted_value: Any
    stored_value: Any
    error_message: str


@dataclass
class FormResult:
    """Aggregated persistence result for one form."""
    form_id: str
    total_fields: int = 0
    passed_fields: int = 0
    failed_fields: int = 0
    failures: list = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_fields == 0:
            return 0.0
        return self.passed_fields / self.total_fields


@dataclass
class PersistenceReport:
    """Top-level persistence validation report."""
    total_forms: int = 0
    tested_forms: int = 0
    successful_persistence: int = 0
    failed_persistence: int = 0
    failures: list = field(default_factory=list)
    form_results: list = field(default_factory=list)
    generated_at: str = ""

    @property
    def overall_success_rate(self) -> float:
        if self.tested_forms == 0:
            return 0.0
        return self.successful_persistence / self.tested_forms


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def compare_values(submitted: Any, stored: Any) -> Optional[str]:
    """Compare submitted vs stored value, return error message or None."""
    if submitted is None and stored is None:
        return None

    if submitted is None or stored is None:
        return f"value mismatch: submitted={submitted!r}, stored={stored!r}"

    # Normalize types for comparison
    if isinstance(submitted, (int, float)) and isinstance(stored, (int, float)):
        if abs(float(submitted) - float(stored)) < 1e-9:
            return None
        return f"numeric mismatch: submitted={submitted}, stored={stored}"

    if str(submitted) == str(stored):
        return None

    return f"value mismatch: submitted={submitted!r}, stored={stored!r}"


def validate_persistence(
    form_id: str,
    submitted_data: dict[str, Any],
    stored_data: dict[str, Any],
) -> FormResult:
    """
    Validate that submitted data matches stored data for a single form.

    Returns a FormResult with per-field pass/fail details.
    """
    if not isinstance(submitted_data, dict):
        return FormResult(form_id=form_id)
    if not isinstance(stored_data, dict):
        return FormResult(form_id=form_id)

    result = FormResult(form_id=form_id)
    result.total_fields = len(submitted_data)

    for field_name, submitted_value in submitted_data.items():
        stored_value = stored_data.get(field_name)
        error = compare_values(submitted_value, stored_value)

        if error is None:
            result.passed_fields += 1
        else:
            result.failed_fields += 1
            result.failures.append(PersistenceFailure(
                form_id=form_id,
                field_name=field_name,
                submitted_value=submitted_value,
                stored_value=stored_value,
                error_message=error,
            ))

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_persistence_report(
    form_results: list[FormResult],
    total_forms: int | None = None,
) -> PersistenceReport:
    """
    Build a PersistenceReport from a list of per-form results.

    Args:
        form_results: validated FormResult objects.
        total_forms: total number of forms in the system (defaults to
                     len(form_results) if not provided).
    """
    if total_forms is None:
        total_forms = len(form_results)

    all_failures: list[PersistenceFailure] = []
    successful = 0
    failed = 0

    for fr in form_results:
        if fr.failed_fields == 0:
            successful += 1
        else:
            failed += 1
            all_failures.extend(fr.failures)

    return PersistenceReport(
        total_forms=total_forms,
        tested_forms=len(form_results),
        successful_persistence=successful,
        failed_persistence=failed,
        failures=all_failures,
        form_results=form_results,
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


def export_report_json(report: PersistenceReport) -> str:
    """Export a PersistenceReport as a JSON string."""
    data = asdict(report)
    # Inject computed properties
    data["overall_success_rate"] = report.overall_success_rate
    for i, fr in enumerate(report.form_results):
        data["form_results"][i]["success_rate"] = fr.success_rate
    return json.dumps(data, indent=2, default=_serialise)
