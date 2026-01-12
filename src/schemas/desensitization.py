"""
脱敏相关Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class PatternType(str, Enum):
    REGEX = "regex"
    PRESIDIO = "presidio"
    CUSTOM = "custom"

class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class MaskingType(str, Enum):
    REDACT = "redact"
    REPLACE = "replace"
    HASH = "hash"
    ENCRYPT = "encrypt"
    PARTIAL = "partial"

class SensitivityPatternCreate(BaseModel):
    name: str = Field(..., description="模式名称")
    pattern: str = Field(..., description="匹配模式")
    pattern_type: PatternType = Field(..., description="模式类型")
    sensitivity_level: SensitivityLevel = Field(..., description="敏感度级别")
    entity_type: str = Field(..., description="实体类型")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="置信度")

class SensitivityPatternResponse(SensitivityPatternCreate):
    id: str

class MaskingCondition(BaseModel):
    field: str = Field(..., description="条件字段")
    operator: str = Field(..., description="操作符")
    value: Any = Field(..., description="条件值")
    context: Optional[str] = Field(None, description="上下文")

class MaskingRuleCreate(BaseModel):
    entity_type: str = Field(..., description="实体类型")
    masking_type: MaskingType = Field(..., description="脱敏类型")
    masking_config: Dict[str, Any] = Field(..., description="脱敏配置")
    conditions: List[MaskingCondition] = Field(default_factory=list, description="脱敏条件")

class MaskingRuleResponse(MaskingRuleCreate):
    id: str

class SensitivityPolicyCreate(BaseModel):
    name: str = Field(..., description="策略名称")
    tenant_id: str = Field(..., description="租户ID")
    patterns: List[SensitivityPatternCreate] = Field(default_factory=list, description="敏感数据模式")
    masking_rules: List[MaskingRuleCreate] = Field(default_factory=list, description="脱敏规则")
    is_active: bool = Field(True, description="是否激活")

class SensitivityPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, description="策略名称")
    patterns: Optional[List[SensitivityPatternCreate]] = Field(None, description="敏感数据模式")
    masking_rules: Optional[List[MaskingRuleCreate]] = Field(None, description="脱敏规则")
    is_active: Optional[bool] = Field(None, description="是否激活")

class SensitivityPolicyResponse(BaseModel):
    id: str
    name: str
    tenant_id: str
    patterns: List[Dict[str, Any]]
    masking_rules: List[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PolicyAuditLogResponse(BaseModel):
    id: str
    policy_id: str
    tenant_id: str
    user_id: str
    action: str
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    
    class Config:
        from_attributes = True