"""
API endpoints for reward distribution system.

Provides REST API for reward calculation, approval workflows,
and reward analytics.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal

from src.billing.reward_system import (
    RewardDistributionManager, RewardType, RewardStatus, 
    ApprovalLevel, RewardFrequency, RewardRecord
)


router = APIRouter(prefix="/api/rewards", tags=["rewards"])


class RewardCalculationRequest(BaseModel):
    """Request model for reward calculation."""
    tenant_id: str = Field(..., description="Tenant identifier")
    user_ids: List[str] = Field(..., description="List of user identifiers")
    period_start: date = Field(..., description="Period start date")
    period_end: date = Field(..., description="Period end date")
    frequency: RewardFrequency = Field(default=RewardFrequency.MONTHLY, description="Calculation frequency")
    innovation_metrics: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Innovation metrics by user")


class RewardApprovalRequest(BaseModel):
    """Request model for reward approval."""
    reward_id: str = Field(..., description="Reward identifier")
    approver_id: str = Field(..., description="Approver identifier")
    approver_role: str = Field(..., description="Approver role")
    approved: bool = Field(..., description="Approval decision")
    notes: str = Field(default="", description="Approval notes")


class RewardPaymentRequest(BaseModel):
    """Request model for reward payment."""
    reward_ids: List[str] = Field(..., description="List of reward identifiers to pay")
    payment_method: str = Field(default="bank_transfer", description="Payment method")
    notes: str = Field(default="", description="Payment notes")


class RewardStatisticsRequest(BaseModel):
    """Request model for reward statistics."""
    tenant_id: str = Field(..., description="Tenant identifier")
    start_date: Optional[date] = Field(None, description="Start date filter")
    end_date: Optional[date] = Field(None, description="End date filter")
    user_ids: Optional[List[str]] = Field(None, description="Filter by specific users")
    reward_types: Optional[List[RewardType]] = Field(None, description="Filter by reward types")


class RewardResponse(BaseModel):
    """Response model for reward operations."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


# Initialize reward manager
reward_manager = RewardDistributionManager()


def get_user_role(user_id: str) -> str:
    """
    Get user's role for approval permissions.
    
    Args:
        user_id: User identifier
        
    Returns:
        User role
    """
    # This would typically check user roles from database
    # For demonstration, return based on user_id pattern
    if user_id.startswith("supervisor_"):
        return "supervisor"
    elif user_id.startswith("manager_"):
        return "manager"
    elif user_id.startswith("executive_"):
        return "executive"
    else:
        return "user"


def check_approval_permission(user_id: str, approval_level: ApprovalLevel) -> bool:
    """
    Check if user has permission to approve at given level.
    
    Args:
        user_id: User identifier
        approval_level: Required approval level
        
    Returns:
        True if user has permission
    """
    user_role = get_user_role(user_id)
    
    permission_map = {
        ApprovalLevel.AUTO_APPROVED: True,  # No approval needed
        ApprovalLevel.SUPERVISOR_APPROVAL: user_role in ["supervisor", "manager", "executive"],
        ApprovalLevel.MANAGER_APPROVAL: user_role in ["manager", "executive"],
        ApprovalLevel.EXECUTIVE_APPROVAL: user_role == "executive"
    }
    
    return permission_map.get(approval_level, False)


