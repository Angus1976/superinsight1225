# 生产环境：OpenClaw 与 LLM 配置说明

## 1. 优先级总览（与本项目代码一致）

| 范围 | 顺序 |
|------|------|
| **通用 LLM**（直连 / Switcher / 多数业务路径） | `llm_configurations` 表中 `config_data`（租户 → 若缺省再考虑全局行）→ **环境变量兜底**（`merge_llm_config_with_env_defaults`） |
| **OpenClaw 网关 URL / Core / Agent / Token** | `llm_configurations.config_data.openclaw`（租户合并全局）→ **`AIGateway.configuration.network_settings`**（仅网关 Base URL 在库表未写时作为回退）→ **环境变量** → 内置默认 |

生产部署建议：**敏感值**（Token、API Key）使用密钥管理（Vault、K8s Secret）注入为环境变量，或写入数据库并由应用加密存储；**不要在镜像中硬编码**。

## 2. 后端（FastAPI）相关环境变量

| 变量 | 含义 | 典型生产值 |
|------|------|------------|
| `OPENCLAW_GATEWAY_BASE_URL` | 后端访问 **OpenClaw 兼容网关** 的根 URL（无路径） | `http://openclaw-gateway:3000`（K8s 内 DNS） |
| `OPENCLAW_CORE_URL` | 供 **兼容网关容器** 转发到官方 Core；后端亦可通过 `llm_configurations` 的 `openclaw.core_url` 覆盖 | `http://openclaw-core:18789` |
| `OPENCLAW_GATEWAY_TOKEN` | 调用 Core `POST /v1/chat/completions` 的 **Bearer**，须与 Core 配置 `gateway.auth.token` **一致** | 长随机串（与 Core `openclaw.json` 同步） |
| `OPENCLAW_AGENT_URL` | Agent 根 URL（种子网关配置 `agent_url` 时的回退） | `http://openclaw-agent:8080` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 本地 Ollama；库表未配置 `local_config` 时使用 | 按集群内服务名 |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 云端 OpenAI 兼容接口；库表未填密钥时回退 | 按供应商文档 |

## 3. Docker Compose（`docker-compose.ai-integration.yml`）中的对应项

以下在 **compose 环境** 中注入到 `openclaw-core`、`openclaw-gateway`，需与生产密钥一致：

```yaml
# OpenClaw Core（官方镜像）
OPENCLAW_GATEWAY_TOKEN=${OPENCLAW_GATEWAY_TOKEN:-...}

# 兼容网关（Node）
OPENCLAW_CORE_URL=${OPENCLAW_CORE_URL:-http://openclaw-core:18789}
OPENCLAW_GATEWAY_TOKEN=${OPENCLAW_GATEWAY_TOKEN:-...}
AGENT_URL=${AGENT_URL:-http://openclaw-agent:8080}
```

主应用 `app` 服务建议同步设置：

```yaml
OPENCLAW_GATEWAY_BASE_URL=${OPENCLAW_GATEWAY_BASE_URL:-http://openclaw-gateway:3000}
```

（若未设置，代码默认亦为 `http://openclaw-gateway:3000`。）

## 4. 数据库 `llm_configurations.config_data` 结构（可选）

在 JSON 中增加 **`openclaw`** 对象后，**优先于** 同名的环境变量（网关 Base URL 仍低于该对象中的显式 `gateway_base_url`）：

```json
{
  "default_method": "local_ollama",
  "local_config": { "ollama_url": "http://ollama:11434", "default_model": "qwen2.5vl:7b" },
  "openclaw": {
    "gateway_base_url": "http://openclaw-gateway:3000",
    "core_url": "http://openclaw-core:18789",
    "gateway_token": "与 Core gateway.auth.token 一致",
    "agent_url": "http://openclaw-agent:8080"
  }
}
```

租户级行覆盖全局行中缺失字段。

## 5. 运维注意

- **兼容网关**与 **Grafana** 默认均曾使用宿主机 `3000`；本仓库将网关映射为 **`3001:3000`**（`OPENCLAW_GATEWAY_HOST_PORT`），避免端口冲突。
- **Node 网关进程**仅在启动时读取环境变量；若仅改 DB 而不重启网关，需重启网关容器或通过 DB 配置让 **后端** 使用新 URL（后端每次请求会读库）。
- Core 首次启动可能在 `openclaw.json` 中生成 token；生产环境应 **固定 token** 并同步到 `OPENCLAW_GATEWAY_TOKEN` 与数据库（若使用）。

更多组件说明见同目录 [README.md](./README.md)。
