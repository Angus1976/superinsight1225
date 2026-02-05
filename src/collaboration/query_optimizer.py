"""
本体专家协作数据库查询优化模块

提供数据库查询优化支持：
- 索引管理
- 连接池配置
- 分页查询
- JSONB 查询优化

Validates: Task 28.2 - Optimize database queries
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, TypeVar, Generic, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class IndexType(str, Enum):
    """索引类型"""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    BRIN = "brin"


@dataclass
class IndexDefinition:
    """索引定义"""
    name: str
    table: str
    columns: List[str]
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    where_clause: Optional[str] = None
    include_columns: Optional[List[str]] = None
    
    def to_sql(self) -> str:
        """生成创建索引的 SQL"""
        unique_str = "UNIQUE " if self.unique else ""
        columns_str = ", ".join(self.columns)
        
        sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {self.name} "
        sql += f"ON {self.table} USING {self.index_type.value} ({columns_str})"
        
        if self.include_columns:
            include_str = ", ".join(self.include_columns)
            sql += f" INCLUDE ({include_str})"
        
        if self.where_clause:
            sql += f" WHERE {self.where_clause}"
        
        return sql


# 协作模块推荐索引
COLLABORATION_INDEXES: List[IndexDefinition] = [
    # 专家表索引
    IndexDefinition(
        name="idx_experts_expertise_area",
        table="expert_profiles",
        columns=["expertise_area"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_experts_availability",
        table="expert_profiles",
        columns=["is_available"],
        index_type=IndexType.BTREE,
        where_clause="is_available = true",
    ),
    IndexDefinition(
        name="idx_experts_quality_score",
        table="expert_profiles",
        columns=["quality_score"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_experts_tenant",
        table="expert_profiles",
        columns=["tenant_id"],
        index_type=IndexType.HASH,
    ),
    
    # 模板表索引
    IndexDefinition(
        name="idx_templates_industry",
        table="ontology_templates",
        columns=["industry"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_templates_status",
        table="ontology_templates",
        columns=["status"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_templates_created_at",
        table="ontology_templates",
        columns=["created_at"],
        index_type=IndexType.BRIN,
    ),
    
    # 变更请求表索引
    IndexDefinition(
        name="idx_change_requests_status",
        table="change_requests",
        columns=["status"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_change_requests_requester",
        table="change_requests",
        columns=["requester_id"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_change_requests_ontology_area",
        table="change_requests",
        columns=["ontology_area"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_change_requests_deadline",
        table="change_requests",
        columns=["deadline"],
        index_type=IndexType.BTREE,
        where_clause="status IN ('submitted', 'in_review')",
    ),
    
    # 审批记录表索引
    IndexDefinition(
        name="idx_approval_records_approver",
        table="approval_records",
        columns=["approver_id"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_approval_records_status",
        table="approval_records",
        columns=["status"],
        index_type=IndexType.BTREE,
    ),
    
    # 验证规则表索引
    IndexDefinition(
        name="idx_validation_rules_region_industry",
        table="validation_rules",
        columns=["region", "industry"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_validation_rules_entity_type",
        table="validation_rules",
        columns=["entity_type"],
        index_type=IndexType.BTREE,
    ),
    
    # 审计日志表索引
    IndexDefinition(
        name="idx_audit_logs_timestamp",
        table="ontology_audit_logs",
        columns=["timestamp"],
        index_type=IndexType.BRIN,
    ),
    IndexDefinition(
        name="idx_audit_logs_user",
        table="ontology_audit_logs",
        columns=["user_id"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_audit_logs_change_type",
        table="ontology_audit_logs",
        columns=["change_type"],
        index_type=IndexType.BTREE,
    ),
    IndexDefinition(
        name="idx_audit_logs_ontology",
        table="ontology_audit_logs",
        columns=["ontology_id"],
        index_type=IndexType.BTREE,
    ),
    
    # JSONB 索引
    IndexDefinition(
        name="idx_templates_metadata_gin",
        table="ontology_templates",
        columns=["metadata"],
        index_type=IndexType.GIN,
    ),
    IndexDefinition(
        name="idx_experts_certifications_gin",
        table="expert_profiles",
        columns=["certifications"],
        index_type=IndexType.GIN,
    ),
    IndexDefinition(
        name="idx_audit_logs_affected_elements_gin",
        table="ontology_audit_logs",
        columns=["affected_elements"],
        index_type=IndexType.GIN,
    ),
]


@dataclass
class QueryStats:
    """查询统计"""
    total_queries: int = 0
    slow_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_execution_time_ms: float = 0.0
    max_execution_time_ms: float = 0.0


@dataclass
class PaginationParams:
    """分页参数"""
    page: int = 1
    page_size: int = 20
    max_page_size: int = 100
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """获取限制数"""
        return min(self.page_size, self.max_page_size)
    
    def validate(self) -> None:
        """验证参数"""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1:
            raise ValueError("Page size must be >= 1")
        if self.page_size > self.max_page_size:
            raise ValueError(f"Page size must be <= {self.max_page_size}")


@dataclass
class PaginatedResult(Generic[T]):
    """分页结果"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        params: PaginationParams,
    ) -> "PaginatedResult[T]":
        """创建分页结果"""
        total_pages = (total + params.page_size - 1) // params.page_size
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "items": self.items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "page_size": self.page_size,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev,
            },
        }


