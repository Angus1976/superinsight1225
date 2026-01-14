"""
Property Tests for Conflict Resolver (冲突解决器属性测试)

Tests Property 7: 冲突检测和解决

**Validates: Requirements 4.1, 4.2**
"""

import asyncio
import pytest
from collections import Counter
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import Any, Dict, List
from uuid import uuid4


# ============== Local Schema Definitions ==============

class ConflictResolver:
    """冲突解决器 - 本地测试版本"""
    
    def __init__(self):
        self._conflicts: Dict[str, dict] = {}
        self._votes: Dict[str, List[dict]] = {}
        self._resolutions: Dict[str, dict] = {}
    
    async def detect_conflicts(self, task_id: str, versions: List[dict]) -> List[dict]:
        """检测标注冲突"""
        conflicts = []
        
        for i, v1 in enumerate(versions):
            for v2 in versions[i+1:]:
                if self._has_conflict(v1.get("annotation", {}), v2.get("annotation", {})):
                    conflict = {
                        "id": str(uuid4()),
                        "task_id": task_id,
                        "version1_id": v1.get("id"),
                        "version2_id": v2.get("id"),
                        "conflict_type": self._get_conflict_type(v1, v2),
                        "status": "unresolved",
                        "created_at": datetime.utcnow()
                    }
                    self._conflicts[conflict["id"]] = conflict
                    conflicts.append(conflict)
        
        return conflicts
    
    def _has_conflict(self, annotation1: Dict[str, Any], annotation2: Dict[str, Any]) -> bool:
        """检查两个标注是否存在冲突"""
        return annotation1 != annotation2
    
    def _get_conflict_type(self, v1: dict, v2: dict) -> str:
        """获取冲突类型"""
        a1 = v1.get("annotation", {})
        a2 = v2.get("annotation", {})
        
        if a1.get("label") != a2.get("label"):
            return "label_mismatch"
        if a1.get("start") != a2.get("start") or a1.get("end") != a2.get("end"):
            return "boundary_mismatch"
        return "content_mismatch"
    
    async def vote(self, conflict_id: str, voter_id: str, choice: str) -> dict:
        """投票"""
        vote = {
            "conflict_id": conflict_id,
            "voter_id": voter_id,
            "choice": choice,
            "voted_at": datetime.utcnow()
        }
        
        if conflict_id not in self._votes:
            self._votes[conflict_id] = []
        
        # 检查是否已投票
        existing = [v for v in self._votes[conflict_id] if v["voter_id"] == voter_id]
        if existing:
            existing[0]["choice"] = choice
            existing[0]["voted_at"] = datetime.utcnow()
        else:
            self._votes[conflict_id].append(vote)
        
        if conflict_id in self._conflicts:
            self._conflicts[conflict_id]["status"] = "voting"
        
        return vote
    
    async def get_votes(self, conflict_id: str) -> List[dict]:
        return self._votes.get(conflict_id, [])
    
    async def resolve_by_voting(self, conflict_id: str, min_votes: int = 3) -> dict:
        """投票解决冲突"""
        votes = self._votes.get(conflict_id, [])
        
        if len(votes) < min_votes:
            raise ValueError(f"Not enough votes. Need at least {min_votes}, got {len(votes)}")
        
        vote_counts = Counter(v["choice"] for v in votes)
        winner = vote_counts.most_common(1)[0][0]
        
        resolution = {
            "id": str(uuid4()),
            "conflict_id": conflict_id,
            "method": "voting",
            "result": {"winner": winner},
            "vote_counts": dict(vote_counts),
            "expert_id": None,
            "resolved_at": datetime.utcnow()
        }
        
        self._resolutions[conflict_id] = resolution
        
        if conflict_id in self._conflicts:
            self._conflicts[conflict_id]["status"] = "resolved"
        
        return resolution
    
    async def resolve_by_expert(
        self,
        conflict_id: str,
        expert_id: str,
        decision: Dict[str, Any]
    ) -> dict:
        """专家仲裁解决冲突"""
        resolution = {
            "id": str(uuid4()),
            "conflict_id": conflict_id,
            "method": "expert",
            "result": decision,
            "vote_counts": None,
            "expert_id": expert_id,
            "resolved_at": datetime.utcnow()
        }
        
        self._resolutions[conflict_id] = resolution
        
        if conflict_id in self._conflicts:
            self._conflicts[conflict_id]["status"] = "resolved"
        
        return resolution
    
    async def get_conflict(self, conflict_id: str) -> dict:
        return self._conflicts.get(conflict_id)
    
    async def get_resolution(self, conflict_id: str) -> dict:
        return self._resolutions.get(conflict_id)


