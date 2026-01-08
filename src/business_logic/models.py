#!/usr/bin/env python3
"""
业务逻辑数据模型
定义业务规则、模式和洞察的数据库模型

实现需求 13: 客户业务逻辑提炼与智能化
"""

from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from enum import Enum

Base = declarative_base()

class BusinessRuleModel(Base):
    """业务规则数据库模型"""
    __tablename__ = "business_rules"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    pattern = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, default=0.0)
    frequency = Column(Integer, default=0)
    examples = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class BusinessPatternModel(Base):
    """业务模式数据库模型"""
    __tablename__ = "business_patterns"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=False, index=True)
    pattern_type = Column(String(50), nullable=False, index=True)
    description = Column(Text)
    strength = Column(Float, default=0.0)
    evidence = Column(JSON, default=list)
    detected_at = Column(DateTime, default=func.now())
    last_seen = Column(DateTime, default=func.now())

class BusinessInsightModel(Base):
    """业务洞察数据库模型"""
    __tablename__ = "business_insights"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=False, index=True)
    insight_type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    impact_score = Column(Float, default=0.0)
    recommendations = Column(JSON, default=list)
    data_points = Column(JSON, default=list)
    created_at = Column(DateTime, default=func.now())
    acknowledged_at = Column(DateTime, nullable=True)

# Pydantic 模型用于API

class RuleTypeEnum(str, Enum):
    """业务规则类型枚举"""
    SENTIMENT_RULE = "sentiment_rule"
    KEYWORD_RULE = "keyword_rule"
    TEMPORAL_RULE = "temporal_rule"
    BEHAVIORAL_RULE = "behavioral_rule"

class PatternTypeEnum(str, Enum):
    """业务模式类型枚举"""
    SENTIMENT_CORRELATION = "sentiment_correlation"
    KEYWORD_ASSOCIATION = "keyword_association"
    TEMPORAL_TREND = "temporal_trend"
    USER_BEHAVIOR = "user_behavior"

class InsightTypeEnum(str, Enum):
    """业务洞察类型枚举"""
    QUALITY_INSIGHT = "quality_insight"
    EFFICIENCY_INSIGHT = "efficiency_insight"
    PATTERN_INSIGHT = "pattern_insight"
    TREND_INSIGHT = "trend_insight"

class AnnotationExample(BaseModel):
    """标注示例"""
    id: str
    text: str
    annotation: Dict[str, Any]
    timestamp: datetime
    annotator: str

class BusinessRule(BaseModel):
    """业务规则API模型"""
    id: str
    tenant_id: str
    project_id: str
    name: str
    description: Optional[str] = None
    pattern: str
    rule_type: RuleTypeEnum
    confidence: float = 0.0
    frequency: int = 0
    examples: List[AnnotationExample] = []
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BusinessPattern(BaseModel):
    """业务模式API模型"""
    id: str
    tenant_id: str
    project_id: str
    pattern_type: PatternTypeEnum
    description: Optional[str] = None
    strength: float = 0.0
    evidence: List[Dict[str, Any]] = []
    detected_at: datetime
    last_seen: datetime

    class Config:
        from_attributes = True

class BusinessInsight(BaseModel):
    """业务洞察API模型"""
    id: str
    tenant_id: str
    project_id: str
    insight_type: InsightTypeEnum
    title: str
    description: Optional[str] = None
    impact_score: float = 0.0
    recommendations: List[str] = []
    data_points: List[Dict[str, Any]] = []
    created_at: datetime
    acknowledged_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PatternAnalysisRequest(BaseModel):
    """模式分析请求"""
    project_id: str
    confidence_threshold: float = 0.8
    min_frequency: int = 3
    time_range_days: Optional[int] = None

class PatternAnalysisResponse(BaseModel):
    """模式分析响应"""
    project_id: str
    patterns: List[BusinessPattern]
    total_annotations: int
    analysis_timestamp: datetime
    confidence_threshold: float

class RuleExtractionRequest(BaseModel):
    """规则提取请求"""
    project_id: str
    threshold: float = 0.8
    rule_types: Optional[List[RuleTypeEnum]] = None

class RuleExtractionResponse(BaseModel):
    """规则提取响应"""
    project_id: str
    rules: List[BusinessRule]
    extraction_timestamp: datetime
    threshold: float

class RuleApplicationRequest(BaseModel):
    """规则应用请求"""
    source_project_id: str
    target_project_id: str
    rule_ids: List[str]
    apply_mode: str = "copy"  # copy, reference, adapt

class RuleApplicationResponse(BaseModel):
    """规则应用响应"""
    source_project_id: str
    target_project_id: str
    applied_rules: List[BusinessRule]
    application_timestamp: datetime
    success_count: int
    failure_count: int

class BusinessLogicExportRequest(BaseModel):
    """业务逻辑导出请求"""
    project_id: str
    export_format: str = "json"  # json, csv, xml
    include_rules: bool = True
    include_patterns: bool = True
    include_insights: bool = True

class BusinessLogicExportResponse(BaseModel):
    """业务逻辑导出响应"""
    project_id: str
    export_format: str
    download_url: str
    file_size: int
    export_timestamp: datetime
    expires_at: datetime

class VisualizationRequest(BaseModel):
    """可视化请求"""
    project_id: str
    visualization_type: str = "rule_network"  # rule_network, pattern_timeline, insight_dashboard
    time_range_days: Optional[int] = 30

class VisualizationResponse(BaseModel):
    """可视化响应"""
    project_id: str
    visualization_type: str
    chart_data: Dict[str, Any]
    chart_config: Dict[str, Any]
    generation_timestamp: datetime

class ChangeDetectionRequest(BaseModel):
    """变化检测请求"""
    project_id: str
    time_window_days: int = 7
    change_threshold: float = 0.2

class ChangeDetectionResponse(BaseModel):
    """变化检测响应"""
    project_id: str
    changes_detected: List[Dict[str, Any]]
    change_summary: Dict[str, Any]
    detection_timestamp: datetime
    time_window_days: int

class NotificationPreference(BaseModel):
    """通知偏好设置"""
    user_id: str
    project_id: str
    email_enabled: bool = True
    sms_enabled: bool = False
    webhook_url: Optional[str] = None
    notification_types: List[str] = ["new_pattern", "rule_change", "insight_generated"]
    frequency: str = "immediate"  # immediate, daily, weekly

class BusinessLogicStats(BaseModel):
    """业务逻辑统计"""
    project_id: str
    total_rules: int
    active_rules: int
    total_patterns: int
    total_insights: int
    last_analysis: Optional[datetime] = None
    avg_rule_confidence: float = 0.0
    top_pattern_types: List[Dict[str, Any]] = []