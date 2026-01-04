# i18n 系统线程安全文档

## 概述

SuperInsight 平台的 i18n 系统采用了基于 Python `contextvars` 的设计，确保在多线程和异步环境下的线程安全性。本文档详细说明了系统的线程安全特性、实现原理和使用指南。

## 线程安全特性

### 1. 上下文变量隔离

i18n 系统使用 Python 的 `ContextVar` 来管理每个请求/线程的语言设置：

```python
from contextvars import ContextVar

# 每个上下文都有独立的语言设置
_current_language: ContextVar[str] = ContextVar('language', default='zh')
```

**特性：**
- 每个线程/协程都有独立的语言上下文
- 语言设置不会在线程间相互影响
- 支持异步和同步代码
- 自动继承父上下文的设置

### 2. 并发翻译访问

翻译查找操作是线程安全的：

```python
# 多个线程可以同时安全地调用
translation = get_translation('app_name')
```

**安全保证：**
- 翻译字典是只读的，不会被修改
- 查找操作是 O(1) 的字典访问
- 缓存机制使用线程安全的数据结构
- 性能监控使用线程锁保护

### 3. 上下文复制和传播

支持上下文的复制和传播：

```python
from contextvars import copy_context

# 复制当前上下文
ctx = copy_context()

# 在复制的上下文中运行代码
result = ctx.run(some_function)
```

## 实现原理

### 上下文变量机制

```python
# 设置语言（仅影响当前上下文）
def set_language(language: str) -> None:
    _current_language.set(language)

# 获取当前上下文的语言
def get_current_language() -> str:
    return _current_language.get()
```

### 性能优化的线程安全

```python
# 使用线程锁保护性能统计
_stats_lock = threading.Lock()

def record_performance_data():
    with _stats_lock:
        # 更新性能统计数据
        _performance_stats['lookup_count'] += 1
```

### 缓存的线程安全

```python
# LRU 缓存是线程安全的
@lru_cache(maxsize=1000)
def cached_translation_lookup(key: str, language: str) -> str:
    # 缓存的翻译查找
    pass

# 弱引用缓存用于减少内存占用
_weak_cache = weakref.WeakValueDictionary()
```

## 使用指南

### 在 Web 应用中使用

在 FastAPI 等 Web 框架中，每个请求都有独立的上下文：

```python
from fastapi import FastAPI, Request
from src.i18n import set_language, get_translation

app = FastAPI()

@app.middleware("http")
async def language_middleware(request: Request, call_next):
    # 从请求中检测语言
    language = request.query_params.get('language', 'zh')
    set_language(language)
    
    # 处理请求
    response = await call_next(request)
    return response

@app.get("/api/info")
async def get_info():
    # 每个请求都有独立的语言设置
    app_name = get_translation('app_name')
    return {"app_name": app_name}
```

### 在多线程应用中使用

```python
import threading
from src.i18n import set_language, get_translation

def worker_function(thread_id: int, language: str):
    # 每个线程设置自己的语言
    set_language(language)
    
    # 翻译操作不会影响其他线程
    for i in range(100):
        translation = get_translation('app_name')
        print(f"Thread {thread_id}: {translation}")

# 启动多个线程
threads = []
for i in range(10):
    language = 'zh' if i % 2 == 0 else 'en'
    thread = threading.Thread(target=worker_function, args=(i, language))
    threads.append(thread)
    thread.start()

# 等待所有线程完成
for thread in threads:
    thread.join()
```

### 在异步代码中使用

```python
import asyncio
from src.i18n import set_language, get_translation

async def async_worker(worker_id: int, language: str):
    # 设置协程的语言
    set_language(language)
    
    # 异步操作
    await asyncio.sleep(0.1)
    
    # 翻译操作
    translation = get_translation('app_name')
    return f"Worker {worker_id}: {translation}"

async def main():
    # 启动多个协程
    tasks = []
    for i in range(10):
        language = 'zh' if i % 2 == 0 else 'en'
        task = async_worker(i, language)
        tasks.append(task)
    
    # 等待所有协程完成
    results = await asyncio.gather(*tasks)
    for result in results:
        print(result)

# 运行异步代码
asyncio.run(main())
```

