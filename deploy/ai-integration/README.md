# OpenClaw AI Integration 部署指南

## 概述

本目录包含 OpenClaw AI 助手与 SuperInsight 平台集成所需的 Docker 配置和部署脚本。

## 架构

```
┌─────────────────────────────────────────┐
│      SuperInsight Platform              │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │   Backend    │  │   Governed      │ │
│  │   (FastAPI)  │◄─┤   Data          │ │
│  └──────┬───────┘  └─────────────────┘ │
└─────────┼──────────────────────────────┘
          │ API
          │
┌─────────▼──────────────────────────────┐
│      OpenClaw Services                  │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │   Gateway    │◄─┤     Agent       │ │
│  │   (路由)     │  │   (技能执行)    │ │
│  └──────────────┘  └─────────────────┘ │
└─────────────────────────────────────────┘
```

## 组件说明

### OpenClaw Gateway
- **端口**: 3000
- **功能**: 多渠道消息路由和通信
- **健康检查**: `http://localhost:3000/health`
- **API 信息**: `http://localhost:3000/api/info`

### OpenClaw Agent
- **端口**: 8081 (映射到容器内的 8080)
- **功能**: 技能执行和对话管理
- **健康检查**: `http://localhost:8081/health`
- **API 信息**: `http://localhost:8081/api/info`
- **技能列表**: `http://localhost:8081/api/skills`

## 快速开始

### 1. 环境配置

确保 `.env` 文件包含以下配置：

```bash
# OpenClaw API Configuration
OPENCLAW_API_KEY=dev-test-api-key-12345
TENANT_ID=default-tenant

# OpenClaw Agent Configuration
OPENCLAW_AGENT_NAME=SuperInsight Assistant
OPENCLAW_AGENT_DESCRIPTION=AI assistant for governed data access

# LLM Configuration
OPENCLAW_LLM_PROVIDER=ollama
OPENCLAW_LLM_MODEL=llama2
OPENCLAW_LLM_API_URL=http://ollama:11434

# Language Configuration
OPENCLAW_USER_LANGUAGE=zh-CN
OPENCLAW_LOCALE=zh-CN
```

### 2. 构建镜像

```bash
docker compose -f docker-compose.yml -f docker-compose.ai-integration.yml build openclaw-gateway openclaw-agent
```

### 3. 启动服务

```bash
docker compose -f docker-compose.yml -f docker-compose.ai-integration.yml up -d openclaw-gateway openclaw-agent
```

### 4. 验证部署

运行集成测试脚本：

```bash
./scripts/test_openclaw_integration.sh
```

或手动测试：

```bash
# 测试 Gateway
curl http://localhost:3000/health

# 测试 Agent
curl http://localhost:8081/health

# 测试技能执行
curl -X POST http://localhost:8081/api/skills/execute \
  -H "Content-Type: application/json" \
  -d '{"skill_name": "superinsight-data-query", "parameters": {"query": "测试"}}'
```

## 服务管理

### 查看日志

```bash
# Gateway 日志
docker logs superinsight-openclaw-gateway

# Agent 日志
docker logs superinsight-openclaw-agent

# 实时跟踪日志
docker logs -f superinsight-openclaw-agent
```

### 重启服务

```bash
docker compose -f docker-compose.yml -f docker-compose.ai-integration.yml restart openclaw-gateway openclaw-agent
```

### 停止服务

```bash
docker compose -f docker-compose.yml -f docker-compose.ai-integration.yml stop openclaw-gateway openclaw-agent
```

### 删除服务

```bash
docker compose -f docker-compose.yml -f docker-compose.ai-integration.yml down openclaw-gateway openclaw-agent
```

## 技能开发

### SuperInsight 数据查询技能

当前实现的技能：

- **名称**: `superinsight-data-query`
- **描述**: 查询 SuperInsight 治理数据
- **状态**: 活跃

### 执行技能示例

```bash
curl -X POST http://localhost:8081/api/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "superinsight-data-query",
    "parameters": {
      "query": "获取数据质量报告",
      "filters": {
        "dataset": "customer_data",
        "quality_score": 0.8
      }
    }
  }'
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENCLAW_API_KEY` | SuperInsight API 密钥 | - |
| `TENANT_ID` | 租户 ID | - |
| `OPENCLAW_LLM_PROVIDER` | LLM 提供商 | `ollama` |
| `OPENCLAW_LLM_MODEL` | LLM 模型 | `llama2` |
| `OPENCLAW_USER_LANGUAGE` | 用户语言 | `zh-CN` |
| `OPENCLAW_LOG_LEVEL` | 日志级别 | `info` |

### 数据卷

- `openclaw_config`: 配置文件
- `openclaw_skills`: 技能代码
- `openclaw_memory`: 对话记忆
- `openclaw_logs`: 日志文件

## 故障排查

### Gateway 无法启动

1. 检查端口 3000 是否被占用
2. 查看日志: `docker logs superinsight-openclaw-gateway`
3. 验证环境变量配置

### Agent 无法连接 Gateway

1. 确认 Gateway 已启动: `docker ps | grep openclaw-gateway`
2. 检查网络连接: `docker network inspect superinsight_network`
3. 验证 `GATEWAY_URL` 环境变量

### 技能执行失败

1. 检查 SuperInsight API 是否可访问
2. 验证 API 密钥配置
3. 查看 Agent 日志获取详细错误信息

## 监控

### 健康检查

所有服务都提供健康检查端点：

```bash
# Gateway
curl http://localhost:3000/health

# Agent
curl http://localhost:8081/health
```

### 容器状态

```bash
docker ps --filter "name=openclaw"
```

### 资源使用

```bash
docker stats superinsight-openclaw-gateway superinsight-openclaw-agent
```

## 生产部署建议

1. **安全性**
   - 使用强 API 密钥
   - 启用 HTTPS
   - 配置防火墙规则

2. **性能**
   - 根据负载调整容器资源限制
   - 配置日志轮转
   - 使用持久化存储

3. **监控**
   - 集成 Prometheus 指标
   - 配置告警规则
   - 定期检查健康状态

4. **备份**
   - 定期备份配置文件
   - 备份对话记忆数据
   - 保存技能代码版本

## 相关文档

- [AI Integration Spec](.kiro/specs/ai-application-integration/)
- [Docker Compose 配置](../../docker-compose.ai-integration.yml)
- [测试脚本](../../scripts/test_openclaw_integration.sh)

## 支持

如有问题，请查看：
- 项目文档: `文档/`
- 问题修复: `文档/问题修复/`
- GitHub Issues
