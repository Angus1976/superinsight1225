"""
Security models for SuperInsight Platform.

Defines security-related data models including users, permissions, audit logs, etc.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List, Dict, Any

from src.database.connection import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    BUSINESS_EXPERT = "business_expert"
    TECHNICAL_EXPERT = "technical_expert"
    CONTRACTOR = "contractor"
    VIEWER = "viewer"


class PermissionType(str, enum.Enum):
    """Permission type enumeration."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class AuditAction(str, enum.Enum):
    """Audit action enumeration."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    ANNOTATE = "annotate"
    REVIEW = "review"


class UserModel(Base):
    """
    User table for authentication and authorization.
    
    Stores user information and role assignments.
    """
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    permissions: Mapped[List["ProjectPermissionModel"]] = relationship("ProjectPermissionModel", back_populates="user", foreign_keys="ProjectPermissionModel.user_id")
    audit_logs: Mapped[List["SecurityAuditLogModel"]] = relationship("SecurityAuditLogModel", back_populates="user")


class ProjectPermissionModel(Base):
    """
    Project permissions table for fine-grained access control.
    
    Manages user permissions at the project level.
    """
    __tablename__ = "project_permissions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False)
    permission_type: Mapped[PermissionType] = mapped_column(SQLEnum(PermissionType), nullable=False)
    granted_by: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="permissions", foreign_keys=[user_id])
    granted_by_user: Mapped[Optional["UserModel"]] = relationship("UserModel", foreign_keys=[granted_by], overlaps="user")


class IPWhitelistModel(Base):
    """
    IP whitelist table for access control.
    
    Manages allowed IP addresses and ranges.
    """
    __tablename__ = "ip_whitelist"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    ip_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # CIDR notation
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    creator: Mapped["UserModel"] = relationship("UserModel")


class SecurityAuditLogModel(Base):
    """
    Audit log table for tracking user operations.
    
    Records all user actions for security and compliance.
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default={})
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user: Mapped[Optional["UserModel"]] = relationship("UserModel", back_populates="audit_logs")


class DataMaskingRuleModel(Base):
    """
    Data masking rules table for sensitive data protection.
    
    Defines rules for masking sensitive information.
    """
    __tablename__ = "data_masking_rules"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Regex pattern
    masking_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hash, partial, replace, etc.
    masking_config: Mapped[dict] = mapped_column(JSONB, default={})
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    creator: Mapped["UserModel"] = relationship("UserModel")


# ============================================================================
# Backward Compatibility Alias
# ============================================================================
# 
# 问题背景：
# 在代码重构过程中，审计日志模型从 AuditLogModel 重命名为 SecurityAuditLogModel
# 以更好地反映其在安全模块中的作用。但是，系统中有大量文件仍在使用旧名称。
#
# 解决方案：
# 为了保持向后兼容性，避免大规模修改现有代码，这里创建了一个别名。
# 所有使用 AuditLogModel 的代码都会自动映射到 SecurityAuditLogModel。
#
# 使用示例：
#   from src.security.models import AuditLogModel  # 旧代码仍然可以工作
#   from src.security.models import SecurityAuditLogModel  # 推荐使用新名称
#
# 注意事项：
# - 新代码应该使用 SecurityAuditLogModel 而不是 AuditLogModel
# - 这个别名将在未来版本中保留，以确保兼容性
# - 如果遇到类似的模型重命名问题，可以采用相同的别名模式
#
# 相关文件：
# - src/database/models.py (已更新导入)
# - src/security/audit_*.py (多个审计相关文件)
# - src/compliance/*.py (合规性检查文件)
# - tests/test_*.py (测试文件)
# ============================================================================
AuditLogModel = SecurityAuditLogModel
