"""
Quality Controller (质量控制器)

Monitors and ensures annotation quality.
"""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class QualityController:
    """质量控制器 - 监控和保证标注质量"""
    
    def __init__(self, db: "AsyncSession" = None, notification_service=None):
        self.db = db
        self.notification_service = notification_service
        self._annotations: Dict[str, List[dict]] = {}  # annotator_id -> annotations
        self._gold_results: Dict[str, dict] = {}  # annotator_id -> gold test result
    
    async def calculate_accuracy(
        self,
        annotator_id: str,
        project_id: str = None
    ) -> float:
        """计算标注员准确率
        
        Args:
            annotator_id: 标注员ID
            project_id: 项目ID（可选）
            
        Returns:
            准确率 (0.0 - 1.0)
        """
        annotations = self._annotations.get(annotator_id, [])
        
        if project_id:
            annotations = [a for a in annotations if a.get("project_id") == project_id]
        
        # 只计算已审核的标注
        reviewed = [a for a in annotations if a.get("status") in ["approved", "rejected"]]
        
        if not reviewed:
            return 0.0
        
        approved = sum(1 for a in reviewed if a["status"] == "approved")
        return approved / len(reviewed)
    
    async def add_annotation(
        self,
        annotator_id: str,
        annotation: dict
    ) -> None:
        """添加标注记录（用于测试）"""
        if annotator_id not in self._annotations:
            self._annotations[annotator_id] = []
        self._annotations[annotator_id].append(annotation)
    
    async def sample_for_review(
        self,
        project_id: str,
        annotations: List[dict],
        sample_rate: float = 0.1
    ) -> List[str]:
        """抽样检查
        
        Args:
            project_id: 项目ID
            annotations: 标注列表
            sample_rate: 抽样率
            
        Returns:
            抽样的标注ID列表
        """
        # 筛选未审核的标注
        unreviewed = [a for a in annotations if a.get("status") == "pending"]
        
        sample_size = max(1, int(len(unreviewed) * sample_rate))
        sample_size = min(sample_size, len(unreviewed))
        
        sampled = random.sample(unreviewed, sample_size)
        return [a["id"] for a in sampled]
    
    async def run_gold_standard_test(
        self,
        annotator_id: str,
        gold_tasks: List[dict]
    ) -> dict:
        """黄金标准测试
        
        Args:
            annotator_id: 标注员ID
            gold_tasks: 黄金标准任务列表 [{task_id, gold_answer}]
            
        Returns:
            GoldTestResult dict
        """
        results = []
        
        for task in gold_tasks:
            # 获取标注员对该任务的标注
            annotation = await self._get_annotation(annotator_id, task["task_id"])
            
            if annotation:
                is_correct = self._compare_with_gold(
                    annotation.get("annotation", {}),
                    task["gold_answer"]
                )
            else:
                is_correct = False
            
            results.append(is_correct)
        
        accuracy = sum(results) / len(results) if results else 0.0
        passed = accuracy >= 0.8
        
        result = {
            "annotator_id": annotator_id,
            "accuracy": accuracy,
            "passed": passed,
            "details": results,
            "tested_at": datetime.utcnow()
        }
        
        self._gold_results[annotator_id] = result
        return result
    
    async def _get_annotation(self, annotator_id: str, task_id: str) -> Optional[dict]:
        """获取标注员对特定任务的标注"""
        annotations = self._annotations.get(annotator_id, [])
        for a in annotations:
            if a.get("task_id") == task_id:
                return a
        return None
    
    def _compare_with_gold(
        self,
        annotation: Dict[str, Any],
        gold_answer: Dict[str, Any]
    ) -> bool:
        """比较标注与黄金标准"""
        # 简单比较：检查关键字段是否匹配
        if "label" in gold_answer:
            if annotation.get("label") != gold_answer["label"]:
                return False
        
        if "value" in gold_answer:
            if annotation.get("value") != gold_answer["value"]:
                return False
        
        return True
    
    async def check_quality_threshold(
        self,
        annotator_id: str,
        threshold: float = 0.8
    ) -> bool:
        """检查质量阈值
        
        Args:
            annotator_id: 标注员ID
            threshold: 质量阈值
            
        Returns:
            是否达标
        """
        accuracy = await self.calculate_accuracy(annotator_id)
        
        if accuracy < threshold:
            if self.notification_service:
                await self.notification_service.send_quality_warning(
                    annotator_id, accuracy, threshold
                )
            return False
        
        return True
    
    async def get_quality_ranking(
        self,
        project_id: str,
        annotator_ids: List[str] = None
    ) -> List[dict]:
        """获取质量排名
        
        Args:
            project_id: 项目ID
            annotator_ids: 标注员ID列表
            
        Returns:
            质量排名列表
        """
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
                "annotator_name": f"Annotator {annotator_id[:8]}",
                "accuracy": accuracy,
                "total_annotations": total,
                "approved_annotations": approved,
                "rank": 0  # 将在排序后设置
            })
        
        # 按准确率排序
        rankings.sort(key=lambda x: x["accuracy"], reverse=True)
        
        # 设置排名
        for i, r in enumerate(rankings):
            r["rank"] = i + 1
        
        return rankings
    
    async def generate_quality_report(
        self,
        project_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> dict:
        """生成质量趋势报告
        
        Args:
            project_id: 项目ID
            period_start: 开始时间
            period_end: 结束时间
            
        Returns:
            QualityReport dict
        """
        rankings = await self.get_quality_ranking(project_id)
        
        # 计算整体准确率
        if rankings:
            overall_accuracy = sum(r["accuracy"] for r in rankings) / len(rankings)
        else:
            overall_accuracy = 0.0
        
        return {
            "project_id": project_id,
            "period_start": period_start,
            "period_end": period_end,
            "overall_accuracy": overall_accuracy,
            "annotator_rankings": rankings,
            "trend_data": [],  # 实际实现会计算趋势数据
            "generated_at": datetime.utcnow()
        }
