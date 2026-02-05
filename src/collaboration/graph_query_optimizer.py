"""
本体专家协作 Neo4j 图查询优化模块

提供 Neo4j 图查询优化支持：
- 索引管理
- 查询参数化
- 遍历深度限制
- 查询结果缓存

Validates: Task 28.3 - Optimize Neo4j graph queries
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class Neo4jIndexType(str, Enum):
    """Neo4j 索引类型"""
    RANGE = "RANGE"
    TEXT = "TEXT"
    POINT = "POINT"
    FULLTEXT = "FULLTEXT"
    LOOKUP = "LOOKUP"


@dataclass
class Neo4jIndexDefinition:
    """Neo4j 索引定义"""
    name: str
    label: str
    properties: List[str]
    index_type: Neo4jIndexType = Neo4jIndexType.RANGE
    
    def to_cypher(self) -> str:
        """生成创建索引的 Cypher"""
        props = ", ".join(f"n.{p}" for p in self.properties)
        
        if self.index_type == Neo4jIndexType.FULLTEXT:
            return (
                f"CREATE FULLTEXT INDEX {self.name} IF NOT EXISTS "
                f"FOR (n:{self.label}) ON EACH [{props}]"
            )
        else:
            return (
                f"CREATE {self.index_type.value} INDEX {self.name} IF NOT EXISTS "
                f"FOR (n:{self.label}) ON ({props})"
            )


@dataclass
class Neo4jConstraintDefinition:
    """Neo4j 约束定义"""
    name: str
    label: str
    property: str
    constraint_type: str = "UNIQUE"
    
    def to_cypher(self) -> str:
        """生成创建约束的 Cypher"""
        if self.constraint_type == "UNIQUE":
            return (
                f"CREATE CONSTRAINT {self.name} IF NOT EXISTS "
                f"FOR (n:{self.label}) REQUIRE n.{self.property} IS UNIQUE"
            )
        elif self.constraint_type == "NOT_NULL":
            return (
                f"CREATE CONSTRAINT {self.name} IF NOT EXISTS "
                f"FOR (n:{self.label}) REQUIRE n.{self.property} IS NOT NULL"
            )
        else:
            raise ValueError(f"Unknown constraint type: {self.constraint_type}")


# 协作模块推荐 Neo4j 索引
COLLABORATION_NEO4J_INDEXES: List[Neo4jIndexDefinition] = [
    # 实体类型索引
    Neo4jIndexDefinition(
        name="idx_entity_type_id",
        label="EntityType",
        properties=["id"],
        index_type=Neo4jIndexType.RANGE,
    ),
    Neo4jIndexDefinition(
        name="idx_entity_type_name",
        label="EntityType",
        properties=["name"],
        index_type=Neo4jIndexType.TEXT,
    ),
    Neo4jIndexDefinition(
        name="idx_entity_type_ontology",
        label="EntityType",
        properties=["ontology_id"],
        index_type=Neo4jIndexType.RANGE,
    ),
    
    # 关系类型索引
    Neo4jIndexDefinition(
        name="idx_relation_type_id",
        label="RelationType",
        properties=["id"],
        index_type=Neo4jIndexType.RANGE,
    ),
    Neo4jIndexDefinition(
        name="idx_relation_type_name",
        label="RelationType",
        properties=["name"],
        index_type=Neo4jIndexType.TEXT,
    ),
    
    # 专家索引
    Neo4jIndexDefinition(
        name="idx_expert_id",
        label="Expert",
        properties=["id"],
        index_type=Neo4jIndexType.RANGE,
    ),
    Neo4jIndexDefinition(
        name="idx_expert_expertise",
        label="Expert",
        properties=["expertise_area"],
        index_type=Neo4jIndexType.RANGE,
    ),
    
    # 模板索引
    Neo4jIndexDefinition(
        name="idx_template_id",
        label="Template",
        properties=["id"],
        index_type=Neo4jIndexType.RANGE,
    ),
    Neo4jIndexDefinition(
        name="idx_template_industry",
        label="Template",
        properties=["industry"],
        index_type=Neo4jIndexType.RANGE,
    ),
    
    # 项目索引
    Neo4jIndexDefinition(
        name="idx_project_id",
        label="Project",
        properties=["id"],
        index_type=Neo4jIndexType.RANGE,
    ),
    
    # 全文搜索索引
    Neo4jIndexDefinition(
        name="idx_entity_fulltext",
        label="EntityType",
        properties=["name", "description"],
        index_type=Neo4jIndexType.FULLTEXT,
    ),
]

# 协作模块推荐 Neo4j 约束
COLLABORATION_NEO4J_CONSTRAINTS: List[Neo4jConstraintDefinition] = [
    Neo4jConstraintDefinition(
        name="constraint_entity_type_id",
        label="EntityType",
        property="id",
        constraint_type="UNIQUE",
    ),
    Neo4jConstraintDefinition(
        name="constraint_relation_type_id",
        label="RelationType",
        property="id",
        constraint_type="UNIQUE",
    ),
    Neo4jConstraintDefinition(
        name="constraint_expert_id",
        label="Expert",
        property="id",
        constraint_type="UNIQUE",
    ),
    Neo4jConstraintDefinition(
        name="constraint_template_id",
        label="Template",
        property="id",
        constraint_type="UNIQUE",
    ),
]


@dataclass
class GraphQueryStats:
    """图查询统计"""
    total_queries: int = 0
    slow_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_execution_time_ms: float = 0.0
    max_execution_time_ms: float = 0.0
    avg_nodes_returned: float = 0.0
    avg_relationships_returned: float = 0.0


class GraphQueryOptimizer:
    """
    Neo4j 图查询优化器
    
    提供：
    - 索引管理
    - 查询参数化
    - 遍历深度限制
    - 查询结果缓存
    """
    
    # 默认遍历深度限制
    DEFAULT_MAX_DEPTH = 5
    
    # 默认结果限制
    DEFAULT_RESULT_LIMIT = 1000
    
    def __init__(
        self,
        max_depth: int = DEFAULT_MAX_DEPTH,
        result_limit: int = DEFAULT_RESULT_LIMIT,
    ):
        """
        初始化图查询优化器
        
        Args:
            max_depth: 最大遍历深度
            result_limit: 默认结果限制
        """
        self._max_depth = max_depth
        self._result_limit = result_limit
        self._stats = GraphQueryStats()
        self._lock = asyncio.Lock()
        self._slow_query_threshold_ms = 500.0
        
        # 查询缓存
        self._query_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl_seconds = 600  # 10 分钟
        
        logger.info(
            f"GraphQueryOptimizer initialized "
            f"(max_depth={max_depth}, result_limit={result_limit})"
        )
    
    # ========================================================================
    # 索引管理
    # ========================================================================
    
    def get_recommended_indexes(self) -> List[Neo4jIndexDefinition]:
        """获取推荐索引列表"""
        return COLLABORATION_NEO4J_INDEXES.copy()
    
    def get_recommended_constraints(self) -> List[Neo4jConstraintDefinition]:
        """获取推荐约束列表"""
        return COLLABORATION_NEO4J_CONSTRAINTS.copy()
    
    def generate_index_cypher(self) -> str:
        """生成所有索引的 Cypher"""
        statements = []
        
        # 约束
        for constraint in COLLABORATION_NEO4J_CONSTRAINTS:
            statements.append(constraint.to_cypher() + ";")
        
        # 索引
        for index in COLLABORATION_NEO4J_INDEXES:
            statements.append(index.to_cypher() + ";")
        
        return "\n".join(statements)
    
    def generate_drop_index_cypher(self) -> str:
        """生成删除所有索引的 Cypher"""
        statements = []
        
        for index in COLLABORATION_NEO4J_INDEXES:
            statements.append(f"DROP INDEX {index.name} IF EXISTS;")
        
        for constraint in COLLABORATION_NEO4J_CONSTRAINTS:
            statements.append(f"DROP CONSTRAINT {constraint.name} IF EXISTS;")
        
        return "\n".join(statements)
    
    # ========================================================================
    # 参数化查询
    # ========================================================================
    
    def build_dependency_query(
        self,
        element_id: str,
        max_depth: Optional[int] = None,
        direction: str = "OUTGOING",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        构建依赖查询
        
        Args:
            element_id: 元素 ID
            max_depth: 最大深度
            direction: 方向 (OUTGOING, INCOMING, BOTH)
            
        Returns:
            (Cypher 查询, 参数字典)
        """
        depth = min(max_depth or self._max_depth, self._max_depth)
        
        if direction == "OUTGOING":
            rel_pattern = "-[r:DEPENDS_ON|USED_BY|CONNECTS*1..{depth}]->"
        elif direction == "INCOMING":
            rel_pattern = "<-[r:DEPENDS_ON|USED_BY|CONNECTS*1..{depth}]-"
        else:  # BOTH
            rel_pattern = "-[r:DEPENDS_ON|USED_BY|CONNECTS*1..{depth}]-"
        
        rel_pattern = rel_pattern.format(depth=depth)
        
        cypher = f"""
        MATCH (start {{id: $element_id}})
        MATCH path = (start){rel_pattern}(end)
        WITH end, length(path) as distance
        RETURN DISTINCT end.id as id, end.name as name, 
               labels(end)[0] as type, min(distance) as distance
        ORDER BY distance
        LIMIT $limit
        """
        
        params = {
            "element_id": element_id,
            "limit": self._result_limit,
        }
        
        return cypher.strip(), params
    
    def build_impact_analysis_query(
        self,
        element_id: str,
        change_type: str,
        max_depth: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        构建影响分析查询
        
        Args:
            element_id: 元素 ID
            change_type: 变更类型
            max_depth: 最大深度
            
        Returns:
            (Cypher 查询, 参数字典)
        """
        depth = min(max_depth or self._max_depth, self._max_depth)
        
        # 删除操作需要双向遍历
        if change_type == "delete":
            cypher = f"""
            MATCH (start {{id: $element_id}})
            CALL {{
                WITH start
                MATCH path = (start)-[r:DEPENDS_ON|USED_BY|CONNECTS*1..{depth}]-(end)
                RETURN end, length(path) as distance
            }}
            WITH end, min(distance) as distance
            RETURN 
                count(DISTINCT end) as affected_count,
                collect(DISTINCT {{
                    id: end.id, 
                    name: end.name, 
                    type: labels(end)[0],
                    distance: distance
                }})[0..{self._result_limit}] as affected_elements
            """
        else:
            cypher = f"""
            MATCH (start {{id: $element_id}})
            CALL {{
                WITH start
                MATCH path = (start)-[r:DEPENDS_ON|USED_BY|CONNECTS*1..{depth}]->(end)
                RETURN end, length(path) as distance
            }}
            WITH end, min(distance) as distance
            RETURN 
                count(DISTINCT end) as affected_count,
                collect(DISTINCT {{
                    id: end.id, 
                    name: end.name, 
                    type: labels(end)[0],
                    distance: distance
                }})[0..{self._result_limit}] as affected_elements
            """
        
        params = {
            "element_id": element_id,
        }
        
        return cypher.strip(), params
    
    def build_expert_contribution_query(
        self,
        expert_id: str,
        ontology_id: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        构建专家贡献查询
        
        Args:
            expert_id: 专家 ID
            ontology_id: 本体 ID（可选）
            
        Returns:
            (Cypher 查询, 参数字典)
        """
        if ontology_id:
            cypher = """
            MATCH (e:Expert {id: $expert_id})-[c:CONTRIBUTED_TO]->(element)
            WHERE element.ontology_id = $ontology_id
            RETURN 
                count(c) as contribution_count,
                collect(DISTINCT labels(element)[0]) as element_types,
                avg(c.quality_score) as avg_quality
            """
            params = {
                "expert_id": expert_id,
                "ontology_id": ontology_id,
            }
        else:
            cypher = """
            MATCH (e:Expert {id: $expert_id})-[c:CONTRIBUTED_TO]->(element)
            RETURN 
                count(c) as contribution_count,
                collect(DISTINCT labels(element)[0]) as element_types,
                avg(c.quality_score) as avg_quality
            """
            params = {
                "expert_id": expert_id,
            }
        
        return cypher.strip(), params
    
    def build_template_usage_query(
        self,
        template_id: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        构建模板使用查询
        
        Args:
            template_id: 模板 ID
            
        Returns:
            (Cypher 查询, 参数字典)
        """
        cypher = """
        MATCH (t:Template {id: $template_id})<-[u:DERIVED_FROM]-(ontology)
        RETURN 
            count(u) as usage_count,
            collect(DISTINCT {
                id: ontology.id,
                name: ontology.name,
                created_at: u.created_at
            })[0..$limit] as usages
        """
        
        params = {
            "template_id": template_id,
            "limit": self._result_limit,
        }
        
        return cypher.strip(), params
    
    def build_search_query(
        self,
        search_term: str,
        labels: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        构建全文搜索查询
        
        Args:
            search_term: 搜索词
            labels: 标签过滤
            limit: 结果限制
            
        Returns:
            (Cypher 查询, 参数字典)
        """
        result_limit = min(limit or self._result_limit, self._result_limit)
        
        if labels:
            label_filter = " OR ".join(f"'{l}' IN labels(node)" for l in labels)
            cypher = f"""
            CALL db.index.fulltext.queryNodes('idx_entity_fulltext', $search_term)
            YIELD node, score
            WHERE {label_filter}
            RETURN node.id as id, node.name as name, 
                   labels(node)[0] as type, score
            ORDER BY score DESC
            LIMIT $limit
            """
        else:
            cypher = """
            CALL db.index.fulltext.queryNodes('idx_entity_fulltext', $search_term)
            YIELD node, score
            RETURN node.id as id, node.name as name, 
                   labels(node)[0] as type, score
            ORDER BY score DESC
            LIMIT $limit
            """
        
        params = {
            "search_term": search_term,
            "limit": result_limit,
        }
        
        return cypher.strip(), params
    
    # ========================================================================
    # 查询缓存
    # ========================================================================
    
    def _generate_cache_key(
        self,
        query: str,
        params: Dict[str, Any],
    ) -> str:
        """生成缓存键"""
        import hashlib
        key_str = f"{query}:{sorted(params.items())}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get_cached_result(
        self,
        query: str,
        params: Dict[str, Any],
    ) -> Optional[Any]:
        """获取缓存的查询结果"""
        cache_key = self._generate_cache_key(query, params)
        
        async with self._lock:
            if cache_key in self._query_cache:
                result, cached_at = self._query_cache[cache_key]
                
                # 检查是否过期
                age = (datetime.now() - cached_at).total_seconds()
                if age < self._cache_ttl_seconds:
                    self._stats.cache_hits += 1
                    return result
                else:
                    del self._query_cache[cache_key]
            
            self._stats.cache_misses += 1
            return None
    
    async def cache_result(
        self,
        query: str,
        params: Dict[str, Any],
        result: Any,
    ) -> None:
        """缓存查询结果"""
        cache_key = self._generate_cache_key(query, params)
        
        async with self._lock:
            self._query_cache[cache_key] = (result, datetime.now())
    
    async def invalidate_cache(
        self,
        pattern: Optional[str] = None,
    ) -> int:
        """失效缓存"""
        async with self._lock:
            if pattern is None:
                count = len(self._query_cache)
                self._query_cache.clear()
                return count
            else:
                # 简单的模式匹配（实际应用中可能需要更复杂的逻辑）
                keys_to_delete = [
                    k for k in self._query_cache.keys()
                    if pattern in k
                ]
                for key in keys_to_delete:
                    del self._query_cache[key]
                return len(keys_to_delete)
    
    # ========================================================================
    # 查询统计
    # ========================================================================
    
    async def record_query(
        self,
        execution_time_ms: float,
        nodes_returned: int = 0,
        relationships_returned: int = 0,
        cache_hit: bool = False,
    ) -> None:
        """记录查询统计"""
        async with self._lock:
            self._stats.total_queries += 1
            
            if cache_hit:
                self._stats.cache_hits += 1
            else:
                self._stats.cache_misses += 1
            
            if execution_time_ms > self._slow_query_threshold_ms:
                self._stats.slow_queries += 1
            
            # 更新平均执行时间
            n = self._stats.total_queries
            old_avg = self._stats.avg_execution_time_ms
            self._stats.avg_execution_time_ms = (
                old_avg * (n - 1) + execution_time_ms
            ) / n
            
            # 更新最大执行时间
            if execution_time_ms > self._stats.max_execution_time_ms:
                self._stats.max_execution_time_ms = execution_time_ms
            
            # 更新平均返回节点数
            old_avg_nodes = self._stats.avg_nodes_returned
            self._stats.avg_nodes_returned = (
                old_avg_nodes * (n - 1) + nodes_returned
            ) / n
            
            # 更新平均返回关系数
            old_avg_rels = self._stats.avg_relationships_returned
            self._stats.avg_relationships_returned = (
                old_avg_rels * (n - 1) + relationships_returned
            ) / n
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取查询统计"""
        async with self._lock:
            return {
                "total_queries": self._stats.total_queries,
                "slow_queries": self._stats.slow_queries,
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "cache_hit_rate": (
                    self._stats.cache_hits / self._stats.total_queries
                    if self._stats.total_queries > 0 else 0.0
                ),
                "avg_execution_time_ms": self._stats.avg_execution_time_ms,
                "max_execution_time_ms": self._stats.max_execution_time_ms,
                "avg_nodes_returned": self._stats.avg_nodes_returned,
                "avg_relationships_returned": self._stats.avg_relationships_returned,
                "slow_query_threshold_ms": self._slow_query_threshold_ms,
                "max_depth": self._max_depth,
                "result_limit": self._result_limit,
                "cache_size": len(self._query_cache),
            }
    
    async def reset_stats(self) -> None:
        """重置统计"""
        async with self._lock:
            self._stats = GraphQueryStats()


# 全局实例
_graph_optimizer: Optional[GraphQueryOptimizer] = None


def get_graph_query_optimizer() -> GraphQueryOptimizer:
    """获取或创建全局图查询优化器实例"""
    global _graph_optimizer
    
    if _graph_optimizer is None:
        _graph_optimizer = GraphQueryOptimizer()
    
    return _graph_optimizer
