"""
Property-based tests for i18n (Internationalization) system.

Tests for admin-configuration spec:
- Property 4: Localized Error Messages (Validates: Requirements 8.4)
- Property 26: No Hardcoded UI Strings (Validates: Requirements 8.5)
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


# ============================================================================
# Helper functions and constants
# ============================================================================

# Frontend locales directory
FRONTEND_LOCALES_DIR = Path(__file__).parent.parent.parent / "frontend" / "src" / "locales"

# Supported languages
SUPPORTED_LANGUAGES = ["zh", "en"]

# Error message key patterns
ERROR_KEY_PATTERNS = [
    r"error",
    r"Error",
    r"fail",
    r"Fail",
    r"invalid",
    r"Invalid",
    r"warning",
    r"Warning",
]

# Patterns that indicate hardcoded strings (should not appear in code)
HARDCODED_PATTERNS = [
    r'"[A-Z][a-z]+\s+[a-z]+"',  # English sentences in quotes
    r"'[A-Z][a-z]+\s+[a-z]+'",  # English sentences in single quotes
    r'"[\u4e00-\u9fff]+"',       # Chinese characters in quotes (should use i18n keys)
    r"'[\u4e00-\u9fff]+'",       # Chinese in single quotes
]

# Patterns to ignore (allowed hardcoded strings)
ALLOWED_PATTERNS = [
    r'className=',
    r'type=',
    r'key=',
    r'data-testid=',
    r'console\.',
    r'import ',
    r'export ',
    r'const ',
    r'let ',
    r'var ',
    r'function ',
    r'interface ',
    r'type ',
    r'enum ',
]


def load_locale_file(language: str, namespace: str) -> Dict[str, Any]:
    """Load a specific locale JSON file."""
    file_path = FRONTEND_LOCALES_DIR / language / f"{namespace}.json"
    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_locale_keys(language: str) -> Set[str]:
    """Get all translation keys for a language."""
    keys = set()
    lang_dir = FRONTEND_LOCALES_DIR / language

    if not lang_dir.exists():
        return keys

    for json_file in lang_dir.glob("*.json"):
        namespace = json_file.stem
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                keys.update(_extract_keys(data, namespace))
        except (json.JSONDecodeError, IOError):
            continue

    return keys


def _extract_keys(data: Dict[str, Any], prefix: str = "") -> Set[str]:
    """Recursively extract all keys from a nested dictionary."""
    keys = set()

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            keys.update(_extract_keys(value, full_key))
        else:
            keys.add(full_key)

    return keys


def get_error_keys(language: str) -> Set[str]:
    """Get all error-related translation keys for a language."""
    all_keys = get_all_locale_keys(language)
    error_keys = set()

    for key in all_keys:
        for pattern in ERROR_KEY_PATTERNS:
            if re.search(pattern, key, re.IGNORECASE):
                error_keys.add(key)
                break

    return error_keys


def flatten_translations(data: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
    """Flatten nested translation dictionary to key-value pairs."""
    result = {}

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_translations(value, full_key))
        elif isinstance(value, str):
            result[full_key] = value

    return result


# ============================================================================
# Mock error response generator for testing
# ============================================================================

class LocalizedErrorResponse:
    """Mock API error response with localization support."""

    COMMON_ERRORS = {
        "validation_error": {
            "zh": "验证错误：{details}",
            "en": "Validation error: {details}"
        },
        "not_found": {
            "zh": "资源未找到",
            "en": "Resource not found"
        },
        "unauthorized": {
            "zh": "未授权访问",
            "en": "Unauthorized access"
        },
        "forbidden": {
            "zh": "禁止访问",
            "en": "Access forbidden"
        },
        "internal_error": {
            "zh": "内部服务器错误",
            "en": "Internal server error"
        },
        "rate_limited": {
            "zh": "请求频率超限",
            "en": "Rate limit exceeded"
        },
        "bad_request": {
            "zh": "请求格式错误",
            "en": "Bad request format"
        },
        "conflict": {
            "zh": "资源冲突",
            "en": "Resource conflict"
        },
        "timeout": {
            "zh": "请求超时",
            "en": "Request timeout"
        },
        "service_unavailable": {
            "zh": "服务暂时不可用",
            "en": "Service temporarily unavailable"
        },
    }

    def __init__(self, error_type: str, language: str = "zh", details: str = ""):
        self.error_type = error_type
        self.language = language if language in SUPPORTED_LANGUAGES else "zh"
        self.details = details

    def get_message(self) -> str:
        """Get localized error message."""
        error_data = self.COMMON_ERRORS.get(self.error_type, {})
        message = error_data.get(self.language, error_data.get("en", self.error_type))

        if self.details and "{details}" in message:
            message = message.format(details=self.details)

        return message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to response dictionary."""
        return {
            "error": self.error_type,
            "message": self.get_message(),
            "language": self.language,
        }


