/**
 * LLM Provider Form Component
 * 
 * Form for creating and editing LLM provider configurations.
 * Supports multiple provider types with dynamic field rendering.
 * 
 * **Requirements: 6.2**
 */

import React, { useEffect, useMemo } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Space,
  Typography,
  Divider,
  Row,
  Col,
  Tooltip,
} from 'antd';
import {
  CloudOutlined,
  DatabaseOutlined,
  ApiOutlined,
  RobotOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { LLMConfigCreate, LLMConfigUpdate, LLMType } from '@/services/adminApi';

const { Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// Provider type definitions with icons and metadata
export const PROVIDER_TYPES: Array<{
  value: LLMType;
  label: string;
  icon: React.ReactNode;
  category: 'local' | 'cloud' | 'china';
  requiresApiKey: boolean;
  requiresEndpoint: boolean;
}> = [
  {
    value: 'local_ollama',
    label: '本地 Ollama',
    icon: <DatabaseOutlined />,
    category: 'local',
    requiresApiKey: false,
    requiresEndpoint: true,
  },
  {
    value: 'openai',
    label: 'OpenAI',
    icon: <CloudOutlined />,
    category: 'cloud',
    requiresApiKey: true,
    requiresEndpoint: true,
  },
  {
    value: 'qianwen',
    label: '通义千问 (Qwen)',
    icon: <RobotOutlined />,
    category: 'china',
    requiresApiKey: true,
    requiresEndpoint: false,
  },
  {
    value: 'zhipu',
    label: '智谱 GLM',
    icon: <RobotOutlined />,
    category: 'china',
    requiresApiKey: true,
    requiresEndpoint: false,
  },
  {
    value: 'hunyuan',
    label: '腾讯混元',
    icon: <RobotOutlined />,
    category: 'china',
    requiresApiKey: true,
    requiresEndpoint: false,
  },
  {
    value: 'custom',
    label: '自定义',
    icon: <ApiOutlined />,
    category: 'cloud',
    requiresApiKey: true,
    requiresEndpoint: true,
  },
];

// Default model suggestions by provider type
const MODEL_SUGGESTIONS: Record<LLMType, string[]> = {
  local_ollama: ['llama2', 'llama2:7b', 'llama2:13b', 'mistral', 'codellama', 'qwen:7b'],
  openai: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini'],
  qianwen: ['qwen-turbo', 'qwen-plus', 'qwen-max', 'qwen-long'],
  zhipu: ['glm-4', 'glm-4-flash', 'glm-3-turbo'],
  hunyuan: ['hunyuan-lite', 'hunyuan-standard', 'hunyuan-pro'],
  custom: [],
};

// Default endpoints by provider type
const DEFAULT_ENDPOINTS: Record<LLMType, string> = {
  local_ollama: 'http://localhost:11434',
  openai: 'https://api.openai.com/v1',
  qianwen: '',
  zhipu: '',
  hunyuan: '',
  custom: '',
};

export interface ProviderFormProps {
  form: ReturnType<typeof Form.useForm>[0];
  initialValues?: Partial<LLMConfigCreate | LLMConfigUpdate>;
  isEditing?: boolean;
  onValuesChange?: (changedValues: unknown, allValues: unknown) => void;
}

export const ProviderForm: React.FC<ProviderFormProps> = ({
  form,
  initialValues,
  isEditing = false,
  onValuesChange,
}) => {
  const { t } = useTranslation(['admin', 'common']);
  
  // Watch the selected provider type
  const selectedType = Form.useWatch('llm_type', form) as LLMType | undefined;
  
  // Get provider config based on selected type
  const providerConfig = useMemo(() => {
    return PROVIDER_TYPES.find(p => p.value === selectedType);
  }, [selectedType]);
  
  // Update default endpoint when provider type changes
  useEffect(() => {
    if (selectedType && !isEditing) {
      const defaultEndpoint = DEFAULT_ENDPOINTS[selectedType];
      if (defaultEndpoint) {
        form.setFieldValue('api_endpoint', defaultEndpoint);
      }
    }
  }, [selectedType, form, isEditing]);
  
  // Set initial values
  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue(initialValues);
    }
  }, [initialValues, form]);

  return (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={onValuesChange}
      initialValues={{
        temperature: 0.7,
        max_tokens: 2048,
        timeout_seconds: 60,
        is_default: false,
        extra_config: {},
        ...initialValues,
      }}
    >
      {/* Basic Information */}
      <Typography.Title level={5}>{t('common:basicInfo')}</Typography.Title>
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="name"
            label={t('llm.form.configName')}
            rules={[
              { required: true, message: t('llm.form.configNameRequired') },
              { max: 100, message: t('common:maxLength', { max: 100 }) },
            ]}
          >
            <Input placeholder={t('llm.form.configNamePlaceholder')} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name="llm_type"
            label={t('llm.form.llmType')}
            rules={[{ required: true, message: t('llm.form.llmTypeRequired') }]}
          >
            <Select
              placeholder={t('llm.form.llmTypePlaceholder')}
              optionLabelProp="label"
            >
              {PROVIDER_TYPES.map(provider => (
                <Option key={provider.value} value={provider.value} label={provider.label}>
                  <Space>
                    {provider.icon}
                    <span>{provider.label}</span>
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
      
      <Form.Item
        name="description"
        label={t('common:description')}
      >
        <TextArea
          rows={2}
          placeholder={t('llm.form.descriptionPlaceholder')}
          maxLength={500}
          showCount
        />
      </Form.Item>
      
      <Divider />
      
      {/* Provider Configuration */}
      <Typography.Title level={5}>
        {t('llm.form.providerConfig', { defaultValue: '提供商配置' })}
      </Typography.Title>
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="model_name"
            label={
              <Space>
                {t('llm.form.modelName')}
                <Tooltip title={t('llm.form.modelNameTooltip', { defaultValue: '选择或输入模型名称' })}>
                  <QuestionCircleOutlined />
                </Tooltip>
              </Space>
            }
            rules={[{ required: true, message: t('llm.form.modelNameRequired') }]}
          >
            <Select
              mode="tags"
              maxCount={1}
              placeholder={t('llm.form.modelNamePlaceholder')}
              options={
                selectedType
                  ? MODEL_SUGGESTIONS[selectedType].map(model => ({
                      value: model,
                      label: model,
                    }))
                  : []
              }
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name="api_endpoint"
            label={t('llm.form.apiEndpoint')}
            rules={[
              {
                required: providerConfig?.requiresEndpoint,
                message: t('llm.form.apiEndpointRequired', { defaultValue: '请输入 API 端点' }),
              },
              {
                type: 'url',
                message: t('llm.form.apiEndpointInvalid', { defaultValue: '请输入有效的 URL' }),
              },
            ]}
          >
            <Input
              placeholder={t('llm.form.apiEndpointPlaceholder')}
              disabled={!providerConfig?.requiresEndpoint && selectedType !== 'custom'}
            />
          </Form.Item>
        </Col>
      </Row>
      
      {/* API Key - only show for providers that require it */}
      {(providerConfig?.requiresApiKey || selectedType === 'custom') && (
        <Form.Item
          name="api_key"
          label="API Key"
          extra={isEditing ? t('llm.form.apiKeyKeepEmpty') : undefined}
          rules={[
            {
              required: !isEditing && providerConfig?.requiresApiKey,
              message: t('llm.form.apiKeyRequired', { defaultValue: '请输入 API Key' }),
            },
          ]}
        >
          <Input.Password
            placeholder={t('llm.form.apiKeyPlaceholder')}
            autoComplete="new-password"
          />
        </Form.Item>
      )}
      
      <Divider />
      
      {/* Model Parameters */}
      <Typography.Title level={5}>
        {t('llm.form.modelParams', { defaultValue: '模型参数' })}
      </Typography.Title>
      
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            name="temperature"
            label={
              <Space>
                Temperature
                <Tooltip title={t('llm.form.temperatureTooltip', { defaultValue: '控制输出的随机性，值越高输出越随机' })}>
                  <QuestionCircleOutlined />
                </Tooltip>
              </Space>
            }
            rules={[
              { type: 'number', min: 0, max: 2, message: t('llm.form.temperatureRange', { defaultValue: '范围: 0-2' }) },
            ]}
          >
            <InputNumber
              min={0}
              max={2}
              step={0.1}
              style={{ width: '100%' }}
              precision={1}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="max_tokens"
            label={
              <Space>
                {t('llm.form.maxTokens')}
                <Tooltip title={t('llm.form.maxTokensTooltip', { defaultValue: '生成文本的最大 token 数量' })}>
                  <QuestionCircleOutlined />
                </Tooltip>
              </Space>
            }
            rules={[
              { type: 'number', min: 1, max: 128000, message: t('llm.form.maxTokensRange', { defaultValue: '范围: 1-128000' }) },
            ]}
          >
            <InputNumber
              min={1}
              max={128000}
              style={{ width: '100%' }}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="timeout_seconds"
            label={
              <Space>
                {t('llm.form.timeout')}
                <Tooltip title={t('llm.form.timeoutTooltip', { defaultValue: '请求超时时间（秒）' })}>
                  <QuestionCircleOutlined />
                </Tooltip>
              </Space>
            }
            rules={[
              { type: 'number', min: 1, max: 600, message: t('llm.form.timeoutRange', { defaultValue: '范围: 1-600 秒' }) },
            ]}
          >
            <InputNumber
              min={1}
              max={600}
              style={{ width: '100%' }}
              addonAfter={t('common:seconds', { defaultValue: '秒' })}
            />
          </Form.Item>
        </Col>
      </Row>
      
      <Divider />
      
      {/* Settings */}
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="is_default"
            valuePropName="checked"
            label={t('llm.form.setAsDefault')}
          >
            <Switch />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name="is_active"
            valuePropName="checked"
            label={t('llm.form.enabled')}
            initialValue={true}
          >
            <Switch defaultChecked />
          </Form.Item>
        </Col>
      </Row>
      
      {/* Provider-specific help text */}
      {selectedType && (
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">
            {getProviderHelpText(selectedType, t)}
          </Text>
        </div>
      )}
    </Form>
  );
};

// Helper function to get provider-specific help text
function getProviderHelpText(
  type: LLMType,
  t: (key: string, options?: Record<string, unknown>) => string
): string {
  const helpTexts: Record<LLMType, string> = {
    local_ollama: t('llm.help.ollama', { defaultValue: '确保 Ollama 服务已在本地运行，默认端口为 11434。' }),
    openai: t('llm.help.openai', { defaultValue: '需要有效的 OpenAI API Key，可在 platform.openai.com 获取。' }),
    qianwen: t('llm.help.qianwen', { defaultValue: '需要阿里云通义千问 API Key，可在阿里云控制台获取。' }),
    zhipu: t('llm.help.zhipu', { defaultValue: '需要智谱 AI API Key，可在 open.bigmodel.cn 获取。' }),
    hunyuan: t('llm.help.hunyuan', { defaultValue: '需要腾讯云混元 API Key，可在腾讯云控制台获取。' }),
    custom: t('llm.help.custom', { defaultValue: '自定义提供商需要配置兼容 OpenAI API 格式的端点。' }),
  };
  return helpTexts[type] || '';
}

export default ProviderForm;
