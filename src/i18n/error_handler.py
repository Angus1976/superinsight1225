"""
i18n 错误处理模块
提供全面的错误处理、日志记录和回退机制
"""

import logging
from typing import Optional, Dict, Any, Union
from contextvars import ContextVar
from functools import wraps

# 配置 i18n 专用日志记录器
logger = logging.getLogger('i18n')
logger.setLevel(logging.INFO)

# 如果没有处理器，添加一个控制台处理器
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# 错误统计上下文变量
_error_stats: ContextVar[Dict[str, int]] = ContextVar('error_stats', default={})


class I18nError(Exception):
    """i18n 系统基础异常类"""
    pass


class TranslationKeyError(I18nError):
    """翻译键不存在异常"""
    def __init__(self, key: str, language: str):
        self.key = key
        self.language = language
        super().__init__(f"Translation key '{key}' not found for language '{language}'")


class UnsupportedLanguageError(I18nError):
    """不支持的语言异常"""
    def __init__(self, language: str, supported_languages: list):
        self.language = language
        self.supported_languages = supported_languages
        super().__init__(f"Language '{language}' not supported. Supported: {supported_languages}")


class ParameterSubstitutionError(I18nError):
    """参数替换异常"""
    def __init__(self, key: str, language: str, error: str):
        self.key = key
        self.language = language
        self.error = error
        super().__init__(f"Parameter substitution failed for key '{key}' in '{language}': {error}")


class TranslationSystemError(I18nError):
    """翻译系统内部错误"""
    pass


def log_translation_error(error_type: str, details: Dict[str, Any], level: str = 'warning') -> None:
    """
    记录翻译相关错误
    
    Args:
        error_type: 错误类型
        details: 错误详情
        level: 日志级别 ('debug', 'info', 'warning', 'error', 'critical')
    """
    # 更新错误统计
    try:
        stats = _error_stats.get({})
        stats[error_type] = stats.get(error_type, 0) + 1
        _error_stats.set(stats)
    except Exception:
        # 如果统计更新失败，不影响主要功能
        pass
    
    # 记录日志
    log_message = f"I18n {error_type}: {details}"
    
    if level == 'debug':
        logger.debug(log_message)
    elif level == 'info':
        logger.info(log_message)
    elif level == 'warning':
        logger.warning(log_message)
    elif level == 'error':
        logger.error(log_message)
    elif level == 'critical':
        logger.critical(log_message)
    else:
        logger.warning(log_message)


def handle_missing_translation_key(key: str, language: str, fallback_language: str = 'zh') -> str:
    """
    处理缺失的翻译键
    
    Args:
        key: 翻译键
        language: 请求的语言
        fallback_language: 回退语言
        
    Returns:
        回退文本（键本身或回退语言的翻译）
    """
    log_translation_error(
        'missing_key',
        {
            'key': key,
            'requested_language': language,
            'fallback_language': fallback_language
        },
        'warning'
    )
    
    # 如果请求的语言就是回退语言，直接返回键
    if language == fallback_language:
        return key
    
    # 尝试从回退语言获取翻译
    try:
        from .translations import TRANSLATIONS
        if fallback_language in TRANSLATIONS and key in TRANSLATIONS[fallback_language]:
            fallback_text = TRANSLATIONS[fallback_language][key]
            log_translation_error(
                'fallback_used',
                {
                    'key': key,
                    'requested_language': language,
                    'fallback_language': fallback_language,
                    'fallback_text': fallback_text
                },
                'info'
            )
            return fallback_text
    except Exception as e:
        log_translation_error(
            'fallback_failed',
            {
                'key': key,
                'requested_language': language,
                'fallback_language': fallback_language,
                'error': str(e)
            },
            'error'
        )
    
    # 最终回退：返回键本身
    return key


def handle_unsupported_language(language: str, supported_languages: list, fallback_language: str = 'zh') -> str:
    """
    处理不支持的语言
    
    Args:
        language: 请求的语言
        supported_languages: 支持的语言列表
        fallback_language: 回退语言
        
    Returns:
        回退语言代码
    """
    log_translation_error(
        'unsupported_language',
        {
            'requested_language': language,
            'supported_languages': supported_languages,
            'fallback_language': fallback_language
        },
        'warning'
    )
    
    # 确保回退语言是支持的
    if fallback_language in supported_languages:
        return fallback_language
    
    # 如果回退语言也不支持，使用第一个支持的语言
    if supported_languages:
        emergency_fallback = supported_languages[0]
        log_translation_error(
            'emergency_fallback',
            {
                'requested_language': language,
                'fallback_language': fallback_language,
                'emergency_fallback': emergency_fallback
            },
            'error'
        )
        return emergency_fallback
    
    # 极端情况：没有支持的语言
    log_translation_error(
        'no_supported_languages',
        {
            'requested_language': language,
            'supported_languages': supported_languages
        },
        'critical'
    )
    return 'zh'  # 硬编码回退


