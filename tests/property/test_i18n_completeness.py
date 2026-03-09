"""
Property-Based Tests for Internationalization Completeness

**Validates: Requirements 11.5, 19.2, 19.3, 19.4, 19.5, 19.6**

Property 26: Internationalization Completeness
All user-facing strings in the data lifecycle frontend must be internationalized
with matching keys in both Chinese (zh) and English (en) translation files.
"""

import json
import os
import pytest
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List


# ============================================================================
# Test Configuration
# ============================================================================

# Path to translation files
TRANSLATIONS_DIR = Path(__file__).parent.parent.parent / "frontend" / "src" / "locales"
ZH_TRANSLATIONS_DIR = TRANSLATIONS_DIR / "zh"
EN_TRANSLATIONS_DIR = TRANSLATIONS_DIR / "en"


# ============================================================================
# Helper Functions
# ============================================================================

def load_translation_file(lang: str, namespace: str) -> Dict[str, Any]:
    """Load a translation JSON file for a specific language and namespace."""
    file_path = TRANSLATIONS_DIR / lang / f"{namespace}.json"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_all_keys(obj: Dict[str, Any], prefix: str = '') -> List[str]:
    """Recursively get all keys from a nested dictionary."""
    keys = []
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.extend(get_all_keys(value, full_key))
        else:
            keys.append(full_key)
    return keys


