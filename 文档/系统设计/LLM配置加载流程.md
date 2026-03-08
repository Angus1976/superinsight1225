# LLM 配置加载流程

**文档版本**: 1.0  
**最后更新**: 2026-03-08  
**维护者**: Angus Liu

---

## 📋 概述

本文档描述 SuperInsight 平台中 LLM（大语言模型）配置的加载流程和优先级策略。

### 核心原则

**数据库配置优先，环境变量作为回退方案**

- 如果数据库中有配置，必须使用数据库配置
- 数据库配置加载失败时，不会回退到环境变量，而是抛出错误
- 只有在数据库中没有配置时，才使用环境变量
- 这确保了配置的一致性和可追溯性

---

## 🔄 配置加载流程图

```
开始
  ↓
检查数据库是否有应用绑定配置
  ↓
有配置？
  ├─ 是 → 尝试解密 API key
  │       ↓
  │     解密成功？
  │       ├─ 是 → 返回数据库配置 ✓
  │       │      (包含: API key, base_url, model, timeout, max_retries)
  │       │
  │       └─ 否 → 抛出错误 ❌
  │              错误信息: "Database has LLM configuration but failed to decrypt"
  │              提示: 检查 LLM_ENCRYPTION_KEY 环境变量
  │
  └─ 否 → 检查环境变量
          ↓
        环境变量存在？
          ├─ 是 → 返回环境变量配置 ✓
          │      (使用: OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
          │
          └─ 否 → 抛出错误 ❌
                 错误信息: "No LLM configuration found"
                 提示: 在管理控制台配置或设置环境变量
```

---

## 📊 配置优先级

### 优先级顺序

1. **数据库配置（最高优先级）**
   - 通过应用绑定（LLMApplicationBinding）关联
   - 按 priority 字段排序（数字越小优先级越高）
   - 支持租户隔离（tenant_id）
   - API key 加密存储

2. **环境变量配置（回退方案）**
   - 仅在数据库无配置时使用
   - 适用于开发环境和快速测试
   - 不支持高级特性（如超时、重试配置）

### 配置来源对比

| 特性 | 数据库配置 | 环境变量配置 |
|------|-----------|-------------|
| 优先级 | 高 | 低（仅回退） |
| 加密存储 | ✓ | ✗ |
| 租户隔离 | ✓ | ✗ |
| 优先级控制 | ✓ | ✗ |
| 超时配置 | ✓ | ✗ |
| 重试配置 | ✓ | ✗ |
| 动态更新 | ✓ | ✗（需重启） |
| 审计日志 | ✓ | ✗ |

---

## 🔧 实现细节

### 数据库配置加载

#### 步骤 1: 查询应用

```python
# 根据应用代码查询应用
stmt = select(LLMApplication).where(LLMApplication.code == application_code)
app = db.execute(stmt).scalar_one_or_none()
```

#### 步骤 2: 查询绑定

```python
# 查询应用的 LLM 配置绑定，按优先级排序
stmt = (
    select(LLMApplicationBinding)
    .options(selectinload(LLMApplicationBinding.llm_config))
    .where(
        LLMApplicationBinding.application_id == app.id,
        LLMApplicationBinding.is_active == True
    )
    .join(LLMConfiguration)
    .where(LLMConfiguration.is_active == True)
    .order_by(LLMApplicationBinding.priority.asc())
)
```

#### 步骤 3: 租户过滤

```python
# 优先使用租户配置，如果没有则使用全局配置
if tenant_id:
    tenant_stmt = stmt.where(LLMConfiguration.tenant_id == tenant_id)
    bindings = db.execute(tenant_stmt).scalars().all()
    if not bindings:
        # 回退到全局配置
        global_stmt = stmt.where(LLMConfiguration.tenant_id == None)
        bindings = db.execute(global_stmt).scalars().all()
else:
    # 直接使用全局配置
    global_stmt = stmt.where(LLMConfiguration.tenant_id == None)
    bindings = db.execute(global_stmt).scalars().all()
```

#### 步骤 4: 解密 API Key

```python
# 使用加密服务解密 API key
encryption_service = get_encryption_service()
config_data = llm_config.config_data or {}
api_key_encrypted = config_data.get("api_key_encrypted")

if api_key_encrypted:
    api_key = encryption_service.decrypt(api_key_encrypted)
else:
    api_key = config_data.get("api_key", "")
```

#### 步骤 5: 构建配置对象

```python
config = CloudConfig(
    openai_api_key=api_key,
    openai_base_url=base_url,
    openai_model=model_name,
    timeout=binding.timeout_seconds or 60,
    max_retries=binding.max_retries or 3
)
```

### 环境变量配置加载

```python
# 仅在数据库无配置时使用
api_key = os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# 特殊处理：Ollama 不需要真实 API key
if "ollama" in base_url.lower() and not api_key:
    api_key = "ollama"

config = CloudConfig(
    openai_api_key=api_key,
    openai_base_url=base_url,
    openai_model=model,
)
```

---

## 🔐 加密密钥管理

### 环境变量要求

**必需环境变量**: `LLM_ENCRYPTION_KEY`

