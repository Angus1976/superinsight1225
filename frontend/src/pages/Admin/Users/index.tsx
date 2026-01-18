import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation('admin');
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
      message.success(t('users.createSuccess'));
    },
    onError: () => {
      message.error(t('users.createFailed'));
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.put(`/api/v1/admin/users/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('users.updateSuccess'));
    },
    onError: () => {
      message.error(t('users.updateFailed'));
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/admin/users/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      message.success(t('users.deleteSuccess'));
    },
    onError: () => {
      message.error(t('users.deleteFailed'));
    },
  });

  const lockUserMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'lock' | 'unlock' }) =>
      api.post(`/api/v1/admin/users/${id}/${action}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      message.success(t('users.statusUpdateSuccess'));
    },
    onError: () => {
      message.error(t('users.statusUpdateFailed'));
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/admin/users/${id}/reset-password`),
    onSuccess: () => {
      message.success(t('users.passwordResetSent'));
    },
    onError: () => {
      message.error(t('users.passwordResetFailed'));
    },
  });

  const columns: ColumnsType<User> = [
    {
      title: t('users.columns.userInfo'),
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
                <Tag color="green" style={{ marginLeft: 4 }}>{t('users.info.verified')}</Tag>
              )}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: t('users.columns.tenant'),
      dataIndex: 'tenantName',
      key: 'tenantName',
      render: (tenantName: string) => <Tag color="blue">{tenantName}</Tag>,
    },
    {
      title: t('users.columns.roles'),
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
      title: t('users.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          active: 'success',
          inactive: 'default',
          locked: 'error',
          pending: 'processing',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{t(`users.status.${status}`)}</Tag>;
      },
    },
    {
      title: t('users.columns.loginStats'),
      key: 'loginStats',
      render: (_, record) => (
        <div>
          <div>{t('users.info.loginCount')}: {record.loginCount}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {t('users.info.lastLogin')}: {record.lastLoginAt ? new Date(record.lastLoginAt).toLocaleString() : t('users.info.neverLoggedIn')}
          </div>
        </div>
      ),
    },
    {
      title: t('users.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('users.columns.action'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title={t('users.actions.edit')}>
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

          <Tooltip title={t('users.actions.resetPassword')}>
            <Button
              type="link"
              icon={<MailOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: t('users.confirmResetPassword'),
                  content: t('users.confirmResetPasswordMessage', { name: record.fullName }),
                  onOk: () => resetPasswordMutation.mutate(record.id),
                });
              }}
            />
          </Tooltip>

          {record.status === 'locked' ? (
            <Tooltip title={t('users.actions.unlock')}>
              <Button
                type="link"
                icon={<UnlockOutlined />}
                onClick={() => lockUserMutation.mutate({ id: record.id, action: 'unlock' })}
              />
            </Tooltip>
          ) : (
            <Tooltip title={t('users.actions.lock')}>
              <Button
                type="link"
                icon={<LockOutlined />}
                onClick={() => {
                  Modal.confirm({
                    title: t('users.confirmLock'),
                    content: t('users.confirmLockMessage', { name: record.fullName }),
                    onOk: () => lockUserMutation.mutate({ id: record.id, action: 'lock' }),
                  });
                }}
              />
            </Tooltip>
          )}

          <Tooltip title={t('users.actions.delete')}>
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: t('users.confirmDelete'),
                  content: t('users.confirmDeleteMessage', { name: record.fullName }),
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
        title={t('users.title')}
        extra={
          <Space>
            <Select
              value={selectedTenant}
              onChange={setSelectedTenant}
              style={{ width: 120 }}
              placeholder={t('users.filters.selectTenant')}
            >
              <Select.Option value="all">{t('users.filters.allTenants')}</Select.Option>
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
              placeholder={t('users.filters.selectRole')}
            >
              <Select.Option value="all">{t('users.filters.allRoles')}</Select.Option>
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
              placeholder={t('users.filters.selectStatus')}
            >
              <Select.Option value="all">{t('users.filters.allStatus')}</Select.Option>
              <Select.Option value="active">{t('users.status.active')}</Select.Option>
              <Select.Option value="inactive">{t('users.status.inactive')}</Select.Option>
              <Select.Option value="locked">{t('users.status.locked')}</Select.Option>
              <Select.Option value="pending">{t('users.status.pending')}</Select.Option>
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
              {t('users.createUser')}
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
            showTotal: (total, range) => t('common:pagination.total', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      <Modal
        title={editingUser ? t('users.editUser') : t('users.createUser')}
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
            label={t('users.form.username')}
            rules={[{ required: true, message: t('users.form.usernameRequired') }]}
          >
            <Input placeholder={t('users.form.usernamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="email"
            label={t('users.form.email')}
            rules={[
              { required: true, message: t('users.form.emailRequired') },
              { type: 'email', message: t('users.form.emailInvalid') },
            ]}
          >
            <Input placeholder={t('users.form.emailPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="fullName"
            label={t('users.form.fullName')}
            rules={[{ required: true, message: t('users.form.fullNameRequired') }]}
          >
            <Input placeholder={t('users.form.fullNamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="tenantId"
            label={t('users.form.tenant')}
            rules={[{ required: true, message: t('users.form.tenantRequired') }]}
          >
            <Select placeholder={t('users.form.tenantPlaceholder')}>
              {tenants?.map((tenant: any) => (
                <Select.Option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="roles"
            label={t('users.form.roles')}
            rules={[{ required: true, message: t('users.form.rolesRequired') }]}
          >
            <Select mode="multiple" placeholder={t('users.form.rolesPlaceholder')}>
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
              label={t('users.form.password')}
              rules={[{ required: true, message: t('users.form.passwordRequired') }]}
            >
              <Input.Password placeholder={t('users.form.passwordPlaceholder')} />
            </Form.Item>
          )}

          <Form.Item
            name="status"
            label={t('users.form.status')}
            initialValue="active"
          >
            <Select>
              <Select.Option value="active">{t('users.status.active')}</Select.Option>
              <Select.Option value="inactive">{t('users.status.inactive')}</Select.Option>
              <Select.Option value="pending">{t('users.status.pending')}</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="isEmailVerified"
            label={t('users.form.isEmailVerified')}
            valuePropName="checked"
            initialValue={false}
          >
            <Switch checkedChildren={t('users.form.verified')} unCheckedChildren={t('users.form.unverified')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminUsers;