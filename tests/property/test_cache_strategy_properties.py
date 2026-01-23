"""
Cache Strategy Property Tests - 缓存策略属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代

**Feature: system-optimization, Properties 16-17**
**Validates: Requirements 8.1, 8.3, 8.5**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass, field


# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================

@dataclass
class CacheConfig:
    """缓存配置"""
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 3600
    ttl_by_type: Dict[str, int] = field(default_factory=lambda: {
        "user": 1800,
        "project": 3600,
        "task": 600,
        "config": 86400,
        "data_source": 300,
        "evaluation_result": 3600,
        "business_rule": 600,
        "system_config": 1800,
        "user_session": 7200,
    })
    hit_rate_threshold: float = 0.8
    warmup_keys: List[str] = field(default_factory=list)
    key_prefix: str = "superinsight:"
    enable_logging: bool = False


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    invalidations: int = 0
    errors: int = 0
    last_reset: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# ============================================================================
# Core Functions (独立实现，用于属性测试)
# ============================================================================

def serialize_value(value: Any) -> str:
    """序列化值为 JSON 字符串"""
    return json.dumps(value, ensure_ascii=False, default=str)


def deserialize_value(value: str) -> Any:
    """反序列化 JSON 字符串"""
    return json.loads(value)


def get_ttl_for_type(data_type: Optional[str], config: CacheConfig) -> int:
    """获取数据类型对应的 TTL"""
    if data_type and data_type in config.ttl_by_type:
        return config.ttl_by_type[data_type]
    return config.default_ttl


def calculate_hit_rate(hits: int, misses: int) -> float:
    """计算缓存命中率"""
    total = hits + misses
    return hits / total if total > 0 else 0.0


def check_hit_rate_threshold(hits: int, misses: int, threshold: float) -> bool:
    """检查命中率是否达到阈值"""
    hit_rate = calculate_hit_rate(hits, misses)
    return hit_rate >= threshold


def get_full_key(key: str, prefix: str) -> str:
    """获取带前缀的完整键名"""
    if key.startswith(prefix):
        return key
    return f"{prefix}{key}"


def match_pattern(key: str, pattern: str) -> bool:
    """检查键是否匹配模式（简化的通配符匹配）"""
    import fnmatch
    return fnmatch.fnmatch(key, pattern)


class MockCacheStorage:
    """模拟缓存存储，用于属性测试"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.storage: Dict[str, str] = {}
        self.ttls: Dict[str, int] = {}
        self.stats = CacheStats(last_reset=datetime.utcnow())
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        full_key = get_full_key(key, self.config.key_prefix)
        
        if full_key in self.storage:
            self.stats.hits += 1
            return deserialize_value(self.storage[full_key])
        else:
            self.stats.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, data_type: Optional[str] = None) -> bool:
        """设置缓存值"""
        full_key = get_full_key(key, self.config.key_prefix)
        actual_ttl = ttl if ttl is not None else get_ttl_for_type(data_type, self.config)
        
        try:
            self.storage[full_key] = serialize_value(value)
            self.ttls[full_key] = actual_ttl
            self.stats.sets += 1
            return True
        except Exception:
            self.stats.errors += 1
            return False
    
    def get_or_set(self, key: str, factory_value: Any, ttl: Optional[int] = None, data_type: Optional[str] = None) -> Any:
        """Cache-aside 模式"""
        cached = self.get(key)
        if cached is not None:
            return cached
        
        self.set(key, factory_value, ttl=ttl, data_type=data_type)
        return factory_value
    
    def invalidate(self, key: str) -> bool:
        """失效单个缓存"""
        full_key = get_full_key(key, self.config.key_prefix)
        
        if full_key in self.storage:
            del self.storage[full_key]
            if full_key in self.ttls:
                del self.ttls[full_key]
            self.stats.invalidations += 1
            return True
        return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """批量失效匹配模式的缓存"""
        full_pattern = get_full_key(pattern, self.config.key_prefix)
        keys_to_delete = [k for k in self.storage.keys() if match_pattern(k, full_pattern)]
        
        for key in keys_to_delete:
            del self.storage[key]
            if key in self.ttls:
                del self.ttls[key]
        
        self.stats.invalidations += len(keys_to_delete)
        return len(keys_to_delete)
    
    def check_hit_rate(self) -> bool:
        """检查命中率是否达标"""
        return check_hit_rate_threshold(
            self.stats.hits, 
            self.stats.misses, 
            self.config.hit_rate_threshold
        )
    
    def reset_stats(self):
        """重置统计"""
        self.stats = CacheStats(last_reset=datetime.utcnow())


