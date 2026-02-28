"""
Form discovery system for SuperInsight platform.

Statically analyzes React/TypeScript frontend source code to:
- Identify all Ant Design Form components
- Extract form fields, types, and validation rules
- Map forms to backend API endpoints
- Map API endpoints to database tables

Usage:
    python3 -m tests.form_discovery
    # or
    from tests.form_discovery import discover_all_forms
    report = discover_all_forms()
"""

import os
import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRONTEND_SRC = os.path.join("frontend", "src")
BACKEND_SRC = "src"

# Regex: match <Form (but NOT <Form.Item, <Form.List, etc.)
FORM_TAG_PATTERN = re.compile(
    r'<Form(?!\.\w)\b([^>]*?)>', re.DOTALL
)
FORM_NAME_ATTR = re.compile(r'\bname=["\'](\w+)["\']')

FORM_ITEM_PATTERN = re.compile(r'<Form\.Item\b([^>]*?)>', re.DOTALL)
FIELD_NAME_PATTERN = re.compile(r'\bname=["\'](\w+)["\']')

RULES_BLOCK_PATTERN = re.compile(
    r'\brules=\{?\[([^\]]*)\]\}?', re.DOTALL
)
REQUIRED_RULE = re.compile(r'\brequired:\s*true\b', re.IGNORECASE)
MIN_RULE = re.compile(r'\bmin:\s*(\d+)')
MAX_RULE = re.compile(r'\bmax:\s*(\d+)')
TYPE_RULE = re.compile(r"type:\s*['\"](\w+)['\"]")
PATTERN_RULE = re.compile(r'pattern:\s*/([^/]+)/')

# Input component type detection (order matters — most specific first)
INPUT_TYPE_DETECTORS = [
    (re.compile(r'<Input\.Password\b'), "password"),
    (re.compile(r'<DatePicker\b'), "date"),
    (re.compile(r'<Select\b'), "select"),
    (re.compile(r'<Checkbox\b'), "checkbox"),
    (re.compile(r'<InputNumber\b'), "number"),
    (re.compile(r'<TextArea\b'), "textarea"),
    (re.compile(r'<Upload\b'), "file"),
    (re.compile(r'<Input\b'), "text"),
]

# Backend patterns
ROUTER_DECORATOR = re.compile(
    r'@router\.(post|put|patch|delete|get)\(\s*["\']([^"\']+)["\']'
)
MODEL_CLASS = re.compile(r'class\s+(\w+Model)\(Base\):')
TABLENAME = re.compile(r'__tablename__\s*=\s*["\'](\w+)["\']')


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ValidationRule:
    rule_type: str
    value: Optional[str] = None


@dataclass
class FormField:
    field_name: str
    field_type: str = "text"
    required: bool = False
    validation_rules: list = field(default_factory=list)
    db_column: str = ""


