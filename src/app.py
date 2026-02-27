"""
FastAPI application for SuperInsight Platform.

Main web application with all API endpoints and system integration.
"""

import logging
import asyncio
import time
import importlib
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from src.config.settings import settings
from src.database.connection import init_database, test_database_connection, close_database
from src.system.integration import system_manager, system_lifespan
from src.system.error_handler import error_handler, ErrorCategory, ErrorSeverity
from src.system.monitoring import metrics_collector, performance_monitor, health_monitor, RequestTracker
from src.system.health import health_checker

# Import API routers
from src.api.extraction import router as extraction_router

# Import startup services for AI Annotation and Text-to-SQL integration
from src.startup import initialize_services, shutdown_services, health_router

logger = logging.getLogger(__name__)


# =============================================================================
# Global API Registration Tracking
# =============================================================================

# Global tracking for API registration status
# Validates: Requirements 2.5 - 清晰的 API 注册状态
_registered_apis: List[Dict[str, Any]] = []
_failed_apis: List[Dict[str, Any]] = []


def _track_api_registration(
    module_path: str,
    prefix: str,
    tags: List[str],
    success: bool,
    error: Optional[str] = None
) -> None:
    """Track API registration status.
    
    Args:
        module_path: The module path of the API
        prefix: The route prefix
        tags: API tags
        success: Whether registration was successful
        error: Error message if registration failed
    
    Note:
        This function avoids duplicate tracking by checking if the API
        is already registered before adding it to the tracking lists.
    """
    # Check if already tracked to avoid duplicates
    existing_paths = [api["path"] for api in _registered_apis]
    failed_paths = [api["path"] for api in _failed_apis]
    
    if prefix in existing_paths or prefix in failed_paths:
        return  # Already tracked, skip
    
    if success:
        _registered_apis.append({
            "path": prefix,
            "name": module_path.split(".")[-1].replace("_router", "").replace("_", " ").title(),
            "tags": tags,
            "status": "active"
        })
    else:
        _failed_apis.append({
            "path": prefix,
            "module": module_path,
            "error": error or "Unknown error"
        })


def get_api_registration_status() -> Dict[str, Any]:
    """Get the current API registration status.
    
    Returns:
        Dict containing registration statistics and details.
    
    Validates: Requirements 2.5 - 清晰的 API 注册状态
    """
    # Check if all high priority APIs are registered
    high_priority_prefixes = [config.prefix for config in HIGH_PRIORITY_APIS]
    registered_prefixes = [api["path"] for api in _registered_apis]
    
    missing_high_priority = [
        prefix for prefix in high_priority_prefixes 
        if prefix not in registered_prefixes
    ]
    
    return {
        "registered_count": len(_registered_apis),
        "failed_count": len(_failed_apis),
        "registered": _registered_apis,
        "failed": _failed_apis,
        "validation": {
            "high_priority_complete": len(missing_high_priority) == 0,
            "missing_count": len(missing_high_priority),
            "missing_apis": missing_high_priority
        }
    }


def _log_api_registration_summary() -> None:
    """Log API registration summary with emoji format.
    
    Outputs a structured summary of API registration status including:
    - Total APIs attempted
    - Successful registrations
    - Failed registrations
    - List of failed APIs (if any)
    
    Validates: Requirements 3.2 - 详细的日志记录每个 API 的注册状态
    """
    status = get_api_registration_status()
    total = status["registered_count"] + status["failed_count"]
    successful = status["registered_count"]
    failed = status["failed_count"]
    
    # Log summary header
    logger.info("=" * 60)
    logger.info("📊 API Registration Summary")
    logger.info("=" * 60)
    
    # Log statistics
    if failed == 0:
        logger.info(f"✅ All APIs registered successfully: {successful}/{total}")
    else:
        logger.info(f"📈 Registration Results: {successful}/{total} successful, {failed} failed")
    
    # Log high priority API validation
    validation = status["validation"]
    if validation["high_priority_complete"]:
        logger.info("✅ All high-priority APIs registered successfully")
    else:
        logger.warning(f"⚠️ Missing high-priority APIs: {validation['missing_count']}")
        for missing_api in validation["missing_apis"]:
            logger.warning(f"   - {missing_api}")
    
    # Log failed APIs if any
    if failed > 0:
        logger.warning("❌ Failed API registrations:")
        for failed_api in status["failed"]:
            logger.warning(f"   - {failed_api['path']}: {failed_api['error']}")
    
    # Log footer
    logger.info("=" * 60)


# =============================================================================
# API Registration Configuration Model
# =============================================================================

class APIRouterConfig(BaseModel):
    """API 路由配置模型
    
    用于定义 API 路由的配置信息，支持批量注册和配置管理。
    
    Attributes:
        module_path: 模块路径，如 "src.api.license_router"
        router_name: 路由对象名称，默认 "router"
        prefix: 路由前缀，如 "/api/v1/license"
        tags: API 标签列表
        required: 是否为必需 API（失败时是否抛出异常）
        priority: 优先级: high, medium, low
        description: 描述信息
    
    Validates: Requirements 2.5 - 清晰的 API 注册规范
    """
    module_path: str
    router_name: str = "router"
    prefix: Optional[str] = None
    tags: Optional[List[str]] = None
    required: bool = False
    priority: str = "high"
    description: str = ""


# =============================================================================
# API Registration Manager
# =============================================================================

class APIRegistrationManager:
    """API 注册管理器
    
    统一管理 API 路由注册，提供错误处理、日志记录和注册报告功能。
    
    Features:
        - 单个路由注册 (register_router)
        - 批量路由注册 (register_batch)
        - 配置对象注册 (register_from_configs)
        - 注册状态查询 (is_registered, get_registered_count, get_failed_count)
        - 注册报告生成 (get_registration_report)
    
    Validates: Requirements 2.5 - 清晰的 API 注册规范
    Validates: Requirements 3.1 - 失败的 API 注册不应阻塞其他 API 的加载
    Validates: Requirements 3.2 - 单个 API 注册失败不应导致整个应用崩溃
    
    Example:
        >>> manager = APIRegistrationManager(app, logger)
        >>> manager.register_router(
        ...     module_path="src.api.license_router",
        ...     prefix="/api/v1/license",
        ...     tags=["license"]
        ... )
        True
        >>> manager.get_registration_report()
        {'total': 1, 'successful': 1, 'failed': 0, ...}
    """
    
    def __init__(self, app: FastAPI, logger: logging.Logger):
        """初始化 API 注册管理器
        
        Args:
            app: FastAPI 应用实例
            logger: 日志记录器
        """
        self.app = app
        self.logger = logger
        self.registered_apis: List[str] = []
        self.failed_apis: List[Tuple[str, str]] = []
    
    def register_router(
        self,
        module_path: str,
        router_name: str = "router",
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        required: bool = False
    ) -> bool:
        """注册单个 API 路由
        
        动态导入模块并注册其路由到 FastAPI 应用。
        
        Args:
            module_path: 模块路径，如 "src.api.license_router"
            router_name: 路由对象名称，默认 "router"
            prefix: 路由前缀，如 "/api/v1/license"
            tags: API 标签列表
            required: 是否为必需 API（失败时是否抛出异常）
        
        Returns:
            bool: 注册是否成功
        
        Raises:
            ImportError: 当 required=True 且模块不存在时
            AttributeError: 当 required=True 且路由对象不存在时
            Exception: 当 required=True 且发生其他错误时
        
        Validates: Requirements 2.5 - 清晰的 API 注册规范
        Validates: Requirements 3.2 - 详细的日志记录每个 API 的注册状态
        """
        try:
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 获取路由对象
            router = getattr(module, router_name)
            
            # 构建 include_router 参数
            include_kwargs: Dict[str, Any] = {}
            if prefix:
                include_kwargs["prefix"] = prefix
            if tags:
                include_kwargs["tags"] = tags
            
            # 注册路由
            self.app.include_router(router, **include_kwargs)
            
            # 记录成功
            self.registered_apis.append(module_path)
            display_prefix = prefix or "(default)"
            self.logger.info(f"✅ {module_path} registered: {display_prefix}")
            
            return True
            
        except ImportError as e:
            # 模块不存在
            error_msg = str(e)
            self.failed_apis.append((module_path, error_msg))
            self.logger.warning(f"⚠️ {module_path} not available: {error_msg}")
            
            if required:
                raise
            return False
            
        except AttributeError as e:
            # 路由对象不存在
            error_msg = f"Router '{router_name}' not found: {e}"
            self.failed_apis.append((module_path, error_msg))
            self.logger.error(f"❌ {module_path} failed: {error_msg}")
            
            if required:
                raise
            return False
            
        except Exception as e:
            # 其他错误
            error_msg = str(e)
            self.failed_apis.append((module_path, error_msg))
            self.logger.error(f"❌ {module_path} failed to load: {error_msg}")
            
            if required:
                raise
            return False
    
    def register_batch(self, routers: List[Dict[str, Any]]) -> Tuple[int, int]:
        """批量注册 API 路由
        
        按顺序注册多个路由，单个失败不影响其他路由的注册。
        
        Args:
            routers: 路由配置列表，每个配置是一个字典，包含:
                - module_path: 模块路径 (必需)
                - router_name: 路由对象名称 (可选，默认 "router")
                - prefix: 路由前缀 (可选)
                - tags: API 标签 (可选)
                - required: 是否必需 (可选，默认 False)
        
        Returns:
            Tuple[int, int]: (成功数量, 失败数量)
        
        Validates: Requirements 3.1 - 失败的 API 注册不应阻塞其他 API 的加载
        """
        success_count = 0
        failed_count = 0
        
        for router_config in routers:
            try:
                # 检查必需字段
                module_path = router_config.get("module_path")
                if not module_path:
                    self.failed_apis.append(("unknown", "Missing module_path"))
                    self.logger.error("❌ Missing module_path in router config")
                    failed_count += 1
                    continue
                
                # 提取配置
                router_name = router_config.get("router_name", "router")
                prefix = router_config.get("prefix")
                tags = router_config.get("tags")
                required = router_config.get("required", False)
                
                # 注册路由
                result = self.register_router(
                    module_path=module_path,
                    router_name=router_name,
                    prefix=prefix,
                    tags=tags,
                    required=required
                )
                
                if result:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                # 捕获所有异常，确保批量注册继续
                failed_count += 1
                self.logger.error(f"❌ Batch registration error: {e}")
        
        # 输出批量注册摘要
        total = success_count + failed_count
        self.logger.info(
            f"📊 Batch Registration Summary: {success_count}/{total} successful, "
            f"{failed_count} failed"
        )
        
        return success_count, failed_count
    
    def register_from_configs(self, configs: List[APIRouterConfig]) -> Tuple[int, int]:
        """从配置对象列表注册 API 路由
        
        使用 APIRouterConfig 对象进行批量注册。
        
        Args:
            configs: APIRouterConfig 对象列表
        
        Returns:
            Tuple[int, int]: (成功数量, 失败数量)
        
        Validates: Requirements 2.5 - 使用配置对象注册
        """
        routers = [config.model_dump() for config in configs]
        return self.register_batch(routers)
    
    def get_registration_report(self) -> Dict[str, Any]:
        """获取注册报告
        
        生成包含注册状态、成功/失败列表和统计信息的报告。
        
        Returns:
            Dict[str, Any]: 注册报告，包含:
                - total: 总注册数
                - successful: 成功数
                - failed: 失败数
                - success_rate: 成功率 (0.0-1.0)
                - status: 状态 ("complete" 或 "partial")
                - registered_apis: 已注册的 API 列表
                - failed_apis: 失败的 API 列表 [(module_path, error)]
        
        Validates: Requirements 2.5 - 清晰的 API 注册状态
        """
        total = len(self.registered_apis) + len(self.failed_apis)
        successful = len(self.registered_apis)
        failed = len(self.failed_apis)
        
        # 计算成功率
        success_rate = successful / total if total > 0 else 0.0
        
        # 确定状态
        if failed == 0:
            status = "complete"
        else:
            status = "partial"
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "status": status,
            "registered_apis": list(self.registered_apis),
            "failed_apis": list(self.failed_apis)
        }
    
    def is_registered(self, module_path: str) -> bool:
        """检查模块是否已注册
        
        Args:
            module_path: 模块路径
        
        Returns:
            bool: 是否已注册
        """
        return module_path in self.registered_apis
    
    def get_registered_count(self) -> int:
        """获取已注册的 API 数量
        
        Returns:
            int: 已注册数量
        """
        return len(self.registered_apis)
    
    def get_failed_count(self) -> int:
        """获取注册失败的 API 数量
        
        Returns:
            int: 失败数量
        """
        return len(self.failed_apis)


# =============================================================================
# High Priority API Configurations
# =============================================================================

HIGH_PRIORITY_APIS: List[APIRouterConfig] = [
    # License 模块 (3个)
    # Validates: Requirements 2.1 - License 模块用户需求
    APIRouterConfig(
        module_path="src.api.license_router",
        prefix="/api/v1/license",
        tags=["License"],
        priority="high",
        description="License management API"
    ),
    APIRouterConfig(
        module_path="src.api.usage_router",
        prefix="/api/v1/usage",
        tags=["Usage"],
        priority="high",
        description="License usage monitoring API"
    ),
    APIRouterConfig(
        module_path="src.api.activation_router",
        prefix="/api/v1/activation",
        tags=["Activation"],
        priority="high",
        description="License activation API"
    ),
    
    # Quality 子模块 (3个)
    # Validates: Requirements 2.2 - Quality 模块用户需求
    APIRouterConfig(
        module_path="src.api.quality_rules",
        prefix="/api/v1/quality-rules",
        tags=["Quality Rules"],
        priority="high",
        description="Quality rules management API"
    ),
    APIRouterConfig(
        module_path="src.api.quality_reports",
        prefix="/api/v1/quality-reports",
        tags=["Quality Reports"],
        priority="high",
        description="Quality reports API"
    ),
    APIRouterConfig(
        module_path="src.api.quality_workflow",
        prefix="/api/v1/quality-workflow",
        tags=["Quality Workflow"],
        priority="high",
        description="Quality workflow API"
    ),
    
    # Augmentation 模块 (1个)
    # Validates: Requirements 2.3 - Augmentation 模块用户需求
    APIRouterConfig(
        module_path="src.api.augmentation",
        prefix="/api/v1/augmentation",
        tags=["Augmentation"],
        priority="high",
        description="Data augmentation API"
    ),
    
    # Security 子模块 (4个)
    # Validates: Requirements 2.4 - Security 子模块用户需求
    APIRouterConfig(
        module_path="src.api.sessions",
        prefix="/api/v1/sessions",
        tags=["Sessions"],
        priority="medium",
        description="Session management API"
    ),
    APIRouterConfig(
        module_path="src.api.sso",
        prefix="/api/v1/sso",
        tags=["SSO"],
        priority="medium",
        description="SSO configuration API"
    ),
    APIRouterConfig(
        module_path="src.api.rbac",
        prefix="/api/v1/rbac",
        tags=["RBAC"],
        priority="medium",
        description="RBAC management API"
    ),
    APIRouterConfig(
        module_path="src.api.data_permission_router",
        prefix="/api/v1/data-permissions",
        tags=["Data Permissions"],
        priority="medium",
        description="Data permissions API"
    ),
    
    # Versioning (1个)
    APIRouterConfig(
        module_path="src.api.versioning",
        prefix="/api/v1/versioning",
        tags=["Versioning"],
        priority="medium",
        description="Data versioning API"
    ),
]

