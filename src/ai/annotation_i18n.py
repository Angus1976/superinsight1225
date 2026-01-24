"""
AI Annotation Methods Internationalization Module

Provides i18n support for all AI annotation features including:
- Pre-annotation engine messages
- Mid-coverage engine messages  
- Post-validation engine messages
- Collaboration manager messages
- Method switcher messages
- Security and audit messages
- Error messages

Supports: zh-CN (Chinese) and en-US (English)

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

from typing import Dict, Any, Optional
from datetime import datetime
import locale

# AI Annotation Translation Keys
AI_ANNOTATION_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'zh': {
        # ==========================================================================
        # Pre-Annotation Engine (预标注引擎)
        # ==========================================================================
        'ai.preannotation.title': 'AI 预标注',
        'ai.preannotation.description': '使用 AI 模型自动预标注数据',
        'ai.preannotation.batch_started': '批量预标注任务已启动',
        'ai.preannotation.batch_completed': '批量预标注任务已完成',
        'ai.preannotation.batch_failed': '批量预标注任务失败',
        'ai.preannotation.item_processed': '项目已处理',
        'ai.preannotation.item_failed': '项目处理失败',
        'ai.preannotation.progress': '预标注进度',
        'ai.preannotation.confidence_low': '置信度低于阈值，需要人工审核',
        'ai.preannotation.sample_learning': '使用样本学习',
        'ai.preannotation.no_samples': '没有可用的样本数据',
        'ai.preannotation.chunk_processing': '分块处理中',
        'ai.preannotation.results_ready': '预标注结果已就绪',
        'ai.preannotation.flagged_for_review': '已标记需要审核',
        'ai.preannotation.auto_approved': '自动批准',
        'ai.preannotation.task_created': '预标注任务已创建',
        'ai.preannotation.task_cancelled': '预标注任务已取消',
        'ai.preannotation.invalid_type': '不支持的标注类型',
        'ai.preannotation.model_loading': '正在加载模型',
        'ai.preannotation.model_loaded': '模型加载完成',
        'ai.preannotation.model_error': '模型加载失败',
        
        # ==========================================================================
        # Mid-Coverage Engine (实时辅助引擎)
        # ==========================================================================
        'ai.midcoverage.title': '实时标注辅助',
        'ai.midcoverage.description': '在标注过程中提供实时 AI 建议',
        'ai.midcoverage.suggestion_ready': '建议已就绪',
        'ai.midcoverage.suggestion_accepted': '建议已接受',
        'ai.midcoverage.suggestion_rejected': '建议已拒绝',
        'ai.midcoverage.suggestion_modified': '建议已修改',
        'ai.midcoverage.pattern_detected': '检测到标注模式',
        'ai.midcoverage.pattern_applied': '模式已应用',
        'ai.midcoverage.batch_coverage': '批量覆盖',
        'ai.midcoverage.batch_coverage_applied': '批量覆盖已应用',
        'ai.midcoverage.batch_coverage_skipped': '批量覆盖已跳过',
        'ai.midcoverage.conflict_detected': '检测到标注冲突',
        'ai.midcoverage.conflict_resolved': '冲突已解决',
        'ai.midcoverage.high_rejection_rate': '拒绝率过高，已通知质检员',
        'ai.midcoverage.similarity_low': '相似度低于阈值',
        'ai.midcoverage.feedback_recorded': '反馈已记录',
        'ai.midcoverage.learning_updated': '学习模型已更新',
        'ai.midcoverage.latency_warning': '响应延迟超过阈值',
        
        # ==========================================================================
        # Post-Validation Engine (后验证引擎)
        # ==========================================================================
        'ai.postvalidation.title': '质量验证',
        'ai.postvalidation.description': '多维度标注质量评估',
        'ai.postvalidation.validation_started': '质量验证已启动',
        'ai.postvalidation.validation_completed': '质量验证已完成',
        'ai.postvalidation.validation_failed': '质量验证失败',
        'ai.postvalidation.quality_report': '质量报告',
        'ai.postvalidation.accuracy': '准确率',
        'ai.postvalidation.recall': '召回率',
        'ai.postvalidation.consistency': '一致性',
        'ai.postvalidation.completeness': '完整性',
        'ai.postvalidation.inter_annotator_agreement': '标注者间一致性',
        'ai.postvalidation.below_threshold': '低于质量阈值',
        'ai.postvalidation.above_threshold': '高于质量阈值',
        'ai.postvalidation.inconsistency_detected': '检测到不一致标注',
        'ai.postvalidation.inconsistency_grouped': '不一致标注已分组',
        'ai.postvalidation.review_task_created': '审核任务已创建',
        'ai.postvalidation.quality_degradation': '质量下降警告',
        'ai.postvalidation.quality_improvement': '质量提升',
        'ai.postvalidation.trend_analysis': '趋势分析',
        'ai.postvalidation.recommendation': '改进建议',
        
        # ==========================================================================
        # Method Switcher (方法切换器)
        # ==========================================================================
        'ai.switcher.title': '标注引擎管理',
        'ai.switcher.description': '管理和切换标注引擎',
        'ai.switcher.engine_selected': '引擎已选择',
        'ai.switcher.engine_switched': '引擎已切换',
        'ai.switcher.engine_registered': '引擎已注册',
        'ai.switcher.engine_unregistered': '引擎已注销',
        'ai.switcher.engine_updated': '引擎配置已更新',
        'ai.switcher.engine_unavailable': '引擎不可用',
        'ai.switcher.fallback_activated': '已切换到备用引擎',
        'ai.switcher.fallback_failed': '备用引擎也不可用',
        'ai.switcher.comparison_started': '引擎比较已启动',
        'ai.switcher.comparison_completed': '引擎比较已完成',
        'ai.switcher.ab_test_started': 'A/B 测试已启动',
        'ai.switcher.ab_test_completed': 'A/B 测试已完成',
        'ai.switcher.hot_reload': '引擎热重载',
        'ai.switcher.hot_reload_success': '热重载成功',
        'ai.switcher.hot_reload_failed': '热重载失败',
        'ai.switcher.format_normalized': '格式已标准化',
        'ai.switcher.format_migration': '格式迁移',
        'ai.switcher.format_migration_success': '格式迁移成功',
        'ai.switcher.format_migration_failed': '格式迁移失败',
        'ai.switcher.health_check': '健康检查',
        'ai.switcher.health_check_passed': '健康检查通过',
        'ai.switcher.health_check_failed': '健康检查失败',
        'ai.switcher.retry_scheduled': '已安排重试',
        
        # ==========================================================================
        # Collaboration Manager (协作管理器)
        # ==========================================================================
        'ai.collaboration.title': '协作标注',
        'ai.collaboration.description': '人机协作标注工作流',
        'ai.collaboration.task_assigned': '任务已分配',
        'ai.collaboration.task_completed': '任务已完成',
        'ai.collaboration.task_reassigned': '任务已重新分配',
        'ai.collaboration.annotation_submitted': '标注已提交',
        'ai.collaboration.annotation_approved': '标注已批准',
        'ai.collaboration.annotation_rejected': '标注已拒绝',
        'ai.collaboration.conflict_detected': '检测到冲突',
        'ai.collaboration.conflict_resolved': '冲突已解决',
        'ai.collaboration.workload_updated': '工作量已更新',
        'ai.collaboration.progress_updated': '进度已更新',
        'ai.collaboration.real_time_sync': '实时同步',
        'ai.collaboration.connection_established': '连接已建立',
        'ai.collaboration.connection_lost': '连接已断开',
        'ai.collaboration.reconnecting': '正在重新连接',
        'ai.collaboration.broadcast_sent': '广播已发送',
        'ai.collaboration.notification_sent': '通知已发送',
        
        # ==========================================================================
        # Annotator Roles (标注者角色)
        # ==========================================================================
        'ai.role.annotator': '标注员',
        'ai.role.expert_reviewer': '专家审核员',
        'ai.role.quality_checker': '质检员',
        'ai.role.external_contractor': '外部承包商',
        'ai.role.project_manager': '项目经理',
        'ai.role.admin': '管理员',
        
        # ==========================================================================
        # Annotation Types (标注类型)
        # ==========================================================================
        'ai.type.ner': '命名实体识别',
        'ai.type.classification': '文本分类',
        'ai.type.sentiment': '情感分析',
        'ai.type.relation_extraction': '关系抽取',
        'ai.type.summarization': '文本摘要',
        'ai.type.qa': '问答对',
        'ai.type.translation': '翻译',
        'ai.type.custom': '自定义',
        
        # ==========================================================================
        # Engine Types (引擎类型)
        # ==========================================================================
        'ai.engine.label_studio': 'Label Studio ML 后端',
        'ai.engine.argilla': 'Argilla',
        'ai.engine.ollama': 'Ollama 本地模型',
        'ai.engine.openai': 'OpenAI',
        'ai.engine.chinese_llm': '国产大模型',
        'ai.engine.huggingface': 'HuggingFace',
        'ai.engine.custom': '自定义引擎',
        
        # ==========================================================================
        # Security & Audit (安全与审计)
        # ==========================================================================
        'ai.security.audit_logged': '审计日志已记录',
        'ai.security.access_denied': '访问被拒绝',
        'ai.security.permission_required': '需要权限',
        'ai.security.role_required': '需要角色: {role}',
        'ai.security.tenant_mismatch': '租户不匹配',
        'ai.security.pii_detected': '检测到敏感信息',
        'ai.security.pii_desensitized': '敏感信息已脱敏',
        'ai.security.data_encrypted': '数据已加密',
        'ai.security.data_decrypted': '数据已解密',
        'ai.security.version_created': '版本已创建',
        'ai.security.version_restored': '版本已恢复',
        'ai.security.export_started': '导出已启动',
        'ai.security.export_completed': '导出已完成',
        'ai.security.export_failed': '导出失败',
        'ai.security.import_started': '导入已启动',
        'ai.security.import_completed': '导入已完成',
        'ai.security.import_failed': '导入失败',
        
        # ==========================================================================
        # Error Messages (错误消息)
        # ==========================================================================
        'ai.error.invalid_annotation_type': '无效的标注类型: {type}',
        'ai.error.invalid_engine': '无效的引擎: {engine}',
        'ai.error.engine_not_found': '引擎未找到: {engine}',
        'ai.error.engine_timeout': '引擎超时: {engine}',
        'ai.error.engine_error': '引擎错误: {message}',
        'ai.error.model_not_found': '模型未找到: {model}',
        'ai.error.model_load_failed': '模型加载失败: {message}',
        'ai.error.prediction_failed': '预测失败: {message}',
        'ai.error.validation_failed': '验证失败: {message}',
        'ai.error.batch_too_large': '批量大小超过限制: {size}',
        'ai.error.confidence_invalid': '置信度无效: {value}',
        'ai.error.task_not_found': '任务未找到: {task_id}',
        'ai.error.item_not_found': '项目未找到: {item_id}',
        'ai.error.annotation_not_found': '标注未找到: {annotation_id}',
        'ai.error.conflict_not_found': '冲突未找到: {conflict_id}',
        'ai.error.user_not_found': '用户未找到: {user_id}',
        'ai.error.project_not_found': '项目未找到: {project_id}',
        'ai.error.permission_denied': '权限不足: {action}',
        'ai.error.rate_limit_exceeded': '请求频率超限',
        'ai.error.network_error': '网络错误: {message}',
        'ai.error.database_error': '数据库错误: {message}',
        'ai.error.websocket_error': 'WebSocket 错误: {message}',
        'ai.error.retry_exhausted': '重试次数已用尽',
        'ai.error.format_conversion_failed': '格式转换失败: {message}',
        'ai.error.export_failed': '导出失败: {message}',
        'ai.error.import_failed': '导入失败: {message}',
        
        # ==========================================================================
        # Quality Metrics Labels (质量指标标签)
        # ==========================================================================
        'ai.metric.accuracy': '准确率',
        'ai.metric.recall': '召回率',
        'ai.metric.precision': '精确率',
        'ai.metric.f1_score': 'F1 分数',
        'ai.metric.consistency': '一致性',
        'ai.metric.completeness': '完整性',
        'ai.metric.latency': '延迟',
        'ai.metric.throughput': '吞吐量',
        'ai.metric.success_rate': '成功率',
        'ai.metric.error_rate': '错误率',
        'ai.metric.rejection_rate': '拒绝率',
        'ai.metric.acceptance_rate': '接受率',
        'ai.metric.coverage': '覆盖率',
        'ai.metric.confidence_avg': '平均置信度',
        'ai.metric.processing_time': '处理时间',
        'ai.metric.queue_length': '队列长度',
        
        # ==========================================================================
        # UI Labels (界面标签)
        # ==========================================================================
        'ai.ui.start': '开始',
        'ai.ui.stop': '停止',
        'ai.ui.pause': '暂停',
        'ai.ui.resume': '继续',
        'ai.ui.cancel': '取消',
        'ai.ui.confirm': '确认',
        'ai.ui.save': '保存',
        'ai.ui.submit': '提交',
        'ai.ui.approve': '批准',
        'ai.ui.reject': '拒绝',
        'ai.ui.accept': '接受',
        'ai.ui.modify': '修改',
        'ai.ui.delete': '删除',
        'ai.ui.edit': '编辑',
        'ai.ui.view': '查看',
        'ai.ui.export': '导出',
        'ai.ui.import': '导入',
        'ai.ui.refresh': '刷新',
        'ai.ui.filter': '筛选',
        'ai.ui.search': '搜索',
        'ai.ui.sort': '排序',
        'ai.ui.settings': '设置',
        'ai.ui.configuration': '配置',
        'ai.ui.dashboard': '仪表板',
        'ai.ui.history': '历史',
        'ai.ui.details': '详情',
        'ai.ui.summary': '摘要',
        'ai.ui.statistics': '统计',
        'ai.ui.progress': '进度',
        'ai.ui.status': '状态',
        'ai.ui.actions': '操作',
        'ai.ui.options': '选项',
        'ai.ui.help': '帮助',
        'ai.ui.loading': '加载中...',
        'ai.ui.processing': '处理中...',
        'ai.ui.no_data': '暂无数据',
        'ai.ui.select_all': '全选',
        'ai.ui.deselect_all': '取消全选',
        'ai.ui.expand': '展开',
        'ai.ui.collapse': '收起',
        'ai.ui.previous': '上一个',
        'ai.ui.next': '下一个',
        'ai.ui.first': '第一个',
        'ai.ui.last': '最后一个',
        'ai.ui.page': '页',
        'ai.ui.total': '共计',
        'ai.ui.items': '项',
    },
    
    'en': {
        # ==========================================================================
        # Pre-Annotation Engine
        # ==========================================================================
        'ai.preannotation.title': 'AI Pre-Annotation',
        'ai.preannotation.description': 'Automatically pre-annotate data using AI models',
        'ai.preannotation.batch_started': 'Batch pre-annotation task started',
        'ai.preannotation.batch_completed': 'Batch pre-annotation task completed',
        'ai.preannotation.batch_failed': 'Batch pre-annotation task failed',
        'ai.preannotation.item_processed': 'Item processed',
        'ai.preannotation.item_failed': 'Item processing failed',
        'ai.preannotation.progress': 'Pre-annotation progress',
        'ai.preannotation.confidence_low': 'Confidence below threshold, requires human review',
        'ai.preannotation.sample_learning': 'Using sample-based learning',
        'ai.preannotation.no_samples': 'No sample data available',
        'ai.preannotation.chunk_processing': 'Processing in chunks',
        'ai.preannotation.results_ready': 'Pre-annotation results ready',
        'ai.preannotation.flagged_for_review': 'Flagged for review',
        'ai.preannotation.auto_approved': 'Auto-approved',
        'ai.preannotation.task_created': 'Pre-annotation task created',
        'ai.preannotation.task_cancelled': 'Pre-annotation task cancelled',
        'ai.preannotation.invalid_type': 'Unsupported annotation type',
        'ai.preannotation.model_loading': 'Loading model',
        'ai.preannotation.model_loaded': 'Model loaded',
        'ai.preannotation.model_error': 'Model loading failed',
        
        # ==========================================================================
        # Mid-Coverage Engine
        # ==========================================================================
        'ai.midcoverage.title': 'Real-Time Annotation Assistance',
        'ai.midcoverage.description': 'Provide real-time AI suggestions during annotation',
        'ai.midcoverage.suggestion_ready': 'Suggestion ready',
        'ai.midcoverage.suggestion_accepted': 'Suggestion accepted',
        'ai.midcoverage.suggestion_rejected': 'Suggestion rejected',
        'ai.midcoverage.suggestion_modified': 'Suggestion modified',
        'ai.midcoverage.pattern_detected': 'Annotation pattern detected',
        'ai.midcoverage.pattern_applied': 'Pattern applied',
        'ai.midcoverage.batch_coverage': 'Batch coverage',
        'ai.midcoverage.batch_coverage_applied': 'Batch coverage applied',
        'ai.midcoverage.batch_coverage_skipped': 'Batch coverage skipped',
        'ai.midcoverage.conflict_detected': 'Annotation conflict detected',
        'ai.midcoverage.conflict_resolved': 'Conflict resolved',
        'ai.midcoverage.high_rejection_rate': 'High rejection rate, quality checker notified',
        'ai.midcoverage.similarity_low': 'Similarity below threshold',
        'ai.midcoverage.feedback_recorded': 'Feedback recorded',
        'ai.midcoverage.learning_updated': 'Learning model updated',
        'ai.midcoverage.latency_warning': 'Response latency exceeded threshold',
        
        # ==========================================================================
        # Post-Validation Engine
        # ==========================================================================
        'ai.postvalidation.title': 'Quality Validation',
        'ai.postvalidation.description': 'Multi-dimensional annotation quality assessment',
        'ai.postvalidation.validation_started': 'Quality validation started',
        'ai.postvalidation.validation_completed': 'Quality validation completed',
        'ai.postvalidation.validation_failed': 'Quality validation failed',
        'ai.postvalidation.quality_report': 'Quality Report',
        'ai.postvalidation.accuracy': 'Accuracy',
        'ai.postvalidation.recall': 'Recall',
        'ai.postvalidation.consistency': 'Consistency',
        'ai.postvalidation.completeness': 'Completeness',
        'ai.postvalidation.inter_annotator_agreement': 'Inter-Annotator Agreement',
        'ai.postvalidation.below_threshold': 'Below quality threshold',
        'ai.postvalidation.above_threshold': 'Above quality threshold',
        'ai.postvalidation.inconsistency_detected': 'Inconsistent annotations detected',
        'ai.postvalidation.inconsistency_grouped': 'Inconsistent annotations grouped',
        'ai.postvalidation.review_task_created': 'Review task created',
        'ai.postvalidation.quality_degradation': 'Quality degradation warning',
        'ai.postvalidation.quality_improvement': 'Quality improvement',
        'ai.postvalidation.trend_analysis': 'Trend Analysis',
        'ai.postvalidation.recommendation': 'Improvement Recommendation',
        
        # ==========================================================================
        # Method Switcher
        # ==========================================================================
        'ai.switcher.title': 'Annotation Engine Management',
        'ai.switcher.description': 'Manage and switch annotation engines',
        'ai.switcher.engine_selected': 'Engine selected',
        'ai.switcher.engine_switched': 'Engine switched',
        'ai.switcher.engine_registered': 'Engine registered',
        'ai.switcher.engine_unregistered': 'Engine unregistered',
        'ai.switcher.engine_updated': 'Engine configuration updated',
        'ai.switcher.engine_unavailable': 'Engine unavailable',
        'ai.switcher.fallback_activated': 'Switched to fallback engine',
        'ai.switcher.fallback_failed': 'Fallback engine also unavailable',
        'ai.switcher.comparison_started': 'Engine comparison started',
        'ai.switcher.comparison_completed': 'Engine comparison completed',
        'ai.switcher.ab_test_started': 'A/B test started',
        'ai.switcher.ab_test_completed': 'A/B test completed',
        'ai.switcher.hot_reload': 'Engine hot reload',
        'ai.switcher.hot_reload_success': 'Hot reload successful',
        'ai.switcher.hot_reload_failed': 'Hot reload failed',
        'ai.switcher.format_normalized': 'Format normalized',
        'ai.switcher.format_migration': 'Format migration',
        'ai.switcher.format_migration_success': 'Format migration successful',
        'ai.switcher.format_migration_failed': 'Format migration failed',
        'ai.switcher.health_check': 'Health check',
        'ai.switcher.health_check_passed': 'Health check passed',
        'ai.switcher.health_check_failed': 'Health check failed',
        'ai.switcher.retry_scheduled': 'Retry scheduled',
        
        # ==========================================================================
        # Collaboration Manager
        # ==========================================================================
        'ai.collaboration.title': 'Collaborative Annotation',
        'ai.collaboration.description': 'Human-AI collaborative annotation workflow',
        'ai.collaboration.task_assigned': 'Task assigned',
        'ai.collaboration.task_completed': 'Task completed',
        'ai.collaboration.task_reassigned': 'Task reassigned',
        'ai.collaboration.annotation_submitted': 'Annotation submitted',
        'ai.collaboration.annotation_approved': 'Annotation approved',
        'ai.collaboration.annotation_rejected': 'Annotation rejected',
        'ai.collaboration.conflict_detected': 'Conflict detected',
        'ai.collaboration.conflict_resolved': 'Conflict resolved',
        'ai.collaboration.workload_updated': 'Workload updated',
        'ai.collaboration.progress_updated': 'Progress updated',
        'ai.collaboration.real_time_sync': 'Real-time sync',
        'ai.collaboration.connection_established': 'Connection established',
        'ai.collaboration.connection_lost': 'Connection lost',
        'ai.collaboration.reconnecting': 'Reconnecting',
        'ai.collaboration.broadcast_sent': 'Broadcast sent',
        'ai.collaboration.notification_sent': 'Notification sent',
        
        # ==========================================================================
        # Annotator Roles
        # ==========================================================================
        'ai.role.annotator': 'Annotator',
        'ai.role.expert_reviewer': 'Expert Reviewer',
        'ai.role.quality_checker': 'Quality Checker',
        'ai.role.external_contractor': 'External Contractor',
        'ai.role.project_manager': 'Project Manager',
        'ai.role.admin': 'Administrator',
        
        # ==========================================================================
        # Annotation Types
        # ==========================================================================
        'ai.type.ner': 'Named Entity Recognition',
        'ai.type.classification': 'Text Classification',
        'ai.type.sentiment': 'Sentiment Analysis',
        'ai.type.relation_extraction': 'Relation Extraction',
        'ai.type.summarization': 'Text Summarization',
        'ai.type.qa': 'Question-Answer Pairs',
        'ai.type.translation': 'Translation',
        'ai.type.custom': 'Custom',
        
        # ==========================================================================
        # Engine Types
        # ==========================================================================
        'ai.engine.label_studio': 'Label Studio ML Backend',
        'ai.engine.argilla': 'Argilla',
        'ai.engine.ollama': 'Ollama Local Model',
        'ai.engine.openai': 'OpenAI',
        'ai.engine.chinese_llm': 'Chinese LLM',
        'ai.engine.huggingface': 'HuggingFace',
        'ai.engine.custom': 'Custom Engine',
        
        # ==========================================================================
        # Security & Audit
        # ==========================================================================
        'ai.security.audit_logged': 'Audit log recorded',
        'ai.security.access_denied': 'Access denied',
        'ai.security.permission_required': 'Permission required',
        'ai.security.role_required': 'Role required: {role}',
        'ai.security.tenant_mismatch': 'Tenant mismatch',
        'ai.security.pii_detected': 'Sensitive information detected',
        'ai.security.pii_desensitized': 'Sensitive information desensitized',
        'ai.security.data_encrypted': 'Data encrypted',
        'ai.security.data_decrypted': 'Data decrypted',
        'ai.security.version_created': 'Version created',
        'ai.security.version_restored': 'Version restored',
        'ai.security.export_started': 'Export started',
        'ai.security.export_completed': 'Export completed',
        'ai.security.export_failed': 'Export failed',
        'ai.security.import_started': 'Import started',
        'ai.security.import_completed': 'Import completed',
        'ai.security.import_failed': 'Import failed',
        
        # ==========================================================================
        # Error Messages
        # ==========================================================================
        'ai.error.invalid_annotation_type': 'Invalid annotation type: {type}',
        'ai.error.invalid_engine': 'Invalid engine: {engine}',
        'ai.error.engine_not_found': 'Engine not found: {engine}',
        'ai.error.engine_timeout': 'Engine timeout: {engine}',
        'ai.error.engine_error': 'Engine error: {message}',
        'ai.error.model_not_found': 'Model not found: {model}',
        'ai.error.model_load_failed': 'Model load failed: {message}',
        'ai.error.prediction_failed': 'Prediction failed: {message}',
        'ai.error.validation_failed': 'Validation failed: {message}',
        'ai.error.batch_too_large': 'Batch size exceeds limit: {size}',
        'ai.error.confidence_invalid': 'Invalid confidence value: {value}',
        'ai.error.task_not_found': 'Task not found: {task_id}',
        'ai.error.item_not_found': 'Item not found: {item_id}',
        'ai.error.annotation_not_found': 'Annotation not found: {annotation_id}',
        'ai.error.conflict_not_found': 'Conflict not found: {conflict_id}',
        'ai.error.user_not_found': 'User not found: {user_id}',
        'ai.error.project_not_found': 'Project not found: {project_id}',
        'ai.error.permission_denied': 'Permission denied: {action}',
        'ai.error.rate_limit_exceeded': 'Rate limit exceeded',
        'ai.error.network_error': 'Network error: {message}',
        'ai.error.database_error': 'Database error: {message}',
        'ai.error.websocket_error': 'WebSocket error: {message}',
        'ai.error.retry_exhausted': 'Retry attempts exhausted',
        'ai.error.format_conversion_failed': 'Format conversion failed: {message}',
        'ai.error.export_failed': 'Export failed: {message}',
        'ai.error.import_failed': 'Import failed: {message}',
        
        # ==========================================================================
        # Quality Metrics Labels
        # ==========================================================================
        'ai.metric.accuracy': 'Accuracy',
        'ai.metric.recall': 'Recall',
        'ai.metric.precision': 'Precision',
        'ai.metric.f1_score': 'F1 Score',
        'ai.metric.consistency': 'Consistency',
        'ai.metric.completeness': 'Completeness',
        'ai.metric.latency': 'Latency',
        'ai.metric.throughput': 'Throughput',
        'ai.metric.success_rate': 'Success Rate',
        'ai.metric.error_rate': 'Error Rate',
        'ai.metric.rejection_rate': 'Rejection Rate',
        'ai.metric.acceptance_rate': 'Acceptance Rate',
        'ai.metric.coverage': 'Coverage',
        'ai.metric.confidence_avg': 'Average Confidence',
        'ai.metric.processing_time': 'Processing Time',
        'ai.metric.queue_length': 'Queue Length',
        
        # ==========================================================================
        # UI Labels
        # ==========================================================================
        'ai.ui.start': 'Start',
        'ai.ui.stop': 'Stop',
        'ai.ui.pause': 'Pause',
        'ai.ui.resume': 'Resume',
        'ai.ui.cancel': 'Cancel',
        'ai.ui.confirm': 'Confirm',
        'ai.ui.save': 'Save',
        'ai.ui.submit': 'Submit',
        'ai.ui.approve': 'Approve',
        'ai.ui.reject': 'Reject',
        'ai.ui.accept': 'Accept',
        'ai.ui.modify': 'Modify',
        'ai.ui.delete': 'Delete',
        'ai.ui.edit': 'Edit',
        'ai.ui.view': 'View',
        'ai.ui.export': 'Export',
        'ai.ui.import': 'Import',
        'ai.ui.refresh': 'Refresh',
        'ai.ui.filter': 'Filter',
        'ai.ui.search': 'Search',
        'ai.ui.sort': 'Sort',
        'ai.ui.settings': 'Settings',
        'ai.ui.configuration': 'Configuration',
        'ai.ui.dashboard': 'Dashboard',
        'ai.ui.history': 'History',
        'ai.ui.details': 'Details',
        'ai.ui.summary': 'Summary',
        'ai.ui.statistics': 'Statistics',
        'ai.ui.progress': 'Progress',
        'ai.ui.status': 'Status',
        'ai.ui.actions': 'Actions',
        'ai.ui.options': 'Options',
        'ai.ui.help': 'Help',
        'ai.ui.loading': 'Loading...',
        'ai.ui.processing': 'Processing...',
        'ai.ui.no_data': 'No data available',
        'ai.ui.select_all': 'Select All',
        'ai.ui.deselect_all': 'Deselect All',
        'ai.ui.expand': 'Expand',
        'ai.ui.collapse': 'Collapse',
        'ai.ui.previous': 'Previous',
        'ai.ui.next': 'Next',
        'ai.ui.first': 'First',
        'ai.ui.last': 'Last',
        'ai.ui.page': 'Page',
        'ai.ui.total': 'Total',
        'ai.ui.items': 'items',
    },
}


# Supported languages
SUPPORTED_LANGUAGES = ['zh', 'en']
DEFAULT_LANGUAGE = 'zh'

# Language context variable
from contextvars import ContextVar
_current_language: ContextVar[str] = ContextVar('ai_annotation_language', default=DEFAULT_LANGUAGE)


def get_current_language() -> str:
    """Get the current language setting."""
    return _current_language.get()


def set_language(language: str) -> None:
    """
    Set the current language.
    
    Args:
        language: Language code ('zh' or 'en')
        
    Raises:
        ValueError: If language is not supported
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}. Supported: {SUPPORTED_LANGUAGES}")
    _current_language.set(language)


