/**
 * Admin Database Configuration Page
 * 
 * Provides interface for managing database connection configurations including
 * creation, editing, testing connections, and viewing masked passwords.
 * 
 * **Requirement 3.1, 3.2, 3.3, 3.5: Database Configuration**
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Tag,
  Tooltip,
  message,
  Popconfirm,
  Badge,
  Typography,
  Alert,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeInvisibleOutlined,
  ReloadOutlined,
  SafetyOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import {
  adminApi,
  DBConfigResponse,
  DBConfigCreate,
  DBConfigUpdate,
  DatabaseType,
  getDBTypeName,
  ConnectionTestResult,
} from '@/services/adminApi';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const DB_TYPES: DatabaseType[] = ['postgresql', 'mysql', 'sqlite', 'oracle', 'sqlserver'];

const DEFAULT_PORTS: Record<DatabaseType, number> = {
  postgresql: 5432,
  mysql: 3306,
  sqlite: 0,
  oracle: 1521,
  sqlserver: 1433,
};

const ConfigDB: React.FC = () => {
  const { t } = useTranslation(['admin', 'common']);
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<DBConfigResponse | null>(null);
  const [selectedConfig, setSelectedConfig] = useState<DBConfigResponse | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ConnectionTestResult>>({});
  const [form] = Form.useForm();

  // Fetch DB configs
  const { data: configs = [], isLoading, refetch } = useQuery({
    queryKey: ['admin-db-configs'],
    queryFn: () => adminApi.listDBConfigs(undefined, false),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (config: DBConfigCreate) =>
      adminApi.createDBConfig(config, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('admin:configDB.createSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-db-configs'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(t('admin:configDB.createFailed', { error: error.message }));
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, config }: { id: string; config: DBConfigUpdate }) =>
      adminApi.updateDBConfig(id, config, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('admin:configDB.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-db-configs'] });
      setModalVisible(false);
      setEditingConfig(null);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(t('admin:configDB.updateFailed', { error: error.message }));
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteDBConfig(id, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('admin:configDB.deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-db-configs'] });
    },
    onError: (error: Error) => {
      message.error(t('admin:configDB.deleteFailed', { error: error.message }));
    },
  });

  // Test connection
  const handleTestConnection = async (configId: string) => {
    setTestResults(prev => ({ ...prev, [configId]: { success: false, latency_ms: 0, error_message: t('admin:configDB.testing') } }));
    try {
      const result = await adminApi.testDBConnection(configId);
      setTestResults(prev => ({ ...prev, [configId]: result }));
      if (result.success) {
        message.success(t('admin:configDB.connectionSuccess', { latency: result.latency_ms }));
      } else {
        message.error(t('admin:configDB.connectionFailed', { error: result.error_message }));
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : t('admin:configDB.testFailed');
      setTestResults(prev => ({ ...prev, [configId]: { success: false, latency_ms: 0, error_message: errorMsg } }));
      message.error(errorMsg);
    }
  };

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      db_type: 'postgresql',
      port: 5432,
      is_readonly: true,
      ssl_enabled: false,
    });
    setModalVisible(true);
  };

  const handleEdit = (record: DBConfigResponse) => {
    setEditingConfig(record);
    form.setFieldsValue({
      ...record,
      password: '', // Don't show encrypted password
    });
    setModalVisible(true);
  };

  const handleViewDetail = (record: DBConfigResponse) => {
    setSelectedConfig(record);
    setDetailVisible(true);
  };

  const handleDbTypeChange = (dbType: DatabaseType) => {
    form.setFieldValue('port', DEFAULT_PORTS[dbType]);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Remove empty password if not changed
      if (!values.password) {
        delete values.password;
      }

      if (editingConfig) {
        updateMutation.mutate({ id: editingConfig.id, config: values });
      } else {
        createMutation.mutate(values);
      }
    } catch (error) {
      // Form validation error
    }
  };

  const columns = [
    {
      title: t('admin:configDB.columns.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: DBConfigResponse) => (
        <Button type="link" onClick={() => handleViewDetail(record)}>
          {text}
        </Button>
      ),
    },
    {
      title: t('admin:configDB.columns.type'),
      dataIndex: 'db_type',
      key: 'db_type',
      render: (type: DatabaseType) => <Tag color="geekblue">{getDBTypeName(type)}</Tag>,
    },
    {
      title: t('admin:configDB.columns.host'),
      key: 'host',
      render: (_: unknown, record: DBConfigResponse) => (
        <Text code>{`${record.host}:${record.port}`}</Text>
      ),
    },
    {
      title: t('admin:configDB.columns.database'),
      dataIndex: 'database',
      key: 'database',
    },
    {
      title: t('admin:configDB.columns.permission'),
      key: 'permission',
      render: (_: unknown, record: DBConfigResponse) => (
        <Space>
          {record.is_readonly ? (
            <Tag icon={<SafetyOutlined />} color="green">{t('admin:configDB.readonly')}</Tag>
          ) : (
            <Tag icon={<SafetyOutlined />} color="orange">{t('admin:configDB.readwrite')}</Tag>
          )}
          {record.ssl_enabled && <Tag color="blue">SSL</Tag>}
        </Space>
      ),
    },
    {
      title: t('admin:configDB.columns.status'),
      key: 'status',
      render: (_: unknown, record: DBConfigResponse) => {
        const testResult = testResults[record.id];
        if (testResult) {
          return testResult.success ? (
            <Badge status="success" text={t('admin:configDB.connectionNormal', { latency: testResult.latency_ms })} />
          ) : (
            <Badge status="error" text={testResult.error_message || t('admin:configDB.connectionFailedShort')} />
          );
        }
        return record.is_active ? (
          <Badge status="default" text={t('admin:configDB.enabled')} />
        ) : (
          <Badge status="error" text={t('admin:configDB.disabled')} />
        );
      },
    },
    {
      title: t('admin:configDB.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: DBConfigResponse) => (
        <Space>
          <Tooltip title={t('admin:configDB.testConnection')}>
            <Button
              type="text"
              icon={<LinkOutlined />}
              onClick={() => handleTestConnection(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('common:edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('admin:configDB.confirmDelete')}
            description={t('admin:configDB.confirmDeleteDescription')}
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText={t('common:confirm')}
            cancelText={t('common:cancel')}
          >
            <Tooltip title={t('common:delete')}>
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <DatabaseOutlined />
            <span>{t('admin:configDB.title')}</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('common:refresh')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('admin:configDB.addDatabase')}
            </Button>
          </Space>
        }
      >
        <Alert
          message={t('admin:configDB.securityTip')}
          description={t('admin:configDB.securityTipDescription')}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Table
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingConfig ? t('admin:configDB.editConfig') : t('admin:configDB.addConfig')}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingConfig(null);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('admin:configDB.form.connectionName')}
            rules={[{ required: true, message: t('admin:configDB.form.connectionNameRequired') }]}
          >
            <Input placeholder={t('admin:configDB.form.connectionNamePlaceholder')} />
          </Form.Item>

          <Form.Item name="description" label={t('admin:configDB.form.description')}>
            <TextArea rows={2} placeholder={t('admin:configDB.form.descriptionPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="db_type"
            label={t('admin:configDB.form.dbType')}
            rules={[{ required: true, message: t('admin:configDB.form.dbTypeRequired') }]}
          >
            <Select placeholder={t('admin:configDB.form.dbTypePlaceholder')} onChange={handleDbTypeChange}>
              {DB_TYPES.map(type => (
                <Option key={type} value={type}>
                  {getDBTypeName(type)}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="host"
            label={t('admin:configDB.form.host')}
            rules={[{ required: true, message: t('admin:configDB.form.hostRequired') }]}
          >
            <Input placeholder={t('admin:configDB.form.hostPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="port"
            label={t('admin:configDB.form.port')}
            rules={[{ required: true, message: t('admin:configDB.form.portRequired') }]}
          >
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="database"
            label={t('admin:configDB.form.databaseName')}
            rules={[{ required: true, message: t('admin:configDB.form.databaseNameRequired') }]}
          >
            <Input placeholder={t('admin:configDB.form.databaseNamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="username"
            label={t('admin:configDB.form.username')}
            rules={[{ required: true, message: t('admin:configDB.form.usernameRequired') }]}
          >
            <Input placeholder={t('admin:configDB.form.usernamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="password"
            label={t('admin:configDB.form.password')}
            extra={editingConfig ? t('admin:configDB.form.passwordKeepEmpty') : undefined}
          >
            <Input.Password placeholder={t('admin:configDB.form.passwordPlaceholder')} />
          </Form.Item>

          <Form.Item name="is_readonly" valuePropName="checked" label={t('admin:configDB.form.readonlyConnection')}>
            <Switch checkedChildren={t('admin:configDB.readonly')} unCheckedChildren={t('admin:configDB.readwrite')} />
          </Form.Item>

          <Form.Item name="ssl_enabled" valuePropName="checked" label={t('admin:configDB.form.enableSSL')}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title={t('admin:configDB.configDetail')}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            {t('common:close')}
          </Button>,
          <Button
            key="test"
            type="primary"
            icon={<LinkOutlined />}
            onClick={() => selectedConfig && handleTestConnection(selectedConfig.id)}
          >
            {t('admin:configDB.testConnection')}
          </Button>,
        ]}
        width={600}
      >
        {selectedConfig && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label={t('admin:configDB.detail.name')} span={2}>{selectedConfig.name}</Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.type')}>{getDBTypeName(selectedConfig.db_type)}</Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.status')}>
              {selectedConfig.is_active ? <Badge status="success" text={t('admin:configDB.enabled')} /> : <Badge status="error" text={t('admin:configDB.disabled')} />}
            </Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.host')}>{selectedConfig.host}</Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.port')}>{selectedConfig.port}</Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.database')}>{selectedConfig.database}</Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.username')}>{selectedConfig.username}</Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.password')} span={2}>
              <Space>
                <EyeInvisibleOutlined />
                <Text code>{selectedConfig.password_masked || '******'}</Text>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.permission')}>
              {selectedConfig.is_readonly ? <Tag color="green">{t('admin:configDB.readonly')}</Tag> : <Tag color="orange">{t('admin:configDB.readwrite')}</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="SSL">
              {selectedConfig.ssl_enabled ? <Tag color="blue">{t('admin:configDB.sslEnabled')}</Tag> : <Tag>{t('admin:configDB.sslDisabled')}</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.createdAt')} span={2}>
              {new Date(selectedConfig.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label={t('admin:configDB.detail.updatedAt')} span={2}>
              {new Date(selectedConfig.updated_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default ConfigDB;
