#!/usr/bin/env python3
"""
性能优化器
优化大数据集的分析性能，实现分布式计算支持，添加缓存机制，实现异步任务处理

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 49.1
"""

import asyncio
import logging
import time
import hashlib
import pickle
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from functools import wraps
from multiprocessing import cpu_count

# Optional dependencies
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not available, using memory cache only")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, system metrics will be limited")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标"""
    execution_time: float
    memory_usage: float
    cpu_usage: float
    cache_hit_rate: float
    throughput: float
    error_count: int

@dataclass
class OptimizationConfig:
    """优化配置"""
    enable_caching: bool = True
    enable_parallel_processing: bool = True
    enable_distributed_computing: bool = False
    max_workers: int = cpu_count()
    chunk_size: int = 1000
    cache_ttl: int = 3600  # 缓存过期时间(秒)
    memory_limit_mb: int = 1024  # 内存限制(MB)

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        """初始化缓存管理器"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis不可用，使用内存缓存")
            self.cache_enabled = False
            self.memory_cache = {}
            return
            
        try:
            import redis
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=False  # 保持二进制数据
            )
            # 测试连接
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis缓存连接成功")
        except Exception as e:
            logger.warning(f"Redis连接失败，使用内存缓存: {e}")
            self.cache_enabled = False
            self.memory_cache = {}
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        # 创建参数的哈希值
        key_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        key_string = str(key_data)
        return f"bl_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            if self.cache_enabled:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    return pickle.loads(cached_data)
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"缓存获取失败: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存"""
        try:
            if self.cache_enabled:
                serialized_data = pickle.dumps(value)
                return self.redis_client.setex(key, ttl, serialized_data)
            else:
                self.memory_cache[key] = value
                # 简单的TTL实现
                asyncio.create_task(self._expire_memory_cache(key, ttl))
                return True
        except Exception as e:
            logger.error(f"缓存设置失败: {e}")
            return False
    
    async def _expire_memory_cache(self, key: str, ttl: int):
        """内存缓存过期处理"""
        await asyncio.sleep(ttl)
        self.memory_cache.pop(key, None)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            if self.cache_enabled:
                return bool(self.redis_client.delete(key))
            else:
                return self.memory_cache.pop(key, None) is not None
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            return False
    
    def clear_all(self) -> bool:
        """清空所有缓存"""
        try:
            if self.cache_enabled:
                # 只删除业务逻辑相关的缓存
                keys = self.redis_client.keys("bl_cache:*")
                if keys:
                    return bool(self.redis_client.delete(*keys))
                return True
            else:
                self.memory_cache.clear()
                return True
        except Exception as e:
            logger.error(f"缓存清空失败: {e}")
            return False

