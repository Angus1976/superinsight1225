"""
API endpoints for AI Integration Workflow Designer.

Provides REST API for conversational workflow design, execution, and comparison.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field

from src.ai_integration.workflow_designer import (
    WorkflowDesigner,
    WorkflowDefinition,
    ValidationResult,
    WorkflowResult,
    ComparisonResult
)
from src.ai_integration.data_bridge import OpenClawDataBridge
from src.ai_integration.authorization import AuthorizationService
from src.ai_integration.auth import JWTTokenService, TokenClaims
from src.database.connection import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-integration/workflows", tags=["ai-integration-workflows"])

# Initialize JWT service
jwt_service = JWTTokenService()


# Request/Response Models

class ParseWorkflowRequest(BaseModel):
    """Request to parse natural language workflow description."""
    description: str = Field(..., description="Natural language workflow description")
    tenant_id: str = Field(..., description="Tenant ID for multi-tenant isolation")


class WorkflowResponse(BaseModel):
    """Workflow definition response."""
    id: str
    name: str
    description: str
    tenant_id: str
    data_sources: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]
    output: Dict[str, Any]
    quality_requirements: Dict[str, Any]
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    version: int = 1


class SaveWorkflowRequest(BaseModel):
    """Request to save workflow definition."""
    workflow: Dict[str, Any] = Field(..., description="Workflow definition")


class ValidationResponse(BaseModel):
    """Workflow validation response."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute workflow."""
    use_governed_data: bool = Field(
        default=True,
        description="Whether to use governed data (True) or raw data (False)"
    )


class WorkflowResultResponse(BaseModel):
    """Workflow execution result response."""
    workflow_id: str
    execution_id: str
    status: str
    data: Any
    quality_metrics: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None
    error: Optional[str] = None


class ComparisonResponse(BaseModel):
    """Comparison result response."""
    workflow_id: str
    governed_result: WorkflowResultResponse
    raw_result: WorkflowResultResponse
    comparison_metrics: Dict[str, Any]


# Dependency injection

