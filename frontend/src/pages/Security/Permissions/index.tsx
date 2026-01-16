import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Tree, message, Tabs, Switch } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined, TeamOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { DataNode } from 'antd/es/tree';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/services/api';

const { TabPane } = Tabs;

interface Permission {
  id: string;
  name: string;
  code: string;
  description: string;
  resource: string;
  action: string;
  enabled: boolean;
  createdAt: string;
}

interface Role {
  id: string;
  name: string;
  code: string;
  description: string;
  permissions: string[];
  userCount: number;
  enabled: boolean;
  createdAt: string;
}

interface UserPermission {
  userId: string;
  userName: string;
  email: string;
  roles: string[];
  directPermissions: string[];
  effectivePermissions: string[];
  lastLogin: string;
}

const SecurityPermissions: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [activeTab, setActiveTab] = useState('permissions');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalType, setModalType] = useState<'permission' | 'role'>('permission');
  const [editingItem, setEditingItem] = useState<Permission | Role | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 权限数据
  const { data: permissions, isLoading: permissionsLoading } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => api.get('/api/v1/security/permissions').then(res => res.data),
  });

  // 角色数据
  const { data: roles, isLoading: rolesLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.get('/api/v1/security/roles').then(res => res.data),
  });

  // 用户权限数据
  const { data: userPermissions, isLoading: userPermissionsLoading } = useQuery({
    queryKey: ['user-permissions'],
    queryFn: () => api.get('/api/v1/security/user-permissions').then(res => res.data),
  });

  // 权限树数据
  const { data: permissionTree } = useQuery({
    queryKey: ['permission-tree'],
    queryFn: () => api.get('/api/v1/security/permission-tree').then(res => res.data),
  });

  const createPermissionMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/security/permissions', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissions'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('permissions.createSuccess'));
    },
    onError: () => {
      message.error(t('permissions.createError'));
    },
  });

  const createRoleMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/security/roles', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('roles.createSuccess'));
    },
    onError: () => {
      message.error(t('roles.createError'));
    },
  });

  const deletePermissionMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/security/permissions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissions'] });
      message.success(t('permissions.deleteSuccess'));
    },
    onError: () => {
      message.error(t('permissions.deleteError'));
    },
  });

  const deleteRoleMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/security/roles/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      message.success(t('roles.deleteSuccess'));
    },
    onError: () => {
      message.error(t('roles.deleteError'));
    },
  });

  // 权限表格列
  const permissionColumns: ColumnsType<Permission> = [
    {
      title: t('permissions.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('permissions.columns.code'),
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <code>{code}</code>,
    },
    {
      title: t('permissions.columns.resource'),
      dataIndex: 'resource',
      key: 'resource',
    },
    {
      title: t('permissions.columns.action'),
      dataIndex: 'action',
      key: 'action',
    },
    {
      title: t('permissions.columns.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? t('permissions.enabled') : t('permissions.disabled')}
        </Tag>
      ),
    },
    {
      title: t('permissions.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('common:actions'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setModalType('permission');
              setEditingItem(record);
              form.setFieldsValue(record);
              setIsModalVisible(true);
            }}
          >
            {t('common:edit')}
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: t('common:confirmDelete'),
                content: t('permissions.confirmDelete', { name: record.name }),
                onOk: () => deletePermissionMutation.mutate(record.id),
              });
            }}
          >
            {t('common:delete')}
          </Button>
        </Space>
      ),
    },
  ];

  // 角色表格列
  const roleColumns: ColumnsType<Role> = [
    {
      title: t('roles.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('roles.columns.code'),
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <code>{code}</code>,
    },
    {
      title: t('roles.columns.description'),
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: t('roles.columns.permissionCount'),
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: string[]) => permissions.length,
    },
    {
      title: t('roles.columns.userCount'),
      dataIndex: 'userCount',
      key: 'userCount',
    },
    {
      title: t('permissions.columns.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? t('permissions.enabled') : t('permissions.disabled')}
        </Tag>
      ),
    },
    {
      title: t('roles.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('common:actions'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setModalType('role');
              setEditingItem(record);
              form.setFieldsValue(record);
              setIsModalVisible(true);
            }}
          >
            {t('common:edit')}
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: t('common:confirmDelete'),
                content: t('roles.confirmDelete', { name: record.name }),
                onOk: () => deleteRoleMutation.mutate(record.id),
              });
            }}
          >
            {t('common:delete')}
          </Button>
        </Space>
      ),
    },
  ];

  // 用户权限表格列
  const userPermissionColumns: ColumnsType<UserPermission> = [
    {
      title: t('userPermissions.columns.user'),
      dataIndex: 'userName',
      key: 'userName',
      render: (userName: string, record) => (
        <div>
          <div>{userName}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>{record.email}</div>
        </div>
      ),
    },
    {
      title: t('userPermissions.columns.roles'),
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[]) => (
        <Space wrap>
          {roles.map(role => (
            <Tag key={role} color="blue">{role}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('userPermissions.columns.directPermissions'),
      dataIndex: 'directPermissions',
      key: 'directPermissions',
      render: (permissions: string[]) => permissions.length,
    },
    {
      title: t('userPermissions.columns.effectivePermissions'),
      dataIndex: 'effectivePermissions',
      key: 'effectivePermissions',
      render: (permissions: string[]) => permissions.length,
    },
    {
      title: t('userPermissions.columns.lastLogin'),
      dataIndex: 'lastLogin',
      key: 'lastLogin',
      render: (date: string) => date ? new Date(date).toLocaleString() : t('userPermissions.neverLoggedIn'),
    },
    {
      title: t('common:actions'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            onClick={() => {
              // 查看用户权限详情
              console.log('查看用户权限:', record.userId);
            }}
          >
            {t('userPermissions.viewDetail')}
          </Button>
          <Button
            type="link"
            onClick={() => {
              // 编辑用户权限
              console.log('编辑用户权限:', record.userId);
            }}
          >
            {t('userPermissions.editPermissions')}
          </Button>
        </Space>
      ),
    },
  ];

  const handleSubmit = (values: any) => {
    if (modalType === 'permission') {
      if (editingItem) {
        // 更新权限逻辑
        console.log('更新权限:', values);
      } else {
        createPermissionMutation.mutate(values);
      }
    } else {
      if (editingItem) {
        // 更新角色逻辑
        console.log('更新角色:', values);
      } else {
        createRoleMutation.mutate(values);
      }
    }
  };

  return (
    <div className="security-permissions">
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab={t('permissions.title')} key="permissions">
          <Card
            title={t('permissions.title')}
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setModalType('permission');
                  setEditingItem(null);
                  form.resetFields();
                  setIsModalVisible(true);
                }}
              >
                {t('permissions.createPermission')}
              </Button>
            }
          >
            <Table
              columns={permissionColumns}
              dataSource={permissions}
              loading={permissionsLoading}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => t('common.range', { start: range[0], end: range[1], total }),
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab={t('roles.title')} key="roles">
          <Card
            title={t('roles.title')}
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setModalType('role');
                  setEditingItem(null);
                  form.resetFields();
                  setIsModalVisible(true);
                }}
              >
                {t('roles.createRole')}
              </Button>
            }
          >
            <Table
              columns={roleColumns}
              dataSource={roles}
              loading={rolesLoading}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => t('common.range', { start: range[0], end: range[1], total }),
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab={t('userPermissions.title')} key="user-permissions">
          <Card title={t('userPermissions.title')}>
            <Table
              columns={userPermissionColumns}
              dataSource={userPermissions}
              loading={userPermissionsLoading}
              rowKey="userId"
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => t('common.range', { start: range[0], end: range[1], total }),
              }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 创建/编辑模态框 */}
      <Modal
        title={
          modalType === 'permission' 
            ? (editingItem ? t('permissions.editPermission') : t('permissions.createPermission'))
            : (editingItem ? t('roles.editRole') : t('roles.createRole'))
        }
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createPermissionMutation.isPending || createRoleMutation.isPending}
        width={modalType === 'role' ? 800 : 600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          {modalType === 'permission' ? (
            <>
              <Form.Item
                name="name"
                label={t('permissions.columns.name')}
                rules={[{ required: true, message: t('common:pleaseInput', { field: t('permissions.columns.name') }) }]}
              >
                <Input placeholder={t('common:pleaseInput', { field: t('permissions.columns.name') })} />
              </Form.Item>
              <Form.Item
                name="code"
                label={t('permissions.columns.code')}
                rules={[{ required: true, message: t('common:pleaseInput', { field: t('permissions.columns.code') }) }]}
              >
                <Input placeholder="user:create" />
              </Form.Item>
              <Form.Item
                name="resource"
                label={t('permissions.columns.resource')}
                rules={[{ required: true, message: t('common:pleaseInput', { field: t('permissions.columns.resource') }) }]}
              >
                <Input placeholder="user" />
              </Form.Item>
              <Form.Item
                name="action"
                label={t('permissions.columns.action')}
                rules={[{ required: true, message: t('common:pleaseSelect', { field: t('permissions.columns.action') }) }]}
              >
                <Select placeholder={t('common:pleaseSelect', { field: t('permissions.columns.action') })}>
                  <Select.Option value="create">{t('common:create')}</Select.Option>
                  <Select.Option value="read">{t('permissions.read')}</Select.Option>
                  <Select.Option value="update">{t('common:update')}</Select.Option>
                  <Select.Option value="delete">{t('common:delete')}</Select.Option>
                  <Select.Option value="export">{t('permissions.export')}</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item
                name="description"
                label={t('permissions.columns.description')}
              >
                <Input.TextArea rows={3} placeholder={t('common:pleaseInput', { field: t('permissions.columns.description') })} />
              </Form.Item>
              <Form.Item
                name="enabled"
                label={t('permissions.columns.status')}
                valuePropName="checked"
                initialValue={true}
              >
                <Switch checkedChildren={t('permissions.enabled')} unCheckedChildren={t('permissions.disabled')} />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item
                name="name"
                label={t('roles.columns.name')}
                rules={[{ required: true, message: t('common:pleaseInput', { field: t('roles.columns.name') }) }]}
              >
                <Input placeholder={t('roles.form.namePlaceholder')} />
              </Form.Item>
              <Form.Item
                name="code"
                label={t('roles.columns.code')}
                rules={[{ required: true, message: t('common:pleaseInput', { field: t('roles.columns.code') }) }]}
              >
                <Input placeholder="admin" />
              </Form.Item>
              <Form.Item
                name="description"
                label={t('roles.columns.description')}
              >
                <Input.TextArea rows={3} placeholder={t('roles.form.descriptionPlaceholder')} />
              </Form.Item>
              <Form.Item
                name="permissions"
                label={t('rbac.permissionMatrix')}
              >
                <Tree
                  checkable
                  treeData={permissionTree}
                  height={300}
                />
              </Form.Item>
              <Form.Item
                name="enabled"
                label={t('permissions.columns.status')}
                valuePropName="checked"
                initialValue={true}
              >
                <Switch checkedChildren={t('permissions.enabled')} unCheckedChildren={t('permissions.disabled')} />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default SecurityPermissions;