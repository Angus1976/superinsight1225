"""
Property Tests for Quality Controller (质量控制器属性测试)

Tests Property 8: 质量评分准确性
Tests Property 9: 质量阈值预警

**Validates: Requirements 5.1, 5.4, 5.6**
"""

import asyncio
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List
from uuid import uuid4


# ============== Local Schema Definitions ==============

class MockNotificationService:
    """模拟通知服务"""
    
    def __init__(self):
        self.warnings_sent = []
    
    async def send_quality_warning(self, user_id: str, accuracy: float, threshold: float):
        self.warnings_sent.append({
            "user_id": user_id,
            "accuracy": accuracy,
            "threshold": threshold
        })


class QualityController:
    """质量控制器 - 本地测试版本"""
    
    def __init__(self, notification_service=None):
        self.notification_service = notification_service
        self._annotations: Dict[str, List[dict]] = {}
    
    async def add_annotation(self, annotator_id: str, annotation: dict) -> None:
        """添加标注记录"""
        if annotator_id not in self._annotations:
            self._annotations[annotator_id] = []
        self._annotations[annotator_id].append(annotation)
    
    async def calculate_accuracy(self, annotator_id: str, project_id: str = None) -> float:
        """计算标注员准确率"""
        annotations = self._annotations.get(annotator_id, [])
        
        if project_id:
            annotations = [a for a in annotations if a.get("project_id") == project_id]
        
        reviewed = [a for a in annotations if a.get("status") in ["approved", "rejected"]]
        
        if not reviewed:
            return 0.0
        
        approved = sum(1 for a in reviewed if a["status"] == "approved")
        return approved / len(reviewed)
    
    async def check_quality_threshold(self, annotator_id: str, threshold: float = 0.8) -> bool:
        """检查质量阈值"""
        accuracy = await self.calculate_accuracy(annotator_id)
        
        if accuracy < threshold:
            if self.notification_service:
                await self.notification_service.send_quality_warning(
                    annotator_id, accuracy, threshold
                )
            return False
        
        return True
    
    async def get_quality_ranking(self, project_id: str, annotator_ids: List[str] = None) -> List[dict]:
        """获取质量排名"""
        if annotator_ids is None:
            annotator_ids = list(self._annotations.keys())
        
        rankings = []
        for annotator_id in annotator_ids:
            accuracy = await self.calculate_accuracy(annotator_id, project_id)
            annotations = self._annotations.get(annotator_id, [])
            
            if project_id:
                annotations = [a for a in annotations if a.get("project_id") == project_id]
            
            total = len(annotations)
            approved = sum(1 for a in annotations if a.get("status") == "approved")
            
            rankings.append({
                "annotator_id": annotator_id,
                "accuracy": accuracy,
                "total_annotations": total,
                "approved_annotations": approved,
                "rank": 0
            })
        
        rankings.sort(key=lambda x: x["accuracy"], reverse=True)
        
        for i, r in enumerate(rankings):
            r["rank"] = i + 1
        
        return rankings


# ============== Test Strategies ==============

def create_annotation(annotation_id: str, status: str, project_id: str = None) -> dict:
    return {
        "id": annotation_id,
        "status": status,
        "project_id": project_id,
        "created_at": datetime.utcnow()
    }


# ============== Property 8: 质量评分准确性 ==============

class TestQualityScoreAccuracy:
    """
    Property 8: 质量评分准确性
    
    *For any* 标注员的质量评分，应基于其已审核标注的通过率准确计算。
    
    **Validates: Requirements 5.1, 5.6**
    """
    
    @given(
        approved_count=st.integers(min_value=0, max_value=50),
        rejected_count=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100)
    def test_accuracy_calculation_property(self, approved_count: int, rejected_count: int):
        """Property: 准确率应等于通过数/总审核数"""
        # 跳过没有审核记录的情况
        total = approved_count + rejected_count
        assume(total > 0)
        
        controller = QualityController()
        annotator_id = "annotator_1"
        
        # 添加已通过的标注
        for i in range(approved_count):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    annotator_id,
                    create_annotation(f"approved_{i}", "approved")
                )
            )
        
        # 添加已驳回的标注
        for i in range(rejected_count):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    annotator_id,
                    create_annotation(f"rejected_{i}", "rejected")
                )
            )
        
        # 计算准确率
        accuracy = asyncio.get_event_loop().run_until_complete(
            controller.calculate_accuracy(annotator_id)
        )
        
        # 验证准确率计算正确
        expected_accuracy = approved_count / total
        assert abs(accuracy - expected_accuracy) < 0.0001
    
    def test_no_reviewed_annotations_returns_zero(self):
        """没有审核记录时准确率应为0"""
        controller = QualityController()
        
        # 添加未审核的标注
        asyncio.get_event_loop().run_until_complete(
            controller.add_annotation(
                "annotator_1",
                create_annotation("pending_1", "pending")
            )
        )
        
        accuracy = asyncio.get_event_loop().run_until_complete(
            controller.calculate_accuracy("annotator_1")
        )
        
        assert accuracy == 0.0
    
    def test_all_approved_returns_one(self):
        """全部通过时准确率应为1"""
        controller = QualityController()
        
        for i in range(10):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    "annotator_1",
                    create_annotation(f"approved_{i}", "approved")
                )
            )
        
        accuracy = asyncio.get_event_loop().run_until_complete(
            controller.calculate_accuracy("annotator_1")
        )
        
        assert accuracy == 1.0
    
    def test_all_rejected_returns_zero(self):
        """全部驳回时准确率应为0"""
        controller = QualityController()
        
        for i in range(10):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    "annotator_1",
                    create_annotation(f"rejected_{i}", "rejected")
                )
            )
        
        accuracy = asyncio.get_event_loop().run_until_complete(
            controller.calculate_accuracy("annotator_1")
        )
        
        assert accuracy == 0.0
    
    def test_accuracy_filtered_by_project(self):
        """准确率应按项目过滤"""
        controller = QualityController()
        
        # 项目1：全部通过
        for i in range(5):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    "annotator_1",
                    create_annotation(f"p1_{i}", "approved", "project_1")
                )
            )
        
        # 项目2：全部驳回
        for i in range(5):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    "annotator_1",
                    create_annotation(f"p2_{i}", "rejected", "project_2")
                )
            )
        
        # 项目1准确率应为1
        accuracy_p1 = asyncio.get_event_loop().run_until_complete(
            controller.calculate_accuracy("annotator_1", "project_1")
        )
        assert accuracy_p1 == 1.0
        
        # 项目2准确率应为0
        accuracy_p2 = asyncio.get_event_loop().run_until_complete(
            controller.calculate_accuracy("annotator_1", "project_2")
        )
        assert accuracy_p2 == 0.0


