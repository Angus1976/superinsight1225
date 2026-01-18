/**
 * Tenant Management Page
 * 
 * Provides comprehensive tenant management including:
 * - Tenant list with filtering
 * - Create/Edit/Delete tenants
 * - Status management (active/suspended/disabled)
 * - Quota overview
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card, Table, Button, Space, Tag, Modal, Form, Input, Select,
  message, Progress, Statistic, Row, Col, Tabs, Descriptions, Badge
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SettingOutlined,
  UserOutlined, DatabaseOutlined, ReloadOutlined, EyeOutlined,
  CheckCircleOutlined, PauseCircleOutlined, StopOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  tenantApi, quotaApi,
  Tenant, TenantStatus, TenantCreateRequest, TenantUpdateRequest,
  QuotaResponse, QuotaUsage
} from '@/services/multiTenantApi';

const { TabPane } = Tabs;

const AdminTenants: React.FC = () => {
  const { t } = useTranslation('admin');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDetailVisible, setIsDetailVisible] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [statusFilter, setStatusFilter] = useState<TenantStatus | undefined>();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch tenants
  const { data: tenants, isLoading, refetch } = useQuery({
    queryKey: ['tenants', statusFilter],
    queryFn: () => tenantApi.list({ status: statusFilter }).then(res => res.data),
  });

  // Fetch quota for selected tenant
  const { data: tenantQuota } = useQuery({
    queryKey: ['tenant-quota', selectedTenant?.id],
    queryFn: () => selectedTenant ? quotaApi.get('tenant', selectedTenant.id).then(res => res.data) : null,
    enabled: !!selectedTenant,
  });

  const { data: tenantUsage } = useQuery({
    queryKey: ['tenant-usage', selectedTenant?.id],
    queryFn: () => selectedTenant ? quotaApi.getUsage('tenant', selectedTenant.id).then(res => res.data) : null,
    enabled: !!selectedTenant,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: TenantCreateRequest) => tenantApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('tenants.createSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('tenants.createFailed'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TenantUpdateRequest }) =>
      tenantApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('tenants.updateSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('tenants.updateFailed'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tenantApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      message.success(t('tenants.deleteSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('tenants.deleteFailed'));
    },
  });

  const setStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TenantStatus }) =>
      tenantApi.setStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      message.success(t('tenants.statusUpdateSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('tenants.statusUpdateFailed'));
    },
  });

  const getStatusTag = (status: TenantStatus) => {
    const config = {
      active: { color: 'success', icon: <CheckCircleOutlined />, text: t('tenants.status.active') },
      suspended: { color: 'warning', icon: <PauseCircleOutlined />, text: t('tenants.status.suspended') },
      disabled: { color: 'error', icon: <StopOutlined />, text: t('tenants.status.disabled') },
    };
    const { color, icon, text } = config[status] || config.active;
    return <Tag icon={icon} color={color}>{text}</Tag>;
  };

  const columns: ColumnsType<Tenant> = [
    {
      title: t('tenants.columns.tenantInfo'),
      key: 'info',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{record.name}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            ID: {record.id.slice(0, 8)}...
          </div>
          {record.description && (
            <div style={{ fontSize: '12px', color: '#999' }}>
              {record.description.slice(0, 50)}...
            </div>
          )}
        </div>
      ),
    },
    {
      title: t('tenants.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: TenantStatus) => getStatusTag(status),
      filters: [
        { text: t('tenants.status.active'), value: 'active' },
        { text: t('tenants.status.suspended'), value: 'suspended' },
        { text: t('tenants.status.disabled'), value: 'disabled' },
      ],
    },
    {
      title: t('tenants.columns.plan'),
      dataIndex: 'plan',
      key: 'plan',
      render: (plan: string) => {
        const colors: Record<string, string> = {
          free: 'default',
          basic: 'blue',
          professional: 'purple',
          enterprise: 'gold',
        };
        return <Tag color={colors[plan] || 'default'}>{t(`tenants.plans.${plan}`)}</Tag>;
      },
    },
    {
      title: t('tenants.columns.adminEmail'),
      dataIndex: 'admin_email',
      key: 'admin_email',
    },
    {
      title: t('tenants.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: t('tenants.columns.action'),
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedTenant(record);
              setIsDetailVisible(true);
            }}
          >
            {t('tenants.actions.detail')}
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingTenant(record);
              form.setFieldsValue({
                name: record.name,
                description: record.description,
                admin_email: record.admin_email,
                plan: record.plan,
              });
              setIsModalVisible(true);
            }}
          >
            {t('tenants.actions.edit')}
          </Button>
          {record.status === 'active' ? (
            <Button
              type="link"
              size="small"
              danger
              onClick={() => {
                Modal.confirm({
                  title: t('tenants.confirmSuspend'),
                  content: t('tenants.confirmSuspendMessage', { name: record.name }),
                  onOk: () => setStatusMutation.mutate({ id: record.id, status: 'suspended' }),
                });
              }}
            >
              {t('tenants.actions.suspend')}
            </Button>
          ) : (
            <Button
              type="link"
              size="small"
              onClick={() => setStatusMutation.mutate({ id: record.id, status: 'active' })}
            >
              {t('tenants.actions.activate')}
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: t('tenants.confirmDelete'),
                content: t('tenants.confirmDeleteMessage', { name: record.name }),
                onOk: () => deleteMutation.mutate(record.id),
              });
            }}
          >
            {t('tenants.actions.delete')}
          </Button>
        </Space>
      ),
    },
  ];

  const handleSubmit = (values: any) => {
    if (editingTenant) {
      updateMutation.mutate({ id: editingTenant.id, data: values });
    } else {
      createMutation.mutate(values);
    }
  };

  // Statistics
  const totalTenants = tenants?.length || 0;
  const activeTenants = tenants?.filter(t => t.status === 'active').length || 0;
  const suspendedTenants = tenants?.filter(t => t.status === 'suspended').length || 0;

  return (
    <div className="admin-tenants">
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('tenants.stats.totalTenants')} value={totalTenants} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('tenants.stats.activeTenants')} value={activeTenants} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('tenants.stats.suspendedTenants')} value={suspendedTenants} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('tenants.stats.activeRate')}
              value={totalTenants ? Math.round((activeTenants / totalTenants) * 100) : 0}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* Tenant List */}
      <Card
        title={t('tenants.title')}
        extra={
          <Space>
            <Select
              placeholder={t('tenants.statusFilter')}
              allowClear
              style={{ width: 120 }}
              onChange={(value) => setStatusFilter(value)}
            >
              <Select.Option value="active">{t('tenants.status.active')}</Select.Option>
              <Select.Option value="suspended">{t('tenants.status.suspended')}</Select.Option>
              <Select.Option value="disabled">{t('tenants.status.disabled')}</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('common:refresh')}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingTenant(null);
                form.resetFields();
                setIsModalVisible(true);
              }}
            >
              {t('tenants.createTenant')}
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={tenants}
          loading={isLoading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => t('tenants.pagination.total', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingTenant ? t('tenants.editTenant') : t('tenants.createTenant')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label={t('tenants.form.name')}
            rules={[{ required: true, message: t('tenants.form.nameRequired') }]}
          >
            <Input placeholder={t('tenants.form.namePlaceholder')} />
          </Form.Item>

          <Form.Item name="description" label={t('tenants.form.description')}>
            <Input.TextArea rows={3} placeholder={t('tenants.form.descriptionPlaceholder')} />
          </Form.Item>

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

          <Form.Item
            name="plan"
            label={t('tenants.form.plan')}
            initialValue="free"
          >
            <Select>
              <Select.Option value="free">{t('tenants.plans.free')}</Select.Option>
              <Select.Option value="basic">{t('tenants.plans.basic')}</Select.Option>
              <Select.Option value="professional">{t('tenants.plans.professional')}</Select.Option>
              <Select.Option value="enterprise">{t('tenants.plans.enterprise')}</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title={t('tenants.tenantDetail')}
        open={isDetailVisible}
        onCancel={() => setIsDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedTenant && (
          <Tabs defaultActiveKey="info">
            <TabPane tab={t('tenants.detail.basicInfo')} key="info">
              <Descriptions bordered column={2}>
                <Descriptions.Item label={t('tenants.detail.tenantId')}>{selectedTenant.id}</Descriptions.Item>
                <Descriptions.Item label={t('tenants.detail.name')}>{selectedTenant.name}</Descriptions.Item>
                <Descriptions.Item label={t('tenants.detail.status')}>{getStatusTag(selectedTenant.status)}</Descriptions.Item>
                <Descriptions.Item label={t('tenants.detail.plan')}>{t(`tenants.plans.${selectedTenant.plan}`)}</Descriptions.Item>
                <Descriptions.Item label={t('tenants.detail.adminEmail')}>{selectedTenant.admin_email}</Descriptions.Item>
                <Descriptions.Item label={t('tenants.detail.createdAt')}>
                  {new Date(selectedTenant.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label={t('tenants.detail.description')} span={2}>
                  {selectedTenant.description || '-'}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>
            <TabPane tab={t('tenants.detail.quotaUsage')} key="quota">
              {tenantQuota && tenantUsage ? (
                <div>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card size="small" title={t('tenants.quota.storage')}>
                        <Progress
                          percent={Math.round((tenantUsage.storage_bytes / tenantQuota.storage_bytes) * 100)}
                          status={tenantUsage.storage_bytes / tenantQuota.storage_bytes > 0.9 ? 'exception' : 'active'}
                        />
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {(tenantUsage.storage_bytes / 1024 / 1024 / 1024).toFixed(2)} GB /
                          {(tenantQuota.storage_bytes / 1024 / 1024 / 1024).toFixed(2)} GB
                        </div>
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small" title={t('tenants.quota.projectCount')}>
                        <Progress
                          percent={Math.round((tenantUsage.project_count / tenantQuota.project_count) * 100)}
                          status={tenantUsage.project_count / tenantQuota.project_count > 0.9 ? 'exception' : 'active'}
                        />
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {tenantUsage.project_count} / {tenantQuota.project_count}
                        </div>
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={16} style={{ marginTop: 16 }}>
                    <Col span={12}>
                      <Card size="small" title={t('tenants.quota.userCount')}>
                        <Progress
                          percent={Math.round((tenantUsage.user_count / tenantQuota.user_count) * 100)}
                          status={tenantUsage.user_count / tenantQuota.user_count > 0.9 ? 'exception' : 'active'}
                        />
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {tenantUsage.user_count} / {tenantQuota.user_count}
                        </div>
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small" title={t('tenants.quota.apiCalls')}>
                        <Progress
                          percent={Math.round((tenantUsage.api_call_count / tenantQuota.api_call_count) * 100)}
                          status={tenantUsage.api_call_count / tenantQuota.api_call_count > 0.9 ? 'exception' : 'active'}
                        />
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {tenantUsage.api_call_count.toLocaleString()} / {tenantQuota.api_call_count.toLocaleString()}
                        </div>
                      </Card>
                    </Col>
                  </Row>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: 20 }}>{t('common:loading')}</div>
              )}
            </TabPane>
            <TabPane tab={t('tenants.detail.config')} key="config">
              <Descriptions bordered column={1}>
                <Descriptions.Item label={t('tenants.config.features')}>
                  {selectedTenant.config?.features && Object.entries(selectedTenant.config.features).map(([key, value]) => (
                    <Tag key={key} color={value ? 'green' : 'default'}>
                      {key}: {value ? t('tenants.config.enabled') : t('tenants.config.disabled')}
                    </Tag>
                  ))}
                </Descriptions.Item>
                <Descriptions.Item label={t('tenants.config.security')}>
                  {selectedTenant.config?.security && (
                    <div>
                      <div>{t('tenants.config.mfa')}: {selectedTenant.config.security.mfa_required ? t('tenants.config.mfaRequired') : t('tenants.config.mfaOptional')}</div>
                      <div>{t('tenants.config.sessionTimeout')}: {selectedTenant.config.security.session_timeout_minutes} {t('tenants.config.minutes')}</div>
                    </div>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>
          </Tabs>
        )}
      </Modal>
    </div>
  );
};

export default AdminTenants;
