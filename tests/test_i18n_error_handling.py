"""
i18n 错误处理单元测试
测试翻译系统的错误处理、回退机制和系统稳定性
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

from src.i18n.error_handler import (
    I18nError,
    TranslationKeyError,
    UnsupportedLanguageError,
    ParameterSubstitutionError,
    TranslationSystemError,
    log_translation_error,
    handle_missing_translation_key,
    handle_unsupported_language,
    handle_parameter_substitution_error,
    safe_translation_wrapper,
    validate_translation_system,
    get_error_statistics,
    reset_error_statistics,
    ensure_system_stability
)
from src.i18n.translations import (
    set_language,
    get_translation,
    get_all_translations,
    get_current_language,
    get_supported_languages
)


class TestI18nExceptions:
    """测试 i18n 异常类"""
    
    def test_translation_key_error(self):
        """测试翻译键错误异常"""
        error = TranslationKeyError("missing_key", "en")
        assert error.key == "missing_key"
        assert error.language == "en"
        assert "missing_key" in str(error)
        assert "en" in str(error)
    
    def test_unsupported_language_error(self):
        """测试不支持语言异常"""
        supported = ["zh", "en"]
        error = UnsupportedLanguageError("fr", supported)
        assert error.language == "fr"
        assert error.supported_languages == supported
        assert "fr" in str(error)
        assert "zh" in str(error)
    
    def test_parameter_substitution_error(self):
        """测试参数替换异常"""
        error = ParameterSubstitutionError("test_key", "zh", "KeyError: missing param")
        assert error.key == "test_key"
        assert error.language == "zh"
        assert error.error == "KeyError: missing param"


class TestErrorLogging:
    """测试错误日志记录"""
    
    def setup_method(self):
        """重置错误统计"""
        reset_error_statistics()
    
    def test_log_translation_error(self):
        """测试错误日志记录"""
        with patch('src.i18n.error_handler.logger') as mock_logger:
            log_translation_error(
                'test_error',
                {'key': 'value'},
                'warning'
            )
            
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert 'test_error' in call_args
            assert 'key' in call_args
    
    def test_error_statistics_tracking(self):
        """测试错误统计跟踪"""
        # 初始状态应该为空
        stats = get_error_statistics()
        assert stats == {}
        
        # 记录一些错误
        log_translation_error('error_type_1', {}, 'info')
        log_translation_error('error_type_1', {}, 'info')
        log_translation_error('error_type_2', {}, 'warning')
        
        # 检查统计
        stats = get_error_statistics()
        assert stats.get('error_type_1', 0) == 2
        assert stats.get('error_type_2', 0) == 1
        
        # 重置统计
        reset_error_statistics()
        stats = get_error_statistics()
        assert stats == {}


class TestMissingKeyHandling:
    """测试缺失翻译键处理"""
    
    def test_handle_missing_translation_key_same_language(self):
        """测试相同语言的缺失键处理"""
        result = handle_missing_translation_key("missing_key", "zh", "zh")
        assert result == "missing_key"
    
    def test_handle_missing_translation_key_fallback_exists(self):
        """测试回退语言存在翻译的情况"""
        # 使用已知存在的键进行测试
        result = handle_missing_translation_key("app_name", "invalid_lang", "zh")
        assert result == "SuperInsight 平台"  # 中文翻译
    
    def test_handle_missing_translation_key_fallback_missing(self):
        """测试回退语言也缺失翻译的情况"""
        result = handle_missing_translation_key("truly_missing_key", "en", "zh")
        assert result == "truly_missing_key"
    
    @patch('src.i18n.translations.TRANSLATIONS', {})
    def test_handle_missing_translation_key_no_translations(self):
        """测试翻译字典为空的情况"""
        result = handle_missing_translation_key("any_key", "zh", "zh")
        assert result == "any_key"


class TestUnsupportedLanguageHandling:
    """测试不支持语言处理"""
    
    def test_handle_unsupported_language_valid_fallback(self):
        """测试有效回退语言"""
        supported = ["zh", "en"]
        result = handle_unsupported_language("fr", supported, "zh")
        assert result == "zh"
    
    def test_handle_unsupported_language_invalid_fallback(self):
        """测试无效回退语言"""
        supported = ["zh", "en"]
        result = handle_unsupported_language("fr", supported, "invalid")
        assert result == "zh"  # 应该使用第一个支持的语言
    
    def test_handle_unsupported_language_no_supported(self):
        """测试没有支持语言的情况"""
        result = handle_unsupported_language("fr", [], "zh")
        assert result == "zh"  # 硬编码回退


class TestParameterSubstitutionHandling:
    """测试参数替换错误处理"""
    
    def test_handle_parameter_substitution_error_cleanup(self):
        """测试参数替换错误的文本清理"""
        text = "Hello {name}, you have {count} messages"
        result = handle_parameter_substitution_error(
            "test_key", "en", text, {"name": "John"}, KeyError("count")
        )
        # 应该移除参数占位符
        assert "{" not in result
        assert "}" not in result
        assert "Hello" in result
    
    def test_handle_parameter_substitution_error_cleanup_failure(self):
        """测试文本清理失败的情况"""
        text = "Hello {name}"
        
        with patch('re.sub', side_effect=Exception("Regex failed")):
            result = handle_parameter_substitution_error(
                "test_key", "en", text, {}, KeyError("name")
            )
            # 应该返回原始文本
            assert result == text


class TestSafeTranslationWrapper:
    """测试安全翻译包装器"""
    
    def test_safe_wrapper_normal_execution(self):
        """测试正常执行情况"""
        @safe_translation_wrapper
        def normal_function(x):
            return x * 2
        
        result = normal_function(5)
        assert result == 10
    
    def test_safe_wrapper_translation_key_error(self):
        """测试翻译键错误处理"""
        @safe_translation_wrapper
        def failing_function():
            raise TranslationKeyError("missing_key", "en")
        
        result = failing_function()
        assert result == "missing_key"  # 应该返回键本身
    
    def test_safe_wrapper_unsupported_language_error(self):
        """测试不支持语言错误处理"""
        @safe_translation_wrapper
        def failing_function(key):
            raise UnsupportedLanguageError("fr", ["zh", "en"])
        
        result = failing_function("test_key")
        assert result == "test_key"  # 应该返回第一个参数
    
    def test_safe_wrapper_parameter_substitution_error(self):
        """测试参数替换错误处理"""
        @safe_translation_wrapper
        def failing_function():
            raise ParameterSubstitutionError("key", "en", "error")
        
        result = failing_function()
        assert isinstance(result, str)  # 应该返回字符串
    
    def test_safe_wrapper_unexpected_error(self):
        """测试意外错误处理"""
        @safe_translation_wrapper
        def failing_function(key):
            raise ValueError("Unexpected error")
        
        result = failing_function("test_key")
        assert result == "test_key"  # 应该返回第一个参数
    
    def test_safe_wrapper_no_args_error(self):
        """测试无参数函数的错误处理"""
        @safe_translation_wrapper
        def failing_function():
            raise ValueError("Unexpected error")
        
        result = failing_function()
        assert result == "System Error"  # 默认错误消息


class TestSystemValidation:
    """测试系统验证功能"""
    
    def test_validate_translation_system_healthy(self):
        """测试健康的翻译系统验证"""
        result = validate_translation_system()
        
        assert isinstance(result, dict)
        assert 'is_valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'statistics' in result
        
        # 系统应该是健康的
        assert result['is_valid'] is True
        assert isinstance(result['errors'], list)
        assert isinstance(result['warnings'], list)
        assert isinstance(result['statistics'], dict)
    
    @patch('src.i18n.translations.get_supported_languages', return_value=[])
    def test_validate_translation_system_no_languages(self, mock_get_languages):
        """测试没有支持语言的情况"""
        result = validate_translation_system()
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert 'No supported languages found' in result['errors'][0]
    
    @patch('src.i18n.translations.get_supported_languages', side_effect=Exception("System error"))
    def test_validate_translation_system_exception(self, mock_get_languages):
        """测试系统验证异常情况"""
        result = validate_translation_system()
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert 'System validation failed' in result['errors'][0]


class TestSystemStability:
    """测试系统稳定性"""
    
    def setup_method(self):
        """重置错误统计"""
        reset_error_statistics()
    
    def test_ensure_system_stability_healthy(self):
        """测试健康系统的稳定性检查"""
        result = ensure_system_stability()
        assert result is True
    
    def test_ensure_system_stability_high_error_rate(self):
        """测试高错误率情况"""
        # 模拟大量错误
        for i in range(150):
            log_translation_error(f'error_{i % 5}', {}, 'warning')
        
        result = ensure_system_stability()
        # 即使有很多错误，系统仍应保持稳定（只是记录警告）
        assert result is True
    
    @patch('src.i18n.error_handler.validate_translation_system')
    def test_ensure_system_stability_validation_failure(self, mock_validate):
        """测试验证失败的情况"""
        mock_validate.return_value = {
            'is_valid': False,
            'errors': ['Critical error'],
            'warnings': []
        }
        
        result = ensure_system_stability()
        assert result is False
    
    @patch('src.i18n.error_handler.validate_translation_system', side_effect=Exception("Validation error"))
    def test_ensure_system_stability_exception(self, mock_validate):
        """测试稳定性检查异常"""
        result = ensure_system_stability()
        assert result is False


class TestTranslationFunctionErrorHandling:
    """测试翻译函数的错误处理"""
    
    def setup_method(self):
        """设置测试环境"""
        set_language('zh')
        reset_error_statistics()
    
    def test_get_translation_missing_key(self):
        """测试获取不存在的翻译键"""
        result = get_translation("definitely_missing_key")
        assert result == "definitely_missing_key"
    
    def test_get_translation_unsupported_language(self):
        """测试不支持的语言"""
        result = get_translation("app_name", "unsupported_lang")
        # 应该回退到中文
        assert result == "SuperInsight 平台"
    
    def test_get_translation_parameter_error(self):
        """测试参数替换错误"""
        # 使用带参数的翻译，但提供错误的参数
        result = get_translation("welcome_user", "zh", invalid_param="test")
        # 应该返回处理后的文本（移除了参数占位符）
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_set_language_unsupported(self):
        """测试设置不支持的语言"""
        original_lang = get_current_language()
        
        # 尝试设置不支持的语言
        set_language("unsupported_language")
        
        # 应该回退到支持的语言
        current_lang = get_current_language()
        assert current_lang in get_supported_languages()
    
    def test_get_all_translations_unsupported_language(self):
        """测试获取不支持语言的所有翻译"""
        result = get_all_translations("unsupported_lang")
        
        # 应该回退到中文翻译
        assert isinstance(result, dict)
        assert len(result) > 0
        assert "app_name" in result
        assert result["app_name"] == "SuperInsight 平台"


class TestErrorHandlingIntegration:
    """测试错误处理集成"""
    
    def setup_method(self):
        """设置测试环境"""
        set_language('zh')
        reset_error_statistics()
    
    def test_error_logging_integration(self):
        """测试错误日志记录集成"""
        # 触发一些错误
        get_translation("missing_key_1")
        get_translation("missing_key_2")
        set_language("invalid_language")
        
        # 检查错误统计
        stats = get_error_statistics()
        assert len(stats) > 0
    
    def test_system_resilience_under_errors(self):
        """测试系统在错误情况下的弹性"""
        # 触发各种错误
        for i in range(10):
            get_translation(f"missing_key_{i}")
            get_translation("app_name", f"invalid_lang_{i}")
        
        # 系统应该仍然正常工作
        assert get_translation("app_name") == "SuperInsight 平台"
        assert get_current_language() in get_supported_languages()
        
        # 稳定性检查应该通过
        assert ensure_system_stability() is True
    
    def test_concurrent_error_handling(self):
        """测试并发错误处理"""
        import threading
        import time
        
        errors = []
        
        def worker():
            try:
                for i in range(5):
                    get_translation(f"missing_key_{threading.current_thread().ident}_{i}")
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)
        
        # 启动多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 不应该有异常
        assert len(errors) == 0
        
        # 系统应该仍然稳定
        assert ensure_system_stability() is True


if __name__ == "__main__":
    pytest.main([__file__])