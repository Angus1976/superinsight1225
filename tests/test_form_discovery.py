"""Tests for the form discovery system."""

import pytest
from tests.form_discovery import (
    discover_all_forms,
    discover_frontend_forms,
    discover_backend_endpoints,
    discover_database_tables,
    extract_form_fields,
    extract_validation_rules,
    detect_input_type,
    apply_endpoint_mappings,
    FormDefinition,
    FormField,
    ValidationRule,
    FRONTEND_SRC,
    BACKEND_SRC,
)
import os


# ---------------------------------------------------------------------------
# Unit tests for parsing helpers
# ---------------------------------------------------------------------------

class TestExtractValidationRules:
    def test_required_rule(self):
        rules = extract_validation_rules("{ required: true, message: 'Required' }")
        assert any(r.rule_type == "required" for r in rules)

    def test_min_max_rules(self):
        rules = extract_validation_rules("{ min: 3, max: 20 }")
        types = {r.rule_type for r in rules}
        assert "min" in types
        assert "max" in types

    def test_type_rule(self):
        rules = extract_validation_rules("{ type: 'email', message: 'Invalid' }")
        assert any(r.rule_type == "type" and r.value == "email" for r in rules)

    def test_pattern_rule(self):
        rules = extract_validation_rules("{ pattern: /^[a-z]+$/ }")
        assert any(r.rule_type == "pattern" for r in rules)

    def test_custom_validator(self):
        rules = extract_validation_rules("({ getFieldValue }) => ({ validator(_, v) {} })")
        assert any(r.rule_type == "custom" for r in rules)

    def test_empty_rules(self):
        rules = extract_validation_rules("")
        assert rules == []


class TestDetectInputType:
    def test_password(self):
        assert detect_input_type("<Input.Password />") == "password"

    def test_select(self):
        assert detect_input_type("<Select><Option /></Select>") == "select"

    def test_datepicker(self):
        assert detect_input_type("<DatePicker />") == "date"

    def test_checkbox(self):
        assert detect_input_type("<Checkbox>Agree</Checkbox>") == "checkbox"

    def test_number(self):
        assert detect_input_type("<InputNumber min={0} />") == "number"

    def test_textarea(self):
        assert detect_input_type("<TextArea rows={4} />") == "textarea"

    def test_plain_input(self):
        assert detect_input_type("<Input placeholder='Name' />") == "text"

    def test_no_match(self):
        assert detect_input_type("<div>no input</div>") == "text"


class TestExtractFormFields:
    def test_extracts_named_fields(self):
        content = """
        <Form name="test">
          <Form.Item name="username" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, min: 8 }]}>
            <Input.Password />
          </Form.Item>
        </Form>
        """
        fields = extract_form_fields(content)
        names = [f.field_name for f in fields]
        assert "username" in names
        assert "password" in names

    def test_detects_field_types(self):
        content = """
        <Form name="test">
          <Form.Item name="email">
            <Input />
          </Form.Item>
          <Form.Item name="role">
            <Select><Option value="admin" /></Select>
          </Form.Item>
        </Form>
        """
        fields = extract_form_fields(content)
        field_map = {f.field_name: f for f in fields}
        assert field_map["email"].field_type == "text"
        assert field_map["role"].field_type == "select"

    def test_skips_unnamed_items(self):
        content = """
        <Form name="test">
          <Form.Item>
            <Button>Submit</Button>
          </Form.Item>
        </Form>
        """
        fields = extract_form_fields(content)
        assert len(fields) == 0


# ---------------------------------------------------------------------------
# Integration tests against actual project files
# ---------------------------------------------------------------------------

class TestDiscoverFrontendForms:
    def test_discovers_forms(self):
        forms = discover_frontend_forms()
        assert len(forms) > 0

    def test_login_form_discovered(self):
        forms = discover_frontend_forms()
        login = [f for f in forms if f.form_id == "login"]
        assert len(login) == 1
        field_names = [fd.field_name for fd in _to_field_objects(login[0].fields)]
        assert "username" in field_names
        assert "password" in field_names

    def test_register_form_discovered(self):
        forms = discover_frontend_forms()
        reg = [f for f in forms if f.form_id == "register"]
        assert len(reg) == 1
        field_names = [fd.field_name for fd in _to_field_objects(reg[0].fields)]
        assert "username" in field_names
        assert "email" in field_names
        assert "password" in field_names

    def test_task_create_form_discovered(self):
        forms = discover_frontend_forms()
        task = [f for f in forms if f.form_id == "TaskCreateModal"]
        assert len(task) == 1
        field_names = [fd.field_name for fd in _to_field_objects(task[0].fields)]
        assert "name" in field_names

    def test_task_edit_form_discovered(self):
        forms = discover_frontend_forms()
        edit = [f for f in forms if f.form_id == "TaskEditForm"]
        assert len(edit) == 1


class TestDiscoverBackendEndpoints:
    def test_discovers_endpoints(self):
        api_dir = os.path.join(BACKEND_SRC, "api")
        endpoints = discover_backend_endpoints(api_dir)
        assert len(endpoints) > 0

    def test_auth_endpoints_found(self):
        api_dir = os.path.join(BACKEND_SRC, "api")
        endpoints = discover_backend_endpoints(api_dir)
        assert "auth.py" in endpoints
        paths = [e["path"] for e in endpoints["auth.py"]]
        assert "/login" in paths

    def test_tasks_endpoints_found(self):
        api_dir = os.path.join(BACKEND_SRC, "api")
        endpoints = discover_backend_endpoints(api_dir)
        assert "tasks.py" in endpoints


class TestDiscoverDatabaseTables:
    def test_discovers_tables(self):
        tables = discover_database_tables()
        assert len(tables) > 0

    def test_users_table(self):
        tables = discover_database_tables()
        assert "UserModel" in tables
        assert tables["UserModel"] == "users"

    def test_tasks_table(self):
        tables = discover_database_tables()
        assert "TaskModel" in tables
        assert tables["TaskModel"] == "tasks"


class TestApplyEndpointMappings:
    def test_maps_known_forms(self):
        forms = [
            FormDefinition(form_id="login", form_name="login", component_file="test.tsx"),
            FormDefinition(form_id="register", form_name="register", component_file="test.tsx"),
            FormDefinition(form_id="unknown", form_name="unknown", component_file="test.tsx"),
        ]
        mapped = apply_endpoint_mappings(forms)
        assert mapped[0].submit_endpoint == "/api/auth/login"
        assert mapped[0].expected_table == "users"
        assert mapped[1].submit_endpoint == "/api/auth/register"
        assert mapped[2].submit_endpoint == ""  # unmapped


class TestDiscoverAllForms:
    def test_returns_complete_report(self):
        report = discover_all_forms()
        assert "forms" in report
        assert "backend_endpoints" in report
        assert "database_tables" in report
        assert "summary" in report

    def test_summary_counts(self):
        report = discover_all_forms()
        s = report["summary"]
        assert s["total_forms"] > 0
        assert s["mapped_forms"] > 0
        assert s["total_fields"] > 0
        assert s["total_backend_files"] > 0
        assert s["total_database_tables"] > 0
        assert s["total_forms"] == s["mapped_forms"] + s["unmapped_forms"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_field_objects(fields_dicts: list[dict]) -> list[FormField]:
    """Convert list of field dicts back to FormField objects."""
    return [
        FormField(
            field_name=d["field_name"],
            field_type=d.get("field_type", "text"),
            required=d.get("required", False),
            validation_rules=d.get("validation_rules", []),
            db_column=d.get("db_column", ""),
        )
        for d in fields_dicts
    ]
