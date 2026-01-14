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
      message.success('数据库配置创建成功');
      queryClient.invalidateQueries({ queryKey: ['admin-db-configs'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`创建失败: ${error.message}`);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, config }: { id: string; config: DBConfigUpdate }) =>
      adminApi.updateDBConfig(id, config, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success('数据库配置更新成功');
      queryClient.invalidateQueries({ queryKey: ['admin-db-configs'] });
      setModalVisible(false);
      setEditingConfig(null);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`更新失败: ${error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteDBConfig(id, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success('数据库配置删除成功');
      queryClient.invalidateQueries({ queryKey: ['admin-db-configs'] });
    },
    onError: (error: Error) => {
      message.error(`删除失败: ${error.message}`);
    },
  });

  // Test connection
  const handleTestConnection = async (configId: string) => {
    setTestResults(prev => ({ ...prev, [configId]: { success: false, latency_ms: 0, error_message: '测试中...' } }));
    try {
      const result = await adminApi.testDBConnection(configId);
      setTestResults(prev => ({ ...prev, [configId]: result }));
      if (result.success) {
        message.success(`连接成功 (${result.latency_ms}ms)`);
      } else {
        message.error(`连接失败: ${result.error_message}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '测试失败';
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
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: DBConfigResponse) => (
        <Button type="link" onClick={() => handleViewDetail(record)}>
          {text}
        </Button>
      ),
    },
    {
      title: '类型',
      dataIndex: 'db_type',
      key: 'db_type',
      render: (type: DatabaseType) => <Tag color="geekblue">{getDBTypeName(type)}</Tag>,
    },
    {
      title: '主机',
      key: 'host',
      render: (_: unknown, record: DBConfigResponse) => (
        <Text code>{`${record.host}:${record.port}`}</Text>
      ),
    },
    {
      title: '数据库',
      dataIndex: 'database',
      key: 'database',
    },
    {
      title: '权限',
      key: 'permission',
      render: (_: unknown, record: DBConfigResponse) => (
        <Space>
          {record.is_readonly ? (
            <Tag icon={<SafetyOutlined />} color="green">只读</Tag>
          ) : (
            <Tag icon={<SafetyOutlined />} color="orange">读写</Tag>
          )}
          {record.ssl_enabled && <Tag color="blue">SSL</Tag>}
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, record: DBConfigResponse) => {
        const testResult = testResults[record.id];
        if (testResult) {
          return testResult.success ? (
            <Badge status="success" text={`连接正常 (${testResult.latency_ms}ms)`} />
          ) : (
            <Badge status="error" text={testResult.error_message || '连接失败'} />
          );
        }
        return record.is_active ? (
          <Badge status="default" text="已启用" />
        ) : (
          <Badge status="error" text="已禁用" />
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: DBConfigResponse) => (
        <Space>
          <Tooltip title="测试连接">
            <Button
              type="text"
              icon={<LinkOutlined />}
              onClick={() => handleTestConnection(record.id)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此配置？"
            description="删除后相关的同步策略也将失效"
            onConfirm={() => deleteMutation.mutate(record.id)}
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

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <DatabaseOutlined />
            <span>数据库配置管理</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              添加数据库
            </Button>
          </Space>
        }
      >
        <Alert
          message="安全提示"
          description="建议使用只读权限的数据库账户进行数据提取，密码将加密存储并脱敏显示。"
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
        title={editingConfig ? '编辑数据库配置' : '添加数据库配置'}
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
            label="连接名称"
            rules={[{ required: true, message: '请输入连接名称' }]}
          >
            <Input placeholder="例如：生产数据库-只读" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="连接描述（可选）" />
          </Form.Item>

          <Form.Item
            name="db_type"
            label="数据库类型"
            rules={[{ required: true, message: '请选择数据库类型' }]}
          >
            <Select placeholder="选择数据库类型" onChange={handleDbTypeChange}>
              {DB_TYPES.map(type => (
                <Option key={type} value={type}>
                  {getDBTypeName(type)}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="host"
            label="主机地址"
            rules={[{ required: true, message: '请输入主机地址' }]}
          >
            <Input placeholder="例如：localhost 或 192.168.1.100" />
          </Form.Item>

          <Form.Item
            name="port"
            label="端口"
            rules={[{ required: true, message: '请输入端口' }]}
          >
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="database"
            label="数据库名"
            rules={[{ required: true, message: '请输入数据库名' }]}
          >
            <Input placeholder="数据库名称" />
          </Form.Item>

          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="数据库用户名" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            extra={editingConfig ? '留空则保持原有密码不变' : undefined}
          >
            <Input.Password placeholder="数据库密码（将加密存储）" />
          </Form.Item>

          <Form.Item name="is_readonly" valuePropName="checked" label="只读连接">
            <Switch checkedChildren="只读" unCheckedChildren="读写" />
          </Form.Item>

          <Form.Item name="ssl_enabled" valuePropName="checked" label="启用 SSL">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="数据库配置详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
          <Button
            key="test"
            type="primary"
            icon={<LinkOutlined />}
            onClick={() => selectedConfig && handleTestConnection(selectedConfig.id)}
          >
            测试连接
          </Button>,
        ]}
        width={600}
      >
        {selectedConfig && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="名称" span={2}>{selectedConfig.name}</Descriptions.Item>
            <Descriptions.Item label="类型">{getDBTypeName(selectedConfig.db_type)}</Descriptions.Item>
            <Descriptions.Item label="状态">
              {selectedConfig.is_active ? <Badge status="success" text="已启用" /> : <Badge status="error" text="已禁用" />}
            </Descriptions.Item>
            <Descriptions.Item label="主机">{selectedConfig.host}</Descriptions.Item>
            <Descriptions.Item label="端口">{selectedConfig.port}</Descriptions.Item>
            <Descriptions.Item label="数据库">{selectedConfig.database}</Descriptions.Item>
            <Descriptions.Item label="用户名">{selectedConfig.username}</Descriptions.Item>
            <Descriptions.Item label="密码" span={2}>
              <Space>
                <EyeInvisibleOutlined />
                <Text code>{selectedConfig.password_masked || '******'}</Text>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="权限">
              {selectedConfig.is_readonly ? <Tag color="green">只读</Tag> : <Tag color="orange">读写</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="SSL">
              {selectedConfig.ssl_enabled ? <Tag color="blue">已启用</Tag> : <Tag>未启用</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {new Date(selectedConfig.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间" span={2}>
              {new Date(selectedConfig.updated_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default ConfigDB;