def get_ai_translation(key: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Get translation for a key with optional parameter substitution.
    
    Args:
        key: Translation key (e.g., 'ai.preannotation.title')
        language: Language code (optional, uses current language if not specified)
        **kwargs: Parameters for string formatting
        
    Returns:
        Translated string with parameters substituted
        
    Example:
        >>> get_ai_translation('ai.error.engine_timeout', engine='ollama')
        '引擎超时: ollama'
    """
    lang = language or get_current_language()
    
    # Fallback to default language if not supported
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    translations = AI_ANNOTATION_TRANSLATIONS.get(lang, {})
    text = translations.get(key)
    
    # Fallback to English if key not found in current language
    if text is None and lang != 'en':
        text = AI_ANNOTATION_TRANSLATIONS.get('en', {}).get(key)
    
    # Return key if translation not found
    if text is None:
        return key
    
    # Substitute parameters
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # Return text without substitution if params don't match
    
    return text


# Alias for convenience
t = get_ai_translation


def get_all_translations(language: Optional[str] = None) -> Dict[str, str]:
    """
    Get all translations for a language.
    
    Args:
        language: Language code (optional, uses current language if not specified)
        
    Returns:
        Dictionary of all translation key-value pairs
    """
    lang = language or get_current_language()
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return AI_ANNOTATION_TRANSLATIONS.get(lang, {}).copy()


def has_translation(key: str, language: Optional[str] = None) -> bool:
    """
    Check if a translation key exists.
    
    Args:
        key: Translation key
        language: Language code (optional)
        
    Returns:
        True if translation exists, False otherwise
    """
    lang = language or get_current_language()
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return key in AI_ANNOTATION_TRANSLATIONS.get(lang, {})


def get_missing_translations(language: str) -> list:
    """
    Get list of translation keys missing in a language compared to English.
    
    Args:
        language: Language code to check
        
    Returns:
        List of missing translation keys
    """
    if language not in SUPPORTED_LANGUAGES:
        return []
    
    en_keys = set(AI_ANNOTATION_TRANSLATIONS.get('en', {}).keys())
    lang_keys = set(AI_ANNOTATION_TRANSLATIONS.get(language, {}).keys())
    
    return list(en_keys - lang_keys)


# =============================================================================
# Locale-Aware Formatting (Requirement 8.4)
# =============================================================================

class LocaleFormatter:
    """
    Locale-aware formatter for dates, numbers, and metrics.
    
    Supports formatting according to user's locale preferences.
    """
    
    LOCALE_SETTINGS = {
        'zh': {
            'date_format': '%Y年%m月%d日',
            'datetime_format': '%Y年%m月%d日 %H:%M:%S',
            'time_format': '%H:%M:%S',
            'decimal_separator': '.',
            'thousands_separator': ',',
            'percent_format': '{value:.1f}%',
            'currency_symbol': '¥',
            'currency_format': '¥{value:,.2f}',
        },
        'en': {
            'date_format': '%Y-%m-%d',
            'datetime_format': '%Y-%m-%d %H:%M:%S',
            'time_format': '%H:%M:%S',
            'decimal_separator': '.',
            'thousands_separator': ',',
            'percent_format': '{value:.1f}%',
            'currency_symbol': '$',
            'currency_format': '${value:,.2f}',
        },
    }
    
    def __init__(self, language: Optional[str] = None):
        """
        Initialize formatter with language.
        
        Args:
            language: Language code (optional, uses current language if not specified)
        """
        self.language = language or get_current_language()
        if self.language not in SUPPORTED_LANGUAGES:
            self.language = DEFAULT_LANGUAGE
        self.settings = self.LOCALE_SETTINGS.get(self.language, self.LOCALE_SETTINGS['en'])

    
    def format_date(self, dt: datetime) -> str:
        """Format date according to locale."""
        return dt.strftime(self.settings['date_format'])
    
    def format_datetime(self, dt: datetime) -> str:
        """Format datetime according to locale."""
        return dt.strftime(self.settings['datetime_format'])
    
    def format_time(self, dt: datetime) -> str:
        """Format time according to locale."""
        return dt.strftime(self.settings['time_format'])
    
    def format_number(self, value: float, decimals: int = 2) -> str:
        """Format number with locale-specific separators."""
        formatted = f"{value:,.{decimals}f}"
        return formatted
    
    def format_percent(self, value: float) -> str:
        """Format percentage according to locale."""
        return self.settings['percent_format'].format(value=value * 100)
    
    def format_currency(self, value: float) -> str:
        """Format currency according to locale."""
        return self.settings['currency_format'].format(value=value)
    
    def format_duration(self, seconds: float) -> str:
        """
        Format duration in human-readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 60:
            if self.language == 'zh':
                return f"{seconds:.1f} 秒"
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            if self.language == 'zh':
                return f"{minutes:.1f} 分钟"
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            if self.language == 'zh':
                return f"{hours:.1f} 小时"
            return f"{hours:.1f}h"
    
    def format_file_size(self, bytes_size: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            bytes_size: Size in bytes
            
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} PB"


def get_formatter(language: Optional[str] = None) -> LocaleFormatter:
    """
    Get a locale formatter for the specified language.
    
    Args:
        language: Language code (optional)
        
    Returns:
        LocaleFormatter instance
    """
    return LocaleFormatter(language)


# =============================================================================
# Multilingual Guidelines Support (Requirement 8.3)
# =============================================================================

class MultilingualGuidelines:
    """
    Support for multilingual annotation guidelines.
    
    Stores and retrieves annotation guidelines in multiple languages.
    """
    
    def __init__(self):
        """Initialize guidelines storage."""
        self._guidelines: Dict[str, Dict[str, str]] = {}
        self._examples: Dict[str, Dict[str, list]] = {}
    
    def set_guideline(
        self,
        project_id: str,
        language: str,
        content: str
    ) -> None:
        """
        Set annotation guideline for a project in a specific language.
        
        Args:
            project_id: Project identifier
            language: Language code
            content: Guideline content
        """
        if project_id not in self._guidelines:
            self._guidelines[project_id] = {}
        self._guidelines[project_id][language] = content
    
    def get_guideline(
        self,
        project_id: str,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Get annotation guideline for a project.
        
        Args:
            project_id: Project identifier
            language: Language code (optional, uses current language)
            
        Returns:
            Guideline content or None if not found
        """
        lang = language or get_current_language()
        project_guidelines = self._guidelines.get(project_id, {})
        
        # Try requested language first
        if lang in project_guidelines:
            return project_guidelines[lang]
        
        # Fallback to English
        if 'en' in project_guidelines:
            return project_guidelines['en']
        
        # Return any available guideline
        if project_guidelines:
            return next(iter(project_guidelines.values()))
        
        return None
    
    def set_examples(
        self,
        project_id: str,
        language: str,
        examples: list
    ) -> None:
        """
        Set language-specific examples for a project.
        
        Args:
            project_id: Project identifier
            language: Language code
            examples: List of example annotations
        """
        if project_id not in self._examples:
            self._examples[project_id] = {}
        self._examples[project_id][language] = examples
    
    def get_examples(
        self,
        project_id: str,
        language: Optional[str] = None
    ) -> list:
        """
        Get language-specific examples for a project.
        
        Args:
            project_id: Project identifier
            language: Language code (optional)
            
        Returns:
            List of examples or empty list
        """
        lang = language or get_current_language()
        project_examples = self._examples.get(project_id, {})
        
        if lang in project_examples:
            return project_examples[lang]
        
        if 'en' in project_examples:
            return project_examples['en']
        
        return []
    
    def get_available_languages(self, project_id: str) -> list:
        """
        Get list of languages with available guidelines.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of language codes
        """
        return list(self._guidelines.get(project_id, {}).keys())


# Global guidelines instance
_guidelines = MultilingualGuidelines()


def get_guidelines_manager() -> MultilingualGuidelines:
    """Get the global guidelines manager instance."""
    return _guidelines


# =============================================================================
# I18n Hot-Reload Support (Requirement 8.5)
# =============================================================================

import asyncio
import json
import os
from pathlib import Path


class I18nHotReloader:
    """
    Hot-reload support for i18n translations.
    
    Allows loading new translations without code changes.
    """
    
    def __init__(self, translations_dir: Optional[str] = None):
        """
        Initialize hot reloader.
        
        Args:
            translations_dir: Directory containing translation JSON files
        """
        self.translations_dir = translations_dir or os.path.join(
            os.path.dirname(__file__), 'translations'
        )
        self._custom_translations: Dict[str, Dict[str, str]] = {}
        self._lock = asyncio.Lock()
        self._last_reload: Optional[datetime] = None
    
    async def load_translations(self, language: str) -> Dict[str, str]:
        """
        Load translations for a language from file.
        
        Args:
            language: Language code
            
        Returns:
            Dictionary of translations
        """
        async with self._lock:
            file_path = Path(self.translations_dir) / f"ai_annotation_{language}.json"
            
            if not file_path.exists():
                return {}
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                self._custom_translations[language] = translations
                self._last_reload = datetime.now()
                return translations
            except (json.JSONDecodeError, IOError) as e:
                # Log error but don't fail
                return {}
    
    async def reload_all(self) -> Dict[str, int]:
        """
        Reload translations for all supported languages.
        
        Returns:
            Dictionary with count of loaded translations per language
        """
        results = {}
        for lang in SUPPORTED_LANGUAGES:
            translations = await self.load_translations(lang)
            results[lang] = len(translations)
        return results
    
    def get_custom_translation(
        self,
        key: str,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Get custom translation (loaded from file).
        
        Args:
            key: Translation key
            language: Language code
            
        Returns:
            Translation or None if not found
        """
        lang = language or get_current_language()
        return self._custom_translations.get(lang, {}).get(key)
    
    async def add_translation(
        self,
        language: str,
        key: str,
        value: str,
        persist: bool = True
    ) -> None:
        """
        Add a new translation dynamically.
        
        Args:
            language: Language code
            key: Translation key
            value: Translation value
            persist: Whether to save to file
        """
        async with self._lock:
            if language not in self._custom_translations:
                self._custom_translations[language] = {}
            
            self._custom_translations[language][key] = value
            
            if persist:
                await self._save_translations(language)
    
    async def _save_translations(self, language: str) -> None:
        """Save translations to file."""
        file_path = Path(self.translations_dir) / f"ai_annotation_{language}.json"
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    self._custom_translations.get(language, {}),
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except IOError:
            pass  # Log error but don't fail
    
    def get_last_reload_time(self) -> Optional[datetime]:
        """Get the timestamp of the last reload."""
        return self._last_reload


# Global hot reloader instance
_hot_reloader: Optional[I18nHotReloader] = None


def get_hot_reloader() -> I18nHotReloader:
    """Get the global hot reloader instance."""
    global _hot_reloader
    if _hot_reloader is None:
        _hot_reloader = I18nHotReloader()
    return _hot_reloader


async def reload_translations() -> Dict[str, int]:
    """
    Reload all translations from files.
    
    Returns:
        Dictionary with count of loaded translations per language
    """
    return await get_hot_reloader().reload_all()


# =============================================================================
# Enhanced Translation Function with Hot-Reload Support
# =============================================================================

def get_translation_with_fallback(
    key: str,
    language: Optional[str] = None,
    **kwargs
) -> str:
    """
    Get translation with hot-reload and fallback support.
    
    Checks custom translations first, then built-in translations.
    
    Args:
        key: Translation key
        language: Language code (optional)
        **kwargs: Parameters for string formatting
        
    Returns:
        Translated string
    """
    lang = language or get_current_language()
    
    # Check custom translations first (hot-reloaded)
    hot_reloader = get_hot_reloader()
    custom_text = hot_reloader.get_custom_translation(key, lang)
    
    if custom_text is not None:
        if kwargs:
            try:
                return custom_text.format(**kwargs)
            except KeyError:
                return custom_text
        return custom_text
    
    # Fall back to built-in translations
    return get_ai_translation(key, lang, **kwargs)


# =============================================================================
# Quality Report Formatting (Requirement 8.4)
# =============================================================================

def format_quality_report(
    metrics: Dict[str, float],
    language: Optional[str] = None
) -> Dict[str, str]:
    """
    Format quality metrics for display according to locale.
    
    Args:
        metrics: Dictionary of metric name to value
        language: Language code (optional)
        
    Returns:
        Dictionary of metric name to formatted string
    """
    formatter = get_formatter(language)
    lang = language or get_current_language()
    
    formatted = {}
    for metric_name, value in metrics.items():
        # Get translated metric label
        label_key = f'ai.metric.{metric_name}'
        label = get_ai_translation(label_key, lang)
        if label == label_key:
            label = metric_name.replace('_', ' ').title()
        
        # Format value based on metric type
        if metric_name in ['accuracy', 'recall', 'precision', 'consistency', 
                          'completeness', 'f1_score', 'success_rate', 
                          'error_rate', 'rejection_rate', 'acceptance_rate',
                          'coverage', 'confidence_avg']:
            formatted_value = formatter.format_percent(value)
        elif metric_name in ['latency', 'processing_time']:
            formatted_value = formatter.format_duration(value)
        elif metric_name in ['throughput', 'queue_length']:
            formatted_value = formatter.format_number(value, 0)
        else:
            formatted_value = formatter.format_number(value, 2)
        
        formatted[label] = formatted_value
    
    return formatted


def format_annotation_summary(
    total: int,
    completed: int,
    flagged: int,
    avg_confidence: float,
    processing_time: float,
    language: Optional[str] = None
) -> Dict[str, str]:
    """
    Format annotation batch summary for display.
    
    Args:
        total: Total items
        completed: Completed items
        flagged: Items flagged for review
        avg_confidence: Average confidence score
        processing_time: Processing time in seconds
        language: Language code (optional)
        
    Returns:
        Dictionary of formatted summary fields
    """
    formatter = get_formatter(language)
    lang = language or get_current_language()
    
    return {
        get_ai_translation('ai.ui.total', lang): formatter.format_number(total, 0),
        get_ai_translation('ai.ui.completed', lang) if has_translation('ai.ui.completed', lang) 
            else 'Completed': formatter.format_number(completed, 0),
        get_ai_translation('ai.preannotation.flagged_for_review', lang): formatter.format_number(flagged, 0),
        get_ai_translation('ai.metric.confidence_avg', lang): formatter.format_percent(avg_confidence),
        get_ai_translation('ai.metric.processing_time', lang): formatter.format_duration(processing_time),
    }


# =============================================================================
# Export all public functions and classes
# =============================================================================

__all__ = [
    # Translation functions
    'get_ai_translation',
    't',
    'get_all_translations',
    'has_translation',
    'get_missing_translations',
    'get_translation_with_fallback',
    
    # Language management
    'get_current_language',
    'set_language',
    'SUPPORTED_LANGUAGES',
    'DEFAULT_LANGUAGE',
    
    # Locale formatting
    'LocaleFormatter',
    'get_formatter',
    'format_quality_report',
    'format_annotation_summary',
    
    # Guidelines
    'MultilingualGuidelines',
    'get_guidelines_manager',
    
    # Hot reload
    'I18nHotReloader',
    'get_hot_reloader',
    'reload_translations',
    
    # Translations dictionary
    'AI_ANNOTATION_TRANSLATIONS',
]
