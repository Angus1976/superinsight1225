/**
 * Label Studio Workspace Selector Component
 *
 * A dropdown selector for switching between Label Studio workspaces.
 * Features:
 * - Workspace selection with search
 * - Create new workspace modal
 * - Member and project count display
 * - Auto-refresh support
 * - i18n support
 */

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
  message,
} from 'antd';
import {
  AppstoreOutlined,
  PlusOutlined,
  TeamOutlined,
  FolderOutlined,
  ProjectOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  useLSWorkspaceSelector,
  useCreateLSWorkspace,
  useLSWorkspaces,
} from '@/hooks/useLSWorkspaces';
import type { LSWorkspace, CreateLSWorkspaceRequest } from '@/types/ls-workspace';

const { Text } = Typography;

interface LSWorkspaceSelectorProps {
  /** Selected workspace ID */
  value?: string | null;
  /** Callback when workspace changes */
  onChange?: (workspaceId: string | null, workspace: LSWorkspace | null) => void;
  /** Selector size */
  size?: 'small' | 'middle' | 'large';
  /** Custom style */
  style?: React.CSSProperties;
  /** Show create button */
  showCreateButton?: boolean;
  /** Show label */
  showLabel?: boolean;
  /** Additional class name */
  className?: string;
  /** Auto refresh interval in ms (0 to disable) */
  autoRefreshInterval?: number;
  /** Placeholder text */
  placeholder?: string;
  /** Allow clearing selection */
  allowClear?: boolean;
  /** Disabled state */
  disabled?: boolean;
}

