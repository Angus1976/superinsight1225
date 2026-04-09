// Label Studio project synchronization component with workspace filtering
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Row, Col, Progress, Tag, Space, Button, Table, Alert, Statistic, Badge, Tooltip, message, Empty } from 'antd';
import {
  SyncOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  CloudSyncOutlined,
  UserOutlined,
  FileTextOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { LSWorkspaceSelector } from './LSWorkspaceSelector';
import { useLSWorkspaceProjects } from '@/hooks/useLSWorkspaces';
import type { LSWorkspace, LSWorkspaceProject } from '@/types/ls-workspace';

interface ProjectSyncStatus {
  projectId: string;
  projectName: string;
  labelStudioProjectId: string;
  syncStatus: 'synced' | 'syncing' | 'pending' | 'error';
  lastSyncAt?: string;
  totalTasks: number;
  completedTasks: number;
  annotators: number;
  errorMessage?: string;
  workspaceId?: string;
}

interface SyncLog {
  id: string;
  timestamp: string;
  action: 'sync_start' | 'sync_complete' | 'sync_error' | 'task_import' | 'annotation_export';
  status: 'success' | 'error' | 'warning';
  message: string;
  details?: Record<string, unknown>;
}

interface ProjectSyncProps {
  projectId?: string;
  autoSync?: boolean;
  syncInterval?: number;
  onSyncComplete?: (status: ProjectSyncStatus) => void;
  onSyncError?: (error: string) => void;
  /** Initial workspace ID to filter projects */
  initialWorkspaceId?: string | null;
  /** Whether to show workspace selector */
  showWorkspaceSelector?: boolean;
  /** Callback when workspace changes */
  onWorkspaceChange?: (workspaceId: string | null, workspace: LSWorkspace | null) => void;
}

export const ProjectSync: React.FC<ProjectSyncProps> = ({
  autoSync = false,
  syncInterval = 60000,
  onSyncComplete,
  initialWorkspaceId = null,
  showWorkspaceSelector = true,
  onWorkspaceChange,
}) => {
  const { t } = useTranslation(['labelStudio', 'common']);
  const [syncStatus, setSyncStatus] = useState<ProjectSyncStatus[]>([]);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);

  // Workspace filtering state
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(initialWorkspaceId);
  const [selectedWorkspace, setSelectedWorkspace] = useState<LSWorkspace | null>(null);

  // Fetch workspace projects when a workspace is selected
  const {
    data: workspaceProjectsData,
    isLoading: isLoadingWorkspaceProjects,
    refetch: refetchWorkspaceProjects
  } = useLSWorkspaceProjects(selectedWorkspaceId);

  // Handle workspace change
  const handleWorkspaceChange = useCallback((workspaceId: string | null, workspace: LSWorkspace | null) => {
    setSelectedWorkspaceId(workspaceId);
    setSelectedWorkspace(workspace);
    onWorkspaceChange?.(workspaceId, workspace);
  }, [onWorkspaceChange]);

  // Mock sync status data
  const mockSyncStatus: ProjectSyncStatus[] = [
    {
      projectId: '1',
      projectName: '客服对话标注项目',
      labelStudioProjectId: 'ls-proj-001',
      syncStatus: 'synced',
      lastSyncAt: new Date().toISOString(),
      totalTasks: 500,
      completedTasks: 350,
      annotators: 5,
    },
    {
      projectId: '2',
      projectName: '医疗文档实体识别',
      labelStudioProjectId: 'ls-proj-002',
      syncStatus: 'syncing',
      lastSyncAt: new Date(Date.now() - 300000).toISOString(),
      totalTasks: 300,
      completedTasks: 180,
      annotators: 3,
    },
    {
      projectId: '3',
      projectName: '金融报告分类',
      labelStudioProjectId: 'ls-proj-003',
      syncStatus: 'error',
      lastSyncAt: new Date(Date.now() - 3600000).toISOString(),
      totalTasks: 200,
      completedTasks: 200,
      annotators: 2,
      errorMessage: '连接超时，请检查 Label Studio 服务状态',
    },
  ];

  const mockSyncLogs: SyncLog[] = [
    {
      id: '1',
      timestamp: new Date().toISOString(),
      action: 'sync_complete',
      status: 'success',
      message: '项目同步完成',
      details: { tasksImported: 50, annotationsExported: 120 },
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 300000).toISOString(),
      action: 'sync_start',
      status: 'success',
      message: '开始同步项目数据',
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 600000).toISOString(),
      action: 'annotation_export',
      status: 'success',
      message: '导出标注数据',
      details: { count: 45 },
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      action: 'sync_error',
      status: 'error',
      message: '同步失败：连接超时',
    },
  ];

  // Convert workspace projects to sync status format
  const workspaceProjectsAsSyncStatus = useMemo((): ProjectSyncStatus[] => {
    if (!workspaceProjectsData?.items) return [];
    return workspaceProjectsData.items.map((project: LSWorkspaceProject) => ({
      projectId: project.id,
      projectName: project.label_studio_project_id, // Will be replaced with actual name when available
      labelStudioProjectId: project.label_studio_project_id,
      syncStatus: 'synced' as const,
      lastSyncAt: project.updated_at,
      totalTasks: 0, // Will be fetched from Label Studio
      completedTasks: 0,
      annotators: 0,
      workspaceId: project.workspace_id,
    }));
  }, [workspaceProjectsData]);

  // Merge workspace projects with mock data or use only workspace projects
  useEffect(() => {
    if (selectedWorkspaceId && workspaceProjectsData?.items) {
      // Use workspace projects when a workspace is selected
      setSyncStatus(workspaceProjectsAsSyncStatus);
    } else if (!selectedWorkspaceId) {
      // Use mock data when no workspace is selected
      setSyncStatus(mockSyncStatus);
    }
    setSyncLogs(mockSyncLogs);
  }, [selectedWorkspaceId, workspaceProjectsData, workspaceProjectsAsSyncStatus]);

  // Auto sync functionality
  useEffect(() => {
    if (!autoSync) return;

    const interval = setInterval(() => {
      handleSyncAll();
    }, syncInterval);

    return () => clearInterval(interval);
  }, [autoSync, syncInterval]);

  // Sync single project
  const handleSyncProject = useCallback(async (projId: string) => {
    setIsSyncing(true);
    
    // Update status to syncing
    setSyncStatus(prev => prev.map(p => 
      p.projectId === projId ? { ...p, syncStatus: 'syncing' as const } : p
    ));

    // Simulate sync process
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Update status to synced
    setSyncStatus(prev => prev.map(p => 
      p.projectId === projId ? { 
        ...p, 
        syncStatus: 'synced' as const,
        lastSyncAt: new Date().toISOString(),
      } : p
    ));

    // Add sync log
    const newLog: SyncLog = {
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString(),
      action: 'sync_complete',
      status: 'success',
      message: `项目 ${projId} 同步完成`,
    };
    setSyncLogs(prev => [newLog, ...prev]);

    setIsSyncing(false);
    setLastSyncTime(new Date());
    message.success(t('sync.syncSuccess') || 'Sync completed successfully');

    const updatedProject = syncStatus.find(p => p.projectId === projId);
    if (updatedProject) {
      onSyncComplete?.(updatedProject);
    }
  }, [syncStatus, onSyncComplete, t]);

  // Sync all projects
  const handleSyncAll = useCallback(async () => {
    setIsSyncing(true);
    
    for (const project of syncStatus) {
      await handleSyncProject(project.projectId);
    }

    setIsSyncing(false);
    setLastSyncTime(new Date());
  }, [syncStatus, handleSyncProject]);

  // Get status config
  const getStatusConfig = (status: ProjectSyncStatus['syncStatus']) => {
    switch (status) {
      case 'synced':
        return { color: 'success', icon: <CheckCircleOutlined />, text: t('sync.synced') || 'Synced' };
      case 'syncing':
        return { color: 'processing', icon: <SyncOutlined spin />, text: t('sync.syncing') || 'Syncing' };
      case 'pending':
        return { color: 'warning', icon: <ClockCircleOutlined />, text: t('sync.pending') || 'Pending' };
      case 'error':
        return { color: 'error', icon: <ExclamationCircleOutlined />, text: t('sync.error') || 'Error' };
      default:
        return { color: 'default', icon: <ClockCircleOutlined />, text: status };
    }
  };

  const columns = [
    {
      title: t('sync.projectName') || 'Project Name',
      dataIndex: 'projectName',
      key: 'projectName',
      render: (text: string, record: ProjectSyncStatus) => (
        <Space>
          <FileTextOutlined />
          <span>{text}</span>
          <Tag>{record.labelStudioProjectId}</Tag>
        </Space>
      ),
    },
    {
      title: t('sync.status') || 'Status',
      dataIndex: 'syncStatus',
      key: 'syncStatus',
      render: (status: ProjectSyncStatus['syncStatus'], record: ProjectSyncStatus) => {
        const config = getStatusConfig(status);
        return (
          <Tooltip title={record.errorMessage}>
            <Tag color={config.color} icon={config.icon}>
              {config.text}
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: t('sync.progress') || 'Progress',
      key: 'progress',
      render: (_: unknown, record: ProjectSyncStatus) => {
        const percent = record.totalTasks > 0
          ? Math.round((record.completedTasks / record.totalTasks) * 100)
          : 0;
        return (
          <Progress
            percent={percent}
            size="small"
            status={record.syncStatus === 'error' ? 'exception' : 'active'}
          />
        );
      },
    },
    {
      title: t('sync.annotators') || 'Annotators',
      dataIndex: 'annotators',
      key: 'annotators',
      render: (count: number) => (
        <Space>
          <UserOutlined />
          <span>{count}</span>
        </Space>
      ),
    },
    {
      title: t('sync.lastSync') || 'Last Sync',
      dataIndex: 'lastSyncAt',
      key: 'lastSyncAt',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: t('common.actions') || 'Actions',
      key: 'actions',
      render: (_: unknown, record: ProjectSyncStatus) => (
        <Button
          type="link"
          icon={<SyncOutlined />}
          onClick={() => handleSyncProject(record.projectId)}
          loading={record.syncStatus === 'syncing'}
          disabled={isSyncing && record.syncStatus !== 'syncing'}
        >
          {t('sync.syncNow') || 'Sync Now'}
        </Button>
      ),
    },
  ];

  // Calculate summary stats
  const totalProjects = syncStatus.length;
  const syncedProjects = syncStatus.filter(p => p.syncStatus === 'synced').length;
  const errorProjects = syncStatus.filter(p => p.syncStatus === 'error').length;
  const totalTasks = syncStatus.reduce((sum, p) => sum + p.totalTasks, 0);
  const completedTasks = syncStatus.reduce((sum, p) => sum + p.completedTasks, 0);

  return (
    <div>
      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('sync.totalProjects') || 'Total Projects'}
              value={totalProjects}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('sync.syncedProjects') || 'Synced Projects'}
              value={syncedProjects}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
              suffix={`/ ${totalProjects}`}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('sync.completedTasks') || 'Completed Tasks'}
              value={completedTasks}
              prefix={<CloudSyncOutlined />}
              suffix={`/ ${totalTasks}`}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('sync.errorProjects') || 'Error Projects'}
              value={errorProjects}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: errorProjects > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Workspace Filter */}
      {showWorkspaceSelector && (
        <Card style={{ marginBottom: 16 }}>
          <Space size="middle" wrap>
            <Space>
              <FilterOutlined style={{ color: '#1890ff' }} />
              <span>{t('workspace.filterByWorkspace', 'Filter by Workspace')}:</span>
            </Space>
            <LSWorkspaceSelector
              value={selectedWorkspaceId}
              onChange={handleWorkspaceChange}
              size="middle"
              allowClear
              placeholder={t('workspace.allWorkspaces', 'All workspaces')}
              showCreateButton={false}
            />
            {selectedWorkspace && (
              <Tag color="blue">
                {selectedWorkspace.name}
                {selectedWorkspace.project_count > 0 && (
                  <span> ({selectedWorkspace.project_count} {t('workspace.projects', 'projects')})</span>
                )}
              </Tag>
            )}
          </Space>
        </Card>
      )}

      {/* Sync Controls */}
      <Card
        title={
          <Space>
            <span>{t('sync.projectSync') || 'Project Synchronization'}</span>
            {selectedWorkspace && (
              <Tag color="processing">{selectedWorkspace.name}</Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            {lastSyncTime && (
              <span style={{ color: '#999', fontSize: 12 }}>
                {t('sync.lastSyncTime') || 'Last sync'}: {lastSyncTime.toLocaleTimeString()}
              </span>
            )}
            {selectedWorkspaceId && (
              <Button
                icon={<ReloadOutlined />}
                onClick={() => refetchWorkspaceProjects()}
                loading={isLoadingWorkspaceProjects}
              >
                {t('common.refresh', 'Refresh')}
              </Button>
            )}
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={handleSyncAll}
              loading={isSyncing}
              disabled={syncStatus.length === 0}
            >
              {t('sync.syncAll') || 'Sync All'}
            </Button>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {isLoadingWorkspaceProjects ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <SyncOutlined spin style={{ fontSize: 24, color: '#1890ff' }} />
            <p style={{ marginTop: 16, color: '#666' }}>
              {t('workspace.loadingProjects', 'Loading workspace projects...')}
            </p>
          </div>
        ) : syncStatus.length === 0 ? (
          <Empty
            description={
              selectedWorkspaceId
                ? t('workspace.noProjectsInWorkspace', 'No projects in this workspace')
                : t('sync.noProjects', 'No projects available')
            }
          />
        ) : (
          <Table
            dataSource={syncStatus}
            columns={columns}
            rowKey="projectId"
            pagination={false}
          />
        )}
      </Card>

      {/* Sync Logs */}
      <Card title={t('sync.syncLogs') || 'Sync Logs'}>
        {syncLogs.length === 0 ? (
          <Alert
            type="info"
            message={t('sync.noLogs') || 'No sync logs available'}
            showIcon
          />
        ) : (
          <Table
            dataSource={syncLogs.slice(0, 10)}
            columns={[
              {
                title: t('sync.time') || 'Time',
                dataIndex: 'timestamp',
                key: 'timestamp',
                render: (date: string) => new Date(date).toLocaleString(),
                width: 180,
              },
              {
                title: t('sync.action') || 'Action',
                dataIndex: 'action',
                key: 'action',
                render: (action: string) => (
                  <Tag>{action.replace('_', ' ').toUpperCase()}</Tag>
                ),
                width: 150,
              },
              {
                title: t('sync.statusLabel') || 'Status',
                dataIndex: 'status',
                key: 'status',
                render: (status: string) => (
                  <Badge
                    status={status === 'success' ? 'success' : status === 'error' ? 'error' : 'warning'}
                    text={status}
                  />
                ),
                width: 100,
              },
              {
                title: t('sync.message') || 'Message',
                dataIndex: 'message',
                key: 'message',
              },
            ]}
            rowKey="id"
            pagination={false}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default ProjectSync;
