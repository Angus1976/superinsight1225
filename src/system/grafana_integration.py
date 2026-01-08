"""
Enhanced Grafana Integration Service for System Health Monitoring.

Provides comprehensive Grafana integration including dashboard deployment,
data source configuration, and real-time monitoring setup.
"""

import asyncio
import logging
import json
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import aiohttp
from dataclasses import dataclass, field

from src.system.grafana_dashboards import dashboard_generator

logger = logging.getLogger(__name__)


@dataclass
class GrafanaConfig:
    """Configuration for Grafana integration."""
    url: str
    api_key: str
    prometheus_url: str = "http://localhost:9090"
    organization_id: int = 1
    folder_name: str = "SuperInsight Monitoring"
    auto_deploy_dashboards: bool = True
    timeout_seconds: int = 30


class GrafanaIntegrationService:
    """
    Enhanced Grafana integration service for system monitoring.
    
    Provides:
    - Automated dashboard deployment and management
    - Data source configuration and validation
    - Alert rule management
    - Real-time monitoring setup
    """
    
    def __init__(self, config: GrafanaConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.folder_id: Optional[int] = None
        self.datasource_uid: Optional[str] = None
        
        # Dashboard tracking
        self.deployed_dashboards: Dict[str, Dict[str, Any]] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        
        logger.info(f"Grafana integration initialized for {config.url}")
    
    async def initialize(self):
        """Initialize Grafana integration service."""
        logger.info("Initializing Grafana integration service")
        
        # Create HTTP session
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        
        # Test connection
        await self._test_connection()
        
        # Setup folder
        await self._setup_folder()
        
        # Setup data sources
        await self._setup_prometheus_datasource()
        
        # Deploy dashboards if auto-deploy is enabled
        if self.config.auto_deploy_dashboards:
            await self.deploy_all_dashboards()
        
        # Setup alert rules
        await self._setup_alert_rules()
        
        logger.info("Grafana integration service initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("Grafana integration service cleaned up")
    
    async def _test_connection(self):
        """Test connection to Grafana API."""
        try:
            async with self.session.get(f"{self.config.url}/api/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"Grafana connection successful: {health_data}")
                else:
                    raise Exception(f"Grafana health check failed: HTTP {response.status}")
        
        except Exception as e:
            logger.error(f"Failed to connect to Grafana: {e}")
            raise Exception(f"Grafana connection failed: {e}")
    
    async def _setup_folder(self):
        """Setup folder for SuperInsight dashboards."""
        try:
            # Check if folder exists
            async with self.session.get(f"{self.config.url}/api/folders") as response:
                if response.status == 200:
                    folders = await response.json()
                    
                    # Look for existing folder
                    for folder in folders:
                        if folder.get("title") == self.config.folder_name:
                            self.folder_id = folder.get("id")
                            logger.info(f"Found existing folder: {self.config.folder_name} (ID: {self.folder_id})")
                            return
            
            # Create new folder
            folder_config = {
                "title": self.config.folder_name,
                "uid": "superinsight-monitoring"
            }
            
            async with self.session.post(
                f"{self.config.url}/api/folders",
                json=folder_config
            ) as response:
                if response.status in [200, 201]:
                    folder_data = await response.json()
                    self.folder_id = folder_data.get("id")
                    logger.info(f"Created folder: {self.config.folder_name} (ID: {self.folder_id})")
                elif response.status == 412:
                    # Folder already exists
                    logger.info(f"Folder {self.config.folder_name} already exists")
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create folder: HTTP {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"Error setting up folder: {e}")
            # Continue without folder - dashboards can still be deployed
    
    async def _setup_prometheus_datasource(self):
        """Setup Prometheus data source."""
        try:
            datasource_name = "Prometheus-SuperInsight"
            
            # Check if data source exists
            async with self.session.get(
                f"{self.config.url}/api/datasources/name/{datasource_name}"
            ) as response:
                if response.status == 200:
                    datasource_data = await response.json()
                    self.datasource_uid = datasource_data.get("uid")
                    logger.info(f"Found existing Prometheus datasource: {datasource_name}")
                    return
            
            # Create new data source
            datasource_config = {
                "name": datasource_name,
                "type": "prometheus",
                "url": self.config.prometheus_url,
                "access": "proxy",
                "isDefault": True,
                "jsonData": {
                    "httpMethod": "POST",
                    "timeInterval": "15s",
                    "queryTimeout": "60s",
                    "exemplarTraceIdDestinations": []
                },
                "secureJsonFields": {}
            }
            
            async with self.session.post(
                f"{self.config.url}/api/datasources",
                json=datasource_config
            ) as response:
                if response.status in [200, 201]:
                    datasource_data = await response.json()
                    self.datasource_uid = datasource_data.get("datasource", {}).get("uid")
                    logger.info(f"Created Prometheus datasource: {datasource_name}")
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create datasource: HTTP {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"Error setting up Prometheus datasource: {e}")
    
    async def deploy_all_dashboards(self):
        """Deploy all dashboard configurations to Grafana."""
        logger.info("Deploying all dashboards to Grafana")
        
        dashboards = dashboard_generator.get_all_dashboards()
        deployment_results = {}
        
        for dashboard_name, dashboard_config in dashboards.items():
            try:
                result = await self._deploy_single_dashboard(dashboard_name, dashboard_config)
                deployment_results[dashboard_name] = result
                
            except Exception as e:
                logger.error(f"Failed to deploy dashboard {dashboard_name}: {e}")
                deployment_results[dashboard_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        self.deployed_dashboards = deployment_results
        
        # Log summary
        successful = len([r for r in deployment_results.values() if r.get("status") == "success"])
        total = len(deployment_results)
        logger.info(f"Dashboard deployment complete: {successful}/{total} successful")
        
        return deployment_results
    
    async def _deploy_single_dashboard(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a single dashboard to Grafana."""
        try:
            # Update dashboard config with folder ID
            if self.folder_id:
                config["folderId"] = self.folder_id
            
            # Update datasource references if we have a specific UID
            if self.datasource_uid:
                self._update_datasource_references(config, self.datasource_uid)
            
            async with self.session.post(
                f"{self.config.url}/api/dashboards/db",
                json=config
            ) as response:
                if response.status in [200, 201]:
                    result_data = await response.json()
                    dashboard_uid = result_data.get("uid")
                    dashboard_url = f"{self.config.url}/d/{dashboard_uid}"
                    
                    logger.info(f"Successfully deployed dashboard: {name} -> {dashboard_url}")
                    
                    return {
                        "status": "success",
                        "uid": dashboard_uid,
                        "url": dashboard_url,
                        "id": result_data.get("id"),
                        "version": result_data.get("version")
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to deploy dashboard {name}: HTTP {response.status} - {error_text}")
                    
                    return {
                        "status": "failed",
                        "error": f"HTTP {response.status}: {error_text}"
                    }
        
        except Exception as e:
            logger.error(f"Error deploying dashboard {name}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _update_datasource_references(self, config: Dict[str, Any], datasource_uid: str):
        """Update datasource references in dashboard config."""
        def update_targets(obj):
            if isinstance(obj, dict):
                if "datasource" in obj and isinstance(obj["datasource"], str):
                    obj["datasource"] = {"uid": datasource_uid}
                elif "datasource" in obj and isinstance(obj["datasource"], dict):
                    obj["datasource"]["uid"] = datasource_uid
                
                for value in obj.values():
                    update_targets(value)
            elif isinstance(obj, list):
                for item in obj:
                    update_targets(item)
        
        update_targets(config)
    
    async def _setup_alert_rules(self):
        """Setup alert rules for system monitoring."""
        try:
            alert_rules = [
                {
                    "uid": "superinsight-high-cpu",
                    "title": "SuperInsight High CPU Usage",
                    "condition": "A",
                    "data": [{
                        "refId": "A",
                        "queryType": "",
                        "relativeTimeRange": {"from": 300, "to": 0},
                        "datasourceUid": self.datasource_uid or "prometheus",
                        "model": {
                            "expr": 'system_cpu_usage_percent{core="total"} > 80',
                            "refId": "A"
                        }
                    }],
                    "noDataState": "NoData",
                    "execErrState": "Alerting",
                    "for": "5m",
                    "annotations": {
                        "summary": "High CPU usage detected",
                        "description": "CPU usage has been above 80% for 5 minutes"
                    },
                    "labels": {
                        "severity": "warning",
                        "component": "system",
                        "service": "superinsight"
                    }
                },
                {
                    "uid": "superinsight-high-memory",
                    "title": "SuperInsight High Memory Usage",
                    "condition": "A",
                    "data": [{
                        "refId": "A",
                        "queryType": "",
                        "relativeTimeRange": {"from": 300, "to": 0},
                        "datasourceUid": self.datasource_uid or "prometheus",
                        "model": {
                            "expr": "system_memory_usage_percent > 90",
                            "refId": "A"
                        }
                    }],
                    "noDataState": "NoData",
                    "execErrState": "Alerting",
                    "for": "5m",
                    "annotations": {
                        "summary": "High memory usage detected",
                        "description": "Memory usage has been above 90% for 5 minutes"
                    },
                    "labels": {
                        "severity": "critical",
                        "component": "system",
                        "service": "superinsight"
                    }
                },
                {
                    "uid": "superinsight-high-response-time",
                    "title": "SuperInsight High Response Time",
                    "condition": "A",
                    "data": [{
                        "refId": "A",
                        "queryType": "",
                        "relativeTimeRange": {"from": 300, "to": 0},
                        "datasourceUid": self.datasource_uid or "prometheus",
                        "model": {
                            "expr": 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 3',
                            "refId": "A"
                        }
                    }],
                    "noDataState": "NoData",
                    "execErrState": "Alerting",
                    "for": "2m",
                    "annotations": {
                        "summary": "High API response time detected",
                        "description": "95th percentile response time is above 3 seconds"
                    },
                    "labels": {
                        "severity": "warning",
                        "component": "api",
                        "service": "superinsight"
                    }
                },
                {
                    "uid": "superinsight-low-annotation-quality",
                    "title": "SuperInsight Low Annotation Quality",
                    "condition": "A",
                    "data": [{
                        "refId": "A",
                        "queryType": "",
                        "relativeTimeRange": {"from": 600, "to": 0},
                        "datasourceUid": self.datasource_uid or "prometheus",
                        "model": {
                            "expr": "avg(business_annotation_quality_score) < 0.7",
                            "refId": "A"
                        }
                    }],
                    "noDataState": "NoData",
                    "execErrState": "Alerting",
                    "for": "10m",
                    "annotations": {
                        "summary": "Low annotation quality detected",
                        "description": "Average annotation quality score is below 70%"
                    },
                    "labels": {
                        "severity": "warning",
                        "component": "business",
                        "service": "superinsight"
                    }
                }
            ]
            
            # Deploy alert rules
            for rule in alert_rules:
                await self._deploy_alert_rule(rule)
            
            self.alert_rules = alert_rules
            logger.info(f"Setup {len(alert_rules)} alert rules")
        
        except Exception as e:
            logger.error(f"Error setting up alert rules: {e}")
    
    async def _deploy_alert_rule(self, rule: Dict[str, Any]):
        """Deploy a single alert rule to Grafana."""
        try:
            # Grafana unified alerting API
            async with self.session.post(
                f"{self.config.url}/api/ruler/grafana/api/v1/rules/superinsight",
                json={"rules": [rule]}
            ) as response:
                if response.status in [200, 201, 202]:
                    logger.info(f"Deployed alert rule: {rule['title']}")
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to deploy alert rule {rule['title']}: HTTP {response.status} - {error_text}")
        
        except Exception as e:
            logger.warning(f"Error deploying alert rule {rule['title']}: {e}")
    
    async def get_dashboard_urls(self) -> Dict[str, str]:
        """Get URLs for all deployed dashboards."""
        urls = {}
        for name, deployment_info in self.deployed_dashboards.items():
            if deployment_info.get("status") == "success":
                urls[name] = deployment_info.get("url", "")
        
        return urls
    
    async def update_dashboard(self, dashboard_name: str) -> Dict[str, Any]:
        """Update a specific dashboard."""
        dashboards = dashboard_generator.get_all_dashboards()
        
        if dashboard_name not in dashboards:
            raise ValueError(f"Dashboard {dashboard_name} not found")
        
        result = await self._deploy_single_dashboard(dashboard_name, dashboards[dashboard_name])
        self.deployed_dashboards[dashboard_name] = result
        
        return result
    
    async def delete_dashboard(self, dashboard_uid: str) -> bool:
        """Delete a dashboard by UID."""
        try:
            async with self.session.delete(
                f"{self.config.url}/api/dashboards/uid/{dashboard_uid}"
            ) as response:
                if response.status in [200, 404]:  # 404 means already deleted
                    logger.info(f"Deleted dashboard: {dashboard_uid}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to delete dashboard {dashboard_uid}: HTTP {response.status} - {error_text}")
                    return False
        
        except Exception as e:
            logger.error(f"Error deleting dashboard {dashboard_uid}: {e}")
            return False
    
    async def get_grafana_info(self) -> Dict[str, Any]:
        """Get Grafana instance information."""
        try:
            async with self.session.get(f"{self.config.url}/api/org") as response:
                if response.status == 200:
                    org_info = await response.json()
                else:
                    org_info = {"name": "Unknown"}
            
            async with self.session.get(f"{self.config.url}/api/admin/settings") as response:
                if response.status == 200:
                    settings = await response.json()
                    version = settings.get("buildInfo", {}).get("version", "Unknown")
                else:
                    version = "Unknown"
            
            return {
                "url": self.config.url,
                "organization": org_info.get("name", "Unknown"),
                "version": version,
                "folder_id": self.folder_id,
                "datasource_uid": self.datasource_uid,
                "deployed_dashboards": len(self.deployed_dashboards),
                "alert_rules": len(self.alert_rules)
            }
        
        except Exception as e:
            logger.error(f"Error getting Grafana info: {e}")
            return {
                "url": self.config.url,
                "error": str(e)
            }
    
    async def export_dashboard_config(self, dashboard_name: str, file_path: str):
        """Export dashboard configuration to file."""
        if dashboard_name not in self.deployed_dashboards:
            raise ValueError(f"Dashboard {dashboard_name} not deployed")
        
        dashboards = dashboard_generator.get_all_dashboards()
        if dashboard_name not in dashboards:
            raise ValueError(f"Dashboard {dashboard_name} not found")
        
        config = dashboards[dashboard_name]
        
        # Add deployment info
        config["deployment_info"] = self.deployed_dashboards[dashboard_name]
        config["exported_at"] = datetime.now().isoformat()
        
        # Write to file
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Dashboard {dashboard_name} exported to {file_path}")
    
    async def import_dashboard_config(self, file_path: str) -> str:
        """Import dashboard configuration from file."""
        with open(file_path, 'r') as f:
            config = json.load(f)
        
        # Remove deployment info if present
        config.pop("deployment_info", None)
        config.pop("exported_at", None)
        
        # Deploy the imported dashboard
        dashboard_name = config.get("dashboard", {}).get("title", "imported_dashboard")
        result = await self._deploy_single_dashboard(dashboard_name, config)
        
        if result.get("status") == "success":
            self.deployed_dashboards[dashboard_name] = result
            logger.info(f"Dashboard imported from {file_path}")
            return result.get("uid", "")
        else:
            raise Exception(f"Failed to import dashboard: {result.get('error', 'Unknown error')}")


# Global Grafana integration service
grafana_service: Optional[GrafanaIntegrationService] = None


async def initialize_grafana_integration(config: GrafanaConfig) -> GrafanaIntegrationService:
    """Initialize the global Grafana integration service."""
    global grafana_service
    
    grafana_service = GrafanaIntegrationService(config)
    await grafana_service.initialize()
    
    logger.info("Global Grafana integration service initialized")
    return grafana_service


async def cleanup_grafana_integration():
    """Cleanup the global Grafana integration service."""
    global grafana_service
    
    if grafana_service:
        await grafana_service.cleanup()
        grafana_service = None
        logger.info("Global Grafana integration service cleaned up")


def get_grafana_service() -> Optional[GrafanaIntegrationService]:
    """Get the global Grafana service instance."""
    return grafana_service


# Convenience functions
async def deploy_dashboards() -> Dict[str, Any]:
    """Deploy all dashboards to Grafana."""
    if not grafana_service:
        raise Exception("Grafana service not initialized")
    
    return await grafana_service.deploy_all_dashboards()


async def get_dashboard_urls() -> Dict[str, str]:
    """Get URLs for all deployed dashboards."""
    if not grafana_service:
        return {}
    
    return await grafana_service.get_dashboard_urls()


async def update_dashboard(dashboard_name: str) -> Dict[str, Any]:
    """Update a specific dashboard."""
    if not grafana_service:
        raise Exception("Grafana service not initialized")
    
    return await grafana_service.update_dashboard(dashboard_name)