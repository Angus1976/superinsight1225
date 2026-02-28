"""
Backend endpoint discovery system for SuperInsight platform.

Statically analyzes FastAPI router source files in src/api/ to:
- Extract all endpoints (HTTP method + path + handler name)
- Resolve full paths using APIRouter prefix
- Categorize endpoints as CRUD or business-logic

Usage:
    python3 -m tests.endpoint_discovery
    # or
    from tests.endpoint_discovery import discover_endpoints
    report = discover_endpoints()
"""

import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_DIR = os.path.join("src", "api")

# Regex patterns
PREFIX_PATTERN = re.compile(
    r'APIRouter\(\s*prefix\s*=\s*["\']([^"\']+)["\']'
)
ROUTER_DECORATOR = re.compile(
    r'@router\.(get|post|put|patch|delete)\(\s*["\']([^"\']*)["\']'
)
HANDLER_AFTER_DECORATOR = re.compile(
    r'(?:async\s+)?def\s+(\w+)\s*\('
)

# CRUD categorisation rules (method → category)
METHOD_CATEGORY = {
    "GET": "Read",
    "POST": "Create",
    "PUT": "Update",
    "PATCH": "Update",
    "DELETE": "Delete",
}

# Path patterns that indicate business-logic rather than plain CRUD
BUSINESS_LOGIC_PATTERNS = [
    re.compile(r'/sync'),
    re.compile(r'/export'),
    re.compile(r'/import'),
    re.compile(r'/batch'),
    re.compile(r'/test-connection'),
    re.compile(r'/stats'),
    re.compile(r'/health'),
    re.compile(r'/metrics'),
    re.compile(r'/login'),
    re.compile(r'/logout'),
    re.compile(r'/register'),
    re.compile(r'/refresh'),
    re.compile(r'/verify'),
    re.compile(r'/scan'),
    re.compile(r'/trigger'),
    re.compile(r'/evaluate'),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EndpointInfo:
    """Single discovered endpoint."""
    method: str
    path: str
    full_path: str
    handler: str
    category: str  # Create / Read / Update / Delete / Business
    source_file: str


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _read_file(filepath: str) -> str:
    """Read file content safely, return empty string on failure."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def extract_prefix(content: str) -> str:
    """Extract APIRouter prefix from file content."""
    match = PREFIX_PATTERN.search(content)
    return match.group(1) if match else ""


def classify_endpoint(method: str, path: str) -> str:
    """Classify an endpoint as CRUD type or Business logic."""
    for pattern in BUSINESS_LOGIC_PATTERNS:
        if pattern.search(path):
            return "Business"
    return METHOD_CATEGORY.get(method.upper(), "Business")


def extract_endpoints(content: str, filename: str) -> list[EndpointInfo]:
    """Extract all router-decorated endpoints from a single file."""
    prefix = extract_prefix(content)
    endpoints: list[EndpointInfo] = []

    for match in ROUTER_DECORATOR.finditer(content):
        method = match.group(1).upper()
        path = match.group(2)
        full_path = prefix + path if not path.startswith(prefix) else path

        # Find the handler function name after the decorator
        after = content[match.end():]
        handler_match = HANDLER_AFTER_DECORATOR.search(after)
        handler = handler_match.group(1) if handler_match else "unknown"

        category = classify_endpoint(method, full_path)

        endpoints.append(EndpointInfo(
            method=method,
            path=path,
            full_path=full_path,
            handler=handler,
            category=category,
            source_file=filename,
        ))

    return endpoints


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_endpoints(api_dir: str = API_DIR) -> dict:
    """
    Scan all Python files in *api_dir* and return a structured report.

    Returns dict with keys:
        endpoints  – list of EndpointInfo dicts
        by_file    – {filename: [EndpointInfo dict, …]}
        by_category – {category: [EndpointInfo dict, …]}
        summary    – aggregate counts
    """
    if not os.path.isdir(api_dir):
        return _empty_report()

    all_endpoints: list[EndpointInfo] = []

    for fname in sorted(os.listdir(api_dir)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        filepath = os.path.join(api_dir, fname)
        content = _read_file(filepath)
        if not content:
            continue
        all_endpoints.extend(extract_endpoints(content, fname))

    return _build_report(all_endpoints)


def _empty_report() -> dict:
    return {
        "endpoints": [],
        "by_file": {},
        "by_category": {},
        "summary": {
            "total_endpoints": 0,
            "total_files": 0,
            "by_method": {},
            "by_category": {},
        },
    }


def _build_report(endpoints: list[EndpointInfo]) -> dict:
    by_file: dict[str, list[dict]] = {}
    by_category: dict[str, list[dict]] = {}
    method_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    endpoint_dicts = [asdict(ep) for ep in endpoints]

    for ep_dict in endpoint_dicts:
        # group by file
        fname = ep_dict["source_file"]
        by_file.setdefault(fname, []).append(ep_dict)

        # group by category
        cat = ep_dict["category"]
        by_category.setdefault(cat, []).append(ep_dict)

        # counts
        method_counts[ep_dict["method"]] = method_counts.get(ep_dict["method"], 0) + 1
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "endpoints": endpoint_dicts,
        "by_file": by_file,
        "by_category": by_category,
        "summary": {
            "total_endpoints": len(endpoint_dicts),
            "total_files": len(by_file),
            "by_method": method_counts,
            "by_category": category_counts,
        },
    }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    report = discover_endpoints()
    print(json.dumps(report, indent=2, default=str))
    s = report["summary"]
    print(f"\n=== Summary ===")
    print(f"Total endpoints : {s['total_endpoints']}")
    print(f"Total files     : {s['total_files']}")
    print(f"By method       : {s['by_method']}")
    print(f"By category     : {s['by_category']}")
