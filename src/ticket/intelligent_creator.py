"""
Intelligent ticket creation system for SuperInsight platform.

Provides:
- Automatic ticket creation from quality issues
- Intelligent priority assessment
- Ticket classification and tagging
- Template-based ticket creation
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.ticket.models import (
    TicketModel,
    TicketHistoryModel,
    TicketStatus,
    TicketPriority,
    TicketType,
    SLAConfig,
)
from src.models.quality_issue import QualityIssue, IssueSeverity
from src.models.task import Task

logger = logging.getLogger(__name__)


class TicketTemplate(str, Enum):
    """Predefined ticket templates."""
    QUALITY_ISSUE = "quality_issue"
    ANNOTATION_ERROR = "annotation_error"
    DATA_REPAIR = "data_repair"
    REVIEW_REQUEST = "review_request"
    TRAINING_FEEDBACK = "training_feedback"
    CUSTOMER_COMPLAINT = "customer_complaint"
    SYSTEM_ERROR = "system_error"


class PriorityAssessmentRule:
    """Rule for assessing ticket priority based on various factors."""
    
    def __init__(
        self,
        name: str,
        condition: callable,
        priority: TicketPriority,
        weight: float = 1.0
    ):
        self.name = name
        self.condition = condition
        self.priority = priority
        self.weight = weight


class TicketClassifier:
    """Classifier for automatic ticket categorization."""
    
    # Keywords for different ticket types
    TYPE_KEYWORDS = {
        TicketType.QUALITY_ISSUE: [
            "质量", "quality", "准确性", "accuracy", "一致性", "consistency",
            "完整性", "completeness", "标准", "standard"
        ],
        TicketType.ANNOTATION_ERROR: [
            "标注", "annotation", "错误", "error", "标记", "label",
            "分类", "classification", "识别", "recognition"
        ],
        TicketType.DATA_REPAIR: [
            "修复", "repair", "数据", "data", "损坏", "corrupt",
            "恢复", "recovery", "清理", "cleanup"
        ],
        TicketType.REVIEW_REQUEST: [
            "审核", "review", "检查", "check", "验证", "verify",
            "确认", "confirm", "评估", "assess"
        ],
        TicketType.TRAINING_FEEDBACK: [
            "培训", "training", "学习", "learning", "指导", "guidance",
            "教学", "teaching", "技能", "skill"
        ],
        TicketType.CUSTOMER_COMPLAINT: [
            "投诉", "complaint", "客户", "customer", "不满", "dissatisfied",
            "问题", "problem", "服务", "service"
        ],
        TicketType.SYSTEM_ERROR: [
            "系统", "system", "错误", "error", "故障", "failure",
            "异常", "exception", "崩溃", "crash"
        ]
    }
    
    @classmethod
    def classify_ticket_type(
        cls,
        title: str,
        description: Optional[str] = None,
        quality_issue: Optional[QualityIssue] = None
    ) -> TicketType:
        """
        Classify ticket type based on content analysis.
        
        Args:
            title: Ticket title
            description: Ticket description
            quality_issue: Related quality issue
            
        Returns:
            Classified ticket type
        """
        text = f"{title} {description or ''}".lower()
        
        # If related to quality issue, prioritize quality-related types
        if quality_issue:
            if quality_issue.issue_type in ["annotation_error", "labeling_mistake"]:
                return TicketType.ANNOTATION_ERROR
            elif quality_issue.issue_type in ["data_corruption", "missing_data"]:
                return TicketType.DATA_REPAIR
            else:
                return TicketType.QUALITY_ISSUE
        
        # Score each type based on keyword matches
        type_scores = {}
        for ticket_type, keywords in cls.TYPE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                type_scores[ticket_type] = score
        
        # Return type with highest score, default to QUALITY_ISSUE
        if type_scores:
            return max(type_scores, key=type_scores.get)
        
        return TicketType.QUALITY_ISSUE


class IntelligentTicketCreator:
    """
    Intelligent ticket creation system.
    
    Automatically creates tickets from quality issues with smart
    priority assessment, classification, and template application.
    """
    
    def __init__(self):
        """Initialize the intelligent ticket creator."""
        self._priority_rules = self._setup_priority_rules()
        self._templates = self._setup_templates()
        
    def _setup_priority_rules(self) -> List[PriorityAssessmentRule]:
        """Setup priority assessment rules."""
        return [
            # Critical priority rules
            PriorityAssessmentRule(
                "critical_severity",
                lambda qi, **kwargs: qi and qi.severity == IssueSeverity.CRITICAL,
                TicketPriority.CRITICAL,
                weight=2.0
            ),
            PriorityAssessmentRule(
                "customer_complaint",
                lambda qi, ticket_type, **kwargs: ticket_type == TicketType.CUSTOMER_COMPLAINT,
                TicketPriority.HIGH,
                weight=1.5
            ),
            PriorityAssessmentRule(
                "system_error",
                lambda qi, ticket_type, **kwargs: ticket_type == TicketType.SYSTEM_ERROR,
                TicketPriority.HIGH,
                weight=1.5
            ),
            
            # High priority rules
            PriorityAssessmentRule(
                "high_severity",
                lambda qi, **kwargs: qi and qi.severity == IssueSeverity.HIGH,
                TicketPriority.HIGH,
                weight=1.5
            ),
            PriorityAssessmentRule(
                "data_repair_urgent",
                lambda qi, ticket_type, **kwargs: (
                    ticket_type == TicketType.DATA_REPAIR and 
                    qi and "urgent" in (qi.description or "").lower()
                ),
                TicketPriority.HIGH,
                weight=1.3
            ),
            
            # Medium priority rules
            PriorityAssessmentRule(
                "medium_severity",
                lambda qi, **kwargs: qi and qi.severity == IssueSeverity.MEDIUM,
                TicketPriority.MEDIUM,
                weight=1.0
            ),
            PriorityAssessmentRule(
                "annotation_error",
                lambda qi, ticket_type, **kwargs: ticket_type == TicketType.ANNOTATION_ERROR,
                TicketPriority.MEDIUM,
                weight=1.0
            ),
            
            # Low priority rules
            PriorityAssessmentRule(
                "low_severity",
                lambda qi, **kwargs: qi and qi.severity == IssueSeverity.LOW,
                TicketPriority.LOW,
                weight=0.8
            ),
            PriorityAssessmentRule(
                "training_feedback",
                lambda qi, ticket_type, **kwargs: ticket_type == TicketType.TRAINING_FEEDBACK,
                TicketPriority.LOW,
                weight=0.8
            ),
        ]
    
    def _setup_templates(self) -> Dict[TicketTemplate, Dict[str, Any]]:
        """Setup ticket templates."""
        return {
            TicketTemplate.QUALITY_ISSUE: {
                "title_template": "质量问题: {issue_type}",
                "description_template": """
