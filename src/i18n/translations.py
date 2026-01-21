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
        
        # ============================================================================
        # 系统优化模块 i18n 翻译键 (System Optimization Module)
        # ============================================================================
        
        # 错误响应 (Error Response) - error.*
        'error.validation.invalid_input': '输入数据无效',
        'error.validation.missing_field': '缺少必填字段',
        'error.validation.invalid_format': '格式无效',
        'error.validation.invalid_value': '值无效',
        'error.validation.field_too_long': '字段过长',
        'error.validation.field_too_short': '字段过短',
        'error.validation.invalid_type': '类型无效',
        'error.validation.invalid_range': '值超出范围',
        'error.validation.invalid_enum': '枚举值无效',
        'error.validation.invalid_json': 'JSON格式无效',
        
        'error.auth.invalid_credentials': '用户名或密码错误',
        'error.auth.token_expired': '令牌已过期',
        'error.auth.token_invalid': '令牌无效',
        'error.auth.token_missing': '缺少认证令牌',
        'error.auth.session_expired': '会话已过期',
        'error.auth.account_locked': '账户已锁定',
        'error.auth.account_disabled': '账户已禁用',
        
        'error.permission.access_denied': '访问被拒绝',
        'error.permission.insufficient_role': '权限不足',
        'error.permission.resource_forbidden': '禁止访问该资源',
        'error.permission.operation_forbidden': '禁止执行该操作',
        'error.permission.tenant_mismatch': '租户不匹配',
        
        'error.not_found.resource': '资源未找到',
        'error.not_found.user': '用户未找到',
        'error.not_found.task': '任务未找到',
        'error.not_found.project': '项目未找到',
        'error.not_found.annotation': '标注未找到',
        'error.not_found.data_source': '数据源未找到',
        'error.not_found.evaluation': '评估结果未找到',
        'error.not_found.rule': '规则未找到',
        'error.not_found.endpoint': '端点未找到',
        
        'error.conflict.resource_exists': '资源已存在',
        'error.conflict.version_mismatch': '版本不匹配',
        'error.conflict.state_invalid': '状态无效',
        'error.conflict.duplicate_key': '键值重复',
        'error.conflict.concurrent_update': '并发更新冲突',
        
        'error.rate_limit.exceeded': '请求频率超限',
        'error.rate_limit.api_quota': 'API配额已用尽',
        'error.rate_limit.user_quota': '用户配额已用尽',
        
        'error.internal.server_error': '服务器内部错误',
        'error.internal.database_error': '数据库错误',
        'error.internal.cache_error': '缓存错误',
        'error.internal.processing_error': '处理错误',
        'error.internal.configuration_error': '配置错误',
        'error.internal.unexpected_error': '未知错误',
        
        'error.service.unavailable': '服务不可用',
        'error.service.maintenance': '服务维护中',
        'error.service.overloaded': '服务过载',
        'error.service.dependency_failed': '依赖服务失败',
        'error.service.timeout': '服务超时',
        
        # 缓存策略 (Cache Strategy) - cache.*
        'cache.strategy.cache_hit': '缓存命中',
        'cache.strategy.cache_miss': '缓存未命中',
        'cache.strategy.cache_set': '缓存已设置',
        'cache.strategy.cache_invalidated': '缓存已失效',
        'cache.strategy.batch_invalidated': '批量缓存已失效',
        
        'cache.warmup.started': '缓存预热开始',
        'cache.warmup.completed': '缓存预热完成',
        'cache.warmup.failed': '缓存预热失败',
        
        'cache.monitor.hit_rate_low': '缓存命中率过低',
        'cache.monitor.stats_reset': '缓存统计已重置',
        
        'cache.error.connection_failed': '缓存连接失败',
        'cache.error.serialization_failed': '序列化失败',
        'cache.error.deserialization_failed': '反序列化失败',
        'cache.error.operation_failed': '缓存操作失败',
        
        # 数据库操作 (Database Operations) - database.*
        'database.batch.insert_started': '批量插入开始: {count} 条记录',
        'database.batch.insert_completed': '批量插入完成: {count} 条记录, 耗时 {duration}ms',
        'database.batch.update_started': '批量更新开始: {count} 条记录',
        'database.batch.update_completed': '批量更新完成: {count} 条记录, 耗时 {duration}ms',
        'database.batch.upsert_started': '批量插入或更新开始: {count} 条记录',
        'database.batch.upsert_completed': '批量插入或更新完成: {count} 条记录, 耗时 {duration}ms',
        'database.error.batch_failed': '批量操作失败: {error}',
        
        'database.pagination.invalid_page': '无效的页码: {page}',
        'database.pagination.invalid_size': '无效的页大小: {size}',
        'database.pagination.query_started': '分页查询开始: page={page}, size={size}',
        'database.pagination.query_completed': '分页查询完成: 返回 {count} 条记录',
        'database.error.query_failed': '查询失败: {error}',
        
        'database.monitor.slow_query_detected': '检测到慢查询: {duration}ms, SQL: {sql}',
        'database.monitor.stats_reset': '慢查询统计已重置',
        'database.monitor.threshold_updated': '慢查询阈值已更新: {threshold}ms',
        'database.monitor.query_recorded': '查询已记录: {duration}ms',
        
        # SLA 通知 (SLA Notification) - sla_monitor.*
        'sla_monitor.notification.email_subject_breach': 'SLA 违规告警: {ticket_title}',
        'sla_monitor.notification.email_subject_warning': 'SLA 预警: {ticket_title}',
        'sla_monitor.notification.email_subject_escalation': 'SLA 升级告警: {ticket_title}',
        
        'sla_monitor.notification.breach_message': '工单 {ticket_id} 已违反 SLA，请立即处理',
        'sla_monitor.notification.warning_message': '工单 {ticket_id} 即将违反 SLA，请尽快处理',
        'sla_monitor.notification.escalation_message': '工单 {ticket_id} SLA 违规已升级',
        
        'sla_monitor.notification.send_failed': '通知发送失败: {error}',
        'sla_monitor.notification.channel_unavailable': '通知渠道不可用: {channel}',
        'sla_monitor.notification.retry_attempt': '正在重试发送通知 (第 {attempt} 次)',
        'sla_monitor.notification.all_channels_failed': '所有通知渠道均失败',
        'sla_monitor.notification.send_success': '通知发送成功: {channel}',
        
        'sla_monitor.notification.wechat_card_title': 'SLA 告警通知',
        'sla_monitor.notification.wechat_card_description': '工单 {ticket_id} 需要您的关注',
        
        # 合规报告调度 (Compliance Scheduler) - compliance.*
        'compliance.scheduler.job_added': '合规报告任务已添加: {report_type}',
        'compliance.scheduler.job_removed': '合规报告任务已移除: {report_type}',
        'compliance.scheduler.job_executed': '合规报告任务已执行: {report_type}',
        'compliance.scheduler.job_failed': '合规报告任务执行失败: {error}',
        'compliance.scheduler.invalid_cron': '无效的 cron 表达式: {expression}',
        'compliance.scheduler.invalid_report_type': '无效的报告类型: {report_type}',
        'compliance.scheduler.next_run': '下次执行时间: {next_run}',
        
        # 同步管理器 (Sync Manager) - sync.*
        'sync.manager.sync_started': '同步开始',
        'sync.manager.sync_completed': '同步完成: {count} 条记录',
        'sync.manager.sync_failed': '同步失败: {error}',
        'sync.manager.conflict_resolved': '冲突已解决: {item_id}',
        'sync.manager.model_downloaded': '模型已下载: {model_name}',
        
        # 报告服务 (Report Service) - report.*
        'report.email.send_started': '邮件发送开始: {recipient}',
        'report.email.send_completed': '邮件发送完成: {recipient}',
        'report.email.send_failed': '邮件发送失败: {error}',
        'report.email.retry_attempt': '邮件发送重试 (第 {attempt} 次)',
        
        # ============================================================================
        # 安全控制模块 (Security Control Module)
        # ============================================================================
        
        # 加密服务 (Encryption Service) - security.encryption.*
        'security.encryption.empty_plaintext': '明文不能为空',
        'security.encryption.empty_ciphertext': '密文不能为空',
        'security.encryption.invalid_ciphertext': '无效的密文格式',
        'security.encryption.invalid_key': '无效的加密密钥',
        'security.encryption.no_key': '未提供加密密钥',
        'security.encryption.encrypt_success': '加密成功',
        'security.encryption.encrypt_failed': '加密失败',
        'security.encryption.decrypt_success': '解密成功',
        'security.encryption.decrypt_failed': '解密失败',
        'security.encryption.key_generated': '密钥已生成',
        'security.encryption.key_derived': '密钥已派生',
        
        # 速率限制 (Rate Limiting) - security.rate_limit.*
        'security.rate_limit.exceeded': '请求频率超限，请稍后重试',
        'security.rate_limit.limit_info': '限制: {limit} 次/{window}秒',
        'security.rate_limit.remaining': '剩余请求次数: {remaining}',
        'security.rate_limit.reset_time': '重置时间: {reset_time}',
        'security.rate_limit.blocked': '请求已被阻止',
        'security.rate_limit.config_updated': '速率限制配置已更新',
        
        # 输入验证 (Input Validation) - security.validation.*
        'security.validation.invalid_email': '无效的邮箱格式',
        'security.validation.invalid_phone': '无效的电话号码格式',
        'security.validation.invalid_url': '无效的URL格式',
        'security.validation.invalid_ip': '无效的IP地址格式',
        'security.validation.invalid_uuid': '无效的UUID格式',
        'security.validation.xss_detected': '检测到潜在的XSS攻击',
        'security.validation.sql_injection_detected': '检测到潜在的SQL注入',
        'security.validation.path_traversal_detected': '检测到路径遍历攻击',
        'security.validation.field_required': '字段 {field} 是必填的',
        'security.validation.field_too_long': '字段 {field} 超过最大长度 {max_length}',
        'security.validation.field_too_short': '字段 {field} 少于最小长度 {min_length}',
        'security.validation.field_invalid_pattern': '字段 {field} 格式不正确',
        
        # 审计日志 (Audit Logging) - security.audit.*
        'security.audit.event_logged': '审计事件已记录',
        'security.audit.login_success': '用户 {username} 登录成功',
        'security.audit.login_failed': '用户 {username} 登录失败',
        'security.audit.logout': '用户 {username} 已登出',
        'security.audit.password_changed': '用户 {username} 密码已更改',
        'security.audit.permission_changed': '用户 {username} 权限已更改',
        'security.audit.resource_accessed': '资源 {resource} 被访问',
        'security.audit.resource_created': '资源 {resource} 已创建',
        'security.audit.resource_updated': '资源 {resource} 已更新',
        'security.audit.resource_deleted': '资源 {resource} 已删除',
        'security.audit.sensitive_operation': '敏感操作: {operation}',
        'security.audit.suspicious_activity': '可疑活动: {activity}',
        'security.audit.ip_blocked': 'IP {ip} 已被阻止',
        'security.audit.rate_limit_exceeded': '用户 {username} 超过速率限制',
        
        # ============================================================================
        # 监控和告警模块 (Monitoring and Alerting Module)
        # ============================================================================
        
        # Prometheus 指标 - monitoring.metrics.*
        'monitoring.metrics.counter_negative_value': '计数器值不能为负数',
        'monitoring.metrics.metric_already_registered': '指标已注册: {name}',
        'monitoring.metrics.metric_registered': '指标已注册: {name}',
        'monitoring.metrics.metric_unregistered': '指标已取消注册: {name}',
        
        # 告警配置 - monitoring.alert.*
        'monitoring.alert.invalid_duration': '无效的持续时间',
        'monitoring.alert.invalid_value': '无效的阈值',
        'monitoring.alert.invalid_cooldown': '无效的冷却时间',
        'monitoring.alert.invalid_max_alerts': '无效的最大告警数',
        'monitoring.alert.threshold_added': '告警阈值已添加: {id}',
        'monitoring.alert.threshold_updated': '告警阈值已更新: {id}',
        'monitoring.alert.threshold_removed': '告警阈值已移除: {id}',
        'monitoring.alert.threshold_not_found': '告警阈值未找到: {id}',
        'monitoring.alert.hourly_limit_reached': '每小时告警限制已达到',
        'monitoring.alert.callback_error': '告警回调错误: {error}',
        'monitoring.alert.config_updated': '告警配置已更新',
        'monitoring.alert.cooldown_updated': '冷却时间已更新: {seconds}秒',
        'monitoring.alert.max_alerts_updated': '每小时最大告警数已更新: {max_alerts}',
        'monitoring.alert.channel_added': '通知渠道已添加: {channel}',
        'monitoring.alert.channel_removed': '通知渠道已移除: {channel}',
        'monitoring.alert.acknowledged': '告警已确认: {id}',
        'monitoring.alert.resolved': '告警已解决: {id}',
        
        # 健康检查 - monitoring.health.*
        'monitoring.health.timeout': '服务 {service} 健康检查超时',
        'monitoring.health.database_connected': '数据库连接正常',
        'monitoring.health.database_not_configured': '数据库未配置',
        'monitoring.health.redis_connected': 'Redis 连接正常',
        'monitoring.health.redis_not_installed': 'Redis 客户端未安装',
        'monitoring.health.neo4j_connected': 'Neo4j 连接正常',
        'monitoring.health.neo4j_not_configured': 'Neo4j 未配置',
        'monitoring.health.label_studio_connected': 'Label Studio 连接正常',
        'monitoring.health.label_studio_not_configured': 'Label Studio 未配置',
        'monitoring.health.label_studio_error': 'Label Studio 错误: {code}',
        'monitoring.health.api_connected': '{name} API 连接正常',
        'monitoring.health.api_error': '{name} API 错误: {code}',
        'monitoring.health.checker_registered': '健康检查器已注册: {name}',
        'monitoring.health.checker_unregistered': '健康检查器已取消注册: {name}',
        
        # 服务告警 - monitoring.service_alert.*
        'monitoring.service_alert.already_monitoring': '监控已在运行中',
        'monitoring.service_alert.monitoring_started': '服务监控已启动',
        'monitoring.service_alert.monitoring_stopped': '服务监控已停止',
        'monitoring.service_alert.monitoring_error': '监控错误: {error}',
        'monitoring.service_alert.alert_triggered': '服务告警触发: {service} 状态={status} 严重程度={severity}',
        'monitoring.service_alert.recovery_triggered': '服务恢复通知: {service} 状态={status}',
        'monitoring.service_alert.callback_error': '回调错误: {error}',
        'monitoring.service_alert.config_updated': '服务告警配置已更新',
        
        # ============================================================================
        # 企业本体模块 (Enterprise Ontology Module)
        # ============================================================================
        
        # 本体管理器 - ontology.manager.*
        'ontology.manager.initialized': '企业本体管理器已初始化',
        'ontology.manager.entity_created': '本体实体已创建: {name}',
        'ontology.manager.entity_updated': '本体实体已更新: {name}',
        'ontology.manager.entity_deleted': '本体实体已删除: {id}',
        'ontology.manager.relation_created': '本体关系已创建: {type}',
        'ontology.manager.relation_updated': '本体关系已更新: {id}',
        'ontology.manager.relation_deleted': '本体关系已删除: {id}',
        'ontology.manager.cache_cleared': '本体缓存已清除',
        'ontology.manager.lineage_tracked': '数据血缘已追踪: {entity_id}',
        
        # AI 数据转换器 - ontology.converter.*
        'ontology.converter.initialized': 'AI 数据转换器已初始化',
        'ontology.converter.conversion_started': '数据转换已开始: {format}',
        'ontology.converter.conversion_completed': '数据转换已完成: {count} 条记录',
        'ontology.converter.conversion_failed': '数据转换失败: {error}',
        'ontology.converter.validation_passed': '数据验证通过',
        'ontology.converter.validation_failed': '数据验证失败: {count} 条记录无效',
        'ontology.converter.missing_question': '缺少问题/指令字段',
        'ontology.converter.missing_answer': '缺少回答/输出字段',
        
        # 合规验证 - ontology.compliance.*
        'ontology.compliance.check_started': '合规检查已开始',
        'ontology.compliance.check_completed': '合规检查已完成',
        'ontology.compliance.compliant': '实体合规',
        'ontology.compliance.non_compliant': '实体不合规',
        'ontology.compliance.missing_classification': '缺少数据分类等级',
        'ontology.compliance.cross_border_violation': '数据不允许跨境传输到 {target}',
        'ontology.compliance.pii_sensitivity_mismatch': '包含个人信息但敏感度等级不是高',
        'ontology.compliance.pii_classification_mismatch': '包含个人信息但数据分类等级过低',
        'ontology.compliance.missing_retention_period': '包含个人信息但未设置保留期限',
        
        # 实体类型 - ontology.entity_type.*
        'ontology.entity_type.person': '人员',
        'ontology.entity_type.organization': '组织',
        'ontology.entity_type.document': '文档',
        'ontology.entity_type.location': '位置',
        'ontology.entity_type.department': '部门',
        'ontology.entity_type.business_unit': '业务单元',
        'ontology.entity_type.regulation': '法规政策',
        'ontology.entity_type.contract': '合同',
        'ontology.entity_type.approval': '审批流程',
        'ontology.entity_type.seal': '印章',
        'ontology.entity_type.invoice': '发票',
        'ontology.entity_type.certificate': '资质证书',
        'ontology.entity_type.budget': '预算',
        'ontology.entity_type.project': '项目',
        'ontology.entity_type.meeting': '会议',
        'ontology.entity_type.policy': '内部政策',
        
        # 关系类型 - ontology.relation_type.*
        'ontology.relation_type.belongs_to': '属于',
        'ontology.relation_type.created_by': '创建者',
        'ontology.relation_type.related_to': '关联',
        'ontology.relation_type.reports_to': '汇报给',
        'ontology.relation_type.approves': '审批',
        'ontology.relation_type.seals': '用印',
        'ontology.relation_type.complies_with': '合规于',
        'ontology.relation_type.supervises': '监管',
        'ontology.relation_type.delegates_to': '授权给',
        'ontology.relation_type.manages': '管理',
        'ontology.relation_type.participates_in': '参与',
        'ontology.relation_type.signs': '签署',
        'ontology.relation_type.reviews': '审核',
        'ontology.relation_type.issues': '开具',
        'ontology.relation_type.holds': '持有',
        
        # 数据分类 - ontology.classification.*
        'ontology.classification.public': '公开',
        'ontology.classification.internal': '内部',
        'ontology.classification.confidential': '机密',
        'ontology.classification.secret': '秘密',
        'ontology.classification.top_secret': '绝密',
        
        # 敏感度等级 - ontology.sensitivity.*
        'ontology.sensitivity.low': '低',
        'ontology.sensitivity.medium': '中',
        'ontology.sensitivity.high': '高',
        'ontology.sensitivity.critical': '极高',
        
        # AI 数据格式 - ontology.format.*
        'ontology.format.alpaca': 'Alpaca 格式',
        'ontology.format.sharegpt': 'ShareGPT 格式',
        'ontology.format.openai': 'OpenAI 微调格式',
        'ontology.format.llama_factory': 'LLaMA-Factory 格式',
        'ontology.format.fastchat': 'FastChat 格式',
        'ontology.format.belle': 'BELLE 格式',
        'ontology.format.custom': '自定义格式',
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
        
        # ============================================================================
        # System Optimization Module i18n Translation Keys
        # ============================================================================
        
        # Error Response - error.*
        'error.validation.invalid_input': 'Invalid input data',
        'error.validation.missing_field': 'Missing required field',
        'error.validation.invalid_format': 'Invalid format',
        'error.validation.invalid_value': 'Invalid value',
        'error.validation.field_too_long': 'Field too long',
        'error.validation.field_too_short': 'Field too short',
        'error.validation.invalid_type': 'Invalid type',
        'error.validation.invalid_range': 'Value out of range',
        'error.validation.invalid_enum': 'Invalid enum value',
        'error.validation.invalid_json': 'Invalid JSON format',
        
        'error.auth.invalid_credentials': 'Invalid username or password',
        'error.auth.token_expired': 'Token expired',
        'error.auth.token_invalid': 'Invalid token',
        'error.auth.token_missing': 'Missing authentication token',
        'error.auth.session_expired': 'Session expired',
        'error.auth.account_locked': 'Account locked',
        'error.auth.account_disabled': 'Account disabled',
        
        'error.permission.access_denied': 'Access denied',
        'error.permission.insufficient_role': 'Insufficient permissions',
        'error.permission.resource_forbidden': 'Access to this resource is forbidden',
        'error.permission.operation_forbidden': 'This operation is forbidden',
        'error.permission.tenant_mismatch': 'Tenant mismatch',
        
        'error.not_found.resource': 'Resource not found',
        'error.not_found.user': 'User not found',
        'error.not_found.task': 'Task not found',
        'error.not_found.project': 'Project not found',
        'error.not_found.annotation': 'Annotation not found',
        'error.not_found.data_source': 'Data source not found',
        'error.not_found.evaluation': 'Evaluation result not found',
        'error.not_found.rule': 'Rule not found',
        'error.not_found.endpoint': 'Endpoint not found',
        
        'error.conflict.resource_exists': 'Resource already exists',
        'error.conflict.version_mismatch': 'Version mismatch',
        'error.conflict.state_invalid': 'Invalid state',
        'error.conflict.duplicate_key': 'Duplicate key',
        'error.conflict.concurrent_update': 'Concurrent update conflict',
        
        'error.rate_limit.exceeded': 'Rate limit exceeded',
        'error.rate_limit.api_quota': 'API quota exhausted',
        'error.rate_limit.user_quota': 'User quota exhausted',
        
        'error.internal.server_error': 'Internal server error',
        'error.internal.database_error': 'Database error',
        'error.internal.cache_error': 'Cache error',
        'error.internal.processing_error': 'Processing error',
        'error.internal.configuration_error': 'Configuration error',
        'error.internal.unexpected_error': 'Unexpected error',
        
        'error.service.unavailable': 'Service unavailable',
        'error.service.maintenance': 'Service under maintenance',
        'error.service.overloaded': 'Service overloaded',
        'error.service.dependency_failed': 'Dependency service failed',
        'error.service.timeout': 'Service timeout',
        
        # Cache Strategy - cache.*
        'cache.strategy.cache_hit': 'Cache hit',
        'cache.strategy.cache_miss': 'Cache miss',
        'cache.strategy.cache_set': 'Cache set',
        'cache.strategy.cache_invalidated': 'Cache invalidated',
        'cache.strategy.batch_invalidated': 'Batch cache invalidated',
        
        'cache.warmup.started': 'Cache warmup started',
        'cache.warmup.completed': 'Cache warmup completed',
        'cache.warmup.failed': 'Cache warmup failed',
        
        'cache.monitor.hit_rate_low': 'Cache hit rate too low',
        'cache.monitor.stats_reset': 'Cache statistics reset',
        
        'cache.error.connection_failed': 'Cache connection failed',
        'cache.error.serialization_failed': 'Serialization failed',
        'cache.error.deserialization_failed': 'Deserialization failed',
        'cache.error.operation_failed': 'Cache operation failed',
        
        # Database Operations - database.*
        'database.batch.insert_started': 'Batch insert started: {count} records',
        'database.batch.insert_completed': 'Batch insert completed: {count} records, duration {duration}ms',
        'database.batch.update_started': 'Batch update started: {count} records',
        'database.batch.update_completed': 'Batch update completed: {count} records, duration {duration}ms',
        'database.batch.upsert_started': 'Batch upsert started: {count} records',
        'database.batch.upsert_completed': 'Batch upsert completed: {count} records, duration {duration}ms',
        'database.error.batch_failed': 'Batch operation failed: {error}',
        
        'database.pagination.invalid_page': 'Invalid page number: {page}',
        'database.pagination.invalid_size': 'Invalid page size: {size}',
        'database.pagination.query_started': 'Pagination query started: page={page}, size={size}',
        'database.pagination.query_completed': 'Pagination query completed: returned {count} records',
        'database.error.query_failed': 'Query failed: {error}',
        
        'database.monitor.slow_query_detected': 'Slow query detected: {duration}ms, SQL: {sql}',
        'database.monitor.stats_reset': 'Slow query statistics reset',
        'database.monitor.threshold_updated': 'Slow query threshold updated: {threshold}ms',
        'database.monitor.query_recorded': 'Query recorded: {duration}ms',
        
        # SLA Notification - sla_monitor.*
        'sla_monitor.notification.email_subject_breach': 'SLA Breach Alert: {ticket_title}',
        'sla_monitor.notification.email_subject_warning': 'SLA Warning: {ticket_title}',
        'sla_monitor.notification.email_subject_escalation': 'SLA Escalation Alert: {ticket_title}',
        
        'sla_monitor.notification.breach_message': 'Ticket {ticket_id} has breached SLA, please handle immediately',
        'sla_monitor.notification.warning_message': 'Ticket {ticket_id} is about to breach SLA, please handle soon',
        'sla_monitor.notification.escalation_message': 'Ticket {ticket_id} SLA breach has been escalated',
        
        'sla_monitor.notification.send_failed': 'Notification send failed: {error}',
        'sla_monitor.notification.channel_unavailable': 'Notification channel unavailable: {channel}',
        'sla_monitor.notification.retry_attempt': 'Retrying notification send (attempt {attempt})',
        'sla_monitor.notification.all_channels_failed': 'All notification channels failed',
        'sla_monitor.notification.send_success': 'Notification sent successfully: {channel}',
        
        'sla_monitor.notification.wechat_card_title': 'SLA Alert Notification',
        'sla_monitor.notification.wechat_card_description': 'Ticket {ticket_id} requires your attention',
        
        # Compliance Scheduler - compliance.*
        'compliance.scheduler.job_added': 'Compliance report job added: {report_type}',
        'compliance.scheduler.job_removed': 'Compliance report job removed: {report_type}',
        'compliance.scheduler.job_executed': 'Compliance report job executed: {report_type}',
        'compliance.scheduler.job_failed': 'Compliance report job failed: {error}',
        'compliance.scheduler.invalid_cron': 'Invalid cron expression: {expression}',
        'compliance.scheduler.invalid_report_type': 'Invalid report type: {report_type}',
        'compliance.scheduler.next_run': 'Next run time: {next_run}',
        
        # Sync Manager - sync.*
        'sync.manager.sync_started': 'Sync started',
        'sync.manager.sync_completed': 'Sync completed: {count} records',
        'sync.manager.sync_failed': 'Sync failed: {error}',
        'sync.manager.conflict_resolved': 'Conflict resolved: {item_id}',
        'sync.manager.model_downloaded': 'Model downloaded: {model_name}',
        
        # Report Service - report.*
        'report.email.send_started': 'Email send started: {recipient}',
        'report.email.send_completed': 'Email send completed: {recipient}',
        'report.email.send_failed': 'Email send failed: {error}',
        'report.email.retry_attempt': 'Email send retry (attempt {attempt})',
        
        # ============================================================================
        # Security Control Module
        # ============================================================================
        
        # Encryption Service - security.encryption.*
        'security.encryption.empty_plaintext': 'Plaintext cannot be empty',
        'security.encryption.empty_ciphertext': 'Ciphertext cannot be empty',
        'security.encryption.invalid_ciphertext': 'Invalid ciphertext format',
        'security.encryption.invalid_key': 'Invalid encryption key',
        'security.encryption.no_key': 'No encryption key provided',
        'security.encryption.encrypt_success': 'Encryption successful',
        'security.encryption.encrypt_failed': 'Encryption failed',
        'security.encryption.decrypt_success': 'Decryption successful',
        'security.encryption.decrypt_failed': 'Decryption failed',
        'security.encryption.key_generated': 'Key generated',
        'security.encryption.key_derived': 'Key derived',
        
        # Rate Limiting - security.rate_limit.*
        'security.rate_limit.exceeded': 'Rate limit exceeded, please try again later',
        'security.rate_limit.limit_info': 'Limit: {limit} requests/{window} seconds',
        'security.rate_limit.remaining': 'Remaining requests: {remaining}',
        'security.rate_limit.reset_time': 'Reset time: {reset_time}',
        'security.rate_limit.blocked': 'Request blocked',
        'security.rate_limit.config_updated': 'Rate limit configuration updated',
        
        # Input Validation - security.validation.*
        'security.validation.invalid_email': 'Invalid email format',
        'security.validation.invalid_phone': 'Invalid phone number format',
        'security.validation.invalid_url': 'Invalid URL format',
        'security.validation.invalid_ip': 'Invalid IP address format',
        'security.validation.invalid_uuid': 'Invalid UUID format',
        'security.validation.xss_detected': 'Potential XSS attack detected',
        'security.validation.sql_injection_detected': 'Potential SQL injection detected',
        'security.validation.path_traversal_detected': 'Path traversal attack detected',
        'security.validation.field_required': 'Field {field} is required',
        'security.validation.field_too_long': 'Field {field} exceeds maximum length {max_length}',
        'security.validation.field_too_short': 'Field {field} is shorter than minimum length {min_length}',
        'security.validation.field_invalid_pattern': 'Field {field} has invalid format',
        
        # Audit Logging - security.audit.*
        'security.audit.event_logged': 'Audit event logged',
        'security.audit.login_success': 'User {username} logged in successfully',
        'security.audit.login_failed': 'User {username} login failed',
        'security.audit.logout': 'User {username} logged out',
        'security.audit.password_changed': 'User {username} password changed',
        'security.audit.permission_changed': 'User {username} permissions changed',
        'security.audit.resource_accessed': 'Resource {resource} accessed',
        'security.audit.resource_created': 'Resource {resource} created',
        'security.audit.resource_updated': 'Resource {resource} updated',
        'security.audit.resource_deleted': 'Resource {resource} deleted',
        'security.audit.sensitive_operation': 'Sensitive operation: {operation}',
        'security.audit.suspicious_activity': 'Suspicious activity: {activity}',
        'security.audit.ip_blocked': 'IP {ip} blocked',
        'security.audit.rate_limit_exceeded': 'User {username} exceeded rate limit',
        
        # ============================================================================
        # Monitoring and Alerting Module
        # ============================================================================
        
        # Prometheus Metrics - monitoring.metrics.*
        'monitoring.metrics.counter_negative_value': 'Counter value cannot be negative',
        'monitoring.metrics.metric_already_registered': 'Metric already registered: {name}',
        'monitoring.metrics.metric_registered': 'Metric registered: {name}',
        'monitoring.metrics.metric_unregistered': 'Metric unregistered: {name}',
        
        # Alert Configuration - monitoring.alert.*
        'monitoring.alert.invalid_duration': 'Invalid duration',
        'monitoring.alert.invalid_value': 'Invalid threshold value',
        'monitoring.alert.invalid_cooldown': 'Invalid cooldown time',
        'monitoring.alert.invalid_max_alerts': 'Invalid max alerts count',
        'monitoring.alert.threshold_added': 'Alert threshold added: {id}',
        'monitoring.alert.threshold_updated': 'Alert threshold updated: {id}',
        'monitoring.alert.threshold_removed': 'Alert threshold removed: {id}',
        'monitoring.alert.threshold_not_found': 'Alert threshold not found: {id}',
        'monitoring.alert.hourly_limit_reached': 'Hourly alert limit reached',
        'monitoring.alert.callback_error': 'Alert callback error: {error}',
        'monitoring.alert.config_updated': 'Alert configuration updated',
        'monitoring.alert.cooldown_updated': 'Cooldown updated: {seconds} seconds',
        'monitoring.alert.max_alerts_updated': 'Max alerts per hour updated: {max_alerts}',
        'monitoring.alert.channel_added': 'Notification channel added: {channel}',
        'monitoring.alert.channel_removed': 'Notification channel removed: {channel}',
        'monitoring.alert.acknowledged': 'Alert acknowledged: {id}',
        'monitoring.alert.resolved': 'Alert resolved: {id}',
        
        # Health Check - monitoring.health.*
        'monitoring.health.timeout': 'Service {service} health check timeout',
        'monitoring.health.database_connected': 'Database connection healthy',
        'monitoring.health.database_not_configured': 'Database not configured',
        'monitoring.health.redis_connected': 'Redis connection healthy',
        'monitoring.health.redis_not_installed': 'Redis client not installed',
        'monitoring.health.neo4j_connected': 'Neo4j connection healthy',
        'monitoring.health.neo4j_not_configured': 'Neo4j not configured',
        'monitoring.health.label_studio_connected': 'Label Studio connection healthy',
        'monitoring.health.label_studio_not_configured': 'Label Studio not configured',
        'monitoring.health.label_studio_error': 'Label Studio error: {code}',
        'monitoring.health.api_connected': '{name} API connection healthy',
        'monitoring.health.api_error': '{name} API error: {code}',
        'monitoring.health.checker_registered': 'Health checker registered: {name}',
        'monitoring.health.checker_unregistered': 'Health checker unregistered: {name}',
        
        # Service Alert - monitoring.service_alert.*
        'monitoring.service_alert.already_monitoring': 'Monitoring already running',
        'monitoring.service_alert.monitoring_started': 'Service monitoring started',
        'monitoring.service_alert.monitoring_stopped': 'Service monitoring stopped',
        'monitoring.service_alert.monitoring_error': 'Monitoring error: {error}',
        'monitoring.service_alert.alert_triggered': 'Service alert triggered: {service} status={status} severity={severity}',
        'monitoring.service_alert.recovery_triggered': 'Service recovery notification: {service} status={status}',
        'monitoring.service_alert.callback_error': 'Callback error: {error}',
        'monitoring.service_alert.config_updated': 'Service alert configuration updated',
        
        # ============================================================================
        # Enterprise Ontology Module
        # ============================================================================
        
        # Ontology Manager - ontology.manager.*
        'ontology.manager.initialized': 'Enterprise ontology manager initialized',
        'ontology.manager.entity_created': 'Ontology entity created: {name}',
        'ontology.manager.entity_updated': 'Ontology entity updated: {name}',
        'ontology.manager.entity_deleted': 'Ontology entity deleted: {id}',
        'ontology.manager.relation_created': 'Ontology relation created: {type}',
        'ontology.manager.relation_updated': 'Ontology relation updated: {id}',
        'ontology.manager.relation_deleted': 'Ontology relation deleted: {id}',
        'ontology.manager.cache_cleared': 'Ontology cache cleared',
        'ontology.manager.lineage_tracked': 'Data lineage tracked: {entity_id}',
        
        # AI Data Converter - ontology.converter.*
        'ontology.converter.initialized': 'AI data converter initialized',
        'ontology.converter.conversion_started': 'Data conversion started: {format}',
        'ontology.converter.conversion_completed': 'Data conversion completed: {count} records',
        'ontology.converter.conversion_failed': 'Data conversion failed: {error}',
        'ontology.converter.validation_passed': 'Data validation passed',
        'ontology.converter.validation_failed': 'Data validation failed: {count} invalid records',
        'ontology.converter.missing_question': 'Missing question/instruction field',
        'ontology.converter.missing_answer': 'Missing answer/output field',
        
        # Compliance Validation - ontology.compliance.*
        'ontology.compliance.check_started': 'Compliance check started',
        'ontology.compliance.check_completed': 'Compliance check completed',
        'ontology.compliance.compliant': 'Entity is compliant',
        'ontology.compliance.non_compliant': 'Entity is non-compliant',
        'ontology.compliance.missing_classification': 'Missing data classification level',
        'ontology.compliance.cross_border_violation': 'Data not allowed for cross-border transfer to {target}',
        'ontology.compliance.pii_sensitivity_mismatch': 'Contains PII but sensitivity level is not high',
        'ontology.compliance.pii_classification_mismatch': 'Contains PII but data classification level is too low',
        'ontology.compliance.missing_retention_period': 'Contains PII but no retention period is set',
        
        # Entity Types - ontology.entity_type.*
        'ontology.entity_type.person': 'Person',
        'ontology.entity_type.organization': 'Organization',
        'ontology.entity_type.document': 'Document',
        'ontology.entity_type.location': 'Location',
        'ontology.entity_type.department': 'Department',
        'ontology.entity_type.business_unit': 'Business Unit',
        'ontology.entity_type.regulation': 'Regulation',
        'ontology.entity_type.contract': 'Contract',
        'ontology.entity_type.approval': 'Approval',
        'ontology.entity_type.seal': 'Seal',
        'ontology.entity_type.invoice': 'Invoice',
        'ontology.entity_type.certificate': 'Certificate',
        'ontology.entity_type.budget': 'Budget',
        'ontology.entity_type.project': 'Project',
        'ontology.entity_type.meeting': 'Meeting',
        'ontology.entity_type.policy': 'Policy',
        
        # Relation Types - ontology.relation_type.*
        'ontology.relation_type.belongs_to': 'Belongs To',
        'ontology.relation_type.created_by': 'Created By',
        'ontology.relation_type.related_to': 'Related To',
        'ontology.relation_type.reports_to': 'Reports To',
        'ontology.relation_type.approves': 'Approves',
        'ontology.relation_type.seals': 'Seals',
        'ontology.relation_type.complies_with': 'Complies With',
        'ontology.relation_type.supervises': 'Supervises',
        'ontology.relation_type.delegates_to': 'Delegates To',
        'ontology.relation_type.manages': 'Manages',
        'ontology.relation_type.participates_in': 'Participates In',
        'ontology.relation_type.signs': 'Signs',
        'ontology.relation_type.reviews': 'Reviews',
        'ontology.relation_type.issues': 'Issues',
        'ontology.relation_type.holds': 'Holds',
        
        # Data Classification - ontology.classification.*
        'ontology.classification.public': 'Public',
        'ontology.classification.internal': 'Internal',
        'ontology.classification.confidential': 'Confidential',
        'ontology.classification.secret': 'Secret',
        'ontology.classification.top_secret': 'Top Secret',
        
        # Sensitivity Level - ontology.sensitivity.*
        'ontology.sensitivity.low': 'Low',
        'ontology.sensitivity.medium': 'Medium',
        'ontology.sensitivity.high': 'High',
        'ontology.sensitivity.critical': 'Critical',
        
        # AI Data Format - ontology.format.*
        'ontology.format.alpaca': 'Alpaca Format',
        'ontology.format.sharegpt': 'ShareGPT Format',
        'ontology.format.openai': 'OpenAI Fine-tuning Format',
        'ontology.format.llama_factory': 'LLaMA-Factory Format',
        'ontology.format.fastchat': 'FastChat Format',
        'ontology.format.belle': 'BELLE Format',
        'ontology.format.custom': 'Custom Format',
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
