"""
Frontend component discovery system for SuperInsight platform.

Statically analyzes React/TypeScript frontend source to:
- Extract API calls from components and service files
- Parse route definitions from the router
- Map UI components to API endpoints
- Identify navigation paths

Usage:
    python3 -m tests.frontend_discovery
    # or
    from tests.frontend_discovery import discover_frontend_components
    report = discover_frontend_components()
"""

import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRONTEND_SRC = os.path.join("frontend", "src")

# API call patterns: apiClient.get/post/put/patch/delete or api.get etc.
API_CALL_PATTERN = re.compile(
    r'(?:apiClient|api|optimizedApiClient)\.(get|post|put|patch|delete)\s*(?:<[^>]*>)?\s*\(\s*'
    r"""(?:['"`]([^'"`]+)['"`]|([A-Z_]+(?:\.[A-Z_]+)+)(?:\([^)]*\))?)""",
    re.IGNORECASE,
)

# fetch() calls with method
FETCH_PATTERN = re.compile(
    r"""fetch\(\s*['"`]([^'"`]+)['"`]""",
)

# Route path pattern: path: 'something' or path: ROUTES.SOMETHING
ROUTE_PATH_PATTERN = re.compile(
    r"""path:\s*(?:['"]([^'"]+)['"]|ROUTES\.(\w+))""",
)

# Route element pattern: element: withSuspense(ComponentName) or <ComponentName />
ROUTE_ELEMENT_PATTERN = re.compile(
    r'element:\s*(?:withSuspense\((\w+)|withMinimalSuspense\((\w+)|<(\w+)\s)',
)

# Lazy import pattern: const XPage = lazyWithPreload(() => import('path'))
LAZY_IMPORT_PATTERN = re.compile(
    r"""const\s+(\w+)\s*=\s*lazyWithPreload\(\s*\(\)\s*=>\s*import\(\s*['"]([^'"]+)['"]\s*\)\s*\)""",
)

