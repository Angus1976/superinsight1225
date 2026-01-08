"""
Reward distribution system for quality-based incentives.

Implements multi-tier reward calculation, approval workflows,
and comprehensive reward analytics and effect evaluation.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4
import json
from collections import defaultdict
import pandas as pd
import numpy as np

from src.billing.models import BillingRecord


class RewardType(str, Enum):
    """Types of rewards."""
    QUALITY_BONUS = "quality_bonus"
    EFFICIENCY_BONUS = "efficiency_bonus"
    INNOVATION_BONUS = "innovation_bonus"
    CONSISTENCY_BONUS = "consistency_bonus"
    MILESTONE_BONUS = "milestone_bonus"
    TEAM_BONUS = "team_bonus"
    PENALTY_REDUCTION = "penalty_reduction"


class RewardStatus(str, Enum):
    """Reward processing status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


class ApprovalLevel(str, Enum):
    """Approval levels for rewards."""
    AUTO_APPROVED = "auto_approved"
    SUPERVISOR_APPROVAL = "supervisor_approval"
    MANAGER_APPROVAL = "manager_approval"
    EXECUTIVE_APPROVAL = "executive_approval"


class RewardFrequency(str, Enum):
    """Reward calculation frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class RewardCriteria:
    """Criteria for reward calculation."""
    reward_type: RewardType
    min_quality_score: float
    min_efficiency_score: float
    min_consistency_days: int
    base_amount: Decimal
    multiplier_factor: float
    max_amount: Optional[Decimal] = None
    requires_approval: bool = True
    approval_level: ApprovalLevel = ApprovalLevel.SUPERVISOR_APPROVAL


@dataclass
class RewardCalculation:
    """Reward calculation details."""
    user_id: str
    reward_type: RewardType
    base_amount: Decimal
    multiplier: float
    final_amount: Decimal
    quality_score: float
    efficiency_score: float
    consistency_days: int
    calculation_details: Dict[str, Any]
    criteria_met: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "reward_type": self.reward_type.value,
            "base_amount": float(self.base_amount),
            "multiplier": self.multiplier,
            "final_amount": float(self.final_amount),
            "quality_score": self.quality_score,
            "efficiency_score": self.efficiency_score,
            "consistency_days": self.consistency_days,
            "calculation_details": self.calculation_details,
            "criteria_met": self.criteria_met
        }


@dataclass
class RewardRecord:
    """Individual reward record."""
    id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    tenant_id: str = ""
    reward_type: RewardType = RewardType.QUALITY_BONUS
    amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    status: RewardStatus = RewardStatus.PENDING
    approval_level: ApprovalLevel = ApprovalLevel.AUTO_APPROVED
    calculation: Optional[RewardCalculation] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "reward_type": self.reward_type.value,
            "amount": float(self.amount),
            "status": self.status.value,
            "approval_level": self.approval_level.value,
            "calculation": self.calculation.to_dict() if self.calculation else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
            "metadata": self.metadata
        }


class QualityMetricsCalculator:
    """Calculator for quality-based metrics."""
    
    def __init__(self):
        """Initialize the calculator."""
        self.quality_weights = {
            "accuracy": 0.4,
            "consistency": 0.3,
            "completeness": 0.2,
            "timeliness": 0.1
        }
    
    def calculate_quality_score(self, user_id: str, period_start: date, 
                              period_end: date) -> float:
        """
        Calculate overall quality score for user in period.
        
        Args:
            user_id: User identifier
            period_start: Period start date
            period_end: Period end date
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        # This would typically fetch actual quality data from database
        # For demonstration, return simulated score
        base_score = 0.75 + (hash(user_id) % 25) / 100  # 0.75-1.0 range
        return min(1.0, base_score)
    
    def calculate_efficiency_score(self, user_id: str, period_start: date,
                                 period_end: date) -> float:
        """
        Calculate efficiency score based on time vs. output.
        
        Args:
            user_id: User identifier
            period_start: Period start date
            period_end: Period end date
            
        Returns:
            Efficiency score (0.0 to 1.0)
        """
        # Simulated efficiency calculation
        base_efficiency = 0.70 + (hash(user_id + "efficiency") % 30) / 100
        return min(1.0, base_efficiency)
    
    def calculate_consistency_days(self, user_id: str, period_start: date,
                                 period_end: date) -> int:
        """
        Calculate number of consistent quality days.
        
        Args:
            user_id: User identifier
            period_start: Period start date
            period_end: Period end date
            
        Returns:
            Number of consistent days
        """
        # Simulated consistency calculation
        total_days = (period_end - period_start).days + 1
        consistency_rate = 0.6 + (hash(user_id + "consistency") % 40) / 100
        return int(total_days * consistency_rate)
    
    def get_improvement_rate(self, user_id: str, current_period: Tuple[date, date],
                           previous_period: Tuple[date, date]) -> float:
        """
        Calculate improvement rate compared to previous period.
        
        Args:
            user_id: User identifier
            current_period: Current period (start, end)
            previous_period: Previous period (start, end)
            
        Returns:
            Improvement rate (-1.0 to 1.0)
        """
        current_score = self.calculate_quality_score(
            user_id, current_period[0], current_period[1]
        )
        previous_score = self.calculate_quality_score(
            user_id, previous_period[0], previous_period[1]
        )
        
        if previous_score == 0:
            return 0.0
        
        return (current_score - previous_score) / previous_score


class RewardCalculationEngine:
    """Engine for calculating various types of rewards."""
    
    def __init__(self):
        """Initialize the calculation engine."""
        self.metrics_calculator = QualityMetricsCalculator()
        
        # Default reward criteria
        self.reward_criteria = {
            RewardType.QUALITY_BONUS: RewardCriteria(
                reward_type=RewardType.QUALITY_BONUS,
                min_quality_score=0.85,
                min_efficiency_score=0.70,
                min_consistency_days=20,
                base_amount=Decimal("100.00"),
                multiplier_factor=2.0,
                max_amount=Decimal("500.00"),
                requires_approval=False,
                approval_level=ApprovalLevel.AUTO_APPROVED
            ),
            RewardType.EFFICIENCY_BONUS: RewardCriteria(
                reward_type=RewardType.EFFICIENCY_BONUS,
                min_quality_score=0.75,
                min_efficiency_score=0.90,
                min_consistency_days=15,
                base_amount=Decimal("80.00"),
                multiplier_factor=1.5,
                max_amount=Decimal("300.00"),
                requires_approval=False,
                approval_level=ApprovalLevel.AUTO_APPROVED
            ),
            RewardType.INNOVATION_BONUS: RewardCriteria(
                reward_type=RewardType.INNOVATION_BONUS,
                min_quality_score=0.80,
                min_efficiency_score=0.75,
                min_consistency_days=10,
                base_amount=Decimal("200.00"),
                multiplier_factor=3.0,
                max_amount=Decimal("1000.00"),
                requires_approval=True,
                approval_level=ApprovalLevel.MANAGER_APPROVAL
            ),
            RewardType.CONSISTENCY_BONUS: RewardCriteria(
                reward_type=RewardType.CONSISTENCY_BONUS,
                min_quality_score=0.80,
                min_efficiency_score=0.70,
                min_consistency_days=25,
                base_amount=Decimal("150.00"),
                multiplier_factor=1.2,
                max_amount=Decimal("400.00"),
                requires_approval=False,
                approval_level=ApprovalLevel.AUTO_APPROVED
            )
        }
    
    def calculate_quality_bonus(self, user_id: str, period_start: date,
                              period_end: date) -> Optional[RewardCalculation]:
        """
        Calculate quality bonus reward.
        
        Args:
            user_id: User identifier
            period_start: Period start date
            period_end: Period end date
            
        Returns:
            Reward calculation if eligible, None otherwise
        """
        criteria = self.reward_criteria[RewardType.QUALITY_BONUS]
        
        # Get metrics
        quality_score = self.metrics_calculator.calculate_quality_score(
            user_id, period_start, period_end
        )
        efficiency_score = self.metrics_calculator.calculate_efficiency_score(
            user_id, period_start, period_end
        )
        consistency_days = self.metrics_calculator.calculate_consistency_days(
            user_id, period_start, period_end
        )
        
        # Check eligibility
        criteria_met = []
        if quality_score >= criteria.min_quality_score:
            criteria_met.append(f"Quality score: {quality_score:.2f} >= {criteria.min_quality_score}")
        if efficiency_score >= criteria.min_efficiency_score:
            criteria_met.append(f"Efficiency score: {efficiency_score:.2f} >= {criteria.min_efficiency_score}")
        if consistency_days >= criteria.min_consistency_days:
            criteria_met.append(f"Consistency days: {consistency_days} >= {criteria.min_consistency_days}")
        
        # Must meet all criteria
        if len(criteria_met) < 3:
            return None
        
        # Calculate reward amount
        quality_multiplier = min(quality_score / criteria.min_quality_score, criteria.multiplier_factor)
        efficiency_multiplier = min(efficiency_score / criteria.min_efficiency_score, 1.5)
        consistency_multiplier = min(consistency_days / criteria.min_consistency_days, 1.3)
        
        total_multiplier = quality_multiplier * efficiency_multiplier * consistency_multiplier
        final_amount = criteria.base_amount * Decimal(str(total_multiplier))
        
        # Apply maximum limit
        if criteria.max_amount:
            final_amount = min(final_amount, criteria.max_amount)
        
        return RewardCalculation(
            user_id=user_id,
            reward_type=RewardType.QUALITY_BONUS,
            base_amount=criteria.base_amount,
            multiplier=total_multiplier,
            final_amount=final_amount,
            quality_score=quality_score,
            efficiency_score=efficiency_score,
            consistency_days=consistency_days,
            calculation_details={
                "quality_multiplier": quality_multiplier,
                "efficiency_multiplier": efficiency_multiplier,
                "consistency_multiplier": consistency_multiplier,
                "total_multiplier": total_multiplier
            },
            criteria_met=criteria_met
        )
    
    def calculate_efficiency_bonus(self, user_id: str, period_start: date,
                                 period_end: date) -> Optional[RewardCalculation]:
        """Calculate efficiency bonus reward."""
        criteria = self.reward_criteria[RewardType.EFFICIENCY_BONUS]
        
        quality_score = self.metrics_calculator.calculate_quality_score(
            user_id, period_start, period_end
        )
        efficiency_score = self.metrics_calculator.calculate_efficiency_score(
            user_id, period_start, period_end
        )
        consistency_days = self.metrics_calculator.calculate_consistency_days(
            user_id, period_start, period_end
        )
        
        # Check eligibility
        if (quality_score < criteria.min_quality_score or
            efficiency_score < criteria.min_efficiency_score or
            consistency_days < criteria.min_consistency_days):
            return None
        
        # Calculate reward with emphasis on efficiency
        efficiency_multiplier = min(efficiency_score / criteria.min_efficiency_score, criteria.multiplier_factor)
        final_amount = criteria.base_amount * Decimal(str(efficiency_multiplier))
        
        if criteria.max_amount:
            final_amount = min(final_amount, criteria.max_amount)
        
        return RewardCalculation(
            user_id=user_id,
            reward_type=RewardType.EFFICIENCY_BONUS,
            base_amount=criteria.base_amount,
            multiplier=efficiency_multiplier,
            final_amount=final_amount,
            quality_score=quality_score,
            efficiency_score=efficiency_score,
            consistency_days=consistency_days,
            calculation_details={
                "efficiency_multiplier": efficiency_multiplier
            },
            criteria_met=[
                f"Quality: {quality_score:.2f}",
                f"Efficiency: {efficiency_score:.2f}",
                f"Consistency: {consistency_days} days"
            ]
        )
    
    def calculate_innovation_bonus(self, user_id: str, period_start: date,
                                 period_end: date, innovation_metrics: Dict[str, Any]) -> Optional[RewardCalculation]:
        """
        Calculate innovation bonus reward.
        
        Args:
            user_id: User identifier
            period_start: Period start date
            period_end: Period end date
            innovation_metrics: Innovation-specific metrics
            
        Returns:
            Reward calculation if eligible
        """
        criteria = self.reward_criteria[RewardType.INNOVATION_BONUS]
        
        quality_score = self.metrics_calculator.calculate_quality_score(
            user_id, period_start, period_end
        )
        efficiency_score = self.metrics_calculator.calculate_efficiency_score(
            user_id, period_start, period_end
        )
        
        # Innovation-specific checks
        innovation_score = innovation_metrics.get("innovation_score", 0.0)
        process_improvements = innovation_metrics.get("process_improvements", 0)
        knowledge_sharing = innovation_metrics.get("knowledge_sharing", 0)
        
        if (quality_score < criteria.min_quality_score or
            efficiency_score < criteria.min_efficiency_score or
            innovation_score < 0.7):
            return None
        
        # Calculate innovation multiplier
        innovation_multiplier = (
            innovation_score * 1.5 +
            min(process_improvements / 3, 1.0) * 0.5 +
            min(knowledge_sharing / 5, 1.0) * 0.3
        )
        
        final_amount = criteria.base_amount * Decimal(str(innovation_multiplier))
        
        if criteria.max_amount:
            final_amount = min(final_amount, criteria.max_amount)
        
        return RewardCalculation(
            user_id=user_id,
            reward_type=RewardType.INNOVATION_BONUS,
            base_amount=criteria.base_amount,
            multiplier=innovation_multiplier,
            final_amount=final_amount,
            quality_score=quality_score,
            efficiency_score=efficiency_score,
            consistency_days=0,  # Not applicable for innovation
            calculation_details={
                "innovation_score": innovation_score,
                "process_improvements": process_improvements,
                "knowledge_sharing": knowledge_sharing,
                "innovation_multiplier": innovation_multiplier
            },
            criteria_met=[
                f"Innovation score: {innovation_score:.2f}",
                f"Process improvements: {process_improvements}",
                f"Knowledge sharing: {knowledge_sharing}"
            ]
        )
    
    def calculate_all_eligible_rewards(self, user_id: str, period_start: date,
                                     period_end: date, 
                                     innovation_metrics: Optional[Dict[str, Any]] = None) -> List[RewardCalculation]:
        """
        Calculate all eligible rewards for a user in a period.
        
        Args:
            user_id: User identifier
            period_start: Period start date
            period_end: Period end date
            innovation_metrics: Optional innovation metrics
            
        Returns:
            List of eligible reward calculations
        """
        rewards = []
        
        # Quality bonus
        quality_reward = self.calculate_quality_bonus(user_id, period_start, period_end)
        if quality_reward:
            rewards.append(quality_reward)
        
        # Efficiency bonus
        efficiency_reward = self.calculate_efficiency_bonus(user_id, period_start, period_end)
        if efficiency_reward:
            rewards.append(efficiency_reward)
        
        # Innovation bonus (if metrics provided)
        if innovation_metrics:
            innovation_reward = self.calculate_innovation_bonus(
                user_id, period_start, period_end, innovation_metrics
            )
            if innovation_reward:
                rewards.append(innovation_reward)
        
        # Consistency bonus
        consistency_reward = self.calculate_consistency_bonus(user_id, period_start, period_end)
        if consistency_reward:
            rewards.append(consistency_reward)
        
        return rewards
    
    def calculate_consistency_bonus(self, user_id: str, period_start: date,
                                  period_end: date) -> Optional[RewardCalculation]:
        """Calculate consistency bonus reward."""
        criteria = self.reward_criteria[RewardType.CONSISTENCY_BONUS]
        
        quality_score = self.metrics_calculator.calculate_quality_score(
            user_id, period_start, period_end
        )
        efficiency_score = self.metrics_calculator.calculate_efficiency_score(
            user_id, period_start, period_end
        )
        consistency_days = self.metrics_calculator.calculate_consistency_days(
            user_id, period_start, period_end
        )
        
        if (quality_score < criteria.min_quality_score or
            efficiency_score < criteria.min_efficiency_score or
            consistency_days < criteria.min_consistency_days):
            return None
        
        # Consistency multiplier based on days
        consistency_multiplier = min(consistency_days / criteria.min_consistency_days, criteria.multiplier_factor)
        final_amount = criteria.base_amount * Decimal(str(consistency_multiplier))
        
        if criteria.max_amount:
            final_amount = min(final_amount, criteria.max_amount)
        
        return RewardCalculation(
            user_id=user_id,
            reward_type=RewardType.CONSISTENCY_BONUS,
            base_amount=criteria.base_amount,
            multiplier=consistency_multiplier,
            final_amount=final_amount,
            quality_score=quality_score,
            efficiency_score=efficiency_score,
            consistency_days=consistency_days,
            calculation_details={
                "consistency_multiplier": consistency_multiplier
            },
            criteria_met=[
                f"Consistency: {consistency_days} days >= {criteria.min_consistency_days}"
            ]
        )


