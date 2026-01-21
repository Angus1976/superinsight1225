"""
Redis 缓存策略模块

提供完整的 Redis 缓存策略实现，包括：
- Cache-aside 模式
- 不同数据类型的 TTL 配置
- 缓存失效（单个和批量）
- 缓存预热
- 命中率监控

Feature: system-optimization
验证: 需求 8.1, 8.2, 8.3, 8.4, 8.5
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# i18n 翻译键定义
# ============================================================================

class CacheI18nKeys:
    """缓存策略相关的 i18n 翻译键"""
    
    # 缓存操作
    CACHE_HIT = "cache.strategy.cache_hit"
    CACHE_MISS = "cache.strategy.cache_miss"
    CACHE_SET = "cache.strategy.cache_set"
    CACHE_INVALIDATED = "cache.strategy.cache_invalidated"
    BATCH_INVALIDATED = "cache.strategy.batch_invalidated"
    
    # 预热相关
    WARMUP_STARTED = "cache.warmup.started"
    WARMUP_COMPLETED = "cache.warmup.completed"
    WARMUP_FAILED = "cache.warmup.failed"
    
    # 监控相关
    HIT_RATE_LOW = "cache.monitor.hit_rate_low"
    STATS_RESET = "cache.monitor.stats_reset"
    
    # 错误消息
    CONNECTION_FAILED = "cache.error.connection_failed"
    SERIALIZATION_FAILED = "cache.error.serialization_failed"
    DESERIALIZATION_FAILED = "cache.error.deserialization_failed"
    OPERATION_FAILED = "cache.error.operation_failed"


# ============================================================================
# 配置数据类
# ============================================================================

@dataclass
class CacheConfig:
    """缓存配置"""
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 3600  # 1 小时
    ttl_by_type: Dict[str, int] = field(default_factory=lambda: {
        "user": 1800,           # 30 分钟
        "project": 3600,        # 1 小时
        "task": 600,            # 10 分钟
        "config": 86400,        # 24 小时
        "data_source": 300,     # 5 分钟
        "evaluation_result": 3600,  # 1 小时
        "business_rule": 600,   # 10 分钟
        "system_config": 1800,  # 30 分钟
        "user_session": 7200,   # 2 小时
    })
    hit_rate_threshold: float = 0.8  # 80%
    warmup_keys: List[str] = field(default_factory=list)
    key_prefix: str = "superinsight:"
    enable_logging: bool = True


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    invalidations: int = 0
    errors: int = 0
    last_reset: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def total_operations(self) -> int:
        """总操作数"""
        return self.hits + self.misses + self.sets + self.invalidations
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "invalidations": self.invalidations,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate * 100, 2),
            "total_operations": self.total_operations,
            "last_reset": self.last_reset.isoformat() if self.last_reset else None
        }


# ============================================================================
# 缓存策略类
# ============================================================================

class CacheStrategy:
    """
    Redis 缓存策略
    
    实现 cache-aside 模式，支持：
    - 不同数据类型的 TTL 配置
    - 缓存失效（单个和批量模式匹配）
    - 缓存预热
    - 命中率监控
    
    Feature: system-optimization
    验证: 需求 8.1, 8.2, 8.3, 8.4, 8.5
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        初始化缓存策略
        
        Args:
            config: 缓存配置，如果为 None 则使用默认配置
        """
        self.config = config or CacheConfig()
        self._redis = None
        self._stats = CacheStats(last_reset=datetime.utcnow())
        self._connected = False
        self._lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """
        连接 Redis
        
        Returns:
            连接是否成功
        """
        try:
            import redis.asyncio as redis
            
            self._redis = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # 测试连接
            await self._redis.ping()
            self._connected = True
            
            if self.config.enable_logging:
                logger.info(
                    f"[{CacheI18nKeys.CACHE_SET}] "
                    f"Redis connection established: {self.config.redis_url}"
                )
            
            return True
            
        except Exception as e:
            self._connected = False
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.CONNECTION_FAILED}] "
                f"Redis connection failed: {e}"
            )
            return False
    
    async def disconnect(self) -> None:
        """断开 Redis 连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False
            
            if self.config.enable_logging:
                logger.info("Redis connection closed")
    
    def _get_full_key(self, key: str) -> str:
        """获取带前缀的完整键名"""
        if key.startswith(self.config.key_prefix):
            return key
        return f"{self.config.key_prefix}{key}"
    
    def _get_ttl(self, data_type: Optional[str] = None, ttl: Optional[int] = None) -> int:
        """
        获取 TTL 值
        
        Args:
            data_type: 数据类型
            ttl: 显式指定的 TTL
            
        Returns:
            TTL 秒数
        """
        if ttl is not None:
            return ttl
        if data_type and data_type in self.config.ttl_by_type:
            return self.config.ttl_by_type[data_type]
        return self.config.default_ttl

    
    def _serialize(self, value: Any) -> str:
        """
        序列化值为 JSON 字符串
        
        Args:
            value: 要序列化的值
            
        Returns:
            JSON 字符串
        """
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(
                f"[{CacheI18nKeys.SERIALIZATION_FAILED}] "
                f"Serialization failed: {e}"
            )
            raise
    
    def _deserialize(self, value: str) -> Any:
        """
        反序列化 JSON 字符串
        
        Args:
            value: JSON 字符串
            
        Returns:
            反序列化后的值
        """
        try:
            return json.loads(value)
        except Exception as e:
            logger.error(
                f"[{CacheI18nKeys.DESERIALIZATION_FAILED}] "
                f"Deserialization failed: {e}"
            )
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回 None
        """
        if not self._connected or not self._redis:
            return None
        
        full_key = self._get_full_key(key)
        
        try:
            value = await self._redis.get(full_key)
            
            if value is not None:
                self._stats.hits += 1
                if self.config.enable_logging:
                    logger.debug(
                        f"[{CacheI18nKeys.CACHE_HIT}] "
                        f"Cache hit: {key}"
                    )
                return self._deserialize(value)
            else:
                self._stats.misses += 1
                if self.config.enable_logging:
                    logger.debug(
                        f"[{CacheI18nKeys.CACHE_MISS}] "
                        f"Cache miss: {key}"
                    )
                return None
                
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache get failed for key {key}: {e}"
            )
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        data_type: Optional[str] = None
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: TTL 秒数（可选）
            data_type: 数据类型，用于确定 TTL（可选）
            
        Returns:
            是否设置成功
        """
        if not self._connected or not self._redis:
            return False
        
        full_key = self._get_full_key(key)
        actual_ttl = self._get_ttl(data_type, ttl)
        
        try:
            serialized_value = self._serialize(value)
            await self._redis.setex(full_key, actual_ttl, serialized_value)
            
            self._stats.sets += 1
            if self.config.enable_logging:
                logger.debug(
                    f"[{CacheI18nKeys.CACHE_SET}] "
                    f"Cache set: {key}, TTL: {actual_ttl}s"
                )
            return True
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache set failed for key {key}: {e}"
            )
            return False

    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: Optional[int] = None,
        data_type: Optional[str] = None
    ) -> T:
        """
        获取缓存值，未命中则调用 factory 获取并缓存 (cache-aside 模式)
        
        Args:
            key: 缓存键
            factory: 获取数据的异步工厂函数
            ttl: TTL 秒数（可选）
            data_type: 数据类型，用于确定 TTL（可选）
            
        Returns:
            缓存值或从 factory 获取的值
            
        Feature: system-optimization
        验证: 需求 8.1
        """
        # 先尝试从缓存获取
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
        
        # 缓存未命中，调用 factory 获取数据
        async with self._lock:
            # 双重检查，避免并发时重复获取
            cached_value = await self.get(key)
            if cached_value is not None:
                return cached_value
            
            # 调用 factory 获取数据
            value = await factory()
            
            # 写入缓存
            await self.set(key, value, ttl=ttl, data_type=data_type)
            
            return value
    
    async def invalidate(self, key: str) -> bool:
        """
        失效单个缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
            
        Feature: system-optimization
        验证: 需求 8.3
        """
        if not self._connected or not self._redis:
            return False
        
        full_key = self._get_full_key(key)
        
        try:
            result = await self._redis.delete(full_key)
            
            if result > 0:
                self._stats.invalidations += 1
                if self.config.enable_logging:
                    logger.info(
                        f"[{CacheI18nKeys.CACHE_INVALIDATED}] "
                        f"Cache invalidated: {key}"
                    )
            return result > 0
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache invalidate failed for key {key}: {e}"
            )
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        批量失效匹配模式的缓存
        
        Args:
            pattern: 匹配模式（如 "user:*"）
            
        Returns:
            删除的键数量
            
        Feature: system-optimization
        验证: 需求 8.3
        """
        if not self._connected or not self._redis:
            return 0
        
        full_pattern = self._get_full_key(pattern)
        
        try:
            # 使用 SCAN 命令查找匹配的键
            keys_to_delete = []
            cursor = 0
            
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor,
                    match=full_pattern,
                    count=100
                )
                keys_to_delete.extend(keys)
                
                if cursor == 0:
                    break
            
            # 批量删除
            if keys_to_delete:
                deleted_count = await self._redis.delete(*keys_to_delete)
                self._stats.invalidations += deleted_count
                
                if self.config.enable_logging:
                    logger.info(
                        f"[{CacheI18nKeys.BATCH_INVALIDATED}] "
                        f"Batch cache invalidated: {pattern}, count: {deleted_count}"
                    )
                return deleted_count
            
            return 0
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache invalidate pattern failed for {pattern}: {e}"
            )
            return 0

    
    async def warmup(
        self,
        data_loader: Callable[[], Awaitable[Dict[str, Any]]],
        data_type: Optional[str] = None
    ) -> int:
        """
        缓存预热
        
        Args:
            data_loader: 加载预热数据的异步函数，返回 {key: value} 字典
            data_type: 数据类型，用于确定 TTL（可选）
            
        Returns:
            成功加载的键数量
            
        Feature: system-optimization
        验证: 需求 8.4
        """
        if not self._connected or not self._redis:
            logger.warning(
                f"[{CacheI18nKeys.WARMUP_FAILED}] "
                f"Cache warmup failed: Redis not connected"
            )
            return 0
        
        if self.config.enable_logging:
            logger.info(
                f"[{CacheI18nKeys.WARMUP_STARTED}] "
                f"Cache warmup started"
            )
        
        try:
            # 加载预热数据
            warmup_data = await data_loader()
            
            if not warmup_data:
                if self.config.enable_logging:
                    logger.info(
                        f"[{CacheI18nKeys.WARMUP_COMPLETED}] "
                        f"Cache warmup completed, loaded 0 keys (no data)"
                    )
                return 0
            
            # 批量写入缓存
            loaded_count = 0
            ttl = self._get_ttl(data_type)
            
            # 使用 pipeline 批量写入
            pipe = self._redis.pipeline()
            
            for key, value in warmup_data.items():
                full_key = self._get_full_key(key)
                serialized_value = self._serialize(value)
                pipe.setex(full_key, ttl, serialized_value)
                loaded_count += 1
            
            await pipe.execute()
            self._stats.sets += loaded_count
            
            if self.config.enable_logging:
                logger.info(
                    f"[{CacheI18nKeys.WARMUP_COMPLETED}] "
                    f"Cache warmup completed, loaded {loaded_count} keys"
                )
            
            return loaded_count
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.WARMUP_FAILED}] "
                f"Cache warmup failed: {e}"
            )
            return 0
    
    async def warmup_keys(
        self,
        keys: List[str],
        factory: Callable[[str], Awaitable[Any]],
        data_type: Optional[str] = None
    ) -> int:
        """
        预热指定的键列表
        
        Args:
            keys: 要预热的键列表
            factory: 根据键获取数据的异步函数
            data_type: 数据类型，用于确定 TTL（可选）
            
        Returns:
            成功加载的键数量
        """
        if not self._connected or not self._redis:
            return 0
        
        if self.config.enable_logging:
            logger.info(
                f"[{CacheI18nKeys.WARMUP_STARTED}] "
                f"Cache warmup started for {len(keys)} keys"
            )
        
        loaded_count = 0
        
        for key in keys:
            try:
                value = await factory(key)
                if value is not None:
                    await self.set(key, value, data_type=data_type)
                    loaded_count += 1
            except Exception as e:
                logger.warning(
                    f"[{CacheI18nKeys.WARMUP_FAILED}] "
                    f"Failed to warmup key {key}: {e}"
                )
        
        if self.config.enable_logging:
            logger.info(
                f"[{CacheI18nKeys.WARMUP_COMPLETED}] "
                f"Cache warmup completed, loaded {loaded_count}/{len(keys)} keys"
            )
        
        return loaded_count

    
    def get_stats(self) -> CacheStats:
        """
        获取缓存统计
        
        Returns:
            缓存统计对象
        """
        return self._stats
    
    def reset_stats(self) -> None:
        """
        重置缓存统计
        
        Feature: system-optimization
        验证: 需求 8.5
        """
        self._stats = CacheStats(last_reset=datetime.utcnow())
        
        if self.config.enable_logging:
            logger.info(
                f"[{CacheI18nKeys.STATS_RESET}] "
                f"Cache stats reset"
            )
    
    def check_hit_rate(self) -> bool:
        """
        检查命中率是否达标
        
        Returns:
            命中率是否达到阈值
            
        Feature: system-optimization
        验证: 需求 8.5
        """
        hit_rate = self._stats.hit_rate
        threshold = self.config.hit_rate_threshold
        
        if hit_rate < threshold and self._stats.total_operations > 0:
            logger.warning(
                f"[{CacheI18nKeys.HIT_RATE_LOW}] "
                f"Cache hit rate low: {hit_rate * 100:.2f}% < {threshold * 100:.2f}%"
            )
            return False
        
        return True
    
    async def check_and_warn(self) -> bool:
        """
        检查命中率并在低于阈值时发出警告
        
        Returns:
            命中率是否达到阈值
        """
        return self.check_hit_rate()
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        if not self._connected or not self._redis:
            return False
        
        full_key = self._get_full_key(key)
        
        try:
            return await self._redis.exists(full_key) > 0
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache exists check failed for key {key}: {e}"
            )
            return False
    
    async def get_ttl(self, key: str) -> int:
        """
        获取键的剩余 TTL
        
        Args:
            key: 缓存键
            
        Returns:
            剩余 TTL 秒数，-1 表示无过期，-2 表示键不存在
        """
        if not self._connected or not self._redis:
            return -2
        
        full_key = self._get_full_key(key)
        
        try:
            return await self._redis.ttl(full_key)
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache TTL check failed for key {key}: {e}"
            )
            return -2

    
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取多个键的值
        
        Args:
            keys: 缓存键列表
            
        Returns:
            键值字典，不存在的键不包含在结果中
        """
        if not self._connected or not self._redis or not keys:
            return {}
        
        full_keys = [self._get_full_key(k) for k in keys]
        
        try:
            values = await self._redis.mget(full_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    self._stats.hits += 1
                    result[key] = self._deserialize(value)
                else:
                    self._stats.misses += 1
            
            return result
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache mget failed: {e}"
            )
            return {}
    
    async def mset(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        data_type: Optional[str] = None
    ) -> bool:
        """
        批量设置多个键值对
        
        Args:
            data: 键值字典
            ttl: TTL 秒数（可选）
            data_type: 数据类型，用于确定 TTL（可选）
            
        Returns:
            是否设置成功
        """
        if not self._connected or not self._redis or not data:
            return False
        
        actual_ttl = self._get_ttl(data_type, ttl)
        
        try:
            pipe = self._redis.pipeline()
            
            for key, value in data.items():
                full_key = self._get_full_key(key)
                serialized_value = self._serialize(value)
                pipe.setex(full_key, actual_ttl, serialized_value)
            
            await pipe.execute()
            self._stats.sets += len(data)
            
            if self.config.enable_logging:
                logger.debug(
                    f"[{CacheI18nKeys.CACHE_SET}] "
                    f"Cache mset: {len(data)} keys, TTL: {actual_ttl}s"
                )
            
            return True
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"[{CacheI18nKeys.OPERATION_FAILED}] "
                f"Cache mset failed: {e}"
            )
            return False


