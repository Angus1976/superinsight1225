"""
翻译管理模块
支持中文和英文的动态切换
"""

from typing import Dict, Any, Optional
from contextvars import ContextVar
from .error_handler import (
    log_translation_error,
    handle_missing_translation_key,
    handle_unsupported_language,
    handle_parameter_substitution_error,
    safe_translation_wrapper,
    UnsupportedLanguageError,
    TranslationKeyError,
    ParameterSubstitutionError
)
from .performance import (
    performance_timer,
    get_optimized_translation,
    precompute_common_translations,
    get_performance_report,
    reset_performance_stats,
    optimize_memory_usage
)

# 当前语言上下文变量（默认中文）
_current_language: ContextVar[str] = ContextVar('language', default='zh')

# 翻译字典
TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    'zh': {
        # 通用
        'app_name': 'SuperInsight 平台',
        'app_description': '企业级 AI 数据治理与标注平台',
        'version': '版本',
        'status': '状态',
        'error': '错误',
        'success': '成功',
        'warning': '警告',
        'info': '信息',
        
        # 认证相关
        'login': '登录',
        'logout': '登出',
        'username': '用户名',
        'password': '密码',
        'email': '邮箱',
        'full_name': '全名',
        'role': '角色',
        'invalid_credentials': '用户名或密码错误',
        'user_created': '用户创建成功',
        'user_exists': '用户已存在',
        'login_success': '登录成功',
        'logout_success': '登出成功',
        
        # 用户角色
        'admin': '系统管理员',
        'business_expert': '业务专家',
        'annotator': '数据标注员',
        'viewer': '报表查看者',
        
        # 系统状态
        'healthy': '健康',
        'unhealthy': '不健康',
        'system_status': '系统状态',
        'services': '服务',
        'metrics': '指标',
        'uptime': '运行时间',
        'cpu_usage': 'CPU 使用率',
        'memory_usage': '内存使用率',
        'disk_usage': '磁盘使用率',
        
        # 数据提取
        'extraction': '数据提取',
        'extract_data': '提取数据',
        'extraction_started': '数据提取已启动',
        'extraction_completed': '数据提取已完成',
        'source_type': '源类型',
        'task_id': '任务ID',
        
        # 质量管理
        'quality': '质量',
        'evaluate_quality': '评估质量',
        'completeness': '完整性',
        'accuracy': '准确性',
        'consistency': '一致性',
        'overall_score': '总体评分',
        
        # AI 预标注
        'ai_annotation': 'AI 预标注',
        'preannotate': '预标注',
        'confidence': '置信度',
        'label': '标签',
        
        # 计费
        'billing': '计费',
        'usage': '使用情况',
        'cost': '成本',
        'currency': '货币',
        'total': '总计',
        'extraction_tasks': '提取任务',
        'annotations': '标注数',
        'ai_predictions': 'AI 预测',
        'storage': '存储',
        
        # 知识图谱
        'knowledge_graph': '知识图谱',
        'entities': '实体',
        'entity': '实体',
        'entity_type': '实体类型',
        'person': '人物',
        'organization': '组织',
        'location': '地点',
        
        # 任务管理
        'tasks': '任务',
        'task': '任务',
        'task_title': '任务标题',
        'pending': '待处理',
        'in_progress': '进行中',
        'completed': '已完成',
        'failed': '失败',
        'created_at': '创建时间',
        'updated_at': '更新时间',
        
        # API 相关
        'api_info': 'API 信息',
        'endpoints': '端点',
        'features': '功能',
        'docs_url': '文档 URL',
        'health_url': '健康检查 URL',
        'login_url': '登录 URL',
        
        # 错误消息
        'not_found': '未找到',
        'unauthorized': '未授权',
        'forbidden': '禁止访问',
        'bad_request': '请求错误',
        'internal_error': '内部错误',
        'service_unavailable': '服务不可用',
        
        # 语言设置
        'language': '语言',
        'language_changed': '语言已更改',
        'chinese': '中文',
        'english': '英文',
        
        # API 通用消息
        'operation_successful': '操作成功',
        'operation_failed': '操作失败',
        'invalid_request': '无效请求',
        'resource_not_found': '资源未找到',
        'access_denied': '访问被拒绝',
        'server_error': '服务器内部错误',
        'invalid_format': '格式无效',
        'already_exists': '已存在',
        'not_enabled': '未启用',
        'not_disabled': '未禁用',
        'cancelled_successfully': '取消成功',
        'created_successfully': '创建成功',
        'updated_successfully': '更新成功',
        'deleted_successfully': '删除成功',
        'enabled_successfully': '启用成功',
        'disabled_successfully': '禁用成功',
        'approved_successfully': '批准成功',
        'rejected_successfully': '拒绝成功',
        'executed_successfully': '执行成功',
        'verified_successfully': '验证成功',
        'assigned_successfully': '分配成功',
        'resolved_successfully': '解决成功',
        'saved_successfully': '保存成功',
        'exported_successfully': '导出成功',
        'imported_successfully': '导入成功',
        'synchronized_successfully': '同步成功',
        'processed_successfully': '处理成功',
        'validated_successfully': '验证成功',
        'configured_successfully': '配置成功',
        
        # 错误消息
        'internal_server_error': '服务器内部错误',
        'unsupported_language': '不支持的语言',
        'invalid_language_code': '无效的语言代码',
        'missing_required_parameter': '缺少必需参数',
        'invalid_parameter_value': '参数值无效',
        'resource_already_exists': '资源已存在',
        'operation_not_allowed': '操作不被允许',
        'insufficient_permissions': '权限不足',
        'request_timeout': '请求超时',
        'service_unavailable': '服务不可用',
        'database_error': '数据库错误',
        'network_error': '网络错误',
        'file_not_found': '文件未找到',
        'file_too_large': '文件过大',
        'invalid_file_format': '文件格式无效',
        'connection_failed': '连接失败',
        'authentication_failed': '认证失败',
        'authorization_failed': '授权失败',
        'validation_failed': '验证失败',
        'processing_failed': '处理失败',
        'enhancement_failed': '增强失败',
        'amplification_failed': '放大失败',
        'reconstruction_failed': '重建失败',
        'quality_check_failed': '质量检查失败',
        'repair_failed': '修复失败',
        'export_failed': '导出失败',
        'import_failed': '导入失败',
        'sync_failed': '同步失败',
        
        # 状态消息
        'job_started': '任务已启动',
        'job_completed': '任务已完成',
        'job_cancelled': '任务已取消',
        'job_failed': '任务失败',
        'job_pending': '任务待处理',
        'job_running': '任务运行中',
        'processing': '处理中',
        'completed': '已完成',
        'cancelled': '已取消',
        'failed': '失败',
        'pending': '待处理',
        'running': '运行中',
        'enabled': '已启用',
        'disabled': '已禁用',
        'approved': '已批准',
        'rejected': '已拒绝',
        'assigned': '已分配',
        'resolved': '已解决',
        
        # 参数化翻译示例
        'welcome_user': '欢迎，{username}！',
        'items_count': '共有 {count} 个项目',
        'processing_progress': '处理进度：{current}/{total} ({percentage}%)',
        'user_role_info': '用户 {username} 的角色是 {role}',
        'rule_created': '质量规则 {rule_id} 创建成功',
        'rule_enabled': '质量规则 {rule_id} 已启用',
        'rule_disabled': '质量规则 {rule_id} 已禁用',
        'rule_deleted': '质量规则 {rule_id} 已删除',
        'rule_not_found': '质量规则 {rule_id} 未找到',
        'issue_assigned': '质量问题 {issue_id} 已分配给 {assignee_id}',
        'issue_resolved': '质量问题 {issue_id} 已解决',
        'repair_approved': '修复 {repair_id} 已批准',
        'repair_rejected': '修复 {repair_id} 已拒绝',
        'repair_executed': '修复 {repair_id} 执行成功',
        'job_cancelled': '任务 {job_id} 已取消',
        'quality_check_triggered': '任务 {task_id} 的质量检查已触发',
    },
    'en': {
        # General
        'app_name': 'SuperInsight Platform',
        'app_description': 'Enterprise-grade AI Data Governance and Annotation Platform',
        'version': 'Version',
        'status': 'Status',
        'error': 'Error',
        'success': 'Success',
        'warning': 'Warning',
        'info': 'Information',
        
        # Authentication
        'login': 'Login',
        'logout': 'Logout',
        'username': 'Username',
        'password': 'Password',
        'email': 'Email',
        'full_name': 'Full Name',
        'role': 'Role',
        'invalid_credentials': 'Invalid username or password',
        'user_created': 'User created successfully',
        'user_exists': 'User already exists',
        'login_success': 'Login successful',
        'logout_success': 'Logout successful',
        
        # User Roles
        'admin': 'System Administrator',
        'business_expert': 'Business Expert',
        'annotator': 'Data Annotator',
        'viewer': 'Report Viewer',
        
        # System Status
        'healthy': 'Healthy',
        'unhealthy': 'Unhealthy',
        'system_status': 'System Status',
        'services': 'Services',
        'metrics': 'Metrics',
        'uptime': 'Uptime',
        'cpu_usage': 'CPU Usage',
        'memory_usage': 'Memory Usage',
        'disk_usage': 'Disk Usage',
        
        # Data Extraction
        'extraction': 'Data Extraction',
        'extract_data': 'Extract Data',
        'extraction_started': 'Data extraction started',
        'extraction_completed': 'Data extraction completed',
        'source_type': 'Source Type',
        'task_id': 'Task ID',
        
        # Quality Management
        'quality': 'Quality',
        'evaluate_quality': 'Evaluate Quality',
        'completeness': 'Completeness',
        'accuracy': 'Accuracy',
        'consistency': 'Consistency',
        'overall_score': 'Overall Score',
        
        # AI Annotation
        'ai_annotation': 'AI Pre-annotation',
        'preannotate': 'Pre-annotate',
        'confidence': 'Confidence',
        'label': 'Label',
        
        # Billing
        'billing': 'Billing',
        'usage': 'Usage',
        'cost': 'Cost',
        'currency': 'Currency',
        'total': 'Total',
        'extraction_tasks': 'Extraction Tasks',
        'annotations': 'Annotations',
        'ai_predictions': 'AI Predictions',
        'storage': 'Storage',
        
        # Knowledge Graph
        'knowledge_graph': 'Knowledge Graph',
        'entities': 'Entities',
        'entity': 'Entity',
        'entity_type': 'Entity Type',
        'person': 'Person',
        'organization': 'Organization',
        'location': 'Location',
        
        # Task Management
        'tasks': 'Tasks',
        'task': 'Task',
        'task_title': 'Task Title',
        'pending': 'Pending',
        'in_progress': 'In Progress',
        'completed': 'Completed',
        'failed': 'Failed',
        'created_at': 'Created At',
        'updated_at': 'Updated At',
        
        # API Related
        'api_info': 'API Information',
        'endpoints': 'Endpoints',
        'features': 'Features',
        'docs_url': 'Documentation URL',
        'health_url': 'Health Check URL',
        'login_url': 'Login URL',
        
        # Error Messages
        'not_found': 'Not Found',
        'unauthorized': 'Unauthorized',
        'forbidden': 'Forbidden',
        'bad_request': 'Bad Request',
        'internal_error': 'Internal Error',
        'service_unavailable': 'Service Unavailable',
        
        # Language Settings
        'language': 'Language',
        'language_changed': 'Language changed',
        'chinese': 'Chinese',
        'english': 'English',
        
        # API Common Messages
        'operation_successful': 'Operation successful',
        'operation_failed': 'Operation failed',
        'invalid_request': 'Invalid request',
        'resource_not_found': 'Resource not found',
        'access_denied': 'Access denied',
        'server_error': 'Internal server error',
        'invalid_format': 'Invalid format',
        'already_exists': 'Already exists',
        'not_enabled': 'Not enabled',
        'not_disabled': 'Not disabled',
        'cancelled_successfully': 'Cancelled successfully',
        'created_successfully': 'Created successfully',
        'updated_successfully': 'Updated successfully',
        'deleted_successfully': 'Deleted successfully',
        'enabled_successfully': 'Enabled successfully',
        'disabled_successfully': 'Disabled successfully',
        'approved_successfully': 'Approved successfully',
        'rejected_successfully': 'Rejected successfully',
        'executed_successfully': 'Executed successfully',
        'verified_successfully': 'Verified successfully',
        'assigned_successfully': 'Assigned successfully',
        'resolved_successfully': 'Resolved successfully',
        'saved_successfully': 'Saved successfully',
        'exported_successfully': 'Exported successfully',
        'imported_successfully': 'Imported successfully',
        'synchronized_successfully': 'Synchronized successfully',
        'processed_successfully': 'Processed successfully',
        'validated_successfully': 'Validated successfully',
        'configured_successfully': 'Configured successfully',
        
        # Error Messages
        'internal_server_error': 'Internal server error',
        'unsupported_language': 'Unsupported language',
        'invalid_language_code': 'Invalid language code',
        'missing_required_parameter': 'Missing required parameter',
        'invalid_parameter_value': 'Invalid parameter value',
        'resource_already_exists': 'Resource already exists',
        'operation_not_allowed': 'Operation not allowed',
        'insufficient_permissions': 'Insufficient permissions',
        'request_timeout': 'Request timeout',
        'service_unavailable': 'Service unavailable',
        'database_error': 'Database error',
        'network_error': 'Network error',
        'file_not_found': 'File not found',
        'file_too_large': 'File too large',
        'invalid_file_format': 'Invalid file format',
        'connection_failed': 'Connection failed',
        'authentication_failed': 'Authentication failed',
        'authorization_failed': 'Authorization failed',
        'validation_failed': 'Validation failed',
        'processing_failed': 'Processing failed',
        'enhancement_failed': 'Enhancement failed',
        'amplification_failed': 'Amplification failed',
        'reconstruction_failed': 'Reconstruction failed',
        'quality_check_failed': 'Quality check failed',
        'repair_failed': 'Repair failed',
        'export_failed': 'Export failed',
        'import_failed': 'Import failed',
        'sync_failed': 'Sync failed',
        
        # Status Messages
        'job_started': 'Job started',
        'job_completed': 'Job completed',
        'job_cancelled': 'Job cancelled',
        'job_failed': 'Job failed',
        'job_pending': 'Job pending',
        'job_running': 'Job running',
        'processing': 'Processing',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'failed': 'Failed',
        'pending': 'Pending',
        'running': 'Running',
        'enabled': 'Enabled',
        'disabled': 'Disabled',
        'approved': 'Approved',
        'rejected': 'Rejected',
        'assigned': 'Assigned',
        'resolved': 'Resolved',
        
        # Parameterized translation examples
        'welcome_user': 'Welcome, {username}!',
        'items_count': 'Total {count} items',
        'processing_progress': 'Progress: {current}/{total} ({percentage}%)',
        'user_role_info': 'User {username} has role {role}',
        'rule_created': 'Quality rule {rule_id} created successfully',
        'rule_enabled': 'Quality rule {rule_id} enabled',
        'rule_disabled': 'Quality rule {rule_id} disabled',
        'rule_deleted': 'Quality rule {rule_id} deleted',
        'rule_not_found': 'Quality rule {rule_id} not found',
        'issue_assigned': 'Quality issue {issue_id} assigned to {assignee_id}',
        'issue_resolved': 'Quality issue {issue_id} resolved',
        'repair_approved': 'Repair {repair_id} approved successfully',
        'repair_rejected': 'Repair {repair_id} rejected successfully',
        'repair_executed': 'Repair {repair_id} executed successfully',
        'job_cancelled': 'Job {job_id} cancelled successfully',
        'quality_check_triggered': 'Quality check triggered for task {task_id}',
    }
}