def handle_parameter_substitution_error(
    key: str, 
    language: str, 
    text: str, 
    parameters: Dict[str, Any], 
    error: Exception
) -> str:
    """
    处理参数替换错误
    
    Args:
        key: 翻译键
        language: 语言代码
        text: 原始文本
        parameters: 替换参数
        error: 异常对象
        
    Returns:
        安全的文本（移除参数占位符或返回原始文本）
    """
    log_translation_error(
        'parameter_substitution_error',
        {
            'key': key,
            'language': language,
            'text': text,
            'parameters': parameters,
            'error': str(error),
            'error_type': type(error).__name__
        },
        'warning'
    )
    
    # 尝试返回不带参数的原始文本
    try:
        # 移除所有 {参数} 占位符
        import re
        safe_text = re.sub(r'\{[^}]*\}', '', text)
        if safe_text.strip():
            return safe_text.strip()
    except Exception as cleanup_error:
        log_translation_error(
            'text_cleanup_failed',
            {
                'key': key,
                'language': language,
                'original_error': str(error),
                'cleanup_error': str(cleanup_error)
            },
            'error'
        )
    
    # 最终回退：返回原始文本
    return text


def safe_translation_wrapper(func):
    """
    翻译函数的安全包装器装饰器
    确保翻译函数在任何情况下都不会抛出异常
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TranslationKeyError as e:
            return handle_missing_translation_key(e.key, e.language)
        except UnsupportedLanguageError as e:
            # 对于语言错误，需要特殊处理
            log_translation_error(
                'function_language_error',
                {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'error': str(e)
                },
                'error'
            )
            # 返回一个安全的默认值
            if args:
                return str(args[0])  # 通常第一个参数是键
            return "Translation Error"
        except ParameterSubstitutionError as e:
            return handle_parameter_substitution_error(e.key, e.language, "", {}, e)
        except Exception as e:
            log_translation_error(
                'unexpected_error',
                {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'error': str(e),
                    'error_type': type(e).__name__
                },
                'error'
            )
            # 返回一个安全的默认值
            if args:
                return str(args[0])
            return "System Error"
    
    return wrapper


def validate_translation_system() -> Dict[str, Any]:
    """
    验证翻译系统的完整性
    
    Returns:
        验证结果字典
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'statistics': {}
    }
    
    try:
        from .translations import TRANSLATIONS, get_supported_languages
        
        supported_languages = get_supported_languages()
        validation_result['statistics']['supported_languages'] = len(supported_languages)
        
        if not supported_languages:
            validation_result['is_valid'] = False
            validation_result['errors'].append('No supported languages found')
            return validation_result
        
        # 检查每种语言的翻译完整性
        all_keys = set()
        language_keys = {}
        
        for lang in supported_languages:
            if lang not in TRANSLATIONS:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f'Language {lang} not found in translations')
                continue
            
            lang_keys = set(TRANSLATIONS[lang].keys())
            language_keys[lang] = lang_keys
            all_keys.update(lang_keys)
        
        validation_result['statistics']['total_keys'] = len(all_keys)
        
        # 检查翻译键的一致性
        for lang in supported_languages:
            if lang not in language_keys:
                continue
            
            missing_keys = all_keys - language_keys[lang]
            if missing_keys:
                validation_result['warnings'].append(
                    f'Language {lang} missing keys: {list(missing_keys)[:5]}...'
                )
        
        # 检查错误统计
        try:
            error_stats = _error_stats.get({})
            validation_result['statistics']['error_counts'] = error_stats
        except Exception:
            pass
        
    except Exception as e:
        validation_result['is_valid'] = False
        validation_result['errors'].append(f'System validation failed: {str(e)}')
        log_translation_error(
            'system_validation_error',
            {'error': str(e)},
            'error'
        )
    
    return validation_result


def get_error_statistics() -> Dict[str, int]:
    """
    获取错误统计信息
    
    Returns:
        错误类型和计数的字典
    """
    try:
        return _error_stats.get({}).copy()
    except Exception:
        return {}


def reset_error_statistics() -> None:
    """
    重置错误统计信息
    """
    try:
        _error_stats.set({})
    except Exception:
        pass


def ensure_system_stability() -> bool:
    """
    确保系统稳定性检查
    
    Returns:
        系统是否稳定
    """
    try:
        validation = validate_translation_system()
        
        # 如果有严重错误，记录并返回 False
        if not validation['is_valid']:
            log_translation_error(
                'system_instability',
                {
                    'errors': validation['errors'],
                    'warnings': validation['warnings']
                },
                'critical'
            )
            return False
        
        # 检查错误率
        error_stats = get_error_statistics()
        total_errors = sum(error_stats.values())
        
        # 如果错误过多，记录警告
        if total_errors > 100:  # 可配置的阈值
            log_translation_error(
                'high_error_rate',
                {
                    'total_errors': total_errors,
                    'error_breakdown': error_stats
                },
                'warning'
            )
        
        return True
        
    except Exception as e:
        log_translation_error(
            'stability_check_failed',
            {'error': str(e)},
            'critical'
        )
        return False


# 导出的函数和类
__all__ = [
    'I18nError',
    'TranslationKeyError', 
    'UnsupportedLanguageError',
    'ParameterSubstitutionError',
    'TranslationSystemError',
    'log_translation_error',
    'handle_missing_translation_key',
    'handle_unsupported_language', 
    'handle_parameter_substitution_error',
    'safe_translation_wrapper',
    'validate_translation_system',
    'get_error_statistics',
    'reset_error_statistics',
    'ensure_system_stability'
]