async def get_current_gateway(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> TokenClaims:
    """
    Extract and validate JWT token from Authorization header.
    
    Args:
        authorization: Authorization header (Bearer token)
        db: Database session
        
    Returns:
        TokenClaims with gateway and tenant information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        claims = jwt_service.validate_token(token)
        return claims
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(e)}"
        )


async def get_workflow_designer(
    claims: TokenClaims = Depends(get_current_gateway),
    db: Session = Depends(get_db)
) -> WorkflowDesigner:
    """Get WorkflowDesigner instance."""
    # Initialize dependencies
    data_bridge = OpenClawDataBridge()
    authorization_service = AuthorizationService(db)
    
    # Create workflow designer
    designer = WorkflowDesigner(
        data_bridge=data_bridge,
        authorization_service=authorization_service,
        tenant_id=claims.tenant_id
    )
    
    await designer.initialize()
    
    return designer


# API Endpoints

@router.post("/parse", response_model=WorkflowResponse, status_code=status.HTTP_200_OK)
async def parse_workflow(
    request: ParseWorkflowRequest,
    designer: WorkflowDesigner = Depends(get_workflow_designer),
    claims: TokenClaims = Depends(get_current_gateway)
):
    """
    Parse natural language workflow description.
    
    Uses LLM to extract workflow components from natural language.
    
    Requirements: 14.1, 14.2
    """
    try:
        # Validate tenant access
        if request.tenant_id != claims.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant mismatch"
            )
        
        # Parse workflow
        workflow = await designer.parse_workflow_description(
            description=request.description,
            tenant_id=request.tenant_id
        )
        
        logger.info(f"Workflow parsed: {workflow.id} for tenant {request.tenant_id}")
        
        return WorkflowResponse(**workflow.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to parse workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse workflow: {str(e)}"
        )


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def save_workflow(
    request: SaveWorkflowRequest,
    designer: WorkflowDesigner = Depends(get_workflow_designer),
    claims: TokenClaims = Depends(get_current_gateway)
):
    """
    Save workflow definition.
    
    Validates and stores workflow for later execution.
    
    Requirements: 14.3, 14.4
    """
    try:
        # Create workflow definition from request
        workflow_data = request.workflow
        
        # Validate tenant access
        if workflow_data.get("tenant_id") != claims.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant mismatch"
            )
        
        # Create workflow definition
        workflow = WorkflowDefinition(
            id=workflow_data.get("id"),
            name=workflow_data.get("name"),
            description=workflow_data.get("description"),
            tenant_id=workflow_data.get("tenant_id"),
            data_sources=workflow_data.get("data_sources", []),
            steps=workflow_data.get("steps", []),
            output=workflow_data.get("output", {}),
            quality_requirements=workflow_data.get("quality_requirements"),
            created_by=claims.gateway_id
        )
        
        # Validate workflow
        validation = await designer.validate_workflow(
            workflow=workflow,
            tenant_id=claims.tenant_id
        )
        
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow validation failed: {', '.join(validation.errors)}"
            )
        
        # Store workflow
        designer._workflows[workflow.id] = workflow
        
        logger.info(f"Workflow saved: {workflow.id} for tenant {claims.tenant_id}")
        
        return WorkflowResponse(**workflow.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save workflow: {str(e)}"
        )


@router.get("", response_model=List[WorkflowResponse], status_code=status.HTTP_200_OK)
async def list_workflows(
    designer: WorkflowDesigner = Depends(get_workflow_designer),
    claims: TokenClaims = Depends(get_current_gateway)
):
    """
    List workflows for current tenant.
    
    Returns all workflows accessible to the current gateway's tenant.
    
    Requirements: 14.3
    """
    try:
        # Filter workflows by tenant
        workflows = [
            WorkflowResponse(**workflow.to_dict())
            for workflow in designer._workflows.values()
            if workflow.tenant_id == claims.tenant_id
        ]
        
        logger.info(f"Listed {len(workflows)} workflows for tenant {claims.tenant_id}")
        
        return workflows
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse, status_code=status.HTTP_200_OK)
async def get_workflow(
    workflow_id: str,
    designer: WorkflowDesigner = Depends(get_workflow_designer),
    claims: TokenClaims = Depends(get_current_gateway)
):
    """
    Get workflow details.
    
    Returns detailed information about a specific workflow.
    
    Requirements: 14.3
    """
    try:
        # Get workflow
        workflow = designer._workflows.get(workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Validate tenant access
        if workflow.tenant_id != claims.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant mismatch"
            )
        
        logger.info(f"Retrieved workflow: {workflow_id}")
        
        return WorkflowResponse(**workflow.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}"
        )


@router.post("/{workflow_id}/execute", response_model=WorkflowResultResponse, status_code=status.HTTP_200_OK)
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    designer: WorkflowDesigner = Depends(get_workflow_designer),
    claims: TokenClaims = Depends(get_current_gateway)
):
    """
    Execute workflow.
    
    Executes workflow with governed or raw data based on request.
    
    Requirements: 14.5
    """
    try:
        # Get workflow
        workflow = designer._workflows.get(workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Validate tenant access
        if workflow.tenant_id != claims.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant mismatch"
            )
        
        # Execute workflow
        result = await designer.execute_workflow(
            workflow_id=workflow_id,
            use_governed_data=request.use_governed_data
        )
        
        logger.info(
            f"Executed workflow: {workflow_id} "
            f"(governed={request.use_governed_data}, status={result.status})"
        )
        
        return WorkflowResultResponse(**result.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.post("/{workflow_id}/compare", response_model=ComparisonResponse, status_code=status.HTTP_200_OK)
async def compare_workflow_results(
    workflow_id: str,
    designer: WorkflowDesigner = Depends(get_workflow_designer),
    claims: TokenClaims = Depends(get_current_gateway)
):
    """
    Compare workflow results.
    
    Executes workflow with both governed and raw data and compares results.
    
    Requirements: 14.5, 14.6
    """
    try:
        # Get workflow
        workflow = designer._workflows.get(workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Validate tenant access
        if workflow.tenant_id != claims.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant mismatch"
            )
        
        # Compare results
        comparison = await designer.compare_results(workflow_id=workflow_id)
        
        logger.info(
            f"Compared workflow results: {workflow_id} "
            f"(improvement={comparison.comparison_metrics.get('improvement_percentage', 0):.2f}%)"
        )
        
        return ComparisonResponse(
            workflow_id=comparison.workflow_id,
            governed_result=WorkflowResultResponse(**comparison.governed_result.to_dict()),
            raw_result=WorkflowResultResponse(**comparison.raw_result.to_dict()),
            comparison_metrics=comparison.comparison_metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare workflow results: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare workflow results: {str(e)}"
        )
