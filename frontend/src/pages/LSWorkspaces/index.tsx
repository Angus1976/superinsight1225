/**
 * Label Studio Workspace Management Page
 *
 * Provides workspace management for Label Studio Enterprise including:
 * - Workspace list view
 * - Create/Edit/Delete workspaces
 * - Member management
 * - Project association overview
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  message,
  Row,
  Col,
  Statistic,
  Tooltip,
  Dropdown,
  Empty,
  Typography,
  Badge,
  Tabs,
  Avatar,
  Switch,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  TeamOutlined,
  FolderOutlined,
  ReloadOutlined,
  MoreOutlined,
  CrownOutlined,
  SettingOutlined,
  EyeOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  useLSWorkspaces,
  useCreateLSWorkspace,
  useUpdateLSWorkspace,
  useDeleteLSWorkspace,
} from '@/hooks/useLSWorkspaces';
import type {
  LSWorkspace,
  CreateLSWorkspaceRequest,
  UpdateLSWorkspaceRequest,
} from '@/types/ls-workspace';
import LSWorkspaceMemberManagement from './MemberManagement';
import LSWorkspaceProjectList from './ProjectList';

const { Title, Text } = Typography;
const { TextArea } = Input;

const LSWorkspacesPage: React.FC = () => {
  const { t } = useTranslation(['lsWorkspace', 'common']);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState<LSWorkspace | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<LSWorkspace | null>(null);
  const [detailTab, setDetailTab] = useState<'members' | 'projects'>('members');
  const [includeInactive, setIncludeInactive] = useState(false);
  const [form] = Form.useForm();

  // Fetch workspaces
  const { data: workspacesData, isLoading, refetch } = useLSWorkspaces(includeInactive);

  // Mutations
  const createMutation = useCreateLSWorkspace();
  const updateMutation = useUpdateLSWorkspace();
  const deleteMutation = useDeleteLSWorkspace();

  const workspaces = useMemo(() => workspacesData?.items ?? [], [workspacesData]);

  // Statistics
  const totalWorkspaces = workspacesData?.total ?? 0;
  const activeWorkspaces = workspaces.filter((w) => w.is_active).length;
  const totalMembers = workspaces.reduce((sum, w) => sum + w.member_count, 0);
  const totalProjects = workspaces.reduce((sum, w) => sum + w.project_count, 0);

  const handleCreate = () => {
    setEditingWorkspace(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleEdit = (workspace: LSWorkspace) => {
    setEditingWorkspace(workspace);
    form.setFieldsValue({
      name: workspace.name,
      description: workspace.description,
    });
    setIsModalVisible(true);
  };

  const handleDelete = (workspace: LSWorkspace) => {
    Modal.confirm({
      title: t('confirmDelete', { defaultValue: 'Delete Workspace' }),
      content: t('confirmDeleteContent', {
        name: workspace.name,
        defaultValue: `Are you sure you want to delete workspace "${workspace.name}"? This action cannot be undone.`,
      }),
      okText: t('common:delete', { defaultValue: 'Delete' }),
      okType: 'danger',
      cancelText: t('common:cancel', { defaultValue: 'Cancel' }),
      onOk: async () => {
        try {
          await deleteMutation.mutateAsync({ workspaceId: workspace.id });
          if (selectedWorkspace?.id === workspace.id) {
            setSelectedWorkspace(null);
          }
        } catch (error) {
          // Error handled by hook
        }
      },
    });
  };

  const handleSubmit = async (values: CreateLSWorkspaceRequest | UpdateLSWorkspaceRequest) => {
    try {
      if (editingWorkspace) {
        await updateMutation.mutateAsync({
          workspaceId: editingWorkspace.id,
          request: values as UpdateLSWorkspaceRequest,
        });
      } else {
        await createMutation.mutateAsync(values as CreateLSWorkspaceRequest);
      }
      setIsModalVisible(false);
      form.resetFields();
    } catch (error) {
      // Error handled by hook
    }
  };

  const getActionMenu = (workspace: LSWorkspace): MenuProps['items'] => [
    {
      key: 'view',
      icon: <EyeOutlined />,
      label: t('viewDetails', { defaultValue: 'View Details' }),
      onClick: () => setSelectedWorkspace(workspace),
    },
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: t('common:edit', { defaultValue: 'Edit' }),
      onClick: () => handleEdit(workspace),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: t('settings', { defaultValue: 'Settings' }),
      onClick: () => message.info(t('settingsComingSoon', { defaultValue: 'Settings coming soon' })),
    },
    { type: 'divider' },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: t('common:delete', { defaultValue: 'Delete' }),
      danger: true,
      onClick: () => handleDelete(workspace),
    },
  ];

  const columns: ColumnsType<LSWorkspace> = [
    {
      title: t('columns.name', { defaultValue: 'Name' }),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          <Avatar
            icon={<FolderOutlined />}
            style={{ backgroundColor: record.is_active ? '#1890ff' : '#d9d9d9' }}
          />
          <div>
            <div style={{ fontWeight: 500 }}>{name}</div>
            {record.description && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.description.slice(0, 50)}
                {record.description.length > 50 ? '...' : ''}
              </Text>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: t('columns.status', { defaultValue: 'Status' }),
      dataIndex: 'is_active',
      key: 'status',
      width: 100,
      render: (isActive: boolean) => (
        <Badge
          status={isActive ? 'success' : 'default'}
          text={isActive ? t('status.active', { defaultValue: 'Active' }) : t('status.inactive', { defaultValue: 'Inactive' })}
        />
      ),
      filters: [
        { text: t('status.active', { defaultValue: 'Active' }), value: true },
        { text: t('status.inactive', { defaultValue: 'Inactive' }), value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
    },
    {
      title: t('columns.members', { defaultValue: 'Members' }),
      dataIndex: 'member_count',
      key: 'members',
      width: 100,
      render: (count: number) => (
        <Space>
          <TeamOutlined />
          <span>{count}</span>
        </Space>
      ),
      sorter: (a, b) => a.member_count - b.member_count,
    },
    {
      title: t('columns.projects', { defaultValue: 'Projects' }),
      dataIndex: 'project_count',
      key: 'projects',
      width: 100,
      render: (count: number) => (
        <Space>
          <FolderOutlined />
          <span>{count}</span>
        </Space>
      ),
      sorter: (a, b) => a.project_count - b.project_count,
    },
    {
      title: t('columns.createdAt', { defaultValue: 'Created' }),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => (date ? new Date(date).toLocaleDateString() : '-'),
      sorter: (a, b) => {
        if (!a.created_at || !b.created_at) return 0;
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      },
    },
    {
      title: t('columns.actions', { defaultValue: 'Actions' }),
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Dropdown menu={{ items: getActionMenu(record) }} trigger={['click']}>
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  return (
    <div className="ls-workspaces-page">
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('stats.totalWorkspaces', { defaultValue: 'Total Workspaces' })}
              value={totalWorkspaces}
              prefix={<FolderOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('stats.activeWorkspaces', { defaultValue: 'Active Workspaces' })}
              value={activeWorkspaces}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CrownOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('stats.totalMembers', { defaultValue: 'Total Members' })}
              value={totalMembers}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('stats.totalProjects', { defaultValue: 'Total Projects' })}
              value={totalProjects}
              prefix={<FolderOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* Workspace List */}
        <Col span={selectedWorkspace ? 14 : 24}>
          <Card
            title={
              <Space>
                <FolderOutlined />
                {t('title', { defaultValue: 'Label Studio Workspaces' })}
              </Space>
            }
            extra={
              <Space>
                <span style={{ marginRight: 8 }}>
                  {t('showInactive', { defaultValue: 'Show Inactive' })}:
                </span>
                <Switch
                  size="small"
                  checked={includeInactive}
                  onChange={setIncludeInactive}
                />
                <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                  {t('common:refresh', { defaultValue: 'Refresh' })}
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  {t('createWorkspace', { defaultValue: 'Create Workspace' })}
                </Button>
              </Space>
            }
          >
            <Table
              columns={columns}
              dataSource={workspaces}
              loading={isLoading}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showTotal: (total) =>
                  t('totalWorkspacesCount', {
                    total,
                    defaultValue: `Total ${total} workspaces`,
                  }),
              }}
              onRow={(record) => ({
                onClick: () => setSelectedWorkspace(record),
                style: {
                  cursor: 'pointer',
                  backgroundColor: selectedWorkspace?.id === record.id ? '#e6f7ff' : undefined,
                },
              })}
              locale={{
                emptyText: (
                  <Empty
                    description={t('noWorkspaces', { defaultValue: 'No workspaces found' })}
                  >
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                      {t('createFirstWorkspace', { defaultValue: 'Create Your First Workspace' })}
                    </Button>
                  </Empty>
                ),
              }}
            />
          </Card>
        </Col>

        {/* Detail Panel */}
        {selectedWorkspace && (
          <Col span={10}>
            <Card
              title={
                <Space>
                  <Avatar
                    icon={<FolderOutlined />}
                    style={{ backgroundColor: '#1890ff' }}
                  />
                  <div>
                    <div style={{ fontWeight: 500 }}>{selectedWorkspace.name}</div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {selectedWorkspace.description || t('noDescription', { defaultValue: 'No description' })}
                    </Text>
                  </div>
                </Space>
              }
              extra={
                <Space>
                  <Button
                    type="text"
                    icon={<EditOutlined />}
                    onClick={() => handleEdit(selectedWorkspace)}
                  />
                  <Button
                    type="text"
                    onClick={() => setSelectedWorkspace(null)}
                  >
                    {t('common:close', { defaultValue: 'Close' })}
                  </Button>
                </Space>
              }
            >
              <Tabs
                activeKey={detailTab}
                onChange={(key) => setDetailTab(key as 'members' | 'projects')}
                items={[
                  {
                    key: 'members',
                    label: (
                      <span>
                        <TeamOutlined />
                        {t('tabs.members', { defaultValue: 'Members' })} ({selectedWorkspace.member_count})
                      </span>
                    ),
                    children: (
                      <LSWorkspaceMemberManagement workspaceId={selectedWorkspace.id} />
                    ),
                  },
                  {
                    key: 'projects',
                    label: (
                      <span>
                        <FolderOutlined />
                        {t('tabs.projects', { defaultValue: 'Projects' })} ({selectedWorkspace.project_count})
                      </span>
                    ),
                    children: (
                      <LSWorkspaceProjectList workspaceId={selectedWorkspace.id} />
                    ),
                  },
                ]}
              />
            </Card>
          </Col>
        )}
      </Row>

      {/* Create/Edit Modal */}
      <Modal
        title={
          editingWorkspace
            ? t('editWorkspace', { defaultValue: 'Edit Workspace' })
            : t('createWorkspace', { defaultValue: 'Create Workspace' })
        }
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label={t('form.name', { defaultValue: 'Workspace Name' })}
            rules={[
              {
                required: true,
                message: t('form.nameRequired', { defaultValue: 'Please enter workspace name' }),
              },
              {
                max: 100,
                message: t('form.nameTooLong', { defaultValue: 'Name cannot exceed 100 characters' }),
              },
            ]}
          >
            <Input
              placeholder={t('form.namePlaceholder', { defaultValue: 'Enter workspace name' })}
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={t('form.description', { defaultValue: 'Description' })}
            rules={[
              {
                max: 500,
                message: t('form.descriptionTooLong', { defaultValue: 'Description cannot exceed 500 characters' }),
              },
            ]}
          >
            <TextArea
              rows={3}
              placeholder={t('form.descriptionPlaceholder', { defaultValue: 'Enter workspace description (optional)' })}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default LSWorkspacesPage;
