# 业务逻辑功能性能优化指南

## 概述

本指南详细介绍如何优化 SuperInsight 业务逻辑提炼与智能化功能的性能，包括数据处理优化、算法调优、系统配置和监控策略。

## 性能基准

### 当前性能指标

| 数据规模 | 分析时间 | 内存使用 | CPU 使用率 |
|----------|----------|----------|------------|
| < 1,000 条 | < 5 秒 | < 512MB | < 50% |
| 1,000-10,000 条 | < 30 秒 | < 2GB | < 70% |
| 10,000-100,000 条 | < 5 分钟 | < 8GB | < 80% |
| > 100,000 条 | < 30 分钟 | < 16GB | < 90% |

### 性能目标

- **响应时间**: 95% 的请求在 30 秒内完成
- **吞吐量**: 支持每分钟 100 个分析请求
- **并发性**: 支持 50 个并发分析任务
- **可用性**: 99.9% 系统可用性

## 数据处理优化

### 1. 数据预处理优化

```python
# optimizations/data_preprocessor.py
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

class OptimizedDataPreprocessor:
    """优化的数据预处理器"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or mp.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def preprocess_batch(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """批量预处理数据"""
        # 转换为 DataFrame（更高效的批量操作）
        df = pd.DataFrame(data)
        
        # 并行处理不同的预处理任务
        futures = []
        
        # 文本清理
        if 'content' in df.columns:
            future = self.executor.submit(self._clean_text_batch, df['content'])
            futures.append(('content_cleaned', future))
        
        # 时间解析
        if 'created_at' in df.columns:
            future = self.executor.submit(self._parse_datetime_batch, df['created_at'])
            futures.append(('created_at_parsed', future))
        
        # 特征提取
        if 'content' in df.columns:
            future = self.executor.submit(self._extract_features_batch, df['content'])
            futures.append(('features', future))
        
        # 收集结果
        for column_name, future in futures:
            df[column_name] = future.result()
        
        return df
    
    def _clean_text_batch(self, texts: pd.Series) -> pd.Series:
        """批量文本清理"""
        import re
        
        # 使用向量化操作
        cleaned = texts.str.lower()
        cleaned = cleaned.str.replace(r'[^\w\s]', '', regex=True)
        cleaned = cleaned.str.replace(r'\s+', ' ', regex=True)
        cleaned = cleaned.str.strip()
        
        return cleaned
    
    def _parse_datetime_batch(self, datetimes: pd.Series) -> pd.Series:
        """批量时间解析"""
        return pd.to_datetime(datetimes, errors='coerce')
    
    def _extract_features_batch(self, texts: pd.Series) -> pd.Series:
        """批量特征提取"""
        features = []
        
        for text in texts:
            if pd.isna(text):
                features.append({})
                continue
                
            feature = {
                'length': len(text),
                'word_count': len(text.split()),
                'sentence_count': text.count('.') + text.count('!') + text.count('?'),
                'avg_word_length': np.mean([len(word) for word in text.split()]) if text.split() else 0
            }
            features.append(feature)
        
        return pd.Series(features)
```

### 2. 数据分片处理

```python
# optimizations/data_chunker.py
import math
from typing import List, Dict, Any, Iterator

class DataChunker:
    """数据分片处理器"""
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    def chunk_data(self, data: List[Dict[str, Any]]) -> Iterator[List[Dict[str, Any]]]:
        """将数据分片"""
        for i in range(0, len(data), self.chunk_size):
            yield data[i:i + self.chunk_size]
    
    def calculate_optimal_chunk_size(self, data_size: int, available_memory: int) -> int:
        """计算最优分片大小"""
        # 估算每条记录的内存使用（字节）
        estimated_record_size = 1024  # 1KB per record
        
        # 计算可以在内存中处理的记录数
        max_records_in_memory = available_memory // estimated_record_size
        
        # 确保分片大小合理
        optimal_chunk_size = min(
            max_records_in_memory // 4,  # 留出缓冲空间
            max(100, data_size // 10)    # 至少100条，最多分成10片
        )
        
        return optimal_chunk_size
    
    def adaptive_chunking(self, data: List[Dict[str, Any]], memory_limit: int) -> Iterator[List[Dict[str, Any]]]:
        """自适应分片"""
        chunk_size = self.calculate_optimal_chunk_size(len(data), memory_limit)
        
        for chunk in self.chunk_data(data):
            yield chunk
```

