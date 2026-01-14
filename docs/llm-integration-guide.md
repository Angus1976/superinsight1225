# LLM Integration Guide

## Overview

The LLM Integration module provides a unified interface for accessing multiple Large Language Model providers, including local Ollama instances, cloud services (OpenAI, Azure), and Chinese LLM services (Qwen, Zhipu, Baidu, Hunyuan).

## Features

- **Unified API**: Single interface for all LLM providers
- **Hot Configuration Reload**: Update configurations without service restart
- **Multi-tenant Support**: Isolated configurations per tenant
- **Health Monitoring**: Real-time health checks for all providers
- **API Key Security**: Automatic masking of sensitive credentials
- **Error Handling**: Comprehensive error handling with retry logic
- **Performance Monitoring**: Latency and usage tracking

## Quick Start

### 1. Configuration

Access the LLM configuration page at `/admin/llm-config` (admin access required).

#### Local Ollama Setup
```yaml
local_config:
  ollama_url: "http://localhost:11434"
  default_model: "llama2"
  timeout: 30
  max_retries: 3
```

#### Cloud Provider Setup
```yaml
cloud_config:
  # OpenAI
  openai_api_key: "sk-your-api-key"
  openai_base_url: "https://api.openai.com/v1"
  openai_model: "gpt-3.5-turbo"
  
  # Azure OpenAI
  azure_endpoint: "https://your-resource.openai.azure.com/"
  azure_api_key: "your-azure-key"
  azure_deployment: "gpt-35-turbo"
  azure_api_version: "2023-12-01-preview"
  
  timeout: 60
  max_retries: 3
```

#### Chinese LLM Setup
```yaml
china_config:
  # Qwen (通义千问)
  qwen_api_key: "your-qwen-key"
  qwen_model: "qwen-turbo"
  
  # Zhipu GLM (智谱)
  zhipu_api_key: "your-zhipu-key"
  zhipu_model: "glm-4"
  
  # Baidu ERNIE (文心一言)
  baidu_api_key: "your-baidu-key"
  baidu_secret_key: "your-baidu-secret"
  baidu_model: "ernie-bot-turbo"
  
  # Tencent Hunyuan (腾讯混元)
  hunyuan_secret_id: "your-secret-id"
  hunyuan_secret_key: "your-secret-key"
  hunyuan_model: "hunyuan-lite"
  
  timeout: 60
  max_retries: 3
```

### 2. API Usage

#### Text Generation
```python
from src.ai.llm_switcher import get_initialized_switcher
from src.ai.llm_schemas import GenerateRequest

# Get the LLM switcher
switcher = await get_initialized_switcher()

# Generate text
request = GenerateRequest(
    prompt="Explain machine learning in simple terms",
    options={
        "max_tokens": 200,
        "temperature": 0.7
    },
    method="local_ollama"  # Optional: specify method
)

response = await switcher.generate(request)
print(response.content)
```

#### REST API
```bash
# Generate text
curl -X POST "http://localhost:8000/api/v1/llm/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain machine learning",
    "options": {
      "max_tokens": 200,
      "temperature": 0.7
    },
    "method": "local_ollama"
  }'

# Get health status
curl "http://localhost:8000/api/v1/llm/health"

# List available methods
curl "http://localhost:8000/api/v1/llm/methods"
```

## Configuration Management

### Hot Reload
Configuration changes can be applied without restarting the service:

```python
from src.ai.llm_config_manager import get_config_manager

config_manager = await get_config_manager()
await config_manager.hot_reload()
```

### Multi-tenant Configuration
Each tenant can have isolated LLM configurations:

```python
# Save tenant-specific config
await config_manager.save_config(config, tenant_id="tenant_123")

# Get tenant-specific config
config = await config_manager.get_config(tenant_id="tenant_123")
```

### Configuration Validation
All configurations are validated before saving:

```python
validation_result = await config_manager.validate_config(config)
if not validation_result.valid:
    print("Errors:", validation_result.errors)
    print("Warnings:", validation_result.warnings)
```

## Provider-Specific Setup

### Local Ollama
1. Install Ollama: https://ollama.ai/
2. Start Ollama service: `ollama serve`
3. Pull models: `ollama pull llama2`
4. Configure URL in admin panel

### OpenAI
1. Get API key from https://platform.openai.com/
2. Configure API key in admin panel
3. Test connection

### Azure OpenAI
1. Create Azure OpenAI resource
2. Deploy a model (e.g., gpt-35-turbo)
3. Get endpoint and API key
4. Configure in admin panel

### Chinese LLMs

#### Qwen (通义千问)
1. Register at https://dashscope.aliyun.com/
2. Get API key
3. Configure in admin panel

#### Zhipu GLM
1. Register at https://open.bigmodel.cn/
2. Get API key
3. Configure in admin panel

#### Baidu ERNIE
1. Register at https://cloud.baidu.com/
2. Create application and get API key + Secret key
3. Configure in admin panel