# ============================================================================
# 全局缓存实例管理
# ============================================================================

_cache_instance: Optional[CacheStrategy] = None


async def get_cache(config: Optional[CacheConfig] = None) -> CacheStrategy:
    """
    获取全局缓存实例
    
    Args:
        config: 缓存配置（可选）
        
    Returns:
        缓存策略实例
    """
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = CacheStrategy(config)
        await _cache_instance.connect()
    
    return _cache_instance


async def close_cache() -> None:
    """关闭全局缓存实例"""
    global _cache_instance
    
    if _cache_instance is not None:
        await _cache_instance.disconnect()
        _cache_instance = None


# ============================================================================
# 缓存装饰器
# ============================================================================

def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    data_type: Optional[str] = None,
    key_builder: Optional[Callable[..., str]] = None
):
    """
    缓存装饰器
    
    Args:
        key_prefix: 缓存键前缀
        ttl: TTL 秒数（可选）
        data_type: 数据类型，用于确定 TTL（可选）
        key_builder: 自定义键构建函数（可选）
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            # 构建缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认使用参数构建键
                key_parts = [key_prefix]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # 获取缓存实例
            cache = await get_cache()
            
            # 使用 cache-aside 模式
            return await cache.get_or_set(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl=ttl,
                data_type=data_type
            )
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    缓存失效装饰器
    
    在函数执行后失效匹配模式的缓存
    
    Args:
        pattern: 缓存键模式
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            result = await func(*args, **kwargs)
            
            # 失效缓存
            cache = await get_cache()
            await cache.invalidate_pattern(pattern)
            
            return result
        
        return wrapper
    return decorator
