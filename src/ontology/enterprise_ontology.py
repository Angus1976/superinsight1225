"""
企业数据本体模型

与现有知识图谱模块融合，提供中国企业特色的本体定义。

Validates: 设计文档 - 本体模型设计
"""

import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from src.knowledge_graph.core.models import (
    Entity, Relation, EntityType, RelationType
)
from src.i18n.translations import get_translation

logger = logging.getLogger(__name__)


# ============================================================================
# 中国企业特色类型定义
# ============================================================================

class ChineseEntityType(str, Enum):
    """
    中国企业特色实体类型扩展
    
    继承基础类型并添加中国企业特有的实体类型
    """
    # 继承基础类型
    PERSON = "person"
    ORGANIZATION = "organization"
    DOCUMENT = "document"
    LOCATION = "location"
    
    # 中国企业特色类型
    DEPARTMENT = "department"          # 部门
    BUSINESS_UNIT = "business_unit"    # 业务单元
    REGULATION = "regulation"          # 法规政策
    CONTRACT = "contract"              # 合同
    APPROVAL = "approval"              # 审批流程
    SEAL = "seal"                      # 印章
    INVOICE = "invoice"                # 发票
    CERTIFICATE = "certificate"        # 资质证书
    BUDGET = "budget"                  # 预算
    PROJECT = "project"                # 项目
    MEETING = "meeting"                # 会议
    POLICY = "policy"                  # 内部政策
    
    @classmethod
    def get_display_name(cls, entity_type: "ChineseEntityType", lang: str = "zh") -> str:
        """获取实体类型的显示名称"""
        names = {
            cls.PERSON: {"zh": "人员", "en": "Person"},
            cls.ORGANIZATION: {"zh": "组织", "en": "Organization"},
            cls.DOCUMENT: {"zh": "文档", "en": "Document"},
            cls.LOCATION: {"zh": "位置", "en": "Location"},
            cls.DEPARTMENT: {"zh": "部门", "en": "Department"},
            cls.BUSINESS_UNIT: {"zh": "业务单元", "en": "Business Unit"},
            cls.REGULATION: {"zh": "法规政策", "en": "Regulation"},
            cls.CONTRACT: {"zh": "合同", "en": "Contract"},
            cls.APPROVAL: {"zh": "审批流程", "en": "Approval"},
            cls.SEAL: {"zh": "印章", "en": "Seal"},
            cls.INVOICE: {"zh": "发票", "en": "Invoice"},
            cls.CERTIFICATE: {"zh": "资质证书", "en": "Certificate"},
            cls.BUDGET: {"zh": "预算", "en": "Budget"},
            cls.PROJECT: {"zh": "项目", "en": "Project"},
            cls.MEETING: {"zh": "会议", "en": "Meeting"},
            cls.POLICY: {"zh": "内部政策", "en": "Policy"},
        }
        return names.get(entity_type, {}).get(lang, entity_type.value)


class ChineseRelationType(str, Enum):
    """
    中国企业特色关系类型扩展
    
    继承基础类型并添加中国企业特有的关系类型
    """
    # 继承基础类型
    BELONGS_TO = "belongs_to"
    CREATED_BY = "created_by"
    RELATED_TO = "related_to"
    
    # 中国企业特色关系
    REPORTS_TO = "reports_to"          # 汇报关系
    APPROVES = "approves"              # 审批关系
    SEALS = "seals"                    # 用印关系
    COMPLIES_WITH = "complies_with"    # 合规关系
    SUPERVISES = "supervises"          # 监管关系
    DELEGATES_TO = "delegates_to"      # 授权关系
    MANAGES = "manages"                # 管理关系
    PARTICIPATES_IN = "participates_in"  # 参与关系
    SIGNS = "signs"                    # 签署关系
    REVIEWS = "reviews"                # 审核关系
    ISSUES = "issues"                  # 开具关系
    HOLDS = "holds"                    # 持有关系
    
    @classmethod
    def get_display_name(cls, relation_type: "ChineseRelationType", lang: str = "zh") -> str:
        """获取关系类型的显示名称"""
        names = {
            cls.BELONGS_TO: {"zh": "属于", "en": "Belongs To"},
            cls.CREATED_BY: {"zh": "创建者", "en": "Created By"},
            cls.RELATED_TO: {"zh": "关联", "en": "Related To"},
            cls.REPORTS_TO: {"zh": "汇报给", "en": "Reports To"},
            cls.APPROVES: {"zh": "审批", "en": "Approves"},
            cls.SEALS: {"zh": "用印", "en": "Seals"},
            cls.COMPLIES_WITH: {"zh": "合规于", "en": "Complies With"},
            cls.SUPERVISES: {"zh": "监管", "en": "Supervises"},
            cls.DELEGATES_TO: {"zh": "授权给", "en": "Delegates To"},
            cls.MANAGES: {"zh": "管理", "en": "Manages"},
            cls.PARTICIPATES_IN: {"zh": "参与", "en": "Participates In"},
            cls.SIGNS: {"zh": "签署", "en": "Signs"},
            cls.REVIEWS: {"zh": "审核", "en": "Reviews"},
            cls.ISSUES: {"zh": "开具", "en": "Issues"},
            cls.HOLDS: {"zh": "持有", "en": "Holds"},
        }
        return names.get(relation_type, {}).get(lang, relation_type.value)


