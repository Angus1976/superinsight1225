/**
 * Role List Component for RBAC Management
 */

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
  message,
  Popconfirm,
  Tooltip,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  KeyOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { rbacApi, Role, Permission, CreateRoleRequest } from '@/services/rbacApi';

const { Text } = Typography;
const { TextArea } = Input;

const RoleList: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch roles
  const { data: roles = [], isLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rbacApi.listRoles(),
  });

  // Create role mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateRoleRequest) => rbacApi.createRole(data),
    onSuccess: () => {
      message.success(t('roles.createSuccess'));
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      handleCloseModal();
    },
    onError: () => {
      message.error(t('roles.createError'));
    },
  });

  // Update role mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CreateRoleRequest }) =>
      rbacApi.updateRole(id, data),
    onSuccess: () => {
      message.success(t('roles.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      handleCloseModal();
    },
    onError: () => {
      message.error(t('roles.updateError'));
    },
  });

  // Delete role mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => rbacApi.deleteRole(id),
    onSuccess: () => {
      message.success(t('roles.deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
    onError: () => {
      message.error(t('roles.deleteError'));
    },
  });

  const handleOpenModal = (role?: Role) => {
    if (role) {
      setEditingRole(role);
      form.setFieldsValue({
        name: role.name,
        description: role.description,
        permissions: role.permissions.map((p) => `${p.resource}:${p.action}`),
        parent_role_id: role.parent_role_id,
      });
    } else {
      setEditingRole(null);
      form.resetFields();
    }
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setEditingRole(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const permissions: Permission[] = (values.permissions || []).map(
        (p: string) => {
          const [resource, action] = p.split(':');
          return { resource, action };
        }
      );

      const data: CreateRoleRequest = {
        name: values.name,
        description: values.description,
        permissions,
        parent_role_id: values.parent_role_id,
      };

      if (editingRole) {
        updateMutation.mutate({ id: editingRole.id, data });
      } else {
        createMutation.mutate(data);
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const columns: ColumnsType<Role> = [
    {
      title: t('roles.columns.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name) => (
        <Space>
          <TeamOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: t('roles.columns.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('roles.columns.permissionCount'),
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: Permission[]) => (
        <Space wrap>
          {permissions.slice(0, 3).map((p, i) => (
            <Tag key={i} icon={<KeyOutlined />} color="blue">
              {p.resource}:{p.action}
            </Tag>
          ))}
          {permissions.length > 3 && (
            <Tooltip
              title={permissions
                .slice(3)
                .map((p) => `${p.resource}:${p.action}`)
                .join(', ')}
            >
              <Tag>+{permissions.length - 3} more</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: t('roles.columns.parentRole'),
      dataIndex: 'parent_role_id',
      key: 'parent_role_id',
      render: (parentId) => {
        if (!parentId) return '-';
        const parent = roles.find((r) => r.id === parentId);
        return parent ? <Tag>{parent.name}</Tag> : parentId;
      },
    },
    {
      title: t('roles.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          />
          <Popconfirm
            title={t('roles.confirmDelete', { name: record.name })}
            description={t('roles.deleteWarning')}
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText={t('common:delete')}
            cancelText={t('common:cancel')}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Common permission options
  const permissionOptions = [
    { label: `${t('rbac.resources.projects')}: ${t('rbac.actions.read')}`, value: 'projects:read' },
    { label: `${t('rbac.resources.projects')}: ${t('rbac.actions.write')}`, value: 'projects:write' },
    { label: `${t('rbac.resources.projects')}: ${t('rbac.actions.delete')}`, value: 'projects:delete' },
    { label: `${t('rbac.resources.tasks')}: ${t('rbac.actions.read')}`, value: 'tasks:read' },
    { label: `${t('rbac.resources.tasks')}: ${t('rbac.actions.write')}`, value: 'tasks:write' },
    { label: `${t('rbac.resources.tasks')}: ${t('rbac.actions.delete')}`, value: 'tasks:delete' },
    { label: `${t('rbac.resources.annotations')}: ${t('rbac.actions.read')}`, value: 'annotations:read' },
    { label: `${t('rbac.resources.annotations')}: ${t('rbac.actions.write')}`, value: 'annotations:write' },
    { label: `${t('rbac.resources.users')}: ${t('rbac.actions.read')}`, value: 'users:read' },
    { label: `${t('rbac.resources.users')}: ${t('rbac.actions.write')}`, value: 'users:write' },
    { label: `${t('rbac.resources.admin')}: ${t('rbac.actions.all')}`, value: 'admin:*' },
    { label: `All Resources: ${t('rbac.actions.read')}`, value: '*:read' },
    { label: `All Resources: ${t('rbac.actions.all')}`, value: '*:*' },
  ];

  return (
    <Card
      title={t('rbac.roleManagement')}
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          {t('rbac.createRole')}
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={roles}
        rowKey="id"
        loading={isLoading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => t('common.totalRoles', { total }),
        }}
      />

      <Modal
        title={editingRole ? t('roles.editRole') : t('roles.createRole')}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCloseModal}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('roles.columns.name')}
            rules={[{ required: true, message: t('common:pleaseInput', { field: t('roles.columns.name') }) }]}
          >
            <Input placeholder={t('roles.form.namePlaceholder')} />
          </Form.Item>

          <Form.Item name="description" label={t('roles.columns.description')}>
            <TextArea rows={2} placeholder={t('roles.form.descriptionPlaceholder')} />
          </Form.Item>

          <Form.Item name="permissions" label={t('rbac.permissionMatrix')}>
            <Select
              mode="multiple"
              placeholder={t('roles.form.selectPermissions')}
              options={permissionOptions}
              allowClear
            />
          </Form.Item>

          <Form.Item name="parent_role_id" label={t('roles.columns.parentRole')}>
            <Select
              placeholder={t('roles.form.selectParentRole')}
              allowClear
              options={roles
                .filter((r) => r.id !== editingRole?.id)
                .map((r) => ({ label: r.name, value: r.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default RoleList;
