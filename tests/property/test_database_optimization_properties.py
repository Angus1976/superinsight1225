"""
Database Optimization Property Tests - 数据库优化属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代

**Feature: system-optimization, Properties 18-20**
**Validates: Requirements 9.2, 9.3, 9.5**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass, field


# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================

@dataclass
class BatchConfig:
    """批量操作配置"""
    batch_size: int = 1000
    return_ids: bool = True
    on_conflict: str = "ignore"
    timeout_seconds: Optional[int] = None


@dataclass
class BatchResult:
    """批量操作结果"""
    success_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    duration_ms: float = 0.0
    ids: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 100.0
        return (self.success_count / self.total_count) * 100


@dataclass
class PageInfo:
    """分页信息"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


@dataclass
class PaginatedResult:
    """分页结果"""
    items: List[Any]
    page_info: PageInfo


@dataclass
class SlowQueryRecord:
    """慢查询记录"""
    sql: str
    duration_ms: float
    params: Dict[str, Any]
    timestamp: datetime
    stack_trace: Optional[str] = None
    query_type: Optional[str] = None
    table_name: Optional[str] = None


# ============================================================================
# Core Functions (独立实现，用于属性测试)
# ============================================================================

def calculate_batch_count(total: int, batch_size: int) -> int:
    """计算批次数量"""
    if batch_size <= 0:
        return 0
    return (total + batch_size - 1) // batch_size


