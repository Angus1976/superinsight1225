// Workspace switcher component for switching workspaces
import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { 
  Select, 
  Spin, 
  Button, 
  Modal, 
  Form, 
  Input, 
  Space, 
  Tooltip,
  Badge,
  Divider,
  Typography,
  message
} from 'antd';
import { 
  AppstoreOutlined, 
  PlusOutlined,
  TeamOutlined,
  FolderOutlined,
  CheckCircleOutlined,
  SwapOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/hooks/useAuth';
import type { Workspace } from '@/types';

const { Text } = Typography;

interface WorkspaceSwitcherProps {
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
  showCreateButton?: boolean;
  showLabel?: boolean;
  onWorkspaceChange?: (workspace: Workspace) => void;
  className?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({
  size = 'middle',
  style,
  showCreateButton = true,
  showLabel = false,
  onWorkspaceChange,
  className,
  autoRefresh = false,
  refreshInterval = 60000, // 1 minute default
}) => {
  const { t } = useTranslation('auth');
  const { 
    currentWorkspace, 
    workspaces, 
    switchWorkspace, 
    createWorkspace,
    refreshWorkspaces,
    user 
  } = useAuth();
  
  const [switching, setSwitching] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [creating, setCreating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [form] = Form.useForm();
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-refresh workspaces periodically
  useEffect(() => {
    if (autoRefresh && user) {
      refreshTimerRef.current = setInterval(async () => {
        try {
          await refreshWorkspaces();
        } catch (error) {
          console.error('Auto-refresh workspaces failed:', error);
        }
      }, refreshInterval);

      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, refreshWorkspaces, user]);

  // Handle manual refresh
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshWorkspaces();
      message.success(t('workspace.refreshSuccess', '工作空间列表已刷新'));
    } catch (error) {
      console.error('Failed to refresh workspaces:', error);
      message.error(t('workspace.refreshFailed', '刷新工作空间列表失败'));
    } finally {
      setRefreshing(false);
    }
  }, [refreshWorkspaces, t]);

  // Optimized workspace change handler with debounce protection
  const handleWorkspaceChange = useCallback(async (workspaceId: string) => {
    if (workspaceId === currentWorkspace?.id || switching) return;
    
    const selectedWorkspace = workspaces.find(w => w.id === workspaceId);
    if (!selectedWorkspace) {
      message.error(t('workspace.switchFailed', '切换工作空间失败'));
      return;
    }

    setSwitching(true);
    try {
      const success = await switchWorkspace(workspaceId);
      
      if (success) {
        onWorkspaceChange?.(selectedWorkspace);
      }
    } catch (error) {
      console.error('Failed to switch workspace:', error);
      const errorMessage = error instanceof Error ? error.message : t('workspace.switchFailed', '切换工作空间失败');
      message.error(errorMessage);
    } finally {
      setSwitching(false);
    }
  }, [currentWorkspace?.id, workspaces, switchWorkspace, onWorkspaceChange, switching, t]);

  const handleCreateWorkspace = useCallback(async (values: { name: string; description?: string }) => {
    setCreating(true);
    try {
      const newWorkspace = await createWorkspace(values);
      
      if (newWorkspace) {
        setCreateModalVisible(false);
        form.resetFields();
        
        // Optionally switch to the new workspace
        await switchWorkspace(newWorkspace.id);
        onWorkspaceChange?.(newWorkspace);
      }
    } catch (error) {
      console.error('Failed to create workspace:', error);
      const errorMessage = error instanceof Error ? error.message : t('workspace.createFailed', '创建工作空间失败');
      message.error(errorMessage);
    } finally {
      setCreating(false);
    }
  }, [createWorkspace, switchWorkspace, onWorkspaceChange, form, t]);

  const handleOpenCreateModal = useCallback(() => {
    setCreateModalVisible(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setCreateModalVisible(false);
    form.resetFields();
  }, [form]);

  // Translate workspace name for display
  const translateWorkspaceName = useCallback((name: string): string => {
    // Check if it's a default workspace name pattern: "{tenant_id} Workspace"
    if (name.endsWith(' Workspace') || name.endsWith(' workspace')) {
      return t('workspace.defaultWorkspaceName', '默认工作空间');
    }
    // Return original name for custom workspaces
    return name;
  }, [t]);

  // Optimized filter function for search
  const filterOption = useCallback((input: string, option?: { label?: string; value?: string }) => {
    if (!option) return false;
    const workspace = workspaces.find(w => w.id === option?.value);
    if (!workspace) return false;
    return workspace.name.toLowerCase().includes(input.toLowerCase());
  }, [workspaces]);

  // Memoized workspace options for better performance
  const workspaceOptions = useMemo(() => {
    return workspaces.map((workspace) => ({
      value: workspace.id,
      label: translateWorkspaceName(workspace.name),
      workspace,
    }));
  }, [workspaces, translateWorkspaceName]);

  // Don't show if not logged in
  if (!user) {
    return null;
  }

  // Show loading state if workspaces haven't loaded yet
  if (workspaces.length === 0) {
    return (
      <Tooltip title={t('workspace.loading', '加载工作空间...')}>
        <Button type="text" size={size} loading>
          <AppstoreOutlined />
        </Button>
      </Tooltip>
    );
  }

  return (
    <>
      <Space size={4} className={className}>
        {showLabel && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('workspace.select', '选择工作空间')}:
          </Text>
        )}
        <Select
          value={currentWorkspace?.id}
          onChange={handleWorkspaceChange}
          loading={switching}
          size={size}
          style={{ minWidth: 160, ...style }}
          placeholder={t('workspace.selectPlaceholder', '选择工作空间')}
          suffixIcon={switching ? <SwapOutlined spin /> : <AppstoreOutlined />}
          showSearch
          filterOption={filterOption}
          disabled={switching}
          optionLabelProp="label"
          popupMatchSelectWidth={false}
          styles={{ popup: { root: { minWidth: 220 } } }}
          aria-label={t('workspace.select', '选择工作空间')}
          notFoundContent={<Spin size="small" />}
          popupRender={(menu) => (
            <>
              {menu}
              <Divider style={{ margin: '8px 0' }} />
              <Space style={{ padding: '0 8px 8px', width: '100%', justifyContent: 'space-between' }}>
                {showCreateButton && (
                  <Button
                    type="text"
                    icon={<PlusOutlined />}
                    onClick={handleOpenCreateModal}
                    size="small"
                  >
                    {t('workspace.create', '创建工作空间')}
                  </Button>
                )}
                <Tooltip title={t('workspace.refresh', '刷新列表')}>
                  <Button
                    type="text"
                    icon={<ReloadOutlined spin={refreshing} />}
                    onClick={handleRefresh}
                    size="small"
                    loading={refreshing}
                  />
                </Tooltip>
              </Space>
            </>
          )}
        >
          {workspaceOptions.map(({ value, workspace }) => (
            <Select.Option 
              key={value} 
              value={value}
              label={translateWorkspaceName(workspace.name)}
            >
              <div 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                  gap: 8,
                  padding: '4px 0',
                }}
              >
                <Space size={8}>
                  <FolderOutlined style={{ color: '#1890ff', fontSize: 14 }} />
                  <span style={{ fontWeight: workspace.id === currentWorkspace?.id ? 500 : 400 }}>
                    {translateWorkspaceName(workspace.name)}
                  </span>
                </Space>
                <Space size={4}>
                  {workspace.is_default && (
                    <Badge 
                      count={t('workspace.default', '默认')} 
                      style={{ 
                        backgroundColor: '#52c41a', 
                        fontSize: '10px',
                        padding: '0 4px'
                      }} 
                    />
                  )}
                  {workspace.member_count !== undefined && (
                    <Tooltip title={t('workspace.members', '成员数')}>
                      <span style={{ color: '#999', fontSize: '12px' }}>
                        <TeamOutlined /> {workspace.member_count}
                      </span>
                    </Tooltip>
                  )}
                  {workspace.id === currentWorkspace?.id && (
                    <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
                  )}
                </Space>
              </div>
            </Select.Option>
          ))}
        </Select>
      </Space>

      {/* Create Workspace Modal */}
      <Modal
        title={
          <Space>
            <PlusOutlined />
            {t('workspace.createTitle', '创建新工作空间')}
          </Space>
        }
        open={createModalVisible}
        onCancel={handleCloseCreateModal}
        footer={null}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateWorkspace}
          autoComplete="off"
        >
          <Form.Item
            name="name"
            label={t('workspace.name', '工作空间名称')}
            rules={[
              { required: true, message: t('workspace.nameRequired', '请输入工作空间名称') },
              { min: 2, message: t('workspace.nameMinLength', '名称至少2个字符') },
              { max: 50, message: t('workspace.nameMaxLength', '名称最多50个字符') },
            ]}
          >
            <Input 
              placeholder={t('workspace.namePlaceholder', '输入工作空间名称')}
              prefix={<FolderOutlined />}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('workspace.description', '描述')}
            rules={[
              { max: 200, message: t('workspace.descriptionMaxLength', '描述最多200个字符') },
            ]}
          >
            <Input.TextArea 
              placeholder={t('workspace.descriptionPlaceholder', '可选：添加工作空间描述')}
              rows={3}
              showCount
              maxLength={200}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={handleCloseCreateModal}>
                {t('cancel', { ns: 'common' })}
              </Button>
              <Button type="primary" htmlType="submit" loading={creating}>
                {t('create', { ns: 'common' })}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
