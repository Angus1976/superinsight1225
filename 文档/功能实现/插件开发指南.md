# 第三方标注工具对接指南

本指南介绍如何开发和集成第三方标注工具插件到 SuperInsight 平台。

## 概述

SuperInsight 平台支持通过插件机制对接第三方标注工具，包括：
- Prodigy
- Doccano
- 自定义 ML 后端
- 其他支持 REST API 的标注工具

## 插件接口规范

### 基础接口

所有插件必须实现 `AnnotationPluginInterface` 抽象类：

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class AnnotationPluginInterface(ABC):
    """标注插件接口规范"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    async def annotate(
        self,
        tasks: List[Dict[str, Any]],
        annotation_type: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行标注"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """获取支持的标注类型"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭插件"""
        pass
```

### 数据格式

#### 输入任务格式

```json
{
  "id": "task_123",
  "data": {
    "text": "待标注的文本内容",
    "metadata": {
      "source": "document_1",
      "language": "zh"
    }
  },
  "annotation_type": "text_classification"
}
```

#### 输出结果格式

```json
{
  "task_id": "task_123",
  "annotation_data": {
    "label": "positive",
    "entities": [
      {
        "start": 0,
        "end": 5,
        "label": "PERSON",
        "text": "张三"
      }
    ]
  },
  "confidence": 0.95,
  "method_used": "llm",
  "metadata": {
    "model_version": "v1.0",
    "processing_time_ms": 150
  }
}
```

## 开发步骤

### 1. 创建插件类

```python
from src.ai.annotation_plugin_interface import AnnotationPluginInterface

class MyCustomPlugin(AnnotationPluginInterface):
    """自定义标注插件"""
    
    def __init__(self):
        self.name = "my_custom_plugin"
        self.version = "1.0.0"
        self._client = None
        self._config = {}
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件连接"""
        self._config = config
        self._client = await self._create_client(config)
        return True
    
    async def annotate(
        self,
        tasks: List[Dict[str, Any]],
        annotation_type: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行标注"""
        results = []
        for task in tasks:
            result = await self._process_task(task, annotation_type)
            results.append(result)
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """检查服务健康状态"""
        try:
            # 执行健康检查逻辑
            return {"status": "healthy", "latency_ms": 50}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def get_supported_types(self) -> List[str]:
        """返回支持的标注类型"""
        return ["text_classification", "ner", "sentiment"]
    
    async def shutdown(self) -> None:
        """清理资源"""
        if self._client:
            await self._client.close()
