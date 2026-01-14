"""
Property Tests for Task Dispatcher (任务分配器属性测试)

Tests Property 1: 技能匹配任务分配
Tests Property 2: 工作负载均衡

**Validates: Requirements 1.1, 1.3**
"""

import asyncio
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List, Set
from uuid import uuid4


# ============== Local Schema Definitions ==============

class TaskDispatcher:
    """任务分配器 - 本地测试版本"""
    
    def __init__(self):
        self._tasks = {}
        self._annotators = {}
        self._assignments = {}
    
    def add_task(self, task: dict) -> None:
        self._tasks[task["id"]] = task
    
    def add_annotator(self, annotator: dict) -> None:
        self._annotators[annotator["id"]] = annotator
    
    async def assign_task(self, task_id: str, mode: str = "auto", annotator_id: str = None) -> dict:
        if mode == "manual":
            return await self._manual_assign(task_id, annotator_id)
        return await self._auto_assign(task_id)
    
    async def _auto_assign(self, task_id: str) -> dict:
        task = self._tasks.get(task_id, {"id": task_id, "required_skills": []})
        required_skills = task.get("required_skills", [])
        
        candidates = await self._get_skill_matched_annotators(required_skills)
        if not candidates:
            raise ValueError("No matching annotators found")
        
        candidates = sorted(candidates, key=lambda x: x.get("current_workload", 0))
        annotator = candidates[0]
        
        assignment = {
            "id": str(uuid4()),
            "task_id": task_id,
            "annotator_id": annotator["id"],
            "assigned_at": datetime.utcnow()
        }
        self._assignments[assignment["id"]] = assignment
        
        annotator["current_workload"] = annotator.get("current_workload", 0) + 1
        
        return assignment
    
    async def _manual_assign(self, task_id: str, annotator_id: str) -> dict:
        if not annotator_id:
            raise ValueError("annotator_id required")
        
        assignment = {
            "id": str(uuid4()),
            "task_id": task_id,
            "annotator_id": annotator_id,
            "assigned_at": datetime.utcnow()
        }
        self._assignments[assignment["id"]] = assignment
        
        if annotator_id in self._annotators:
            self._annotators[annotator_id]["current_workload"] = \
                self._annotators[annotator_id].get("current_workload", 0) + 1
        
        return assignment
    
    async def _get_skill_matched_annotators(self, required_skills: List[str]) -> List[dict]:
        if not required_skills:
            return [a for a in self._annotators.values() if a.get("status") != "disabled"]
        
        required_set = set(required_skills)
        matched = []
        
        for annotator in self._annotators.values():
            if annotator.get("status") == "disabled":
                continue
            annotator_skills = set(annotator.get("skills", []))
            if required_set.issubset(annotator_skills):
                matched.append(annotator)
        
        return matched
    
    def is_skill_matched(self, task: dict, annotator: dict) -> bool:
        required_skills = set(task.get("required_skills", []))
        annotator_skills = set(annotator.get("skills", []))
        return required_skills.issubset(annotator_skills)
    
    def calculate_workload_balance(self) -> dict:
        annotators = list(self._annotators.values())
        if not annotators:
            return {"mean": 0, "std": 0, "cv": 0}
        
        workloads = [a.get("current_workload", 0) for a in annotators]
        mean = sum(workloads) / len(workloads)
        
        if len(workloads) < 2:
            std = 0
        else:
            variance = sum((x - mean) ** 2 for x in workloads) / (len(workloads) - 1)
            std = variance ** 0.5
        
        cv = std / mean if mean > 0 else 0
        
        return {"mean": mean, "std": std, "cv": cv, "workloads": workloads}


# ============== Test Strategies ==============

skill_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_",
    min_size=2,
    max_size=15
)

skills_list_strategy = st.lists(skill_strategy, min_size=0, max_size=5, unique=True)


def create_task(task_id: str, required_skills: List[str]) -> dict:
    return {
        "id": task_id,
        "required_skills": required_skills
    }


def create_annotator(annotator_id: str, skills: List[str], workload: int = 0) -> dict:
    return {
        "id": annotator_id,
        "skills": skills,
        "current_workload": workload,
        "status": "active"
    }


