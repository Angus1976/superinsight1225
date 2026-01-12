"""
Deployment module for SuperInsight Platform.

Provides deployment management, TCB integration, and CI/CD support.
"""

from .tcb_client import TCBClient, TCBConfig, ServiceConfig, DeploymentResult
from .blue_green_deployer import (
    BlueGreenDeployer,
    BlueGreenConfig,
    DeploymentStrategy,
    DeploymentPhase,
    EnvironmentColor
)
from .tcb_auto_scaler import (
    TCBAutoScaler,
    TCBAutoScalerConfig,
    ScalingRule,
    ScalingMetricType,
    initialize_tcb_auto_scaler,
    get_tcb_auto_scaler
)
from .tcb_env_config import (
    TCBEnvConfigManager,
    EnvironmentConfig,
    Environment,
    initialize_tcb_env_config_manager,
    get_tcb_env_config_manager
)
from .tcb_monitoring import (
    TCBMonitoringService,
    TCBMonitoringConfig,
    AlertRule,
    AlertSeverity,
    initialize_tcb_monitoring,
    shutdown_tcb_monitoring,
    get_tcb_monitoring_service
)
from .tcb_logger import (
    TCBLogManager,
    TCBLoggerConfig,
    ContextLogger,
    initialize_tcb_logging,
    get_tcb_log_manager,
    get_context_logger
)

__all__ = [
    # TCB Client
    "TCBClient",
    "TCBConfig",
    "ServiceConfig",
    "DeploymentResult",
    # Blue-Green Deployer
    "BlueGreenDeployer",
    "BlueGreenConfig",
    "DeploymentStrategy",
    "DeploymentPhase",
    "EnvironmentColor",
    # Auto-Scaler
    "TCBAutoScaler",
    "TCBAutoScalerConfig",
    "ScalingRule",
    "ScalingMetricType",
    "initialize_tcb_auto_scaler",
    "get_tcb_auto_scaler",
    # Environment Config
    "TCBEnvConfigManager",
    "EnvironmentConfig",
    "Environment",
    "initialize_tcb_env_config_manager",
    "get_tcb_env_config_manager",
    # Monitoring
    "TCBMonitoringService",
    "TCBMonitoringConfig",
    "AlertRule",
    "AlertSeverity",
    "initialize_tcb_monitoring",
    "shutdown_tcb_monitoring",
    "get_tcb_monitoring_service",
    # Logging
    "TCBLogManager",
    "TCBLoggerConfig",
    "ContextLogger",
    "initialize_tcb_logging",
    "get_tcb_log_manager",
    "get_context_logger",
]
