"""
Monitoring module for SuperInsight Platform.

Provides comprehensive monitoring capabilities including:
- Quality monitoring and dashboards
- Alert management and notifications
- Advanced anomaly detection with ML
- SLA compliance monitoring
- Capacity planning and prediction
- Report generation and scheduling
- Prometheus metrics collection
- Configurable alert thresholds
- Health check endpoints
- Service unhealthy alerts
"""

def get_quality_monitor():
    """Get QualityMonitor instance with lazy import."""
    from .quality_monitor import QualityMonitor
    return QualityMonitor()


def get_alert_manager():
    """Get AlertManager instance with lazy import."""
    from .alert_manager import AlertManager
    return AlertManager()


def get_anomaly_detector():
    """Get AdvancedAnomalyDetector instance with lazy import."""
    from .advanced_anomaly_detection import advanced_anomaly_detector
    return advanced_anomaly_detector


def get_report_service():
    """Get MonitoringReportService instance with lazy import."""
    from .report_service import monitoring_report_service
    return monitoring_report_service


def get_metrics_registry():
    """Get MetricsRegistry instance with lazy import."""
    from .prometheus_metrics import metrics_registry
    return metrics_registry


def get_alert_config_manager():
    """Get AlertConfigManager instance with lazy import."""
    from .alert_config import alert_config_manager
    return alert_config_manager


def get_health_check_manager():
    """Get HealthCheckManager instance with lazy import."""
    from .health_check import health_check_manager
    return health_check_manager


def get_service_alert_manager():
    """Get ServiceAlertManager instance with lazy import."""
    from .service_alert import service_alert_manager
    return service_alert_manager


__all__ = [
    "get_quality_monitor",
    "get_alert_manager",
    "get_anomaly_detector",
    "get_report_service",
    "get_metrics_registry",
    "get_alert_config_manager",
    "get_health_check_manager",
    "get_service_alert_manager",
]