# Middleware for request tracking and monitoring
class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request monitoring and performance tracking."""
    
    async def dispatch(self, request: Request, call_next):
        # Start request tracking
        request_id = f"req_{int(time.time() * 1000000)}"
        endpoint = f"{request.method} {request.url.path}"
        start_time = time.time()
        
        # Skip monitoring for health and metrics endpoints to avoid blocking
        skip_monitoring = request.url.path in ['/health', '/metrics', '/docs', '/openapi.json', '/favicon.ico']
        
        if not skip_monitoring:
            # Track request start in a non-blocking way
            try:
                # Use a simple dict instead of performance_monitor to avoid locks
                pass  # Skip start tracking to avoid potential deadlock
            except Exception as e:
                logger.warning(f"Failed to start request tracking: {e}")
        
        status_code = 200
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Track Prometheus metrics (non-blocking)
            if not skip_monitoring:
                try:
                    from src.system.prometheus_exporter import prometheus_exporter
                    duration = time.time() - start_time
                    prometheus_exporter.track_http_request(
                        method=request.method,
                        endpoint=request.url.path,
                        status_code=response.status_code,
                        duration=duration
                    )
                except ImportError:
                    pass  # Prometheus exporter not available
                except Exception as e:
                    pass  # Don't let metrics tracking break the request
            
            return response
        except Exception as e:
            status_code = 500
            
            # Handle error through error handler
            try:
                error_handler.handle_error(
                    exception=e,
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    service_name="api",
                    request_id=request_id,
                    endpoint=endpoint
                )
            except Exception:
                pass  # Don't let error handling break the request
            raise


async def register_system_services():
    """Register all system services with the integration manager."""
    
    # Database service
    def database_startup():
        init_database()
        if not test_database_connection():
            raise Exception("Database connection test failed")
    
    def database_shutdown():
        close_database()
    
    def database_health_check():
        return test_database_connection()
    
    system_manager.register_service(
        name="database",
        startup_func=database_startup,
        shutdown_func=database_shutdown,
        health_check=database_health_check,
        service_type="core"
    )
    
    # Metrics collection service
    async def metrics_startup():
        await metrics_collector.start_collection()
    
    async def metrics_shutdown():
        await metrics_collector.stop_collection()
    
    system_manager.register_service(
        name="metrics",
        startup_func=metrics_startup,
        shutdown_func=metrics_shutdown,
        dependencies=["database"],
        service_type="monitoring"
    )
    
    # Health monitoring service
    def health_startup():
        # Set up health monitoring thresholds
        health_monitor.set_threshold("system.cpu.usage_percent", warning=80.0, critical=95.0)
        health_monitor.set_threshold("system.memory.usage_percent", warning=85.0, critical=95.0)
        health_monitor.set_threshold("system.disk.usage_percent", warning=85.0, critical=95.0)
    
    system_manager.register_service(
        name="health_monitor",
        startup_func=health_startup,
        dependencies=["metrics"],
        service_type="monitoring"
    )
    
    # Try to register optional services
    try:
        from src.api.quality import router as quality_router
        
        def quality_service_startup():
            logger.info("Quality management service initialized")
        
        system_manager.register_service(
            name="quality_service",
            startup_func=quality_service_startup,
            dependencies=["database"],
            service_type="feature"
        )
        
    except ImportError:
        logger.warning("Quality management service not available")
    
    try:
        from src.api.ai_annotation import router as ai_router
        
        def ai_service_startup():
            logger.info("AI annotation service initialized")
        
        system_manager.register_service(
            name="ai_service",
            startup_func=ai_service_startup,
            dependencies=["database"],
            service_type="feature"
        )
        
    except ImportError:
        logger.warning("AI annotation service not available")
    
    try:
        from src.api.billing import router as billing_router
        
        def billing_service_startup():
            logger.info("Billing service initialized")
        
        system_manager.register_service(
            name="billing_service",
            startup_func=billing_service_startup,
            dependencies=["database"],
            service_type="feature"
        )
        
    except ImportError:
        logger.warning("Billing service not available")
    
    try:
        from src.api.security import router as security_router
        
        def security_service_startup():
            logger.info("Security service initialized")
        
        system_manager.register_service(
            name="security_service",
            startup_func=security_service_startup,
            dependencies=["database"],
            service_type="security"
        )
        
    except ImportError:
        logger.warning("Security service not available")
    
    try:
        from src.system.business_metrics import business_metrics_collector
        
        async def business_metrics_startup():
            await business_metrics_collector.start_collection()
            logger.info("Business metrics collection service initialized")
        
        async def business_metrics_shutdown():
            await business_metrics_collector.stop_collection()
        
        system_manager.register_service(
            name="business_metrics",
            startup_func=business_metrics_startup,
            shutdown_func=business_metrics_shutdown,
            dependencies=["database", "metrics"],
            service_type="monitoring"
        )
        
    except ImportError:
        logger.warning("Business metrics service not available")
    
    # Complete Event Capture System (100% Security Event Capture)
    try:
        from src.security.complete_event_capture_system import initialize_complete_capture_system
        from src.security.security_event_monitor import get_security_monitor
        from src.security.threat_detector import get_threat_detector
        
        async def complete_capture_startup():
            security_monitor = get_security_monitor()
            threat_detector = get_threat_detector()
            
            if security_monitor and threat_detector:
                capture_system = await initialize_complete_capture_system(
                    security_monitor, threat_detector
                )
                logger.info("Complete Event Capture System initialized successfully")
                return capture_system
            else:
                logger.warning("Security monitor or threat detector not available for complete capture")
        
        async def complete_capture_shutdown():
            from src.security.complete_event_capture_system import get_complete_capture_system
            capture_system = get_complete_capture_system()
            if capture_system:
                await capture_system.stop_capture_system()
                logger.info("Complete Event Capture System shutdown successfully")
        
        system_manager.register_service(
            name="complete_event_capture",
            startup_func=complete_capture_startup,
            shutdown_func=complete_capture_shutdown,
            dependencies=["database", "security_service"],
            service_type="security"
        )
        
    except ImportError:
        logger.warning("Complete Event Capture System not available")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with system integration."""
    # Startup
    logger.info(f"Starting {settings.app.app_name} v{settings.app.app_version}")

    # Initialize LLM Health Monitor reference (will be populated if available)
    llm_health_monitor = None

    try:
        # Simplified startup - skip service orchestration for now
        # Just initialize database connection
        init_database()
        if test_database_connection():
            logger.info("Database connection established")
        else:
            logger.warning("Database connection test failed")

        # Initialize LLM Health Monitor (if LLM integration is available)
        try:
            from src.ai.llm_switcher import get_llm_switcher
            from src.ai.llm.health_monitor import get_initialized_health_monitor
            from src.database.connection import get_db_session

            # Get LLM Switcher instance
            llm_switcher = get_llm_switcher()

            # Get database session for health status persistence
            db_session = None
            try:
                # Use next() instead of anext() for sync generator
                db_gen = get_db_session()
                db_session = next(db_gen)
            except Exception as e:
                logger.warning(f"Could not get database session for health monitor: {e}")

            # Initialize and start Health Monitor
            llm_health_monitor = await get_initialized_health_monitor(
                switcher=llm_switcher,
                db_session=db_session,
                metrics_collector=metrics_collector
            )

            logger.info("✅ LLM Health Monitor started successfully")

        except ImportError as e:
            logger.info("LLM Health Monitor not available (LLM integration not installed)")
        except Exception as e:
            logger.warning(f"Failed to start LLM Health Monitor: {e}")

        # Include optional routers
        await include_optional_routers()

        # Initialize AI Annotation and Text-to-SQL services
        await initialize_services(app)

        logger.info("Application startup completed")

        yield

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application")

        # Stop LLM Health Monitor if it was started
        if llm_health_monitor is not None:
            try:
                await llm_health_monitor.stop()
                logger.info("✅ LLM Health Monitor stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping LLM Health Monitor: {e}")

        # Shutdown AI Annotation and Text-to-SQL services
        await shutdown_services(app)

        close_database()

# Create FastAPI application
app = FastAPI(
    title="SuperInsight AI 数据治理与标注平台",
    description="企业级 AI 语料治理与智能标注平台 API",
    version=settings.app.app_version,
    debug=settings.app.debug,
    lifespan=lifespan
)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Add CORS middleware
# Configure CORS based on environment settings
# Note: When using wildcard origins ["*"], credentials cannot be enabled
cors_origins = settings.app.cors_origins
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
        # SSE streaming headers
        "X-Accel-Buffering",
    ],
    expose_headers=[
        "Content-Type",
        "Cache-Control",
        "Content-Encoding",
        "Content-Length",
        # SSE streaming headers
        "X-Accel-Buffering",
    ],
    max_age=600,
)

# Add automatic desensitization middleware
try:
    from src.security.auto_desensitization_middleware import AutoDesensitizationMiddleware
    app.add_middleware(
        AutoDesensitizationMiddleware,
        enabled=True,
        mask_requests=True,
        mask_responses=True,
        excluded_paths=[
            "/health", "/metrics", "/docs", "/openapi.json", "/static", "/favicon.ico",
            "/system/status", "/system/metrics", "/system/services"
        ]
    )
    logger.info("Automatic desensitization middleware loaded successfully")
except ImportError as e:
    logger.warning(f"Automatic desensitization middleware not available: {e}")
except Exception as e:
    logger.warning(f"Automatic desensitization middleware failed to load: {e}")

# Add i18n middleware
try:
    from src.i18n.middleware import language_middleware
    app.middleware("http")(language_middleware)
    logger.info("i18n middleware loaded successfully")
except ImportError as e:
    logger.warning(f"i18n middleware not available: {e}")
except Exception as e:
    logger.warning(f"i18n middleware failed to load: {e}")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with error tracking."""
    logger.error(f"Unhandled exception: {exc}")
    
    # Handle through error handler
    error_context = error_handler.handle_error(
        exception=exc,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        service_name="api",
        endpoint=f"{request.method} {request.url.path}"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_context.error_id,
            "message": str(exc) if settings.app.debug else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint for Docker.
    
    Returns health status including API registration information.
    
    Response Fields:
        - status: "healthy" or "unhealthy"
        - message: Status message
        - api_registration_status: "complete" if all high priority APIs registered, "partial" otherwise
        - registered_apis_count: Total number of registered APIs
    
    Validates: Requirements 3.2 - 可靠性要求
    """
    try:
        # Get API registration status
        api_status = get_api_registration_status()
        api_registration_status = "complete" if api_status["validation"]["high_priority_complete"] else "partial"
        registered_apis_count = api_status["registered_count"]
        
        # Simple health check - just return that API is running
        # Database check is skipped to avoid async/sync issues
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "message": "API is running",
                "api_registration_status": api_registration_status,
                "registered_apis_count": registered_apis_count
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