class RewardApprovalWorkflow:
    """Workflow for reward approval process."""
    
    def __init__(self):
        """Initialize the approval workflow."""
        self.approval_hierarchy = {
            ApprovalLevel.AUTO_APPROVED: [],
            ApprovalLevel.SUPERVISOR_APPROVAL: ["supervisor"],
            ApprovalLevel.MANAGER_APPROVAL: ["supervisor", "manager"],
            ApprovalLevel.EXECUTIVE_APPROVAL: ["supervisor", "manager", "executive"]
        }
        
        self.approval_limits = {
            ApprovalLevel.AUTO_APPROVED: Decimal("200.00"),
            ApprovalLevel.SUPERVISOR_APPROVAL: Decimal("500.00"),
            ApprovalLevel.MANAGER_APPROVAL: Decimal("2000.00"),
            ApprovalLevel.EXECUTIVE_APPROVAL: Decimal("10000.00")
        }
    
    def determine_approval_level(self, reward_amount: Decimal, 
                               reward_type: RewardType) -> ApprovalLevel:
        """
        Determine required approval level based on amount and type.
        
        Args:
            reward_amount: Reward amount
            reward_type: Type of reward
            
        Returns:
            Required approval level
        """
        # Innovation bonuses always require manager approval
        if reward_type == RewardType.INNOVATION_BONUS:
            return ApprovalLevel.MANAGER_APPROVAL
        
        # Determine by amount
        if reward_amount <= self.approval_limits[ApprovalLevel.AUTO_APPROVED]:
            return ApprovalLevel.AUTO_APPROVED
        elif reward_amount <= self.approval_limits[ApprovalLevel.SUPERVISOR_APPROVAL]:
            return ApprovalLevel.SUPERVISOR_APPROVAL
        elif reward_amount <= self.approval_limits[ApprovalLevel.MANAGER_APPROVAL]:
            return ApprovalLevel.MANAGER_APPROVAL
        else:
            return ApprovalLevel.EXECUTIVE_APPROVAL
    
    def create_approval_request(self, reward_record: RewardRecord) -> Dict[str, Any]:
        """
        Create approval request for reward.
        
        Args:
            reward_record: Reward record to approve
            
        Returns:
            Approval request details
        """
        required_approvers = self.approval_hierarchy[reward_record.approval_level]
        
        return {
            "reward_id": str(reward_record.id),
            "user_id": reward_record.user_id,
            "reward_type": reward_record.reward_type.value,
            "amount": float(reward_record.amount),
            "approval_level": reward_record.approval_level.value,
            "required_approvers": required_approvers,
            "pending_approvers": required_approvers.copy(),
            "approved_by": [],
            "created_at": datetime.now().isoformat(),
            "status": "pending_approval"
        }
    
    def process_approval(self, reward_id: str, approver_id: str, 
                        approver_role: str, approved: bool, 
                        notes: str = "") -> Dict[str, Any]:
        """
        Process approval decision.
        
        Args:
            reward_id: Reward identifier
            approver_id: Approver identifier
            approver_role: Approver's role
            approved: Whether approved or rejected
            notes: Approval notes
            
        Returns:
            Approval result
        """
        # This would typically update database records
        # For demonstration, return approval result
        
        return {
            "reward_id": reward_id,
            "approver_id": approver_id,
            "approver_role": approver_role,
            "approved": approved,
            "notes": notes,
            "processed_at": datetime.now().isoformat(),
            "next_action": "approved" if approved else "rejected"
        }


