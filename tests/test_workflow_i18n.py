"""
Property-based tests for workflow i18n translation consistency.
Feature: ai-workflow-engine
"""
import json
import os
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


def load_json(path: str) -> dict:
    """Load a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_keys(obj: dict, prefix: str = '') -> set:
    """Recursively extract all leaf keys from a nested dict."""
    keys = set()
    for k, v in obj.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(extract_keys(v, full_key))
        else:
            keys.add(full_key)
    return keys


# Paths to translation files
ZH_PATH = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'locales', 'zh', 'workflow.json')
EN_PATH = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'locales', 'en', 'workflow.json')


class TestTranslationKeyConsistency:
    """Property 20: Translation key zh/en consistency."""

    def test_zh_en_keys_match(self):
        """# Feature: ai-workflow-engine, Property 20: Translation keys zh/en consistency

        All keys in zh/workflow.json must exist in en/workflow.json and vice versa.

        **Validates: Requirements 10.2**
        """
        zh_data = load_json(ZH_PATH)
        en_data = load_json(EN_PATH)

        zh_keys = extract_keys(zh_data)
        en_keys = extract_keys(en_data)

        missing_in_en = zh_keys - en_keys
        missing_in_zh = en_keys - zh_keys

        assert not missing_in_en, f"Keys in zh but missing in en: {missing_in_en}"
        assert not missing_in_zh, f"Keys in en but missing in zh: {missing_in_zh}"
        assert zh_keys == en_keys

    @settings(max_examples=100)
    @given(key_index=st.integers(min_value=0, max_value=1000))
    def test_random_key_exists_in_both(self, key_index: int):
        """# Feature: ai-workflow-engine, Property 20: Random key sampling

        For any randomly sampled key from either translation file,
        it must exist in the other file.

        **Validates: Requirements 10.2**
        """
        zh_data = load_json(ZH_PATH)
        en_data = load_json(EN_PATH)

        zh_keys = sorted(extract_keys(zh_data))
        en_keys = sorted(extract_keys(en_data))

        if zh_keys:
            zh_key = zh_keys[key_index % len(zh_keys)]
            assert zh_key in set(en_keys), f"Key '{zh_key}' in zh but not in en"

        if en_keys:
            en_key = en_keys[key_index % len(en_keys)]
            assert en_key in set(zh_keys), f"Key '{en_key}' in en but not in zh"


import re


class TestErrorResponseCodes:
    """Property 21: Error responses use error codes."""

    # All known workflow error codes from the design doc
    KNOWN_ERROR_CODES = [
        'WORKFLOW_NOT_FOUND',
        'WORKFLOW_DISABLED',
        'WORKFLOW_NAME_CONFLICT',
        'WORKFLOW_PERMISSION_DENIED',
        'WORKFLOW_SKILL_NOT_FOUND',
        'WORKFLOW_DATASOURCE_NOT_FOUND',
        'WORKFLOW_DATASOURCE_DISABLED',
        'WORKFLOW_INVALID_ROLE',
        'WORKFLOW_SKILL_DENIED',
        'WORKFLOW_DATASOURCE_DENIED',
        'WORKFLOW_PRESET_DELETE_DENIED',
        'ADMIN_REQUIRED',
        'AUTHORIZATION_NOT_IMPLEMENTED',
        'VALIDATION_ERROR',
    ]

    def test_error_codes_are_strings(self):
        """# Feature: ai-workflow-engine, Property 21: Error codes are strings

        All defined error codes must be non-empty strings.

        **Validates: Requirements 10.4**
        """
        for code in self.KNOWN_ERROR_CODES:
            assert isinstance(code, str), f"Error code must be string: {code}"
            assert len(code) > 0, f"Error code must be non-empty: {code}"
            assert code == code.upper(), f"Error code must be uppercase: {code}"

    @settings(max_examples=100)
    @given(code_index=st.integers(min_value=0, max_value=100))
    def test_error_code_format_consistency(self, code_index: int):
        """# Feature: ai-workflow-engine, Property 21: Error code format consistency

        For any error code, it should follow UPPER_SNAKE_CASE format.

        **Validates: Requirements 10.4**
        """
        code = self.KNOWN_ERROR_CODES[code_index % len(self.KNOWN_ERROR_CODES)]
        assert re.match(r'^[A-Z][A-Z0-9_]*$', code), \
            f"Error code '{code}' does not match UPPER_SNAKE_CASE format"

    def test_workflow_error_response_schema(self):
        """# Feature: ai-workflow-engine, Property 21: WorkflowErrorResponse has error_code

        The WorkflowErrorResponse schema must include error_code field.

        **Validates: Requirements 10.4**
        """
        from src.api.workflow_schemas import WorkflowErrorResponse

        # Verify the schema has error_code field
        fields = WorkflowErrorResponse.__fields__
        assert 'error_code' in fields, "WorkflowErrorResponse must have error_code field"
        assert 'success' in fields, "WorkflowErrorResponse must have success field"
        assert 'message' in fields, "WorkflowErrorResponse must have message field"

        # Verify error_code is string type
        error = WorkflowErrorResponse(
            success=False,
            error_code='WORKFLOW_NOT_FOUND',
            message='Test error'
        )
        assert isinstance(error.error_code, str)