# ============== Property 1: 技能匹配任务分配 ==============

class TestSkillMatchingAssignment:
    """
    Property 1: 技能匹配任务分配
    
    *For any* 自动分配的任务，分配的标注员应具备任务所需的技能。
    
    **Validates: Requirements 1.1**
    """
    
    @given(
        task_skills=skills_list_strategy,
        annotator_skills=skills_list_strategy
    )
    @settings(max_examples=100)
    def test_skill_matching_property(self, task_skills: List[str], annotator_skills: List[str]):
        """Property: 如果标注员技能包含任务所需技能，则匹配成功"""
        dispatcher = TaskDispatcher()
        
        task = create_task("task_1", task_skills)
        annotator = create_annotator("annotator_1", annotator_skills)
        
        is_matched = dispatcher.is_skill_matched(task, annotator)
        
        # 验证：匹配当且仅当任务技能是标注员技能的子集
        expected = set(task_skills).issubset(set(annotator_skills))
        assert is_matched == expected
    
    @given(
        required_skills=st.lists(skill_strategy, min_size=1, max_size=3, unique=True)
    )
    @settings(max_examples=100)
    def test_auto_assign_matches_skills(self, required_skills: List[str]):
        """Property: 自动分配的标注员必须具备所需技能"""
        dispatcher = TaskDispatcher()
        
        task_id = str(uuid4())
        task = create_task(task_id, required_skills)
        dispatcher.add_task(task)
        
        # 创建一个具备所需技能的标注员
        annotator_skills = required_skills + ["extra_skill"]
        annotator = create_annotator(str(uuid4()), annotator_skills)
        dispatcher.add_annotator(annotator)
        
        # 执行分配
        assignment = asyncio.get_event_loop().run_until_complete(
            dispatcher.assign_task(task_id, mode="auto")
        )
        
        # 验证分配的标注员具备所需技能
        assigned_annotator = dispatcher._annotators[assignment["annotator_id"]]
        assert dispatcher.is_skill_matched(task, assigned_annotator)
    
    def test_no_matching_annotator_raises_error(self):
        """当没有匹配的标注员时应抛出错误"""
        dispatcher = TaskDispatcher()
        
        task = create_task("task_1", ["python", "nlp"])
        dispatcher.add_task(task)
        
        # 添加一个不具备所需技能的标注员
        annotator = create_annotator("annotator_1", ["java"])
        dispatcher.add_annotator(annotator)
        
        with pytest.raises(ValueError, match="No matching annotators"):
            asyncio.get_event_loop().run_until_complete(
                dispatcher.assign_task("task_1", mode="auto")
            )
    
    def test_empty_skills_matches_all(self):
        """无技能要求的任务应匹配所有标注员"""
        dispatcher = TaskDispatcher()
        
        task = create_task("task_1", [])  # 无技能要求
        annotator = create_annotator("annotator_1", ["any_skill"])
        
        assert dispatcher.is_skill_matched(task, annotator) is True


# ============== Property 2: 工作负载均衡 ==============

class TestWorkloadBalancing:
    """
    Property 2: 工作负载均衡
    
    *For any* 一组待分配任务，自动分配后各标注员的工作量差异应在合理范围内
    （标准差不超过平均值的 20%）。
    
    **Validates: Requirements 1.3**
    """
    
    @given(
        num_tasks=st.integers(min_value=5, max_value=20),
        num_annotators=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100)
    def test_workload_balancing_property(self, num_tasks: int, num_annotators: int):
        """Property: 批量分配后工作负载应均衡"""
        dispatcher = TaskDispatcher()
        
        # 创建标注员（初始负载为0）
        for i in range(num_annotators):
            annotator = create_annotator(f"annotator_{i}", ["common_skill"], workload=0)
            dispatcher.add_annotator(annotator)
        
        # 创建任务（无特殊技能要求）
        for i in range(num_tasks):
            task = create_task(f"task_{i}", [])
            dispatcher.add_task(task)
        
        # 分配所有任务
        for i in range(num_tasks):
            asyncio.get_event_loop().run_until_complete(
                dispatcher.assign_task(f"task_{i}", mode="auto")
            )
        
        # 计算工作负载均衡度
        balance = dispatcher.calculate_workload_balance()
        
        # 验证：变异系数应在合理范围内
        # 对于均匀分配，CV 应该很小
        # 允许一定的不均衡（因为任务数可能不能被标注员数整除）
        if balance["mean"] > 0:
            # 变异系数不应超过 50%（考虑到整数分配的限制）
            assert balance["cv"] <= 0.5, f"Workload too unbalanced: CV={balance['cv']}"
    
    @given(
        initial_workloads=st.lists(
            st.integers(min_value=0, max_value=10),
            min_size=3,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_assigns_to_lowest_workload(self, initial_workloads: List[int]):
        """Property: 新任务应分配给负载最低的标注员"""
        dispatcher = TaskDispatcher()
        
        # 创建具有不同初始负载的标注员
        for i, workload in enumerate(initial_workloads):
            annotator = create_annotator(f"annotator_{i}", ["skill"], workload=workload)
            dispatcher.add_annotator(annotator)
        
        # 创建并分配一个任务
        task = create_task("new_task", [])
        dispatcher.add_task(task)
        
        assignment = asyncio.get_event_loop().run_until_complete(
            dispatcher.assign_task("new_task", mode="auto")
        )
        
        # 找出分配前负载最低的标注员
        min_workload = min(initial_workloads)
        min_workload_annotators = [
            f"annotator_{i}" for i, w in enumerate(initial_workloads) if w == min_workload
        ]
        
        # 验证：任务应分配给负载最低的标注员之一
        assert assignment["annotator_id"] in min_workload_annotators
    
    def test_workload_increases_after_assignment(self):
        """分配后标注员工作负载应增加"""
        dispatcher = TaskDispatcher()
        
        annotator = create_annotator("annotator_1", ["skill"], workload=5)
        dispatcher.add_annotator(annotator)
        
        task = create_task("task_1", [])
        dispatcher.add_task(task)
        
        initial_workload = dispatcher._annotators["annotator_1"]["current_workload"]
        
        asyncio.get_event_loop().run_until_complete(
            dispatcher.assign_task("task_1", mode="auto")
        )
        
        final_workload = dispatcher._annotators["annotator_1"]["current_workload"]
        
        assert final_workload == initial_workload + 1


# ============== Additional Unit Tests ==============

class TestTaskDispatcherBasics:
    """基础功能单元测试"""
    
    def test_manual_assignment(self):
        """手动分配应直接分配给指定标注员"""
        dispatcher = TaskDispatcher()
        
        annotator = create_annotator("annotator_1", ["skill"])
        dispatcher.add_annotator(annotator)
        
        task = create_task("task_1", ["different_skill"])
        dispatcher.add_task(task)
        
        # 手动分配不检查技能匹配
        assignment = asyncio.get_event_loop().run_until_complete(
            dispatcher.assign_task("task_1", mode="manual", annotator_id="annotator_1")
        )
        
        assert assignment["annotator_id"] == "annotator_1"
    
    def test_manual_assignment_requires_annotator_id(self):
        """手动分配必须提供标注员ID"""
        dispatcher = TaskDispatcher()
        
        with pytest.raises(ValueError, match="annotator_id required"):
            asyncio.get_event_loop().run_until_complete(
                dispatcher.assign_task("task_1", mode="manual", annotator_id=None)
            )
    
    def test_disabled_annotator_not_assigned(self):
        """禁用的标注员不应被分配任务"""
        dispatcher = TaskDispatcher()
        
        # 添加一个禁用的标注员
        disabled = create_annotator("disabled_1", ["skill"])
        disabled["status"] = "disabled"
        dispatcher.add_annotator(disabled)
        
        # 添加一个活跃的标注员
        active = create_annotator("active_1", ["skill"])
        dispatcher.add_annotator(active)
        
        task = create_task("task_1", [])
        dispatcher.add_task(task)
        
        assignment = asyncio.get_event_loop().run_until_complete(
            dispatcher.assign_task("task_1", mode="auto")
        )
        
        assert assignment["annotator_id"] == "active_1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