# ============== Test Strategies ==============

annotation_strategy = st.fixed_dictionaries({
    "label": st.sampled_from(["A", "B", "C", "D"]),
    "value": st.text(min_size=0, max_size=50)
})


def create_version(version_id: str, annotation: dict) -> dict:
    return {
        "id": version_id,
        "annotation": annotation
    }


# ============== Property 7: 冲突检测和解决 ==============

class TestConflictDetection:
    """
    Property 7: 冲突检测和解决
    
    *For any* 存在分歧的多人标注，系统应检测到冲突；投票解决时应采用多数决定。
    
    **Validates: Requirements 4.1, 4.2**
    """
    
    @given(
        annotation1=annotation_strategy,
        annotation2=annotation_strategy
    )
    @settings(max_examples=100)
    def test_different_annotations_detected_as_conflict(
        self,
        annotation1: dict,
        annotation2: dict
    ):
        """Property: 不同的标注应被检测为冲突"""
        resolver = ConflictResolver()
        
        v1 = create_version("v1", annotation1)
        v2 = create_version("v2", annotation2)
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        # 如果标注不同，应该检测到冲突
        if annotation1 != annotation2:
            assert len(conflicts) == 1
        else:
            assert len(conflicts) == 0
    
    def test_same_annotations_no_conflict(self):
        """相同的标注不应产生冲突"""
        resolver = ConflictResolver()
        
        annotation = {"label": "A", "value": "test"}
        v1 = create_version("v1", annotation)
        v2 = create_version("v2", annotation)
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        assert len(conflicts) == 0
    
    @given(
        num_versions=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100)
    def test_multiple_versions_pairwise_conflicts(self, num_versions: int):
        """Property: 多个不同版本应产生成对的冲突"""
        resolver = ConflictResolver()
        
        # 创建不同的版本
        versions = []
        for i in range(num_versions):
            v = create_version(f"v{i}", {"label": f"label_{i}", "value": f"value_{i}"})
            versions.append(v)
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", versions)
        )
        
        # 冲突数应该是 C(n,2) = n*(n-1)/2
        expected_conflicts = num_versions * (num_versions - 1) // 2
        assert len(conflicts) == expected_conflicts


