"""
Advanced Reward System for SuperInsight Platform.

Extends the base reward system with comprehensive reward calculation,
performance evaluation, and payout processing capabilities.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from uuid import UUID, uuid4
import logging
import statistics

from src.billing.reward_system import (
    RewardType, RewardStatus, ApprovalLevel, RewardFrequency,
    RewardCriteria, RewardCalculation, RewardRecord,
    RewardCalculationEngine, RewardApprovalWorkflow, RewardDistributionManager
)

logger = logging.getLogger(__name__)


class BonusType(str, Enum):
    """Bonus type enumeration."""
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    COLLABORATION = "collaboration"
    INNOVATION = "innovation"
    MILESTONE = "milestone"
    RETENTION = "retention"
    REFERRAL = "referral"


class PerformanceLevel(str, Enum):
    """Performance level enumeration."""
    EXCEPTIONAL = "exceptional"
    EXCELLENT = "excellent"
    GOOD = "good"
    SATISFACTORY = "satisfactory"
    NEEDS_IMPROVEMENT = "needs_improvement"


@dataclass
class PerformanceMetrics:
    """Performance metrics for evaluation."""
    user_id: str
    period_start: date
    period_end: date
    quality_score: float
    efficiency_score: float
    collaboration_score: float
    consistency_score: float
    innovation_score: float
    overall_score: float
    level: PerformanceLevel
    tasks_completed: int
    annotations_count: int
    accuracy_rate: float
    on_time_rate: float
    peer_feedback_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BonusCalculation:
    """Bonus calculation details."""
    bonus_type: BonusType
    base_amount: Decimal
    multiplier: float
    final_amount: Decimal
    calculation_details: Dict[str, Any]
    eligibility_criteria: List[str]
    criteria_met: List[str]


@dataclass
class ComprehensiveReward:
    """Comprehensive reward calculation result."""
    user_id: str
    period: Tuple[date, date]
    base_reward: Decimal
    quality_bonus: Decimal
    efficiency_bonus: Decimal
    collaboration_bonus: Decimal
    milestone_rewards: List[Dict[str, Any]]
    total_reward: Decimal
    performance_metrics: PerformanceMetrics
    bonus_breakdown: List[BonusCalculation]
    approval_status: str
    calculated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PayoutRecord:
    """Payout record for tracking payments."""
    payout_id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    tenant_id: str = ""
    reward_ids: List[str] = field(default_factory=list)
    total_amount: Decimal = Decimal("0")
    currency: str = "CNY"
    payment_method: str = "bank_transfer"
    status: str = "pending"
    scheduled_date: Optional[date] = None
    processed_date: Optional[datetime] = None
    reference_number: Optional[str] = None
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceEvaluator:
    """
    Performance evaluation engine.
    
    Evaluates user performance across multiple dimensions
    for reward calculation.
    """
    
    def __init__(self):
        self.weights = {
            'quality': 0.30,
            'efficiency': 0.25,
            'collaboration': 0.15,
            'consistency': 0.15,
            'innovation': 0.15
        }
        
        self.level_thresholds = {
            PerformanceLevel.EXCEPTIONAL: 0.95,
            PerformanceLevel.EXCELLENT: 0.85,
            PerformanceLevel.GOOD: 0.70,
            PerformanceLevel.SATISFACTORY: 0.55,
            PerformanceLevel.NEEDS_IMPROVEMENT: 0.0
        }
    
    async def evaluate(self, user_id: str, evaluation_period: Tuple[date, date],
                      performance_data: Dict[str, Any] = None) -> PerformanceMetrics:
        """Evaluate user performance for a period."""
        performance_data = performance_data or {}
        
        # Get individual scores
        quality_score = await self._calculate_quality_score(user_id, evaluation_period, performance_data)
        efficiency_score = await self._calculate_efficiency_score(user_id, evaluation_period, performance_data)
        collaboration_score = await self._calculate_collaboration_score(user_id, evaluation_period, performance_data)
        consistency_score = await self._calculate_consistency_score(user_id, evaluation_period, performance_data)
        innovation_score = await self._calculate_innovation_score(user_id, evaluation_period, performance_data)
        
        # Calculate overall score
        overall_score = (
            quality_score * self.weights['quality'] +
            efficiency_score * self.weights['efficiency'] +
            collaboration_score * self.weights['collaboration'] +
            consistency_score * self.weights['consistency'] +
            innovation_score * self.weights['innovation']
        )
        
        # Determine performance level
        level = self._determine_level(overall_score)
        
        # Get additional metrics
        tasks_completed = performance_data.get('tasks_completed', 0)
        annotations_count = performance_data.get('annotations_count', 0)
        accuracy_rate = performance_data.get('accuracy_rate', 0.0)
        on_time_rate = performance_data.get('on_time_rate', 0.0)
        peer_feedback = performance_data.get('peer_feedback_score', 0.0)
        
        return PerformanceMetrics(
            user_id=user_id,
            period_start=evaluation_period[0],
            period_end=evaluation_period[1],
            quality_score=quality_score,
            efficiency_score=efficiency_score,
            collaboration_score=collaboration_score,
            consistency_score=consistency_score,
            innovation_score=innovation_score,
            overall_score=overall_score,
            level=level,
            tasks_completed=tasks_completed,
            annotations_count=annotations_count,
            accuracy_rate=accuracy_rate,
            on_time_rate=on_time_rate,
            peer_feedback_score=peer_feedback
        )
    
    async def _calculate_quality_score(self, user_id: str, period: Tuple[date, date],
                                      data: Dict[str, Any]) -> float:
        """Calculate quality score."""
        # Would integrate with quality assessment system
        base_score = data.get('quality_score', 0.80)
        accuracy = data.get('accuracy_rate', 0.85)
        defect_rate = data.get('defect_rate', 0.05)
        
        # Weighted calculation
        score = base_score * 0.5 + accuracy * 0.3 + (1 - defect_rate) * 0.2
        return min(1.0, max(0.0, score))
    
    async def _calculate_efficiency_score(self, user_id: str, period: Tuple[date, date],
                                         data: Dict[str, Any]) -> float:
        """Calculate efficiency score."""
        items_per_hour = data.get('items_per_hour', 10)
        expected_items = data.get('expected_items_per_hour', 12)
        on_time_rate = data.get('on_time_rate', 0.90)
        
        efficiency_ratio = min(1.0, items_per_hour / expected_items) if expected_items > 0 else 0
        score = efficiency_ratio * 0.6 + on_time_rate * 0.4
        return min(1.0, max(0.0, score))
    
    async def _calculate_collaboration_score(self, user_id: str, period: Tuple[date, date],
                                            data: Dict[str, Any]) -> float:
        """Calculate collaboration score."""
        peer_feedback = data.get('peer_feedback_score', 0.75)
        team_contribution = data.get('team_contribution', 0.80)
        knowledge_sharing = data.get('knowledge_sharing', 0.70)
        
        score = peer_feedback * 0.4 + team_contribution * 0.35 + knowledge_sharing * 0.25
        return min(1.0, max(0.0, score))
    
    async def _calculate_consistency_score(self, user_id: str, period: Tuple[date, date],
                                          data: Dict[str, Any]) -> float:
        """Calculate consistency score."""
        daily_scores = data.get('daily_quality_scores', [])
        if not daily_scores:
            return 0.75  # Default
        
        avg_score = statistics.mean(daily_scores)
        std_dev = statistics.stdev(daily_scores) if len(daily_scores) > 1 else 0
        
        # Lower variance = higher consistency
        consistency = max(0, 1 - std_dev * 2)
        score = avg_score * 0.6 + consistency * 0.4
        return min(1.0, max(0.0, score))
    
    async def _calculate_innovation_score(self, user_id: str, period: Tuple[date, date],
                                         data: Dict[str, Any]) -> float:
        """Calculate innovation score."""
        process_improvements = data.get('process_improvements', 0)
        suggestions_accepted = data.get('suggestions_accepted', 0)
        new_methods_adopted = data.get('new_methods_adopted', 0)
        
        # Normalize scores
        improvement_score = min(1.0, process_improvements / 3)
        suggestion_score = min(1.0, suggestions_accepted / 5)
        adoption_score = min(1.0, new_methods_adopted / 2)
        
        score = improvement_score * 0.4 + suggestion_score * 0.35 + adoption_score * 0.25
        return min(1.0, max(0.0, score))
    
    def _determine_level(self, score: float) -> PerformanceLevel:
        """Determine performance level from score."""
        for level, threshold in self.level_thresholds.items():
            if score >= threshold:
                return level
        return PerformanceLevel.NEEDS_IMPROVEMENT


class BonusCalculator:
    """
    Bonus calculation engine.
    
    Calculates various types of bonuses based on performance.
    """
    
    def __init__(self):
        self.bonus_configs = {
            BonusType.QUALITY: {
                'base_rate': Decimal("0.15"),  # 15% of base
                'threshold': 0.90,
                'max_multiplier': 2.0
            },
            BonusType.EFFICIENCY: {
                'base_rate': Decimal("0.10"),
                'threshold': 0.85,
                'max_multiplier': 1.5
            },
            BonusType.COLLABORATION: {
                'base_rate': Decimal("0.08"),
                'threshold': 0.80,
                'max_multiplier': 1.3
            },
            BonusType.INNOVATION: {
                'base_rate': Decimal("0.12"),
                'threshold': 0.75,
                'max_multiplier': 2.5
            },
            BonusType.MILESTONE: {
                'fixed_amounts': {
                    '100_tasks': Decimal("50.00"),
                    '500_tasks': Decimal("200.00"),
                    '1000_tasks': Decimal("500.00"),
                    'perfect_week': Decimal("100.00"),
                    'perfect_month': Decimal("300.00")
                }
            }
        }
    
    async def calculate_quality_bonus(self, user_id: str, 
                                     quality_score: float,
                                     base_earnings: Decimal = Decimal("1000")) -> Decimal:
        """Calculate quality bonus."""
        config = self.bonus_configs[BonusType.QUALITY]
        
        if quality_score < config['threshold']:
            return Decimal("0")
        
        # Calculate multiplier based on score above threshold
        excess = quality_score - config['threshold']
        multiplier = min(1 + excess * 10, config['max_multiplier'])
        
        bonus = base_earnings * config['base_rate'] * Decimal(str(multiplier))
        return bonus.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    async def calculate_efficiency_bonus(self, user_id: str,
                                        efficiency_score: float,
                                        base_earnings: Decimal = Decimal("1000")) -> Decimal:
        """Calculate efficiency bonus."""
        config = self.bonus_configs[BonusType.EFFICIENCY]
        
        if efficiency_score < config['threshold']:
            return Decimal("0")
        
        excess = efficiency_score - config['threshold']
        multiplier = min(1 + excess * 5, config['max_multiplier'])
        
        bonus = base_earnings * config['base_rate'] * Decimal(str(multiplier))
        return bonus.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    async def calculate_collaboration_bonus(self, user_id: str,
                                           collaboration_score: float,
                                           base_earnings: Decimal = Decimal("1000")) -> Decimal:
        """Calculate collaboration bonus."""
        config = self.bonus_configs[BonusType.COLLABORATION]
        
        if collaboration_score < config['threshold']:
            return Decimal("0")
        
        excess = collaboration_score - config['threshold']
        multiplier = min(1 + excess * 3, config['max_multiplier'])
        
        bonus = base_earnings * config['base_rate'] * Decimal(str(multiplier))
        return bonus.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    async def calculate_milestone_bonuses(self, user_id: str,
                                         milestones_achieved: List[str]) -> List[Dict[str, Any]]:
        """Calculate milestone bonuses."""
        config = self.bonus_configs[BonusType.MILESTONE]
        bonuses = []
        
        for milestone in milestones_achieved:
            if milestone in config['fixed_amounts']:
                bonuses.append({
                    'milestone': milestone,
                    'amount': float(config['fixed_amounts'][milestone]),
                    'achieved_at': datetime.now().isoformat()
                })
        
        return bonuses


class PayoutProcessor:
    """
    Payout processing engine.
    
    Handles reward payment processing and tracking.
    """
    
    def __init__(self):
        self.payouts: Dict[str, PayoutRecord] = {}
        self.payment_methods = ['bank_transfer', 'paypal', 'alipay', 'wechat_pay']
    
    async def create_payout(self, user_id: str, tenant_id: str,
                           reward_ids: List[str], total_amount: Decimal,
                           payment_method: str = "bank_transfer",
                           scheduled_date: date = None) -> PayoutRecord:
        """Create a payout record."""
        payout = PayoutRecord(
            user_id=user_id,
            tenant_id=tenant_id,
            reward_ids=reward_ids,
            total_amount=total_amount,
            payment_method=payment_method,
            scheduled_date=scheduled_date or date.today() + timedelta(days=7),
            status="pending"
        )
        
        self.payouts[str(payout.payout_id)] = payout
        logger.info(f"Created payout {payout.payout_id} for user {user_id}")
        return payout
    
    async def process_payout(self, payout_id: str) -> Dict[str, Any]:
        """Process a payout."""
        payout = self.payouts.get(payout_id)
        if not payout:
            return {'success': False, 'error': 'Payout not found'}
        
        if payout.status != 'pending':
            return {'success': False, 'error': f'Payout status is {payout.status}'}
        
        try:
            # Simulate payment processing
            payout.status = 'processing'
            
            # Generate reference number
            payout.reference_number = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{payout_id[:8]}"
            
            # Mark as completed
            payout.status = 'completed'
            payout.processed_date = datetime.now()
            
            logger.info(f"Processed payout {payout_id}, ref: {payout.reference_number}")
            
            return {
                'success': True,
                'payout_id': payout_id,
                'reference_number': payout.reference_number,
                'amount': float(payout.total_amount),
                'processed_at': payout.processed_date.isoformat()
            }
            
        except Exception as e:
            payout.status = 'failed'
            payout.notes = str(e)
            logger.error(f"Failed to process payout {payout_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_payout_history(self, user_id: str, 
                                start_date: date = None,
                                end_date: date = None) -> List[Dict[str, Any]]:
        """Get payout history for a user."""
        history = []
        
        for payout in self.payouts.values():
            if payout.user_id != user_id:
                continue
            
            if start_date and payout.scheduled_date < start_date:
                continue
            if end_date and payout.scheduled_date > end_date:
                continue
            
            history.append({
                'payout_id': str(payout.payout_id),
                'amount': float(payout.total_amount),
                'currency': payout.currency,
                'status': payout.status,
                'payment_method': payout.payment_method,
                'scheduled_date': payout.scheduled_date.isoformat() if payout.scheduled_date else None,
                'processed_date': payout.processed_date.isoformat() if payout.processed_date else None,
                'reference_number': payout.reference_number
            })
        
        return sorted(history, key=lambda x: x['scheduled_date'] or '', reverse=True)


class AdvancedRewardSystem(RewardDistributionManager):
    """
    Advanced reward system with comprehensive reward calculation.
    
    Extends base reward system with multi-dimensional bonus calculation,
    performance evaluation, and payout processing.
    """
    
    def __init__(self):
        super().__init__()
        self.performance_evaluator = PerformanceEvaluator()
        self.bonus_calculator = BonusCalculator()
        self.payout_processor = PayoutProcessor()
    
    async def calculate_comprehensive_rewards(
        self, 
        user_id: str,
        evaluation_period: Tuple[date, date],
        performance_data: Dict[str, Any] = None,
        base_earnings: Decimal = Decimal("1000")
    ) -> ComprehensiveReward:
        """Calculate comprehensive rewards for a user."""
        performance_data = performance_data or {}
        
        # Evaluate performance
        performance_metrics = await self.performance_evaluator.evaluate(
            user_id, evaluation_period, performance_data
        )
        
        # Calculate base reward from parent
        base_reward = base_earnings
        
        # Calculate quality bonus
        quality_bonus = await self.bonus_calculator.calculate_quality_bonus(
            user_id, performance_metrics.quality_score, base_earnings
        )
        
        # Calculate efficiency bonus
        efficiency_bonus = await self.bonus_calculator.calculate_efficiency_bonus(
            user_id, performance_metrics.efficiency_score, base_earnings
        )
        
        # Calculate collaboration bonus
        collaboration_bonus = await self.bonus_calculator.calculate_collaboration_bonus(
            user_id, performance_metrics.collaboration_score, base_earnings
        )
        
        # Calculate milestone rewards
        milestones_achieved = performance_data.get('milestones_achieved', [])
        milestone_rewards = await self.bonus_calculator.calculate_milestone_bonuses(
            user_id, milestones_achieved
        )
        
        # Calculate total
        milestone_total = sum(Decimal(str(m['amount'])) for m in milestone_rewards)
        total_reward = (
            base_reward + quality_bonus + efficiency_bonus + 
            collaboration_bonus + milestone_total
        )
        
        # Build bonus breakdown
        bonus_breakdown = []
        
        if quality_bonus > 0:
            bonus_breakdown.append(BonusCalculation(
                bonus_type=BonusType.QUALITY,
                base_amount=base_earnings * Decimal("0.15"),
                multiplier=float(quality_bonus / (base_earnings * Decimal("0.15"))) if base_earnings > 0 else 0,
                final_amount=quality_bonus,
                calculation_details={'quality_score': performance_metrics.quality_score},
                eligibility_criteria=['quality_score >= 0.90'],
                criteria_met=['quality_score >= 0.90'] if performance_metrics.quality_score >= 0.90 else []
            ))
        
        if efficiency_bonus > 0:
            bonus_breakdown.append(BonusCalculation(
                bonus_type=BonusType.EFFICIENCY,
                base_amount=base_earnings * Decimal("0.10"),
                multiplier=float(efficiency_bonus / (base_earnings * Decimal("0.10"))) if base_earnings > 0 else 0,
                final_amount=efficiency_bonus,
                calculation_details={'efficiency_score': performance_metrics.efficiency_score},
                eligibility_criteria=['efficiency_score >= 0.85'],
                criteria_met=['efficiency_score >= 0.85'] if performance_metrics.efficiency_score >= 0.85 else []
            ))
        
        if collaboration_bonus > 0:
            bonus_breakdown.append(BonusCalculation(
                bonus_type=BonusType.COLLABORATION,
                base_amount=base_earnings * Decimal("0.08"),
                multiplier=float(collaboration_bonus / (base_earnings * Decimal("0.08"))) if base_earnings > 0 else 0,
                final_amount=collaboration_bonus,
                calculation_details={'collaboration_score': performance_metrics.collaboration_score},
                eligibility_criteria=['collaboration_score >= 0.80'],
                criteria_met=['collaboration_score >= 0.80'] if performance_metrics.collaboration_score >= 0.80 else []
            ))
        
        # Determine approval status
        approval_status = "auto_approved" if total_reward < Decimal("500") else "pending_approval"
        
        return ComprehensiveReward(
            user_id=user_id,
            period=evaluation_period,
            base_reward=base_reward,
            quality_bonus=quality_bonus,
            efficiency_bonus=efficiency_bonus,
            collaboration_bonus=collaboration_bonus,
            milestone_rewards=milestone_rewards,
            total_reward=total_reward,
            performance_metrics=performance_metrics,
            bonus_breakdown=bonus_breakdown,
            approval_status=approval_status
        )
    
    async def process_reward_payout(self, user_id: str, tenant_id: str,
                                   reward: ComprehensiveReward,
                                   payment_method: str = "bank_transfer") -> Dict[str, Any]:
        """Process payout for a comprehensive reward."""
        # Create payout record
        payout = await self.payout_processor.create_payout(
            user_id=user_id,
            tenant_id=tenant_id,
            reward_ids=[f"reward_{user_id}_{reward.period[0].isoformat()}"],
            total_amount=reward.total_reward,
            payment_method=payment_method
        )
        
        # Process if auto-approved
        if reward.approval_status == "auto_approved":
            result = await self.payout_processor.process_payout(str(payout.payout_id))
            return result
        
        return {
            'success': True,
            'payout_id': str(payout.payout_id),
            'status': 'pending_approval',
            'amount': float(reward.total_reward),
            'message': 'Payout created, pending approval'
        }
    
    async def get_reward_summary(self, user_id: str, 
                                period_start: date,
                                period_end: date) -> Dict[str, Any]:
        """Get reward summary for a user."""
        # Get payout history
        payout_history = await self.payout_processor.get_payout_history(
            user_id, period_start, period_end
        )
        
        # Calculate totals
        total_paid = sum(
            p['amount'] for p in payout_history 
            if p['status'] == 'completed'
        )
        total_pending = sum(
            p['amount'] for p in payout_history 
            if p['status'] == 'pending'
        )
        
        return {
            'user_id': user_id,
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            },
            'total_paid': total_paid,
            'total_pending': total_pending,
            'payout_count': len(payout_history),
            'recent_payouts': payout_history[:5]
        }


def get_advanced_reward_system() -> AdvancedRewardSystem:
    """Get advanced reward system instance."""
    return AdvancedRewardSystem()
