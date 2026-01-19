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
      message.error(t('annotationPlugins.loadPluginsFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

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
        message.success(t('annotationPlugins.pluginUpdateSuccess'));
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
        message.success(t('annotationPlugins.pluginCreateSuccess'));
      }

      setModalVisible(false);
      form.resetFields();
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error(t('annotationPlugins.configJsonError'));
      }
    }
  };

  // Handle delete plugin
  const handleDeletePlugin = async (pluginId: string) => {
    setPlugins(prev => prev.filter(p => p.id !== pluginId));
    message.success(t('annotationPlugins.pluginDeleted'));
  };

  // Handle enable/disable plugin
  const handleTogglePlugin = async (pluginId: string, enabled: boolean) => {
    setPlugins(prev => prev.map(p => 
      p.id === pluginId 
        ? { ...p, enabled, status: enabled ? 'active' : 'inactive' }
        : p
    ));
    message.success(enabled ? t('annotationPlugins.pluginEnabled') : t('annotationPlugins.pluginDisabled'));
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
        message.success(t('annotationPlugins.connectionTestSuccess'));
      } else {
        message.error(t('annotationPlugins.connectionTestFailed'));
      }
    } catch (error) {
      message.error(t('annotationPlugins.connectionTestError'));
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
    message.success(t('annotationPlugins.priorityUpdated'));
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
          <Tooltip title={t('annotationPlugins.tooltips.testConnection')}>
            <Button
              type="text"
              icon={testingPlugin === record.id ? <SyncOutlined spin /> : <LinkOutlined />}
              onClick={() => handleTestConnection(record.id)}
              disabled={testingPlugin !== null}
            />
          </Tooltip>
          <Tooltip title={t('annotationPlugins.tooltips.viewStats')}>
            <Button
              type="text"
              icon={<BarChartOutlined />}
              onClick={() => handleViewStats(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('annotationPlugins.tooltips.edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleOpenModal(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('annotationPlugins.confirm.deletePlugin')}
            onConfirm={() => handleDeletePlugin(record.id)}
            okText={t('annotationPlugins.confirm.ok')}
            cancelText={t('annotationPlugins.confirm.cancel')}
          >
            <Tooltip title={t('annotationPlugins.tooltips.delete')}>
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
        title={editingPlugin ? t('annotationPlugins.modal.editPlugin') : t('annotationPlugins.modal.addPlugin')}
        open={modalVisible}
        onOk={handleSavePlugin}
        onCancel={() => setModalVisible(false)}
        width={600}
        okText={t('annotationPlugins.buttons.save')}
        cancelText={t('annotationPlugins.confirm.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('annotationPlugins.form.name')}
            rules={[{ required: true, message: t('annotationPlugins.form.nameRequired') }]}
          >
            <Input placeholder={t('annotationPlugins.form.namePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="type"
            label={t('annotationPlugins.form.type')}
            rules={[{ required: true, message: t('annotationPlugins.form.typeRequired') }]}
          >
            <Select placeholder={t('annotationPlugins.form.typePlaceholder')}>
              <Option value="rest_api">{t('annotationPlugins.types.restApi')}</Option>
              <Option value="grpc">{t('annotationPlugins.types.grpc')}</Option>
              <Option value="websocket">{t('annotationPlugins.types.websocket')}</Option>
              <Option value="sdk">{t('annotationPlugins.types.sdk')}</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="endpoint"
            label={t('annotationPlugins.form.endpoint')}
            rules={[{ required: true, message: t('annotationPlugins.form.endpointRequired') }]}
          >
            <Input placeholder={t('annotationPlugins.form.endpointPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="priority"
            label={t('annotationPlugins.form.priority')}
            initialValue={0}
            tooltip={t('annotationPlugins.form.priorityTooltip')}
          >
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="supportedTypes"
            label={t('annotationPlugins.form.supportedTypes')}
            rules={[{ required: true, message: t('annotationPlugins.form.supportedTypesRequired') }]}
          >
            <Select mode="multiple" placeholder={t('annotationPlugins.form.supportedTypesPlaceholder')}>
              <Option value="text_classification">{t('annotationPlugins.annotationTypes.textClassification')}</Option>
              <Option value="ner">{t('annotationPlugins.annotationTypes.ner')}</Option>
              <Option value="sentiment">{t('annotationPlugins.annotationTypes.sentiment')}</Option>
              <Option value="relation_extraction">{t('annotationPlugins.annotationTypes.relationExtraction')}</Option>
              <Option value="qa">{t('annotationPlugins.annotationTypes.qa')}</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="config"
            label={t('annotationPlugins.form.config')}
            initialValue="{}"
          >
            <TextArea
              rows={4}
              placeholder={t('annotationPlugins.form.configPlaceholder')}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Stats Modal */}
      <Modal
        title={t('annotationPlugins.modal.pluginStats')}
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
                  title={t('annotationPlugins.stats.totalCalls')}
                  value={selectedPluginStats.totalCalls}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('annotationPlugins.stats.successRate')}
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
                  title={t('annotationPlugins.stats.avgLatency')}
                  value={selectedPluginStats.avgLatencyMs}
                  suffix="ms"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('annotationPlugins.stats.totalCost')}
                  value={selectedPluginStats.totalCost}
                  prefix="¥"
                  precision={2}
                />
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title={t('annotationPlugins.stats.errorCount')}
                  value={selectedPluginStats.errorCount}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('annotationPlugins.stats.lastCall')}
                  value={selectedPluginStats.lastCallAt 
                    ? new Date(selectedPluginStats.lastCallAt).toLocaleString()
                    : '-'
                  }
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
            </Row>
            
            <div style={{ marginTop: 24 }}>
              <Text type="secondary">{t('annotationPlugins.stats.successRateTrend')}</Text>
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
            message={t('annotationPlugins.stats.noData')}
            description={t('annotationPlugins.stats.noDataDescription')}
            type="info"
            showIcon
          />
        )}
      </Modal>
    </div>
  );
};

export default AnnotationPluginsPage;
