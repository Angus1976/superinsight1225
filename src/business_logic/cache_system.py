#!/usr/bin/env python3
"""
增强缓存系统
实现多层缓存机制，优化查询速度，支持智能缓存策略

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 49.1
"""

import asyncio
import logging
import time
import hashlib
import pickle
import json
import zlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import threading
from collections import OrderedDict, defaultdict

# Optional dependencies
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not available, using memory cache only")

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False
    logger.warning("aioredis not available, using memory cache only")

class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "l1_memory"      # 内存缓存
    L2_REDIS = "l2_redis"        # Redis缓存
    L3_PERSISTENT = "l3_persistent"  # 持久化缓存

class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"                  # 最近最少使用
    LFU = "lfu"                  # 最少使用频率
    TTL = "ttl"                  # 基于时间
    ADAPTIVE = "adaptive"        # 自适应策略

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl: int
    size_bytes: int
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    @property
    def age_seconds(self) -> float:
        """获取年龄(秒)"""
        return (datetime.now() - self.created_at).total_seconds()

@dataclass
class CacheStats:
    """缓存统计"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    memory_usage_bytes: int = 0
    average_response_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """未命中率"""
        return 1.0 - self.hit_rate

class LRUCache:
    """LRU内存缓存"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        """初始化LRU缓存"""
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.stats = CacheStats()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            self.stats.total_requests += 1
            
            if key in self.cache:
                entry = self.cache[key]
                
                # 检查是否过期
                if entry.is_expired:
                    del self.cache[key]
                    self.stats.cache_misses += 1
                    return None
                
                # 更新访问信息
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                entry.hit_count += 1
                
                # 移到末尾(最近使用)
                self.cache.move_to_end(key)
                
                self.stats.cache_hits += 1
                return entry.value
            
            self.stats.cache_misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        with self.lock:
            try:
                # 序列化并计算大小
                serialized_value = pickle.dumps(value)
                size_bytes = len(serialized_value)
                
                # 检查内存限制
                if size_bytes > self.max_memory_bytes:
                    logger.warning(f"缓存项过大，跳过: {size_bytes} bytes")
                    return False
                
                # 创建缓存条目
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=1,
                    ttl=ttl,
                    size_bytes=size_bytes
                )
                
                # 如果键已存在，更新
                if key in self.cache:
                    old_entry = self.cache[key]
                    self.stats.memory_usage_bytes -= old_entry.size_bytes
                
                # 添加新条目
                self.cache[key] = entry
                self.stats.memory_usage_bytes += size_bytes
                
                # 检查是否需要清理
                self._evict_if_needed()
                
                return True
                
            except Exception as e:
                logger.error(f"设置缓存失败: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                entry = self.cache.pop(key)
                self.stats.memory_usage_bytes -= entry.size_bytes
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.stats.memory_usage_bytes = 0
    
    def _evict_if_needed(self):
        """根据需要清理缓存"""
        # 按大小清理
        while len(self.cache) > self.max_size:
            self._evict_lru()
        
        # 按内存清理
        while self.stats.memory_usage_bytes > self.max_memory_bytes:
            if not self._evict_lru():
                break
    
    def _evict_lru(self) -> bool:
        """清理最近最少使用的项"""
        if not self.cache:
            return False
        
        # 获取最旧的项
        key, entry = self.cache.popitem(last=False)
        self.stats.memory_usage_bytes -= entry.size_bytes
        self.stats.evictions += 1
        
        logger.debug(f"清理LRU缓存项: {key}")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            return {
                "cache_type": "LRU",
                "total_items": len(self.cache),
                "max_size": self.max_size,
                "memory_usage_mb": self.stats.memory_usage_bytes / 1024 / 1024,
                "max_memory_mb": self.max_memory_bytes / 1024 / 1024,
                "hit_rate": self.stats.hit_rate,
                "miss_rate": self.stats.miss_rate,
                "total_requests": self.stats.total_requests,
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses,
                "evictions": self.stats.evictions
            }

class RedisCache:
    """Redis缓存"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 1):
        """初始化Redis缓存"""
        self.redis_url = redis_url
        self.db = db
        self.redis_client = None
        self.stats = CacheStats()
        self.key_prefix = "bl_cache:"
        
    async def initialize(self):
        """初始化Redis连接"""
        if not AIOREDIS_AVAILABLE:
            logger.warning("aioredis not available, Redis cache disabled")
            return False
            
        try:
            self.redis_client = await aioredis.from_url(f"{self.redis_url}/{self.db}")
            await self.redis_client.ping()
            logger.info("Redis缓存连接成功")
            return True
        except Exception as e:
            logger.error(f"Redis缓存连接失败: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.redis_client:
            return None
        
        try:
            self.stats.total_requests += 1
            
            # 获取压缩数据
            compressed_data = await self.redis_client.get(f"{self.key_prefix}{key}")
            
            if compressed_data:
                # 解压缩和反序列化
                decompressed_data = zlib.decompress(compressed_data)
                value = pickle.loads(decompressed_data)
                
                self.stats.cache_hits += 1
                
                # 更新访问时间
                await self.redis_client.hset(
                    f"{self.key_prefix}meta:{key}",
                    "last_accessed",
                    datetime.now().isoformat()
                )
                
                return value
            
            self.stats.cache_misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Redis获取缓存失败: {e}")
            self.stats.cache_misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        if not self.redis_client:
            return False
        
        try:
            # 序列化和压缩
            serialized_data = pickle.dumps(value)
            compressed_data = zlib.compress(serialized_data)
            
            # 设置缓存值
            await self.redis_client.setex(
                f"{self.key_prefix}{key}",
                ttl,
                compressed_data
            )
            
            # 设置元数据
            metadata = {
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "size_bytes": len(compressed_data),
                "ttl": ttl
            }
            
            await self.redis_client.hset(
                f"{self.key_prefix}meta:{key}",
                mapping=metadata
            )
            await self.redis_client.expire(f"{self.key_prefix}meta:{key}", ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"Redis设置缓存失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存项"""
        if not self.redis_client:
            return False
        
        try:
            # 删除数据和元数据
            deleted_count = await self.redis_client.delete(
                f"{self.key_prefix}{key}",
                f"{self.key_prefix}meta:{key}"
            )
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Redis删除缓存失败: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """清空所有缓存"""
        if not self.redis_client:
            return False
        
        try:
            # 获取所有相关键
            keys = await self.redis_client.keys(f"{self.key_prefix}*")
            if keys:
                await self.redis_client.delete(*keys)
            return True
            
        except Exception as e:
            logger.error(f"Redis清空缓存失败: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            if not self.redis_client:
                return {"error": "Redis未连接"}
            
            # 获取键数量
            keys = await self.redis_client.keys(f"{self.key_prefix}*")
            data_keys = [k for k in keys if not k.decode().endswith(":meta")]
            
            # 计算总大小
            total_size = 0
            if data_keys:
                sizes = await self.redis_client.mget(data_keys)
                total_size = sum(len(s) if s else 0 for s in sizes)
            
            return {
                "cache_type": "Redis",
                "total_items": len(data_keys),
                "memory_usage_mb": total_size / 1024 / 1024,
                "hit_rate": self.stats.hit_rate,
                "miss_rate": self.stats.miss_rate,
                "total_requests": self.stats.total_requests,
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses
            }
            
        except Exception as e:
            logger.error(f"获取Redis统计失败: {e}")
            return {"error": str(e)}

class MultiLevelCache:
    """多级缓存系统"""
    
    def __init__(self, 
                 l1_max_size: int = 1000,
                 l1_max_memory_mb: int = 100,
                 redis_url: str = "redis://localhost:6379"):
        """初始化多级缓存"""
        self.l1_cache = LRUCache(l1_max_size, l1_max_memory_mb)
        self.l2_cache = RedisCache(redis_url)
        self.stats = CacheStats()
        self.cache_strategy = CacheStrategy.ADAPTIVE
        
    async def initialize(self):
        """初始化缓存系统"""
        await self.l2_cache.initialize()
        logger.info("多级缓存系统初始化完成")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        start_time = time.time()
        self.stats.total_requests += 1
        
        try:
            # L1缓存查找
            value = self.l1_cache.get(key)
            if value is not None:
                self.stats.cache_hits += 1
                self._update_response_time(start_time)
                logger.debug(f"L1缓存命中: {key}")
                return value
            
            # L2缓存查找
            value = await self.l2_cache.get(key)
            if value is not None:
                # 回填到L1缓存
                self.l1_cache.set(key, value)
                self.stats.cache_hits += 1
                self._update_response_time(start_time)
                logger.debug(f"L2缓存命中: {key}")
                return value
            
            # 缓存未命中
            self.stats.cache_misses += 1
            self._update_response_time(start_time)
            return None
            
        except Exception as e:
            logger.error(f"多级缓存获取失败: {e}")
            self.stats.cache_misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        try:
            # 根据策略决定缓存级别
            cache_levels = self._determine_cache_levels(key, value, ttl)
            
            success = True
            
            # L1缓存
            if CacheLevel.L1_MEMORY in cache_levels:
                success &= self.l1_cache.set(key, value, ttl)
            
            # L2缓存
            if CacheLevel.L2_REDIS in cache_levels:
                success &= await self.l2_cache.set(key, value, ttl)
            
            return success
            
        except Exception as e:
            logger.error(f"多级缓存设置失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存项"""
        try:
            l1_success = self.l1_cache.delete(key)
            l2_success = await self.l2_cache.delete(key)
            return l1_success or l2_success
            
        except Exception as e:
            logger.error(f"多级缓存删除失败: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """清空所有缓存"""
        try:
            self.l1_cache.clear()
            await self.l2_cache.clear_all()
            return True
            
        except Exception as e:
            logger.error(f"多级缓存清空失败: {e}")
            return False
    
    def _determine_cache_levels(self, key: str, value: Any, ttl: int) -> List[CacheLevel]:
        """确定缓存级别"""
        levels = []
        
        try:
            # 计算值的大小
            serialized_size = len(pickle.dumps(value))
            
            # 自适应策略
            if self.cache_strategy == CacheStrategy.ADAPTIVE:
                # 小数据优先L1缓存
                if serialized_size < 10 * 1024:  # 10KB
                    levels.append(CacheLevel.L1_MEMORY)
                
                # 所有数据都缓存到L2
                levels.append(CacheLevel.L2_REDIS)
                
                # 长期数据考虑L3持久化
                if ttl > 24 * 3600:  # 超过1天
                    levels.append(CacheLevel.L3_PERSISTENT)
            
            else:
                # 默认策略：都缓存
                levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]
            
        except Exception as e:
            logger.error(f"确定缓存级别失败: {e}")
            levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]
        
        return levels
    
    def _update_response_time(self, start_time: float):
        """更新响应时间"""
        response_time_ms = (time.time() - start_time) * 1000
        
        # 简单的移动平均
        if self.stats.average_response_time_ms == 0:
            self.stats.average_response_time_ms = response_time_ms
        else:
            self.stats.average_response_time_ms = (
                self.stats.average_response_time_ms * 0.9 + response_time_ms * 0.1
            )
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        l1_stats = self.l1_cache.get_stats()
        l2_stats = await self.l2_cache.get_stats()
        
        return {
            "multi_level_cache": {
                "total_requests": self.stats.total_requests,
                "total_hits": self.stats.cache_hits,
                "total_misses": self.stats.cache_misses,
                "overall_hit_rate": self.stats.hit_rate,
                "average_response_time_ms": round(self.stats.average_response_time_ms, 2),
                "cache_strategy": self.cache_strategy.value
            },
            "l1_memory_cache": l1_stats,
            "l2_redis_cache": l2_stats
        }

class SmartCacheManager:
    """智能缓存管理器"""
    
    def __init__(self):
        """初始化智能缓存管理器"""
        self.cache = MultiLevelCache()
        self.access_patterns = defaultdict(list)
        self.cache_effectiveness = defaultdict(float)
        
    async def initialize(self):
        """初始化缓存管理器"""
        await self.cache.initialize()
        logger.info("智能缓存管理器初始化完成")
    
    def cached_function(self, ttl: int = 3600, key_generator: Callable = None):
        """智能缓存装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_generator:
                    cache_key = key_generator(*args, **kwargs)
                else:
                    cache_key = self._generate_cache_key(func.__name__, args, kwargs)
                
                # 记录访问模式
                self._record_access_pattern(cache_key)
                
                # 尝试从缓存获取
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    self._update_cache_effectiveness(cache_key, True)
                    return cached_result
                
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 智能决定是否缓存
                if self._should_cache(cache_key, result):
                    adaptive_ttl = self._calculate_adaptive_ttl(cache_key, ttl)
                    await self.cache.set(cache_key, result, adaptive_ttl)
                
                self._update_cache_effectiveness(cache_key, False)
                return result
                
            return wrapper
        return decorator
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        key_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _record_access_pattern(self, cache_key: str):
        """记录访问模式"""
        now = datetime.now()
        self.access_patterns[cache_key].append(now)
        
        # 只保留最近的访问记录
        cutoff_time = now - timedelta(hours=24)
        self.access_patterns[cache_key] = [
            access_time for access_time in self.access_patterns[cache_key]
            if access_time > cutoff_time
        ]
    
    def _should_cache(self, cache_key: str, result: Any) -> bool:
        """智能决定是否应该缓存"""
        try:
            # 检查结果大小
            result_size = len(pickle.dumps(result))
            if result_size > 1024 * 1024:  # 1MB
                return False
            
            # 检查访问频率
            access_count = len(self.access_patterns.get(cache_key, []))
            if access_count < 2:  # 访问次数太少
                return False
            
            # 检查缓存效果
            effectiveness = self.cache_effectiveness.get(cache_key, 0.0)
            if effectiveness < 0.3:  # 效果太差
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"缓存决策失败: {e}")
            return True  # 默认缓存
    
    def _calculate_adaptive_ttl(self, cache_key: str, base_ttl: int) -> int:
        """计算自适应TTL"""
        try:
            access_times = self.access_patterns.get(cache_key, [])
            if len(access_times) < 2:
                return base_ttl
            
            # 计算访问间隔
            intervals = []
            for i in range(1, len(access_times)):
                interval = (access_times[i] - access_times[i-1]).total_seconds()
                intervals.append(interval)
            
            # 基于访问模式调整TTL
            avg_interval = sum(intervals) / len(intervals)
            
            if avg_interval < 300:  # 5分钟内频繁访问
                return min(base_ttl * 2, 7200)  # 延长TTL，最多2小时
            elif avg_interval > 3600:  # 访问间隔超过1小时
                return max(base_ttl // 2, 300)  # 缩短TTL，最少5分钟
            
            return base_ttl
            
        except Exception as e:
            logger.error(f"计算自适应TTL失败: {e}")
            return base_ttl
    
    def _update_cache_effectiveness(self, cache_key: str, cache_hit: bool):
        """更新缓存效果"""
        current_effectiveness = self.cache_effectiveness.get(cache_key, 0.5)
        
        if cache_hit:
            # 缓存命中，提高效果评分
            new_effectiveness = min(current_effectiveness + 0.1, 1.0)
        else:
            # 缓存未命中，降低效果评分
            new_effectiveness = max(current_effectiveness - 0.05, 0.0)
        
        self.cache_effectiveness[cache_key] = new_effectiveness
    
    async def get_cache_analytics(self) -> Dict[str, Any]:
        """获取缓存分析"""
        stats = await self.cache.get_comprehensive_stats()
        
        # 分析访问模式
        pattern_analysis = {}
        for cache_key, access_times in self.access_patterns.items():
            if len(access_times) > 1:
                intervals = []
                for i in range(1, len(access_times)):
                    interval = (access_times[i] - access_times[i-1]).total_seconds()
                    intervals.append(interval)
                
                pattern_analysis[cache_key] = {
                    "access_count": len(access_times),
                    "avg_interval_seconds": sum(intervals) / len(intervals),
                    "effectiveness": self.cache_effectiveness.get(cache_key, 0.0)
                }
        
        # 找出热点数据
        hot_keys = sorted(
            pattern_analysis.items(),
            key=lambda x: x[1]["access_count"],
            reverse=True
        )[:10]
        
        return {
            "cache_stats": stats,
            "access_patterns": {
                "total_tracked_keys": len(self.access_patterns),
                "hot_keys": [{"key": k, "stats": v} for k, v in hot_keys],
                "average_effectiveness": sum(self.cache_effectiveness.values()) / len(self.cache_effectiveness) if self.cache_effectiveness else 0.0
            }
        }

# 全局智能缓存管理器实例
smart_cache_manager = SmartCacheManager()

# 便捷装饰器
def smart_cache(ttl: int = 3600, key_generator: Callable = None):
    """智能缓存装饰器"""
    return smart_cache_manager.cached_function(ttl, key_generator)

# 初始化函数
async def initialize_cache_system():
    """初始化缓存系统"""
    await smart_cache_manager.initialize()
    logger.info("缓存系统初始化完成")