"""
Endpoint-to-UI completeness mapping for SuperInsight platform.

Maps backend endpoints to frontend API calls, identifying:
- Matched endpoints (backend + frontend coverage)
- Orphaned backend endpoints (no frontend UI)
- Frontend-only calls (no matching backend endpoint)
- Completeness percentage

Usage:
    python3 -m tests.completeness_mapping
    # or
    from tests.completeness_mapping import map_completeness
    report = map_completeness()
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from tests.endpoint_discovery import discover_endpoints
from tests.frontend_discovery import discover_frontend_components


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------

# FastAPI uses {param}, React/TS often uses :param
_FASTAPI_PARAM = re.compile(r"\{[^}]+\}")
_COLON_PARAM = re.compile(r":[a-zA-Z_]\w*")
_TRAILING_SLASH = re.compile(r"/+$")


def normalize_path(path: str) -> str:
    """Normalise an endpoint path for comparison.

    - Replace {id} and :id style params with a common placeholder
    - Strip trailing slashes
    - Lower-case the path
    """
    result = _FASTAPI_PARAM.sub(":param", path)
    result = _COLON_PARAM.sub(":param", result)
    result = _TRAILING_SLASH.sub("", result)
    return result.lower()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MappedEndpoint:
    """A backend endpoint matched to one or more frontend calls."""
    method: str
    backend_path: str
    handler: str
    category: str
    frontend_sources: list = field(default_factory=list)


@dataclass
class OrphanedEndpoint:
    """A backend endpoint with no frontend API call."""
    method: str
    backend_path: str
    handler: str
    category: str
    source_file: str


@dataclass
class FrontendOnlyCall:
    """A frontend API call with no matching backend endpoint."""
    method: str
    endpoint: str
    source_file: str


# ---------------------------------------------------------------------------
# Core mapping logic
# ---------------------------------------------------------------------------

def _collect_frontend_calls(fe_report: dict) -> list[dict]:
    """Flatten all frontend API calls into a single list of dicts."""
    calls: list[dict] = []
    for c in fe_report.get("service_api_calls", []):
        calls.append(c)
    for file_calls in fe_report.get("component_api_calls", {}).values():
        calls.extend(file_calls)
    return calls


def _build_frontend_index(fe_calls: list[dict]) -> dict[str, list[dict]]:
    """Build a lookup: (METHOD, normalised_path) → [call dicts]."""
    index: dict[str, list[dict]] = {}
    for call in fe_calls:
        method = call.get("method", "").upper()
        endpoint = call.get("endpoint", "")
        # Skip constant references like API_ENDPOINTS.TASKS.BASE
        if not endpoint.startswith("/"):
            continue
        key = f"{method}:{normalize_path(endpoint)}"
        index.setdefault(key, []).append(call)
    return index


def map_completeness(
    be_report: Optional[dict] = None,
    fe_report: Optional[dict] = None,
) -> dict:
    """
    Map backend endpoints to frontend API calls.

    Parameters can be pre-computed reports or None (auto-discovered).

    Returns dict with:
        matched        – endpoints with frontend coverage
        orphaned       – backend endpoints without frontend calls
        frontend_only  – frontend calls without backend endpoints
        completeness   – percentage of backend endpoints with UI
        summary        – aggregate counts
    """
    if be_report is None:
        be_report = discover_endpoints()
    if fe_report is None:
        fe_report = discover_frontend_components()

    fe_calls = _collect_frontend_calls(fe_report)
    fe_index = _build_frontend_index(fe_calls)

    matched: list[dict] = []
    orphaned: list[dict] = []
    used_fe_keys: set[str] = set()

    for ep in be_report.get("endpoints", []):
        method = ep["method"]
        norm = normalize_path(ep["full_path"])
        key = f"{method}:{norm}"

        if key in fe_index:
            sources = [c["source_file"] for c in fe_index[key]]
            matched.append(asdict(MappedEndpoint(
                method=method,
                backend_path=ep["full_path"],
                handler=ep["handler"],
                category=ep["category"],
                frontend_sources=sources,
            )))
            used_fe_keys.add(key)
        else:
            orphaned.append(asdict(OrphanedEndpoint(
                method=method,
                backend_path=ep["full_path"],
                handler=ep["handler"],
                category=ep["category"],
                source_file=ep["source_file"],
            )))

    # Frontend-only: calls whose key was never matched
    frontend_only: list[dict] = []
    for call in fe_calls:
        endpoint = call.get("endpoint", "")
        if not endpoint.startswith("/"):
            continue
        key = f"{call['method']}:{normalize_path(endpoint)}"
        if key not in used_fe_keys:
            # Avoid duplicates
            used_fe_keys.add(key)
            frontend_only.append(asdict(FrontendOnlyCall(
                method=call["method"],
                endpoint=endpoint,
                source_file=call["source_file"],
            )))

    total_be = len(be_report.get("endpoints", []))
    completeness = (len(matched) / total_be * 100) if total_be else 0.0

    return {
        "matched": matched,
        "orphaned": orphaned,
        "frontend_only": frontend_only,
        "completeness": round(completeness, 1),
        "summary": {
            "total_backend_endpoints": total_be,
            "matched_count": len(matched),
            "orphaned_count": len(orphaned),
            "frontend_only_count": len(frontend_only),
            "completeness_pct": round(completeness, 1),
        },
    }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    report = map_completeness()
    print(json.dumps(report, indent=2, default=str))
    s = report["summary"]
    print(f"\n=== Completeness Summary ===")
    print(f"Backend endpoints : {s['total_backend_endpoints']}")
    print(f"Matched (with UI) : {s['matched_count']}")
    print(f"Orphaned (no UI)  : {s['orphaned_count']}")
    print(f"Frontend-only     : {s['frontend_only_count']}")
    print(f"Completeness      : {s['completeness_pct']}%")
