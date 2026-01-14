"""
Crowdsource Billing (众包计费)

Manages crowdsourcing billing and settlement.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WithdrawalMethod(str, Enum):
    """提现方式"""
    BANK_TRANSFER = "bank_transfer"
    ALIPAY = "alipay"
    WECHAT = "wechat"


class CrowdsourceBilling:
    """众包计费 - 管理众包标注的计费和结算"""
    
    def __init__(
        self,
        db: "AsyncSession" = None,
        quality_controller=None,
        crowdsource_manager=None,
        annotator_manager=None
    ):
        self.db = db
        self.quality_controller = quality_controller
        self.crowdsource_manager = crowdsource_manager
        self.annotator_manager = annotator_manager
        self._pricing_configs: Dict[str, dict] = {}  # project_id -> config
        self._withdrawals: List[dict] = []
        self._invoices: Dict[str, dict] = {}  # invoice_id -> invoice
    
    async def configure_pricing(self, project_id: str, pricing: dict) -> dict:
        """配置计费
        
        Args:
            project_id: 项目ID
            pricing: 计费配置
            
        Returns:
            PricingConfig dict
        """
        config = {
            "project_id": project_id,
            "base_price": pricing.get("base_price", 0.1),
            "task_type_prices": pricing.get("task_type_prices", {}),
            "quality_bonus_enabled": pricing.get("quality_bonus_enabled", True),
            "star_bonus_enabled": pricing.get("star_bonus_enabled", True),
            "created_at": datetime.utcnow()
        }
        self._pricing_configs[project_id] = config
        return config
    
    async def get_pricing_config(self, project_id: str) -> dict:
        """获取计费配置"""
        return self._pricing_configs.get(project_id, {
            "base_price": 0.1,
            "task_type_prices": {},
            "quality_bonus_enabled": True,
            "star_bonus_enabled": True
        })
    
    async def calculate_earnings(
        self,
        annotator_id: str,
        period_start: datetime,
        period_end: datetime,
        submissions: List[dict] = None,
        annotator: dict = None
    ) -> dict:
        """计算收益
        
        Args:
            annotator_id: 标注员ID
            period_start: 开始时间
            period_end: 结束时间
            submissions: 提交列表（可选，用于测试）
            annotator: 标注员信息（可选，用于测试）
            
        Returns:
            Earnings dict
        """
        # 获取已审核通过的提交
        if submissions is None:
            submissions = await self._get_approved_submissions(
                annotator_id, period_start, period_end
            )
        
        # 获取标注员信息
        if annotator is None and self.annotator_manager:
            annotator = await self.annotator_manager.get_annotator(annotator_id)
        
        if annotator is None:
            annotator = {"star_rating": 3}
        
        # 计算基础金额
        base_amount = sum(s.get("price", 0.1) for s in submissions)
        
        # 质量系数调整
        quality_score = 0.85  # 默认值
        if self.quality_controller:
            quality_score = await self.quality_controller.calculate_accuracy(annotator_id)
        
        quality_multiplier = self._get_quality_multiplier(quality_score)
        
        # 星级系数调整
        star_rating = annotator.get("star_rating", 3)
        star_multiplier = self._get_star_multiplier(star_rating)
        
        total_amount = base_amount * quality_multiplier * star_multiplier
        
        return {
            "annotator_id": annotator_id,
            "base_amount": base_amount,
            "quality_multiplier": quality_multiplier,
            "star_multiplier": star_multiplier,
            "total_amount": total_amount,
            "task_count": len(submissions),
            "period_start": period_start,
            "period_end": period_end
        }
    
    async def _get_approved_submissions(
        self,
        annotator_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> List[dict]:
        """获取已审核通过的提交"""
        if self.crowdsource_manager:
            submissions = await self.crowdsource_manager.get_annotator_submissions(
                annotator_id, status="approved"
            )
            # 过滤时间范围
            return [
                s for s in submissions
                if period_start <= s.get("created_at", datetime.utcnow()) <= period_end
            ]
        return []
    
    def _get_quality_multiplier(self, quality_score: float) -> float:
        """获取质量系数
        
        Args:
            quality_score: 质量分数 (0.0 - 1.0)
            
        Returns:
            质量系数
        """
        if quality_score >= 0.95:
            return 1.2
        elif quality_score >= 0.9:
            return 1.1
        elif quality_score >= 0.8:
            return 1.0
        elif quality_score >= 0.7:
            return 0.9
        else:
            return 0.8
    
    def _get_star_multiplier(self, star_rating: int) -> float:
        """获取星级系数
        
        Args:
            star_rating: 星级 (1-5)
            
        Returns:
            星级系数 (3星=1.0, 5星=1.2, 1星=0.8)
        """
        return 1.0 + (star_rating - 3) * 0.1
    
    async def generate_settlement_report(
        self,
        period_start: datetime,
        period_end: datetime,
        annotator_ids: List[str] = None
    ) -> dict:
        """生成结算报表
        
        Args:
            period_start: 开始时间
            period_end: 结束时间
            annotator_ids: 标注员ID列表（可选）
            
        Returns:
            SettlementReport dict
        """
        if annotator_ids is None and self.annotator_manager:
            annotators = await self.annotator_manager.get_all_annotators()
            annotator_ids = [a["id"] for a in annotators]
        elif annotator_ids is None:
            annotator_ids = []
        
        details = []
        total_amount = 0.0
        
        for annotator_id in annotator_ids:
            earnings = await self.calculate_earnings(
                annotator_id, period_start, period_end
            )
            if earnings["task_count"] > 0:
                details.append(earnings)
                total_amount += earnings["total_amount"]
        
        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_amount": total_amount,
            "annotator_count": len(details),
            "task_count": sum(e["task_count"] for e in details),
            "details": details,
            "generated_at": datetime.utcnow()
        }
    
    async def generate_invoice(
        self,
        annotator_id: str,
        period: str,
        earnings: dict = None
    ) -> dict:
        """生成发票
        
        Args:
            annotator_id: 标注员ID
            period: 结算周期（如 "2026-01"）
            earnings: 收益信息（可选）
            
        Returns:
            Invoice dict
        """
        if earnings is None:
            # 解析周期
            year, month = map(int, period.split("-"))
            period_start = datetime(year, month, 1)
            if month == 12:
                period_end = datetime(year + 1, 1, 1)
            else:
                period_end = datetime(year, month + 1, 1)
            
            earnings = await self.calculate_earnings(
                annotator_id, period_start, period_end
            )
        
        invoice = {
            "id": str(uuid4()),
            "annotator_id": annotator_id,
            "period": period,
            "amount": earnings["total_amount"],
            "task_count": earnings["task_count"],
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        self._invoices[invoice["id"]] = invoice
        return invoice
    
    async def get_invoice(self, invoice_id: str) -> Optional[dict]:
        """获取发票"""
        return self._invoices.get(invoice_id)
    
    async def process_withdrawal(
        self,
        annotator_id: str,
        amount: float,
        method: WithdrawalMethod,
        account_info: Dict[str, str] = None
    ) -> dict:
        """处理提现
        
        Args:
            annotator_id: 标注员ID
            amount: 提现金额
            method: 提现方式
            account_info: 账户信息
            
        Returns:
            WithdrawalResult dict
        """
        # 检查余额
        # 实际实现会从数据库获取余额
        available_balance = 1000.0  # 模拟余额
        
        if amount > available_balance:
            return {
                "success": False,
                "transaction_id": None,
                "amount": amount,
                "method": method,
                "message": "Insufficient balance",
                "processed_at": datetime.utcnow()
            }
        
        if amount <= 0:
            return {
                "success": False,
                "transaction_id": None,
                "amount": amount,
                "method": method,
                "message": "Invalid amount",
                "processed_at": datetime.utcnow()
            }
        
        # 处理提现
        transaction_id = str(uuid4())
        
        withdrawal = {
            "id": transaction_id,
            "annotator_id": annotator_id,
            "amount": amount,
            "method": method.value,
            "account_info": account_info,
            "status": "completed",
            "processed_at": datetime.utcnow()
        }
        
        self._withdrawals.append(withdrawal)
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "amount": amount,
            "method": method,
            "message": "Withdrawal processed successfully",
            "processed_at": datetime.utcnow()
        }
    
    async def get_withdrawal_history(
        self,
        annotator_id: str
    ) -> List[dict]:
        """获取提现历史"""
        return [w for w in self._withdrawals if w["annotator_id"] == annotator_id]
    
    async def get_annotator_balance(self, annotator_id: str) -> float:
        """获取标注员余额"""
        # 实际实现会从数据库计算
        return 1000.0
