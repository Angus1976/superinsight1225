"""
Multi-Tenant Caching System
多租户缓存系统实现
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union, Set
from datetime import datetime, timedelta
import hashlib
import redis.asyncio as redis
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class TenantAwareCache:
    """租户感知的缓存系统"""
    
    def __init__(self, redis_client: redis.Redis, default_ttl: int = 3600):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = "superinsight"
        self.tenant_prefix = "tenant"
        self.workspace_prefix = "workspace"
        
        # 缓存统计
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'invalidations': 0
        }
        
        # 缓存策略配置
        self.cache_policies = {
            'user_permissions': {'ttl': 1800, 'invalidate_on_change': True},
            'tenant_config': {'ttl': 3600, 'invalidate_on_change': True},
            'workspace_settings': {'ttl': 1800, 'invalidate_on_change': True},
            'api_responses': {'ttl': 300, 'invalidate_on_change': False},
            'query_results': {'ttl': 600, 'invalidate_on_change': False},
            'session_data': {'ttl': 7200, 'invalidate_on_change': True}
        }
    
    def _build_key(self, tenant_id: str, workspace_id: Optional[str], 
                   cache_type: str, key: str) -> str:
        """构建租户感知的缓存键"""
        parts = [self.key_prefix, self.tenant_prefix, tenant_id]
        
        if workspace_id:
            parts.extend([self.workspace_prefix, workspace_id])
        
        parts.extend([cache_type, key])
        
        # 使用冒号分隔符，便于Redis键空间分析
        return ":".join(parts)
    
    def _build_pattern(self, tenant_id: Optional[str] = None, 
                      workspace_id: Optional[str] = None,
                      cache_type: Optional[str] = None) -> str:
        """构建缓存键模式用于批量操作"""
        parts = [self.key_prefix]
        
        if tenant_id:
            parts.extend([self.tenant_prefix, tenant_id])
            
            if workspace_id:
                parts.extend([self.workspace_prefix, workspace_id])
            else:
                parts.append("*")
        else:
            parts.append("*")
        
        if cache_type:
            parts.append(cache_type)
        else:
            parts.append("*")
        
        parts.append("*")
        
        return ":".join(parts)
    
    async def get(self, tenant_id: str, cache_type: str, key: str, 
                  workspace_id: Optional[str] = None) -> Optional[Any]:
        """获取缓存值"""
        cache_key = self._build_key(tenant_id, workspace_id, cache_type, key)
        
        try:
            value = await self.redis_client.get(cache_key)
            
            if value is not None:
                self.stats['hits'] += 1
                return json.loads(value)
            else:
                self.stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"获取缓存失败 {cache_key}: {e}")
            self.stats['misses'] += 1
            return None
    
    async def set(self, tenant_id: str, cache_type: str, key: str, value: Any,
                  workspace_id: Optional[str] = None, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        cache_key = self._build_key(tenant_id, workspace_id, cache_type, key)
        
        # 获取TTL配置
        if ttl is None:
            policy = self.cache_policies.get(cache_type, {})
            ttl = policy.get('ttl', self.default_ttl)
        
        try:
            serialized_value = json.dumps(value, default=str)
            
            if ttl > 0:
                await self.redis_client.setex(cache_key, ttl, serialized_value)
            else:
                await self.redis_client.set(cache_key, serialized_value)
            
            self.stats['sets'] += 1
            
            # 添加到租户键集合用于批量操作
            await self._add_to_tenant_keys(tenant_id, workspace_id, cache_key)
            
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败 {cache_key}: {e}")
            return False
    
    async def delete(self, tenant_id: str, cache_type: str, key: str,
                     workspace_id: Optional[str] = None) -> bool:
        """删除缓存值"""
        cache_key = self._build_key(tenant_id, workspace_id, cache_type, key)
        
        try:
            result = await self.redis_client.delete(cache_key)
            
            if result > 0:
                self.stats['deletes'] += 1
                await self._remove_from_tenant_keys(tenant_id, workspace_id, cache_key)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"删除缓存失败 {cache_key}: {e}")
            return False
    
    async def exists(self, tenant_id: str, cache_type: str, key: str,
                     workspace_id: Optional[str] = None) -> bool:
        """检查缓存是否存在"""
        cache_key = self._build_key(tenant_id, workspace_id, cache_type, key)
        
        try:
            return await self.redis_client.exists(cache_key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败 {cache_key}: {e}")
            return False
    
    async def invalidate_by_pattern(self, tenant_id: Optional[str] = None,
                                   workspace_id: Optional[str] = None,
                                   cache_type: Optional[str] = None) -> int:
        """根据模式批量失效缓存"""
        pattern = self._build_pattern(tenant_id, workspace_id, cache_type)
        
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self.stats['invalidations'] += deleted_count
                
                logger.info(f"批量失效缓存: {deleted_count} 个键, 模式: {pattern}")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"批量失效缓存失败, 模式 {pattern}: {e}")
            return 0
    
    async def invalidate_tenant_cache(self, tenant_id: str) -> int:
        """失效指定租户的所有缓存"""
        return await self.invalidate_by_pattern(tenant_id=tenant_id)
    
    async def invalidate_workspace_cache(self, tenant_id: str, workspace_id: str) -> int:
        """失效指定工作空间的所有缓存"""
        return await self.invalidate_by_pattern(tenant_id=tenant_id, workspace_id=workspace_id)
    
    async def invalidate_cache_type(self, cache_type: str, tenant_id: Optional[str] = None) -> int:
        """失效指定类型的缓存"""
        return await self.invalidate_by_pattern(tenant_id=tenant_id, cache_type=cache_type)
    
    async def _add_to_tenant_keys(self, tenant_id: str, workspace_id: Optional[str], 
                                 cache_key: str):
        """将键添加到租户键集合"""
        try:
            tenant_keys_set = f"{self.key_prefix}:tenant_keys:{tenant_id}"
            await self.redis_client.sadd(tenant_keys_set, cache_key)
            
            # 设置租户键集合的过期时间
            await self.redis_client.expire(tenant_keys_set, 86400)  # 24小时
            
            if workspace_id:
                workspace_keys_set = f"{self.key_prefix}:workspace_keys:{tenant_id}:{workspace_id}"
                await self.redis_client.sadd(workspace_keys_set, cache_key)
                await self.redis_client.expire(workspace_keys_set, 86400)
                
        except Exception as e:
            logger.error(f"添加到租户键集合失败: {e}")
    
    async def _remove_from_tenant_keys(self, tenant_id: str, workspace_id: Optional[str],
                                      cache_key: str):
        """从租户键集合中移除键"""
        try:
            tenant_keys_set = f"{self.key_prefix}:tenant_keys:{tenant_id}"
            await self.redis_client.srem(tenant_keys_set, cache_key)
            
            if workspace_id:
                workspace_keys_set = f"{self.key_prefix}:workspace_keys:{tenant_id}:{workspace_id}"
                await self.redis_client.srem(workspace_keys_set, cache_key)
                
        except Exception as e:
            logger.error(f"从租户键集合移除失败: {e}")
    
    async def get_tenant_cache_keys(self, tenant_id: str) -> Set[str]:
        """获取租户的所有缓存键"""
        try:
            tenant_keys_set = f"{self.key_prefix}:tenant_keys:{tenant_id}"
            keys = await self.redis_client.smembers(tenant_keys_set)
            return {key.decode() if isinstance(key, bytes) else key for key in keys}
        except Exception as e:
            logger.error(f"获取租户缓存键失败: {e}")
            return set()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            # Redis信息
            redis_info = await self.redis_client.info('memory')
            
            # 计算命中率
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cache_stats': self.stats.copy(),
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests,
                'redis_memory_used': redis_info.get('used_memory_human', 'N/A'),
                'redis_memory_peak': redis_info.get('used_memory_peak_human', 'N/A'),
                'redis_connected_clients': redis_info.get('connected_clients', 0)
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {'error': str(e)}
    
    async def warm_up_cache(self, tenant_id: str, cache_data: Dict[str, Any]):
        """预热缓存"""
        try:
            warmed_count = 0
            
            for cache_type, data in cache_data.items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        success = await self.set(tenant_id, cache_type, key, value)
                        if success:
                            warmed_count += 1
            
            logger.info(f"租户 {tenant_id} 缓存预热完成: {warmed_count} 个键")
            return warmed_count
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")
            return 0
    
    @asynccontextmanager
    async def cache_lock(self, tenant_id: str, lock_key: str, timeout: int = 30):
        """分布式缓存锁"""
        lock_cache_key = self._build_key(tenant_id, None, "locks", lock_key)
        lock_acquired = False
        
        try:
            # 尝试获取锁
            lock_acquired = await self.redis_client.set(
                lock_cache_key, 
                "locked", 
                nx=True, 
                ex=timeout
            )
            
            if not lock_acquired:
                raise Exception(f"无法获取锁: {lock_key}")
            
            yield
            
        finally:
            if lock_acquired:
                await self.redis_client.delete(lock_cache_key)


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.cache: Optional[TenantAwareCache] = None
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """初始化缓存管理器"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # 测试连接
            await self.redis_client.ping()
            
            self.cache = TenantAwareCache(self.redis_client)
            
            logger.info("缓存管理器初始化成功")
            
        except Exception as e:
            logger.error(f"缓存管理器初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭缓存连接"""
        if self.redis_client:
            await self.redis_client.close()
    
    def get_cache(self) -> TenantAwareCache:
        """获取缓存实例"""
        if not self.cache:
            raise Exception("缓存管理器未初始化")
        return self.cache


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None

async def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()
    
    return _cache_manager

async def get_tenant_cache() -> TenantAwareCache:
    """获取租户缓存实例的便捷函数"""
    manager = await get_cache_manager()
    return manager.get_cache()


# 缓存装饰器
def cache_result(cache_type: str, ttl: Optional[int] = None, 
                key_builder: Optional[callable] = None):
    """缓存结果装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 提取租户ID和工作空间ID
            tenant_id = kwargs.get('tenant_id') or (args[0] if args else None)
            workspace_id = kwargs.get('workspace_id')
            
            if not tenant_id:
                # 如果没有租户ID，直接执行函数
                return await func(*args, **kwargs)
            
            # 构建缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认键构建逻辑
                key_parts = [func.__name__]
                key_parts.extend([str(arg) for arg in args[1:]])  # 跳过tenant_id
                key_parts.extend([f"{k}={v}" for k, v in kwargs.items() 
                                if k not in ['tenant_id', 'workspace_id']])
                cache_key = ":".join(key_parts)
            
            try:
                cache = await get_tenant_cache()
                
                # 尝试从缓存获取
                cached_result = await cache.get(tenant_id, cache_type, cache_key, workspace_id)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数并缓存结果
                result = await func(*args, **kwargs)
                await cache.set(tenant_id, cache_type, cache_key, result, workspace_id, ttl)
                
                return result
                
            except Exception as e:
                logger.error(f"缓存装饰器错误: {e}")
                # 缓存失败时直接执行函数
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator