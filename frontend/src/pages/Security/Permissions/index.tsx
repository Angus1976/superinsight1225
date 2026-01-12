import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Tree, message, Tabs, Switch } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined, TeamOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { DataNode } from 'antd/es/tree';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
      message.success('权限创建成功');
    },
    onError: () => {
      message.error('权限创建失败');
    },
  });

  const createRoleMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/security/roles', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('角色创建成功');
    },
    onError: () => {
      message.error('角色创建失败');
    },
  });

  const deletePermissionMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/security/permissions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissions'] });
      message.success('权限删除成功');
    },
    onError: () => {
      message.error('权限删除失败');
    },
  });

  const deleteRoleMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/security/roles/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      message.success('角色删除成功');
    },
    onError: () => {
      message.error('角色删除失败');
    },
  });

  // 权限表格列
  const permissionColumns: ColumnsType<Permission> = [
    {
      title: '权限名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '权限代码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <code>{code}</code>,
    },
    {
      title: '资源',
      dataIndex: 'resource',
      key: 'resource',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
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
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: '确认删除',
                content: `确定要删除权限 "${record.name}" 吗？`,
                onOk: () => deletePermissionMutation.mutate(record.id),
              });
            }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 角色表格列
  const roleColumns: ColumnsType<Role> = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '角色代码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <code>{code}</code>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '权限数量',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: string[]) => permissions.length,
    },
    {
      title: '用户数量',
      dataIndex: 'userCount',
      key: 'userCount',
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
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
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: '确认删除',
                content: `确定要删除角色 "${record.name}" 吗？`,
                onOk: () => deleteRoleMutation.mutate(record.id),
              });
            }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 用户权限表格列
  const userPermissionColumns: ColumnsType<UserPermission> = [
    {
      title: '用户',
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
      title: '角色',
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
      title: '直接权限',
      dataIndex: 'directPermissions',
      key: 'directPermissions',
      render: (permissions: string[]) => permissions.length,
    },
    {
      title: '有效权限',
      dataIndex: 'effectivePermissions',
      key: 'effectivePermissions',
      render: (permissions: string[]) => permissions.length,
    },
    {
      title: '最后登录',
      dataIndex: 'lastLogin',
      key: 'lastLogin',
      render: (date: string) => date ? new Date(date).toLocaleString() : '从未登录',
    },
    {
      title: '操作',
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
            查看详情
          </Button>
          <Button
            type="link"
            onClick={() => {
              // 编辑用户权限
              console.log('编辑用户权限:', record.userId);
            }}
          >
            编辑权限
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
        <TabPane tab="权限管理" key="permissions">
          <Card
            title="权限管理"
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
                新建权限
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
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab="角色管理" key="roles">
          <Card
            title="角色管理"
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
                新建角色
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
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab="用户权限" key="user-permissions">
          <Card title="用户权限管理">
            <Table
              columns={userPermissionColumns}
              dataSource={userPermissions}
              loading={userPermissionsLoading}
              rowKey="userId"
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 创建/编辑模态框 */}
      <Modal
        title={
          modalType === 'permission' 
            ? (editingItem ? '编辑权限' : '新建权限')
            : (editingItem ? '编辑角色' : '新建角色')
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
                label="权限名称"
                rules={[{ required: true, message: '请输入权限名称' }]}
              >
                <Input placeholder="请输入权限名称" />
              </Form.Item>
              <Form.Item
                name="code"
                label="权限代码"
                rules={[{ required: true, message: '请输入权限代码' }]}
              >
                <Input placeholder="例如: user:create" />
              </Form.Item>
              <Form.Item
                name="resource"
                label="资源"
                rules={[{ required: true, message: '请输入资源' }]}
              >
                <Input placeholder="例如: user" />
              </Form.Item>
              <Form.Item
                name="action"
                label="操作"
                rules={[{ required: true, message: '请输入操作' }]}
              >
                <Select placeholder="请选择操作">
                  <Select.Option value="create">创建</Select.Option>
                  <Select.Option value="read">读取</Select.Option>
                  <Select.Option value="update">更新</Select.Option>
                  <Select.Option value="delete">删除</Select.Option>
                  <Select.Option value="export">导出</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item
                name="description"
                label="描述"
              >
                <Input.TextArea rows={3} placeholder="请输入权限描述" />
              </Form.Item>
              <Form.Item
                name="enabled"
                label="启用状态"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item
                name="name"
                label="角色名称"
                rules={[{ required: true, message: '请输入角色名称' }]}
              >
                <Input placeholder="请输入角色名称" />
              </Form.Item>
              <Form.Item
                name="code"
                label="角色代码"
                rules={[{ required: true, message: '请输入角色代码' }]}
              >
                <Input placeholder="例如: admin" />
              </Form.Item>
              <Form.Item
                name="description"
                label="描述"
              >
                <Input.TextArea rows={3} placeholder="请输入角色描述" />
              </Form.Item>
              <Form.Item
                name="permissions"
                label="权限配置"
              >
                <Tree
                  checkable
                  treeData={permissionTree}
                  height={300}
                />
              </Form.Item>
              <Form.Item
                name="enabled"
                label="启用状态"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default SecurityPermissions;