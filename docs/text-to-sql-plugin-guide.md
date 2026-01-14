# Text-to-SQL 插件开发指南

本指南介绍如何开发和集成第三方 Text-to-SQL 工具插件。

## 概述

SuperInsight 平台支持通过插件机制集成第三方专业 Text-to-SQL 工具，如 Vanna.ai、DIN-SQL、DAIL-SQL 等。

## 插件接口规范

所有插件必须实现 `PluginInterface` 抽象类：

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.text_to_sql.schemas import SQLGenerationResult, PluginInfo
from src.text_to_sql.schema_analyzer import DatabaseSchema

class PluginInterface(ABC):
    """第三方工具插件接口规范"""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass
    
    @abstractmethod
    def to_native_format(self, query: str, schema: Optional[DatabaseSchema]) -> Dict[str, Any]:
        """将请求转换为工具特定格式"""
        pass
    
    @abstractmethod
    async def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        pass
    
    @abstractmethod
    def from_native_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        """从工具格式转换为统一格式"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
```

## 创建插件

### 1. 创建插件类

```python
from src.text_to_sql.plugin_interface import PluginInterface, PluginInfo
from src.text_to_sql.schemas import SQLGenerationResult, ConnectionType
import aiohttp

class MyTextToSQLPlugin(PluginInterface):
    """自定义 Text-to-SQL 插件"""
    
    def __init__(self, endpoint: str, api_key: str = None, timeout: int = 30):
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self._is_healthy = False
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="my-text-to-sql",
            version="1.0.0",
            description="My custom Text-to-SQL plugin",
            connection_type=ConnectionType.REST_API,
            supported_db_types=["postgresql", "mysql"],
            is_healthy=self._is_healthy,
            is_enabled=True,
        )
    
    def to_native_format(self, query: str, schema=None) -> dict:
        """转换为工具特定的请求格式"""
        request = {
            "question": query,
            "options": {"max_tokens": 500},
        }
        
        if schema:
            request["schema"] = {
                "tables": [
                    {"name": t["name"], "columns": t["columns"]}
                    for t in schema.tables
                ]
            }
        
        return request
    
    async def call(self, request: dict) -> dict:
        """调用第三方工具 API"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint}/generate",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                return await response.json()
    
    def from_native_format(self, response: dict) -> SQLGenerationResult:
        """从工具响应转换为统一格式"""
        return SQLGenerationResult(
            sql=response.get("sql", ""),
            method_used=f"third_party:{self.get_info().name}",
            confidence=response.get("confidence", 0.0),
            execution_time_ms=response.get("latency_ms", 0.0),
            metadata=response.get("metadata", {}),
        )
    
    async def health_check(self) -> bool:
        """检查服务健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    self._is_healthy = response.status == 200
                    return self._is_healthy
        except Exception:
            self._is_healthy = False
            return False
```

### 2. 注册插件

通过 API 注册插件：

```bash
curl -X POST http://localhost:8000/api/v1/text-to-sql/plugins \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-text-to-sql",
    "connection_type": "rest_api",
    "endpoint": "http://localhost:8080/api",
    "api_key": "your-api-key",
    "timeout": 30,
    "enabled": true
  }'
```

或通过前端管理界面添加。

## 支持的连接类型

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| `rest_api` | REST API 调用 | 云服务、远程部署 |
| `grpc` | gRPC 调用 | 高性能场景 |
| `local_sdk` | 本地 SDK 调用 | 本地部署、离线使用 |

## 请求/响应格式

### 统一请求格式

```json
{
  "query": "查询所有用户的订单数量",
  "schema": {
    "tables": [
      {
        "name": "users",
        "columns": [
          {"name": "id", "data_type": "integer"},
          {"name": "name", "data_type": "varchar"}
        ]
      }
    ]
  },
  "db_type": "postgresql"
}
```

### 统一响应格式

```json
{
  "sql": "SELECT u.name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name",
  "method_used": "third_party:my-plugin",
  "confidence": 0.85,
  "execution_time_ms": 150.0,
  "metadata": {
    "model": "custom-model",
    "tokens_used": 100
  }
}
```

## 错误处理

插件应正确处理以下错误情况：

1. **连接超时**: 返回空结果，触发回退机制
2. **认证失败**: 抛出 `AuthenticationError`
3. **格式错误**: 抛出 `ValidationError`
4. **服务不可用**: 健康检查返回 `False`

## 最佳实践

1. **实现健康检查**: 定期检查服务可用性
2. **设置合理超时**: 避免长时间阻塞
3. **记录日志**: 便于问题排查
4. **处理重试**: 对临时错误进行重试
5. **保护 API Key**: 不要在日志中暴露敏感信息

## 示例插件

参考 `src/text_to_sql/adapters/rest_adapter.py` 中的 REST API 适配器实现。

## API 参考

### 插件管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/text-to-sql/plugins` | GET | 列出所有插件 |
| `/api/v1/text-to-sql/plugins` | POST | 注册新插件 |
| `/api/v1/text-to-sql/plugins/{name}` | PUT | 更新插件配置 |
| `/api/v1/text-to-sql/plugins/{name}` | DELETE | 删除插件 |
| `/api/v1/text-to-sql/plugins/{name}/enable` | POST | 启用插件 |
| `/api/v1/text-to-sql/plugins/{name}/disable` | POST | 禁用插件 |
| `/api/v1/text-to-sql/plugins/health` | GET | 检查所有插件健康状态 |
| `/api/v1/text-to-sql/plugins/{name}/health` | GET | 检查单个插件健康状态 |

## 支持

如有问题，请联系技术支持或查阅 API 文档。
