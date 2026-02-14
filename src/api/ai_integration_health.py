"""
Health check endpoints for AI Integration.

Requirements: 6.1, 6.2
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.ai_integration.monitoring_service import MonitoringService

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("")
async def health_check():
    """Overall system health."""
    return {"status": "healthy"}


@router.get("/gateway/{gateway_id}")
async def gateway_health(gateway_id: str):
    """Gateway health check."""
    service = MonitoringService()
    return service.health_check_gateway(gateway_id)


@router.get("/database")
async def database_health(db: Session = Depends(get_db)):
    """Database connectivity check."""
    try:
        db.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
