// Label Studio permission mapping component
import { useState, useCallback } from 'react';
import { Card, Table, Tag, Space, Button, Select, Alert, Modal, message, Badge } from 'antd';
import {
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  UserOutlined,
  LockOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

// SuperInsight roles
type SuperInsightRole = 'ADMIN' | 'BUSINESS_EXPERT' | 'ANNOTATOR' | 'VIEWER';

// Label Studio roles
type LabelStudioRole = 'owner' | 'manager' | 'annotator' | 'reviewer';

interface UserPermissionMapping {
  userId: string;
  userName: string;
  email: string;
  superInsightRole: SuperInsightRole;
  labelStudioRole: LabelStudioRole;
  syncStatus: 'synced' | 'pending' | 'error';
  lastSyncAt?: string;
  projects: string[];
}

interface RoleMapping {
  superInsightRole: SuperInsightRole;
  labelStudioRole: LabelStudioRole;
  description: string;
}

interface PermissionMapperProps {
  projectId?: string;
  onSyncComplete?: (users: UserPermissionMapping[]) => void;
}

// Default role mappings
const defaultRoleMappings: RoleMapping[] = [
  { superInsightRole: 'ADMIN', labelStudioRole: 'owner', description: '完全控制权限' },
  { superInsightRole: 'BUSINESS_EXPERT', labelStudioRole: 'manager', description: '项目管理权限' },
  { superInsightRole: 'ANNOTATOR', labelStudioRole: 'annotator', description: '标注权限' },
  { superInsightRole: 'VIEWER', labelStudioRole: 'reviewer', description: '查看和审核权限' },
];

export const PermissionMapper: React.FC<PermissionMapperProps> = ({
  onSyncComplete,
}) => {
  const { t } = useTranslation(['labelStudio', 'common']);
  const [isSyncing, setIsSyncing] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [roleMappings, setRoleMappings] = useState<RoleMapping[]>(defaultRoleMappings);
  const [editMappingVisible, setEditMappingVisible] = useState(false);

  // Mock user data
  const [users, setUsers] = useState<UserPermissionMapping[]>([
    {
      userId: '1',
      userName: '张三',
      email: 'zhangsan@company.com',
      superInsightRole: 'ADMIN',
      labelStudioRole: 'owner',
      syncStatus: 'synced',
      lastSyncAt: new Date().toISOString(),
      projects: ['proj-1', 'proj-2', 'proj-3'],
    },
    {
      userId: '2',
      userName: '李四',
      email: 'lisi@company.com',
      superInsightRole: 'BUSINESS_EXPERT',
      labelStudioRole: 'manager',
      syncStatus: 'synced',
      lastSyncAt: new Date().toISOString(),
      projects: ['proj-1', 'proj-2'],
    },
    {
      userId: '3',
      userName: '王五',
      email: 'wangwu@company.com',
      superInsightRole: 'ANNOTATOR',
      labelStudioRole: 'annotator',
      syncStatus: 'pending',
      projects: ['proj-1'],
    },
    {
      userId: '4',
      userName: '赵六',
      email: 'zhaoliu@company.com',
      superInsightRole: 'VIEWER',
      labelStudioRole: 'reviewer',
      syncStatus: 'error',
      projects: [],
    },
  ]);

  // Get role display config
  const getRoleConfig = (role: SuperInsightRole) => {
    switch (role) {
      case 'ADMIN':
        return { color: 'red', text: '系统管理员' };
      case 'BUSINESS_EXPERT':
        return { color: 'blue', text: '业务专家' };
      case 'ANNOTATOR':
        return { color: 'green', text: '标注员' };
      case 'VIEWER':
        return { color: 'default', text: '查看者' };
      default:
        return { color: 'default', text: role };
    }
  };

  const getLSRoleConfig = (role: LabelStudioRole) => {
    switch (role) {
      case 'owner':
        return { color: 'red', text: 'Owner' };
      case 'manager':
        return { color: 'blue', text: 'Manager' };
      case 'annotator':
        return { color: 'green', text: 'Annotator' };
      case 'reviewer':
        return { color: 'orange', text: 'Reviewer' };
      default:
        return { color: 'default', text: role };
    }
  };

  const getSyncStatusConfig = (status: UserPermissionMapping['syncStatus']) => {
    switch (status) {
      case 'synced':
        return { color: 'success', icon: <CheckCircleOutlined />, text: '已同步' };
      case 'pending':
        return { color: 'warning', icon: <SyncOutlined />, text: '待同步' };
      case 'error':
        return { color: 'error', icon: <ExclamationCircleOutlined />, text: '同步失败' };
      default:
        return { color: 'default', icon: <SyncOutlined />, text: status };
    }
  };

  // Sync single user
  const handleSyncUser = useCallback(async (userId: string) => {
    setIsSyncing(true);
    
    // Update status to pending
    setUsers(prev => prev.map(u => 
      u.userId === userId ? { ...u, syncStatus: 'pending' as const } : u
    ));

    // Simulate sync
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Update status to synced
    setUsers(prev => prev.map(u => 
      u.userId === userId ? { 
        ...u, 
        syncStatus: 'synced' as const,
        lastSyncAt: new Date().toISOString(),
      } : u
    ));

    setIsSyncing(false);
    message.success(t('permission.syncSuccess') || 'User permission synced successfully');
  }, [t]);

  // Sync all users
  const handleSyncAll = useCallback(async () => {
    setIsSyncing(true);
    
    // Update all to pending
    setUsers(prev => prev.map(u => ({ ...u, syncStatus: 'pending' as const })));

    // Simulate sync
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Update all to synced
    setUsers(prev => prev.map(u => ({ 
      ...u, 
      syncStatus: 'synced' as const,
      lastSyncAt: new Date().toISOString(),
    })));

    setIsSyncing(false);
    message.success(t('permission.syncAllSuccess') || 'All user permissions synced successfully');
    onSyncComplete?.(users);
  }, [users, onSyncComplete, t]);

  // Sync selected users
  const handleSyncSelected = useCallback(async () => {
    if (selectedUsers.length === 0) {
      message.warning(t('permission.selectUsers') || 'Please select users to sync');
      return;
    }

    setIsSyncing(true);
    
    for (const userId of selectedUsers) {
      await handleSyncUser(userId);
    }

    setSelectedUsers([]);
    setIsSyncing(false);
  }, [selectedUsers, handleSyncUser, t]);

  // Update role mapping
  const handleUpdateMapping = useCallback((superInsightRole: SuperInsightRole, labelStudioRole: LabelStudioRole) => {
    setRoleMappings(prev => prev.map(m => 
      m.superInsightRole === superInsightRole ? { ...m, labelStudioRole } : m
    ));
    
    // Update users with this role
    setUsers(prev => prev.map(u => 
      u.superInsightRole === superInsightRole ? { 
        ...u, 
        labelStudioRole,
        syncStatus: 'pending' as const,
      } : u
    ));

    message.info(t('permission.mappingUpdated') || 'Role mapping updated. Please sync to apply changes.');
  }, [t]);

  const columns = [
    {
      title: t('permission.user') || 'User',
      key: 'user',
      render: (_: unknown, record: UserPermissionMapping) => (
        <Space>
          <UserOutlined />
          <Space direction="vertical" size={0}>
            <span>{record.userName}</span>
            <span style={{ fontSize: 12, color: '#999' }}>{record.email}</span>
          </Space>
        </Space>
      ),
    },
    {
      title: t('permission.superInsightRole') || 'SuperInsight Role',
      dataIndex: 'superInsightRole',
      key: 'superInsightRole',
      render: (role: SuperInsightRole) => {
        const config = getRoleConfig(role);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: t('permission.labelStudioRole') || 'Label Studio Role',
      dataIndex: 'labelStudioRole',
      key: 'labelStudioRole',
      render: (role: LabelStudioRole) => {
        const config = getLSRoleConfig(role);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: t('permission.projects') || 'Projects',
      dataIndex: 'projects',
      key: 'projects',
      render: (projects: string[]) => (
        <Badge count={projects.length} style={{ backgroundColor: '#1890ff' }}>
          <TeamOutlined style={{ fontSize: 16 }} />
        </Badge>
      ),
    },
    {
      title: t('permission.syncStatus') || 'Sync Status',
      dataIndex: 'syncStatus',
      key: 'syncStatus',
      render: (status: UserPermissionMapping['syncStatus']) => {
        const config = getSyncStatusConfig(status);
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: t('permission.lastSync') || 'Last Sync',
      dataIndex: 'lastSyncAt',
      key: 'lastSyncAt',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: t('common.actions') || 'Actions',
      key: 'actions',
      render: (_: unknown, record: UserPermissionMapping) => (
        <Button
          type="link"
          icon={<SyncOutlined />}
          onClick={() => handleSyncUser(record.userId)}
          loading={isSyncing && record.syncStatus === 'pending'}
        >
          {t('permission.sync') || 'Sync'}
        </Button>
      ),
    },
  ];

  const mappingColumns = [
    {
      title: t('permission.superInsightRole') || 'SuperInsight Role',
      dataIndex: 'superInsightRole',
      key: 'superInsightRole',
      render: (role: SuperInsightRole) => {
        const config = getRoleConfig(role);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '→',
      key: 'arrow',
      width: 50,
      render: () => <span style={{ color: '#999' }}>→</span>,
    },
    {
      title: t('permission.labelStudioRole') || 'Label Studio Role',
      dataIndex: 'labelStudioRole',
      key: 'labelStudioRole',
      render: (role: LabelStudioRole, record: RoleMapping) => (
        <Select
          value={role}
          onChange={(value) => handleUpdateMapping(record.superInsightRole, value)}
          style={{ width: 120 }}
          options={[
            { value: 'owner', label: 'Owner' },
            { value: 'manager', label: 'Manager' },
            { value: 'annotator', label: 'Annotator' },
            { value: 'reviewer', label: 'Reviewer' },
          ]}
        />
      ),
    },
    {
      title: t('permission.description') || 'Description',
      dataIndex: 'description',
      key: 'description',
    },
  ];

  // Calculate stats
  const syncedCount = users.filter(u => u.syncStatus === 'synced').length;
  const pendingCount = users.filter(u => u.syncStatus === 'pending').length;
  const errorCount = users.filter(u => u.syncStatus === 'error').length;

  return (
    <div>
      {/* Summary Alert */}
      <Alert
        message={t('permission.summary') || 'Permission Sync Summary'}
        description={
          <Space size="large">
            <span><CheckCircleOutlined style={{ color: '#52c41a' }} /> {t('permission.synced') || 'Synced'}: {syncedCount}</span>
            <span><SyncOutlined style={{ color: '#faad14' }} /> {t('permission.pending') || 'Pending'}: {pendingCount}</span>
            <span><ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> {t('permission.error') || 'Error'}: {errorCount}</span>
          </Space>
        }
        type="info"
        showIcon
        icon={<LockOutlined />}
        style={{ marginBottom: 16 }}
      />

      {/* Role Mapping Configuration */}
      <Card
        title={
          <Space>
            <LockOutlined />
            {t('permission.roleMapping') || 'Role Mapping Configuration'}
          </Space>
        }
        style={{ marginBottom: 16 }}
        extra={
          <Button onClick={() => setEditMappingVisible(true)}>
            {t('permission.editMapping') || 'Edit Mapping'}
          </Button>
        }
      >
        <Table
          dataSource={roleMappings}
          columns={mappingColumns}
          rowKey="superInsightRole"
          pagination={false}
          size="small"
        />
      </Card>

      {/* User Permission List */}
      <Card
        title={
          <Space>
            <UserOutlined />
            {t('permission.userPermissions') || 'User Permissions'}
          </Space>
        }
        extra={
          <Space>
            {selectedUsers.length > 0 && (
              <Button
                icon={<SyncOutlined />}
                onClick={handleSyncSelected}
                loading={isSyncing}
              >
                {t('permission.syncSelected', { count: selectedUsers.length }) || `Sync Selected (${selectedUsers.length})`}
              </Button>
            )}
            <Button
              type="primary"
              icon={<SyncOutlined />}
              onClick={handleSyncAll}
              loading={isSyncing}
            >
              {t('permission.syncAll') || 'Sync All'}
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={users}
          columns={columns}
          rowKey="userId"
          rowSelection={{
            selectedRowKeys: selectedUsers,
            onChange: (keys) => setSelectedUsers(keys as string[]),
          }}
          pagination={false}
        />
      </Card>

      {/* Edit Mapping Modal */}
      <Modal
        title={t('permission.editRoleMapping') || 'Edit Role Mapping'}
        open={editMappingVisible}
        onCancel={() => setEditMappingVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setEditMappingVisible(false)}>
            {t('common.cancel') || 'Cancel'}
          </Button>,
          <Button key="save" type="primary" onClick={() => {
            setEditMappingVisible(false);
            message.success(t('permission.mappingSaved') || 'Role mapping saved');
          }}>
            {t('common.save') || 'Save'}
          </Button>,
        ]}
      >
        <Alert
          message={t('permission.mappingNote') || 'Note'}
          description={t('permission.mappingNoteDesc') || 'Changes to role mapping will require re-syncing affected users.'}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Table
          dataSource={roleMappings}
          columns={mappingColumns}
          rowKey="superInsightRole"
          pagination={false}
          size="small"
        />
      </Modal>
    </div>
  );
};

export default PermissionMapper;
