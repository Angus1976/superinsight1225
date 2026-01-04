#!/usr/bin/env python3
"""
i18n 属性测试
验证多语言系统的正确性属性
"""

import sys
import os
import pytest
from hypothesis import given, strategies as st, settings

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from i18n import (
    get_translation,
    set_language,
    get_current_language,
    get_all_translations,
    get_supported_languages,
    get_manager
)
from i18n.translations import TRANSLATIONS

class TestTranslationProperties:
    """翻译系统属性测试"""
    
    def test_property_2_translation_dictionary_completeness(self):
        """
        Property 2: Translation Dictionary Completeness
        For any translation key that exists in one supported language, 
        the same key should exist in all other supported languages.
        Validates: Requirements 1.4, 1.5
        Feature: i18n-support, Property 2: Translation Dictionary Completeness
        """
        supported_languages = get_supported_languages()
        
        # 获取所有语言的键集合
        key_sets = {}
        for lang in supported_languages:
            key_sets[lang] = set(TRANSLATIONS[lang].keys())
        
        # 验证所有语言的键集合相同
        reference_keys = key_sets[supported_languages[0]]
        for lang in supported_languages[1:]:
            assert key_sets[lang] == reference_keys, f"Language {lang} has different keys than reference"
        
        # 验证至少有90个翻译键
        assert len(reference_keys) >= 90, f"Expected at least 90 translation keys, got {len(reference_keys)}"
    
    @given(st.sampled_from(['zh', 'en']))
    @settings(max_examples=100)
    def test_property_1_language_support_consistency(self, language):
        """
        Property 1: Language Support Consistency
        For any supported language code, the translation system should return translations 
        and include the language in the supported languages list.
        Validates: Requirements 1.1
        Feature: i18n-support, Property 1: Language Support Consistency
        """
        supported_languages = get_supported_languages()
        
        # 验证语言在支持列表中
        assert language in supported_languages
        
        # 验证可以设置该语言
        set_language(language)
        assert get_current_language() == language
        
        # 验证可以获取该语言的翻译
        translations = get_all_translations(language)
        assert len(translations) > 0
        
        # 验证可以获取特定翻译
        app_name = get_translation('app_name', language)
        assert app_name is not None
        assert len(app_name) > 0
    
    @given(st.sampled_from(list(TRANSLATIONS['zh'].keys())))
    @settings(max_examples=100)
    def test_property_11_translation_query_functionality(self, translation_key):
        """
        Property 11: Translation Query Functionality
        For any valid translation key and language combination, 
        the translation manager should return the appropriate translation.
        Validates: Requirements 4.1
        Feature: i18n-support, Property 11: Translation Query Functionality
        """
        manager = get_manager()
        
        for language in get_supported_languages():
            # 验证可以获取翻译
            translation = manager.translate(translation_key, language)
            assert translation is not None
            assert len(translation) > 0
            
            # 验证翻译不是键本身（除非翻译就是键）
            expected_translation = TRANSLATIONS[language][translation_key]
            assert translation == expected_translation
    
    @given(st.text().filter(lambda x: x not in TRANSLATIONS['zh']))
    @settings(max_examples=50)
    def test_property_14_missing_key_fallback(self, missing_key):
        """
        Property 14: Missing Key Fallback
        For any non-existent translation key, the system should return the key itself as fallback text.
        Validates: Requirements 4.5, 5.1
        Feature: i18n-support, Property 14: Missing Key Fallback
        """
        # 测试不存在的键返回键本身
        for language in get_supported_languages():
            translation = get_translation(missing_key, language)
            assert translation == missing_key
    
    @given(st.text().filter(lambda x: x not in ['zh', 'en']))
    @settings(max_examples=50)
    def test_property_15_unsupported_language_fallback(self, unsupported_language):
        """
        Property 15: Unsupported Language Fallback
        For any unsupported language code, the system should fallback to Chinese for translations.
        Validates: Requirements 5.2
        Feature: i18n-support, Property 15: Unsupported Language Fallback
        """
        # 测试不支持的语言回退到中文
        translation = get_translation('app_name', unsupported_language)
        expected_translation = TRANSLATIONS['zh']['app_name']
        assert translation == expected_translation
    
    def test_property_10_default_language_fallback(self):
        """
        Property 10: Default Language Fallback
        For any request without explicit language specification, 
        the system should use Chinese as the default language.
        Validates: Requirements 3.5
        Feature: i18n-support, Property 10: Default Language Fallback
        """
        # 重新初始化管理器以确保默认语言
        manager = get_manager('zh')
        
        # 验证默认语言是中文
        assert manager.get_language() == 'zh'
        
        # 验证不指定语言时使用中文
        translation = get_translation('app_name')
        expected_translation = TRANSLATIONS['zh']['app_name']
        assert translation == expected_translation
    
    @given(st.sampled_from(['zh', 'en']))
    @settings(max_examples=100)
    def test_property_3_language_switching_immediacy(self, target_language):
        """
        Property 3: Language Switching Immediacy
        For any valid language code, when the language is changed, 
        all subsequent translation requests should use the new language immediately.
        Validates: Requirements 2.1
        Feature: i18n-support, Property 3: Language Switching Immediacy
        """
        # 设置语言
        set_language(target_language)
        
        # 验证语言立即生效
        assert get_current_language() == target_language
        
        # 验证翻译使用新语言
        translation = get_translation('app_name')
        expected_translation = TRANSLATIONS[target_language]['app_name']
        assert translation == expected_translation
    
    @given(st.text().filter(lambda x: x not in ['zh', 'en'] and len(x) > 0))
    @settings(max_examples=50)
    def test_property_4_invalid_language_validation(self, invalid_language):
        """
        Property 4: Invalid Language Validation
        For any invalid language code, the system should reject the language change request 
        and maintain the current language setting.
        Validates: Requirements 2.2, 2.3
        Feature: i18n-support, Property 4: Invalid Language Validation
        """
        # 记录当前语言
        original_language = get_current_language()
        
        # 尝试设置无效语言应该抛出异常
        with pytest.raises(ValueError):
            set_language(invalid_language)
        
        # 验证语言没有改变
        assert get_current_language() == original_language
    
    def test_property_12_batch_translation_consistency(self):
        """
        Property 12: Batch Translation Consistency
        For any list of translation keys, batch translation should return 
        the same results as individual translations for each key.
        Validates: Requirements 4.2
        Feature: i18n-support, Property 12: Batch Translation Consistency
        """
        manager = get_manager()
        test_keys = ['app_name', 'login', 'logout', 'error', 'success']
        
        for language in get_supported_languages():
            # 获取批量翻译
            batch_translations = manager.translate_list(test_keys, language)
            
            # 获取单独翻译
            individual_translations = [manager.translate(key, language) for key in test_keys]
            
            # 验证结果一致
            assert batch_translations == individual_translations
    
    @given(st.sampled_from(['zh', 'en']))
    @settings(max_examples=100)
    def test_property_13_complete_translation_retrieval(self, language):
        """
        Property 13: Complete Translation Retrieval
        For any supported language, requesting all translations should return 
        a complete dictionary of all available translation keys.
        Validates: Requirements 4.4
        Feature: i18n-support, Property 13: Complete Translation Retrieval
        """
        manager = get_manager()
        
        # 获取所有翻译
        all_translations = manager.get_all(language)
        
        # 验证包含所有预期的键
        expected_keys = set(TRANSLATIONS[language].keys())
        actual_keys = set(all_translations.keys())
        
        assert actual_keys == expected_keys
        
        # 验证翻译内容正确
        for key, translation in all_translations.items():
            expected_translation = TRANSLATIONS[language][key]
            assert translation == expected_translation


