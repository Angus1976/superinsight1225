"""
Grafana Dashboard Templates for Quality Billing System.

Provides pre-configured dashboard templates that can be
customized and deployed to Grafana.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class DashboardTemplateGenerator:
    """
    Generates Grafana dashboard templates for the quality billing system.
    
    Provides methods to create various types of dashboards with
    customizable panels, queries, and visualizations.
    """

    def __init__(self):
        self.default_config = {
            "refresh": "30s",
            "time_from": "now-1h",
            "time_to": "now",
            "timezone": "browser",
            "theme": "light"
        }

    def create_executive_dashboard(self, config: Optional[Dict] = None) -> Dict:
        """Create executive summary dashboard for management overview."""
        config = {**self.default_config, **(config or {})}
        
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Executive Summary",
                "uid": "quality-billing-executive",
                "tags": ["quality-billing", "executive", "summary"],
                "timezone": config["timezone"],
                "refresh": config["refresh"],
                "time": {
                    "from": "now-7d",
                    "to": "now"
                },
                "panels": [
                    # KPI Row
                    self._create_row_panel("Key Performance Indicators", 0),
                    
                    # Revenue KPI
                    {
                        "id": 2,
                        "title": "Weekly Revenue",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 1},
                        "targets": [{
                            "expr": "sum(increase(quality_billing_total_amount_cents[7d])) / 100",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "currencyUSD",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 10000},
                                        {"color": "green", "value": 25000}
                                    ]
                                }
                            }
                        },
                        "options": {
                            "colorMode": "background",
                            "graphMode": "area",
                            "justifyMode": "center"
                        }
                    },
                    
                    # Quality KPI
                    {
                        "id": 3,
                        "title": "Average Quality Score",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 1},
                        "targets": [{
                            "expr": "avg(quality_billing_quality_score)",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "min": 0,
                                "max": 1,
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 0.7},
                                        {"color": "green", "value": 0.85}
                                    ]
                                }
                            }
                        },
                        "options": {
                            "colorMode": "background",
                            "graphMode": "area"
                        }
                    },
                    
                    # Productivity KPI
                    {
                        "id": 4,
                        "title": "Team Productivity",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 1},
                        "targets": [{
                            "expr": "sum(quality_billing_tasks_completed_today)",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "short",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 50},
                                        {"color": "green", "value": 100}
                                    ]
                                }
                            }
                        }
                    },
                    
                    # Efficiency KPI
                    {
                        "id": 5,
                        "title": "Work Efficiency",
                        "type": "gauge",
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 1},
                        "targets": [{
                            "expr": "quality_billing_overall_work_efficiency",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "min": 0,
                                "max": 1,
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 0.7},
                                        {"color": "green", "value": 0.85}
                                    ]
                                }
                            }
                        }
                    },
                    
                    # Trends Row
                    self._create_row_panel("Performance Trends", 9),
                    
                    # Revenue Trend
                    {
                        "id": 7,
                        "title": "Revenue Trend (7 Days)",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 10},
                        "targets": [{
                            "expr": "sum(increase(quality_billing_total_amount_cents[1d])) by (day) / 100",
                            "refId": "A",
                            "legendFormat": "Daily Revenue"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "currencyUSD",
                                "custom": {
                                    "drawStyle": "line",
                                    "lineInterpolation": "smooth",
                                    "fillOpacity": 20
                                }
                            }
                        }
                    },
                    
                    # Quality Trend
                    {
                        "id": 8,
                        "title": "Quality Score Trend",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 10},
                        "targets": [{
                            "expr": "avg(quality_billing_quality_score)",
                            "refId": "A",
                            "legendFormat": "Average Quality"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "min": 0,
                                "max": 1,
                                "custom": {
                                    "drawStyle": "line",
                                    "lineInterpolation": "smooth",
                                    "fillOpacity": 20
                                }
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def create_operational_dashboard(self, config: Optional[Dict] = None) -> Dict:
        """Create operational dashboard for day-to-day monitoring."""
        config = {**self.default_config, **(config or {})}
        
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Operations",
                "uid": "quality-billing-operations",
                "tags": ["quality-billing", "operations", "monitoring"],
                "timezone": config["timezone"],
                "refresh": "15s",
                "time": {
                    "from": "now-4h",
                    "to": "now"
                },
                "panels": [
                    # System Health Row
                    self._create_row_panel("System Health", 0),
                    
                    # Active Users
                    {
                        "id": 2,
                        "title": "Active Users",
                        "type": "timeseries",
                        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 1},
                        "targets": [{
                            "expr": "quality_billing_current_active_users",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "short"
                            }
                        }
                    },
                    
                    # Active Sessions
                    {
                        "id": 3,
                        "title": "Active Sessions",
                        "type": "timeseries",
                        "gridPos": {"h": 8, "w": 8, "x": 8, "y": 1},
                        "targets": [{
                            "expr": "quality_billing_active_sessions",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "short"
                            }
                        }
                    },
                    
                    # API Health
                    {
                        "id": 4,
                        "title": "API Request Rate",
                        "type": "timeseries",
                        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 1},
                        "targets": [{
                            "expr": "rate(quality_billing_api_requests_total[5m])",
                            "refId": "A",
                            "legendFormat": "{{endpoint}}"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "reqps"
                            }
                        }
                    },
                    
                    # Performance Row
                    self._create_row_panel("Performance Metrics", 9),
                    
                    # Response Time Distribution
                    {
                        "id": 6,
                        "title": "API Response Time Distribution",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 10},
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.50, rate(quality_billing_api_response_time_seconds_bucket[5m]))",
                                "refId": "A",
                                "legendFormat": "50th percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.95, rate(quality_billing_api_response_time_seconds_bucket[5m]))",
                                "refId": "B",
                                "legendFormat": "95th percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.99, rate(quality_billing_api_response_time_seconds_bucket[5m]))",
                                "refId": "C",
                                "legendFormat": "99th percentile"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "s"
                            }
                        }
                    },
                    
                    # Error Rate
                    {
                        "id": 7,
                        "title": "API Error Rate",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 10},
                        "targets": [{
                            "expr": "rate(quality_billing_api_requests_total{status_code=~\"5..\"}[5m]) / rate(quality_billing_api_requests_total[5m])",
                            "refId": "A",
                            "legendFormat": "Error Rate"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "custom": {
                                    "thresholds": {
                                        "steps": [
                                            {"color": "green", "value": 0},
                                            {"color": "yellow", "value": 0.01},
                                            {"color": "red", "value": 0.05}
                                        ]
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def create_quality_analytics_dashboard(self, config: Optional[Dict] = None) -> Dict:
        """Create detailed quality analytics dashboard."""
        config = {**self.default_config, **(config or {})}
        
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Quality Analytics",
                "uid": "quality-billing-quality-analytics",
                "tags": ["quality-billing", "quality", "analytics"],
                "timezone": config["timezone"],
                "refresh": config["refresh"],
                "time": {
                    "from": "now-24h",
                    "to": "now"
                },
                "panels": [
                    # Quality Overview Row
                    self._create_row_panel("Quality Overview", 0),
                    
                    # Quality Score Heatmap
                    {
                        "id": 2,
                        "title": "Quality Score by User and Time",
                        "type": "heatmap",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 1},
                        "targets": [{
                            "expr": "quality_billing_quality_score",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "min": 0,
                                "max": 1
                            }
                        }
                    },
                    
                    # Quality Distribution Row
                    self._create_row_panel("Quality Distribution", 10),
                    
                    # Quality Score Histogram
                    {
                        "id": 4,
                        "title": "Quality Score Distribution",
                        "type": "histogram",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 11},
                        "targets": [{
                            "expr": "quality_billing_quality_score",
                            "refId": "A"
                        }],
                        "options": {
                            "bucketSize": 0.05,
                            "bucketOffset": 0
                        }
                    },
                    
                    # Quality by Task Type
                    {
                        "id": 5,
                        "title": "Quality Score by Task Type",
                        "type": "barchart",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 11},
                        "targets": [{
                            "expr": "avg(quality_billing_quality_score) by (task_type)",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit"
                            }
                        }
                    },
                    
                    # Improvement Tracking Row
                    self._create_row_panel("Quality Improvement Tracking", 20),
                    
                    # Quality Improvement Rate
                    {
                        "id": 7,
                        "title": "Quality Improvement Rate Over Time",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 21},
                        "targets": [{
                            "expr": "quality_billing_quality_improvement_rate",
                            "refId": "A",
                            "legendFormat": "Improvement Rate"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "custom": {
                                    "drawStyle": "line",
                                    "lineInterpolation": "smooth"
                                }
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def create_financial_dashboard(self, config: Optional[Dict] = None) -> Dict:
        """Create financial analytics dashboard."""
        config = {**self.default_config, **(config or {})}
        
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Financial Analytics",
                "uid": "quality-billing-financial",
                "tags": ["quality-billing", "financial", "billing"],
                "timezone": config["timezone"],
                "refresh": config["refresh"],
                "time": {
                    "from": "now-30d",
                    "to": "now"
                },
                "panels": [
                    # Revenue Overview Row
                    self._create_row_panel("Revenue Overview", 0),
                    
                    # Monthly Revenue
                    {
                        "id": 2,
                        "title": "Monthly Revenue Trend",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 1},
                        "targets": [{
                            "expr": "sum(increase(quality_billing_total_amount_cents[30d])) / 100",
                            "refId": "A",
                            "legendFormat": "Monthly Revenue"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "currencyUSD"
                            }
                        }
                    },
                    
                    # Revenue by Quality Level
                    {
                        "id": 3,
                        "title": "Revenue by Quality Level",
                        "type": "piechart",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 1},
                        "targets": [{
                            "expr": "sum(quality_billing_total_amount_cents) by (quality_level) / 100",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "currencyUSD"
                            }
                        }
                    },
                    
                    # Billing Metrics Row
                    self._create_row_panel("Billing Metrics", 10),
                    
                    # Invoice Generation Rate
                    {
                        "id": 5,
                        "title": "Invoice Generation Rate",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 11},
                        "targets": [{
                            "expr": "rate(quality_billing_invoices_generated_total[1h])",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "short"
                            }
                        }
                    },
                    
                    # Average Invoice Amount
                    {
                        "id": 6,
                        "title": "Average Invoice Amount Trend",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 11},
                        "targets": [{
                            "expr": "quality_billing_today_average_invoice_cents / 100",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "currencyUSD"
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def _create_row_panel(self, title: str, y_pos: int) -> Dict:
        """Create a row panel for organizing dashboard sections."""
        return {
            "id": None,
            "title": title,
            "type": "row",
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y_pos},
            "collapsed": False,
            "panels": []
        }

    def create_custom_dashboard(
        self,
        title: str,
        uid: str,
        panels: List[Dict],
        config: Optional[Dict] = None
    ) -> Dict:
        """Create a custom dashboard with specified panels."""
        config = {**self.default_config, **(config or {})}
        
        return {
            "dashboard": {
                "id": None,
                "title": title,
                "uid": uid,
                "tags": ["quality-billing", "custom"],
                "timezone": config["timezone"],
                "refresh": config["refresh"],
                "time": {
                    "from": config["time_from"],
                    "to": config["time_to"]
                },
                "panels": panels
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def get_all_dashboard_templates(self) -> Dict[str, Dict]:
        """Get all available dashboard templates."""
        return {
            "executive": self.create_executive_dashboard(),
            "operational": self.create_operational_dashboard(),
            "quality_analytics": self.create_quality_analytics_dashboard(),
            "financial": self.create_financial_dashboard()
        }


# Global template generator instance
dashboard_generator = DashboardTemplateGenerator()


def get_dashboard_generator() -> DashboardTemplateGenerator:
    """Get the global dashboard template generator."""
    return dashboard_generator