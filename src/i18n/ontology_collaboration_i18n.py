"""
本体专家协作国际化集成模块

扩展现有 i18n 系统，添加本体协作相关的翻译键。

Validates: Task 27.3 - Integrate with i18n system
"""

from typing import Dict, Any, Optional
from src.i18n.translations import TRANSLATIONS, get_translation, set_language

# 本体协作翻译键
ONTOLOGY_COLLABORATION_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'zh': {
        # ============================================================================
        # 专家管理 (Expert Management)
        # ============================================================================
        'ontology.expert.title': '专家管理',
        'ontology.expert.list': '专家列表',
        'ontology.expert.profile': '专家档案',
        'ontology.expert.create': '创建专家',
        'ontology.expert.edit': '编辑专家',
        'ontology.expert.delete': '删除专家',
        'ontology.expert.name': '姓名',
        'ontology.expert.email': '邮箱',
        'ontology.expert.expertise_areas': '专业领域',
        'ontology.expert.certifications': '资质认证',
        'ontology.expert.languages': '语言能力',
        'ontology.expert.department': '部门',
        'ontology.expert.title_position': '职位',
        'ontology.expert.bio': '简介',
        'ontology.expert.status': '状态',
        'ontology.expert.availability': '可用性',
        'ontology.expert.contribution_score': '贡献分数',
        
        # 专家状态
        'ontology.expert.status.active': '活跃',
        'ontology.expert.status.inactive': '非活跃',
        'ontology.expert.status.pending': '待审核',
        'ontology.expert.status.suspended': '已暂停',
        
        # 可用性
        'ontology.expert.availability.high': '高',
        'ontology.expert.availability.medium': '中',
        'ontology.expert.availability.low': '低',
        'ontology.expert.availability.unavailable': '不可用',

        # 专业领域
        'ontology.expert.area.finance': '金融',
        'ontology.expert.area.healthcare': '医疗',
        'ontology.expert.area.manufacturing': '制造',
        'ontology.expert.area.government': '政务',
        'ontology.expert.area.legal': '法律',
        'ontology.expert.area.education': '教育',
        
        # 专家推荐
        'ontology.expert.recommend': '专家推荐',
        'ontology.expert.recommend.title': '推荐专家',
        'ontology.expert.recommend.match_score': '匹配度',
        'ontology.expert.recommend.select': '选择专家',
        'ontology.expert.recommend.no_results': '暂无推荐专家',
        
        # 专家指标
        'ontology.expert.metrics': '专家指标',
        'ontology.expert.metrics.contributions': '贡献数',
        'ontology.expert.metrics.accepted': '已接受',
        'ontology.expert.metrics.rejected': '已拒绝',
        'ontology.expert.metrics.quality_score': '质量分数',
        'ontology.expert.metrics.acceptance_rate': '接受率',
        
        # ============================================================================
        # 模板管理 (Template Management)
        # ============================================================================
        'ontology.template.title': '模板管理',
        'ontology.template.browser': '模板浏览',
        'ontology.template.create': '创建模板',
        'ontology.template.edit': '编辑模板',
        'ontology.template.delete': '删除模板',
        'ontology.template.instantiate': '实例化模板',
        'ontology.template.customize': '自定义模板',
        'ontology.template.export': '导出模板',
        'ontology.template.import': '导入模板',
        'ontology.template.name': '模板名称',
        'ontology.template.industry': '行业',
        'ontology.template.version': '版本',
        'ontology.template.description': '描述',
        'ontology.template.usage_count': '使用次数',
        'ontology.template.lineage': '模板血缘',
        
        # 模板实例化
        'ontology.template.wizard.title': '模板实例化向导',
        'ontology.template.wizard.step1': '选择模板',
        'ontology.template.wizard.step2': '配置参数',
        'ontology.template.wizard.step3': '预览',
        'ontology.template.wizard.step4': '确认',
        'ontology.template.wizard.project_id': '项目ID',
        'ontology.template.wizard.customizations': '自定义配置',
        
        # 模板自定义
        'ontology.template.customize.add_entity': '添加实体类型',
        'ontology.template.customize.remove_entity': '移除实体类型',
        'ontology.template.customize.add_relation': '添加关系类型',
        'ontology.template.customize.remove_relation': '移除关系类型',
        'ontology.template.customize.preserve_core': '保留核心结构',

        # ============================================================================
        # 协作编辑 (Collaborative Editing)
        # ============================================================================
        'ontology.collaboration.title': '协作编辑',
        'ontology.collaboration.session': '协作会话',
        'ontology.collaboration.join': '加入会话',
        'ontology.collaboration.leave': '离开会话',
        'ontology.collaboration.participants': '参与者',
        'ontology.collaboration.lock': '锁定元素',
        'ontology.collaboration.unlock': '解锁元素',
        'ontology.collaboration.locked_by': '已被 {user} 锁定',
        'ontology.collaboration.lock_expired': '锁定已过期',
        
        # 冲突解决
        'ontology.collaboration.conflict': '编辑冲突',
        'ontology.collaboration.conflict.detected': '检测到编辑冲突',
        'ontology.collaboration.conflict.accept_theirs': '接受对方版本',
        'ontology.collaboration.conflict.accept_mine': '保留我的版本',
        'ontology.collaboration.conflict.manual_merge': '手动合并',
        'ontology.collaboration.conflict.resolved': '冲突已解决',
        
        # 版本历史
        'ontology.collaboration.version': '版本历史',
        'ontology.collaboration.version.current': '当前版本',
        'ontology.collaboration.version.restore': '恢复版本',
        'ontology.collaboration.version.compare': '版本对比',
        'ontology.collaboration.version.by': '修改者',
        'ontology.collaboration.version.at': '修改时间',
        
        # 变更对比
        'ontology.collaboration.change.before': '修改前',
        'ontology.collaboration.change.after': '修改后',
        'ontology.collaboration.change.added': '新增',
        'ontology.collaboration.change.removed': '删除',
        'ontology.collaboration.change.modified': '修改',
        
        # ============================================================================
        # 审批工作流 (Approval Workflow)
        # ============================================================================
        'ontology.approval.title': '审批工作流',
        'ontology.approval.chain': '审批链',
        'ontology.approval.chain.create': '创建审批链',
        'ontology.approval.chain.edit': '编辑审批链',
        'ontology.approval.chain.delete': '删除审批链',
        'ontology.approval.chain.name': '审批链名称',
        'ontology.approval.chain.area': '本体领域',
        'ontology.approval.chain.levels': '审批级别',
        'ontology.approval.chain.type': '审批类型',
        'ontology.approval.chain.type.parallel': '并行审批',
        'ontology.approval.chain.type.sequential': '顺序审批',

        # 审批级别
        'ontology.approval.level': '审批级别',
        'ontology.approval.level.add': '添加级别',
        'ontology.approval.level.remove': '移除级别',
        'ontology.approval.level.approvers': '审批人',
        'ontology.approval.level.deadline': '截止时间',
        'ontology.approval.level.min_approvals': '最少审批数',
        
        # 变更请求
        'ontology.approval.request': '变更请求',
        'ontology.approval.request.create': '创建变更请求',
        'ontology.approval.request.submit': '提交审批',
        'ontology.approval.request.approve': '批准',
        'ontology.approval.request.reject': '拒绝',
        'ontology.approval.request.request_changes': '请求修改',
        'ontology.approval.request.status': '状态',
        'ontology.approval.request.description': '变更描述',
        'ontology.approval.request.impact': '影响分析',
        
        # 变更请求状态
        'ontology.approval.status.draft': '草稿',
        'ontology.approval.status.submitted': '已提交',
        'ontology.approval.status.in_review': '审核中',
        'ontology.approval.status.approved': '已批准',
        'ontology.approval.status.rejected': '已拒绝',
        'ontology.approval.status.changes_requested': '需要修改',
        
        # 待审批
        'ontology.approval.pending': '待审批',
        'ontology.approval.pending.title': '待审批列表',
        'ontology.approval.pending.urgent': '紧急',
        'ontology.approval.pending.deadline': '截止时间',
        'ontology.approval.pending.requester': '申请人',
        
        # 审批追踪
        'ontology.approval.tracker': '审批追踪',
        'ontology.approval.tracker.progress': '审批进度',
        'ontology.approval.tracker.completed': '已完成',
        'ontology.approval.tracker.pending': '待处理',
        'ontology.approval.tracker.escalated': '已升级',
        
        # ============================================================================
        # 验证规则 (Validation Rules)
        # ============================================================================
        'ontology.validation.title': '验证规则',
        'ontology.validation.rule': '验证规则',
        'ontology.validation.rule.create': '创建规则',
        'ontology.validation.rule.edit': '编辑规则',
        'ontology.validation.rule.delete': '删除规则',
        'ontology.validation.rule.name': '规则名称',
        'ontology.validation.rule.type': '规则类型',
        'ontology.validation.rule.target': '目标实体',
        'ontology.validation.rule.field': '目标字段',
        'ontology.validation.rule.logic': '验证逻辑',
        'ontology.validation.rule.error_message': '错误消息',
        'ontology.validation.rule.region': '适用地区',
        'ontology.validation.rule.industry': '适用行业',

        # 中国业务验证
        'ontology.validation.chinese': '中国业务验证',
        'ontology.validation.chinese.uscc': '统一社会信用代码',
        'ontology.validation.chinese.org_code': '组织机构代码',
        'ontology.validation.chinese.business_license': '营业执照号',
        'ontology.validation.chinese.contract': '合同验证',
        'ontology.validation.chinese.seal': '印章验证',
        'ontology.validation.chinese.test': '测试验证',
        'ontology.validation.chinese.valid': '验证通过',
        'ontology.validation.chinese.invalid': '验证失败',
        
        # 验证结果
        'ontology.validation.result': '验证结果',
        'ontology.validation.result.valid': '有效',
        'ontology.validation.result.invalid': '无效',
        'ontology.validation.result.errors': '错误列表',
        'ontology.validation.result.suggestion': '修改建议',
        
        # ============================================================================
        # 合规模板 (Compliance Templates)
        # ============================================================================
        'ontology.compliance.title': '合规模板',
        'ontology.compliance.template': '合规模板',
        'ontology.compliance.template.select': '选择模板',
        'ontology.compliance.template.apply': '应用模板',
        'ontology.compliance.template.dsl': '数据安全法',
        'ontology.compliance.template.pipl': '个人信息保护法',
        'ontology.compliance.template.csl': '网络安全法',
        
        # 合规报告
        'ontology.compliance.report': '合规报告',
        'ontology.compliance.report.generate': '生成报告',
        'ontology.compliance.report.export': '导出报告',
        'ontology.compliance.report.score': '合规分数',
        'ontology.compliance.report.issues': '合规问题',
        'ontology.compliance.report.recommendations': '改进建议',
        'ontology.compliance.report.citations': '法规引用',
        
        # 数据分类
        'ontology.compliance.classification': '数据分类',
        'ontology.compliance.classification.general': '一般数据',
        'ontology.compliance.classification.important': '重要数据',
        'ontology.compliance.classification.core': '核心数据',
        
        # ============================================================================
        # 影响分析 (Impact Analysis)
        # ============================================================================
        'ontology.impact.title': '影响分析',
        'ontology.impact.analyze': '分析影响',
        'ontology.impact.report': '影响报告',
        'ontology.impact.affected_entities': '受影响实体',
        'ontology.impact.affected_relations': '受影响关系',
        'ontology.impact.affected_projects': '受影响项目',
        'ontology.impact.migration_complexity': '迁移复杂度',
        'ontology.impact.migration_hours': '预估工时',
        'ontology.impact.breaking_changes': '破坏性变更',
        'ontology.impact.recommendations': '建议',
        'ontology.impact.high_impact': '高影响变更',
        'ontology.impact.requires_approval': '需要高级审批',

        # 复杂度等级
        'ontology.impact.complexity.low': '低',
        'ontology.impact.complexity.medium': '中',
        'ontology.impact.complexity.high': '高',
        
        # ============================================================================
        # 国际化支持 (I18n Support)
        # ============================================================================
        'ontology.i18n.title': '多语言支持',
        'ontology.i18n.translation': '翻译管理',
        'ontology.i18n.add': '添加翻译',
        'ontology.i18n.edit': '编辑翻译',
        'ontology.i18n.delete': '删除翻译',
        'ontology.i18n.language': '语言',
        'ontology.i18n.name': '名称',
        'ontology.i18n.description': '描述',
        'ontology.i18n.help_text': '帮助文本',
        'ontology.i18n.missing': '缺少翻译',
        'ontology.i18n.coverage': '翻译覆盖率',
        'ontology.i18n.export': '导出翻译',
        'ontology.i18n.import': '导入翻译',
        
        # 语言选择
        'ontology.i18n.lang.zh_cn': '简体中文',
        'ontology.i18n.lang.en_us': '英文',
        'ontology.i18n.lang.zh_tw': '繁体中文',
        'ontology.i18n.lang.ja_jp': '日文',
        'ontology.i18n.lang.ko_kr': '韩文',
        
        # ============================================================================
        # 帮助和引导 (Help and Onboarding)
        # ============================================================================
        'ontology.help.title': '帮助中心',
        'ontology.help.search': '搜索帮助',
        'ontology.help.documentation': '文档',
        'ontology.help.tutorials': '教程',
        'ontology.help.best_practices': '最佳实践',
        'ontology.help.faq': '常见问题',
        
        # 新手引导
        'ontology.onboarding.title': '新手引导',
        'ontology.onboarding.welcome': '欢迎使用本体协作系统',
        'ontology.onboarding.checklist': '入门清单',
        'ontology.onboarding.progress': '完成进度',
        'ontology.onboarding.step.profile': '完善个人资料',
        'ontology.onboarding.step.expertise': '设置专业领域',
        'ontology.onboarding.step.tutorial': '完成基础教程',
        'ontology.onboarding.step.first_contribution': '提交首次贡献',
        'ontology.onboarding.step.mentor': '联系导师',
        
        # ============================================================================
        # 审计和回滚 (Audit and Rollback)
        # ============================================================================
        'ontology.audit.title': '审计日志',
        'ontology.audit.log': '操作日志',
        'ontology.audit.filter': '筛选日志',
        'ontology.audit.export': '导出日志',
        'ontology.audit.user': '操作用户',
        'ontology.audit.action': '操作类型',
        'ontology.audit.timestamp': '操作时间',
        'ontology.audit.details': '操作详情',
        
        # 回滚
        'ontology.rollback.title': '版本回滚',
        'ontology.rollback.select': '选择版本',
        'ontology.rollback.confirm': '确认回滚',
        'ontology.rollback.affected_users': '受影响用户',
        'ontology.rollback.success': '回滚成功',
        'ontology.rollback.failed': '回滚失败',

        # ============================================================================
        # 最佳实践 (Best Practices)
        # ============================================================================
        'ontology.best_practice.title': '最佳实践',
        'ontology.best_practice.library': '实践库',
        'ontology.best_practice.search': '搜索实践',
        'ontology.best_practice.apply': '应用实践',
        'ontology.best_practice.contribute': '贡献实践',
        'ontology.best_practice.review': '审核实践',
        'ontology.best_practice.popular': '热门实践',
        'ontology.best_practice.steps': '实施步骤',
        'ontology.best_practice.benefits': '预期收益',
        'ontology.best_practice.examples': '示例',
        
        # ============================================================================
        # 知识贡献 (Knowledge Contribution)
        # ============================================================================
        'ontology.contribution.title': '知识贡献',
        'ontology.contribution.comment': '评论',
        'ontology.contribution.suggestion': '建议',
        'ontology.contribution.document': '文档',
        'ontology.contribution.entity': '实体建议',
        'ontology.contribution.relation': '关系建议',
        'ontology.contribution.submit': '提交贡献',
        'ontology.contribution.review': '审核贡献',
        'ontology.contribution.accept': '接受',
        'ontology.contribution.reject': '拒绝',
        
        # ============================================================================
        # 通用操作 (Common Actions)
        # ============================================================================
        'ontology.action.save': '保存',
        'ontology.action.cancel': '取消',
        'ontology.action.confirm': '确认',
        'ontology.action.delete': '删除',
        'ontology.action.edit': '编辑',
        'ontology.action.view': '查看',
        'ontology.action.search': '搜索',
        'ontology.action.filter': '筛选',
        'ontology.action.refresh': '刷新',
        'ontology.action.export': '导出',
        'ontology.action.import': '导入',
        'ontology.action.back': '返回',
        'ontology.action.next': '下一步',
        'ontology.action.previous': '上一步',
        'ontology.action.finish': '完成',
        
        # ============================================================================
        # 成功消息 (Success Messages)
        # ============================================================================
        'ontology.success.created': '创建成功',
        'ontology.success.updated': '更新成功',
        'ontology.success.deleted': '删除成功',
        'ontology.success.saved': '保存成功',
        'ontology.success.submitted': '提交成功',
        'ontology.success.approved': '审批通过',
        'ontology.success.rejected': '已拒绝',
        'ontology.success.exported': '导出成功',
        'ontology.success.imported': '导入成功',
        
        # ============================================================================
        # 错误消息 (Error Messages)
        # ============================================================================
        'ontology.error.not_found': '未找到',
        'ontology.error.already_exists': '已存在',
        'ontology.error.invalid_input': '输入无效',
        'ontology.error.permission_denied': '权限不足',
        'ontology.error.operation_failed': '操作失败',
        'ontology.error.network_error': '网络错误',
        'ontology.error.server_error': '服务器错误',
        'ontology.error.validation_failed': '验证失败',
        'ontology.error.conflict': '冲突',
        'ontology.error.locked': '资源已锁定',
    },

    'en': {
        # Expert Management
        'ontology.expert.title': 'Expert Management',
        'ontology.expert.list': 'Expert List',
        'ontology.expert.profile': 'Expert Profile',
        'ontology.expert.create': 'Create Expert',
        'ontology.expert.edit': 'Edit Expert',
        'ontology.expert.delete': 'Delete Expert',
        'ontology.expert.name': 'Name',
        'ontology.expert.email': 'Email',
        'ontology.expert.expertise_areas': 'Expertise Areas',
        'ontology.expert.certifications': 'Certifications',
        'ontology.expert.languages': 'Languages',
        'ontology.expert.department': 'Department',
        'ontology.expert.title_position': 'Title',
        'ontology.expert.bio': 'Bio',
        'ontology.expert.status': 'Status',
        'ontology.expert.availability': 'Availability',
        'ontology.expert.contribution_score': 'Contribution Score',
        
        # Expert Status
        'ontology.expert.status.active': 'Active',
        'ontology.expert.status.inactive': 'Inactive',
        'ontology.expert.status.pending': 'Pending',
        'ontology.expert.status.suspended': 'Suspended',
        
        # Availability
        'ontology.expert.availability.high': 'High',
        'ontology.expert.availability.medium': 'Medium',
        'ontology.expert.availability.low': 'Low',
        'ontology.expert.availability.unavailable': 'Unavailable',
        
        # Expertise Areas
        'ontology.expert.area.finance': 'Finance',
        'ontology.expert.area.healthcare': 'Healthcare',
        'ontology.expert.area.manufacturing': 'Manufacturing',
        'ontology.expert.area.government': 'Government',
        'ontology.expert.area.legal': 'Legal',
        'ontology.expert.area.education': 'Education',
        
        # Expert Recommendation
        'ontology.expert.recommend': 'Expert Recommendation',
        'ontology.expert.recommend.title': 'Recommended Experts',
        'ontology.expert.recommend.match_score': 'Match Score',
        'ontology.expert.recommend.select': 'Select Expert',
        'ontology.expert.recommend.no_results': 'No recommended experts',
        
        # Expert Metrics
        'ontology.expert.metrics': 'Expert Metrics',
        'ontology.expert.metrics.contributions': 'Contributions',
        'ontology.expert.metrics.accepted': 'Accepted',
        'ontology.expert.metrics.rejected': 'Rejected',
        'ontology.expert.metrics.quality_score': 'Quality Score',
        'ontology.expert.metrics.acceptance_rate': 'Acceptance Rate',

        # Template Management
        'ontology.template.title': 'Template Management',
        'ontology.template.browser': 'Template Browser',
        'ontology.template.create': 'Create Template',
        'ontology.template.edit': 'Edit Template',
        'ontology.template.delete': 'Delete Template',
        'ontology.template.instantiate': 'Instantiate Template',
        'ontology.template.customize': 'Customize Template',
        'ontology.template.export': 'Export Template',
        'ontology.template.import': 'Import Template',
        'ontology.template.name': 'Template Name',
        'ontology.template.industry': 'Industry',
        'ontology.template.version': 'Version',
        'ontology.template.description': 'Description',
        'ontology.template.usage_count': 'Usage Count',
        'ontology.template.lineage': 'Template Lineage',
        
        # Collaborative Editing
        'ontology.collaboration.title': 'Collaborative Editing',
        'ontology.collaboration.session': 'Collaboration Session',
        'ontology.collaboration.join': 'Join Session',
        'ontology.collaboration.leave': 'Leave Session',
        'ontology.collaboration.participants': 'Participants',
        'ontology.collaboration.lock': 'Lock Element',
        'ontology.collaboration.unlock': 'Unlock Element',
        'ontology.collaboration.locked_by': 'Locked by {user}',
        'ontology.collaboration.lock_expired': 'Lock Expired',
        
        # Conflict Resolution
        'ontology.collaboration.conflict': 'Edit Conflict',
        'ontology.collaboration.conflict.detected': 'Edit conflict detected',
        'ontology.collaboration.conflict.accept_theirs': 'Accept Their Version',
        'ontology.collaboration.conflict.accept_mine': 'Keep My Version',
        'ontology.collaboration.conflict.manual_merge': 'Manual Merge',
        'ontology.collaboration.conflict.resolved': 'Conflict Resolved',
        
        # Version History
        'ontology.collaboration.version': 'Version History',
        'ontology.collaboration.version.current': 'Current Version',
        'ontology.collaboration.version.restore': 'Restore Version',
        'ontology.collaboration.version.compare': 'Compare Versions',
        'ontology.collaboration.version.by': 'Modified By',
        'ontology.collaboration.version.at': 'Modified At',
        
        # Approval Workflow
        'ontology.approval.title': 'Approval Workflow',
        'ontology.approval.chain': 'Approval Chain',
        'ontology.approval.chain.create': 'Create Approval Chain',
        'ontology.approval.chain.edit': 'Edit Approval Chain',
        'ontology.approval.chain.delete': 'Delete Approval Chain',
        'ontology.approval.chain.name': 'Chain Name',
        'ontology.approval.chain.area': 'Ontology Area',
        'ontology.approval.chain.levels': 'Approval Levels',
        'ontology.approval.chain.type': 'Approval Type',
        'ontology.approval.chain.type.parallel': 'Parallel Approval',
        'ontology.approval.chain.type.sequential': 'Sequential Approval',

        # Approval Status
        'ontology.approval.status.draft': 'Draft',
        'ontology.approval.status.submitted': 'Submitted',
        'ontology.approval.status.in_review': 'In Review',
        'ontology.approval.status.approved': 'Approved',
        'ontology.approval.status.rejected': 'Rejected',
        'ontology.approval.status.changes_requested': 'Changes Requested',
        
        # Validation Rules
        'ontology.validation.title': 'Validation Rules',
        'ontology.validation.rule': 'Validation Rule',
        'ontology.validation.rule.create': 'Create Rule',
        'ontology.validation.rule.edit': 'Edit Rule',
        'ontology.validation.rule.delete': 'Delete Rule',
        'ontology.validation.rule.name': 'Rule Name',
        'ontology.validation.rule.type': 'Rule Type',
        'ontology.validation.rule.target': 'Target Entity',
        'ontology.validation.rule.field': 'Target Field',
        'ontology.validation.rule.logic': 'Validation Logic',
        'ontology.validation.rule.error_message': 'Error Message',
        'ontology.validation.rule.region': 'Region',
        'ontology.validation.rule.industry': 'Industry',
        
        # Chinese Business Validation
        'ontology.validation.chinese': 'Chinese Business Validation',
        'ontology.validation.chinese.uscc': 'Unified Social Credit Code',
        'ontology.validation.chinese.org_code': 'Organization Code',
        'ontology.validation.chinese.business_license': 'Business License Number',
        'ontology.validation.chinese.contract': 'Contract Validation',
        'ontology.validation.chinese.seal': 'Seal Validation',
        'ontology.validation.chinese.test': 'Test Validation',
        'ontology.validation.chinese.valid': 'Valid',
        'ontology.validation.chinese.invalid': 'Invalid',
        
        # Compliance Templates
        'ontology.compliance.title': 'Compliance Templates',
        'ontology.compliance.template': 'Compliance Template',
        'ontology.compliance.template.select': 'Select Template',
        'ontology.compliance.template.apply': 'Apply Template',
        'ontology.compliance.template.dsl': 'Data Security Law',
        'ontology.compliance.template.pipl': 'Personal Information Protection Law',
        'ontology.compliance.template.csl': 'Cybersecurity Law',
        
        # Impact Analysis
        'ontology.impact.title': 'Impact Analysis',
        'ontology.impact.analyze': 'Analyze Impact',
        'ontology.impact.report': 'Impact Report',
        'ontology.impact.affected_entities': 'Affected Entities',
        'ontology.impact.affected_relations': 'Affected Relations',
        'ontology.impact.affected_projects': 'Affected Projects',
        'ontology.impact.migration_complexity': 'Migration Complexity',
        'ontology.impact.migration_hours': 'Estimated Hours',
        'ontology.impact.breaking_changes': 'Breaking Changes',
        'ontology.impact.recommendations': 'Recommendations',
        'ontology.impact.high_impact': 'High Impact Change',
        'ontology.impact.requires_approval': 'Requires Senior Approval',
        'ontology.impact.complexity.low': 'Low',
        'ontology.impact.complexity.medium': 'Medium',
        'ontology.impact.complexity.high': 'High',

        # I18n Support
        'ontology.i18n.title': 'Multi-language Support',
        'ontology.i18n.translation': 'Translation Management',
        'ontology.i18n.add': 'Add Translation',
        'ontology.i18n.edit': 'Edit Translation',
        'ontology.i18n.delete': 'Delete Translation',
        'ontology.i18n.language': 'Language',
        'ontology.i18n.name': 'Name',
        'ontology.i18n.description': 'Description',
        'ontology.i18n.help_text': 'Help Text',
        'ontology.i18n.missing': 'Missing Translation',
        'ontology.i18n.coverage': 'Translation Coverage',
        'ontology.i18n.export': 'Export Translations',
        'ontology.i18n.import': 'Import Translations',
        
        # Languages
        'ontology.i18n.lang.zh_cn': 'Simplified Chinese',
        'ontology.i18n.lang.en_us': 'English',
        'ontology.i18n.lang.zh_tw': 'Traditional Chinese',
        'ontology.i18n.lang.ja_jp': 'Japanese',
        'ontology.i18n.lang.ko_kr': 'Korean',
        
        # Help and Onboarding
        'ontology.help.title': 'Help Center',
        'ontology.help.search': 'Search Help',
        'ontology.help.documentation': 'Documentation',
        'ontology.help.tutorials': 'Tutorials',
        'ontology.help.best_practices': 'Best Practices',
        'ontology.help.faq': 'FAQ',
        
        # Onboarding
        'ontology.onboarding.title': 'Getting Started',
        'ontology.onboarding.welcome': 'Welcome to Ontology Collaboration',
        'ontology.onboarding.checklist': 'Getting Started Checklist',
        'ontology.onboarding.progress': 'Progress',
        'ontology.onboarding.step.profile': 'Complete Your Profile',
        'ontology.onboarding.step.expertise': 'Set Expertise Areas',
        'ontology.onboarding.step.tutorial': 'Complete Basic Tutorial',
        'ontology.onboarding.step.first_contribution': 'Make First Contribution',
        'ontology.onboarding.step.mentor': 'Connect with Mentor',
        
        # Common Actions
        'ontology.action.save': 'Save',
        'ontology.action.cancel': 'Cancel',
        'ontology.action.confirm': 'Confirm',
        'ontology.action.delete': 'Delete',
        'ontology.action.edit': 'Edit',
        'ontology.action.view': 'View',
        'ontology.action.search': 'Search',
        'ontology.action.filter': 'Filter',
        'ontology.action.refresh': 'Refresh',
        'ontology.action.export': 'Export',
        'ontology.action.import': 'Import',
        'ontology.action.back': 'Back',
        'ontology.action.next': 'Next',
        'ontology.action.previous': 'Previous',
        'ontology.action.finish': 'Finish',
        
        # Success Messages
        'ontology.success.created': 'Created successfully',
        'ontology.success.updated': 'Updated successfully',
        'ontology.success.deleted': 'Deleted successfully',
        'ontology.success.saved': 'Saved successfully',
        'ontology.success.submitted': 'Submitted successfully',
        'ontology.success.approved': 'Approved',
        'ontology.success.rejected': 'Rejected',
        'ontology.success.exported': 'Exported successfully',
        'ontology.success.imported': 'Imported successfully',
        
        # Error Messages
        'ontology.error.not_found': 'Not found',
        'ontology.error.already_exists': 'Already exists',
        'ontology.error.invalid_input': 'Invalid input',
        'ontology.error.permission_denied': 'Permission denied',
        'ontology.error.operation_failed': 'Operation failed',
        'ontology.error.network_error': 'Network error',
        'ontology.error.server_error': 'Server error',
        'ontology.error.validation_failed': 'Validation failed',
        'ontology.error.conflict': 'Conflict',
        'ontology.error.locked': 'Resource locked',
    },
}


def register_ontology_collaboration_translations() -> None:
    """注册本体协作翻译键到全局翻译字典"""
    for lang, translations in ONTOLOGY_COLLABORATION_TRANSLATIONS.items():
        if lang in TRANSLATIONS:
            TRANSLATIONS[lang].update(translations)
        else:
            TRANSLATIONS[lang] = translations


def get_ontology_translation(key: str, lang: str = 'zh', **kwargs) -> str:
    """
    获取本体协作翻译
    
    Args:
        key: 翻译键
        lang: 语言代码
        **kwargs: 参数替换
        
    Returns:
        翻译后的文本
    """
    # 确保翻译已注册
    if 'ontology.expert.title' not in TRANSLATIONS.get('zh', {}):
        register_ontology_collaboration_translations()
    
    return get_translation(key, lang, **kwargs)


# 自动注册翻译
register_ontology_collaboration_translations()
