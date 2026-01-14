"""
Activation API Router for SuperInsight Platform.

Provides REST API endpoints for license activation.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.license.remote_activation_service import RemoteActivationService
from src.license.license_audit_logger import LicenseAuditLogger
from src.models.license import LicenseEventType
from src.schemas.license import (
    ActivateLicenseRequest, ActivationResult, OfflineActivationResponse,
    OfflineActivationRequest
)


router = APIRouter(prefix="/api/v1/activation", tags=["Activation"])


def get_activation_service(db: AsyncSession = Depends(get_db)) -> RemoteActivationService:
    """Get activation service instance."""
    return RemoteActivationService(db)


def get_audit_logger(db: AsyncSession = Depends(get_db)) -> LicenseAuditLogger:
    """Get audit logger instance."""
    return LicenseAuditLogger(db)


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/activate", response_model=ActivationResult)
async def activate_license(
    request_body: ActivateLicenseRequest,
    request: Request,
    service: RemoteActivationService = Depends(get_activation_service),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Activate a license online.
    
    Activates a license using the provided license key and optional hardware fingerprint.
    If no hardware fingerprint is provided, one will be generated automatically.
    """
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    result = await service.activate_online(
        license_key=request_body.license_key,
        hardware_fingerprint=request_body.hardware_fingerprint,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Log activation attempt
    if result.license:
        await audit_logger.log_activation(
            license_id=result.license.id,
            hardware_id=request_body.hardware_fingerprint or service.get_hardware_fingerprint(),
            result="success" if result.success else (result.error or "failed"),
            ip_address=ip_address,
        )
    
    return result


@router.post("/offline/request", response_model=OfflineActivationResponse)
async def generate_offline_request(
    license_key: str,
    hardware_fingerprint: Optional[str] = None,
    service: RemoteActivationService = Depends(get_activation_service),
):
    """
    Generate offline activation request.
    
    Creates an activation request code that can be submitted to the license server
    for offline activation. The request code is valid for 7 days.
    """
    return service.generate_offline_request(
        license_key=license_key,
        hardware_fingerprint=hardware_fingerprint,
    )


@router.post("/offline/activate", response_model=ActivationResult)
async def activate_offline(
    activation_code: str,
    request: Request,
    service: RemoteActivationService = Depends(get_activation_service),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Complete offline activation.
    
    Activates a license using an activation code obtained from the license server.
    """
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    result = await service.activate_offline(
        activation_code=activation_code,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Log activation attempt
    if result.license:
        await audit_logger.log_activation(
            license_id=result.license.id,
            hardware_id=service.get_hardware_fingerprint(),
            result="success" if result.success else (result.error or "failed"),
            ip_address=ip_address,
        )
    
    return result


@router.get("/verify/{license_id}")
async def verify_activation(
    license_id: UUID,
    service: RemoteActivationService = Depends(get_activation_service),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Verify activation status.
    
    Checks if the license is properly activated and hardware binding is valid.
    """
    result = await service.verify_activation_status(license_id)
    
    await audit_logger.log_validation(
        license_id=license_id,
        result="valid" if result.get("valid") else result.get("reason", "invalid"),
    )
    
    return result


@router.get("/fingerprint")
async def get_hardware_fingerprint(
    service: RemoteActivationService = Depends(get_activation_service),
):
    """
    Get current hardware fingerprint.
    
    Returns the hardware fingerprint for this machine, which is used for license binding.
    """
    fingerprint = service.get_hardware_fingerprint()
    
    return {
        "fingerprint": fingerprint,
        "message": "Use this fingerprint for license activation"
    }


@router.post("/revoke/{license_id}")
async def revoke_activation(
    license_id: UUID,
    reason: str,
    service: RemoteActivationService = Depends(get_activation_service),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Revoke license activation.
    
    Revokes a license, making it unusable. This action cannot be undone.
    """
    success = await service.remote_revoke(license_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    await audit_logger.log_event(
        event_type=LicenseEventType.REVOKED,
        license_id=license_id,
        details={"reason": reason, "method": "remote_revoke"},
    )
    
    return {"success": True, "message": "License revoked"}