@dataclass
class FormDefinition:
    form_id: str
    form_name: str
    component_file: str
    route: str = ""
    fields: list = field(default_factory=list)
    submit_endpoint: str = ""
    http_method: str = "POST"
    expected_table: str = ""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def read_file_safe(filepath: str) -> str:
    """Read file content, returning empty string on failure."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def extract_validation_rules(rules_text: str) -> list[ValidationRule]:
    """Parse Ant Design validation rules from a rules=[...] block."""
    rules: list[ValidationRule] = []

    if REQUIRED_RULE.search(rules_text):
        rules.append(ValidationRule("required", "true"))
    m = MIN_RULE.search(rules_text)
    if m:
        rules.append(ValidationRule("min", m.group(1)))
    m = MAX_RULE.search(rules_text)
    if m:
        rules.append(ValidationRule("max", m.group(1)))
    m = TYPE_RULE.search(rules_text)
    if m:
        rules.append(ValidationRule("type", m.group(1)))
    m = PATTERN_RULE.search(rules_text)
    if m:
        rules.append(ValidationRule("pattern", m.group(1)))
    if "validator" in rules_text:
        rules.append(ValidationRule("custom", "validator"))

    return rules


def detect_input_type(context: str) -> str:
    """Detect the Ant Design input component type from surrounding JSX."""
    for pattern, input_type in INPUT_TYPE_DETECTORS:
        if pattern.search(context):
            return input_type
    return "text"


def extract_form_fields(content: str) -> list[FormField]:
    """Extract all Form.Item fields from a React component file."""
    fields: list[FormField] = []
    items = list(FORM_ITEM_PATTERN.finditer(content))

    for i, item_match in enumerate(items):
        attrs = item_match.group(1)
        name_match = FIELD_NAME_PATTERN.search(attrs)
        if not name_match:
            continue

        field_name = name_match.group(1)

        # Context: text between this Form.Item and the next one
        start = item_match.end()
        end = items[i + 1].start() if i + 1 < len(items) else start + 500
        context = content[start:end]

        field_type = detect_input_type(context)

        # Extract validation rules from attrs or nearby context
        rules_match = RULES_BLOCK_PATTERN.search(attrs)
        if not rules_match:
            rules_match = RULES_BLOCK_PATTERN.search(context[:300])

        validation_rules: list[ValidationRule] = []
        if rules_match:
            validation_rules = extract_validation_rules(rules_match.group(1))

        required = any(r.rule_type == "required" for r in validation_rules)

        fields.append(FormField(
            field_name=field_name,
            field_type=field_type,
            required=required,
            validation_rules=[asdict(r) for r in validation_rules],
            db_column=field_name,
        ))

    return fields


# ---------------------------------------------------------------------------
# Form discovery
# ---------------------------------------------------------------------------

def find_form_files(src_dir: str) -> list[str]:
    """Recursively find .tsx files containing <Form and Form.Item."""
    form_files: list[str] = []
    for root, _dirs, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(".tsx"):
                continue
            filepath = os.path.join(root, fname)
            content = read_file_safe(filepath)
            if "<Form" in content and "Form.Item" in content:
                form_files.append(filepath)
    return sorted(form_files)


def parse_form_component(filepath: str) -> list[FormDefinition]:
    """Parse a React component file and extract one FormDefinition per <Form>."""
    content = read_file_safe(filepath)
    if not content:
        return []

    form_tags = list(FORM_TAG_PATTERN.finditer(content))
    if not form_tags:
        return []

    rel_path = os.path.relpath(filepath, FRONTEND_SRC)
    forms: list[FormDefinition] = []

    for tag_match in form_tags:
        attrs = tag_match.group(1)
        name_match = FORM_NAME_ATTR.search(attrs)
        form_name = name_match.group(1) if name_match else Path(filepath).stem

        fields = extract_form_fields(content)
        if not fields:
            continue

        # Deduplicate: skip if we already have this form_name from this file
        if any(f.form_id == form_name for f in forms):
            continue

        forms.append(FormDefinition(
            form_id=form_name,
            form_name=form_name,
            component_file=rel_path,
            fields=[asdict(f) for f in fields],
        ))

    return forms


def discover_frontend_forms() -> list[FormDefinition]:
    """Discover all forms in the frontend source tree."""
    form_files = find_form_files(FRONTEND_SRC)
    all_forms: list[FormDefinition] = []
    for filepath in form_files:
        all_forms.extend(parse_form_component(filepath))
    return all_forms


# ---------------------------------------------------------------------------
# Endpoint & table mapping
# ---------------------------------------------------------------------------

# Known mapping: form_id -> (api_endpoint, http_method, db_table)
KNOWN_FORM_MAPPINGS: dict[str, dict] = {
    "login": {
        "submit_endpoint": "/api/auth/login",
        "http_method": "POST",
        "expected_table": "users",
    },
    "register": {
        "submit_endpoint": "/api/auth/register",
        "http_method": "POST",
        "expected_table": "users",
    },
    "forgotPassword": {
        "submit_endpoint": "/api/auth/forgot-password",
        "http_method": "POST",
        "expected_table": "users",
    },
    "resetPassword": {
        "submit_endpoint": "/api/auth/reset-password",
        "http_method": "POST",
        "expected_table": "users",
    },
    "TaskEditForm": {
        "submit_endpoint": "/api/tasks/{id}",
        "http_method": "PATCH",
        "expected_table": "tasks",
    },
    "TaskCreateModal": {
        "submit_endpoint": "/api/tasks",
        "http_method": "POST",
        "expected_table": "tasks",
    },
    "taskCreate": {
        "submit_endpoint": "/api/tasks",
        "http_method": "POST",
        "expected_table": "tasks",
    },
    "taskEdit": {
        "submit_endpoint": "/api/tasks/{id}",
        "http_method": "PATCH",
        "expected_table": "tasks",
    },
    "billingRuleConfig": {
        "submit_endpoint": "/api/billing/rules",
        "http_method": "POST",
        "expected_table": "billing_records",
    },
    "qualityRule": {
        "submit_endpoint": "/api/quality/rules",
        "http_method": "POST",
        "expected_table": "quality_issues",
    },
    "ruleConfig": {
        "submit_endpoint": "/api/quality/rules",
        "http_method": "POST",
        "expected_table": "quality_issues",
    },
    "llmProvider": {
        "submit_endpoint": "/api/llm/providers",
        "http_method": "POST",
        "expected_table": "llm_providers",
    },
    "providerForm": {
        "submit_endpoint": "/api/llm/providers",
        "http_method": "POST",
        "expected_table": "llm_providers",
    },
}


def discover_backend_endpoints(api_dir: str) -> dict[str, list[dict]]:
    """Parse backend API files to extract router endpoints."""
    endpoints: dict[str, list[dict]] = {}

    if not os.path.isdir(api_dir):
        return endpoints

    for fname in sorted(os.listdir(api_dir)):
        if not fname.endswith(".py"):
            continue
        filepath = os.path.join(api_dir, fname)
        content = read_file_safe(filepath)
        if not content:
            continue

        file_endpoints: list[dict] = []
        for match in ROUTER_DECORATOR.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            file_endpoints.append({"method": method, "path": path})

        if file_endpoints:
            endpoints[fname] = file_endpoints

    return endpoints


def discover_database_tables(models_dir: str = BACKEND_SRC) -> dict[str, str]:
    """Scan for SQLAlchemy models and return {ModelName: table_name}."""
    tables: dict[str, str] = {}

    for root, _dirs, files in os.walk(models_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(root, fname)
            content = read_file_safe(filepath)

            for m in MODEL_CLASS.finditer(content):
                model_name = m.group(1)
                after_class = content[m.end():]
                table_match = TABLENAME.search(after_class[:500])
                if table_match:
                    tables[model_name] = table_match.group(1)

    return tables


def apply_endpoint_mappings(forms: list[FormDefinition]) -> list[FormDefinition]:
    """Enrich form definitions with API endpoint and table mappings."""
    for form in forms:
        mapping = KNOWN_FORM_MAPPINGS.get(form.form_id)
        if not mapping:
            continue
        form.submit_endpoint = mapping["submit_endpoint"]
        form.http_method = mapping["http_method"]
        form.expected_table = mapping["expected_table"]
    return forms


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_all_forms() -> dict:
    """
    Run the full form discovery pipeline.

    Returns a structured report dict with:
    - forms: list of discovered form definitions
    - backend_endpoints: dict of API file -> endpoints
    - database_tables: dict of model name -> table name
    - summary: counts and coverage stats
    """
    forms = discover_frontend_forms()
    forms = apply_endpoint_mappings(forms)

    api_dir = os.path.join(BACKEND_SRC, "api")
    backend_endpoints = discover_backend_endpoints(api_dir)
    database_tables = discover_database_tables()

    mapped_count = sum(1 for f in forms if f.submit_endpoint)
    total_fields = sum(len(f.fields) for f in forms)

    return {
        "forms": [asdict(f) for f in forms],
        "backend_endpoints": backend_endpoints,
        "database_tables": database_tables,
        "summary": {
            "total_forms": len(forms),
            "mapped_forms": mapped_count,
            "unmapped_forms": len(forms) - mapped_count,
            "total_fields": total_fields,
            "total_backend_files": len(backend_endpoints),
            "total_database_tables": len(database_tables),
        },
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    report = discover_all_forms()
    print(json.dumps(report, indent=2, default=str))