## 算法优化

### 1. 算法并行化

```python
# optimizations/parallel_algorithms.py
import asyncio
import numpy as np
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Dict, Any, Callable
import multiprocessing as mp

class ParallelAlgorithmExecutor:
    """并行算法执行器"""
    
    def __init__(self, max_processes: int = None, max_threads: int = None):
        self.max_processes = max_processes or mp.cpu_count()
        self.max_threads = max_threads or mp.cpu_count() * 2
        
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_processes)
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_threads)
    
    async def execute_cpu_intensive_algorithm(
        self, 
        algorithm_func: Callable,
        data_chunks: List[List[Dict[str, Any]]],
        **kwargs
    ) -> List[Any]:
        """执行 CPU 密集型算法"""
        loop = asyncio.get_event_loop()
        
        # 使用进程池处理 CPU 密集型任务
        tasks = []
        for chunk in data_chunks:
            task = loop.run_in_executor(
                self.process_executor,
                algorithm_func,
                chunk,
                kwargs
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def execute_io_intensive_algorithm(
        self,
        algorithm_func: Callable,
        data_chunks: List[List[Dict[str, Any]]],
        **kwargs
    ) -> List[Any]:
        """执行 I/O 密集型算法"""
        loop = asyncio.get_event_loop()
        
        # 使用线程池处理 I/O 密集型任务
        tasks = []
        for chunk in data_chunks:
            task = loop.run_in_executor(
                self.thread_executor,
                algorithm_func,
                chunk,
                kwargs
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    def merge_results(self, results: List[Any], merge_strategy: str = 'concatenate') -> Any:
        """合并结果"""
        if not results:
            return None
        
        if merge_strategy == 'concatenate':
            # 连接列表结果
            merged = []
            for result in results:
                if isinstance(result, list):
                    merged.extend(result)
                else:
                    merged.append(result)
            return merged
        
        elif merge_strategy == 'average':
            # 平均数值结果
            if all(isinstance(r, (int, float)) for r in results):
                return np.mean(results)
        
        elif merge_strategy == 'sum':
            # 求和数值结果
            if all(isinstance(r, (int, float)) for r in results):
                return sum(results)
        
        return results
```

### 2. 算法缓存优化

```python
# optimizations/algorithm_cache.py
import hashlib
import json
import pickle
import redis
from typing import Any, Optional, Dict
import asyncio
from functools import wraps

class AlgorithmCache:
    """算法结果缓存"""
    
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self.redis_client = redis.from_url(redis_url)
        self.default_ttl = default_ttl
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0
        }
    
    def generate_cache_key(self, algorithm_name: str, data: Any, config: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 创建数据的哈希
        if isinstance(data, list):
            data_str = json.dumps([str(item) for item in data], sort_keys=True)
        else:
            data_str = str(data)
        
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        
        # 创建配置的哈希
        config_str = json.dumps(config, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        return f"algo:{algorithm_name}:{config_hash}:{data_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存结果"""
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                self.cache_stats['hits'] += 1
                return pickle.loads(cached_data)
            else:
                self.cache_stats['misses'] += 1
                return None
        except Exception:
            self.cache_stats['misses'] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存结果"""
        try:
            ttl = ttl or self.default_ttl
            serialized_value = pickle.dumps(value)
            self.redis_client.setex(key, ttl, serialized_value)
            self.cache_stats['sets'] += 1
            return True
        except Exception:
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'sets': self.cache_stats['sets'],
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }

def cached_algorithm(cache: AlgorithmCache, ttl: Optional[int] = None):
    """算法缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(algorithm_name: str, data: Any, config: Dict[str, Any], **kwargs):
            # 生成缓存键
            cache_key = cache.generate_cache_key(algorithm_name, data, config)
            
            # 尝试获取缓存结果
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行算法
            result = await func(algorithm_name, data, config, **kwargs)
            
            # 缓存结果
            await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
```

