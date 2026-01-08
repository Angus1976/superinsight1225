"""
Monitoring System Configuration.

Centralized configuration for all monitoring components.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class MonitoringMode(str, Enum):
    """Monitoring operation modes."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class MetricsConfig:
    """Metrics collection configuration."""
    collection_interval: int = 10  # seconds
    retention_points: int = 10000
    export_port: int = 8001
    export_path: str = "/metrics"
    enable_system_metrics: bool = True
    enable_process_metrics: bool = True
    
    # Histogram buckets for latency metrics
    latency_buckets: List[float] = field(default_factory=lambda: [
        0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
    ])


@dataclass
class AlertConfig:
    """Alert system configuration."""
    evaluation_interval: int = 30  # seconds
    enable_default_rules: bool = True
    
    # Default thresholds
    latency_warning_threshold: float = 5.0  # seconds
    latency_critical_threshold: float = 10.0  # seconds
    error_rate_warning_threshold: float = 0.05  # 5%
    error_rate_critical_threshold: float = 0.20  # 20%
    queue_depth_warning_threshold: int = 1000
    queue_depth_critical_threshold: int = 5000
    throughput_warning_threshold: float = 100.0  # records/second


@dataclass
class NotificationConfig:
    """Notification system configuration."""
    processing_interval: int = 10  # seconds
    aggregation_window: int = 300  # seconds (5 minutes)
    deduplication_window: int = 3600  # seconds (1 hour)
    max_retry_attempts: int = 3
    
    # Email configuration
    email_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_use_tls: bool = True
    
    # Slack configuration
    slack_enabled: bool = False
    slack_webhook_url: Optional[str] = None
    
    # Webhook configuration
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class GrafanaConfig:
    """Grafana integration configuration."""
    enabled: bool = False
    url: Optional[str] = None
    api_key: Optional[str] = None
    prometheus_url: str = "http://localhost:9090"
    folder_name: str = "Data Sync System"
    auto_deploy_dashboards: bool = True
    dashboard_update_interval: int = 3600  # seconds (1 hour)


@dataclass
class PrometheusConfig:
    """Prometheus configuration."""
    enabled: bool = True
    url: str = "http://localhost:9090"
    scrape_interval: int = 15  # seconds
    evaluation_interval: int = 15  # seconds
    
    # Scrape targets
    sync_service_target: str = "localhost:8001"
    connector_target: str = "localhost:8002"
    websocket_target: str = "localhost:8003"
    queue_target: str = "localhost:8004"


@dataclass
class MonitoringConfig:
    """Complete monitoring system configuration."""
    mode: MonitoringMode = MonitoringMode.DEVELOPMENT
    
    # Component configurations
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    grafana: GrafanaConfig = field(default_factory=GrafanaConfig)
    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)
    
    # Service intervals
    cleanup_interval: int = 86400  # seconds (24 hours)
    health_check_interval: int = 60  # seconds
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def load_config_from_env() -> MonitoringConfig:
    """Load monitoring configuration from environment variables."""
    config = MonitoringConfig()
    
    # Mode
    config.mode = MonitoringMode(os.getenv("MONITORING_MODE", "development"))
    
    # Metrics configuration
    config.metrics.collection_interval = int(os.getenv("METRICS_COLLECTION_INTERVAL", "10"))
    config.metrics.retention_points = int(os.getenv("METRICS_RETENTION_POINTS", "10000"))
    config.metrics.export_port = int(os.getenv("METRICS_EXPORT_PORT", "8001"))
    config.metrics.export_path = os.getenv("METRICS_EXPORT_PATH", "/metrics")
    
    # Alert configuration
    config.alerts.evaluation_interval = int(os.getenv("ALERT_EVALUATION_INTERVAL", "30"))
    config.alerts.latency_warning_threshold = float(os.getenv("ALERT_LATENCY_WARNING", "5.0"))
    config.alerts.latency_critical_threshold = float(os.getenv("ALERT_LATENCY_CRITICAL", "10.0"))
    config.alerts.error_rate_warning_threshold = float(os.getenv("ALERT_ERROR_RATE_WARNING", "0.05"))
    config.alerts.error_rate_critical_threshold = float(os.getenv("ALERT_ERROR_RATE_CRITICAL", "0.20"))
    
    # Notification configuration
    config.notifications.processing_interval = int(os.getenv("NOTIFICATION_PROCESSING_INTERVAL", "10"))
    config.notifications.aggregation_window = int(os.getenv("NOTIFICATION_AGGREGATION_WINDOW", "300"))
    config.notifications.deduplication_window = int(os.getenv("NOTIFICATION_DEDUPLICATION_WINDOW", "3600"))
    
    # Email configuration
    config.notifications.email_enabled = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "false").lower() == "true"
    config.notifications.smtp_host = os.getenv("SMTP_HOST")
    config.notifications.smtp_port = int(os.getenv("SMTP_PORT", "587"))
    config.notifications.smtp_username = os.getenv("SMTP_USERNAME")
    config.notifications.smtp_password = os.getenv("SMTP_PASSWORD")
    config.notifications.smtp_from_email = os.getenv("SMTP_FROM_EMAIL")
    config.notifications.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # Slack configuration
    config.notifications.slack_enabled = os.getenv("SLACK_NOTIFICATIONS_ENABLED", "false").lower() == "true"
    config.notifications.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    # Webhook configuration
    config.notifications.webhook_enabled = os.getenv("WEBHOOK_NOTIFICATIONS_ENABLED", "false").lower() == "true"
    config.notifications.webhook_url = os.getenv("WEBHOOK_URL")
    
    # Grafana configuration
    config.grafana.enabled = os.getenv("GRAFANA_ENABLED", "false").lower() == "true"
    config.grafana.url = os.getenv("GRAFANA_URL")
    config.grafana.api_key = os.getenv("GRAFANA_API_KEY")
    config.grafana.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    config.grafana.auto_deploy_dashboards = os.getenv("GRAFANA_AUTO_DEPLOY", "true").lower() == "true"
    
    # Prometheus configuration
    config.prometheus.enabled = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    config.prometheus.url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    config.prometheus.scrape_interval = int(os.getenv("PROMETHEUS_SCRAPE_INTERVAL", "15"))
    
    # Logging
    config.log_level = os.getenv("MONITORING_LOG_LEVEL", "INFO")
    
    return config


def get_production_config() -> MonitoringConfig:
    """Get production-ready monitoring configuration."""
    config = MonitoringConfig(mode=MonitoringMode.PRODUCTION)
    
    # Production metrics settings
    config.metrics.collection_interval = 5  # More frequent collection
    config.metrics.retention_points = 50000  # More retention
    config.metrics.enable_system_metrics = True
    config.metrics.enable_process_metrics = True
    
    # Production alert settings
    config.alerts.evaluation_interval = 15  # More frequent evaluation
    config.alerts.latency_warning_threshold = 2.0  # Stricter thresholds
    config.alerts.latency_critical_threshold = 5.0
    config.alerts.error_rate_warning_threshold = 0.01  # 1%
    config.alerts.error_rate_critical_threshold = 0.05  # 5%
    
    # Production notification settings
    config.notifications.processing_interval = 5  # Faster processing
    config.notifications.aggregation_window = 180  # 3 minutes
    config.notifications.deduplication_window = 1800  # 30 minutes
    
    # Enable all notification channels in production
    config.notifications.email_enabled = True
    config.notifications.slack_enabled = True
    config.notifications.webhook_enabled = True
    
    # Enable Grafana in production
    config.grafana.enabled = True
    config.grafana.auto_deploy_dashboards = True
    config.grafana.dashboard_update_interval = 1800  # 30 minutes
    
    # Production cleanup settings
    config.cleanup_interval = 43200  # 12 hours
    config.health_check_interval = 30  # 30 seconds
    
    return config