# API_ENDPOINTS constant references like API_ENDPOINTS.TASKS.BASE
API_CONST_PATTERN = re.compile(
    r'API_ENDPOINTS\.([A-Z_]+)\.([A-Z_]+)',
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ComponentInfo:
    """A discovered frontend component with its API calls."""
    component_name: str
    component_path: str
    api_calls: list = field(default_factory=list)
    route: Optional[str] = None


@dataclass
class RouteInfo:
    """A discovered frontend route."""
    path: str
    component_name: str
    import_path: str = ""


@dataclass
class ApiCallInfo:
    """A single API call found in source."""
    method: str
    endpoint: str
    source_file: str


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _read_file(filepath: str) -> str:
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def extract_api_calls(content: str, filename: str) -> list[ApiCallInfo]:
    """Extract API calls from a TypeScript/TSX file."""
    calls: list[ApiCallInfo] = []

    for match in API_CALL_PATTERN.finditer(content):
        method = match.group(1).upper()
        endpoint = match.group(2) or match.group(3) or ""
        if endpoint:
            calls.append(ApiCallInfo(method=method, endpoint=endpoint, source_file=filename))

    for match in FETCH_PATTERN.finditer(content):
        endpoint = match.group(1)
        if endpoint.startswith("/api") or endpoint.startswith("http"):
            calls.append(ApiCallInfo(method="GET", endpoint=endpoint, source_file=filename))

    return calls


def extract_routes(content: str) -> list[RouteInfo]:
    """Extract route definitions from a router file."""
    # Build lazy-import map: ComponentName -> import path
    import_map: dict[str, str] = {}
    for match in LAZY_IMPORT_PATTERN.finditer(content):
        import_map[match.group(1)] = match.group(2)

    routes: list[RouteInfo] = []
    # Find path + element pairs by scanning route objects
    path_matches = list(ROUTE_PATH_PATTERN.finditer(content))

    for pm in path_matches:
        path = pm.group(1) or pm.group(2) or ""
        # Look for the element in the nearby text (within 300 chars after path)
        after = content[pm.end():pm.end() + 300]
        elem_match = ROUTE_ELEMENT_PATTERN.search(after)
        component = ""
        if elem_match:
            component = elem_match.group(1) or elem_match.group(2) or elem_match.group(3) or ""

        if path and component:
            routes.append(RouteInfo(
                path=path,
                component_name=component,
                import_path=import_map.get(component, ""),
            ))

    return routes


# ---------------------------------------------------------------------------
# Discovery functions
# ---------------------------------------------------------------------------

def discover_service_api_calls(src_dir: str = FRONTEND_SRC) -> list[ApiCallInfo]:
    """Scan service files for API call patterns."""
    services_dir = os.path.join(src_dir, "services")
    if not os.path.isdir(services_dir):
        return []

    calls: list[ApiCallInfo] = []
    for root, _dirs, files in os.walk(services_dir):
        for fname in files:
            if not fname.endswith((".ts", ".tsx")):
                continue
            filepath = os.path.join(root, fname)
            content = _read_file(filepath)
            if not content:
                continue
            rel = os.path.relpath(filepath, src_dir)
            calls.extend(extract_api_calls(content, rel))
    return calls


def discover_component_api_calls(src_dir: str = FRONTEND_SRC) -> dict[str, list[ApiCallInfo]]:
    """Scan component/page/hook files for API calls, grouped by file."""
    scan_dirs = ["components", "pages", "hooks", "stores"]
    result: dict[str, list[ApiCallInfo]] = {}

    for subdir in scan_dirs:
        target = os.path.join(src_dir, subdir)
        if not os.path.isdir(target):
            continue
        for root, _dirs, files in os.walk(target):
            for fname in files:
                if not fname.endswith((".ts", ".tsx")):
                    continue
                filepath = os.path.join(root, fname)
                content = _read_file(filepath)
                if not content:
                    continue
                rel = os.path.relpath(filepath, src_dir)
                calls = extract_api_calls(content, rel)
                if calls:
                    result[rel] = calls
    return result


def discover_routes(src_dir: str = FRONTEND_SRC) -> list[RouteInfo]:
    """Parse the router files for route definitions."""
    router_dir = os.path.join(src_dir, "router")
    if not os.path.isdir(router_dir):
        return []

    all_routes: list[RouteInfo] = []
    for fname in sorted(os.listdir(router_dir)):
        if not fname.endswith((".ts", ".tsx")):
            continue
        filepath = os.path.join(router_dir, fname)
        content = _read_file(filepath)
        if content:
            all_routes.extend(extract_routes(content))
    return all_routes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_frontend_components(src_dir: str = FRONTEND_SRC) -> dict:
    """
    Run the full frontend component discovery pipeline.

    Returns dict with:
        service_api_calls  – API calls found in service files
        component_api_calls – API calls grouped by component file
        routes             – route definitions
        route_component_map – {route_path: component_name}
        summary            – aggregate counts
    """
    if not os.path.isdir(src_dir):
        return _empty_report()

    service_calls = discover_service_api_calls(src_dir)
    component_calls = discover_component_api_calls(src_dir)
    routes = discover_routes(src_dir)

    # Build route → component map
    route_map = {r.path: r.component_name for r in routes}

    # Collect all unique endpoints
    all_endpoints: set[str] = set()
    for c in service_calls:
        all_endpoints.add(c.endpoint)
    for calls in component_calls.values():
        for c in calls:
            all_endpoints.add(c.endpoint)

    # Method counts
    method_counts: dict[str, int] = {}
    for c in service_calls:
        method_counts[c.method] = method_counts.get(c.method, 0) + 1

    return {
        "service_api_calls": [asdict(c) for c in service_calls],
        "component_api_calls": {
            k: [asdict(c) for c in v] for k, v in component_calls.items()
        },
        "routes": [asdict(r) for r in routes],
        "route_component_map": route_map,
        "summary": {
            "total_service_api_calls": len(service_calls),
            "total_component_files_with_api_calls": len(component_calls),
            "total_routes": len(routes),
            "unique_endpoints": len(all_endpoints),
            "by_method": method_counts,
        },
    }


def _empty_report() -> dict:
    return {
        "service_api_calls": [],
        "component_api_calls": {},
        "routes": [],
        "route_component_map": {},
        "summary": {
            "total_service_api_calls": 0,
            "total_component_files_with_api_calls": 0,
            "total_routes": 0,
            "unique_endpoints": 0,
            "by_method": {},
        },
    }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    report = discover_frontend_components()
    print(json.dumps(report, indent=2, default=str))
    s = report["summary"]
    print(f"\n=== Summary ===")
    print(f"Service API calls          : {s['total_service_api_calls']}")
    print(f"Component files with calls : {s['total_component_files_with_api_calls']}")
    print(f"Routes                     : {s['total_routes']}")
    print(f"Unique endpoints           : {s['unique_endpoints']}")
    print(f"By method                  : {s['by_method']}")