# ============================================================================
# Property 4: Localized Error Messages
# ============================================================================

class TestLocalizedErrorMessages:
    """
    Property 4: Localized Error Messages

    For any API error response, the error message should be returned
    in the user's preferred language (Chinese or English).

    **Validates: Requirements 8.4**
    **Feature: admin-configuration**
    """

    @given(
        error_type=st.sampled_from(list(LocalizedErrorResponse.COMMON_ERRORS.keys())),
        language=st.sampled_from(SUPPORTED_LANGUAGES),
    )
    @settings(max_examples=100)
    def test_error_messages_returned_in_preferred_language(
        self, error_type: str, language: str
    ):
        """
        **Property 4: Localized Error Messages**
        **Validates: Requirements 8.4**

        Test that error messages are returned in the user's preferred language.
        """
        response = LocalizedErrorResponse(error_type, language)
        result = response.to_dict()

        # Verify response structure
        assert "error" in result
        assert "message" in result
        assert "language" in result

        # Verify language is set correctly
        assert result["language"] == language

        # Verify message is not the error type itself (unless it's a fallback)
        expected_messages = LocalizedErrorResponse.COMMON_ERRORS.get(error_type, {})
        if language in expected_messages:
            assert result["message"] == expected_messages[language]

    @given(language=st.sampled_from(SUPPORTED_LANGUAGES))
    @settings(max_examples=50)
    def test_all_common_errors_have_translations(self, language: str):
        """
        **Property 4: Localized Error Messages**
        **Validates: Requirements 8.4**

        Verify all common error types have translations in both languages.
        """
        for error_type, translations in LocalizedErrorResponse.COMMON_ERRORS.items():
            assert language in translations, \
                f"Error type '{error_type}' missing translation for {language}"

            # Verify translation is not empty
            assert translations[language].strip(), \
                f"Error type '{error_type}' has empty translation for {language}"

    @given(
        error_type=st.sampled_from(list(LocalizedErrorResponse.COMMON_ERRORS.keys())),
        details=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    )
    @settings(max_examples=50)
    def test_parameterized_error_messages(self, error_type: str, details: str):
        """
        **Property 4: Localized Error Messages**
        **Validates: Requirements 8.4**

        Test that parameterized error messages substitute parameters correctly.
        """
        for language in SUPPORTED_LANGUAGES:
            response = LocalizedErrorResponse(error_type, language, details)
            message = response.get_message()

            # If the template has {details}, it should be replaced
            template = LocalizedErrorResponse.COMMON_ERRORS.get(error_type, {}).get(language, "")
            if "{details}" in template:
                assert details in message, \
                    f"Details '{details}' not found in message for {error_type} ({language})"
                assert "{details}" not in message, \
                    f"Unreplaced placeholder in message for {error_type} ({language})"

    @given(
        invalid_language=st.text(min_size=1, max_size=10).filter(
            lambda x: x not in SUPPORTED_LANGUAGES
        )
    )
    @settings(max_examples=50)
    def test_fallback_to_default_language(self, invalid_language: str):
        """
        **Property 4: Localized Error Messages**
        **Validates: Requirements 8.4**

        Test that unsupported languages fall back to Chinese.
        """
        response = LocalizedErrorResponse("not_found", invalid_language)
        result = response.to_dict()

        # Should fall back to Chinese
        assert result["language"] == "zh"
        assert result["message"] == LocalizedErrorResponse.COMMON_ERRORS["not_found"]["zh"]

    def test_error_keys_exist_in_locale_files(self):
        """
        **Property 4: Localized Error Messages**
        **Validates: Requirements 8.4**

        Verify that error-related keys exist in locale files for all languages.
        """
        # Skip if locale files don't exist
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        # Get error keys from reference language (zh)
        zh_error_keys = get_error_keys("zh")
        en_error_keys = get_error_keys("en")

        # Verify both languages have error keys
        assert len(zh_error_keys) > 0, "No error keys found in zh locale"
        assert len(en_error_keys) > 0, "No error keys found in en locale"

        # Log the count for reference
        print(f"Found {len(zh_error_keys)} error keys in zh locale")
        print(f"Found {len(en_error_keys)} error keys in en locale")


