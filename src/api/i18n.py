"""
国际化 (i18n) API 端点
提供语言管理和翻译查询的 RESTful API
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, Dict, List

from i18n import (
    get_manager,
    set_language,
    get_current_language,
    get_all_translations,
    get_supported_languages,
    get_translation
)
from i18n.error_handler import (
    log_translation_error,
    UnsupportedLanguageError,
    TranslationSystemError,
    validate_translation_system,
    get_error_statistics
)
from i18n.api_error_handler import (
    safe_api_call,
    validate_language_parameter,
    validate_query_parameters,
    ValidationAPIError,
    LanguageNotSupportedAPIError,
    InternalServerAPIError,
    APIErrorResponse
)

# 创建路由器
router = APIRouter(prefix="/api", tags=["i18n"])

# 响应模型
class LanguageSettingsResponse(BaseModel):
    """语言设置响应模型"""
    current_language: str
    supported_languages: List[str]
    language_names: Dict[str, str]

class LanguageChangeRequest(BaseModel):
    """语言更改请求模型"""
    language: str

class LanguageChangeResponse(BaseModel):
    """语言更改响应模型"""
    message: str
    current_language: str

class TranslationsResponse(BaseModel):
    """翻译字典响应模型"""
    language: str
    translations: Dict[str, str]

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    message: str
    details: Optional[Dict] = None

class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    is_healthy: bool
    validation_result: Dict
    error_statistics: Dict[str, int]

class SupportedLanguagesResponse(BaseModel):
    """支持的语言列表响应模型"""
    supported_languages: List[str]
    language_names: Dict[str, str]


@router.get("/i18n/status", response_model=SystemStatusResponse)
@safe_api_call
async def get_i18n_system_status(request: Request):
    """
    获取 i18n 系统状态和健康检查
    
    Returns:
        SystemStatusResponse: 包含系统健康状态和统计信息
    """
    validation_result = validate_translation_system()
    error_stats = get_error_statistics()
    
    return SystemStatusResponse(
        is_healthy=validation_result['is_valid'],
        validation_result=validation_result,
        error_statistics=error_stats
    )


@router.get("/settings/language", response_model=LanguageSettingsResponse)
@safe_api_call
async def get_language_settings(request: Request):
    """
    获取当前语言设置
    
    Returns:
        LanguageSettingsResponse: 包含当前语言和支持的语言列表
    """
    manager = get_manager()
    current_lang = get_current_language()
    supported_langs = get_supported_languages()
    
    # 获取语言名称
    language_names = {}
    for lang in supported_langs:
        try:
            if lang == 'zh':
                language_names[lang] = get_translation("chinese", lang)
            elif lang == 'en':
                language_names[lang] = get_translation("english", lang)
            else:
                language_names[lang] = lang.upper()
        except Exception as name_error:
            log_translation_error(
                'language_name_error',
                {
                    'language': lang,
                    'error': str(name_error)
                },
                'warning'
            )
            language_names[lang] = lang.upper()  # 回退到大写语言代码
    
    return LanguageSettingsResponse(
        current_language=current_lang,
        supported_languages=supported_langs,
        language_names=language_names
    )


@router.post("/settings/language", response_model=LanguageChangeResponse)
@safe_api_call
async def set_language_setting(
    request: Request,
    language: str = Query(..., description="要设置的语言代码 (zh, en)")
):
    """
    设置当前语言
    
    Args:
        language: 语言代码 (zh 或 en)
        
    Returns:
        LanguageChangeResponse: 包含成功消息和当前语言
        
    Raises:
        ValidationAPIError: 当参数无效时
        LanguageNotSupportedAPIError: 当语言不被支持时
    """
    # 验证参数
    validated_params = validate_query_parameters(
        request,
        required_params=['language']
    )
    
    language = validated_params['language']
    supported_languages = get_supported_languages()
    
    # 验证语言
    validated_language = validate_language_parameter(language, supported_languages)
    
    # 设置语言
    set_language(validated_language)
    
    log_translation_error(
        'language_change_success',
        {'new_language': validated_language},
        'info'
    )
    
    return LanguageChangeResponse(
        message=get_translation("language_changed"),
        current_language=validated_language
    )


@router.get("/i18n/translations", response_model=TranslationsResponse)
@safe_api_call
async def get_translations(
    request: Request,
    language: Optional[str] = Query(None, description="语言代码，不指定则使用当前语言")
):
    """
    获取指定语言的所有翻译
    
    Args:
        language: 可选的语言代码，不指定则使用当前语言
        
    Returns:
        TranslationsResponse: 包含语言代码和翻译字典
        
    Raises:
        LanguageNotSupportedAPIError: 当语言代码无效时
    """
    # 如果没有指定语言，使用当前语言
    if language is None:
        language = get_current_language()
    else:
        # 验证语言参数
        supported_languages = get_supported_languages()
        language = validate_language_parameter(language, supported_languages)
    
    # 获取翻译字典
    manager = get_manager()
    translations = manager.get_all(language)
    
    if not translations:
        log_translation_error(
            'empty_translations',
            {'language': language},
            'warning'
        )
    
    return TranslationsResponse(
        language=language,
        translations=translations
    )


@router.get("/i18n/languages", response_model=SupportedLanguagesResponse)
@safe_api_call
async def get_supported_languages_endpoint(request: Request):
    """
    获取所有支持的语言列表
    
    Returns:
        SupportedLanguagesResponse: 包含支持的语言列表和语言名称
    """
    supported_langs = get_supported_languages()
    
    if not supported_langs:
        log_translation_error(
            'no_supported_languages',
            {},
            'critical'
        )
        raise InternalServerAPIError()
    
    # 获取语言名称
    language_names = {}
    for lang in supported_langs:
        try:
            if lang == 'zh':
                language_names[lang] = get_translation("chinese", lang)
            elif lang == 'en':
                language_names[lang] = get_translation("english", lang)
            else:
                language_names[lang] = lang.upper()
        except Exception as name_error:
            log_translation_error(
                'language_name_error',
                {
                    'language': lang,
                    'error': str(name_error)
                },
                'warning'
            )
            language_names[lang] = lang.upper()  # 回退到大写语言代码
    
    return SupportedLanguagesResponse(
        supported_languages=supported_langs,
        language_names=language_names
    )


# 导出路由器
__all__ = ['router']