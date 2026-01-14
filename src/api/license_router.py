"""
License API Router for SuperInsight Platform.

Provides REST API endpoints for license management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.license.license_manager import LicenseManager
from src.license.license_validator import LicenseValidator
from src.license.time_controller import TimeController
from src.license.feature_controller import FeatureController
from src.license.license_audit_logger import LicenseAuditLogger
from src.models.license import LicenseEventType
from src.schemas.license import (
    CreateLicenseRequest, LicenseResponse, LicenseStatusResponse,
    RenewLicenseRequest, UpgradeLicenseRequest, RevokeLicenseRequest,
    ValidationResult, FeatureInfo, LicenseLimits, ValidityStatus,
    LicenseStatus, UsageInfo
)


router = APIRouter(prefix="/api/v1/license", tags=["License"])


def get_license_manager(db: AsyncSession = Depends(get_db)) -> LicenseManager:
    """Get license manager instance."""
    return LicenseManager(db)


def get_license_validator() -> LicenseValidator:
    """Get license validator instance."""
    return LicenseValidator()


def get_time_controller() -> TimeController:
    """Get time controller instance."""
    return TimeController()


def get_feature_controller(db: AsyncSession = Depends(get_db)) -> FeatureController:
    """Get feature controller instance."""
    return FeatureController(db)


def get_audit_logger(db: AsyncSession = Depends(get_db)) -> LicenseAuditLogger:
    """Get audit logger instance."""
    return LicenseAuditLogger(db)


@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(
    manager: LicenseManager = Depends(get_license_manager),
    validator: LicenseValidator = Depends(get_license_validator),
    time_controller: TimeController = Depends(get_time_controller),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Get current license status.
    
    Returns comprehensive license status including validity, features, and limits.
    """
    license = await manager.get_current_license()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active license found"
        )
    
    # Check validity
    validity_result = time_controller.check_license_validity(license)
    
    # Validate license
    validation = await validator.validate_license(license)
    
    # Log validation
    await audit_logger.log_validation(
        license_id=license.id,
        result="valid" if validation.valid else validation.reason or "invalid",
    )
    
    warnings = list(validation.warnings)
    if validity_result.message and validity_result.status != ValidityStatus.ACTIVE:
        warnings.append(validity_result.message)
    
    return LicenseStatusResponse(
        license_id=license.id,
        license_key=license.license_key,
        license_type=license.license_type,
        status=license.status,
        validity_status=validity_result.status,
        days_remaining=validity_result.days_remaining,
        days_until_start=validity_result.days_until_start,
        features=license.features,
        limits=LicenseLimits(
            max_concurrent_users=license.max_concurrent_users,
            max_cpu_cores=license.max_cpu_cores,
            max_storage_gb=license.max_storage_gb,
            max_projects=license.max_projects,
            max_datasets=license.max_datasets,
        ),
        warnings=warnings,
    )


@router.post("/", response_model=LicenseResponse)
async def create_license(
    request: CreateLicenseRequest,
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Create a new license.
    
    Creates a license in PENDING status that needs to be activated.
    """
    license = await manager.create_license(request)
    
    await audit_logger.log_event(
        event_type=LicenseEventType.CREATED,
        license_id=license.id,
        details={
            "license_type": license.license_type.value,
            "features": license.features,
        },
    )
    
    return license


@router.get("/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: UUID,
    manager: LicenseManager = Depends(get_license_manager),
):
    """Get license by ID."""
    license = await manager.get_license(license_id)
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    return license


@router.get("/", response_model=List[LicenseResponse])
async def list_licenses(
    status: Optional[LicenseStatus] = None,
    limit: int = 100,
    offset: int = 0,
    manager: LicenseManager = Depends(get_license_manager),
):
    """List all licenses with optional filters."""
    return await manager.list_licenses(
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/{license_id}/renew", response_model=LicenseResponse)
async def renew_license(
    license_id: UUID,
    request: RenewLicenseRequest,
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Renew a license.
    
    Extends the validity period of an existing license.
    """
    license = await manager.renew_license(license_id, request)
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found or cannot be renewed"
        )
    
    await audit_logger.log_event(
        event_type=LicenseEventType.RENEWED,
        license_id=license.id,
        details={
            "new_end_date": request.new_end_date.isoformat(),
        },
    )
    
    return license


