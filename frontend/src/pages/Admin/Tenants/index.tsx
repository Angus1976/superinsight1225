import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, message, Progress, Statistic, Row, Col } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SettingOutlined, UserOutlined, DatabaseOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

interface Tenant {
  id: string;
  name: string;
  code: string;
  description: string;
  status: 'active' | 'inactive' | 'suspended';
  plan: 'basic' | 'professional' | 'enterprise';
  userCount: number;
  workspaceCount: number;
  storageUsed: number;
  storageLimit: number;
  apiCallsUsed: number;
  apiCallsLimit: number;
  createdAt: string;
  lastActiveAt: string;
  settings: {
    maxUsers: number;
    maxWorkspaces: number;
    features: string[];
  };
}

const AdminTenants: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: tenants, isLoading } = useQuery({
    queryKey: ['admin-tenants'],
    queryFn: () => api.get('/api/v1/admin/tenants').then(res => res.data),
  });

  const createTenantMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/admin/tenants', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('租户创建成功');
    },
    onError: () => {
      message.error('租户创建失败');
    },
  });

  const updateTenantMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.put(`/api/v1/admin/tenants/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('租户更新成功');
    },
    onError: () => {
      message.error('租户更新失败');
    },
  });

  const deleteTenantMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/admin/tenants/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
      message.success('租户删除成功');
    },
    onError: () => {
      message.error('租户删除失败');
    },
  });

  const suspendTenantMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'suspend' | 'activate' }) => 
      api.post(`/api/v1/admin/tenants/${id}/${action}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
      message.success('租户状态更新成功');
    },
    onError: () => {
      message.error('租户状态更新失败');
    },
  });

  const columns: ColumnsType<Tenant> = [
    {
      title: '租户信息',
      key: 'info',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{record.name}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            代码: {record.code}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.description}
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          active: 'success',
          inactive: 'default',
          suspended: 'error',
        };
        const labels = {
          active: '活跃',
          inactive: '非活跃',
          suspended: '已暂停',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{labels[status as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '套餐',
      dataIndex: 'plan',
      key: 'plan',
      render: (plan: string) => {
        const colors = {
          basic: 'default',
          professional: 'processing',
          enterprise: 'success',
        };
        const labels = {
          basic: '基础版',
          professional: '专业版',
          enterprise: '企业版',
        };
        return <Tag color={colors[plan as keyof typeof colors]}>{labels[plan as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '用户/工作空间',
      key: 'usage',
      render: (_, record) => (
        <div>
          <div>
            <UserOutlined /> {record.userCount}/{record.settings.maxUsers}
          </div>
          <div>
            <DatabaseOutlined /> {record.workspaceCount}/{record.settings.maxWorkspaces}
          </div>
        </div>
      ),
    },
    {
      title: '存储使用',
      key: 'storage',
      render: (_, record) => {
        const percentage = (record.storageUsed / record.storageLimit) * 100;
        return (
          <div>
            <Progress 
              percent={percentage} 
              size="small" 
              status={percentage > 90 ? 'exception' : percentage > 70 ? 'active' : 'normal'}
            />
            <div style={{ fontSize: '12px', color: '#666' }}>
              {(record.storageUsed / 1024 / 1024 / 1024).toFixed(2)}GB / 
              {(record.storageLimit / 1024 / 1024 / 1024).toFixed(2)}GB
            </div>
          </div>
        );
      },
    },
    {
      title: 'API调用',
      key: 'apiCalls',
      render: (_, record) => {
        const percentage = (record.apiCallsUsed / record.apiCallsLimit) * 100;
        return (
          <div>
            <Progress 
              percent={percentage} 
              size="small" 
              status={percentage > 90 ? 'exception' : percentage > 70 ? 'active' : 'normal'}
            />
            <div style={{ fontSize: '12px', color: '#666' }}>
              {record.apiCallsUsed.toLocaleString()} / {record.apiCallsLimit.toLocaleString()}
            </div>
          </div>
        );
      },
    },
    {
      title: '最后活跃',
      dataIndex: 'lastActiveAt',
      key: 'lastActiveAt',
      render: (date: string) => date ? new Date(date).toLocaleString() : '从未活跃',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingTenant(record);
              form.setFieldsValue(record);
              setIsModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Button
            type="link"
            icon={<SettingOutlined />}
            onClick={() => {
              // 租户设置
              console.log('租户设置:', record.id);
            }}
          >
            设置
          </Button>
          {record.status === 'active' ? (
            <Button
              type="link"
              danger
              onClick={() => {
                Modal.confirm({
                  title: '确认暂停',
                  content: `确定要暂停租户 "${record.name}" 吗？`,
                  onOk: () => suspendTenantMutation.mutate({ id: record.id, action: 'suspend' }),
                });
              }}
            >
              暂停
            </Button>
          ) : (
            <Button
              type="link"
              onClick={() => suspendTenantMutation.mutate({ id: record.id, action: 'activate' })}
            >
              激活
            </Button>
          )}
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: '确认删除',
                content: `确定要删除租户 "${record.name}" 吗？此操作不可恢复！`,
                onOk: () => deleteTenantMutation.mutate(record.id),
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
      updateTenantMutation.mutate({ id: editingTenant.id, data: values });
    } else {
      createTenantMutation.mutate(values);
    }
  };

  // 统计数据
  const totalTenants = tenants?.length || 0;
  const activeTenants = tenants?.filter((t: Tenant) => t.status === 'active').length || 0;
  const totalUsers = tenants?.reduce((sum: number, t: Tenant) => sum + t.userCount, 0) || 0;
  const totalStorage = tenants?.reduce((sum: number, t: Tenant) => sum + t.storageUsed, 0) || 0;

  return (
    <div className="admin-tenants">
      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总租户数" value={totalTenants} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="活跃租户" value={activeTenants} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总用户数" value={totalUsers} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="总存储使用" 
              value={(totalStorage / 1024 / 1024 / 1024).toFixed(2)} 
              suffix="GB" 
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="租户管理"
        extra={
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
        }
      >
        <Table
          columns={columns}
          dataSource={tenants}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: 1400 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      <Modal
        title={editingTenant ? '编辑租户' : '新建租户'}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createTenantMutation.isPending || updateTenantMutation.isPending}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label="租户名称"
            rules={[{ required: true, message: '请输入租户名称' }]}
          >
            <Input placeholder="请输入租户名称" />
          </Form.Item>
          
          <Form.Item
            name="code"
            label="租户代码"
            rules={[{ required: true, message: '请输入租户代码' }]}
          >
            <Input placeholder="请输入租户代码（唯一标识）" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={3} placeholder="请输入租户描述" />
          </Form.Item>
          
          <Form.Item
            name="plan"
            label="套餐类型"
            rules={[{ required: true, message: '请选择套餐类型' }]}
          >
            <Select placeholder="请选择套餐类型">
              <Select.Option value="basic">基础版</Select.Option>
              <Select.Option value="professional">专业版</Select.Option>
              <Select.Option value="enterprise">企业版</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name={['settings', 'maxUsers']}
            label="最大用户数"
            rules={[{ required: true, message: '请输入最大用户数' }]}
          >
            <Input type="number" min={1} placeholder="100" />
          </Form.Item>
          
          <Form.Item
            name={['settings', 'maxWorkspaces']}
            label="最大工作空间数"
            rules={[{ required: true, message: '请输入最大工作空间数' }]}
          >
            <Input type="number" min={1} placeholder="10" />
          </Form.Item>
          
          <Form.Item
            name="storageLimit"
            label="存储限制（GB）"
            rules={[{ required: true, message: '请输入存储限制' }]}
          >
            <Input type="number" min={1} placeholder="100" />
          </Form.Item>
          
          <Form.Item
            name="apiCallsLimit"
            label="API调用限制（每月）"
            rules={[{ required: true, message: '请输入API调用限制' }]}
          >
            <Input type="number" min={1000} placeholder="100000" />
          </Form.Item>
          
          <Form.Item
            name="status"
            label="状态"
            initialValue="active"
          >
            <Select>
              <Select.Option value="active">活跃</Select.Option>
              <Select.Option value="inactive">非活跃</Select.Option>
              <Select.Option value="suspended">已暂停</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminTenants;