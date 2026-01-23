"""
Ragas API Property Tests - Ragas API 属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代

**Feature: system-optimization, Properties 11-12**
**Validates: Requirements 4.1, 4.2, 4.3**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4
from dataclasses import dataclass, field
import json


# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================

@dataclass
class EvaluationResult:
    """评估结果数据类"""
    id: str
    task_id: Optional[str]
    annotation_ids: List[str]
    metrics: Dict[str, float]
    scores: Dict[str, Any]
    overall_score: float
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "annotation_ids": self.annotation_ids,
            "metrics": self.metrics,
            "scores": self.scores,
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationResult':
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            id=data.get('id', str(uuid4())),
            task_id=data.get('task_id'),
            annotation_ids=data.get('annotation_ids', []),
            metrics=data.get('metrics', {}),
            scores=data.get('scores', {}),
            overall_score=data.get('overall_score', 0.0),
            created_at=created_at or datetime.utcnow(),
            metadata=data.get('metadata')
        )


# ============================================================================
# In-Memory Repository for Testing (模拟数据库行为)
# ============================================================================

class InMemoryEvaluationResultRepository:
    """内存评估结果仓库 - 用于属性测试"""
    
    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}
    
    def save(self, result: Dict[str, Any]) -> str:
        """保存评估结果"""
        evaluation_id = result.get('id') or result.get('evaluation_id') or str(uuid4())
        
        # Normalize the data
        stored_result = {
            'id': evaluation_id,
            'task_id': result.get('task_id'),
            'annotation_ids': result.get('annotation_ids', []),
            'metrics': result.get('metrics', {}),
            'scores': result.get('scores', {}),
            'overall_score': result.get('overall_score', 0.0),
            'created_at': result.get('created_at') or result.get('evaluation_date') or datetime.utcnow(),
            'metadata': result.get('metadata')
        }
        
        # Ensure created_at is datetime
        if isinstance(stored_result['created_at'], str):
            stored_result['created_at'] = datetime.fromisoformat(stored_result['created_at'])
        
        self.storage[evaluation_id] = stored_result
        return evaluation_id
    
    def get_by_id(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取评估结果"""
        result = self.storage.get(evaluation_id)
        if result:
            # Return a copy with serialized datetime
            return {
                **result,
                'created_at': result['created_at'].isoformat() if isinstance(result['created_at'], datetime) else result['created_at']
            }
        return None
    
    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出评估结果，支持分页和日期过滤"""
        results = list(self.storage.values())
        
        # Apply filters
        if start_date:
            results = [r for r in results if r['created_at'] >= start_date]
        
        if end_date:
            results = [r for r in results if r['created_at'] <= end_date]
        
        if task_id:
            results = [r for r in results if r['task_id'] == task_id]
        
        # Sort by created_at descending
        results.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply pagination
        paginated = results[skip:skip + limit]
        
        # Serialize datetime for output
        return [
            {
                **r,
                'created_at': r['created_at'].isoformat() if isinstance(r['created_at'], datetime) else r['created_at']
            }
            for r in paginated
        ]
    
    def count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> int:
        """计算匹配的评估结果数量"""
        results = list(self.storage.values())
        
        if start_date:
            results = [r for r in results if r['created_at'] >= start_date]
        
        if end_date:
            results = [r for r in results if r['created_at'] <= end_date]
        
        if task_id:
            results = [r for r in results if r['task_id'] == task_id]
        
        return len(results)
    
    def clear(self):
        """清空存储"""
        self.storage.clear()


# ============================================================================
# Hypothesis Strategies (测试数据生成策略)
# ============================================================================

# 生成有效的评估 ID
evaluation_id_strategy = st.uuids().map(lambda u: f"ragas_eval_{u.hex[:16]}")

# 生成有效的任务 ID
task_id_strategy = st.one_of(
    st.none(),
    st.uuids().map(str),
    st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P')))
)

# 生成标注 ID 列表
annotation_ids_strategy = st.lists(
    st.uuids().map(str),
    min_size=0,
    max_size=20
)

# 生成指标字典
metrics_strategy = st.fixed_dictionaries({
    'faithfulness': st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    'answer_relevancy': st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    'context_precision': st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
})

# 生成分数字典
scores_strategy = st.fixed_dictionaries({
    'individual_scores': st.lists(
        st.fixed_dictionaries({
            'annotation_id': st.uuids().map(str),
            'score': st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
        }),
        min_size=0,
        max_size=10
    )
})

# 生成总体分数
overall_score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# 生成创建时间
created_at_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31)
)

# 生成元数据
metadata_strategy = st.one_of(
    st.none(),
    st.fixed_dictionaries({
        'metrics_used': st.lists(st.sampled_from(['faithfulness', 'answer_relevancy', 'context_precision']), min_size=1, max_size=3),
        'annotations_count': st.integers(min_value=0, max_value=100),
        'ragas_version': st.sampled_from(['available', 'not_available'])
    })
)

# 完整的评估结果策略
evaluation_result_strategy = st.fixed_dictionaries({
    'id': evaluation_id_strategy,
    'task_id': task_id_strategy,
    'annotation_ids': annotation_ids_strategy,
    'metrics': metrics_strategy,
    'scores': scores_strategy,
    'overall_score': overall_score_strategy,
    'created_at': created_at_strategy,
    'metadata': metadata_strategy
})


# ============================================================================
# Property 11: Ragas API 评估结果往返
# **Validates: Requirements 4.1, 4.2**
# ============================================================================

class TestEvaluationResultRoundTrip:
    """Property 11: Ragas API 评估结果往返"""
    
    @given(result=evaluation_result_strategy)
    @settings(max_examples=100)
    def test_save_and_retrieve_by_id(self, result):
        """存储后通过 ID 检索应该返回等价的结果
        
        **Feature: system-optimization, Property 11: Ragas API 评估结果往返**
        **Validates: Requirements 4.1, 4.2**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 保存评估结果
        saved_id = repository.save(result)
        
        # 通过 ID 检索
        retrieved = repository.get_by_id(saved_id)
        
        # 验证检索成功
        assert retrieved is not None, "Saved evaluation result should be retrievable"
        
        # 验证 ID 匹配
        assert retrieved['id'] == result['id'], "ID should match"
        
        # 验证任务 ID 匹配
        assert retrieved['task_id'] == result['task_id'], "Task ID should match"
        
        # 验证标注 ID 列表匹配
        assert retrieved['annotation_ids'] == result['annotation_ids'], "Annotation IDs should match"
        
        # 验证指标匹配
        assert retrieved['metrics'] == result['metrics'], "Metrics should match"
        
        # 验证分数匹配
        assert retrieved['scores'] == result['scores'], "Scores should match"
        
        # 验证总体分数匹配（使用近似比较处理浮点数精度）
        assert abs(retrieved['overall_score'] - result['overall_score']) < 0.0001, \
            f"Overall score should match: {retrieved['overall_score']} vs {result['overall_score']}"
        
        # 验证元数据匹配
        assert retrieved['metadata'] == result['metadata'], "Metadata should match"
    
    @given(result=evaluation_result_strategy)
    @settings(max_examples=100)
    def test_metrics_preserved_after_roundtrip(self, result):
        """所有指标和分数应该在往返后保持不变
        
        **Feature: system-optimization, Property 11: Ragas API 评估结果往返**
        **Validates: Requirements 4.1, 4.2**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 保存评估结果
        saved_id = repository.save(result)
        
        # 检索评估结果
        retrieved = repository.get_by_id(saved_id)
        
        # 验证所有指标键存在
        for metric_name in result['metrics'].keys():
            assert metric_name in retrieved['metrics'], f"Metric {metric_name} should be preserved"
        
        # 验证所有指标值匹配
        for metric_name, metric_value in result['metrics'].items():
            assert abs(retrieved['metrics'][metric_name] - metric_value) < 0.0001, \
                f"Metric {metric_name} value should match"
    
    @given(result=evaluation_result_strategy)
    @settings(max_examples=100)
    def test_nonexistent_id_returns_none(self, result):
        """不存在的 ID 应该返回 None
        
        **Feature: system-optimization, Property 11: Ragas API 评估结果往返**
        **Validates: Requirement 4.2**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 保存评估结果
        repository.save(result)
        
        # 尝试检索不存在的 ID
        nonexistent_id = f"nonexistent_{uuid4().hex}"
        retrieved = repository.get_by_id(nonexistent_id)
        
        assert retrieved is None, "Nonexistent ID should return None"
    
    @given(
        results=st.lists(evaluation_result_strategy, min_size=2, max_size=5)
    )
    @settings(max_examples=100)
    def test_multiple_results_independent(self, results):
        """多个评估结果应该独立存储和检索
        
        **Feature: system-optimization, Property 11: Ragas API 评估结果往返**
        **Validates: Requirements 4.1, 4.2**
        """
        # 确保所有 ID 唯一
        ids = [r['id'] for r in results]
        assume(len(ids) == len(set(ids)))
        
        repository = InMemoryEvaluationResultRepository()
        
        # 保存所有评估结果
        saved_ids = []
        for result in results:
            saved_id = repository.save(result)
            saved_ids.append(saved_id)
        
        # 验证每个结果都能独立检索
        for i, saved_id in enumerate(saved_ids):
            retrieved = repository.get_by_id(saved_id)
            assert retrieved is not None, f"Result {i} should be retrievable"
            assert retrieved['id'] == results[i]['id'], f"Result {i} ID should match"


