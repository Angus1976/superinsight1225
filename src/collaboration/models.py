"""
Collaboration Workflow Database Models (协作与审核流程数据库模型)

SQLAlchemy models for collaboration workflow functionality.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.database.base import Base


# ============== Task Assignment Models ==============

class TaskAssignment(Base):
    """任务分配表"""
    __tablename__ = "collab_task_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    annotator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    priority = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    status = Column(String(20), default="assigned")  # assigned, in_progress, completed, cancelled
    assigned_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('task_id', 'annotator_id', name='uq_task_annotator'),
    )


class AnnotationVersion(Base):
    """标注版本表"""
    __tablename__ = "collab_annotation_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    annotator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    annotation = Column(JSONB, nullable=False)
    version = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('task_id', 'version', name='uq_task_version'),
    )


class TaskLock(Base):
    """任务锁表"""
    __tablename__ = "collab_task_locks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    locked_by = Column(UUID(as_uuid=True), nullable=False)
    locked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


# ============== Review Flow Models ==============

class ReviewFlow(Base):
    """审核流程配置表"""
    __tablename__ = "collab_review_flows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    levels = Column(Integer, default=2)
    pass_threshold = Column(Float, default=0.8)
    auto_approve = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReviewTask(Base):
    """审核任务表"""
    __tablename__ = "collab_review_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    annotation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    current_level = Column(Integer, default=1)
    max_level = Column(Integer, default=2)
    status = Column(String(20), default="pending")  # pending, in_review, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReviewHistory(Base):
    """审核历史表"""
    __tablename__ = "collab_review_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    review_task_id = Column(UUID(as_uuid=True), ForeignKey("collab_review_tasks.id"), nullable=False, index=True)
    annotation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # approve, reject, modify
    reason = Column(Text, nullable=True)
    level = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============== Conflict Resolution Models ==============

class Conflict(Base):
    """冲突表"""
    __tablename__ = "collab_conflicts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    version1_id = Column(UUID(as_uuid=True), ForeignKey("collab_annotation_versions.id"), nullable=False)
    version2_id = Column(UUID(as_uuid=True), ForeignKey("collab_annotation_versions.id"), nullable=False)
    conflict_type = Column(String(50), nullable=False)  # label_mismatch, boundary_mismatch, content_mismatch
    status = Column(String(20), default="unresolved")  # unresolved, voting, resolved
    created_at = Column(DateTime, default=datetime.utcnow)


class ConflictVote(Base):
    """冲突投票表"""
    __tablename__ = "collab_conflict_votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conflict_id = Column(UUID(as_uuid=True), ForeignKey("collab_conflicts.id"), nullable=False, index=True)
    voter_id = Column(UUID(as_uuid=True), nullable=False)
    choice = Column(String(50), nullable=False)  # version1, version2, other
    voted_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('conflict_id', 'voter_id', name='uq_conflict_voter'),
    )


class ConflictResolution(Base):
    """冲突解决表"""
    __tablename__ = "collab_conflict_resolutions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conflict_id = Column(UUID(as_uuid=True), ForeignKey("collab_conflicts.id"), nullable=False, unique=True)
    method = Column(String(20), nullable=False)  # voting, expert
    result = Column(JSONB, nullable=False)
    vote_counts = Column(JSONB, nullable=True)
    expert_id = Column(UUID(as_uuid=True), nullable=True)
    resolved_at = Column(DateTime, default=datetime.utcnow)


# ============== Crowdsource Models ==============

class CrowdsourceTask(Base):
    """众包任务表"""
    __tablename__ = "collab_crowdsource_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    data_ids = Column(JSONB, nullable=False)
    config = Column(JSONB, nullable=False)
    platform = Column(String(50), default="internal")  # internal, mturk, scale_ai, custom
    status = Column(String(20), default="open")  # open, in_progress, completed, cancelled
    external_task_id = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrowdsourceAnnotator(Base):
    """众包标注员表"""
    __tablename__ = "collab_crowdsource_annotators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(200), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(200), nullable=True)
    real_name = Column(String(100), nullable=True)
    identity_verified = Column(Boolean, default=False)
    identity_doc_type = Column(String(20), nullable=True)
    identity_doc_number = Column(String(50), nullable=True)
    status = Column(String(30), default="pending_verification")  # pending_verification, pending_test, active, suspended, disabled
    star_rating = Column(Integer, default=0)  # 1-5 stars
    ability_tags = Column(JSONB, default=list)
    total_tasks = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrowdsourceTaskClaim(Base):
    """众包任务领取表"""
    __tablename__ = "collab_crowdsource_task_claims"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("collab_crowdsource_tasks.id"), nullable=False, index=True)
    annotator_id = Column(UUID(as_uuid=True), ForeignKey("collab_crowdsource_annotators.id"), nullable=False, index=True)
    claimed_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="active")  # active, expired, completed
    
    __table_args__ = (
        UniqueConstraint('task_id', 'annotator_id', name='uq_crowdsource_task_annotator'),
    )


class CrowdsourceSubmission(Base):
    """众包提交表"""
    __tablename__ = "collab_crowdsource_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("collab_crowdsource_tasks.id"), nullable=False, index=True)
    annotator_id = Column(UUID(as_uuid=True), ForeignKey("collab_crowdsource_annotators.id"), nullable=False, index=True)
    annotation = Column(JSONB, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    price = Column(Float, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class CrowdsourceAbilityTest(Base):
    """众包能力测试表"""
    __tablename__ = "collab_crowdsource_ability_tests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    annotator_id = Column(UUID(as_uuid=True), ForeignKey("collab_crowdsource_annotators.id"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False)
    details = Column(JSONB, nullable=True)
    tested_at = Column(DateTime, default=datetime.utcnow)


# ============== Third Party Platform Models ==============

class ThirdPartyPlatform(Base):
    """第三方平台配置表"""
    __tablename__ = "collab_third_party_platforms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    platform_type = Column(String(20), nullable=False)  # mturk, scale_ai, custom
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)
    endpoint = Column(String(500), nullable=True)
    extra_config = Column(JSONB, default=dict)
    status = Column(String(20), default="disconnected")  # connected, disconnected
    connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlatformSyncLog(Base):
    """平台同步日志表"""
    __tablename__ = "collab_platform_sync_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    platform_name = Column(String(100), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    external_task_id = Column(String(200), nullable=True)
    action = Column(String(20), nullable=False)  # create, fetch, update
    success = Column(Boolean, nullable=False)
    message = Column(Text, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)


# ============== Billing Models ==============

class CrowdsourcePricingConfig(Base):
    """众包计费配置表"""
    __tablename__ = "collab_crowdsource_pricing_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    base_price = Column(Float, default=0.1)
    task_type_prices = Column(JSONB, default=dict)
    quality_bonus_enabled = Column(Boolean, default=True)
    star_bonus_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrowdsourceWithdrawal(Base):
    """众包提现记录表"""
    __tablename__ = "collab_crowdsource_withdrawals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    annotator_id = Column(UUID(as_uuid=True), ForeignKey("collab_crowdsource_annotators.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    method = Column(String(20), nullable=False)  # bank_transfer, alipay, wechat
    account_info = Column(JSONB, nullable=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    transaction_id = Column(String(100), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CrowdsourceInvoice(Base):
    """众包发票表"""
    __tablename__ = "collab_crowdsource_invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    annotator_id = Column(UUID(as_uuid=True), ForeignKey("collab_crowdsource_annotators.id"), nullable=False, index=True)
    period = Column(String(20), nullable=False)  # e.g., "2026-01"
    amount = Column(Float, nullable=False)
    task_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, issued, paid
    created_at = Column(DateTime, default=datetime.utcnow)


# ============== Notification Models ==============

class NotificationPreference(Base):
    """通知偏好表"""
    __tablename__ = "collab_notification_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    channels = Column(JSONB, default=["in_app"])
    task_assigned = Column(Boolean, default=True)
    review_completed = Column(Boolean, default=True)
    deadline_reminder = Column(Boolean, default=True)
    quality_warning = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    """通知表"""
    __tablename__ = "collab_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # in_app, email, webhook
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
