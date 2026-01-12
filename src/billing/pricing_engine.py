"""
Multi-dimensional Pricing Engine for SuperInsight Platform.

Provides flexible pricing calculations with support for:
- Multiple billing modes (hourly, per-item, project-based)
- Dynamic rate adjustments
- Volume discounts
- Quality-based pricing
- Time-based rate variations
"""

from datetime import datetime, date, time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PricingModel(str, Enum):
    """Pricing model types."""
    HOURLY = "hourly"
    PER_ITEM = "per_item"
    PROJECT_FIXED = "project_fixed"
    MILESTONE = "milestone"
    HYBRID = "hybrid"
    TIERED = "tiered"


class RateType(str, Enum):
    """Rate type enumeration."""
    STANDARD = "standard"
    OVERTIME = "overtime"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    RUSH = "rush"
    DISCOUNT = "discount"


@dataclass
class PricingRule:
    """Pricing rule configuration."""
    rule_id: str
    name: str
    pricing_model: PricingModel
    base_rate: Decimal
    currency: str = "CNY"
    min_quantity: int = 0
    max_quantity: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateSchedule:
    """Rate schedule for time-based pricing."""
    schedule_id: str
    name: str
    rates: Dict[RateType, Decimal]
    overtime_threshold_hours: float = 8.0
    weekend_multiplier: Decimal = Decimal("1.5")
    holiday_multiplier: Decimal = Decimal("2.0")
    rush_multiplier: Decimal = Decimal("1.3")


@dataclass
class TieredRate:
    """Tiered pricing rate."""
    tier_id: str
    min_quantity: int
    max_quantity: Optional[int]
    rate: Decimal
    description: str


@dataclass
class PricingResult:
    """Result of pricing calculation."""
    item_id: str
    pricing_model: PricingModel
    quantity: Union[int, float]
    unit_rate: Decimal
    base_amount: Decimal
    adjustments: List[Dict[str, Any]]
    final_amount: Decimal
    currency: str
    breakdown: Dict[str, Any]
    calculated_at: datetime = field(default_factory=datetime.now)


