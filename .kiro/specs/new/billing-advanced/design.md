# Design Document

## Overview

计费细节完善系统为SuperInsight 2.3提供企业级的精细化计费管理能力。系统基于现有计费架构扩展，实现工时统计、多维度计费、账单生成、Excel导出和奖励发放，确保计费的准确性、透明性和灵活性。

## Architecture Design

### System Architecture

```
Billing Advanced System
├── Work Time Management
│   ├── Time Tracker
│   ├── Activity Monitor
│   ├── Productivity Analyzer
│   └── Time Validator
├── Multi-Dimensional Billing
│   ├── Rate Calculator
│   ├── Pricing Engine
│   ├── Discount Manager
│   └── Tax Calculator
├── Invoice Generation
│   ├── Invoice Builder
│   ├── Template Engine
│   ├── PDF Generator
│   └── Email Sender
├── Reward System
│   ├── Performance Evaluator
│   ├── Bonus Calculator
│   ├── Incentive Manager
│   └── Payout Processor
└── Reporting & Export
    ├── Report Generator
    ├── Excel Exporter
    ├── Analytics Dashboard
    └── Audit Trail
```

## Implementation Strategy

### Phase 1: 基于现有计费系统扩展

#### 扩展现有工时计算器
```python
# 扩展 src/quality_billing/work_time_calculator.py
from src.quality_billing.work_time_calculator import WorkTimeCalculator

class AdvancedWorkTimeCalculator(WorkTimeCalculator):
    """高级工时计算器 - 基于现有工时计算"""
    
    def __init__(self):
        super().__init__()  # 保持现有工时计算逻辑
        self.activity_monitor = ActivityMonitor()
        self.productivity_analyzer = ProductivityAnalyzer()
        self.time_validator = TimeValidator()
    
    async def calculate_detailed_work_time(
        self, 
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        task_context: dict = None
    ) -> DetailedWorkTime:
        """详细工时计算"""
        # 基于现有工时计算逻辑
        base_work_time = await super().calculate_work_time(
            user_id, start_time, end_time
        )
        
        # 活动监控分析
        activity_data = await self.activity_monitor.get_activity_data(
            user_id, start_time, end_time
        )
        
        # 生产力分析
        productivity_metrics = await self.productivity_analyzer.analyze(
            user_id, activity_data, task_context
        )
        
        # 时间验证
        validation_result = await self.time_validator.validate_time_entries(
            user_id, start_time, end_time, activity_data
        )
        
        return DetailedWorkTime(
            user_id=user_id,
            period_start=start_time,
            period_end=end_time,
            total_hours=base_work_time.total_hours,
            billable_hours=await self.calculate_billable_hours(activity_data),
            productive_hours=productivity_metrics.productive_hours,
            break_time=activity_data.break_time,
            overtime_hours=await self.calculate_overtime(base_work_time),
            activity_breakdown=activity_data.breakdown,
            productivity_score=productivity_metrics.score,
            validation_status=validation_result.status,
            quality_factor=await self.calculate_quality_factor(user_id, task_context)
        )
```

#### 扩展现有计费服务
```python
# 扩展 src/billing/invoice_generator.py
from src.billing.invoice_generator import InvoiceGenerator

class AdvancedInvoiceGenerator(InvoiceGenerator):
    """高级发票生成器"""
    
    def __init__(self):
        super().__init__()  # 保持现有发票生成逻辑
        self.pricing_engine = PricingEngine()
        self.discount_manager = DiscountManager()
        self.tax_calculator = TaxCalculator()
    
    async def generate_detailed_invoice(
        self, 
        billing_period: BillingPeriod,
        client_id: str,
        billing_items: List[BillingItem]
    ) -> DetailedInvoice:
        """生成详细发票"""
        # 基于现有发票生成逻辑
        base_invoice = await super().generate_invoice(
            billing_period, client_id, billing_items
        )
        
        # 多维度定价计算
        pricing_details = []
        for item in billing_items:
            item_pricing = await self.pricing_engine.calculate_pricing(item)
            pricing_details.append(item_pricing)
        
        # 折扣计算
        applicable_discounts = await self.discount_manager.get_applicable_discounts(
            client_id, billing_items
        )
        discount_amount = await self.discount_manager.calculate_discount(
            pricing_details, applicable_discounts
        )
        
        # 税费计算
        tax_details = await self.tax_calculator.calculate_taxes(
            pricing_details, discount_amount, client_id
        )
        
        return DetailedInvoice(
            **base_invoice.dict(),
            pricing_breakdown=pricing_details,
            discounts_applied=applicable_discounts,
            discount_amount=discount_amount,
            tax_details=tax_details,
            subtotal=sum(p.amount for p in pricing_details),
            total_amount=sum(p.amount for p in pricing_details) - discount_amount + tax_details.total_tax
        )
```