质量问题详情:
- 问题类型: {issue_type}
- 严重程度: {severity}
- 相关任务: {task_id}
- 问题描述: {description}

建议处理步骤:
1. 分析问题根因
2. 制定修复方案
3. 执行修复操作
4. 验证修复效果
                """.strip(),
                "skill_requirements": {
                    "skills": ["quality_control", "data_analysis"],
                    "min_level": 0.6
                },
                "workload_weight": 1.2
            },
            
            TicketTemplate.ANNOTATION_ERROR: {
                "title_template": "标注错误: {task_title}",
                "description_template": """
标注错误详情:
- 任务ID: {task_id}
- 错误类型: {issue_type}
- 发现时间: {created_at}
- 错误描述: {description}

处理要求:
1. 重新审核标注结果
2. 纠正错误标注
3. 更新质量评分
4. 记录改进建议
                """.strip(),
                "skill_requirements": {
                    "skills": ["annotation", "quality_review"],
                    "min_level": 0.7
                },
                "workload_weight": 1.0
            },
            
            TicketTemplate.DATA_REPAIR: {
                "title_template": "数据修复: {issue_description}",
                "description_template": """
数据修复任务:
- 数据范围: {task_id}
- 问题类型: {issue_type}
- 影响程度: {severity}
- 详细说明: {description}

修复流程:
1. 备份原始数据
2. 分析损坏范围
3. 执行数据修复
4. 验证数据完整性
5. 更新相关记录
                """.strip(),
                "skill_requirements": {
                    "skills": ["data_repair", "database_management"],
                    "min_level": 0.8
                },
                "workload_weight": 1.5
            },
            
            TicketTemplate.REVIEW_REQUEST: {
                "title_template": "审核请求: {task_title}",
                "description_template": """
审核请求详情:
- 请求类型: {issue_type}
- 任务信息: {task_id}
- 审核要求: {description}
- 截止时间: {sla_deadline}