class PricingEngine:
    """
    Multi-dimensional pricing engine.
    
    Handles complex pricing calculations with support for
    multiple models, rate schedules, and adjustments.
    """
    
    def __init__(self):
        self.pricing_rules: Dict[str, PricingRule] = {}
        self.rate_schedules: Dict[str, RateSchedule] = {}
        self.tiered_rates: Dict[str, List[TieredRate]] = {}
        
        # Default rates
        self.default_hourly_rate = Decimal("50.00")
        self.default_per_item_rate = Decimal("0.50")
        
        # Initialize default rate schedule
        self._init_default_schedule()
    
    def _init_default_schedule(self):
        """Initialize default rate schedule."""
        default_schedule = RateSchedule(
            schedule_id="default",
            name="Standard Rate Schedule",
            rates={
                RateType.STANDARD: Decimal("50.00"),
                RateType.OVERTIME: Decimal("75.00"),
                RateType.WEEKEND: Decimal("75.00"),
                RateType.HOLIDAY: Decimal("100.00"),
                RateType.RUSH: Decimal("65.00")
            }
        )
        self.rate_schedules["default"] = default_schedule
    
    def add_pricing_rule(self, rule: PricingRule) -> None:
        """Add a pricing rule."""
        self.pricing_rules[rule.rule_id] = rule
        logger.info(f"Added pricing rule: {rule.rule_id}")
    
    def add_rate_schedule(self, schedule: RateSchedule) -> None:
        """Add a rate schedule."""
        self.rate_schedules[schedule.schedule_id] = schedule
        logger.info(f"Added rate schedule: {schedule.schedule_id}")
    
    def add_tiered_rates(self, tier_group_id: str, tiers: List[TieredRate]) -> None:
        """Add tiered pricing rates."""
        self.tiered_rates[tier_group_id] = sorted(tiers, key=lambda t: t.min_quantity)
        logger.info(f"Added tiered rates for group: {tier_group_id}")
    
    async def calculate_pricing(self, item: Dict[str, Any]) -> PricingResult:
        """
        Calculate pricing for a billing item.
        
        Args:
            item: Billing item with quantity, type, and context
            
        Returns:
            PricingResult with calculated amounts
        """
        item_id = item.get('id', 'unknown')
        pricing_model = PricingModel(item.get('pricing_model', 'hourly'))
        quantity = item.get('quantity', 0)
        
        # Get applicable rule
        rule = self._get_applicable_rule(item)
        
        # Calculate base amount
        if pricing_model == PricingModel.HOURLY:
            result = await self._calculate_hourly_pricing(item, rule)
        elif pricing_model == PricingModel.PER_ITEM:
            result = await self._calculate_per_item_pricing(item, rule)
        elif pricing_model == PricingModel.TIERED:
            result = await self._calculate_tiered_pricing(item, rule)
        elif pricing_model == PricingModel.PROJECT_FIXED:
            result = await self._calculate_fixed_pricing(item, rule)
        elif pricing_model == PricingModel.MILESTONE:
            result = await self._calculate_milestone_pricing(item, rule)
        else:  # HYBRID
            result = await self._calculate_hybrid_pricing(item, rule)
        
        return result
    
    async def _calculate_hourly_pricing(self, item: Dict[str, Any],
                                       rule: Optional[PricingRule]) -> PricingResult:
        """Calculate hourly-based pricing."""
        hours = item.get('hours', 0)
        schedule_id = item.get('schedule_id', 'default')
        schedule = self.rate_schedules.get(schedule_id, self.rate_schedules['default'])
        
        # Determine rate type based on context
        rate_type = self._determine_rate_type(item)
        hourly_rate = schedule.rates.get(rate_type, schedule.rates[RateType.STANDARD])
        
        # Calculate base amount
        base_amount = Decimal(str(hours)) * hourly_rate
        
        # Apply adjustments
        adjustments = []
        final_amount = base_amount
        
        # Overtime calculation
        if hours > schedule.overtime_threshold_hours:
            overtime_hours = hours - schedule.overtime_threshold_hours
            regular_hours = schedule.overtime_threshold_hours
            
            regular_amount = Decimal(str(regular_hours)) * schedule.rates[RateType.STANDARD]
            overtime_amount = Decimal(str(overtime_hours)) * schedule.rates[RateType.OVERTIME]
            
            final_amount = regular_amount + overtime_amount
            adjustments.append({
                'type': 'overtime',
                'hours': overtime_hours,
                'rate': float(schedule.rates[RateType.OVERTIME]),
                'amount': float(overtime_amount - Decimal(str(overtime_hours)) * schedule.rates[RateType.STANDARD])
            })
        
        return PricingResult(
            item_id=item.get('id', 'unknown'),
            pricing_model=PricingModel.HOURLY,
            quantity=hours,
            unit_rate=hourly_rate,
            base_amount=base_amount,
            adjustments=adjustments,
            final_amount=final_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency=rule.currency if rule else "CNY",
            breakdown={
                'hours': hours,
                'rate_type': rate_type.value,
                'hourly_rate': float(hourly_rate),
                'overtime_threshold': schedule.overtime_threshold_hours
            }
        )
    
    async def _calculate_per_item_pricing(self, item: Dict[str, Any],
                                         rule: Optional[PricingRule]) -> PricingResult:
        """Calculate per-item pricing."""
        quantity = item.get('quantity', 0)
        unit_rate = rule.base_rate if rule else self.default_per_item_rate
        
        # Check for complexity adjustments
        complexity = item.get('complexity', 1.0)
        adjusted_rate = unit_rate * Decimal(str(complexity))
        
        base_amount = Decimal(str(quantity)) * adjusted_rate
        adjustments = []
        
        if complexity != 1.0:
            adjustments.append({
                'type': 'complexity',
                'factor': complexity,
                'impact': float(base_amount - Decimal(str(quantity)) * unit_rate)
            })
        
        return PricingResult(
            item_id=item.get('id', 'unknown'),
            pricing_model=PricingModel.PER_ITEM,
            quantity=quantity,
            unit_rate=adjusted_rate,
            base_amount=base_amount,
            adjustments=adjustments,
            final_amount=base_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency=rule.currency if rule else "CNY",
            breakdown={
                'quantity': quantity,
                'base_rate': float(unit_rate),
                'complexity': complexity,
                'adjusted_rate': float(adjusted_rate)
            }
        )
    
    async def _calculate_tiered_pricing(self, item: Dict[str, Any],
                                       rule: Optional[PricingRule]) -> PricingResult:
        """Calculate tiered pricing."""
        quantity = item.get('quantity', 0)
        tier_group = item.get('tier_group', 'default')
        tiers = self.tiered_rates.get(tier_group, [])
        
        if not tiers:
            # Fall back to per-item pricing
            return await self._calculate_per_item_pricing(item, rule)
        
        # Calculate amount across tiers
        remaining = quantity
        total_amount = Decimal("0")
        tier_breakdown = []
        
        for tier in tiers:
            if remaining <= 0:
                break
            
            tier_max = tier.max_quantity or float('inf')
            tier_quantity = min(remaining, tier_max - tier.min_quantity)
            
            if tier_quantity > 0:
                tier_amount = Decimal(str(tier_quantity)) * tier.rate
                total_amount += tier_amount
                tier_breakdown.append({
                    'tier': tier.tier_id,
                    'quantity': tier_quantity,
                    'rate': float(tier.rate),
                    'amount': float(tier_amount)
                })
                remaining -= tier_quantity
        
        effective_rate = total_amount / Decimal(str(quantity)) if quantity > 0 else Decimal("0")
        
        return PricingResult(
            item_id=item.get('id', 'unknown'),
            pricing_model=PricingModel.TIERED,
            quantity=quantity,
            unit_rate=effective_rate,
            base_amount=total_amount,
            adjustments=[],
            final_amount=total_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency=rule.currency if rule else "CNY",
            breakdown={
                'quantity': quantity,
                'tiers': tier_breakdown,
                'effective_rate': float(effective_rate)
            }
        )
    
    async def _calculate_fixed_pricing(self, item: Dict[str, Any],
                                      rule: Optional[PricingRule]) -> PricingResult:
        """Calculate fixed project pricing."""
        fixed_amount = Decimal(str(item.get('fixed_amount', 0)))
        
        if rule:
            fixed_amount = rule.base_rate
        
        return PricingResult(
            item_id=item.get('id', 'unknown'),
            pricing_model=PricingModel.PROJECT_FIXED,
            quantity=1,
            unit_rate=fixed_amount,
            base_amount=fixed_amount,
            adjustments=[],
            final_amount=fixed_amount,
            currency=rule.currency if rule else "CNY",
            breakdown={
                'project_id': item.get('project_id'),
                'fixed_amount': float(fixed_amount)
            }
        )
    
    async def _calculate_milestone_pricing(self, item: Dict[str, Any],
                                          rule: Optional[PricingRule]) -> PricingResult:
        """Calculate milestone-based pricing."""
        milestones = item.get('milestones', [])
        completed_milestones = item.get('completed_milestones', [])
        
        total_amount = Decimal("0")
        milestone_breakdown = []
        
        for milestone in milestones:
            if milestone['id'] in completed_milestones:
                amount = Decimal(str(milestone.get('amount', 0)))
                total_amount += amount
                milestone_breakdown.append({
                    'milestone_id': milestone['id'],
                    'name': milestone.get('name', ''),
                    'amount': float(amount),
                    'completed': True
                })
        
        return PricingResult(
            item_id=item.get('id', 'unknown'),
            pricing_model=PricingModel.MILESTONE,
            quantity=len(completed_milestones),
            unit_rate=total_amount / len(completed_milestones) if completed_milestones else Decimal("0"),
            base_amount=total_amount,
            adjustments=[],
            final_amount=total_amount,
            currency=rule.currency if rule else "CNY",
            breakdown={
                'total_milestones': len(milestones),
                'completed_milestones': len(completed_milestones),
                'milestone_details': milestone_breakdown
            }
        )
    
    async def _calculate_hybrid_pricing(self, item: Dict[str, Any],
                                       rule: Optional[PricingRule]) -> PricingResult:
        """Calculate hybrid pricing (combination of models)."""
        # Calculate hourly component
        hourly_item = {**item, 'pricing_model': 'hourly'}
        hourly_result = await self._calculate_hourly_pricing(hourly_item, rule)
        
        # Calculate per-item component
        per_item_item = {**item, 'pricing_model': 'per_item'}
        per_item_result = await self._calculate_per_item_pricing(per_item_item, rule)
        
        # Combine results
        total_amount = hourly_result.final_amount + per_item_result.final_amount
        
        return PricingResult(
            item_id=item.get('id', 'unknown'),
            pricing_model=PricingModel.HYBRID,
            quantity=item.get('quantity', 0),
            unit_rate=total_amount / Decimal(str(item.get('quantity', 1))) if item.get('quantity') else Decimal("0"),
            base_amount=total_amount,
            adjustments=[],
            final_amount=total_amount,
            currency=rule.currency if rule else "CNY",
            breakdown={
                'hourly_component': hourly_result.breakdown,
                'per_item_component': per_item_result.breakdown,
                'hourly_amount': float(hourly_result.final_amount),
                'per_item_amount': float(per_item_result.final_amount)
            }
        )
    
    def _get_applicable_rule(self, item: Dict[str, Any]) -> Optional[PricingRule]:
        """Get applicable pricing rule for an item."""
        rule_id = item.get('rule_id')
        if rule_id and rule_id in self.pricing_rules:
            return self.pricing_rules[rule_id]
        
        # Find matching rule based on conditions
        for rule in self.pricing_rules.values():
            if self._rule_matches(rule, item):
                return rule
        
        return None
    
    def _rule_matches(self, rule: PricingRule, item: Dict[str, Any]) -> bool:
        """Check if a rule matches an item."""
        # Check date range
        today = date.today()
        if rule.effective_from and today < rule.effective_from:
            return False
        if rule.effective_to and today > rule.effective_to:
            return False
        
        # Check quantity range
        quantity = item.get('quantity', 0)
        if quantity < rule.min_quantity:
            return False
        if rule.max_quantity and quantity > rule.max_quantity:
            return False
        
        # Check conditions
        for key, value in rule.conditions.items():
            if item.get(key) != value:
                return False
        
        return True
    
    def _determine_rate_type(self, item: Dict[str, Any]) -> RateType:
        """Determine rate type based on item context."""
        work_date = item.get('work_date', date.today())
        if isinstance(work_date, str):
            work_date = date.fromisoformat(work_date)
        
        # Check for holiday
        if item.get('is_holiday', False):
            return RateType.HOLIDAY
        
        # Check for weekend
        if work_date.weekday() >= 5:
            return RateType.WEEKEND
        
        # Check for rush
        if item.get('is_rush', False):
            return RateType.RUSH
        
        return RateType.STANDARD


def get_pricing_engine() -> PricingEngine:
    """Get pricing engine instance."""
    return PricingEngine()