class TestVotingResolution:
    """投票解决冲突测试"""
    
    @given(
        votes=st.lists(
            st.sampled_from(["version1", "version2"]),
            min_size=3,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_majority_wins(self, votes: List[str]):
        """Property: 投票解决应采用多数决定"""
        resolver = ConflictResolver()
        
        # 创建冲突
        v1 = create_version("v1", {"label": "A"})
        v2 = create_version("v2", {"label": "B"})
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        conflict_id = conflicts[0]["id"]
        
        # 投票
        for i, choice in enumerate(votes):
            asyncio.get_event_loop().run_until_complete(
                resolver.vote(conflict_id, f"voter_{i}", choice)
            )
        
        # 解决冲突
        resolution = asyncio.get_event_loop().run_until_complete(
            resolver.resolve_by_voting(conflict_id, min_votes=3)
        )
        
        # 验证：获胜者应该是得票最多的选项
        vote_counts = Counter(votes)
        expected_winner = vote_counts.most_common(1)[0][0]
        
        assert resolution["result"]["winner"] == expected_winner
    
    def test_not_enough_votes_raises_error(self):
        """投票数不足应抛出错误"""
        resolver = ConflictResolver()
        
        v1 = create_version("v1", {"label": "A"})
        v2 = create_version("v2", {"label": "B"})
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        conflict_id = conflicts[0]["id"]
        
        # 只投2票
        asyncio.get_event_loop().run_until_complete(
            resolver.vote(conflict_id, "voter_1", "version1")
        )
        asyncio.get_event_loop().run_until_complete(
            resolver.vote(conflict_id, "voter_2", "version2")
        )
        
        with pytest.raises(ValueError, match="Not enough votes"):
            asyncio.get_event_loop().run_until_complete(
                resolver.resolve_by_voting(conflict_id, min_votes=3)
            )
    
    def test_voter_can_change_vote(self):
        """投票者可以更改投票"""
        resolver = ConflictResolver()
        
        v1 = create_version("v1", {"label": "A"})
        v2 = create_version("v2", {"label": "B"})
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        conflict_id = conflicts[0]["id"]
        
        # 第一次投票
        asyncio.get_event_loop().run_until_complete(
            resolver.vote(conflict_id, "voter_1", "version1")
        )
        
        # 更改投票
        asyncio.get_event_loop().run_until_complete(
            resolver.vote(conflict_id, "voter_1", "version2")
        )
        
        votes = asyncio.get_event_loop().run_until_complete(
            resolver.get_votes(conflict_id)
        )
        
        # 应该只有一票，且是更改后的选择
        assert len(votes) == 1
        assert votes[0]["choice"] == "version2"


class TestExpertResolution:
    """专家仲裁解决冲突测试"""
    
    @given(
        expert_id=st.text(min_size=1, max_size=36),
        decision=st.fixed_dictionaries({
            "chosen_version": st.sampled_from(["v1", "v2"]),
            "reason": st.text(min_size=1, max_size=100)
        })
    )
    @settings(max_examples=100)
    def test_expert_resolution_recorded(self, expert_id: str, decision: dict):
        """Property: 专家仲裁应被正确记录"""
        resolver = ConflictResolver()
        
        v1 = create_version("v1", {"label": "A"})
        v2 = create_version("v2", {"label": "B"})
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        conflict_id = conflicts[0]["id"]
        
        resolution = asyncio.get_event_loop().run_until_complete(
            resolver.resolve_by_expert(conflict_id, expert_id, decision)
        )
        
        assert resolution["method"] == "expert"
        assert resolution["expert_id"] == expert_id
        assert resolution["result"] == decision
    
    def test_expert_resolution_updates_status(self):
        """专家仲裁后冲突状态应更新为已解决"""
        resolver = ConflictResolver()
        
        v1 = create_version("v1", {"label": "A"})
        v2 = create_version("v2", {"label": "B"})
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        conflict_id = conflicts[0]["id"]
        
        asyncio.get_event_loop().run_until_complete(
            resolver.resolve_by_expert(conflict_id, "expert_1", {"chosen": "v1"})
        )
        
        conflict = asyncio.get_event_loop().run_until_complete(
            resolver.get_conflict(conflict_id)
        )
        
        assert conflict["status"] == "resolved"


class TestConflictTypes:
    """冲突类型检测测试"""
    
    def test_label_mismatch_detected(self):
        """标签不匹配应被检测"""
        resolver = ConflictResolver()
        
        v1 = create_version("v1", {"label": "A", "value": "same"})
        v2 = create_version("v2", {"label": "B", "value": "same"})
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "label_mismatch"
    
    def test_boundary_mismatch_detected(self):
        """边界不匹配应被检测"""
        resolver = ConflictResolver()
        
        v1 = create_version("v1", {"label": "A", "start": 0, "end": 10})
        v2 = create_version("v2", {"label": "A", "start": 0, "end": 15})
        
        conflicts = asyncio.get_event_loop().run_until_complete(
            resolver.detect_conflicts("task_1", [v1, v2])
        )
        
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "boundary_mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
