"""
健康检查模块
为所有服务提供健康检查端点

**Feature: system-optimization**
**Validates: Requirements 13.3**
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import threading

from pydantic import BaseModel, Field

from src.i18n.translations import t

logger = logging.getLogger(__name__)


# ============================================================================
# 健康状态定义
# ============================================================================

class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceType(str, Enum):
    """服务类型"""
    DATABASE = "database"
    REDIS = "redis"
    NEO4J = "neo4j"
    LABEL_STUDIO = "label_studio"
    EXTERNAL_API = "external_api"
    INTERNAL = "internal"


# ============================================================================
# 健康检查结果模型
# ============================================================================

class ServiceHealthResult(BaseModel):
    """
    服务健康检查结果
    """
    status: HealthStatus = Field(..., description="健康状态")
    latency_ms: float = Field(default=0.0, description="延迟（毫秒）")
    message: Optional[str] = Field(default=None, description="状态消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")
    last_check: datetime = Field(default_factory=datetime.now, description="最后检查时间")


class HealthCheckResponse(BaseModel):
    """
    健康检查响应
    """
    status: HealthStatus = Field(..., description="整体健康状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间戳")
    services: Dict[str, ServiceHealthResult] = Field(default_factory=dict, description="各服务状态")
    version: str = Field(default="1.0.0", description="系统版本")
    uptime_seconds: float = Field(default=0.0, description="运行时间（秒）")


# ============================================================================
# 健康检查器抽象基类
# ============================================================================

class HealthChecker(ABC):
    """
    健康检查器抽象基类
    """
    
    def __init__(self, name: str, service_type: ServiceType, timeout: float = 5.0):
        self.name = name
        self.service_type = service_type
        self.timeout = timeout
        self._last_result: Optional[ServiceHealthResult] = None
        self._last_check_time: Optional[datetime] = None
    
    @abstractmethod
    async def check(self) -> ServiceHealthResult:
        """
        执行健康检查
        
        Returns:
            健康检查结果
        """
        pass
    
    async def check_with_timeout(self) -> ServiceHealthResult:
        """
        带超时的健康检查
        """
        start_time = time.time()
        try:
            result = await asyncio.wait_for(self.check(), timeout=self.timeout)
            result.latency_ms = (time.time() - start_time) * 1000
            self._last_result = result
            self._last_check_time = datetime.now()
            return result
        except asyncio.TimeoutError:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start_time) * 1000,
                message=t('monitoring.health.timeout', service=self.name),
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start_time) * 1000,
                message=str(e),
                last_check=datetime.now()
            )
    
    def get_last_result(self) -> Optional[ServiceHealthResult]:
        """获取最后一次检查结果"""
        return self._last_result


# ============================================================================
# 具体健康检查器实现
# ============================================================================

class DatabaseHealthChecker(HealthChecker):
    """
    数据库健康检查器
    """
    
    def __init__(
        self,
        name: str = "database",
        connection_string: Optional[str] = None,
        timeout: float = 5.0
    ):
        super().__init__(name, ServiceType.DATABASE, timeout)
        self.connection_string = connection_string
    
    async def check(self) -> ServiceHealthResult:
        """检查数据库连接"""
        try:
            # 尝试导入数据库连接
            from src.database.connection import db_manager
            
            start_time = time.time()
            
            # 执行简单查询
            with db_manager.get_session() as session:
                result = session.execute("SELECT 1")
                result.fetchone()
            
            latency = (time.time() - start_time) * 1000
            
            return ServiceHealthResult(
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message=t('monitoring.health.database_connected'),
                details={"query": "SELECT 1"},
                last_check=datetime.now()
            )
        except ImportError:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                message=t('monitoring.health.database_not_configured'),
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )


class RedisHealthChecker(HealthChecker):
    """
    Redis 健康检查器
    """
    
    def __init__(
        self,
        name: str = "redis",
        host: str = "localhost",
        port: int = 6379,
        timeout: float = 5.0
    ):
        super().__init__(name, ServiceType.REDIS, timeout)
        self.host = host
        self.port = port
    
    async def check(self) -> ServiceHealthResult:
        """检查 Redis 连接"""
        try:
            import redis.asyncio as redis
            
            start_time = time.time()
            
            client = redis.Redis(
                host=self.host,
                port=self.port,
                socket_timeout=self.timeout
            )
            
            # 执行 PING 命令
            await client.ping()
            
            # 获取 Redis 信息
            info = await client.info("server")
            
            await client.close()
            
            latency = (time.time() - start_time) * 1000
            
            return ServiceHealthResult(
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message=t('monitoring.health.redis_connected'),
                details={
                    "redis_version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0)
                },
                last_check=datetime.now()
            )
        except ImportError:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                message=t('monitoring.health.redis_not_installed'),
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )


class Neo4jHealthChecker(HealthChecker):
    """
    Neo4j 健康检查器
    """
    
    def __init__(
        self,
        name: str = "neo4j",
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "",
        timeout: float = 5.0
    ):
        super().__init__(name, ServiceType.NEO4J, timeout)
        self.uri = uri
        self.username = username
        self.password = password
    
    async def check(self) -> ServiceHealthResult:
        """检查 Neo4j 连接"""
        try:
            from neo4j import AsyncGraphDatabase
            
            start_time = time.time()
            
            driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS num")
                record = await result.single()
            
            await driver.close()
            
            latency = (time.time() - start_time) * 1000
            
            return ServiceHealthResult(
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message=t('monitoring.health.neo4j_connected'),
                details={"query": "RETURN 1"},
                last_check=datetime.now()
            )
        except ImportError:
            return ServiceHealthResult(
                status=HealthStatus.DEGRADED,
                message=t('monitoring.health.neo4j_not_configured'),
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )


class LabelStudioHealthChecker(HealthChecker):
    """
    Label Studio 健康检查器
    """
    
    def __init__(
        self,
        name: str = "label_studio",
        base_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        timeout: float = 5.0
    ):
        super().__init__(name, ServiceType.LABEL_STUDIO, timeout)
        self.base_url = base_url
        self.api_key = api_key
    
    async def check(self) -> ServiceHealthResult:
        """检查 Label Studio 连接"""
        try:
            import httpx
            
            start_time = time.time()
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Token {self.api_key}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/health",
                    headers=headers
                )
            
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return ServiceHealthResult(
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message=t('monitoring.health.label_studio_connected'),
                    details={"status_code": response.status_code},
                    last_check=datetime.now()
                )
            else:
                return ServiceHealthResult(
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message=t('monitoring.health.label_studio_error', code=response.status_code),
                    details={"status_code": response.status_code},
                    last_check=datetime.now()
                )
        except ImportError:
            return ServiceHealthResult(
                status=HealthStatus.DEGRADED,
                message=t('monitoring.health.label_studio_not_configured'),
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )


class ExternalAPIHealthChecker(HealthChecker):
    """
    外部 API 健康检查器
    """
    
    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
        timeout: float = 5.0
    ):
        super().__init__(name, ServiceType.EXTERNAL_API, timeout)
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.expected_status = expected_status
    
    async def check(self) -> ServiceHealthResult:
        """检查外部 API 连接"""
        try:
            import httpx
            
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers
                )
            
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == self.expected_status:
                return ServiceHealthResult(
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message=t('monitoring.health.api_connected', name=self.name),
                    details={"status_code": response.status_code},
                    last_check=datetime.now()
                )
            else:
                return ServiceHealthResult(
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message=t('monitoring.health.api_error', name=self.name, code=response.status_code),
                    details={"status_code": response.status_code},
                    last_check=datetime.now()
                )
        except Exception as e:
            return ServiceHealthResult(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )


class CustomHealthChecker(HealthChecker):
    """
    自定义健康检查器
    """
    
    def __init__(
        self,
        name: str,
        check_func: Callable[[], Awaitable[ServiceHealthResult]],
        service_type: ServiceType = ServiceType.INTERNAL,
        timeout: float = 5.0
    ):
        super().__init__(name, service_type, timeout)
        self.check_func = check_func
    
    async def check(self) -> ServiceHealthResult:
        """执行自定义检查"""
        return await self.check_func()


# ============================================================================
# 健康检查管理器
# ============================================================================

class HealthCheckManager:
    """
    健康检查管理器
    
    管理所有服务的健康检查
    """
    
    def __init__(self, version: str = "1.0.0"):
        self._checkers: Dict[str, HealthChecker] = {}
        self._start_time = datetime.now()
        self._version = version
        self._lock = threading.Lock()
        self._cached_results: Dict[str, ServiceHealthResult] = {}
        self._cache_ttl_seconds = 10  # 缓存 TTL
        self._last_full_check: Optional[datetime] = None
    
    def register(self, checker: HealthChecker):
        """
        注册健康检查器
        
        Args:
            checker: 健康检查器实例
        """
        with self._lock:
            self._checkers[checker.name] = checker
            logger.info(t('monitoring.health.checker_registered', name=checker.name))
    
    def unregister(self, name: str):
        """
        取消注册健康检查器
        
        Args:
            name: 检查器名称
        """
        with self._lock:
            if name in self._checkers:
                del self._checkers[name]
                logger.info(t('monitoring.health.checker_unregistered', name=name))
    
    def get_checker(self, name: str) -> Optional[HealthChecker]:
        """获取健康检查器"""
        with self._lock:
            return self._checkers.get(name)
    
    def list_checkers(self) -> List[str]:
        """列出所有检查器名称"""
        with self._lock:
            return list(self._checkers.keys())
    
    async def check_service(self, name: str) -> Optional[ServiceHealthResult]:
        """
        检查单个服务
        
        Args:
            name: 服务名称
            
        Returns:
            健康检查结果
        """
        checker = self.get_checker(name)
        if not checker:
            return None
        
        result = await checker.check_with_timeout()
        
        with self._lock:
            self._cached_results[name] = result
        
        return result
    
    async def check_all(self, use_cache: bool = False) -> HealthCheckResponse:
        """
        检查所有服务
        
        Args:
            use_cache: 是否使用缓存结果
            
        Returns:
            健康检查响应
        """
        now = datetime.now()
        
        # 检查缓存
        if use_cache and self._last_full_check:
            elapsed = (now - self._last_full_check).total_seconds()
            if elapsed < self._cache_ttl_seconds:
                return self._build_response(self._cached_results)
        
        # 并发执行所有检查
        with self._lock:
            checkers = list(self._checkers.items())
        
        tasks = [
            checker.check_with_timeout()
            for _, checker in checkers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        service_results: Dict[str, ServiceHealthResult] = {}
        for (name, _), result in zip(checkers, results):
            if isinstance(result, Exception):
                service_results[name] = ServiceHealthResult(
                    status=HealthStatus.UNHEALTHY,
                    message=str(result),
                    last_check=now
                )
            else:
                service_results[name] = result
        
        # 更新缓存
        with self._lock:
            self._cached_results = service_results
            self._last_full_check = now
        
        return self._build_response(service_results)
    
    def _build_response(self, service_results: Dict[str, ServiceHealthResult]) -> HealthCheckResponse:
        """构建健康检查响应"""
        # 计算整体状态
        overall_status = HealthStatus.HEALTHY
        
        for result in service_results.values():
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif result.status == HealthStatus.DEGRADED:
                overall_status = HealthStatus.DEGRADED
        
        # 计算运行时间
        uptime = (datetime.now() - self._start_time).total_seconds()
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            services=service_results,
            version=self._version,
            uptime_seconds=uptime
        )
    
    async def get_liveness(self) -> Dict[str, Any]:
        """
        获取存活状态（Kubernetes liveness probe）
        
        Returns:
            存活状态
        """
        return {
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_readiness(self) -> Dict[str, Any]:
        """
        获取就绪状态（Kubernetes readiness probe）
        
        Returns:
            就绪状态
        """
        response = await self.check_all(use_cache=True)
        
        is_ready = response.status != HealthStatus.UNHEALTHY
        
        return {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: result.status.value
                for name, result in response.services.items()
            }
        }
    
    def set_cache_ttl(self, seconds: int):
        """设置缓存 TTL"""
        self._cache_ttl_seconds = seconds
    
    def get_uptime(self) -> float:
        """获取运行时间（秒）"""
        return (datetime.now() - self._start_time).total_seconds()


# ============================================================================
# 全局健康检查管理器
# ============================================================================

# 全局实例
health_check_manager = HealthCheckManager()


def setup_default_checkers():
    """设置默认健康检查器"""
    import os
    
    # 数据库检查器
    health_check_manager.register(DatabaseHealthChecker())
    
    # Redis 检查器
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    health_check_manager.register(RedisHealthChecker(
        host=redis_host,
        port=redis_port
    ))
    
    # Neo4j 检查器（如果配置了）
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        health_check_manager.register(Neo4jHealthChecker(
            uri=neo4j_uri,
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "")
        ))
    
    # Label Studio 检查器（如果配置了）
    label_studio_url = os.getenv("LABEL_STUDIO_URL")
    if label_studio_url:
        health_check_manager.register(LabelStudioHealthChecker(
            base_url=label_studio_url,
            api_key=os.getenv("LABEL_STUDIO_API_KEY")
        ))


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 枚举
    "HealthStatus",
    "ServiceType",
    # 模型
    "ServiceHealthResult",
    "HealthCheckResponse",
    # 检查器
    "HealthChecker",
    "DatabaseHealthChecker",
    "RedisHealthChecker",
    "Neo4jHealthChecker",
    "LabelStudioHealthChecker",
    "ExternalAPIHealthChecker",
    "CustomHealthChecker",
    # 管理器
    "HealthCheckManager",
    # 全局实例
    "health_check_manager",
    # 辅助函数
    "setup_default_checkers",
]