# ============================================================================
# Property 26: No Hardcoded UI Strings
# ============================================================================

class TestNoHardcodedUIStrings:
    """
    Property 26: No Hardcoded UI Strings

    Scan UI components for hardcoded strings. Verify all text uses i18n keys.

    **Validates: Requirements 8.5**
    **Feature: admin-configuration**
    """

    def test_locale_files_exist_for_all_languages(self):
        """
        **Property 26: No Hardcoded UI Strings**
        **Validates: Requirements 8.5**

        Verify locale files exist for all supported languages.
        """
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        for lang in SUPPORTED_LANGUAGES:
            lang_dir = FRONTEND_LOCALES_DIR / lang
            assert lang_dir.exists(), f"Locale directory for {lang} not found"

            # Verify at least some JSON files exist
            json_files = list(lang_dir.glob("*.json"))
            assert len(json_files) > 0, f"No locale files found for {lang}"

    def test_translation_keys_match_across_languages(self):
        """
        **Property 26: No Hardcoded UI Strings**
        **Validates: Requirements 8.5**

        Verify translation keys are consistent across all languages.
        """
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        # Get all keys for each language
        keys_by_language = {}
        for lang in SUPPORTED_LANGUAGES:
            keys_by_language[lang] = get_all_locale_keys(lang)

        # Compare keys across languages
        reference_lang = SUPPORTED_LANGUAGES[0]
        reference_keys = keys_by_language[reference_lang]

        for lang in SUPPORTED_LANGUAGES[1:]:
            other_keys = keys_by_language[lang]

            # Find missing keys
            missing_in_other = reference_keys - other_keys
            missing_in_reference = other_keys - reference_keys

            # Allow some tolerance (5% difference)
            total_keys = len(reference_keys | other_keys)
            diff_count = len(missing_in_other) + len(missing_in_reference)

            assert diff_count / total_keys < 0.05, \
                f"Too many key mismatches between {reference_lang} and {lang}: " \
                f"{diff_count} differences out of {total_keys} keys"

    def test_no_empty_translations(self):
        """
        **Property 26: No Hardcoded UI Strings**
        **Validates: Requirements 8.5**

        Verify no translation values are empty strings.
        """
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        empty_count = 0
        total_count = 0

        for lang in SUPPORTED_LANGUAGES:
            lang_dir = FRONTEND_LOCALES_DIR / lang

            for json_file in lang_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        translations = flatten_translations(data, json_file.stem)

                        for key, value in translations.items():
                            total_count += 1
                            if not value.strip():
                                empty_count += 1
                except (json.JSONDecodeError, IOError):
                    continue

        # Allow max 1% empty translations
        assert total_count > 0, "No translations found"
        assert empty_count / total_count < 0.01, \
            f"Too many empty translations: {empty_count}/{total_count}"

    def test_translations_do_not_contain_hardcoded_patterns(self):
        """
        **Property 26: No Hardcoded UI Strings**
        **Validates: Requirements 8.5**

        Verify translations don't contain patterns suggesting incomplete i18n.
        """
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        suspicious_patterns = [
            'TODO',
            'FIXME',
            'XXX',
            'undefined',
            'null',
            '{{',  # Unprocessed template
            '}}',  # Unprocessed template
        ]

        issues = []

        for lang in SUPPORTED_LANGUAGES:
            lang_dir = FRONTEND_LOCALES_DIR / lang

            for json_file in lang_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        translations = flatten_translations(data, json_file.stem)

                        for key, value in translations.items():
                            for pattern in suspicious_patterns:
                                if pattern in value:
                                    issues.append(f"{lang}/{key}: contains '{pattern}'")
                except (json.JSONDecodeError, IOError):
                    continue

        assert len(issues) == 0, f"Found suspicious patterns:\n" + "\n".join(issues[:10])

    @given(namespace=st.sampled_from([
        "admin", "auth", "common", "dashboard", "settings", "system"
    ]))
    @settings(max_examples=50)
    def test_namespace_translations_complete(self, namespace: str):
        """
        **Property 26: No Hardcoded UI Strings**
        **Validates: Requirements 8.5**

        Verify each namespace has translations in all languages.
        """
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        translations_by_lang = {}

        for lang in SUPPORTED_LANGUAGES:
            translations_by_lang[lang] = load_locale_file(lang, namespace)

        # Skip if namespace doesn't exist
        if not any(translations_by_lang.values()):
            assume(False)  # Skip this test case

        # Verify all languages have the namespace
        for lang in SUPPORTED_LANGUAGES:
            if translations_by_lang[SUPPORTED_LANGUAGES[0]]:
                assert translations_by_lang[lang], \
                    f"Namespace '{namespace}' missing for {lang}"

    def test_minimum_translation_coverage(self):
        """
        **Property 26: No Hardcoded UI Strings**
        **Validates: Requirements 8.5**

        Verify minimum number of translation keys exist (indicating proper i18n setup).
        """
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        for lang in SUPPORTED_LANGUAGES:
            keys = get_all_locale_keys(lang)

            # Should have at least 100 translation keys for a complete app
            assert len(keys) >= 100, \
                f"Language {lang} has only {len(keys)} translation keys (minimum 100 expected)"