@router.post("/calculate", response_model=RewardResponse)
async def calculate_rewards(
    request: RewardCalculationRequest,
    background_tasks: BackgroundTasks,
    calculated_by: str = Query(..., description="User performing calculation")
):
    """
    Calculate rewards for users in a period.
    
    Args:
        request: Reward calculation request
        background_tasks: FastAPI background tasks
        calculated_by: User performing calculation
        
    Returns:
        Calculation results
    """
    try:
        # Calculate rewards
        reward_records = reward_manager.calculate_period_rewards(
            tenant_id=request.tenant_id,
            user_ids=request.user_ids,
            period_start=request.period_start,
            period_end=request.period_end,
            frequency=request.frequency
        )
        
        # Prepare response data
        response_data = {
            "calculation_summary": {
                "total_rewards": len(reward_records),
                "total_amount": float(sum(record.amount for record in reward_records)),
                "auto_approved": len([r for r in reward_records if r.status == RewardStatus.APPROVED]),
                "pending_approval": len([r for r in reward_records if r.status == RewardStatus.PENDING])
            },
            "rewards_by_type": {},
            "rewards_by_user": {},
            "reward_details": []
        }
        
        # Group by type and user
        by_type = {}
        by_user = {}
        
        for record in reward_records:
            # By type
            if record.reward_type.value not in by_type:
                by_type[record.reward_type.value] = {"count": 0, "amount": 0.0}
            by_type[record.reward_type.value]["count"] += 1
            by_type[record.reward_type.value]["amount"] += float(record.amount)
            
            # By user
            if record.user_id not in by_user:
                by_user[record.user_id] = {"count": 0, "amount": 0.0, "rewards": []}
            by_user[record.user_id]["count"] += 1
            by_user[record.user_id]["amount"] += float(record.amount)
            by_user[record.user_id]["rewards"].append({
                "reward_id": str(record.id),
                "reward_type": record.reward_type.value,
                "amount": float(record.amount),
                "status": record.status.value
            })
            
            # Detailed records
            response_data["reward_details"].append(record.to_dict())
        
        response_data["rewards_by_type"] = by_type
        response_data["rewards_by_user"] = by_user
        
        return RewardResponse(
            success=True,
            message=f"Successfully calculated {len(reward_records)} rewards",
            data=response_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-approvals")
async def get_pending_approvals(
    tenant_id: str = Query(..., description="Tenant identifier"),
    approver_id: str = Query(..., description="Approver identifier")
):
    """
    Get pending reward approvals for an approver.
    
    Args:
        tenant_id: Tenant identifier
        approver_id: Approver identifier
        
    Returns:
        List of pending approvals
    """
    try:
        approver_role = get_user_role(approver_id)
        pending_approvals = []
        
        for record in reward_manager.reward_records.values():
            if (record.tenant_id == tenant_id and 
                record.status == RewardStatus.PENDING and
                check_approval_permission(approver_id, record.approval_level)):
                
                approval_info = {
                    "reward_id": str(record.id),
                    "user_id": record.user_id,
                    "reward_type": record.reward_type.value,
                    "amount": float(record.amount),
                    "approval_level": record.approval_level.value,
                    "period_start": record.period_start.isoformat(),
                    "period_end": record.period_end.isoformat(),
                    "created_at": record.created_at.isoformat(),
                    "calculation_details": record.calculation.to_dict() if record.calculation else None
                }
                pending_approvals.append(approval_info)
        
        return {
            "pending_approvals": pending_approvals,
            "approver_role": approver_role,
            "total_count": len(pending_approvals)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve", response_model=RewardResponse)
async def approve_reward(request: RewardApprovalRequest):
    """
    Approve or reject a reward.
    
    Args:
        request: Approval request
        
    Returns:
        Approval result
    """
    try:
        # Get reward record
        record = reward_manager.reward_records.get(request.reward_id)
        if not record:
            raise HTTPException(status_code=404, detail="Reward record not found")
        
        # Check approval permission
        if not check_approval_permission(request.approver_id, record.approval_level):
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions to approve this reward"
            )
        
        # Process approval
        if request.approved:
            record.status = RewardStatus.APPROVED
            record.approved_by = request.approver_id
            record.approved_at = datetime.now()
            record.notes = request.notes
            message = "Reward approved successfully"
        else:
            record.status = RewardStatus.REJECTED
            record.notes = request.notes
            message = "Reward rejected"
        
        # Process approval workflow
        approval_result = reward_manager.approval_workflow.process_approval(
            reward_id=request.reward_id,
            approver_id=request.approver_id,
            approver_role=get_user_role(request.approver_id),
            approved=request.approved,
            notes=request.notes
        )
        
        return RewardResponse(
            success=True,
            message=message,
            data={
                "reward_id": request.reward_id,
                "new_status": record.status.value,
                "approval_result": approval_result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pay", response_model=RewardResponse)
async def process_reward_payments(
    request: RewardPaymentRequest,
    processed_by: str = Query(..., description="User processing payments")
):
    """
    Process payments for approved rewards.
    
    Args:
        request: Payment request
        processed_by: User processing payments
        
    Returns:
        Payment processing results
    """
    try:
        # Process payments
        payment_results = reward_manager.process_reward_payments(request.reward_ids)
        
        return RewardResponse(
            success=True,
            message=f"Processed {payment_results['payment_count']} payments totaling ${payment_results['total_amount']:.2f}",
            data={
                "payment_results": payment_results,
                "processed_by": processed_by,
                "processed_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_reward_statistics(
    tenant_id: str = Query(..., description="Tenant identifier"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter")
):
    """
    Get reward distribution statistics.
    
    Args:
        tenant_id: Tenant identifier
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        Reward statistics
    """
    try:
        stats = reward_manager.get_reward_statistics(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "statistics": stats,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def generate_reward_report(
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_start: date = Query(..., description="Report period start"),
    period_end: date = Query(..., description="Report period end")
):
    """
    Generate comprehensive reward report.
    
    Args:
        tenant_id: Tenant identifier
        period_start: Report period start
        period_end: Report period end
        
    Returns:
        Comprehensive reward report
    """
    try:
        report = reward_manager.generate_reward_report(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end
        )
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/effectiveness")
async def evaluate_reward_effectiveness(
    tenant_id: str = Query(..., description="Tenant identifier"),
    evaluation_period: int = Query(90, description="Evaluation period in days")
):
    """
    Evaluate reward program effectiveness.
    
    Args:
        tenant_id: Tenant identifier
        evaluation_period: Evaluation period in days
        
    Returns:
        Reward effectiveness analysis
    """
    try:
        effectiveness = reward_manager.evaluate_reward_effectiveness(
            tenant_id=tenant_id,
            evaluation_period=evaluation_period
        )
        
        return effectiveness
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}")
async def get_user_rewards(
    user_id: str,
    tenant_id: str = Query(..., description="Tenant identifier"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter")
):
    """
    Get rewards for a specific user.
    
    Args:
        user_id: User identifier
        tenant_id: Tenant identifier
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        User's reward history
    """
    try:
        user_rewards = []
        total_amount = Decimal("0.00")
        
        for record in reward_manager.reward_records.values():
            if (record.user_id == user_id and 
                record.tenant_id == tenant_id):
                
                # Apply date filters
                if start_date and record.period_start < start_date:
                    continue
                if end_date and record.period_end > end_date:
                    continue
                
                user_rewards.append(record.to_dict())
                total_amount += record.amount
        
        # Sort by creation date (newest first)
        user_rewards.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "user_id": user_id,
            "rewards": user_rewards,
            "summary": {
                "total_rewards": len(user_rewards),
                "total_amount": float(total_amount),
                "by_status": {},
                "by_type": {}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_reward_types():
    """
    Get available reward types and their descriptions.
    
    Returns:
        List of reward types
    """
    try:
        reward_types = {}
        for reward_type in RewardType:
            reward_types[reward_type.value] = {
                "name": reward_type.value,
                "description": f"{reward_type.value.replace('_', ' ').title()} reward"
            }
        
        return {
            "reward_types": reward_types,
            "approval_levels": [level.value for level in ApprovalLevel],
            "frequencies": [freq.value for freq in RewardFrequency]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criteria")
async def update_reward_criteria(
    reward_type: RewardType,
    criteria_updates: Dict[str, Any],
    updated_by: str = Query(..., description="User updating criteria")
):
    """
    Update reward calculation criteria.
    
    Args:
        reward_type: Type of reward to update
        criteria_updates: Criteria updates
        updated_by: User making updates
        
    Returns:
        Update confirmation
    """
    try:
        # Get current criteria
        current_criteria = reward_manager.calculation_engine.reward_criteria.get(reward_type)
        if not current_criteria:
            raise HTTPException(status_code=404, detail="Reward type not found")
        
        # Update criteria (this would typically validate and save to database)
        updated_fields = []
        for field, value in criteria_updates.items():
            if hasattr(current_criteria, field):
                setattr(current_criteria, field, value)
                updated_fields.append(field)
        
        return {
            "reward_type": reward_type.value,
            "updated_fields": updated_fields,
            "updated_by": updated_by,
            "updated_at": datetime.now().isoformat(),
            "message": "Reward criteria updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-log")
async def get_reward_audit_log(
    tenant_id: str = Query(..., description="Tenant identifier"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(100, description="Maximum number of records")
):
    """
    Get reward system audit log.
    
    Args:
        tenant_id: Tenant identifier
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of records
        
    Returns:
        Audit log entries
    """
    try:
        audit_entries = []
        
        for record in reward_manager.reward_records.values():
            if record.tenant_id != tenant_id:
                continue
            
            # Apply date filters
            if start_date and record.created_at.date() < start_date:
                continue
            if end_date and record.created_at.date() > end_date:
                continue
            
            audit_entry = {
                "reward_id": str(record.id),
                "user_id": record.user_id,
                "reward_type": record.reward_type.value,
                "amount": float(record.amount),
                "status": record.status.value,
                "created_at": record.created_at.isoformat(),
                "approved_by": record.approved_by,
                "approved_at": record.approved_at.isoformat() if record.approved_at else None,
                "paid_at": record.paid_at.isoformat() if record.paid_at else None,
                "notes": record.notes
            }
            audit_entries.append(audit_entry)
        
        # Sort by creation time (newest first) and limit
        audit_entries.sort(key=lambda x: x["created_at"], reverse=True)
        audit_entries = audit_entries[:limit]
        
        return {
            "audit_entries": audit_entries,
            "total_count": len(audit_entries),
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))