class RewardDistributionManager:
    """Manager for reward distribution and tracking."""
    
    def __init__(self):
        """Initialize the distribution manager."""
        self.calculation_engine = RewardCalculationEngine()
        self.approval_workflow = RewardApprovalWorkflow()
        self.reward_records: Dict[str, RewardRecord] = {}
        self.distribution_statistics = defaultdict(lambda: defaultdict(int))
    
    def calculate_period_rewards(self, tenant_id: str, user_ids: List[str],
                               period_start: date, period_end: date,
                               frequency: RewardFrequency = RewardFrequency.MONTHLY) -> List[RewardRecord]:
        """
        Calculate rewards for multiple users in a period.
        
        Args:
            tenant_id: Tenant identifier
            user_ids: List of user identifiers
            period_start: Period start date
            period_end: Period end date
            frequency: Reward calculation frequency
            
        Returns:
            List of reward records
        """
        reward_records = []
        
        for user_id in user_ids:
            # Calculate all eligible rewards
            calculations = self.calculation_engine.calculate_all_eligible_rewards(
                user_id, period_start, period_end
            )
            
            for calculation in calculations:
                # Determine approval level
                approval_level = self.approval_workflow.determine_approval_level(
                    calculation.final_amount, calculation.reward_type
                )
                
                # Create reward record
                record = RewardRecord(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    reward_type=calculation.reward_type,
                    amount=calculation.final_amount,
                    status=RewardStatus.APPROVED if approval_level == ApprovalLevel.AUTO_APPROVED else RewardStatus.PENDING,
                    approval_level=approval_level,
                    calculation=calculation,
                    period_start=period_start,
                    period_end=period_end,
                    metadata={
                        "frequency": frequency.value,
                        "auto_approved": approval_level == ApprovalLevel.AUTO_APPROVED
                    }
                )
                
                # Auto-approve if eligible
                if approval_level == ApprovalLevel.AUTO_APPROVED:
                    record.approved_by = "system"
                    record.approved_at = datetime.now()
                
                self.reward_records[str(record.id)] = record
                reward_records.append(record)
        
        return reward_records
    
    def process_reward_payments(self, reward_ids: List[str]) -> Dict[str, Any]:
        """
        Process payment for approved rewards.
        
        Args:
            reward_ids: List of reward identifiers to pay
            
        Returns:
            Payment processing results
        """
        results = {
            "successful_payments": [],
            "failed_payments": [],
            "total_amount": Decimal("0.00"),
            "payment_count": 0
        }
        
        for reward_id in reward_ids:
            record = self.reward_records.get(reward_id)
            if not record:
                results["failed_payments"].append({
                    "reward_id": reward_id,
                    "error": "Reward record not found"
                })
                continue
            
            if record.status != RewardStatus.APPROVED:
                results["failed_payments"].append({
                    "reward_id": reward_id,
                    "error": f"Reward not approved. Current status: {record.status.value}"
                })
                continue
            
            # Process payment (this would integrate with payment system)
            try:
                # Simulate payment processing
                record.status = RewardStatus.PAID
                record.paid_at = datetime.now()
                
                results["successful_payments"].append({
                    "reward_id": reward_id,
                    "user_id": record.user_id,
                    "amount": float(record.amount),
                    "reward_type": record.reward_type.value
                })
                
                results["total_amount"] += record.amount
                results["payment_count"] += 1
                
                # Update statistics
                self.distribution_statistics[record.tenant_id]["total_paid"] += float(record.amount)
                self.distribution_statistics[record.tenant_id]["payment_count"] += 1
                
            except Exception as e:
                results["failed_payments"].append({
                    "reward_id": reward_id,
                    "error": str(e)
                })
        
        return results
    
    def get_reward_statistics(self, tenant_id: str, 
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get reward distribution statistics.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Reward statistics
        """
        # Filter records by tenant and date range
        filtered_records = []
        for record in self.reward_records.values():
            if record.tenant_id != tenant_id:
                continue
            if start_date and record.period_start < start_date:
                continue
            if end_date and record.period_end > end_date:
                continue
            filtered_records.append(record)
        
        # Calculate statistics
        stats = {
            "total_rewards": len(filtered_records),
            "total_amount": sum(record.amount for record in filtered_records),
            "by_type": defaultdict(lambda: {"count": 0, "amount": Decimal("0.00")}),
            "by_status": defaultdict(int),
            "by_user": defaultdict(lambda: {"count": 0, "amount": Decimal("0.00")}),
            "approval_stats": {
                "auto_approved": 0,
                "pending_approval": 0,
                "manually_approved": 0,
                "rejected": 0
            },
            "payment_stats": {
                "paid": 0,
                "pending_payment": 0,
                "total_paid_amount": Decimal("0.00")
            }
        }
        
        for record in filtered_records:
            # By type
            stats["by_type"][record.reward_type.value]["count"] += 1
            stats["by_type"][record.reward_type.value]["amount"] += record.amount
            
            # By status
            stats["by_status"][record.status.value] += 1
            
            # By user
            stats["by_user"][record.user_id]["count"] += 1
            stats["by_user"][record.user_id]["amount"] += record.amount
            
            # Approval stats
            if record.approval_level == ApprovalLevel.AUTO_APPROVED:
                stats["approval_stats"]["auto_approved"] += 1
            elif record.status == RewardStatus.PENDING:
                stats["approval_stats"]["pending_approval"] += 1
            elif record.status == RewardStatus.APPROVED:
                stats["approval_stats"]["manually_approved"] += 1
            elif record.status == RewardStatus.REJECTED:
                stats["approval_stats"]["rejected"] += 1
            
            # Payment stats
            if record.status == RewardStatus.PAID:
                stats["payment_stats"]["paid"] += 1
                stats["payment_stats"]["total_paid_amount"] += record.amount
            elif record.status == RewardStatus.APPROVED:
                stats["payment_stats"]["pending_payment"] += 1
        
        # Convert defaultdicts to regular dicts and Decimals to floats
        stats["by_type"] = {
            k: {"count": v["count"], "amount": float(v["amount"])}
            for k, v in stats["by_type"].items()
        }
        stats["by_user"] = {
            k: {"count": v["count"], "amount": float(v["amount"])}
            for k, v in stats["by_user"].items()
        }
        stats["total_amount"] = float(stats["total_amount"])
        stats["payment_stats"]["total_paid_amount"] = float(stats["payment_stats"]["total_paid_amount"])
        
        return stats
    
    def generate_reward_report(self, tenant_id: str, period_start: date,
                             period_end: date) -> Dict[str, Any]:
        """
        Generate comprehensive reward report.
        
        Args:
            tenant_id: Tenant identifier
            period_start: Report period start
            period_end: Report period end
            
        Returns:
            Comprehensive reward report
        """
        stats = self.get_reward_statistics(tenant_id, period_start, period_end)
        
        # Get top performers
        user_stats = stats["by_user"]
        top_earners = sorted(
            user_stats.items(),
            key=lambda x: x[1]["amount"],
            reverse=True
        )[:10]
        
        # Calculate reward effectiveness
        total_users = len(user_stats)
        rewarded_users = len([u for u in user_stats.values() if u["count"] > 0])
        reward_participation_rate = rewarded_users / total_users if total_users > 0 else 0
        
        return {
            "report_period": {
                "start_date": period_start.isoformat(),
                "end_date": period_end.isoformat()
            },
            "summary": stats,
            "top_earners": [
                {"user_id": user_id, **user_data}
                for user_id, user_data in top_earners
            ],
            "effectiveness_metrics": {
                "total_users": total_users,
                "rewarded_users": rewarded_users,
                "participation_rate": reward_participation_rate,
                "average_reward_per_user": float(stats["total_amount"]) / rewarded_users if rewarded_users > 0 else 0
            },
            "generated_at": datetime.now().isoformat()
        }
    
    def evaluate_reward_effectiveness(self, tenant_id: str, 
                                    evaluation_period: int = 90) -> Dict[str, Any]:
        """
        Evaluate the effectiveness of reward programs.
        
        Args:
            tenant_id: Tenant identifier
            evaluation_period: Evaluation period in days
            
        Returns:
            Reward effectiveness analysis
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=evaluation_period)
        
        # Get reward statistics for the period
        stats = self.get_reward_statistics(tenant_id, start_date, end_date)
        
        # Calculate effectiveness metrics
        effectiveness = {
            "period_days": evaluation_period,
            "total_investment": float(stats["total_amount"]),
            "reward_distribution": stats["by_type"],
            "user_engagement": {
                "total_participants": len(stats["by_user"]),
                "average_rewards_per_user": len(stats["by_user"]) / stats["total_rewards"] if stats["total_rewards"] > 0 else 0
            },
            "quality_impact": {
                "estimated_quality_improvement": 0.15,  # Would be calculated from actual data
                "cost_per_quality_point": float(stats["total_amount"]) / 0.15 if stats["total_amount"] > 0 else 0
            },
            "roi_analysis": {
                "estimated_productivity_gain": 0.20,  # Would be calculated from actual data
                "estimated_cost_savings": float(stats["total_amount"]) * 1.5,  # Estimated
                "roi_percentage": 50.0  # Estimated ROI
            },
            "recommendations": self._generate_effectiveness_recommendations(stats)
        }
        
        return effectiveness
    
    def _generate_effectiveness_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on reward statistics."""
        recommendations = []
        
        # Analyze reward distribution
        total_amount = stats["total_amount"]
        by_type = stats["by_type"]
        
        if total_amount > 0:
            # Check if quality bonuses dominate
            quality_percentage = by_type.get("quality_bonus", {}).get("amount", 0) / total_amount
            if quality_percentage > 0.6:
                recommendations.append("Consider diversifying reward types to include more efficiency and innovation bonuses")
            
            # Check participation
            if len(stats["by_user"]) < 5:
                recommendations.append("Low participation rate - consider lowering reward thresholds or improving communication")
            
            # Check approval efficiency
            pending_percentage = stats["approval_stats"]["pending_approval"] / stats["total_rewards"]
            if pending_percentage > 0.3:
                recommendations.append("High percentage of pending approvals - consider increasing auto-approval limits")
        
        if not recommendations:
            recommendations.append("Reward system is performing well - continue current strategy")
        
        return recommendations