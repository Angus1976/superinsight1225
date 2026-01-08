// Tenant management component
import React, { useState } from 'react';
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
  Progress,
  Tooltip,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Switch,
  InputNumber,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  UserOutlined,
  DatabaseOutlined,
  CloudOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useTenants, useCreateTenant, useUpdateTenant, useDeleteTenant } from '@/hooks';
import type { SystemTenant, CreateTenantRequest, UpdateTenantRequest } from '@/types';

const { TextArea } = Input;

const statusColors = {
  active: 'success',
  inactive: 'default',
  suspended: 'error',
} as const;

const planColors = {
  free: 'default',
  pro: 'blue',
  enterprise: 'gold',
} as const;

const TenantManager: React.FC = () => {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<SystemTenant | null>(null);
  
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [settingsForm] = Form.useForm();

  const { data: tenants = [], isLoading } = useTenants();
  const createTenantMutation = useCreateTenant();
  const updateTenantMutation = useUpdateTenant();
  const deleteTenantMutation = useDeleteTenant();

  const handleCreateTenant = async (values: CreateTenantRequest) => {
    await createTenantMutation.mutateAsync(values);
    setCreateModalOpen(false);
    createForm.resetFields();
  };

  const handleEditTenant = async (values: UpdateTenantRequest) => {
    if (!selectedTenant) return;
    await updateTenantMutation.mutateAsync({ id: selectedTenant.id, data: values });
    setEditModalOpen(false);
    setSelectedTenant(null);
    editForm.resetFields();
  };

  const handleUpdateSettings = async (values: any) => {
    if (!selectedTenant) return;
    await updateTenantMutation.mutateAsync({
      id: selectedTenant.id,
      data: { settings: values },
    });
    setSettingsModalOpen(false);
    setSelectedTenant(null);
    settingsForm.resetFields();
  };

  const handleDeleteTenant = async (id: string) => {
    await deleteTenantMutation.mutateAsync(id);
  };

  const openEditModal = (tenant: SystemTenant) => {
    setSelectedTenant(tenant);
    editForm.setFieldsValue({
      name: tenant.name,
      description: tenant.description,
      status: tenant.status,
      plan: tenant.plan,
      storage_limit: tenant.storage_limit,
      cpu_quota: tenant.cpu_quota,
      memory_quota: tenant.memory_quota,
      api_rate_limit: tenant.api_rate_limit,
    });
    setEditModalOpen(true);
  };

  const openSettingsModal = (tenant: SystemTenant) => {
    setSelectedTenant(tenant);
    settingsForm.setFieldsValue(tenant.settings);
    setSettingsModalOpen(true);
  };

  const columns: ColumnsType<SystemTenant> = [
    {
      title: 'Tenant Name',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          {record.description && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              {record.description}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: keyof typeof statusColors) => (
        <Tag color={statusColors[status]}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Plan',
      dataIndex: 'plan',
      key: 'plan',
      render: (plan: keyof typeof planColors) => (
        <Tag color={planColors[plan]}>{plan.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Users',
      dataIndex: 'users_count',
      key: 'users_count',
      render: (count) => (
        <Tooltip title="Active users">
          <Space>
            <UserOutlined />
            {count}
          </Space>
        </Tooltip>
      ),
    },
    {
      title: 'Storage Usage',
      key: 'storage',
      render: (_, record) => {
        const percentage = Math.round((record.storage_used / record.storage_limit) * 100);
        return (
          <div style={{ width: 120 }}>
            <Progress
              percent={percentage}
              size="small"
              status={percentage > 90 ? 'exception' : percentage > 70 ? 'active' : 'success'}
            />
            <div style={{ fontSize: '12px', marginTop: 4 }}>
              {record.storage_used}GB / {record.storage_limit}GB
            </div>
          </div>
        );
      },
    },
    {
      title: 'Resources',
      key: 'resources',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Tooltip title="CPU Quota">
            <Space size="small">
              <CloudOutlined />
              {record.cpu_quota} cores
            </Space>
          </Tooltip>
          <Tooltip title="Memory Quota">
            <Space size="small">
              <DatabaseOutlined />
              {record.memory_quota}GB
            </Space>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="Edit Tenant">
            <Button
              type="link"
              icon={<EditOutlined />}
              size="small"
              onClick={() => openEditModal(record)}
            />
          </Tooltip>
          <Tooltip title="Settings">
            <Button
              type="link"
              icon={<SettingOutlined />}
              size="small"
              onClick={() => openSettingsModal(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete Tenant"
            description="Are you sure you want to delete this tenant? This action cannot be undone."
            icon={<ExclamationCircleOutlined style={{ color: 'red' }} />}
            onConfirm={() => handleDeleteTenant(record.id)}
            okText="Delete"
            cancelText="Cancel"
            okType="danger"
          >
            <Tooltip title="Delete Tenant">
              <Button
                type="link"
                danger
                icon={<DeleteOutlined />}
                size="small"
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Calculate statistics
  const stats = {
    total: tenants.length,
    active: tenants.filter((t: SystemTenant) => t.status === 'active').length,
    totalUsers: tenants.reduce((sum: number, t: SystemTenant) => sum + t.users_count, 0),
    totalStorage: tenants.reduce((sum: number, t: SystemTenant) => sum + t.storage_used, 0),
  };

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Total Tenants"
              value={stats.total}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Active Tenants"
              value={stats.active}
              valueStyle={{ color: '#52c41a' }}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Total Users"
              value={stats.totalUsers}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Storage Used"
              value={stats.totalStorage}
              suffix="GB"
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tenant Table */}
      <Card
        title="Tenant Management"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            Create Tenant
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={tenants}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} tenants`,
          }}
        />
      </Card>

      {/* Create Tenant Modal */}
      <Modal
        title="Create New Tenant"
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        onOk={() => createForm.submit()}
        confirmLoading={createTenantMutation.isPending}
        width={600}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateTenant}
        >
          <Form.Item
            name="name"
            label="Tenant Name"
            rules={[{ required: true, message: 'Please enter tenant name' }]}
          >
            <Input placeholder="Enter tenant name" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea rows={3} placeholder="Enter tenant description" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="plan"
                label="Plan"
                rules={[{ required: true }]}
                initialValue="free"
              >
                <Select>
                  <Select.Option value="free">Free</Select.Option>
                  <Select.Option value="pro">Pro</Select.Option>
                  <Select.Option value="enterprise">Enterprise</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="storage_limit"
                label="Storage Limit (GB)"
                initialValue={10}
              >
                <InputNumber min={1} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider>Admin Account</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="admin_username"
                label="Admin Username"
                rules={[{ required: true, message: 'Please enter admin username' }]}
              >
                <Input placeholder="Enter admin username" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="admin_email"
                label="Admin Email"
                rules={[
                  { required: true, message: 'Please enter admin email' },
                  { type: 'email', message: 'Please enter a valid email' },
                ]}
              >
                <Input placeholder="Enter admin email" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Edit Tenant Modal */}
      <Modal
        title="Edit Tenant"
        open={editModalOpen}
        onCancel={() => {
          setEditModalOpen(false);
          setSelectedTenant(null);
          editForm.resetFields();
        }}
        onOk={() => editForm.submit()}
        confirmLoading={updateTenantMutation.isPending}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditTenant}
        >
          <Form.Item
            name="name"
            label="Tenant Name"
            rules={[{ required: true, message: 'Please enter tenant name' }]}
          >
            <Input placeholder="Enter tenant name" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea rows={3} placeholder="Enter tenant description" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="status"
                label="Status"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="active">Active</Select.Option>
                  <Select.Option value="inactive">Inactive</Select.Option>
                  <Select.Option value="suspended">Suspended</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="plan"
                label="Plan"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="free">Free</Select.Option>
                  <Select.Option value="pro">Pro</Select.Option>
                  <Select.Option value="enterprise">Enterprise</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="storage_limit"
                label="Storage Limit (GB)"
              >
                <InputNumber min={1} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="cpu_quota"
                label="CPU Quota (cores)"
              >
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="memory_quota"
                label="Memory Quota (GB)"
              >
                <InputNumber min={1} max={256} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="api_rate_limit"
                label="API Rate Limit (req/min)"
              >
                <InputNumber min={100} max={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Settings Modal */}
      <Modal
        title="Tenant Settings"
        open={settingsModalOpen}
        onCancel={() => {
          setSettingsModalOpen(false);
          setSelectedTenant(null);
          settingsForm.resetFields();
        }}
        onOk={() => settingsForm.submit()}
        confirmLoading={updateTenantMutation.isPending}
        width={600}
      >
        <Form
          form={settingsForm}
          layout="vertical"
          onFinish={handleUpdateSettings}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="theme"
                label="Theme"
                initialValue="light"
              >
                <Select>
                  <Select.Option value="light">Light</Select.Option>
                  <Select.Option value="dark">Dark</Select.Option>
                  <Select.Option value="auto">Auto</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="language"
                label="Language"
                initialValue="en"
              >
                <Select>
                  <Select.Option value="en">English</Select.Option>
                  <Select.Option value="zh">中文</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="timezone"
                label="Timezone"
                initialValue="UTC"
              >
                <Select>
                  <Select.Option value="UTC">UTC</Select.Option>
                  <Select.Option value="Asia/Shanghai">Asia/Shanghai</Select.Option>
                  <Select.Option value="America/New_York">America/New_York</Select.Option>
                  <Select.Option value="Europe/London">Europe/London</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="audit_log_retention"
                label="Audit Log Retention (days)"
                initialValue={90}
              >
                <InputNumber min={30} max={365} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="notification_enabled"
                label="Notifications"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="backup_enabled"
                label="Backup"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="backup_frequency"
            label="Backup Frequency"
            initialValue="daily"
          >
            <Select>
              <Select.Option value="daily">Daily</Select.Option>
              <Select.Option value="weekly">Weekly</Select.Option>
              <Select.Option value="monthly">Monthly</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TenantManager;