## 系统配置优化

### 1. 数据库优化

```sql
-- database/performance_optimizations.sql

-- 创建索引优化查询性能
CREATE INDEX CONCURRENTLY idx_annotations_project_created 
ON annotations(project_id, created_at);

CREATE INDEX CONCURRENTLY idx_annotations_content_gin 
ON annotations USING gin(to_tsvector('english', content));

CREATE INDEX CONCURRENTLY idx_business_rules_project_confidence 
ON business_rules(project_id, confidence DESC);

-- 分区表优化大数据量查询
CREATE TABLE annotations_partitioned (
    LIKE annotations INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 创建月度分区
CREATE TABLE annotations_2026_01 PARTITION OF annotations_partitioned
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- 优化查询计划
ANALYZE annotations;
ANALYZE business_rules;
ANALYZE business_patterns;

-- 配置参数优化
-- postgresql.conf 建议配置
/*
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
*/
```

### 2. Redis 配置优化

```bash
# redis/redis_optimization.conf

# 内存优化
maxmemory 2gb
maxmemory-policy allkeys-lru

# 持久化优化
save 900 1
save 300 10
save 60 10000

# 网络优化
tcp-keepalive 300
timeout 0

# 性能优化
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64

# 客户端优化
tcp-backlog 511
```

### 3. 应用配置优化

```python
# config/performance_config.py
from pydantic import BaseSettings

class PerformanceSettings(BaseSettings):
    # 数据库连接池
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    # Redis 连接池
    redis_pool_size: int = 50
    redis_pool_timeout: int = 10
    
    # 算法执行
    max_concurrent_algorithms: int = 10
    algorithm_timeout: int = 300  # 5分钟
    chunk_size: int = 1000
    
    # 缓存配置
    enable_result_cache: bool = True
    cache_ttl: int = 3600
    max_cache_size: int = 1000
    
    # 异步处理
    max_workers: int = 8
    queue_size: int = 1000
    
    # 内存管理
    max_memory_usage: int = 8 * 1024 * 1024 * 1024  # 8GB
    gc_threshold: float = 0.8
    
    class Config:
        env_file = ".env"

settings = PerformanceSettings()
```

## 监控和诊断

### 1. 性能监控

```python
# monitoring/performance_monitor.py
import time
import psutil
import gc
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge
import asyncio

# 性能指标
request_duration = Histogram(
    'bl_request_duration_seconds',
    'Business logic request duration',
    ['algorithm', 'data_size_range']
)

memory_usage = Gauge(
    'bl_memory_usage_bytes',
    'Business logic memory usage'
)

cpu_usage = Gauge(
    'bl_cpu_usage_percent',
    'Business logic CPU usage'
)

active_algorithms = Gauge(
    'bl_active_algorithms',
    'Number of active algorithms'
)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        process = psutil.Process()
        
        # CPU 使用率
        cpu_percent = process.cpu_percent()
        
        # 内存使用
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # 磁盘 I/O
        io_counters = process.io_counters()
        
        metrics = {
            'cpu_percent': cpu_percent,
            'memory_rss': memory_info.rss,
            'memory_vms': memory_info.vms,
            'memory_percent': memory_percent,
            'io_read_bytes': io_counters.read_bytes,
            'io_write_bytes': io_counters.write_bytes,
            'uptime': time.time() - self.start_time
        }
        
        # 更新 Prometheus 指标
        memory_usage.set(memory_info.rss)
        cpu_usage.set(cpu_percent)
        
        return metrics
    
    def monitor_algorithm_execution(self, algorithm_name: str, data_size: int):
        """监控算法执行"""
        data_size_range = self._get_data_size_range(data_size)
        
        return AlgorithmExecutionMonitor(algorithm_name, data_size_range)
    
    def _get_data_size_range(self, size: int) -> str:
        """获取数据大小范围"""
        if size < 1000:
            return 'small'
        elif size < 10000:
            return 'medium'
        elif size < 100000:
            return 'large'
        else:
            return 'xlarge'
    
    def check_memory_pressure(self) -> bool:
        """检查内存压力"""
        memory_percent = psutil.virtual_memory().percent
        return memory_percent > 80
    
    def trigger_garbage_collection(self):
        """触发垃圾回收"""
        if self.check_memory_pressure():
            self.logger.info("内存压力过高，触发垃圾回收")
            gc.collect()

class AlgorithmExecutionMonitor:
    """算法执行监控器"""
    
    def __init__(self, algorithm_name: str, data_size_range: str):
        self.algorithm_name = algorithm_name
        self.data_size_range = data_size_range
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        active_algorithms.inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        active_algorithms.dec()
        
        request_duration.labels(
            algorithm=self.algorithm_name,
            data_size_range=self.data_size_range
        ).observe(duration)
```