#### Tencent Hunyuan
1. Register at https://cloud.tencent.com/
2. Get Secret ID and Secret Key
3. Configure in admin panel

## Health Monitoring

The system continuously monitors the health of all configured providers:

```python
# Get health status for all providers
health_status = await switcher.get_health_status()

# Get health for specific provider
health = await switcher.get_health_status("local_ollama")
```

Health status includes:
- `available`: Whether the provider is accessible
- `latency_ms`: Response latency in milliseconds
- `model`: Currently active model
- `error`: Error message if unavailable
- `last_check`: Timestamp of last health check

## Error Handling

The system provides comprehensive error handling:

### Timeout Handling
- Local providers: 30-second default timeout
- Cloud providers: 60-second default timeout
- Configurable per provider

### Retry Logic
- Exponential backoff: 1s, 2s, 4s, 8s...
- Maximum 5 retries for Chinese LLMs
- Configurable retry counts

### Error Types
- `TIMEOUT_ERROR`: Request timeout
- `API_KEY_ERROR`: Invalid or missing API key
- `RATE_LIMIT_ERROR`: Rate limit exceeded
- `MODEL_ERROR`: Model not available
- `NETWORK_ERROR`: Network connectivity issues

## Performance Optimization

### Caching
- Configuration caching with Redis
- Hot reload without service interruption
- Tenant-specific cache isolation

### Connection Pooling
- Persistent connections for cloud providers
- Connection reuse for better performance

### Monitoring
- Request latency tracking
- Usage statistics
- Error rate monitoring

## Security

### API Key Protection
- Automatic masking in responses
- Secure storage in database
- Environment variable support

### Access Control
- Admin-only configuration access
- Role-based API access
- Tenant isolation

### Audit Logging
- Configuration changes logged
- API usage tracked
- Security events monitored

## Troubleshooting

### Common Issues

#### Ollama Connection Failed
```
Error: Connection refused to http://localhost:11434
```
**Solution**: Ensure Ollama is running: `ollama serve`

#### OpenAI API Key Invalid
```
Error: Invalid API key provided
```
**Solution**: Check API key format and permissions

#### Chinese LLM Rate Limited
```
Error: Rate limit exceeded, retry after 60 seconds
```
**Solution**: Automatic retry with exponential backoff

### Debug Mode
Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger("src.ai.llm").setLevel(logging.DEBUG)
```

### Health Check Endpoints
```bash
# Overall system health
curl "http://localhost:8000/health"

# LLM-specific health
curl "http://localhost:8000/api/v1/llm/health"

# Test specific provider
curl -X POST "http://localhost:8000/api/v1/llm/config/test" \
  -H "Content-Type: application/json" \
  -d '{"method": "local_ollama"}'
```

## API Reference

### Endpoints

#### POST /api/v1/llm/generate
Generate text using configured LLM.

**Request:**
```json
{
  "prompt": "string",
  "options": {
    "max_tokens": 100,
    "temperature": 0.7,
    "top_p": 1.0,
    "stop_sequences": ["\\n"]
  },
  "method": "local_ollama",
  "model": "llama2",
  "system_prompt": "You are a helpful assistant"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "content": "Generated text response",
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 20,
      "total_tokens": 30
    },
    "model": "llama2",
    "provider": "local_ollama",
    "latency_ms": 150,
    "finish_reason": "stop"
  }
}
```

#### GET /api/v1/llm/config
Get current LLM configuration (admin only).

#### PUT /api/v1/llm/config
Update LLM configuration (admin only).

#### GET /api/v1/llm/health
Get health status of all providers.

#### GET /api/v1/llm/methods
List available LLM methods.

#### POST /api/v1/llm/config/test
Test connection to specific provider.

## Best Practices

### Configuration
- Use environment variables for API keys
- Set appropriate timeouts for your use case
- Enable only needed providers
- Regular health monitoring

### Usage
- Handle errors gracefully
- Implement client-side timeouts
- Cache responses when appropriate
- Monitor usage and costs

### Security
- Rotate API keys regularly
- Use least-privilege access
- Monitor for unusual usage patterns
- Keep configurations updated

## Migration Guide

### From Direct Provider Usage
If you're currently using providers directly:

1. Update imports:
```python
# Old
from src.ai.ollama_annotator import OllamaAnnotator

# New
from src.ai.llm_switcher import get_initialized_switcher
```

2. Update usage:
```python
# Old
annotator = OllamaAnnotator()
result = await annotator.annotate(text)

# New
switcher = await get_initialized_switcher()
request = GenerateRequest(prompt=text, method="local_ollama")
response = await switcher.generate(request)
```

### Configuration Migration
Existing configurations will be automatically migrated during the first startup.

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs for error details
- Test individual providers
- Contact system administrators

## Changelog

### Version 1.0.0
- Initial release
- Support for Ollama, OpenAI, Azure, Chinese LLMs
- Hot configuration reload
- Multi-tenant support
- Health monitoring
- API key security