@router.post("/{license_id}/upgrade", response_model=LicenseResponse)
async def upgrade_license(
    license_id: UUID,
    request: UpgradeLicenseRequest,
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Upgrade a license.
    
    Upgrades license type, features, or limits.
    """
    license = await manager.upgrade_license(license_id, request)
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found or cannot be upgraded"
        )
    
    await audit_logger.log_event(
        event_type=LicenseEventType.UPGRADED,
        license_id=license.id,
        details={
            "new_type": request.new_type.value if request.new_type else None,
            "new_features": request.new_features,
        },
    )
    
    return license


@router.post("/{license_id}/revoke")
async def revoke_license(
    license_id: UUID,
    request: RevokeLicenseRequest,
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Revoke a license.
    
    Permanently revokes a license. This action cannot be undone.
    """
    success = await manager.revoke_license(license_id, request.reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    await audit_logger.log_event(
        event_type=LicenseEventType.REVOKED,
        license_id=license_id,
        details={"reason": request.reason},
    )
    
    return {"success": True, "message": "License revoked"}


@router.post("/{license_id}/suspend")
async def suspend_license(
    license_id: UUID,
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Suspend a license temporarily."""
    success = await manager.suspend_license(license_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License not found or cannot be suspended"
        )
    
    await audit_logger.log_event(
        event_type=LicenseEventType.SUSPENDED,
        license_id=license_id,
    )
    
    return {"success": True, "message": "License suspended"}


@router.post("/{license_id}/reactivate")
async def reactivate_license(
    license_id: UUID,
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Reactivate a suspended license."""
    success = await manager.reactivate_license(license_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License not found or cannot be reactivated"
        )
    
    await audit_logger.log_event(
        event_type=LicenseEventType.ACTIVATED,
        license_id=license_id,
        details={"action": "reactivate"},
    )
    
    return {"success": True, "message": "License reactivated"}


@router.get("/features/list", response_model=List[FeatureInfo])
async def get_available_features(
    feature_controller: FeatureController = Depends(get_feature_controller),
):
    """Get list of all features with availability status."""
    return await feature_controller.get_available_features()


@router.get("/features/{feature}/check")
async def check_feature_access(
    feature: str,
    feature_controller: FeatureController = Depends(get_feature_controller),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Check if a specific feature is accessible."""
    result = await feature_controller.check_feature_access(feature)
    
    # Get license for logging
    license = await feature_controller._get_current_license()
    
    await audit_logger.log_feature_access(
        feature=feature,
        allowed=result.allowed,
        license_id=license.id if license else None,
        reason=result.reason,
    )
    
    return result


@router.get("/limits", response_model=LicenseLimits)
async def get_license_limits(
    manager: LicenseManager = Depends(get_license_manager),
):
    """Get current license limits."""
    license = await manager.get_current_license()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active license found"
        )
    
    return LicenseLimits(
        max_concurrent_users=license.max_concurrent_users,
        max_cpu_cores=license.max_cpu_cores,
        max_storage_gb=license.max_storage_gb,
        max_projects=license.max_projects,
        max_datasets=license.max_datasets,
    )


@router.get("/validate", response_model=ValidationResult)
async def validate_license(
    hardware_id: Optional[str] = None,
    manager: LicenseManager = Depends(get_license_manager),
    validator: LicenseValidator = Depends(get_license_validator),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Validate current license.
    
    Performs full validation including signature, validity, and hardware binding.
    """
    license = await manager.get_current_license()
    
    if not license:
        return ValidationResult(
            valid=False,
            reason="No active license found"
        )
    
    result = await validator.validate_license(license, hardware_id)
    
    await audit_logger.log_validation(
        license_id=license.id,
        result="valid" if result.valid else result.reason or "invalid",
        details={"hardware_id": hardware_id},
    )
    
    return result
