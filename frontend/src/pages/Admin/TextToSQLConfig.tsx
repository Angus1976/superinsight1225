/**
 * Text-to-SQL Configuration Page
 * 
 * Provides interface for configuring Text-to-SQL methods,
 * testing SQL generation, and managing third-party plugins.
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
      message.error('加载配置失败');
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
      
      message.success('配置保存成功');
      await loadInitialData();
    } catch (error) {
      console.error('Failed to save configuration:', error);
      message.error('保存配置失败');
    } finally {
      setSaving(false);
    }
  };

  const handleSwitchMethod = async (method: MethodType) => {
    try {
      const result = await textToSqlService.switchMethod(method);
      message.success(`已切换到 ${getMethodDisplayName(method)} 方法 (${result.switch_time_ms.toFixed(2)}ms)`);
      await loadInitialData();
    } catch (error) {
      console.error('Failed to switch method:', error);
      message.error('切换方法失败');
    }
  };

  // ==================== Test Handlers ====================

  const handleTestGenerate = async () => {
    if (!testQuery.trim()) {
      message.warning('请输入测试查询');
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
        message.success('SQL 生成成功');
      } else {
        message.warning('SQL 生成失败');
      }
    } catch (error) {
      console.error('Test generation failed:', error);
      message.error('测试生成失败');
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
      title: '删除插件',
      content: `确定要删除插件 "${name}" 吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await textToSqlService.unregisterPlugin(name);
          message.success('插件删除成功');
          await refreshPlugins();
        } catch (error) {
          console.error('Failed to delete plugin:', error);
          message.error('删除插件失败');
        }
      },
    });
  };

  const handleTogglePlugin = async (name: string, enabled: boolean) => {
    try {
      if (enabled) {
        await textToSqlService.enablePlugin(name);
        message.success(`插件 "${name}" 已启用`);
      } else {
        await textToSqlService.disablePlugin(name);
        message.success(`插件 "${name}" 已禁用`);
      }
      await refreshPlugins();
    } catch (error) {
      console.error('Failed to toggle plugin:', error);
      message.error('操作失败');
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
        message.success('插件更新成功');
      } else {
        await textToSqlService.registerPlugin(pluginConfig);
        message.success('插件注册成功');
      }
      
      setPluginModalVisible(false);
      await refreshPlugins();
    } catch (error) {
      console.error('Failed to save plugin:', error);
      message.error('保存插件失败');
    }
  };

  const handleCheckPluginHealth = async (name: string) => {
    try {
      const result = await textToSqlService.getPluginHealth(name);
      if (result.healthy) {
        message.success(`插件 "${name}" 健康状态正常`);
      } else {
        message.warning(`插件 "${name}" 健康检查失败`);
      }
      await refreshPlugins();
    } catch (error) {
      console.error('Failed to check plugin health:', error);
      message.error('健康检查失败');
    }
  };

  // ==================== Render Methods ====================

  const renderMethodsConfig = () => (
    <Card title="方法配置" extra={
      <Button icon={<ReloadOutlined />} onClick={loadInitialData}>刷新</Button>
    }>
      <Form form={form} layout="vertical">
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="default_method"
              label="默认方法"
              rules={[{ required: true, message: '请选择默认方法' }]}
            >
              <Select placeholder="选择默认方法" onChange={(v) => handleSwitchMethod(v)}>
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
              label="自动方法选择"
              valuePropName="checked"
            >
              <Switch checkedChildren="开启" unCheckedChildren="关闭" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="fallback_enabled"
              label="失败回退"
              valuePropName="checked"
            >
              <Switch checkedChildren="开启" unCheckedChildren="关闭" />
            </Form.Item>
          </Col>
        </Row>
      </Form>

      <Divider>可用方法</Divider>
      
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
                  text={method.is_available ? '可用' : '不可用'} 
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
    <Card title="SQL 生成测试">
      <Row gutter={16}>
        <Col span={16}>
          <Form.Item label="自然语言查询">
            <TextArea
              rows={3}
              placeholder="输入自然语言查询，例如：查询所有用户的订单数量"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="测试方法">
            <Select
              placeholder="使用默认方法"
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
            测试生成
          </Button>
        </Col>
      </Row>

      {testResult && (
        <>
          <Divider>生成结果</Divider>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item label="生成的 SQL">
                <TextArea
                  rows={6}
                  value={testResult.sql || '(无结果)'}
                  readOnly
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic
                  title="使用方法"
                  value={testResult.method_used}
                  prefix={testResult.success ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <ExclamationCircleOutlined style={{ color: '#faad14' }} />}
                />
                <Statistic
                  title="置信度"
                  value={testResult.confidence * 100}
                  precision={1}
                  suffix="%"
                />
                <Statistic
                  title="执行时间"
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
        title: '插件名称',
        dataIndex: 'name',
        key: 'name',
        render: (name: string) => <Text strong>{name}</Text>,
      },
      {
        title: '连接类型',
        dataIndex: 'connection_type',
        key: 'connection_type',
        render: (type: ConnectionType) => (
          <Tag color="blue">{getConnectionTypeDisplayName(type)}</Tag>
        ),
      },
      {
        title: '支持数据库',
        dataIndex: 'supported_db_types',
        key: 'supported_db_types',
        render: (types: string[]) => (
          <Space wrap>
            {types.map(t => <Tag key={t}>{t}</Tag>)}
          </Space>
        ),
      },
      {
        title: '健康状态',
        dataIndex: 'is_healthy',
        key: 'is_healthy',
        render: (healthy: boolean) => (
          <Badge status={healthy ? 'success' : 'error'} text={healthy ? '健康' : '异常'} />
        ),
      },
      {
        title: '启用状态',
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
        title: '操作',
        key: 'actions',
        render: (_: unknown, record: PluginInfo) => (
          <Space>
            <Tooltip title="健康检查">
              <Button
                type="text"
                icon={<CheckCircleOutlined />}
                onClick={() => handleCheckPluginHealth(record.name)}
              />
            </Tooltip>
            <Tooltip title="编辑">
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={() => handleEditPlugin(record)}
              />
            </Tooltip>
            <Tooltip title="删除">
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
        title="第三方插件管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddPlugin}>
            添加插件
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={plugins}
          rowKey="name"
          pagination={false}
          locale={{ emptyText: '暂无插件' }}
        />
      </Card>
    );
  };

  const renderStatistics = () => (
    <Card title="统计信息">
      {statistics && (
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title="总调用次数" value={statistics.total_calls} />
          </Col>
          <Col span={6}>
            <Statistic title="当前方法" value={getMethodDisplayName(statistics.current_method as MethodType)} />
          </Col>
          <Col span={6}>
            <Statistic 
              title="平均切换时间" 
              value={statistics.average_switch_time_ms} 
              precision={2}
              suffix="ms"
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="最大切换时间" 
              value={statistics.max_switch_time_ms} 
              precision={2}
              suffix="ms"
            />
          </Col>
        </Row>
      )}
      
      {statistics && Object.keys(statistics.method_calls).length > 0 && (
        <>
          <Divider>方法调用分布</Divider>
          <Row gutter={16}>
            {Object.entries(statistics.method_calls).map(([method, count]) => (
              <Col span={6} key={method}>
                <Statistic 
                  title={getMethodDisplayName(method as MethodType)} 
                  value={count} 
                  suffix="次"
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
      title={editingPlugin ? '编辑插件' : '添加插件'}
      open={pluginModalVisible}
      onOk={handlePluginModalOk}
      onCancel={() => setPluginModalVisible(false)}
      width={600}
    >
      <Form form={pluginForm} layout="vertical">
        <Form.Item
          name="name"
          label="插件名称"
          rules={[{ required: true, message: '请输入插件名称' }]}
        >
          <Input placeholder="例如：vanna-ai" disabled={!!editingPlugin} />
        </Form.Item>
        
        <Form.Item
          name="connection_type"
          label="连接类型"
          rules={[{ required: true, message: '请选择连接类型' }]}
        >
          <Select placeholder="选择连接类型">
            <Option value="rest_api">REST API</Option>
            <Option value="grpc">gRPC</Option>
            <Option value="local_sdk">本地 SDK</Option>
          </Select>
        </Form.Item>
        
        <Form.Item
          name="endpoint"
          label="API 端点"
          rules={[{ required: true, message: '请输入 API 端点' }]}
        >
          <Input placeholder="例如：http://localhost:8080/api/v1" />
        </Form.Item>
        
        <Form.Item
          name="api_key"
          label="API Key"
        >
          <Input.Password placeholder="可选，用于认证" />
        </Form.Item>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="timeout"
              label="超时时间 (秒)"
              rules={[{ required: true, type: 'number', min: 1, max: 300 }]}
            >
              <InputNumber min={1} max={300} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="enabled"
              label="启用状态"
              valuePropName="checked"
            >
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
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
        <div style={{ marginTop: 16 }}>加载配置中...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SettingOutlined /> Text-to-SQL 配置
        </Title>
        <Paragraph>
          配置和管理 Text-to-SQL 方法，包括模板填充、LLM 生成、混合方法和第三方工具。
        </Paragraph>
      </div>

      <Tabs defaultActiveKey="methods">
        <TabPane tab={<span><SettingOutlined />方法配置</span>} key="methods">
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {renderMethodsConfig()}
            {renderStatistics()}
          </Space>
        </TabPane>
        
        <TabPane tab={<span><PlayCircleOutlined />SQL 测试</span>} key="test">
          {renderTestPanel()}
        </TabPane>
        
        <TabPane tab={<span><ApiOutlined />第三方插件</span>} key="plugins">
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
            保存配置
          </Button>
          
          <Button
            icon={<ReloadOutlined />}
            onClick={loadInitialData}
            size="large"
          >
            刷新
          </Button>
        </Space>
      </div>

      {renderPluginModal()}
    </div>
  );
};

export default TextToSQLConfigPage;