# 翻译字典哈希值（用于缓存失效检测）
_translations_hash = hash(str(TRANSLATIONS))

# 初始化性能优化
def _initialize_performance_optimizations():
    """初始化性能优化"""
    precompute_common_translations(TRANSLATIONS)

# 在模块加载时初始化
_initialize_performance_optimizations()

@safe_translation_wrapper
def set_language(language: str) -> None:
    """
    设置当前语言
    
    Args:
        language: 语言代码 ('zh' 或 'en')
        
    Raises:
        UnsupportedLanguageError: 当语言不被支持时
    """
    if language not in TRANSLATIONS:
        supported_languages = list(TRANSLATIONS.keys())
        fallback_language = handle_unsupported_language(language, supported_languages)
        
        # 如果回退语言不同于请求语言，记录并使用回退语言
        if fallback_language != language:
            _current_language.set(fallback_language)
            return
        
        # 如果回退也失败，抛出异常
        raise UnsupportedLanguageError(language, supported_languages)
    
    _current_language.set(language)
    
    # 记录语言切换
    log_translation_error(
        'language_changed',
        {
            'new_language': language,
            'previous_language': _current_language.get('zh')
        },
        'info'
    )

def get_current_language() -> str:
    """
    获取当前语言
    
    Returns:
        当前语言代码
    """
    return _current_language.get()

