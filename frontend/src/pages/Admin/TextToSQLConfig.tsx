/**
 * Text-to-SQL Configuration Page
 * 
 * Provides interface for configuring Text-to-SQL methods,
 * testing SQL generation, and managing third-party plugins.
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
  Table,
  Badge,
  Tooltip,
  Progress,
  Statistic,
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ApiOutlined,
  CodeOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  SyncOutlined,
} from '@ant-design/icons';

import {
  textToSqlService,
  MethodType,
  ConnectionType,
  MethodInfo,
  PluginInfo,
  PluginConfig,
  TextToSQLConfig,
  GenerateResponse,
  SwitcherStatistics,
  getMethodDisplayName,
  getMethodDescription,
  getConnectionTypeDisplayName,
} from '@/services/textToSql';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { TextArea } = Input;

// ==================== Component ====================

const TextToSQLConfigPage: React.FC = () => {
  const { t } = useTranslation('admin');
  const [form] = Form.useForm();
  const [pluginForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  
  // Data states
  const [config, setConfig] = useState<TextToSQLConfig | null>(null);
  const [methods, setMethods] = useState<MethodInfo[]>([]);
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [statistics, setStatistics] = useState<SwitcherStatistics | null>(null);
  
  // Test states
  const [testQuery, setTestQuery] = useState('');
  const [testMethod, setTestMethod] = useState<MethodType | undefined>();
  const [testResult, setTestResult] = useState<GenerateResponse | null>(null);
  
  // Plugin modal states
  const [pluginModalVisible, setPluginModalVisible] = useState(false);
  const [editingPlugin, setEditingPlugin] = useState<PluginInfo | null>(null);

  // ==================== Effects ====================

  useEffect(() => {
    loadInitialData();
  }, []);

  // ==================== Data Loading ====================

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [configRes, methodsData, pluginsData, statsRes] = await Promise.all([
        textToSqlService.getConfig(),
        textToSqlService.getMethods(),
        textToSqlService.getPlugins(),
        textToSqlService.getStatistics(),
      ]);

      setConfig(configRes.config);
      setMethods(methodsData);
      setPlugins(pluginsData);
      setStatistics(statsRes.statistics);
      
      form.setFieldsValue({
        default_method: configRes.config.default_method,
        auto_select_enabled: configRes.config.auto_select_enabled,
        fallback_enabled: configRes.config.fallback_enabled,
      });
    } catch (error) {
      console.error('Failed to load Text-to-SQL configuration:', error);
      message.error(t('textToSql.loadConfigFailed'));
    } finally {
      setLoading(false);
    }
  };

  const refreshPlugins = async () => {
    try {
      const pluginsData = await textToSqlService.getPlugins();
      setPlugins(pluginsData);
    } catch (error) {
      console.error('Failed to refresh plugins:', error);
    }
  };

  // ==================== Form Handlers ====================

  const handleSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();
      
      await textToSqlService.updateConfig({
        default_method: values.default_method,
        auto_select_enabled: values.auto_select_enabled,
        fallback_enabled: values.fallback_enabled,
      });
      message.success(t('textToSql.saveConfigSuccess'));
      await loadInitialData();

    } catch (error) {
      console.error('Failed to save configuration:', error);
      message.error(t('textToSql.saveConfigFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleSwitchMethod = async (method: MethodType) => {
    try {
      const result = await textToSqlService.switchMethod(method);
      message.success(t('textToSql.switchMethodSuccess', {
        method: getMethodDisplayName(method),
        time: result.switch_time_ms.toFixed(2)
      }));
      await loadInitialData();
    } catch (error) {
      console.error('Failed to switch method:', error);
      message.error(t('textToSql.switchMethodFailed'));
    }
  };

  // ==================== Test Handlers ====================

  const handleTestGenerate = async () => {
    if (!testQuery.trim()) {
      message.warning(t('textToSql.testQueryRequired'));
      return;
    }
    
    setTesting(true);
    setTestResult(null);
    
    try {
      const result = await textToSqlService.testGenerate({
        query: testQuery,
        method: testMethod,
        db_type: 'postgresql',
      });
      setTestResult(result);
      if (result.success) {
        message.success(t('textToSql.sqlGenerationSuccess'));
      } else {
        message.warning(t('textToSql.sqlGenerationFailed'));
      }

    } catch (error) {
      console.error('Test generation failed:', error);
      message.error(t('textToSql.testGenerationFailed'));
    } finally {
      setTesting(false);
    }
  };

  // ==================== Plugin Handlers ====================

  const handleAddPlugin = () => {
    setEditingPlugin(null);
    pluginForm.resetFields();
    pluginForm.setFieldsValue({
      connection_type: 'rest_api',
      timeout: 30,
      enabled: true,
      extra_config: {},
    });
    setPluginModalVisible(true);
  };

  const handleEditPlugin = (plugin: PluginInfo) => {
    setEditingPlugin(plugin);
    pluginForm.setFieldsValue({
      name: plugin.name,
      connection_type: plugin.connection_type,
      timeout: 30,
      enabled: plugin.is_enabled,
    });
    setPluginModalVisible(true);
  };

  const handleDeletePlugin = async (name: string) => {
    Modal.confirm({
      title: t('textToSql.deletePlugin'),
      content: t('textToSql.confirmDeletePlugin', { name }),
      okText: t('textToSql.pluginsTable.delete'),
      okType: 'danger',
      cancelText: t('textToSql.cancel'),
      onOk: async () => {
        try {
          await textToSqlService.unregisterPlugin(name);
          message.success(t('textToSql.deletePluginSuccess'));
          await refreshPlugins();
        } catch (error) {
          console.error('Failed to delete plugin:', error);
          message.error(t('textToSql.deletePluginFailed'));
        }
      },
    });
  };

  const handleTogglePlugin = async (name: string, enabled: boolean) => {
    try {
      if (enabled) {
        await textToSqlService.enablePlugin(name);
        message.success(t('textToSql.pluginEnabled', { name }));
      } else {
        await textToSqlService.disablePlugin(name);
        message.success(t('textToSql.pluginDisabled', { name }));
      }
      await refreshPlugins();
    } catch (error) {
      console.error('Failed to toggle plugin:', error);
      message.error(t('textToSql.operationFailed'));
    }
  };

  const handlePluginModalOk = async () => {
    try {
      const values = await pluginForm.validateFields();
      
      const pluginConfig: PluginConfig = {
        name: values.name,
        connection_type: values.connection_type,
        endpoint: values.endpoint,
        api_key: values.api_key,
        timeout: values.timeout,
        enabled: values.enabled,
        extra_config: values.extra_config || {},
      };
      
      if (editingPlugin) {
        await textToSqlService.updatePlugin(editingPlugin.name, pluginConfig);
        message.success(t('textToSql.pluginUpdateSuccess'));
      } else {
        await textToSqlService.registerPlugin(pluginConfig);
        message.success(t('textToSql.pluginRegisterSuccess'));
      }

      setPluginModalVisible(false);
      await refreshPlugins();
    } catch (error) {
      console.error('Failed to save plugin:', error);
      message.error(t('textToSql.savePluginFailed'));
    }
  };

  const handleCheckPluginHealth = async (name: string) => {
    try {
      const result = await textToSqlService.getPluginHealth(name);
      if (result.healthy) {
        message.success(t('textToSql.pluginHealthCheckSuccess', { name }));
      } else {
        message.warning(t('textToSql.pluginHealthCheckFailed', { name }));
      }
      await refreshPlugins();
    } catch (error) {
      console.error('Failed to check plugin health:', error);
      message.error(t('textToSql.healthCheckFailed'));
    }
  };

  // ==================== Render Methods ====================

  const renderMethodsConfig = () => (
    <Card title={t('textToSql.methodsConfig')} extra={
      <Button icon={<ReloadOutlined />} onClick={loadInitialData}>{t('textToSql.refresh')}</Button>
    }>
      <Form form={form} layout="vertical">
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="default_method"
              label={t('textToSql.defaultMethod')}
              rules={[{ required: true, message: t('textToSql.selectDefaultMethod') }]}
            >
              <Select placeholder={t('textToSql.selectMethodPlaceholder')} onChange={(v) => handleSwitchMethod(v)}>
                <Option value="template">
                  <Space>
                    <CodeOutlined />
                    {getMethodDisplayName('template')}
                  </Space>
                </Option>
                <Option value="llm">
                  <Space>
                    <ThunderboltOutlined />
                    {getMethodDisplayName('llm')}
                  </Space>
                </Option>
                <Option value="hybrid">
                  <Space>
                    <SyncOutlined />
                    {getMethodDisplayName('hybrid')}
                  </Space>
                </Option>
                <Option value="third_party">
                  <Space>
                    <ApiOutlined />
                    {getMethodDisplayName('third_party')}
                  </Space>
                </Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="auto_select_enabled"
              label={t('textToSql.autoSelectEnabled')}
              valuePropName="checked"
            >
              <Switch checkedChildren={t('textToSql.on')} unCheckedChildren={t('textToSql.off')} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="fallback_enabled"
              label={t('textToSql.fallbackEnabled')}
              valuePropName="checked"
            >
              <Switch checkedChildren={t('textToSql.on')} unCheckedChildren={t('textToSql.off')} />
            </Form.Item>
          </Col>
        </Row>
      </Form>

      <Divider>{t('textToSql.availableMethods')}</Divider>
      
      <Row gutter={[16, 16]}>
        {methods.map(method => (
          <Col span={12} key={method.name}>
            <Card 
              size="small"
              title={
                <Space>
                  {method.type === 'template' && <CodeOutlined />}
                  {method.type === 'llm' && <ThunderboltOutlined />}
                  {method.type === 'hybrid' && <SyncOutlined />}
                  {method.type === 'third_party' && <ApiOutlined />}
                  {method.name}
                </Space>
              }
              extra={
                <Badge
                  status={method.is_available ? 'success' : 'default'}
                  text={method.is_available ? t('textToSql.available') : t('textToSql.unavailable')}
                />
              }
            >
              <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                {method.description}
              </Paragraph>
              <Space wrap>
                {method.supported_db_types.map(db => (
                  <Tag key={db} color="blue">{db}</Tag>
                ))}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );

  const renderTestPanel = () => (
    <Card title={t('textToSql.sqlGenerationTest')}>
      <Row gutter={16}>
        <Col span={16}>
          <Form.Item label={t('textToSql.naturalLanguageQuery')}>
            <TextArea
              rows={3}
              placeholder={t('textToSql.queryPlaceholder')}
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label={t('textToSql.testMethod')}>
            <Select
              placeholder={t('textToSql.useDefaultMethod')}
              allowClear
              value={testMethod}
              onChange={setTestMethod}
              style={{ width: '100%' }}
            >
              <Option value="template">{getMethodDisplayName('template')}</Option>
              <Option value="llm">{getMethodDisplayName('llm')}</Option>
              <Option value="hybrid">{getMethodDisplayName('hybrid')}</Option>
            </Select>
          </Form.Item>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleTestGenerate}
            loading={testing}
            block
          >
            {t('textToSql.testGenerate')}
          </Button>
        </Col>
      </Row>

      {testResult && (
        <>
          <Divider>{t('textToSql.generationResult')}</Divider>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item label={t('textToSql.generatedSql')}>
                <TextArea
                  rows={6}
                  value={testResult.sql || t('textToSql.noResult')}
                  readOnly
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic
                  title={t('textToSql.methodUsed')}
                  value={testResult.method_used}
                  prefix={testResult.success ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <ExclamationCircleOutlined style={{ color: '#faad14' }} />}
                />
                <Statistic
                  title={t('textToSql.confidence')}
                  value={testResult.confidence * 100}
                  precision={1}
                  suffix="%"
                />
                <Statistic
                  title={t('textToSql.executionTime')}
                  value={testResult.execution_time_ms}
                  precision={2}
                  suffix="ms"
                />
              </Space>
            </Col>
          </Row>
        </>
      )}
    </Card>
  );

  const renderPluginsPanel = () => {
    const columns = [
      {
        title: t('textToSql.pluginName'),
        dataIndex: 'name',
        key: 'name',
        render: (name: string) => <Text strong>{name}</Text>,
      },
      {
        title: t('textToSql.connectionType'),
        dataIndex: 'connection_type',
        key: 'connection_type',
        render: (type: ConnectionType) => (
          <Tag color="blue">{getConnectionTypeDisplayName(type)}</Tag>
        ),
      },
      {
        title: t('textToSql.supportedDatabases'),
        dataIndex: 'supported_db_types',
        key: 'supported_db_types',
        render: (types: string[]) => (
          <Space wrap>
            {types.map(t => <Tag key={t}>{t}</Tag>)}
          </Space>
        ),
      },
      {
        title: t('textToSql.healthStatus'),
        dataIndex: 'is_healthy',
        key: 'is_healthy',
        render: (healthy: boolean) => (
          <Badge status={healthy ? 'success' : 'error'} text={healthy ? t('textToSql.pluginsTable.healthy') : t('textToSql.pluginsTable.unhealthy')} />
        ),
      },
      {
        title: t('textToSql.enabledStatus'),
        dataIndex: 'is_enabled',
        key: 'is_enabled',
        render: (enabled: boolean, record: PluginInfo) => (
          <Switch
            checked={enabled}
            onChange={(checked) => handleTogglePlugin(record.name, checked)}
          />
        ),
      },
      {
        title: t('textToSql.actions'),
        key: 'actions',
        render: (_: unknown, record: PluginInfo) => (
          <Space>
            <Tooltip title={t('textToSql.healthCheck')}>
              <Button
                type="text"
                icon={<CheckCircleOutlined />}
                onClick={() => handleCheckPluginHealth(record.name)}
              />
            </Tooltip>
            <Tooltip title={t('textToSql.edit')}>
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={() => handleEditPlugin(record)}
              />
            </Tooltip>
            <Tooltip title={t('textToSql.delete')}>
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDeletePlugin(record.name)}
              />
            </Tooltip>
          </Space>
        ),
      },
    ];

    return (
      <Card
        title={t('textToSql.thirdPartyPlugins')}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddPlugin}>
            {t('textToSql.addPlugin')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={plugins}
          rowKey="name"
          pagination={false}
          locale={{ emptyText: t('textToSql.noPlugins') }}
        />
      </Card>
    );
  };

  const renderStatistics = () => (
    <Card title={t('textToSql.statistics')}>
      {statistics && (
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title={t('textToSql.totalCalls')} value={statistics.total_calls} />
          </Col>
          <Col span={6}>
            <Statistic title={t('textToSql.currentMethod')} value={getMethodDisplayName(statistics.current_method as MethodType)} />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('textToSql.averageSwitchTime')}
              value={statistics.average_switch_time_ms}
              precision={2}
              suffix="ms"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('textToSql.maxSwitchTime')}
              value={statistics.max_switch_time_ms}
              precision={2}
              suffix="ms"
            />
          </Col>
        </Row>
      )}
      
      {statistics && Object.keys(statistics.method_calls).length > 0 && (
        <>
          <Divider>{t('textToSql.methodUsage')}</Divider>
          <Row gutter={16}>
            {Object.entries(statistics.method_calls).map(([method, count]) => (
              <Col span={6} key={method}>
                <Statistic
                  title={getMethodDisplayName(method as MethodType)}
                  value={count}
                  suffix={t('textToSql.times')}
                />
              </Col>
            ))}
          </Row>
        </>
      )}
    </Card>
  );

  // ==================== Plugin Modal ====================

  const renderPluginModal = () => (
    <Modal
      title={editingPlugin ? t('textToSql.editPlugin') : t('textToSql.addPlugin')}
      open={pluginModalVisible}
      onOk={handlePluginModalOk}
      onCancel={() => setPluginModalVisible(false)}
      width={600}
    >
      <Form form={pluginForm} layout="vertical">
        <Form.Item
          name="name"
          label={t('textToSql.pluginName')}
          rules={[{ required: true, message: t('textToSql.pluginNameRequired') }]}
        >
          <Input placeholder={t('textToSql.pluginNamePlaceholder')} disabled={!!editingPlugin} />
        </Form.Item>
        
        <Form.Item
          name="connection_type"
          label={t('textToSql.connectionType')}
          rules={[{ required: true, message: t('textToSql.connectionTypeRequired') }]}
        >
          <Select placeholder={t('textToSql.connectionTypePlaceholder')}>
            <Option value="rest_api">{t('textToSql.restApi')}</Option>
            <Option value="grpc">gRPC</Option>
            <Option value="local_sdk">{t('textToSql.localSdk')}</Option>
          </Select>
        </Form.Item>
        
        <Form.Item
          name="endpoint"
          label={t('textToSql.apiEndpoint')}
          rules={[{ required: true, message: t('textToSql.apiEndpointRequired') }]}
        >
          <Input placeholder={t('textToSql.apiEndpointPlaceholder')} />
        </Form.Item>
        
        <Form.Item
          name="api_key"
          label="API Key"
        >
          <Input.Password placeholder={t('textToSql.apiKeyPlaceholder')} />
        </Form.Item>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="timeout"
              label={t('textToSql.timeout')}
              rules={[{ required: true, type: 'number', min: 1, max: 300, message: t('textToSql.timeoutRequired') }]}
            >
              <InputNumber min={1} max={300} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="enabled"
              label={t('textToSql.enabled')}
              valuePropName="checked"
            >
              <Switch checkedChildren={t('textToSql.enabledText')} unCheckedChildren={t('textToSql.disabledText')} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );

  // ==================== Main Render ====================

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>{t('textToSql.loadingConfig')}</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SettingOutlined /> {t('textToSql.title')}
        </Title>
        <Paragraph>
          {t('textToSql.subtitle')}
        </Paragraph>
      </div>

      <Tabs defaultActiveKey="methods">
        <TabPane tab={<span><SettingOutlined />{t('textToSql.methodsTab')}</span>} key="methods">
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {renderMethodsConfig()}
            {renderStatistics()}
          </Space>
        </TabPane>

        <TabPane tab={<span><PlayCircleOutlined />{t('textToSql.testTab')}</span>} key="test">
          {renderTestPanel()}
        </TabPane>

        <TabPane tab={<span><ApiOutlined />{t('textToSql.pluginsTab')}</span>} key="plugins">
          {renderPluginsPanel()}
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
            {t('textToSql.saveConfig')}
          </Button>

          <Button
            icon={<ReloadOutlined />}
            onClick={loadInitialData}
            size="large"
          >
            {t('textToSql.refresh')}
          </Button>
        </Space>
      </div>

      {renderPluginModal()}
    </div>
  );
};

export default TextToSQLConfigPage;
