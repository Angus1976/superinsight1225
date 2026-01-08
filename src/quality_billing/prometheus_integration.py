"""
Prometheus Integration Service for Quality Billing System.

Provides HTTP endpoint for Prometheus to scrape metrics and
manages Prometheus server configuration.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import yaml
from pathlib import Path
from aiohttp import web, ClientSession
# import aiofiles  # Not needed for this implementation

from .prometheus_metrics import quality_billing_metrics, PrometheusMetricsCollector

logger = logging.getLogger(__name__)


class PrometheusIntegrationService:
    """
    Manages Prometheus integration for the quality billing system.
    
    Provides:
    - HTTP metrics endpoint for Prometheus scraping
    - Prometheus configuration management
    - Health checks and service discovery
    - Custom metric registration
    """

    def __init__(self, metrics_collector: Optional[PrometheusMetricsCollector] = None):
        self.metrics_collector = metrics_collector or quality_billing_metrics
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Configuration
        self.config = {
            "metrics_port": 9090,
            "metrics_path": "/metrics",
            "health_path": "/health",
            "prometheus_config_path": "./prometheus.yml",  # Use local path for demo
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        }
        
        # Service discovery
        self.service_targets: List[Dict[str, Any]] = []
        
        # Alert rules
        self.alert_rules: List[Dict[str, Any]] = []

    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Prometheus integration service."""
        if config:
            self.config.update(config)
        
        logger.info("Initializing Prometheus integration service")
        
        # Create web application
        self.app = web.Application()
        
        # Add routes
        self.app.router.add_get(self.config["metrics_path"], self._metrics_handler)
        self.app.router.add_get(self.config["health_path"], self._health_handler)
        self.app.router.add_get("/config", self._config_handler)
        self.app.router.add_get("/targets", self._targets_handler)
        self.app.router.add_post("/reload", self._reload_handler)
        
        # Add middleware
        self.app.middlewares.append(self._logging_middleware)
        self.app.middlewares.append(self._cors_middleware)
        
        logger.info("Prometheus integration service initialized")

    async def start(self):
        """Start the Prometheus metrics server."""
        if not self.app:
            await self.initialize()
        
        logger.info(f"Starting Prometheus metrics server on port {self.config['metrics_port']}")
        
        # Create runner and site
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner,
            host="0.0.0.0",
            port=self.config["metrics_port"]
        )
        await self.site.start()
        
        logger.info(f"Prometheus metrics server started on http://0.0.0.0:{self.config['metrics_port']}")

    async def stop(self):
        """Stop the Prometheus metrics server."""
        if self.site:
            await self.site.stop()
            self.site = None
        
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
        
        logger.info("Prometheus metrics server stopped")

    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """Handle metrics endpoint requests."""
        try:
            # Export metrics in Prometheus format
            metrics_data = self.metrics_collector.export_prometheus()
            
            # Update request metrics
            self.metrics_collector.inc_counter(
                "quality_billing_api_requests_total",
                1.0,
                {"endpoint": "/metrics", "method": "GET", "status_code": "200"}
            )
            
            return web.Response(
                text=metrics_data,
                content_type="text/plain; version=0.0.4; charset=utf-8"
            )
        
        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
            
            self.metrics_collector.inc_counter(
                "quality_billing_api_requests_total",
                1.0,
                {"endpoint": "/metrics", "method": "GET", "status_code": "500"}
            )
            
            return web.Response(
                text=f"Error: {str(e)}",
                status=500,
                content_type="text/plain"
            )

    async def _health_handler(self, request: web.Request) -> web.Response:
        """Handle health check requests."""
        try:
            # Get system health status
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "metrics_collector": "active",
                "total_metrics": len(self.metrics_collector.get_all_metrics()),
                "uptime_seconds": self._get_uptime_seconds()
            }
            
            # Check if metrics are being updated
            recent_activity = self._check_recent_activity()
            if not recent_activity:
                health_status["status"] = "degraded"
                health_status["warning"] = "No recent metric updates detected"
            
            status_code = 200 if health_status["status"] == "healthy" else 503
            
            self.metrics_collector.inc_counter(
                "quality_billing_api_requests_total",
                1.0,
                {"endpoint": "/health", "method": "GET", "status_code": str(status_code)}
            )
            
            return web.json_response(health_status, status=status_code)
        
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return web.json_response(
                {"status": "error", "error": str(e)},
                status=500
            )

    async def _config_handler(self, request: web.Request) -> web.Response:
        """Handle configuration requests."""
        try:
            config_data = {
                "prometheus_config": await self._generate_prometheus_config(),
                "alert_rules": self.alert_rules,
                "service_targets": self.service_targets,
                "scrape_configs": await self._get_scrape_configs()
            }
            
            return web.json_response(config_data)
        
        except Exception as e:
            logger.error(f"Error serving config: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _targets_handler(self, request: web.Request) -> web.Response:
        """Handle service discovery targets."""
        try:
            targets = {
                "quality_billing_targets": [
                    {
                        "targets": [f"localhost:{self.config['metrics_port']}"],
                        "labels": {
                            "job": "quality-billing",
                            "service": "quality-billing-loop",
                            "environment": "production"
                        }
                    }
                ] + self.service_targets
            }
            
            return web.json_response(targets)
        
        except Exception as e:
            logger.error(f"Error serving targets: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _reload_handler(self, request: web.Request) -> web.Response:
        """Handle Prometheus reload requests."""
        try:
            # Reload Prometheus configuration
            success = await self._reload_prometheus_config()
            
            if success:
                return web.json_response({"status": "reloaded", "timestamp": datetime.now().isoformat()})
            else:
                return web.json_response({"status": "failed", "error": "Reload failed"}, status=500)
        
        except Exception as e:
            logger.error(f"Error reloading config: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _logging_middleware(self, request: web.Request, handler):
        """Logging middleware for requests."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await handler(request)
            
            # Record response time
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics_collector.observe_histogram(
                "quality_billing_api_response_time_seconds",
                response_time,
                {"endpoint": request.path, "method": request.method}
            )
            
            return response
        
        except Exception as e:
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics_collector.observe_histogram(
                "quality_billing_api_response_time_seconds",
                response_time,
                {"endpoint": request.path, "method": request.method}
            )
            raise

    async def _cors_middleware(self, request: web.Request, handler):
        """CORS middleware for cross-origin requests."""
        response = await handler(request)
        
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        
        return response

    def _get_uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        # This would typically track actual start time
        return 3600.0  # Placeholder: 1 hour

    def _check_recent_activity(self) -> bool:
        """Check if there has been recent metric activity."""
        # Check if any metrics have been updated recently
        all_metrics = self.metrics_collector.get_all_metrics()
        
        # Simple check: if we have any metrics, assume activity
        return (
            len(all_metrics.get("counters", {})) > 0 or
            len(all_metrics.get("gauges", {})) > 0 or
            len(all_metrics.get("histograms", {})) > 0
        )

    async def _generate_prometheus_config(self) -> Dict[str, Any]:
        """Generate Prometheus configuration."""
        config = {
            "global": {
                "scrape_interval": self.config["scrape_interval"],
                "evaluation_interval": self.config["evaluation_interval"]
            },
            "rule_files": [
                "/etc/prometheus/rules/*.yml"
            ],
            "scrape_configs": await self._get_scrape_configs(),
            "alerting": {
                "alertmanagers": [
                    {
                        "static_configs": [
                            {
                                "targets": ["alertmanager:9093"]
                            }
                        ]
                    }
                ]
            }
        }
        
        return config

    async def _get_scrape_configs(self) -> List[Dict[str, Any]]:
        """Get Prometheus scrape configurations."""
        scrape_configs = [
            {
                "job_name": "quality-billing-metrics",
                "static_configs": [
                    {
                        "targets": [f"localhost:{self.config['metrics_port']}"],
                        "labels": {
                            "service": "quality-billing",
                            "component": "metrics"
                        }
                    }
                ],
                "metrics_path": self.config["metrics_path"],
                "scrape_interval": "15s"
            },
            {
                "job_name": "quality-billing-system",
                "static_configs": [
                    {
                        "targets": ["localhost:8000"],  # Main application
                        "labels": {
                            "service": "quality-billing",
                            "component": "application"
                        }
                    }
                ],
                "metrics_path": "/api/metrics",
                "scrape_interval": "30s"
            }
        ]
        
        return scrape_configs

    async def _reload_prometheus_config(self) -> bool:
        """Reload Prometheus configuration."""
        try:
            # Write new configuration
            config = await self._generate_prometheus_config()
            config_path = Path(self.config["prometheus_config_path"])
            
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write YAML configuration
            with open(config_path, 'w') as f:
                f.write(yaml.dump(config, default_flow_style=False))
            
            # Send reload signal to Prometheus (if running)
            try:
                async with ClientSession() as session:
                    async with session.post("http://localhost:9090/-/reload") as response:
                        return response.status == 200
            except Exception as e:
                logger.warning(f"Could not reload Prometheus: {e}")
                return True  # Config written successfully even if reload failed
        
        except Exception as e:
            logger.error(f"Failed to reload Prometheus config: {e}")
            return False

    def add_service_target(
        self,
        target: str,
        job_name: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """Add a service target for monitoring."""
        target_config = {
            "targets": [target],
            "labels": {
                "job": job_name,
                **(labels or {})
            }
        }
        
        self.service_targets.append(target_config)
        logger.info(f"Added service target: {target} (job: {job_name})")

    def add_alert_rule(
        self,
        name: str,
        expression: str,
        duration: str = "5m",
        severity: str = "warning",
        summary: str = "",
        description: str = ""
    ):
        """Add a Prometheus alert rule."""
        rule = {
            "alert": name,
            "expr": expression,
            "for": duration,
            "labels": {
                "severity": severity
            },
            "annotations": {
                "summary": summary or f"Alert: {name}",
                "description": description or f"Alert rule {name} triggered"
            }
        }
        
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {name}")

    async def write_alert_rules(self, rules_path: str = "./prometheus_rules.yml"):
        """Write alert rules to file."""
        if not self.alert_rules:
            return
        
        rules_config = {
            "groups": [
                {
                    "name": "quality_billing_alerts",
                    "rules": self.alert_rules
                }
            ]
        }
        
        rules_file = Path(rules_path)
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(rules_file, 'w') as f:
            f.write(yaml.dump(rules_config, default_flow_style=False))
        
        logger.info(f"Alert rules written to {rules_path}")

    def setup_default_alerts(self):
        """Setup default alert rules for quality billing system."""
        
        # High error rate alert
        self.add_alert_rule(
            name="QualityBillingHighErrorRate",
            expression="rate(quality_billing_api_requests_total{status_code=~\"5..\"}[5m]) > 0.1",
            duration="2m",
            severity="critical",
            summary="High error rate in Quality Billing API",
            description="Error rate is above 10% for the last 5 minutes"
        )
        
        # Low quality score alert
        self.add_alert_rule(
            name="QualityBillingLowQualityScore",
            expression="avg(quality_billing_quality_score) < 0.7",
            duration="10m",
            severity="warning",
            summary="Low average quality score",
            description="Average quality score is below 70% for the last 10 minutes"
        )
        
        # High response time alert
        self.add_alert_rule(
            name="QualityBillingHighResponseTime",
            expression="histogram_quantile(0.95, rate(quality_billing_api_response_time_seconds_bucket[5m])) > 2.0",
            duration="5m",
            severity="warning",
            summary="High API response time",
            description="95th percentile response time is above 2 seconds"
        )
        
        # No active users alert
        self.add_alert_rule(
            name="QualityBillingNoActiveUsers",
            expression="quality_billing_current_active_users == 0",
            duration="30m",
            severity="warning",
            summary="No active users detected",
            description="No active users for the last 30 minutes"
        )
        
        # Billing system down alert
        self.add_alert_rule(
            name="QualityBillingSystemDown",
            expression="up{job=\"quality-billing-metrics\"} == 0",
            duration="1m",
            severity="critical",
            summary="Quality Billing system is down",
            description="Quality Billing metrics endpoint is not responding"
        )

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics for monitoring."""
        return self.metrics_collector.get_metric_summary()


# Global Prometheus integration service
prometheus_service = PrometheusIntegrationService()


# Convenience functions
async def start_prometheus_service(config: Optional[Dict[str, Any]] = None):
    """Start the Prometheus integration service."""
    await prometheus_service.initialize(config)
    await prometheus_service.start()
    
    # Setup default alerts
    prometheus_service.setup_default_alerts()
    await prometheus_service.write_alert_rules()


async def stop_prometheus_service():
    """Stop the Prometheus integration service."""
    await prometheus_service.stop()


def get_prometheus_service() -> PrometheusIntegrationService:
    """Get the global Prometheus service instance."""
    return prometheus_service