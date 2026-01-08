#!/usr/bin/env python3
"""
SuperInsight Multi-Tenant Monitoring Discovery Service

This service provides dynamic service discovery for Prometheus to monitor
multi-tenant metrics with proper isolation and security.

Features:
- Dynamic tenant discovery
- Tenant-specific metric endpoints
- Security and access control
- Performance monitoring per tenant
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, generate_latest
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TenantTarget:
    """Represents a tenant monitoring target for Prometheus."""
    targets: List[str]
    labels: Dict[str, str]


@dataclass
class TenantMetrics:
    """Tenant-specific metrics."""
    tenant_id: str
    tenant_name: str
    resource_usage_percent: float
    active_users: int
    api_requests_per_minute: float
    error_rate_percent: float
    storage_usage_bytes: int
    last_activity: datetime


class TenantDiscoveryService:
    """
    Multi-tenant monitoring discovery service.
    
    Provides dynamic service discovery for Prometheus to monitor
    tenant-specific metrics with proper isolation.
    """
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://localhost/superinsight")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.tenant_discovery_requests = Counter(
            'tenant_discovery_requests_total',
            'Total tenant discovery requests',
            ['endpoint', 'status'],
            registry=self.registry
        )
        self.tenant_metrics_collection_time = Histogram(
            'tenant_metrics_collection_seconds',
            'Time spent collecting tenant metrics',
            registry=self.registry
        )
        self.active_tenants_gauge = Gauge(
            'active_tenants_total',
            'Total number of active tenants',
            registry=self.registry
        )
        
        # Database connection
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        
        # Cache
        self.tenant_cache: Dict[str, TenantMetrics] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update: Optional[datetime] = None

    async def startup(self):
        """Initialize the service."""
        logger.info("Starting Tenant Discovery Service...")
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
        
        # Test database connection
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
        
        # Start background tasks
        asyncio.create_task(self.update_tenant_cache_periodically())
        
        logger.info("Tenant Discovery Service started successfully")

    async def shutdown(self):
        """Cleanup resources."""
        logger.info("Shutting down Tenant Discovery Service...")
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Tenant Discovery Service stopped")

    def get_db(self) -> Session:
        """Get database session."""
        db = self.SessionLocal()
        try:
            return db
        finally:
            db.close()

    async def get_active_tenants(self) -> List[Dict[str, Any]]:
        """Get list of active tenants from database."""
        query = """
        SELECT DISTINCT 
            t.id as tenant_id,
            t.name as tenant_name,
            t.created_at,
            t.is_active,
            COUNT(DISTINCT u.id) as user_count,
            COUNT(DISTINCT p.id) as project_count
        FROM tenants t
        LEFT JOIN users u ON u.tenant_id = t.id AND u.is_active = true
        LEFT JOIN projects p ON p.tenant_id = t.id AND p.is_active = true
        WHERE t.is_active = true
        GROUP BY t.id, t.name, t.created_at, t.is_active
        ORDER BY t.name
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row._mapping) for row in result]

    async def get_tenant_metrics(self, tenant_id: str) -> Optional[TenantMetrics]:
        """Get comprehensive metrics for a specific tenant."""
        # Check cache first
        if (self.last_cache_update and 
            datetime.now() - self.last_cache_update < timedelta(seconds=self.cache_ttl) and
            tenant_id in self.tenant_cache):
            return self.tenant_cache[tenant_id]
        
        with self.tenant_metrics_collection_time.time():
            try:
                # Get tenant basic info
                tenant_query = """
                SELECT id, name, created_at, is_active
                FROM tenants 
                WHERE id = :tenant_id AND is_active = true
                """
                
                # Get resource usage metrics
                resource_query = """
                SELECT 
                    COALESCE(AVG(cpu_usage_percent), 0) as avg_cpu,
                    COALESCE(AVG(memory_usage_percent), 0) as avg_memory,
                    COALESCE(SUM(storage_usage_bytes), 0) as total_storage
                FROM tenant_resource_usage 
                WHERE tenant_id = :tenant_id 
                AND created_at > NOW() - INTERVAL '1 hour'
                """
                
                # Get activity metrics
                activity_query = """
                SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_requests,
                    AVG(CASE WHEN status_code >= 400 THEN 1.0 ELSE 0.0 END) as error_rate,
                    MAX(created_at) as last_activity
                FROM api_requests 
                WHERE tenant_id = :tenant_id 
                AND created_at > NOW() - INTERVAL '1 hour'
                """
                
                with self.engine.connect() as conn:
                    # Execute queries
                    tenant_result = conn.execute(text(tenant_query), {"tenant_id": tenant_id}).fetchone()
                    if not tenant_result:
                        return None
                    
                    resource_result = conn.execute(text(resource_query), {"tenant_id": tenant_id}).fetchone()
                    activity_result = conn.execute(text(activity_query), {"tenant_id": tenant_id}).fetchone()
                    
                    # Calculate resource usage percentage
                    resource_usage = max(
                        resource_result.avg_cpu if resource_result.avg_cpu else 0,
                        resource_result.avg_memory if resource_result.avg_memory else 0
                    )
                    
                    # Calculate API requests per minute
                    total_requests = activity_result.total_requests if activity_result.total_requests else 0
                    api_requests_per_minute = total_requests / 60.0  # Last hour average
                    
                    # Create metrics object
                    metrics = TenantMetrics(
                        tenant_id=tenant_id,
                        tenant_name=tenant_result.name,
                        resource_usage_percent=resource_usage,
                        active_users=activity_result.active_users if activity_result.active_users else 0,
                        api_requests_per_minute=api_requests_per_minute,
                        error_rate_percent=(activity_result.error_rate * 100) if activity_result.error_rate else 0,
                        storage_usage_bytes=resource_result.total_storage if resource_result.total_storage else 0,
                        last_activity=activity_result.last_activity or datetime.now()
                    )
                    
                    # Cache the result
                    self.tenant_cache[tenant_id] = metrics
                    
                    return metrics
                    
            except Exception as e:
                logger.error(f"Error getting metrics for tenant {tenant_id}: {e}")
                return None

    async def update_tenant_cache_periodically(self):
        """Background task to update tenant cache periodically."""
        while True:
            try:
                logger.info("Updating tenant cache...")
                
                tenants = await self.get_active_tenants()
                self.active_tenants_gauge.set(len(tenants))
                
                # Update cache for each tenant
                for tenant in tenants:
                    tenant_id = tenant['tenant_id']
                    await self.get_tenant_metrics(tenant_id)
                
                self.last_cache_update = datetime.now()
                logger.info(f"Updated cache for {len(tenants)} tenants")
                
                # Store in Redis if available
                if self.redis_client:
                    try:
                        cache_data = {
                            tenant_id: asdict(metrics) 
                            for tenant_id, metrics in self.tenant_cache.items()
                        }
                        await self.redis_client.setex(
                            f"tenant_cache:{self.environment}",
                            self.cache_ttl,
                            json.dumps(cache_data, default=str)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store cache in Redis: {e}")
                
            except Exception as e:
                logger.error(f"Error updating tenant cache: {e}")
            
            # Wait before next update
            await asyncio.sleep(self.cache_ttl)

    async def generate_prometheus_targets(self) -> List[TenantTarget]:
        """Generate Prometheus service discovery targets for all tenants."""
        targets = []
        
        try:
            tenants = await self.get_active_tenants()
            
            for tenant in tenants:
                tenant_id = tenant['tenant_id']
                tenant_name = tenant['tenant_name']
                
                # Create target for tenant-specific metrics endpoint
                target = TenantTarget(
                    targets=[f"localhost:8000"],  # Main API server
                    labels={
                        "__meta_tenant_id": tenant_id,
                        "__meta_tenant_name": tenant_name,
                        "__meta_environment": self.environment,
                        "__meta_service": "tenant-metrics",
                        "__metrics_path__": f"/api/v1/metrics/tenant/{tenant_id}",
                        "tenant_id": tenant_id,
                        "tenant_name": tenant_name,
                        "environment": self.environment
                    }
                )
                targets.append(target)
            
            logger.info(f"Generated {len(targets)} Prometheus targets")
            
        except Exception as e:
            logger.error(f"Error generating Prometheus targets: {e}")
        
        return targets


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await discovery_service.startup()
    yield
    # Shutdown
    await discovery_service.shutdown()


# Initialize service
discovery_service = TenantDiscoveryService()

# Create FastAPI app
app = FastAPI(
    title="SuperInsight Tenant Discovery Service",
    description="Multi-tenant monitoring discovery for Prometheus",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    discovery_service.tenant_discovery_requests.labels(endpoint="health", status="success").inc()
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/v1/discovery/tenants")
async def discover_tenants():
    """
    Prometheus service discovery endpoint.
    Returns tenant targets in Prometheus HTTP SD format.
    """
    try:
        targets = await discovery_service.generate_prometheus_targets()
        
        # Convert to Prometheus HTTP SD format
        prometheus_targets = [
            {
                "targets": target.targets,
                "labels": target.labels
            }
            for target in targets
        ]
        
        discovery_service.tenant_discovery_requests.labels(endpoint="discovery", status="success").inc()
        
        return prometheus_targets
        
    except Exception as e:
        logger.error(f"Error in tenant discovery: {e}")
        discovery_service.tenant_discovery_requests.labels(endpoint="discovery", status="error").inc()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/tenants")
async def list_tenants():
    """List all active tenants with basic information."""
    try:
        tenants = await discovery_service.get_active_tenants()
        discovery_service.tenant_discovery_requests.labels(endpoint="tenants", status="success").inc()
        return {"tenants": tenants}
        
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        discovery_service.tenant_discovery_requests.labels(endpoint="tenants", status="error").inc()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/tenants/{tenant_id}/metrics")
async def get_tenant_metrics(tenant_id: str):
    """Get detailed metrics for a specific tenant."""
    try:
        metrics = await discovery_service.get_tenant_metrics(tenant_id)
        
        if not metrics:
            discovery_service.tenant_discovery_requests.labels(endpoint="tenant_metrics", status="not_found").inc()
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        discovery_service.tenant_discovery_requests.labels(endpoint="tenant_metrics", status="success").inc()
        
        return asdict(metrics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant metrics: {e}")
        discovery_service.tenant_discovery_requests.labels(endpoint="tenant_metrics", status="error").inc()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/alerts/{tenant_id}")
async def receive_tenant_alert(tenant_id: str, alert_data: dict, background_tasks: BackgroundTasks):
    """Receive and process tenant-specific alerts."""
    try:
        logger.info(f"Received alert for tenant {tenant_id}: {alert_data}")
        
        # Add background task to process the alert
        background_tasks.add_task(process_tenant_alert, tenant_id, alert_data)
        
        discovery_service.tenant_discovery_requests.labels(endpoint="alerts", status="success").inc()
        
        return {"status": "accepted", "tenant_id": tenant_id}
        
    except Exception as e:
        logger.error(f"Error processing alert for tenant {tenant_id}: {e}")
        discovery_service.tenant_discovery_requests.labels(endpoint="alerts", status="error").inc()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint for the discovery service itself."""
    return generate_latest(discovery_service.registry).decode('utf-8')


async def process_tenant_alert(tenant_id: str, alert_data: dict):
    """Process tenant-specific alert (background task)."""
    try:
        # Log the alert
        logger.info(f"Processing alert for tenant {tenant_id}: {alert_data.get('alertname', 'unknown')}")
        
        # Store alert in Redis if available
        if discovery_service.redis_client:
            alert_key = f"alerts:{tenant_id}:{datetime.now().isoformat()}"
            await discovery_service.redis_client.setex(
                alert_key,
                3600,  # 1 hour TTL
                json.dumps(alert_data, default=str)
            )
        
        # Here you could add additional processing like:
        # - Sending tenant-specific notifications
        # - Updating tenant status
        # - Triggering automated responses
        
    except Exception as e:
        logger.error(f"Error processing alert for tenant {tenant_id}: {e}")


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "src.monitoring.tenant_discovery:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )