/**
 * Annotation Plugins Configuration Page
 * 
 * Manages third-party annotation tool plugins including:
 * - Plugin registration and configuration
 * - Enable/disable controls
 * - Priority management
 * - Connection testing
 * - Usage statistics
 * 
 * Requirements: 9.1-9.7 - 插件配置界面
 */

import { useState, useCallback, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  message,
  Tooltip,
  Popconfirm,
  Statistic,
  Row,
  Col,
  Progress,
  Alert,
  Tabs,
  Descriptions,
  Badge,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  SettingOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Title } = Typography;

// Types
interface AnnotationPlugin {
  id: string;
  name: string;
  type: 'rest_api' | 'grpc' | 'websocket' | 'sdk';
  endpoint?: string;
  status: 'active' | 'inactive' | 'error';
  enabled: boolean;
  priority: number;
  config: Record<string, unknown>;
  supportedTypes: string[];
  createdAt: string;
  updatedAt: string;
  lastHealthCheck?: string;
  healthStatus?: 'healthy' | 'unhealthy' | 'unknown';
}

interface PluginStats {
  pluginId: string;
  totalCalls: number;
  successRate: number;
  avgLatencyMs: number;
  totalCost: number;
  lastCallAt?: string;
  errorCount: number;
}

// Mock data
const mockPlugins: AnnotationPlugin[] = [
  {
    id: 'plugin-1',
    name: 'Prodigy Adapter',
    type: 'rest_api',
    endpoint: 'http://localhost:8080/api',
    status: 'active',
    enabled: true,
    priority: 10,
    config: { apiKey: '***', timeout: 30000 },
    supportedTypes: ['ner', 'text_classification'],
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-10T12:00:00Z',
    lastHealthCheck: '2026-01-14T10:00:00Z',
    healthStatus: 'healthy',
  },
  {
    id: 'plugin-2',
    name: 'Doccano Integration',
    type: 'rest_api',
    endpoint: 'http://doccano.local:8000',
    status: 'inactive',
    enabled: false,
    priority: 5,
    config: { username: 'admin', projectId: 1 },
    supportedTypes: ['text_classification', 'sentiment'],
    createdAt: '2026-01-05T00:00:00Z',
    updatedAt: '2026-01-08T15:30:00Z',
    healthStatus: 'unknown',
  },
  {
    id: 'plugin-3',
    name: 'Custom ML Backend',
    type: 'grpc',
    endpoint: 'ml-backend.internal:50051',
    status: 'error',
    enabled: true,
    priority: 20,
    config: { modelVersion: 'v2.1', batchSize: 32 },
    supportedTypes: ['ner', 'sentiment', 'text_classification'],
    createdAt: '2026-01-03T00:00:00Z',
    updatedAt: '2026-01-12T09:00:00Z',
    lastHealthCheck: '2026-01-14T09:55:00Z',
    healthStatus: 'unhealthy',
  },
];

const mockStats: Record<string, PluginStats> = {
  'plugin-1': {
    pluginId: 'plugin-1',
    totalCalls: 15420,
    successRate: 98.5,
    avgLatencyMs: 245,
    totalCost: 125.50,
    lastCallAt: '2026-01-14T10:30:00Z',
    errorCount: 231,
  },
  'plugin-2': {
    pluginId: 'plugin-2',
    totalCalls: 0,
    successRate: 0,
    avgLatencyMs: 0,
    totalCost: 0,
    errorCount: 0,
  },
  'plugin-3': {
    pluginId: 'plugin-3',
    totalCalls: 8750,
    successRate: 85.2,
    avgLatencyMs: 520,
    totalCost: 87.25,
    lastCallAt: '2026-01-14T09:45:00Z',
    errorCount: 1295,
  },
};

const AnnotationPluginsPage: React.FC = () => {
  const { t } = useTranslation(['admin', 'common']);
  const [plugins, setPlugins] = useState<AnnotationPlugin[]>(mockPlugins);
  const [stats] = useState<Record<string, PluginStats>>(mockStats);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingPlugin, setEditingPlugin] = useState<AnnotationPlugin | null>(null);
  const [statsModalVisible, setStatsModalVisible] = useState(false);
  const [selectedPluginStats, setSelectedPluginStats] = useState<PluginStats | null>(null);
  const [testingPlugin, setTestingPlugin] = useState<string | null>(null);
  const [form] = Form.useForm();

  // Fetch plugins
  const fetchPlugins = useCallback(async () => {
    setLoading(true);
    try {
      // In real implementation, call API
      // const response = await apiClient.get('/api/v1/annotation/plugins');
      // setPlugins(response.data.plugins);
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (error) {
      message.error('加载插件列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlugins();
  }, [fetchPlugins]);

  // Handle add/edit plugin
  const handleOpenModal = (plugin?: AnnotationPlugin) => {
    setEditingPlugin(plugin || null);
    if (plugin) {
      form.setFieldsValue({
        name: plugin.name,
        type: plugin.type,
        endpoint: plugin.endpoint,
        priority: plugin.priority,
        supportedTypes: plugin.supportedTypes,
        config: JSON.stringify(plugin.config, null, 2),
      });
    } else {
      form.resetFields();
    }
    setModalVisible(true);
  };

  const handleSavePlugin = async () => {
    try {
      const values = await form.validateFields();
      const pluginData = {
        ...values,
        config: JSON.parse(values.config || '{}'),
      };

      if (editingPlugin) {
        // Update existing plugin
        setPlugins(prev => prev.map(p => 
          p.id === editingPlugin.id 
            ? { ...p, ...pluginData, updatedAt: new Date().toISOString() }
            : p
        ));
        message.success('插件更新成功');
      } else {
        // Create new plugin
        const newPlugin: AnnotationPlugin = {
          id: `plugin-${Date.now()}`,
          ...pluginData,
          status: 'inactive',
          enabled: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          healthStatus: 'unknown',
        };
        setPlugins(prev => [...prev, newPlugin]);
        message.success('插件创建成功');
      }

      setModalVisible(false);
      form.resetFields();
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error('配置 JSON 格式错误');
      }
    }
  };

  // Handle delete plugin
  const handleDeletePlugin = async (pluginId: string) => {
    setPlugins(prev => prev.filter(p => p.id !== pluginId));
    message.success('插件已删除');
  };

  // Handle enable/disable plugin
  const handleTogglePlugin = async (pluginId: string, enabled: boolean) => {
    setPlugins(prev => prev.map(p => 
      p.id === pluginId 
        ? { ...p, enabled, status: enabled ? 'active' : 'inactive' }
        : p
    ));
    message.success(enabled ? '插件已启用' : '插件已禁用');
  };

  // Handle test connection
  const handleTestConnection = async (pluginId: string) => {
    setTestingPlugin(pluginId);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Random success/failure for demo
      const success = Math.random() > 0.3;
      
      setPlugins(prev => prev.map(p => 
        p.id === pluginId 
          ? { 
              ...p, 
              healthStatus: success ? 'healthy' : 'unhealthy',
              lastHealthCheck: new Date().toISOString(),
            }
          : p
      ));
      
      if (success) {
        message.success('连接测试成功');
      } else {
        message.error('连接测试失败');
      }
    } catch (error) {
      message.error('连接测试出错');
    } finally {
      setTestingPlugin(null);
    }
  };

  // Handle view stats
  const handleViewStats = (pluginId: string) => {
    setSelectedPluginStats(stats[pluginId] || null);
    setStatsModalVisible(true);
  };

  // Handle priority change
  const handlePriorityChange = async (pluginId: string, priority: number) => {
    setPlugins(prev => prev.map(p => 
      p.id === pluginId ? { ...p, priority } : p
    ));
    message.success('优先级已更新');
  };

  // Table columns
  const columns: ColumnsType<AnnotationPlugin> = [
    {
      title: t('annotationPlugins.columns.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <ApiOutlined />
          <span>{name}</span>
          {record.healthStatus === 'healthy' && (
            <Badge status="success" />
          )}
          {record.healthStatus === 'unhealthy' && (
            <Badge status="error" />
          )}
        </Space>
      ),
    },
    {
      title: t('annotationPlugins.columns.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type) => (
        <Tag color={
          type === 'rest_api' ? 'blue' :
          type === 'grpc' ? 'purple' :
          type === 'websocket' ? 'cyan' : 'default'
        }>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('annotationPlugins.columns.endpoint'),
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint) => (
        <Tooltip title={endpoint}>
          <Text copyable={{ text: endpoint }} style={{ maxWidth: 200 }}>
            {endpoint || '-'}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: t('annotationPlugins.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={
          status === 'active' ? 'success' :
          status === 'error' ? 'error' : 'default'
        }>
          {status === 'active' ? t('annotationPlugins.status.running') :
           status === 'error' ? t('annotationPlugins.status.error') : t('annotationPlugins.status.inactive')}
        </Tag>
      ),
    },
    {
      title: t('annotationPlugins.columns.enabled'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleTogglePlugin(record.id, checked)}
        />
      ),
    },
    {
      title: t('annotationPlugins.columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      sorter: (a, b) => b.priority - a.priority,
      render: (priority, record) => (
        <InputNumber
          min={0}
          max={100}
          value={priority}
          size="small"
          onChange={(value) => handlePriorityChange(record.id, value || 0)}
          style={{ width: 70 }}
        />
      ),
    },
    {
      title: t('annotationPlugins.columns.supportedTypes'),
      dataIndex: 'supportedTypes',
      key: 'supportedTypes',
      render: (types: string[]) => (
        <Space wrap>
          {types.map(type => (
            <Tag key={type} color="geekblue">{type}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('annotationPlugins.columns.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="测试连接">
            <Button
              type="text"
              icon={testingPlugin === record.id ? <SyncOutlined spin /> : <LinkOutlined />}
              onClick={() => handleTestConnection(record.id)}
              disabled={testingPlugin !== null}
            />
          </Tooltip>
          <Tooltip title="查看统计">
            <Button
              type="text"
              icon={<BarChartOutlined />}
              onClick={() => handleViewStats(record.id)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleOpenModal(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除此插件吗？"
            onConfirm={() => handleDeletePlugin(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Calculate overall stats
  const overallStats = {
    total: plugins.length,
    active: plugins.filter(p => p.enabled).length,
    healthy: plugins.filter(p => p.healthStatus === 'healthy').length,
    totalCalls: Object.values(stats).reduce((sum, s) => sum + s.totalCalls, 0),
  };

  return (
    <div>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              <SettingOutlined /> {t('annotationPlugins.title')}
            </Title>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => handleOpenModal()}
            >
              {t('annotationPlugins.buttons.addPlugin')}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Stats Overview */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('annotationPlugins.statistics.totalPlugins')}
              value={overallStats.total}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('annotationPlugins.statistics.enabled')}
              value={overallStats.active}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('annotationPlugins.statistics.healthy')}
              value={overallStats.healthy}
              suffix={`/ ${overallStats.total}`}
              valueStyle={{ color: overallStats.healthy === overallStats.total ? '#52c41a' : '#faad14' }}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('annotationPlugins.statistics.totalCalls')}
              value={overallStats.totalCalls}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Plugins Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={plugins}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Add/Edit Plugin Modal */}
      <Modal
        title={editingPlugin ? '编辑插件' : '添加插件'}
        open={modalVisible}
        onOk={handleSavePlugin}
        onCancel={() => setModalVisible(false)}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="插件名称"
            rules={[{ required: true, message: '请输入插件名称' }]}
          >
            <Input placeholder="例如: Prodigy Adapter" />
          </Form.Item>

          <Form.Item
            name="type"
            label="连接类型"
            rules={[{ required: true, message: '请选择连接类型' }]}
          >
            <Select placeholder="选择连接类型">
              <Option value="rest_api">REST API</Option>
              <Option value="grpc">gRPC</Option>
              <Option value="websocket">WebSocket</Option>
              <Option value="sdk">SDK</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="endpoint"
            label="端点地址"
            rules={[{ required: true, message: '请输入端点地址' }]}
          >
            <Input placeholder="例如: http://localhost:8080/api" />
          </Form.Item>

          <Form.Item
            name="priority"
            label="优先级"
            initialValue={0}
            tooltip="数值越大优先级越高"
          >
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="supportedTypes"
            label="支持的标注类型"
            rules={[{ required: true, message: '请选择支持的标注类型' }]}
          >
            <Select mode="multiple" placeholder="选择支持的标注类型">
              <Option value="text_classification">文本分类</Option>
              <Option value="ner">命名实体识别</Option>
              <Option value="sentiment">情感分析</Option>
              <Option value="relation_extraction">关系抽取</Option>
              <Option value="qa">问答</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="config"
            label="配置 (JSON)"
            initialValue="{}"
          >
            <TextArea
              rows={4}
              placeholder='{"apiKey": "xxx", "timeout": 30000}'
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Stats Modal */}
      <Modal
        title="插件统计"
        open={statsModalVisible}
        onCancel={() => setStatsModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedPluginStats ? (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={12}>
                <Statistic
                  title="总调用次数"
                  value={selectedPluginStats.totalCalls}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="成功率"
                  value={selectedPluginStats.successRate}
                  suffix="%"
                  valueStyle={{ 
                    color: selectedPluginStats.successRate >= 95 ? '#52c41a' : 
                           selectedPluginStats.successRate >= 80 ? '#faad14' : '#ff4d4f'
                  }}
                />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={12}>
                <Statistic
                  title="平均延迟"
                  value={selectedPluginStats.avgLatencyMs}
                  suffix="ms"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="总成本"
                  value={selectedPluginStats.totalCost}
                  prefix="¥"
                  precision={2}
                />
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="错误次数"
                  value={selectedPluginStats.errorCount}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="最后调用"
                  value={selectedPluginStats.lastCallAt 
                    ? new Date(selectedPluginStats.lastCallAt).toLocaleString()
                    : '-'
                  }
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
            </Row>
            
            <div style={{ marginTop: 24 }}>
              <Text type="secondary">成功率趋势</Text>
              <Progress
                percent={selectedPluginStats.successRate}
                status={selectedPluginStats.successRate >= 95 ? 'success' : 
                        selectedPluginStats.successRate >= 80 ? 'normal' : 'exception'}
                strokeWidth={12}
              />
            </div>
          </div>
        ) : (
          <Alert
            message="暂无统计数据"
            description="该插件尚未被调用过"
            type="info"
            showIcon
          />
        )}
      </Modal>
    </div>
  );
};

export default AnnotationPluginsPage;