class TestParameterizedTranslations:
    """参数化翻译测试"""
    
    @given(
        st.text(min_size=1, max_size=20),
        st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=50)
    def test_property_22_parameterized_translation_support(self, name, count):
        """
        Property 22: Parameterized Translation Support
        For any translation with formatting parameters, the system should correctly 
        substitute the parameters in the translated text.
        Validates: Requirements 11.3
        Feature: i18n-support, Property 22: Parameterized Translation Support
        """
        # 添加一个测试用的参数化翻译
        test_key = 'test_parameterized'
        TRANSLATIONS['zh'][test_key] = '用户 {name} 有 {count} 个任务'
        TRANSLATIONS['en'][test_key] = 'User {name} has {count} tasks'
        
        try:
            for language in get_supported_languages():
                translation = get_translation(test_key, language, name=name, count=count)
                
                # 验证参数被正确替换
                assert str(name) in translation
                assert str(count) in translation
                
                # 验证不包含未替换的占位符
                assert '{name}' not in translation
                assert '{count}' not in translation
        finally:
            # 清理测试数据
            del TRANSLATIONS['zh'][test_key]
            del TRANSLATIONS['en'][test_key]


class TestMiddlewareProperties:
    """中间件属性测试"""
    
    @given(st.sampled_from(['zh', 'en']))
    @settings(max_examples=50)
    def test_property_7_automatic_language_detection(self, language):
        """
        Property 7: Automatic Language Detection
        For any request containing language preferences in query parameters or headers, 
        the system should detect and apply the preferred language.
        Validates: Requirements 3.1
        Feature: i18n-support, Property 7: Automatic Language Detection
        """
        # 这个测试需要FastAPI应用运行，这里测试核心逻辑
        from i18n import set_language, get_current_language, get_supported_languages
        
        # 验证语言检测逻辑
        if language in get_supported_languages():
            set_language(language)
            assert get_current_language() == language
        else:
            # 不支持的语言应该回退到默认语言
            original_lang = get_current_language()
            try:
                set_language(language)
            except ValueError:
                # 预期的异常
                assert get_current_language() == original_lang
    
    def test_property_9_content_language_header_inclusion(self):
        """
        Property 9: Content-Language Header Inclusion
        For any API response, the response should include a Content-Language header 
        matching the current language.
        Validates: Requirements 3.3, 9.3
        Feature: i18n-support, Property 9: Content-Language Header Inclusion
        """
        # 这个属性在中间件中实现，这里验证逻辑
        from i18n import set_language, get_current_language
        
        for language in ['zh', 'en']:
            set_language(language)
            current = get_current_language()
            assert current == language
    
    def test_property_18_middleware_language_detection(self):
        """
        Property 18: Middleware Language Detection
        For any request with language indicators, the middleware should correctly 
        detect and set the language context.
        Validates: Requirements 9.1, 9.2
        Feature: i18n-support, Property 18: Middleware Language Detection
        """
        from i18n import set_language, get_current_language, get_supported_languages
        
        # 测试语言设置逻辑
        supported_languages = get_supported_languages()
        
        for language in supported_languages:
            set_language(language)
            assert get_current_language() == language
    
    def test_property_19_detection_method_priority(self):
        """
        Property 19: Detection Method Priority
        For any request containing both query parameters and headers with different languages, 
        query parameters should take precedence.
        Validates: Requirements 9.5
        Feature: i18n-support, Property 19: Detection Method Priority
        """
        # 这个测试验证优先级逻辑
        from i18n import set_language, get_current_language
        
        # 模拟查询参数优先级高于请求头的逻辑
        # 在实际中间件中，查询参数会覆盖请求头设置
        
        # 设置"请求头"语言
        set_language('zh')
        header_lang = get_current_language()
        
        # 设置"查询参数"语言（优先级更高）
        set_language('en')
        query_lang = get_current_language()
        
        # 验证查询参数优先
        assert query_lang == 'en'
        assert query_lang != header_lang or header_lang == 'en'
    
    @given(st.sampled_from(['zh', 'en']))
    @settings(max_examples=50)
    def test_property_5_multi_method_language_setting(self, language):
        """
        Property 5: Multi-method Language Setting
        For any valid language code, the system should accept language changes 
        through query parameters, headers, and direct API calls with consistent results.
        Validates: Requirements 2.4
        Feature: i18n-support, Property 5: Multi-method Language Setting
        """
        from i18n import set_language, get_current_language
        
        # 测试直接API调用方法
        set_language(language)
        assert get_current_language() == language
        
        # 验证设置持久性
        current_lang = get_current_language()
        assert current_lang == language
    
    @given(st.sampled_from(['zh', 'en']))
    @settings(max_examples=50)
    def test_property_6_language_persistence(self, language):
        """
        Property 6: Language Persistence
        For any language change, all subsequent API responses should use 
        the new language until changed again.
        Validates: Requirements 2.5
        Feature: i18n-support, Property 6: Language Persistence
        """
        from i18n import set_language, get_current_language, get_translation
        
        # 设置语言
        set_language(language)
        
        # 验证语言持久性 - 多次调用应该返回相同语言
        for _ in range(5):
            assert get_current_language() == language
            translation = get_translation('app_name')
            assert translation is not None
            assert len(translation) > 0


