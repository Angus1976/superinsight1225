"""
Resource Controller for SuperInsight Platform.

Manages resource limits including CPU cores, storage, projects, and datasets.
"""

import multiprocessing
import os
import shutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.license import LicenseModel, LicenseStatus
from src.schemas.license import ResourceCheckResult, ResourceUsage


class ResourceController:
    """
    Resource Controller.
    
    Manages and enforces resource limits based on license.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        data_path: str = "./data"
    ):
        """
        Initialize Resource Controller.
        
        Args:
            db: Database session
            data_path: Path to data directory for storage calculation
        """
        self.db = db
        self.data_path = data_path
        self._license_cache: Optional[LicenseModel] = None
    
    async def _get_current_license(self) -> Optional[LicenseModel]:
        """Get current active license."""
        if self._license_cache:
            return self._license_cache
        
        result = await self.db.execute(
            select(LicenseModel)
            .where(LicenseModel.status == LicenseStatus.ACTIVE)
            .order_by(LicenseModel.activated_at.desc())
            .limit(1)
        )
        license_model = result.scalar_one_or_none()
        
        if license_model:
            self._license_cache = license_model
        
        return license_model
    
    def detect_cpu_cores(self) -> int:
        """Detect available CPU cores."""
        return multiprocessing.cpu_count()
    
    def detect_storage_usage_gb(self) -> float:
        """Detect current storage usage in GB."""
        if not os.path.exists(self.data_path):
            return 0.0
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.data_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, IOError):
                    pass
        
        return total_size / (1024 ** 3)  # Convert to GB
    
    async def check_cpu_limit(self) -> ResourceCheckResult:
        """
        Check CPU core limit.
        
        Returns:
            Resource check result
        """
        license = await self._get_current_license()
        
        if not license:
            return ResourceCheckResult(
                allowed=False,
                reason="No valid license found"
            )
        
        available_cores = self.detect_cpu_cores()
        max_cores = license.max_cpu_cores
        
        if available_cores > max_cores:
            return ResourceCheckResult(
                allowed=True,
                warning=f"System has {available_cores} cores, license allows {max_cores}. "
                        f"Only {max_cores} cores will be utilized.",
                current=available_cores,
                max=max_cores
            )
        
        return ResourceCheckResult(
            allowed=True,
            current=available_cores,
            max=max_cores
        )
    
    async def check_storage_limit(self) -> ResourceCheckResult:
        """
        Check storage limit.
        
        Returns:
            Resource check result
        """
        license = await self._get_current_license()
        
        if not license:
            return ResourceCheckResult(
                allowed=False,
                reason="No valid license found"
            )
        
        current_gb = self.detect_storage_usage_gb()
        max_gb = license.max_storage_gb
        
        if current_gb >= max_gb:
            return ResourceCheckResult(
                allowed=False,
                reason=f"Storage limit reached ({current_gb:.2f}GB / {max_gb}GB)",
                current=int(current_gb),
                max=max_gb
            )
        
        # Warning at 80% usage
        if current_gb >= max_gb * 0.8:
            return ResourceCheckResult(
                allowed=True,
                warning=f"Storage usage at {(current_gb/max_gb)*100:.1f}%",
                current=int(current_gb),
                max=max_gb
            )
        
        return ResourceCheckResult(
            allowed=True,
            current=int(current_gb),
            max=max_gb
        )
    
    async def check_project_limit(
        self,
        current_projects: int
    ) -> ResourceCheckResult:
        """
        Check project count limit.
        
        Args:
            current_projects: Current number of projects
            
        Returns:
            Resource check result
        """
        license = await self._get_current_license()
        
        if not license:
            return ResourceCheckResult(
                allowed=False,
                reason="No valid license found"
            )
        
        max_projects = license.max_projects
        
        if current_projects >= max_projects:
            return ResourceCheckResult(
                allowed=False,
                reason=f"Project limit reached ({current_projects}/{max_projects})",
                current=current_projects,
                max=max_projects
            )
        
        return ResourceCheckResult(
            allowed=True,
            current=current_projects,
            max=max_projects
        )
    
    async def check_dataset_limit(
        self,
        current_datasets: int
    ) -> ResourceCheckResult:
        """
        Check dataset count limit.
        
        Args:
            current_datasets: Current number of datasets
            
        Returns:
            Resource check result
        """
        license = await self._get_current_license()
        
        if not license:
            return ResourceCheckResult(
                allowed=False,
                reason="No valid license found"
            )
        
        max_datasets = license.max_datasets
        
        if current_datasets >= max_datasets:
            return ResourceCheckResult(
                allowed=False,
                reason=f"Dataset limit reached ({current_datasets}/{max_datasets})",
                current=current_datasets,
                max=max_datasets
            )
        
        return ResourceCheckResult(
            allowed=True,
            current=current_datasets,
            max=max_datasets
        )
    
    async def get_resource_usage(self) -> ResourceUsage:
        """
        Get current resource usage.
        
        Returns:
            Resource usage information
        """
        return ResourceUsage(
            cpu_cores=self.detect_cpu_cores(),
            storage_gb=self.detect_storage_usage_gb(),
            projects_count=0,  # Would need to query actual projects
            datasets_count=0,  # Would need to query actual datasets
        )
    
    async def get_resource_limits(self) -> Optional[Dict[str, int]]:
        """
        Get resource limits from license.
        
        Returns:
            Dictionary of resource limits or None if no license
        """
        license = await self._get_current_license()
        
        if not license:
            return None
        
        return {
            "max_cpu_cores": license.max_cpu_cores,
            "max_storage_gb": license.max_storage_gb,
            "max_projects": license.max_projects,
            "max_datasets": license.max_datasets,
            "max_concurrent_users": license.max_concurrent_users,
        }
    
    async def get_resource_utilization(self) -> Dict[str, float]:
        """
        Get resource utilization percentages.
        
        Returns:
            Dictionary of utilization percentages
        """
        license = await self._get_current_license()
        
        if not license:
            return {}
        
        cpu_cores = self.detect_cpu_cores()
        storage_gb = self.detect_storage_usage_gb()
        
        return {
            "cpu_utilization": min(100.0, (cpu_cores / license.max_cpu_cores) * 100),
            "storage_utilization": min(100.0, (storage_gb / license.max_storage_gb) * 100),
        }
    
    async def check_all_resources(self) -> Dict[str, ResourceCheckResult]:
        """
        Check all resource limits.
        
        Returns:
            Dictionary of resource check results
        """
        return {
            "cpu": await self.check_cpu_limit(),
            "storage": await self.check_storage_limit(),
        }
    
    def get_effective_cpu_cores(self, max_cores: int) -> int:
        """
        Get effective CPU cores to use based on license limit.
        
        Args:
            max_cores: Maximum cores allowed by license
            
        Returns:
            Number of cores to use
        """
        available = self.detect_cpu_cores()
        return min(available, max_cores)
    
    def clear_cache(self):
        """Clear license cache."""
        self._license_cache = None