def get_development_config() -> MonitoringConfig:
    """Get development-friendly monitoring configuration."""
    config = MonitoringConfig(mode=MonitoringMode.DEVELOPMENT)
    
    # Development metrics settings
    config.metrics.collection_interval = 30  # Less frequent
    config.metrics.retention_points = 1000  # Less retention
    config.metrics.enable_system_metrics = False  # Disable to reduce noise
    config.metrics.enable_process_metrics = True
    
    # Development alert settings
    config.alerts.evaluation_interval = 60  # Less frequent
    config.alerts.latency_warning_threshold = 10.0  # More relaxed
    config.alerts.latency_critical_threshold = 30.0
    config.alerts.error_rate_warning_threshold = 0.10  # 10%
    config.alerts.error_rate_critical_threshold = 0.50  # 50%
    
    # Development notification settings
    config.notifications.processing_interval = 30
    config.notifications.aggregation_window = 600  # 10 minutes
    config.notifications.deduplication_window = 7200  # 2 hours
    
    # Disable notifications in development by default
    config.notifications.email_enabled = False
    config.notifications.slack_enabled = False
    config.notifications.webhook_enabled = False
    
    # Disable Grafana in development by default
    config.grafana.enabled = False
    
    # Development cleanup settings
    config.cleanup_interval = 86400  # 24 hours
    config.health_check_interval = 300  # 5 minutes
    
    return config


def validate_config(config: MonitoringConfig) -> List[str]:
    """Validate monitoring configuration and return list of issues."""
    issues = []
    
    # Validate notification configuration
    if config.notifications.email_enabled:
        if not config.notifications.smtp_host:
            issues.append("SMTP host is required when email notifications are enabled")
        if not config.notifications.smtp_username:
            issues.append("SMTP username is required when email notifications are enabled")
        if not config.notifications.smtp_password:
            issues.append("SMTP password is required when email notifications are enabled")
        if not config.notifications.smtp_from_email:
            issues.append("SMTP from email is required when email notifications are enabled")
    
    if config.notifications.slack_enabled:
        if not config.notifications.slack_webhook_url:
            issues.append("Slack webhook URL is required when Slack notifications are enabled")
    
    if config.notifications.webhook_enabled:
        if not config.notifications.webhook_url:
            issues.append("Webhook URL is required when webhook notifications are enabled")
    
    # Validate Grafana configuration
    if config.grafana.enabled:
        if not config.grafana.url:
            issues.append("Grafana URL is required when Grafana integration is enabled")
        if not config.grafana.api_key:
            issues.append("Grafana API key is required when Grafana integration is enabled")
    
    # Validate thresholds
    if config.alerts.latency_warning_threshold >= config.alerts.latency_critical_threshold:
        issues.append("Latency warning threshold must be less than critical threshold")
    
    if config.alerts.error_rate_warning_threshold >= config.alerts.error_rate_critical_threshold:
        issues.append("Error rate warning threshold must be less than critical threshold")
    
    if config.alerts.queue_depth_warning_threshold >= config.alerts.queue_depth_critical_threshold:
        issues.append("Queue depth warning threshold must be less than critical threshold")
    
    # Validate intervals
    if config.metrics.collection_interval <= 0:
        issues.append("Metrics collection interval must be positive")
    
    if config.alerts.evaluation_interval <= 0:
        issues.append("Alert evaluation interval must be positive")
    
    if config.notifications.processing_interval <= 0:
        issues.append("Notification processing interval must be positive")
    
    return issues


# Global configuration instance
_config: Optional[MonitoringConfig] = None


def get_config() -> MonitoringConfig:
    """Get the global monitoring configuration."""
    global _config
    if _config is None:
        _config = load_config_from_env()
    return _config


def set_config(config: MonitoringConfig):
    """Set the global monitoring configuration."""
    global _config
    
    # Validate configuration
    issues = validate_config(config)
    if issues:
        raise ValueError(f"Invalid monitoring configuration: {', '.join(issues)}")
    
    _config = config


def reset_config():
    """Reset the global configuration to None."""
    global _config
    _config = None


# Configuration presets
PRESETS = {
    "development": get_development_config,
    "staging": get_production_config,  # Use production config for staging
    "production": get_production_config,
}


def load_preset(preset_name: str) -> MonitoringConfig:
    """Load a configuration preset."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    
    return PRESETS[preset_name]()