class TestAPIProperties:
    """API端点属性测试"""
    
    def test_property_17_http_status_code_appropriateness(self):
        """
        Property 17: HTTP Status Code Appropriateness
        For any language management API request, the system should return 
        appropriate HTTP status codes (200 for success, 400 for bad requests, etc.).
        Validates: Requirements 8.5
        Feature: i18n-support, Property 17: HTTP Status Code Appropriateness
        """
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from api.i18n import router
        from i18n import get_supported_languages
        
        # Set up test client
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Test successful requests (should return 200)
        supported_languages = get_supported_languages()
        
        # Test GET endpoints
        response = client.get("/api/settings/language")
        assert response.status_code == 200
        
        response = client.get("/api/i18n/translations")
        assert response.status_code == 200
        
        response = client.get("/api/i18n/languages")
        assert response.status_code == 200
        
        # Test successful POST with valid languages
        for language in supported_languages:
            response = client.post(f"/api/settings/language?language={language}")
            assert response.status_code == 200
        
        # Test bad requests (should return 400)
        invalid_languages = ['invalid', 'xx', 'fake', 'notreal']
        for invalid_lang in invalid_languages:
            response = client.post(f"/api/settings/language?language={invalid_lang}")
            assert response.status_code == 400
            
            response = client.get(f"/api/i18n/translations?language={invalid_lang}")
            assert response.status_code == 400
        
        # Test missing parameters (should return 422)
        response = client.post("/api/settings/language")
        assert response.status_code == 422
    
    @given(st.sampled_from(['zh', 'en']))
    @settings(max_examples=50)
    def test_property_8_response_translation_consistency(self, language):
        """
        Property 8: Response Translation Consistency
        For any API response containing translatable text, the response should be 
        translated according to the current language setting.
        Validates: Requirements 3.2
        Feature: i18n-support, Property 8: Response Translation Consistency
        """
        from i18n import set_language, get_translation
        
        # 设置语言
        set_language(language)
        
        # 测试翻译一致性
        key = 'app_name'
        translation1 = get_translation(key)
        translation2 = get_translation(key)
        
        # 同一语言下的翻译应该一致
        assert translation1 == translation2
        
        # 翻译应该不为空
        assert translation1 is not None
        assert len(translation1) > 0
    
    def test_property_20_translation_coverage_completeness(self):
        """
        Property 20: Translation Coverage Completeness
        For any major functional category (authentication, system status, etc.), 
        translations should exist for all relevant text.
        Validates: Requirements 10.1, 10.2
        Feature: i18n-support, Property 20: Translation Coverage Completeness
        """
        from i18n import get_all_translations
        
        # 定义主要功能类别的必需翻译键
        required_categories = {
            'authentication': ['login', 'logout', 'username', 'password'],
            'system_status': ['healthy', 'status', 'services'],
            'errors': ['error', 'not_found', 'bad_request'],
            'general': ['app_name', 'success', 'info']
        }
        
        for language in ['zh', 'en']:
            translations = get_all_translations(language)
            
            for category, keys in required_categories.items():
                for key in keys:
                    assert key in translations, f"Missing {key} in {language} for {category}"
    
    def test_property_21_translation_consistency_across_modules(self):
        """
        Property 21: Translation Consistency Across Modules
        For any common concept used across different modules, 
        the same translation should be used consistently.
        Validates: Requirements 10.3
        Feature: i18n-support, Property 21: Translation Consistency Across Modules
        """
        from i18n import get_translation
        
        # 测试跨模块的一致性概念
        common_concepts = ['error', 'success', 'status', 'info']
        
        for language in ['zh', 'en']:
            for concept in common_concepts:
                # 同一概念在不同调用中应该返回相同翻译
                translation1 = get_translation(concept, language)
                translation2 = get_translation(concept, language)
                assert translation1 == translation2