## 线程安全验证

### 自动化测试

系统提供了完整的线程安全验证工具：

```python
from src.i18n.thread_safety import (
    validate_thread_safety,
    run_thread_safety_benchmark
)

# 运行线程安全验证
result = validate_thread_safety(
    context_isolation=True,
    concurrent_access=True,
    context_copying=True
)

print(f"线程安全验证: {'通过' if all(r.get('is_thread_safe', r.get('is_context_safe', False)) for r in result.values()) else '失败'}")

# 运行基准测试
benchmark_result = run_thread_safety_benchmark()
print(f"基准测试: {'通过' if benchmark_result['overall_thread_safety'] else '失败'}")
```

### 验证器使用

```python
from src.i18n.thread_safety import get_thread_safety_validator

# 获取验证器实例
validator = get_thread_safety_validator()

# 验证上下文隔离
isolation_result = validator.validate_context_variable_isolation(
    num_threads=20,
    operations_per_thread=100
)

# 验证并发访问
concurrent_result = validator.validate_concurrent_translation_access(
    num_threads=30,
    operations_per_thread=50
)

# 验证上下文复制
context_result = validator.validate_context_copying(num_contexts=15)
```

## 性能考虑

### 上下文变量开销

- 上下文变量的访问开销很小（纳秒级别）
- 上下文复制的开销也很小
- 不会显著影响应用性能

### 缓存策略

- 预计算常用翻译键以提高性能
- 使用 LRU 缓存减少重复查找
- 弱引用缓存减少内存占用

### 并发性能

- 翻译查找操作支持高并发
- 无锁设计确保最佳性能
- 性能监控不会成为瓶颈

## 最佳实践

### 1. 正确设置语言

```python
# 好的做法：在请求开始时设置语言
@app.middleware("http")
async def language_middleware(request: Request, call_next):
    language = detect_language_from_request(request)
    set_language(language)
    response = await call_next(request)
    return response

# 避免：在业务逻辑中频繁切换语言
def bad_practice():
    set_language('zh')
    name_zh = get_translation('app_name')
    set_language('en')  # 避免这样做
    name_en = get_translation('app_name')
```

### 2. 上下文传播

```python
# 好的做法：使用上下文传播
async def process_with_context():
    set_language('zh')
    
    # 上下文会自动传播到子任务
    await asyncio.create_task(sub_task())

async def sub_task():
    # 这里会继承父任务的语言设置
    translation = get_translation('app_name')
    return translation
```

### 3. 错误处理

```python
# 好的做法：处理语言设置错误
try:
    set_language(user_language)
except UnsupportedLanguageError:
    # 回退到默认语言
    set_language('zh')
```

## 故障排除

### 常见问题

1. **语言设置不生效**
   - 检查是否在正确的上下文中设置语言
   - 确认没有在其他地方覆盖语言设置

2. **翻译结果不一致**
   - 验证上下文隔离是否正常工作
   - 检查是否有全局状态污染

3. **性能问题**
   - 检查是否有过多的语言切换
   - 验证缓存是否正常工作

### 调试工具

```python
from src.i18n.thread_safety import get_context_variable_info

# 获取上下文信息
info = get_context_variable_info()
print(f"当前语言: {info['current_value']}")
print(f"上下文变量名: {info['context_var_name']}")
```

## 总结

SuperInsight 平台的 i18n 系统通过以下机制确保线程安全：

1. **上下文变量隔离** - 每个线程/协程都有独立的语言设置
2. **只读翻译数据** - 翻译字典不会被修改，确保并发安全
3. **线程安全缓存** - 使用线程安全的缓存机制
4. **性能监控保护** - 使用锁保护性能统计数据
5. **全面测试验证** - 提供完整的线程安全测试套件

这些特性确保了系统在高并发环境下的稳定性和正确性，同时保持了优秀的性能表现。