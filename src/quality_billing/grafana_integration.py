"""
Grafana Integration Service for Quality Billing System.

Provides integration with Grafana for creating and managing
monitoring dashboards and visualizations.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class GrafanaIntegrationService:
    """
    Manages Grafana integration for the quality billing system.
    
    Provides:
    - Dashboard creation and management
    - Data source configuration
    - Alert rule management
    - Dashboard provisioning
    """

    def __init__(
        self,
        grafana_url: str,
        api_key: str,
        prometheus_url: str = "http://localhost:9090"
    ):
        self.grafana_url = grafana_url.rstrip('/')
        self.api_key = api_key
        self.prometheus_url = prometheus_url
        
        # HTTP session for API calls
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Dashboard configurations
        self.dashboards: Dict[str, Dict] = {}
        self.data_sources: Dict[str, Dict] = {}
        
        # Configuration
        self.config = {
            "organization_id": 1,
            "folder_name": "Quality Billing",
            "dashboard_refresh": "30s",
            "time_range": "1h"
        }

    async def initialize(self):
        """Initialize the Grafana integration service."""
        logger.info("Initializing Grafana integration service")
        
        # Create HTTP session
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Test connection
        await self._test_connection()
        
        # Setup data sources
        await self._setup_data_sources()
        
        # Create folder for dashboards
        await self._create_dashboard_folder()
        
        # Initialize dashboard configurations
        self._initialize_dashboard_configs()
        
        logger.info("Grafana integration service initialized")

    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _test_connection(self):
        """Test connection to Grafana API."""
        try:
            async with self.session.get(f"{self.grafana_url}/api/health") as response:
                if response.status == 200:
                    logger.info("Grafana connection test successful")
                else:
                    raise Exception(f"Grafana health check failed: {response.status}")
        except Exception as e:
            logger.error(f"Failed to connect to Grafana: {e}")
            raise

    async def _setup_data_sources(self):
        """Setup Prometheus data source in Grafana."""
        prometheus_datasource = {
            "name": "Prometheus-QualityBilling",
            "type": "prometheus",
            "url": self.prometheus_url,
            "access": "proxy",
            "isDefault": True,
            "jsonData": {
                "httpMethod": "POST",
                "timeInterval": "15s"
            }
        }
        
        try:
            # Check if data source exists
            async with self.session.get(
                f"{self.grafana_url}/api/datasources/name/{prometheus_datasource['name']}"
            ) as response:
                if response.status == 404:
                    # Create new data source
                    async with self.session.post(
                        f"{self.grafana_url}/api/datasources",
                        json=prometheus_datasource
                    ) as create_response:
                        if create_response.status == 200:
                            logger.info("Prometheus data source created")
                        else:
                            logger.error(f"Failed to create data source: {create_response.status}")
                else:
                    logger.info("Prometheus data source already exists")
        
        except Exception as e:
            logger.error(f"Error setting up data sources: {e}")

    async def _create_dashboard_folder(self):
        """Create folder for quality billing dashboards."""
        folder_config = {
            "title": self.config["folder_name"],
            "uid": "quality-billing-folder"
        }
        
        try:
            async with self.session.post(
                f"{self.grafana_url}/api/folders",
                json=folder_config
            ) as response:
                if response.status in [200, 412]:  # 412 = already exists
                    logger.info(f"Dashboard folder '{self.config['folder_name']}' ready")
                else:
                    logger.error(f"Failed to create folder: {response.status}")
        
        except Exception as e:
            logger.error(f"Error creating dashboard folder: {e}")

    def _initialize_dashboard_configs(self):
        """Initialize dashboard configurations."""
        
        # Main Quality Billing Overview Dashboard
        self.dashboards["overview"] = self._create_overview_dashboard()
        
        # Work Time Analytics Dashboard
        self.dashboards["work_time"] = self._create_work_time_dashboard()
        
        # Quality Metrics Dashboard
        self.dashboards["quality"] = self._create_quality_dashboard()
        
        # Billing Analytics Dashboard
        self.dashboards["billing"] = self._create_billing_dashboard()
        
        # System Performance Dashboard
        self.dashboards["system"] = self._create_system_dashboard()

    def _create_overview_dashboard(self) -> Dict:
        """Create the main overview dashboard configuration."""
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Overview",
                "uid": "quality-billing-overview",
                "tags": ["quality-billing", "overview"],
                "timezone": "browser",
                "refresh": self.config["dashboard_refresh"],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "panels": [
                    # Key Metrics Row
                    {
                        "id": 1,
                        "title": "Active Users",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                        "targets": [{
                            "expr": "quality_billing_current_active_users",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 5},
                                        {"color": "green", "value": 10}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Average Quality Score",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
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
                        }
                    },
                    {
                        "id": 3,
                        "title": "Today's Revenue",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                        "targets": [{
                            "expr": "quality_billing_today_total_amount_cents / 100",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "currencyUSD",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 1000},
                                        {"color": "green", "value": 5000}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": 4,
                        "title": "Work Efficiency",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                        "targets": [{
                            "expr": "quality_billing_overall_work_efficiency",
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
                        }
                    },
                    # Time Series Charts
                    {
                        "id": 5,
                        "title": "Quality Score Trend",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 8},
                        "targets": [{
                            "expr": "avg(quality_billing_quality_score) by (user_id)",
                            "refId": "A",
                            "legendFormat": "User {{user_id}}"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "min": 0,
                                "max": 1
                            }
                        }
                    },
                    {
                        "id": 6,
                        "title": "API Response Time",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 8},
                        "targets": [{
                            "expr": "histogram_quantile(0.95, rate(quality_billing_api_response_time_seconds_bucket[5m]))",
                            "refId": "A",
                            "legendFormat": "95th percentile"
                        }, {
                            "expr": "histogram_quantile(0.50, rate(quality_billing_api_response_time_seconds_bucket[5m]))",
                            "refId": "B",
                            "legendFormat": "50th percentile"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "s"
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def _create_work_time_dashboard(self) -> Dict:
        """Create work time analytics dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Work Time Analytics",
                "uid": "quality-billing-work-time",
                "tags": ["quality-billing", "work-time"],
                "timezone": "browser",
                "refresh": self.config["dashboard_refresh"],
                "time": {
                    "from": "now-24h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "Total Work Hours Today",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
                        "targets": [{
                            "expr": "quality_billing_today_total_work_hours",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "h"
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Effective Work Hours",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
                        "targets": [{
                            "expr": "quality_billing_today_effective_work_hours",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "h"
                            }
                        }
                    },
                    {
                        "id": 3,
                        "title": "Work Efficiency",
                        "type": "gauge",
                        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
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
                    {
                        "id": 4,
                        "title": "Work Time by User",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 8},
                        "targets": [{
                            "expr": "rate(quality_billing_work_time_total_seconds[1h]) by (user_id) * 3600",
                            "refId": "A",
                            "legendFormat": "User {{user_id}}"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "h"
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def _create_quality_dashboard(self) -> Dict:
        """Create quality metrics dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Quality Metrics",
                "uid": "quality-billing-quality",
                "tags": ["quality-billing", "quality"],
                "timezone": "browser",
                "refresh": self.config["dashboard_refresh"],
                "time": {
                    "from": "now-6h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "Quality Score Distribution",
                        "type": "histogram",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 0},
                        "targets": [{
                            "expr": "quality_billing_quality_score",
                            "refId": "A"
                        }]
                    },
                    {
                        "id": 2,
                        "title": "Quality Assessments Today",
                        "type": "stat",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 0},
                        "targets": [{
                            "expr": "quality_billing_assessments_today",
                            "refId": "A"
                        }]
                    },
                    {
                        "id": 3,
                        "title": "Quality Improvement Rate",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 9},
                        "targets": [{
                            "expr": "quality_billing_quality_improvement_rate",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit"
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    def _create_billing_dashboard(self) -> Dict:
        """Create billing analytics dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - Billing Analytics",
                "uid": "quality-billing-billing",
                "tags": ["quality-billing", "billing"],
                "timezone": "browser",
                "refresh": self.config["dashboard_refresh"],
                "time": {
                    "from": "now-7d",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "Daily Revenue",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 0},
                        "targets": [{
                            "expr": "increase(quality_billing_total_amount_cents[1d]) / 100",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "currencyUSD"
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Invoices Generated",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 0},
                        "targets": [{
                            "expr": "increase(quality_billing_invoices_generated_total[1d])",
                            "refId": "A"
                        }]
                    },
                    {
                        "id": 3,
                        "title": "Average Invoice Amount",
                        "type": "stat",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 9},
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

    def _create_system_dashboard(self) -> Dict:
        """Create system performance dashboard."""
        return {
            "dashboard": {
                "id": None,
                "title": "Quality Billing - System Performance",
                "uid": "quality-billing-system",
                "tags": ["quality-billing", "system"],
                "timezone": "browser",
                "refresh": self.config["dashboard_refresh"],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "CPU Usage",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 8, "x": 0, "y": 0},
                        "targets": [{
                            "expr": "system_cpu_percent",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Memory Usage",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 8, "x": 8, "y": 0},
                        "targets": [{
                            "expr": "system_memory_percent",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100
                            }
                        }
                    },
                    {
                        "id": 3,
                        "title": "Disk Usage",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 8, "x": 16, "y": 0},
                        "targets": [{
                            "expr": "system_disk_percent",
                            "refId": "A"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100
                            }
                        }
                    },
                    {
                        "id": 4,
                        "title": "API Request Rate",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 9},
                        "targets": [{
                            "expr": "rate(quality_billing_api_requests_total[5m])",
                            "refId": "A",
                            "legendFormat": "{{endpoint}} - {{method}}"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "reqps"
                            }
                        }
                    }
                ]
            },
            "folderId": None,
            "folderUid": "quality-billing-folder",
            "overwrite": True
        }

    async def deploy_dashboards(self):
        """Deploy all dashboards to Grafana."""
        logger.info("Deploying dashboards to Grafana")
        
        deployed_dashboards = {}
        
        for dashboard_name, dashboard_config in self.dashboards.items():
            try:
                async with self.session.post(
                    f"{self.grafana_url}/api/dashboards/db",
                    json=dashboard_config
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        dashboard_uid = result.get("uid")
                        dashboard_url = f"{self.grafana_url}/d/{dashboard_uid}"
                        
                        deployed_dashboards[dashboard_name] = {
                            "uid": dashboard_uid,
                            "url": dashboard_url,
                            "status": "deployed"
                        }
                        
                        logger.info(f"Dashboard '{dashboard_name}' deployed: {dashboard_url}")
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to deploy dashboard '{dashboard_name}': {response.status} - {error_text}")
                        
                        deployed_dashboards[dashboard_name] = {
                            "status": "failed",
                            "error": f"HTTP {response.status}: {error_text}"
                        }
            
            except Exception as e:
                logger.error(f"Error deploying dashboard '{dashboard_name}': {e}")
                deployed_dashboards[dashboard_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return deployed_dashboards

    async def update_dashboards(self):
        """Update existing dashboards with latest configurations."""
        return await self.deploy_dashboards()

    async def get_dashboard_urls(self) -> Dict[str, str]:
        """Get URLs for all deployed dashboards."""
        dashboard_urls = {}
        
        for dashboard_name, dashboard_config in self.dashboards.items():
            dashboard_uid = dashboard_config["dashboard"]["uid"]
            dashboard_urls[dashboard_name] = f"{self.grafana_url}/d/{dashboard_uid}"
        
        return dashboard_urls

    async def create_alert_rules(self):
        """Create Grafana alert rules for quality billing metrics."""
        alert_rules = [
            {
                "uid": "quality-billing-low-quality",
                "title": "Low Quality Score Alert",
                "condition": "A",
                "data": [{
                    "refId": "A",
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 600,
                        "to": 0
                    },
                    "model": {
                        "expr": "avg(quality_billing_quality_score) < 0.7",
                        "refId": "A"
                    }
                }],
                "noDataState": "NoData",
                "execErrState": "Alerting",
                "for": "5m",
                "annotations": {
                    "summary": "Quality score is below threshold",
                    "description": "Average quality score has been below 70% for 5 minutes"
                },
                "labels": {
                    "severity": "warning",
                    "team": "quality-billing"
                }
            },
            {
                "uid": "quality-billing-high-response-time",
                "title": "High API Response Time",
                "condition": "A",
                "data": [{
                    "refId": "A",
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "model": {
                        "expr": "histogram_quantile(0.95, rate(quality_billing_api_response_time_seconds_bucket[5m])) > 2.0",
                        "refId": "A"
                    }
                }],
                "noDataState": "NoData",
                "execErrState": "Alerting",
                "for": "2m",
                "annotations": {
                    "summary": "API response time is high",
                    "description": "95th percentile response time is above 2 seconds"
                },
                "labels": {
                    "severity": "warning",
                    "team": "quality-billing"
                }
            }
        ]
        
        # Deploy alert rules
        for rule in alert_rules:
            try:
                async with self.session.post(
                    f"{self.grafana_url}/api/ruler/grafana/api/v1/rules/quality-billing",
                    json={"rules": [rule]}
                ) as response:
                    if response.status == 202:
                        logger.info(f"Alert rule '{rule['title']}' created")
                    else:
                        logger.error(f"Failed to create alert rule '{rule['title']}': {response.status}")
            
            except Exception as e:
                logger.error(f"Error creating alert rule '{rule['title']}': {e}")

    async def export_dashboard_config(self, dashboard_name: str, file_path: str):
        """Export dashboard configuration to file."""
        if dashboard_name not in self.dashboards:
            raise ValueError(f"Dashboard '{dashboard_name}' not found")
        
        config = self.dashboards[dashboard_name]
        
        # Write to file
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Dashboard '{dashboard_name}' exported to {file_path}")

    async def import_dashboard_config(self, file_path: str) -> str:
        """Import dashboard configuration from file."""
        with open(file_path, 'r') as f:
            config = json.load(f)
        
        # Deploy the imported dashboard
        async with self.session.post(
            f"{self.grafana_url}/api/dashboards/db",
            json=config
        ) as response:
            if response.status == 200:
                result = await response.json()
                dashboard_uid = result.get("uid")
                logger.info(f"Dashboard imported with UID: {dashboard_uid}")
                return dashboard_uid
            else:
                error_text = await response.text()
                raise Exception(f"Failed to import dashboard: {response.status} - {error_text}")


# Global Grafana integration service
grafana_service: Optional[GrafanaIntegrationService] = None


def initialize_grafana_integration(
    grafana_url: str,
    api_key: str,
    prometheus_url: str = "http://localhost:9090"
) -> GrafanaIntegrationService:
    """Initialize the global Grafana integration service."""
    global grafana_service
    grafana_service = GrafanaIntegrationService(grafana_url, api_key, prometheus_url)
    return grafana_service


def get_grafana_service() -> Optional[GrafanaIntegrationService]:
    """Get the global Grafana service instance."""
    return grafana_service