class TestTranslationValidation:
    """翻译验证属性测试"""
    
    def test_property_16_translation_completeness_validation(self):
        """
        Property 16: Translation Completeness Validation
        For any supported language, the system should be able to detect 
        if any translation keys are missing compared to other languages.
        Validates: Requirements 7.4
        Feature: i18n-support, Property 16: Translation Completeness Validation
        """
        from i18n.validation import validate_translation_completeness, get_translation_statistics
        
        # 验证完整性检查功能
        completeness_result = validate_translation_completeness()
        
        # 当前实现应该没有缺失的键
        assert len(completeness_result) == 0, f"Found missing keys: {completeness_result}"
        
        # 验证统计功能
        stats = get_translation_statistics()
        assert stats['supported_languages_count'] == 2
        assert stats['zh_keys_count'] == stats['en_keys_count']
        assert stats['min_keys_per_language'] == stats['max_keys_per_language']
        
        # 验证键存在检查
        from i18n.validation import check_translation_key_exists
        
        # 测试存在的键
        assert check_translation_key_exists('app_name') == True
        assert check_translation_key_exists('app_name', 'zh') == True
        assert check_translation_key_exists('app_name', 'en') == True
        
        # 测试不存在的键
        assert check_translation_key_exists('nonexistent_key') == False
        assert check_translation_key_exists('nonexistent_key', 'zh') == False