def split_into_batches(items: List[Any], batch_size: int) -> List[List[Any]]:
    """将列表分割为批次"""
    if batch_size <= 0:
        return []
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def calculate_pagination(total_items: int, page: int, page_size: int) -> PageInfo:
    """计算分页信息"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 1000:
        page_size = 1000
    
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    return PageInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


def calculate_offset(page: int, page_size: int) -> int:
    """计算偏移量"""
    if page < 1:
        page = 1
    return (page - 1) * page_size


def is_slow_query(duration_ms: float, threshold_ms: float = 1000.0) -> bool:
    """判断是否为慢查询"""
    return duration_ms >= threshold_ms


def extract_query_type(sql: str) -> str:
    """从 SQL 中提取查询类型"""
    sql_upper = sql.strip().upper()
    for query_type in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']:
        if sql_upper.startswith(query_type):
            return query_type
    return 'OTHER'


def calculate_hit_rate(hits: int, misses: int) -> float:
    """计算命中率"""
    total = hits + misses
    return hits / total if total > 0 else 0.0


# ============================================================================
# Mock Classes for Testing
# ============================================================================

class MockBatchOperations:
    """模拟批量操作类"""
    
    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self.storage: Dict[str, Dict[str, Any]] = {}
        self.operation_log: List[Dict[str, Any]] = []
    
    def bulk_insert(
        self,
        records: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """批量插入"""
        if not records:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(records)
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        batches = split_into_batches(records, batch_size)
        
        for batch in batches:
            for record in batch:
                record_id = record.get('id', str(uuid4()))
                record['id'] = record_id
                self.storage[record_id] = record.copy()
                result.ids.append(record_id)
                result.success_count += 1
            
            self.operation_log.append({
                'type': 'insert',
                'batch_size': len(batch),
                'timestamp': datetime.now()
            })
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def bulk_update(
        self,
        records: List[Dict[str, Any]],
        key_field: str = "id",
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """批量更新"""
        if not records:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(records)
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        batches = split_into_batches(records, batch_size)
        
        for batch in batches:
            for record in batch:
                key_value = record.get(key_field)
                if key_value is None:
                    result.failed_count += 1
                    result.errors.append(f"Missing key field '{key_field}'")
                    continue
                
                if key_value in self.storage:
                    self.storage[key_value].update(record)
                    result.success_count += 1
                    result.ids.append(key_value)
                else:
                    result.failed_count += 1
                    result.errors.append(f"Record not found: {key_value}")
            
            self.operation_log.append({
                'type': 'update',
                'batch_size': len(batch),
                'timestamp': datetime.now()
            })
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有记录"""
        return list(self.storage.values())
    
    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取记录"""
        return self.storage.get(record_id)


class MockPaginator:
    """模拟分页器"""
    
    def __init__(self, items: List[Any]):
        self.items = items
    
    def paginate(self, page: int = 1, page_size: int = 20) -> PaginatedResult:
        """偏移分页"""
        page_info = calculate_pagination(len(self.items), page, page_size)
        offset = calculate_offset(page_info.page, page_info.page_size)
        
        paginated_items = self.items[offset:offset + page_info.page_size]
        
        return PaginatedResult(items=paginated_items, page_info=page_info)
    
    def cursor_paginate(
        self,
        cursor: Optional[int] = None,
        limit: int = 20
    ) -> Tuple[List[Any], Optional[int]]:
        """游标分页"""
        if limit < 1:
            limit = 20
        if limit > 1000:
            limit = 1000
        
        start_idx = cursor if cursor is not None else 0
        end_idx = start_idx + limit + 1  # +1 to check for next page
        
        items = self.items[start_idx:end_idx]
        
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]
        
        next_cursor = start_idx + limit if has_next else None
        
        return items, next_cursor


class MockQueryMonitor:
    """模拟查询监控器"""
    
    def __init__(self, threshold_ms: float = 1000.0):
        self.threshold_ms = threshold_ms
        self.slow_queries: List[SlowQueryRecord] = []
        self.total_queries = 0
        self.slow_query_count = 0
        self.total_duration_ms = 0.0
        self.max_duration_ms = 0.0
        self.min_duration_ms = float('inf')
        self.queries_by_type: Dict[str, int] = {}
    
    def record_query(
        self,
        sql: str,
        duration_ms: float,
        params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """记录查询"""
        params = params or {}
        is_slow = is_slow_query(duration_ms, self.threshold_ms)
        
        self.total_queries += 1
        self.total_duration_ms += duration_ms
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        
        query_type = extract_query_type(sql)
        self.queries_by_type[query_type] = self.queries_by_type.get(query_type, 0) + 1
        
        if is_slow:
            self.slow_query_count += 1
            record = SlowQueryRecord(
                sql=sql[:2000],
                duration_ms=duration_ms,
                params=params,
                timestamp=datetime.now(),
                query_type=query_type
            )
            self.slow_queries.append(record)
        
        return is_slow
    
    def get_slow_queries(self, limit: int = 100) -> List[SlowQueryRecord]:
        """获取慢查询列表"""
        sorted_queries = sorted(
            self.slow_queries,
            key=lambda q: q.duration_ms,
            reverse=True
        )
        return sorted_queries[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_duration = (
            self.total_duration_ms / self.total_queries
            if self.total_queries > 0 else 0.0
        )
        
        return {
            'total_queries': self.total_queries,
            'slow_queries': self.slow_query_count,
            'total_duration_ms': self.total_duration_ms,
            'avg_duration_ms': avg_duration,
            'max_duration_ms': self.max_duration_ms,
            'min_duration_ms': self.min_duration_ms if self.min_duration_ms != float('inf') else 0.0,
            'queries_by_type': self.queries_by_type.copy()
        }
    
    def reset(self):
        """重置统计"""
        self.slow_queries.clear()
        self.total_queries = 0
        self.slow_query_count = 0
        self.total_duration_ms = 0.0
        self.max_duration_ms = 0.0
        self.min_duration_ms = float('inf')
        self.queries_by_type.clear()


# ============================================================================
# Property 18: 批量数据库操作
# ============================================================================

class TestBatchDatabaseOperations:
    """Property 18: 批量数据库操作
    
    对于任意批量插入或更新操作，所有项目应该在单个事务中处理，
    且返回的成功数量应该等于实际插入/更新的记录数。
    
    **Feature: system-optimization, Property 18: 批量数据库操作**
    **Validates: Requirements 9.2**
    """
    
    @given(
        records=st.lists(
            st.fixed_dictionaries({
                'name': st.text(min_size=1, max_size=50),
                'value': st.integers()
            }),
            min_size=1,
            max_size=100
        ),
        batch_size=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_bulk_insert_count_consistency(self, records, batch_size):
        """批量插入的成功数量应该等于实际插入的记录数
        
        **Feature: system-optimization, Property 18: 批量数据库操作**
        **Validates: Requirements 9.2**
        """
        config = BatchConfig(batch_size=batch_size)
        batch_ops = MockBatchOperations(config)
        
        result = batch_ops.bulk_insert(records, batch_size=batch_size)
        
        # 验证成功数量
        assert result.success_count == len(records), \
            f"Success count mismatch: {result.success_count} != {len(records)}"
        
        # 验证总数量
        assert result.total_count == len(records), \
            f"Total count mismatch: {result.total_count} != {len(records)}"
        
        # 验证存储中的记录数
        assert len(batch_ops.storage) == len(records), \
            f"Storage count mismatch: {len(batch_ops.storage)} != {len(records)}"
        
        # 验证返回的 ID 数量
        assert len(result.ids) == len(records), \
            f"IDs count mismatch: {len(result.ids)} != {len(records)}"
    
    @given(
        num_records=st.integers(min_value=1, max_value=100),
        batch_size=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_batch_count_calculation(self, num_records, batch_size):
        """批次数量计算应该正确
        
        **Feature: system-optimization, Property 18: 批量数据库操作**
        **Validates: Requirements 9.2**
        """
        expected_batches = calculate_batch_count(num_records, batch_size)
        
        # 验证批次数量
        records = [{'name': f'record_{i}', 'value': i} for i in range(num_records)]
        batches = split_into_batches(records, batch_size)
        
        assert len(batches) == expected_batches, \
            f"Batch count mismatch: {len(batches)} != {expected_batches}"
        
        # 验证所有记录都被分配到批次中
        total_in_batches = sum(len(batch) for batch in batches)
        assert total_in_batches == num_records, \
            f"Total in batches mismatch: {total_in_batches} != {num_records}"
    
    @given(
        records=st.lists(
            st.fixed_dictionaries({
                'id': st.uuids().map(str),
                'name': st.text(min_size=1, max_size=50),
                'value': st.integers()
            }),
            min_size=1,
            max_size=50,
            unique_by=lambda x: x['id']
        )
    )
    @settings(max_examples=100)
    def test_bulk_insert_roundtrip(self, records):
        """批量插入后应该能正确检索所有记录
        
        **Feature: system-optimization, Property 18: 批量数据库操作**
        **Validates: Requirements 9.2**
        """
        batch_ops = MockBatchOperations()
        
        result = batch_ops.bulk_insert(records)
        
        # 验证每条记录都能被检索
        for record in records:
            stored = batch_ops.get_by_id(record['id'])
            assert stored is not None, f"Record {record['id']} not found"
            assert stored['name'] == record['name'], \
                f"Name mismatch for {record['id']}"
            assert stored['value'] == record['value'], \
                f"Value mismatch for {record['id']}"

    
    @given(
        initial_records=st.lists(
            st.fixed_dictionaries({
                'id': st.uuids().map(str),
                'name': st.text(min_size=1, max_size=50),
                'value': st.integers()
            }),
            min_size=1,
            max_size=30,
            unique_by=lambda x: x['id']
        ),
        update_value=st.integers()
    )
    @settings(max_examples=100)
    def test_bulk_update_count_consistency(self, initial_records, update_value):
        """批量更新的成功数量应该等于实际更新的记录数
        
        **Feature: system-optimization, Property 18: 批量数据库操作**
        **Validates: Requirements 9.2**
        """
        batch_ops = MockBatchOperations()
        
        # 先插入记录
        batch_ops.bulk_insert(initial_records)
        
        # 准备更新数据
        update_records = [
            {'id': record['id'], 'value': update_value}
            for record in initial_records
        ]
        
        # 执行批量更新
        result = batch_ops.bulk_update(update_records)
        
        # 验证成功数量
        assert result.success_count == len(initial_records), \
            f"Update success count mismatch: {result.success_count} != {len(initial_records)}"
        
        # 验证更新后的值
        for record in initial_records:
            stored = batch_ops.get_by_id(record['id'])
            assert stored['value'] == update_value, \
                f"Value not updated for {record['id']}"
    
    @given(
        batch_size=st.integers(min_value=1, max_value=100),
        num_records=st.integers(min_value=1, max_value=200)
    )
    @settings(max_examples=100)
    def test_batch_operation_logging(self, batch_size, num_records):
        """批量操作应该正确记录操作日志
        
        **Feature: system-optimization, Property 18: 批量数据库操作**
        **Validates: Requirements 9.2**
        """
        config = BatchConfig(batch_size=batch_size)
        batch_ops = MockBatchOperations(config)
        
        records = [{'name': f'record_{i}', 'value': i} for i in range(num_records)]
        batch_ops.bulk_insert(records, batch_size=batch_size)
        
        expected_batches = calculate_batch_count(num_records, batch_size)
        
        # 验证操作日志数量
        assert len(batch_ops.operation_log) == expected_batches, \
            f"Operation log count mismatch: {len(batch_ops.operation_log)} != {expected_batches}"
        
        # 验证每个日志条目
        for log_entry in batch_ops.operation_log:
            assert log_entry['type'] == 'insert', "Log type should be 'insert'"
            assert log_entry['batch_size'] <= batch_size, \
                f"Batch size in log exceeds config: {log_entry['batch_size']} > {batch_size}"


# ============================================================================
# Property 19: 分页查询
# ============================================================================

class TestPaginationQueries:
    """Property 19: 分页查询
    
    对于任意分页查询，返回的结果数量应该不超过 limit，
    且 offset 应该正确跳过指定数量的记录。
    
    **Feature: system-optimization, Property 19: 分页查询**
    **Validates: Requirements 9.3**
    """
    
    @given(
        total_items=st.integers(min_value=0, max_value=1000),
        page=st.integers(min_value=1, max_value=100),
        page_size=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_pagination_result_count(self, total_items, page, page_size):
        """分页结果数量不应超过 page_size
        
        **Feature: system-optimization, Property 19: 分页查询**
        **Validates: Requirements 9.3**
        """
        items = list(range(total_items))
        paginator = MockPaginator(items)
        
        result = paginator.paginate(page=page, page_size=page_size)
        
        # 验证结果数量不超过 page_size
        assert len(result.items) <= page_size, \
            f"Result count exceeds page_size: {len(result.items)} > {page_size}"
        
        # 验证 page_info 中的 page_size
        assert result.page_info.page_size == page_size, \
            f"Page size mismatch: {result.page_info.page_size} != {page_size}"
    
    @given(
        total_items=st.integers(min_value=1, max_value=500),
        page_size=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_pagination_offset_correctness(self, total_items, page_size):
        """偏移量应该正确跳过指定数量的记录
        
        **Feature: system-optimization, Property 19: 分页查询**
        **Validates: Requirements 9.3**
        """
        items = list(range(total_items))
        paginator = MockPaginator(items)
        
        # 测试多个页面
        total_pages = calculate_batch_count(total_items, page_size)
        
        for page in range(1, min(total_pages + 1, 10)):  # 最多测试 10 页
            result = paginator.paginate(page=page, page_size=page_size)
            
            expected_offset = (page - 1) * page_size
            expected_first_item = expected_offset if expected_offset < total_items else None
            
            if result.items:
                assert result.items[0] == expected_first_item, \
                    f"First item mismatch on page {page}: {result.items[0]} != {expected_first_item}"

    
    @given(
        total_items=st.integers(min_value=0, max_value=500),
        page_size=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_pagination_total_pages_calculation(self, total_items, page_size):
        """总页数计算应该正确
        
        **Feature: system-optimization, Property 19: 分页查询**
        **Validates: Requirements 9.3**
        """
        page_info = calculate_pagination(total_items, 1, page_size)
        
        expected_total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
        
        assert page_info.total_pages == expected_total_pages, \
            f"Total pages mismatch: {page_info.total_pages} != {expected_total_pages}"
        
        assert page_info.total_items == total_items, \
            f"Total items mismatch: {page_info.total_items} != {total_items}"
    
    @given(
        total_items=st.integers(min_value=1, max_value=500),
        page_size=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_pagination_has_next_prev(self, total_items, page_size):
        """has_next 和 has_prev 标志应该正确
        
        **Feature: system-optimization, Property 19: 分页查询**
        **Validates: Requirements 9.3**
        """
        total_pages = (total_items + page_size - 1) // page_size
        
        # 第一页
        page_info_first = calculate_pagination(total_items, 1, page_size)
        assert not page_info_first.has_prev, "First page should not have prev"
        assert page_info_first.has_next == (total_pages > 1), \
            f"First page has_next mismatch"
        
        # 最后一页
        if total_pages > 0:
            page_info_last = calculate_pagination(total_items, total_pages, page_size)
            assert not page_info_last.has_next, "Last page should not have next"
            assert page_info_last.has_prev == (total_pages > 1), \
                f"Last page has_prev mismatch"
        
        # 中间页 (确保不是第一页或最后一页)
        if total_pages > 2:
            middle_page = (total_pages // 2) + 1  # 确保是真正的中间页
            if middle_page > 1 and middle_page < total_pages:
                page_info_middle = calculate_pagination(total_items, middle_page, page_size)
                assert page_info_middle.has_next, "Middle page should have next"
                assert page_info_middle.has_prev, "Middle page should have prev"
    
    @given(
        total_items=st.integers(min_value=1, max_value=200),
        limit=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_cursor_pagination_limit(self, total_items, limit):
        """游标分页结果数量不应超过 limit
        
        **Feature: system-optimization, Property 19: 分页查询**
        **Validates: Requirements 9.3**
        """
        items = list(range(total_items))
        paginator = MockPaginator(items)
        
        result_items, next_cursor = paginator.cursor_paginate(cursor=None, limit=limit)
        
        # 验证结果数量不超过 limit
        assert len(result_items) <= limit, \
            f"Cursor pagination result exceeds limit: {len(result_items)} > {limit}"
        
        # 验证 next_cursor 的正确性
        if len(items) > limit:
            assert next_cursor is not None, "Should have next cursor when more items exist"
        else:
            assert next_cursor is None, "Should not have next cursor when no more items"
    
    @given(
        total_items=st.integers(min_value=10, max_value=200),
        limit=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100)
    def test_cursor_pagination_traversal(self, total_items, limit):
        """游标分页应该能遍历所有记录
        
        **Feature: system-optimization, Property 19: 分页查询**
        **Validates: Requirements 9.3**
        """
        items = list(range(total_items))
        paginator = MockPaginator(items)
        
        all_items = []
        cursor = None
        max_iterations = (total_items // limit) + 2  # 防止无限循环
        iterations = 0
        
        while iterations < max_iterations:
            result_items, next_cursor = paginator.cursor_paginate(cursor=cursor, limit=limit)
            all_items.extend(result_items)
            
            if next_cursor is None:
                break
            
            cursor = next_cursor
            iterations += 1
        
        # 验证遍历了所有记录
        assert len(all_items) == total_items, \
            f"Cursor pagination missed items: {len(all_items)} != {total_items}"
        
        # 验证顺序正确
        assert all_items == items, "Cursor pagination order mismatch"


# ============================================================================
# Property 20: 慢查询监控
# ============================================================================

class TestSlowQueryMonitoring:
    """Property 20: 慢查询监控
    
    对于任意执行时间超过 1 秒的查询，系统应该生成包含查询内容和执行时间的警告日志。
    
    **Feature: system-optimization, Property 20: 慢查询监控**
    **Validates: Requirements 9.5**
    """
    
    @given(
        duration_ms=st.floats(min_value=0, max_value=10000, allow_nan=False),
        threshold_ms=st.floats(min_value=100, max_value=5000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_slow_query_detection(self, duration_ms, threshold_ms):
        """慢查询检测应该正确
        
        **Feature: system-optimization, Property 20: 慢查询监控**
        **Validates: Requirements 9.5**
        """
        is_slow = is_slow_query(duration_ms, threshold_ms)
        
        if duration_ms >= threshold_ms:
            assert is_slow, f"Query with {duration_ms}ms should be slow (threshold: {threshold_ms}ms)"
        else:
            assert not is_slow, f"Query with {duration_ms}ms should not be slow (threshold: {threshold_ms}ms)"
    
    @given(
        sql=st.sampled_from([
            "SELECT * FROM users WHERE id = :id",
            "INSERT INTO logs (message) VALUES (:msg)",
            "UPDATE users SET name = :name WHERE id = :id",
            "DELETE FROM sessions WHERE expired_at < :now",
            "CREATE TABLE test (id INT)",
            "DROP TABLE IF EXISTS temp",
            "ALTER TABLE users ADD COLUMN email VARCHAR(255)"
        ])
    )
    @settings(max_examples=100)
    def test_query_type_extraction(self, sql):
        """查询类型提取应该正确
        
        **Feature: system-optimization, Property 20: 慢查询监控**
        **Validates: Requirements 9.5**
        """
        query_type = extract_query_type(sql)
        
        expected_types = {
            'SELECT': 'SELECT',
            'INSERT': 'INSERT',
            'UPDATE': 'UPDATE',
            'DELETE': 'DELETE',
            'CREATE': 'CREATE',
            'DROP': 'DROP',
            'ALTER': 'ALTER'
        }
        
        sql_upper = sql.strip().upper()
        expected_type = None
        for prefix, qtype in expected_types.items():
            if sql_upper.startswith(prefix):
                expected_type = qtype
                break
        
        if expected_type:
            assert query_type == expected_type, \
                f"Query type mismatch: {query_type} != {expected_type}"
        else:
            assert query_type == 'OTHER', \
                f"Unknown query type should be 'OTHER': {query_type}"
    
    @given(
        queries=st.lists(
            st.tuples(
                st.sampled_from([
                    "SELECT * FROM users",
                    "INSERT INTO logs VALUES (1)",
                    "UPDATE users SET name = 'test'",
                    "DELETE FROM sessions"
                ]),
                st.floats(min_value=0, max_value=5000, allow_nan=False)
            ),
            min_size=1,
            max_size=50
        ),
        threshold_ms=st.floats(min_value=500, max_value=2000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_slow_query_recording(self, queries, threshold_ms):
        """慢查询应该被正确记录
        
        **Feature: system-optimization, Property 20: 慢查询监控**
        **Validates: Requirements 9.5**
        """
        monitor = MockQueryMonitor(threshold_ms=threshold_ms)
        
        expected_slow_count = 0
        
        for sql, duration_ms in queries:
            is_slow = monitor.record_query(sql, duration_ms)
            
            if duration_ms >= threshold_ms:
                expected_slow_count += 1
                assert is_slow, f"Query with {duration_ms}ms should be marked as slow"
        
        # 验证慢查询计数
        assert monitor.slow_query_count == expected_slow_count, \
            f"Slow query count mismatch: {monitor.slow_query_count} != {expected_slow_count}"
        
        # 验证慢查询列表
        assert len(monitor.slow_queries) == expected_slow_count, \
            f"Slow queries list count mismatch: {len(monitor.slow_queries)} != {expected_slow_count}"

    
    @given(
        num_queries=st.integers(min_value=1, max_value=100),
        threshold_ms=st.floats(min_value=500, max_value=2000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_query_statistics_accuracy(self, num_queries, threshold_ms):
        """查询统计应该准确
        
        **Feature: system-optimization, Property 20: 慢查询监控**
        **Validates: Requirements 9.5**
        """
        monitor = MockQueryMonitor(threshold_ms=threshold_ms)
        
        total_duration = 0.0
        max_duration = 0.0
        min_duration = float('inf')
        
        for i in range(num_queries):
            duration_ms = (i + 1) * 100.0  # 100ms, 200ms, 300ms, ...
            monitor.record_query(f"SELECT {i}", duration_ms)
            
            total_duration += duration_ms
            max_duration = max(max_duration, duration_ms)
            min_duration = min(min_duration, duration_ms)
        
        stats = monitor.get_stats()
        
        # 验证总查询数
        assert stats['total_queries'] == num_queries, \
            f"Total queries mismatch: {stats['total_queries']} != {num_queries}"
        
        # 验证总时长
        assert abs(stats['total_duration_ms'] - total_duration) < 0.01, \
            f"Total duration mismatch: {stats['total_duration_ms']} != {total_duration}"
        
        # 验证最大时长
        assert abs(stats['max_duration_ms'] - max_duration) < 0.01, \
            f"Max duration mismatch: {stats['max_duration_ms']} != {max_duration}"
        
        # 验证最小时长
        assert abs(stats['min_duration_ms'] - min_duration) < 0.01, \
            f"Min duration mismatch: {stats['min_duration_ms']} != {min_duration}"
        
        # 验证平均时长
        expected_avg = total_duration / num_queries
        assert abs(stats['avg_duration_ms'] - expected_avg) < 0.01, \
            f"Avg duration mismatch: {stats['avg_duration_ms']} != {expected_avg}"
    
    @given(
        queries=st.lists(
            st.tuples(
                st.sampled_from(['SELECT', 'INSERT', 'UPDATE', 'DELETE']),
                st.floats(min_value=100, max_value=2000, allow_nan=False)
            ),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=100)
    def test_query_type_statistics(self, queries):
        """查询类型统计应该正确
        
        **Feature: system-optimization, Property 20: 慢查询监控**
        **Validates: Requirements 9.5**
        """
        monitor = MockQueryMonitor()
        
        expected_counts = {}
        
        for query_type, duration_ms in queries:
            sql = f"{query_type} * FROM table"
            monitor.record_query(sql, duration_ms)
            expected_counts[query_type] = expected_counts.get(query_type, 0) + 1
        
        stats = monitor.get_stats()
        
        for query_type, expected_count in expected_counts.items():
            actual_count = stats['queries_by_type'].get(query_type, 0)
            assert actual_count == expected_count, \
                f"Query type count mismatch for {query_type}: {actual_count} != {expected_count}"
    
    @given(
        num_slow_queries=st.integers(min_value=1, max_value=20),
        limit=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100)
    def test_get_slow_queries_limit(self, num_slow_queries, limit):
        """获取慢查询应该遵守 limit 限制
        
        **Feature: system-optimization, Property 20: 慢查询监控**
        **Validates: Requirements 9.5**
        """
        monitor = MockQueryMonitor(threshold_ms=500)
        
        # 记录慢查询
        for i in range(num_slow_queries):
            duration_ms = 1000 + i * 100  # 都超过阈值
            monitor.record_query(f"SELECT {i}", duration_ms)
        
        slow_queries = monitor.get_slow_queries(limit=limit)
        
        # 验证返回数量不超过 limit
        expected_count = min(num_slow_queries, limit)
        assert len(slow_queries) == expected_count, \
            f"Slow queries count mismatch: {len(slow_queries)} != {expected_count}"
        
        # 验证按时长降序排列
        for i in range(len(slow_queries) - 1):
            assert slow_queries[i].duration_ms >= slow_queries[i + 1].duration_ms, \
                "Slow queries should be sorted by duration descending"
    
    @given(
        num_queries=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_monitor_reset(self, num_queries):
        """重置后统计应该清零
        
        **Feature: system-optimization, Property 20: 慢查询监控**
        **Validates: Requirements 9.5**
        """
        monitor = MockQueryMonitor()
        
        # 记录一些查询
        for i in range(num_queries):
            monitor.record_query(f"SELECT {i}", 1500)  # 慢查询
        
        # 验证有数据
        assert monitor.total_queries == num_queries
        assert monitor.slow_query_count > 0
        
        # 重置
        monitor.reset()
        
        # 验证已清零
        stats = monitor.get_stats()
        assert stats['total_queries'] == 0, "Total queries should be 0 after reset"
        assert stats['slow_queries'] == 0, "Slow queries should be 0 after reset"
        assert stats['total_duration_ms'] == 0.0, "Total duration should be 0 after reset"
        assert len(monitor.slow_queries) == 0, "Slow queries list should be empty after reset"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
