"""
本体专家协作性能缓存模块

提供高性能缓存支持：
- Redis 缓存集成
- 模板缓存 (TTL: 1小时)
- 验证规则缓存 (TTL: 30分钟)
- 专家推荐缓存 (TTL: 15分钟)
- 缓存失效机制

Validates: Task 28.1 - Add caching for frequently accessed data
"""

import logging
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, TypeVar, Generic, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheType(str, Enum):
    """缓存类型"""
    TEMPLATE = "template"
    VALIDATION_RULE = "validation_rule"
    EXPERT_RECOMMENDATION = "expert_recommendation"
    COLLABORATION_SESSION = "collaboration_session"
    APPROVAL_CHAIN = "approval_chain"
    IMPACT_ANALYSIS = "impact_analysis"
    TRANSLATION = "translation"
    BEST_PRACTICE = "best_practice"


# 缓存 TTL 配置 (秒)
CACHE_TTL_CONFIG: Dict[CacheType, int] = {
    CacheType.TEMPLATE: 3600,              # 1 小时
    CacheType.VALIDATION_RULE: 1800,       # 30 分钟
    CacheType.EXPERT_RECOMMENDATION: 900,  # 15 分钟
    CacheType.COLLABORATION_SESSION: 300,  # 5 分钟
    CacheType.APPROVAL_CHAIN: 1800,        # 30 分钟
    CacheType.IMPACT_ANALYSIS: 600,        # 10 分钟
    CacheType.TRANSLATION: 3600,           # 1 小时
    CacheType.BEST_PRACTICE: 1800,         # 30 分钟
}


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    key: str
    value: T
    cache_type: CacheType
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def increment_hit(self) -> None:
        """增加命中计数"""
        self.hit_count += 1