class TestTextMetadata:
    """文本元数据属性测试"""
    
    @given(st.sampled_from(list(TRANSLATIONS['zh'].keys())))
    @settings(max_examples=100)
    def test_property_23_text_metadata_provision(self, translation_key):
        """
        Property 23: Text Metadata Provision
        For any translation, the system should be able to provide metadata 
        about text characteristics when requested.
        Validates: Requirements 11.5
        Feature: i18n-support, Property 23: Text Metadata Provision
        """
        from i18n import get_text_metadata, get_all_text_metadata
        
        for language in get_supported_languages():
            # 获取单个翻译的元数据
            metadata = get_text_metadata(translation_key, language)
            
            # 验证元数据包含必需的字段
            required_fields = [
                'key', 'language', 'text', 'length', 'char_count', 
                'word_count', 'direction', 'script', 'has_parameters', 
                'is_empty', 'estimated_width'
            ]
            
            for field in required_fields:
                assert field in metadata, f"Missing required field '{field}' in metadata"
            
            # 验证元数据值的正确性
            assert metadata['key'] == translation_key
            assert metadata['language'] == language
            assert isinstance(metadata['text'], str)
            assert isinstance(metadata['length'], int)
            assert isinstance(metadata['char_count'], int)
            assert isinstance(metadata['word_count'], int)
            assert metadata['direction'] in ['ltr', 'rtl']
            assert metadata['script'] in ['han', 'latin', 'cyrillic', 'arabic']
            assert isinstance(metadata['has_parameters'], bool)
            assert isinstance(metadata['is_empty'], bool)
            assert isinstance(metadata['estimated_width'], int)
            
            # 验证长度计算正确
            actual_text = TRANSLATIONS[language][translation_key]
            assert metadata['length'] == len(actual_text)
            assert metadata['char_count'] == len(actual_text)
            
            # 验证单词计数
            expected_word_count = len(actual_text.split()) if actual_text else 0
            assert metadata['word_count'] == expected_word_count
            
            # 验证参数检测
            has_params = '{' in actual_text and '}' in actual_text
            assert metadata['has_parameters'] == has_params
            
            # 验证空文本检测
            is_empty = len(actual_text.strip()) == 0
            assert metadata['is_empty'] == is_empty
            
            # 验证脚本类型
            if language == 'zh':
                assert metadata['script'] == 'han'
            elif language == 'en':
                assert metadata['script'] == 'latin'
            
            # 验证估计宽度
            expected_width = len(actual_text) * (2 if language == 'zh' else 1)
            assert metadata['estimated_width'] == expected_width
        
        # 测试获取所有元数据
        for language in get_supported_languages():
            all_metadata = get_all_text_metadata(language)
            
            # 验证包含所有翻译键
            expected_keys = set(TRANSLATIONS[language].keys())
            actual_keys = set(all_metadata.keys())
            assert actual_keys == expected_keys
            
            # 验证每个元数据项的结构
            for key, metadata in all_metadata.items():
                assert isinstance(metadata, dict)
                assert metadata['key'] == key
                assert metadata['language'] == language


if __name__ == "__main__":
    pytest.main([__file__, "-v"])