import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, message, Avatar, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UserOutlined, LockOutlined, UnlockOutlined, MailOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

interface User {
  id: string;
  username: string;
  email: string;
  fullName: string;
  avatar?: string;
  status: 'active' | 'inactive' | 'locked' | 'pending';
  roles: string[];
  tenantId: string;
  tenantName: string;
  lastLoginAt: string;
  createdAt: string;
  isEmailVerified: boolean;
  loginCount: number;
  permissions: string[];
}

const AdminUsers: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();
  const [selectedTenant, setSelectedTenant] = useState<string>('all');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const queryClient = useQueryClient();

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users', selectedTenant, selectedRole, selectedStatus],
    queryFn: () => api.get('/api/v1/admin/users', {
      params: {
        tenant: selectedTenant !== 'all' ? selectedTenant : undefined,
        role: selectedRole !== 'all' ? selectedRole : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
      },
    }).then(res => res.data),
  });

  const { data: tenants } = useQuery({
    queryKey: ['tenants-list'],
    queryFn: () => api.get('/api/v1/admin/tenants/list').then(res => res.data),
  });

  const { data: roles } = useQuery({
    queryKey: ['roles-list'],
    queryFn: () => api.get('/api/v1/security/roles/list').then(res => res.data),
  });

  const createUserMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/admin/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('用户创建成功');
    },
    onError: () => {
      message.error('用户创建失败');
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.put(`/api/v1/admin/users/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('用户更新成功');
    },
    onError: () => {
      message.error('用户更新失败');
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/admin/users/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      message.success('用户删除成功');
    },
    onError: () => {
      message.error('用户删除失败');
    },
  });

  const lockUserMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'lock' | 'unlock' }) => 
      api.post(`/api/v1/admin/users/${id}/${action}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      message.success('用户状态更新成功');
    },
    onError: () => {
      message.error('用户状态更新失败');
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/admin/users/${id}/reset-password`),
    onSuccess: () => {
      message.success('密码重置邮件已发送');
    },
    onError: () => {
      message.error('密码重置失败');
    },
  });

  const columns: ColumnsType<User> = [
    {
      title: '用户信息',
      key: 'userInfo',
      render: (_, record) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Avatar 
            src={record.avatar} 
            icon={<UserOutlined />} 
            style={{ marginRight: 12 }}
          />
          <div>
            <div style={{ fontWeight: 'bold' }}>{record.fullName}</div>
            <div style={{ fontSize: '12px', color: '#666' }}>
              @{record.username}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>
              {record.email}
              {record.isEmailVerified && (
                <Tag color="green" size="small" style={{ marginLeft: 4 }}>已验证</Tag>
              )}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: '租户',
      dataIndex: 'tenantName',
      key: 'tenantName',
      render: (tenantName: string) => <Tag color="blue">{tenantName}</Tag>,
    },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[]) => (
        <Space wrap>
          {roles.map(role => (
            <Tag key={role} color="purple">{role}</Tag>
          ))}
        </Space>
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
          locked: 'error',
          pending: 'processing',
        };
        const labels = {
          active: '活跃',
          inactive: '非活跃',
          locked: '已锁定',
          pending: '待激活',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{labels[status as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '登录统计',
      key: 'loginStats',
      render: (_, record) => (
        <div>
          <div>登录次数: {record.loginCount}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            最后登录: {record.lastLoginAt ? new Date(record.lastLoginAt).toLocaleString() : '从未登录'}
          </div>
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="编辑用户">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingUser(record);
                form.setFieldsValue({
                  ...record,
                  roles: record.roles,
                });
                setIsModalVisible(true);
              }}
            />
          </Tooltip>
          
          <Tooltip title="重置密码">
            <Button
              type="link"
              icon={<MailOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: '确认重置密码',
                  content: `确定要为用户 "${record.fullName}" 重置密码吗？重置链接将发送到用户邮箱。`,
                  onOk: () => resetPasswordMutation.mutate(record.id),
                });
              }}
            />
          </Tooltip>
          
          {record.status === 'locked' ? (
            <Tooltip title="解锁用户">
              <Button
                type="link"
                icon={<UnlockOutlined />}
                onClick={() => lockUserMutation.mutate({ id: record.id, action: 'unlock' })}
              />
            </Tooltip>
          ) : (
            <Tooltip title="锁定用户">
              <Button
                type="link"
                icon={<LockOutlined />}
                onClick={() => {
                  Modal.confirm({
                    title: '确认锁定用户',
                    content: `确定要锁定用户 "${record.fullName}" 吗？`,
                    onOk: () => lockUserMutation.mutate({ id: record.id, action: 'lock' }),
                  });
                }}
              />
            </Tooltip>
          )}
          
          <Tooltip title="删除用户">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: '确认删除',
                  content: `确定要删除用户 "${record.fullName}" 吗？此操作不可恢复！`,
                  onOk: () => deleteUserMutation.mutate(record.id),
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleSubmit = (values: any) => {
    if (editingUser) {
      updateUserMutation.mutate({ id: editingUser.id, data: values });
    } else {
      createUserMutation.mutate(values);
    }
  };

  return (
    <div className="admin-users">
      <Card
        title="用户管理"
        extra={
          <Space>
            <Select
              value={selectedTenant}
              onChange={setSelectedTenant}
              style={{ width: 120 }}
              placeholder="选择租户"
            >
              <Select.Option value="all">全部租户</Select.Option>
              {tenants?.map((tenant: any) => (
                <Select.Option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </Select.Option>
              ))}
            </Select>
            
            <Select
              value={selectedRole}
              onChange={setSelectedRole}
              style={{ width: 120 }}
              placeholder="选择角色"
            >
              <Select.Option value="all">全部角色</Select.Option>
              {roles?.map((role: any) => (
                <Select.Option key={role.code} value={role.code}>
                  {role.name}
                </Select.Option>
              ))}
            </Select>
            
            <Select
              value={selectedStatus}
              onChange={setSelectedStatus}
              style={{ width: 120 }}
              placeholder="选择状态"
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="active">活跃</Select.Option>
              <Select.Option value="inactive">非活跃</Select.Option>
              <Select.Option value="locked">已锁定</Select.Option>
              <Select.Option value="pending">待激活</Select.Option>
            </Select>
            
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingUser(null);
                form.resetFields();
                setIsModalVisible(true);
              }}
            >
              新建用户
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={users}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createUserMutation.isPending || updateUserMutation.isPending}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>
          
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          
          <Form.Item
            name="fullName"
            label="姓名"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input placeholder="请输入姓名" />
          </Form.Item>
          
          <Form.Item
            name="tenantId"
            label="所属租户"
            rules={[{ required: true, message: '请选择租户' }]}
          >
            <Select placeholder="请选择租户">
              {tenants?.map((tenant: any) => (
                <Select.Option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="roles"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select mode="multiple" placeholder="请选择角色">
              {roles?.map((role: any) => (
                <Select.Option key={role.code} value={role.code}>
                  {role.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          
          {!editingUser && (
            <Form.Item
              name="password"
              label="初始密码"
              rules={[{ required: true, message: '请输入初始密码' }]}
            >
              <Input.Password placeholder="请输入初始密码" />
            </Form.Item>
          )}
          
          <Form.Item
            name="status"
            label="状态"
            initialValue="active"
          >
            <Select>
              <Select.Option value="active">活跃</Select.Option>
              <Select.Option value="inactive">非活跃</Select.Option>
              <Select.Option value="pending">待激活</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="isEmailVerified"
            label="邮箱验证"
            valuePropName="checked"
            initialValue={false}
          >
            <Switch checkedChildren="已验证" unCheckedChildren="未验证" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminUsers;