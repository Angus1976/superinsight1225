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
import { 
  memberApi, workspaceApi,
  WorkspaceMember, MemberRole, MemberAddRequest, InvitationConfig, CustomRoleConfig
} from '@/services/multiTenantApi';

const MemberManagement: React.FC = () => {
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
      message.success('邀请已发送');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '邀请发送失败');
    },
  });

  const addMutation = useMutation({
    mutationFn: (data: MemberAddRequest) => memberApi.add(selectedWorkspaceId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] });
      setIsAddModalVisible(false);
      addForm.resetFields();
      message.success('成员添加成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '成员添加失败');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => memberApi.remove(selectedWorkspaceId!, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] });
      message.success('成员已移除');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '移除失败');
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: MemberRole }) => 
      memberApi.updateRole(selectedWorkspaceId!, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] });
      message.success('角色已更新');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '角色更新失败');
    },
  });

  const createRoleMutation = useMutation({
    mutationFn: (data: CustomRoleConfig) => memberApi.createCustomRole(selectedWorkspaceId!, data),
    onSuccess: () => {
      setIsRoleModalVisible(false);
      roleForm.resetFields();
      message.success('自定义角色创建成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '角色创建失败');
    },
  });


  const getRoleTag = (role: MemberRole) => {
    const config: Record<MemberRole, { color: string; icon: React.ReactNode; text: string }> = {
      owner: { color: 'gold', icon: <CrownOutlined />, text: '所有者' },
      admin: { color: 'purple', icon: <SafetyOutlined />, text: '管理员' },
      member: { color: 'blue', icon: <UserOutlined />, text: '成员' },
      guest: { color: 'default', icon: <UserOutlined />, text: '访客' },
    };
    const { color, icon, text } = config[role] || config.member;
    return <Tag icon={icon} color={color}>{text}</Tag>;
  };

  const columns: ColumnsType<WorkspaceMember> = [
    {
      title: '成员',
      key: 'user',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div>用户 ID: {record.user_id.slice(0, 8)}...</div>
            <div style={{ fontSize: 12, color: '#666' }}>
              加入时间: {new Date(record.joined_at).toLocaleDateString()}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: MemberRole) => getRoleTag(role),
      filters: [
        { text: '所有者', value: 'owner' },
        { text: '管理员', value: 'admin' },
        { text: '成员', value: 'member' },
        { text: '访客', value: 'guest' },
      ],
      onFilter: (value, record) => record.role === value,
    },
    {
      title: '最后活跃',
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
      title: '操作',
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
            <Select.Option value="admin">管理员</Select.Option>
            <Select.Option value="member">成员</Select.Option>
            <Select.Option value="guest">访客</Select.Option>
          </Select>
          <Tooltip title={record.role === 'owner' ? '无法移除所有者' : '移除成员'}>
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={record.role === 'owner'}
              onClick={() => {
                Modal.confirm({
                  title: '确认移除',
                  content: '确定要移除该成员吗？移除后将撤销其所有权限。',
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
            <Statistic title="总成员数" value={totalMembers} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="管理员" value={adminCount} prefix={<SafetyOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="普通成员" value={totalMembers - adminCount} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="管理员占比" 
              value={totalMembers ? Math.round((adminCount / totalMembers) * 100) : 0} 
              suffix="%" 
            />
          </Card>
        </Col>
      </Row>

      {/* Member List */}
      <Card
        title="成员管理"
        extra={
          <Space>
            <Select
              placeholder="选择工作空间"
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
              邀请
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!selectedWorkspaceId}
              onClick={() => setIsAddModalVisible(true)}
            >
              添加成员
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
            showTotal: (total) => `共 ${total} 名成员`,
          }}
          locale={{ emptyText: selectedWorkspaceId ? '暂无成员' : '请先选择工作空间' }}
        />
      </Card>

      {/* Invite Modal */}
      <Modal
        title="邀请成员"
        open={isInviteModalVisible}
        onCancel={() => setIsInviteModalVisible(false)}
        onOk={() => inviteForm.submit()}
        confirmLoading={inviteMutation.isPending}
      >
        <Form form={inviteForm} layout="vertical" onFinish={(values) => inviteMutation.mutate(values)}>
          <Form.Item
            name="email"
            label="邮箱地址"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder="user@example.com" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="member">
            <Select>
              <Select.Option value="admin">管理员</Select.Option>
              <Select.Option value="member">成员</Select.Option>
              <Select.Option value="guest">访客</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="message" label="邀请消息">
            <Input.TextArea rows={3} placeholder="可选：添加邀请消息" />
          </Form.Item>
          <Form.Item name="expires_in_days" label="有效期（天）" initialValue={7}>
            <Select>
              <Select.Option value={1}>1 天</Select.Option>
              <Select.Option value={7}>7 天</Select.Option>
              <Select.Option value={30}>30 天</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Add Member Modal */}
      <Modal
        title="添加成员"
        open={isAddModalVisible}
        onCancel={() => setIsAddModalVisible(false)}
        onOk={() => addForm.submit()}
        confirmLoading={addMutation.isPending}
      >
        <Form form={addForm} layout="vertical" onFinish={(values) => addMutation.mutate(values)}>
          <Form.Item
            name="user_id"
            label="用户 ID"
            rules={[{ required: true, message: '请输入用户 ID' }]}
          >
            <Input placeholder="请输入用户 ID" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="member">
            <Select>
              <Select.Option value="admin">管理员</Select.Option>
              <Select.Option value="member">成员</Select.Option>
              <Select.Option value="guest">访客</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Custom Role Modal */}
      <Modal
        title="创建自定义角色"
        open={isRoleModalVisible}
        onCancel={() => setIsRoleModalVisible(false)}
        onOk={() => roleForm.submit()}
        confirmLoading={createRoleMutation.isPending}
      >
        <Form form={roleForm} layout="vertical" onFinish={(values) => createRoleMutation.mutate(values)}>
          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="请输入角色名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色描述" />
          </Form.Item>
          <Form.Item
            name="permissions"
            label="权限"
            rules={[{ required: true, message: '请选择权限' }]}
          >
            <Select mode="multiple" placeholder="选择权限">
              <Select.Option value="read">读取</Select.Option>
              <Select.Option value="write">写入</Select.Option>
              <Select.Option value="delete">删除</Select.Option>
              <Select.Option value="manage_members">管理成员</Select.Option>
              <Select.Option value="manage_settings">管理设置</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MemberManagement;
