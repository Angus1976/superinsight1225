"""
TCB (Tencent Cloud Base) Client for SuperInsight Platform.

Provides integration with Tencent Cloud Base services including
Cloud Run, storage, and serverless functions.
"""

import asyncio
import logging
import time
import json
import hashlib
import hmac
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class TCBServiceType(Enum):
    """Types of TCB services."""
    CLOUD_RUN = "cloud_run"
    FUNCTION = "function"
    STORAGE = "storage"
    DATABASE = "database"


class DeploymentStatus(Enum):
    """Status of a deployment."""
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TCBConfig:
    """Configuration for TCB client."""
    env_id: str
    secret_id: str
    secret_key: str
    region: str = "ap-shanghai"
    api_endpoint: str = "https://tcb.tencentcloudapi.com"
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class ServiceConfig:
    """Configuration for a TCB service."""
    service_name: str
    service_type: TCBServiceType
    cpu: int = 2
    memory: int = 4096
    min_instances: int = 1
    max_instances: int = 10
    port: int = 8000
    env_variables: Dict[str, str] = field(default_factory=dict)
    volume_mounts: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    success: bool
    deployment_id: str
    status: DeploymentStatus
    service_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TCBClient:
    """
    Client for Tencent Cloud Base (TCB) services.
    
    Features:
    - Cloud Run container deployment
    - Serverless function management
    - Storage integration
    - Auto-scaling configuration
    - Deployment status monitoring
    """
    
    def __init__(self, config: TCBConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self.deployments: Dict[str, DeploymentResult] = {}
        
        logger.info(f"TCBClient initialized for env: {config.env_id}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        return self._session
    
    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _generate_signature(
        self,
        method: str,
        action: str,
        params: Dict[str, Any],
        timestamp: int
    ) -> str:
        """Generate TCB API signature."""
        # Simplified signature generation
        # In production, use proper TC3-HMAC-SHA256 signing
        canonical_request = f"{method}\n{action}\n{json.dumps(params, sort_keys=True)}"
        string_to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        signing_key = hmac.new(
            f"TC3{self.config.secret_key}".encode(),
            str(timestamp).encode(),
            hashlib.sha256
        ).digest()
        
        signature = hmac.new(
            signing_key,
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _make_request(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a request to TCB API."""
        session = await self._get_session()
        timestamp = int(time.time())
        
        headers = {
            "Content-Type": "application/json",
            "X-TC-Action": action,
            "X-TC-Version": "2018-06-08",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.config.region,
            "Authorization": f"TC3-HMAC-SHA256 Credential={self.config.secret_id}/{timestamp}/tcb/tc3_request, SignedHeaders=content-type;host, Signature={self._generate_signature('POST', action, params, timestamp)}"
        }
        
        for attempt in range(self.config.max_retries):
            try:
                async with session.post(
                    self.config.api_endpoint,
                    json=params,
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        return result
                    else:
                        logger.warning(f"TCB API error: {result}")
                        
            except Exception as e:
                logger.error(f"TCB API request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return {"error": "Max retries exceeded"}
    
    async def deploy_container(
        self,
        service_config: ServiceConfig,
        image_url: str
    ) -> DeploymentResult:
        """Deploy a container to TCB Cloud Run."""
        deployment_id = f"deploy_{int(time.time())}_{service_config.service_name}"
        
        logger.info(f"Starting container deployment: {deployment_id}")
        
        result = DeploymentResult(
            success=False,
            deployment_id=deployment_id,
            status=DeploymentStatus.PENDING
        )
        
        self.deployments[deployment_id] = result
        
        try:
            # Update status to building
            result.status = DeploymentStatus.BUILDING
            
            # Prepare deployment parameters
            params = {
                "EnvId": self.config.env_id,
                "ServerName": service_config.service_name,
                "ImageInfo": {
                    "ImageUrl": image_url
                },
                "ContainerPort": service_config.port,
                "Cpu": service_config.cpu,
                "Mem": service_config.memory,
                "MinNum": service_config.min_instances,
                "MaxNum": service_config.max_instances,
                "EnvParams": json.dumps(service_config.env_variables),
                "PolicyType": "cpu",
                "PolicyThreshold": 70
            }
            
            # Make deployment request
            result.status = DeploymentStatus.DEPLOYING
            response = await self._make_request("CreateCloudRunServer", params)
            
            if "error" not in response:
                result.success = True
                result.status = DeploymentStatus.RUNNING
                result.service_url = f"https://{service_config.service_name}.{self.config.env_id}.{self.config.region}.tcb.qcloud.la"
                result.metadata = response
                logger.info(f"Deployment {deployment_id} successful")
            else:
                result.status = DeploymentStatus.FAILED
                result.error_message = str(response.get("error"))
                logger.error(f"Deployment {deployment_id} failed: {result.error_message}")
            
        except Exception as e:
            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Deployment {deployment_id} error: {e}")
        
        result.completed_at = time.time()
        return result
    
    async def get_deployment_status(self, service_name: str) -> Dict[str, Any]:
        """Get the status of a deployed service."""
        params = {
            "EnvId": self.config.env_id,
            "ServerName": service_name
        }
        
        response = await self._make_request("DescribeCloudRunServerDetail", params)
        return response
    
    async def update_service_config(
        self,
        service_name: str,
        config_updates: Dict[str, Any]
    ) -> bool:
        """Update service configuration."""
        params = {
            "EnvId": self.config.env_id,
            "ServerName": service_name,
            **config_updates
        }
        
        response = await self._make_request("ModifyCloudRunServer", params)
        return "error" not in response
    
    async def scale_service(
        self,
        service_name: str,
        min_instances: int,
        max_instances: int
    ) -> bool:
        """Scale a service."""
        return await self.update_service_config(
            service_name,
            {
                "MinNum": min_instances,
                "MaxNum": max_instances
            }
        )
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a service."""
        params = {
            "EnvId": self.config.env_id,
            "ServerName": service_name
        }
        
        response = await self._make_request("DeleteCloudRunServer", params)
        return "error" not in response
    
    async def get_service_logs(
        self,
        service_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get service logs."""
        params = {
            "EnvId": self.config.env_id,
            "ServerName": service_name,
            "Limit": limit
        }
        
        if start_time:
            params["StartTime"] = start_time.isoformat()
        if end_time:
            params["EndTime"] = end_time.isoformat()
        
        response = await self._make_request("DescribeCloudRunServerLogs", params)
        return response.get("LogSet", [])
    
    async def get_service_metrics(
        self,
        service_name: str,
        metric_names: List[str],
        period: int = 60
    ) -> Dict[str, Any]:
        """Get service metrics."""
        params = {
            "EnvId": self.config.env_id,
            "ServerName": service_name,
            "MetricNames": metric_names,
            "Period": period
        }
        
        response = await self._make_request("DescribeCloudRunServerMetrics", params)
        return response
    
    def get_deployment_history(self) -> List[DeploymentResult]:
        """Get deployment history."""
        return list(self.deployments.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics."""
        deployments = list(self.deployments.values())
        successful = sum(1 for d in deployments if d.success)
        
        return {
            "env_id": self.config.env_id,
            "region": self.config.region,
            "total_deployments": len(deployments),
            "successful_deployments": successful,
            "failed_deployments": len(deployments) - successful,
            "success_rate": successful / len(deployments) if deployments else 0
        }


# Factory function for creating TCB client
def create_tcb_client(
    env_id: Optional[str] = None,
    secret_id: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: str = "ap-shanghai"
) -> Optional[TCBClient]:
    """Create a TCB client from environment or parameters."""
    import os
    
    env_id = env_id or os.getenv("TCB_ENV_ID")
    secret_id = secret_id or os.getenv("TCB_SECRET_ID")
    secret_key = secret_key or os.getenv("TCB_SECRET_KEY")
    region = os.getenv("TCB_REGION", region)
    
    if not all([env_id, secret_id, secret_key]):
        logger.warning("TCB credentials not configured")
        return None
    
    config = TCBConfig(
        env_id=env_id,
        secret_id=secret_id,
        secret_key=secret_key,
        region=region
    )
    
    return TCBClient(config)