export const LSWorkspaceSelector: React.FC<LSWorkspaceSelectorProps> = ({
  value,
  onChange,
  size = 'middle',
  style,
  showCreateButton = true,
  showLabel = false,
  className,
  autoRefreshInterval = 0,
  placeholder,
  allowClear = false,
  disabled = false,
}) => {
  const { t } = useTranslation(['labelStudio', 'common']);
  const { workspaces, isLoading, error, total } = useLSWorkspaceSelector();
  const { refetch } = useLSWorkspaces();
  const createWorkspaceMutation = useCreateLSWorkspace();

  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [form] = Form.useForm();
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-refresh workspaces periodically
  useEffect(() => {
    if (autoRefreshInterval > 0) {
      refreshTimerRef.current = setInterval(async () => {
        try {
          await refetch();
        } catch (err) {
          console.error('Auto-refresh workspaces failed:', err);
        }
      }, autoRefreshInterval);

      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [autoRefreshInterval, refetch]);

  // Handle manual refresh
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refetch();
      message.success(t('workspace.refreshSuccess', 'Workspace list refreshed'));
    } catch (err) {
      console.error('Failed to refresh workspaces:', err);
      message.error(t('workspace.refreshFailed', 'Failed to refresh workspace list'));
    } finally {
      setRefreshing(false);
    }
  }, [refetch, t]);

  // Handle workspace change
  const handleWorkspaceChange = useCallback(
    (workspaceId: string | null) => {
      const selectedWorkspace = workspaceId
        ? workspaces.find((w) => w.id === workspaceId) ?? null
        : null;
      onChange?.(workspaceId, selectedWorkspace);
    },
    [workspaces, onChange]
  );

  // Handle create workspace
  const handleCreateWorkspace = useCallback(
    async (values: { name: string; description?: string }) => {
      try {
        const request: CreateLSWorkspaceRequest = {
          name: values.name,
          description: values.description,
        };
        const newWorkspace = await createWorkspaceMutation.mutateAsync(request);

        setCreateModalVisible(false);
        form.resetFields();

        // Select the new workspace
        onChange?.(newWorkspace.id, newWorkspace);
      } catch (err) {
        console.error('Failed to create workspace:', err);
      }
    },
    [createWorkspaceMutation, form, onChange]
  );

  const handleOpenCreateModal = useCallback(() => {
    setCreateModalVisible(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setCreateModalVisible(false);
    form.resetFields();
  }, [form]);

  // Filter function for search
  const filterOption = useCallback(
    (input: string, option?: { label?: string; value?: string }) => {
      if (!option) return false;
      const workspace = workspaces.find((w) => w.id === option?.value);
      if (!workspace) return false;
      return workspace.name.toLowerCase().includes(input.toLowerCase());
    },
    [workspaces]
  );

  // Memoized workspace options
  const workspaceOptions = useMemo(() => {
    return workspaces.map((workspace) => ({
      value: workspace.id,
      label: workspace.name,
      workspace,
    }));
  }, [workspaces]);

  // Get current selected workspace
  const selectedWorkspace = useMemo(() => {
    return value ? workspaces.find((w) => w.id === value) : null;
  }, [value, workspaces]);

  // Show loading state if workspaces haven't loaded yet
  if (isLoading && workspaces.length === 0) {
    return (
      <Tooltip title={t('workspace.loading', 'Loading workspaces...')}>
        <Button type="text" size={size} loading>
          <AppstoreOutlined />
        </Button>
      </Tooltip>
    );
  }

  if (error) {
    return (
      <Tooltip title={t('workspace.loadError', 'Failed to load workspaces')}>
        <Button type="text" size={size} danger onClick={handleRefresh}>
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
            {t('workspace.label', 'Label Studio Workspace')}:
          </Text>
        )}
        <Select
          value={value}
          onChange={handleWorkspaceChange}
          loading={isLoading}
          size={size}
          style={{ minWidth: 180, ...style }}
          placeholder={placeholder ?? t('workspace.selectPlaceholder', 'Select workspace')}
          suffixIcon={<AppstoreOutlined />}
          showSearch
          filterOption={filterOption}
          disabled={disabled}
          allowClear={allowClear}
          optionLabelProp="label"
          popupMatchSelectWidth={false}
          styles={{ popup: { root: { minWidth: 240 } } }}
          aria-label={t('workspace.select', 'Select workspace')}
          notFoundContent={
            isLoading ? (
              <Spin size="small" />
            ) : (
              <span>{t('workspace.noWorkspaces', 'No workspaces found')}</span>
            )
          }
          popupRender={(menu) => (
            <>
              {menu}
              <Divider style={{ margin: '8px 0' }} />
              <Space
                style={{
                  padding: '0 8px 8px',
                  width: '100%',
                  justifyContent: 'space-between',
                }}
              >
                {showCreateButton && (
                  <Button
                    type="text"
                    icon={<PlusOutlined />}
                    onClick={handleOpenCreateModal}
                    size="small"
                  >
                    {t('workspace.create', 'Create workspace')}
                  </Button>
                )}
                <Tooltip title={t('workspace.refresh', 'Refresh list')}>
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
          {workspaceOptions.map(({ value: optionValue, workspace }) => (
            <Select.Option key={optionValue} value={optionValue} label={workspace.name}>
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
                  <span
                    style={{
                      fontWeight: workspace.id === value ? 500 : 400,
                    }}
                  >
                    {workspace.name}
                  </span>
                </Space>
                <Space size={8}>
                  {workspace.member_count > 0 && (
                    <Tooltip title={t('workspace.memberCount', 'Members')}>
                      <span style={{ color: '#999', fontSize: '12px' }}>
                        <TeamOutlined /> {workspace.member_count}
                      </span>
                    </Tooltip>
                  )}
                  {workspace.project_count > 0 && (
                    <Tooltip title={t('workspace.projectCount', 'Projects')}>
                      <span style={{ color: '#999', fontSize: '12px' }}>
                        <ProjectOutlined /> {workspace.project_count}
                      </span>
                    </Tooltip>
                  )}
                  {workspace.id === value && (
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
            {t('workspace.createTitle', 'Create New Workspace')}
          </Space>
        }
        open={createModalVisible}
        onCancel={handleCloseCreateModal}
        footer={null}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={handleCreateWorkspace} autoComplete="off">
          <Form.Item
            name="name"
            label={t('workspace.nameLabel', 'Workspace Name')}
            rules={[
              { required: true, message: t('workspace.nameRequired', 'Please enter workspace name') },
              { min: 2, message: t('workspace.nameMinLength', 'Name must be at least 2 characters') },
              { max: 255, message: t('workspace.nameMaxLength', 'Name must not exceed 255 characters') },
            ]}
          >
            <Input
              placeholder={t('workspace.namePlaceholder', 'Enter workspace name')}
              prefix={<FolderOutlined />}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('workspace.descriptionLabel', 'Description')}
            rules={[
              { max: 2000, message: t('workspace.descriptionMaxLength', 'Description must not exceed 2000 characters') },
            ]}
          >
            <Input.TextArea
              placeholder={t('workspace.descriptionPlaceholder', 'Optional: Add workspace description')}
              rows={3}
              showCount
              maxLength={2000}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={handleCloseCreateModal}>
                {t('cancel', 'Cancel', { ns: 'common' })}
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={createWorkspaceMutation.isPending}
              >
                {t('create', 'Create', { ns: 'common' })}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default LSWorkspaceSelector;