- 用于加密/解密数据库中的 API key
- 必须在所有需要访问 LLM 配置的容器中设置
- 32 字节 Base64 编码的密钥

### 生成加密密钥

```bash
python -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())'
```

### Docker Compose 配置

```yaml
services:
  app:
    environment:
      - LLM_ENCRYPTION_KEY=${LLM_ENCRYPTION_KEY}
  
  celery-worker:
    environment:
      - LLM_ENCRYPTION_KEY=${LLM_ENCRYPTION_KEY}
```

### 错误处理

如果 `LLM_ENCRYPTION_KEY` 未设置或无效：

```
ValueError: Database has LLM configuration but failed to decrypt: 
LLM_ENCRYPTION_KEY environment variable not set. 
Generate a key with: python -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())'
```

---

## 📝 日志示例

### 成功加载数据库配置

```
INFO: Loading LLM config for application: structuring
INFO: Found database config: deepseek R1-1 (priority=1, provider=deepseek)
INFO: ✓ API key decrypted successfully (length=35)
INFO: ✓ Using database LLM config: model=deepseek-reasoner, base_url=https://api.deepseek.com/v1, priority=1
```

### 回退到环境变量

```
INFO: Loading LLM config for application: structuring
INFO: Application 'structuring' not found in database
INFO: No database config found, falling back to environment variables
INFO: ✓ Using environment variable LLM config: model=qwen2.5:1.5b, base_url=http://ollama:11434/v1
```

### 解密失败

```
INFO: Loading LLM config for application: structuring
INFO: Found database config: deepseek R1-1 (priority=1, provider=deepseek)
ERROR: Database has LLM configuration but failed to decrypt: LLM_ENCRYPTION_KEY environment variable not set
ValueError: Database has LLM configuration but failed to decrypt...
```

---

## 🎯 使用场景

### 场景 1: 生产环境（推荐）

**使用数据库配置**

- 在管理控制台配置 LLM
- 创建应用绑定
- 设置 `LLM_ENCRYPTION_KEY` 环境变量
- 系统自动使用数据库配置

**优势**:
- 配置集中管理
- 支持多租户
- API key 加密存储
- 可动态更新
- 完整审计日志

### 场景 2: 开发环境

**使用环境变量配置**

- 不配置数据库 LLM
- 在 `.env` 文件中设置环境变量
- 系统自动回退到环境变量

**优势**:
- 快速启动
- 无需数据库配置
- 适合本地测试

### 场景 3: 混合环境

**部分应用使用数据库，部分使用环境变量**

- 为关键应用配置数据库 LLM
- 其他应用使用环境变量
- 系统按应用自动选择配置源

---

## ⚠️ 注意事项

### 1. 不要混用配置

- 一旦在数据库中配置了 LLM，就不应该依赖环境变量
- 数据库配置失败不会回退到环境变量

### 2. 加密密钥管理

- `LLM_ENCRYPTION_KEY` 必须在所有容器中一致
- 密钥丢失将导致无法解密已存储的 API key
- 定期轮换密钥时需要重新加密所有 API key

### 3. 容器环境变量

- 确保 `LLM_ENCRYPTION_KEY` 在 `docker-compose.yml` 中正确配置
- 修改环境变量后需要重启容器
- Celery worker 和 app 容器都需要配置

### 4. 配置优先级

- 数据库配置的 priority 字段：数字越小优先级越高
- 相同优先级时，使用第一个找到的配置
- 租户配置优先于全局配置

---

## 🔍 故障排查

### 问题 1: 使用了环境变量而不是数据库配置

**症状**: 日志显示 "Using environment variable LLM config"

**原因**:
- 数据库中没有配置
- 应用绑定未激活
- LLM 配置未激活

**解决方案**:
1. 检查数据库中是否有 LLM 配置
2. 检查应用绑定是否存在且激活
3. 检查 LLM 配置的 `is_active` 字段

### 问题 2: 解密失败

**症状**: "Database has LLM configuration but failed to decrypt"

**原因**:
- `LLM_ENCRYPTION_KEY` 未设置
- 加密密钥不正确
- 加密密钥在容器中未传递

**解决方案**:
1. 检查 `.env` 文件中的 `LLM_ENCRYPTION_KEY`
2. 检查 `docker-compose.yml` 中的环境变量配置
3. 重启容器以应用新的环境变量

### 问题 3: 配置未生效

**症状**: 修改了数据库配置但仍使用旧配置

**原因**:
- 配置缓存未刷新
- 容器未重启
- 使用了错误的应用代码

**解决方案**:
1. 重启 Celery worker 容器
2. 检查应用代码是否正确
3. 检查配置的 priority 字段

---

## 📚 相关文档

- [LLM 配置管理 API](../API文档/LLM配置管理API.md)
- [加密服务设计](./加密服务设计.md)
- [应用绑定管理](./应用绑定管理.md)
- [Docker 部署指南](../部署指南/Docker部署指南.md)

---

## 📝 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-03-08 | 初始版本，重构配置加载流程 | Angus Liu |

---

**重要提示**: 此流程是系统的核心配置机制，任何修改都需要经过充分测试并更新本文档。