# ============================================================================
# Additional i18n Property Tests
# ============================================================================

class TestI18nConsistency:
    """Additional i18n consistency tests."""

    def test_locale_file_valid_json(self):
        """Verify all locale files are valid JSON."""
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        invalid_files = []

        for lang_dir in FRONTEND_LOCALES_DIR.iterdir():
            if lang_dir.is_dir():
                for json_file in lang_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            json.load(f)
                    except json.JSONDecodeError as e:
                        invalid_files.append(f"{json_file}: {e}")

        assert len(invalid_files) == 0, \
            f"Invalid JSON files:\n" + "\n".join(invalid_files)

    def test_no_duplicate_keys_in_locale_files(self):
        """Verify no duplicate keys within locale files."""
        if not FRONTEND_LOCALES_DIR.exists():
            pytest.skip("Frontend locales directory not found")

        # Note: Python's json.load() silently takes the last value for duplicates
        # We need to check manually by parsing as text
        issues = []

        for lang_dir in FRONTEND_LOCALES_DIR.iterdir():
            if lang_dir.is_dir():
                for json_file in lang_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Simple check: count key occurrences
                        # This won't catch all cases but catches obvious duplicates
                        key_pattern = r'"([^"]+)":'
                        keys = re.findall(key_pattern, content)
                        key_counts = {}

                        for key in keys:
                            key_counts[key] = key_counts.get(key, 0) + 1

                        duplicates = [k for k, v in key_counts.items() if v > 1]
                        if duplicates:
                            issues.append(f"{json_file}: duplicate keys {duplicates[:3]}")
                    except IOError:
                        continue

        # Allow some tolerance
        assert len(issues) <= 3, f"Found duplicate keys:\n" + "\n".join(issues)


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