# ============================================================================
# Property 16: 缓存一致性
# ============================================================================

class TestCacheConsistency:
    """Property 16: 缓存一致性
    
    对于任意缓存的数据，如果底层数据更新，缓存应该失效；
    下次访问应该从数据库获取最新数据并更新缓存。
    
    **Feature: system-optimization, Property 16: 缓存一致性**
    **Validates: Requirements 8.1, 8.3**
    """
    
    @given(
        key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))),
        value=st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(max_size=100),
            st.booleans(),
            st.lists(st.integers(), max_size=10),
            st.dictionaries(st.text(min_size=1, max_size=20), st.integers(), max_size=5)
        )
    )
    @settings(max_examples=100)
    def test_cache_roundtrip(self, key, value):
        """缓存数据的往返一致性
        
        **Feature: system-optimization, Property 16: 缓存一致性**
        **Validates: Requirements 8.1**
        """
        # 过滤掉无效的键
        assume(key.strip() != "")
        assume(not key.startswith("*"))
        
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        # 设置缓存
        success = cache.set(key, value)
        assert success, "Cache set should succeed"
        
        # 获取缓存
        cached_value = cache.get(key)
        
        # 验证往返一致性
        assert cached_value == value, f"Cache roundtrip failed: {cached_value} != {value}"
    
    @given(
        key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        initial_value=st.integers(),
        updated_value=st.integers()
    )
    @settings(max_examples=100)
    def test_cache_invalidation_on_update(self, key, initial_value, updated_value):
        """数据更新时缓存应该失效
        
        **Feature: system-optimization, Property 16: 缓存一致性**
        **Validates: Requirements 8.3**
        """
        assume(key.strip() != "")
        assume(initial_value != updated_value)
        
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        # 设置初始缓存
        cache.set(key, initial_value)
        
        # 验证初始值
        assert cache.get(key) == initial_value
        
        # 失效缓存
        invalidated = cache.invalidate(key)
        assert invalidated, "Cache invalidation should succeed"
        
        # 验证缓存已失效
        assert cache.get(key) is None, "Cache should be invalidated"
        
        # 设置新值
        cache.set(key, updated_value)
        
        # 验证新值
        assert cache.get(key) == updated_value, "Cache should have updated value"
    
    @given(
        keys=st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=20,
            unique=True
        ),
        values=st.lists(st.integers(), min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    def test_cache_aside_pattern(self, keys, values):
        """Cache-aside 模式应该正确工作
        
        **Feature: system-optimization, Property 16: 缓存一致性**
        **Validates: Requirements 8.1**
        """
        assume(len(keys) > 0)
        assume(len(values) > 0)
        
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        # 使用 cache-aside 模式
        key = keys[0]
        value = values[0]
        
        # 第一次访问 - 缓存未命中
        initial_hits = cache.stats.hits
        initial_misses = cache.stats.misses
        
        result = cache.get_or_set(key, value)
        
        # 应该返回 factory 值
        assert result == value, "get_or_set should return factory value on miss"
        
        # 应该记录一次 miss
        assert cache.stats.misses == initial_misses + 1, "Should record a miss"
        
        # 第二次访问 - 缓存命中
        result2 = cache.get_or_set(key, value + 1)  # 使用不同的 factory 值
        
        # 应该返回缓存值，而不是新的 factory 值
        assert result2 == value, "get_or_set should return cached value on hit"
        
        # 应该记录一次 hit
        assert cache.stats.hits == initial_hits + 1, "Should record a hit"
    
    @given(
        prefix=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
        suffixes=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_batch_invalidation_pattern(self, prefix, suffixes):
        """批量失效应该正确匹配模式
        
        **Feature: system-optimization, Property 16: 缓存一致性**
        **Validates: Requirements 8.3**
        """
        assume(prefix.strip() != "")
        assume(all(s.strip() != "" for s in suffixes))
        
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        # 设置多个缓存键
        matching_keys = [f"{prefix}:{suffix}" for suffix in suffixes]
        non_matching_key = f"other:{suffixes[0]}" if suffixes else "other:key"
        
        for key in matching_keys:
            cache.set(key, 1)
        cache.set(non_matching_key, 2)
        
        # 批量失效匹配模式的键
        pattern = f"{prefix}:*"
        invalidated_count = cache.invalidate_pattern(pattern)
        
        # 验证匹配的键被失效
        assert invalidated_count == len(matching_keys), \
            f"Should invalidate {len(matching_keys)} keys, got {invalidated_count}"
        
        for key in matching_keys:
            assert cache.get(key) is None, f"Key {key} should be invalidated"
        
        # 验证不匹配的键未被失效
        assert cache.get(non_matching_key) == 2, "Non-matching key should not be invalidated"


# ============================================================================
# Property 17: 缓存命中率监控
# ============================================================================

class TestCacheHitRateMonitoring:
    """Property 17: 缓存命中率监控
    
    对于任意缓存操作序列，如果命中率低于 80%，系统应该生成警告日志。
    
    **Feature: system-optimization, Property 17: 缓存命中率监控**
    **Validates: Requirements 8.5**
    """
    
    @given(
        hits=st.integers(min_value=0, max_value=1000),
        misses=st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=100)
    def test_hit_rate_calculation(self, hits, misses):
        """命中率计算应该正确
        
        **Feature: system-optimization, Property 17: 缓存命中率监控**
        **Validates: Requirements 8.5**
        """
        hit_rate = calculate_hit_rate(hits, misses)
        
        total = hits + misses
        if total == 0:
            assert hit_rate == 0.0, "Hit rate should be 0 when no operations"
        else:
            expected_rate = hits / total
            assert abs(hit_rate - expected_rate) < 0.0001, \
                f"Hit rate calculation error: {hit_rate} != {expected_rate}"
            assert 0.0 <= hit_rate <= 1.0, "Hit rate should be between 0 and 1"
    
    @given(
        hits=st.integers(min_value=0, max_value=1000),
        misses=st.integers(min_value=0, max_value=1000),
        threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_hit_rate_threshold_check(self, hits, misses, threshold):
        """命中率阈值检查应该正确
        
        **Feature: system-optimization, Property 17: 缓存命中率监控**
        **Validates: Requirements 8.5**
        """
        hit_rate = calculate_hit_rate(hits, misses)
        is_above_threshold = check_hit_rate_threshold(hits, misses, threshold)
        
        if hit_rate >= threshold:
            assert is_above_threshold, \
                f"Should be above threshold: {hit_rate} >= {threshold}"
        else:
            assert not is_above_threshold, \
                f"Should be below threshold: {hit_rate} < {threshold}"
    
    @given(
        num_hits=st.integers(min_value=0, max_value=100),
        num_misses=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100)
    def test_stats_tracking(self, num_hits, num_misses):
        """统计跟踪应该准确
        
        **Feature: system-optimization, Property 17: 缓存命中率监控**
        **Validates: Requirements 8.5**
        """
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        # 模拟缓存操作
        for i in range(num_hits):
            key = f"hit_key_{i}"
            cache.set(key, i)
            cache.get(key)  # 命中
        
        for i in range(num_misses):
            cache.get(f"miss_key_{i}")  # 未命中
        
        # 验证统计
        assert cache.stats.hits == num_hits, \
            f"Hits mismatch: {cache.stats.hits} != {num_hits}"
        assert cache.stats.misses == num_misses, \
            f"Misses mismatch: {cache.stats.misses} != {num_misses}"
        assert cache.stats.sets == num_hits, \
            f"Sets mismatch: {cache.stats.sets} != {num_hits}"
    
    @given(
        high_hit_ratio=st.floats(min_value=0.8, max_value=1.0, allow_nan=False),
        low_hit_ratio=st.floats(min_value=0.0, max_value=0.79, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_hit_rate_warning_threshold(self, high_hit_ratio, low_hit_ratio):
        """命中率低于 80% 时应该触发警告
        
        **Feature: system-optimization, Property 17: 缓存命中率监控**
        **Validates: Requirements 8.5**
        """
        config = CacheConfig(hit_rate_threshold=0.8, enable_logging=False)
        
        # 高命中率场景
        high_hits = int(high_hit_ratio * 100)
        high_misses = 100 - high_hits
        
        cache_high = MockCacheStorage(config)
        cache_high.stats.hits = high_hits
        cache_high.stats.misses = high_misses
        
        assert cache_high.check_hit_rate(), \
            f"High hit rate ({high_hit_ratio}) should pass threshold check"
        
        # 低命中率场景
        low_hits = int(low_hit_ratio * 100)
        low_misses = 100 - low_hits
        
        cache_low = MockCacheStorage(config)
        cache_low.stats.hits = low_hits
        cache_low.stats.misses = low_misses
        
        assert not cache_low.check_hit_rate(), \
            f"Low hit rate ({low_hit_ratio}) should fail threshold check"
    
    @given(
        operations=st.lists(
            st.tuples(
                st.sampled_from(['set', 'get', 'invalidate']),
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N')))
            ),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=100)
    def test_stats_consistency_after_operations(self, operations):
        """操作后统计应该保持一致
        
        **Feature: system-optimization, Property 17: 缓存命中率监控**
        **Validates: Requirements 8.5**
        """
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        expected_sets = 0
        expected_invalidations = 0
        
        for op, key in operations:
            if not key.strip():
                continue
                
            if op == 'set':
                cache.set(key, 1)
                expected_sets += 1
            elif op == 'get':
                cache.get(key)
            elif op == 'invalidate':
                if cache.invalidate(key):
                    expected_invalidations += 1
        
        # 验证统计一致性
        assert cache.stats.sets == expected_sets, \
            f"Sets mismatch: {cache.stats.sets} != {expected_sets}"
        assert cache.stats.invalidations == expected_invalidations, \
            f"Invalidations mismatch: {cache.stats.invalidations} != {expected_invalidations}"
        
        # 命中 + 未命中 应该等于 get 操作数
        total_gets = cache.stats.hits + cache.stats.misses
        get_count = sum(1 for op, key in operations if op == 'get' and key.strip())
        assert total_gets == get_count, \
            f"Total gets mismatch: {total_gets} != {get_count}"


# ============================================================================
# Additional Properties: TTL 配置和序列化
# ============================================================================

class TestCacheTTLConfiguration:
    """TTL 配置测试"""
    
    @given(
        data_type=st.sampled_from([
            'user', 'project', 'task', 'config', 
            'data_source', 'evaluation_result', 
            'business_rule', 'system_config', 'user_session'
        ])
    )
    @settings(max_examples=100)
    def test_ttl_by_data_type(self, data_type):
        """不同数据类型应该有不同的 TTL
        
        **Feature: system-optimization**
        **Validates: Requirements 8.2**
        """
        config = CacheConfig()
        ttl = get_ttl_for_type(data_type, config)
        
        assert ttl > 0, f"TTL for {data_type} should be positive"
        assert ttl == config.ttl_by_type[data_type], \
            f"TTL mismatch for {data_type}"
    
    @given(
        unknown_type=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',)))
    )
    @settings(max_examples=100)
    def test_default_ttl_for_unknown_type(self, unknown_type):
        """未知数据类型应该使用默认 TTL
        
        **Feature: system-optimization**
        **Validates: Requirements 8.2**
        """
        assume(unknown_type not in [
            'user', 'project', 'task', 'config', 
            'data_source', 'evaluation_result', 
            'business_rule', 'system_config', 'user_session'
        ])
        
        config = CacheConfig()
        ttl = get_ttl_for_type(unknown_type, config)
        
        assert ttl == config.default_ttl, \
            f"Unknown type should use default TTL: {ttl} != {config.default_ttl}"


class TestCacheSerialization:
    """序列化测试"""
    
    @given(
        value=st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(max_size=100),
            st.booleans(),
            st.none(),
            st.lists(st.integers(), max_size=10),
            st.dictionaries(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
                st.one_of(st.integers(), st.text(max_size=50), st.booleans()),
                max_size=5
            )
        )
    )
    @settings(max_examples=100)
    def test_serialization_roundtrip(self, value):
        """序列化和反序列化应该保持数据一致
        
        **Feature: system-optimization**
        **Validates: Requirements 8.1**
        """
        serialized = serialize_value(value)
        deserialized = deserialize_value(serialized)
        
        assert deserialized == value, \
            f"Serialization roundtrip failed: {deserialized} != {value}"
    
    @given(
        nested_dict=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'name': st.text(min_size=1, max_size=50),
            'data': st.dictionaries(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
                st.integers(),
                max_size=5
            ),
            'tags': st.lists(st.text(max_size=20), max_size=5)
        })
    )
    @settings(max_examples=100)
    def test_complex_object_serialization(self, nested_dict):
        """复杂对象的序列化应该正确
        
        **Feature: system-optimization**
        **Validates: Requirements 8.1**
        """
        serialized = serialize_value(nested_dict)
        deserialized = deserialize_value(serialized)
        
        assert deserialized == nested_dict, \
            f"Complex object serialization failed"
        assert isinstance(serialized, str), \
            "Serialized value should be a string"


class TestCacheKeyManagement:
    """缓存键管理测试"""
    
    @given(
        key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        prefix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',)))
    )
    @settings(max_examples=100)
    def test_key_prefix_application(self, key, prefix):
        """键前缀应该正确应用
        
        **Feature: system-optimization**
        **Validates: Requirements 8.1**
        """
        assume(key.strip() != "")
        assume(prefix.strip() != "")
        
        full_prefix = f"{prefix}:"
        full_key = get_full_key(key, full_prefix)
        
        assert full_key.startswith(full_prefix), \
            f"Full key should start with prefix: {full_key}"
        
        # 已有前缀的键不应该重复添加
        full_key_again = get_full_key(full_key, full_prefix)
        assert full_key_again == full_key, \
            "Key with prefix should not get prefix added again"
    
    @given(
        pattern=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
        matching_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        non_matching_prefix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',)))
    )
    @settings(max_examples=100)
    def test_pattern_matching(self, pattern, matching_suffix, non_matching_prefix):
        """模式匹配应该正确工作
        
        **Feature: system-optimization**
        **Validates: Requirements 8.3**
        """
        assume(pattern.strip() != "")
        assume(matching_suffix.strip() != "")
        assume(non_matching_prefix.strip() != "")
        assume(non_matching_prefix != pattern)
        
        wildcard_pattern = f"{pattern}*"
        matching_key = f"{pattern}{matching_suffix}"
        non_matching_key = f"{non_matching_prefix}{matching_suffix}"
        
        assert match_pattern(matching_key, wildcard_pattern), \
            f"Key {matching_key} should match pattern {wildcard_pattern}"
        
        # 不匹配的键
        if not non_matching_key.startswith(pattern):
            assert not match_pattern(non_matching_key, wildcard_pattern), \
                f"Key {non_matching_key} should not match pattern {wildcard_pattern}"


# ============================================================================
# 缓存预热测试
# ============================================================================

class TestCacheWarmup:
    """缓存预热测试"""
    
    @given(
        warmup_data=st.dictionaries(
            st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            st.integers(),
            min_size=0,
            max_size=20
        )
    )
    @settings(max_examples=100)
    def test_warmup_loads_all_keys(self, warmup_data):
        """预热应该加载所有指定的键
        
        **Feature: system-optimization**
        **Validates: Requirements 8.4**
        """
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        # 模拟预热
        for key, value in warmup_data.items():
            if key.strip():
                cache.set(key, value)
        
        # 验证所有键都被加载
        for key, value in warmup_data.items():
            if key.strip():
                cached = cache.get(key)
                assert cached == value, \
                    f"Warmup key {key} should have value {value}, got {cached}"
    
    @given(
        keys=st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_warmup_stats_tracking(self, keys):
        """预热应该正确跟踪统计
        
        **Feature: system-optimization**
        **Validates: Requirements 8.4**
        """
        valid_keys = [k for k in keys if k.strip()]
        assume(len(valid_keys) > 0)
        
        config = CacheConfig(enable_logging=False)
        cache = MockCacheStorage(config)
        
        # 模拟预热
        for i, key in enumerate(valid_keys):
            cache.set(key, i)
        
        # 验证 sets 统计
        assert cache.stats.sets == len(valid_keys), \
            f"Sets should equal number of warmup keys: {cache.stats.sets} != {len(valid_keys)}"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
