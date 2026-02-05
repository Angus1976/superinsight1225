/**
 * LLM Provider Configuration Component
 *
 * Provides detailed LLM provider-specific settings:
 * - Ollama: Local model configuration
 * - OpenAI: API keys, models, temperature
 * - Azure OpenAI: Deployment, endpoint
 * - Chinese LLMs: Qwen, Zhipu, Baidu, Hunyuan
 *
 * Features:
 * - Provider-specific configuration forms
 * - Connection testing
 * - Model selection with context window info
 * - Advanced settings (timeout, retries, streaming, caching)
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Button,
  Space,
  Alert,
  Divider,
  Row,
  Col,
  Tag,
  Tooltip,
  message,
  Collapse,
  Badge,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  LockOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

import type { EngineConfig } from '@/pages/AIAnnotation/EngineConfiguration';

interface LLMProviderConfigProps {
  engines: EngineConfig[];
  onSave: (config: EngineConfig) => Promise<void>;
  loading?: boolean;
}

interface ProviderModel {
  name: string;
  displayName: string;
  contextWindow: number;
  costPer1kTokens?: {
    input: number;
    output: number;
  };
}

interface ConnectionTestResult {
  success: boolean;
  message: string;
  latency?: number;
  model?: string;
}

const LLMProviderConfig: React.FC<LLMProviderConfigProps> = ({
  engines,
  onSave,
  loading = false,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [form] = Form.useForm();
  const [selectedEngine, setSelectedEngine] = useState<EngineConfig | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('openai');
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionResult, setConnectionResult] = useState<ConnectionTestResult | null>(null);
  const [availableModels, setAvailableModels] = useState<ProviderModel[]>([]);

  // Provider model configurations
  const providerModels: Record<string, ProviderModel[]> = {
    ollama: [
      { name: 'llama2', displayName: 'Llama 2', contextWindow: 4096 },
      { name: 'llama2:13b', displayName: 'Llama 2 13B', contextWindow: 4096 },
      { name: 'llama2:70b', displayName: 'Llama 2 70B', contextWindow: 4096 },
      { name: 'mistral', displayName: 'Mistral', contextWindow: 8192 },
      { name: 'mixtral', displayName: 'Mixtral 8x7B', contextWindow: 32768 },
      { name: 'codellama', displayName: 'Code Llama', contextWindow: 16384 },
      { name: 'qwen:7b', displayName: 'Qwen 7B', contextWindow: 8192 },
      { name: 'qwen:14b', displayName: 'Qwen 14B', contextWindow: 8192 },
    ],
    openai: [
      {
        name: 'gpt-4-turbo',
        displayName: 'GPT-4 Turbo',
        contextWindow: 128000,
        costPer1kTokens: { input: 0.01, output: 0.03 },
      },
      {
        name: 'gpt-4',
        displayName: 'GPT-4',
        contextWindow: 8192,
        costPer1kTokens: { input: 0.03, output: 0.06 },
      },
      {
        name: 'gpt-3.5-turbo',
        displayName: 'GPT-3.5 Turbo',
        contextWindow: 16385,
        costPer1kTokens: { input: 0.0015, output: 0.002 },
      },
      {
        name: 'gpt-3.5-turbo-16k',
        displayName: 'GPT-3.5 Turbo 16K',
        contextWindow: 16385,
        costPer1kTokens: { input: 0.003, output: 0.004 },
      },
    ],
    azure: [
      { name: 'gpt-4-turbo', displayName: 'GPT-4 Turbo', contextWindow: 128000 },
      { name: 'gpt-4', displayName: 'GPT-4', contextWindow: 8192 },
      { name: 'gpt-35-turbo', displayName: 'GPT-3.5 Turbo', contextWindow: 16385 },
    ],
    qwen: [
      { name: 'qwen-turbo', displayName: 'Qwen Turbo (通义千问-Turbo)', contextWindow: 8192 },
      { name: 'qwen-plus', displayName: 'Qwen Plus (通义千问-Plus)', contextWindow: 32768 },
      { name: 'qwen-max', displayName: 'Qwen Max (通义千问-Max)', contextWindow: 8192 },
      { name: 'qwen-max-longcontext', displayName: 'Qwen Max Long (长文本)', contextWindow: 30000 },
    ],
    zhipu: [
      { name: 'chatglm_pro', displayName: 'ChatGLM Pro (智谱Pro)', contextWindow: 8192 },
      { name: 'chatglm_std', displayName: 'ChatGLM Std (智谱Std)', contextWindow: 8192 },
      { name: 'chatglm_lite', displayName: 'ChatGLM Lite (智谱Lite)', contextWindow: 8192 },
    ],
    baidu: [
      { name: 'ernie-bot-4', displayName: 'ERNIE Bot 4.0 (文心一言4.0)', contextWindow: 8192 },
      { name: 'ernie-bot', displayName: 'ERNIE Bot (文心一言)', contextWindow: 8192 },
      { name: 'ernie-bot-turbo', displayName: 'ERNIE Bot Turbo (文心一言Turbo)', contextWindow: 8192 },
    ],
    hunyuan: [
      { name: 'hunyuan-pro', displayName: 'Hunyuan Pro (混元Pro)', contextWindow: 32768 },
      { name: 'hunyuan-standard', displayName: 'Hunyuan Standard (混元标准版)', contextWindow: 8192 },
      { name: 'hunyuan-lite', displayName: 'Hunyuan Lite (混元轻量版)', contextWindow: 8192 },
    ],
  };

  useEffect(() => {
    if (engines.length > 0) {
      setSelectedEngine(engines[0]);
      setSelectedProvider(engines[0].provider);
      form.setFieldsValue(getProviderConfig(engines[0]));
    }
  }, [engines, form]);

  useEffect(() => {
    setAvailableModels(providerModels[selectedProvider] || []);
  }, [selectedProvider]);

  const getProviderConfig = (engine: EngineConfig): any => {
    // Extract provider-specific config from engine
    return {
      provider: engine.provider,
      model: engine.model,
      apiKey: '',
      endpoint: '',
      temperature: 0.7,
      maxTokens: 2000,
      timeout: 30,
      maxRetries: 3,
      enableStreaming: false,
      enableCache: true,
    };
  };

  const handleEngineSelect = (engineId: string) => {
    const engine = engines.find((e) => e.id === engineId);
    if (engine) {
      setSelectedEngine(engine);
      setSelectedProvider(engine.provider);
      form.setFieldsValue(getProviderConfig(engine));
      setConnectionResult(null);
    }
  };

  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider);
    setConnectionResult(null);
    // Reset form fields for new provider
    form.resetFields(['model', 'apiKey', 'endpoint', 'deployment']);
  };

  const handleTestConnection = async () => {
    try {
      setTestingConnection(true);
      setConnectionResult(null);

      const values = await form.validateFields();
      const testPayload = {
        provider: selectedProvider,
        config: values,
      };

      const response = await fetch('/api/v1/annotation/engines/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testPayload),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        setConnectionResult({
          success: true,
          message: t('ai_annotation:messages.connection_success'),
          latency: result.latency,
          model: result.model,
        });
        message.success(t('ai_annotation:messages.connection_success'));
      } else {
        setConnectionResult({
          success: false,
          message: result.error || t('ai_annotation:errors.connection_failed'),
        });
        message.error(result.error || t('ai_annotation:errors.connection_failed'));
      }
    } catch (error: any) {
      setConnectionResult({
        success: false,
        message: error.message || t('ai_annotation:errors.connection_test_failed'),
      });
      message.error(t('ai_annotation:errors.connection_test_failed'));
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveConfig = async () => {
    try {
      const values = await form.validateFields();
      if (!selectedEngine) {
        message.error(t('ai_annotation:errors.no_engine_selected'));
        return;
      }

      const updatedConfig: EngineConfig = {
        ...selectedEngine,
        provider: selectedProvider as any,
        model: values.model,
        // Store provider-specific config in a metadata field
        // (Backend should handle this appropriately)
      };

      await onSave(updatedConfig);
      message.success(t('ai_annotation:messages.config_saved'));
    } catch (error) {
      console.error('Failed to save config:', error);
    }
  };

  const renderOllamaConfig = () => (
    <>
      <Form.Item
        name="endpoint"
        label={t('ai_annotation:fields.ollama_endpoint')}
        rules={[{ required: true, type: 'url' }]}
        tooltip={t('ai_annotation:tooltips.ollama_endpoint')}
      >
        <Input
          prefix={<GlobalOutlined />}
          placeholder="http://localhost:11434"
        />
      </Form.Item>

      <Form.Item
        name="model"
        label={t('ai_annotation:fields.model_name')}
        rules={[{ required: true }]}
      >
        <Select
          showSearch
          placeholder={t('ai_annotation:placeholders.select_model')}
          optionFilterProp="children"
        >
          {availableModels.map((model) => (
            <Select.Option key={model.name} value={model.name}>
              <Space>
                {model.displayName}
                <Tag color="blue">{model.contextWindow.toLocaleString()} tokens</Tag>
              </Space>
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Alert
        message={t('ai_annotation:info.ollama_local')}
        description={t('ai_annotation:info.ollama_local_desc')}
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 16 }}
      />
    </>
  );

  const renderOpenAIConfig = () => (
    <>
      <Form.Item
        name="apiKey"
        label={t('ai_annotation:fields.api_key')}
        rules={[{ required: true }]}
        tooltip={t('ai_annotation:tooltips.openai_api_key')}
      >
        <Input.Password
          prefix={<LockOutlined />}
          placeholder="sk-..."
        />
      </Form.Item>

      <Form.Item
        name="organization"
        label={t('ai_annotation:fields.organization_id')}
        tooltip={t('ai_annotation:tooltips.openai_org')}
      >
        <Input placeholder="org-..." />
      </Form.Item>

      <Form.Item
        name="model"
        label={t('ai_annotation:fields.model_name')}
        rules={[{ required: true }]}
      >
        <Select placeholder={t('ai_annotation:placeholders.select_model')}>
          {availableModels.map((model) => (
            <Select.Option key={model.name} value={model.name}>
              <Space direction="vertical" size={0}>
                <span>{model.displayName}</span>
                <Space size="small" style={{ fontSize: 12, color: '#999' }}>
                  <Tag color="blue">{model.contextWindow.toLocaleString()} tokens</Tag>
                  {model.costPer1kTokens && (
                    <Tag color="green">
                      ${model.costPer1kTokens.input.toFixed(4)}/
                      ${model.costPer1kTokens.output.toFixed(4)} per 1K
                    </Tag>
                  )}
                </Space>
              </Space>
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item
        name="temperature"
        label={t('ai_annotation:fields.temperature')}
        tooltip={t('ai_annotation:tooltips.temperature')}
      >
        <Slider
          min={0}
          max={2}
          step={0.1}
          marks={{
            0: t('ai_annotation:labels.deterministic'),
            1: t('ai_annotation:labels.balanced'),
            2: t('ai_annotation:labels.creative'),
          }}
        />
      </Form.Item>

      <Form.Item
        name="maxTokens"
        label={t('ai_annotation:fields.max_tokens')}
        tooltip={t('ai_annotation:tooltips.max_tokens')}
      >
        <InputNumber
          min={1}
          max={128000}
          step={100}
          style={{ width: '100%' }}
        />
      </Form.Item>
    </>
  );

  const renderAzureConfig = () => (
    <>
      <Form.Item
        name="apiKey"
        label={t('ai_annotation:fields.api_key')}
        rules={[{ required: true }]}
      >
        <Input.Password prefix={<LockOutlined />} />
      </Form.Item>

      <Form.Item
        name="endpoint"
        label={t('ai_annotation:fields.azure_endpoint')}
        rules={[{ required: true, type: 'url' }]}
        tooltip={t('ai_annotation:tooltips.azure_endpoint')}
      >
        <Input
          prefix={<GlobalOutlined />}
          placeholder="https://your-resource.openai.azure.com"
        />
      </Form.Item>

      <Form.Item
        name="deployment"
        label={t('ai_annotation:fields.deployment_name')}
        rules={[{ required: true }]}
        tooltip={t('ai_annotation:tooltips.azure_deployment')}
      >
        <Input placeholder="your-deployment-name" />
      </Form.Item>

      <Form.Item
        name="apiVersion"
        label={t('ai_annotation:fields.api_version')}
        rules={[{ required: true }]}
      >
        <Select defaultValue="2023-05-15">
          <Select.Option value="2023-05-15">2023-05-15</Select.Option>
          <Select.Option value="2023-06-01-preview">2023-06-01-preview</Select.Option>
          <Select.Option value="2023-12-01-preview">2023-12-01-preview</Select.Option>
        </Select>
      </Form.Item>

      <Form.Item
        name="model"
        label={t('ai_annotation:fields.model_name')}
        rules={[{ required: true }]}
      >
        <Select>
          {availableModels.map((model) => (
            <Select.Option key={model.name} value={model.name}>
              <Space>
                {model.displayName}
                <Tag color="blue">{model.contextWindow.toLocaleString()} tokens</Tag>
              </Space>
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
    </>
  );

  const renderChineseLLMConfig = () => {
    const isQwen = selectedProvider === 'qwen';
    const isZhipu = selectedProvider === 'zhipu';
    const isBaidu = selectedProvider === 'baidu';
    const isHunyuan = selectedProvider === 'hunyuan';

    return (
      <>
        <Form.Item
          name="apiKey"
          label={t('ai_annotation:fields.api_key')}
          rules={[{ required: true }]}
          tooltip={
            isQwen
              ? t('ai_annotation:tooltips.qwen_api_key')
              : isZhipu
              ? t('ai_annotation:tooltips.zhipu_api_key')
              : isBaidu
              ? t('ai_annotation:tooltips.baidu_api_key')
              : t('ai_annotation:tooltips.hunyuan_secret_id')
          }
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder={
              isQwen
                ? 'sk-...'
                : isZhipu
                ? 'zhipu-...'
                : isBaidu
                ? 'Access Key'
                : 'SecretId'
            }
          />
        </Form.Item>

        {(isBaidu || isHunyuan) && (
          <Form.Item
            name="secretKey"
            label={
              isBaidu
                ? t('ai_annotation:fields.secret_key')
                : t('ai_annotation:fields.secret_key_hunyuan')
            }
            rules={[{ required: true }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder={isBaidu ? 'Secret Key' : 'SecretKey'}
            />
          </Form.Item>
        )}

        <Form.Item
          name="model"
          label={t('ai_annotation:fields.model_name')}
          rules={[{ required: true }]}
        >
          <Select>
            {availableModels.map((model) => (
              <Select.Option key={model.name} value={model.name}>
                <Space>
                  {model.displayName}
                  <Tag color="blue">{model.contextWindow.toLocaleString()} tokens</Tag>
                </Space>
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Alert
          message={
            isQwen
              ? t('ai_annotation:info.qwen_notice')
              : isZhipu
              ? t('ai_annotation:info.zhipu_notice')
              : isBaidu
              ? t('ai_annotation:info.baidu_notice')
              : t('ai_annotation:info.hunyuan_notice')
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      </>
    );
  };

  const renderAdvancedSettings = () => (
    <Collapse
      items={[
        {
          key: 'advanced',
          label: t('ai_annotation:sections.advanced_settings'),
          children: (
            <>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="timeout"
                    label={t('ai_annotation:fields.request_timeout')}
                    tooltip={t('ai_annotation:tooltips.request_timeout')}
                  >
                    <InputNumber
                      min={5}
                      max={300}
                      addonAfter="s"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="maxRetries"
                    label={t('ai_annotation:fields.max_retries')}
                    tooltip={t('ai_annotation:tooltips.max_retries')}
                  >
                    <InputNumber min={0} max={10} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="enableStreaming"
                valuePropName="checked"
                tooltip={t('ai_annotation:tooltips.enable_streaming')}
              >
                <Switch /> {t('ai_annotation:fields.enable_streaming')}
              </Form.Item>

              <Form.Item
                name="enableCache"
                valuePropName="checked"
                tooltip={t('ai_annotation:tooltips.enable_cache')}
              >
                <Switch /> {t('ai_annotation:fields.enable_response_cache')}
              </Form.Item>
            </>
          ),
        },
      ]}
    />
  );

  return (
    <div className="llm-provider-config">
      <Row gutter={16}>
        <Col span={8}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined />
                {t('ai_annotation:sections.select_engine')}
              </Space>
            }
            size="small"
          >
            <Select
              style={{ width: '100%' }}
              value={selectedEngine?.id}
              onChange={handleEngineSelect}
              placeholder={t('ai_annotation:placeholders.select_engine')}
            >
              {engines.map((engine) => (
                <Select.Option key={engine.id} value={engine.id}>
                  <Space>
                    <Tag color="blue">{engine.engineType}</Tag>
                    {engine.model}
                  </Space>
                </Select.Option>
              ))}
            </Select>

            {selectedEngine && (
              <div style={{ marginTop: 16 }}>
                <Divider style={{ margin: '12px 0' }} />
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <div>
                    <strong>{t('ai_annotation:labels.current_provider')}:</strong>{' '}
                    <Tag color="cyan">{selectedEngine.provider}</Tag>
                  </div>
                  <div>
                    <strong>{t('ai_annotation:labels.current_model')}:</strong>{' '}
                    {selectedEngine.model || t('common:not_configured')}
                  </div>
                  <div>
                    <strong>{t('ai_annotation:labels.status')}:</strong>{' '}
                    <Badge
                      status={selectedEngine.enabled ? 'success' : 'default'}
                      text={
                        selectedEngine.enabled
                          ? t('common:status.enabled')
                          : t('common:status.disabled')
                      }
                    />
                  </div>
                </Space>
              </div>
            )}
          </Card>
        </Col>

        <Col span={16}>
          <Card
            title={
              <Space>
                <ApiOutlined />
                {t('ai_annotation:sections.provider_configuration')}
              </Space>
            }
            extra={
              <Space>
                <Button
                  icon={<CheckCircleOutlined />}
                  onClick={handleTestConnection}
                  loading={testingConnection}
                >
                  {t('ai_annotation:actions.test_connection')}
                </Button>
                <Button type="primary" onClick={handleSaveConfig} loading={loading}>
                  {t('common:actions.save')}
                </Button>
              </Space>
            }
          >
            <Form form={form} layout="vertical">
              <Form.Item
                name="provider"
                label={t('ai_annotation:fields.llm_provider')}
                rules={[{ required: true }]}
              >
                <Select onChange={handleProviderChange} value={selectedProvider}>
                  <Select.Option value="ollama">
                    <Space>
                      <Tag color="purple">Ollama</Tag>
                      {t('ai_annotation:providers.ollama_desc')}
                    </Space>
                  </Select.Option>
                  <Select.Option value="openai">
                    <Space>
                      <Tag color="cyan">OpenAI</Tag>
                      {t('ai_annotation:providers.openai_desc')}
                    </Space>
                  </Select.Option>
                  <Select.Option value="azure">
                    <Space>
                      <Tag color="blue">Azure OpenAI</Tag>
                      {t('ai_annotation:providers.azure_desc')}
                    </Space>
                  </Select.Option>
                  <Select.Option value="qwen">
                    <Space>
                      <Tag color="orange">Qwen (通义千问)</Tag>
                      {t('ai_annotation:providers.qwen_desc')}
                    </Space>
                  </Select.Option>
                  <Select.Option value="zhipu">
                    <Space>
                      <Tag color="green">Zhipu (智谱)</Tag>
                      {t('ai_annotation:providers.zhipu_desc')}
                    </Space>
                  </Select.Option>
                  <Select.Option value="baidu">
                    <Space>
                      <Tag color="red">Baidu (百度)</Tag>
                      {t('ai_annotation:providers.baidu_desc')}
                    </Space>
                  </Select.Option>
                  <Select.Option value="hunyuan">
                    <Space>
                      <Tag color="magenta">Hunyuan (腾讯混元)</Tag>
                      {t('ai_annotation:providers.hunyuan_desc')}
                    </Space>
                  </Select.Option>
                </Select>
              </Form.Item>

              <Divider />

              {/* Provider-specific configurations */}
              {selectedProvider === 'ollama' && renderOllamaConfig()}
              {selectedProvider === 'openai' && renderOpenAIConfig()}
              {selectedProvider === 'azure' && renderAzureConfig()}
              {['qwen', 'zhipu', 'baidu', 'hunyuan'].includes(selectedProvider) &&
                renderChineseLLMConfig()}

              <Divider />

              {/* Advanced settings */}
              {renderAdvancedSettings()}

              {/* Connection test result */}
              {connectionResult && (
                <>
                  <Divider />
                  <Alert
                    message={
                      connectionResult.success
                        ? t('ai_annotation:messages.connection_success')
                        : t('ai_annotation:errors.connection_failed')
                    }
                    description={
                      connectionResult.success ? (
                        <Space direction="vertical">
                          <div>{connectionResult.message}</div>
                          {connectionResult.latency && (
                            <div>
                              {t('ai_annotation:labels.latency')}: {connectionResult.latency}ms
                            </div>
                          )}
                          {connectionResult.model && (
                            <div>
                              {t('ai_annotation:labels.detected_model')}: {connectionResult.model}
                            </div>
                          )}
                        </Space>
                      ) : (
                        connectionResult.message
                      )
                    }
                    type={connectionResult.success ? 'success' : 'error'}
                    showIcon
                    icon={
                      connectionResult.success ? (
                        <CheckCircleOutlined />
                      ) : (
                        <CloseCircleOutlined />
                      )
                    }
                  />
                </>
              )}
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default LLMProviderConfig;
