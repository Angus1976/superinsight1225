"""
Grafana API endpoints for Quality Billing System.

Provides HTTP endpoints for managing Grafana dashboards,
data sources, and monitoring configurations.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from fastapi.responses import JSONResponse
import asyncio

from ..quality_billing.grafana_integration import grafana_service, GrafanaIntegrationService
from ..quality_billing.dashboard_templates import dashboard_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/grafana", tags=["grafana"])


def get_grafana_service() -> GrafanaIntegrationService:
    """Dependency to get Grafana service instance."""
    if not grafana_service:
        raise HTTPException(
            status_code=503,
            detail="Grafana service not configured. Please configure Grafana integration first."
        )
    return grafana_service


@router.get("/status")
async def get_grafana_status(service: GrafanaIntegrationService = Depends(get_grafana_service)):
    """
    Get Grafana integration status.
    
    Returns the current status of the Grafana integration including
    connection health and configuration details.
    """
    try:
        # Test connection
        await service._test_connection()
        
        status = {
            "status": "connected",
            "grafana_url": service.grafana_url,
            "prometheus_url": service.prometheus_url,
            "timestamp": datetime.now().isoformat(),
            "dashboards_configured": len(service.dashboards),
            "data_sources_configured": len(service.data_sources)
        }
        
        return status
    
    except Exception as e:
        logger.error(f"Error getting Grafana status: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )


@router.post("/dashboards/deploy")
async def deploy_dashboards(
    dashboard_names: Optional[List[str]] = Body(None, description="Specific dashboards to deploy (all if not specified)"),
    service: GrafanaIntegrationService = Depends(get_grafana_service)
):
    """
    Deploy dashboards to Grafana.
    
    Args:
        dashboard_names: Optional list of specific dashboard names to deploy.
                        If not provided, all configured dashboards will be deployed.
    
    Returns:
        Deployment results for each dashboard including URLs and status.
    """
    try:
        # If specific dashboards requested, filter the deployment
        if dashboard_names:
            original_dashboards = service.dashboards.copy()
            service.dashboards = {
                name: config for name, config in service.dashboards.items()
                if name in dashboard_names
            }
        
        # Deploy dashboards
        deployment_results = await service.deploy_dashboards()
        
        # Restore original dashboards if filtered
        if dashboard_names:
            service.dashboards = original_dashboards
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "deployed_dashboards": deployment_results,
            "total_deployed": len(deployment_results)
        }
    
    except Exception as e:
        logger.error(f"Error deploying dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Error deploying dashboards: {str(e)}")


@router.get("/dashboards")
async def list_dashboards(service: GrafanaIntegrationService = Depends(get_grafana_service)):
    """
    List all configured dashboards.
    
    Returns information about all dashboards including their URLs,
    configuration status, and metadata.
    """
    try:
        dashboard_urls = await service.get_dashboard_urls()
        
        dashboards_info = {}
        for name, config in service.dashboards.items():
            dashboard_uid = config["dashboard"]["uid"]
            dashboards_info[name] = {
                "title": config["dashboard"]["title"],
                "uid": dashboard_uid,
                "url": dashboard_urls.get(name, f"{service.grafana_url}/d/{dashboard_uid}"),
                "tags": config["dashboard"].get("tags", []),
                "refresh": config["dashboard"].get("refresh", "30s"),
                "panels_count": len(config["dashboard"].get("panels", []))
            }
        
        return {
            "dashboards": dashboards_info,
            "total_count": len(dashboards_info),
            "grafana_url": service.grafana_url
        }
    
    except Exception as e:
        logger.error(f"Error listing dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing dashboards: {str(e)}")


@router.get("/dashboards/{dashboard_name}")
async def get_dashboard_info(
    dashboard_name: str,
    service: GrafanaIntegrationService = Depends(get_grafana_service)
):
    """
    Get detailed information about a specific dashboard.
    
    Args:
        dashboard_name: Name of the dashboard to retrieve information for.
    
    Returns:
        Detailed dashboard configuration and metadata.
    """
    try:
        if dashboard_name not in service.dashboards:
            raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_name}' not found")
        
        config = service.dashboards[dashboard_name]
        dashboard_uid = config["dashboard"]["uid"]
        dashboard_urls = await service.get_dashboard_urls()
        
        return {
            "name": dashboard_name,
            "title": config["dashboard"]["title"],
            "uid": dashboard_uid,
            "url": dashboard_urls.get(dashboard_name),
            "configuration": config,
            "panels": [
                {
                    "id": panel.get("id"),
                    "title": panel.get("title"),
                    "type": panel.get("type"),
                    "gridPos": panel.get("gridPos")
                }
                for panel in config["dashboard"].get("panels", [])
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard info for {dashboard_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard info: {str(e)}")


@router.post("/dashboards/{dashboard_name}/update")
async def update_dashboard(
    dashboard_name: str,
    service: GrafanaIntegrationService = Depends(get_grafana_service)
):
    """
    Update a specific dashboard in Grafana.
    
    Args:
        dashboard_name: Name of the dashboard to update.
    
    Returns:
        Update result including new URL and status.
    """
    try:
        if dashboard_name not in service.dashboards:
            raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_name}' not found")
        
        # Update single dashboard
        original_dashboards = service.dashboards.copy()
        service.dashboards = {dashboard_name: service.dashboards[dashboard_name]}
        
        deployment_results = await service.deploy_dashboards()
        
        # Restore original dashboards
        service.dashboards = original_dashboards
        
        return {
            "status": "updated",
            "dashboard_name": dashboard_name,
            "result": deployment_results.get(dashboard_name, {}),
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dashboard {dashboard_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating dashboard: {str(e)}")


@router.get("/templates")
async def list_dashboard_templates():
    """
    List all available dashboard templates.
    
    Returns information about all dashboard templates that can be
    deployed to Grafana.
    """
    try:
        templates = dashboard_generator.get_all_dashboard_templates()
        
        templates_info = {}
        for name, config in templates.items():
            dashboard_config = config["dashboard"]
            templates_info[name] = {
                "title": dashboard_config["title"],
                "uid": dashboard_config["uid"],
                "tags": dashboard_config.get("tags", []),
                "panels_count": len(dashboard_config.get("panels", [])),
                "description": f"Template for {name.replace('_', ' ').title()} dashboard"
            }
        
        return {
            "templates": templates_info,
            "total_count": len(templates_info)
        }
    
    except Exception as e:
        logger.error(f"Error listing dashboard templates: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing templates: {str(e)}")


@router.post("/templates/{template_name}/deploy")
async def deploy_template(
    template_name: str,
    custom_config: Optional[Dict[str, Any]] = Body(None, description="Custom configuration for the template"),
    service: GrafanaIntegrationService = Depends(get_grafana_service)
):
    """
    Deploy a dashboard template to Grafana.
    
    Args:
        template_name: Name of the template to deploy.
        custom_config: Optional custom configuration to override template defaults.
    
    Returns:
        Deployment result including dashboard URL and status.
    """
    try:
        # Get template configuration
        if template_name == "executive":
            template_config = dashboard_generator.create_executive_dashboard(custom_config)
        elif template_name == "operational":
            template_config = dashboard_generator.create_operational_dashboard(custom_config)
        elif template_name == "quality_analytics":
            template_config = dashboard_generator.create_quality_analytics_dashboard(custom_config)
        elif template_name == "financial":
            template_config = dashboard_generator.create_financial_dashboard(custom_config)
        else:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        # Deploy the template
        async with service.session.post(
            f"{service.grafana_url}/api/dashboards/db",
            json=template_config
        ) as response:
            if response.status == 200:
                result = await response.json()
                dashboard_uid = result.get("uid")
                dashboard_url = f"{service.grafana_url}/d/{dashboard_uid}"
                
                return {
                    "status": "deployed",
                    "template_name": template_name,
                    "dashboard_uid": dashboard_uid,
                    "dashboard_url": dashboard_url,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                error_text = await response.text()
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Failed to deploy template: {error_text}"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying template {template_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deploying template: {str(e)}")


@router.post("/alerts/deploy")
async def deploy_alert_rules(service: GrafanaIntegrationService = Depends(get_grafana_service)):
    """
    Deploy alert rules to Grafana.
    
    Creates and deploys alert rules for quality billing metrics
    to enable proactive monitoring and notifications.
    """
    try:
        await service.create_alert_rules()
        
        return {
            "status": "deployed",
            "message": "Alert rules deployed successfully",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error deploying alert rules: {e}")
        raise HTTPException(status_code=500, detail=f"Error deploying alert rules: {str(e)}")


@router.get("/datasources")
async def list_data_sources(service: GrafanaIntegrationService = Depends(get_grafana_service)):
    """
    List configured data sources in Grafana.
    
    Returns information about all data sources configured
    for the quality billing system.
    """
    try:
        # Get data sources from Grafana API
        async with service.session.get(f"{service.grafana_url}/api/datasources") as response:
            if response.status == 200:
                datasources = await response.json()
                
                # Filter for quality billing related data sources
                quality_billing_datasources = [
                    ds for ds in datasources
                    if "quality" in ds.get("name", "").lower() or "prometheus" in ds.get("name", "").lower()
                ]
                
                return {
                    "datasources": quality_billing_datasources,
                    "total_count": len(quality_billing_datasources)
                }
            else:
                raise HTTPException(
                    status_code=response.status,
                    detail="Failed to retrieve data sources from Grafana"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing data sources: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing data sources: {str(e)}")


@router.post("/datasources/setup")
async def setup_data_sources(service: GrafanaIntegrationService = Depends(get_grafana_service)):
    """
    Setup required data sources in Grafana.
    
    Creates and configures the Prometheus data source
    for quality billing metrics.
    """
    try:
        await service._setup_data_sources()
        
        return {
            "status": "configured",
            "message": "Data sources setup completed",
            "prometheus_url": service.prometheus_url,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error setting up data sources: {e}")
        raise HTTPException(status_code=500, detail=f"Error setting up data sources: {str(e)}")


@router.post("/dashboards/export/{dashboard_name}")
async def export_dashboard(
    dashboard_name: str,
    service: GrafanaIntegrationService = Depends(get_grafana_service)
):
    """
    Export dashboard configuration to JSON.
    
    Args:
        dashboard_name: Name of the dashboard to export.
    
    Returns:
        Dashboard configuration in JSON format.
    """
    try:
        if dashboard_name not in service.dashboards:
            raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_name}' not found")
        
        config = service.dashboards[dashboard_name]
        
        return {
            "dashboard_name": dashboard_name,
            "configuration": config,
            "exported_at": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting dashboard {dashboard_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting dashboard: {str(e)}")


@router.post("/dashboards/import")
async def import_dashboard(
    dashboard_config: Dict[str, Any] = Body(..., description="Dashboard configuration to import"),
    service: GrafanaIntegrationService = Depends(get_grafana_service)
):
    """
    Import and deploy a dashboard configuration.
    
    Args:
        dashboard_config: Complete dashboard configuration in Grafana format.
    
    Returns:
        Import result including dashboard URL and UID.
    """
    try:
        # Deploy the imported dashboard
        async with service.session.post(
            f"{service.grafana_url}/api/dashboards/db",
            json=dashboard_config
        ) as response:
            if response.status == 200:
                result = await response.json()
                dashboard_uid = result.get("uid")
                dashboard_url = f"{service.grafana_url}/d/{dashboard_uid}"
                
                return {
                    "status": "imported",
                    "dashboard_uid": dashboard_uid,
                    "dashboard_url": dashboard_url,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                error_text = await response.text()
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Failed to import dashboard: {error_text}"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing dashboard: {str(e)}")


@router.get("/health")
async def get_grafana_health():
    """
    Get Grafana service health status.
    
    Returns health information for the Grafana integration
    including connection status and service availability.
    """
    try:
        if not grafana_service:
            return JSONResponse(
                content={
                    "status": "not_configured",
                    "message": "Grafana service not configured",
                    "timestamp": datetime.now().isoformat()
                },
                status_code=503
            )
        
        # Test connection
        await grafana_service._test_connection()
        
        return {
            "status": "healthy",
            "grafana_url": grafana_service.grafana_url,
            "prometheus_url": grafana_service.prometheus_url,
            "dashboards_count": len(grafana_service.dashboards),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Grafana health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )