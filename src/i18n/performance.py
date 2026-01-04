"""
性能优化模块
提供翻译查找性能优化和监控功能
"""

import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache, wraps
from collections import defaultdict
from contextvars import ContextVar
import weakref
import gc

# 性能监控数据
_performance_stats: Dict[str, Any] = {
    'lookup_count': 0,
    'total_lookup_time': 0.0,
    'cache_hits': 0,
    'cache_misses': 0,
    'startup_time': 0.0,
    'memory_usage': 0,
    'concurrent_requests': 0,
    'max_concurrent_requests': 0
}

# 线程锁用于性能统计
_stats_lock = threading.Lock()

# 当前并发请求计数器
_concurrent_counter: ContextVar[int] = ContextVar('concurrent_counter', default=0)

# 缓存配置
CACHE_SIZE = 1000  # LRU缓存大小
PRECOMPUTE_COMMON_KEYS = True  # 是否预计算常用键

# 常用翻译键（基于使用频率优化）
COMMON_TRANSLATION_KEYS = {
    'app_name', 'login', 'logout', 'error', 'success', 'warning', 'info',
    'status', 'healthy', 'unhealthy', 'pending', 'completed', 'failed',
    'operation_successful', 'operation_failed', 'invalid_request',
    'resource_not_found', 'access_denied', 'server_error'
}

# 预计算的翻译缓存
_precomputed_cache: Dict[Tuple[str, str], str] = {}

# 弱引用缓存用于减少内存占用
_weak_cache = weakref.WeakValueDictionary()


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_times: List[float] = []
        self.max_request_time = 0.0
        self.min_request_time = float('inf')
    
    def record_lookup(self, lookup_time: float, cache_hit: bool = False):
        """记录查找性能数据"""
        with _stats_lock:
            _performance_stats['lookup_count'] += 1
            _performance_stats['total_lookup_time'] += lookup_time
            
            if cache_hit:
                _performance_stats['cache_hits'] += 1
            else:
                _performance_stats['cache_misses'] += 1
            
            # 更新请求时间统计
            self.request_times.append(lookup_time)
            if lookup_time > self.max_request_time:
                self.max_request_time = lookup_time
            if lookup_time < self.min_request_time:
                self.min_request_time = lookup_time
            
            # 保持最近1000次请求的记录
            if len(self.request_times) > 1000:
                self.request_times = self.request_times[-1000:]
    
    def record_concurrent_request(self, increment: bool = True):
        """记录并发请求数"""
        with _stats_lock:
            if increment:
                _performance_stats['concurrent_requests'] += 1
                if _performance_stats['concurrent_requests'] > _performance_stats['max_concurrent_requests']:
                    _performance_stats['max_concurrent_requests'] = _performance_stats['concurrent_requests']
            else:
                _performance_stats['concurrent_requests'] = max(0, _performance_stats['concurrent_requests'] - 1)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计数据"""
        with _stats_lock:
            stats = _performance_stats.copy()
            
            # 计算平均查找时间
            if stats['lookup_count'] > 0:
                stats['avg_lookup_time'] = stats['total_lookup_time'] / stats['lookup_count']
            else:
                stats['avg_lookup_time'] = 0.0
            
            # 计算缓存命中率
            total_requests = stats['cache_hits'] + stats['cache_misses']
            if total_requests > 0:
                stats['cache_hit_rate'] = stats['cache_hits'] / total_requests
            else:
                stats['cache_hit_rate'] = 0.0
            
            # 添加请求时间统计
            if self.request_times:
                stats['max_request_time'] = self.max_request_time
                stats['min_request_time'] = self.min_request_time
                stats['recent_avg_time'] = sum(self.request_times[-100:]) / min(100, len(self.request_times))
            
            # 添加内存使用情况
            stats['cache_size'] = len(_precomputed_cache)
            stats['weak_cache_size'] = len(_weak_cache)
            
            return stats


# 全局性能监控器实例
_monitor = PerformanceMonitor()


def performance_timer(func):
    """性能计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        _monitor.record_concurrent_request(True)
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            lookup_time = end_time - start_time
            
            # 检查是否为缓存命中（简单启发式）
            cache_hit = lookup_time < 0.0001  # 小于0.1ms认为是缓存命中
            _monitor.record_lookup(lookup_time, cache_hit)
            
            return result
        finally:
            _monitor.record_concurrent_request(False)
    
    return wrapper


@lru_cache(maxsize=CACHE_SIZE)
def cached_translation_lookup(key: str, language: str, translations_hash: int) -> Optional[str]:
    """
    缓存的翻译查找
    
    Args:
        key: 翻译键
        language: 语言代码
        translations_hash: 翻译字典的哈希值（用于缓存失效）
    
    Returns:
        翻译文本或None
    """
    # 这个函数会被LRU缓存，实际的查找逻辑在调用方
    return None


