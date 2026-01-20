#!/usr/bin/env python3
"""
Demo script for Quality Billing Monitoring Dashboard System.

Demonstrates the Prometheus + Grafana integration including:
- Metrics collection and export
- Dashboard deployment and management
- Real-time monitoring capabilities
- Alert rule configuration
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import quality billing monitoring components
try:
    from src.quality_billing.prometheus_metrics import (
        quality_billing_metrics,
        record_work_session,
        record_billing_event,
        record_performance_evaluation
    )
    from src.quality_billing.prometheus_integration import (
        prometheus_service,
        start_prometheus_service,
        stop_prometheus_service
    )
    from src.quality_billing.system_metrics_collector import (
        system_metrics_collector,
        start_system_metrics_collection,
        stop_system_metrics_collection
    )
    from src.quality_billing.grafana_integration import (
        initialize_grafana_integration,
        GrafanaIntegrationService
    )
    from src.quality_billing.dashboard_templates import dashboard_generator
    
    logger.info("Successfully imported quality billing monitoring components")
    
except ImportError as e:
    logger.error(f"Failed to import monitoring components: {e}")
    logger.info("Please ensure the quality billing monitoring system is properly installed")
    exit(1)


class MonitoringDashboardDemo:
    """
    Demonstrates the Quality Billing Monitoring Dashboard System.
    
    Shows how to:
    - Collect and export Prometheus metrics
    - Deploy Grafana dashboards
    - Monitor system performance
    - Configure alerts and notifications
    """

    def __init__(self):
        self.running = False
        self.demo_users = ["user_001", "user_002", "user_003", "user_004", "user_005"]
        self.demo_projects = ["project_alpha", "project_beta", "project_gamma"]
        self.quality_levels = ["excellent", "good", "fair", "poor"]
        self.task_types = ["annotation", "review", "validation", "correction"]
        
        # Grafana service (will be initialized if configured)
        self.grafana_service: GrafanaIntegrationService = None

    async def run_demo(self):
        """Run the complete monitoring dashboard demo."""
        logger.info("🚀 Starting Quality Billing Monitoring Dashboard Demo")
        
        try:
            # Step 1: Initialize monitoring services
            await self._initialize_services()
            
            # Step 2: Start metrics collection
            await self._start_metrics_collection()
            
            # Step 3: Generate sample data
            await self._generate_sample_metrics()
            
            # Step 4: Setup Grafana integration (if configured)
            await self._setup_grafana_integration()
            
            # Step 5: Deploy dashboards
            await self._deploy_dashboards()
            
            # Step 6: Demonstrate real-time monitoring
            await self._demonstrate_realtime_monitoring()
            
            # Step 7: Show metrics export
            await self._demonstrate_metrics_export()
            
            # Step 8: Display summary
            await self._display_demo_summary()
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            raise
        finally:
            await self._cleanup_services()

    async def _initialize_services(self):
        """Initialize monitoring services."""
        logger.info("📊 Initializing monitoring services...")
        
        # Initialize Prometheus service
        await start_prometheus_service({
            "metrics_port": 9091,  # Use different port to avoid conflicts
            "scrape_interval": "10s"
        })
        
        # Initialize system metrics collector
        await start_system_metrics_collection()
        
        logger.info("✅ Monitoring services initialized")

    async def _start_metrics_collection(self):
        """Start metrics collection."""
        logger.info("📈 Starting metrics collection...")
        
        self.running = True
        
        # Start background task for continuous metrics generation
        asyncio.create_task(self._continuous_metrics_generation())
        
        logger.info("✅ Metrics collection started")

    async def _generate_sample_metrics(self):
        """Generate sample metrics data."""
        logger.info("🎲 Generating sample metrics data...")
        
        # Generate work session metrics
        for _ in range(20):
            user_id = random.choice(self.demo_users)
            project_id = random.choice(self.demo_projects)
            
            duration = random.uniform(1800, 7200)  # 30 minutes to 2 hours
            effective_duration = duration * random.uniform(0.7, 0.95)  # 70-95% efficiency
            quality_score = random.uniform(0.6, 0.98)
            
            record_work_session(user_id, project_id, duration, effective_duration, quality_score)
        
        # Generate billing events
        for _ in range(15):
            user_id = random.choice(self.demo_users)
            project_id = random.choice(self.demo_projects)
            quality_level = random.choice(self.quality_levels)
            task_type = random.choice(self.task_types)
            
            # Amount based on quality level
            base_amount = 5000  # $50.00 in cents
            quality_multiplier = {
                "excellent": 1.5,
                "good": 1.2,
                "fair": 1.0,
                "poor": 0.8
            }
            amount = int(base_amount * quality_multiplier[quality_level])
            
            record_billing_event(user_id, project_id, amount, quality_level, task_type)
        
        # Generate performance evaluations
        for user_id in self.demo_users:
            performance_score = random.uniform(0.6, 0.95)
            tasks_completed = random.randint(5, 25)
            avg_completion_time = random.uniform(900, 3600)  # 15 minutes to 1 hour
            
            record_performance_evaluation(user_id, performance_score, tasks_completed, avg_completion_time)
        
        # Update system metrics
        quality_billing_metrics.update_active_sessions(random.randint(8, 15))
        quality_billing_metrics.update_active_users(random.randint(5, 12))
        
        logger.info("✅ Sample metrics data generated")

    async def _setup_grafana_integration(self):
        """Setup Grafana integration if configured."""
        logger.info("🎨 Setting up Grafana integration...")
        
        # Check if Grafana is configured
        grafana_url = "http://localhost:3000"  # Default Grafana URL
        api_key = "demo_api_key"  # This would be a real API key in production
        
        try:
            # Initialize Grafana service (this would fail without real credentials)
            # self.grafana_service = initialize_grafana_integration(grafana_url, api_key)
            # await self.grafana_service.initialize()
            
            logger.info("ℹ️  Grafana integration would be configured here with real credentials")
            logger.info(f"   Grafana URL: {grafana_url}")
            logger.info("   Dashboard templates are ready for deployment")
            
        except Exception as e:
            logger.warning(f"Grafana not configured (expected in demo): {e}")
            logger.info("📝 Dashboard templates are available for manual deployment")

    async def _deploy_dashboards(self):
        """Deploy or show dashboard configurations."""
        logger.info("📊 Preparing dashboard deployments...")
        
        # Get all dashboard templates
        templates = dashboard_generator.get_all_dashboard_templates()
        
        logger.info(f"📋 Available dashboard templates ({len(templates)}):")
        for name, config in templates.items():
            dashboard_config = config["dashboard"]
            logger.info(f"   • {dashboard_config['title']} (UID: {dashboard_config['uid']})")
            logger.info(f"     - Panels: {len(dashboard_config.get('panels', []))}")
            logger.info(f"     - Tags: {', '.join(dashboard_config.get('tags', []))}")
        
        if self.grafana_service:
            try:
                deployment_results = await self.grafana_service.deploy_dashboards()
                logger.info("✅ Dashboards deployed to Grafana:")
                for name, result in deployment_results.items():
                    if result.get("status") == "deployed":
                        logger.info(f"   • {name}: {result.get('url')}")
                    else:
                        logger.warning(f"   • {name}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Failed to deploy dashboards: {e}")
        else:
            logger.info("📝 Dashboard templates ready for manual deployment to Grafana")

    async def _demonstrate_realtime_monitoring(self):
        """Demonstrate real-time monitoring capabilities."""
        logger.info("⏱️  Demonstrating real-time monitoring (30 seconds)...")
        
        start_time = time.time()
        while time.time() - start_time < 30:
            # Simulate real-time activity
            user_id = random.choice(self.demo_users)
            
            # Random API request
            endpoint = random.choice(["/api/work-time", "/api/billing", "/api/quality"])
            method = "GET"
            status_code = random.choices([200, 400, 500], weights=[0.9, 0.08, 0.02])[0]
            response_time = random.uniform(0.05, 2.0)
            
            quality_billing_metrics.record_api_request(endpoint, method, status_code, response_time)
            
            # Random quality assessment
            if random.random() < 0.3:  # 30% chance
                quality_score = random.uniform(0.7, 0.98)
                quality_billing_metrics.set_gauge("quality_billing_quality_score", quality_score, {"user_id": user_id})
            
            # Update active users count
            active_users = random.randint(8, 15)
            quality_billing_metrics.update_active_users(active_users)
            
            await asyncio.sleep(1)
        
        logger.info("✅ Real-time monitoring demonstration completed")

    async def _demonstrate_metrics_export(self):
        """Demonstrate Prometheus metrics export."""
        logger.info("📤 Demonstrating Prometheus metrics export...")
        
        # Get metrics summary
        summary = quality_billing_metrics.get_metric_summary(hours=1)
        
        logger.info("📊 Metrics Summary (Last Hour):")
        logger.info(f"   Work Time:")
        logger.info(f"     - Total Hours: {summary['work_time']['total_seconds'] / 3600:.2f}")
        logger.info(f"     - Effective Hours: {summary['work_time']['effective_seconds'] / 3600:.2f}")
        logger.info(f"     - Efficiency: {summary['work_time']['efficiency']:.2%}")
        
        logger.info(f"   Quality:")
        logger.info(f"     - Total Assessments: {summary['quality']['total_assessments']}")
        
        logger.info(f"   Billing:")
        logger.info(f"     - Total Invoices: {summary['billing']['total_invoices']}")
        logger.info(f"     - Total Amount: ${summary['billing']['total_amount_cents'] / 100:.2f}")
        
        logger.info(f"   Performance:")
        logger.info(f"     - Tasks Completed: {summary['performance']['tasks_completed']}")
        
        logger.info(f"   System:")
        logger.info(f"     - API Requests: {summary['system']['api_requests']}")
        logger.info(f"     - Active Sessions: {summary['system']['active_sessions']}")
        
        # Show Prometheus export format (first 10 lines)
        prometheus_export = quality_billing_metrics.export_prometheus()
        lines = prometheus_export.split('\n')[:10]
        
        logger.info("📋 Prometheus Export Format (sample):")
        for line in lines:
            if line.strip():
                logger.info(f"   {line}")
        
        logger.info(f"   ... ({len(prometheus_export.split())} total lines)")
        logger.info(f"📡 Metrics available at: http://localhost:9091/metrics")

    async def _continuous_metrics_generation(self):
        """Generate metrics continuously in the background."""
        while self.running:
            try:
                # Simulate ongoing work activity
                if random.random() < 0.1:  # 10% chance per second
                    user_id = random.choice(self.demo_users)
                    project_id = random.choice(self.demo_projects)
                    
                    # Short work session
                    duration = random.uniform(300, 1800)  # 5-30 minutes
                    effective_duration = duration * random.uniform(0.8, 0.95)
                    quality_score = random.uniform(0.75, 0.95)
                    
                    record_work_session(user_id, project_id, duration, effective_duration, quality_score)
                
                # Simulate API requests
                if random.random() < 0.5:  # 50% chance per second
                    endpoint = random.choice(["/api/metrics", "/api/health", "/api/dashboards"])
                    response_time = random.uniform(0.01, 0.5)
                    status_code = random.choices([200, 404, 500], weights=[0.95, 0.04, 0.01])[0]
                    
                    quality_billing_metrics.record_api_request(endpoint, "GET", status_code, response_time)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in continuous metrics generation: {e}")
                await asyncio.sleep(5)

    async def _display_demo_summary(self):
        """Display demo summary and next steps."""
        logger.info("🎉 Quality Billing Monitoring Dashboard Demo Completed!")
        logger.info("")
        logger.info("📋 What was demonstrated:")
        logger.info("   ✅ Prometheus metrics collection and export")
        logger.info("   ✅ System metrics monitoring")
        logger.info("   ✅ Business metrics tracking (work time, quality, billing)")
        logger.info("   ✅ Real-time metrics generation")
        logger.info("   ✅ Dashboard template configuration")
        logger.info("   ✅ API endpoints for metrics access")
        logger.info("")
        logger.info("🔗 Available endpoints:")
        logger.info("   • Prometheus metrics: http://localhost:9091/metrics")
        logger.info("   • Health check: http://localhost:9091/health")
        logger.info("   • Configuration: http://localhost:9091/config")
        logger.info("   • Service targets: http://localhost:9091/targets")
        logger.info("")
        logger.info("📊 Dashboard templates ready for Grafana:")
        templates = dashboard_generator.get_all_dashboard_templates()
        for name, config in templates.items():
            title = config["dashboard"]["title"]
            uid = config["dashboard"]["uid"]
            logger.info(f"   • {title} (UID: {uid})")
        logger.info("")
        logger.info("🚀 Next steps:")
        logger.info("   1. Configure Grafana with API credentials")
        logger.info("   2. Deploy dashboards using the API endpoints")
        logger.info("   3. Set up Prometheus to scrape metrics")
        logger.info("   4. Configure alert rules and notifications")
        logger.info("   5. Customize dashboards for your specific needs")

    async def _cleanup_services(self):
        """Cleanup monitoring services."""
        logger.info("🧹 Cleaning up services...")
        
        self.running = False
        
        try:
            await stop_system_metrics_collection()
            await stop_prometheus_service()
            
            if self.grafana_service:
                await self.grafana_service.cleanup()
            
            logger.info("✅ Services cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main demo function."""
    demo = MonitoringDashboardDemo()
    
    try:
        await demo.run_demo()
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    print("=" * 80)
    print("Quality Billing Monitoring Dashboard System Demo")
    print("=" * 80)
    print()
    print("This demo showcases the Prometheus + Grafana integration for")
    print("the Quality Billing Loop system, including:")
    print("• Metrics collection and export")
    print("• Dashboard templates and deployment")
    print("• Real-time monitoring capabilities")
    print("• System performance tracking")
    print()
    print("Press Ctrl+C to stop the demo at any time.")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo stopped by user.")
    except Exception as e:
        print(f"\nDemo failed: {e}")
        exit(1)