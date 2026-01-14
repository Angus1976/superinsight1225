"""
Property Tests for Collaboration Engine (协作引擎属性测试)

Tests Property 3: 任务重复标注防止
Tests Property 4: 标注版本保留

**Validates: Requirements 2.3, 2.4**
"""

import asyncio
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import Any, Dict, List
from uuid import uuid4


# ============== Local Schema Definitions ==============

class CollaborationEngine:
    """协作引擎 - 本地测试版本"""
    
    def __init__(self):
        self._locks: Dict[str, str] = {}  # task_id -> annotator_id
        self._versions: Dict[str, List[dict]] = {}  # task_id -> versions
    
    async def acquire_task_lock(self, task_id: str, annotator_id: str) -> bool:
        """获取任务锁"""
        if task_id in self._locks:
            return False
        self._locks[task_id] = annotator_id
        return True
    
    async def release_task_lock(self, task_id: str, annotator_id: str) -> bool:
        """释放任务锁"""
        if self._locks.get(task_id) == annotator_id:
            del self._locks[task_id]
            return True
        return False
    
    async def get_lock_holder(self, task_id: str) -> str:
        """获取锁持有者"""
        return self._locks.get(task_id)
    
    async def save_annotation_version(
        self,
        task_id: str,
        annotator_id: str,
        annotation: Dict[str, Any]
    ) -> dict:
        """保存标注版本"""
        version_num = await self._get_next_version(task_id)
        
        version = {
            "id": str(uuid4()),
            "task_id": task_id,
            "annotator_id": annotator_id,
            "annotation": annotation,
            "version": version_num,
            "created_at": datetime.utcnow()
        }
        
        if task_id not in self._versions:
            self._versions[task_id] = []
        self._versions[task_id].append(version)
        
        return version
    
    async def _get_next_version(self, task_id: str) -> int:
        """获取下一个版本号"""
        versions = self._versions.get(task_id, [])
        if not versions:
            return 1
        return max(v["version"] for v in versions) + 1
    
    async def get_annotation_versions(self, task_id: str) -> List[dict]:
        """获取所有标注版本"""
        return self._versions.get(task_id, [])


# ============== Test Strategies ==============

annotation_strategy = st.fixed_dictionaries({
    "label": st.text(min_size=1, max_size=20),
    "value": st.text(min_size=0, max_size=100),
    "confidence": st.floats(min_value=0, max_value=1)
})


# ============== Property 3: 任务重复标注防止 ==============

class TestTaskLockPrevention:
    """
    Property 3: 任务重复标注防止
    
    *For any* 已被锁定的任务，其他标注员不应能够获取该任务的锁。
    
    **Validates: Requirements 2.3**
    """
    
    @given(
        task_id=st.text(min_size=1, max_size=36),
        annotator1_id=st.text(min_size=1, max_size=36),
        annotator2_id=st.text(min_size=1, max_size=36)
    )
    @settings(max_examples=100)
    def test_lock_prevents_duplicate_annotation(
        self,
        task_id: str,
        annotator1_id: str,
        annotator2_id: str
    ):
        """Property: 已锁定的任务不能被其他人再次锁定"""
        # 跳过相同标注员的情况
        if annotator1_id == annotator2_id:
            return
        
        engine = CollaborationEngine()
        
        # 第一个标注员获取锁
        lock1 = asyncio.get_event_loop().run_until_complete(
            engine.acquire_task_lock(task_id, annotator1_id)
        )
        
        # 第二个标注员尝试获取锁
        lock2 = asyncio.get_event_loop().run_until_complete(
            engine.acquire_task_lock(task_id, annotator2_id)
        )
        
        # 验证：第一个成功，第二个失败
        assert lock1 is True
        assert lock2 is False
    
    @given(
        task_id=st.text(min_size=1, max_size=36),
        annotator_id=st.text(min_size=1, max_size=36)
    )
    @settings(max_examples=100)
    def test_same_annotator_cannot_lock_twice(self, task_id: str, annotator_id: str):
        """Property: 同一标注员不能重复锁定同一任务"""
        engine = CollaborationEngine()
        
        # 第一次获取锁
        lock1 = asyncio.get_event_loop().run_until_complete(
            engine.acquire_task_lock(task_id, annotator_id)
        )
        
        # 第二次尝试获取锁
        lock2 = asyncio.get_event_loop().run_until_complete(
            engine.acquire_task_lock(task_id, annotator_id)
        )
        
        assert lock1 is True
        assert lock2 is False
    
    @given(
        task_id=st.text(min_size=1, max_size=36),
        annotator1_id=st.text(min_size=1, max_size=36),
        annotator2_id=st.text(min_size=1, max_size=36)
    )
    @settings(max_examples=100)
    def test_lock_release_allows_new_lock(
        self,
        task_id: str,
        annotator1_id: str,
        annotator2_id: str
    ):
        """Property: 释放锁后其他人可以获取锁"""
        if annotator1_id == annotator2_id:
            return
        
        engine = CollaborationEngine()
        
        # 第一个标注员获取并释放锁
        asyncio.get_event_loop().run_until_complete(
            engine.acquire_task_lock(task_id, annotator1_id)
        )
        asyncio.get_event_loop().run_until_complete(
            engine.release_task_lock(task_id, annotator1_id)
        )
        
        # 第二个标注员应该能获取锁
        lock2 = asyncio.get_event_loop().run_until_complete(
            engine.acquire_task_lock(task_id, annotator2_id)
        )
        
        assert lock2 is True
    
    def test_only_lock_holder_can_release(self):
        """只有锁持有者才能释放锁"""
        engine = CollaborationEngine()
        
        # annotator1 获取锁
        asyncio.get_event_loop().run_until_complete(
            engine.acquire_task_lock("task_1", "annotator_1")
        )
        
        # annotator2 尝试释放锁
        released = asyncio.get_event_loop().run_until_complete(
            engine.release_task_lock("task_1", "annotator_2")
        )
        
        assert released is False
        
        # 锁仍然被 annotator1 持有
        holder = asyncio.get_event_loop().run_until_complete(
            engine.get_lock_holder("task_1")
        )
        assert holder == "annotator_1"