# ============== Property 9: 质量阈值预警 ==============

class TestQualityThresholdAlert:
    """
    Property 9: 质量阈值预警
    
    *For any* 质量低于阈值的标注员，系统应发送预警通知。
    
    **Validates: Requirements 5.4**
    """
    
    @given(
        accuracy=st.floats(min_value=0, max_value=1),
        threshold=st.floats(min_value=0, max_value=1)
    )
    @settings(max_examples=100)
    def test_threshold_check_property(self, accuracy: float, threshold: float):
        """Property: 准确率低于阈值时应返回False并发送预警"""
        notification_service = MockNotificationService()
        controller = QualityController(notification_service)
        
        annotator_id = "annotator_1"
        
        # 根据目标准确率创建标注
        total = 100
        approved_count = int(accuracy * total)
        rejected_count = total - approved_count
        
        for i in range(approved_count):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    annotator_id,
                    create_annotation(f"approved_{i}", "approved")
                )
            )
        
        for i in range(rejected_count):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    annotator_id,
                    create_annotation(f"rejected_{i}", "rejected")
                )
            )
        
        # 检查阈值
        result = asyncio.get_event_loop().run_until_complete(
            controller.check_quality_threshold(annotator_id, threshold)
        )
        
        actual_accuracy = asyncio.get_event_loop().run_until_complete(
            controller.calculate_accuracy(annotator_id)
        )
        
        # 验证结果
        if actual_accuracy < threshold:
            assert result is False
            assert len(notification_service.warnings_sent) == 1
        else:
            assert result is True
            assert len(notification_service.warnings_sent) == 0
    
    def test_warning_sent_when_below_threshold(self):
        """低于阈值时应发送预警"""
        notification_service = MockNotificationService()
        controller = QualityController(notification_service)
        
        # 创建低质量标注（30%通过率）
        for i in range(3):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    "annotator_1",
                    create_annotation(f"approved_{i}", "approved")
                )
            )
        
        for i in range(7):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    "annotator_1",
                    create_annotation(f"rejected_{i}", "rejected")
                )
            )
        
        result = asyncio.get_event_loop().run_until_complete(
            controller.check_quality_threshold("annotator_1", 0.8)
        )
        
        assert result is False
        assert len(notification_service.warnings_sent) == 1
        assert notification_service.warnings_sent[0]["user_id"] == "annotator_1"
    
    def test_no_warning_when_above_threshold(self):
        """高于阈值时不应发送预警"""
        notification_service = MockNotificationService()
        controller = QualityController(notification_service)
        
        # 创建高质量标注（90%通过率）
        for i in range(9):
            asyncio.get_event_loop().run_until_complete(
                controller.add_annotation(
                    "annotator_1",
                    create_annotation(f"approved_{i}", "approved")
                )
            )
        
        asyncio.get_event_loop().run_until_complete(
            controller.add_annotation(
                "annotator_1",
                create_annotation("rejected_0", "rejected")
            )
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            controller.check_quality_threshold("annotator_1", 0.8)
        )
        
        assert result is True
        assert len(notification_service.warnings_sent) == 0


class TestQualityRanking:
    """质量排名测试"""
    
    @given(
        accuracies=st.lists(
            st.floats(min_value=0, max_value=1),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_ranking_ordered_by_accuracy(self, accuracies: List[float]):
        """Property: 排名应按准确率降序排列"""
        controller = QualityController()
        
        # 为每个标注员创建对应准确率的标注
        for i, accuracy in enumerate(accuracies):
            annotator_id = f"annotator_{i}"
            total = 100
            approved = int(accuracy * total)
            
            for j in range(approved):
                asyncio.get_event_loop().run_until_complete(
                    controller.add_annotation(
                        annotator_id,
                        create_annotation(f"approved_{j}", "approved", "project_1")
                    )
                )
            
            for j in range(total - approved):
                asyncio.get_event_loop().run_until_complete(
                    controller.add_annotation(
                        annotator_id,
                        create_annotation(f"rejected_{j}", "rejected", "project_1")
                    )
                )
        
        rankings = asyncio.get_event_loop().run_until_complete(
            controller.get_quality_ranking("project_1")
        )
        
        # 验证排名按准确率降序
        for i in range(len(rankings) - 1):
            assert rankings[i]["accuracy"] >= rankings[i + 1]["accuracy"]
        
        # 验证排名号正确
        for i, r in enumerate(rankings):
            assert r["rank"] == i + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
