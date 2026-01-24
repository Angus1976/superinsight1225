"""
知识图谱协作集成模块

将专家协作服务与知识图谱数据库集成，提供：
- 本体元素存储到 Neo4j
- 依赖关系图查询
- 影响分析图遍历
- PostgreSQL 和 Neo4j 同步

Validates: Task 27.2 - Integrate with knowledge graph
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from uuid import UUID, uuid4

from src.knowledge_graph.core.graph_db import GraphDatabase, get_graph_database
from src.knowledge_graph.core.models import (
    Entity,
    Relation,
    EntityType,
    RelationType,
    GraphQueryResult,
)
from src.collaboration.impact_analysis_service import ImpactAnalysisService

logger = logging.getLogger(__name__)


class CollaborationGraphIntegration:
    """
    协作知识图谱集成
    
    提供专家协作与知识图谱的双向集成：
    - 将本体元素同步到 Neo4j
    - 从 Neo4j 查询依赖关系
    - 支持影响分析的图遍历
    """
    
    # 本体元素类型到知识图谱实体类型的映射
    ONTOLOGY_TO_KG_TYPE = {
        "entity_type": EntityType.CONCEPT,
        "relation_type": EntityType.CONCEPT,
        "attribute": EntityType.CONCEPT,
        "validation_rule": EntityType.DOCUMENT,
        "template": EntityType.DOCUMENT,
        "expert": EntityType.PERSON,
        "project": EntityType.PROJECT,
    }
    
    # 本体关系类型到知识图谱关系类型的映射
    ONTOLOGY_TO_KG_RELATION = {
        "DEPENDS_ON": RelationType.DERIVED_FROM,
        "USED_BY": RelationType.REFERENCES,
        "CONNECTS": RelationType.RELATED_TO,
        "CONTRIBUTED_BY": RelationType.CREATED_BY,
        "DERIVED_FROM": RelationType.DERIVED_FROM,
        "PART_OF": RelationType.PART_OF,
    }
    
    def __init__(
        self,
        graph_db: Optional[GraphDatabase] = None,
        impact_service: Optional[ImpactAnalysisService] = None,
    ):
        """
        初始化协作图谱集成
        
        Args:
            graph_db: Neo4j 数据库连接
            impact_service: 影响分析服务
        """
        self._graph_db = graph_db
        self._impact_service = impact_service or ImpactAnalysisService()
        self._lock = asyncio.Lock()
        self._initialized = False
        
        logger.info("CollaborationGraphIntegration initialized")
    
    async def initialize(self) -> None:
        """初始化图数据库连接"""
        if self._initialized:
            return
        
        if not self._graph_db:
            self._graph_db = get_graph_database()
        
        try:
            await self._graph_db.initialize()
            await self._create_collaboration_indexes()
            self._initialized = True
            logger.info("CollaborationGraphIntegration connected to Neo4j")
        except Exception as e:
            logger.warning(f"Failed to initialize Neo4j connection: {e}")
            # 继续运行，使用内存模式
    
    async def _create_collaboration_indexes(self) -> None:
        """创建协作相关的索引"""
        if not self._graph_db:
            return
        
        try:
            # 本体元素索引
            await self._graph_db.execute_cypher(
                "CREATE INDEX ontology_element_id IF NOT EXISTS FOR (e:OntologyElement) ON (e.element_id)"
            )
            await self._graph_db.execute_cypher(
                "CREATE INDEX ontology_element_type IF NOT EXISTS FOR (e:OntologyElement) ON (e.element_type)"
            )
            await self._graph_db.execute_cypher(
                "CREATE INDEX ontology_element_ontology IF NOT EXISTS FOR (e:OntologyElement) ON (e.ontology_id)"
            )
            
            # 专家索引
            await self._graph_db.execute_cypher(
                "CREATE INDEX expert_id IF NOT EXISTS FOR (e:Expert) ON (e.expert_id)"
            )
            
            # 模板索引
            await self._graph_db.execute_cypher(
                "CREATE INDEX template_id IF NOT EXISTS FOR (t:Template) ON (t.template_id)"
            )
            
            logger.info("Created collaboration indexes in Neo4j")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    # ========================================================================
    # 本体元素同步
    # ========================================================================
    
    async def sync_ontology_element(
        self,
        ontology_id: str,
        element_id: str,
        element_type: str,
        element_data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> Optional[str]:
        """
        同步本体元素到知识图谱
        
        Args:
            ontology_id: 本体ID
            element_id: 元素ID
            element_type: 元素类型 (entity_type/relation_type/attribute)
            element_data: 元素数据
            created_by: 创建者ID
            
        Returns:
            Neo4j 节点ID
        """
        if not self._graph_db or not self._initialized:
            logger.debug("Neo4j not available, skipping sync")
            return None
        
        async with self._lock:
            try:
                # 映射实体类型
                kg_type = self.ONTOLOGY_TO_KG_TYPE.get(element_type, EntityType.CONCEPT)
                
                # 创建实体
                entity = Entity(
                    id=uuid4(),
                    entity_type=kg_type,
                    name=element_data.get("name", element_id),
                    properties={
                        "ontology_id": ontology_id,
                        "element_id": element_id,
                        "element_type": element_type,
                        "name_zh": element_data.get("name_zh", ""),
                        "description": element_data.get("description", ""),
                        "is_core": element_data.get("is_core", False),
                        **{k: v for k, v in element_data.items() 
                           if k not in ("name", "name_zh", "description", "is_core")
                           and isinstance(v, (str, int, float, bool))},
                    },
                    description=element_data.get("description"),
                    created_by=created_by,
                    source="ontology_collaboration",
                )
                
                # 检查是否已存在
                existing = await self._find_ontology_element(ontology_id, element_id)
                if existing:
                    # 更新现有节点
                    await self._graph_db.update_entity(
                        existing.id,
                        {
                            "name": entity.name,
                            "description": entity.description,
                            **entity.properties,
                        }
                    )
                    return str(existing.id)
                else:
                    # 创建新节点
                    created = await self._graph_db.create_entity(entity)
                    return str(created.id)
                    
            except Exception as e:
                logger.error(f"Failed to sync ontology element: {e}")
                return None
    
    async def _find_ontology_element(
        self,
        ontology_id: str,
        element_id: str,
    ) -> Optional[Entity]:
        """查找本体元素"""
        if not self._graph_db:
            return None
        
        try:
            results = await self._graph_db.execute_cypher(
                """
                MATCH (e:Entity)
                WHERE e.prop_ontology_id = $ontology_id AND e.prop_element_id = $element_id
                RETURN e
                LIMIT 1
                """,
                {"ontology_id": ontology_id, "element_id": element_id}
            )
            
            if results:
                return self._graph_db._record_to_entity(results[0]["e"])
        except Exception as e:
            logger.warning(f"Failed to find ontology element: {e}")
        
        return None
    
    async def sync_ontology_relation(
        self,
        ontology_id: str,
        source_element_id: str,
        target_element_id: str,
        relation_type: str,
        relation_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        同步本体关系到知识图谱
        
        Args:
            ontology_id: 本体ID
            source_element_id: 源元素ID
            target_element_id: 目标元素ID
            relation_type: 关系类型
            relation_data: 关系数据
            
        Returns:
            Neo4j 关系ID
        """
        if not self._graph_db or not self._initialized:
            return None
        
        async with self._lock:
            try:
                # 查找源和目标节点
                source = await self._find_ontology_element(ontology_id, source_element_id)
                target = await self._find_ontology_element(ontology_id, target_element_id)
                
                if not source or not target:
                    logger.warning(f"Source or target not found for relation: {source_element_id} -> {target_element_id}")
                    return None
                
                # 映射关系类型
                kg_relation_type = self.ONTOLOGY_TO_KG_RELATION.get(
                    relation_type, RelationType.RELATED_TO
                )
                
                # 创建关系
                relation = Relation(
                    id=uuid4(),
                    source_id=source.id,
                    target_id=target.id,
                    relation_type=kg_relation_type,
                    properties={
                        "ontology_id": ontology_id,
                        "original_type": relation_type,
                        **(relation_data or {}),
                    },
                    source="ontology_collaboration",
                )
                
                created = await self._graph_db.create_relation(relation)
                return str(created.id)
                
            except Exception as e:
                logger.error(f"Failed to sync ontology relation: {e}")
                return None
    
    # ========================================================================
    # 依赖关系查询
    # ========================================================================
    
    async def get_element_dependencies(
        self,
        ontology_id: str,
        element_id: str,
        direction: str = "both",
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        获取元素的依赖关系
        
        Args:
            ontology_id: 本体ID
            element_id: 元素ID
            direction: 方向 (upstream/downstream/both)
            max_depth: 最大深度
            
        Returns:
            依赖关系信息
        """
        # 首先尝试从 Neo4j 获取
        if self._graph_db and self._initialized:
            try:
                element = await self._find_ontology_element(ontology_id, element_id)
                if element:
                    result = await self._graph_db.get_neighbors(
                        entity_id=element.id,
                        depth=max_depth,
                        limit=100,
                    )
                    
                    return {
                        "element_id": element_id,
                        "ontology_id": ontology_id,
                        "direction": direction,
                        "dependencies": [
                            {
                                "id": str(e.id),
                                "name": e.name,
                                "type": e.properties.get("element_type", "unknown"),
                                "element_id": e.properties.get("element_id"),
                            }
                            for e in result.entities
                        ],
                        "total_count": result.total_count,
                        "source": "neo4j",
                    }
            except Exception as e:
                logger.warning(f"Failed to get dependencies from Neo4j: {e}")
        
        # 回退到影响分析服务的内存图
        impact_result = await self._impact_service.analyze_change(
            ontology_id=ontology_id,
            element_id=element_id,
            change_type="MODIFY",
        )
        
        return {
            "element_id": element_id,
            "ontology_id": ontology_id,
            "direction": direction,
            "dependencies": impact_result.get("affected_elements", []) if impact_result else [],
            "total_count": impact_result.get("affected_entity_count", 0) if impact_result else 0,
            "source": "memory",
        }
    
    async def find_path_between_elements(
        self,
        ontology_id: str,
        source_element_id: str,
        target_element_id: str,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """
        查找两个元素之间的路径
        
        Args:
            ontology_id: 本体ID
            source_element_id: 源元素ID
            target_element_id: 目标元素ID
            max_depth: 最大路径长度
            
        Returns:
            路径信息
        """
        if not self._graph_db or not self._initialized:
            return {
                "source": source_element_id,
                "target": target_element_id,
                "paths": [],
                "error": "Neo4j not available",
            }
        
        try:
            source = await self._find_ontology_element(ontology_id, source_element_id)
            target = await self._find_ontology_element(ontology_id, target_element_id)
            
            if not source or not target:
                return {
                    "source": source_element_id,
                    "target": target_element_id,
                    "paths": [],
                    "error": "Source or target not found",
                }
            
            result = await self._graph_db.find_path(
                source_id=source.id,
                target_id=target.id,
                max_depth=max_depth,
            )
            
            return {
                "source": source_element_id,
                "target": target_element_id,
                "paths": result.paths,
                "query_time_ms": result.query_time_ms,
            }
            
        except Exception as e:
            logger.error(f"Failed to find path: {e}")
            return {
                "source": source_element_id,
                "target": target_element_id,
                "paths": [],
                "error": str(e),
            }
    
    # ========================================================================
    # 影响分析图遍历
    # ========================================================================
    
    async def analyze_change_impact_with_graph(
        self,
        ontology_id: str,
        element_id: str,
        change_type: str,
        proposed_changes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        使用知识图谱进行影响分析
        
        结合 Neo4j 图遍历和内存影响分析
        
        Args:
            ontology_id: 本体ID
            element_id: 元素ID
            change_type: 变更类型
            proposed_changes: 提议的变更
            
        Returns:
            影响分析报告
        """
        # 基础影响分析
        base_analysis = await self._impact_service.analyze_change(
            ontology_id=ontology_id,
            element_id=element_id,
            change_type=change_type,
            proposed_changes=proposed_changes,
        )
        
        # 如果 Neo4j 可用，增强分析
        if self._graph_db and self._initialized:
            try:
                element = await self._find_ontology_element(ontology_id, element_id)
                if element:
                    # 获取图中的依赖
                    neighbors = await self._graph_db.get_neighbors(
                        entity_id=element.id,
                        depth=3,
                        limit=200,
                    )
                    
                    # 增强报告
                    if base_analysis:
                        base_analysis["graph_analysis"] = {
                            "total_connected_elements": neighbors.total_count,
                            "query_time_ms": neighbors.query_time_ms,
                            "connected_elements": [
                                {
                                    "id": str(e.id),
                                    "name": e.name,
                                    "type": e.properties.get("element_type"),
                                }
                                for e in neighbors.entities[:20]  # 限制返回数量
                            ],
                        }
            except Exception as e:
                logger.warning(f"Failed to enhance impact analysis with graph: {e}")
        
        return base_analysis or {}
    
    # ========================================================================
    # 同步管理
    # ========================================================================
    
    async def sync_ontology_to_graph(
        self,
        ontology_id: str,
        ontology_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        将完整本体同步到知识图谱
        
        Args:
            ontology_id: 本体ID
            ontology_data: 本体数据（包含实体类型、关系类型等）
            
        Returns:
            同步结果
        """
        if not self._graph_db or not self._initialized:
            return {
                "success": False,
                "error": "Neo4j not available",
                "synced_elements": 0,
                "synced_relations": 0,
            }
        
        synced_elements = 0
        synced_relations = 0
        errors = []
        
        # 同步实体类型
        for entity_type in ontology_data.get("entity_types", []):
            try:
                await self.sync_ontology_element(
                    ontology_id=ontology_id,
                    element_id=entity_type.get("id", str(uuid4())),
                    element_type="entity_type",
                    element_data=entity_type,
                )
                synced_elements += 1
            except Exception as e:
                errors.append(f"Entity type sync error: {e}")
        
        # 同步关系类型
        for relation_type in ontology_data.get("relation_types", []):
            try:
                await self.sync_ontology_element(
                    ontology_id=ontology_id,
                    element_id=relation_type.get("id", str(uuid4())),
                    element_type="relation_type",
                    element_data=relation_type,
                )
                synced_elements += 1
                
                # 同步关系连接
                source_type = relation_type.get("source_type")
                target_type = relation_type.get("target_type")
                if source_type and target_type:
                    await self.sync_ontology_relation(
                        ontology_id=ontology_id,
                        source_element_id=source_type,
                        target_element_id=target_type,
                        relation_type="CONNECTS",
                        relation_data={"relation_name": relation_type.get("name")},
                    )
                    synced_relations += 1
            except Exception as e:
                errors.append(f"Relation type sync error: {e}")
        
        return {
            "success": len(errors) == 0,
            "ontology_id": ontology_id,
            "synced_elements": synced_elements,
            "synced_relations": synced_relations,
            "errors": errors,
        }
    
    async def get_graph_statistics(
        self,
        ontology_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取图统计信息
        
        Args:
            ontology_id: 可选的本体ID过滤
            
        Returns:
            统计信息
        """
        if not self._graph_db or not self._initialized:
            return {
                "available": False,
                "error": "Neo4j not available",
            }
        
        try:
            stats = await self._graph_db.get_statistics()
            
            result = {
                "available": True,
                "total_entities": stats.total_entities,
                "total_relations": stats.total_relations,
                "entities_by_type": stats.entities_by_type,
                "relations_by_type": stats.relations_by_type,
                "avg_degree": stats.avg_degree,
                "density": stats.density,
            }
            
            # 如果指定了本体ID，获取该本体的统计
            if ontology_id:
                ontology_stats = await self._graph_db.execute_cypher(
                    """
                    MATCH (e:Entity)
                    WHERE e.prop_ontology_id = $ontology_id
                    RETURN count(e) as element_count
                    """,
                    {"ontology_id": ontology_id}
                )
                if ontology_stats:
                    result["ontology_element_count"] = ontology_stats[0].get("element_count", 0)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {
                "available": False,
                "error": str(e),
            }
    
    async def close(self) -> None:
        """关闭连接"""
        if self._graph_db:
            await self._graph_db.close()
            self._initialized = False


# 全局实例
_collaboration_graph: Optional[CollaborationGraphIntegration] = None


def get_collaboration_graph() -> CollaborationGraphIntegration:
    """获取或创建全局协作图谱集成实例"""
    global _collaboration_graph
    
    if _collaboration_graph is None:
        _collaboration_graph = CollaborationGraphIntegration()
    
    return _collaboration_graph


async def init_collaboration_graph() -> CollaborationGraphIntegration:
    """初始化并返回协作图谱集成"""
    graph = get_collaboration_graph()
    await graph.initialize()
    return graph
