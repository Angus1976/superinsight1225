/**
 * User Role Assignment Component
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
  Select,
  DatePicker,
  message,
  Popconfirm,
  Input,
  Avatar,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  UserOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import { rbacApi, Role, UserRoleAssignment as Assignment } from '@/services/rbacApi';
import dayjs from 'dayjs';

const { Text } = Typography;

// Mock users - in production, this would come from a user API
const mockUsers = [
  { id: 'user1', name: 'Admin User', email: 'admin@example.com' },
  { id: 'user2', name: 'John Doe', email: 'john@example.com' },
  { id: 'user3', name: 'Jane Smith', email: 'jane@example.com' },
  { id: 'user4', name: 'Bob Wilson', email: 'bob@example.com' },
];

interface UserWithRoles {
  id: string;
  name: string;
  email: string;
  roles: Assignment[];
}

const UserRoleAssignment: React.FC = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch roles
  const { data: roles = [] } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rbacApi.listRoles(),
  });

  // Fetch user roles for all users
  const { data: userRolesMap = new Map(), isLoading } = useQuery({
    queryKey: ['userRoles'],
    queryFn: async () => {
      const map = new Map<string, Assignment[]>();
      for (const user of mockUsers) {
        try {
          const assignments = await rbacApi.getUserRoles(user.id);
          map.set(user.id, assignments);
        } catch {
          map.set(user.id, []);
        }
      }
      return map;
    },
  });

  // Assign role mutation
  const assignMutation = useMutation({
    mutationFn: ({ userId, roleId, expiresAt }: { userId: string; roleId: string; expiresAt?: string }) =>
      rbacApi.assignRoleToUser(userId, { role_id: roleId, expires_at: expiresAt }),
    onSuccess: () => {
      message.success('Role assigned successfully');
      queryClient.invalidateQueries({ queryKey: ['userRoles'] });
      handleCloseModal();
    },
    onError: () => {
      message.error('Failed to assign role');
    },
  });

  // Revoke role mutation
  const revokeMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      rbacApi.revokeRoleFromUser(userId, roleId),
    onSuccess: () => {
      message.success('Role revoked successfully');
      queryClient.invalidateQueries({ queryKey: ['userRoles'] });
    },
    onError: () => {
      message.error('Failed to revoke role');
    },
  });

  const handleOpenModal = (userId?: string) => {
    setSelectedUser(userId || null);
    form.resetFields();
    if (userId) {
      form.setFieldValue('user_id', userId);
    }
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedUser(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      assignMutation.mutate({
        userId: values.user_id,
        roleId: values.role_id,
        expiresAt: values.expires_at?.toISOString(),
      });
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  // Build user data with roles
  const usersWithRoles: UserWithRoles[] = mockUsers
    .filter(
      (user) =>
        user.name.toLowerCase().includes(searchText.toLowerCase()) ||
        user.email.toLowerCase().includes(searchText.toLowerCase())
    )
    .map((user) => ({
      ...user,
      roles: userRolesMap.get(user.id) || [],
    }));

  const columns: ColumnsType<UserWithRoles> = [
    {
      title: 'User',
      key: 'user',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <Text strong>{record.name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.email}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: 'Assigned Roles',
      key: 'roles',
      render: (_, record) => (
        <Space wrap>
          {record.roles.length === 0 ? (
            <Text type="secondary">No roles assigned</Text>
          ) : (
            record.roles.map((assignment) => (
              <Tag
                key={assignment.id}
                color="blue"
                closable
                onClose={(e) => {
                  e.preventDefault();
                  revokeMutation.mutate({
                    userId: record.id,
                    roleId: assignment.role_id,
                  });
                }}
              >
                {assignment.role_name}
                {assignment.expires_at && (
                  <span style={{ marginLeft: 4, fontSize: 10 }}>
                    (expires: {new Date(assignment.expires_at).toLocaleDateString()})
                  </span>
                )}
              </Tag>
            ))
          )}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<PlusOutlined />}
          onClick={() => handleOpenModal(record.id)}
        >
          Add Role
        </Button>
      ),
    },
  ];

  return (
    <Card
      title="User Role Assignments"
      extra={
        <Space>
          <Input
            placeholder="Search users..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
            Assign Role
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={usersWithRoles}
        rowKey="id"
        loading={isLoading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} users`,
        }}
      />

      <Modal
        title="Assign Role to User"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCloseModal}
        confirmLoading={assignMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="user_id"
            label="User"
            rules={[{ required: true, message: 'Please select a user' }]}
          >
            <Select
              placeholder="Select user"
              disabled={!!selectedUser}
              options={mockUsers.map((u) => ({
                label: `${u.name} (${u.email})`,
                value: u.id,
              }))}
            />
          </Form.Item>

          <Form.Item
            name="role_id"
            label="Role"
            rules={[{ required: true, message: 'Please select a role' }]}
          >
            <Select
              placeholder="Select role"
              options={roles.map((r) => ({
                label: r.name,
                value: r.id,
              }))}
            />
          </Form.Item>

          <Form.Item name="expires_at" label="Expiration (Optional)">
            <DatePicker
              showTime
              style={{ width: '100%' }}
              disabledDate={(current) => current && current < dayjs().startOf('day')}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default UserRoleAssignment;