### 2. 性能分析工具

```python
# tools/performance_profiler.py
import cProfile
import pstats
import io
from typing import Dict, Any, Callable
import asyncio
import time

class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.profiles = {}
    
    def profile_function(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """分析函数性能"""
        profiler = cProfile.Profile()
        
        # 开始分析
        profiler.enable()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        finally:
            end_time = time.time()
            profiler.disable()
        
        # 生成报告
        stats_stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stats_stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # 显示前20个函数
        
        return {
            'result': result,
            'success': success,
            'error': error,
            'execution_time': end_time - start_time,
            'profile_report': stats_stream.getvalue()
        }
    
    async def profile_async_function(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """分析异步函数性能"""
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        finally:
            end_time = time.time()
        
        return {
            'result': result,
            'success': success,
            'error': error,
            'execution_time': end_time - start_time
        }
    
    def benchmark_algorithm(self, algorithm_func: Callable, test_data: list, iterations: int = 10) -> Dict[str, Any]:
        """基准测试算法"""
        execution_times = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                algorithm_func(test_data)
                end_time = time.time()
                execution_times.append(end_time - start_time)
            except Exception as e:
                print(f"基准测试失败 (迭代 {i+1}): {e}")
                continue
        
        if not execution_times:
            return {'error': '所有基准测试都失败了'}
        
        import statistics
        
        return {
            'iterations': len(execution_times),
            'min_time': min(execution_times),
            'max_time': max(execution_times),
            'avg_time': statistics.mean(execution_times),
            'median_time': statistics.median(execution_times),
            'std_dev': statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        }
```

## 性能调优策略

### 1. 数据量优化策略

```python
# strategies/data_optimization.py
from typing import List, Dict, Any
import pandas as pd

class DataOptimizationStrategy:
    """数据优化策略"""
    
    @staticmethod
    def optimize_for_small_dataset(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """小数据集优化策略"""
        return {
            'chunk_size': len(data),  # 不分片
            'parallel_processing': False,
            'cache_enabled': True,
            'algorithm_timeout': 30
        }
    
    @staticmethod
    def optimize_for_medium_dataset(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """中等数据集优化策略"""
        return {
            'chunk_size': 1000,
            'parallel_processing': True,
            'max_workers': 4,
            'cache_enabled': True,
            'algorithm_timeout': 120
        }
    
    @staticmethod
    def optimize_for_large_dataset(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """大数据集优化策略"""
        return {
            'chunk_size': 5000,
            'parallel_processing': True,
            'max_workers': 8,
            'cache_enabled': True,
            'algorithm_timeout': 300,
            'memory_limit': 4 * 1024 * 1024 * 1024,  # 4GB
            'use_sampling': True,
            'sample_rate': 0.1
        }
    
    @staticmethod
    def get_optimization_strategy(data_size: int) -> Dict[str, Any]:
        """根据数据大小获取优化策略"""
        if data_size < 1000:
            return DataOptimizationStrategy.optimize_for_small_dataset([])
        elif data_size < 10000:
            return DataOptimizationStrategy.optimize_for_medium_dataset([])
        else:
            return DataOptimizationStrategy.optimize_for_large_dataset([])
```

### 2. 算法选择策略

