# Design Document: LLM Integration (LLM 基础能力)

## Overview

本设计文档描述 LLM Integration 模块的架构设计，该模块扩展现有 `src/ai/` 目录，实现统一的 LLM 调用接口，支持本地部署（Ollama）和云端 API（OpenAI、千问、智谱等）的动态切换。

设计原则：
- **扩展而非重写**：基于现有 `AIAnnotator` 基类和 `AnnotatorFactory` 工厂模式扩展
- **统一接口**：提供 `LLMSwitcher` 作为统一入口，屏蔽底层实现差异
- **热加载配置**：支持运行时动态切换 LLM 服务，无需重启
- **中国 LLM 优先**：原生支持千问、智谱等国产大模型

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        UI[LLM Config UI]
        API_Client[API Client]
    end
    
    subgraph API["API 层"]
        Router[/api/v1/llm]
        ConfigAPI[Config API]
        GenerateAPI[Generate API]
        HealthAPI[Health API]
    end
    
    subgraph Core["核心层"]
        Switcher[LLM Switcher]
        ConfigManager[Config Manager]
        HealthChecker[Health Checker]
    end
    
    subgraph Providers["Provider 层"]
        LocalProvider[Local Provider]
        CloudProvider[Cloud Provider]
        ChinaProvider[China LLM Provider]
    end
    
    subgraph Services["服务层"]
        Ollama[Ollama Service]
        OpenAI[OpenAI Service]
        Qwen[Qwen Service]
        Zhipu[Zhipu Service]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
        Config[Config Files]
    end
    
    UI --> API_Client
    API_Client --> Router
    Router --> ConfigAPI
    Router --> GenerateAPI
    Router --> HealthAPI
    
    ConfigAPI --> ConfigManager
    GenerateAPI --> Switcher
    HealthAPI --> HealthChecker
    
    Switcher --> LocalProvider
    Switcher --> CloudProvider
    Switcher --> ChinaProvider
    
    LocalProvider --> Ollama
    CloudProvider --> OpenAI
    ChinaProvider --> Qwen
    ChinaProvider --> Zhipu
    
    ConfigManager --> DB
    ConfigManager --> Cache
    ConfigManager --> Config
    
    HealthChecker --> Ollama
    HealthChecker --> OpenAI
    HealthChecker --> Qwen
    HealthChecker --> Zhipu
```

## Components and Interfaces

### 1. LLM Switcher (核心切换器)

**文件**: `src/ai/llm_switcher.py`

**职责**: 统一 LLM 调用入口，根据配置动态路由到具体 Provider

```python
class LLMSwitcher:
    """统一 LLM 调用接口"""
    
    async def generate(
        self, 
        prompt: str, 
        options: GenerateOptions = None,
        method: str = None  # 可选，覆盖默认方法
    ) -> LLMResponse:
        """生成文本响应"""
        pass
    
    async def embed(
        self, 
        text: str,
        method: str = None
    ) -> EmbeddingResponse:
        """生成文本向量"""
        pass
    
    async def stream_generate(
        self, 
        prompt: str, 
        options: GenerateOptions = None
    ) -> AsyncIterator[str]:
        """流式生成响应"""
        pass
    
    def switch_method(self, method: str) -> None:
        """切换默认方法"""
        pass
    
    def get_current_method(self) -> str:
        """获取当前方法"""
        pass
    
    def list_available_methods(self) -> List[str]:
        """列出可用方法"""
        pass
```

**接口定义**:

```python
class GenerateOptions(BaseModel):
    """生成选项"""
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    stop_sequences: List[str] = []
    stream: bool = False

class LLMResponse(BaseModel):
    """统一响应格式"""
    content: str
    usage: TokenUsage
    model: str
    provider: str
    latency_ms: float
    
