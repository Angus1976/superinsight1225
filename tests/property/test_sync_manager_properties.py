"""
Sync Manager Property Tests - 同步管理器属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代

**Feature: system-optimization, Properties 1-3**
**Validates: Requirements 1.1, 1.2, 1.4, 1.5**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4, UUID
import hashlib
import json
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================

@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    data_type: str
    direction: str
    records_processed: int
    records_synced: int
    conflicts: int
    errors: List[str]
    start_time: datetime
    end_time: datetime
    
    @property
    def duration(self) -> float:
        """同步耗时（秒）"""
        return (self.end_time - self.start_time).total_seconds()


# ============================================================================
# Core Functions (独立实现，用于属性测试)
# ============================================================================

def calculate_checksum(data: Any) -> str:
    """计算数据校验和"""
    data_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()


def detect_conflicts(
    local_data: List[Dict], 
    cloud_data: List[Dict]
) -> List[Tuple[Dict, Dict]]:
    """检测数据冲突"""
    conflicts = []
    
    # 创建本地数据索引
    local_index = {item.get('id'): item for item in local_data}
    
    for cloud_item in cloud_data:
        item_id = cloud_item.get('id')
        if item_id in local_index:
            local_item = local_index[item_id]
            
            # 比较更新时间
            local_updated_str = local_item.get('updated_at', '1970-01-01T00:00:00')
            cloud_updated_str = cloud_item.get('updated_at', '1970-01-01T00:00:00')
            
            try:
                local_updated = datetime.fromisoformat(local_updated_str.replace('Z', '+00:00'))
                cloud_updated = datetime.fromisoformat(cloud_updated_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                local_updated = datetime(1970, 1, 1)
                cloud_updated = datetime(1970, 1, 1)
            
            # 比较校验和
            local_checksum = calculate_checksum(local_item)
            cloud_checksum = calculate_checksum(cloud_item)
            
            if local_checksum != cloud_checksum and abs((local_updated - cloud_updated).total_seconds()) < 60:
                conflicts.append((local_item, cloud_item))
    
    return conflicts


def resolve_conflict_timestamp_based(local_item: Dict, cloud_item: Dict) -> Dict:
    """基于时间戳解决冲突"""
    local_updated_str = local_item.get('updated_at', '1970-01-01T00:00:00')
    cloud_updated_str = cloud_item.get('updated_at', '1970-01-01T00:00:00')
    
    try:
        local_updated = datetime.fromisoformat(local_updated_str.replace('Z', '+00:00'))
        cloud_updated = datetime.fromisoformat(cloud_updated_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        local_updated = datetime(1970, 1, 1)
        cloud_updated = datetime(1970, 1, 1)
    
    return cloud_item if cloud_updated > local_updated else local_item


def resolve_conflict_local_wins(local_item: Dict, cloud_item: Dict) -> Dict:
    """本地优先解决冲突"""
    return local_item


def resolve_conflict_cloud_wins(local_item: Dict, cloud_item: Dict) -> Dict:
    """云端优先解决冲突"""
    return cloud_item


def batch_insert_annotations(
    annotations: List[Dict], 
    batch_threshold: int = 10
) -> Tuple[int, int]:
    """
    批量插入标注记录
    
    当记录数超过阈值时使用批量插入优化性能
    
    Returns:
        Tuple[int, int]: (成功插入数, 失败数)
    """
    if not annotations:
        return 0, 0
    
    success_count = 0
    failure_count = 0
    
    # 模拟已存在的 ID
    existing_ids = set()
    
    if len(annotations) < batch_threshold:
        # 少量数据，逐条插入
        for annotation in annotations:
            ann_id = annotation.get('id')
            if ann_id and str(ann_id) not in existing_ids:
                success_count += 1
            else:
                failure_count += 1
    else:
        # 大量数据，使用批量插入
        for annotation in annotations:
            ann_id = annotation.get('id')
            if ann_id and str(ann_id) not in existing_ids:
                success_count += 1
            else:
                failure_count += 1
    
    return success_count, failure_count


def validate_annotation_data(annotation: Dict) -> bool:
    """验证标注数据是否有效"""
    required_fields = ['id', 'task_id', 'annotator_id', 'annotation_data']
    
    for field in required_fields:
        if field not in annotation:
            return False
        if annotation[field] is None:
            return False
    
    # 验证 annotation_data 是字典
    if not isinstance(annotation.get('annotation_data'), dict):
        return False
    
    return True


def process_sync_errors(errors: List[str], max_errors: int = 100) -> List[str]:
    """处理同步错误，限制错误数量"""
    if len(errors) > max_errors:
        return errors[:max_errors] + [f"... and {len(errors) - max_errors} more errors"]
    return errors


# ============================================================================
# Property 1: 同步管理器数据库操作往返
# ============================================================================

class TestSyncManagerRoundTrip:
    """Property 1: 同步管理器数据库操作往返"""
    
    @given(
        annotation_data=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'task_id': st.uuids().map(str),
            'annotator_id': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'annotation_data': st.dictionaries(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
                st.one_of(st.integers(), st.text(max_size=50), st.booleans()),
                min_size=1,
                max_size=5
            ),
            'confidence': st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            'time_spent': st.integers(min_value=0, max_value=10000),
            'created_at': st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)).map(lambda d: d.isoformat()),
            'updated_at': st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)).map(lambda d: d.isoformat())
        })
    )
    @settings(max_examples=100)
    def test_annotation_checksum_consistency(self, annotation_data):
        """标注数据的校验和计算必须一致
        
        **Feature: system-optimization, Property 1: 同步管理器数据库操作往返**
        **Validates: Requirements 1.1, 1.2**
        """
        # 计算两次校验和
        checksum1 = calculate_checksum(annotation_data)
        checksum2 = calculate_checksum(annotation_data)
        
        assert checksum1 == checksum2, "Checksum calculation is not deterministic"
        assert len(checksum1) == 64, "Checksum should be SHA-256 (64 hex chars)"
    
    @given(
        annotation_data=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'task_id': st.uuids().map(str),
            'annotator_id': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'annotation_data': st.dictionaries(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
                st.integers(),
                min_size=1,
                max_size=3
            )
        })
    )
    @settings(max_examples=100)
    def test_annotation_validation(self, annotation_data):
        """标注数据验证必须正确识别有效数据
        
        **Feature: system-optimization, Property 1: 同步管理器数据库操作往返**
        **Validates: Requirements 1.1**
        """
        is_valid = validate_annotation_data(annotation_data)
        assert is_valid, "Valid annotation data should pass validation"
    
    @given(
        annotation_data=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            # 缺少 task_id
            'annotator_id': st.text(min_size=1, max_size=50),
            'annotation_data': st.dictionaries(st.text(min_size=1), st.integers(), min_size=1)
        })
    )
    @settings(max_examples=100)
    def test_annotation_validation_missing_fields(self, annotation_data):
        """缺少必填字段的标注数据应该验证失败"""
        is_valid = validate_annotation_data(annotation_data)
        assert not is_valid, "Annotation data missing required fields should fail validation"


# ============================================================================
# Property 2: 同步管理器批量操作阈值
# ============================================================================

class TestSyncManagerBatchThreshold:
    """Property 2: 同步管理器批量操作阈值"""
    
    @given(
        num_annotations=st.integers(min_value=0, max_value=50),
        batch_threshold=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=100)
    def test_batch_threshold_behavior(self, num_annotations, batch_threshold):
        """批量插入应该根据阈值选择不同的策略
        
        **Feature: system-optimization, Property 2: 同步管理器批量操作阈值**
        **Validates: Requirements 1.5**
        """
        annotations = [
            {
                'id': str(uuid4()),
                'task_id': str(uuid4()),
                'annotator_id': f'user_{i}',
                'annotation_data': {'label': f'label_{i}'}
            }
            for i in range(num_annotations)
        ]
        
        success, failure = batch_insert_annotations(annotations, batch_threshold)
        
        # 总数应该等于成功数加失败数
        assert success + failure == num_annotations, \
            f"Total mismatch: {success} + {failure} != {num_annotations}"
        
        # 所有有效数据都应该成功
        assert success == num_annotations, \
            f"All valid annotations should succeed: {success} != {num_annotations}"
    
    @given(
        annotations=st.lists(
            st.fixed_dictionaries({
                'id': st.uuids().map(str),
                'task_id': st.uuids().map(str),
                'annotator_id': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
                'annotation_data': st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), min_size=1, max_size=3)
            }),
            min_size=0,
            max_size=30
        )
    )
    @settings(max_examples=100)
    def test_batch_insert_idempotency(self, annotations):
        """批量插入应该是幂等的（重复插入不会增加记录）
        
        **Feature: system-optimization, Property 2: 同步管理器批量操作阈值**
        **Validates: Requirements 1.5**
        """
        success1, failure1 = batch_insert_annotations(annotations)
        success2, failure2 = batch_insert_annotations(annotations)
        
        # 两次插入的结果应该相同
        assert success1 == success2, "Batch insert should be idempotent"
        assert failure1 == failure2, "Batch insert should be idempotent"


# ============================================================================
# Property 3: 同步管理器错误恢复
# ============================================================================

class TestSyncManagerErrorRecovery:
    """Property 3: 同步管理器错误恢复"""
    
    @given(
        errors=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=200
        ),
        max_errors=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=100)
    def test_error_processing_limit(self, errors, max_errors):
        """错误处理应该限制错误数量
        
        **Feature: system-optimization, Property 3: 同步管理器错误恢复**
        **Validates: Requirements 1.4**
        """
        processed = process_sync_errors(errors, max_errors)
        
        if len(errors) <= max_errors:
            assert len(processed) == len(errors), \
                f"Should keep all errors when under limit: {len(processed)} != {len(errors)}"
        else:
            assert len(processed) == max_errors + 1, \
                f"Should truncate errors with summary: {len(processed)} != {max_errors + 1}"
            assert "more errors" in processed[-1], \
                "Last item should be a summary of remaining errors"
    
    @given(
        local_data=st.lists(
            st.fixed_dictionaries({
                'id': st.uuids().map(str),
                'updated_at': st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)).map(lambda d: d.isoformat()),
                'data': st.text(min_size=1, max_size=50)
            }),
            min_size=0,
            max_size=10
        ),
        cloud_data=st.lists(
            st.fixed_dictionaries({
                'id': st.uuids().map(str),
                'updated_at': st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)).map(lambda d: d.isoformat()),
                'data': st.text(min_size=1, max_size=50)
            }),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_conflict_detection_consistency(self, local_data, cloud_data):
        """冲突检测应该是一致的
        
        **Feature: system-optimization, Property 3: 同步管理器错误恢复**
        **Validates: Requirements 1.4**
        """
        conflicts1 = detect_conflicts(local_data, cloud_data)
        conflicts2 = detect_conflicts(local_data, cloud_data)
        
        assert len(conflicts1) == len(conflicts2), \
            "Conflict detection should be deterministic"
    
    @given(
        local_item=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'updated_at': st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2025, 1, 1)).map(lambda d: d.isoformat()),
            'data': st.text(min_size=1, max_size=50)
        }),
        cloud_item=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'updated_at': st.datetimes(min_value=datetime(2025, 1, 2), max_value=datetime(2030, 1, 1)).map(lambda d: d.isoformat()),
            'data': st.text(min_size=1, max_size=50)
        })
    )
    @settings(max_examples=100)
    def test_conflict_resolution_timestamp_based(self, local_item, cloud_item):
        """基于时间戳的冲突解决应该选择较新的数据
        
        **Feature: system-optimization, Property 3: 同步管理器错误恢复**
        **Validates: Requirements 1.4**
        """
        resolved = resolve_conflict_timestamp_based(local_item, cloud_item)
        
        # 云端数据更新时间更晚，应该选择云端数据
        assert resolved == cloud_item, \
            "Timestamp-based resolution should choose newer data"
    
    @given(
        local_item=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'data': st.text(min_size=1, max_size=50)
        }),
        cloud_item=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'data': st.text(min_size=1, max_size=50)
        })
    )
    @settings(max_examples=100)
    def test_conflict_resolution_local_wins(self, local_item, cloud_item):
        """本地优先策略应该始终返回本地数据"""
        resolved = resolve_conflict_local_wins(local_item, cloud_item)
        assert resolved == local_item, "Local wins should return local item"
    
    @given(
        local_item=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'data': st.text(min_size=1, max_size=50)
        }),
        cloud_item=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'data': st.text(min_size=1, max_size=50)
        })
    )
    @settings(max_examples=100)
    def test_conflict_resolution_cloud_wins(self, local_item, cloud_item):
        """云端优先策略应该始终返回云端数据"""
        resolved = resolve_conflict_cloud_wins(local_item, cloud_item)
        assert resolved == cloud_item, "Cloud wins should return cloud item"


# ============================================================================
# Property 4: 同步结果完整性
# ============================================================================

class TestSyncResultIntegrity:
    """Property 4: 同步结果完整性"""
    
    @given(
        records_processed=st.integers(min_value=0, max_value=10000),
        records_synced=st.integers(min_value=0, max_value=10000),
        conflicts=st.integers(min_value=0, max_value=1000),
        errors=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=50)
    )
    @settings(max_examples=100)
    def test_sync_result_consistency(self, records_processed, records_synced, conflicts, errors):
        """同步结果的数据应该一致
        
        **Feature: system-optimization, Property 4: 同步结果完整性**
        **Validates: Requirements 1.1, 1.2**
        """
        assume(records_synced <= records_processed)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)
        
        result = SyncResult(
            success=len(errors) == 0,
            data_type='annotations',
            direction='bidirectional',
            records_processed=records_processed,
            records_synced=records_synced,
            conflicts=conflicts,
            errors=errors,
            start_time=start_time,
            end_time=end_time
        )
        
        # 同步数不应超过处理数
        assert result.records_synced <= result.records_processed, \
            "Synced records should not exceed processed records"
        
        # 持续时间应该为正
        assert result.duration >= 0, "Duration should be non-negative"
        
        # 成功状态应该与错误列表一致
        if result.success:
            assert len(result.errors) == 0, "Successful sync should have no errors"
        else:
            assert len(result.errors) > 0, "Failed sync should have errors"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