@safe_translation_wrapper
@performance_timer
def get_translation(key: str, language: Optional[str] = None, **kwargs) -> str:
    """
    获取翻译文本
    
    Args:
        key: 翻译键
        language: 语言代码（可选，默认使用当前语言）
        **kwargs: 用于格式化的参数
    
    Returns:
        翻译后的文本
    """
    if language is None:
        language = get_current_language()
    
    # 处理不支持的语言
    if language not in TRANSLATIONS:
        supported_languages = list(TRANSLATIONS.keys())
        language = handle_unsupported_language(language, supported_languages)
    
    # 使用优化的翻译查找
    text = get_optimized_translation(key, language, TRANSLATIONS)
    
    # 如果未找到翻译，使用回退处理
    if text is None:
        return handle_missing_translation_key(key, language)
    
    # 如果提供了格式化参数，进行格式化
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError, TypeError) as e:
            return handle_parameter_substitution_error(key, language, text, kwargs, e)
    
    return text

@safe_translation_wrapper
@performance_timer
def get_all_translations(language: Optional[str] = None) -> Dict[str, str]:
    """
    获取指定语言的所有翻译
    
    Args:
        language: 语言代码（可选，默认使用当前语言）
    
    Returns:
        翻译字典
    """
    if language is None:
        language = get_current_language()
    
    # 处理不支持的语言
    if language not in TRANSLATIONS:
        supported_languages = list(TRANSLATIONS.keys())
        language = handle_unsupported_language(language, supported_languages)
    
    return TRANSLATIONS[language].copy()