# ============================================================================
# 数据分类等级
# ============================================================================

class DataClassification(str, Enum):
    """数据分类等级（符合中国数据安全法）"""
    PUBLIC = "public"              # 公开数据
    INTERNAL = "internal"          # 内部数据
    CONFIDENTIAL = "confidential"  # 机密数据
    SECRET = "secret"              # 秘密数据
    TOP_SECRET = "top_secret"      # 绝密数据
    
    @classmethod
    def get_display_name(cls, classification: "DataClassification", lang: str = "zh") -> str:
        """获取分类等级的显示名称"""
        names = {
            cls.PUBLIC: {"zh": "公开", "en": "Public"},
            cls.INTERNAL: {"zh": "内部", "en": "Internal"},
            cls.CONFIDENTIAL: {"zh": "机密", "en": "Confidential"},
            cls.SECRET: {"zh": "秘密", "en": "Secret"},
            cls.TOP_SECRET: {"zh": "绝密", "en": "Top Secret"},
        }
        return names.get(classification, {}).get(lang, classification.value)


class SensitivityLevel(str, Enum):
    """敏感度等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    @classmethod
    def get_display_name(cls, level: "SensitivityLevel", lang: str = "zh") -> str:
        """获取敏感度等级的显示名称"""
        names = {
            cls.LOW: {"zh": "低", "en": "Low"},
            cls.MEDIUM: {"zh": "中", "en": "Medium"},
            cls.HIGH: {"zh": "高", "en": "High"},
            cls.CRITICAL: {"zh": "极高", "en": "Critical"},
        }
        return names.get(level, {}).get(lang, level.value)


# ============================================================================
# 本体实体模型
# ============================================================================

class OntologyEntity(BaseModel):
    """
    本体实体 - 扩展知识图谱 Entity
    
    增加中文语义和业务属性，支持中国企业数据治理需求
    """
    # 基础属性
    id: UUID = Field(default_factory=uuid4, description="实体唯一ID")
    entity_type: ChineseEntityType = Field(..., description="实体类型")
    name: str = Field(..., min_length=1, description="实体名称")
    properties: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    description: Optional[str] = Field(None, description="实体描述")
    
    # 中文语义
    name_zh: str = Field(..., description="中文名称")
    description_zh: Optional[str] = Field(None, description="中文描述")
    aliases_zh: List[str] = Field(default_factory=list, description="中文别名")
    
    # 业务分类
    business_domain: Optional[str] = Field(None, description="业务领域")
    data_classification: Optional[DataClassification] = Field(None, description="数据分类等级")
    sensitivity_level: Optional[SensitivityLevel] = Field(None, description="敏感度等级")
    
    # 合规属性
    retention_period_days: Optional[int] = Field(None, description="保留期限（天）")
    cross_border_allowed: bool = Field(default=True, description="是否允许跨境传输")
    pii_fields: List[str] = Field(default_factory=list, description="个人信息字段")
    
    # 数据血缘
    lineage_id: Optional[str] = Field(None, description="血缘追踪ID")
    upstream_sources: List[str] = Field(default_factory=list, description="上游数据源")
    downstream_targets: List[str] = Field(default_factory=list, description="下游目标")
    
    # 质量指标
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    verified: bool = Field(default=False, description="是否已验证")
    
    # 多租户
    tenant_id: Optional[str] = Field(None, description="租户ID")
    
    # 审计
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_by: Optional[str] = Field(None, description="创建者")
    updated_by: Optional[str] = Field(None, description="更新者")
    version: int = Field(default=1, ge=1, description="版本号")
    is_active: bool = Field(default=True, description="是否激活")
    
    def to_knowledge_graph_entity(self) -> Entity:
        """转换为知识图谱实体"""
        # 映射实体类型
        try:
            kg_entity_type = EntityType(self.entity_type.value)
        except ValueError:
            kg_entity_type = EntityType.CUSTOM
        
        return Entity(
            id=self.id,
            entity_type=kg_entity_type,
            name=self.name,
            properties={
                **self.properties,
                "name_zh": self.name_zh,
                "description_zh": self.description_zh,
                "business_domain": self.business_domain,
                "data_classification": self.data_classification.value if self.data_classification else None,
                "sensitivity_level": self.sensitivity_level.value if self.sensitivity_level else None,
                "cross_border_allowed": self.cross_border_allowed,
                "pii_fields": self.pii_fields,
            },
            aliases=self.aliases + self.aliases_zh,
            description=self.description,
            confidence=self.confidence,
            verified=self.verified,
            tenant_id=self.tenant_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            created_by=self.created_by,
            updated_by=self.updated_by,
            version=self.version,
            is_active=self.is_active,
        )
    
    @classmethod
    def from_knowledge_graph_entity(cls, entity: Entity, name_zh: str) -> "OntologyEntity":
        """从知识图谱实体创建本体实体"""
        # 映射实体类型
        try:
            entity_type = ChineseEntityType(entity.entity_type.value)
        except ValueError:
            entity_type = ChineseEntityType.DOCUMENT
        
        return cls(
            id=entity.id,
            entity_type=entity_type,
            name=entity.name,
            name_zh=name_zh,
            properties=entity.properties,
            aliases=entity.aliases,
            description=entity.description,
            description_zh=entity.properties.get("description_zh"),
            confidence=entity.confidence,
            verified=entity.verified,
            tenant_id=entity.tenant_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
            is_active=entity.is_active,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "name_zh": self.name_zh,
            "description": self.description,
            "description_zh": self.description_zh,
            "properties": self.properties,
            "aliases": self.aliases,
            "aliases_zh": self.aliases_zh,
            "business_domain": self.business_domain,
            "data_classification": self.data_classification.value if self.data_classification else None,
            "sensitivity_level": self.sensitivity_level.value if self.sensitivity_level else None,
            "retention_period_days": self.retention_period_days,
            "cross_border_allowed": self.cross_border_allowed,
            "pii_fields": self.pii_fields,
            "lineage_id": self.lineage_id,
            "upstream_sources": self.upstream_sources,
            "downstream_targets": self.downstream_targets,
            "confidence": self.confidence,
            "verified": self.verified,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "version": self.version,
            "is_active": self.is_active,
        }


# ============================================================================
# 本体关系模型
# ============================================================================

class OntologyRelation(BaseModel):
    """
    本体关系 - 扩展知识图谱 Relation
    
    增加业务语义和合规属性
    """
    # 基础属性
    id: UUID = Field(default_factory=uuid4, description="关系唯一ID")
    source_id: UUID = Field(..., description="源实体ID")
    target_id: UUID = Field(..., description="目标实体ID")
    relation_type: ChineseRelationType = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")
    
    # 中文语义
    name_zh: Optional[str] = Field(None, description="关系中文名称")
    description_zh: Optional[str] = Field(None, description="关系中文描述")
    
    # 业务属性
    business_rule: Optional[str] = Field(None, description="关联的业务规则")
    approval_required: bool = Field(default=False, description="是否需要审批")
    audit_required: bool = Field(default=True, description="是否需要审计")
    
    # 时效性
    effective_date: Optional[datetime] = Field(None, description="生效日期")
    expiry_date: Optional[datetime] = Field(None, description="失效日期")
    
    # 质量指标
    weight: float = Field(default=1.0, ge=0.0, description="关系权重")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    verified: bool = Field(default=False, description="是否已验证")
    evidence: Optional[str] = Field(None, description="证据文本")
    
    # 多租户
    tenant_id: Optional[str] = Field(None, description="租户ID")
    
    # 审计
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_by: Optional[str] = Field(None, description="创建者")
    version: int = Field(default=1, ge=1, description="版本号")
    is_active: bool = Field(default=True, description="是否激活")
    
    def to_knowledge_graph_relation(self) -> Relation:
        """转换为知识图谱关系"""
        # 映射关系类型
        try:
            kg_relation_type = RelationType(self.relation_type.value)
        except ValueError:
            kg_relation_type = RelationType.CUSTOM
        
        return Relation(
            id=self.id,
            source_id=self.source_id,
            target_id=self.target_id,
            relation_type=kg_relation_type,
            properties={
                **self.properties,
                "name_zh": self.name_zh,
                "description_zh": self.description_zh,
                "business_rule": self.business_rule,
                "approval_required": self.approval_required,
                "audit_required": self.audit_required,
            },
            weight=self.weight,
            confidence=self.confidence,
            verified=self.verified,
            evidence=self.evidence,
            valid_from=self.effective_date,
            valid_to=self.expiry_date,
            tenant_id=self.tenant_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            created_by=self.created_by,
            version=self.version,
            is_active=self.is_active,
        )
    
    def is_valid(self) -> bool:
        """检查关系是否在有效期内"""
        now = datetime.now()
        if self.effective_date and now < self.effective_date:
            return False
        if self.expiry_date and now > self.expiry_date:
            return False
        return self.is_active
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "relation_type": self.relation_type.value,
            "name_zh": self.name_zh,
            "description_zh": self.description_zh,
            "properties": self.properties,
            "business_rule": self.business_rule,
            "approval_required": self.approval_required,
            "audit_required": self.audit_required,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "weight": self.weight,
            "confidence": self.confidence,
            "verified": self.verified,
            "evidence": self.evidence,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "version": self.version,
            "is_active": self.is_active,
        }


# ============================================================================
# 数据血缘节点
# ============================================================================

class DataLineageNode(BaseModel):
    """
    数据血缘节点 - 与 LineageTracker 集成
    """
    id: UUID = Field(default_factory=uuid4, description="节点唯一ID")
    entity_id: UUID = Field(..., description="关联的本体实体ID")
    node_type: str = Field(..., description="节点类型: source/transform/target")
    
    # 数据源信息
    source_system: Optional[str] = Field(None, description="源系统")
    source_table: Optional[str] = Field(None, description="源表")
    source_column: Optional[str] = Field(None, description="源字段")
    
    # 转换信息
    transformation_type: Optional[str] = Field(None, description="转换类型")
    transformation_logic: Optional[str] = Field(None, description="转换逻辑")
    
    # 质量信息
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="数据质量分数")
    last_quality_check: Optional[datetime] = Field(None, description="最后质量检查时间")
    
    # 审计信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    created_by: Optional[str] = Field(None, description="创建者")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "entity_id": str(self.entity_id),
            "node_type": self.node_type,
            "source_system": self.source_system,
            "source_table": self.source_table,
            "source_column": self.source_column,
            "transformation_type": self.transformation_type,
            "transformation_logic": self.transformation_logic,
            "quality_score": self.quality_score,
            "last_quality_check": self.last_quality_check.isoformat() if self.last_quality_check else None,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }


# ============================================================================
# 合规验证结果
# ============================================================================

class ComplianceIssue(BaseModel):
    """合规问题"""
    issue_type: str = Field(..., description="问题类型")
    message: str = Field(..., description="问题描述")
    message_zh: str = Field(..., description="问题中文描述")
    severity: str = Field(..., description="严重程度: warning/error")
    field: Optional[str] = Field(None, description="相关字段")
    suggestion: Optional[str] = Field(None, description="建议")
    suggestion_zh: Optional[str] = Field(None, description="中文建议")


class ComplianceResult(BaseModel):
    """合规验证结果"""
    entity_id: str = Field(..., description="实体ID")
    compliant: bool = Field(..., description="是否合规")
    issues: List[ComplianceIssue] = Field(default_factory=list, description="问题列表")
    checked_at: datetime = Field(default_factory=datetime.now, description="检查时间")
    
    @property
    def error_count(self) -> int:
        """错误数量"""
        return len([i for i in self.issues if i.severity == "error"])
    
    @property
    def warning_count(self) -> int:
        """警告数量"""
        return len([i for i in self.issues if i.severity == "warning"])


# ============================================================================
# 企业本体管理器
# ============================================================================

class EnterpriseOntologyManager:
    """
    企业本体管理器 - 统一管理本体模型
    
    集成知识图谱数据库和数据血缘追踪器
    """
    
    # 跨境目标关键词
    CROSS_BORDER_KEYWORDS = ["aws", "azure", "gcp", "overseas", "foreign", "海外", "境外"]
    
    def __init__(
        self,
        knowledge_graph_db=None,
        lineage_tracker=None,
    ):
        """
        初始化企业本体管理器
        
        Args:
            knowledge_graph_db: Neo4j 数据库连接（可选）
            lineage_tracker: 血缘追踪器（可选）
        """
        self.kg_db = knowledge_graph_db
        self.lineage_tracker = lineage_tracker
        self._entity_cache: Dict[UUID, OntologyEntity] = {}
        self._relation_cache: Dict[UUID, OntologyRelation] = {}
        logger.info(get_translation("ontology.manager.initialized", "zh"))
    
    async def create_entity(
        self,
        entity: OntologyEntity,
        track_lineage: bool = True
    ) -> OntologyEntity:
        """
        创建本体实体
        
        同时更新知识图谱和血缘追踪
        
        Args:
            entity: 本体实体
            track_lineage: 是否追踪血缘
            
        Returns:
            创建的实体
        """
        # 保存到知识图谱
        if self.kg_db:
            kg_entity = entity.to_knowledge_graph_entity()
            await self.kg_db.create_entity(kg_entity)
        
        # 追踪血缘
        if track_lineage and self.lineage_tracker and entity.upstream_sources:
            lineage_node = DataLineageNode(
                entity_id=entity.id,
                node_type="transform",
                source_system=entity.upstream_sources[0] if entity.upstream_sources else None,
            )
            # 记录血缘
            for source in entity.upstream_sources:
                self.lineage_tracker.add_data_flow(
                    source_node_id=source,
                    target_node_id=str(entity.id),
                    transformation_rule="ontology_mapping"
                )
        
        # 缓存实体
        self._entity_cache[entity.id] = entity
        
        logger.info(
            f"Created ontology entity: {entity.name_zh} ({entity.entity_type.value})"
        )
        
        return entity
    
    async def get_entity(self, entity_id: UUID) -> Optional[OntologyEntity]:
        """获取实体"""
        # 先检查缓存
        if entity_id in self._entity_cache:
            return self._entity_cache[entity_id]
        
        # 从知识图谱获取
        if self.kg_db:
            kg_entity = await self.kg_db.get_entity(entity_id)
            if kg_entity:
                # 转换为本体实体
                name_zh = kg_entity.properties.get("name_zh", kg_entity.name)
                entity = OntologyEntity.from_knowledge_graph_entity(kg_entity, name_zh)
                self._entity_cache[entity_id] = entity
                return entity
        
        return None
    
    async def update_entity(
        self,
        entity_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[OntologyEntity]:
        """更新实体"""
        entity = await self.get_entity(entity_id)
        if not entity:
            return None
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        entity.updated_at = datetime.now()
        entity.version += 1
        
        # 更新知识图谱
        if self.kg_db:
            kg_entity = entity.to_knowledge_graph_entity()
            await self.kg_db.update_entity(kg_entity)
        
        # 更新缓存
        self._entity_cache[entity_id] = entity
        
        return entity
    
    async def delete_entity(self, entity_id: UUID) -> bool:
        """删除实体"""
        # 从知识图谱删除
        if self.kg_db:
            await self.kg_db.delete_entity(entity_id)
        
        # 从缓存删除
        if entity_id in self._entity_cache:
            del self._entity_cache[entity_id]
        
        return True
    
    async def create_relation(
        self,
        relation: OntologyRelation,
        audit_log: bool = True
    ) -> OntologyRelation:
        """
        创建本体关系
        
        支持审计日志
        
        Args:
            relation: 本体关系
            audit_log: 是否记录审计日志
            
        Returns:
            创建的关系
        """
        # 保存到知识图谱
        if self.kg_db:
            kg_relation = relation.to_knowledge_graph_relation()
            await self.kg_db.create_relation(kg_relation)
        
        # 审计日志
        if audit_log and relation.audit_required:
            logger.info(
                f"Audit: Created relation {relation.relation_type.value} "
                f"from {relation.source_id} to {relation.target_id}"
            )
        
        # 缓存关系
        self._relation_cache[relation.id] = relation
        
        return relation
    
    async def get_entity_lineage(
        self,
        entity_id: UUID,
        direction: str = "both",
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        获取实体的完整数据血缘
        
        Args:
            entity_id: 实体ID
            direction: 方向 (upstream/downstream/both)
            max_depth: 最大深度
            
        Returns:
            血缘信息
        """
        if not self.lineage_tracker:
            return {
                "entity_id": str(entity_id),
                "direction": direction,
                "lineage": [],
                "error": "Lineage tracker not configured"
            }
        
        result = {
            "entity_id": str(entity_id),
            "direction": direction,
            "upstream": [],
            "downstream": [],
        }
        
        node_id = str(entity_id)
        
        if direction in ("upstream", "both"):
            upstream = self.lineage_tracker.graph.get_upstream(node_id, max_depth)
            result["upstream"] = [n.to_dict() for n in upstream]
        
        if direction in ("downstream", "both"):
            downstream = self.lineage_tracker.graph.get_downstream(node_id, max_depth)
            result["downstream"] = [n.to_dict() for n in downstream]
        
        return result
    
    async def validate_compliance(
        self,
        entity: OntologyEntity
    ) -> ComplianceResult:
        """
        验证实体的合规性
        
        检查数据分类、跨境传输、个人信息保护等
        
        Args:
            entity: 本体实体
            
        Returns:
            合规验证结果
        """
        issues: List[ComplianceIssue] = []
        
        # 检查数据分类
        if not entity.data_classification:
            issues.append(ComplianceIssue(
                issue_type="missing_classification",
                message="Missing data classification level",
                message_zh="缺少数据分类等级",
                severity="warning",
                suggestion="Please set data classification level",
                suggestion_zh="请设置数据分类等级"
            ))
        
        # 检查跨境传输
        if not entity.cross_border_allowed and entity.downstream_targets:
            for target in entity.downstream_targets:
                if self._is_cross_border_target(target):
                    issues.append(ComplianceIssue(
                        issue_type="cross_border_violation",
                        message=f"Data not allowed for cross-border transfer to {target}",
                        message_zh=f"数据不允许跨境传输到 {target}",
                        severity="error",
                        field="downstream_targets",
                        suggestion="Remove cross-border target or enable cross-border transfer",
                        suggestion_zh="移除跨境目标或启用跨境传输"
                    ))
        
        # 检查个人信息保护
        if entity.pii_fields:
            if entity.sensitivity_level not in (SensitivityLevel.HIGH, SensitivityLevel.CRITICAL):
                issues.append(ComplianceIssue(
                    issue_type="pii_sensitivity_mismatch",
                    message="Entity contains PII but sensitivity level is not high",
                    message_zh="实体包含个人信息但敏感度等级不是高",
                    severity="warning",
                    field="sensitivity_level",
                    suggestion="Set sensitivity level to HIGH or CRITICAL",
                    suggestion_zh="将敏感度等级设置为高或极高"
                ))
            
            # 检查数据分类是否足够
            if entity.data_classification in (DataClassification.PUBLIC, DataClassification.INTERNAL):
                issues.append(ComplianceIssue(
                    issue_type="pii_classification_mismatch",
                    message="Entity contains PII but data classification is too low",
                    message_zh="实体包含个人信息但数据分类等级过低",
                    severity="error",
                    field="data_classification",
                    suggestion="Set data classification to CONFIDENTIAL or higher",
                    suggestion_zh="将数据分类设置为机密或更高"
                ))
        
        # 检查保留期限
        if entity.pii_fields and not entity.retention_period_days:
            issues.append(ComplianceIssue(
                issue_type="missing_retention_period",
                message="Entity contains PII but no retention period is set",
                message_zh="实体包含个人信息但未设置保留期限",
                severity="warning",
                field="retention_period_days",
                suggestion="Set a retention period for PII data",
                suggestion_zh="为个人信息数据设置保留期限"
            ))
        
        # 判断是否合规
        error_count = len([i for i in issues if i.severity == "error"])
        compliant = error_count == 0
        
        return ComplianceResult(
            entity_id=str(entity.id),
            compliant=compliant,
            issues=issues
        )
    
    def _is_cross_border_target(self, target: str) -> bool:
        """检查目标是否为跨境"""
        target_lower = target.lower()
        return any(kw in target_lower for kw in self.CROSS_BORDER_KEYWORDS)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "cached_entities": len(self._entity_cache),
            "cached_relations": len(self._relation_cache),
            "kg_connected": self.kg_db is not None,
            "lineage_connected": self.lineage_tracker is not None,
        }
    
    def clear_cache(self):
        """清除缓存"""
        self._entity_cache.clear()
        self._relation_cache.clear()
        logger.info("Ontology cache cleared")
