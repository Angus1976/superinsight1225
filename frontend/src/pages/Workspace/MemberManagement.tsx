/**
 * Member Management Page
 * 
 * Provides workspace member management including:
 * - Member list
 * - Invite members
 * - Add/Remove members
 * - Role configuration
 * - Custom roles
 */

import React, { useState } from 'react';
import { 
  Card, Table, Button, Space, Tag, Modal, Form, Input, Select, 
  message, Avatar, Tooltip, Row, Col, Statistic, Tabs
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  PlusOutlined, DeleteOutlined, UserOutlined, MailOutlined,
  ReloadOutlined, TeamOutlined, CrownOutlined, SafetyOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { 
  memberApi, workspaceApi,
  WorkspaceMember, MemberRole, MemberAddRequest, InvitationConfig, CustomRoleConfig
} from '@/services/multiTenantApi';

const MemberManagement: React.FC = () => {
  const { t } = useTranslation(['workspace', 'common']);
  const [isInviteModalVisible, setIsInviteModalVisible] = useState(false);
  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [isRoleModalVisible, setIsRoleModalVisible] = useState(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | undefined>();
  const [selectedMember, setSelectedMember] = useState<WorkspaceMember | null>(null);
  const [inviteForm] = Form.useForm();
  const [addForm] = Form.useForm();
  const [roleForm] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch workspaces for selector
  const { data: workspaces } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => workspaceApi.list({ status: 'active' }).then(res => res.data),
  });

  // Fetch members
  const { data: members, isLoading, refetch } = useQuery({
    queryKey: ['workspace-members', selectedWorkspaceId],
    queryFn: () => memberApi.list(selectedWorkspaceId!).then(res => res.data),
    enabled: !!selectedWorkspaceId,
  });

  // Mutations
  const inviteMutation = useMutation({
    mutationFn: (data: InvitationConfig) => memberApi.invite(selectedWorkspaceId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] });
      setIsInviteModalVisible(false);
      inviteForm.resetFields();
      message.success(t('member.inviteSent'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('member.inviteError'));
    },
  });

  const addMutation = useMutation({
    mutationFn: (data: MemberAddRequest) => memberApi.add(selectedWorkspaceId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] });
      setIsAddModalVisible(false);
      addForm.resetFields();
      message.success(t('member.addSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('member.addError'));
    },
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => memberApi.remove(selectedWorkspaceId!, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] });
      message.success(t('member.removeSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('member.removeError'));
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: MemberRole }) => 
      memberApi.updateRole(selectedWorkspaceId!, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] });
      message.success(t('member.roleUpdated'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('member.roleUpdateError'));
    },
  });

  const createRoleMutation = useMutation({
    mutationFn: (data: CustomRoleConfig) => memberApi.createCustomRole(selectedWorkspaceId!, data),
    onSuccess: () => {
      setIsRoleModalVisible(false);
      roleForm.resetFields();
      message.success(t('member.customRoleCreated'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('member.customRoleError'));
    },
  });


  const getRoleTag = (role: MemberRole) => {
    const config: Record<MemberRole, { color: string; icon: React.ReactNode; textKey: string }> = {
      owner: { color: 'gold', icon: <CrownOutlined />, textKey: 'member.roles.owner' },
      admin: { color: 'purple', icon: <SafetyOutlined />, textKey: 'member.roles.admin' },
      member: { color: 'blue', icon: <UserOutlined />, textKey: 'member.roles.member' },
      guest: { color: 'default', icon: <UserOutlined />, textKey: 'member.roles.guest' },
    };
    const { color, icon, textKey } = config[role] || config.member;
    return <Tag icon={icon} color={color}>{t(textKey)}</Tag>;
  };

  const columns: ColumnsType<WorkspaceMember> = [
    {
      title: t('member.columns.member'),
      key: 'user',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div>{t('member.columns.userId')}: {record.user_id.slice(0, 8)}...</div>
            <div style={{ fontSize: 12, color: '#666' }}>
              {t('member.columns.joinedAt')}: {new Date(record.joined_at).toLocaleDateString()}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: t('member.columns.role'),
      dataIndex: 'role',
      key: 'role',
      render: (role: MemberRole) => getRoleTag(role),
      filters: [
        { text: t('member.roles.owner'), value: 'owner' },
        { text: t('member.roles.admin'), value: 'admin' },
        { text: t('member.roles.member'), value: 'member' },
        { text: t('member.roles.guest'), value: 'guest' },
      ],
      onFilter: (value, record) => record.role === value,
    },
    {
      title: t('member.columns.lastActive'),
      dataIndex: 'last_active_at',
      key: 'last_active_at',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
      sorter: (a, b) => {
        if (!a.last_active_at) return 1;
        if (!b.last_active_at) return -1;
        return new Date(a.last_active_at).getTime() - new Date(b.last_active_at).getTime();
      },
    },
    {
      title: t('member.columns.action'),
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Select
            value={record.role}
            style={{ width: 100 }}
            size="small"
            disabled={record.role === 'owner'}
            onChange={(role) => updateRoleMutation.mutate({ userId: record.user_id, role })}
          >
            <Select.Option value="admin">{t('member.roles.admin')}</Select.Option>
            <Select.Option value="member">{t('member.roles.member')}</Select.Option>
            <Select.Option value="guest">{t('member.roles.guest')}</Select.Option>
          </Select>
          <Tooltip title={record.role === 'owner' ? t('member.cannotRemoveOwner') : t('member.removeMember')}>
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={record.role === 'owner'}
              onClick={() => {
                Modal.confirm({
                  title: t('member.confirmRemove'),
                  content: t('member.confirmRemoveContent'),
                  onOk: () => removeMutation.mutate(record.user_id),
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Statistics
  const totalMembers = members?.length || 0;
  const adminCount = members?.filter(m => m.role === 'admin' || m.role === 'owner').length || 0;

  return (
    <div className="member-management">
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('member.totalMembers')} value={totalMembers} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('member.admins')} value={adminCount} prefix={<SafetyOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('member.regularMembers')} value={totalMembers - adminCount} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title={t('member.adminRatio')} 
              value={totalMembers ? Math.round((adminCount / totalMembers) * 100) : 0} 
              suffix="%" 
            />
          </Card>
        </Col>
      </Row>

      {/* Member List */}
      <Card
        title={t('member.title')}
        extra={
          <Space>
            <Select
              placeholder={t('member.selectWorkspace')}
              style={{ width: 200 }}
              onChange={setSelectedWorkspaceId}
              value={selectedWorkspaceId}
            >
              {workspaces?.map(w => (
                <Select.Option key={w.id} value={w.id}>{w.name}</Select.Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()} disabled={!selectedWorkspaceId} />
            <Button
              icon={<MailOutlined />}
              disabled={!selectedWorkspaceId}
              onClick={() => setIsInviteModalVisible(true)}
            >
              {t('member.invite')}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!selectedWorkspaceId}
              onClick={() => setIsAddModalVisible(true)}
            >
              {t('member.addMember')}
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={members}
          loading={isLoading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => t('member.totalMembersCount', { total }),
          }}
          locale={{ emptyText: selectedWorkspaceId ? t('member.noMembers') : t('member.selectWorkspaceFirst') }}
        />
      </Card>

      {/* Invite Modal */}
      <Modal
        title={t('member.inviteMember')}
        open={isInviteModalVisible}
        onCancel={() => setIsInviteModalVisible(false)}
        onOk={() => inviteForm.submit()}
        confirmLoading={inviteMutation.isPending}
      >
        <Form form={inviteForm} layout="vertical" onFinish={(values) => inviteMutation.mutate(values)}>
          <Form.Item
            name="email"
            label={t('member.inviteForm.email')}
            rules={[
              { required: true, message: t('member.inviteForm.emailRequired') },
              { type: 'email', message: t('member.inviteForm.emailInvalid') },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder={t('member.inviteForm.emailPlaceholder')} />
          </Form.Item>
          <Form.Item name="role" label={t('member.inviteForm.role')} initialValue="member">
            <Select>
              <Select.Option value="admin">{t('member.roles.admin')}</Select.Option>
              <Select.Option value="member">{t('member.roles.member')}</Select.Option>
              <Select.Option value="guest">{t('member.roles.guest')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="message" label={t('member.inviteForm.message')}>
            <Input.TextArea rows={3} placeholder={t('member.inviteForm.messagePlaceholder')} />
          </Form.Item>
          <Form.Item name="expires_in_days" label={t('member.inviteForm.expiresIn')} initialValue={7}>
            <Select>
              <Select.Option value={1}>{t('member.inviteForm.expires1Day')}</Select.Option>
              <Select.Option value={7}>{t('member.inviteForm.expires7Days')}</Select.Option>
              <Select.Option value={30}>{t('member.inviteForm.expires30Days')}</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Add Member Modal */}
      <Modal
        title={t('member.addMember')}
        open={isAddModalVisible}
        onCancel={() => setIsAddModalVisible(false)}
        onOk={() => addForm.submit()}
        confirmLoading={addMutation.isPending}
      >
        <Form form={addForm} layout="vertical" onFinish={(values) => addMutation.mutate(values)}>
          <Form.Item
            name="user_id"
            label={t('member.addForm.userId')}
            rules={[{ required: true, message: t('member.addForm.userIdRequired') }]}
          >
            <Input placeholder={t('member.addForm.userIdPlaceholder')} />
          </Form.Item>
          <Form.Item name="role" label={t('member.addForm.role')} initialValue="member">
            <Select>
              <Select.Option value="admin">{t('member.roles.admin')}</Select.Option>
              <Select.Option value="member">{t('member.roles.member')}</Select.Option>
              <Select.Option value="guest">{t('member.roles.guest')}</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Custom Role Modal */}
      <Modal
        title={t('member.customRole.title')}
        open={isRoleModalVisible}
        onCancel={() => setIsRoleModalVisible(false)}
        onOk={() => roleForm.submit()}
        confirmLoading={createRoleMutation.isPending}
      >
        <Form form={roleForm} layout="vertical" onFinish={(values) => createRoleMutation.mutate(values)}>
          <Form.Item
            name="name"
            label={t('member.customRole.name')}
            rules={[{ required: true, message: t('member.customRole.nameRequired') }]}
          >
            <Input placeholder={t('member.customRole.namePlaceholder')} />
          </Form.Item>
          <Form.Item name="description" label={t('member.customRole.description')}>
            <Input.TextArea rows={2} placeholder={t('member.customRole.descriptionPlaceholder')} />
          </Form.Item>
          <Form.Item
            name="permissions"
            label={t('member.customRole.permissions')}
            rules={[{ required: true, message: t('member.customRole.permissionsRequired') }]}
          >
            <Select mode="multiple" placeholder={t('member.customRole.permissionsPlaceholder')}>
              <Select.Option value="read">{t('member.customRole.permissionRead')}</Select.Option>
              <Select.Option value="write">{t('member.customRole.permissionWrite')}</Select.Option>
              <Select.Option value="delete">{t('member.customRole.permissionDelete')}</Select.Option>
              <Select.Option value="manage_members">{t('member.customRole.permissionManageMembers')}</Select.Option>
              <Select.Option value="manage_settings">{t('member.customRole.permissionManageSettings')}</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MemberManagement;
