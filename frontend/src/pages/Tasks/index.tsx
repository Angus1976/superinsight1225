// Tasks list page - redesigned with status tabs, clean batch actions, click-to-detail
import { useState, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProTable, type ProColumns, type ActionType } from '@ant-design/pro-components';
import {
  Button, Tag, Space, App, Progress, Dropdown, Tooltip, Badge,
  Card, Statistic, Row, Col, Modal, Tabs,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined, EyeOutlined, MoreOutlined,
  ExclamationCircleOutlined, FilterOutlined, ReloadOutlined, DownloadOutlined,
  UploadOutlined, PlayCircleOutlined, PauseCircleOutlined, CheckCircleOutlined,
  CloseCircleOutlined, CalendarOutlined, BarChartOutlined, SyncOutlined,
  DisconnectOutlined, ClockCircleOutlined, UserOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTasks, useUpdateTask, useTaskStats } from '@/hooks/useTask';
import { usePermissions } from '@/hooks/usePermissions';
import { HelpPopover, HelpIcon } from '@/components/SmartHelp';
import { TaskCreateModal } from './TaskCreateModal';
import { TaskEditModal } from './TaskEditModal';
import { TaskImportModal } from './TaskImportModal';
import { BatchEditModal } from './BatchEditModal';
import { TaskDeleteModal } from './TaskDeleteModal';
import { ExportOptionsModal } from '@/components/Tasks';
import { useLabelStudioSync } from './hooks/useLabelStudioSync';
import { useTaskExport } from './hooks/useTaskExport';
import type { Task, TaskStatus, TaskPriority } from '@/types';

const statusColorMap: Record<TaskStatus, string> = {
  pending: 'default', in_progress: 'processing', completed: 'success', cancelled: 'error',
};
const priorityColorMap: Record<TaskPriority, string> = {
  low: 'green', medium: 'blue', high: 'orange', urgent: 'red',
};
const statusIconMap: Record<TaskStatus, React.ReactNode> = {
  pending: <CalendarOutlined />, in_progress: <PlayCircleOutlined />,
  completed: <CheckCircleOutlined />, cancelled: <CloseCircleOutlined />,
};

