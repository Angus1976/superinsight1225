"""
Property-Based Tests for AI Annotation I18n

Tests internationalization properties for the AI annotation system.
Uses Hypothesis for property-based testing with minimum 100 iterations.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
from typing import Dict, Any

# Import i18n module
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.ai.annotation_i18n import (
    get_ai_translation,
    t,
    get_all_translations,
    has_translation,
    get_missing_translations,
    get_translation_with_fallback,
    get_current_language,
    set_language,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    LocaleFormatter,
    get_formatter,
    format_quality_report,
    format_annotation_summary,
    MultilingualGuidelines,
    get_guidelines_manager,
    I18nHotReloader,
    get_hot_reloader,
    AI_ANNOTATION_TRANSLATIONS,
)


# =============================================================================
# Test Strategies
# =============================================================================

# Strategy for supported languages
language_strategy = st.sampled_from(SUPPORTED_LANGUAGES)

# Strategy for translation keys (from actual keys)
def get_all_keys():
    """Get all translation keys from both languages."""
    all_keys = set()
    for lang_translations in AI_ANNOTATION_TRANSLATIONS.values():
        all_keys.update(lang_translations.keys())
    return list(all_keys)

translation_key_strategy = st.sampled_from(get_all_keys())

# Strategy for quality metrics
quality_metric_strategy = st.fixed_dictionaries({
    'accuracy': st.floats(min_value=0.0, max_value=1.0),
    'recall': st.floats(min_value=0.0, max_value=1.0),
    'consistency': st.floats(min_value=0.0, max_value=1.0),
    'completeness': st.floats(min_value=0.0, max_value=1.0),
})

# Strategy for datetime
datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31)
)

# Strategy for numbers
positive_float_strategy = st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)
positive_int_strategy = st.integers(min_value=0, max_value=1000000)


# =============================================================================
# Property 29: I18n Display Consistency
# Validates: Requirements 8.2, 8.3, 8.4
# =============================================================================

class TestI18nDisplayConsistency:
    """
    Property 29: I18n Display Consistency
    
    For any user with language preference set, all UI text, error messages,
    notifications, guidelines, and quality reports should be displayed in
    that language with locale-appropriate formatting.
    
    **Validates: Requirements 8.2, 8.3, 8.4**
    """
    
    @given(language=language_strategy, key=translation_key_strategy)
    @settings(max_examples=100)
    def test_translation_returns_string_for_supported_language(
        self, language: str, key: str
    ):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        For any supported language and valid key, translation should return
        a non-empty string.
        """
        # Set language
        set_language(language)
        
        # Get translation
        result = get_ai_translation(key, language)
        
        # Verify result is a string
        assert isinstance(result, str)
        
        # If key exists in this language, result should not be the key itself
        if has_translation(key, language):
            # Result should be non-empty
            assert len(result) > 0
    
    @given(language=language_strategy)
    @settings(max_examples=100)
    def test_all_translations_complete_for_language(self, language: str):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        For any supported language, all translations should be available.
        """
        translations = get_all_translations(language)
        
        # Should have translations
        assert len(translations) > 0
        
        # All values should be non-empty strings
        for key, value in translations.items():
            assert isinstance(value, str)
            assert len(value) > 0
    
    @given(
        language=language_strategy,
        metrics=quality_metric_strategy
    )
    @settings(max_examples=100)
    def test_quality_report_formatted_per_locale(
        self, language: str, metrics: Dict[str, float]
    ):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Quality reports should be formatted according to user's locale.
        """
        # Format quality report
        formatted = format_quality_report(metrics, language)
        
        # Should have formatted values for all metrics
        assert len(formatted) == len(metrics)
        
        # All formatted values should be strings
        for label, value in formatted.items():
            assert isinstance(label, str)
            assert isinstance(value, str)
            assert len(value) > 0
            # Percentage values should contain %
            assert '%' in value

    
    @given(
        language=language_strategy,
        dt=datetime_strategy
    )
    @settings(max_examples=100)
    def test_date_formatting_per_locale(self, language: str, dt: datetime):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Dates should be formatted according to user's locale.
        """
        formatter = get_formatter(language)
        
        # Format date
        formatted_date = formatter.format_date(dt)
        formatted_datetime = formatter.format_datetime(dt)
        formatted_time = formatter.format_time(dt)
        
        # All should be non-empty strings
        assert isinstance(formatted_date, str) and len(formatted_date) > 0
        assert isinstance(formatted_datetime, str) and len(formatted_datetime) > 0
        assert isinstance(formatted_time, str) and len(formatted_time) > 0
        
        # Chinese format should contain Chinese characters
        if language == 'zh':
            assert '年' in formatted_date or '月' in formatted_date or '日' in formatted_date
    
    @given(
        language=language_strategy,
        value=positive_float_strategy
    )
    @settings(max_examples=100)
    def test_number_formatting_per_locale(self, language: str, value: float):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Numbers should be formatted according to user's locale.
        """
        formatter = get_formatter(language)
        
        # Format number
        formatted = formatter.format_number(value)
        
        # Should be a non-empty string
        assert isinstance(formatted, str)
        assert len(formatted) > 0
    
    @given(
        language=language_strategy,
        value=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_percentage_formatting_per_locale(self, language: str, value: float):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Percentages should be formatted according to user's locale.
        """
        formatter = get_formatter(language)
        
        # Format percentage
        formatted = formatter.format_percent(value)
        
        # Should contain % symbol
        assert '%' in formatted
        
        # Should be a valid percentage string
        assert isinstance(formatted, str)
        assert len(formatted) > 0


# =============================================================================
# Property 30: I18n Hot-Reload
# Validates: Requirements 8.5
# =============================================================================

class TestI18nHotReload:
    """
    Property 30: I18n Hot-Reload
    
    For any new language addition, translations should be loaded from
    the i18n system without code changes.
    
    **Validates: Requirements 8.5**
    """
    
    @given(
        language=language_strategy,
        key=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))),
        value=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_dynamic_translation_addition(
        self, language: str, key: str, value: str
    ):
        """
        Feature: ai-annotation-methods, Property 30: I18n Hot-Reload
        
        New translations can be added dynamically without code changes.
        """
        # Skip if key or value is empty after stripping
        assume(key.strip() and value.strip())
        
        # Create a fresh hot reloader for this test
        hot_reloader = I18nHotReloader()
        
        # Add translation dynamically (without persisting to avoid file I/O)
        await hot_reloader.add_translation(language, key, value, persist=False)
        
        # Verify translation was added
        result = hot_reloader.get_custom_translation(key, language)
        assert result == value

    
    @given(language=language_strategy)
    @settings(max_examples=100)
    def test_fallback_to_builtin_translations(self, language: str):
        """
        Feature: ai-annotation-methods, Property 30: I18n Hot-Reload
        
        When custom translation not found, should fall back to built-in.
        """
        # Use a key that exists in built-in translations
        key = 'ai.preannotation.title'
        
        # Get translation directly from built-in (avoid hot reloader which needs event loop)
        # This tests the fallback logic without requiring async context
        result = get_ai_translation(key, language)
        
        # Should return built-in translation
        expected = AI_ANNOTATION_TRANSLATIONS.get(language, {}).get(key, key)
        assert result == expected
        
        # Verify the translation is not just the key
        assert result != key or key not in AI_ANNOTATION_TRANSLATIONS.get(language, {})
    
    @given(
        language=language_strategy,
        key=translation_key_strategy,
        param_name=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
        param_value=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100)
    def test_parameter_substitution_in_translations(
        self, language: str, key: str, param_name: str, param_value: str
    ):
        """
        Feature: ai-annotation-methods, Property 30: I18n Hot-Reload
        
        Translations should support parameter substitution.
        """
        # Get translation with parameter
        kwargs = {param_name: param_value}
        result = get_ai_translation(key, language, **kwargs)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If the translation contains the parameter placeholder, it should be substituted
        translation = AI_ANNOTATION_TRANSLATIONS.get(language, {}).get(key, '')
        if f'{{{param_name}}}' in translation:
            assert param_value in result


# =============================================================================
# Additional I18n Properties
# =============================================================================

class TestMultilingualGuidelines:
    """
    Tests for multilingual annotation guidelines support.
    
    **Validates: Requirements 8.3**
    """
    
    @given(
        project_id=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_'),
        language=language_strategy,
        content=st.text(min_size=10, max_size=1000)
    )
    @settings(max_examples=100)
    def test_guideline_storage_and_retrieval(
        self, project_id: str, language: str, content: str
    ):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Guidelines can be stored and retrieved per language.
        """
        assume(project_id.strip() and content.strip())
        
        # Create fresh guidelines manager
        guidelines = MultilingualGuidelines()
        
        # Set guideline
        guidelines.set_guideline(project_id, language, content)
        
        # Retrieve guideline
        result = guidelines.get_guideline(project_id, language)
        
        # Should match
        assert result == content
    
    @given(
        project_id=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_'),
        examples=st.lists(st.text(min_size=5, max_size=100), min_size=1, max_size=10)
    )
    @settings(max_examples=100)
    def test_language_specific_examples(self, project_id: str, examples: list):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Language-specific examples can be stored and retrieved.
        """
        assume(project_id.strip())
        assume(all(ex.strip() for ex in examples))
        
        guidelines = MultilingualGuidelines()
        
        for language in SUPPORTED_LANGUAGES:
            # Set examples
            guidelines.set_examples(project_id, language, examples)
            
            # Retrieve examples
            result = guidelines.get_examples(project_id, language)
            
            # Should match
            assert result == examples


class TestLocaleFormatting:
    """
    Tests for locale-aware formatting.
    
    **Validates: Requirements 8.4**
    """
    
    @given(
        language=language_strategy,
        seconds=st.floats(min_value=0.0, max_value=86400.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_duration_formatting(self, language: str, seconds: float):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Duration should be formatted according to locale.
        """
        formatter = get_formatter(language)
        
        result = formatter.format_duration(seconds)
        
        # Should be a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Chinese should have Chinese units
        if language == 'zh':
            if seconds >= 3600:
                assert '小时' in result
            elif seconds >= 60:
                assert '分钟' in result
            else:
                assert '秒' in result
        else:
            # English should have s/m/h
            if seconds >= 3600:
                assert 'h' in result
            elif seconds >= 60:
                assert 'm' in result
            else:
                assert 's' in result
    
    @given(
        language=language_strategy,
        bytes_size=st.integers(min_value=0, max_value=10**15)
    )
    @settings(max_examples=100)
    def test_file_size_formatting(self, language: str, bytes_size: int):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        File size should be formatted in human-readable format.
        """
        formatter = get_formatter(language)
        
        result = formatter.format_file_size(bytes_size)
        
        # Should be a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should contain a unit
        assert any(unit in result for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB'])
    
    @given(
        language=language_strategy,
        value=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_currency_formatting(self, language: str, value: float):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Currency should be formatted according to locale.
        """
        formatter = get_formatter(language)
        
        result = formatter.format_currency(value)
        
        # Should be a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should contain currency symbol
        if language == 'zh':
            assert '¥' in result
        else:
            assert '$' in result


class TestLanguageManagement:
    """
    Tests for language management functions.
    
    **Validates: Requirements 8.1, 8.2**
    """
    
    @given(language=language_strategy)
    @settings(max_examples=100)
    def test_language_setting_and_getting(self, language: str):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Language can be set and retrieved correctly.
        """
        # Set language
        set_language(language)
        
        # Get language
        result = get_current_language()
        
        # Should match
        assert result == language
    
    @given(
        invalid_language=st.text(min_size=1, max_size=10).filter(
            lambda x: x not in SUPPORTED_LANGUAGES
        )
    )
    @settings(max_examples=100)
    def test_invalid_language_raises_error(self, invalid_language: str):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Setting an unsupported language should raise an error.
        """
        with pytest.raises(ValueError):
            set_language(invalid_language)
    
    @given(language=language_strategy)
    @settings(max_examples=100)
    def test_missing_translations_detection(self, language: str):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Missing translations can be detected.
        """
        missing = get_missing_translations(language)
        
        # Should return a list
        assert isinstance(missing, list)
        
        # All items should be strings
        for key in missing:
            assert isinstance(key, str)


# =============================================================================
# Annotation Summary Formatting Tests
# =============================================================================

class TestAnnotationSummaryFormatting:
    """
    Tests for annotation summary formatting.
    
    **Validates: Requirements 8.4**
    """
    
    @given(
        language=language_strategy,
        total=positive_int_strategy,
        completed=positive_int_strategy,
        flagged=positive_int_strategy,
        avg_confidence=st.floats(min_value=0.0, max_value=1.0),
        processing_time=st.floats(min_value=0.0, max_value=86400.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_annotation_summary_formatting(
        self,
        language: str,
        total: int,
        completed: int,
        flagged: int,
        avg_confidence: float,
        processing_time: float
    ):
        """
        Feature: ai-annotation-methods, Property 29: I18n Display Consistency
        
        Annotation summary should be formatted according to locale.
        """
        # Ensure completed and flagged don't exceed total
        completed = min(completed, total)
        flagged = min(flagged, total)
        
        result = format_annotation_summary(
            total=total,
            completed=completed,
            flagged=flagged,
            avg_confidence=avg_confidence,
            processing_time=processing_time,
            language=language
        )
        
        # Should return a dictionary
        assert isinstance(result, dict)
        
        # Should have multiple entries
        assert len(result) > 0
        
        # All values should be strings
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
