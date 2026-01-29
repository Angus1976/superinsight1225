/**
 * Label Studio Workspace Member Management Component
 *
 * Manages workspace members including:
 * - Member list
 * - Add/Remove members
 * - Role management
 * - Permission display
 */

import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Avatar,
  Tooltip,
  Empty,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined,
  DeleteOutlined,
  UserOutlined,
  CrownOutlined,
  SafetyOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  useLSWorkspaceMembers,
  useAddLSWorkspaceMember,
  useUpdateLSWorkspaceMember,
  useRemoveLSWorkspaceMember,
  useLSWorkspacePermissions,
} from '@/hooks/useLSWorkspaces';
import type {
  LSWorkspaceMember,
  WorkspaceMemberRole,
  AddLSWorkspaceMemberRequest,
} from '@/types/ls-workspace';
import { canManageRole, isHigherRole, ROLE_HIERARCHY } from '@/types/ls-workspace';

const { Text } = Typography;

interface Props {
  workspaceId: string;
}

const LSWorkspaceMemberManagement: React.FC<Props> = ({ workspaceId }) => {
  const { t } = useTranslation(['lsWorkspace', 'common']);
  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [editingMember, setEditingMember] = useState<LSWorkspaceMember | null>(null);
  const [form] = Form.useForm();

  // Fetch members and current user's permissions
  const { data: membersData, isLoading } = useLSWorkspaceMembers(workspaceId);
  const { data: myPermissions } = useLSWorkspacePermissions(workspaceId);

  // Mutations
  const addMutation = useAddLSWorkspaceMember();
  const updateMutation = useUpdateLSWorkspaceMember();
  const removeMutation = useRemoveLSWorkspaceMember();

  const members = membersData?.items ?? [];
  const myRole = myPermissions?.role ?? 'annotator';
  const canManageMembers = myPermissions?.permissions.includes('workspace:manage_members') ?? false;

  const getRoleConfig = (role: WorkspaceMemberRole) => {
    const config: Record<
      WorkspaceMemberRole,
      { color: string; icon: React.ReactNode; labelKey: string }
    > = {
      owner: { color: 'gold', icon: <CrownOutlined />, labelKey: 'roles.owner' },
      admin: { color: 'purple', icon: <SafetyOutlined />, labelKey: 'roles.admin' },
      manager: { color: 'blue', icon: <UserOutlined />, labelKey: 'roles.manager' },
      reviewer: { color: 'cyan', icon: <UserOutlined />, labelKey: 'roles.reviewer' },
      annotator: { color: 'default', icon: <UserOutlined />, labelKey: 'roles.annotator' },
    };
    return config[role] || config.annotator;
  };

  const getRoleTag = (role: WorkspaceMemberRole) => {
    const { color, icon, labelKey } = getRoleConfig(role);
    return (
      <Tag icon={icon} color={color}>
        {t(labelKey, { defaultValue: role })}
      </Tag>
    );
  };

  const handleAddMember = () => {
    setEditingMember(null);
    form.resetFields();
    form.setFieldsValue({ role: 'annotator' });
    setIsAddModalVisible(true);
  };

  const handleEditRole = (member: LSWorkspaceMember) => {
    setEditingMember(member);
    form.setFieldsValue({ role: member.role });
    setIsAddModalVisible(true);
  };

  const handleRemoveMember = (member: LSWorkspaceMember) => {
    Modal.confirm({
      title: t('member.confirmRemove', { defaultValue: 'Remove Member' }),
      icon: <ExclamationCircleOutlined />,
      content: t('member.confirmRemoveContent', {
        name: member.user_name || member.user_id,
        defaultValue: `Are you sure you want to remove "${member.user_name || member.user_id}" from this workspace?`,
      }),
      okText: t('common:remove', { defaultValue: 'Remove' }),
      okType: 'danger',
      cancelText: t('common:cancel', { defaultValue: 'Cancel' }),
      onOk: async () => {
        try {
          await removeMutation.mutateAsync({
            workspaceId,
            userId: member.user_id,
          });
        } catch (error) {
          // Error handled by hook
        }
      },
    });
  };

  const handleSubmit = async (values: { user_id?: string; role: WorkspaceMemberRole }) => {
    try {
      if (editingMember) {
        // Update role
        await updateMutation.mutateAsync({
          workspaceId,
          userId: editingMember.user_id,
          request: { role: values.role },
        });
      } else {
        // Add member
        if (!values.user_id) {
          message.error(t('member.userIdRequired', { defaultValue: 'User ID is required' }));
          return;
        }
        await addMutation.mutateAsync({
          workspaceId,
          request: {
            user_id: values.user_id,
            role: values.role,
          },
        });
      }
      setIsAddModalVisible(false);
      form.resetFields();
      setEditingMember(null);
    } catch (error) {
      // Error handled by hook
    }
  };

  const getAvailableRoles = (): WorkspaceMemberRole[] => {
    // Filter roles that the current user can assign
    return ROLE_HIERARCHY.filter((role) => {
      if (myRole === 'owner') return role !== 'owner'; // Owner can assign any role except owner
      if (myRole === 'admin') return role !== 'owner' && role !== 'admin';
      return false;
    });
  };

  const columns: ColumnsType<LSWorkspaceMember> = [
    {
      title: t('member.columns.member', { defaultValue: 'Member' }),
      key: 'user',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div style={{ fontWeight: 500 }}>
              {record.user_name || t('member.unknownUser', { defaultValue: 'Unknown User' })}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.user_email || record.user_id.slice(0, 12) + '...'}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: t('member.columns.role', { defaultValue: 'Role' }),
      dataIndex: 'role',
      key: 'role',
      width: 120,
      render: (role: WorkspaceMemberRole) => getRoleTag(role),
      filters: ROLE_HIERARCHY.map((role) => ({
        text: t(`roles.${role}`, { defaultValue: role }),
        value: role,
      })),
      onFilter: (value, record) => record.role === value,
    },
    {
      title: t('member.columns.joinedAt', { defaultValue: 'Joined' }),
      dataIndex: 'joined_at',
      key: 'joined_at',
      width: 120,
      render: (date: string) => (date ? new Date(date).toLocaleDateString() : '-'),
    },
    {
      title: t('member.columns.status', { defaultValue: 'Status' }),
      dataIndex: 'is_active',
      key: 'status',
      width: 80,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'default'}>
          {isActive
            ? t('status.active', { defaultValue: 'Active' })
            : t('status.inactive', { defaultValue: 'Inactive' })}
        </Tag>
      ),
    },
    {
      title: t('member.columns.actions', { defaultValue: 'Actions' }),
      key: 'actions',
      width: 120,
      render: (_, record) => {
        const canEdit = canManageMembers && canManageRole(myRole, record.role);
        const canRemove = canManageMembers && record.role !== 'owner' && canManageRole(myRole, record.role);

        return (
          <Space size="small">
            <Tooltip
              title={
                !canEdit
                  ? t('member.cannotEditRole', { defaultValue: 'Cannot edit this role' })
                  : t('member.editRole', { defaultValue: 'Edit Role' })
              }
            >
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                disabled={!canEdit}
                onClick={() => handleEditRole(record)}
              />
            </Tooltip>
            <Tooltip
              title={
                !canRemove
                  ? record.role === 'owner'
                    ? t('member.cannotRemoveOwner', { defaultValue: 'Cannot remove owner' })
                    : t('member.cannotRemove', { defaultValue: 'Cannot remove this member' })
                  : t('member.remove', { defaultValue: 'Remove' })
              }
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={!canRemove}
                onClick={() => handleRemoveMember(record)}
              />
            </Tooltip>
          </Space>
        );
      },
    },
  ];

  return (
    <div className="ls-workspace-member-management">
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleAddMember}
          disabled={!canManageMembers}
        >
          {t('member.addMember', { defaultValue: 'Add Member' })}
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={members}
        loading={isLoading}
        rowKey="id"
        size="small"
        pagination={{
          pageSize: 5,
          showSizeChanger: false,
          showTotal: (total) =>
            t('member.totalMembers', {
              total,
              defaultValue: `${total} members`,
            }),
        }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t('member.noMembers', { defaultValue: 'No members in this workspace' })}
            />
          ),
        }}
      />

      {/* Add/Edit Member Modal */}
      <Modal
        title={
          editingMember
            ? t('member.editRole', { defaultValue: 'Edit Role' })
            : t('member.addMember', { defaultValue: 'Add Member' })
        }
        open={isAddModalVisible}
        onCancel={() => {
          setIsAddModalVisible(false);
          form.resetFields();
          setEditingMember(null);
        }}
        onOk={() => form.submit()}
        confirmLoading={addMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          {!editingMember && (
            <Form.Item
              name="user_id"
              label={t('member.form.userId', { defaultValue: 'User ID' })}
              rules={[
                {
                  required: true,
                  message: t('member.form.userIdRequired', { defaultValue: 'Please enter user ID' }),
                },
              ]}
            >
              <Input
                placeholder={t('member.form.userIdPlaceholder', { defaultValue: 'Enter user ID or email' })}
              />
            </Form.Item>
          )}

          {editingMember && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">
                {t('member.editingMember', { defaultValue: 'Editing role for:' })}
              </Text>
              <div style={{ fontWeight: 500 }}>
                {editingMember.user_name || editingMember.user_email || editingMember.user_id}
              </div>
            </div>
          )}

          <Form.Item
            name="role"
            label={t('member.form.role', { defaultValue: 'Role' })}
            rules={[
              {
                required: true,
                message: t('member.form.roleRequired', { defaultValue: 'Please select a role' }),
              },
            ]}
          >
            <Select placeholder={t('member.form.selectRole', { defaultValue: 'Select role' })}>
              {getAvailableRoles().map((role) => {
                const { color, labelKey } = getRoleConfig(role);
                return (
                  <Select.Option key={role} value={role}>
                    <Tag color={color}>{t(labelKey, { defaultValue: role })}</Tag>
                  </Select.Option>
                );
              })}
            </Select>
          </Form.Item>

          {/* Role description */}
          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.role !== curr.role}>
            {({ getFieldValue }) => {
              const role = getFieldValue('role') as WorkspaceMemberRole;
              const descriptions: Record<WorkspaceMemberRole, string> = {
                owner: t('roleDesc.owner', { defaultValue: 'Full control over workspace' }),
                admin: t('roleDesc.admin', { defaultValue: 'Manage workspace settings and members' }),
                manager: t('roleDesc.manager', { defaultValue: 'Manage projects and assign tasks' }),
                reviewer: t('roleDesc.reviewer', { defaultValue: 'Review and approve annotations' }),
                annotator: t('roleDesc.annotator', { defaultValue: 'Create and edit annotations' }),
              };
              return role ? (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {descriptions[role]}
                </Text>
              ) : null;
            }}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default LSWorkspaceMemberManagement;