```python
# strategies/algorithm_selection.py
from typing import Dict, Any, List

class AlgorithmSelectionStrategy:
    """算法选择策略"""
    
    # 算法复杂度映射
    ALGORITHM_COMPLEXITY = {
        'sentiment_correlation': 'O(n)',
        'keyword_cooccurrence': 'O(n²)',
        'time_series_analysis': 'O(n log n)',
        'user_behavior_analysis': 'O(n³)'
    }
    
    # 算法资源需求
    ALGORITHM_RESOURCES = {
        'sentiment_correlation': {'cpu': 'low', 'memory': 'low'},
        'keyword_cooccurrence': {'cpu': 'medium', 'memory': 'medium'},
        'time_series_analysis': {'cpu': 'high', 'memory': 'low'},
        'user_behavior_analysis': {'cpu': 'high', 'memory': 'high'}
    }
    
    @classmethod
    def select_algorithms_for_dataset(
        cls, 
        data_size: int, 
        available_memory: int,
        available_cpu: int,
        requested_algorithms: List[str]
    ) -> List[str]:
        """为数据集选择合适的算法"""
        selected_algorithms = []
        
        for algorithm in requested_algorithms:
            if cls._can_run_algorithm(algorithm, data_size, available_memory, available_cpu):
                selected_algorithms.append(algorithm)
        
        return selected_algorithms
    
    @classmethod
    def _can_run_algorithm(
        cls,
        algorithm: str,
        data_size: int,
        available_memory: int,
        available_cpu: int
    ) -> bool:
        """检查是否可以运行算法"""
        if algorithm not in cls.ALGORITHM_RESOURCES:
            return False
        
        resources = cls.ALGORITHM_RESOURCES[algorithm]
        
        # 检查内存需求
        memory_requirement = cls._estimate_memory_requirement(algorithm, data_size)
        if memory_requirement > available_memory:
            return False
        
        # 检查 CPU 需求
        cpu_requirement = cls._estimate_cpu_requirement(algorithm, data_size)
        if cpu_requirement > available_cpu:
            return False
        
        return True
    
    @classmethod
    def _estimate_memory_requirement(cls, algorithm: str, data_size: int) -> int:
        """估算内存需求"""
        base_memory = 100 * 1024 * 1024  # 100MB 基础内存
        
        if algorithm == 'sentiment_correlation':
            return base_memory + data_size * 1024  # 1KB per record
        elif algorithm == 'keyword_cooccurrence':
            return base_memory + data_size * 2048  # 2KB per record
        elif algorithm == 'time_series_analysis':
            return base_memory + data_size * 512   # 0.5KB per record
        elif algorithm == 'user_behavior_analysis':
            return base_memory + data_size * 4096  # 4KB per record
        
        return base_memory
    
    @classmethod
    def _estimate_cpu_requirement(cls, algorithm: str, data_size: int) -> int:
        """估算 CPU 需求（相对值）"""
        if algorithm == 'sentiment_correlation':
            return min(50, data_size // 100)
        elif algorithm == 'keyword_cooccurrence':
            return min(80, data_size // 50)
        elif algorithm == 'time_series_analysis':
            return min(70, data_size // 75)
        elif algorithm == 'user_behavior_analysis':
            return min(90, data_size // 25)
        
        return 50
```

## 故障排查

### 1. 性能问题诊断

