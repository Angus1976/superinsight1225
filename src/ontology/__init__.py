"""
企业本体模型模块

提供企业级数据本体管理功能，包括：
- 中国企业特色实体和关系类型
- 本体实体和关系扩展
- 企业本体管理器
- AI 友好型数据转换器
- 合规验证功能

与现有知识图谱模块（src/knowledge_graph/）和数据血缘模块（src/sync/lineage/）深度融合。
"""

from src.ontology.enterprise_ontology import (
    ChineseEntityType,
    ChineseRelationType,
    OntologyEntity,
    OntologyRelation,
    DataLineageNode,
    EnterpriseOntologyManager,
)
from src.ontology.ai_data_converter import (
    AIDataFormat,
    AIDataConverter,
)

__all__ = [
    # 实体类型
    "ChineseEntityType",
    "ChineseRelationType",
    # 本体模型
    "OntologyEntity",
    "OntologyRelation",
    "DataLineageNode",
    # 管理器
    "EnterpriseOntologyManager",
    # AI 数据转换
    "AIDataFormat",
    "AIDataConverter",
]
