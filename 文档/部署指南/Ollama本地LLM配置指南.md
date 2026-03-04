# Ollama 本地 LLM 配置指南

**文档版本**: 1.0  
**最后更新**: 2026-03-04  
**适用场景**: 本地开发、测试环境、离线部署

---

## 概述

本指南介绍如何配置 Ollama 作为本地 LLM 提供商，使系统的所有 AI 功能可以在本地运行，无需依赖云端 API。

### 优势

- ✅ **零成本**: 无需 API 密钥，完全免费
- ✅ **隐私保护**: 数据不离开本地环境
- ✅ **离线可用**: 无需互联网连接
- ✅ **快速响应**: 本地推理，低延迟
- ✅ **开发友好**: 适合开发和测试

### 系统中的 AI 应用

本系统包含 6 个使用 LLM 的应用：

| 应用代码 | 应用名称 | 功能描述 | 使用频率 |
|---------|---------|---------|---------|
| `structuring` | 数据结构化 | 从非结构化数据推断模式和提取实体 | 高频 |
| `knowledge_graph` | 知识图谱 | 构建知识图谱，提取实体和关系 | 中频 |
| `ai_assistant` | AI 助手 | 智能对话助手服务 | 高频 |
| `semantic_analysis` | 语义分析 | 深度语义理解和文本分析 | 中频 |
| `rag_agent` | RAG 智能体 | 检索增强生成，上下文感知回答 | 高频 |
| `text_to_sql` | 文本转 SQL | 自然语言转 SQL 查询 | 中频 |

---

## 前置条件

### 1. 安装 Ollama

**macOS / Linux**:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows**:
下载安装包：https://ollama.ai/download

**验证安装**:
```bash
ollama --version
```

### 2. 拉取模型

推荐使用 Llama 3 8B 模型（平衡性能和质量）：

```bash
# 拉取 Llama 3 8B 模型
ollama pull llama3:8b

# 验证模型
ollama list
```

**其他可选模型**:
- `llama3:70b` - 更高质量，需要更多资源
- `mistral:7b` - 轻量级，速度快
- `codellama:13b` - 专注代码理解
- `qwen2:7b` - 中文优化

### 3. 启动 Ollama 服务

```bash
# 启动服务（默认端口 11434）
ollama serve
```

**验证服务**:
```bash
curl http://localhost:11434/api/tags
```

---

## 快速配置

### 方式一：使用初始化脚本（推荐）

我们提供了自动化脚本来配置所有应用：

```bash
# 1. 确保数据库已启动
docker compose up -d postgres

# 2. 运行初始化脚本
python scripts/init_ollama_bindings.py
```

**脚本功能**:
- ✅ 测试 Ollama 连接
- ✅ 创建 Ollama LLM 配置
- ✅ 为所有 6 个应用创建绑定
- ✅ 设置合适的重试和超时参数

**查看当前状态**:
```bash
python scripts/init_ollama_bindings.py --status
```

### 方式二：通过管理界面配置

1. **访问管理界面**:
   ```
   http://localhost:5173/admin/llm-config
   ```

2. **创建 LLM 配置**:
   - 点击"添加配置"
   - 配置名称：`Ollama Llama3 Local`
   - 提供商：选择 `ollama`
   - API 密钥：留空（Ollama 不需要）
   - API 基础地址：`http://localhost:11434`
   - 模型名称：`llama3:8b`
   - 点击"测试连接"验证
   - 保存配置

3. **创建应用绑定**:
   - 切换到"应用绑定"标签
   - 为每个应用点击"添加绑定"
   - 选择刚创建的 Ollama 配置
   - 设置优先级为 1（最高）
   - 保存绑定

---

## 配置参数说明

### 应用特定配置

不同应用有不同的性能要求，建议配置如下：

#### 数据结构化 (structuring)
```
优先级: 1
最大重试: 3
超时时间: 30秒
```
- 高频使用，需要快速响应
- 处理表格和文档数据

#### 知识图谱 (knowledge_graph)
```
优先级: 1
最大重试: 2
超时时间: 60秒
```
- 中频使用，需要高质量输出
- 提取复杂的实体关系

#### AI 助手 (ai_assistant)
```
优先级: 1
最大重试: 3
超时时间: 20秒
```
- 高频使用，对话场景
- 需要低延迟响应

#### 语义分析 (semantic_analysis)
```
优先级: 1
最大重试: 2
超时时间: 45秒
```
- 中频使用，深度分析
- 需要较长处理时间

#### RAG 智能体 (rag_agent)
```
优先级: 1
最大重试: 3
超时时间: 30秒
```
- 高频使用，检索增强
- 平衡速度和质量

#### 文本转 SQL (text_to_sql)
```
优先级: 1
最大重试: 2
超时时间: 30秒
```
- 中频使用，精确转换
- 需要准确的代码生成

---

## 验证配置

### 1. 检查配置状态

```bash
python scripts/init_ollama_bindings.py --status
```

