"""
Crowdsource Annotator Manager (众包标注员管理器)

Manages the complete lifecycle of crowdsource annotators.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AnnotatorStatus(str, Enum):
    """众包标注员状态"""
    PENDING_VERIFICATION = "pending_verification"
    PENDING_TEST = "pending_test"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class IdentityVerifier:
    """身份验证器"""
    
    async def verify(self, identity_doc: dict) -> dict:
        """验证身份
        
        Args:
            identity_doc: 身份证件信息
            
        Returns:
            VerificationResult dict
        """
        # 实际实现会调用第三方身份验证服务
        # 这里简单模拟验证逻辑
        doc_type = identity_doc.get("doc_type")
        doc_number = identity_doc.get("doc_number")
        
        if not doc_type or not doc_number:
            return {
                "success": False,
                "real_name": None,
                "message": "Missing document information"
            }
        
        # 模拟验证成功
        return {
            "success": True,
            "real_name": f"User_{doc_number[:4]}",
            "message": "Identity verified successfully"
        }


class CrowdsourceAnnotatorManager:
    """众包标注员管理器 - 管理众包标注员的完整生命周期"""
    
    def __init__(
        self,
        db: "AsyncSession" = None,
        identity_verifier: IdentityVerifier = None
    ):
        self.db = db
        self.identity_verifier = identity_verifier or IdentityVerifier()
        self._annotators: Dict[str, dict] = {}  # annotator_id -> annotator
        self._test_submissions: Dict[str, dict] = {}  # key -> submission
    
    async def register(self, registration: dict) -> dict:
        """注册标注员
        
        Args:
            registration: 注册信息 (email, name, phone, password)
            
        Returns:
            CrowdsourceAnnotator dict
        """
        # 检查邮箱是否已注册
        for annotator in self._annotators.values():
            if annotator["email"] == registration.get("email"):
                raise ValueError("Email already registered")
        
        annotator = {
            "id": str(uuid4()),
            "email": registration.get("email"),
            "name": registration.get("name"),
            "phone": registration.get("phone"),
            "real_name": None,
            "identity_verified": False,
            "status": AnnotatorStatus.PENDING_VERIFICATION.value,
            "star_rating": 0,
            "ability_tags": [],
            "total_tasks": 0,
            "total_earnings": 0.0,
            "created_at": datetime.utcnow()
        }
        
        self._annotators[annotator["id"]] = annotator
        return annotator
    
    async def get_annotator(self, annotator_id: str) -> Optional[dict]:
        """获取标注员信息"""
        return self._annotators.get(annotator_id)
    
    async def verify_identity(
        self,
        annotator_id: str,
        identity_doc: dict
    ) -> dict:
        """实名认证
        
        Args:
            annotator_id: 标注员ID
            identity_doc: 身份证件信息
            
        Returns:
            VerificationResult dict
        """
        annotator = self._annotators.get(annotator_id)
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} not found")
        
        result = await self.identity_verifier.verify(identity_doc)
        
        if result["success"]:
            annotator["identity_verified"] = True
            annotator["real_name"] = result["real_name"]
            annotator["status"] = AnnotatorStatus.PENDING_TEST.value
        
        return result
    
    async def submit_test_answer(
        self,
        annotator_id: str,
        task_id: str,
        answer: Dict[str, Any]
    ) -> dict:
        """提交测试答案"""
        key = f"{annotator_id}:{task_id}"
        submission = {
            "annotator_id": annotator_id,
            "task_id": task_id,
            "answer": answer,
            "submitted_at": datetime.utcnow()
        }
        self._test_submissions[key] = submission
        return submission
    
    async def get_test_submission(
        self,
        annotator_id: str,
        task_id: str
    ) -> Optional[dict]:
        """获取测试提交"""
        key = f"{annotator_id}:{task_id}"
        return self._test_submissions.get(key)
    
    async def conduct_ability_test(
        self,
        annotator_id: str,
        test_tasks: List[dict]
    ) -> dict:
        """能力测试
        
        Args:
            annotator_id: 标注员ID
            test_tasks: 测试任务列表 [{id, data, gold_answer}]
            
        Returns:
            AbilityTestResult dict
        """
        annotator = self._annotators.get(annotator_id)
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} not found")
        
        results = []
        details = []
        
        for task in test_tasks:
            submission = await self.get_test_submission(annotator_id, task["id"])
            
            if submission:
                score = self._evaluate_submission(
                    submission.get("answer", {}),
                    task["gold_answer"]
                )
            else:
                score = 0.0
            
            results.append(score)
            details.append({
                "task_id": task["id"],
                "score": score,
                "submitted": submission is not None
            })
        
        avg_score = sum(results) / len(results) if results else 0.0
        passed = avg_score >= 0.8
        
        if passed:
            annotator["status"] = AnnotatorStatus.ACTIVE.value
            annotator["star_rating"] = self._calculate_initial_star(avg_score)
        
        return {
            "annotator_id": annotator_id,
            "score": avg_score,
            "passed": passed,
            "details": details,
            "tested_at": datetime.utcnow()
        }
    
    def _evaluate_submission(
        self,
        answer: Dict[str, Any],
        gold_answer: Dict[str, Any]
    ) -> float:
        """评估提交答案"""
        if not answer:
            return 0.0
        
        # 简单比较：检查关键字段是否匹配
        matches = 0
        total = len(gold_answer)
        
        for key, value in gold_answer.items():
            if answer.get(key) == value:
                matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def _calculate_initial_star(self, score: float) -> int:
        """计算初始星级"""
        if score >= 0.95:
            return 4
        elif score >= 0.9:
            return 3
        elif score >= 0.85:
            return 2
        else:
            return 1
    
    async def update_star_rating(
        self,
        annotator_id: str,
        new_rating: int
    ) -> dict:
        """更新星级评定
        
        Args:
            annotator_id: 标注员ID
            new_rating: 新星级 (1-5)
            
        Returns:
            CrowdsourceAnnotator dict
        """
        annotator = self._annotators.get(annotator_id)
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} not found")
        
        if not 1 <= new_rating <= 5:
            raise ValueError("Star rating must be between 1 and 5")
        
        annotator["star_rating"] = new_rating
        return annotator
    
    async def add_ability_tags(
        self,
        annotator_id: str,
        tags: List[str]
    ) -> dict:
        """添加能力标签
        
        Args:
            annotator_id: 标注员ID
            tags: 能力标签列表
            
        Returns:
            CrowdsourceAnnotator dict
        """
        annotator = self._annotators.get(annotator_id)
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} not found")
        
        existing_tags = set(annotator.get("ability_tags", []))
        existing_tags.update(tags)
        annotator["ability_tags"] = list(existing_tags)
        
        return annotator
    
    async def remove_ability_tags(
        self,
        annotator_id: str,
        tags: List[str]
    ) -> dict:
        """移除能力标签"""
        annotator = self._annotators.get(annotator_id)
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} not found")
        
        existing_tags = set(annotator.get("ability_tags", []))
        existing_tags -= set(tags)
        annotator["ability_tags"] = list(existing_tags)
        
        return annotator
    
    async def set_status(
        self,
        annotator_id: str,
        status: AnnotatorStatus
    ) -> dict:
        """设置状态
        
        Args:
            annotator_id: 标注员ID
            status: 新状态
            
        Returns:
            CrowdsourceAnnotator dict
        """
        annotator = self._annotators.get(annotator_id)
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} not found")
        
        annotator["status"] = status.value
        return annotator
    
    async def conduct_periodic_review(
        self,
        annotator_id: str,
        recent_accuracy: float
    ) -> dict:
        """定期复评
        
        Args:
            annotator_id: 标注员ID
            recent_accuracy: 近期准确率
            
        Returns:
            ReviewResult dict
        """
        annotator = self._annotators.get(annotator_id)
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} not found")
        
        current_star = annotator.get("star_rating", 1)
        
        # 根据准确率调整星级
        if recent_accuracy >= 0.95:
            new_star = min(5, current_star + 1)
            action = "upgrade"
        elif recent_accuracy >= 0.8:
            new_star = current_star
            action = "maintain"
        elif recent_accuracy >= 0.7:
            new_star = max(1, current_star - 1)
            action = "downgrade"
        else:
            new_star = max(1, current_star - 2)
            action = "significant_downgrade"
            # 如果星级降到1且准确率很低，暂停账号
            if new_star == 1 and recent_accuracy < 0.6:
                annotator["status"] = AnnotatorStatus.SUSPENDED.value
                action = "suspended"
        
        annotator["star_rating"] = new_star
        
        return {
            "annotator_id": annotator_id,
            "previous_star": current_star,
            "new_star": new_star,
            "accuracy": recent_accuracy,
            "action": action,
            "reviewed_at": datetime.utcnow()
        }
    
    async def get_all_annotators(
        self,
        status: AnnotatorStatus = None
    ) -> List[dict]:
        """获取所有标注员"""
        annotators = list(self._annotators.values())
        if status:
            annotators = [a for a in annotators if a["status"] == status.value]
        return annotators
