/**
 * LLM Configuration Page
 * 
 * Provides a comprehensive interface for configuring LLM providers including
 * local Ollama, cloud providers (OpenAI, Azure), and Chinese LLM services.
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Tabs,
  Alert,
  Space,
  Divider,
  Tag,
  Spin,
  message,
  Modal,
  Typography,
  Row,
  Col,
  Tooltip,
  Badge,
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  ApiOutlined,
  CloudOutlined,
  DatabaseOutlined,
  SettingOutlined,
} from '@ant-design/icons';

import {
  llmService,
  LLMConfig,
  LLMMethod,
  HealthStatus,
  MethodInfo,
  ValidationResult,
  getMethodName,
  getMethodCategory,
  isApiKeyMasked,
} from '@/services/llm';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

// ==================== Types ====================

interface ConfigFormData extends LLMConfig {}

interface ConnectionTestResult {
  method: LLMMethod;
  status: 'testing' | 'success' | 'error';
  message?: string;
  latency?: number;
}

// ==================== Component ====================

const LLMConfigPage: React.FC = () => {
  const { t } = useTranslation(['admin', 'common']);
  const [form] = Form.useForm<ConfigFormData>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [methods, setMethods] = useState<MethodInfo[]>([]);
  const [healthStatus, setHealthStatus] = useState<Record<string, HealthStatus>>({});
  const [testResults, setTestResults] = useState<Record<string, ConnectionTestResult>>({});
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  // ==================== Effects ====================

  useEffect(() => {
    loadInitialData();
  }, []);

  // ==================== Data Loading ====================

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [configData, methodsData, healthData] = await Promise.all([
        llmService.getConfig(),
        llmService.getMethods(),
        llmService.getHealth(),
      ]);

      setConfig(configData);
      setMethods(methodsData);
      setHealthStatus(healthData);
      form.setFieldsValue(configData);
    } catch (error) {
      console.error('Failed to load LLM configuration:', error);
      message.error(t('llm.loadConfigFailed'));
    } finally {
      setLoading(false);
    }
  };

  const refreshHealth = async () => {
    try {
      const healthData = await llmService.getHealth();
      setHealthStatus(healthData);
    } catch (error) {
      console.error('Failed to refresh health status:', error);
      message.error(t('llm.refreshHealthFailed'));
    }
  };

  // ==================== Form Handlers ====================

  const handleSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();
      
      // Validate configuration
      const validation = await llmService.validateConfig(values);
      setValidationResult(validation);
      
      if (!validation.valid) {
        message.error(t('llm.configValidationFailed'));
        return;
      }

      // Save configuration
      const updatedConfig = await llmService.updateConfig(values);
      setConfig(updatedConfig);
      message.success(t('llm.configSaveSuccess'));

      // Refresh health status
      await refreshHealth();
    } catch (error) {
      console.error('Failed to save configuration:', error);
      message.error(t('llm.configSaveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    Modal.confirm({
      title: t('llm.actions.confirmReset'),
      content: t('llm.actions.confirmResetMessage'),
      onOk: () => {
        if (config) {
          form.setFieldsValue(config);
          setValidationResult(null);
          message.info(t('llm.configReset'));
        }
      },
    });
  };

  const handleHotReload = async () => {
    try {
      const reloadedConfig = await llmService.hotReload();
      setConfig(reloadedConfig);
      form.setFieldsValue(reloadedConfig);
      message.success(t('llm.hotReloadSuccess'));
      await refreshHealth();
    } catch (error) {
      console.error('Failed to hot reload configuration:', error);
      message.error(t('llm.hotReloadFailed'));
    }
  };

  // ==================== Connection Testing ====================

  const testConnection = async (method: LLMMethod) => {
    setTestResults(prev => ({
      ...prev,
      [method]: { method, status: 'testing' }
    }));

    try {
      const result = await llmService.testConnection(method);
      setTestResults(prev => ({
        ...prev,
        [method]: {
          method,
          status: result.available ? 'success' : 'error',
          message: result.error || t('llm.status.connectionSuccess'),
          latency: result.latency_ms,
        }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [method]: {
          method,
          status: 'error',
          message: error instanceof Error ? error.message : t('llm.status.connectionFailed'),
        }
      }));
    }
  };

  // ==================== UI Helpers ====================

  const toggleApiKeyVisibility = (field: string) => {
    setShowApiKeys(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  const renderApiKeyInput = (field: string, label: string, placeholder?: string) => {
    const isVisible = showApiKeys[field];
    return (
      <Form.Item
        name={field}
        label={label}
        rules={[{ required: false }]}
      >
        <Input.Password
          placeholder={placeholder || label}
          visibilityToggle={{
            visible: isVisible,
            onVisibleChange: () => toggleApiKeyVisibility(field),
          }}
          iconRender={(visible) => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
        />
      </Form.Item>
    );
  };

  const renderHealthBadge = (method: LLMMethod) => {
    const health = healthStatus[method];
    const test = testResults[method];
    
    if (test?.status === 'testing') {
      return <Badge status="processing" text={t('llm.status.testing')} />;
    }
    
    if (test?.status === 'success') {
      return <Badge status="success" text={`${t('llm.status.connectionSuccess')} (${test.latency}ms)`} />;
    }
    
    if (test?.status === 'error') {
      return <Badge status="error" text={test.message || t('llm.status.connectionFailed')} />;
    }
    
    if (health?.available) {
      return <Badge status="success" text={`${t('llm.status.online')} (${health.latency_ms}ms)`} />;
    }
    
    if (health?.error) {
      return <Badge status="error" text={health.error} />;
    }
    
    return <Badge status="default" text={t('llm.status.unknown')} />;
  };

  // ==================== Render Methods ====================

  const renderLocalConfig = () => (
    <Card title={t('llm.local.title')} extra={renderHealthBadge('local_ollama')}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'ollama_url']}
            label={t('llm.local.ollamaUrl')}
            rules={[{ required: true, message: t('llm.local.ollamaUrlRequired') }]}
          >
            <Input placeholder={t('llm.local.ollamaUrlPlaceholder')} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'default_model']}
            label={t('llm.local.defaultModel')}
            rules={[{ required: true, message: t('llm.local.defaultModelRequired') }]}
          >
            <Input placeholder={t('llm.local.defaultModelPlaceholder')} />
          </Form.Item>
        </Col>
      </Row>
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'timeout']}
            label={t('llm.local.timeout')}
            rules={[{ required: true, type: 'number', min: 1, max: 300 }]}
          >
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'max_retries']}
            label={t('llm.local.maxRetries')}
            rules={[{ required: true, type: 'number', min: 0, max: 10 }]}
          >
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Space>
        <Button
          type="primary"
          icon={<ApiOutlined />}
          onClick={() => testConnection('local_ollama')}
          loading={testResults['local_ollama']?.status === 'testing'}
        >
          {t('llm.actions.testConnection')}
        </Button>
      </Space>
    </Card>
  );

  const renderCloudConfig = () => (
    <Card title={t('llm.cloud.title')}>
      <Tabs defaultActiveKey="openai">
        <TabPane tab={<span><CloudOutlined />{t('llm.cloud.openai.title')}</span>} key="openai">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('cloud_openai')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              {renderApiKeyInput(['cloud_config', 'openai_api_key'], t('llm.cloud.openai.apiKey'))}
            </Col>
            <Col span={12}>
              <Form.Item
                name={['cloud_config', 'openai_base_url']}
                label={t('llm.cloud.openai.baseUrl')}
                rules={[{ required: true, message: t('llm.cloud.openai.baseUrlRequired') }]}
              >
                <Input placeholder={t('llm.cloud.openai.baseUrlPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name={['cloud_config', 'openai_model']}
                label={t('llm.cloud.openai.model')}
                rules={[{ required: true, message: t('llm.cloud.openai.modelRequired') }]}
              >
                <Input placeholder={t('llm.cloud.openai.modelPlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Space>
                <Button
                  type="primary"
                  icon={<ApiOutlined />}
                  onClick={() => testConnection('cloud_openai')}
                  loading={testResults['cloud_openai']?.status === 'testing'}
                >
                  {t('llm.actions.testConnection')}
                </Button>
              </Space>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<span><CloudOutlined />{t('llm.cloud.azure.title')}</span>} key="azure">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('cloud_azure')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name={['cloud_config', 'azure_endpoint']}
                label={t('llm.cloud.azure.endpoint')}
              >
                <Input placeholder={t('llm.cloud.azure.endpointPlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              {renderApiKeyInput(['cloud_config', 'azure_api_key'], t('llm.cloud.azure.apiKey'))}
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name={['cloud_config', 'azure_deployment']}
                label={t('llm.cloud.azure.deployment')}
              >
                <Input placeholder={t('llm.cloud.azure.deploymentPlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name={['cloud_config', 'azure_api_version']}
                label={t('llm.cloud.azure.apiVersion')}
                rules={[{ required: true, message: t('llm.cloud.azure.apiVersionRequired') }]}
              >
                <Input placeholder={t('llm.cloud.azure.apiVersionPlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Space>
                <Button
                  type="primary"
                  icon={<ApiOutlined />}
                  onClick={() => testConnection('cloud_azure')}
                  loading={testResults['cloud_azure']?.status === 'testing'}
                >
                  {t('llm.actions.testConnection')}
                </Button>
              </Space>
            </Col>
          </Row>
        </TabPane>
      </Tabs>
      
      <Divider />
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name={['cloud_config', 'timeout']}
            label={t('llm.cloud.timeout')}
            rules={[{ required: true, type: 'number', min: 1, max: 300 }]}
          >
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['cloud_config', 'max_retries']}
            label={t('llm.cloud.maxRetries')}
            rules={[{ required: true, type: 'number', min: 0, max: 10 }]}
          >
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );

  const renderChinaConfig = () => (
    <Card title={t('llm.china.title')}>
      <Tabs defaultActiveKey="qwen">
        <TabPane tab={t('llm.qwen.title')} key="qwen">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_qwen')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              {renderApiKeyInput(['china_config', 'qwen_api_key'], t('llm.qwen.apiKey'))}
            </Col>
            <Col span={12}>
              <Form.Item
                name={['china_config', 'qwen_model']}
                label={t('llm.qwen.model')}
                rules={[{ required: true, message: t('llm.qwen.modelRequired') }]}
              >
                <Input placeholder={t('llm.qwen.modelPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          
          <Space>
            <Button
              type="primary"
              icon={<ApiOutlined />}
              onClick={() => testConnection('china_qwen')}
              loading={testResults['china_qwen']?.status === 'testing'}
            >
              {t('llm.actions.testConnection')}
            </Button>
          </Space>
        </TabPane>

        <TabPane tab={t('llm.zhipu.title')} key="zhipu">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_zhipu')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              {renderApiKeyInput(['china_config', 'zhipu_api_key'], t('llm.zhipu.apiKey'))}
            </Col>
            <Col span={12}>
              <Form.Item
                name={['china_config', 'zhipu_model']}
                label={t('llm.zhipu.model')}
                rules={[{ required: true, message: t('llm.zhipu.modelRequired') }]}
              >
                <Input placeholder={t('llm.zhipu.modelPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          
          <Space>
            <Button
              type="primary"
              icon={<ApiOutlined />}
              onClick={() => testConnection('china_zhipu')}
              loading={testResults['china_zhipu']?.status === 'testing'}
            >
              {t('llm.actions.testConnection')}
            </Button>
          </Space>
        </TabPane>

        <TabPane tab={t('llm.baidu.title')} key="baidu">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_baidu')}
          </div>
          
          <Row gutter={16}>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'baidu_api_key'], t('llm.baidu.apiKey'))}
            </Col>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'baidu_secret_key'], t('llm.baidu.secretKey'))}
            </Col>
            <Col span={8}>
              <Form.Item
                name={['china_config', 'baidu_model']}
                label={t('llm.baidu.model')}
                rules={[{ required: true, message: t('llm.baidu.modelRequired') }]}
              >
                <Input placeholder={t('llm.baidu.modelPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          
          <Space>
            <Button
              type="primary"
              icon={<ApiOutlined />}
              onClick={() => testConnection('china_baidu')}
              loading={testResults['china_baidu']?.status === 'testing'}
            >
              {t('llm.actions.testConnection')}
            </Button>
          </Space>
        </TabPane>

        <TabPane tab={t('llm.hunyuan.title')} key="hunyuan">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_hunyuan')}
          </div>
          
          <Row gutter={16}>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'hunyuan_secret_id'], t('llm.hunyuan.secretId'))}
            </Col>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'hunyuan_secret_key'], t('llm.hunyuan.secretKey'))}
            </Col>
            <Col span={8}>
              <Form.Item
                name={['china_config', 'hunyuan_model']}
                label={t('llm.hunyuan.model')}
                rules={[{ required: true, message: t('llm.hunyuan.modelRequired') }]}
              >
                <Input placeholder={t('llm.hunyuan.modelPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          
          <Space>
            <Button
              type="primary"
              icon={<ApiOutlined />}
              onClick={() => testConnection('china_hunyuan')}
              loading={testResults['china_hunyuan']?.status === 'testing'}
            >
              {t('llm.actions.testConnection')}
            </Button>
          </Space>
        </TabPane>
      </Tabs>
      
      <Divider />
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name={['china_config', 'timeout']}
            label={t('llm.china.timeout')}
            rules={[{ required: true, type: 'number', min: 1, max: 300 }]}
          >
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['china_config', 'max_retries']}
            label={t('llm.china.maxRetries')}
            rules={[{ required: true, type: 'number', min: 0, max: 10 }]}
          >
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );

  const renderGeneralConfig = () => (
    <Card title={t('llm.general.title')}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="default_method"
            label={t('llm.general.defaultMethod')}
            rules={[{ required: true, message: t('llm.general.defaultMethodRequired') }]}
          >
            <Select placeholder={t('llm.general.defaultMethodPlaceholder')}>
              {methods.map(method => (
                <Option key={method.method} value={method.method} disabled={!method.enabled}>
                  {getMethodName(method.method)}
                  {!method.configured && <Tag color="orange" style={{ marginLeft: 8 }}>{t('llm.status.notConfigured')}</Tag>}
                  {!method.enabled && <Tag color="red" style={{ marginLeft: 8 }}>{t('llm.status.disabled')}</Tag>}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name="enabled_methods"
            label={t('llm.general.enabledMethods')}
            rules={[{ required: true, message: t('llm.general.enabledMethodsRequired') }]}
          >
            <Select
              mode="multiple"
              placeholder={t('llm.general.enabledMethodsPlaceholder')}
              style={{ width: '100%' }}
            >
              {methods.map(method => (
                <Option key={method.method} value={method.method}>
                  {getMethodName(method.method)}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );

  // ==================== Main Render ====================

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>{t('llm.loadingConfig')}</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SettingOutlined /> {t('llm.title')}
        </Title>
        <Paragraph>
          {t('llm.subtitle')}
        </Paragraph>
      </div>

      {validationResult && !validationResult.valid && (
        <Alert
          type="error"
          message={t('llm.validationFailed')}
          description={
            <ul>
              {validationResult.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          }
          style={{ marginBottom: 16 }}
          closable
        />
      )}

      {validationResult && validationResult.warnings.length > 0 && (
        <Alert
          type="warning"
          message={t('llm.validationWarnings')}
          description={
            <ul>
              {validationResult.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          }
          style={{ marginBottom: 16 }}
          closable
        />
      )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
      >
        <Tabs defaultActiveKey="general">
          <TabPane tab={<span><SettingOutlined />{t('llm.tabs.general')}</span>} key="general">
            {renderGeneralConfig()}
          </TabPane>
          
          <TabPane tab={<span><DatabaseOutlined />{t('llm.tabs.local')}</span>} key="local">
            {renderLocalConfig()}
          </TabPane>
          
          <TabPane tab={<span><CloudOutlined />{t('llm.tabs.cloud')}</span>} key="cloud">
            {renderCloudConfig()}
          </TabPane>
          
          <TabPane tab={<span><ApiOutlined />{t('llm.tabs.china')}</span>} key="china">
            {renderChinaConfig()}
          </TabPane>
        </Tabs>

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Space size="middle">
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
              size="large"
            >
              {t('llm.actions.saveConfig')}
            </Button>
            
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              size="large"
            >
              {t('llm.actions.reset')}
            </Button>
            
            <Button
              icon={<ReloadOutlined />}
              onClick={handleHotReload}
              size="large"
            >
              {t('llm.actions.hotReload')}
            </Button>
            
            <Button
              icon={<CheckCircleOutlined />}
              onClick={refreshHealth}
              size="large"
            >
              {t('llm.actions.refreshStatus')}
            </Button>
          </Space>
        </div>
      </Form>
    </div>
  );
};

export default LLMConfigPage;