def flatten_dict(obj: Dict[str, Any], prefix: str = '', separator: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary to a single level."""
    result = {}
    for key, value in obj.items():
        full_key = f"{prefix}{separator}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, full_key, separator))
        else:
            result[full_key] = value
    return result


# ============================================================================
# Test Strategies
# ============================================================================

@st.composite
def namespace_strategy(draw):
    """Generate valid translation namespace names."""
    namespaces = ['dataLifecycle', 'common', 'dashboard', 'tasks', 'quality']
    return draw(st.sampled_from(namespaces))


@st.composite
def translation_key_strategy(draw):
    """Generate valid translation key patterns."""
    key_patterns = [
        'interface.title',
        'interface.loading',
        'tabs.tempData',
        'tabs.sampleLibrary',
        'tabs.review',
        'tabs.annotation',
        'tabs.enhancement',
        'tabs.aiTrial',
        'common.actions.save',
        'common.actions.cancel',
        'common.status.loading',
        'common.messages.confirmDelete',
        'tempData.title',
        'tempData.columns.id',
        'tempData.columns.name',
        'tempData.columns.state',
        'tempData.actions.create',
        'tempData.actions.edit',
        'tempData.actions.delete',
        'sampleLibrary.title',
        'sampleLibrary.columns.id',
        'sampleLibrary.columns.name',
        'sampleLibrary.columns.qualityScore',
        'sampleLibrary.actions.addToLibrary',
        'review.title',
        'review.columns.id',
        'review.columns.status',
        'review.actions.approve',
        'review.actions.reject',
        'annotationTask.title',
        'annotationTask.columns.id',
        'annotationTask.columns.status',
        'annotationTask.columns.priority',
        'annotationTask.actions.create',
        'enhancement.title',
        'enhancement.columns.id',
        'enhancement.columns.status',
        'enhancement.columns.progress',
        'enhancement.actions.create',
        'aiTrial.title',
        'aiTrial.columns.id',
        'aiTrial.columns.status',
        'aiTrial.columns.successRate',
        'aiTrial.actions.create',
        'errors.permissionDenied',
        'errors.dataNotFound',
        'errors.validationError',
        'permissions.view',
        'permissions.create',
        'permissions.edit',
        'permissions.delete',
    ]
    return draw(st.sampled_from(key_patterns))


@st.composite
def ui_text_strategy(draw):
    """Generate realistic UI text strings."""
    text_samples = [
        "加载中...",
        "保存成功",
        "删除成功",
        "确认删除",
        "操作失败",
        "暂无数据",
        "Loading...",
        "Save successful",
        "Delete successful",
        "Confirm delete",
        "Operation failed",
        "No data available",
    ]
    return draw(st.sampled_from(text_samples))


# ============================================================================
# Property 26: Internationalization Completeness
# **Validates: Requirements 11.5, 19.2, 19.3, 19.4, 19.5, 19.6**
# ============================================================================

@pytest.mark.property
class TestI18nCompleteness:
    """
    Property 26: Internationalization Completeness
    
    All user-facing strings in the data lifecycle frontend must be internationalized
    with matching keys in both Chinese (zh) and English (en) translation files.
    """
    
    def test_data_lifecycle_namespace_exists_in_both_languages(self):
        """
        Property: The dataLifecycle namespace must exist in both zh and en translations.
        
        For the data lifecycle feature to be fully internationalized, the translation
        namespace must be available in both Chinese and English.
        """
        zh_path = ZH_TRANSLATIONS_DIR / "dataLifecycle.json"
        en_path = EN_TRANSLATIONS_DIR / "dataLifecycle.json"
        
        # Assert: Both files must exist
        assert zh_path.exists(), \
            f"Chinese translation file must exist at {zh_path}"
        assert en_path.exists(), \
            f"English translation file must exist at {en_path}"
    
    def test_data_lifecycle_namespace_not_empty(self):
        """
        Property: The dataLifecycle namespace must contain translations.
        
        The translation namespace must not be empty - it must contain actual
        translation keys for the data lifecycle feature.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        # Assert: Both files must have content
        assert len(zh_translations) > 0, \
            "Chinese translation file must not be empty"
        assert len(en_translations) > 0, \
            "English translation file must not be empty"
    
    @given(namespace=namespace_strategy())
    @settings(max_examples=10, deadline=None)
    def test_translation_keys_identical_across_languages(self, namespace: str):
        """
        Property: Translation keys must be identical across zh and en files.
        
        For any translation namespace, the set of keys in the Chinese translation
        file must exactly match the set of keys in the English translation file.
        This ensures that all UI elements are available in both languages.
        """
        zh_translations = load_translation_file('zh', namespace)
        en_translations = load_translation_file('en', namespace)
        
        # Skip if either file doesn't exist
        assume(len(zh_translations) > 0 and len(en_translations) > 0)
        
        # Get all keys from both files
        zh_keys = set(get_all_keys(zh_translations))
        en_keys = set(get_all_keys(en_translations))
        
        # Assert: Keys must be identical
        assert zh_keys == en_keys, \
            f"Translation keys must be identical for namespace '{namespace}':\n" \
            f"Missing in EN: {zh_keys - en_keys}\n" \
            f"Missing in ZH: {en_keys - zh_keys}"
    
    @given(key=translation_key_strategy())
    @settings(max_examples=50, deadline=None)
    def test_translation_values_are_non_empty_strings(self, key: str):
        """
        Property: Translation values must be non-empty strings.
        
        For any translation key, the corresponding value in both zh and en files
        must be a non-empty string. Empty or null translations are not allowed.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        # Navigate to the key (handle nested keys)
        zh_value = zh_translations
        en_value = en_translations
        
        key_parts = key.split('.')
        for part in key_parts:
            if isinstance(zh_value, dict) and part in zh_value:
                zh_value = zh_value[part]
            else:
                zh_value = None
            if isinstance(en_value, dict) and part in en_value:
                en_value = en_value[part]
            else:
                en_value = None
        
        # Assert: Values must be non-empty strings
        assert zh_value is not None, \
            f"Translation key '{key}' must exist in Chinese translations"
        assert en_value is not None, \
            f"Translation key '{key}' must exist in English translations"
        
        assert isinstance(zh_value, str), \
            f"Translation value for '{key}' in Chinese must be a string, got {type(zh_value)}"
        assert isinstance(en_value, str), \
            f"Translation value for '{key}' in English must be a string, got {type(en_value)}"
        
        assert len(zh_value.strip()) > 0, \
            f"Translation value for '{key}' in Chinese must not be empty"
        assert len(en_value.strip()) > 0, \
            f"Translation value for '{key}' in English must not be empty"
    
    def test_all_required_sections_exist(self):
        """
        Property: All required sections must exist in the dataLifecycle namespace.
        
        The data lifecycle feature requires specific sections for different
        functional areas: interface, tabs, tempData, sampleLibrary, review,
        annotationTask, enhancement, aiTrial, common, permissions, errors.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        
        required_sections = [
            'interface',
            'tabs',
            'tempData',
            'sampleLibrary',
            'review',
            'annotationTask',
            'enhancement',
            'aiTrial',
            'common',
            'permissions',
            'errors',
        ]
        
        for section in required_sections:
            assert section in zh_translations, \
                f"Required section '{section}' must exist in dataLifecycle translations"
    
    def test_all_required_actions_exist(self):
        """
        Property: All required action labels must exist in common section.
        
        Common actions like save, cancel, delete, edit, view must be available
        for use across all data lifecycle components.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        required_actions = [
            'common.actions.save',
            'common.actions.cancel',
            'common.actions.confirm',
            'common.actions.delete',
            'common.actions.edit',
            'common.actions.view',
            'common.actions.refresh',
            'common.actions.search',
            'common.actions.filter',
            'common.actions.export',
            'common.actions.import',
        ]
        
        for action_key in required_actions:
            # Check Chinese
            zh_value = zh_translations
            en_value = en_translations
            
            key_parts = action_key.split('.')
            for part in key_parts:
                if isinstance(zh_value, dict) and part in zh_value:
                    zh_value = zh_value[part]
                else:
                    zh_value = None
                if isinstance(en_value, dict) and part in en_value:
                    en_value = en_value[part]
                else:
                    en_value = None
            
            assert zh_value is not None and isinstance(zh_value, str) and len(zh_value.strip()) > 0, \
                f"Required action '{action_key}' must exist in Chinese translations"
            assert en_value is not None and isinstance(en_value, str) and len(en_value.strip()) > 0, \
                f"Required action '{action_key}' must exist in English translations"
    
    def test_all_required_status_messages_exist(self):
        """
        Property: All required status messages must exist in common section.
        
        Common status messages like loading, success, error, warning, empty
        must be available for use across all data lifecycle components.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        required_statuses = [
            'common.status.loading',
            'common.status.error',
            'common.status.success',
            'common.status.warning',
            'common.status.empty',
        ]
        
        for status_key in required_statuses:
            # Check Chinese
            zh_value = zh_translations
            en_value = en_translations
            
            key_parts = status_key.split('.')
            for part in key_parts:
                if isinstance(zh_value, dict) and part in zh_value:
                    zh_value = zh_value[part]
                else:
                    zh_value = None
                if isinstance(en_value, dict) and part in en_value:
                    en_value = en_value[part]
                else:
                    en_value = None
            
            assert zh_value is not None and isinstance(zh_value, str) and len(zh_value.strip()) > 0, \
                f"Required status '{status_key}' must exist in Chinese translations"
            assert en_value is not None and isinstance(en_value, str) and len(en_value.strip()) > 0, \
                f"Required status '{status_key}' must exist in English translations"
    
    def test_all_required_error_messages_exist(self):
        """
        Property: All required error messages must exist in errors section.
        
        Error messages for common error scenarios like permission denied,
        data not found, validation error must be available.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        required_errors = [
            'errors.permissionDenied',
            'errors.dataNotFound',
            'errors.invalidState',
            'errors.validationError',
            'errors.concurrentModification',
            'errors.operationFailed',
            'errors.unknown',
        ]
        
        for error_key in required_errors:
            # Check Chinese
            zh_value = zh_translations
            en_value = en_translations
            
            key_parts = error_key.split('.')
            for part in key_parts:
                if isinstance(zh_value, dict) and part in zh_value:
                    zh_value = zh_value[part]
                else:
                    zh_value = None
                if isinstance(en_value, dict) and part in en_value:
                    en_value = en_value[part]
                else:
                    en_value = None
            
            assert zh_value is not None and isinstance(zh_value, str) and len(zh_value.strip()) > 0, \
                f"Required error message '{error_key}' must exist in Chinese translations"
            assert en_value is not None and isinstance(en_value, str) and len(en_value.strip()) > 0, \
                f"Required error message '{error_key}' must exist in English translations"
    
    def test_all_required_permissions_exist(self):
        """
        Property: All required permission labels must exist in permissions section.
        
        Permission labels for view, create, edit, delete, approve, admin
        must be available for the permission system.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        required_permissions = [
            'permissions.view',
            'permissions.create',
            'permissions.edit',
            'permissions.delete',
            'permissions.approve',
            'permissions.admin',
        ]
        
        for perm_key in required_permissions:
            # Check Chinese
            zh_value = zh_translations
            en_value = en_translations
            
            key_parts = perm_key.split('.')
            for part in key_parts:
                if isinstance(zh_value, dict) and part in zh_value:
                    zh_value = zh_value[part]
                else:
                    zh_value = None
                if isinstance(en_value, dict) and part in en_value:
                    en_value = en_value[part]
                else:
                    en_value = None
            
            assert zh_value is not None and isinstance(zh_value, str) and len(zh_value.strip()) > 0, \
                f"Required permission label '{perm_key}' must exist in Chinese translations"
            assert en_value is not None and isinstance(en_value, str) and len(en_value.strip()) > 0, \
                f"Required permission label '{perm_key}' must exist in English translations"
    
    def test_tabs_section_has_all_required_tabs(self):
        """
        Property: The tabs section must have all required tabs.
        
        The data lifecycle page requires tabs for: tempData, sampleLibrary,
        review, annotation, enhancement, aiTrial.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        
        required_tabs = [
            'tabs.tempData',
            'tabs.sampleLibrary',
            'tabs.review',
            'tabs.annotation',
            'tabs.enhancement',
            'tabs.aiTrial',
        ]
        
        for tab_key in required_tabs:
            # Navigate to the tab key
            zh_value = zh_translations
            key_parts = tab_key.split('.')
            for part in key_parts:
                if isinstance(zh_value, dict) and part in zh_value:
                    zh_value = zh_value[part]
                else:
                    zh_value = None
            
            assert zh_value is not None and isinstance(zh_value, str) and len(zh_value.strip()) > 0, \
                f"Required tab '{tab_key}' must exist in Chinese translations"
    
    def test_i18n_config_includes_data_lifecycle_namespace(self):
        """
        Property: The i18n config must include the dataLifecycle namespace.
        
        The react-i18next configuration must register the dataLifecycle
        namespace for it to be available to components.
        """
        config_path = TRANSLATIONS_DIR.parent / "config.ts"
        
        assert config_path.exists(), \
            f"i18n config file must exist at {config_path}"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Assert: Config must import and register dataLifecycle
        assert 'dataLifecycle' in config_content, \
            "i18n config must import dataLifecycle translations"
        assert "'dataLifecycle'" in config_content or '"dataLifecycle"' in config_content, \
            "i18n config must include 'dataLifecycle' in ns array"
    
    def test_nav_groups_has_data_lifecycle_menu_item(self):
        """
        Property: The navigation configuration must include data lifecycle.
        
        The sidebar navigation must have a menu item for data lifecycle
        to allow users to access the feature.
        """
        nav_groups_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "config" / "navGroups.ts"
        
        assert nav_groups_path.exists(), \
            f"Navigation groups file must exist at {nav_groups_path}"
        
        with open(nav_groups_path, 'r', encoding='utf-8') as f:
            nav_content = f.read()
        
        # Assert: Navigation must include dataLifecycle
        assert 'dataLifecycle' in nav_content, \
            "Navigation groups must include dataLifecycle menu item"
    
    def test_common_menu_translations_include_data_lifecycle(self):
        """
        Property: The common menu translations must include data lifecycle.
        
        The menu translation keys in common.json must include dataLifecycle
        for the sidebar menu to display correctly.
        """
        zh_common = load_translation_file('zh', 'common')
        
        # Check if menu.dataLifecycle exists
        menu_value = zh_common
        for key in ['menu', 'dataLifecycle']:
            if isinstance(menu_value, dict) and key in menu_value:
                menu_value = menu_value[key]
            else:
                menu_value = None
        
        assert menu_value is not None and isinstance(menu_value, str) and len(menu_value.strip()) > 0, \
            "menu.dataLifecycle translation must exist in common.json"


# ============================================================================
# Integration Tests for i18n Completeness
# ============================================================================

@pytest.mark.integration
class TestI18nIntegration:
    """Integration tests for i18n completeness across the frontend."""
    
    def test_all_component_keys_are_translated(self):
        """
        Integration test: All keys used in DataLifecycle components must be translated.
        
        This test verifies that the translation files contain all the keys
        that are used in the DataLifecycle page and component files.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        # Keys that must exist based on component usage
        required_keys = [
            'interface.title',
            'interface.pageTitle',
            'tabs.tempData',
            'tabs.sampleLibrary',
            'tabs.review',
            'tabs.annotation',
            'tabs.enhancement',
            'tabs.aiTrial',
            'tempData.title',
            'tempData.description',
            'tempData.columns.id',
            'tempData.columns.name',
            'tempData.columns.state',
            'tempData.columns.createdAt',
            'tempData.columns.actions',
            'tempData.states.draft',
            'tempData.states.processing',
            'tempData.states.ready',
            'tempData.actions.create',
            'tempData.actions.edit',
            'tempData.actions.delete',
            'sampleLibrary.title',
            'sampleLibrary.columns.id',
            'sampleLibrary.columns.name',
            'sampleLibrary.columns.qualityScore',
            'sampleLibrary.actions.addToLibrary',
            'review.title',
            'review.columns.id',
            'review.columns.status',
            'review.actions.approve',
            'review.actions.reject',
            'annotationTask.title',
            'annotationTask.columns.id',
            'annotationTask.columns.status',
            'annotationTask.columns.priority',
            'annotationTask.actions.create',
            'enhancement.title',
            'enhancement.columns.id',
            'enhancement.columns.status',
            'enhancement.columns.progress',
            'enhancement.actions.create',
            'aiTrial.title',
            'aiTrial.columns.id',
            'aiTrial.columns.status',
            'aiTrial.columns.successRate',
            'aiTrial.actions.create',
            'common.actions.save',
            'common.actions.cancel',
            'common.actions.delete',
            'common.status.loading',
            'common.messages.confirmDelete',
            'common.messages.operationSuccess',
            'common.messages.operationFailed',
            'common.pagination.total',
            'errors.permissionDenied',
            'errors.dataNotFound',
            'errors.validationError',
            'permissions.view',
            'permissions.create',
            'permissions.edit',
            'permissions.delete',
        ]
        
        # Flatten translations for easier lookup
        zh_flat = flatten_dict(zh_translations)
        en_flat = flatten_dict(en_translations)
        
        missing_zh = []
        missing_en = []
        
        for key in required_keys:
            if key not in zh_flat or not zh_flat[key]:
                missing_zh.append(key)
            if key not in en_flat or not en_flat[key]:
                missing_en.append(key)
        
        assert len(missing_zh) == 0, \
            f"Missing keys in Chinese translations: {missing_zh}"
        assert len(missing_en) == 0, \
            f"Missing keys in English translations: {missing_en}"
    
    def test_translation_files_are_synced(self):
        """
        Integration test: zh and en translation files must be kept in sync.
        
        This test verifies that both translation files have the same structure
        and that no keys are added to one language without the other.
        """
        zh_translations = load_translation_file('zh', 'dataLifecycle')
        en_translations = load_translation_file('en', 'dataLifecycle')
        
        # Get all keys from both files
        zh_keys = set(get_all_keys(zh_translations))
        en_keys = set(get_all_keys(en_translations))
        
        # Find differences
        missing_in_en = zh_keys - en_keys
        missing_in_zh = en_keys - zh_keys
        
        assert len(missing_in_en) == 0, \
            f"Keys missing in English translations: {missing_in_en}"
        assert len(missing_in_zh) == 0, \
            f"Keys missing in Chinese translations: {missing_in_zh}"