class TokenUsage(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class EmbeddingResponse(BaseModel):
    """向量响应格式"""
    embedding: List[float]
    model: str
    dimensions: int

class LLMError(BaseModel):
    """统一错误格式"""
    error_code: str
    message: str
    provider: str
    retry_after: Optional[int] = None
```

### 2. Local Provider (本地 LLM 服务)

**文件**: `src/ai/llm_docker.py`

**职责**: 管理本地 Ollama 容器和模型

```python
class LocalLLMProvider:
    """本地 LLM Provider (Ollama)"""
    
    async def start_service(self, model_name: str) -> ServiceStatus:
        """启动 Ollama 服务并加载模型"""
        pass
    
    async def stop_service(self) -> ServiceStatus:
        """停止 Ollama 服务"""
        pass
    
    async def generate(self, prompt: str, options: GenerateOptions) -> LLMResponse:
        """调用本地模型生成"""
        pass
    
    async def list_models(self) -> List[ModelInfo]:
        """列出可用模型"""
        pass
    
    async def pull_model(self, model_name: str) -> PullStatus:
        """拉取新模型"""
        pass
    
    async def health_check(self) -> HealthStatus:
        """健康检查"""
        pass
```

**支持的本地模型**:
- Qwen (通义千问开源版)
- Llama 2/3
- Mistral
- CodeLlama
- Yi (零一万物)

### 3. Cloud Provider (云端 LLM 服务)

**文件**: `src/ai/llm_cloud.py`

**职责**: 统一云端 LLM API 调用

```python
class CloudLLMProvider:
    """云端 LLM Provider"""
    
    def __init__(self, provider_type: CloudProviderType):
        self.provider_type = provider_type
        self.client = self._create_client()
    
    async def generate(self, prompt: str, options: GenerateOptions) -> LLMResponse:
        """调用云端 API 生成"""
        pass
    
    async def stream_generate(self, prompt: str, options: GenerateOptions) -> AsyncIterator[str]:
        """流式生成"""
        pass
    
    async def validate_api_key(self, api_key: str) -> bool:
        """验证 API Key"""
        pass
    
    async def health_check(self) -> HealthStatus:
        """健康检查"""
        pass

class CloudProviderType(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
```

### 4. China LLM Adapter (中国 LLM 适配器)

**文件**: `src/ai/china_llm_adapter.py`

**职责**: 适配中国主流大模型 API

```python
class ChinaLLMAdapter:
    """中国 LLM 统一适配器"""
    
    def __init__(self, provider: ChinaLLMProvider):
        self.provider = provider
        self.adapter = self._create_adapter()
    
    async def generate(self, prompt: str, options: GenerateOptions) -> LLMResponse:
        """统一生成接口"""
        # 1. 转换请求格式
        native_request = self._to_native_format(prompt, options)
        # 2. 调用原生 API
        native_response = await self._call_native_api(native_request)
        # 3. 转换响应格式
        return self._from_native_format(native_response)
    
    def _to_native_format(self, prompt: str, options: GenerateOptions) -> Dict:
        """转换为厂商特定格式"""
        pass
    
    def _from_native_format(self, response: Dict) -> LLMResponse:
        """从厂商格式转换为统一格式"""
        pass

class ChinaLLMProvider(str, Enum):
    QWEN = "qwen"           # 阿里云通义千问
    ZHIPU = "zhipu"         # 智谱 GLM
    BAIDU = "baidu"         # 百度文心一言
    HUNYUAN = "hunyuan"     # 腾讯混元
```

**千问 (Qwen) 适配**:
```python
class QwenAdapter(ChinaLLMAdapter):
    """阿里云 DashScope API 适配器"""
    
    API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    
    def _to_native_format(self, prompt: str, options: GenerateOptions) -> Dict:
        return {
            "model": self.model_name,
            "input": {
                "messages": [{"role": "user", "content": prompt}]
            },
            "parameters": {
                "max_tokens": options.max_tokens,
                "temperature": options.temperature,
                "top_p": options.top_p
            }
        }
```

**智谱 (Zhipu) 适配**:
```python
class ZhipuAdapter(ChinaLLMAdapter):
    """智谱 AI API 适配器"""
    
    API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    
    def _to_native_format(self, prompt: str, options: GenerateOptions) -> Dict:
        return {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p
        }
```

### 5. Config Manager (配置管理器)

**文件**: `src/ai/llm_config_manager.py`

**职责**: 管理 LLM 配置的持久化和热加载

```python
class LLMConfigManager:
    """LLM 配置管理器"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
        self._config_watchers: List[Callable] = []
    
    async def get_config(self, tenant_id: str = None) -> LLMConfig:
        """获取当前配置"""
        pass
    
    async def save_config(self, config: LLMConfig, tenant_id: str = None) -> None:
        """保存配置"""
        pass
    
    async def validate_config(self, config: LLMConfig) -> ValidationResult:
        """验证配置有效性"""
        pass
    
    def watch_config_changes(self, callback: Callable) -> None:
        """注册配置变更监听器"""
        pass
    
    async def hot_reload(self) -> None:
        """热加载配置"""
        pass

class LLMConfig(BaseModel):
    """LLM 配置模型"""
    default_method: str = "local_ollama"
    local_config: LocalConfig
    cloud_config: CloudConfig
    china_config: ChinaLLMConfig
    
class LocalConfig(BaseModel):
    ollama_url: str = "http://localhost:11434"
    default_model: str = "qwen:7b"
    timeout: int = 30
    
class CloudConfig(BaseModel):
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    azure_endpoint: Optional[str] = None
    azure_api_key: Optional[str] = None
    
class ChinaLLMConfig(BaseModel):
    qwen_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None
    baidu_api_key: Optional[str] = None
    baidu_secret_key: Optional[str] = None
    hunyuan_secret_id: Optional[str] = None
    hunyuan_secret_key: Optional[str] = None
```

### 6. API Router (API 路由)

**文件**: `src/api/llm.py`

```python
router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])

@router.post("/generate")
async def generate(request: GenerateRequest) -> LLMResponse:
    """生成文本"""
    pass

@router.post("/embed")
async def embed(request: EmbedRequest) -> EmbeddingResponse:
    """生成向量"""
    pass

@router.get("/config")
async def get_config() -> LLMConfig:
    """获取配置"""
    pass

@router.put("/config")
async def update_config(config: LLMConfig) -> LLMConfig:
    """更新配置"""
    pass

@router.post("/config/test")
async def test_connection(method: str) -> HealthStatus:
    """测试连接"""
    pass

@router.get("/health")
async def health_check() -> Dict[str, HealthStatus]:
    """健康检查"""
    pass

@router.get("/methods")
async def list_methods() -> List[MethodInfo]:
    """列出可用方法"""
    pass
```

### 7. Frontend Component (前端组件)

**文件**: `frontend/src/pages/admin/LLMConfig.tsx`

```typescript
interface LLMConfigPageProps {}

const LLMConfigPage: React.FC<LLMConfigPageProps> = () => {
  // 状态管理
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [testResults, setTestResults] = useState<Record<string, HealthStatus>>({});
  
  // API 调用
  const { data, isLoading } = useQuery(['llm-config'], fetchLLMConfig);
  const updateMutation = useMutation(updateLLMConfig);
  const testMutation = useMutation(testLLMConnection);
  
  return (
    <PageContainer title="LLM 配置">
      <ProCard title="默认方法">
        <MethodSelector value={config?.default_method} onChange={handleMethodChange} />
      </ProCard>
      
      <ProCard title="本地部署 (Ollama)">
        <LocalConfigForm config={config?.local_config} onSave={handleLocalSave} />
        <TestConnectionButton method="local_ollama" onTest={handleTest} />
      </ProCard>
      
      <ProCard title="云端服务">
        <CloudConfigForm config={config?.cloud_config} onSave={handleCloudSave} />
      </ProCard>
      
      <ProCard title="中国 LLM">
        <ChinaLLMConfigForm config={config?.china_config} onSave={handleChinaSave} />
      </ProCard>
    </PageContainer>
  );
};
```

## Data Models

### 数据库模型

```python
class LLMConfiguration(Base):
    """LLM 配置表"""
    __tablename__ = "llm_configurations"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    config_data = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class LLMUsageLog(Base):
    """LLM 使用日志表"""
    __tablename__ = "llm_usage_logs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    method = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Redis 缓存结构

```
llm:config:{tenant_id}          -> JSON (LLMConfig)
llm:health:{method}             -> JSON (HealthStatus)
llm:rate_limit:{tenant_id}:{method} -> Integer (请求计数)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 统一响应格式

*For any* LLM 调用（无论使用哪种方法），返回的响应都应包含 content、usage、model 字段，且格式一致。

**Validates: Requirements 6.4, 6.5**

### Property 2: 方法路由正确性

*For any* 配置的默认方法和调用时指定的方法，LLM Switcher 应正确路由到对应的 Provider，且指定方法优先于默认方法。

**Validates: Requirements 4.1, 4.2, 6.3**

### Property 3: 超时机制

*For any* LLM 调用，如果响应时间超过配置的超时时间（本地 30 秒，云端 60 秒），系统应终止请求并返回超时错误。

**Validates: Requirements 1.3, 2.5**

### Property 4: 中国 LLM 格式转换往返

*For any* 有效的请求，经过 China LLM Adapter 转换为厂商格式后，响应应能正确转换回统一格式，且不丢失关键信息。

**Validates: Requirements 3.3, 3.4**

### Property 5: 配置热加载

*For any* 配置变更，LLM Switcher 应在 1 秒内检测到变更并加载新配置，且不中断正在进行的请求。

**Validates: Requirements 4.3, 4.4**

### Property 6: API Key 脱敏

*For any* 包含 API Key 的配置，在前端显示或 API 响应中，API Key 应被脱敏处理（只显示前 4 位和后 4 位）。

**Validates: Requirements 5.5**

### Property 7: 错误处理一致性

*For any* LLM 调用失败（网络错误、API 错误、超时等），系统应返回统一格式的错误响应，包含 error_code 和 message 字段。

**Validates: Requirements 1.4, 2.3, 6.5**

### Property 8: 限流重试策略

*For any* 中国 LLM API 返回限流错误（429），系统应实现指数退避重试，重试间隔应符合 2^n 秒模式（1s, 2s, 4s, 8s...）。

**Validates: Requirements 3.5**

## Error Handling

### 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 服务不可用 | LLM_SERVICE_UNAVAILABLE | 返回错误，建议切换方法 |
| API Key 无效 | LLM_INVALID_API_KEY | 返回错误，提示检查配置 |
| 请求超时 | LLM_TIMEOUT | 返回错误，记录日志 |
| 限流 | LLM_RATE_LIMITED | 指数退避重试 |
| 模型不存在 | LLM_MODEL_NOT_FOUND | 返回错误，列出可用模型 |
| 配置无效 | LLM_INVALID_CONFIG | 返回验证错误详情 |
| 网络错误 | LLM_NETWORK_ERROR | 重试 3 次后返回错误 |

### 错误响应格式

```python
class LLMErrorResponse(BaseModel):
    error_code: str
    message: str
    provider: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None  # 限流时的重试等待秒数
    suggestions: List[str] = []  # 建议操作
```

### 重试策略

```python
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0  # 秒
    max_delay: float = 60.0  # 秒
    exponential_base: float = 2.0
    
    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
```

## Testing Strategy

### 单元测试

**测试文件**: `tests/test_llm_integration.py`

- 测试 LLM Switcher 方法路由
- 测试配置验证逻辑
- 测试格式转换函数
- 测试错误处理逻辑
- 测试 API Key 脱敏

### 属性测试

**测试文件**: `tests/test_llm_properties.py`

使用 Hypothesis 库进行属性测试：

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1), st.sampled_from(['local_ollama', 'cloud_qwen', 'cloud_zhipu']))
def test_unified_response_format(prompt: str, method: str):
    """Property 1: 统一响应格式"""
    response = llm_switcher.generate(prompt, method=method)
    assert hasattr(response, 'content')
    assert hasattr(response, 'usage')
    assert hasattr(response, 'model')

@given(st.text(min_size=8, max_size=64))
def test_api_key_masking(api_key: str):
    """Property 6: API Key 脱敏"""
    masked = mask_api_key(api_key)
    assert len(masked) == len(api_key)
    assert masked[:4] == api_key[:4]
    assert masked[-4:] == api_key[-4:]
    assert '*' in masked
```

### 集成测试

**测试文件**: `tests/test_llm_integration_e2e.py`

- 测试完整的 API 调用流程
- 测试配置保存和加载
- 测试热加载功能
- 测试多租户隔离

### 测试配置

```python
# pytest.ini
[pytest]
markers =
    llm: LLM integration tests
    slow: slow running tests
    requires_ollama: requires Ollama service
    requires_api_key: requires cloud API key
```

## Migration Plan

### Phase 1: 核心组件 (Week 1)

1. 创建 `LLMSwitcher` 核心类
2. 实现 `LocalLLMProvider` (扩展现有 OllamaAnnotator)
3. 实现 `LLMConfigManager`
4. 添加数据库迁移

### Phase 2: 云端集成 (Week 2)

1. 实现 `CloudLLMProvider`
2. 实现 `ChinaLLMAdapter` (千问、智谱)
3. 添加 API 路由
4. 实现健康检查

### Phase 3: 前端和测试 (Week 3)

1. 实现前端配置页面
2. 编写单元测试和属性测试
3. 编写集成测试
4. 文档更新

## Dependencies

### 新增依赖

```
# requirements.txt 新增
dashscope>=1.14.0      # 阿里云 DashScope SDK
zhipuai>=2.0.0         # 智谱 AI SDK
tencentcloud-sdk-python>=3.0.0  # 腾讯云 SDK (可选)
```

### 现有依赖复用

- `httpx`: HTTP 客户端
- `pydantic`: 数据验证
- `sqlalchemy`: ORM
- `redis`: 缓存