```

### 2. 实现格式转换

如果第三方工具使用不同的数据格式，需要实现格式转换：

```python
class FormatConverter:
    """格式转换器"""
    
    @staticmethod
    def to_external_format(task: Dict[str, Any]) -> Dict[str, Any]:
        """转换为外部工具格式"""
        return {
            "text": task["data"]["text"],
            "meta": task["data"].get("metadata", {}),
        }
    
    @staticmethod
    def from_external_format(result: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """从外部工具格式转换回来"""
        return {
            "task_id": task_id,
            "annotation_data": result.get("annotation", {}),
            "confidence": result.get("score", 0.0),
        }
```

### 3. 注册插件

```python
from src.ai.annotation_plugin_manager import get_plugin_manager

# 获取插件管理器
manager = get_plugin_manager()

# 注册插件
plugin_id = await manager.register_plugin(
    name="my_custom_plugin",
    plugin_type="rest_api",
    endpoint="http://localhost:8080/api",
    config={
        "api_key": "your_api_key",
        "timeout": 30000,
    },
    priority=10,
)
```

## 配置说明

### 插件配置项

| 配置项 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 插件名称 |
| type | string | 是 | 连接类型: rest_api, grpc, websocket, sdk |
| endpoint | string | 是 | 服务端点地址 |
| api_key | string | 否 | API 密钥 |
| timeout | number | 否 | 超时时间(毫秒)，默认 30000 |
| priority | number | 否 | 优先级，数值越大优先级越高 |
| retry_count | number | 否 | 重试次数，默认 3 |
| batch_size | number | 否 | 批处理大小，默认 100 |

### 环境变量

```bash
# 插件相关环境变量
PLUGIN_DEFAULT_TIMEOUT=30000
PLUGIN_MAX_RETRIES=3
PLUGIN_HEALTH_CHECK_INTERVAL=60
```

## 最佳实践

### 1. 错误处理

```python
async def annotate(self, tasks, annotation_type, **kwargs):
    results = []
    for task in tasks:
        try:
            result = await self._process_task(task, annotation_type)
            results.append(result)
        except Exception as e:
            # 记录错误但继续处理其他任务
            results.append({
                "task_id": task["id"],
                "error": str(e),
                "success": False,
            })
    return results
```

### 2. 批量处理

```python
async def annotate_batch(self, tasks, annotation_type, batch_size=100):
    """批量处理以提高效率"""
    results = []
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        batch_results = await self._process_batch(batch, annotation_type)
        results.extend(batch_results)
    return results
```

### 3. 缓存机制

```python
from functools import lru_cache

class CachedPlugin(AnnotationPluginInterface):
    
    @lru_cache(maxsize=1000)
    def _get_cached_result(self, task_hash: str):
        """缓存结果以避免重复计算"""
        return self._cache.get(task_hash)
```

### 4. 监控和日志

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def annotate(self, tasks, annotation_type, **kwargs):
    start_time = datetime.utcnow()
    
    try:
        results = await self._do_annotate(tasks, annotation_type)
        
        # 记录成功指标
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Annotated {len(tasks)} tasks in {duration:.2f}s")
        
        return results
    except Exception as e:
        logger.error(f"Annotation failed: {e}")
        raise
```

## 测试指南

### 单元测试

```python
import pytest
from my_plugin import MyCustomPlugin

@pytest.fixture
def plugin():
    return MyCustomPlugin()

@pytest.mark.asyncio
async def test_initialize(plugin):
    result = await plugin.initialize({"api_key": "test"})
    assert result is True

@pytest.mark.asyncio
async def test_annotate(plugin):
    await plugin.initialize({})
    
    tasks = [{"id": "1", "data": {"text": "test"}}]
    results = await plugin.annotate(tasks, "text_classification")
    
    assert len(results) == 1
    assert "task_id" in results[0]
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_plugin_integration():
    """测试插件与平台的集成"""
    manager = get_plugin_manager()
    
    # 注册插件
    plugin_id = await manager.register_plugin(
        name="test_plugin",
        plugin_type="rest_api",
        endpoint="http://localhost:8080",
    )
    
    # 测试连接
    health = await manager.test_connection(plugin_id)
    assert health["connected"] is True
    
    # 执行标注
    results = await manager.call_plugin(
        plugin_id,
        tasks=[{"id": "1", "data": {"text": "test"}}],
        annotation_type="ner",
    )
    
    assert len(results) > 0
```

## 常见问题

### Q: 如何处理网络超时？

A: 使用重试机制和合理的超时设置：

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def _call_external_api(self, data):
    async with asyncio.timeout(30):
        return await self._client.post("/annotate", json=data)
```

### Q: 如何支持多种标注类型？

A: 在 `get_supported_types()` 中声明支持的类型，并在 `annotate()` 中根据类型分发处理：

```python
def get_supported_types(self):
    return ["text_classification", "ner", "sentiment"]

async def annotate(self, tasks, annotation_type, **kwargs):
    if annotation_type == "text_classification":
        return await self._classify(tasks)
    elif annotation_type == "ner":
        return await self._extract_entities(tasks)
    elif annotation_type == "sentiment":
        return await self._analyze_sentiment(tasks)
    else:
        raise ValueError(f"Unsupported type: {annotation_type}")
```

### Q: 如何实现回退机制？

A: 使用 `ThirdPartyAdapter` 的自动回退功能：

```python
from src.ai.third_party_adapter import ThirdPartyAdapter

adapter = ThirdPartyAdapter(
    primary_plugin=my_plugin,
    fallback_plugin=backup_plugin,
    fallback_threshold=0.5,  # 当主插件成功率低于 50% 时回退
)
```

## 支持

如有问题，请联系：
- 技术支持邮箱: support@superinsight.ai
- 文档网站: https://docs.superinsight.ai
- GitHub Issues: https://github.com/superinsight/platform/issues
