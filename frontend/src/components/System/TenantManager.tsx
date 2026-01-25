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
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation('admin');
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
      title: t('tenants.columns.tenantInfo'),
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
      title: t('tenants.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: keyof typeof statusColors) => (
        <Tag color={statusColors[status]}>{t(`tenants.status.${status}`)}</Tag>
      ),
    },
    {
      title: t('tenants.columns.plan'),
      dataIndex: 'plan',
      key: 'plan',
      render: (plan: keyof typeof planColors) => (
        <Tag color={planColors[plan]}>{t(`tenants.plan.${plan}`)}</Tag>
      ),
    },
    {
      title: t('tenants.columns.users'),
      dataIndex: 'users_count',
      key: 'users_count',
      render: (count) => (
        <Tooltip title={t('tenants.tooltips.activeUsers')}>
          <Space>
            <UserOutlined />
            {count}
          </Space>
        </Tooltip>
      ),
    },
    {
      title: t('tenants.columns.storageUsage'),
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
      title: t('tenants.columns.resources'),
      key: 'resources',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Tooltip title={t('tenants.tooltips.cpuQuota')}>
            <Space size="small">
              <CloudOutlined />
              {record.cpu_quota} cores
            </Space>
          </Tooltip>
          <Tooltip title={t('tenants.tooltips.memoryQuota')}>
            <Space size="small">
              <DatabaseOutlined />
              {record.memory_quota}GB
            </Space>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: t('tenants.columns.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: t('tenants.columns.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('tenants.tooltips.editTenant')}>
            <Button
              type="link"
              icon={<EditOutlined />}
              size="small"
              onClick={() => openEditModal(record)}
            />
          </Tooltip>
          <Tooltip title={t('tenants.tooltips.settings')}>
            <Button
              type="link"
              icon={<SettingOutlined />}
              size="small"
              onClick={() => openSettingsModal(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('tenants.deleteTenant')}
            description={t('tenants.deleteWarning')}
            icon={<ExclamationCircleOutlined style={{ color: 'red' }} />}
            onConfirm={() => handleDeleteTenant(record.id)}
            okText={t('common.delete')}
            cancelText={t('common.cancel')}
            okType="danger"
          >
            <Tooltip title={t('tenants.tooltips.deleteTenant')}>
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
              title={t('tenants.stats.totalTenants')}
              value={stats.total}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('tenants.stats.activeTenants')}
              value={stats.active}
              valueStyle={{ color: '#52c41a' }}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('tenants.stats.totalUsers')}
              value={stats.totalUsers}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('tenants.stats.storageUsed')}
              value={stats.totalStorage}
              suffix="GB"
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tenant Table */}
      <Card
        title={t('tenants.title')}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            {t('tenants.createTenant')}
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
              t('tenants.pagination.range', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      {/* Create Tenant Modal */}
      <Modal
        title={t('tenants.createTenant')}
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
            label={t('tenants.form.name')}
            rules={[{ required: true, message: t('tenants.form.nameRequired') }]}
          >
            <Input placeholder={t('tenants.form.namePlaceholder')} />
          </Form.Item>
          
          <Form.Item
            name="description"
            label={t('tenants.form.description')}
          >
            <TextArea rows={3} placeholder={t('tenants.form.descriptionPlaceholder')} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="plan"
                label={t('tenants.form.plan')}
                rules={[{ required: true }]}
                initialValue="free"
              >
                <Select>
                  <Select.Option value="free">{t('tenants.plan.free')}</Select.Option>
                  <Select.Option value="pro">{t('tenants.plan.pro')}</Select.Option>
                  <Select.Option value="enterprise">{t('tenants.plan.enterprise')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="storage_limit"
                label={t('tenants.form.storageLimit')}
                initialValue={10}
              >
                <InputNumber min={1} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider>{t('tenants.form.adminAccount')}</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="admin_username"
                label={t('tenants.form.adminUsername')}
                rules={[{ required: true, message: t('tenants.form.adminUsernameRequired') }]}
              >
                <Input placeholder={t('tenants.form.adminUsernamePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="admin_email"
                label={t('tenants.form.adminEmail')}
                rules={[
                  { required: true, message: t('tenants.form.adminEmailRequired') },
                  { type: 'email', message: t('tenants.form.adminEmailInvalid') },
                ]}
              >
                <Input placeholder={t('tenants.form.adminEmailPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Edit Tenant Modal */}
      <Modal
        title={t('tenants.editTenant')}
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
            label={t('tenants.form.name')}
            rules={[{ required: true, message: t('tenants.form.nameRequired') }]}
          >
            <Input placeholder={t('tenants.form.namePlaceholder')} />
          </Form.Item>
          
          <Form.Item
            name="description"
            label={t('tenants.form.description')}
          >
            <TextArea rows={3} placeholder={t('tenants.form.descriptionPlaceholder')} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="status"
                label={t('tenants.columns.status')}
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="active">{t('tenants.status.active')}</Select.Option>
                  <Select.Option value="inactive">{t('tenants.status.inactive')}</Select.Option>
                  <Select.Option value="suspended">{t('tenants.status.suspended')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="plan"
                label={t('tenants.form.plan')}
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="free">{t('tenants.plan.free')}</Select.Option>
                  <Select.Option value="pro">{t('tenants.plan.pro')}</Select.Option>
                  <Select.Option value="enterprise">{t('tenants.plan.enterprise')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="storage_limit"
                label={t('tenants.form.storageLimit')}
              >
                <InputNumber min={1} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="cpu_quota"
                label={t('tenants.form.cpuQuota')}
              >
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="memory_quota"
                label={t('tenants.form.memoryQuota')}
              >
                <InputNumber min={1} max={256} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="api_rate_limit"
                label={t('tenants.form.apiRateLimit')}
              >
                <InputNumber min={100} max={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Settings Modal */}
      <Modal
        title={t('tenants.tenantSettings')}
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
                label={t('tenants.settings.theme')}
                initialValue="light"
              >
                <Select>
                  <Select.Option value="light">{t('tenants.settings.themeLight')}</Select.Option>
                  <Select.Option value="dark">{t('tenants.settings.themeDark')}</Select.Option>
                  <Select.Option value="auto">{t('tenants.settings.themeAuto')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="language"
                label={t('tenants.settings.language')}
                initialValue="en"
              >
                <Select>
                  <Select.Option value="en">{t('tenants.settings.languageEn')}</Select.Option>
                  <Select.Option value="zh">{t('tenants.settings.languageZh')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="timezone"
                label={t('tenants.settings.timezone')}
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
                label={t('tenants.settings.auditLogRetention')}
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
                label={t('tenants.settings.notifications')}
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="backup_enabled"
                label={t('tenants.settings.backup')}
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="backup_frequency"
            label={t('tenants.settings.backupFrequency')}
            initialValue="daily"
          >
            <Select>
              <Select.Option value="daily">{t('tenants.settings.backupDaily')}</Select.Option>
              <Select.Option value="weekly">{t('tenants.settings.backupWeekly')}</Select.Option>
              <Select.Option value="monthly">{t('tenants.settings.backupMonthly')}</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TenantManager;