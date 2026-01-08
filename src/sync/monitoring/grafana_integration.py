"""
Grafana Integration Service for Data Sync System.

Provides integration with Grafana for dashboard management and visualization.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class GrafanaDashboard:
    """Grafana dashboard configuration."""
    uid: str
    title: str
    tags: List[str] = field(default_factory=list)
    folder_id: Optional[int] = None
    dashboard_json: Optional[Dict[str, Any]] = None


@dataclass
class GrafanaAlert:
    """Grafana alert configuration."""
    uid: str
    title: str
    condition: str
    frequency: str
    for_duration: str
    no_data_state: str = "NoData"
    exec_err_state: str = "Alerting"
    folder_id: Optional[int] = None


class GrafanaClient:
    """
    Grafana API client for managing dashboards and alerts.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Grafana API."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.base_url}/api{endpoint}"
        
        try:
            async with self.session.request(method, url, json=data) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"Grafana API error: {response.status} - {response_data}")
                    raise Exception(f"Grafana API error: {response.status}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"Grafana client error: {e}")
            raise

    async def get_health(self) -> Dict[str, Any]:
        """Check Grafana health."""
        return await self._request('GET', '/health')

    async def create_dashboard(self, dashboard: GrafanaDashboard) -> Dict[str, Any]:
        """Create or update a dashboard."""
        payload = {
            "dashboard": dashboard.dashboard_json,
            "folderId": dashboard.folder_id,
            "overwrite": True,
            "message": f"Updated by sync system at {datetime.now().isoformat()}"
        }
        
        return await self._request('POST', '/dashboards/db', payload)

    async def get_dashboard(self, uid: str) -> Dict[str, Any]:
        """Get dashboard by UID."""
        return await self._request('GET', f'/dashboards/uid/{uid}')

    async def delete_dashboard(self, uid: str) -> Dict[str, Any]:
        """Delete dashboard by UID."""
        return await self._request('DELETE', f'/dashboards/uid/{uid}')

    async def list_dashboards(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List dashboards, optionally filtered by tag."""
        endpoint = '/search?type=dash-db'
        if tag:
            endpoint += f'&tag={tag}'
        
        return await self._request('GET', endpoint)

    async def create_folder(self, title: str, uid: Optional[str] = None) -> Dict[str, Any]:
        """Create a folder."""
        payload = {"title": title}
        if uid:
            payload["uid"] = uid
            
        return await self._request('POST', '/folders', payload)

    async def get_datasources(self) -> List[Dict[str, Any]]:
        """Get all datasources."""
        return await self._request('GET', '/datasources')

    async def create_datasource(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a datasource."""
        return await self._request('POST', '/datasources', config)


class GrafanaIntegrationService:
    """
    Service for managing Grafana integration.
    
    Handles dashboard deployment, updates, and monitoring.
    """

    def __init__(
        self,
        grafana_url: str,
        api_key: str,
        prometheus_url: str = "http://localhost:9090"
    ):
        self.grafana_url = grafana_url
        self.api_key = api_key
        self.prometheus_url = prometheus_url
        self.folder_name = "Data Sync System"
        self.folder_uid = "sync-system"

    async def initialize(self):
        """Initialize Grafana integration."""
        async with GrafanaClient(self.grafana_url, self.api_key) as client:
            # Check Grafana health
            try:
                health = await client.get_health()
                logger.info(f"Grafana health check: {health}")
            except Exception as e:
                logger.error(f"Failed to connect to Grafana: {e}")
                raise

            # Create folder for sync dashboards
            try:
                await client.create_folder(self.folder_name, self.folder_uid)
                logger.info(f"Created Grafana folder: {self.folder_name}")
            except Exception as e:
                logger.debug(f"Folder may already exist: {e}")

            # Ensure Prometheus datasource exists
            await self._ensure_prometheus_datasource(client)

    async def _ensure_prometheus_datasource(self, client: GrafanaClient):
        """Ensure Prometheus datasource is configured."""
        datasources = await client.get_datasources()
        
        # Check if Prometheus datasource exists
        prometheus_exists = any(
            ds.get('type') == 'prometheus' and ds.get('name') == 'Prometheus'
            for ds in datasources
        )
        
        if not prometheus_exists:
            datasource_config = {
                "name": "Prometheus",
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
                await client.create_datasource(datasource_config)
                logger.info("Created Prometheus datasource in Grafana")
            except Exception as e:
                logger.warning(f"Failed to create Prometheus datasource: {e}")

    async def deploy_dashboards(self):
        """Deploy all sync system dashboards."""
        async with GrafanaClient(self.grafana_url, self.api_key) as client:
            # Get folder ID
            folders = await client._request('GET', '/folders')
            folder_id = None
            for folder in folders:
                if folder.get('uid') == self.folder_uid:
                    folder_id = folder.get('id')
                    break

            # Deploy overview dashboard
            await self._deploy_overview_dashboard(client, folder_id)
            
            # Deploy performance dashboard
            await self._deploy_performance_dashboard(client, folder_id)
            
            # Deploy conflict analysis dashboard
            await self._deploy_conflict_dashboard(client, folder_id)

    async def _deploy_overview_dashboard(self, client: GrafanaClient, folder_id: Optional[int]):
        """Deploy the sync overview dashboard."""
        dashboard_json = self._create_overview_dashboard()
        
        dashboard = GrafanaDashboard(
            uid="sync-system-overview",
            title="Data Sync System Overview",
            tags=["sync", "overview"],
            folder_id=folder_id,
            dashboard_json=dashboard_json
        )
        
        try:
            result = await client.create_dashboard(dashboard)
            logger.info(f"Deployed overview dashboard: {result.get('url')}")
        except Exception as e:
            logger.error(f"Failed to deploy overview dashboard: {e}")

    async def _deploy_performance_dashboard(self, client: GrafanaClient, folder_id: Optional[int]):
        """Deploy the performance monitoring dashboard."""
        dashboard_json = self._create_performance_dashboard()
        
        dashboard = GrafanaDashboard(
            uid="sync-system-performance",
            title="Data Sync System Performance",
            tags=["sync", "performance"],
            folder_id=folder_id,
            dashboard_json=dashboard_json
        )
        
        try:
            result = await client.create_dashboard(dashboard)
            logger.info(f"Deployed performance dashboard: {result.get('url')}")
        except Exception as e:
            logger.error(f"Failed to deploy performance dashboard: {e}")

    async def _deploy_conflict_dashboard(self, client: GrafanaClient, folder_id: Optional[int]):
        """Deploy the conflict analysis dashboard."""
        dashboard_json = self._create_conflict_dashboard()
        
        dashboard = GrafanaDashboard(
            uid="sync-system-conflicts",
            title="Data Sync Conflict Analysis",
            tags=["sync", "conflicts"],
            folder_id=folder_id,
            dashboard_json=dashboard_json
        )
        
        try:
            result = await client.create_dashboard(dashboard)
            logger.info(f"Deployed conflict dashboard: {result.get('url')}")
        except Exception as e:
            logger.error(f"Failed to deploy conflict dashboard: {e}")

    def _create_overview_dashboard(self) -> Dict[str, Any]:
        """Create the overview dashboard configuration."""
        return {
            "id": None,
            "uid": "sync-system-overview",
            "title": "Data Sync System Overview",
            "tags": ["sync", "overview"],
            "timezone": "browser",
            "schemaVersion": 30,
            "version": 1,
            "refresh": "10s",
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "templating": {
                "list": [
                    {
                        "name": "connector_type",
                        "type": "query",
                        "datasource": "Prometheus",
                        "query": "label_values(sync_operations_total, connector_type)",
                        "refresh": 1,
                        "includeAll": True,
                        "multi": True
                    }
                ]
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Sync Operations Rate",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "rate(sync_operations_total{connector_type=~\"$connector_type\"}[5m])",
                            "legendFormat": "{{connector_type}} - {{operation}}",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ops",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            }
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "Active Sync Jobs",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "sync_active_jobs",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 10},
                                    {"color": "red", "value": 50}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 3,
                    "title": "Queue Depth",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
                    "targets": [
                        {
                            "expr": "sync_queue_depth",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 1000},
                                    {"color": "red", "value": 5000}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 4,
                    "title": "Error Rate",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                    "targets": [
                        {
                            "expr": "rate(sync_errors_total[5m]) / rate(sync_operations_total[5m])",
                            "legendFormat": "Error Rate",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 0.05},
                                    {"color": "red", "value": 0.20}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 5,
                    "title": "Sync Latency (P95)",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 12},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(sync_latency_seconds_bucket[5m]))",
                            "legendFormat": "P95 Latency",
                            "refId": "A"
                        },
                        {
                            "expr": "histogram_quantile(0.50, rate(sync_latency_seconds_bucket[5m]))",
                            "legendFormat": "P50 Latency",
                            "refId": "B"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "s",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            }
                        }
                    }
                }
            ]
        }

    def _create_performance_dashboard(self) -> Dict[str, Any]:
        """Create the performance monitoring dashboard configuration."""
        return {
            "id": None,
            "uid": "sync-system-performance",
            "title": "Data Sync System Performance",
            "tags": ["sync", "performance"],
            "timezone": "browser",
            "schemaVersion": 30,
            "version": 1,
            "refresh": "5s",
            "time": {
                "from": "now-30m",
                "to": "now"
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Throughput (Records/sec)",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "rate(sync_records_total[1m])",
                            "legendFormat": "{{connector_type}}",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "rps",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            }
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "Connection Pool Usage",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "connector_pool_size - connector_pool_available",
                            "legendFormat": "Used - {{connector}}",
                            "refId": "A"
                        },
                        {
                            "expr": "connector_pool_available",
                            "legendFormat": "Available - {{connector}}",
                            "refId": "B"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            }
                        }
                    }
                },
                {
                    "id": 3,
                    "title": "WebSocket Connections",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "websocket_active_connections",
                            "legendFormat": "Active Connections",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            }
                        }
                    }
                },
                {
                    "id": 4,
                    "title": "Backpressure Events",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "targets": [
                        {
                            "expr": "rate(websocket_backpressure_events[1m])",
                            "legendFormat": "{{strategy}}",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ops",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            }
                        }
                    }
                }
            ]
        }

    def _create_conflict_dashboard(self) -> Dict[str, Any]:
        """Create the conflict analysis dashboard configuration."""
        return {
            "id": None,
            "uid": "sync-system-conflicts",
            "title": "Data Sync Conflict Analysis",
            "tags": ["sync", "conflicts"],
            "timezone": "browser",
            "schemaVersion": 30,
            "version": 1,
            "refresh": "30s",
            "time": {
                "from": "now-6h",
                "to": "now"
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Conflict Detection Rate",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "rate(conflict_detected_total[5m])",
                            "legendFormat": "{{type}}",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ops",
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            }
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "Resolution Success Rate",
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "avg(conflict_resolution_rate)",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": None},
                                    {"color": "yellow", "value": 0.80},
                                    {"color": "green", "value": 0.90}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 3,
                    "title": "Conflict Types Distribution",
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "sum by (type) (conflict_detected_total)",
                            "legendFormat": "{{type}}",
                            "refId": "A"
                        }
                    ]
                },
                {
                    "id": 4,
                    "title": "Resolution Strategy Usage",
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "targets": [
                        {
                            "expr": "sum by (strategy) (conflict_resolved_total)",
                            "legendFormat": "{{strategy}}",
                            "refId": "A"
                        }
                    ]
                }
            ]
        }

    async def update_dashboards(self):
        """Update existing dashboards with latest configuration."""
        await self.deploy_dashboards()

    async def get_dashboard_urls(self) -> Dict[str, str]:
        """Get URLs for all deployed dashboards."""
        async with GrafanaClient(self.grafana_url, self.api_key) as client:
            dashboards = await client.list_dashboards(tag="sync")
            
            urls = {}
            for dashboard in dashboards:
                uid = dashboard.get('uid')
                title = dashboard.get('title')
                if uid and title:
                    urls[title] = f"{self.grafana_url}/d/{uid}"
            
            return urls


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


async def deploy_sync_dashboards():
    """Deploy all sync system dashboards to Grafana."""
    if not grafana_service:
        raise RuntimeError("Grafana service not initialized")
    
    await grafana_service.initialize()
    await grafana_service.deploy_dashboards()
    
    urls = await grafana_service.get_dashboard_urls()
    logger.info(f"Deployed dashboards: {urls}")
    return urls