class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        """初始化异步任务管理器"""
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks = {}
        self.task_results = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
    
    async def submit_task(self, task_id: str, coro: Callable, *args, **kwargs) -> str:
        """提交异步任务"""
        if task_id in self.running_tasks:
            return f"任务 {task_id} 已在运行中"
        
        # 创建任务
        task = asyncio.create_task(self._execute_task(task_id, coro, *args, **kwargs))
        self.running_tasks[task_id] = task
        
        logger.info(f"异步任务 {task_id} 已提交")
        return task_id
    
    async def _execute_task(self, task_id: str, coro: Callable, *args, **kwargs):
        """执行任务"""
        async with self.semaphore:
            try:
                start_time = time.time()
                logger.info(f"开始执行任务 {task_id}")
                
                # 执行任务
                if asyncio.iscoroutinefunction(coro):
                    result = await coro(*args, **kwargs)
                else:
                    # 在线程池中执行同步函数
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, coro, *args, **kwargs)
                
                execution_time = time.time() - start_time
                
                # 保存结果
                self.task_results[task_id] = {
                    "status": "completed",
                    "result": result,
                    "execution_time": execution_time,
                    "completed_at": datetime.now().isoformat()
                }
                
                logger.info(f"任务 {task_id} 执行完成，耗时 {execution_time:.2f}s")
                
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}")
                self.task_results[task_id] = {
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
            finally:
                # 清理运行中的任务
                self.running_tasks.pop(task_id, None)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id in self.running_tasks:
            return {"status": "running", "task_id": task_id}
        elif task_id in self.task_results:
            return self.task_results[task_id]
        else:
            return {"status": "not_found", "task_id": task_id}
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务状态"""
        return {
            "running_tasks": list(self.running_tasks.keys()),
            "completed_tasks": {k: v for k, v in self.task_results.items() if v["status"] == "completed"},
            "failed_tasks": {k: v for k, v in self.task_results.items() if v["status"] == "failed"},
            "total_running": len(self.running_tasks),
            "total_completed": len([v for v in self.task_results.values() if v["status"] == "completed"]),
            "total_failed": len([v for v in self.task_results.values() if v["status"] == "failed"])
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            self.running_tasks.pop(task_id, None)
            
            self.task_results[task_id] = {
                "status": "cancelled",
                "cancelled_at": datetime.now().isoformat()
            }
            
            logger.info(f"任务 {task_id} 已取消")
            return True
        return False

class DistributedComputeManager:
    """分布式计算管理器"""
    
    def __init__(self, worker_nodes: List[str] = None):
        """初始化分布式计算管理器"""
        self.worker_nodes = worker_nodes or []
        self.local_executor = ProcessPoolExecutor(max_workers=cpu_count())
        self.thread_executor = ThreadPoolExecutor(max_workers=cpu_count() * 2)
    
    async def distribute_computation(self, 
                                   data: List[Any], 
                                   compute_func: Callable,
                                   chunk_size: int = 1000,
                                   use_processes: bool = True) -> List[Any]:
        """分布式计算"""
        if len(data) <= chunk_size:
            # 数据量小，直接本地计算
            return await self._local_compute(data, compute_func, use_processes)
        
        # 分块处理
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        logger.info(f"数据分为 {len(chunks)} 个块进行分布式计算")
        
        # 选择执行器
        executor = self.local_executor if use_processes else self.thread_executor
        
        # 提交任务
        loop = asyncio.get_event_loop()
        futures = []
        
        for i, chunk in enumerate(chunks):
            future = loop.run_in_executor(executor, compute_func, chunk)
            futures.append(future)
        
        # 等待所有任务完成
        results = await asyncio.gather(*futures, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        error_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"块 {i} 计算失败: {result}")
                error_count += 1
            else:
                successful_results.extend(result if isinstance(result, list) else [result])
        
        logger.info(f"分布式计算完成，成功 {len(chunks) - error_count}/{len(chunks)} 个块")
        return successful_results
    
    async def _local_compute(self, data: List[Any], compute_func: Callable, use_processes: bool) -> List[Any]:
        """本地计算"""
        executor = self.local_executor if use_processes else self.thread_executor
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(executor, compute_func, data)
            return result if isinstance(result, list) else [result]
        except Exception as e:
            logger.error(f"本地计算失败: {e}")
            return []
    
    def shutdown(self):
        """关闭执行器"""
        self.local_executor.shutdown(wait=True)
        self.thread_executor.shutdown(wait=True)

class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(self, config: OptimizationConfig = None):
        """初始化性能优化器"""
        self.config = config or OptimizationConfig()
        self.cache_manager = CacheManager() if self.config.enable_caching else None
        self.task_manager = AsyncTaskManager()
        self.compute_manager = DistributedComputeManager() if self.config.enable_distributed_computing else None
        self.performance_metrics = {}
        
        logger.info(f"性能优化器初始化完成，配置: {self.config}")
    
    def cache_result(self, ttl: int = None):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.cache_manager:
                    # 缓存未启用，直接执行
                    return await self._execute_with_metrics(func, *args, **kwargs)
                
                # 生成缓存键
                cache_key = self.cache_manager._generate_cache_key(func.__name__, args, kwargs)
                
                # 尝试从缓存获取
                cached_result = self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.info(f"缓存命中: {func.__name__}")
                    return cached_result
                
                # 执行函数并缓存结果
                result = await self._execute_with_metrics(func, *args, **kwargs)
                
                # 设置缓存
                cache_ttl = ttl or self.config.cache_ttl
                self.cache_manager.set(cache_key, result, cache_ttl)
                
                return result
            return wrapper
        return decorator
    
    async def _execute_with_metrics(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数并收集性能指标"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            memory_usage = self._get_memory_usage() - start_memory
            
            # 记录性能指标
            self.performance_metrics[func.__name__] = PerformanceMetrics(
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=0.0,  # 简化实现
                cache_hit_rate=0.0,  # 需要单独计算
                throughput=1.0 / execution_time if execution_time > 0 else 0.0,
                error_count=0
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.performance_metrics[func.__name__] = PerformanceMetrics(
                execution_time=execution_time,
                memory_usage=0.0,
                cpu_usage=0.0,
                cache_hit_rate=0.0,
                throughput=0.0,
                error_count=1
            )
            raise e
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量(MB)"""
        if not PSUTIL_AVAILABLE:
            return 0.0
            
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    async def optimize_large_dataset_analysis(self, 
                                            data: List[Dict[str, Any]], 
                                            analysis_func: Callable,
                                            chunk_size: int = None) -> Dict[str, Any]:
        """优化大数据集分析"""
        chunk_size = chunk_size or self.config.chunk_size
        
        logger.info(f"开始优化大数据集分析，数据量: {len(data)}")
        
        if len(data) <= chunk_size:
            # 小数据集，直接分析
            return await self._execute_with_metrics(analysis_func, data)
        
        # 大数据集，分块处理
        if self.compute_manager:
            # 使用分布式计算
            results = await self.compute_manager.distribute_computation(
                data, analysis_func, chunk_size, use_processes=True
            )
            
            # 合并结果
            return self._merge_analysis_results(results)
        else:
            # 使用本地并行处理
            return await self._parallel_analysis(data, analysis_func, chunk_size)
    
    async def _parallel_analysis(self, 
                                data: List[Dict[str, Any]], 
                                analysis_func: Callable,
                                chunk_size: int) -> Dict[str, Any]:
        """并行分析"""
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        
        # 创建并行任务
        tasks = []
        for i, chunk in enumerate(chunks):
            task_id = f"chunk_analysis_{i}"
            task = self.task_manager.submit_task(task_id, analysis_func, chunk)
            tasks.append(task_id)
        
        # 等待所有任务完成
        results = []
        for task_id in tasks:
            while True:
                status = self.task_manager.get_task_status(task_id)
                if status["status"] == "completed":
                    results.append(status["result"])
                    break
                elif status["status"] == "failed":
                    logger.error(f"任务 {task_id} 失败: {status.get('error')}")
                    break
                else:
                    await asyncio.sleep(0.1)  # 等待任务完成
        
        return self._merge_analysis_results(results)
    
    def _merge_analysis_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并分析结果"""
        if not results:
            return {"error": "没有有效的分析结果"}
        
        # 简单的结果合并策略
        merged_result = {
            "total_chunks": len(results),
            "successful_chunks": len([r for r in results if "error" not in r]),
            "analysis_timestamp": datetime.now().isoformat(),
            "merged_data": {}
        }
        
        # 合并数值型结果
        numeric_fields = ["total_annotations", "total_rules", "total_patterns"]
        for field in numeric_fields:
            total = sum(r.get(field, 0) for r in results if isinstance(r.get(field), (int, float)))
            if total > 0:
                merged_result["merged_data"][field] = total
        
        # 合并列表型结果
        list_fields = ["rules", "patterns", "insights"]
        for field in list_fields:
            combined_list = []
            for r in results:
                if field in r and isinstance(r[field], list):
                    combined_list.extend(r[field])
            if combined_list:
                merged_result["merged_data"][field] = combined_list
        
        # 合并字典型结果
        dict_fields = ["statistics", "metrics", "summary"]
        for field in dict_fields:
            combined_dict = {}
            for r in results:
                if field in r and isinstance(r[field], dict):
                    combined_dict.update(r[field])
            if combined_dict:
                merged_result["merged_data"][field] = combined_dict
        
        return merged_result
    
    async def submit_async_analysis(self, 
                                  task_id: str,
                                  data: List[Dict[str, Any]], 
                                  analysis_func: Callable) -> str:
        """提交异步分析任务"""
        return await self.task_manager.submit_task(
            task_id, 
            self.optimize_large_dataset_analysis,
            data, 
            analysis_func
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            "function_metrics": {
                name: {
                    "execution_time": metrics.execution_time,
                    "memory_usage": metrics.memory_usage,
                    "throughput": metrics.throughput,
                    "error_count": metrics.error_count
                }
                for name, metrics in self.performance_metrics.items()
            },
            "cache_metrics": self._get_cache_metrics(),
            "task_metrics": self.task_manager.get_all_tasks(),
            "system_metrics": self._get_system_metrics()
        }
    
    def _get_cache_metrics(self) -> Dict[str, Any]:
        """获取缓存指标"""
        if not self.cache_manager:
            return {"cache_enabled": False}
        
        return {
            "cache_enabled": True,
            "cache_type": "redis" if self.cache_manager.cache_enabled else "memory",
            # 这里可以添加更多缓存统计信息
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
            
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "cpu_count": psutil.cpu_count()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def cleanup(self):
        """清理资源"""
        if self.compute_manager:
            self.compute_manager.shutdown()
        
        # 清理缓存
        if self.cache_manager:
            self.cache_manager.clear_all()
        
        logger.info("性能优化器资源清理完成")

# 全局性能优化器实例
performance_optimizer = PerformanceOptimizer()

# 便捷的装饰器
def cached_analysis(ttl: int = 3600):
    """缓存分析结果的装饰器"""
    return performance_optimizer.cache_result(ttl)

async def optimize_analysis(data: List[Dict[str, Any]], 
                          analysis_func: Callable,
                          chunk_size: int = 1000) -> Dict[str, Any]:
    """优化分析函数的便捷接口"""
    return await performance_optimizer.optimize_large_dataset_analysis(
        data, analysis_func, chunk_size
    )