# Liveness probe endpoint (for Kubernetes/container orchestration)
@app.get("/health/live")
async def liveness_probe():
    """Liveness probe - checks if application is running."""
    return {
        "status": "alive",
        "timestamp": asyncio.get_event_loop().time()
    }


# Readiness probe endpoint (for Kubernetes/container orchestration)
@app.get("/health/ready")
async def readiness_probe():
    """Readiness probe - checks if application is ready to serve traffic."""
    try:
        # Check system status only (skip database check to avoid async/sync issues)
        system_status = system_manager.get_system_status()
        
        is_ready = system_status["overall_status"] == "healthy"
        
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={
                "status": "ready" if is_ready else "not_ready",
                "database": "not_checked",
                "services": system_status["overall_status"]
            }
        )
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e)
            }
        )


# System status endpoint
@app.get("/system/status")
async def system_status():
    """Get comprehensive system status."""
    try:
        return {
            "system": system_manager.get_system_status(),
            "metrics": metrics_collector.get_all_metrics_summary(),
            "performance": performance_monitor.get_performance_summary(),
            "errors": error_handler.get_error_statistics()
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Metrics endpoint
@app.get("/system/metrics")
async def system_metrics():
    """Get system metrics."""
    try:
        return metrics_collector.get_all_metrics_summary()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Prometheus metrics endpoint
@app.get("/metrics")
async def prometheus_metrics():
    """Get metrics in Prometheus format."""
    try:
        from src.system.prometheus_exporter import prometheus_exporter
        return prometheus_exporter.get_metrics_response()
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Service status endpoint
@app.get("/system/services")
async def services_status():
    """Get status of all registered services."""
    try:
        return system_manager.get_system_status()
    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Service-specific status endpoint
@app.get("/system/services/{service_name}")
async def service_status(service_name: str):
    """Get status of a specific service."""
    try:
        status = system_manager.get_service_status(service_name)
        if status is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"Service '{service_name}' not found"}
            )
        return status
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        "description": "SuperInsight AI 数据治理与标注平台 API",
        "docs_url": "/docs",
        "health_url": "/health"
    }


# Include routers
app.include_router(extraction_router)

# Include health check endpoints
app.include_router(health_router)

# Include tasks API router
try:
    from src.api.tasks import router as tasks_router
    app.include_router(tasks_router)
    logger.info("Tasks API loaded successfully")
except ImportError as e:
    logger.error(f"Tasks API not available: {e}")
except Exception as e:
    logger.error(f"Tasks API failed to load: {e}")

# Structuring API is registered later in the API registration section (line ~2270)
# Removed duplicate import to avoid table definition conflicts

# Include Label Studio API router
try:
    from src.api.label_studio_api import router as label_studio_router
    app.include_router(label_studio_router)
    logger.info("Label Studio API loaded successfully")
except ImportError as e:
    logger.error(f"Label Studio API not available: {e}")
except Exception as e:
    logger.error(f"Label Studio API failed to load: {e}")

# Include data sync API router
try:
    from src.api.data_sync import router as data_sync_router
    app.include_router(data_sync_router)
    logger.info("Data Sync API loaded successfully")
except ImportError as e:
    logger.error(f"Data Sync API not available: {e}")
except Exception as e:
    logger.error(f"Data Sync API failed to load: {e}")

# Include dashboard API router
try:
    from src.api.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("Dashboard API loaded successfully")
except ImportError as e:
    logger.error(f"Dashboard API not available: {e}")
except Exception as e:
    logger.error(f"Dashboard API failed to load: {e}")

# Include SOX Compliance API router - critical for compliance functionality
try:
    from src.api.sox_compliance_api import router as sox_compliance_router
    app.include_router(sox_compliance_router)
    logger.info("SOX Compliance API loaded successfully")
except ImportError as e:
    logger.error(f"SOX Compliance API not available: {e}")
