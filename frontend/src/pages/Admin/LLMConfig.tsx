/**
 * LLM Configuration Page
 * 
 * Provides a comprehensive interface for configuring LLM providers including
 * local Ollama, cloud providers (OpenAI, Azure), and Chinese LLM services.
 */

import React, { useState, useEffect } from 'react';
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
      message.error('加载配置失败');
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
      message.error('刷新健康状态失败');
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
        message.error('配置验证失败，请检查错误信息');
        return;
      }

      // Save configuration
      const updatedConfig = await llmService.updateConfig(values);
      setConfig(updatedConfig);
      message.success('配置保存成功');

      // Refresh health status
      await refreshHealth();
    } catch (error) {
      console.error('Failed to save configuration:', error);
      message.error('保存配置失败');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    Modal.confirm({
      title: '重置配置',
      content: '确定要重置所有配置吗？未保存的更改将丢失。',
      onOk: () => {
        if (config) {
          form.setFieldsValue(config);
          setValidationResult(null);
          message.info('配置已重置');
        }
      },
    });
  };

  const handleHotReload = async () => {
    try {
      const reloadedConfig = await llmService.hotReload();
      setConfig(reloadedConfig);
      form.setFieldsValue(reloadedConfig);
      message.success('配置热加载成功');
      await refreshHealth();
    } catch (error) {
      console.error('Failed to hot reload configuration:', error);
      message.error('热加载失败');
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
          message: result.error || '连接成功',
          latency: result.latency_ms,
        }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [method]: {
          method,
          status: 'error',
          message: error instanceof Error ? error.message : '连接失败',
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
          placeholder={placeholder || `请输入${label}`}
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
      return <Badge status="processing" text="测试中..." />;
    }
    
    if (test?.status === 'success') {
      return <Badge status="success" text={`连接成功 (${test.latency}ms)`} />;
    }
    
    if (test?.status === 'error') {
      return <Badge status="error" text={test.message || '连接失败'} />;
    }
    
    if (health?.available) {
      return <Badge status="success" text={`在线 (${health.latency_ms}ms)`} />;
    }
    
    if (health?.error) {
      return <Badge status="error" text={health.error} />;
    }
    
    return <Badge status="default" text="未知" />;
  };

  // ==================== Render Methods ====================

  const renderLocalConfig = () => (
    <Card title="本地 Ollama 配置" extra={renderHealthBadge('local_ollama')}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'ollama_url']}
            label="Ollama 服务地址"
            rules={[{ required: true, message: '请输入 Ollama 服务地址' }]}
          >
            <Input placeholder="http://localhost:11434" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'default_model']}
            label="默认模型"
            rules={[{ required: true, message: '请输入默认模型名称' }]}
          >
            <Input placeholder="llama2" />
          </Form.Item>
        </Col>
      </Row>
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'timeout']}
            label="超时时间 (秒)"
            rules={[{ required: true, type: 'number', min: 1, max: 300 }]}
          >
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['local_config', 'max_retries']}
            label="最大重试次数"
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
          测试连接
        </Button>
      </Space>
    </Card>
  );

  const renderCloudConfig = () => (
    <Card title="云端 LLM 配置">
      <Tabs defaultActiveKey="openai">
        <TabPane tab={<span><CloudOutlined />OpenAI</span>} key="openai">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('cloud_openai')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              {renderApiKeyInput(['cloud_config', 'openai_api_key'], 'OpenAI API Key')}
            </Col>
            <Col span={12}>
              <Form.Item
                name={['cloud_config', 'openai_base_url']}
                label="API 基础地址"
                rules={[{ required: true, message: '请输入 API 基础地址' }]}
              >
                <Input placeholder="https://api.openai.com/v1" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name={['cloud_config', 'openai_model']}
                label="默认模型"
                rules={[{ required: true, message: '请输入默认模型' }]}
              >
                <Input placeholder="gpt-3.5-turbo" />
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
                  测试连接
                </Button>
              </Space>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<span><CloudOutlined />Azure OpenAI</span>} key="azure">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('cloud_azure')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name={['cloud_config', 'azure_endpoint']}
                label="Azure 端点"
              >
                <Input placeholder="https://your-resource.openai.azure.com/" />
              </Form.Item>
            </Col>
            <Col span={12}>
              {renderApiKeyInput(['cloud_config', 'azure_api_key'], 'Azure API Key')}
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name={['cloud_config', 'azure_deployment']}
                label="部署名称"
              >
                <Input placeholder="gpt-35-turbo" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name={['cloud_config', 'azure_api_version']}
                label="API 版本"
                rules={[{ required: true, message: '请输入 API 版本' }]}
              >
                <Input placeholder="2023-12-01-preview" />
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
                  测试连接
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
            label="超时时间 (秒)"
            rules={[{ required: true, type: 'number', min: 1, max: 300 }]}
          >
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['cloud_config', 'max_retries']}
            label="最大重试次数"
            rules={[{ required: true, type: 'number', min: 0, max: 10 }]}
          >
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );

  const renderChinaConfig = () => (
    <Card title="中国 LLM 配置">
      <Tabs defaultActiveKey="qwen">
        <TabPane tab="通义千问" key="qwen">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_qwen')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              {renderApiKeyInput(['china_config', 'qwen_api_key'], '千问 API Key')}
            </Col>
            <Col span={12}>
              <Form.Item
                name={['china_config', 'qwen_model']}
                label="默认模型"
                rules={[{ required: true, message: '请输入默认模型' }]}
              >
                <Input placeholder="qwen-turbo" />
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
              测试连接
            </Button>
          </Space>
        </TabPane>

        <TabPane tab="智谱 GLM" key="zhipu">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_zhipu')}
          </div>
          
          <Row gutter={16}>
            <Col span={12}>
              {renderApiKeyInput(['china_config', 'zhipu_api_key'], '智谱 API Key')}
            </Col>
            <Col span={12}>
              <Form.Item
                name={['china_config', 'zhipu_model']}
                label="默认模型"
                rules={[{ required: true, message: '请输入默认模型' }]}
              >
                <Input placeholder="glm-4" />
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
              测试连接
            </Button>
          </Space>
        </TabPane>

        <TabPane tab="文心一言" key="baidu">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_baidu')}
          </div>
          
          <Row gutter={16}>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'baidu_api_key'], '百度 API Key')}
            </Col>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'baidu_secret_key'], '百度 Secret Key')}
            </Col>
            <Col span={8}>
              <Form.Item
                name={['china_config', 'baidu_model']}
                label="默认模型"
                rules={[{ required: true, message: '请输入默认模型' }]}
              >
                <Input placeholder="ernie-bot-turbo" />
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
              测试连接
            </Button>
          </Space>
        </TabPane>

        <TabPane tab="腾讯混元" key="hunyuan">
          <div style={{ marginBottom: 16 }}>
            {renderHealthBadge('china_hunyuan')}
          </div>
          
          <Row gutter={16}>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'hunyuan_secret_id'], '腾讯云 Secret ID')}
            </Col>
            <Col span={8}>
              {renderApiKeyInput(['china_config', 'hunyuan_secret_key'], '腾讯云 Secret Key')}
            </Col>
            <Col span={8}>
              <Form.Item
                name={['china_config', 'hunyuan_model']}
                label="默认模型"
                rules={[{ required: true, message: '请输入默认模型' }]}
              >
                <Input placeholder="hunyuan-lite" />
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
              测试连接
            </Button>
          </Space>
        </TabPane>
      </Tabs>
      
      <Divider />
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name={['china_config', 'timeout']}
            label="超时时间 (秒)"
            rules={[{ required: true, type: 'number', min: 1, max: 300 }]}
          >
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name={['china_config', 'max_retries']}
            label="最大重试次数"
            rules={[{ required: true, type: 'number', min: 0, max: 10 }]}
          >
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );

  const renderGeneralConfig = () => (
    <Card title="通用配置">
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="default_method"
            label="默认 LLM 方法"
            rules={[{ required: true, message: '请选择默认 LLM 方法' }]}
          >
            <Select placeholder="选择默认方法">
              {methods.map(method => (
                <Option key={method.method} value={method.method} disabled={!method.enabled}>
                  {getMethodName(method.method)}
                  {!method.configured && <Tag color="orange" style={{ marginLeft: 8 }}>未配置</Tag>}
                  {!method.enabled && <Tag color="red" style={{ marginLeft: 8 }}>已禁用</Tag>}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name="enabled_methods"
            label="启用的方法"
            rules={[{ required: true, message: '请选择至少一个启用的方法' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择启用的方法"
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
        <div style={{ marginTop: 16 }}>加载配置中...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SettingOutlined /> LLM 配置管理
        </Title>
        <Paragraph>
          配置和管理各种 LLM 提供商，包括本地 Ollama、云端服务和中国 LLM 服务。
        </Paragraph>
      </div>

      {validationResult && !validationResult.valid && (
        <Alert
          type="error"
          message="配置验证失败"
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
          message="配置警告"
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
          <TabPane tab={<span><SettingOutlined />通用配置</span>} key="general">
            {renderGeneralConfig()}
          </TabPane>
          
          <TabPane tab={<span><DatabaseOutlined />本地 LLM</span>} key="local">
            {renderLocalConfig()}
          </TabPane>
          
          <TabPane tab={<span><CloudOutlined />云端 LLM</span>} key="cloud">
            {renderCloudConfig()}
          </TabPane>
          
          <TabPane tab={<span><ApiOutlined />中国 LLM</span>} key="china">
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
              保存配置
            </Button>
            
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              size="large"
            >
              重置
            </Button>
            
            <Button
              icon={<ReloadOutlined />}
              onClick={handleHotReload}
              size="large"
            >
              热加载
            </Button>
            
            <Button
              icon={<CheckCircleOutlined />}
              onClick={refreshHealth}
              size="large"
            >
              刷新状态
            </Button>
          </Space>
        </div>
      </Form>
    </div>
  );
};

export default LLMConfigPage;