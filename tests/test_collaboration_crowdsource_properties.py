"""
Property Tests for Crowdsource Manager and Billing (众包管理器和计费属性测试)

Tests Property 10: 敏感数据过滤
Tests Property 11: 众包计费准确性

**Validates: Requirements 8.2, 8.3, 11.3, 11.4**
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List
from uuid import uuid4


# ============== Local Schema Definitions ==============

class SensitivityFilter:
    """敏感数据过滤器"""
    
    async def filter(self, data: List[dict], max_level: int) -> List[dict]:
        """过滤敏感数据
        
        Args:
            data: 数据列表
            max_level: 最大敏感级别 (1=公开, 2=内部, 3=敏感)
            
        Returns:
            过滤后的数据列表
        """
        return [d for d in data if d.get("sensitivity_level", 1) <= max_level]


class CrowdsourceManager:
    """众包管理器 - 本地测试版本"""
    
    def __init__(self, sensitivity_filter: SensitivityFilter = None):
        self.sensitivity_filter = sensitivity_filter or SensitivityFilter()
        self._tasks: Dict[str, dict] = {}
        self._claims: Dict[str, dict] = {}
        self._submissions: Dict[str, dict] = {}
    
    async def create_crowdsource_task(
        self,
        project_id: str,
        config: dict,
        data: List[dict] = None
    ) -> dict:
        """创建众包任务"""
        if data is None:
            data = []
        
        sensitivity_level = config.get("sensitivity_level", 1)
        filtered_data = await self.sensitivity_filter.filter(data, sensitivity_level)
        
        task = {
            "id": str(uuid4()),
            "project_id": project_id,
            "data_ids": [d.get("id", str(uuid4())) for d in filtered_data],
            "filtered_data": filtered_data,
            "original_data_count": len(data),
            "config": config,
            "status": "open",
            "created_at": datetime.utcnow()
        }
        
        self._tasks[task["id"]] = task
        return task
    
    async def claim_task(
        self,
        task_id: str,
        annotator_id: str,
        claim_duration_hours: int = 2
    ) -> dict:
        """领取任务"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        claim_key = f"{task_id}:{annotator_id}"
        
        claim = {
            "task_id": task_id,
            "annotator_id": annotator_id,
            "claimed_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=claim_duration_hours)
        }
        
        self._claims[claim_key] = claim
        return claim
    
    async def submit_annotation(
        self,
        task_id: str,
        annotator_id: str,
        annotation: dict
    ) -> dict:
        """提交标注"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        config = task.get("config", {})
        price = config.get("price_per_task", 0.1)
        
        submission = {
            "id": str(uuid4()),
            "task_id": task_id,
            "annotator_id": annotator_id,
            "annotation": annotation,
            "status": "pending",
            "price": price,
            "created_at": datetime.utcnow()
        }
        
        self._submissions[submission["id"]] = submission
        return submission
    
    async def approve_submission(self, submission_id: str) -> dict:
        """审核通过提交"""
        submission = self._submissions.get(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        submission["status"] = "approved"
        submission["approved_at"] = datetime.utcnow()
        return submission
    
    async def get_annotator_submissions(
        self,
        annotator_id: str,
        status: str = None
    ) -> List[dict]:
        """获取标注员的提交"""
        submissions = [
            s for s in self._submissions.values()
            if s["annotator_id"] == annotator_id
        ]
        if status:
            submissions = [s for s in submissions if s["status"] == status]
        return submissions


class CrowdsourceBilling:
    """众包计费 - 本地测试版本"""
    
    def __init__(self, crowdsource_manager: CrowdsourceManager = None):
        self.crowdsource_manager = crowdsource_manager
        self._pricing_configs: Dict[str, dict] = {}
    
    async def configure_pricing(self, project_id: str, pricing: dict) -> dict:
        """配置计费"""
        config = {
            "project_id": project_id,
            "base_price": pricing.get("base_price", 0.1),
            "quality_bonus_enabled": pricing.get("quality_bonus_enabled", True),
            "star_bonus_enabled": pricing.get("star_bonus_enabled", True),
            "created_at": datetime.utcnow()
        }
        self._pricing_configs[project_id] = config
        return config
    
    def _get_quality_multiplier(self, quality_score: float) -> float:
        """获取质量系数"""
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
        """获取星级系数 (3星=1.0, 5星=1.2, 1星=0.8)"""
        return 1.0 + (star_rating - 3) * 0.1
    
    async def calculate_earnings(
        self,
        annotator_id: str,
        period_start: datetime,
        period_end: datetime,
        submissions: List[dict] = None,
        annotator: dict = None,
        quality_score: float = 0.85
    ) -> dict:
        """计算收益"""
        if submissions is None:
            submissions = []
        
        if annotator is None:
            annotator = {"star_rating": 3}
        
        # 计算基础金额
        base_amount = sum(s.get("price", 0.1) for s in submissions)
        
        # 质量系数调整
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


# ============== Property 10: 敏感数据过滤 ==============

class TestSensitiveDataFiltering:
    """
    Property 10: 敏感数据过滤
    
    *For any* 众包任务，敏感数据应根据配置的敏感级别被正确过滤。
    
    **Validates: Requirements 8.2, 8.3**
    """
    
    @given(
        public_count=st.integers(min_value=0, max_value=20),
        internal_count=st.integers(min_value=0, max_value=20),
        sensitive_count=st.integers(min_value=0, max_value=20),
        max_level=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100)
    def test_sensitivity_filter_property(
        self,
        public_count: int,
        internal_count: int,
        sensitive_count: int,
        max_level: int
    ):
        """Property: 只有敏感级别 <= max_level 的数据应被包含"""
        manager = CrowdsourceManager()
        
        # 创建不同敏感级别的数据
        data = []
        for i in range(public_count):
            data.append({"id": f"public_{i}", "sensitivity_level": 1})
        for i in range(internal_count):
            data.append({"id": f"internal_{i}", "sensitivity_level": 2})
        for i in range(sensitive_count):
            data.append({"id": f"sensitive_{i}", "sensitivity_level": 3})
        
        # 创建众包任务
        task = asyncio.get_event_loop().run_until_complete(
            manager.create_crowdsource_task(
                project_id="project_1",
                config={"sensitivity_level": max_level},
                data=data
            )
        )
        
        # 验证过滤结果
        filtered_data = task["filtered_data"]
        
        # 计算预期数量
        expected_count = 0
        if max_level >= 1:
            expected_count += public_count
        if max_level >= 2:
            expected_count += internal_count
        if max_level >= 3:
            expected_count += sensitive_count
        
        assert len(filtered_data) == expected_count
        
        # 验证所有过滤后的数据敏感级别都 <= max_level
        for item in filtered_data:
            assert item["sensitivity_level"] <= max_level
    
    def test_level_1_only_public(self):
        """级别1只包含公开数据"""
        manager = CrowdsourceManager()
        
        data = [
            {"id": "1", "sensitivity_level": 1},
            {"id": "2", "sensitivity_level": 2},
            {"id": "3", "sensitivity_level": 3},
        ]
        
        task = asyncio.get_event_loop().run_until_complete(
            manager.create_crowdsource_task(
                project_id="project_1",
                config={"sensitivity_level": 1},
                data=data
            )
        )
        
        assert len(task["filtered_data"]) == 1
        assert task["filtered_data"][0]["id"] == "1"
    
    def test_level_2_includes_internal(self):
        """级别2包含公开和内部数据"""
        manager = CrowdsourceManager()
        
        data = [
            {"id": "1", "sensitivity_level": 1},
            {"id": "2", "sensitivity_level": 2},
            {"id": "3", "sensitivity_level": 3},
        ]
        
        task = asyncio.get_event_loop().run_until_complete(
            manager.create_crowdsource_task(
                project_id="project_1",
                config={"sensitivity_level": 2},
                data=data
            )
        )
        
        assert len(task["filtered_data"]) == 2
        ids = [d["id"] for d in task["filtered_data"]]
        assert "1" in ids
        assert "2" in ids
    
    def test_level_3_includes_all(self):
        """级别3包含所有数据"""
        manager = CrowdsourceManager()
        
        data = [
            {"id": "1", "sensitivity_level": 1},
            {"id": "2", "sensitivity_level": 2},
            {"id": "3", "sensitivity_level": 3},
        ]
        
        task = asyncio.get_event_loop().run_until_complete(
            manager.create_crowdsource_task(
                project_id="project_1",
                config={"sensitivity_level": 3},
                data=data
            )
        )
        
        assert len(task["filtered_data"]) == 3
    
    def test_default_sensitivity_level(self):
        """默认敏感级别为1（公开）"""
        manager = CrowdsourceManager()
        
        data = [
            {"id": "1"},  # 无敏感级别，默认为1
            {"id": "2", "sensitivity_level": 2},
        ]
        
        task = asyncio.get_event_loop().run_until_complete(
            manager.create_crowdsource_task(
                project_id="project_1",
                config={"sensitivity_level": 1},
                data=data
            )
        )
        
        # 只有默认级别1的数据被包含
        assert len(task["filtered_data"]) == 1
        assert task["filtered_data"][0]["id"] == "1"


# ============== Property 11: 众包计费准确性 ==============

class TestCrowdsourceBillingAccuracy:
    """
    Property 11: 众包计费准确性
    
    *For any* 众包标注员的收益计算，应正确应用质量系数和星级系数。
    
    **Validates: Requirements 11.3, 11.4**
    """
    
    @given(
        task_count=st.integers(min_value=1, max_value=50),
        price_per_task=st.floats(min_value=0.01, max_value=10.0),
        quality_score=st.floats(min_value=0.0, max_value=1.0),
        star_rating=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_earnings_calculation_property(
        self,
        task_count: int,
        price_per_task: float,
        quality_score: float,
        star_rating: int
    ):
        """Property: 收益 = 基础金额 × 质量系数 × 星级系数"""
        billing = CrowdsourceBilling()
        
        # 创建提交
        submissions = [
            {"id": f"sub_{i}", "price": price_per_task, "status": "approved"}
            for i in range(task_count)
        ]
        
        annotator = {"star_rating": star_rating}
        
        earnings = asyncio.get_event_loop().run_until_complete(
            billing.calculate_earnings(
                annotator_id="annotator_1",
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
                submissions=submissions,
                annotator=annotator,
                quality_score=quality_score
            )
        )
        
        # 验证基础金额
        expected_base = task_count * price_per_task
        assert abs(earnings["base_amount"] - expected_base) < 0.0001
        
        # 验证质量系数
        expected_quality_mult = billing._get_quality_multiplier(quality_score)
        assert earnings["quality_multiplier"] == expected_quality_mult
        
        # 验证星级系数
        expected_star_mult = billing._get_star_multiplier(star_rating)
        assert abs(earnings["star_multiplier"] - expected_star_mult) < 0.0001
        
        # 验证总金额
        expected_total = expected_base * expected_quality_mult * expected_star_mult
        assert abs(earnings["total_amount"] - expected_total) < 0.0001
    
    def test_quality_multiplier_tiers(self):
        """验证质量系数分级"""
        billing = CrowdsourceBilling()
        
        # 95%+ -> 1.2
        assert billing._get_quality_multiplier(0.95) == 1.2
        assert billing._get_quality_multiplier(1.0) == 1.2
        
        # 90-95% -> 1.1
        assert billing._get_quality_multiplier(0.90) == 1.1
        assert billing._get_quality_multiplier(0.94) == 1.1
        
        # 80-90% -> 1.0
        assert billing._get_quality_multiplier(0.80) == 1.0
        assert billing._get_quality_multiplier(0.89) == 1.0
        
        # 70-80% -> 0.9
        assert billing._get_quality_multiplier(0.70) == 0.9
        assert billing._get_quality_multiplier(0.79) == 0.9
        
        # <70% -> 0.8
        assert billing._get_quality_multiplier(0.69) == 0.8
        assert billing._get_quality_multiplier(0.0) == 0.8
    
    def test_star_multiplier_calculation(self):
        """验证星级系数计算"""
        billing = CrowdsourceBilling()
        
        # 1星 -> 0.8
        assert abs(billing._get_star_multiplier(1) - 0.8) < 0.0001
        
        # 2星 -> 0.9
        assert abs(billing._get_star_multiplier(2) - 0.9) < 0.0001
        
        # 3星 -> 1.0
        assert abs(billing._get_star_multiplier(3) - 1.0) < 0.0001
        
        # 4星 -> 1.1
        assert abs(billing._get_star_multiplier(4) - 1.1) < 0.0001
        
        # 5星 -> 1.2
        assert abs(billing._get_star_multiplier(5) - 1.2) < 0.0001
    
    def test_high_quality_high_star_bonus(self):
        """高质量高星级获得最大奖励"""
        billing = CrowdsourceBilling()
        
        submissions = [{"id": "1", "price": 1.0, "status": "approved"}]
        
        earnings = asyncio.get_event_loop().run_until_complete(
            billing.calculate_earnings(
                annotator_id="annotator_1",
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
                submissions=submissions,
                annotator={"star_rating": 5},
                quality_score=0.98
            )
        )
        
        # 1.0 * 1.2 * 1.2 = 1.44
        assert abs(earnings["total_amount"] - 1.44) < 0.0001
    
    def test_low_quality_low_star_penalty(self):
        """低质量低星级获得最大惩罚"""
        billing = CrowdsourceBilling()
        
        submissions = [{"id": "1", "price": 1.0, "status": "approved"}]
        
        earnings = asyncio.get_event_loop().run_until_complete(
            billing.calculate_earnings(
                annotator_id="annotator_1",
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
                submissions=submissions,
                annotator={"star_rating": 1},
                quality_score=0.5
            )
        )
        
        # 1.0 * 0.8 * 0.8 = 0.64
        assert abs(earnings["total_amount"] - 0.64) < 0.0001
    
    def test_empty_submissions(self):
        """无提交时收益为0"""
        billing = CrowdsourceBilling()
        
        earnings = asyncio.get_event_loop().run_until_complete(
            billing.calculate_earnings(
                annotator_id="annotator_1",
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
                submissions=[],
                annotator={"star_rating": 5},
                quality_score=1.0
            )
        )
        
        assert earnings["base_amount"] == 0
        assert earnings["total_amount"] == 0
        assert earnings["task_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