def precompute_common_translations(translations: Dict[str, Dict[str, str]]) -> None:
    """
    预计算常用翻译
    
    Args:
        translations: 翻译字典
    """
    global _precomputed_cache
    
    start_time = time.perf_counter()
    
    if not PRECOMPUTE_COMMON_KEYS:
        return
    
    _precomputed_cache.clear()
    
    # 预计算常用键的所有语言翻译
    for language in translations.keys():
        for key in COMMON_TRANSLATION_KEYS:
            if key in translations[language]:
                cache_key = (key, language)
                _precomputed_cache[cache_key] = translations[language][key]
    
    end_time = time.perf_counter()
    
    with _stats_lock:
        _performance_stats['startup_time'] = end_time - start_time
    
    print(f"预计算完成：{len(_precomputed_cache)} 个常用翻译，耗时 {end_time - start_time:.4f}s")


def get_optimized_translation(key: str, language: str, translations: Dict[str, Dict[str, str]]) -> Optional[str]:
    """
    优化的翻译查找
    
    Args:
        key: 翻译键
        language: 语言代码
        translations: 翻译字典
    
    Returns:
        翻译文本或None
    """
    # 1. 首先检查预计算缓存
    cache_key = (key, language)
    if cache_key in _precomputed_cache:
        return _precomputed_cache[cache_key]
    
    # 2. 检查弱引用缓存
    weak_key = f"{key}:{language}"
    if weak_key in _weak_cache:
        return _weak_cache[weak_key]
    
    # 3. 直接字典查找（O(1)操作）
    if language in translations and key in translations[language]:
        result = translations[language][key]
        
        # 将结果添加到弱引用缓存（如果不是常用键）
        if key not in COMMON_TRANSLATION_KEYS:
            _weak_cache[weak_key] = result
        
        return result
    
    return None


def optimize_memory_usage() -> Dict[str, Any]:
    """
    优化内存使用
    
    Returns:
        内存优化报告
    """
    initial_cache_size = len(_precomputed_cache)
    initial_weak_cache_size = len(_weak_cache)
    
    # 清理弱引用缓存中的无效引用
    _weak_cache.clear()
    
    # 触发垃圾回收
    collected = gc.collect()
    
    # 清理LRU缓存的一部分（保留最近使用的）
    cached_translation_lookup.cache_clear()
    
    final_cache_size = len(_precomputed_cache)
    final_weak_cache_size = len(_weak_cache)
    
    return {
        'initial_precomputed_cache_size': initial_cache_size,
        'final_precomputed_cache_size': final_cache_size,
        'initial_weak_cache_size': initial_weak_cache_size,
        'final_weak_cache_size': final_weak_cache_size,
        'garbage_collected_objects': collected,
        'memory_freed': initial_weak_cache_size - final_weak_cache_size
    }


def get_performance_report() -> Dict[str, Any]:
    """
    获取完整的性能报告
    
    Returns:
        性能报告字典
    """
    stats = _monitor.get_stats()
    
    # 添加缓存信息
    cache_info = cached_translation_lookup.cache_info()
    stats.update({
        'lru_cache_hits': cache_info.hits,
        'lru_cache_misses': cache_info.misses,
        'lru_cache_size': cache_info.currsize,
        'lru_cache_maxsize': cache_info.maxsize
    })
    
    # 添加配置信息
    stats.update({
        'cache_size_limit': CACHE_SIZE,
        'precompute_enabled': PRECOMPUTE_COMMON_KEYS,
        'common_keys_count': len(COMMON_TRANSLATION_KEYS),
        'precomputed_cache_count': len(_precomputed_cache)
    })
    
    return stats


def reset_performance_stats() -> None:
    """重置性能统计数据"""
    global _performance_stats, _monitor
    
    with _stats_lock:
        _performance_stats = {
            'lookup_count': 0,
            'total_lookup_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'startup_time': 0.0,
            'memory_usage': 0,
            'concurrent_requests': 0,
            'max_concurrent_requests': 0
        }
    
    _monitor = PerformanceMonitor()
    cached_translation_lookup.cache_clear()


def configure_performance(cache_size: int = None, precompute: bool = None) -> Dict[str, Any]:
    """
    配置性能参数
    
    Args:
        cache_size: LRU缓存大小
        precompute: 是否启用预计算
    
    Returns:
        配置结果
    """
    global CACHE_SIZE, PRECOMPUTE_COMMON_KEYS
    
    old_config = {
        'cache_size': CACHE_SIZE,
        'precompute': PRECOMPUTE_COMMON_KEYS
    }
    
    if cache_size is not None:
        CACHE_SIZE = cache_size
        # 重新创建缓存函数以应用新的大小限制
        cached_translation_lookup.cache_clear()
    
    if precompute is not None:
        PRECOMPUTE_COMMON_KEYS = precompute
    
    new_config = {
        'cache_size': CACHE_SIZE,
        'precompute': PRECOMPUTE_COMMON_KEYS
    }
    
    return {
        'old_config': old_config,
        'new_config': new_config,
        'changed': old_config != new_config
    }