except Exception as e:
    logger.error(f"SOX Compliance API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include comprehensive audit integration
try:
    from src.security.comprehensive_audit_integration import comprehensive_audit
    comprehensive_audit.integrate_with_fastapi(app)
    logger.info("Comprehensive audit system integrated successfully")
except Exception as e:
    logger.error(f"Failed to integrate comprehensive audit system: {e}")
    import traceback
    traceback.print_exc()

# Include admin router
try:
    from src.api.admin import router as admin_router, public_router as admin_public_router
    app.include_router(admin_router)
    app.include_router(admin_public_router)
    logger.info("Admin API loaded successfully")
except Exception as e:
    logger.error(f"Admin API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include auth router - CRITICAL for login functionality
try:
    from src.api.auth_simple import router as auth_router
    app.include_router(auth_router)
    logger.info("✅ Simple Auth API loaded successfully")
except Exception as e:
    logger.error(f"❌ Simple Auth API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include enhanced admin router
try:
    from src.api.admin_enhanced import router as admin_enhanced_router
    app.include_router(admin_enhanced_router)
    logger.info("Enhanced Admin API loaded successfully")
except Exception as e:
    logger.error(f"Enhanced Admin API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Force include security router
try:
    from src.api.security import router as security_router
    app.include_router(security_router)
    logger.info("Security API loaded successfully")
except Exception as e:
    logger.error(f"Security API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Force include audit API router
try:
    from src.api.audit_api import router as audit_router
    app.include_router(audit_router)
    logger.info("Audit API loaded successfully")
except Exception as e:
    logger.error(f"Audit API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Force include audit integrity API router
try:
    from src.api.audit_integrity_api import router as audit_integrity_router
    app.include_router(audit_integrity_router)
    logger.info("Audit Integrity API loaded successfully")
except Exception as e:
    logger.error(f"Audit Integrity API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include business metrics router - required for dashboard
try:
    from src.api.business_metrics import router as business_metrics_router
    app.include_router(business_metrics_router)
    logger.info("Business metrics API loaded successfully")
except Exception as e:
    logger.error(f"Business metrics API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include metrics router (alternative business metrics)
try:
    from src.api.metrics import router as metrics_router
    app.include_router(metrics_router)
    logger.info("Metrics API loaded successfully")
except Exception as e:
    logger.error(f"Metrics API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include dashboard router
try:
    from src.api.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("Dashboard API loaded successfully")
except Exception as e:
    logger.error(f"Dashboard API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include workspace router for multi-tenant support
try:
    from src.api.workspace import router as workspace_router
    app.include_router(workspace_router)
    logger.info("Workspace API loaded successfully")
except Exception as e:
    logger.warning(f"Workspace API not available: {e}")

# Include LLM API router for LLM integration
try:
    from src.api.llm import router as llm_router
    app.include_router(llm_router)
    logger.info("LLM API loaded successfully")
except Exception as e:
    logger.warning(f"LLM API not available: {e}")
    import traceback
    traceback.print_exc()

# Dynamically include available API routers
async def include_optional_routers():
    """Include optional API routers if available.
    
    Registers all optional API routers with proper error handling and logging.
    Uses emoji format for clear status indication:
    - ✅ Success
    - ⚠️ Warning (module not available)
    - ❌ Error (registration failed)
    
    Validates: Requirements 3.2 - 详细的日志记录每个 API 的注册状态
    """
    
    # Quality management router
    try:
        from src.api.quality import router as quality_router
        app.include_router(quality_router)
        logger.info("✅ Quality management API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Quality management API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Quality management API failed to load: {e}")
    
    # AI annotation router
    try:
        from src.api.ai_annotation import router as ai_router
        app.include_router(ai_router)
        logger.info("✅ AI annotation API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ AI annotation API not available: {e}")
    except Exception as e:
        logger.error(f"❌ AI annotation API failed to load: {e}")
    
    # Annotation workflow router (pre-annotation, mid-coverage, post-validation)
    # Requirements: 7.1, 7.2, 7.4 - Pre-annotation integration with Label Studio
    try:
        from src.api.annotation import router as annotation_router
        app.include_router(annotation_router)
        logger.info("✅ Annotation Workflow API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Annotation Workflow API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Annotation Workflow API failed to load: {e}")

    # AI Annotation Collaboration API (pre-annotation, mid-coverage, post-validation)
    # Requirements: AI Annotation Methods implementation
    try:
        from src.api.annotation_collaboration import router as annotation_collaboration_router
        app.include_router(annotation_collaboration_router)
        logger.info("✅ AI Annotation Collaboration API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ AI Annotation Collaboration API not available: {e}")
    except Exception as e:
        logger.error(f"❌ AI Annotation Collaboration API failed to load: {e}")

    # Collaboration WebSocket API (real-time presence and conflict detection)
    try:
        from src.api.collaboration_websocket import router as collaboration_websocket_router
        app.include_router(collaboration_websocket_router)
        logger.info("✅ Collaboration WebSocket API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Collaboration WebSocket API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Collaboration WebSocket API failed to load: {e}")
    
    # Billing router
    try:
        from src.api.billing import router as billing_router
        app.include_router(billing_router)
        logger.info("✅ Billing API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Billing API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Billing API failed to load: {e}")

    # License Management API
    # Validates: Requirements 2.1 - License 模块用户需求
    try:
        from src.api.license_router import router as license_router
        app.include_router(license_router)
        _track_api_registration(
            module_path="src.api.license_router",
            prefix="/api/v1/license",
            tags=["License"],
            success=True
        )
        logger.info("✅ License API registered: /api/v1/license")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.license_router",
            prefix="/api/v1/license",
            tags=["License"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ License API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.license_router",
            prefix="/api/v1/license",
            tags=["License"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ License API failed to load: {e}")

    # License Usage API
    # Validates: Requirements 2.1 - 许可证使用监控
    try:
        from src.api.usage_router import router as usage_router
        app.include_router(usage_router)
        _track_api_registration(
            module_path="src.api.usage_router",
            prefix="/api/v1/usage",
            tags=["Usage"],
            success=True
        )
        logger.info("✅ Usage API registered: /api/v1/usage")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.usage_router",
            prefix="/api/v1/usage",
            tags=["Usage"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Usage API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.usage_router",
            prefix="/api/v1/usage",
            tags=["Usage"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Usage API failed to load: {e}")

    # License Activation API
    # Validates: Requirements 2.1 - 许可证激活
    try:
        from src.api.activation_router import router as activation_router
        app.include_router(activation_router)
        _track_api_registration(
            module_path="src.api.activation_router",
            prefix="/api/v1/activation",
            tags=["Activation"],
            success=True
        )
        logger.info("✅ Activation API registered: /api/v1/activation")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.activation_router",
            prefix="/api/v1/activation",
            tags=["Activation"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Activation API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.activation_router",
            prefix="/api/v1/activation",
            tags=["Activation"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Activation API failed to load: {e}")

    # Quality Rules API
    # Validates: Requirements 2.2 - 质量规则管理
    try:
        from src.api.quality_rules import router as quality_rules_router
        app.include_router(quality_rules_router)
        _track_api_registration(
            module_path="src.api.quality_rules",
            prefix="/api/v1/quality-rules",
            tags=["Quality Rules"],
            success=True
        )
        logger.info("✅ Quality Rules API registered: /api/v1/quality-rules")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.quality_rules",
            prefix="/api/v1/quality-rules",
            tags=["Quality Rules"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Quality Rules API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.quality_rules",
            prefix="/api/v1/quality-rules",
            tags=["Quality Rules"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Quality Rules API failed to load: {e}")

    # Quality Reports API
    # Validates: Requirements 2.2 - 质量报告
    try:
        from src.api.quality_reports import router as quality_reports_router
        app.include_router(quality_reports_router)
        _track_api_registration(
            module_path="src.api.quality_reports",
            prefix="/api/v1/quality-reports",
            tags=["Quality Reports"],
            success=True
        )
        logger.info("✅ Quality Reports API registered: /api/v1/quality-reports")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.quality_reports",
            prefix="/api/v1/quality-reports",
            tags=["Quality Reports"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Quality Reports API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.quality_reports",
            prefix="/api/v1/quality-reports",
            tags=["Quality Reports"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Quality Reports API failed to load: {e}")

    # Quality Workflow API
    # Validates: Requirements 2.2 - 质量改进工单
    try:
        from src.api.quality_workflow import router as quality_workflow_router
        app.include_router(quality_workflow_router)
        _track_api_registration(
            module_path="src.api.quality_workflow",
            prefix="/api/v1/quality-workflow",
            tags=["Quality Workflow"],
            success=True
        )
        logger.info("✅ Quality Workflow API registered: /api/v1/quality-workflow")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.quality_workflow",
            prefix="/api/v1/quality-workflow",
            tags=["Quality Workflow"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Quality Workflow API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.quality_workflow",
            prefix="/api/v1/quality-workflow",
            tags=["Quality Workflow"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Quality Workflow API failed to load: {e}")

    # Augmentation API
    # Validates: Requirements 2.3 - 数据增强功能
    try:
        from src.api.augmentation import router as augmentation_router
        app.include_router(augmentation_router)
        _track_api_registration(
            module_path="src.api.augmentation",
            prefix="/api/v1/augmentation",
            tags=["Augmentation"],
            success=True
        )
        logger.info("✅ Augmentation API registered: /api/v1/augmentation")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.augmentation",
            prefix="/api/v1/augmentation",
            tags=["Augmentation"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Augmentation API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.augmentation",
            prefix="/api/v1/augmentation",
            tags=["Augmentation"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Augmentation API failed to load: {e}")

    # Ticket management router
    try:
        from src.api.ticket_api import router as ticket_router
        app.include_router(ticket_router)
        logger.info("✅ Ticket management API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Ticket management API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Ticket management API failed to load: {e}")

    # Performance evaluation router
    try:
        from src.api.evaluation_api import router as evaluation_router
        app.include_router(evaluation_router)
        logger.info("✅ Performance evaluation API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Performance evaluation API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Performance evaluation API failed to load: {e}")

    # Quality analysis router (trends, auto-retrain, pricing, incentives)
    try:
        from src.api.quality_api import router as quality_analysis_router
        app.include_router(quality_analysis_router)
        logger.info("✅ Quality analysis API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Quality analysis API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Quality analysis API failed to load: {e}")

    # Quality monitoring router (dashboard, alerts, anomalies)
    try:
        from src.api.monitoring_api import router as monitoring_router
        app.include_router(monitoring_router)
        logger.info("✅ Quality monitoring API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Quality monitoring API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Quality monitoring API failed to load: {e}")

    # Enhancement router
    try:
        from src.api.enhancement import router as enhancement_router
        app.include_router(enhancement_router)
        logger.info("✅ Enhancement API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Enhancement API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Enhancement API failed to load: {e}")
    
    # Export router
    try:
        from src.api.export import router as export_router
        app.include_router(export_router)
        logger.info("✅ Export API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Export API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Export API failed to load: {e}")
    
    # RAG Agent router
    try:
        from src.api.rag_agent import router as rag_router
        app.include_router(rag_router)
        logger.info("✅ RAG Agent API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ RAG Agent API not available: {e}")
    except Exception as e:
        logger.error(f"❌ RAG Agent API failed to load: {e}")
    
    # Security router
    try:
        from src.api.security import router as security_router
        app.include_router(security_router)
        logger.info("✅ Security API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Security API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Security API failed to load: {e}")
    
    # RBAC (Role-Based Access Control) API
    try:
        from src.api.rbac import router as rbac_router
        app.include_router(rbac_router)
        _track_api_registration(
            module_path="src.api.rbac",
            prefix="/api/v1/rbac",
            tags=["RBAC"],
            success=True
        )
        logger.info("✅ RBAC API registered: /api/v1/rbac")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.rbac",
            prefix="/api/v1/rbac",
            tags=["RBAC"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ RBAC API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.rbac",
            prefix="/api/v1/rbac",
            tags=["RBAC"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ RBAC API failed to load: {e}")
    
    # SSO (Single Sign-On) API
    try:
        from src.api.sso import router as sso_router
        app.include_router(sso_router)
        _track_api_registration(
            module_path="src.api.sso",
            prefix="/api/v1/sso",
            tags=["SSO"],
            success=True
        )
        logger.info("✅ SSO API registered: /api/v1/sso")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.sso",
            prefix="/api/v1/sso",
            tags=["SSO"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ SSO API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.sso",
            prefix="/api/v1/sso",
            tags=["SSO"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ SSO API failed to load: {e}")
    
    # Session Management API
    try:
        from src.api.sessions import router as sessions_router
        app.include_router(sessions_router)
        _track_api_registration(
            module_path="src.api.sessions",
            prefix="/api/v1/sessions",
            tags=["Sessions"],
            success=True
        )
        logger.info("✅ Sessions API registered: /api/v1/sessions")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.sessions",
            prefix="/api/v1/sessions",
            tags=["Sessions"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Sessions API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.sessions",
            prefix="/api/v1/sessions",
            tags=["Sessions"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Sessions API failed to load: {e}")
    
    # Data Permissions API
    try:
        from src.api.data_permission_router import router as data_permission_router
        app.include_router(data_permission_router)
        _track_api_registration(
            module_path="src.api.data_permission_router",
            prefix="/api/v1/data-permissions",
            tags=["Data Permissions"],
            success=True
        )
        logger.info("✅ Data Permissions API registered: /api/v1/data-permissions")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.data_permission_router",
            prefix="/api/v1/data-permissions",
            tags=["Data Permissions"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Data Permissions API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.data_permission_router",
            prefix="/api/v1/data-permissions",
            tags=["Data Permissions"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Data Permissions API failed to load: {e}")
    
    # Collaboration router
    try:
        from src.api.collaboration import router as collaboration_router
        app.include_router(collaboration_router)
        logger.info("✅ Collaboration API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Collaboration API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Collaboration API failed to load: {e}")
    
    # Ontology Expert Collaboration router
    # Requirements: Ontology Expert Collaboration spec - Tasks 15.1-15.7
    try:
        from src.api.ontology_expert_collaboration import router as ontology_collab_router
        app.include_router(ontology_collab_router)
        _track_api_registration(
            module_path="src.api.ontology_expert_collaboration",
            prefix="/api/v1/ontology-collaboration",
            tags=["Ontology Expert Collaboration"],
            success=True
        )
        logger.info("✅ Ontology Expert Collaboration API registered: /api/v1/ontology-collaboration")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.ontology_expert_collaboration",
            prefix="/api/v1/ontology-collaboration",
            tags=["Ontology Expert Collaboration"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Ontology Expert Collaboration API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.ontology_expert_collaboration",
            prefix="/api/v1/ontology-collaboration",
            tags=["Ontology Expert Collaboration"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Ontology Expert Collaboration API failed to load: {e}")
    
    # Ontology Expert Collaboration WebSocket router
    # Requirements: Ontology Expert Collaboration spec - Task 16
    try:
        from src.api.ontology_collaboration_websocket import router as ontology_ws_router
        app.include_router(ontology_ws_router)
        _track_api_registration(
            module_path="src.api.ontology_collaboration_websocket",
            prefix="/api/v1/ontology-collaboration/ws",
            tags=["Ontology Expert Collaboration WebSocket"],
            success=True
        )
        logger.info("✅ Ontology Expert Collaboration WebSocket API registered")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.ontology_collaboration_websocket",
            prefix="/api/v1/ontology-collaboration/ws",
            tags=["Ontology Expert Collaboration WebSocket"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Ontology Expert Collaboration WebSocket API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.ontology_collaboration_websocket",
            prefix="/api/v1/ontology-collaboration/ws",
            tags=["Ontology Expert Collaboration WebSocket"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Ontology Expert Collaboration WebSocket API failed to load: {e}")
    
    # Business metrics router
    try:
        from src.api.business_metrics import router as business_metrics_router
        app.include_router(business_metrics_router)
        logger.info("✅ Business metrics API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Business metrics API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Business metrics API failed to load: {e}")

    # Text-to-SQL router
    try:
        from src.api.text_to_sql import router as text_to_sql_router
        app.include_router(text_to_sql_router)
        logger.info("✅ Text-to-SQL API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Text-to-SQL API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Text-to-SQL API failed to load: {e}")

    # Knowledge Graph router
    try:
        from src.knowledge_graph.api.knowledge_graph_api import router as knowledge_graph_router
        app.include_router(knowledge_graph_router)
        logger.info("✅ Knowledge Graph API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Knowledge Graph API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Knowledge Graph API failed to load: {e}")

    # i18n router
    try:
        from src.api.i18n import router as i18n_router
        app.include_router(i18n_router)
        logger.info("✅ i18n API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ i18n API not available: {e}")
    except Exception as e:
        logger.error(f"❌ i18n API failed to load: {e}")

    # AI Integration - Gateway Management router
    # Requirements: AI Application Integration spec - Tasks 13.1
    try:
        from src.api.ai_integration_gateways import router as ai_gateways_router
        app.include_router(ai_gateways_router)
        _track_api_registration(
            module_path="src.api.ai_integration_gateways",
            prefix="/api/v1/ai-integration/gateways",
            tags=["AI Gateway Management"],
            success=True
        )
        logger.info("✅ AI Gateway Management API registered: /api/v1/ai-integration/gateways")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.ai_integration_gateways",
            prefix="/api/v1/ai-integration/gateways",
            tags=["AI Gateway Management"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ AI Gateway Management API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.ai_integration_gateways",
            prefix="/api/v1/ai-integration/gateways",
            tags=["AI Gateway Management"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ AI Gateway Management API failed to load: {e}")

    # AI Integration - Skill Management router
    # Requirements: AI Application Integration spec - Tasks 13.2
    try:
        from src.api.ai_integration_skills import router as ai_skills_router
        app.include_router(ai_skills_router)
        _track_api_registration(
            module_path="src.api.ai_integration_skills",
            prefix="/api/v1/ai-integration/skills",
            tags=["AI Skill Management"],
            success=True
        )
        logger.info("✅ AI Skill Management API registered: /api/v1/ai-integration/skills")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.ai_integration_skills",
            prefix="/api/v1/ai-integration/skills",
            tags=["AI Skill Management"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ AI Skill Management API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.ai_integration_skills",
            prefix="/api/v1/ai-integration/skills",
            tags=["AI Skill Management"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ AI Skill Management API failed to load: {e}")

    # AI Integration - Data Access router
    # Requirements: AI Application Integration spec - Tasks 13.3
    try:
        from src.api.ai_integration_data import router as ai_data_router
        app.include_router(ai_data_router)
        _track_api_registration(
            module_path="src.api.ai_integration_data",
            prefix="/api/v1/ai-integration/data",
            tags=["AI Data Access"],
            success=True
        )
        logger.info("✅ AI Data Access API registered: /api/v1/ai-integration/data")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.ai_integration_data",
            prefix="/api/v1/ai-integration/data",
            tags=["AI Data Access"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ AI Data Access API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.ai_integration_data",
            prefix="/api/v1/ai-integration/data",
            tags=["AI Data Access"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ AI Data Access API failed to load: {e}")

    # AI Integration - Workflow Designer router
    # Requirements: AI Application Integration spec - Tasks 23.2
    try:
        from src.api.ai_integration_workflows import router as ai_workflows_router
        app.include_router(ai_workflows_router)
        _track_api_registration(
            module_path="src.api.ai_integration_workflows",
            prefix="/api/v1/ai-integration/workflows",
            tags=["AI Workflow Designer"],
            success=True
        )
        logger.info("✅ AI Workflow Designer API registered: /api/v1/ai-integration/workflows")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.ai_integration_workflows",
            prefix="/api/v1/ai-integration/workflows",
            tags=["AI Workflow Designer"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ AI Workflow Designer API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.ai_integration_workflows",
            prefix="/api/v1/ai-integration/workflows",
            tags=["AI Workflow Designer"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ AI Workflow Designer API failed to load: {e}")

    # Compliance Reports API
    try:
        from src.api.compliance_reports import router as compliance_router
        app.include_router(compliance_router)
        logger.info("✅ Compliance Reports API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Compliance Reports API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Compliance Reports API failed to load: {e}")
    
    # Data Sync API
    try:
        from src.api.data_sync import router as data_sync_router
        app.include_router(data_sync_router)
        logger.info("✅ Data Sync API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Data Sync API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Data Sync API failed to load: {e}")

    # AI Assistant API
    try:
        from src.api.ai_assistant import router as ai_assistant_router
        app.include_router(ai_assistant_router)
        logger.info("✅ AI Assistant API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ AI Assistant API not available: {e}")
    except Exception as e:
        logger.error(f"❌ AI Assistant API failed to load: {e}")

    # Skill Admin API (OpenClaw skill management)
    try:
        from src.api.skill_admin import router as skill_admin_router
        app.include_router(skill_admin_router)
        logger.info("✅ Skill Admin API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Skill Admin API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Skill Admin API failed to load: {e}")

    # Datalake/Warehouse API
    # Validates: Requirements 2.1 - 数据湖/数仓数据源管理
    try:
        from src.sync.connectors.datalake.router import router as datalake_router
        app.include_router(datalake_router)
        _track_api_registration(
            module_path="src.sync.connectors.datalake.router",
            prefix="/api/v1/datalake",
            tags=["Datalake"],
            success=True
        )
        logger.info("✅ Datalake API registered: /api/v1/datalake")
    except ImportError as e:
        _track_api_registration(
            module_path="src.sync.connectors.datalake.router",
            prefix="/api/v1/datalake",
            tags=["Datalake"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Datalake API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.sync.connectors.datalake.router",
            prefix="/api/v1/datalake",
            tags=["Datalake"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Datalake API failed to load: {e}")
    
    # SOX Compliance API - moved to main app setup for immediate availability
    # This is handled in the main app setup section below

    # Desensitization API (if not already included)
    try:
        from src.api.desensitization import router as desensitization_router
        app.include_router(desensitization_router)
        logger.info("✅ Desensitization API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Desensitization API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Desensitization API failed to load: {e}")

    # Auto-Desensitization API
    try:
        from src.api.auto_desensitization import router as auto_desensitization_router
        app.include_router(auto_desensitization_router)
        logger.info("✅ Auto-Desensitization API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Auto-Desensitization API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Auto-Desensitization API failed to load: {e}")

    # Real-time Alert API
    try:
        from src.api.real_time_alert_api import router as real_time_alert_router
        app.include_router(real_time_alert_router)
        logger.info("✅ Real-time Alert API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Real-time Alert API not available: {e}")
    
    # Security Monitoring API (if not already included)
    try:
        from src.api.security_monitoring_api import router as security_monitoring_router
        app.include_router(security_monitoring_router)
        logger.info("✅ Security Monitoring API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Security Monitoring API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Security Monitoring API failed to load: {e}")

    # Permission Monitoring API (if not already included)
    try:
        from src.api.permission_monitoring import router as permission_monitoring_router
        app.include_router(permission_monitoring_router)
        logger.info("✅ Permission Monitoring API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Permission Monitoring API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Permission Monitoring API failed to load: {e}")

    # Cache Management API (if not already included)
    try:
        from src.api.cache_management import router as cache_management_router
        app.include_router(cache_management_router)
        logger.info("✅ Cache Management API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Cache Management API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Cache Management API failed to load: {e}")

    # Security Dashboard API (if not already included)
    try:
        from src.api.security_dashboard_api import router as security_dashboard_router
        app.include_router(security_dashboard_router)
        logger.info("✅ Security Dashboard API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Security Dashboard API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Security Dashboard API failed to load: {e}")
    
    # Zero Leakage Prevention API
    try:
        from src.api.zero_leakage_api import router as zero_leakage_router
        app.include_router(zero_leakage_router)
        logger.info("✅ Zero Leakage Prevention API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Zero Leakage Prevention API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Zero Leakage Prevention API failed to load: {e}")
    
    # Compliance Performance API (< 30 seconds target)
    try:
        from src.api.compliance_performance_api import router as compliance_performance_router
        app.include_router(compliance_performance_router)
        logger.info("✅ Compliance Performance API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Compliance Performance API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Compliance Performance API failed to load: {e}")
    
    # Complete Event Capture API (100% Security Event Capture)
    try:
        from src.api.complete_event_capture_api import router as complete_capture_router
        app.include_router(complete_capture_router)
        logger.info("✅ Complete Event Capture API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Complete Event Capture API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Complete Event Capture API failed to load: {e}")
    
    # GDPR Compliance Verification API
    try:
        from src.api.gdpr_verification_api import router as gdpr_verification_router
        app.include_router(gdpr_verification_router)
        logger.info("✅ GDPR Compliance Verification API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ GDPR Compliance Verification API not available: {e}")
    except Exception as e:
        logger.error(f"❌ GDPR Compliance Verification API failed to load: {e}")

    # Quality Governance API (Quality Workflow Module)
    try:
        from src.api.quality_governance_api import router as quality_governance_router
        app.include_router(quality_governance_router)
        logger.info("✅ Quality Governance API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Quality Governance API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Quality Governance API failed to load: {e}")

    # Versioning API
    # Validates: 数据版本管理功能
    try:
        from src.api.versioning import router as versioning_router
        app.include_router(versioning_router)
        _track_api_registration(
            module_path="src.api.versioning",
            prefix="/api/v1/versioning",
            tags=["Versioning"],
            success=True
        )
        logger.info("✅ Versioning API registered: /api/v1/versioning")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.versioning",
            prefix="/api/v1/versioning",
            tags=["Versioning"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Versioning API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.versioning",
            prefix="/api/v1/versioning",
            tags=["Versioning"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Versioning API failed to load: {e}")

    # Data Structuring API
    try:
        from src.api.structuring import router as structuring_router
        app.include_router(structuring_router)
        logger.info("✅ Data Structuring API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Data Structuring API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Data Structuring API failed to load: {e}")

    # Vectorization API
    try:
        from src.api.vectorization import router as vectorization_router
        app.include_router(vectorization_router)
        logger.info("✅ Vectorization API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Vectorization API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Vectorization API failed to load: {e}")

    # Semantic API
    try:
        from src.api.semantic import router as semantic_router
        app.include_router(semantic_router)
        logger.info("✅ Semantic API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Semantic API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Semantic API failed to load: {e}")

    # Output API registration summary
    # Validates: Requirements 3.2 - 详细的日志记录每个 API 的注册状态
    _log_api_registration_summary()

# Include ISO 27001 Compliance API router - comprehensive information security management
try:
    from src.api.iso27001_compliance_api import router as iso27001_compliance_router
    app.include_router(iso27001_compliance_router)
    logger.info("✅ ISO 27001 Compliance API loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ ISO 27001 Compliance API not available: {e}")
except Exception as e:
    logger.error(f"❌ ISO 27001 Compliance API failed to load: {e}")

# Include Data Protection Compliance API router - multi-regulation data protection compliance
try:
    from src.api.data_protection_compliance_api import router as data_protection_compliance_router
    app.include_router(data_protection_compliance_router)
    logger.info("✅ Data Protection Compliance API loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Data Protection Compliance API not available: {e}")
except Exception as e:
    logger.error(f"❌ Data Protection Compliance API failed to load: {e}")

# Include Industry-Specific Compliance API router - HIPAA, PCI-DSS, PIPL, etc.
try:
    from src.api.industry_compliance_api import router as industry_compliance_router
    app.include_router(industry_compliance_router)
    logger.info("✅ Industry-Specific Compliance API loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Industry-Specific Compliance API not available: {e}")
except Exception as e:
    logger.error(f"❌ Industry-Specific Compliance API failed to load: {e}")

# Include Version Control API router - data version management
try:
    from src.api.version_api import router as version_router
    app.include_router(version_router)
    logger.info("✅ Version Control API loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Version Control API not available: {e}")
except Exception as e:
    logger.error(f"❌ Version Control API failed to load: {e}")

# Include Data Lineage API router - lineage tracking and impact analysis
try:
    from src.api.lineage_api import router as lineage_router
    app.include_router(lineage_router)
    logger.info("✅ Data Lineage API loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Data Lineage API not available: {e}")
except Exception as e:
    logger.error(f"❌ Data Lineage API failed to load: {e}")

# LLM Integration API
try:
    from src.api.llm import router as llm_router
    app.include_router(llm_router)
    logger.info("✅ LLM Integration API loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ LLM Integration API not available: {e}")
except Exception as e:
    logger.error(f"❌ LLM Integration API failed to load: {e}")

# Multi-Tenant Workspace API
try:
    from src.api.multi_tenant import router as multi_tenant_router
    app.include_router(multi_tenant_router)
    logger.info("✅ Multi-Tenant Workspace API loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Multi-Tenant Workspace API not available: {e}")
except Exception as e:
    logger.error(f"❌ Multi-Tenant Workspace API failed to load: {e}")


# Include optional routers synchronously at module load time
def _include_optional_routers_sync():
    """Include optional API routers synchronously.
    
    Registers API routers at module load time with proper error handling.
    Uses emoji format for clear status indication:
    - ✅ Success
    - ⚠️ Warning (module not available)
    - ❌ Error (registration failed)
    
    Validates: Requirements 3.2 - 详细的日志记录每个 API 的注册状态
    """
    
    # Billing router - load synchronously
    try:
        from src.api.billing import router as billing_router
        app.include_router(billing_router)
        logger.info("✅ Billing API loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ Billing API not available: {e}")
    except Exception as e:
        logger.error(f"❌ Billing API failed to load: {e}")
    
    # RBAC (Role-Based Access Control) API
    try:
        from src.api.rbac import router as rbac_router
        app.include_router(rbac_router)
        _track_api_registration(
            module_path="src.api.rbac",
            prefix="/api/v1/rbac",
            tags=["RBAC"],
            success=True
        )
        logger.info("✅ RBAC API registered: /api/v1/rbac")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.rbac",
            prefix="/api/v1/rbac",
            tags=["RBAC"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ RBAC API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.rbac",
            prefix="/api/v1/rbac",
            tags=["RBAC"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ RBAC API failed to load: {e}")
    
    # SSO (Single Sign-On) API
    try:
        from src.api.sso import router as sso_router
        app.include_router(sso_router)
        _track_api_registration(
            module_path="src.api.sso",
            prefix="/api/v1/sso",
            tags=["SSO"],
            success=True
        )
        logger.info("✅ SSO API registered: /api/v1/sso")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.sso",
            prefix="/api/v1/sso",
            tags=["SSO"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ SSO API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.sso",
            prefix="/api/v1/sso",
            tags=["SSO"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ SSO API failed to load: {e}")
    
    # Session Management API
    try:
        from src.api.sessions import router as sessions_router
        app.include_router(sessions_router)
        _track_api_registration(
            module_path="src.api.sessions",
            prefix="/api/v1/sessions",
            tags=["Sessions"],
            success=True
        )
        logger.info("✅ Sessions API registered: /api/v1/sessions")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.sessions",
            prefix="/api/v1/sessions",
            tags=["Sessions"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Sessions API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.sessions",
            prefix="/api/v1/sessions",
            tags=["Sessions"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Sessions API failed to load: {e}")
    
    # Data Permissions API
    try:
        from src.api.data_permission_router import router as data_permission_router
        app.include_router(data_permission_router)
        _track_api_registration(
            module_path="src.api.data_permission_router",
            prefix="/api/v1/data-permissions",
            tags=["Data Permissions"],
            success=True
        )
        logger.info("✅ Data Permissions API registered: /api/v1/data-permissions")
    except ImportError as e:
        _track_api_registration(
            module_path="src.api.data_permission_router",
            prefix="/api/v1/data-permissions",
            tags=["Data Permissions"],
            success=False,
            error=str(e)
        )
        logger.warning(f"⚠️ Data Permissions API not available: {e}")
    except Exception as e:
        _track_api_registration(
            module_path="src.api.data_permission_router",
            prefix="/api/v1/data-permissions",
            tags=["Data Permissions"],
            success=False,
            error=str(e)
        )
        logger.error(f"❌ Data Permissions API failed to load: {e}")

# Call synchronously at module load
_include_optional_routers_sync()


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting SuperInsight application...")
    await include_optional_routers()
    
    # Initialize LLM Integration Module
    # Requirements: All backend requirements from LLM Integration spec
    try:
        from src.ai.llm_switcher import get_initialized_switcher
        from src.ai.llm.health_monitor import get_initialized_health_monitor
        
        # Initialize LLM Switcher with cache client
        logger.info("Initializing LLM Switcher...")
        llm_switcher = await get_initialized_switcher()
        
        # Try to set up Redis cache client for response caching (Requirement 10.2)
        try:
            import redis.asyncio as redis
            from src.config.settings import settings
            
            redis_url = getattr(settings, 'redis_url', None) or "redis://localhost:6379"
            cache_client = redis.from_url(redis_url, decode_responses=True)
            llm_switcher.set_cache_client(cache_client)
            logger.info("LLM response caching enabled with Redis")
        except Exception as cache_error:
            logger.warning(f"Redis cache not available for LLM, using in-memory cache: {cache_error}")
        
        # Start Health Monitor background task (Requirements 5.1-5.5)
        logger.info("Starting LLM Health Monitor...")
        health_monitor = await get_initialized_health_monitor(switcher=llm_switcher)
        logger.info("LLM Health Monitor started successfully")
        
        logger.info("LLM Integration Module initialized successfully")
        
    except ImportError as e:
        logger.warning(f"LLM Integration Module not available: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM Integration Module: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("SuperInsight application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down SuperInsight application...")
    
    # Shutdown LLM Health Monitor
    try:
        from src.ai.llm.health_monitor import get_health_monitor
        health_monitor = get_health_monitor()
        if health_monitor and health_monitor.is_running:
            await health_monitor.stop()
            logger.info("LLM Health Monitor shutdown successfully")
    except Exception as e:
        logger.error(f"Failed to shutdown LLM Health Monitor: {e}")
    
    # Shutdown real-time alert system
    try:
        from src.security.alert_system_startup import shutdown_real_time_alerts
        alert_success = await shutdown_real_time_alerts()
        if alert_success:
            logger.info("Real-time alert system shutdown successfully")
        else:
            logger.warning("Real-time alert system failed to shutdown cleanly")
    except Exception as e:
        logger.error(f"Failed to shutdown real-time alerts: {e}")
    
    logger.info("SuperInsight application shutdown completed")


# Additional API information
@app.get("/api/info")
async def api_info():
    """API information endpoint.
    
    Returns comprehensive API information including:
    - Application name and version
    - Available endpoints
    - Features list
    - Deployment modes
    - System status
    - API registration status (registered_count, failed_count, validation)
    
    Validates: Requirements 2.5 - 清晰的 API 注册状态
    Validates: Requirements 8.5 - /api/info 端点返回完整的 API 列表
    """
    # Get API registration status
    registration_status = get_api_registration_status()
    
    # Build endpoints_summary for high priority APIs
    # Validates: Requirements 2.5 - 清晰的 API 注册状态
    endpoints_summary = {
        # License module
        "license": "/api/v1/license",
        "license_usage": "/api/v1/usage",
        "license_activation": "/api/v1/activation",
        # Quality module
        "quality_rules": "/api/v1/quality-rules",
        "quality_reports": "/api/v1/quality-reports",
        "quality_workflow": "/api/v1/quality-workflow",
        # Augmentation module
        "augmentation": "/api/v1/augmentation",
        # Versioning module
        "versioning": "/api/v1/versioning",
        # Security module
        "security_sessions": "/api/v1/sessions",
        "security_sso": "/api/v1/sso",
        "security_rbac": "/api/v1/rbac",
        "security_data_permissions": "/api/v1/data-permissions",
    }
    
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        # API Registration Status
        "total": registration_status["registered_count"] + registration_status["failed_count"],
        "registered_count": registration_status["registered_count"],
        "failed_count": registration_status["failed_count"],
        "registered": registration_status["registered"],
        "failed": registration_status["failed"],
        "validation": registration_status["validation"],
        # High priority endpoints summary
        "endpoints_summary": endpoints_summary,
        "endpoints": {
            "extraction": "/api/v1/extraction",
            "quality": "/api/quality",
            "quality_analysis": "/api/v1/quality",
            "monitoring": "/api/v1/monitoring",
            "ai_annotation": "/api/ai",
            "billing": "/api/billing",
            "ticket": "/api/v1/tickets",
            "evaluation": "/api/v1/evaluation",
            "enhancement": "/api/enhancement",
            "export": "/api/export",
            "rag_agent": "/api/rag",
            "security": "/api/security",
            "audit": "/api/audit",
            "collaboration": "/api/collaboration",
            "business_metrics": "/api/business-metrics",
            "text_to_sql": "/api/v1/text-to-sql",
            "knowledge_graph": "/api/v1/knowledge-graph",
            "i18n": "/api/i18n",
            "desensitization": "/api/desensitization",
            "auto_desensitization": "/api/auto-desensitization",
            "zero_leakage": "/api/zero-leakage",
            "compliance_reports": "/api/compliance",
            "compliance_performance": "/api/compliance/performance",
            "complete_event_capture": "/api/v1/security/capture",
            "data_protection_compliance": "/api/data-protection-compliance",
            "language_settings": "/api/settings/language",
            "multi_tenant": "/api/v1/tenants",
            "workspaces": "/api/v1/workspaces",
            "quotas": "/api/v1/quotas",
            "shares": "/api/v1/shares",
            "admin": "/api/v1/admin",
            "health": "/health",
            "system_status": "/system/status",
            "metrics": "/system/metrics",
            "services": "/system/services",
            "docs": "/docs"
        },
        "features": [
            "安全数据提取 (Database, File, Web, API)",
            "批量数据处理",
            "异步任务处理",
            "进度跟踪",
            "多格式支持 (PDF, DOCX, HTML, JSON)",
            "数据库支持 (MySQL, PostgreSQL, Oracle)",
            "质量管理与评估 (Ragas 集成)",
            "质量工单管理",
            "数据修复功能",
            "AI 预标注服务",
            "计费结算系统",
            "数据增强与重构",
            "多格式数据导出",
            "RAG 和 Agent 测试接口",
            "Text-to-SQL 自然语言查询",
            "知识图谱 (Neo4j 图数据库)",
            "实体抽取与关系挖掘 (spaCy + jieba)",
            "图查询与智能推理",
            "安全控制与权限管理",
            "企业级审计日志系统",
            "审计事件查询与导出",
            "风险评估与威胁检测",
            "安全监控与告警",
            "合规报告生成",
            "敏感数据自动检测与脱敏",
            "实时数据脱敏中间件",
            "批量数据脱敏处理",
            "脱敏质量验证与监控",
            "脱敏策略管理",
            "系统监控与健康检查",
            "统一错误处理",
            "性能指标收集",
            "业务指标监控 (标注效率、用户活跃度、AI 性能)",
            "实时业务分析与趋势预测",
            "智能工单派发 (技能匹配、负载均衡)",
            "SLA 监控与告警",
            "绩效考核与申诉",
            "质量趋势分析与预测",
            "自动重训练触发",
            "质量驱动计费",
            "激励与惩罚机制",
            "实时质量监控仪表盘",
            "异常检测与告警",
            "培训需求分析",
            "客户反馈收集与情感分析",
            "多语言支持 (中文/英文)",
            "动态语言切换",
            "国际化 (i18n) API"
        ],
        "deployment_modes": [
            "腾讯云 TCB 云托管",
            "Docker Compose 私有化部署",
            "混合云部署"
        ],
        "system_status": system_manager.get_system_status()["overall_status"]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower()
    )