import React, { useState, useEffect } from 'react';
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
  Tabs,
  Alert,
  Tooltip,
  Progress,
  Typography,
  Row,
  Col,
  Statistic,
  Timeline,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  StopOutlined,
  HistoryOutlined,
  SecurityScanOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface DataSource {
  id: string;
  name: string;
  type: 'mysql' | 'postgresql' | 'mongodb' | 'redis' | 'elasticsearch' | 'api';
  status: 'connected' | 'disconnected' | 'error' | 'testing';
  host: string;
  port: number;
  database?: string;
  username: string;
  lastConnected?: Date;
  createdAt: Date;
  updatedAt: Date;
  connectionCount: number;
  errorCount: number;
  permissions: string[];
  securityLevel: 'low' | 'medium' | 'high';
}

interface ConnectionTest {
  id: string;
  dataSourceId: string;
  status: 'running' | 'success' | 'failed';
  message: string;
  duration: number;
  timestamp: Date;
}

interface ConnectionLog {
  id: string;
  dataSourceId: string;
  action: 'connect' | 'disconnect' | 'test' | 'error';
  status: 'success' | 'failed';
  message: string;
  timestamp: Date;
  userId: string;
  userAgent: string;
}

const DataSourceManager: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ConnectionTest>>({});
  const [connectionLogs, setConnectionLogs] = useState<ConnectionLog[]>([]);
  const [selectedSource, setSelectedSource] = useState<DataSource | null>(null);
  const [form] = Form.useForm();

  // Mock data for demonstration
  useEffect(() => {
    const mockDataSources: DataSource[] = [
      {
        id: '1',
        name: 'Production MySQL',
        type: 'mysql',
        status: 'connected',
        host: 'prod-mysql.company.com',
        port: 3306,
        database: 'superinsight',
        username: 'app_user',
        lastConnected: new Date(Date.now() - 1000 * 60 * 5),
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
        connectionCount: 1247,
        errorCount: 3,
        permissions: ['read', 'write'],
        securityLevel: 'high',
      },
      {
        id: '2',
        name: 'Analytics PostgreSQL',
        type: 'postgresql',
        status: 'connected',
        host: 'analytics-pg.company.com',
        port: 5432,
        database: 'analytics',
        username: 'readonly_user',
        lastConnected: new Date(Date.now() - 1000 * 60 * 15),
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 15),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 1),
        connectionCount: 892,
        errorCount: 0,
        permissions: ['read'],
        securityLevel: 'medium',
      },
      {
        id: '3',
        name: 'Cache Redis',
        type: 'redis',
        status: 'error',
        host: 'cache-redis.company.com',
        port: 6379,
        username: 'cache_user',
        lastConnected: new Date(Date.now() - 1000 * 60 * 60 * 2),
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
        updatedAt: new Date(Date.now() - 1000 * 60 * 30),
        connectionCount: 456,
        errorCount: 12,
        permissions: ['read', 'write'],
        securityLevel: 'low',
      },
    ];
    setDataSources(mockDataSources);

    const mockLogs: ConnectionLog[] = [
      {
        id: '1',
        dataSourceId: '1',
        action: 'connect',
        status: 'success',
        message: 'Connection established successfully',
        timestamp: new Date(Date.now() - 1000 * 60 * 5),
        userId: 'user1',
        userAgent: 'SuperInsight Frontend v1.0',
      },
      {
        id: '2',
        dataSourceId: '3',
        action: 'error',
        status: 'failed',
        message: 'Connection timeout after 30 seconds',
        timestamp: new Date(Date.now() - 1000 * 60 * 30),
        userId: 'user2',
        userAgent: 'SuperInsight Frontend v1.0',
      },
    ];
    setConnectionLogs(mockLogs);
  }, []);

  const getStatusColor = (status: DataSource['status']) => {
    switch (status) {
      case 'connected':
        return 'success';
      case 'disconnected':
        return 'default';
      case 'error':
        return 'error';
      case 'testing':
        return 'processing';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: DataSource['status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircleOutlined />;
      case 'disconnected':
        return <StopOutlined />;
      case 'error':
        return <CloseCircleOutlined />;
      case 'testing':
        return <ExclamationCircleOutlined />;
      default:
        return null;
    }
  };

  const getSecurityLevelColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      case 'low':
        return 'green';
      default:
        return 'default';
    }
  };

  const handleTestConnection = async (dataSource: DataSource) => {
    setTestResults(prev => ({
      ...prev,
      [dataSource.id]: {
        id: `test-${Date.now()}`,
        dataSourceId: dataSource.id,
        status: 'running',
        message: 'Testing connection...',
        duration: 0,
        timestamp: new Date(),
      },
    }));

    // Simulate connection test
    setTimeout(() => {
      const success = Math.random() > 0.3; // 70% success rate
      setTestResults(prev => ({
        ...prev,
        [dataSource.id]: {
          id: `test-${Date.now()}`,
          dataSourceId: dataSource.id,
          status: success ? 'success' : 'failed',
          message: success ? 'Connection successful' : 'Connection failed: Timeout',
          duration: Math.floor(Math.random() * 5000) + 1000,
          timestamp: new Date(),
        },
      }));

      if (success) {
        setDataSources(prev =>
          prev.map(ds =>
            ds.id === dataSource.id
              ? { ...ds, status: 'connected', lastConnected: new Date() }
              : ds
          )
        );
      }
    }, 2000);
  };

  const handleCreateOrUpdate = async (values: any) => {
    setLoading(true);
    try {
      if (editingSource) {
        // Update existing data source
        setDataSources(prev =>
          prev.map(ds =>
            ds.id === editingSource.id
              ? { ...ds, ...values, updatedAt: new Date() }
              : ds
          )
        );
      } else {
        // Create new data source
        const newSource: DataSource = {
          id: Date.now().toString(),
          ...values,
          status: 'disconnected' as const,
          connectionCount: 0,
          errorCount: 0,
          createdAt: new Date(),
          updatedAt: new Date(),
          permissions: values.permissions || ['read'],
          securityLevel: values.securityLevel || 'medium',
        };
        setDataSources(prev => [...prev, newSource]);
      }
      setModalVisible(false);
      setEditingSource(null);
      form.resetFields();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (dataSource: DataSource) => {
    Modal.confirm({
      title: t('dataSync:dataSource.deleteConfirm'),
      content: t('dataSync:dataSource.deleteWarning', { name: dataSource.name }),
      onOk: () => {
        setDataSources(prev => prev.filter(ds => ds.id !== dataSource.id));
      },
    });
  };

  const columns: ColumnsType<DataSource> = [
    {
      title: t('dataSync:dataSource.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <Text strong>{text}</Text>
          <Tag color={getSecurityLevelColor(record.securityLevel)}>
            {t(`dataSync:security.${record.securityLevel}`)}
          </Tag>
        </Space>
      ),
    },
    {
      title: t('dataSync:dataSource.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type) => (
        <Tag color="blue">{type.toUpperCase()}</Tag>
      ),
    },
    {
      title: t('dataSync:dataSource.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Badge
          status={getStatusColor(status)}
          text={t(`dataSync:status.${status}`)}
        />
      ),
    },
    {
      title: t('dataSync:dataSource.connection'),
      key: 'connection',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text type="secondary">{record.host}:{record.port}</Text>
          {record.database && <Text type="secondary">DB: {record.database}</Text>}
        </Space>
      ),
    },
    {
      title: t('dataSync:dataSource.lastConnected'),
      dataIndex: 'lastConnected',
      key: 'lastConnected',
      render: (date) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: t('dataSync:dataSource.stats'),
      key: 'stats',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text type="secondary">
            {t('dataSync:dataSource.connections')}: {record.connectionCount}
          </Text>
          <Text type={record.errorCount > 0 ? 'danger' : 'secondary'}>
            {t('dataSync:dataSource.errors')}: {record.errorCount}
          </Text>
        </Space>
      ),
    },
    {
      title: t('common:actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('dataSync:dataSource.testConnection')}>
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => handleTestConnection(record)}
              loading={testResults[record.id]?.status === 'running'}
            />
          </Tooltip>
          <Tooltip title={t('common:edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingSource(record);
                form.setFieldsValue(record);
                setModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title={t('dataSync:dataSource.viewLogs')}>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setSelectedSource(record)}
            />
          </Tooltip>
          <Tooltip title={t('common:delete')}>
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:dataSource.totalSources')}
              value={dataSources.length}
              prefix={<SettingOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:dataSource.connectedSources')}
              value={dataSources.filter(ds => ds.status === 'connected').length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:dataSource.errorSources')}
              value={dataSources.filter(ds => ds.status === 'error').length}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:dataSource.totalConnections')}
              value={dataSources.reduce((sum, ds) => sum + ds.connectionCount, 0)}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={t('dataSync:dataSource.title')}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingSource(null);
              form.resetFields();
              setModalVisible(true);
            }}
          >
            {t('dataSync:dataSource.create')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={dataSources}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => t('common:pagination.total', { total }),
          }}
        />

        {/* Test Results */}
        {Object.values(testResults).some(result => result.status !== 'running') && (
          <Alert
            style={{ marginTop: 16 }}
            message={t('dataSync:dataSource.testResults')}
            description={
              <Space direction="vertical" style={{ width: '100%' }}>
                {Object.values(testResults)
                  .filter(result => result.status !== 'running')
                  .map(result => (
                    <div key={result.id}>
                      <Badge
                        status={result.status === 'success' ? 'success' : 'error'}
                        text={`${result.message} (${result.duration}ms)`}
                      />
                    </div>
                  ))}
              </Space>
            }
            type="info"
            closable
            onClose={() => setTestResults({})}
          />
        )}
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingSource ? t('dataSync:dataSource.edit') : t('dataSync:dataSource.create')}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingSource(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={loading}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateOrUpdate}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={t('dataSync:dataSource.name')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder={t('dataSync:dataSource.namePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="type"
                label={t('dataSync:dataSource.type')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Select placeholder={t('dataSync:dataSource.typePlaceholder')}>
                  <Select.Option value="mysql">MySQL</Select.Option>
                  <Select.Option value="postgresql">PostgreSQL</Select.Option>
                  <Select.Option value="mongodb">MongoDB</Select.Option>
                  <Select.Option value="redis">Redis</Select.Option>
                  <Select.Option value="elasticsearch">Elasticsearch</Select.Option>
                  <Select.Option value="api">REST API</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="host"
                label={t('dataSync:dataSource.host')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder="localhost" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="port"
                label={t('dataSync:dataSource.port')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input type="number" placeholder="3306" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="database"
                label={t('dataSync:dataSource.database')}
              >
                <Input placeholder={t('dataSync:dataSource.databasePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="username"
                label={t('dataSync:dataSource.username')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder={t('dataSync:dataSource.usernamePlaceholder')} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="password"
            label={t('dataSync:dataSource.password')}
            rules={[{ required: !editingSource, message: t('common:validation.required') }]}
          >
            <Input.Password placeholder={t('dataSync:dataSource.passwordPlaceholder')} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="securityLevel"
                label={t('dataSync:dataSource.securityLevel')}
                initialValue="medium"
              >
                <Select>
                  <Select.Option value="low">{t('dataSync:security.low')}</Select.Option>
                  <Select.Option value="medium">{t('dataSync:security.medium')}</Select.Option>
                  <Select.Option value="high">{t('dataSync:security.high')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="permissions"
                label={t('dataSync:dataSource.permissions')}
                initialValue={['read']}
              >
                <Select mode="multiple">
                  <Select.Option value="read">{t('dataSync:permissions.read')}</Select.Option>
                  <Select.Option value="write">{t('dataSync:permissions.write')}</Select.Option>
                  <Select.Option value="delete">{t('dataSync:permissions.delete')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Connection Logs Modal */}
      <Modal
        title={t('dataSync:dataSource.connectionLogs')}
        open={!!selectedSource}
        onCancel={() => setSelectedSource(null)}
        footer={null}
        width={800}
      >
        {selectedSource && (
          <Timeline>
            {connectionLogs
              .filter(log => log.dataSourceId === selectedSource.id)
              .map(log => (
                <Timeline.Item
                  key={log.id}
                  color={log.status === 'success' ? 'green' : 'red'}
                >
                  <div>
                    <Text strong>{t(`dataSync:actions.${log.action}`)}</Text>
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      {log.timestamp.toLocaleString()}
                    </Text>
                  </div>
                  <div>{log.message}</div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    User: {log.userId} | {log.userAgent}
                  </Text>
                </Timeline.Item>
              ))}
          </Timeline>
        )}
      </Modal>
    </div>
  );
};

export default DataSourceManager;