def get_supported_languages() -> list:
    """
    获取支持的语言列表
    
    Returns:
        支持的语言代码列表
    """
    return list(TRANSLATIONS.keys())


@safe_translation_wrapper
def get_text_metadata(key: str, language: Optional[str] = None) -> Dict[str, Any]:
    """
    获取翻译文本的元数据
    
    Args:
        key: 翻译键
        language: 语言代码（可选，默认使用当前语言）
    
    Returns:
        包含文本特征的元数据字典
    """
    if language is None:
        language = get_current_language()
    
    # 处理不支持的语言
    if language not in TRANSLATIONS:
        supported_languages = list(TRANSLATIONS.keys())
        language = handle_unsupported_language(language, supported_languages)
    
    # 获取文本，如果键不存在则使用回退处理
    if key not in TRANSLATIONS[language]:
        text = handle_missing_translation_key(key, language)
    else:
        text = TRANSLATIONS[language][key]
    
    metadata = {
        'key': key,
        'language': language,
        'text': text,
        'length': len(text),
        'char_count': len(text),
        'word_count': len(text.split()) if text else 0,
        'direction': 'ltr',  # 左到右（中文和英文都是）
        'script': 'han' if language == 'zh' else 'latin',
        'has_parameters': '{' in text and '}' in text,
        'is_empty': len(text.strip()) == 0,
        'estimated_width': len(text) * (2 if language == 'zh' else 1),  # 中文字符通常更宽
    }
    
    return metadata


@safe_translation_wrapper
def get_all_text_metadata(language: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    获取所有翻译文本的元数据
    
    Args:
        language: 语言代码（可选，默认使用当前语言）
    
    Returns:
        包含所有翻译键元数据的字典
    """
    if language is None:
        language = get_current_language()
    
    # 处理不支持的语言
    if language not in TRANSLATIONS:
        supported_languages = list(TRANSLATIONS.keys())
        language = handle_unsupported_language(language, supported_languages)
    
    metadata = {}
    return metadata


def get_performance_statistics() -> Dict[str, Any]:
    """
    获取翻译系统性能统计
    
    Returns:
        性能统计字典
    """
    return get_performance_report()


def reset_translation_performance_stats() -> None:
    """重置翻译性能统计"""
    reset_performance_stats()


def optimize_translation_memory() -> Dict[str, Any]:
    """
    优化翻译系统内存使用
    
    Returns:
        内存优化报告
    """
    return optimize_memory_usage()


def reinitialize_performance_optimizations() -> None:
    """重新初始化性能优化"""
    global _translations_hash
    _translations_hash = hash(str(TRANSLATIONS))
    precompute_common_translations(TRANSLATIONS)