审核内容:
1. 检查工作质量
2. 验证合规性
3. 提供改进建议
4. 确认完成状态
                """.strip(),
                "skill_requirements": {
                    "skills": ["quality_review", "compliance_check"],
                    "min_level": 0.6
                },
                "workload_weight": 0.8
            },
            
            TicketTemplate.CUSTOMER_COMPLAINT: {
                "title_template": "客户投诉: {complaint_summary}",
                "description_template": """
客户投诉处理:
- 投诉内容: {description}
- 相关任务: {task_id}
- 紧急程度: {severity}
- 处理要求: 24小时内响应

处理步骤:
1. 立即确认收到投诉
2. 调查问题原因
3. 制定解决方案
4. 与客户沟通进展
5. 跟踪满意度
                """.strip(),
                "skill_requirements": {
                    "skills": ["customer_service", "problem_solving"],
                    "min_level": 0.7
                },
                "workload_weight": 1.3
            }
        }
    
    async def create_ticket_from_quality_issue(
        self,
        quality_issue: QualityIssue,
        task: Optional[Task] = None,
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None,
        auto_classify: bool = True,
        template: Optional[TicketTemplate] = None
    ) -> Optional[UUID]:
        """
        Create a ticket automatically from a quality issue.
        
        Args:
            quality_issue: Source quality issue
            task: Related task information
            tenant_id: Tenant identifier
            created_by: User creating the ticket
            auto_classify: Whether to auto-classify ticket type
            template: Specific template to use
            
        Returns:
            Created ticket ID or None if failed
        """
        try:
            with db_manager.get_session() as session:
                # Determine ticket type
                if auto_classify:
                    ticket_type = TicketClassifier.classify_ticket_type(
                        title=quality_issue.issue_type,
                        description=quality_issue.description,
                        quality_issue=quality_issue
                    )
                else:
                    ticket_type = TicketType.QUALITY_ISSUE
                
                # Assess priority
                priority = self._assess_priority(
                    quality_issue=quality_issue,
                    ticket_type=ticket_type,
                    task=task
                )
                
                # Select template
                if not template:
                    template = self._select_template(ticket_type)
                
                # Generate ticket content
                title, description, metadata = self._generate_ticket_content(
                    template=template,
                    quality_issue=quality_issue,
                    task=task,
                    ticket_type=ticket_type
                )
                
                # Get template configuration
                template_config = self._templates.get(template, {})
                
                # Create ticket
                now = datetime.now()
                ticket_model = TicketModel(
                    ticket_type=ticket_type,
                    title=title,
                    description=description,
                    priority=priority,
                    status=TicketStatus.OPEN,
                    quality_issue_id=quality_issue.id,
                    task_id=task.id if task else quality_issue.task_id,
                    tenant_id=tenant_id,
                    created_by=created_by or "system",
                    skill_requirements=template_config.get("skill_requirements", {}),
                    workload_weight=template_config.get("workload_weight", 1.0),
                    metadata=metadata,
                    sla_deadline=SLAConfig.get_sla_deadline(priority, now),
                    created_at=now,
                    updated_at=now,
                )
                
                session.add(ticket_model)
                
                # Add creation tags
                tags = self._generate_tags(quality_issue, ticket_type, priority)
                if tags:
                    ticket_model.extra_metadata["tags"] = tags
                
                # Record creation history
                history = TicketHistoryModel(
                    ticket_id=ticket_model.id,
                    action="auto_created",
                    new_value=f"from_quality_issue:{quality_issue.id}",
                    performed_by=created_by or "system",
                    notes=f"Auto-created from quality issue using {template.value} template"
                )
                session.add(history)
                
                session.commit()
                
                logger.info(
                    f"Auto-created ticket {ticket_model.id} from quality issue {quality_issue.id}"
                )
                
                return ticket_model.id
                
        except Exception as e:
            logger.error(f"Error creating ticket from quality issue: {e}")
            return None
    
    def _assess_priority(
        self,
        quality_issue: Optional[QualityIssue] = None,
        ticket_type: Optional[TicketType] = None,
        task: Optional[Task] = None,
        **kwargs
    ) -> TicketPriority:
        """
        Assess ticket priority using configured rules.
        
        Args:
            quality_issue: Related quality issue
            ticket_type: Ticket type
            task: Related task
            **kwargs: Additional context
            
        Returns:
            Assessed priority level
        """
        # Collect rule scores
        rule_scores = []
        
        for rule in self._priority_rules:
            try:
                if rule.condition(
                    qi=quality_issue,
                    ticket_type=ticket_type,
                    task=task,
                    **kwargs
                ):
                    # Convert priority to numeric score for weighted calculation
                    priority_score = {
                        TicketPriority.LOW: 1,
                        TicketPriority.MEDIUM: 2,
                        TicketPriority.HIGH: 3,
                        TicketPriority.CRITICAL: 4
                    }[rule.priority]
                    
                    rule_scores.append(priority_score * rule.weight)
                    
            except Exception as e:
                logger.warning(f"Error evaluating priority rule {rule.name}: {e}")
        
        # Calculate weighted average
        if rule_scores:
            avg_score = sum(rule_scores) / len(rule_scores)
            
            # Convert back to priority enum
            if avg_score >= 3.5:
                return TicketPriority.CRITICAL
            elif avg_score >= 2.5:
                return TicketPriority.HIGH
            elif avg_score >= 1.5:
                return TicketPriority.MEDIUM
            else:
                return TicketPriority.LOW
        
        # Default priority
        return TicketPriority.MEDIUM
    
    def _select_template(self, ticket_type: TicketType) -> TicketTemplate:
        """Select appropriate template based on ticket type."""
        template_mapping = {
            TicketType.QUALITY_ISSUE: TicketTemplate.QUALITY_ISSUE,
            TicketType.ANNOTATION_ERROR: TicketTemplate.ANNOTATION_ERROR,
            TicketType.DATA_REPAIR: TicketTemplate.DATA_REPAIR,
            TicketType.REVIEW_REQUEST: TicketTemplate.REVIEW_REQUEST,
            TicketType.TRAINING_FEEDBACK: TicketTemplate.TRAINING_FEEDBACK,
            TicketType.CUSTOMER_COMPLAINT: TicketTemplate.CUSTOMER_COMPLAINT,
            TicketType.SYSTEM_ERROR: TicketTemplate.QUALITY_ISSUE,  # Fallback
        }
        
        return template_mapping.get(ticket_type, TicketTemplate.QUALITY_ISSUE)
    
    def _generate_ticket_content(
        self,
        template: TicketTemplate,
        quality_issue: QualityIssue,
        task: Optional[Task] = None,
        ticket_type: Optional[TicketType] = None
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Generate ticket title, description, and metadata from template.
        
        Args:
            template: Template to use
            quality_issue: Source quality issue
            task: Related task
            ticket_type: Ticket type
            
        Returns:
            Tuple of (title, description, metadata)
        """
        template_config = self._templates.get(template, {})
        
        # Prepare template variables
        variables = {
            "issue_type": quality_issue.issue_type,
            "severity": quality_issue.severity.value,
            "task_id": str(quality_issue.task_id),
            "description": quality_issue.description or "无详细描述",
            "created_at": quality_issue.created_at.strftime("%Y-%m-%d %H:%M"),
            "task_title": task.title if task else f"Task {quality_issue.task_id}",
            "issue_description": quality_issue.description or quality_issue.issue_type,
            "complaint_summary": quality_issue.issue_type,
            "sla_deadline": "待确定"
        }
        
        # Generate title
        title_template = template_config.get("title_template", "工单: {issue_type}")
        title = title_template.format(**variables)
        
        # Generate description
        desc_template = template_config.get("description_template", "{description}")
        description = desc_template.format(**variables)
        
        # Generate metadata
        metadata = {
            "template_used": template.value,
            "auto_generated": True,
            "source_quality_issue": str(quality_issue.id),
            "generation_time": datetime.now().isoformat(),
        }
        
        if task:
            metadata["source_task"] = str(task.id)
        
        return title, description, metadata
    
    def _generate_tags(
        self,
        quality_issue: QualityIssue,
        ticket_type: TicketType,
        priority: TicketPriority
    ) -> List[str]:
        """Generate tags for the ticket."""
        tags = []
        
        # Add type-based tags
        tags.append(f"type:{ticket_type.value}")
        tags.append(f"priority:{priority.value}")
        tags.append(f"severity:{quality_issue.severity.value}")
        
        # Add issue-specific tags
        if quality_issue.issue_type:
            tags.append(f"issue:{quality_issue.issue_type}")
        
        # Add auto-generation tag
        tags.append("auto_generated")
        
        # Add urgency tags
        if priority in [TicketPriority.CRITICAL, TicketPriority.HIGH]:
            tags.append("urgent")
        
        return tags
    
    async def create_ticket_from_template(
        self,
        template: TicketTemplate,
        title: str,
        description: Optional[str] = None,
        priority: Optional[TicketPriority] = None,
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None,
        custom_variables: Optional[Dict[str, Any]] = None
    ) -> Optional[UUID]:
        """
        Create a ticket using a specific template.
        
        Args:
            template: Template to use
            title: Ticket title
            description: Custom description (overrides template)
            priority: Custom priority (overrides template assessment)
            tenant_id: Tenant identifier
            created_by: User creating the ticket
            custom_variables: Custom template variables
            
        Returns:
            Created ticket ID or None if failed
        """
        try:
            with db_manager.get_session() as session:
                template_config = self._templates.get(template, {})
                
                # Determine ticket type from template
                type_mapping = {
                    TicketTemplate.QUALITY_ISSUE: TicketType.QUALITY_ISSUE,
                    TicketTemplate.ANNOTATION_ERROR: TicketType.ANNOTATION_ERROR,
                    TicketTemplate.DATA_REPAIR: TicketType.DATA_REPAIR,
                    TicketTemplate.REVIEW_REQUEST: TicketType.REVIEW_REQUEST,
                    TicketTemplate.TRAINING_FEEDBACK: TicketType.TRAINING_FEEDBACK,
                    TicketTemplate.CUSTOMER_COMPLAINT: TicketType.CUSTOMER_COMPLAINT,
                    TicketTemplate.SYSTEM_ERROR: TicketType.SYSTEM_ERROR,
                }
                
                ticket_type = type_mapping.get(template, TicketType.QUALITY_ISSUE)
                
                # Use provided priority or assess from template
                if not priority:
                    priority = TicketPriority.MEDIUM  # Default for manual creation
                
                # Generate description from template if not provided
                if not description and template_config.get("description_template"):
                    variables = custom_variables or {}
                    variables.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
                    
                    try:
                        description = template_config["description_template"].format(**variables)
                    except KeyError as e:
                        logger.warning(f"Missing template variable {e}, using basic description")
                        description = f"使用模板 {template.value} 创建的工单"
                
                # Create ticket
                now = datetime.now()
                ticket_model = TicketModel(
                    ticket_type=ticket_type,
                    title=title,
                    description=description,
                    priority=priority,
                    status=TicketStatus.OPEN,
                    tenant_id=tenant_id,
                    created_by=created_by or "system",
                    skill_requirements=template_config.get("skill_requirements", {}),
                    workload_weight=template_config.get("workload_weight", 1.0),
                    metadata={
                        "template_used": template.value,
                        "manual_creation": True,
                        "creation_time": now.isoformat(),
                        "custom_variables": custom_variables or {}
                    },
                    sla_deadline=SLAConfig.get_sla_deadline(priority, now),
                    created_at=now,
                    updated_at=now,
                )
                
                session.add(ticket_model)
                
                # Record creation history
                history = TicketHistoryModel(
                    ticket_id=ticket_model.id,
                    action="template_created",
                    new_value=template.value,
                    performed_by=created_by or "system",
                    notes=f"Created using {template.value} template"
                )
                session.add(history)
                
                session.commit()
                
                logger.info(f"Created ticket {ticket_model.id} using template {template.value}")
                
                return ticket_model.id
                
        except Exception as e:
            logger.error(f"Error creating ticket from template: {e}")
            return None
    
    async def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available ticket templates with their configurations.
        
        Returns:
            Dictionary of template configurations
        """
        return {
            template.value: {
                "name": template.value,
                "title_template": config.get("title_template", ""),
                "description_template": config.get("description_template", ""),
                "skill_requirements": config.get("skill_requirements", {}),
                "workload_weight": config.get("workload_weight", 1.0),
                "suggested_priority": "medium"
            }
            for template, config in self._templates.items()
        }
    
    async def get_priority_assessment_rules(self) -> List[Dict[str, Any]]:
        """
        Get configured priority assessment rules.
        
        Returns:
            List of rule configurations
        """
        return [
            {
                "name": rule.name,
                "priority": rule.priority.value,
                "weight": rule.weight,
                "description": f"Rule for {rule.name} assessment"
            }
            for rule in self._priority_rules
        ]