const TasksPage: React.FC = () => {
  const { t } = useTranslation(['tasks', 'common']);
  const navigate = useNavigate();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>(null);

  // State
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTaskId, setEditTaskId] = useState<string | null>(null);
  const [batchEditModalOpen, setBatchEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [tasksToDelete, setTasksToDelete] = useState<Task[]>([]);
  const [currentParams, setCurrentParams] = useState({});

  // Permissions
  const { task: taskPerms } = usePermissions();

  // Data
  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = { ...currentParams };
    if (activeTab !== 'all') params.status = activeTab;
    return params;
  }, [currentParams, activeTab]);

  const { data, isLoading, refetch } = useTasks(queryParams);
  const { data: stats } = useTaskStats();
  const updateTask = useUpdateTask();

  // Extracted hooks
  const { syncProgress, syncModalOpen, setSyncModalOpen, resetSyncState, handleSyncSingleTask, handleSyncAllTasks } =
    useLabelStudioSync(updateTask.mutateAsync, refetch);
  const { exportModalOpen, setExportModalOpen, exportLoading, handleExportWithOptions } =
    useTaskExport();

  const items = data?.items || [];

  // Handlers
  const handleDelete = useCallback((id: string) => {
    const task = items.find(t => t.id === id);
    if (task) { setTasksToDelete([task]); setDeleteModalOpen(true); }
  }, [items]);

  const handleBatchDelete = useCallback(() => {
    if (!selectedRowKeys.length) { message.warning(t('selectTasksToDelete')); return; }
    setTasksToDelete(items.filter(task => selectedRowKeys.includes(task.id)));
    setDeleteModalOpen(true);
  }, [selectedRowKeys, items, message, t]);

  const handleBatchStatusUpdate = useCallback(async (status: TaskStatus) => {
    if (!selectedRowKeys.length) { message.warning(t('selectTasksToUpdate')); return; }
    try {
      await Promise.all(selectedRowKeys.map(id => updateTask.mutateAsync({ id, payload: { status } })));
      setSelectedRowKeys([]);
      refetch();
      message.success(t('batchUpdateSuccess'));
    } catch { message.error(t('batchUpdateError')); }
  }, [selectedRowKeys, updateTask, refetch, message, t]);

  const handleDeleteSuccess = useCallback((deletedIds: string[]) => {
    setDeleteModalOpen(false);
    setTasksToDelete([]);
    if (deletedIds.length > 1) setSelectedRowKeys(prev => prev.filter(id => !deletedIds.includes(id)));
    refetch();
    message.success(t('delete.result.success', { count: deletedIds.length }));
  }, [refetch, message, t]);

  const selectedTasks = useMemo(
    () => items.filter(task => selectedRowKeys.includes(task.id)),
    [items, selectedRowKeys]
  );

  // Column definitions
  const columns: ProColumns<Task>[] = useMemo(() => [
    {
      title: t('columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: 260,
      ellipsis: true,
      fixed: 'left',
      render: (_, record) => (
        <a onClick={() => navigate(`/tasks/${record.id}`)} style={{ fontWeight: 500 }}>
          {record.name}
        </a>
      ),
    },
    {
      title: t('columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      hideInSearch: activeTab !== 'all',
      valueType: 'select',
      valueEnum: {
        pending: { text: t('statusPending'), status: 'Default' },
        in_progress: { text: t('statusInProgress'), status: 'Processing' },
        completed: { text: t('statusCompleted'), status: 'Success' },
        cancelled: { text: t('statusCancelled'), status: 'Error' },
      },
      render: (_, record) => (
        <Tag color={statusColorMap[record.status]} icon={statusIconMap[record.status]}>
          {t(`status.${record.status === 'in_progress' ? 'inProgress' : record.status}`)}
        </Tag>
      ),
    },
    {
      title: t('columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      valueType: 'select',
      valueEnum: {
        low: { text: t('priorityLow') }, medium: { text: t('priorityMedium') },
        high: { text: t('priorityHigh') }, urgent: { text: t('priorityUrgent') },
      },
      render: (_, record) => (
        <Tag color={priorityColorMap[record.priority]}>{t(`priority.${record.priority}`)}</Tag>
      ),
    },
    {
      title: t('annotationType'),
      dataIndex: 'annotation_type',
      key: 'annotation_type',
      width: 150,
      valueType: 'select',
      valueEnum: {
        text_classification: { text: t('typeTextClassification') },
        ner: { text: t('typeNER') },
        sentiment: { text: t('typeSentiment') },
        qa: { text: t('typeQA') },
        custom: { text: t('typeCustom') },
      },
      render: (_, record) => {
        const typeKeyMap: Record<string, string> = {
          text_classification: 'typeTextClassification', ner: 'typeNER',
          sentiment: 'typeSentiment', qa: 'typeQA', custom: 'typeCustom',
        };
        return <Tag color="blue">{t(typeKeyMap[record.annotation_type] || 'typeCustom')}</Tag>;
      },
    },
    {
      title: t('columns.progress'),
      dataIndex: 'progress',
      key: 'progress',
      width: 200,
      search: false,
      sorter: true,
      render: (_, record) => {
        const percent = Math.round(record.progress || 0);
        return (
          <div style={{ minWidth: 150 }}>
            <Progress
              percent={percent}
              size="small"
              status={record.status === 'completed' ? 'success' : 'active'}
              strokeColor={
                percent >= 80 ? '#52c41a' : percent >= 50 ? '#1890ff' :
                percent >= 20 ? '#faad14' : '#ff4d4f'
              }
              showInfo={false}
            />
            <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
              {record.completed_items || 0} / {record.total_items || 0}
            </div>
          </div>
        );
      },
    },
    {
      title: t('assignee'),
      dataIndex: 'assignee_name',
      key: 'assignee_name',
      width: 120,
      ellipsis: true,
      render: (text) => (
        <Space><UserOutlined style={{ color: '#1890ff' }} /><span>{text || t('unassigned')}</span></Space>
      ),
    },
    {
      title: t('dueDate'),
      dataIndex: 'due_date',
      key: 'due_date',
      width: 130,
      valueType: 'date',
      sorter: true,
      render: (_, record) => {
        if (!record.due_date) return <span style={{ color: '#999' }}>-</span>;
        const dueDate = new Date(record.due_date);
        const isOverdue = dueDate < new Date() && record.status !== 'completed';
        const isNearDue = dueDate.getTime() - Date.now() < 3 * 24 * 60 * 60 * 1000;
        const color = isOverdue ? '#ff4d4f' : isNearDue ? '#faad14' : undefined;
        return (
          <Space>
            <CalendarOutlined style={{ color: color || '#1890ff' }} />
            <span style={{ color }}>{dueDate.toLocaleDateString()}</span>
            {isOverdue && <Badge status="error" />}
          </Space>
        );
      },
    },

    {
      title: t('syncStatus'),
      dataIndex: 'label_studio_sync_status',
      key: 'label_studio_sync_status',
      width: 140,
      search: false,
      render: (_, record) => {
        const hasProjectId = !!record.label_studio_project_id;
        if (!hasProjectId) {
          return <Tag color="default" icon={<DisconnectOutlined />}>{t('syncStatusNotLinked')}</Tag>;
        }
        const configMap: Record<string, { icon: React.ReactNode; color: string; text: string }> = {
          synced: { icon: <CheckCircleOutlined />, color: 'success', text: t('syncStatusSynced') },
          pending: { icon: <ClockCircleOutlined />, color: 'warning', text: t('syncStatusPending') },
          failed: { icon: <ExclamationCircleOutlined />, color: 'error', text: t('syncStatusFailed') },
        };
        const cfg = configMap[record.label_studio_sync_status || ''] ||
          { icon: <ClockCircleOutlined />, color: 'default', text: t('syncStatusNotSynced') };
        return (
          <Space size={4}>
            <Tag color={cfg.color} icon={cfg.icon}>{cfg.text}</Tag>
            <Tooltip title={t('syncSingleTask')}>
              <Button type="text" size="small" icon={<SyncOutlined />}
                onClick={(e) => { e.stopPropagation(); handleSyncSingleTask(record); }}
                style={{ padding: '0 4px' }} />
            </Tooltip>
          </Space>
        );
      },
    },
    {
      title: t('columns.actions'),
      key: 'actions',
      width: 80,
      fixed: 'right',
      search: false,
      render: (_, record) => (
        <Dropdown menu={{
          items: [
            { key: 'view', icon: <EyeOutlined />, label: t('view'), onClick: () => navigate(`/tasks/${record.id}`) },
            { key: 'edit', icon: <EditOutlined />, label: t('editAction'), onClick: () => { setEditTaskId(record.id); setEditModalOpen(true); } },
            { type: 'divider' as const },
            { key: 'start', icon: <PlayCircleOutlined />, label: t('start'),
              onClick: () => updateTask.mutateAsync({ id: record.id, payload: { status: 'in_progress' as const } }),
              disabled: record.status !== 'pending' },
            { key: 'complete', icon: <CheckCircleOutlined />, label: t('complete'),
              onClick: () => updateTask.mutateAsync({ id: record.id, payload: { status: 'completed' as const } }),
              disabled: record.status !== 'in_progress' },
            { key: 'pause', icon: <PauseCircleOutlined />, label: t('pause'),
              onClick: () => updateTask.mutateAsync({ id: record.id, payload: { status: 'pending' as const } }),
              disabled: record.status !== 'in_progress' },
            { type: 'divider' as const },
            { key: 'delete', icon: <DeleteOutlined />, label: t('deleteAction'), danger: true,
              onClick: () => handleDelete(record.id) },
          ],
        }}>
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ], [t, navigate, activeTab, handleDelete, handleSyncSingleTask, updateTask]);

  // Tab items with counts
  const tabItems = useMemo(() => [
    { key: 'all', label: <span>{t('tabs.all')} <Badge count={stats?.total || 0} showZero style={{ backgroundColor: '#1890ff' }} size="small" /></span> },
    { key: 'pending', label: <span>{t('tabs.pending')} <Badge count={stats?.pending || 0} showZero style={{ backgroundColor: '#d9d9d9', color: '#666' }} size="small" /></span> },
    { key: 'in_progress', label: <span>{t('tabs.inProgress')} <Badge count={stats?.in_progress || 0} showZero style={{ backgroundColor: '#52c41a' }} size="small" /></span> },
    { key: 'completed', label: <span>{t('tabs.completed')} <Badge count={stats?.completed || 0} showZero style={{ backgroundColor: '#52c41a' }} size="small" /></span> },
    { key: 'cancelled', label: <span>{t('tabs.cancelled')} <Badge count={stats?.cancelled || 0} showZero style={{ backgroundColor: '#ff4d4f' }} size="small" /></span> },
  ], [t, stats]);

  return (
    <>
      {/* Statistics Cards - clickable to filter table */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card
              size="small"
              hoverable
              style={{
                cursor: 'pointer',
                borderColor: activeTab === 'all' ? '#1890ff' : undefined,
                borderWidth: activeTab === 'all' ? 2 : 1,
              }}
              onClick={() => { setActiveTab('all'); setSelectedRowKeys([]); }}
            >
              <Statistic title={t('totalTasks')} value={stats.total} prefix={<BarChartOutlined />} valueStyle={{ color: '#1890ff' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card
              size="small"
              hoverable
              style={{
                cursor: 'pointer',
                borderColor: activeTab === 'in_progress' ? '#52c41a' : undefined,
                borderWidth: activeTab === 'in_progress' ? 2 : 1,
              }}
              onClick={() => { setActiveTab('in_progress'); setSelectedRowKeys([]); }}
            >
              <Statistic title={t('inProgress')} value={stats.in_progress} prefix={<PlayCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card
              size="small"
              hoverable
              style={{
                cursor: 'pointer',
                borderColor: activeTab === 'completed' ? '#52c41a' : undefined,
                borderWidth: activeTab === 'completed' ? 2 : 1,
              }}
              onClick={() => { setActiveTab('completed'); setSelectedRowKeys([]); }}
            >
              <Statistic title={t('completed')} value={stats.completed} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card
              size="small"
              hoverable
              style={{
                cursor: 'pointer',
                borderColor: activeTab === 'cancelled' ? '#ff4d4f' : undefined,
                borderWidth: activeTab === 'cancelled' ? 2 : 1,
              }}
              onClick={() => { setActiveTab('cancelled'); setSelectedRowKeys([]); }}
            >
              <Statistic title={t('statistics.cancelled')} value={stats.cancelled} prefix={<CloseCircleOutlined />} valueStyle={{ color: '#ff4d4f' }} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Status Tabs */}
      <Card bodyStyle={{ paddingBottom: 0 }} style={{ marginBottom: 16 }}>
        <Tabs activeKey={activeTab} onChange={(key) => { setActiveTab(key); setSelectedRowKeys([]); }} items={tabItems} />
      </Card>

      {/* Main Table */}
      <ProTable<Task>
        headerTitle={t('annotationTasks')}
        actionRef={actionRef}
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={items}
        scroll={{ x: 1400 }}
        options={{ density: true, fullScreen: false, reload: false, setting: true }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: true,
          searchText: t('search'),
          resetText: t('reset'),
          collapseRender: (collapsed) => (
            <Button type="link" icon={<FilterOutlined />}>
              {collapsed ? t('expandFilters') : t('collapseFilters')}
            </Button>
          ),
        }}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => t('paginationTotal', { start: range[0], end: range[1], total }),
          total: data?.total || 0,
        }}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
        }}
        toolBarRender={() => [
          selectedRowKeys.length > 0 && (
            <Dropdown key="batchActions" trigger={['click']} menu={{
              items: [
                { key: 'batchEdit', icon: <EditOutlined />, label: t('batchEdit.title'),
                  onClick: () => { if (!selectedRowKeys.length) { message.warning(t('selectTasksToUpdate')); return; } setBatchEditModalOpen(true); } },
                { type: 'divider' },
                { key: 'batchStart', icon: <PlayCircleOutlined />, label: t('batchStart'), onClick: () => handleBatchStatusUpdate('in_progress') },
                { key: 'batchComplete', icon: <CheckCircleOutlined />, label: t('batchComplete'), onClick: () => handleBatchStatusUpdate('completed') },
                { key: 'batchPause', icon: <PauseCircleOutlined />, label: t('batchPause'), onClick: () => handleBatchStatusUpdate('pending') },
                { type: 'divider' },
                { key: 'batchDelete', icon: <DeleteOutlined />, label: t('batchDelete'), danger: true, onClick: handleBatchDelete },
              ],
            }}>
              <Button type="primary" ghost icon={<MoreOutlined />}>
                {t('batchActions')} ({selectedRowKeys.length})
              </Button>
            </Dropdown>
          ),
          <Dropdown key="refresh" trigger={['click']} menu={{
            items: [
              { key: 'refreshList', icon: <ReloadOutlined />, label: t('refreshList'), onClick: () => { refetch(); actionRef.current?.reload(); } },
              { key: 'syncAll', icon: <SyncOutlined />, label: t('syncAllTasks'), onClick: () => handleSyncAllTasks(items) },
            ],
          }}>
            <Button icon={<ReloadOutlined />}>{t('refresh')}</Button>
          </Dropdown>,
          <HelpPopover helpKey="tasks.exportButton">
            <Button key="export" data-help-key="tasks.exportButton" icon={<DownloadOutlined />} onClick={() => setExportModalOpen(true)}>
              {selectedRowKeys.length > 0 ? t('exportSelected', { count: selectedRowKeys.length }) : t('exportAll')}
            </Button>
          </HelpPopover>,
          taskPerms.canCreate && (
            <Button key="import" icon={<UploadOutlined />} onClick={() => setImportModalOpen(true)}>
              {t('import.title')}
            </Button>
          ),
          taskPerms.canCreate && (
            <Button key="create" type="primary" icon={<PlusOutlined />} data-help-key="tasks.createButton" onClick={() => setCreateModalOpen(true)}>
              {t('createTask')}
            </Button>
          ),
          taskPerms.canCreate && (
            <HelpIcon key="createHelp" helpKey="tasks.createButton" size="small" />
          ),
        ]}
        onSubmit={(params) => setCurrentParams(params)}
        onReset={() => setCurrentParams({})}
        tableAlertRender={({ selectedRowKeys: keys, onCleanSelected }) => (
          <Space>
            <span>{t('selectedItems', { count: keys.length })}</span>
            <a onClick={onCleanSelected}>{t('clearSelection')}</a>
          </Space>
        )}
        tableAlertOptionRender={() => (
          <Space size={16}>
            <a onClick={() => handleBatchStatusUpdate('in_progress')}>{t('batchStart')}</a>
            <a onClick={() => handleBatchStatusUpdate('completed')}>{t('batchComplete')}</a>
            <a onClick={handleBatchDelete} style={{ color: '#ff4d4f' }}>{t('batchDelete')}</a>
          </Space>
        )}
      />

      {/* Modals */}
      <TaskCreateModal open={createModalOpen} onCancel={() => setCreateModalOpen(false)}
        onSuccess={() => { setCreateModalOpen(false); refetch(); }} />

      <TaskImportModal open={importModalOpen} onCancel={() => setImportModalOpen(false)}
        onSuccess={() => { setImportModalOpen(false); refetch(); }} />

      <ExportOptionsModal open={exportModalOpen} onCancel={() => setExportModalOpen(false)}
        onExport={(options) => handleExportWithOptions(options, items, selectedTasks)}
        selectedCount={selectedRowKeys.length} filteredCount={items.length}
        totalCount={data?.total || 0} loading={exportLoading} />

      <TaskEditModal open={editModalOpen} taskId={editTaskId}
        onCancel={() => { setEditModalOpen(false); setEditTaskId(null); }}
        onSuccess={() => { setEditModalOpen(false); setEditTaskId(null); refetch(); }} />

      <BatchEditModal open={batchEditModalOpen} tasks={selectedTasks}
        onCancel={() => setBatchEditModalOpen(false)}
        onSuccess={() => { setBatchEditModalOpen(false); setSelectedRowKeys([]); refetch(); }} />

      <TaskDeleteModal open={deleteModalOpen} tasks={tasksToDelete}
        onCancel={() => { setDeleteModalOpen(false); setTasksToDelete([]); }}
        onSuccess={handleDeleteSuccess} />

      {/* Sync Progress Modal */}
      <Modal
        title={<Space><SyncOutlined spin={syncProgress.status === 'syncing'} />{t('syncProgressTitle')}</Space>}
        open={syncModalOpen}
        onCancel={() => { if (syncProgress.status !== 'syncing') resetSyncState(); }}
        closable={syncProgress.status !== 'syncing'}
        maskClosable={syncProgress.status !== 'syncing'}
        footer={syncProgress.status === 'syncing' ? null : (
          <Button type="primary" onClick={resetSyncState}>{t('close')}</Button>
        )}
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          {syncProgress.total > 0 ? (
            <Progress type="circle"
              percent={Math.round((syncProgress.current / syncProgress.total) * 100)}
              status={syncProgress.status === 'error' ? 'exception' : syncProgress.status === 'completed' ? 'success' : 'active'}
              format={() => `${syncProgress.current}/${syncProgress.total}`} />
          ) : (
            <Progress type="circle"
              percent={syncProgress.status === 'completed' ? 100 : 0}
              status={syncProgress.status === 'completed' ? 'success' : 'active'} />
          )}
          <p style={{ marginTop: 16, color: '#666' }}>{syncProgress.message}</p>
        </div>
      </Modal>
    </>
  );
};

export default TasksPage;
