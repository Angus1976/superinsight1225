"""
Enhanced invoice generator for SuperInsight platform.

Provides detailed billing with multi-level breakdowns, quality adjustments,
tax handling, and customizable templates.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
from uuid import UUID, uuid4
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from dataclasses import dataclass
from jinja2 import Template
import json

from src.billing.models import BillingRecord, Bill, BillingRule


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


class QualityAdjustmentType(str, Enum):
    """Quality adjustment types."""
    BONUS = "bonus"
    PENALTY = "penalty"
    NEUTRAL = "neutral"


class TaxType(str, Enum):
    """Tax types."""
    VAT = "vat"
    SALES_TAX = "sales_tax"
    SERVICE_TAX = "service_tax"
    NONE = "none"


@dataclass
class QualityAdjustment:
    """Quality-based billing adjustment."""
    type: QualityAdjustmentType
    percentage: Decimal
    reason: str
    quality_score: Optional[float] = None
    baseline_score: Optional[float] = None


@dataclass
class TaxConfiguration:
    """Tax configuration for billing."""
    tax_type: TaxType
    rate: Decimal
    description: str
    applies_to_adjustments: bool = True


@dataclass
class DiscountConfiguration:
    """Discount configuration."""
    percentage: Decimal
    description: str
    applies_to: str = "subtotal"  # subtotal, total, specific_items


@dataclass
class InvoiceLineItem:
    """Individual line item in an invoice."""
    id: str
    description: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    quality_adjustment: Optional[QualityAdjustment] = None
    adjusted_subtotal: Optional[Decimal] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProjectBreakdown:
    """Project-level billing breakdown."""
    project_id: str
    project_name: str
    total_annotations: int
    total_time_spent: int
    base_cost: Decimal
    quality_adjustments: List[QualityAdjustment]
    adjusted_cost: Decimal
    line_items: List[InvoiceLineItem]


@dataclass
class TaskBreakdown:
    """Task-level billing breakdown."""
    task_id: str
    task_name: str
    project_id: str
    annotations: int
    time_spent: int
    base_cost: Decimal
    quality_score: Optional[float]
    quality_adjustment: Optional[QualityAdjustment]
    adjusted_cost: Decimal


@dataclass
class UserBreakdown:
    """User-level billing breakdown."""
    user_id: str
    user_name: str
    total_annotations: int
    total_time_spent: int
    base_cost: Decimal
    quality_adjustments: List[QualityAdjustment]
    adjusted_cost: Decimal
    tasks: List[TaskBreakdown]


class DetailedInvoiceGenerator:
    """
    Enhanced invoice generator with multi-level breakdowns and quality adjustments.
    """

    def __init__(self):
        """Initialize the invoice generator."""
        self.quality_thresholds = {
            "excellent": 0.95,
            "good": 0.85,
            "acceptable": 0.75,
            "poor": 0.60
        }
        
        self.quality_adjustments = {
            "excellent": QualityAdjustment(QualityAdjustmentType.BONUS, Decimal("0.20"), "优秀质量奖励"),
            "good": QualityAdjustment(QualityAdjustmentType.BONUS, Decimal("0.10"), "良好质量奖励"),
            "acceptable": QualityAdjustment(QualityAdjustmentType.NEUTRAL, Decimal("0.00"), "标准质量"),
            "poor": QualityAdjustment(QualityAdjustmentType.PENALTY, Decimal("0.15"), "质量不达标扣减")
        }

    def calculate_quality_adjustment(self, quality_score: float, base_cost: Decimal) -> QualityAdjustment:
        """
        Calculate quality-based adjustment.
        
        Args:
            quality_score: Quality score (0.0 to 1.0)
            base_cost: Base cost before adjustment
            
        Returns:
            Quality adjustment details
        """
        if quality_score >= self.quality_thresholds["excellent"]:
            adjustment = self.quality_adjustments["excellent"]
        elif quality_score >= self.quality_thresholds["good"]:
            adjustment = self.quality_adjustments["good"]
        elif quality_score >= self.quality_thresholds["acceptable"]:
            adjustment = self.quality_adjustments["acceptable"]
        else:
            adjustment = self.quality_adjustments["poor"]
        
        # Create a copy with actual quality score
        return QualityAdjustment(
            type=adjustment.type,
            percentage=adjustment.percentage,
            reason=adjustment.reason,
            quality_score=quality_score,
            baseline_score=self.quality_thresholds["acceptable"]
        )

    def apply_quality_adjustment(self, base_cost: Decimal, adjustment: QualityAdjustment) -> Decimal:
        """
        Apply quality adjustment to base cost.
        
        Args:
            base_cost: Original cost
            adjustment: Quality adjustment to apply
            
        Returns:
            Adjusted cost
        """
        if adjustment.type == QualityAdjustmentType.BONUS:
            return base_cost * (Decimal("1") + adjustment.percentage)
        elif adjustment.type == QualityAdjustmentType.PENALTY:
            return base_cost * (Decimal("1") - adjustment.percentage)
        else:
            return base_cost

    def calculate_tax(self, amount: Decimal, tax_config: TaxConfiguration) -> Decimal:
        """
        Calculate tax amount.
        
        Args:
            amount: Taxable amount
            tax_config: Tax configuration
            
        Returns:
            Tax amount
        """
        if tax_config.tax_type == TaxType.NONE:
            return Decimal("0")
        
        return (amount * tax_config.rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def apply_discount(self, amount: Decimal, discount: DiscountConfiguration) -> Decimal:
        """
        Apply discount to amount.
        
        Args:
            amount: Original amount
            discount: Discount configuration
            
        Returns:
            Discounted amount
        """
        discount_amount = (amount * discount.percentage / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return amount - discount_amount

    def generate_project_breakdown(self, billing_records: List[BillingRecord], 
                                 quality_scores: Dict[str, float]) -> List[ProjectBreakdown]:
        """
        Generate project-level billing breakdown.
        
        Args:
            billing_records: List of billing records
            quality_scores: Quality scores by project/task
            
        Returns:
            List of project breakdowns
        """
        project_data = {}
        
        # Group records by project (using task_id as project identifier for now)
        for record in billing_records:
            project_id = str(record.task_id) if record.task_id else "unknown"
            
            if project_id not in project_data:
                project_data[project_id] = {
                    "records": [],
                    "total_annotations": 0,
                    "total_time_spent": 0,
                    "base_cost": Decimal("0")
                }
            
            project_data[project_id]["records"].append(record)
            project_data[project_id]["total_annotations"] += record.annotation_count
            project_data[project_id]["total_time_spent"] += record.time_spent
            project_data[project_id]["base_cost"] += record.cost

        # Generate breakdowns
        breakdowns = []
        for project_id, data in project_data.items():
            # Get quality score for project
            quality_score = quality_scores.get(project_id, 0.75)  # Default to acceptable
            
            # Calculate quality adjustment
            quality_adjustment = self.calculate_quality_adjustment(quality_score, data["base_cost"])
            adjusted_cost = self.apply_quality_adjustment(data["base_cost"], quality_adjustment)
            
            # Create line items
            line_items = []
            for i, record in enumerate(data["records"]):
                line_item = InvoiceLineItem(
                    id=f"{project_id}_item_{i}",
                    description=f"标注工作 - 用户 {record.user_id}",
                    quantity=record.annotation_count,
                    unit_price=record.cost / record.annotation_count if record.annotation_count > 0 else Decimal("0"),
                    subtotal=record.cost,
                    quality_adjustment=quality_adjustment,
                    adjusted_subtotal=self.apply_quality_adjustment(record.cost, quality_adjustment),
                    metadata={
                        "user_id": record.user_id,
                        "time_spent": record.time_spent,
                        "billing_date": record.billing_date.isoformat()
                    }
                )
                line_items.append(line_item)
            
            breakdown = ProjectBreakdown(
                project_id=project_id,
                project_name=f"项目 {project_id}",
                total_annotations=data["total_annotations"],
                total_time_spent=data["total_time_spent"],
                base_cost=data["base_cost"],
                quality_adjustments=[quality_adjustment],
                adjusted_cost=adjusted_cost,
                line_items=line_items
            )
            breakdowns.append(breakdown)
        
        return breakdowns

    def generate_user_breakdown(self, billing_records: List[BillingRecord],
                              quality_scores: Dict[str, float]) -> List[UserBreakdown]:
        """
        Generate user-level billing breakdown.
        
        Args:
            billing_records: List of billing records
            quality_scores: Quality scores by user
            
        Returns:
            List of user breakdowns
        """
        user_data = {}
        
        # Group records by user
        for record in billing_records:
            user_id = record.user_id
            
            if user_id not in user_data:
                user_data[user_id] = {
                    "records": [],
                    "total_annotations": 0,
                    "total_time_spent": 0,
                    "base_cost": Decimal("0")
                }
            
            user_data[user_id]["records"].append(record)
            user_data[user_id]["total_annotations"] += record.annotation_count
            user_data[user_id]["total_time_spent"] += record.time_spent
            user_data[user_id]["base_cost"] += record.cost

        # Generate breakdowns
        breakdowns = []
        for user_id, data in user_data.items():
            # Get quality score for user
            quality_score = quality_scores.get(user_id, 0.75)  # Default to acceptable
            
            # Calculate quality adjustment
            quality_adjustment = self.calculate_quality_adjustment(quality_score, data["base_cost"])
            adjusted_cost = self.apply_quality_adjustment(data["base_cost"], quality_adjustment)
            
            # Create task breakdowns
            tasks = []
            for record in data["records"]:
                task_breakdown = TaskBreakdown(
                    task_id=str(record.task_id) if record.task_id else "unknown",
                    task_name=f"任务 {record.task_id}",
                    project_id=str(record.task_id) if record.task_id else "unknown",
                    annotations=record.annotation_count,
                    time_spent=record.time_spent,
                    base_cost=record.cost,
                    quality_score=quality_score,
                    quality_adjustment=quality_adjustment,
                    adjusted_cost=self.apply_quality_adjustment(record.cost, quality_adjustment)
                )
                tasks.append(task_breakdown)
            
            breakdown = UserBreakdown(
                user_id=user_id,
                user_name=f"用户 {user_id}",
                total_annotations=data["total_annotations"],
                total_time_spent=data["total_time_spent"],
                base_cost=data["base_cost"],
                quality_adjustments=[quality_adjustment],
                adjusted_cost=adjusted_cost,
                tasks=tasks
            )
            breakdowns.append(breakdown)
        
        return breakdowns

    def generate_detailed_invoice(self, 
                                tenant_id: str,
                                billing_period: str,
                                billing_records: List[BillingRecord],
                                quality_scores: Optional[Dict[str, float]] = None,
                                tax_config: Optional[TaxConfiguration] = None,
                                discounts: Optional[List[DiscountConfiguration]] = None,
                                template_name: str = "standard") -> Dict[str, Any]:
        """
        Generate detailed invoice with multi-level breakdowns.
        
        Args:
            tenant_id: Tenant identifier
            billing_period: Billing period (YYYY-MM)
            billing_records: List of billing records
            quality_scores: Quality scores for adjustments
            tax_config: Tax configuration
            discounts: List of discount configurations
            template_name: Invoice template name
            
        Returns:
            Detailed invoice data
        """
        if quality_scores is None:
            quality_scores = {}
        if discounts is None:
            discounts = []
        
        # Calculate base totals
        base_total = sum(record.cost for record in billing_records)
        total_annotations = sum(record.annotation_count for record in billing_records)
        total_time_spent = sum(record.time_spent for record in billing_records)
        
        # Generate breakdowns
        project_breakdowns = self.generate_project_breakdown(billing_records, quality_scores)
        user_breakdowns = self.generate_user_breakdown(billing_records, quality_scores)
        
        # Calculate adjusted subtotal
        adjusted_subtotal = sum(pb.adjusted_cost for pb in project_breakdowns)
        
        # Apply discounts
        discounted_subtotal = adjusted_subtotal
        discount_details = []
        for discount in discounts:
            if discount.applies_to == "subtotal":
                discount_amount = (adjusted_subtotal * discount.percentage / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                discounted_subtotal -= discount_amount
                discount_details.append({
                    "description": discount.description,
                    "percentage": float(discount.percentage),
                    "amount": float(discount_amount)
                })
        
        # Calculate tax
        tax_amount = Decimal("0")
        tax_details = None
        if tax_config and tax_config.tax_type != TaxType.NONE:
            tax_amount = self.calculate_tax(discounted_subtotal, tax_config)
            tax_details = {
                "type": tax_config.tax_type.value,
                "rate": float(tax_config.rate),
                "description": tax_config.description,
                "amount": float(tax_amount)
            }
        
        # Calculate final total
        final_total = discounted_subtotal + tax_amount
        
        # Generate invoice
        invoice = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "billing_period": billing_period,
            "status": InvoiceStatus.DRAFT.value,
            "template_name": template_name,
            "generated_at": datetime.now().isoformat(),
            
            # Summary
            "summary": {
                "total_annotations": total_annotations,
                "total_time_spent": total_time_spent,
                "base_total": float(base_total),
                "adjusted_subtotal": float(adjusted_subtotal),
                "discounted_subtotal": float(discounted_subtotal),
                "tax_amount": float(tax_amount),
                "final_total": float(final_total)
            },
            
            # Breakdowns
            "project_breakdown": [
                {
                    "project_id": pb.project_id,
                    "project_name": pb.project_name,
                    "total_annotations": pb.total_annotations,
                    "total_time_spent": pb.total_time_spent,
                    "base_cost": float(pb.base_cost),
                    "adjusted_cost": float(pb.adjusted_cost),
                    "quality_adjustments": [
                        {
                            "type": qa.type.value,
                            "percentage": float(qa.percentage),
                            "reason": qa.reason,
                            "quality_score": qa.quality_score
                        } for qa in pb.quality_adjustments
                    ],
                    "line_items": [
                        {
                            "id": li.id,
                            "description": li.description,
                            "quantity": li.quantity,
                            "unit_price": float(li.unit_price),
                            "subtotal": float(li.subtotal),
                            "adjusted_subtotal": float(li.adjusted_subtotal) if li.adjusted_subtotal else None,
                            "metadata": li.metadata
                        } for li in pb.line_items
                    ]
                } for pb in project_breakdowns
            ],
            
            "user_breakdown": [
                {
                    "user_id": ub.user_id,
                    "user_name": ub.user_name,
                    "total_annotations": ub.total_annotations,
                    "total_time_spent": ub.total_time_spent,
                    "base_cost": float(ub.base_cost),
                    "adjusted_cost": float(ub.adjusted_cost),
                    "quality_adjustments": [
                        {
                            "type": qa.type.value,
                            "percentage": float(qa.percentage),
                            "reason": qa.reason,
                            "quality_score": qa.quality_score
                        } for qa in ub.quality_adjustments
                    ],
                    "tasks": [
                        {
                            "task_id": tb.task_id,
                            "task_name": tb.task_name,
                            "project_id": tb.project_id,
                            "annotations": tb.annotations,
                            "time_spent": tb.time_spent,
                            "base_cost": float(tb.base_cost),
                            "quality_score": tb.quality_score,
                            "adjusted_cost": float(tb.adjusted_cost)
                        } for tb in ub.tasks
                    ]
                } for ub in user_breakdowns
            ],
            
            # Financial details
            "discounts": discount_details,
            "tax": tax_details,
            
            # Metadata
            "metadata": {
                "record_count": len(billing_records),
                "quality_scores_provided": len(quality_scores),
                "discounts_applied": len(discounts),
                "tax_applied": tax_config is not None and tax_config.tax_type != TaxType.NONE
            }
        }
        
        return invoice

    def get_invoice_templates(self) -> Dict[str, str]:
        """
        Get available invoice templates.
        
        Returns:
            Dictionary of template names and descriptions
        """
        return {
            "standard": "标准发票模板",
            "detailed": "详细发票模板",
            "summary": "汇总发票模板",
            "project_focused": "项目导向发票模板",
            "user_focused": "用户导向发票模板"
        }

    def render_invoice_html(self, invoice_data: Dict[str, Any], template_name: str = "standard") -> str:
        """
        Render invoice as HTML using template.
        
        Args:
            invoice_data: Invoice data
            template_name: Template to use
            
        Returns:
            Rendered HTML string
        """
        # Basic HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>发票 - {{ invoice_data.id }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { border-bottom: 2px solid #333; padding-bottom: 10px; }
                .summary { margin: 20px 0; }
                .breakdown { margin: 20px 0; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .total { font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>发票</h1>
                <p>发票编号: {{ invoice_data.id }}</p>
                <p>租户: {{ invoice_data.tenant_id }}</p>
                <p>计费周期: {{ invoice_data.billing_period }}</p>
                <p>生成时间: {{ invoice_data.generated_at }}</p>
            </div>
            
            <div class="summary">
                <h2>汇总信息</h2>
                <table>
                    <tr><td>总标注数</td><td>{{ invoice_data.summary.total_annotations }}</td></tr>
                    <tr><td>总工时（秒）</td><td>{{ invoice_data.summary.total_time_spent }}</td></tr>
                    <tr><td>基础费用</td><td>¥{{ "%.2f"|format(invoice_data.summary.base_total) }}</td></tr>
                    <tr><td>质量调整后</td><td>¥{{ "%.2f"|format(invoice_data.summary.adjusted_subtotal) }}</td></tr>
                    <tr><td>折扣后</td><td>¥{{ "%.2f"|format(invoice_data.summary.discounted_subtotal) }}</td></tr>
                    <tr><td>税费</td><td>¥{{ "%.2f"|format(invoice_data.summary.tax_amount) }}</td></tr>
                    <tr class="total"><td>最终总额</td><td>¥{{ "%.2f"|format(invoice_data.summary.final_total) }}</td></tr>
                </table>
            </div>
            
            <div class="breakdown">
                <h2>项目明细</h2>
                {% for project in invoice_data.project_breakdown %}
                <h3>{{ project.project_name }}</h3>
                <table>
                    <tr><td>标注数</td><td>{{ project.total_annotations }}</td></tr>
                    <tr><td>工时</td><td>{{ project.total_time_spent }}秒</td></tr>
                    <tr><td>基础费用</td><td>¥{{ "%.2f"|format(project.base_cost) }}</td></tr>
                    <tr><td>调整后费用</td><td>¥{{ "%.2f"|format(project.adjusted_cost) }}</td></tr>
                </table>
                {% endfor %}
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        return template.render(invoice_data=invoice_data)