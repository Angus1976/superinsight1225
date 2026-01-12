"""
Discount Management for SuperInsight Platform.

Provides comprehensive discount handling including:
- Volume discounts
- Loyalty discounts
- Promotional discounts
- Contract-based discounts
- Seasonal discounts
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DiscountType(str, Enum):
    """Discount type enumeration."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    TIERED = "tiered"
    BUY_X_GET_Y = "buy_x_get_y"


class DiscountCategory(str, Enum):
    """Discount category enumeration."""
    VOLUME = "volume"
    LOYALTY = "loyalty"
    PROMOTIONAL = "promotional"
    CONTRACT = "contract"
    SEASONAL = "seasonal"
    REFERRAL = "referral"
    EARLY_PAYMENT = "early_payment"


@dataclass
class DiscountRule:
    """Discount rule configuration."""
    rule_id: str
    name: str
    discount_type: DiscountType
    category: DiscountCategory
    value: Decimal  # Percentage (0-100) or fixed amount
    min_amount: Decimal = Decimal("0")
    max_discount: Optional[Decimal] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    stackable: bool = False
    priority: int = 0
    usage_limit: Optional[int] = None
    current_usage: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TieredDiscount:
    """Tiered discount configuration."""
    tier_id: str
    min_amount: Decimal
    max_amount: Optional[Decimal]
    discount_percentage: Decimal
    description: str


@dataclass
class AppliedDiscount:
    """Applied discount details."""
    rule_id: str
    name: str
    category: DiscountCategory
    discount_type: DiscountType
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    description: str
    applied_at: datetime = field(default_factory=datetime.now)


class DiscountManager:
    """
    Discount management engine.
    
    Handles discount rule management, eligibility checking,
    and discount calculations.
    """
    
    def __init__(self):
        self.discount_rules: Dict[str, DiscountRule] = {}
        self.tiered_discounts: Dict[str, List[TieredDiscount]] = {}
        self.client_discounts: Dict[str, List[str]] = {}  # client_id -> rule_ids
        
        # Initialize default discounts
        self._init_default_discounts()
    
    def _init_default_discounts(self):
        """Initialize default discount rules."""
        # Volume discount
        self.add_discount_rule(DiscountRule(
            rule_id="volume_5000",
            name="Volume Discount (5000+)",
            discount_type=DiscountType.PERCENTAGE,
            category=DiscountCategory.VOLUME,
            value=Decimal("5"),
            min_amount=Decimal("5000"),
            stackable=True,
            priority=10
        ))
        
        self.add_discount_rule(DiscountRule(
            rule_id="volume_10000",
            name="Volume Discount (10000+)",
            discount_type=DiscountType.PERCENTAGE,
            category=DiscountCategory.VOLUME,
            value=Decimal("10"),
            min_amount=Decimal("10000"),
            stackable=True,
            priority=20
        ))
        
        # Early payment discount
        self.add_discount_rule(DiscountRule(
            rule_id="early_payment",
            name="Early Payment Discount",
            discount_type=DiscountType.PERCENTAGE,
            category=DiscountCategory.EARLY_PAYMENT,
            value=Decimal("2"),
            conditions={"payment_within_days": 7},
            stackable=True,
            priority=5
        ))
    
    def add_discount_rule(self, rule: DiscountRule) -> None:
        """Add a discount rule."""
        self.discount_rules[rule.rule_id] = rule
        logger.info(f"Added discount rule: {rule.rule_id}")
    
    def add_tiered_discount(self, tier_group_id: str, 
                           tiers: List[TieredDiscount]) -> None:
        """Add tiered discount configuration."""
        self.tiered_discounts[tier_group_id] = sorted(
            tiers, key=lambda t: t.min_amount
        )
        logger.info(f"Added tiered discount group: {tier_group_id}")
    
    def assign_client_discount(self, client_id: str, rule_id: str) -> bool:
        """Assign a discount rule to a client."""
        if rule_id not in self.discount_rules:
            return False
        
        if client_id not in self.client_discounts:
            self.client_discounts[client_id] = []
        
        if rule_id not in self.client_discounts[client_id]:
            self.client_discounts[client_id].append(rule_id)
            logger.info(f"Assigned discount {rule_id} to client {client_id}")
        
        return True
    
    async def get_applicable_discounts(self, client_id: str,
                                      billing_items: List[Dict[str, Any]]) -> List[DiscountRule]:
        """Get all applicable discounts for a client and billing items."""
        applicable = []
        total_amount = sum(
            Decimal(str(item.get('amount', 0))) for item in billing_items
        )
        
        # Check client-specific discounts
        client_rule_ids = self.client_discounts.get(client_id, [])
        for rule_id in client_rule_ids:
            rule = self.discount_rules.get(rule_id)
            if rule and self._is_rule_applicable(rule, total_amount, billing_items):
                applicable.append(rule)
        
        # Check general discounts
        for rule in self.discount_rules.values():
            if rule.rule_id not in client_rule_ids:
                if self._is_rule_applicable(rule, total_amount, billing_items):
                    applicable.append(rule)
        
        # Sort by priority (higher priority first)
        applicable.sort(key=lambda r: r.priority, reverse=True)
        
        return applicable
    
    async def calculate_discount(self, pricing_details: List[Any],
                                applicable_discounts: List[DiscountRule]) -> Decimal:
        """Calculate total discount amount."""
        total_amount = sum(
            p.final_amount if hasattr(p, 'final_amount') else Decimal(str(p.get('amount', 0)))
            for p in pricing_details
        )
        
        total_discount = Decimal("0")
        remaining_amount = total_amount
        applied_non_stackable = False
        
        for rule in applicable_discounts:
            # Skip if non-stackable discount already applied
            if not rule.stackable and applied_non_stackable:
                continue
            
            # Check usage limit
            if rule.usage_limit and rule.current_usage >= rule.usage_limit:
                continue
            
            # Calculate discount
            discount = self._calculate_single_discount(rule, remaining_amount)
            
            # Apply max discount cap
            if rule.max_discount:
                discount = min(discount, rule.max_discount)
            
            total_discount += discount
            
            if not rule.stackable:
                applied_non_stackable = True
                remaining_amount -= discount
            
            # Update usage
            rule.current_usage += 1
        
        return total_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    async def apply_discounts(self, amount: Decimal, client_id: str,
                             context: Dict[str, Any] = None) -> Tuple[Decimal, List[AppliedDiscount]]:
        """Apply all applicable discounts to an amount."""
        context = context or {}
        billing_items = [{'amount': float(amount)}]
        
        applicable = await self.get_applicable_discounts(client_id, billing_items)
        
        applied_discounts = []
        remaining = amount
        applied_non_stackable = False
        
        for rule in applicable:
            if not rule.stackable and applied_non_stackable:
                continue
            
            discount_amount = self._calculate_single_discount(rule, remaining)
            
            if rule.max_discount:
                discount_amount = min(discount_amount, rule.max_discount)
            
            if discount_amount > 0:
                applied = AppliedDiscount(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    category=rule.category,
                    discount_type=rule.discount_type,
                    original_amount=remaining,
                    discount_amount=discount_amount,
                    final_amount=remaining - discount_amount,
                    description=f"{rule.name}: -{float(discount_amount):.2f}"
                )
                applied_discounts.append(applied)
                
                if rule.stackable:
                    remaining -= discount_amount
                else:
                    remaining -= discount_amount
                    applied_non_stackable = True
        
        return remaining, applied_discounts
    
    def _is_rule_applicable(self, rule: DiscountRule, total_amount: Decimal,
                           billing_items: List[Dict[str, Any]]) -> bool:
        """Check if a discount rule is applicable."""
        # Check date range
        today = date.today()
        if rule.effective_from and today < rule.effective_from:
            return False
        if rule.effective_to and today > rule.effective_to:
            return False
        
        # Check minimum amount
        if total_amount < rule.min_amount:
            return False
        
        # Check usage limit
        if rule.usage_limit and rule.current_usage >= rule.usage_limit:
            return False
        
        # Check conditions
        for key, value in rule.conditions.items():
            # Handle special conditions
            if key == "payment_within_days":
                # This would be checked at payment time
                continue
            
            # Check if condition is met in any billing item
            condition_met = any(
                item.get(key) == value for item in billing_items
            )
            if not condition_met:
                return False
        
        return True
    
    def _calculate_single_discount(self, rule: DiscountRule, 
                                  amount: Decimal) -> Decimal:
        """Calculate discount for a single rule."""
        if rule.discount_type == DiscountType.PERCENTAGE:
            return (amount * rule.value / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        elif rule.discount_type == DiscountType.FIXED_AMOUNT:
            return min(rule.value, amount)
        elif rule.discount_type == DiscountType.TIERED:
            return self._calculate_tiered_discount(rule.rule_id, amount)
        else:
            return Decimal("0")
    
    def _calculate_tiered_discount(self, tier_group_id: str, 
                                  amount: Decimal) -> Decimal:
        """Calculate tiered discount."""
        tiers = self.tiered_discounts.get(tier_group_id, [])
        
        for tier in reversed(tiers):  # Check from highest tier
            if amount >= tier.min_amount:
                if tier.max_amount is None or amount <= tier.max_amount:
                    return (amount * tier.discount_percentage / Decimal("100")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
        
        return Decimal("0")
    
    def get_discount_summary(self, client_id: str) -> Dict[str, Any]:
        """Get discount summary for a client."""
        client_rules = self.client_discounts.get(client_id, [])
        
        discounts = []
        for rule_id in client_rules:
            rule = self.discount_rules.get(rule_id)
            if rule:
                discounts.append({
                    'rule_id': rule.rule_id,
                    'name': rule.name,
                    'category': rule.category.value,
                    'type': rule.discount_type.value,
                    'value': float(rule.value),
                    'stackable': rule.stackable,
                    'effective_from': rule.effective_from.isoformat() if rule.effective_from else None,
                    'effective_to': rule.effective_to.isoformat() if rule.effective_to else None
                })
        
        return {
            'client_id': client_id,
            'assigned_discounts': discounts,
            'total_discounts': len(discounts)
        }


def get_discount_manager() -> DiscountManager:
    """Get discount manager instance."""
    return DiscountManager()
