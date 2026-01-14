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
import type { ColumnsType } from 'antd/es/table';
import { rbacApi, Role, Permission, CreateRoleRequest } from '@/services/rbacApi';

const { Text } = Typography;
const { TextArea } = Input;

const RoleList: React.FC = () => {
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
      message.success('Role created successfully');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      handleCloseModal();
    },
    onError: () => {
      message.error('Failed to create role');
    },
  });

  // Update role mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CreateRoleRequest }) =>
      rbacApi.updateRole(id, data),
    onSuccess: () => {
      message.success('Role updated successfully');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      handleCloseModal();
    },
    onError: () => {
      message.error('Failed to update role');
    },
  });

  // Delete role mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => rbacApi.deleteRole(id),
    onSuccess: () => {
      message.success('Role deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
    onError: () => {
      message.error('Failed to delete role');
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
      title: 'Role Name',
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
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Permissions',
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
      title: 'Parent Role',
      dataIndex: 'parent_role_id',
      key: 'parent_role_id',
      render: (parentId) => {
        if (!parentId) return '-';
        const parent = roles.find((r) => r.id === parentId);
        return parent ? <Tag>{parent.name}</Tag> : parentId;
      },
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
            title="Delete this role?"
            description="This will also remove all user assignments."
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Delete"
            cancelText="Cancel"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Common permission options
  const permissionOptions = [
    { label: 'Projects: Read', value: 'projects:read' },
    { label: 'Projects: Write', value: 'projects:write' },
    { label: 'Projects: Delete', value: 'projects:delete' },
    { label: 'Tasks: Read', value: 'tasks:read' },
    { label: 'Tasks: Write', value: 'tasks:write' },
    { label: 'Tasks: Delete', value: 'tasks:delete' },
    { label: 'Annotations: Read', value: 'annotations:read' },
    { label: 'Annotations: Write', value: 'annotations:write' },
    { label: 'Users: Read', value: 'users:read' },
    { label: 'Users: Write', value: 'users:write' },
    { label: 'Admin: All', value: 'admin:*' },
    { label: 'All Resources: Read', value: '*:read' },
    { label: 'All Resources: All', value: '*:*' },
  ];

  return (
    <Card
      title="Role Management"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          Create Role
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
          showTotal: (total) => `Total ${total} roles`,
        }}
      />

      <Modal
        title={editingRole ? 'Edit Role' : 'Create Role'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCloseModal}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Role Name"
            rules={[{ required: true, message: 'Please enter role name' }]}
          >
            <Input placeholder="e.g., project_manager" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="Role description" />
          </Form.Item>

          <Form.Item name="permissions" label="Permissions">
            <Select
              mode="multiple"
              placeholder="Select permissions"
              options={permissionOptions}
              allowClear
            />
          </Form.Item>

          <Form.Item name="parent_role_id" label="Parent Role (Inheritance)">
            <Select
              placeholder="Select parent role"
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
