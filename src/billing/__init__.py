"""
Billing system module for SuperInsight platform.

Provides billing tracking, calculation, and reporting functionality.
Includes advanced billing features for SuperInsight 2.3:
- Advanced work time management
- Multi-dimensional pricing
- Discount and tax management
- Reward system
- Report generation
- Rule engine
"""

from src.billing.models import (
    BillingRecord,
    BillingRule,
    Bill,
    BillingReport,
    BillingMode
)
from src.billing.service import BillingSystem
from src.billing.analytics import BillingAnalytics


def get_quality_pricing_engine():
    """Get QualityPricingEngine instance with lazy import."""
    from .quality_pricing import QualityPricingEngine
    return QualityPricingEngine()


def get_incentive_manager():
    """Get IncentiveManager instance with lazy import."""
    from .incentive_manager import IncentiveManager
    return IncentiveManager()


def get_billing_report_service():
    """Get BillingReportService instance with lazy import."""
    from .report_service import get_billing_report_service as _get_service
    return _get_service()


# Advanced Billing Module (SuperInsight 2.3)
def get_advanced_work_time_calculator():
    """Get AdvancedWorkTimeCalculator instance with lazy import."""
    from .advanced_work_time import AdvancedWorkTimeCalculator
    return AdvancedWorkTimeCalculator()


def get_pricing_engine():
    """Get PricingEngine instance with lazy import."""
    from .pricing_engine import PricingEngine
    return PricingEngine()


def get_discount_manager():
    """Get DiscountManager instance with lazy import."""
    from .discount_manager import DiscountManager
    return DiscountManager()


def get_tax_calculator():
    """Get TaxCalculator instance with lazy import."""
    from .tax_calculator import TaxCalculator
    return TaxCalculator()


def get_advanced_reward_system():
    """Get AdvancedRewardSystem instance with lazy import."""
    from .advanced_reward_system import AdvancedRewardSystem
    return AdvancedRewardSystem()


def get_advanced_excel_exporter():
    """Get AdvancedExcelExporter instance with lazy import."""
    from .advanced_excel_exporter import AdvancedExcelExporter
    return AdvancedExcelExporter()


def get_billing_report_generator():
    """Get BillingReportGenerator instance with lazy import."""
    from .billing_report_generator import BillingReportGenerator
    return BillingReportGenerator()


def get_billing_rule_engine():
    """Get BillingRuleEngine instance with lazy import."""
    from .billing_rule_engine import BillingRuleEngine
    return BillingRuleEngine()


__all__ = [
    # Core billing models
    'BillingRecord',
    'BillingRule',
    'Bill',
    'BillingReport',
    'BillingMode',
    'BillingSystem',
    'BillingAnalytics',
    # Core billing services
    'get_quality_pricing_engine',
    'get_incentive_manager',
    'get_billing_report_service',
    # Advanced billing (SuperInsight 2.3)
    'get_advanced_work_time_calculator',
    'get_pricing_engine',
    'get_discount_manager',
    'get_tax_calculator',
    'get_advanced_reward_system',
    'get_advanced_excel_exporter',
    'get_billing_report_generator',
    'get_billing_rule_engine',
]