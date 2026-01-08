"""
Grafana Monitoring API Endpoints.

Provides HTTP endpoints for Grafana dashboard management,
deployment, and monitoring visualization.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from fastapi.responses import JSONResponse
import asyncio

from src.system.grafana_integration import (
    grafana_service,
    initialize_grafana_integration,
    cleanup_grafana_integration,
    GrafanaConfig,
    get_grafana_service
)
from src.system.grafana_dashboards import dashboard_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/grafana", tags=["grafana"])


def get_grafana_service_dependency() -> Optional[object]:
    """Dependency to get Grafana service instance."""
    service = get_grafana_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Grafana service not initialized. Please configure Grafana integration first."
        )
    return service


@router.post("/initialize")
async def initialize_grafana(
    url: str = Body(..., description="Grafana URL"),
    api_key: str = Body(..., description="Grafana API key"),
    prometheus_url: str = Body("http://localhost:9090", description="Prometheus URL"),
    folder_name: str = Body("SuperInsight Monitoring", description="Dashboard folder name"),
    auto_deploy: bool = Body(True, description="Auto-deploy dashboards")
):
    """
    Initialize Grafana integration.
    
    Args:
        url: Grafana instance URL
        api_key: Grafana API key with admin permissions
        prometheus_url: Prometheus server URL
        folder_name: Name for dashboard folder
        auto_deploy: Whether to automatically deploy dashboards
    
    Returns:
        Initialization result with connection status and deployment info.
    """
    try:
        config = GrafanaConfig(
            url=url.rstrip('/'),
            api_key=api_key,
            prometheus_url=prometheus_url,
            folder_name=folder_name,
            auto_deploy_dashboards=auto_deploy
        )
        
        service = await initialize_grafana_integration(config)
        
        # Get deployment results
        dashboard_urls = await service.get_dashboard_urls()
        grafana_info = await service.get_grafana_info()
        
        return {
            "status": "initialized",
            "timestamp": datetime.now().isoformat(),
            "grafana_info": grafana_info,
            "dashboard_urls": dashboard_urls,
            "deployed_dashboards": len(dashboard_urls),
            "message": "Grafana integration initialized successfully"
        }
    
    except Exception as e:
        logger.error(f"Error initializing Grafana integration: {e}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@router.get("/status")
async def get_grafana_status():
    """
    Get Grafana integration status.
    
    Returns current status of Grafana integration including
    connection health, deployed dashboards, and configuration.
    """
    try:
        service = get_grafana_service()
        
        if not service:
            return {
                "status": "not_initialized",
                "message": "Grafana integration not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get Grafana info
        grafana_info = await service.get_grafana_info()
        
        # Get dashboard URLs
        dashboard_urls = await service.get_dashboard_urls()
        
        return {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "grafana_info": grafana_info,
            "dashboard_urls": dashboard_urls,
            "deployed_dashboards": len(dashboard_urls),
            "alert_rules": len(service.alert_rules)
        }
    
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
    dashboard_names: Optional[List[str]] = Body(None, description="Specific dashboards to deploy"),
    service = Depends(get_grafana_service_dependency)
):
    """
    Deploy dashboards to Grafana.
    
    Args:
        dashboard_names: Optional list of specific dashboard names to deploy.
                        If not provided, all dashboards will be deployed.
    
    Returns:
        Deployment results for each dashboard.
    """
    try:
        if dashboard_names:
            # Deploy specific dashboards
            results = {}
            available_dashboards = dashboard_generator.get_all_dashboards()
            
            for name in dashboard_names:
                if name not in available_dashboards:
                    results[name] = {
                        "status": "failed",
                        "error": f"Dashboard '{name}' not found"
                    }
                    continue
                
                try:
                    result = await service.update_dashboard(name)
                    results[name] = result
                except Exception as e:
                    results[name] = {
                        "status": "failed",
                        "error": str(e)
                    }
        else:
            # Deploy all dashboards
            results = await service.deploy_all_dashboards()
        
        # Count successful deployments
        successful = len([r for r in results.values() if r.get("status") == "success"])
        total = len(results)
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "deployment_results": results,
            "summary": {
                "total_dashboards": total,
                "successful_deployments": successful,
                "failed_deployments": total - successful
            }
        }
    
    except Exception as e:
        logger.error(f"Error deploying dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.get("/dashboards")
async def list_dashboards():
    """
    List all available dashboard configurations.
    
    Returns information about all dashboard templates including
    their configuration and deployment status.
    """
    try:
        # Get available dashboards
        available_dashboards = dashboard_generator.get_all_dashboards()
        
        # Get deployment status
        service = get_grafana_service()
        deployed_dashboards = {}
        dashboard_urls = {}
        
        if service:
            deployed_dashboards = service.deployed_dashboards
            dashboard_urls = await service.get_dashboard_urls()
        
        # Build dashboard info
        dashboard_info = {}
        for name, config in available_dashboards.items():
            dashboard_config = config["dashboard"]
            
            deployment_info = deployed_dashboards.get(name, {})
            is_deployed = deployment_info.get("status") == "success"
            
            dashboard_info[name] = {
                "title": dashboard_config["title"],
                "uid": dashboard_config["uid"],
                "tags": dashboard_config.get("tags", []),
                "panels_count": len(dashboard_config.get("panels", [])),
                "refresh": dashboard_config.get("refresh", "30s"),
                "is_deployed": is_deployed,
                "deployment_status": deployment_info.get("status", "not_deployed"),
                "dashboard_url": dashboard_urls.get(name, ""),
                "last_updated": deployment_info.get("last_updated")
            }
        
        return {
            "dashboards": dashboard_info,
            "total_count": len(dashboard_info),
            "deployed_count": len([d for d in dashboard_info.values() if d["is_deployed"]]),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error listing dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing dashboards: {str(e)}")


@router.get("/dashboards/{dashboard_name}")
async def get_dashboard_config(dashboard_name: str):
    """
    Get specific dashboard configuration.
    
    Args:
        dashboard_name: Name of the dashboard to retrieve
    
    Returns:
        Complete dashboard configuration in Grafana format.
    """
    try:
        available_dashboards = dashboard_generator.get_all_dashboards()
        
        if dashboard_name not in available_dashboards:
            available_names = list(available_dashboards.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Dashboard '{dashboard_name}' not found. Available: {available_names}"
            )
        
        config = available_dashboards[dashboard_name]
        
        # Add deployment info if available
        service = get_grafana_service()
        if service and dashboard_name in service.deployed_dashboards:
            config["deployment_info"] = service.deployed_dashboards[dashboard_name]
        
        return {
            "dashboard_name": dashboard_name,
            "configuration": config,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard config for {dashboard_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard: {str(e)}")


@router.post("/dashboards/{dashboard_name}/update")
async def update_dashboard(
    dashboard_name: str,
    service = Depends(get_grafana_service_dependency)
):
    """
    Update a specific dashboard in Grafana.
    
    Args:
        dashboard_name: Name of the dashboard to update
    
    Returns:
        Update result with new deployment information.
    """
    try:
        available_dashboards = dashboard_generator.get_all_dashboards()
        
        if dashboard_name not in available_dashboards:
            available_names = list(available_dashboards.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Dashboard '{dashboard_name}' not found. Available: {available_names}"
            )
        
        # Update dashboard
        result = await service.update_dashboard(dashboard_name)
        
        return {
            "status": "updated",
            "dashboard_name": dashboard_name,
            "deployment_result": result,
            "dashboard_url": result.get("url", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dashboard {dashboard_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating dashboard: {str(e)}")


@router.delete("/dashboards/{dashboard_uid}")
async def delete_dashboard(
    dashboard_uid: str,
    service = Depends(get_grafana_service_dependency)
):
    """
    Delete a dashboard from Grafana.
    
    Args:
        dashboard_uid: UID of the dashboard to delete
    
    Returns:
        Deletion result.
    """
    try:
        success = await service.delete_dashboard(dashboard_uid)
        
        if success:
            return {
                "status": "deleted",
                "dashboard_uid": dashboard_uid,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete dashboard")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dashboard {dashboard_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting dashboard: {str(e)}")


@router.get("/dashboards/{dashboard_name}/export")
async def export_dashboard(
    dashboard_name: str,
    service = Depends(get_grafana_service_dependency)
):
    """
    Export dashboard configuration.
    
    Args:
        dashboard_name: Name of the dashboard to export
    
    Returns:
        Dashboard configuration for download or import.
    """
    try:
        available_dashboards = dashboard_generator.get_all_dashboards()
        
        if dashboard_name not in available_dashboards:
            available_names = list(available_dashboards.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Dashboard '{dashboard_name}' not found. Available: {available_names}"
            )
        
        config = available_dashboards[dashboard_name]
        
        # Add export metadata
        export_data = {
            "dashboard_name": dashboard_name,
            "exported_at": datetime.now().isoformat(),
            "configuration": config
        }
        
        # Add deployment info if available
        if dashboard_name in service.deployed_dashboards:
            export_data["deployment_info"] = service.deployed_dashboards[dashboard_name]
        
        return export_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting dashboard {dashboard_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting dashboard: {str(e)}")


@router.post("/dashboards/import")
async def import_dashboard(
    dashboard_config: Dict[str, Any] = Body(..., description="Dashboard configuration to import"),
    service = Depends(get_grafana_service_dependency)
):
    """
    Import and deploy a dashboard configuration.
    
    Args:
        dashboard_config: Complete dashboard configuration in Grafana format
    
    Returns:
        Import and deployment result.
    """
    try:
        # Extract dashboard name from config
        dashboard_title = dashboard_config.get("dashboard", {}).get("title", "Imported Dashboard")
        
        # Deploy the imported dashboard
        result = await service._deploy_single_dashboard(dashboard_title, dashboard_config)
        
        if result.get("status") == "success":
            service.deployed_dashboards[dashboard_title] = result
            
            return {
                "status": "imported",
                "dashboard_name": dashboard_title,
                "deployment_result": result,
                "dashboard_url": result.get("url", ""),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to import dashboard: {result.get('error', 'Unknown error')}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing dashboard: {str(e)}")


@router.get("/alerts")
async def get_alert_rules(service = Depends(get_grafana_service_dependency)):
    """
    Get configured alert rules.
    
    Returns information about all configured alert rules
    for system monitoring.
    """
    try:
        alert_rules = service.alert_rules
        
        # Format alert rules for response
        formatted_rules = []
        for rule in alert_rules:
            formatted_rules.append({
                "uid": rule.get("uid"),
                "title": rule.get("title"),
                "condition": rule.get("condition"),
                "for_duration": rule.get("for"),
                "severity": rule.get("labels", {}).get("severity"),
                "component": rule.get("labels", {}).get("component"),
                "summary": rule.get("annotations", {}).get("summary"),
                "description": rule.get("annotations", {}).get("description")
            })
        
        return {
            "alert_rules": formatted_rules,
            "total_count": len(formatted_rules),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting alert rules: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting alert rules: {str(e)}")


@router.get("/info")
async def get_grafana_info(service = Depends(get_grafana_service_dependency)):
    """
    Get Grafana instance information.
    
    Returns detailed information about the connected Grafana instance
    including version, organization, and configuration.
    """
    try:
        grafana_info = await service.get_grafana_info()
        
        return {
            "grafana_info": grafana_info,
            "configuration": {
                "url": service.config.url,
                "folder_name": service.config.folder_name,
                "prometheus_url": service.config.prometheus_url,
                "auto_deploy_dashboards": service.config.auto_deploy_dashboards
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting Grafana info: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Grafana info: {str(e)}")


@router.post("/cleanup")
async def cleanup_grafana():
    """
    Cleanup Grafana integration.
    
    Closes connections and cleans up resources used by
    the Grafana integration service.
    """
    try:
        await cleanup_grafana_integration()
        
        return {
            "status": "cleaned_up",
            "timestamp": datetime.now().isoformat(),
            "message": "Grafana integration cleaned up successfully"
        }
    
    except Exception as e:
        logger.error(f"Error cleaning up Grafana integration: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/health")
async def get_grafana_health():
    """
    Get Grafana service health status.
    
    Returns health information for the Grafana integration
    including connection status and service availability.
    """
    try:
        service = get_grafana_service()
        
        if not service:
            return JSONResponse(
                content={
                    "status": "not_initialized",
                    "message": "Grafana service not initialized",
                    "timestamp": datetime.now().isoformat()
                },
                status_code=503
            )
        
        # Test connection
        try:
            await service._test_connection()
            connection_status = "healthy"
        except Exception as e:
            connection_status = f"unhealthy: {str(e)}"
        
        # Get basic info
        grafana_info = await service.get_grafana_info()
        dashboard_urls = await service.get_dashboard_urls()
        
        health_status = {
            "status": "healthy" if connection_status == "healthy" else "unhealthy",
            "connection_status": connection_status,
            "grafana_url": service.config.url,
            "deployed_dashboards": len(dashboard_urls),
            "alert_rules": len(service.alert_rules),
            "folder_id": service.folder_id,
            "datasource_uid": service.datasource_uid,
            "timestamp": datetime.now().isoformat()
        }
        
        status_code = 200 if connection_status == "healthy" else 503
        
        return JSONResponse(content=health_status, status_code=status_code)
    
    except Exception as e:
        logger.error(f"Grafana health check failed: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )