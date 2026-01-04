"""
翻译管理器类
提供高级翻译功能和缓存
"""

from typing import Dict, Optional, List
from .translations import (
    get_translation,
    set_language,
    get_current_language,
    get_all_translations,
    get_supported_languages,
    get_text_metadata,
    get_all_text_metadata
)
from .error_handler import (
    safe_translation_wrapper,
    log_translation_error,
    ensure_system_stability
)

class TranslationManager:
    """
    翻译管理器
    提供翻译功能的统一接口
    """
    
    def __init__(self, default_language: str = 'zh'):
        """
        初始化翻译管理器
        
        Args:
            default_language: 默认语言代码
        """
        self.default_language = default_language
        
        # 确保系统稳定性
        if not ensure_system_stability():
            log_translation_error(
                'manager_init_warning',
                {'default_language': default_language},
                'warning'
            )
        
        set_language(default_language)
    
    def set_language(self, language: str) -> None:
        """
        设置当前语言
        
        Args:
            language: 语言代码
        """
        set_language(language)
    
    def get_language(self) -> str:
        """
        获取当前语言
        
        Returns:
            当前语言代码
        """
        return get_current_language()
    
    def translate(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        翻译文本
        
        Args:
            key: 翻译键
            language: 语言代码（可选）
            **kwargs: 格式化参数
        
        Returns:
            翻译后的文本
        """
        return get_translation(key, language, **kwargs)
    
    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        翻译文本的简写方法
        
        Args:
            key: 翻译键
            language: 语言代码（可选）
            **kwargs: 格式化参数
        
        Returns:
            翻译后的文本
        """
        return self.translate(key, language, **kwargs)
    
    def get_all(self, language: Optional[str] = None) -> Dict[str, str]:
        """
        获取所有翻译
        
        Args:
            language: 语言代码（可选）
        
        Returns:
            翻译字典
        """
        return get_all_translations(language)
    
    def get_supported_languages(self) -> List[str]:
        """
        获取支持的语言列表
        
        Returns:
            语言代码列表
        """
        return get_supported_languages()
    
    @safe_translation_wrapper
    def translate_dict(self, data: Dict, language: Optional[str] = None) -> Dict:
        """
        翻译字典中的所有值
        
        Args:
            data: 包含翻译键的字典
            language: 语言代码（可选）
        
        Returns:
            翻译后的字典
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and value.startswith('i18n:'):
                # 如果值以 'i18n:' 开头，则进行翻译
                translation_key = value[5:]  # 移除 'i18n:' 前缀
                result[key] = self.translate(translation_key, language)
            else:
                result[key] = value
        return result
    
    @safe_translation_wrapper
    def translate_list(self, items: List[str], language: Optional[str] = None) -> List[str]:
        """
        翻译列表中的所有项
        
        Args:
            items: 翻译键列表
            language: 语言代码（可选）
        
        Returns:
            翻译后的列表
        """
        return [self.translate(item, language) for item in items]
    
    def get_text_metadata(self, key: str, language: Optional[str] = None) -> Dict:
        """
        获取翻译文本的元数据
        
        Args:
            key: 翻译键
            language: 语言代码（可选）
        
        Returns:
            包含文本特征的元数据字典
        """
        return get_text_metadata(key, language)
    
    def get_all_text_metadata(self, language: Optional[str] = None) -> Dict[str, Dict]:
        """
        获取所有翻译文本的元数据
        
        Args:
            language: 语言代码（可选）
        
        Returns:
            包含所有翻译键元数据的字典
        """
        return get_all_text_metadata(language)


# 创建全局翻译管理器实例
_manager: Optional[TranslationManager] = None

def get_manager(default_language: str = 'zh') -> TranslationManager:
    """
    获取全局翻译管理器实例
    
    Args:
        default_language: 默认语言代码
    
    Returns:
        翻译管理器实例
    """
    global _manager
    if _manager is None:
        _manager = TranslationManager(default_language)
    return _manager