@dataclass
class CacheStats:
    """缓存统计"""
    total_entries: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_usage_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class InMemoryCache:
    """
    内存缓存实现
    
    用于开发和测试环境，生产环境应使用 RedisCache
    """
    
    def __init__(self, max_size: int = 10000):
        """
        初始化内存缓存
        
        Args:
            max_size: 最大缓存条目数
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
        
        logger.info(f"InMemoryCache initialized with max_size={max_size}")
    
    def _generate_key(self, cache_type: CacheType, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [cache_type.value]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(
        self,
        cache_type: CacheType,
        key: str,
    ) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            cache_type: 缓存类型
            key: 缓存键
            
        Returns:
            缓存值或 None
        """
        full_key = f"{cache_type.value}:{key}"
        
        async with self._lock:
            entry = self._cache.get(full_key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired():
                del self._cache[full_key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            entry.increment_hit()
            self._stats.hits += 1
            return entry.value
    
    async def set(
        self,
        cache_type: CacheType,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值
        
        Args:
            cache_type: 缓存类型
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认值
            
        Returns:
            是否成功
        """
        full_key = f"{cache_type.value}:{key}"
        
        if ttl is None:
            ttl = CACHE_TTL_CONFIG.get(cache_type, 3600)
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        entry = CacheEntry(
            key=full_key,
            value=value,
            cache_type=cache_type,
            expires_at=expires_at,
        )
        
        async with self._lock:
            # 检查是否需要驱逐
            if len(self._cache) >= self._max_size:
                await self._evict_lru()
            
            self._cache[full_key] = entry
            self._stats.total_entries = len(self._cache)
            
        return True
    
    async def delete(
        self,
        cache_type: CacheType,
        key: str,
    ) -> bool:
        """
        删除缓存值
        
        Args:
            cache_type: 缓存类型
            key: 缓存键
            
        Returns:
            是否成功
        """
        full_key = f"{cache_type.value}:{key}"
        
        async with self._lock:
            if full_key in self._cache:
                del self._cache[full_key]
                self._stats.total_entries = len(self._cache)
                return True
        
        return False
    
    async def invalidate_by_type(self, cache_type: CacheType) -> int:
        """
        按类型失效缓存
        
        Args:
            cache_type: 缓存类型
            
        Returns:
            失效的条目数
        """
        prefix = f"{cache_type.value}:"
        count = 0
        
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if k.startswith(prefix)
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
            
            self._stats.total_entries = len(self._cache)
            self._stats.evictions += count
        
        return count
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """
        按模式失效缓存
        
        Args:
            pattern: 键模式（支持 * 通配符）
            
        Returns:
            失效的条目数
        """
        import fnmatch
        count = 0
        
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if fnmatch.fnmatch(k, pattern)
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
            
            self._stats.total_entries = len(self._cache)
            self._stats.evictions += count
        
        return count
    
    async def clear(self) -> int:
        """
        清空所有缓存
        
        Returns:
            清除的条目数
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.total_entries = 0
            self._stats.evictions += count
            return count
    
    async def _evict_lru(self) -> None:
        """驱逐最少使用的条目"""
        if not self._cache:
            return
        
        # 找到命中次数最少的条目
        min_entry = min(
            self._cache.items(),
            key=lambda x: (x[1].hit_count, x[1].created_at)
        )
        
        del self._cache[min_entry[0]]
        self._stats.evictions += 1
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        async with self._lock:
            return {
                "total_entries": self._stats.total_entries,
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "evictions": self._stats.evictions,
                "hit_rate": self._stats.hit_rate,
                "max_size": self._max_size,
            }
    
    async def cleanup_expired(self) -> int:
        """清理过期条目"""
        count = 0
        
        async with self._lock:
            keys_to_delete = [
                k for k, v in self._cache.items()
                if v.is_expired()
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
            
            self._stats.total_entries = len(self._cache)
            self._stats.evictions += count
        
        return count


class RedisCache:
    """
    Redis 缓存实现
    
    用于生产环境，支持分布式缓存
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "ontology_collab:",
    ):
        """
        初始化 Redis 缓存
        
        Args:
            redis_url: Redis 连接 URL
            key_prefix: 键前缀
        """
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._redis = None
        self._stats = CacheStats()
        
        logger.info(f"RedisCache initialized with prefix={key_prefix}")
    
    async def _get_redis(self):
        """获取 Redis 连接"""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self._redis_url)
            except ImportError:
                logger.warning("redis package not installed, using in-memory fallback")
                return None
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                return None
        return self._redis
    
    def _make_key(self, cache_type: CacheType, key: str) -> str:
        """生成完整的 Redis 键"""
        return f"{self._key_prefix}{cache_type.value}:{key}"
    
    async def get(
        self,
        cache_type: CacheType,
        key: str,
    ) -> Optional[Any]:
        """获取缓存值"""
        redis = await self._get_redis()
        if redis is None:
            return None
        
        full_key = self._make_key(cache_type, key)
        
        try:
            value = await redis.get(full_key)
            if value is None:
                self._stats.misses += 1
                return None
            
            self._stats.hits += 1
            return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self._stats.misses += 1
            return None
    
    async def set(
        self,
        cache_type: CacheType,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置缓存值"""
        redis = await self._get_redis()
        if redis is None:
            return False
        
        full_key = self._make_key(cache_type, key)
        
        if ttl is None:
            ttl = CACHE_TTL_CONFIG.get(cache_type, 3600)
        
        try:
            await redis.setex(full_key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(
        self,
        cache_type: CacheType,
        key: str,
    ) -> bool:
        """删除缓存值"""
        redis = await self._get_redis()
        if redis is None:
            return False
        
        full_key = self._make_key(cache_type, key)
        
        try:
            await redis.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def invalidate_by_type(self, cache_type: CacheType) -> int:
        """按类型失效缓存"""
        redis = await self._get_redis()
        if redis is None:
            return 0
        
        pattern = f"{self._key_prefix}{cache_type.value}:*"
        
        try:
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await redis.delete(*keys)
            
            self._stats.evictions += len(keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis invalidate error: {e}")
            return 0
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """按模式失效缓存"""
        redis = await self._get_redis()
        if redis is None:
            return 0
        
        full_pattern = f"{self._key_prefix}{pattern}"
        
        try:
            keys = []
            async for key in redis.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                await redis.delete(*keys)
            
            self._stats.evictions += len(keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis invalidate error: {e}")
            return 0
    
    async def clear(self) -> int:
        """清空所有缓存"""
        redis = await self._get_redis()
        if redis is None:
            return 0
        
        pattern = f"{self._key_prefix}*"
        
        try:
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await redis.delete(*keys)
            
            return len(keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        redis = await self._get_redis()
        
        stats = {
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "evictions": self._stats.evictions,
            "hit_rate": self._stats.hit_rate,
        }
        
        if redis:
            try:
                info = await redis.info("memory")
                stats["memory_usage_bytes"] = info.get("used_memory", 0)
            except Exception:
                pass
        
        return stats
    
    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None


class CollaborationCacheService:
    """
    协作缓存服务
    
    提供统一的缓存接口，支持内存和 Redis 后端
    """
    
    def __init__(
        self,
        use_redis: bool = False,
        redis_url: str = "redis://localhost:6379",
    ):
        """
        初始化缓存服务
        
        Args:
            use_redis: 是否使用 Redis
            redis_url: Redis 连接 URL
        """
        if use_redis:
            self._cache = RedisCache(redis_url=redis_url)
        else:
            self._cache = InMemoryCache()
        
        self._use_redis = use_redis
        logger.info(f"CollaborationCacheService initialized (redis={use_redis})")
    
    # ========================================================================
    # 模板缓存
    # ========================================================================
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板缓存"""
        return await self._cache.get(CacheType.TEMPLATE, template_id)
    
    async def set_template(
        self,
        template_id: str,
        template: Dict[str, Any],
    ) -> bool:
        """设置模板缓存"""
        return await self._cache.set(CacheType.TEMPLATE, template_id, template)
    
    async def invalidate_template(self, template_id: str) -> bool:
        """失效模板缓存"""
        return await self._cache.delete(CacheType.TEMPLATE, template_id)
    
    async def invalidate_all_templates(self) -> int:
        """失效所有模板缓存"""
        return await self._cache.invalidate_by_type(CacheType.TEMPLATE)
    
    # ========================================================================
    # 验证规则缓存
    # ========================================================================
    
    async def get_validation_rules(
        self,
        region: str,
        industry: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """获取验证规则缓存"""
        key = f"{region}:{industry}"
        return await self._cache.get(CacheType.VALIDATION_RULE, key)
    
    async def set_validation_rules(
        self,
        region: str,
        industry: str,
        rules: List[Dict[str, Any]],
    ) -> bool:
        """设置验证规则缓存"""
        key = f"{region}:{industry}"
        return await self._cache.set(CacheType.VALIDATION_RULE, key, rules)
    
    async def invalidate_validation_rules(
        self,
        region: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> int:
        """失效验证规则缓存"""
        if region and industry:
            key = f"{region}:{industry}"
            await self._cache.delete(CacheType.VALIDATION_RULE, key)
            return 1
        elif region:
            return await self._cache.invalidate_by_pattern(
                f"{CacheType.VALIDATION_RULE.value}:{region}:*"
            )
        else:
            return await self._cache.invalidate_by_type(CacheType.VALIDATION_RULE)
    
    # ========================================================================
    # 专家推荐缓存
    # ========================================================================
    
    async def get_expert_recommendations(
        self,
        ontology_area: str,
        limit: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        """获取专家推荐缓存"""
        key = f"{ontology_area}:{limit}"
        return await self._cache.get(CacheType.EXPERT_RECOMMENDATION, key)
    
    async def set_expert_recommendations(
        self,
        ontology_area: str,
        limit: int,
        recommendations: List[Dict[str, Any]],
    ) -> bool:
        """设置专家推荐缓存"""
        key = f"{ontology_area}:{limit}"
        return await self._cache.set(
            CacheType.EXPERT_RECOMMENDATION, key, recommendations
        )
    
    async def invalidate_expert_recommendations(
        self,
        ontology_area: Optional[str] = None,
    ) -> int:
        """失效专家推荐缓存"""
        if ontology_area:
            return await self._cache.invalidate_by_pattern(
                f"{CacheType.EXPERT_RECOMMENDATION.value}:{ontology_area}:*"
            )
        else:
            return await self._cache.invalidate_by_type(CacheType.EXPERT_RECOMMENDATION)
    
    # ========================================================================
    # 影响分析缓存
    # ========================================================================
    
    async def get_impact_analysis(
        self,
        element_id: str,
        change_type: str,
    ) -> Optional[Dict[str, Any]]:
        """获取影响分析缓存"""
        key = f"{element_id}:{change_type}"
        return await self._cache.get(CacheType.IMPACT_ANALYSIS, key)
    
    async def set_impact_analysis(
        self,
        element_id: str,
        change_type: str,
        analysis: Dict[str, Any],
    ) -> bool:
        """设置影响分析缓存"""
        key = f"{element_id}:{change_type}"
        return await self._cache.set(CacheType.IMPACT_ANALYSIS, key, analysis)
    
    async def invalidate_impact_analysis(
        self,
        element_id: Optional[str] = None,
    ) -> int:
        """失效影响分析缓存"""
        if element_id:
            return await self._cache.invalidate_by_pattern(
                f"{CacheType.IMPACT_ANALYSIS.value}:{element_id}:*"
            )
        else:
            return await self._cache.invalidate_by_type(CacheType.IMPACT_ANALYSIS)
    
    # ========================================================================
    # 翻译缓存
    # ========================================================================
    
    async def get_translation(
        self,
        element_id: str,
        language: str,
    ) -> Optional[Dict[str, Any]]:
        """获取翻译缓存"""
        key = f"{element_id}:{language}"
        return await self._cache.get(CacheType.TRANSLATION, key)
    
    async def set_translation(
        self,
        element_id: str,
        language: str,
        translation: Dict[str, Any],
    ) -> bool:
        """设置翻译缓存"""
        key = f"{element_id}:{language}"
        return await self._cache.set(CacheType.TRANSLATION, key, translation)
    
    async def invalidate_translation(
        self,
        element_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> int:
        """失效翻译缓存"""
        if element_id and language:
            key = f"{element_id}:{language}"
            await self._cache.delete(CacheType.TRANSLATION, key)
            return 1
        elif element_id:
            return await self._cache.invalidate_by_pattern(
                f"{CacheType.TRANSLATION.value}:{element_id}:*"
            )
        else:
            return await self._cache.invalidate_by_type(CacheType.TRANSLATION)
    
    # ========================================================================
    # 最佳实践缓存
    # ========================================================================
    
    async def get_best_practice(
        self,
        practice_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取最佳实践缓存"""
        return await self._cache.get(CacheType.BEST_PRACTICE, practice_id)
    
    async def set_best_practice(
        self,
        practice_id: str,
        practice: Dict[str, Any],
    ) -> bool:
        """设置最佳实践缓存"""
        return await self._cache.set(CacheType.BEST_PRACTICE, practice_id, practice)
    
    async def invalidate_best_practice(
        self,
        practice_id: Optional[str] = None,
    ) -> int:
        """失效最佳实践缓存"""
        if practice_id:
            await self._cache.delete(CacheType.BEST_PRACTICE, practice_id)
            return 1
        else:
            return await self._cache.invalidate_by_type(CacheType.BEST_PRACTICE)
    
    # ========================================================================
    # 通用方法
    # ========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return await self._cache.get_stats()
    
    async def clear_all(self) -> int:
        """清空所有缓存"""
        return await self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        if isinstance(self._cache, InMemoryCache):
            return await self._cache.cleanup_expired()
        return 0  # Redis 自动处理过期


# 缓存装饰器
def cached(
    cache_type: CacheType,
    key_func: Optional[Callable[..., str]] = None,
    ttl: Optional[int] = None,
):
    """
    缓存装饰器
    
    用法:
        @cached(CacheType.TEMPLATE, key_func=lambda template_id: template_id)
        async def get_template(template_id: str) -> Dict[str, Any]:
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取缓存服务
            cache_service = get_collaboration_cache_service()
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = hashlib.md5(
                    f"{args}:{kwargs}".encode()
                ).hexdigest()
            
            # 尝试从缓存获取
            cached_value = await cache_service._cache.get(cache_type, cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            if result is not None:
                await cache_service._cache.set(
                    cache_type, cache_key, result, ttl
                )
            
            return result
        
        return wrapper
    return decorator


# 全局实例
_cache_service: Optional[CollaborationCacheService] = None


def get_collaboration_cache_service(
    use_redis: bool = False,
    redis_url: str = "redis://localhost:6379",
) -> CollaborationCacheService:
    """获取或创建全局缓存服务实例"""
    global _cache_service
    
    if _cache_service is None:
        _cache_service = CollaborationCacheService(
            use_redis=use_redis,
            redis_url=redis_url,
        )
    
    return _cache_service


def reset_cache_service() -> None:
    """重置缓存服务（用于测试）"""
    global _cache_service
    _cache_service = None