# ============== Property 4: 标注版本保留 ==============

class TestAnnotationVersionRetention:
    """
    Property 4: 标注版本保留
    
    *For any* 多人标注的任务，所有标注版本应被完整保留，可追溯查询。
    
    **Validates: Requirements 2.4**
    """
    
    @given(
        task_id=st.text(min_size=1, max_size=36),
        annotations=st.lists(annotation_strategy, min_size=1, max_size=10)
    )
    @settings(max_examples=100)
    def test_all_versions_preserved(self, task_id: str, annotations: List[dict]):
        """Property: 所有保存的标注版本都应被保留"""
        engine = CollaborationEngine()
        
        saved_versions = []
        for i, annotation in enumerate(annotations):
            version = asyncio.get_event_loop().run_until_complete(
                engine.save_annotation_version(task_id, f"annotator_{i}", annotation)
            )
            saved_versions.append(version)
        
        # 获取所有版本
        retrieved_versions = asyncio.get_event_loop().run_until_complete(
            engine.get_annotation_versions(task_id)
        )
        
        # 验证：保存的版本数等于检索到的版本数
        assert len(retrieved_versions) == len(annotations)
        
        # 验证：所有版本ID都存在
        saved_ids = {v["id"] for v in saved_versions}
        retrieved_ids = {v["id"] for v in retrieved_versions}
        assert saved_ids == retrieved_ids
    
    @given(
        task_id=st.text(min_size=1, max_size=36),
        num_versions=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_version_numbers_sequential(self, task_id: str, num_versions: int):
        """Property: 版本号应该是连续递增的"""
        engine = CollaborationEngine()
        
        for i in range(num_versions):
            asyncio.get_event_loop().run_until_complete(
                engine.save_annotation_version(
                    task_id,
                    f"annotator_{i}",
                    {"label": f"label_{i}"}
                )
            )
        
        versions = asyncio.get_event_loop().run_until_complete(
            engine.get_annotation_versions(task_id)
        )
        
        # 验证版本号从1开始连续递增
        version_numbers = sorted(v["version"] for v in versions)
        expected = list(range(1, num_versions + 1))
        assert version_numbers == expected
    
    @given(
        annotation=annotation_strategy
    )
    @settings(max_examples=100)
    def test_annotation_content_preserved(self, annotation: dict):
        """Property: 标注内容应被完整保留"""
        engine = CollaborationEngine()
        task_id = str(uuid4())
        
        # 保存标注
        saved = asyncio.get_event_loop().run_until_complete(
            engine.save_annotation_version(task_id, "annotator_1", annotation)
        )
        
        # 检索标注
        versions = asyncio.get_event_loop().run_until_complete(
            engine.get_annotation_versions(task_id)
        )
        
        # 验证内容完整
        assert len(versions) == 1
        assert versions[0]["annotation"] == annotation
    
    def test_versions_isolated_by_task(self):
        """不同任务的版本应该隔离"""
        engine = CollaborationEngine()
        
        # 为两个不同任务保存版本
        asyncio.get_event_loop().run_until_complete(
            engine.save_annotation_version("task_1", "annotator_1", {"label": "A"})
        )
        asyncio.get_event_loop().run_until_complete(
            engine.save_annotation_version("task_2", "annotator_1", {"label": "B"})
        )
        
        # 检索各自的版本
        versions_1 = asyncio.get_event_loop().run_until_complete(
            engine.get_annotation_versions("task_1")
        )
        versions_2 = asyncio.get_event_loop().run_until_complete(
            engine.get_annotation_versions("task_2")
        )
        
        assert len(versions_1) == 1
        assert len(versions_2) == 1
        assert versions_1[0]["annotation"]["label"] == "A"
        assert versions_2[0]["annotation"]["label"] == "B"
    
    def test_multiple_annotators_same_task(self):
        """多个标注员对同一任务的标注都应保留"""
        engine = CollaborationEngine()
        task_id = "shared_task"
        
        # 三个标注员分别标注
        for i in range(3):
            asyncio.get_event_loop().run_until_complete(
                engine.save_annotation_version(
                    task_id,
                    f"annotator_{i}",
                    {"label": f"label_{i}"}
                )
            )
        
        versions = asyncio.get_event_loop().run_until_complete(
            engine.get_annotation_versions(task_id)
        )
        
        # 验证所有版本都保留
        assert len(versions) == 3
        
        # 验证每个标注员的版本都存在
        annotator_ids = {v["annotator_id"] for v in versions}
        assert annotator_ids == {"annotator_0", "annotator_1", "annotator_2"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
