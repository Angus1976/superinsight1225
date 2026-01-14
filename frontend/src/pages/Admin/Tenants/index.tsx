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
      message.success('租户创建成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '租户创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TenantUpdateRequest }) => 
      tenantApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('租户更新成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '租户更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tenantApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      message.success('租户删除成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '租户删除失败');
    },
  });

  const setStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TenantStatus }) => 
      tenantApi.setStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      message.success('租户状态更新成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '租户状态更新失败');
    },
  });

  const getStatusTag = (status: TenantStatus) => {
    const config = {
      active: { color: 'success', icon: <CheckCircleOutlined />, text: '活跃' },
      suspended: { color: 'warning', icon: <PauseCircleOutlined />, text: '暂停' },
      disabled: { color: 'error', icon: <StopOutlined />, text: '禁用' },
    };
    const { color, icon, text } = config[status] || config.active;
    return <Tag icon={icon} color={color}>{text}</Tag>;
  };

  const columns: ColumnsType<Tenant> = [
    {
      title: '租户信息',
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: TenantStatus) => getStatusTag(status),
      filters: [
        { text: '活跃', value: 'active' },
        { text: '暂停', value: 'suspended' },
        { text: '禁用', value: 'disabled' },
      ],
    },
    {
      title: '套餐',
      dataIndex: 'plan',
      key: 'plan',
      render: (plan: string) => {
        const colors: Record<string, string> = {
          free: 'default',
          basic: 'blue',
          professional: 'purple',
          enterprise: 'gold',
        };
        return <Tag color={colors[plan] || 'default'}>{plan}</Tag>;
      },
    },
    {
      title: '管理员邮箱',
      dataIndex: 'admin_email',
      key: 'admin_email',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '操作',
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
            详情
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
            编辑
          </Button>
          {record.status === 'active' ? (
            <Button
              type="link"
              size="small"
              danger
              onClick={() => {
                Modal.confirm({
                  title: '确认暂停',
                  content: `确定要暂停租户 "${record.name}" 吗？`,
                  onOk: () => setStatusMutation.mutate({ id: record.id, status: 'suspended' }),
                });
              }}
            >
              暂停
            </Button>
          ) : (
            <Button
              type="link"
              size="small"
              onClick={() => setStatusMutation.mutate({ id: record.id, status: 'active' })}
            >
              激活
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: '确认删除',
                content: `确定要删除租户 "${record.name}" 吗？此操作不可恢复！`,
                onOk: () => deleteMutation.mutate(record.id),
              });
            }}
          >
            删除
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
            <Statistic title="总租户数" value={totalTenants} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="活跃租户" value={activeTenants} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="暂停租户" value={suspendedTenants} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="活跃率" 
              value={totalTenants ? Math.round((activeTenants / totalTenants) * 100) : 0} 
              suffix="%" 
            />
          </Card>
        </Col>
      </Row>

      {/* Tenant List */}
      <Card
        title="租户管理"
        extra={
          <Space>
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 120 }}
              onChange={(value) => setStatusFilter(value)}
            >
              <Select.Option value="active">活跃</Select.Option>
              <Select.Option value="suspended">暂停</Select.Option>
              <Select.Option value="disabled">禁用</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
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
              新建租户
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
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingTenant ? '编辑租户' : '新建租户'}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="租户名称"
            rules={[{ required: true, message: '请输入租户名称' }]}
          >
            <Input placeholder="请输入租户名称" />
          </Form.Item>
          
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入租户描述" />
          </Form.Item>
          
          <Form.Item
            name="admin_email"
            label="管理员邮箱"
            rules={[
              { required: true, message: '请输入管理员邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="admin@example.com" />
          </Form.Item>
          
          <Form.Item
            name="plan"
            label="套餐类型"
            initialValue="free"
          >
            <Select>
              <Select.Option value="free">免费版</Select.Option>
              <Select.Option value="basic">基础版</Select.Option>
              <Select.Option value="professional">专业版</Select.Option>
              <Select.Option value="enterprise">企业版</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="租户详情"
        open={isDetailVisible}
        onCancel={() => setIsDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedTenant && (
          <Tabs defaultActiveKey="info">
            <TabPane tab="基本信息" key="info">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="租户ID">{selectedTenant.id}</Descriptions.Item>
                <Descriptions.Item label="名称">{selectedTenant.name}</Descriptions.Item>
                <Descriptions.Item label="状态">{getStatusTag(selectedTenant.status)}</Descriptions.Item>
                <Descriptions.Item label="套餐">{selectedTenant.plan}</Descriptions.Item>
                <Descriptions.Item label="管理员邮箱">{selectedTenant.admin_email}</Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {new Date(selectedTenant.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="描述" span={2}>
                  {selectedTenant.description || '-'}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>
            <TabPane tab="配额使用" key="quota">
              {tenantQuota && tenantUsage ? (
                <div>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card size="small" title="存储">
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
                      <Card size="small" title="项目数">
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
                      <Card size="small" title="用户数">
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
                      <Card size="small" title="API调用">
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
                <div style={{ textAlign: 'center', padding: 20 }}>加载中...</div>
              )}
            </TabPane>
            <TabPane tab="配置" key="config">
              <Descriptions bordered column={1}>
                <Descriptions.Item label="功能配置">
                  {selectedTenant.config?.features && Object.entries(selectedTenant.config.features).map(([key, value]) => (
                    <Tag key={key} color={value ? 'green' : 'default'}>
                      {key}: {value ? '启用' : '禁用'}
                    </Tag>
                  ))}
                </Descriptions.Item>
                <Descriptions.Item label="安全配置">
                  {selectedTenant.config?.security && (
                    <div>
                      <div>MFA: {selectedTenant.config.security.mfa_required ? '必需' : '可选'}</div>
                      <div>会话超时: {selectedTenant.config.security.session_timeout_minutes} 分钟</div>
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
