# Requirements Document: LLM Integration (LLM 基础能力)

## Introduction

本模块优化 `src/ai/`，实现全球/中国 LLM 对接（千问、智谱等），支持本地/云端调用 + 方法切换。核心目标是提供统一的 LLM 调用接口，支持动态切换本地部署（Ollama）和云端 API，同时兼容中国主流大模型。

## Glossary

- **LLM_Switcher**: LLM 方法切换器，负责根据配置动态选择本地或云端 LLM 服务
- **LLM_Docker_Service**: 本地 LLM 部署服务，基于 Ollama 容器化运行
- **LLM_Cloud_Service**: 云端 LLM 调用服务，支持多种 API 提供商
- **China_LLM_Adapter**: 中国 LLM 适配器，统一千问、智谱等国产大模型接口
- **LLM_Config_UI**: 前端 LLM 配置界面，提供可视化配置管理

## Requirements

### Requirement 1: 本地 LLM 部署

**User Story:** 作为系统管理员，我希望能够在本地部署 LLM 服务，以便在无网络环境或数据敏感场景下使用 AI 能力。

#### Acceptance Criteria

1. WHEN 管理员选择本地部署模式 THEN THE LLM_Docker_Service SHALL 启动 Ollama 容器并加载指定模型
2. WHEN 本地 LLM 服务启动完成 THEN THE LLM_Docker_Service SHALL 返回服务健康状态和可用模型列表
3. WHEN 调用本地 LLM 进行推理 THEN THE LLM_Docker_Service SHALL 在 30 秒内返回结果或超时错误
4. IF 本地 LLM 服务不可用 THEN THE LLM_Switcher SHALL 记录错误日志并返回服务不可用状态
5. WHEN 管理员配置本地模型 THEN THE LLM_Docker_Service SHALL 支持 Qwen、Llama、Mistral 等开源模型

### Requirement 2: 云端 LLM 调用

**User Story:** 作为系统管理员，我希望能够调用云端 LLM API，以便获得更强大的模型能力和更低的本地资源消耗。

#### Acceptance Criteria

1. WHEN 管理员配置云端 API Key THEN THE LLM_Cloud_Service SHALL 验证 API Key 有效性并存储加密凭证
2. WHEN 调用云端 LLM 进行推理 THEN THE LLM_Cloud_Service SHALL 通过 HTTPS 安全传输请求和响应
3. WHEN 云端 API 返回错误 THEN THE LLM_Cloud_Service SHALL 解析错误码并返回用户友好的错误信息
4. WHILE 云端调用进行中 THEN THE LLM_Cloud_Service SHALL 支持流式响应（Streaming）以提升用户体验
5. WHEN 云端 API 调用超时 THEN THE LLM_Cloud_Service SHALL 在 60 秒后终止请求并返回超时错误

### Requirement 3: 中国 LLM 适配

**User Story:** 作为中国用户，我希望能够使用国产大模型（千问、智谱），以便获得更好的中文理解能力和合规性。

#### Acceptance Criteria

1. WHEN 管理员选择千问（Qwen）模型 THEN THE China_LLM_Adapter SHALL 调用阿里云 DashScope API
2. WHEN 管理员选择智谱（Zhipu）模型 THEN THE China_LLM_Adapter SHALL 调用智谱 AI 开放平台 API
3. WHEN 调用中国 LLM THEN THE China_LLM_Adapter SHALL 将请求格式转换为各厂商特定格式
4. WHEN 中国 LLM 返回响应 THEN THE China_LLM_Adapter SHALL 将响应统一转换为标准格式
5. IF 中国 LLM API 返回限流错误 THEN THE China_LLM_Adapter SHALL 实现指数退避重试策略

### Requirement 4: 方法切换

**User Story:** 作为系统管理员，我希望能够动态切换 LLM 调用方法，以便根据场景选择最优方案。

#### Acceptance Criteria

1. WHEN 管理员在配置中设置默认 LLM 方法 THEN THE LLM_Switcher SHALL 加载并使用该方法
2. WHEN 调用 LLM 时指定方法参数 THEN THE LLM_Switcher SHALL 临时使用指定方法而非默认方法
3. WHEN 切换 LLM 方法 THEN THE LLM_Switcher SHALL 在 1 秒内完成切换且不中断正在进行的请求
4. WHEN 配置文件或数据库中的 LLM 配置变更 THEN THE LLM_Switcher SHALL 自动检测并热加载新配置
5. THE LLM_Switcher SHALL 支持以下方法：local_ollama、cloud_openai、cloud_qwen、cloud_zhipu

### Requirement 5: 前端配置界面

**User Story:** 作为系统管理员，我希望通过可视化界面配置 LLM，以便无需修改配置文件即可管理 LLM 设置。

#### Acceptance Criteria

1. WHEN 管理员访问 LLM 配置页面 THEN THE LLM_Config_UI SHALL 显示当前 LLM 配置状态和可用选项
2. WHEN 管理员修改 LLM 配置 THEN THE LLM_Config_UI SHALL 实时验证配置有效性并显示验证结果
3. WHEN 管理员保存 LLM 配置 THEN THE LLM_Config_UI SHALL 调用后端 API 持久化配置
4. WHEN 管理员测试 LLM 连接 THEN THE LLM_Config_UI SHALL 发送测试请求并显示连接状态
5. THE LLM_Config_UI SHALL 对 API Key 等敏感信息进行脱敏显示

### Requirement 6: 统一调用接口

**User Story:** 作为开发者，我希望有统一的 LLM 调用接口，以便业务代码无需关心底层 LLM 实现细节。

#### Acceptance Criteria

1. THE LLM_Switcher SHALL 提供统一的 `generate(prompt, options)` 接口
2. THE LLM_Switcher SHALL 提供统一的 `embed(text)` 接口用于文本向量化
3. WHEN 调用统一接口 THEN THE LLM_Switcher SHALL 自动路由到当前配置的 LLM 服务
4. THE LLM_Switcher SHALL 返回统一格式的响应，包含 content、usage、model 字段
5. WHEN 调用失败 THEN THE LLM_Switcher SHALL 返回统一格式的错误响应，包含 error_code、message 字段