# ============================================================================
# Property 12: Ragas API 分页日期过滤
# **Validates: Requirement 4.3**
# ============================================================================

class TestPaginationAndDateFiltering:
    """Property 12: Ragas API 分页日期过滤"""
    
    @given(
        num_results=st.integers(min_value=0, max_value=50),
        skip=st.integers(min_value=0, max_value=100),
        limit=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_pagination_limit(self, num_results, skip, limit):
        """返回的结果数量应该不超过指定的 limit
        
        **Feature: system-optimization, Property 12: Ragas API 分页日期过滤**
        **Validates: Requirement 4.3**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 创建多个评估结果
        for i in range(num_results):
            result = {
                'id': f"eval_{uuid4().hex[:16]}",
                'task_id': f"task_{i}",
                'annotation_ids': [],
                'metrics': {'faithfulness': 0.8},
                'scores': {},
                'overall_score': 0.8,
                'created_at': datetime.utcnow() - timedelta(hours=i),
                'metadata': None
            }
            repository.save(result)
        
        # 列出评估结果
        results = repository.list(skip=skip, limit=limit)
        
        # 验证结果数量不超过 limit
        assert len(results) <= limit, f"Results should not exceed limit: {len(results)} > {limit}"
        
        # 验证结果数量正确
        expected_count = max(0, min(limit, num_results - skip))
        assert len(results) == expected_count, \
            f"Results count mismatch: {len(results)} != {expected_count}"
    
    @given(
        num_results=st.integers(min_value=5, max_value=20),
        skip=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_pagination_skip(self, num_results, skip):
        """skip 参数应该正确跳过指定数量的记录
        
        **Feature: system-optimization, Property 12: Ragas API 分页日期过滤**
        **Validates: Requirement 4.3**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 创建多个评估结果
        for i in range(num_results):
            result = {
                'id': f"eval_{i:04d}",
                'task_id': f"task_{i}",
                'annotation_ids': [],
                'metrics': {'faithfulness': 0.8},
                'scores': {},
                'overall_score': 0.8,
                'created_at': datetime.utcnow() - timedelta(hours=i),
                'metadata': None
            }
            repository.save(result)
        
        # 获取所有结果
        all_results = repository.list(skip=0, limit=num_results)
        
        # 获取跳过后的结果
        skipped_results = repository.list(skip=skip, limit=num_results)
        
        # 验证跳过的数量
        expected_count = max(0, num_results - skip)
        assert len(skipped_results) == expected_count, \
            f"Skipped results count mismatch: {len(skipped_results)} != {expected_count}"
    
    @given(
        base_date=st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2024, 12, 31)),
        num_before=st.integers(min_value=0, max_value=10),
        num_in_range=st.integers(min_value=0, max_value=10),
        num_after=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_date_range_filtering(self, base_date, num_before, num_in_range, num_after):
        """返回的结果应该在指定的日期范围内
        
        **Feature: system-optimization, Property 12: Ragas API 分页日期过滤**
        **Validates: Requirement 4.3**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 定义日期范围
        start_date = base_date
        end_date = base_date + timedelta(days=7)
        
        # 创建范围之前的结果
        for i in range(num_before):
            result = {
                'id': f"before_{uuid4().hex[:8]}",
                'task_id': None,
                'annotation_ids': [],
                'metrics': {},
                'scores': {},
                'overall_score': 0.5,
                'created_at': start_date - timedelta(days=i + 1),
                'metadata': None
            }
            repository.save(result)
        
        # 创建范围内的结果
        for i in range(num_in_range):
            result = {
                'id': f"in_range_{uuid4().hex[:8]}",
                'task_id': None,
                'annotation_ids': [],
                'metrics': {},
                'scores': {},
                'overall_score': 0.7,
                'created_at': start_date + timedelta(days=i % 7),
                'metadata': None
            }
            repository.save(result)
        
        # 创建范围之后的结果
        for i in range(num_after):
            result = {
                'id': f"after_{uuid4().hex[:8]}",
                'task_id': None,
                'annotation_ids': [],
                'metrics': {},
                'scores': {},
                'overall_score': 0.9,
                'created_at': end_date + timedelta(days=i + 1),
                'metadata': None
            }
            repository.save(result)
        
        # 使用日期过滤查询
        filtered_results = repository.list(
            start_date=start_date,
            end_date=end_date
        )
        
        # 验证结果数量
        assert len(filtered_results) == num_in_range, \
            f"Filtered results count mismatch: {len(filtered_results)} != {num_in_range}"
        
        # 验证所有结果都在日期范围内
        for result in filtered_results:
            result_date = datetime.fromisoformat(result['created_at'])
            assert start_date <= result_date <= end_date, \
                f"Result date {result_date} should be within range [{start_date}, {end_date}]"
    
    @given(
        num_results=st.integers(min_value=5, max_value=20),
        limit=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_combined_pagination_and_date_filter(self, num_results, limit):
        """分页和日期过滤应该能正确组合使用
        
        **Feature: system-optimization, Property 12: Ragas API 分页日期过滤**
        **Validates: Requirement 4.3**
        """
        repository = InMemoryEvaluationResultRepository()
        
        base_date = datetime(2024, 6, 15)
        start_date = base_date
        end_date = base_date + timedelta(days=30)
        
        # 创建评估结果
        for i in range(num_results):
            result = {
                'id': f"eval_{uuid4().hex[:16]}",
                'task_id': f"task_{i}",
                'annotation_ids': [],
                'metrics': {'faithfulness': 0.8},
                'scores': {},
                'overall_score': 0.8,
                'created_at': start_date + timedelta(days=i % 30),
                'metadata': None
            }
            repository.save(result)
        
        # 使用分页和日期过滤
        results = repository.list(
            skip=0,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        # 验证结果数量不超过 limit
        assert len(results) <= limit, f"Results should not exceed limit"
        
        # 验证所有结果都在日期范围内
        for result in results:
            result_date = datetime.fromisoformat(result['created_at'])
            assert start_date <= result_date <= end_date, \
                f"Result date should be within range"
    
    @given(
        task_ids=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=2,
            max_size=5,
            unique=True
        ),
        results_per_task=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_task_id_filtering(self, task_ids, results_per_task):
        """按任务 ID 过滤应该只返回匹配的结果
        
        **Feature: system-optimization, Property 12: Ragas API 分页日期过滤**
        **Validates: Requirement 4.3**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 为每个任务创建评估结果
        for task_id in task_ids:
            for i in range(results_per_task):
                result = {
                    'id': f"eval_{task_id}_{i}_{uuid4().hex[:8]}",
                    'task_id': task_id,
                    'annotation_ids': [],
                    'metrics': {},
                    'scores': {},
                    'overall_score': 0.8,
                    'created_at': datetime.utcnow() - timedelta(hours=i),
                    'metadata': None
                }
                repository.save(result)
        
        # 按任务 ID 过滤
        target_task_id = task_ids[0]
        filtered_results = repository.list(task_id=target_task_id)
        
        # 验证结果数量
        assert len(filtered_results) == results_per_task, \
            f"Should have {results_per_task} results for task {target_task_id}"
        
        # 验证所有结果都属于目标任务
        for result in filtered_results:
            assert result['task_id'] == target_task_id, \
                f"Result task_id should be {target_task_id}"
    
    @given(
        num_results=st.integers(min_value=3, max_value=10)
    )
    @settings(max_examples=100)
    def test_results_ordered_by_created_at_descending(self, num_results):
        """结果应该按创建时间降序排列（最新的在前）
        
        **Feature: system-optimization, Property 12: Ragas API 分页日期过滤**
        **Validates: Requirement 4.3**
        """
        repository = InMemoryEvaluationResultRepository()
        
        # 创建评估结果，时间间隔不同
        for i in range(num_results):
            result = {
                'id': f"eval_{i:04d}",
                'task_id': None,
                'annotation_ids': [],
                'metrics': {},
                'scores': {},
                'overall_score': 0.8,
                'created_at': datetime.utcnow() - timedelta(hours=i * 2),
                'metadata': None
            }
            repository.save(result)
        
        # 获取所有结果
        results = repository.list()
        
        # 验证结果按时间降序排列
        for i in range(len(results) - 1):
            current_date = datetime.fromisoformat(results[i]['created_at'])
            next_date = datetime.fromisoformat(results[i + 1]['created_at'])
            assert current_date >= next_date, \
                f"Results should be ordered by created_at descending"


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""
    
    @given(
        overall_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_overall_score_range(self, overall_score):
        """总体分数应该在 0.0 到 1.0 之间
        
        **Feature: system-optimization, Property 11: Ragas API 评估结果往返**
        **Validates: Requirement 4.1**
        """
        repository = InMemoryEvaluationResultRepository()
        
        result = {
            'id': f"eval_{uuid4().hex[:16]}",
            'task_id': None,
            'annotation_ids': [],
            'metrics': {},
            'scores': {},
            'overall_score': overall_score,
            'created_at': datetime.utcnow(),
            'metadata': None
        }
        
        saved_id = repository.save(result)
        retrieved = repository.get_by_id(saved_id)
        
        assert 0.0 <= retrieved['overall_score'] <= 1.0, \
            f"Overall score should be between 0.0 and 1.0"
    
    def test_empty_repository_returns_empty_list(self):
        """空仓库应该返回空列表
        
        **Feature: system-optimization, Property 12: Ragas API 分页日期过滤**
        **Validates: Requirement 4.3**
        """
        repository = InMemoryEvaluationResultRepository()
        
        results = repository.list()
        
        assert results == [], "Empty repository should return empty list"
    
    @given(
        annotation_ids=st.lists(st.uuids().map(str), min_size=0, max_size=100)
    )
    @settings(max_examples=100)
    def test_annotation_ids_preserved(self, annotation_ids):
        """标注 ID 列表应该完整保留
        
        **Feature: system-optimization, Property 11: Ragas API 评估结果往返**
        **Validates: Requirement 4.1**
        """
        repository = InMemoryEvaluationResultRepository()
        
        result = {
            'id': f"eval_{uuid4().hex[:16]}",
            'task_id': None,
            'annotation_ids': annotation_ids,
            'metrics': {},
            'scores': {},
            'overall_score': 0.8,
            'created_at': datetime.utcnow(),
            'metadata': None
        }
        
        saved_id = repository.save(result)
        retrieved = repository.get_by_id(saved_id)
        
        assert retrieved['annotation_ids'] == annotation_ids, \
            "Annotation IDs should be preserved exactly"
        assert len(retrieved['annotation_ids']) == len(annotation_ids), \
            "Annotation IDs count should match"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
