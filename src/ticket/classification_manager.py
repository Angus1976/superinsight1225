"""
Ticket classification and tagging management system.

Provides:
- Automatic ticket classification
- Tag management and assignment
- Classification rule engine
- Tag-based filtering and search
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from uuid import UUID
from enum import Enum
import re

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.ticket.models import (
    TicketModel,
    TicketHistoryModel,
    TicketType,
    TicketPriority,
    TicketStatus,
)

logger = logging.getLogger(__name__)


class TagCategory(str, Enum):
    """Categories for ticket tags."""
    TYPE = "type"
    PRIORITY = "priority"
    STATUS = "status"
    SKILL = "skill"
    DOMAIN = "domain"
    URGENCY = "urgency"
    SOURCE = "source"
    CUSTOM = "custom"


class ClassificationRule:
    """Rule for automatic ticket classification."""
    
    def __init__(
        self,
        name: str,
        condition: callable,
        tags: List[str],
        confidence: float = 1.0,
        enabled: bool = True
    ):
        self.name = name
        self.condition = condition
        self.tags = tags
        self.confidence = confidence
        self.enabled = enabled


class TicketClassificationManager:
    """
    Manages ticket classification and tagging.
    
    Provides automatic classification based on content analysis,
    tag management, and classification rule engine.
    """
    
    def __init__(self):
        """Initialize the classification manager."""
        self._classification_rules = self._setup_classification_rules()
        self._tag_hierarchy = self._setup_tag_hierarchy()
        
    def _setup_classification_rules(self) -> List[ClassificationRule]:
        """Setup automatic classification rules."""
        return [
            # Quality-related rules
            ClassificationRule(
                name="quality_accuracy",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["准确性", "accuracy", "精确", "正确性", "错误率"]
                ),
                tags=["domain:quality", "type:accuracy", "skill:quality_control"],
                confidence=0.9
            ),
            
            ClassificationRule(
                name="quality_consistency",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["一致性", "consistency", "统一", "标准化", "规范"]
                ),
                tags=["domain:quality", "type:consistency", "skill:standardization"],
                confidence=0.9
            ),
            
            ClassificationRule(
                name="annotation_error",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["标注错误", "annotation error", "标记错误", "分类错误"]
                ),
                tags=["domain:annotation", "type:error", "skill:annotation", "urgency:high"],
                confidence=0.95
            ),
            
            # Data-related rules
            ClassificationRule(
                name="data_corruption",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["数据损坏", "data corruption", "文件损坏", "数据丢失"]
                ),
                tags=["domain:data", "type:corruption", "skill:data_repair", "urgency:critical"],
                confidence=0.95
            ),
            
            ClassificationRule(
                name="data_missing",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["数据缺失", "missing data", "数据不完整", "缺少文件"]
                ),
                tags=["domain:data", "type:missing", "skill:data_recovery"],
                confidence=0.9
            ),
            
            # System-related rules
            ClassificationRule(
                name="system_performance",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["性能", "performance", "慢", "slow", "超时", "timeout"]
                ),
                tags=["domain:system", "type:performance", "skill:system_admin"],
                confidence=0.8
            ),
            
            ClassificationRule(
                name="system_error",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["系统错误", "system error", "异常", "exception", "崩溃", "crash"]
                ),
                tags=["domain:system", "type:error", "skill:debugging", "urgency:high"],
                confidence=0.9
            ),
            
            # Customer-related rules
            ClassificationRule(
                name="customer_complaint",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["客户投诉", "customer complaint", "用户反馈", "不满意"]
                ),
                tags=["domain:customer", "type:complaint", "skill:customer_service", "urgency:high"],
                confidence=0.95
            ),
            
            # Training-related rules
            ClassificationRule(
                name="training_request",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["培训", "training", "学习", "指导", "教学"]
                ),
                tags=["domain:training", "type:request", "skill:training"],
                confidence=0.85
            ),
            
            # Urgency detection rules
            ClassificationRule(
                name="urgent_keywords",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["紧急", "urgent", "立即", "immediately", "asap", "马上"]
                ),
                tags=["urgency:urgent"],
                confidence=0.9
            ),
            
            ClassificationRule(
                name="critical_keywords",
                condition=lambda title, desc: any(
                    keyword in f"{title} {desc}".lower()
                    for keyword in ["严重", "critical", "重大", "major", "致命", "fatal"]
                ),
                tags=["urgency:critical"],
                confidence=0.9
            ),
        ]
    
    def _setup_tag_hierarchy(self) -> Dict[str, Dict[str, Any]]:
        """Setup tag hierarchy and metadata."""
        return {
            # Domain tags
            "domain:quality": {
                "category": TagCategory.DOMAIN,
                "display_name": "质量管理",
                "description": "质量相关问题",
                "color": "#4CAF50"
            },
            "domain:annotation": {
                "category": TagCategory.DOMAIN,
                "display_name": "标注管理",
                "description": "标注相关问题",
                "color": "#2196F3"
            },
            "domain:data": {
                "category": TagCategory.DOMAIN,
                "display_name": "数据管理",
                "description": "数据相关问题",
                "color": "#FF9800"
            },
            "domain:system": {
                "category": TagCategory.DOMAIN,
                "display_name": "系统管理",
                "description": "系统相关问题",
                "color": "#9C27B0"
            },
            "domain:customer": {
                "category": TagCategory.DOMAIN,
                "display_name": "客户服务",
                "description": "客户相关问题",
                "color": "#F44336"
            },
            "domain:training": {
                "category": TagCategory.DOMAIN,
                "display_name": "培训支持",
                "description": "培训相关问题",
                "color": "#607D8B"
            },
            
            # Type tags
            "type:accuracy": {
                "category": TagCategory.TYPE,
                "display_name": "准确性问题",
                "description": "准确性相关问题"
            },
            "type:consistency": {
                "category": TagCategory.TYPE,
                "display_name": "一致性问题",
                "description": "一致性相关问题"
            },
            "type:error": {
                "category": TagCategory.TYPE,
                "display_name": "错误问题",
                "description": "错误相关问题"
            },
            "type:corruption": {
                "category": TagCategory.TYPE,
                "display_name": "损坏问题",
                "description": "数据损坏问题"
            },
            "type:missing": {
                "category": TagCategory.TYPE,
                "display_name": "缺失问题",
                "description": "数据缺失问题"
            },
            "type:performance": {
                "category": TagCategory.TYPE,
                "display_name": "性能问题",
                "description": "性能相关问题"
            },
            "type:complaint": {
                "category": TagCategory.TYPE,
                "display_name": "投诉问题",
                "description": "客户投诉问题"
            },
            "type:request": {
                "category": TagCategory.TYPE,
                "display_name": "请求问题",
                "description": "服务请求问题"
            },
            
            # Skill tags
            "skill:quality_control": {
                "category": TagCategory.SKILL,
                "display_name": "质量控制",
                "description": "需要质量控制技能"
            },
            "skill:annotation": {
                "category": TagCategory.SKILL,
                "display_name": "标注技能",
                "description": "需要标注技能"
            },
            "skill:data_repair": {
                "category": TagCategory.SKILL,
                "display_name": "数据修复",
                "description": "需要数据修复技能"
            },
            "skill:data_recovery": {
                "category": TagCategory.SKILL,
                "display_name": "数据恢复",
                "description": "需要数据恢复技能"
            },
            "skill:system_admin": {
                "category": TagCategory.SKILL,
                "display_name": "系统管理",
                "description": "需要系统管理技能"
            },
            "skill:debugging": {
                "category": TagCategory.SKILL,
                "display_name": "调试技能",
                "description": "需要调试技能"
            },
            "skill:customer_service": {
                "category": TagCategory.SKILL,
                "display_name": "客户服务",
                "description": "需要客户服务技能"
            },
            "skill:training": {
                "category": TagCategory.SKILL,
                "display_name": "培训技能",
                "description": "需要培训技能"
            },
            "skill:standardization": {
                "category": TagCategory.SKILL,
                "display_name": "标准化",
                "description": "需要标准化技能"
            },
            
            # Urgency tags
            "urgency:low": {
                "category": TagCategory.URGENCY,
                "display_name": "低紧急度",
                "description": "低紧急度问题",
                "color": "#4CAF50"
            },
            "urgency:medium": {
                "category": TagCategory.URGENCY,
                "display_name": "中紧急度",
                "description": "中紧急度问题",
                "color": "#FF9800"
            },
            "urgency:high": {
                "category": TagCategory.URGENCY,
                "display_name": "高紧急度",
                "description": "高紧急度问题",
                "color": "#FF5722"
            },
            "urgency:critical": {
                "category": TagCategory.URGENCY,
                "display_name": "紧急",
                "description": "紧急问题",
                "color": "#F44336"
            },
            "urgency:urgent": {
                "category": TagCategory.URGENCY,
                "display_name": "急需处理",
                "description": "急需处理的问题",
                "color": "#E91E63"
            },
            
            # Source tags
            "source:auto_generated": {
                "category": TagCategory.SOURCE,
                "display_name": "自动生成",
                "description": "自动生成的工单"
            },
            "source:manual": {
                "category": TagCategory.SOURCE,
                "display_name": "手动创建",
                "description": "手动创建的工单"
            },
            "source:quality_issue": {
                "category": TagCategory.SOURCE,
                "display_name": "质量问题",
                "description": "来源于质量问题"
            },
            "source:customer_feedback": {
                "category": TagCategory.SOURCE,
                "display_name": "客户反馈",
                "description": "来源于客户反馈"
            },
        }
    
    async def classify_ticket(
        self,
        ticket_id: UUID,
        title: str,
        description: Optional[str] = None,
        ticket_type: Optional[TicketType] = None,
        priority: Optional[TicketPriority] = None,
        auto_apply: bool = True
    ) -> List[str]:
        """
        Classify a ticket and return suggested tags.
        
        Args:
            ticket_id: Ticket ID
            title: Ticket title
            description: Ticket description
            ticket_type: Ticket type
            priority: Ticket priority
            auto_apply: Whether to automatically apply tags
            
        Returns:
            List of suggested tags
        """
        try:
            suggested_tags = set()
            
            # Add basic tags based on ticket properties
            if ticket_type:
                suggested_tags.add(f"type:{ticket_type.value}")
            
            if priority:
                suggested_tags.add(f"priority:{priority.value}")
            
            # Apply classification rules
            for rule in self._classification_rules:
                if not rule.enabled:
                    continue
                
                try:
                    if rule.condition(title, description or ""):
                        suggested_tags.update(rule.tags)
                        logger.debug(f"Rule '{rule.name}' matched for ticket {ticket_id}")
                        
                except Exception as e:
                    logger.warning(f"Error applying rule '{rule.name}': {e}")
            
            # Convert to sorted list
            final_tags = sorted(list(suggested_tags))
            
            # Auto-apply tags if requested
            if auto_apply and final_tags:
                await self.apply_tags(ticket_id, final_tags, applied_by="system")
            
            return final_tags
            
        except Exception as e:
            logger.error(f"Error classifying ticket {ticket_id}: {e}")
            return []
    
    async def apply_tags(
        self,
        ticket_id: UUID,
        tags: List[str],
        applied_by: str = "system",
        replace_existing: bool = False
    ) -> bool:
        """
        Apply tags to a ticket.
        
        Args:
            ticket_id: Ticket ID
            tags: List of tags to apply
            applied_by: User applying the tags
            replace_existing: Whether to replace existing tags
            
        Returns:
            True if successful
        """
        try:
            with db_manager.get_session() as session:
                ticket = session.execute(
                    select(TicketModel).where(TicketModel.id == ticket_id)
                ).scalar_one_or_none()
                
                if not ticket:
                    logger.error(f"Ticket not found: {ticket_id}")
                    return False
                
                # Get current tags
                current_tags = ticket.extra_metadata.get("tags", [])
                
                if replace_existing:
                    new_tags = tags
                else:
                    # Merge with existing tags
                    new_tags = list(set(current_tags + tags))
                
                # Validate tags
                valid_tags = self._validate_tags(new_tags)
                
                # Update ticket metadata
                if not ticket.extra_metadata:
                    ticket.extra_metadata = {}
                
                ticket.extra_metadata["tags"] = valid_tags
                ticket.updated_at = datetime.now()
                
                # Record history
                history = TicketHistoryModel(
                    ticket_id=ticket.id,
                    action="tags_applied",
                    old_value=",".join(current_tags) if current_tags else None,
                    new_value=",".join(valid_tags),
                    performed_by=applied_by,
                    notes=f"Applied {len(tags)} tags"
                )
                session.add(history)
                
                session.commit()
                
                logger.info(f"Applied tags to ticket {ticket_id}: {valid_tags}")
                return True
                
        except Exception as e:
            logger.error(f"Error applying tags to ticket {ticket_id}: {e}")
            return False
    
    async def remove_tags(
        self,
        ticket_id: UUID,
        tags: List[str],
        removed_by: str = "system"
    ) -> bool:
        """
        Remove tags from a ticket.
        
        Args:
            ticket_id: Ticket ID
            tags: List of tags to remove
            removed_by: User removing the tags
            
        Returns:
            True if successful
        """
        try:
            with db_manager.get_session() as session:
                ticket = session.execute(
                    select(TicketModel).where(TicketModel.id == ticket_id)
                ).scalar_one_or_none()
                
                if not ticket:
                    return False
                
                current_tags = ticket.extra_metadata.get("tags", [])
                new_tags = [tag for tag in current_tags if tag not in tags]
                
                ticket.extra_metadata["tags"] = new_tags
                ticket.updated_at = datetime.now()
                
                # Record history
                history = TicketHistoryModel(
                    ticket_id=ticket.id,
                    action="tags_removed",
                    old_value=",".join(current_tags),
                    new_value=",".join(new_tags),
                    performed_by=removed_by,
                    notes=f"Removed {len(tags)} tags"
                )
                session.add(history)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error removing tags from ticket {ticket_id}: {e}")
            return False
    
    def _validate_tags(self, tags: List[str]) -> List[str]:
        """
        Validate and normalize tags.
        
        Args:
            tags: List of tags to validate
            
        Returns:
            List of valid tags
        """
        valid_tags = []
        
        for tag in tags:
            # Normalize tag format
            normalized_tag = tag.lower().strip()
            
            # Check if tag follows expected format (category:value)
            if ":" in normalized_tag:
                category, value = normalized_tag.split(":", 1)
                
                # Validate category
                if category in [cat.value for cat in TagCategory]:
                    # Validate value format (alphanumeric, underscore, hyphen)
                    if re.match(r'^[a-z0-9_-]+$', value):
                        valid_tags.append(normalized_tag)
                    else:
                        logger.warning(f"Invalid tag value format: {tag}")
                else:
                    logger.warning(f"Invalid tag category: {category}")
            else:
                # Allow simple tags without category (treated as custom)
                if re.match(r'^[a-z0-9_-]+$', normalized_tag):
                    valid_tags.append(f"custom:{normalized_tag}")
                else:
                    logger.warning(f"Invalid tag format: {tag}")
        
        return valid_tags
    
    async def get_ticket_tags(self, ticket_id: UUID) -> List[str]:
        """
        Get tags for a ticket.
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            List of tags
        """
        try:
            with db_manager.get_session() as session:
                ticket = session.execute(
                    select(TicketModel).where(TicketModel.id == ticket_id)
                ).scalar_one_or_none()
                
                if ticket and ticket.extra_metadata:
                    return ticket.extra_metadata.get("tags", [])
                
                return []
                
        except Exception as e:
            logger.error(f"Error getting tags for ticket {ticket_id}: {e}")
            return []
    
    async def search_tickets_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        tenant_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[UUID], int]:
        """
        Search tickets by tags.
        
        Args:
            tags: List of tags to search for
            match_all: Whether to match all tags (AND) or any tag (OR)
            tenant_id: Optional tenant filter
            limit: Max results
            offset: Pagination offset
            
        Returns:
            Tuple of (ticket_ids, total_count)
        """
        try:
            with db_manager.get_session() as session:
                # Build base query
                query = select(TicketModel.id)
                count_query = select(func.count(TicketModel.id))
                
                # Apply tenant filter
                filters = []
                if tenant_id:
                    filters.append(TicketModel.tenant_id == tenant_id)
                
                # Apply tag filters
                if tags:
                    if match_all:
                        # All tags must be present (AND logic)
                        for tag in tags:
                            filters.append(
                                TicketModel.extra_metadata['tags'].astext.contains(f'"{tag}"')
                            )
                    else:
                        # Any tag can be present (OR logic)
                        tag_conditions = [
                            TicketModel.extra_metadata['tags'].astext.contains(f'"{tag}"')
                            for tag in tags
                        ]
                        filters.append(or_(*tag_conditions))
                
                if filters:
                    query = query.where(and_(*filters))
                    count_query = count_query.where(and_(*filters))
                
                # Get total count
                total = session.execute(count_query).scalar()
                
                # Get paginated results
                query = query.order_by(TicketModel.created_at.desc()).limit(limit).offset(offset)
                ticket_ids = session.execute(query).scalars().all()
                
                return list(ticket_ids), total
                
        except Exception as e:
            logger.error(f"Error searching tickets by tags: {e}")
            return [], 0
    
    async def get_tag_statistics(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get tag usage statistics.
        
        Args:
            tenant_id: Optional tenant filter
            
        Returns:
            Tag statistics
        """
        try:
            with db_manager.get_session() as session:
                # Build query
                query = select(TicketModel.extra_metadata)
                if tenant_id:
                    query = query.where(TicketModel.tenant_id == tenant_id)
                
                tickets = session.execute(query).scalars().all()
                
                # Count tag usage
                tag_counts = {}
                total_tickets = 0
                
                for metadata in tickets:
                    if metadata and "tags" in metadata:
                        total_tickets += 1
                        for tag in metadata["tags"]:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # Group by category
                category_stats = {}
                for tag, count in tag_counts.items():
                    if ":" in tag:
                        category = tag.split(":", 1)[0]
                    else:
                        category = "uncategorized"
                    
                    if category not in category_stats:
                        category_stats[category] = {
                            "total_tags": 0,
                            "unique_tags": 0,
                            "tags": {}
                        }
                    
                    category_stats[category]["total_tags"] += count
                    category_stats[category]["unique_tags"] += 1
                    category_stats[category]["tags"][tag] = count
                
                return {
                    "total_tickets": total_tickets,
                    "total_tagged_tickets": len([m for m in tickets if m and "tags" in m]),
                    "unique_tags": len(tag_counts),
                    "tag_counts": tag_counts,
                    "category_stats": category_stats,
                    "most_used_tags": sorted(
                        tag_counts.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                }
                
        except Exception as e:
            logger.error(f"Error getting tag statistics: {e}")
            return {}
    
    async def get_tag_hierarchy(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the tag hierarchy and metadata.
        
        Returns:
            Tag hierarchy configuration
        """
        return self._tag_hierarchy
    
    async def add_classification_rule(
        self,
        name: str,
        condition_pattern: str,
        tags: List[str],
        confidence: float = 1.0,
        enabled: bool = True
    ) -> bool:
        """
        Add a new classification rule.
        
        Args:
            name: Rule name
            condition_pattern: Pattern to match (simple keyword matching)
            tags: Tags to apply when rule matches
            confidence: Rule confidence (0-1)
            enabled: Whether rule is enabled
            
        Returns:
            True if successful
        """
        try:
            # Create condition function from pattern
            keywords = [kw.strip().lower() for kw in condition_pattern.split(",")]
            
            def condition_func(title, desc):
                text = f"{title} {desc}".lower()
                return any(keyword in text for keyword in keywords)
            
            # Create and add rule
            rule = ClassificationRule(
                name=name,
                condition=condition_func,
                tags=tags,
                confidence=confidence,
                enabled=enabled
            )
            
            self._classification_rules.append(rule)
            
            logger.info(f"Added classification rule: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding classification rule: {e}")
            return False
    
    async def get_classification_rules(self) -> List[Dict[str, Any]]:
        """
        Get all classification rules.
        
        Returns:
            List of rule configurations
        """
        return [
            {
                "name": rule.name,
                "tags": rule.tags,
                "confidence": rule.confidence,
                "enabled": rule.enabled
            }
            for rule in self._classification_rules
        ]