**预期输出**:
```
✅ Configured Data Structuring (structuring)
   Priority 1: Ollama Llama3 Local (ollama)

✅ Configured Knowledge Graph (knowledge_graph)
   Priority 1: Ollama Llama3 Local (ollama)

✅ Configured AI Assistant (ai_assistant)
   Priority 1: Ollama Llama3 Local (ollama)

✅ Configured Semantic Analysis (semantic_analysis)
   Priority 1: Ollama Llama3 Local (ollama)

✅ Configured RAG Agent (rag_agent)
   Priority 1: Ollama Llama3 Local (ollama)

✅ Configured Text to SQL (text_to_sql)
   Priority 1: Ollama Llama3 Local (ollama)
```

### 2. 测试数据结构化功能

```bash
# 启动后端服务
python main.py

# 上传测试文件并创建结构化任务
# 通过前端界面或 API 测试
```

### 3. 查看日志

```bash
# 查看 LLM 请求日志
tail -f logs/app.log | grep "LLM"

# 查看 Ollama 服务日志
journalctl -u ollama -f  # Linux
# 或查看 Ollama 控制台输出
```

---

## 性能优化

### 1. 模型选择

根据硬件配置选择合适的模型：

| 硬件配置 | 推荐模型 | 内存需求 | 性能 |
|---------|---------|---------|------|
| 8GB RAM | `llama3:8b` | ~5GB | 良好 |
| 16GB RAM | `llama3:8b` 或 `mistral:7b` | ~5-8GB | 优秀 |
| 32GB+ RAM | `llama3:70b` | ~40GB | 最佳 |

### 2. 并发控制

Ollama 默认支持并发请求，但受硬件限制：

```bash
# 设置最大并发数（环境变量）
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_PARALLEL=4
```

### 3. GPU 加速

如果有 NVIDIA GPU：

```bash
# Ollama 自动检测并使用 GPU
# 验证 GPU 使用
nvidia-smi
```

### 4. 缓存优化

系统内置两级缓存：
- 本地内存缓存：TTL 300秒
- Redis 缓存（可选）：跨实例共享

---

## 故障排查

### 问题 1: Ollama 连接失败

**症状**: `Cannot connect to Ollama at http://localhost:11434`

**解决方案**:
```bash
# 1. 检查 Ollama 是否运行
ps aux | grep ollama

# 2. 重启 Ollama 服务
pkill ollama
ollama serve

# 3. 检查端口占用
lsof -i :11434
```

### 问题 2: 模型未找到

**症状**: `model 'llama3:8b' not found`

**解决方案**:
```bash
# 1. 列出已安装模型
ollama list

# 2. 拉取缺失模型
ollama pull llama3:8b

# 3. 验证模型
ollama run llama3:8b "Hello"
```

### 问题 3: 响应超时

**症状**: `LLM request timeout`

**解决方案**:
1. 增加超时时间（管理界面或数据库）
2. 使用更小的模型（如 `mistral:7b`）
3. 减少并发请求数
4. 检查系统资源（CPU/内存）

### 问题 4: 内存不足

**症状**: `Out of memory` 或系统卡顿

**解决方案**:
```bash
# 1. 使用更小的模型
ollama pull mistral:7b

# 2. 限制并发
export OLLAMA_MAX_LOADED_MODELS=1

# 3. 增加系统交换空间（Linux）
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 高级配置

### 多模型配置

可以配置多个 LLM 作为备份：

```
优先级 1: Ollama Llama3 (本地)
优先级 2: OpenAI GPT-3.5 (云端备份)
优先级 3: Ollama Mistral (本地备份)
```

**配置步骤**:
1. 创建多个 LLM 配置
2. 为同一应用创建多个绑定，设置不同优先级
3. 系统自动故障转移

### 自定义模型参数

在 LLM 配置的"模型参数"中设置：

```json
{
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "num_predict": 2000,
  "repeat_penalty": 1.1
}
```

### 租户特定配置

为特定租户配置专用 LLM：

1. 创建 LLM 配置时选择租户
2. 该配置仅对该租户可见
3. 优先级高于全局配置

---

## 监控和维护

### 监控指标

通过 Prometheus + Grafana 监控：

- LLM 请求数量
- 平均响应时间
- 故障转移次数
- 缓存命中率

### 日常维护

```bash
# 1. 更新模型
ollama pull llama3:8b

# 2. 清理未使用的模型
ollama rm <model_name>

# 3. 查看模型信息
ollama show llama3:8b

# 4. 检查磁盘空间
du -sh ~/.ollama/models
```

---

## 参考资源

- **Ollama 官方文档**: https://ollama.ai/docs
- **模型库**: https://ollama.ai/library
- **系统管理界面**: http://localhost:5173/admin/llm-config
- **API 文档**: http://localhost:8000/docs

---

## 下一步

1. ✅ 配置 Ollama 并绑定到所有应用
2. 📊 测试数据结构化功能
3. 🔍 监控 LLM 性能指标
4. 🚀 根据需要添加云端 LLM 作为备份
5. 📈 优化超时和重试参数

**需要帮助？** 查看 `文档/问题修复/` 目录或联系技术支持。
