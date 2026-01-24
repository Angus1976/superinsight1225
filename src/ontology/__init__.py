"""
企业本体模型模块

提供企业级数据本体管理功能，包括：
- 中国企业特色实体和关系类型
- 本体实体和关系扩展
- 企业本体管理器
- AI 友好型数据转换器
- 合规验证功能
- 专家协作集成

与现有知识图谱模块（src/knowledge_graph/）和数据血缘模块（src/sync/lineage/）深度融合。
"""

from src.ontology.enterprise_ontology import (
    ChineseEntityType,
    ChineseRelationType,
    OntologyEntity,
    OntologyRelation,
    DataLineageNode,
    EnterpriseOntologyManager,
    DataClassification,
    SensitivityLevel,
    ComplianceResult,
    ComplianceIssue,
)
from src.ontology.ai_data_converter import (
    AIDataFormat,
    AIDataConverter,
)
from src.ontology.expert_collaboration_integration import (
    ExpertCollaborationOntologyManager,
    create_expert_collaboration_manager,
)

__all__ = [
    # 实体类型
    "ChineseEntityType",
    "ChineseRelationType",
    # 本体模型
    "OntologyEntity",
    "OntologyRelation",
    "DataLineageNode",
    # 数据分类
    "DataClassification",
    "SensitivityLevel",
    # 合规
    "ComplianceResult",
    "ComplianceIssue",
    # 管理器
    "EnterpriseOntologyManager",
    # 专家协作集成
    "ExpertCollaborationOntologyManager",
    "create_expert_collaboration_manager",
    # AI 数据转换
    "AIDataFormat",
    "AIDataConverter",
]
