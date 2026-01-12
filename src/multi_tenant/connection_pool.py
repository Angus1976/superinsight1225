"""
Multi-Tenant Connection Pool Implementation
租户感知的数据库连接池系统
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import redis.asyncio as redis
from datetime import datetime, timedelta

from src.database.connection import get_database_url
from src.multi_tenant.services import TenantManager

logger = logging.getLogger(__name__)

class TenantAwareConnectionPool:
    """租户感知的连接池管理器"""
    
    def __init__(self, base_database_url: str, redis_client: Optional[redis.Redis] = None):
        self.base_database_url = base_database_url
        self.redis_client = redis_client
        self.tenant_engines: Dict[str, AsyncEngine] = {}
        self.tenant_sessions: Dict[str, sessionmaker] = {}
        self.pool_stats: Dict[str, Dict[str, Any]] = {}
        self.tenant_manager = TenantManager()
        
        # 连接池配置
        self.pool_config = {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        }
        
        # 监控配置
        self.monitoring_enabled = True
        self.stats_update_interval = 60  # 秒
        
    async def initialize(self):
        """初始化连接池系统"""
        logger.info("初始化租户感知连接池系统")
        
        # 创建默认连接池
        await self._create_default_pool()
        
        # 启动监控任务
        if self.monitoring_enabled:
            asyncio.create_task(self._monitoring_task())
        
        logger.info("连接池系统初始化完成")
    
    async def _create_default_pool(self):
        """创建默认连接池"""
        default_engine = create_async_engine(
            self.base_database_url,
            poolclass=QueuePool,
            **self.pool_config,
            echo=False
        )
        
        self.tenant_engines['default'] = default_engine
        self.tenant_sessions['default'] = sessionmaker(
            default_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # 初始化统计信息
        self.pool_stats['default'] = {
            'created_at': datetime.now(),
            'connections_created': 0,
            'connections_active': 0,
            'connections_checked_out': 0,
            'last_activity': datetime.now()
        }
    
    async def get_engine_for_tenant(self, tenant_id: str) -> AsyncEngine:
        """获取指定租户的数据库引擎"""
        if not tenant_id or tenant_id == 'default':
            return self.tenant_engines['default']
        
        # 检查是否已存在该租户的连接池
        if tenant_id not in self.tenant_engines:
            await self._create_tenant_pool(tenant_id)
        
        # 更新最后活动时间
        if tenant_id in self.pool_stats:
            self.pool_stats[tenant_id]['last_activity'] = datetime.now()
        
        return self.tenant_engines[tenant_id]
    
    async def get_session_for_tenant(self, tenant_id: str) -> sessionmaker:
        """获取指定租户的会话工厂"""
        if not tenant_id or tenant_id == 'default':
            return self.tenant_sessions['default']
        
        # 确保引擎存在
        await self.get_engine_for_tenant(tenant_id)
        
        return self.tenant_sessions[tenant_id]
    
    @asynccontextmanager
    async def get_session(self, tenant_id: str):
        """获取租户会话的上下文管理器"""
        session_factory = await self.get_session_for_tenant(tenant_id)
        session = session_factory()
        
        try:
            # 设置租户上下文
            await session.execute(
                "SET LOCAL app.current_tenant_id = :tenant_id",
                {"tenant_id": tenant_id}
            )
            
            yield session
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            logger.error(f"租户 {tenant_id} 会话错误: {e}")
            raise
        finally:
            await session.close()
    
    async def _create_tenant_pool(self, tenant_id: str):
        """为指定租户创建连接池"""
        try:
            # 验证租户存在
            tenant = await self.tenant_manager.get_tenant(tenant_id)
            if not tenant:
                logger.warning(f"租户 {tenant_id} 不存在，使用默认连接池")
                return
            
            # 获取租户特定的数据库配置
            tenant_config = await self._get_tenant_db_config(tenant_id)
            
            # 创建租户特定的引擎
            tenant_engine = create_async_engine(
                tenant_config.get('database_url', self.base_database_url),
                poolclass=QueuePool,
                pool_size=tenant_config.get('pool_size', self.pool_config['pool_size']),
                max_overflow=tenant_config.get('max_overflow', self.pool_config['max_overflow']),
                pool_timeout=tenant_config.get('pool_timeout', self.pool_config['pool_timeout']),
                pool_recycle=tenant_config.get('pool_recycle', self.pool_config['pool_recycle']),
                pool_pre_ping=True,
                echo=False
            )
            
            # 存储引擎和会话工厂
            self.tenant_engines[tenant_id] = tenant_engine
            self.tenant_sessions[tenant_id] = sessionmaker(
                tenant_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 初始化统计信息
            self.pool_stats[tenant_id] = {
                'created_at': datetime.now(),
                'connections_created': 0,
                'connections_active': 0,
                'connections_checked_out': 0,
                'last_activity': datetime.now(),
                'config': tenant_config
            }
            
            logger.info(f"为租户 {tenant_id} 创建连接池成功")
            
        except Exception as e:
            logger.error(f"为租户 {tenant_id} 创建连接池失败: {e}")
            # 回退到默认连接池
            self.tenant_engines[tenant_id] = self.tenant_engines['default']
            self.tenant_sessions[tenant_id] = self.tenant_sessions['default']
    
    async def _get_tenant_db_config(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户的数据库配置"""
        try:
            # 从Redis缓存获取配置
            if self.redis_client:
                cached_config = await self.redis_client.get(f"tenant_db_config:{tenant_id}")
                if cached_config:
                    import json
                    return json.loads(cached_config)
            
            # 从数据库获取租户配置
            tenant = await self.tenant_manager.get_tenant(tenant_id)
            if tenant and tenant.configuration:
                db_config = tenant.configuration.get('database', {})
                
                # 缓存配置
                if self.redis_client:
                    import json
                    await self.redis_client.setex(
                        f"tenant_db_config:{tenant_id}",
                        3600,  # 1小时缓存
                        json.dumps(db_config)
                    )
                
                return db_config
            
            return {}
            
        except Exception as e:
            logger.error(f"获取租户 {tenant_id} 数据库配置失败: {e}")
            return {}
    
    async def get_pool_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if tenant_id:
            if tenant_id in self.pool_stats:
                stats = self.pool_stats[tenant_id].copy()
                
                # 添加实时统计
                if tenant_id in self.tenant_engines:
                    engine = self.tenant_engines[tenant_id]
                    pool = engine.pool
                    
                    stats.update({
                        'pool_size': pool.size(),
                        'checked_out_connections': pool.checkedout(),
                        'overflow_connections': pool.overflow(),
                        'checked_in_connections': pool.checkedin()
                    })
                
                return stats
            else:
                return {}
        else:
            # 返回所有租户的统计信息
            all_stats = {}
            for tid in self.pool_stats:
                all_stats[tid] = await self.get_pool_stats(tid)
            return all_stats
    
    async def cleanup_idle_pools(self, idle_threshold_hours: int = 24):
        """清理空闲的连接池"""
        current_time = datetime.now()
        idle_threshold = timedelta(hours=idle_threshold_hours)
        
        pools_to_remove = []
        
        for tenant_id, stats in self.pool_stats.items():
            if tenant_id == 'default':
                continue  # 不清理默认连接池
            
            last_activity = stats.get('last_activity', stats.get('created_at'))
            if current_time - last_activity > idle_threshold:
                pools_to_remove.append(tenant_id)
        
        for tenant_id in pools_to_remove:
            await self._remove_tenant_pool(tenant_id)
            logger.info(f"清理空闲租户连接池: {tenant_id}")
    
    async def _remove_tenant_pool(self, tenant_id: str):
        """移除租户连接池"""
        try:
            if tenant_id in self.tenant_engines:
                engine = self.tenant_engines[tenant_id]
                await engine.dispose()
                del self.tenant_engines[tenant_id]
            
            if tenant_id in self.tenant_sessions:
                del self.tenant_sessions[tenant_id]
            
            if tenant_id in self.pool_stats:
                del self.pool_stats[tenant_id]
                
        except Exception as e:
            logger.error(f"移除租户 {tenant_id} 连接池失败: {e}")
    
    async def _monitoring_task(self):
        """连接池监控任务"""
        while True:
            try:
                await asyncio.sleep(self.stats_update_interval)
                
                # 更新统计信息
                await self._update_pool_statistics()
                
                # 清理空闲连接池
                await self.cleanup_idle_pools()
                
            except Exception as e:
                logger.error(f"连接池监控任务错误: {e}")
    
    async def _update_pool_statistics(self):
        """更新连接池统计信息"""
        for tenant_id, engine in self.tenant_engines.items():
            try:
                pool = engine.pool
                
                if tenant_id in self.pool_stats:
                    self.pool_stats[tenant_id].update({
                        'connections_active': pool.size(),
                        'connections_checked_out': pool.checkedout(),
                        'connections_overflow': pool.overflow(),
                        'connections_checked_in': pool.checkedin()
                    })
                    
            except Exception as e:
                logger.error(f"更新租户 {tenant_id} 连接池统计失败: {e}")
    
    async def close_all_pools(self):
        """关闭所有连接池"""
        logger.info("关闭所有租户连接池")
        
        for tenant_id, engine in self.tenant_engines.items():
            try:
                await engine.dispose()
                logger.info(f"关闭租户 {tenant_id} 连接池")
            except Exception as e:
                logger.error(f"关闭租户 {tenant_id} 连接池失败: {e}")
        
        self.tenant_engines.clear()
        self.tenant_sessions.clear()
        self.pool_stats.clear()


# 全局连接池实例
_connection_pool: Optional[TenantAwareConnectionPool] = None

async def get_connection_pool() -> TenantAwareConnectionPool:
    """获取全局连接池实例"""
    global _connection_pool
    
    if _connection_pool is None:
        database_url = get_database_url()
        _connection_pool = TenantAwareConnectionPool(database_url)
        await _connection_pool.initialize()
    
    return _connection_pool

async def get_tenant_session(tenant_id: str):
    """获取租户数据库会话的便捷函数"""
    pool = await get_connection_pool()
    return pool.get_session(tenant_id)

async def get_tenant_engine(tenant_id: str) -> AsyncEngine:
    """获取租户数据库引擎的便捷函数"""
    pool = await get_connection_pool()
    return await pool.get_engine_for_tenant(tenant_id)