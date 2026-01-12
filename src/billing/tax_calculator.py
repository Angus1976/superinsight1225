"""
Tax Calculation System for SuperInsight Platform.

Provides multi-region tax calculation with support for:
- VAT (Value Added Tax)
- Sales Tax
- Service Tax
- Withholding Tax
- Multiple tax jurisdictions
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaxType(str, Enum):
    """Tax type enumeration."""
    VAT = "vat"
    SALES_TAX = "sales_tax"
    SERVICE_TAX = "service_tax"
    WITHHOLDING_TAX = "withholding_tax"
    CONSUMPTION_TAX = "consumption_tax"
    NONE = "none"


class TaxJurisdiction(str, Enum):
    """Tax jurisdiction enumeration."""
    CHINA_MAINLAND = "cn_mainland"
    CHINA_HONGKONG = "cn_hongkong"
    USA = "usa"
    EU = "eu"
    UK = "uk"
    SINGAPORE = "sg"
    JAPAN = "jp"
    OTHER = "other"


@dataclass
class TaxRate:
    """Tax rate configuration."""
    rate_id: str
    jurisdiction: TaxJurisdiction
    tax_type: TaxType
    rate: Decimal  # Percentage (0-100)
    name: str
    description: str = ""
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    applies_to: List[str] = field(default_factory=list)  # Service categories
    exemptions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxExemption:
    """Tax exemption configuration."""
    exemption_id: str
    name: str
    jurisdiction: TaxJurisdiction
    tax_types: List[TaxType]
    conditions: Dict[str, Any]
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


@dataclass
class TaxCalculationResult:
    """Tax calculation result."""
    jurisdiction: TaxJurisdiction
    tax_type: TaxType
    taxable_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    exemptions_applied: List[str]
    breakdown: Dict[str, Any]
    calculated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaxSummary:
    """Tax summary for billing."""
    subtotal: Decimal
    total_tax: Decimal
    tax_details: List[TaxCalculationResult]
    grand_total: Decimal
    currency: str
    jurisdiction: TaxJurisdiction


class TaxCalculator:
    """
    Multi-region tax calculation engine.
    
    Handles tax calculations for different jurisdictions
    with support for exemptions and special rules.
    """
    
    def __init__(self):
        self.tax_rates: Dict[str, TaxRate] = {}
        self.exemptions: Dict[str, TaxExemption] = {}
        self.client_jurisdictions: Dict[str, TaxJurisdiction] = {}
        
        # Initialize default tax rates
        self._init_default_rates()
    
    def _init_default_rates(self):
        """Initialize default tax rates."""
        # China Mainland VAT
        self.add_tax_rate(TaxRate(
            rate_id="cn_vat_standard",
            jurisdiction=TaxJurisdiction.CHINA_MAINLAND,
            tax_type=TaxType.VAT,
            rate=Decimal("6"),  # 6% for modern services
            name="China VAT (Modern Services)",
            description="Standard VAT rate for modern services in China",
            applies_to=["annotation", "data_processing", "ai_services"]
        ))
        
        # China Mainland VAT for software
        self.add_tax_rate(TaxRate(
            rate_id="cn_vat_software",
            jurisdiction=TaxJurisdiction.CHINA_MAINLAND,
            tax_type=TaxType.VAT,
            rate=Decimal("13"),  # 13% for software
            name="China VAT (Software)",
            description="VAT rate for software products",
            applies_to=["software", "license"]
        ))
        
        # Hong Kong (no VAT)
        self.add_tax_rate(TaxRate(
            rate_id="hk_none",
            jurisdiction=TaxJurisdiction.CHINA_HONGKONG,
            tax_type=TaxType.NONE,
            rate=Decimal("0"),
            name="Hong Kong (No VAT)",
            description="Hong Kong has no VAT/GST"
        ))
        
        # Singapore GST
        self.add_tax_rate(TaxRate(
            rate_id="sg_gst",
            jurisdiction=TaxJurisdiction.SINGAPORE,
            tax_type=TaxType.VAT,
            rate=Decimal("9"),  # 9% GST
            name="Singapore GST",
            description="Goods and Services Tax"
        ))
        
        # EU VAT (standard rate varies by country, using average)
        self.add_tax_rate(TaxRate(
            rate_id="eu_vat_standard",
            jurisdiction=TaxJurisdiction.EU,
            tax_type=TaxType.VAT,
            rate=Decimal("20"),  # Average EU VAT
            name="EU VAT (Standard)",
            description="Standard EU VAT rate"
        ))
        
        # USA Sales Tax (varies by state, using average)
        self.add_tax_rate(TaxRate(
            rate_id="usa_sales_tax",
            jurisdiction=TaxJurisdiction.USA,
            tax_type=TaxType.SALES_TAX,
            rate=Decimal("7"),  # Average state sales tax
            name="USA Sales Tax",
            description="Average US state sales tax"
        ))
        
        # Japan Consumption Tax
        self.add_tax_rate(TaxRate(
            rate_id="jp_consumption",
            jurisdiction=TaxJurisdiction.JAPAN,
            tax_type=TaxType.CONSUMPTION_TAX,
            rate=Decimal("10"),
            name="Japan Consumption Tax",
            description="Japanese consumption tax"
        ))
    
    def add_tax_rate(self, rate: TaxRate) -> None:
        """Add a tax rate configuration."""
        self.tax_rates[rate.rate_id] = rate
        logger.info(f"Added tax rate: {rate.rate_id}")
    
    def add_exemption(self, exemption: TaxExemption) -> None:
        """Add a tax exemption."""
        self.exemptions[exemption.exemption_id] = exemption
        logger.info(f"Added tax exemption: {exemption.exemption_id}")
    
    def set_client_jurisdiction(self, client_id: str, 
                               jurisdiction: TaxJurisdiction) -> None:
        """Set tax jurisdiction for a client."""
        self.client_jurisdictions[client_id] = jurisdiction
        logger.info(f"Set jurisdiction {jurisdiction.value} for client {client_id}")
    
    async def calculate_taxes(self, pricing_details: List[Any],
                             discount_amount: Decimal,
                             client_id: str) -> TaxSummary:
        """Calculate taxes for billing items."""
        # Get client jurisdiction
        jurisdiction = self.client_jurisdictions.get(
            client_id, TaxJurisdiction.CHINA_MAINLAND
        )
        
        # Calculate subtotal
        subtotal = sum(
            p.final_amount if hasattr(p, 'final_amount') else Decimal(str(p.get('amount', 0)))
            for p in pricing_details
        )
        subtotal -= discount_amount
        
        # Get applicable tax rates
        applicable_rates = self._get_applicable_rates(jurisdiction, pricing_details)
        
        # Calculate taxes
        tax_results = []
        total_tax = Decimal("0")
        
        for rate in applicable_rates:
            # Check for exemptions
            exemptions = self._check_exemptions(client_id, rate, pricing_details)
            
            if exemptions:
                # Fully exempt
                tax_result = TaxCalculationResult(
                    jurisdiction=jurisdiction,
                    tax_type=rate.tax_type,
                    taxable_amount=subtotal,
                    tax_rate=Decimal("0"),
                    tax_amount=Decimal("0"),
                    exemptions_applied=[e.exemption_id for e in exemptions],
                    breakdown={'exempt': True, 'reason': exemptions[0].name}
                )
            else:
                # Calculate tax
                tax_amount = (subtotal * rate.rate / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                
                tax_result = TaxCalculationResult(
                    jurisdiction=jurisdiction,
                    tax_type=rate.tax_type,
                    taxable_amount=subtotal,
                    tax_rate=rate.rate,
                    tax_amount=tax_amount,
                    exemptions_applied=[],
                    breakdown={
                        'rate_id': rate.rate_id,
                        'rate_name': rate.name,
                        'rate_percentage': float(rate.rate)
                    }
                )
                total_tax += tax_amount
            
            tax_results.append(tax_result)
        
        grand_total = subtotal + total_tax
        
        return TaxSummary(
            subtotal=subtotal,
            total_tax=total_tax,
            tax_details=tax_results,
            grand_total=grand_total,
            currency="CNY",
            jurisdiction=jurisdiction
        )
    
    async def calculate_single_tax(self, amount: Decimal, 
                                  jurisdiction: TaxJurisdiction,
                                  service_category: str = None) -> TaxCalculationResult:
        """Calculate tax for a single amount."""
        # Get applicable rate
        rate = self._get_rate_for_category(jurisdiction, service_category)
        
        if not rate or rate.tax_type == TaxType.NONE:
            return TaxCalculationResult(
                jurisdiction=jurisdiction,
                tax_type=TaxType.NONE,
                taxable_amount=amount,
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                exemptions_applied=[],
                breakdown={'no_tax': True}
            )
        
        tax_amount = (amount * rate.rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        return TaxCalculationResult(
            jurisdiction=jurisdiction,
            tax_type=rate.tax_type,
            taxable_amount=amount,
            tax_rate=rate.rate,
            tax_amount=tax_amount,
            exemptions_applied=[],
            breakdown={
                'rate_id': rate.rate_id,
                'rate_name': rate.name
            }
        )
    
    def _get_applicable_rates(self, jurisdiction: TaxJurisdiction,
                             pricing_details: List[Any]) -> List[TaxRate]:
        """Get applicable tax rates for a jurisdiction."""
        applicable = []
        today = date.today()
        
        for rate in self.tax_rates.values():
            if rate.jurisdiction != jurisdiction:
                continue
            
            # Check date range
            if rate.effective_from and today < rate.effective_from:
                continue
            if rate.effective_to and today > rate.effective_to:
                continue
            
            # Check if applies to any service category
            if rate.applies_to:
                categories = set()
                for item in pricing_details:
                    if hasattr(item, 'breakdown'):
                        cat = item.breakdown.get('category')
                    else:
                        cat = item.get('category')
                    if cat:
                        categories.add(cat)
                
                if not categories.intersection(set(rate.applies_to)):
                    continue
            
            applicable.append(rate)
        
        return applicable
    
    def _get_rate_for_category(self, jurisdiction: TaxJurisdiction,
                              category: str = None) -> Optional[TaxRate]:
        """Get tax rate for a specific category."""
        for rate in self.tax_rates.values():
            if rate.jurisdiction != jurisdiction:
                continue
            
            if category and rate.applies_to:
                if category in rate.applies_to:
                    return rate
            elif not rate.applies_to:
                # Default rate for jurisdiction
                return rate
        
        return None
    
    def _check_exemptions(self, client_id: str, rate: TaxRate,
                         pricing_details: List[Any]) -> List[TaxExemption]:
        """Check for applicable tax exemptions."""
        applicable_exemptions = []
        today = date.today()
        
        for exemption in self.exemptions.values():
            if exemption.jurisdiction != rate.jurisdiction:
                continue
            
            if rate.tax_type not in exemption.tax_types:
                continue
            
            # Check date range
            if exemption.effective_from and today < exemption.effective_from:
                continue
            if exemption.effective_to and today > exemption.effective_to:
                continue
            
            # Check conditions
            conditions_met = True
            for key, value in exemption.conditions.items():
                if key == 'client_id' and client_id != value:
                    conditions_met = False
                    break
                # Add more condition checks as needed
            
            if conditions_met:
                applicable_exemptions.append(exemption)
        
        return applicable_exemptions
    
    def get_tax_rates_for_jurisdiction(self, 
                                      jurisdiction: TaxJurisdiction) -> List[Dict[str, Any]]:
        """Get all tax rates for a jurisdiction."""
        rates = []
        for rate in self.tax_rates.values():
            if rate.jurisdiction == jurisdiction:
                rates.append({
                    'rate_id': rate.rate_id,
                    'tax_type': rate.tax_type.value,
                    'rate': float(rate.rate),
                    'name': rate.name,
                    'description': rate.description,
                    'applies_to': rate.applies_to
                })
        return rates
    
    def get_supported_jurisdictions(self) -> List[Dict[str, Any]]:
        """Get list of supported tax jurisdictions."""
        jurisdictions = {}
        for rate in self.tax_rates.values():
            if rate.jurisdiction.value not in jurisdictions:
                jurisdictions[rate.jurisdiction.value] = {
                    'jurisdiction': rate.jurisdiction.value,
                    'tax_types': set(),
                    'rates': []
                }
            jurisdictions[rate.jurisdiction.value]['tax_types'].add(rate.tax_type.value)
            jurisdictions[rate.jurisdiction.value]['rates'].append(float(rate.rate))
        
        return [
            {
                'jurisdiction': j['jurisdiction'],
                'tax_types': list(j['tax_types']),
                'rate_range': f"{min(j['rates'])}-{max(j['rates'])}%"
            }
            for j in jurisdictions.values()
        ]


def get_tax_calculator() -> TaxCalculator:
    """Get tax calculator instance."""
    return TaxCalculator()
