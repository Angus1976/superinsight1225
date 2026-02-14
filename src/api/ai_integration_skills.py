"""
API routes for AI Skill Management.

Provides REST endpoints for skill package creation, deployment,
hot-reloading, and listing.

**Feature: ai-application-integration**
**Validates: Requirements 5.1, 5.6**
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.models.ai_integration import AISkill
from src.ai_integration.skill_manager import (
    SkillManager,
    SkillPackage,
    SkillPackageError,
    SkillDeploymentError,
    SkillNotFoundError
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ai-integration/skills",
    tags=["AI Skill Management"]
)


# ============================================================================
# Request/Response Models
# ============================================================================

class SkillConfigRequest(BaseModel):
    """Skill configuration request."""
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    entry_point: str = Field("index.js", description="Entry point file")
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="Required permissions"
    )
    timeout_seconds: int = Field(30, ge=1, le=300, description="Execution timeout")


class CreateSkillRequest(BaseModel):
    """Request to create a skill package."""
    name: str = Field(..., min_length=1, max_length=255, description="Skill name")
    version: str = Field(..., min_length=1, max_length=50, description="Skill version")
    skill_code: str = Field(..., min_length=1, description="Skill source code")
    dependencies: List[str] = Field(
        default_factory=list,
        description="NPM dependencies (e.g., ['axios@1.0.0'])"
    )
    configuration: SkillConfigRequest = Field(..., description="Skill configuration")


class DeploySkillRequest(BaseModel):
    """Request to deploy a skill to a gateway."""
    gateway_id: str = Field(..., description="Target gateway ID")


class SkillResponse(BaseModel):
    """Skill response model."""
    id: str
    gateway_id: str
    name: str
    version: str
    code_path: str
    configuration: Dict[str, Any]
    dependencies: List[str]
    status: str
    deployed_at: Optional[datetime]
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SkillPackageResponse(BaseModel):
    """Response for skill package creation."""
    name: str
    version: str
    code_path: str
    dependencies: List[str]
    configuration: Dict[str, Any]
    message: str


class DeploymentResult(BaseModel):
    """Result of skill deployment."""
    skill_id: str
    gateway_id: str
    status: str
    message: str
    deployed_at: datetime


class ReloadResult(BaseModel):
    """Result of skill hot reload."""
    skill_id: str
    gateway_id: str
    status: str
    message: str
    reloaded_at: datetime


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=SkillPackageResponse, status_code=status.HTTP_201_CREATED)
async def create_skill_package(
    request: CreateSkillRequest,
    db: Session = Depends(get_db)
):
    """
    Create a skill package.
    
    Packages skill code, dependencies, and configuration into a deployable unit.
    The package is stored and ready for deployment to gateways.
    
    **Validates: Requirements 5.1**
    """
    try:
        manager = SkillManager(db)
        
        skill_package = manager.package_skill(
            name=request.name,
            version=request.version,
            skill_code=request.skill_code,
            dependencies=request.dependencies,
            config=request.configuration.model_dump()
        )
        
        return SkillPackageResponse(
            name=skill_package.name,
            version=skill_package.version,
            code_path=skill_package.code_path,
            dependencies=skill_package.dependencies,
            configuration=skill_package.configuration,
            message="Skill package created successfully"
        )
    except SkillPackageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create skill package: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create skill package"
        )


@router.get("", response_model=List[SkillResponse])
async def list_skills(
    gateway_id: Optional[str] = Query(None, description="Filter by gateway ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: Session = Depends(get_db)
):
    """
    List skills with optional filtering.
    
    Returns paginated list of skills filtered by gateway and status.
    If gateway_id is provided, returns skills for that gateway only.
    
    **Validates: Requirements 5.1**
    """
    try:
        query = db.query(AISkill)
        
        if gateway_id:
            query = query.filter(AISkill.gateway_id == gateway_id)
        
        if status_filter:
            query = query.filter(AISkill.status == status_filter)
        
        skills = query.offset(skip).limit(limit).all()
        
        return [SkillResponse.model_validate(s) for s in skills]
    except Exception as e:
        logger.error(f"Failed to list skills: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list skills"
        )


@router.post("/{skill_id}/deploy", response_model=DeploymentResult)
async def deploy_skill(
    skill_id: str,
    request: DeploySkillRequest,
    db: Session = Depends(get_db)
):
    """
    Deploy skill to a gateway.
    
    Deploys a packaged skill to the specified gateway.
    The skill becomes available for execution on the gateway.
    
    **Validates: Requirements 5.1**
    """
    try:
        # Get the skill package from database
        skill = db.query(AISkill).filter(AISkill.id == skill_id).first()
        
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill with ID '{skill_id}' not found"
            )
        
        # Create skill package from existing skill
        skill_package = SkillPackage(
            name=skill.name,
            version=skill.version,
            code_path=skill.code_path,
            dependencies=skill.dependencies,
            configuration=skill.configuration
        )
        
        manager = SkillManager(db)
        deployed_skill = manager.deploy_skill(
            gateway_id=request.gateway_id,
            skill_package=skill_package
        )
        
        return DeploymentResult(
            skill_id=deployed_skill.id,
            gateway_id=deployed_skill.gateway_id,
            status="deployed",
            message="Skill deployed successfully",
            deployed_at=deployed_skill.deployed_at
        )
    except SkillDeploymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deploy skill: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deploy skill"
        )


@router.post("/{skill_id}/reload", response_model=ReloadResult)
async def hot_reload_skill(
    skill_id: str,
    gateway_id: str = Query(..., description="Gateway ID"),
    db: Session = Depends(get_db)
):
    """
    Hot reload skill without restarting gateway.
    
    Reloads skill code and configuration without gateway restart.
    Useful for updating skills in production without downtime.
    
    **Validates: Requirements 5.6**
    """
    try:
        manager = SkillManager(db)
        manager.hot_reload_skill(
            gateway_id=gateway_id,
            skill_id=skill_id
        )
        
        return ReloadResult(
            skill_id=skill_id,
            gateway_id=gateway_id,
            status="reloaded",
            message="Skill hot reloaded successfully",
            reloaded_at=datetime.utcnow()
        )
    except SkillNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except SkillDeploymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to hot reload skill: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to hot reload skill"
        )