```python
# diagnostics/performance_diagnostics.py
import psutil
import time
from typing import Dict, Any, List

class PerformanceDiagnostics:
    """性能诊断工具"""
    
    def diagnose_slow_performance(self) -> Dict[str, Any]:
        """诊断性能缓慢问题"""
        diagnosis = {
            'timestamp': time.time(),
            'issues': [],
            'recommendations': []
        }
        
        # 检查 CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            diagnosis['issues'].append(f"CPU 使用率过高: {cpu_percent}%")
            diagnosis['recommendations'].append("考虑增加 CPU 核心数或优化算法")
        
        # 检查内存使用
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            diagnosis['issues'].append(f"内存使用率过高: {memory.percent}%")
            diagnosis['recommendations'].append("增加内存或启用数据分片处理")
        
        # 检查磁盘 I/O
        disk_io = psutil.disk_io_counters()
        if disk_io and disk_io.read_bytes > 1024**3:  # 1GB
            diagnosis['issues'].append("磁盘读取量过大")
            diagnosis['recommendations'].append("考虑使用 SSD 或优化数据访问模式")
        
        # 检查网络连接
        net_connections = len(psutil.net_connections())
        if net_connections > 1000:
            diagnosis['issues'].append(f"网络连接数过多: {net_connections}")
            diagnosis['recommendations'].append("检查连接池配置")
        
        return diagnosis
    
    def diagnose_memory_leak(self) -> Dict[str, Any]:
        """诊断内存泄漏"""
        import gc
        
        # 强制垃圾回收
        gc.collect()
        
        # 获取对象统计
        obj_stats = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            obj_stats[obj_type] = obj_stats.get(obj_type, 0) + 1
        
        # 排序并获取前10个
        top_objects = sorted(obj_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_objects': len(gc.get_objects()),
            'top_object_types': top_objects,
            'garbage_count': len(gc.garbage)
        }
```

### 2. 性能优化建议

```python
# recommendations/performance_recommendations.py
from typing import Dict, Any, List

class PerformanceRecommendations:
    """性能优化建议"""
    
    @staticmethod
    def get_recommendations(metrics: Dict[str, Any]) -> List[str]:
        """根据指标获取优化建议"""
        recommendations = []
        
        # CPU 优化建议
        if metrics.get('cpu_percent', 0) > 70:
            recommendations.extend([
                "启用算法并行处理",
                "使用更高效的算法实现",
                "考虑使用缓存减少重复计算"
            ])
        
        # 内存优化建议
        if metrics.get('memory_percent', 0) > 70:
            recommendations.extend([
                "启用数据分片处理",
                "增加垃圾回收频率",
                "使用内存映射文件处理大数据"
            ])
        
        # I/O 优化建议
        if metrics.get('io_read_bytes', 0) > 1024**3:  # 1GB
            recommendations.extend([
                "使用数据库连接池",
                "启用查询结果缓存",
                "优化数据库索引"
            ])
        
        # 算法特定建议
        if 'algorithm_stats' in metrics:
            algo_stats = metrics['algorithm_stats']
            
            if algo_stats.get('avg_execution_time', 0) > 60:  # 1分钟
                recommendations.extend([
                    "考虑使用采样分析",
                    "启用增量分析",
                    "优化算法参数"
                ])
        
        return recommendations
    
    @staticmethod
    def get_scaling_recommendations(data_size: int, current_performance: Dict[str, Any]) -> List[str]:
        """获取扩展建议"""
        recommendations = []
        
        if data_size > 100000:  # 大数据集
            recommendations.extend([
                "考虑使用分布式处理",
                "实施数据预聚合",
                "使用专门的大数据处理框架"
            ])
        
        if current_performance.get('response_time', 0) > 300:  # 5分钟
            recommendations.extend([
                "实施异步处理",
                "使用任务队列",
                "提供进度反馈"
            ])
        
        return recommendations
```

## 最佳实践总结

### 1. 开发阶段
- **算法设计**: 选择合适的算法复杂度
- **数据结构**: 使用高效的数据结构
- **内存管理**: 及时释放不需要的对象
- **异步处理**: 使用异步编程模式

### 2. 测试阶段
- **性能测试**: 使用真实数据进行性能测试
- **压力测试**: 测试系统在高负载下的表现
- **内存测试**: 检查内存泄漏和使用情况
- **基准测试**: 建立性能基准线

### 3. 部署阶段
- **资源配置**: 根据负载配置合适的资源
- **监控设置**: 设置关键性能指标监控
- **告警配置**: 配置性能异常告警
- **扩展计划**: 准备水平和垂直扩展方案

### 4. 运维阶段
- **定期监控**: 持续监控系统性能
- **性能调优**: 根据监控数据进行调优
- **容量规划**: 根据增长趋势规划容量
- **故障处理**: 快速诊断和解决性能问题

---

**SuperInsight 业务逻辑功能性能优化指南** - 让您的系统飞速运行