# 容器诊断报告

**生成时间**: 2026-01-16  
**问题**: API 容器启动成功但请求超时

## 问题总结

✅ **已解决的问题**:
1. PostgreSQL SQL 语法错误 - 已修复（`DO $$` 替代 `DO $`）
2. Docker Desktop 未启动 - 已启动
3. 容器创建和启动 - 全部成功

❌ **当前问题**:
- API 应用启动成功，但所有 HTTP 请求都超时（包括根路径 `/`）
- 容器内部访问 `localhost:8000` 也超时
- 健康检查显示为 healthy，但实际无法响应请求

## 测试结果

### 1. 容器状态 ✅
```
所有容器都已启动并标记为 healthy:
- superinsight-postgres: Up (healthy)
- superinsight-redis: Up (healthy)  
- superinsight-neo4j: Up (healthy)
- superinsight-label-studio: Up (healthy)
- superinsight-api: Up (healthy)
```

### 2. PostgreSQL 初始化 ✅
```
- superinsight 角色已创建
- 扩展已启用 (uuid-ossp, btree_gin, pg_trgm)
- 无 SQL 语法错误
- 数据库连接正常
```

### 3. 服务连接测试 ✅
```
从 API 容器内部测试:
- PostgreSQL: ✓ 连接成功
- Redis: ✓ 连接成功
```

### 4. API 请求测试 ❌
```
所有 HTTP 请求超时:
- GET / - 超时 (3秒)
- GET /health - 超时 (5秒)
- GET /docs - 超时 (5秒)

容器内部访问也超时:
- http://localhost:8000/ - 超时 (3秒)
```

## 根本原因分析

### 可能的原因

#### 1. 应用启动时的阻塞操作 (最可能)
**症状**:
- 应用进程存在
- 端口已监听
- 但请求无响应

**可能位置**:
- 中间件中的同步阻塞操作
- 启动时的数据库迁移或初始化
- 某个服务连接超时但没有正确处理

#### 2. 事件循环阻塞
**症状**:
- Uvicorn 启动成功
- 但无法处理异步请求

**可能原因**:
- 中间件中使用了同步阻塞调用
- 数据库连接池耗尽
- 某个异步任务卡住

#### 3. 健康检查误报
**症状**:
- Docker 健康检查显示 healthy
- 但实际请求超时

**原因**:
- 健康检查可能只检查端口是否监听
- 没有真正测试应用响应能力

## API 容器日志分析

### 关键日志信息

```
1. bcrypt 版本警告 (非致命):
   (trapped) error reading bcrypt version
   AttributeError: module 'bcrypt' has no attribute '__about__'

2. Redis 连接失败 (已解决):
   Redis connection failed, using memory-only cache
   注: 后续测试显示 Redis 实际可连接

3. Import 错误:
   ImportError: cannot import name 'get_admin_user' from 'src.api.admin'
   Enhanced Admin API failed to load

4. 应用启动成功:
   INFO: Application startup complete.
   INFO: Uvicorn running on http://0.0.0.0:8000

5. 健康检查请求成功:
   INFO: 151.101.0.223:39452 - "GET /health HTTP/1.1" 200 OK
```

### 分析

1. **应用确实启动了** - Uvicorn 日志显示启动完成
2. **健康检查有时成功** - 说明应用可以响应某些请求
3. **但大部分请求超时** - 说明某个地方有阻塞

## 下一步诊断步骤

### 方案 1: 禁用中间件逐个测试

创建最小化的 app.py 版本，逐步添加中间件：

```python
# 1. 最小版本 - 无中间件
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

# 2. 逐步添加中间件
# - MonitoringMiddleware
# - CORSMiddleware  
# - AutoDesensitizationMiddleware
# - language_middleware
```

### 方案 2: 检查数据库连接池

```python
# 检查是否有连接池耗尽
docker exec superinsight-api python3 -c "
from src.database.connection import engine
print('Pool size:', engine.pool.size())
print('Checked out:', engine.pool.checkedout())
"
```

### 方案 3: 启用详细日志

修改日志级别为 DEBUG，查看请求处理详情：

```python
# 在 app.py 中添加
logging.basicConfig(level=logging.DEBUG)
```

### 方案 4: 使用 strace 追踪系统调用

```bash
# 安装 strace 到容器
docker exec -u root superinsight-api apk add strace

# 追踪 uvicorn 进程
docker exec superinsight-api strace -p $(pgrep uvicorn) -f
```

### 方案 5: 简化启动流程

临时修改 `src/app.py`，移除所有非必要组件：

```python
# 注释掉所有中间件
# 注释掉所有路由注册
# 只保留最基本的健康检查端点
```

## 推荐的修复步骤

### 步骤 1: 创建最小化测试版本

创建 `src/app_minimal.py`:

```python
from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"status": "ok", "message": "minimal app"}

@app.get("/health")
async def health():
    logger.info("Health endpoint called")
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 步骤 2: 测试最小化版本

```bash
# 修改 docker-compose.yml 中的命令
command: ["python", "-m", "uvicorn", "src.app_minimal:app", "--host", "0.0.0.0", "--port", "8000"]

# 重启容器
docker compose restart superinsight-api

# 测试
curl http://localhost:8000/
```

### 步骤 3: 逐步添加组件

如果最小化版本工作，逐步添加：
1. 数据库连接
2. CORS 中间件
3. 监控中间件
4. i18n 中间件
5. 其他中间件
6. 路由

每添加一个组件后测试，找出导致超时的具体组件。

### 步骤 4: 修复问题组件

一旦找到问题组件：
1. 检查是否有同步阻塞调用
2. 检查是否有未处理的异常
3. 检查是否有死锁或循环等待
4. 添加超时保护

## 临时解决方案

### 选项 1: 使用简化的 app.py

创建一个不包含问题中间件的版本。

### 选项 2: 增加超时时间

在所有可能阻塞的地方添加超时：

```python
import asyncio

async def with_timeout(coro, timeout=5):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout}s")
        return None
```

### 选项 3: 使用线程池处理阻塞操作

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

executor = ThreadPoolExecutor(max_workers=10)

async def run_in_thread(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)
```

## 相关文件

- `src/app.py` - 主应用文件
- `src/i18n/middleware.py` - i18n 中间件
- `src/security/auto_desensitization_middleware.py` - 脱敏中间件
- `src/system/monitoring.py` - 监控中间件
- `docker-compose.yml` - 容器配置

## 下一步行动

1. **立即**: 创建最小化测试版本 `app_minimal.py`
2. **短期**: 逐步添加组件找出问题
3. **中期**: 修复问题组件
4. **长期**: 添加全面的超时保护和错误处理

## 状态

- ⏳ **等待**: 创建最小化测试版本
- 🔍 **调查中**: 找出导致超时的具体组件
- 📋 **已记录**: 所有诊断信息和测试结果

---

**建议**: 先创建最小化版本测试，这是最快找到问题的方法。
