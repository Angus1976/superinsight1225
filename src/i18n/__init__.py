"""
国际化 (i18n) 模块
支持多语言界面切换
"""

from .translations import (
    get_translation,
    set_language,
    get_current_language,
    get_all_translations,
    get_supported_languages,
    get_text_metadata,
    get_all_text_metadata,
    get_performance_statistics,
    reset_translation_performance_stats,
    optimize_translation_memory,
    reinitialize_performance_optimizations
)
from .manager import TranslationManager, get_manager
from .validation import (
    TranslationValidator,
    validate_translation_completeness,
    validate_translation_consistency,
    check_translation_key_exists,
    get_translation_health_report,
    get_translation_statistics
)
from .middleware import (
    language_middleware,
    create_language_middleware,
    detect_language_from_request,
    parse_accept_language
)
from .performance import (
    get_performance_report,
    reset_performance_stats,
    optimize_memory_usage,
    configure_performance
)
from .thread_safety import (
    ThreadSafetyValidator,
    get_thread_safety_validator,
    validate_thread_safety,
    run_thread_safety_benchmark,
    get_context_variable_info
)
from .formatters import (
    DateTimeFormatter,
    NumberFormatter,
    CurrencyFormatter,
    format_date,
    format_time,
    format_datetime,
    format_relative_time,
    format_number,
    format_percent,
    format_currency
)
from .hot_reload import (
    TranslationHotReloader,
    get_hot_reloader,
    reload_translations,
    register_reload_callback,
    unregister_reload_callback,
    start_hot_reload_watching,
    stop_hot_reload_watching,
    get_hot_reload_status
)
from .ontology_collaboration_i18n import (
    ONTOLOGY_COLLABORATION_TRANSLATIONS,
    register_ontology_collaboration_translations,
    get_ontology_translation,
)

__all__ = [
    'get_translation',
    'set_language',
    'get_current_language',
    'get_all_translations',
    'get_supported_languages',
    'get_text_metadata',
    'get_all_text_metadata',
    'get_performance_statistics',
    'reset_translation_performance_stats',
    'optimize_translation_memory',
    'reinitialize_performance_optimizations',
    'TranslationManager',
    'get_manager',
    'TranslationValidator',
    'validate_translation_completeness',
    'validate_translation_consistency',
    'check_translation_key_exists',
    'get_translation_health_report',
    'get_translation_statistics',
    'language_middleware',
    'create_language_middleware',
    'detect_language_from_request',
    'parse_accept_language',
    'get_performance_report',
    'reset_performance_stats',
    'optimize_memory_usage',
    'configure_performance',
    'ThreadSafetyValidator',
    'get_thread_safety_validator',
    'validate_thread_safety',
    'run_thread_safety_benchmark',
    'get_context_variable_info',
    # Formatters
    'DateTimeFormatter',
    'NumberFormatter',
    'CurrencyFormatter',
    'format_date',
    'format_time',
    'format_datetime',
    'format_relative_time',
    'format_number',
    'format_percent',
    'format_currency',
    # Hot Reload
    'TranslationHotReloader',
    'get_hot_reloader',
    'reload_translations',
    'register_reload_callback',
    'unregister_reload_callback',
    'start_hot_reload_watching',
    'stop_hot_reload_watching',
    'get_hot_reload_status',
    # Ontology Collaboration I18n
    'ONTOLOGY_COLLABORATION_TRANSLATIONS',
    'register_ontology_collaboration_translations',
    'get_ontology_translation',
]