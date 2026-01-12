"""
Quality Management API endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from src.database.connection import get_db
from src.security.auth import get_current_user
from src.models.user import User

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


class QualityRule(BaseModel):
    id: str
    name: str
    description: str
    type: str = Field(..., description="Rule type: semantic, syntactic, completeness, consistency, accuracy")
    enabled: bool
    priority: str = Field(..., description="Priority: low, medium, high, critical")
    threshold: float
    conditions: List[Any] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    last_executed: Optional[str] = None
    execution_count: int = 0


class QualityMetrics(BaseModel):
    overall_score: float
    total_samples: int
    passed_samples: int
    failed_samples: int
    trend_data: List[Dict[str, Any]] = Field(default_factory=list)
    score_distribution: List[Dict[str, Any]] = Field(default_factory=list)
    rule_violations: List[Dict[str, Any]] = Field(default_factory=list)


class QualityReport(BaseModel):
    id: str
    name: str
    type: str = Field(..., description="Report type: daily, weekly, monthly, custom")
    overall_score: float
    semantic_score: float
    syntactic_score: float
    completeness_score: float
    consistency_score: float
    accuracy_score: float
    total_samples: int
    passed_samples: int
    failed_samples: int
    created_at: str


class CreateRuleRequest(BaseModel):
    name: str
    description: str
    type: str
    priority: str
    threshold: float
    enabled: bool = True


@router.get("/rules", response_model=List[QualityRule])
async def get_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get quality rules"""
    # Mock data
    rules = [
        {
            "id": "rule1",
            "name": "语义一致性检查",
            "description": "检查相似样本的标签一致性",
            "type": "semantic",
            "enabled": True,
            "priority": "high",
            "threshold": 0.9,
            "conditions": [],
            "actions": ["alert", "flag"],
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-20T10:00:00Z",
            "last_executed": "2025-01-20T09:00:00Z",
            "execution_count": 25
        },
        {
            "id": "rule2",
            "name": "文本长度验证",
            "description": "检查标注文本是否满足最小长度要求",
            "type": "syntactic",
            "enabled": True,
            "priority": "medium",
            "threshold": 0.8,
            "conditions": [],
            "actions": ["warn"],
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-20T10:00:00Z",
            "last_executed": "2025-01-20T09:00:00Z",
            "execution_count": 18
        }
    ]
    return rules[skip:skip + limit]


@router.post("/rules", response_model=QualityRule)
async def create_rule(
    request: CreateRuleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new quality rule"""
    # Mock implementation
    rule = {
        "id": f"rule_{len(request.name)}",
        "name": request.name,
        "description": request.description,
        "type": request.type,
        "enabled": request.enabled,
        "priority": request.priority,
        "threshold": request.threshold,
        "conditions": [],
        "actions": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "execution_count": 0
    }
    return rule


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    request: CreateRuleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a quality rule"""
    # Mock implementation
    return {"message": f"Rule {rule_id} updated successfully"}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a quality rule"""
    # Mock implementation
    return {"message": f"Rule {rule_id} deleted successfully"}


@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: str,
    enabled: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle rule enabled status"""
    # Mock implementation
    return {"message": f"Rule {rule_id} {'enabled' if enabled else 'disabled'}"}


@router.get("/metrics", response_model=QualityMetrics)
async def get_metrics(
    start_date: str = Query(...),
    end_date: str = Query(...),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quality metrics"""
    # Mock data
    metrics = {
        "overall_score": 0.92,
        "total_samples": 5000,
        "passed_samples": 4600,
        "failed_samples": 400,
        "trend_data": [
            {"date": "2025-01-14", "score": 0.85, "samples": 500},
            {"date": "2025-01-15", "score": 0.87, "samples": 520},
            {"date": "2025-01-16", "score": 0.89, "samples": 480},
            {"date": "2025-01-17", "score": 0.91, "samples": 510},
            {"date": "2025-01-18", "score": 0.93, "samples": 490},
            {"date": "2025-01-19", "score": 0.92, "samples": 505},
            {"date": "2025-01-20", "score": 0.94, "samples": 515}
        ],
        "score_distribution": [
            {"type": "semantic", "score": 0.94},
            {"type": "syntactic", "score": 0.91},
            {"type": "completeness", "score": 0.89},
            {"type": "consistency", "score": 0.93},
            {"type": "accuracy", "score": 0.95}
        ],
        "rule_violations": [
            {"rule": "语义一致性", "count": 25, "severity": "high"},
            {"rule": "文本格式", "count": 15, "severity": "medium"},
            {"rule": "数据完整性", "count": 10, "severity": "low"}
        ]
    }
    return metrics


@router.get("/reports", response_model=List[QualityReport])
async def get_reports(
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quality reports"""
    # Mock data
    reports = [
        {
            "id": "report1",
            "name": "每日质量报告 - 2025-01-20",
            "type": "daily",
            "overall_score": 0.92,
            "semantic_score": 0.94,
            "syntactic_score": 0.91,
            "completeness_score": 0.89,
            "consistency_score": 0.93,
            "accuracy_score": 0.95,
            "total_samples": 500,
            "passed_samples": 460,
            "failed_samples": 40,
            "created_at": "2025-01-20T18:00:00Z"
        },
        {
            "id": "report2",
            "name": "每日质量报告 - 2025-01-19",
            "type": "daily",
            "overall_score": 0.90,
            "semantic_score": 0.92,
            "syntactic_score": 0.89,
            "completeness_score": 0.87,
            "consistency_score": 0.91,
            "accuracy_score": 0.93,
            "total_samples": 480,
            "passed_samples": 432,
            "failed_samples": 48,
            "created_at": "2025-01-19T18:00:00Z"
        }
    ]
    return reports