"""
FastAPI 语言中间件
自动处理请求中的语言设置和响应头
"""

from fastapi import Request, Response
from typing import Callable, Optional
import re

from .translations import set_language, get_current_language, get_supported_languages
from .error_handler import (
    log_translation_error,
    handle_unsupported_language,
    safe_translation_wrapper
)


def parse_accept_language(accept_language: str) -> Optional[str]:
    """
    解析 Accept-Language 请求头
    
    Args:
        accept_language: Accept-Language 请求头值
        
    Returns:
        最匹配的支持语言代码，如果没有匹配则返回 None
    """
    if not accept_language:
        return None
    
    try:
        supported_languages = get_supported_languages()
        
        # 解析 Accept-Language 头，格式如: "zh-CN,zh;q=0.9,en;q=0.8"
        languages = []
        for lang_item in accept_language.split(','):
            lang_item = lang_item.strip()
            if ';' in lang_item:
                lang, quality = lang_item.split(';', 1)
                try:
                    q_value = float(quality.split('=')[1])
                except (IndexError, ValueError):
                    q_value = 1.0
            else:
                lang = lang_item
                q_value = 1.0
            
            # 提取主要语言代码 (zh-CN -> zh, en-US -> en)
            main_lang = lang.split('-')[0].lower()
            languages.append((main_lang, q_value))
        
        # 按质量值排序
        languages.sort(key=lambda x: x[1], reverse=True)
        
        # 找到第一个支持的语言
        for lang, _ in languages:
            if lang in supported_languages:
                return lang
        
        return None
        
    except Exception as e:
        log_translation_error(
            'accept_language_parse_error',
            {
                'accept_language': accept_language,
                'error': str(e)
            },
            'warning'
        )
        return None


def detect_language_from_request(request: Request) -> str:
    """
    从请求中检测语言设置
    
    优先级：
    1. 查询参数 ?language=xx
    2. Accept-Language 请求头
    3. 默认语言 (zh)
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        检测到的语言代码
    """
    try:
        supported_languages = get_supported_languages()
        
        # 1. 检查查询参数（优先级最高）
        if "language" in request.query_params:
            language = request.query_params.get("language", "").lower()
            if language in supported_languages:
                return language
            else:
                # 记录无效的查询参数语言
                log_translation_error(
                    'invalid_query_language',
                    {
                        'requested_language': language,
                        'supported_languages': supported_languages,
                        'request_url': str(request.url)
                    },
                    'warning'
                )
        
        # 2. 检查 Accept-Language 请求头
        accept_language = request.headers.get("Accept-Language")
        if accept_language:
            detected_lang = parse_accept_language(accept_language)
            if detected_lang and detected_lang in supported_languages:
                return detected_lang
        
        # 3. 返回默认语言
        return "zh"
        
    except Exception as e:
        log_translation_error(
            'language_detection_error',
            {
                'error': str(e),
                'request_url': str(request.url) if request else 'unknown'
            },
            'error'
        )
        return "zh"  # 安全回退


async def language_middleware(request: Request, call_next: Callable) -> Response:
    """
    语言检测和设置中间件
    
    功能：
    - 自动检测请求中的语言偏好
    - 设置当前请求的语言上下文
    - 在响应中添加 Content-Language 头
    
    Args:
        request: FastAPI 请求对象
        call_next: 下一个中间件或路由处理器
        
    Returns:
        处理后的响应对象
    """
    try:
        # 检测语言
        detected_language = detect_language_from_request(request)
        
        # 设置当前语言上下文
        set_language(detected_language)
        
        # 处理请求
        response = await call_next(request)
        
        # 添加 Content-Language 响应头
        try:
            current_language = get_current_language()
            response.headers["Content-Language"] = current_language
        except Exception as header_error:
            log_translation_error(
                'response_header_error',
                {
                    'error': str(header_error),
                    'request_url': str(request.url)
                },
                'warning'
            )
            # 继续处理，不因为头部错误而失败
        
        return response
        
    except Exception as e:
        log_translation_error(
            'middleware_error',
            {
                'error': str(e),
                'error_type': type(e).__name__,
                'request_url': str(request.url) if request else 'unknown'
            },
            'error'
        )
        
        # 尝试设置默认语言并继续
        try:
            set_language('zh')
            response = await call_next(request)
            response.headers["Content-Language"] = 'zh'
            return response
        except Exception as fallback_error:
            log_translation_error(
                'middleware_fallback_error',
                {
                    'original_error': str(e),
                    'fallback_error': str(fallback_error)
                },
                'critical'
            )
            # 重新抛出原始异常
            raise e


def create_language_middleware():
    """
    创建语言中间件实例
    
    Returns:
        配置好的语言中间件函数
    """
    return language_middleware


# 导出的中间件函数
__all__ = [
    'language_middleware',
    'create_language_middleware',
    'detect_language_from_request',
    'parse_accept_language'
]