class QueryOptimizer:
    """
    查询优化器
    
    提供：
    - 索引管理
    - 查询分析
    - 分页支持
    - JSONB 查询优化
    """
    
    def __init__(self):
        """初始化查询优化器"""
        self._stats = QueryStats()
        self._lock = asyncio.Lock()
        self._slow_query_threshold_ms = 100.0
        
        logger.info("QueryOptimizer initialized")
    
    # ========================================================================
    # 索引管理
    # ========================================================================
    
    def get_recommended_indexes(self) -> List[IndexDefinition]:
        """获取推荐索引列表"""
        return COLLABORATION_INDEXES.copy()
    
    def generate_index_sql(self) -> str:
        """生成所有索引的 SQL"""
        sql_statements = []
        for index in COLLABORATION_INDEXES:
            sql_statements.append(index.to_sql() + ";")
        return "\n".join(sql_statements)
    
    def generate_drop_index_sql(self) -> str:
        """生成删除所有索引的 SQL"""
        sql_statements = []
        for index in COLLABORATION_INDEXES:
            sql_statements.append(f"DROP INDEX IF EXISTS {index.name};")
        return "\n".join(sql_statements)
    
    # ========================================================================
    # JSONB 查询优化
    # ========================================================================
    
    @staticmethod
    def jsonb_contains_query(
        column: str,
        key: str,
        value: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        生成 JSONB 包含查询
        
        Args:
            column: JSONB 列名
            key: JSON 键
            value: 值
            
        Returns:
            (SQL 条件, 参数字典)
        """
        param_name = f"jsonb_{key}"
        sql = f"{column} @> %({param_name})s::jsonb"
        params = {param_name: f'{{"{key}": {value}}}'}
        return sql, params
    
    @staticmethod
    def jsonb_path_query(
        column: str,
        path: str,
        value: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        生成 JSONB 路径查询
        
        Args:
            column: JSONB 列名
            path: JSON 路径 (如 '$.metadata.version')
            value: 值
            
        Returns:
            (SQL 条件, 参数字典)
        """
        param_name = "jsonb_path_value"
        sql = f"jsonb_path_exists({column}, %({param_name}_path)s, %({param_name}_vars)s)"
        params = {
            f"{param_name}_path": path,
            f"{param_name}_vars": f'{{"val": {value}}}',
        }
        return sql, params
    
    @staticmethod
    def jsonb_array_contains_query(
        column: str,
        value: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        生成 JSONB 数组包含查询
        
        Args:
            column: JSONB 数组列名
            value: 要查找的值
            
        Returns:
            (SQL 条件, 参数字典)
        """
        param_name = "jsonb_array_value"
        sql = f"{column} ? %({param_name})s"
        params = {param_name: value}
        return sql, params
    
    # ========================================================================
    # 分页支持
    # ========================================================================
    
    def paginate(
        self,
        items: List[T],
        params: PaginationParams,
    ) -> PaginatedResult[T]:
        """
        对内存列表进行分页
        
        Args:
            items: 完整列表
            params: 分页参数
            
        Returns:
            分页结果
        """
        params.validate()
        
        total = len(items)
        start = params.offset
        end = start + params.limit
        
        paginated_items = items[start:end]
        
        return PaginatedResult.create(
            items=paginated_items,
            total=total,
            params=params,
        )
    
    def generate_pagination_sql(
        self,
        params: PaginationParams,
    ) -> str:
        """
        生成分页 SQL 子句
        
        Args:
            params: 分页参数
            
        Returns:
            SQL 子句
        """
        params.validate()
        return f"LIMIT {params.limit} OFFSET {params.offset}"
    
    # ========================================================================
    # 查询统计
    # ========================================================================
    
    async def record_query(
        self,
        execution_time_ms: float,
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
                "slow_query_threshold_ms": self._slow_query_threshold_ms,
            }
    
    async def reset_stats(self) -> None:
        """重置统计"""
        async with self._lock:
            self._stats = QueryStats()


class ConnectionPoolConfig:
    """
    连接池配置
    
    提供数据库连接池的推荐配置
    """
    
    # PostgreSQL 连接池配置
    POSTGRES_POOL_CONFIG = {
        "min_size": 5,
        "max_size": 20,
        "max_queries": 50000,
        "max_inactive_connection_lifetime": 300.0,
        "timeout": 30.0,
        "command_timeout": 60.0,
        "statement_cache_size": 1024,
    }
    
    # Redis 连接池配置
    REDIS_POOL_CONFIG = {
        "max_connections": 50,
        "socket_timeout": 5.0,
        "socket_connect_timeout": 5.0,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    }
    
    # Neo4j 连接池配置
    NEO4J_POOL_CONFIG = {
        "max_connection_pool_size": 50,
        "connection_acquisition_timeout": 60.0,
        "max_transaction_retry_time": 30.0,
        "connection_timeout": 30.0,
    }
    
    @classmethod
    def get_postgres_config(cls) -> Dict[str, Any]:
        """获取 PostgreSQL 连接池配置"""
        return cls.POSTGRES_POOL_CONFIG.copy()
    
    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """获取 Redis 连接池配置"""
        return cls.REDIS_POOL_CONFIG.copy()
    
    @classmethod
    def get_neo4j_config(cls) -> Dict[str, Any]:
        """获取 Neo4j 连接池配置"""
        return cls.NEO4J_POOL_CONFIG.copy()


# 全局实例
_query_optimizer: Optional[QueryOptimizer] = None


def get_query_optimizer() -> QueryOptimizer:
    """获取或创建全局查询优化器实例"""
    global _query_optimizer
    
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    
    return _query_optimizer
