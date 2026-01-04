"""
翻译验证模块
提供翻译完整性和一致性验证功能
"""

from typing import Dict, List, Set, Tuple, Optional
from .translations import TRANSLATIONS, get_supported_languages

class TranslationValidationError(Exception):
    """翻译验证错误"""
    pass

class TranslationValidator:
    """翻译验证器"""
    
    def __init__(self):
        self.translations = TRANSLATIONS
        self.supported_languages = get_supported_languages()
    
    def validate_completeness(self) -> Dict[str, List[str]]:
        """
        验证翻译完整性
        
        Returns:
            包含缺失翻译键的字典，格式为 {language: [missing_keys]}
        """
        missing_keys = {}
        
        # 获取所有语言的键集合
        all_keys_by_language = {}
        for language in self.supported_languages:
            all_keys_by_language[language] = set(self.translations[language].keys())
        
        # 找出所有键的并集
        all_possible_keys = set()
        for keys in all_keys_by_language.values():
            all_possible_keys.update(keys)
        
        # 检查每种语言缺失的键
        for language in self.supported_languages:
            language_keys = all_keys_by_language[language]
            missing = all_possible_keys - language_keys
            if missing:
                missing_keys[language] = sorted(list(missing))
        
        return missing_keys
    
    def validate_consistency(self) -> List[str]:
        """
        验证翻译一致性
        检查所有语言是否有相同的翻译键集合
        
        Returns:
            不一致的错误信息列表
        """
        errors = []
        
        if len(self.supported_languages) < 2:
            return errors
        
        # 获取参考语言（第一种语言）的键集合
        reference_language = self.supported_languages[0]
        reference_keys = set(self.translations[reference_language].keys())
        
        # 检查其他语言的键集合
        for language in self.supported_languages[1:]:
            language_keys = set(self.translations[language].keys())
            
            # 检查缺失的键
            missing_keys = reference_keys - language_keys
            if missing_keys:
                errors.append(f"Language '{language}' is missing keys: {sorted(missing_keys)}")
            
            # 检查多余的键
            extra_keys = language_keys - reference_keys
            if extra_keys:
                errors.append(f"Language '{language}' has extra keys: {sorted(extra_keys)}")
        
        return errors
    
    def validate_key_existence(self, key: str) -> Dict[str, bool]:
        """
        验证翻译键在所有语言中的存在性
        
        Args:
            key: 要验证的翻译键
        
        Returns:
            每种语言中键存在性的字典，格式为 {language: exists}
        """
        existence = {}
        for language in self.supported_languages:
            existence[language] = key in self.translations[language]
        return existence
    
    def validate_empty_translations(self) -> Dict[str, List[str]]:
        """
        验证空翻译
        检查是否有空字符串或None值的翻译
        
        Returns:
            包含空翻译的字典，格式为 {language: [empty_keys]}
        """
        empty_translations = {}
        
        for language in self.supported_languages:
            empty_keys = []
            for key, value in self.translations[language].items():
                if not value or (isinstance(value, str) and value.strip() == ""):
                    empty_keys.append(key)
            
            if empty_keys:
                empty_translations[language] = empty_keys
        
        return empty_translations
    
    def validate_translation_format(self) -> Dict[str, List[str]]:
        """
        验证翻译格式
        检查翻译值是否为字符串类型
        
        Returns:
            包含格式错误的字典，格式为 {language: [invalid_keys]}
        """
        format_errors = {}
        
        for language in self.supported_languages:
            invalid_keys = []
            for key, value in self.translations[language].items():
                if not isinstance(value, str):
                    invalid_keys.append(key)
            
            if invalid_keys:
                format_errors[language] = invalid_keys
        
        return format_errors
    
    def get_translation_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        获取翻译统计信息
        
        Returns:
            翻译统计信息字典
        """
        stats = {}
        
        for language in self.supported_languages:
            translations = self.translations[language]
            stats[language] = {
                'total_keys': len(translations),
                'empty_translations': len([v for v in translations.values() if not v or v.strip() == ""]),
                'avg_length': sum(len(str(v)) for v in translations.values()) // len(translations) if translations else 0,
                'max_length': max(len(str(v)) for v in translations.values()) if translations else 0,
                'min_length': min(len(str(v)) for v in translations.values()) if translations else 0
            }
        
        return stats
    
    def validate_all(self) -> Dict[str, any]:
        """
        执行所有验证
        
        Returns:
            完整的验证结果字典
        """
        return {
            'completeness': self.validate_completeness(),
            'consistency': self.validate_consistency(),
            'empty_translations': self.validate_empty_translations(),
            'format_errors': self.validate_translation_format(),
            'statistics': self.get_translation_statistics()
        }
    
    def is_valid(self) -> bool:
        """
        检查翻译是否完全有效
        
        Returns:
            如果所有验证都通过则返回True
        """
        results = self.validate_all()
        
        # 检查是否有任何错误
        has_completeness_errors = bool(results['completeness'])
        has_consistency_errors = bool(results['consistency'])
        has_empty_translations = bool(results['empty_translations'])
        has_format_errors = bool(results['format_errors'])
        
        return not (has_completeness_errors or has_consistency_errors or 
                   has_empty_translations or has_format_errors)


def validate_translation_completeness() -> Dict[str, List[str]]:
    """
    验证翻译完整性的便捷函数
    
    Returns:
        缺失翻译键的字典
    """
    validator = TranslationValidator()
    return validator.validate_completeness()

def validate_translation_consistency() -> List[str]:
    """
    验证翻译一致性的便捷函数
    
    Returns:
        不一致错误信息列表
    """
    validator = TranslationValidator()
    return validator.validate_consistency()

def check_translation_key_exists(key: str, language: Optional[str] = None) -> bool:
    """
    检查翻译键存在性的便捷函数
    
    Args:
        key: 要检查的翻译键
        language: 语言代码（可选，如果不提供则检查所有语言）
    
    Returns:
        如果指定了语言，返回该语言中键是否存在
        如果未指定语言，返回键是否在所有语言中都存在
    """
    validator = TranslationValidator()
    existence_dict = validator.validate_key_existence(key)
    
    if language is not None:
        # 检查特定语言
        return existence_dict.get(language, False)
    else:
        # 检查是否在所有语言中都存在
        return all(existence_dict.values())

def get_translation_health_report() -> Dict[str, any]:
    """
    获取翻译健康报告
    
    Returns:
        完整的翻译健康报告
    """
    validator = TranslationValidator()
    results = validator.validate_all()
    
    # 添加总体健康状态
    results['overall_health'] = validator.is_valid()
    results['total_languages'] = len(validator.supported_languages)
    
    return results

def get_translation_statistics() -> Dict[str, int]:
    """
    获取翻译统计信息的便捷函数
    
    Returns:
        翻译统计信息字典
    """
    validator = TranslationValidator()
    detailed_stats = validator.get_translation_statistics()
    
    # 转换为测试期望的格式
    supported_languages = validator.supported_languages
    stats = {
        'supported_languages_count': len(supported_languages)
    }
    
    # 添加每种语言的键数量
    for language in supported_languages:
        stats[f'{language}_keys_count'] = detailed_stats[language]['total_keys']
    
    # 添加最小和最大键数量
    key_counts = [detailed_stats[lang]['total_keys'] for lang in supported_languages]
    stats['min_keys_per_language'] = min(key_counts) if key_counts else 0
    stats['max_keys_per_language'] = max(key_counts) if key_counts else 0
    
    return stats