### Phase 2: 奖励系统实现

#### 扩展现有奖励系统
```python
# 扩展 src/billing/reward_system.py
from src.billing.reward_system import RewardSystem

class AdvancedRewardSystem(RewardSystem):
    """高级奖励系统"""
    
    def __init__(self):
        super().__init__()  # 保持现有奖励逻辑
        self.performance_evaluator = PerformanceEvaluator()
        self.bonus_calculator = BonusCalculator()
        self.incentive_manager = IncentiveManager()
    
    async def calculate_comprehensive_rewards(
        self, 
        user_id: str,
        evaluation_period: DateRange,
        performance_data: dict = None
    ) -> ComprehensiveReward:
        """综合奖励计算"""
        # 基于现有奖励计算逻辑
        base_reward = await super().calculate_reward(user_id, evaluation_period)
        
        # 性能评估
        performance_metrics = await self.performance_evaluator.evaluate(
            user_id, evaluation_period, performance_data
        )
        
        # 质量奖励
        quality_bonus = await self.bonus_calculator.calculate_quality_bonus(
            user_id, performance_metrics.quality_score
        )
        
        # 效率奖励
        efficiency_bonus = await self.bonus_calculator.calculate_efficiency_bonus(
            user_id, performance_metrics.efficiency_score
        )
        
        # 团队协作奖励
        collaboration_bonus = await self.bonus_calculator.calculate_collaboration_bonus(
            user_id, performance_metrics.collaboration_score
        )
        
        # 里程碑奖励
        milestone_rewards = await self.incentive_manager.get_milestone_rewards(
            user_id, evaluation_period
        )
        
        return ComprehensiveReward(
            user_id=user_id,
            period=evaluation_period,
            base_reward=base_reward.amount,
            quality_bonus=quality_bonus,
            efficiency_bonus=efficiency_bonus,
            collaboration_bonus=collaboration_bonus,
            milestone_rewards=milestone_rewards,
            total_reward=base_reward.amount + quality_bonus + efficiency_bonus + 
                        collaboration_bonus + sum(r.amount for r in milestone_rewards),
            performance_metrics=performance_metrics
        )
```

### Phase 3: 导出和报告系统

#### 扩展现有Excel导出器
```python
# 扩展 src/billing/excel_exporter.py
from src.billing.excel_exporter import ExcelExporter

class AdvancedExcelExporter(ExcelExporter):
    """高级Excel导出器"""
    
    def __init__(self):
        super().__init__()  # 保持现有导出逻辑
        self.template_manager = TemplateManager()
        self.chart_generator = ChartGenerator()
        self.formatter = AdvancedFormatter()
    
    async def export_comprehensive_billing_report(
        self, 
        billing_data: BillingData,
        export_options: ExportOptions = None
    ) -> ExportResult:
        """导出综合计费报告"""
        # 基于现有导出逻辑
        base_export = await super().export_to_excel(billing_data)
        
        # 创建工作簿
        workbook = openpyxl.Workbook()
        
        # 工时详情工作表
        work_time_sheet = await self.create_work_time_sheet(
            workbook, billing_data.work_time_data
        )
        
        # 计费明细工作表
        billing_sheet = await self.create_billing_details_sheet(
            workbook, billing_data.billing_items
        )
        
        # 奖励统计工作表
        rewards_sheet = await self.create_rewards_sheet(
            workbook, billing_data.reward_data
        )
        
        # 图表分析工作表
        charts_sheet = await self.create_charts_sheet(
            workbook, billing_data
        )
        
        # 应用格式化
        await self.formatter.apply_advanced_formatting(workbook)
        
        # 添加数据透视表
        await self.add_pivot_tables(workbook, billing_data)
        
        # 保存文件
        output_path = await self.save_workbook(workbook, export_options)
        
        return ExportResult(
            file_path=output_path,
            file_size=os.path.getsize(output_path),
            sheets_created=['工时详情', '计费明细', '奖励统计', '图表分析'],
            export_time=datetime.utcnow()
        )
```

This comprehensive design provides enterprise-grade advanced billing capabilities for SuperInsight 2.3, building upon the existing billing infrastructure while adding detailed work time tracking, multi-dimensional pricing, comprehensive reward systems, and advanced reporting capabilities.