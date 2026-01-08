"""
Grafana Dashboard Templates for System Health Monitoring.

Provides comprehensive dashboard configurations for monitoring
system health, performance, and business metrics.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GrafanaDashboardGenerator:
    """
    Generates Grafana dashboard configurations for system monitoring.
    
    Creates dashboards for:
    - System overview and health
    - Performance monitoring
    - Business metrics and analytics
    - AI model performance
    """
    
    def __init__(self, prometheus_datasource: str = "Prometheus"):
        self.prometheus_datasource = prometheus_datasource
        self.default_refresh = "30s"
        self.default_time_range = {"from": "now-1h", "to": "now"}
    
    def create_system_overview_dashboard(self) -> Dict[str, Any]:
        """Create system overview dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "SuperInsight - System Overview",
                "uid": "superinsight-system-overview",
                "tags": ["superinsight", "system", "overview"],
                "timezone": "browser",
                "refresh": self.default_refresh,
                "time": self.default_time_range,
                "panels": [
                    # System Health Status Row
                    self._create_row_panel("System Health Status", 0),
                    
                    # Health indicators
                    self._create_stat_panel(
                        id=1,
                        title="System Status",
                        query='health_check_status{check_name="system"}',
                        pos={"h": 6, "w": 4, "x": 0, "y": 1},
                        unit="none",
                        thresholds=[
                            {"color": "red", "value": 0},
                            {"color": "green", "value": 1}
                        ],
                        value_mappings=[
                            {"value": "0", "text": "Unhealthy"},
                            {"value": "1", "text": "Healthy"}
                        ]
                    ),
                    
                    self._create_stat_panel(
                        id=2,
                        title="CPU Usage",
                        query='system_cpu_usage_percent{core="total"}',
                        pos={"h": 6, "w": 4, "x": 4, "y": 1},
                        unit="percent",
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 70},
                            {"color": "red", "value": 90}
                        ]
                    ),
                    
                    self._create_stat_panel(
                        id=3,
                        title="Memory Usage",
                        query='system_memory_usage_percent',
                        pos={"h": 6, "w": 4, "x": 8, "y": 1},
                        unit="percent",
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 80},
                            {"color": "red", "value": 95}
                        ]
                    ),
                    
                    self._create_stat_panel(
                        id=4,
                        title="Disk Usage",
                        query='system_disk_usage_percent{device="root"}',
                        pos={"h": 6, "w": 4, "x": 12, "y": 1},
                        unit="percent",
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 85},
                            {"color": "red", "value": 95}
                        ]
                    ),
                    
                    self._create_stat_panel(
                        id=5,
                        title="Active Users",
                        query='business_users_active_count',
                        pos={"h": 6, "w": 4, "x": 16, "y": 1},
                        unit="none",
                        thresholds=[
                            {"color": "red", "value": 0},
                            {"color": "yellow", "value": 5},
                            {"color": "green", "value": 10}
                        ]
                    ),
                    
                    self._create_stat_panel(
                        id=6,
                        title="Active Requests",
                        query='http_requests_active',
                        pos={"h": 6, "w": 4, "x": 20, "y": 1},
                        unit="none",
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 50},
                            {"color": "red", "value": 100}
                        ]
                    ),
                    
                    # Performance Trends Row
                    self._create_row_panel("Performance Trends", 7),
                    
                    # CPU trend
                    self._create_timeseries_panel(
                        id=7,
                        title="CPU Usage Trend",
                        queries=[
                            {
                                "expr": 'system_cpu_usage_percent{core="total"}',
                                "legendFormat": "Total CPU"
                            },
                            {
                                "expr": 'avg(system_cpu_usage_percent{core!="total"})',
                                "legendFormat": "Average per Core"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 8},
                        unit="percent",
                        min_value=0,
                        max_value=100
                    ),
                    
                    # Memory trend
                    self._create_timeseries_panel(
                        id=8,
                        title="Memory Usage Trend",
                        queries=[
                            {
                                "expr": 'system_memory_usage_percent',
                                "legendFormat": "Memory Usage"
                            },
                            {
                                "expr": 'system_swap_usage_percent',
                                "legendFormat": "Swap Usage"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 8},
                        unit="percent",
                        min_value=0,
                        max_value=100
                    ),
                    
                    # Network I/O
                    self._create_timeseries_panel(
                        id=9,
                        title="Network I/O",
                        queries=[
                            {
                                "expr": 'rate(system_network_bytes_sent_total[5m])',
                                "legendFormat": "Bytes Sent/sec"
                            },
                            {
                                "expr": 'rate(system_network_bytes_recv_total[5m])',
                                "legendFormat": "Bytes Received/sec"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 16},
                        unit="Bps"
                    ),
                    
                    # Disk I/O
                    self._create_timeseries_panel(
                        id=10,
                        title="Disk I/O",
                        queries=[
                            {
                                "expr": 'rate(system_disk_read_bytes_total[5m])',
                                "legendFormat": "Read Bytes/sec"
                            },
                            {
                                "expr": 'rate(system_disk_write_bytes_total[5m])',
                                "legendFormat": "Write Bytes/sec"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 16},
                        unit="Bps"
                    ),
                ]
            },
            "folderId": None,
            "overwrite": True
        }
    
    def create_performance_dashboard(self) -> Dict[str, Any]:
        """Create performance monitoring dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "SuperInsight - Performance Monitoring",
                "uid": "superinsight-performance",
                "tags": ["superinsight", "performance"],
                "timezone": "browser",
                "refresh": self.default_refresh,
                "time": self.default_time_range,
                "panels": [
                    # HTTP Performance Row
                    self._create_row_panel("HTTP Performance", 0),
                    
                    # Request rate
                    self._create_stat_panel(
                        id=1,
                        title="Request Rate",
                        query='rate(http_requests_total[5m])',
                        pos={"h": 6, "w": 6, "x": 0, "y": 1},
                        unit="reqps"
                    ),
                    
                    # Average response time
                    self._create_stat_panel(
                        id=2,
                        title="Avg Response Time",
                        query='rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])',
                        pos={"h": 6, "w": 6, "x": 6, "y": 1},
                        unit="s",
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 1},
                            {"color": "red", "value": 3}
                        ]
                    ),
                    
                    # Error rate
                    self._create_stat_panel(
                        id=3,
                        title="Error Rate",
                        query='rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100',
                        pos={"h": 6, "w": 6, "x": 12, "y": 1},
                        unit="percent",
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 1},
                            {"color": "red", "value": 5}
                        ]
                    ),
                    
                    # Active requests
                    self._create_stat_panel(
                        id=4,
                        title="Active Requests",
                        query='http_requests_active',
                        pos={"h": 6, "w": 6, "x": 18, "y": 1},
                        unit="none"
                    ),
                    
                    # Request rate by endpoint
                    self._create_timeseries_panel(
                        id=5,
                        title="Request Rate by Endpoint",
                        queries=[
                            {
                                "expr": 'rate(http_requests_total[5m])',
                                "legendFormat": "{{method}} {{endpoint}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 7},
                        unit="reqps"
                    ),
                    
                    # Response time percentiles
                    self._create_timeseries_panel(
                        id=6,
                        title="Response Time Percentiles",
                        queries=[
                            {
                                "expr": 'histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))',
                                "legendFormat": "50th percentile"
                            },
                            {
                                "expr": 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
                                "legendFormat": "95th percentile"
                            },
                            {
                                "expr": 'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))',
                                "legendFormat": "99th percentile"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 7},
                        unit="s"
                    ),
                    
                    # Database Performance Row
                    self._create_row_panel("Database Performance", 15),
                    
                    # Database query rate
                    self._create_timeseries_panel(
                        id=7,
                        title="Database Query Rate",
                        queries=[
                            {
                                "expr": 'rate(database_queries_total[5m])',
                                "legendFormat": "{{type}} ({{success}})"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 16},
                        unit="qps"
                    ),
                    
                    # Database query duration
                    self._create_timeseries_panel(
                        id=8,
                        title="Database Query Duration",
                        queries=[
                            {
                                "expr": 'histogram_quantile(0.95, rate(database_query_duration_seconds_bucket[5m]))',
                                "legendFormat": "95th percentile"
                            },
                            {
                                "expr": 'rate(database_query_duration_seconds_sum[5m]) / rate(database_query_duration_seconds_count[5m])',
                                "legendFormat": "Average"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 16},
                        unit="s"
                    ),
                ]
            },
            "folderId": None,
            "overwrite": True
        }
    
    def create_business_metrics_dashboard(self) -> Dict[str, Any]:
        """Create business metrics dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "SuperInsight - Business Metrics",
                "uid": "superinsight-business",
                "tags": ["superinsight", "business"],
                "timezone": "browser",
                "refresh": self.default_refresh,
                "time": {"from": "now-24h", "to": "now"},
                "panels": [
                    # User Activity Row
                    self._create_row_panel("User Activity", 0),
                    
                    # Active users
                    self._create_stat_panel(
                        id=1,
                        title="Active Users",
                        query='business_users_active_count',
                        pos={"h": 6, "w": 6, "x": 0, "y": 1},
                        unit="none",
                        thresholds=[
                            {"color": "red", "value": 0},
                            {"color": "yellow", "value": 5},
                            {"color": "green", "value": 10}
                        ]
                    ),
                    
                    # New users today
                    self._create_stat_panel(
                        id=2,
                        title="New Users Today",
                        query='business_users_new_count',
                        pos={"h": 6, "w": 6, "x": 6, "y": 1},
                        unit="none"
                    ),
                    
                    # Average session duration
                    self._create_stat_panel(
                        id=3,
                        title="Avg Session Duration",
                        query='business_users_session_duration_avg_seconds / 60',
                        pos={"h": 6, "w": 6, "x": 12, "y": 1},
                        unit="min"
                    ),
                    
                    # Actions per session
                    self._create_stat_panel(
                        id=4,
                        title="Actions per Session",
                        query='business_users_actions_per_session',
                        pos={"h": 6, "w": 6, "x": 18, "y": 1},
                        unit="none"
                    ),
                    
                    # Annotation Efficiency Row
                    self._create_row_panel("Annotation Efficiency", 7),
                    
                    # Annotations per hour
                    self._create_timeseries_panel(
                        id=5,
                        title="Annotations per Hour",
                        queries=[
                            {
                                "expr": 'business_annotation_efficiency_per_hour',
                                "legendFormat": "{{project}} - {{user}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 8},
                        unit="none"
                    ),
                    
                    # Quality score trend
                    self._create_timeseries_panel(
                        id=6,
                        title="Quality Score Trend",
                        queries=[
                            {
                                "expr": 'business_annotation_quality_score',
                                "legendFormat": "{{project}} - {{user}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 8},
                        unit="percentunit",
                        min_value=0,
                        max_value=1
                    ),
                    
                    # Project Progress Row
                    self._create_row_panel("Project Progress", 16),
                    
                    # Project completion
                    self._create_timeseries_panel(
                        id=7,
                        title="Project Completion Percentage",
                        queries=[
                            {
                                "expr": 'business_project_completion_percentage',
                                "legendFormat": "{{project}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 17},
                        unit="percent",
                        min_value=0,
                        max_value=100
                    ),
                    
                    # Task completion
                    self._create_timeseries_panel(
                        id=8,
                        title="Tasks Completed vs Total",
                        queries=[
                            {
                                "expr": 'business_project_tasks_completed',
                                "legendFormat": "Completed - {{project}}"
                            },
                            {
                                "expr": 'business_project_tasks_total',
                                "legendFormat": "Total - {{project}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 17},
                        unit="none"
                    ),
                ]
            },
            "folderId": None,
            "overwrite": True
        }
    
    def create_ai_performance_dashboard(self) -> Dict[str, Any]:
        """Create AI model performance dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "SuperInsight - AI Performance",
                "uid": "superinsight-ai-performance",
                "tags": ["superinsight", "ai", "performance"],
                "timezone": "browser",
                "refresh": self.default_refresh,
                "time": self.default_time_range,
                "panels": [
                    # AI Model Overview Row
                    self._create_row_panel("AI Model Overview", 0),
                    
                    # Inference rate
                    self._create_stat_panel(
                        id=1,
                        title="Inference Rate",
                        query='rate(business_ai_inference_count_total[5m])',
                        pos={"h": 6, "w": 6, "x": 0, "y": 1},
                        unit="reqps"
                    ),
                    
                    # Average inference time
                    self._create_stat_panel(
                        id=2,
                        title="Avg Inference Time",
                        query='rate(business_ai_inference_duration_seconds_sum[5m]) / rate(business_ai_inference_duration_seconds_count[5m])',
                        pos={"h": 6, "w": 6, "x": 6, "y": 1},
                        unit="s",
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 5},
                            {"color": "red", "value": 15}
                        ]
                    ),
                    
                    # Success rate
                    self._create_stat_panel(
                        id=3,
                        title="Success Rate",
                        query='rate(business_ai_inference_count_total{success="true"}[5m]) / rate(business_ai_inference_count_total[5m]) * 100',
                        pos={"h": 6, "w": 6, "x": 12, "y": 1},
                        unit="percent",
                        thresholds=[
                            {"color": "red", "value": 0},
                            {"color": "yellow", "value": 90},
                            {"color": "green", "value": 95}
                        ]
                    ),
                    
                    # Average confidence
                    self._create_stat_panel(
                        id=4,
                        title="Avg Confidence",
                        query='business_ai_confidence_score',
                        pos={"h": 6, "w": 6, "x": 18, "y": 1},
                        unit="percentunit",
                        min_value=0,
                        max_value=1
                    ),
                    
                    # Model Performance Row
                    self._create_row_panel("Model Performance", 7),
                    
                    # Inference rate by model
                    self._create_timeseries_panel(
                        id=5,
                        title="Inference Rate by Model",
                        queries=[
                            {
                                "expr": 'rate(business_ai_inference_count_total[5m])',
                                "legendFormat": "{{model}} ({{success}})"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 8},
                        unit="reqps"
                    ),
                    
                    # Inference duration by model
                    self._create_timeseries_panel(
                        id=6,
                        title="Inference Duration by Model",
                        queries=[
                            {
                                "expr": 'histogram_quantile(0.95, rate(business_ai_inference_duration_seconds_bucket[5m]))',
                                "legendFormat": "95th percentile - {{model}}"
                            },
                            {
                                "expr": 'rate(business_ai_inference_duration_seconds_sum[5m]) / rate(business_ai_inference_duration_seconds_count[5m])',
                                "legendFormat": "Average - {{model}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 8},
                        unit="s"
                    ),
                    
                    # Model Quality Row
                    self._create_row_panel("Model Quality", 16),
                    
                    # Confidence scores
                    self._create_timeseries_panel(
                        id=7,
                        title="Confidence Scores by Model",
                        queries=[
                            {
                                "expr": 'business_ai_confidence_score',
                                "legendFormat": "{{model}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 0, "y": 17},
                        unit="percentunit",
                        min_value=0,
                        max_value=1
                    ),
                    
                    # Accuracy scores
                    self._create_timeseries_panel(
                        id=8,
                        title="Accuracy Scores by Model",
                        queries=[
                            {
                                "expr": 'business_ai_accuracy_score',
                                "legendFormat": "{{model}}"
                            }
                        ],
                        pos={"h": 8, "w": 12, "x": 12, "y": 17},
                        unit="percentunit",
                        min_value=0,
                        max_value=1
                    ),
                ]
            },
            "folderId": None,
            "overwrite": True
        }
    
    def _create_row_panel(self, title: str, y_pos: int) -> Dict[str, Any]:
        """Create a row panel for organizing dashboard sections."""
        return {
            "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y_pos},
            "id": None,
            "panels": [],
            "title": title,
            "type": "row"
        }
    
    def _create_stat_panel(
        self,
        id: int,
        title: str,
        query: str,
        pos: Dict[str, int],
        unit: str = "none",
        thresholds: Optional[List[Dict[str, Any]]] = None,
        value_mappings: Optional[List[Dict[str, str]]] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a stat panel."""
        panel = {
            "id": id,
            "title": title,
            "type": "stat",
            "gridPos": pos,
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": self.prometheus_datasource
            }],
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "color": {"mode": "thresholds"}
                }
            },
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "orientation": "auto",
                "textMode": "auto",
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto"
            }
        }
        
        if thresholds:
            panel["fieldConfig"]["defaults"]["thresholds"] = {"steps": thresholds}
        
        if value_mappings:
            panel["fieldConfig"]["defaults"]["mappings"] = [
                {"type": "value", "options": {vm["value"]: {"text": vm["text"]}}}
                for vm in value_mappings
            ]
        
        if min_value is not None:
            panel["fieldConfig"]["defaults"]["min"] = min_value
        
        if max_value is not None:
            panel["fieldConfig"]["defaults"]["max"] = max_value
        
        return panel
    
    def _create_timeseries_panel(
        self,
        id: int,
        title: str,
        queries: List[Dict[str, str]],
        pos: Dict[str, int],
        unit: str = "none",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a time series panel."""
        targets = []
        for i, query in enumerate(queries):
            targets.append({
                "expr": query["expr"],
                "refId": chr(65 + i),  # A, B, C, etc.
                "legendFormat": query.get("legendFormat", ""),
                "datasource": self.prometheus_datasource
            })
        
        panel = {
            "id": id,
            "title": title,
            "type": "timeseries",
            "gridPos": pos,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "custom": {
                        "drawStyle": "line",
                        "lineInterpolation": "linear",
                        "lineWidth": 1,
                        "fillOpacity": 10,
                        "gradientMode": "none",
                        "spanNulls": False,
                        "insertNulls": False,
                        "showPoints": "never",
                        "pointSize": 5,
                        "stacking": {"mode": "none", "group": "A"},
                        "axisPlacement": "auto",
                        "axisLabel": "",
                        "scaleDistribution": {"type": "linear"},
                        "hideFrom": {"legend": False, "tooltip": False, "vis": False},
                        "thresholdsStyle": {"mode": "off"}
                    }
                }
            },
            "options": {
                "tooltip": {"mode": "single", "sort": "none"},
                "legend": {"displayMode": "list", "placement": "bottom"},
                "displayMode": "list"
            }
        }
        
        if min_value is not None:
            panel["fieldConfig"]["defaults"]["min"] = min_value
        
        if max_value is not None:
            panel["fieldConfig"]["defaults"]["max"] = max_value
        
        return panel
    
    def get_all_dashboards(self) -> Dict[str, Dict[str, Any]]:
        """Get all dashboard configurations."""
        return {
            "system_overview": self.create_system_overview_dashboard(),
            "performance": self.create_performance_dashboard(),
            "business_metrics": self.create_business_metrics_dashboard(),
            "ai_performance": self.create_ai_performance_dashboard()
        }


# Global dashboard generator instance
dashboard_generator = GrafanaDashboardGenerator()


# Convenience functions
def get_system_overview_dashboard() -> Dict[str, Any]:
    """Get system overview dashboard configuration."""
    return dashboard_generator.create_system_overview_dashboard()


def get_performance_dashboard() -> Dict[str, Any]:
    """Get performance dashboard configuration."""
    return dashboard_generator.create_performance_dashboard()


def get_business_metrics_dashboard() -> Dict[str, Any]:
    """Get business metrics dashboard configuration."""
    return dashboard_generator.create_business_metrics_dashboard()


def get_ai_performance_dashboard() -> Dict[str, Any]:
    """Get AI performance dashboard configuration."""
    return dashboard_generator.create_ai_performance_dashboard()


def get_all_dashboards() -> Dict[str, Dict[str, Any]]:
    """Get all dashboard configurations."""
    return dashboard_generator.get_all_dashboards()