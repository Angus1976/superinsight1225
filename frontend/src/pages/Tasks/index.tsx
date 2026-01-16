// Tasks list page
import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProTable, type ProColumns, type ActionType } from '@ant-design/pro-components';
import { 
  Button, 
  Tag, 
  Space, 
  Modal, 
  Progress, 
  Dropdown, 
  message, 
  Select,
  Input,
  DatePicker,
  Tooltip,
  Badge,
  Card,
  Statistic,
  Row,
  Col
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  MoreOutlined,
  ExclamationCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  TagOutlined,
  UserOutlined,
  CalendarOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTasks, useDeleteTask, useBatchDeleteTasks, useUpdateTask, useTaskStats } from '@/hooks/useTask';
import { TaskCreateModal } from './TaskCreateModal';
import type { Task, TaskStatus, TaskPriority } from '@/types';

const statusColorMap: Record<TaskStatus, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  cancelled: 'error',
};

const priorityColorMap: Record<TaskPriority, string> = {
  low: 'green',
  medium: 'blue',
  high: 'orange',
  urgent: 'red',
};

const TasksPage: React.FC = () => {
  const { t } = useTranslation(['tasks', 'common']);
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [currentParams, setCurrentParams] = useState({});
  const [batchAction, setBatchAction] = useState<string>('');

  const { data, isLoading, refetch } = useTasks(currentParams);
  const { data: stats } = useTaskStats();
  const deleteTask = useDeleteTask();
  const batchDeleteTasks = useBatchDeleteTasks();
  const updateTask = useUpdateTask();

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: t('delete'),
      icon: <ExclamationCircleOutlined />,
      content: t('confirmDeleteTask'),
      okText: t('confirm'),
      cancelText: t('cancel'),
      okType: 'danger',
      onOk: async () => {
        await deleteTask.mutateAsync(id);
        refetch();
      },
    });
  };

  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('selectTasksToDelete'));
      return;
    }
    Modal.confirm({
      title: t('deleteTasks'),
      icon: <ExclamationCircleOutlined />,
      content: t('confirmDeleteTasks', { count: selectedRowKeys.length }),
      okType: 'danger',
      onOk: async () => {
        await batchDeleteTasks.mutateAsync(selectedRowKeys);
        setSelectedRowKeys([]);
        refetch();
      },
    });
  };

  const handleBatchStatusUpdate = async (status: TaskStatus) => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('selectTasksToUpdate'));
      return;
    }
    
    try {
      // Update each selected task
      await Promise.all(
        selectedRowKeys.map(id => 
          updateTask.mutateAsync({ id, payload: { status } })
        )
      );
      setSelectedRowKeys([]);
      refetch();
      message.success(t('batchUpdateSuccess'));
    } catch (error) {
      message.error(t('batchUpdateError'));
    }
  };

  const handleExportTasks = () => {
    // Export selected tasks or all tasks
    const tasksToExport = selectedRowKeys.length > 0 
      ? (data?.items || mockTasks).filter(task => selectedRowKeys.includes(task.id))
      : (data?.items || mockTasks);
    
    const csvContent = [
      ['ID', 'Name', 'Status', 'Priority', 'Assignee', 'Progress', 'Created', 'Due Date'].join(','),
      ...tasksToExport.map(task => [
        task.id,
        `"${task.name}"`,
        task.status,
        task.priority,
        task.assignee_name || '',
        `${task.progress}%`,
        new Date(task.created_at).toLocaleDateString(),
        task.due_date ? new Date(task.due_date).toLocaleDateString() : ''
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tasks_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    message.success(t('exportSuccess'));
  };

  const columns: ProColumns<Task>[] = [
    {
      title: t('taskName'),
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => navigate(`/tasks/${record.id}`)}>{record.name}</a>
          {record.tags && record.tags.length > 0 && (
            <Space size={4}>
              {record.tags.slice(0, 2).map(tag => (
                <Tag key={tag} size="small" icon={<TagOutlined />}>
                  {tag}
                </Tag>
              ))}
              {record.tags.length > 2 && (
                <Tooltip title={record.tags.slice(2).join(', ')}>
                  <Tag size="small">+{record.tags.length - 2}</Tag>
                </Tooltip>
              )}
            </Space>
          )}
        </Space>
      ),
    },
    {
      title: t('status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      valueType: 'select',
      valueEnum: {
        pending: { text: t('statusPending'), status: 'Default' },
        in_progress: { text: t('statusInProgress'), status: 'Processing' },
        completed: { text: t('statusCompleted'), status: 'Success' },
        cancelled: { text: t('statusCancelled'), status: 'Error' },
      },
      render: (_, record) => {
        const statusConfig = {
          pending: { color: 'default', icon: <CalendarOutlined /> },
          in_progress: { color: 'processing', icon: <PlayCircleOutlined /> },
          completed: { color: 'success', icon: <CheckCircleOutlined /> },
          cancelled: { color: 'error', icon: <CloseCircleOutlined /> },
        };
        const statusKeyMap: Record<TaskStatus, string> = {
          pending: 'statusPending',
          in_progress: 'statusInProgress',
          completed: 'statusCompleted',
          cancelled: 'statusCancelled',
        };
        const config = statusConfig[record.status];
        return (
          <Tag color={config.color} icon={config.icon}>
            {t(statusKeyMap[record.status])}
          </Tag>
        );
      },
    },
    {
      title: t('priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      valueType: 'select',
      valueEnum: {
        low: { text: t('priorityLow') },
        medium: { text: t('priorityMedium') },
        high: { text: t('priorityHigh') },
        urgent: { text: t('priorityUrgent') },
      },
      render: (_, record) => {
        const priorityConfig = {
          low: { color: 'green', text: t('priorityLow') },
          medium: { color: 'blue', text: t('priorityMedium') },
          high: { color: 'orange', text: t('priorityHigh') },
          urgent: { color: 'red', text: t('priorityUrgent') },
        };
        const config = priorityConfig[record.priority];
        return <Tag color={config.color}>{config.text}</Tag>;
      },
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
          text_classification: 'typeTextClassification',
          ner: 'typeNER',
          sentiment: 'typeSentiment',
          qa: 'typeQA',
          custom: 'typeCustom',
        };
        return (
          <Tag color="blue">
            {t(typeKeyMap[record.annotation_type] || 'typeCustom')}
          </Tag>
        );
      },
    },
    {
      title: t('progress'),
      dataIndex: 'progress',
      key: 'progress',
      width: 180,
      search: false,
      sorter: true,
      render: (_, record) => (
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Progress
            percent={record.progress}
            size="small"
            status={record.status === 'completed' ? 'success' : 'active'}
            strokeColor={
              record.progress >= 80 ? '#52c41a' :
              record.progress >= 50 ? '#1890ff' :
              record.progress >= 20 ? '#faad14' : '#ff4d4f'
            }
          />
          <Space size={4}>
            <span style={{ fontSize: 12, color: '#999' }}>
              {record.completed_items} / {record.total_items}
            </span>
            <Badge 
              count={record.progress} 
              showZero 
              style={{ backgroundColor: '#52c41a' }}
              size="small"
            />
          </Space>
        </Space>
      ),
    },
    {
      title: t('assignee'),
      dataIndex: 'assignee_name',
      key: 'assignee_name',
      width: 120,
      ellipsis: true,
      render: (text, record) => (
        <Space>
          <UserOutlined style={{ color: '#1890ff' }} />
          <span>{text || t('unassigned')}</span>
        </Space>
      ),
    },
    {
      title: t('dueDate'),
      dataIndex: 'due_date',
      key: 'due_date',
      width: 120,
      valueType: 'date',
      sorter: true,
      render: (_, record) => {
        if (!record.due_date) return <span style={{ color: '#999' }}>-</span>;
        const dueDate = new Date(record.due_date);
        const isOverdue = dueDate < new Date() && record.status !== 'completed';
        const isNearDue = dueDate.getTime() - Date.now() < 3 * 24 * 60 * 60 * 1000; // 3 days
        
        return (
          <Space>
            <CalendarOutlined style={{ 
              color: isOverdue ? '#ff4d4f' : isNearDue ? '#faad14' : '#1890ff' 
            }} />
            <span style={{ 
              color: isOverdue ? '#ff4d4f' : isNearDue ? '#faad14' : undefined 
            }}>
              {dueDate.toLocaleDateString()}
            </span>
            {isOverdue && <Badge status="error" text={t('overdue')} />}
            {isNearDue && !isOverdue && <Badge status="warning" text={t('nearDue')} />}
          </Space>
        );
      },
    },
    {
      title: t('created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      valueType: 'date',
      search: false,
      sorter: true,
      render: (_, record) => (
        <Tooltip title={new Date(record.created_at).toLocaleString()}>
          {new Date(record.created_at).toLocaleDateString()}
        </Tooltip>
      ),
    },
    {
      title: t('actions'),
      key: 'actions',
      width: 120,
      fixed: 'right',
      search: false,
      render: (_, record) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: t('view'),
                onClick: () => navigate(`/tasks/${record.id}`),
              },
              {
                key: 'annotate',
                icon: <EditOutlined />,
                label: t('annotateAction'),
                onClick: () => navigate(`/tasks/${record.id}/annotate`),
                disabled: record.status === 'completed',
              },
              {
                key: 'edit',
                icon: <EditOutlined />,
                label: t('edit'),
                onClick: () => navigate(`/tasks/${record.id}/edit`),
              },
              { type: 'divider' },
              {
                key: 'start',
                icon: <PlayCircleOutlined />,
                label: t('start'),
                onClick: () => updateTask.mutateAsync({ 
                  id: record.id, 
                  payload: { status: 'in_progress' } 
                }),
                disabled: record.status !== 'pending',
              },
              {
                key: 'complete',
                icon: <CheckCircleOutlined />,
                label: t('complete'),
                onClick: () => updateTask.mutateAsync({ 
                  id: record.id, 
                  payload: { status: 'completed' } 
                }),
                disabled: record.status !== 'in_progress',
              },
              {
                key: 'pause',
                icon: <PauseCircleOutlined />,
                label: t('pause'),
                onClick: () => updateTask.mutateAsync({ 
                  id: record.id, 
                  payload: { status: 'pending' } 
                }),
                disabled: record.status !== 'in_progress',
              },
              { type: 'divider' },
              {
                key: 'delete',
                icon: <DeleteOutlined />,
                label: t('delete'),
                danger: true,
                onClick: () => handleDelete(record.id),
              },
            ],
          }}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  // Mock data for development
  const mockTasks: Task[] = [
    {
      id: '1',
      name: 'Customer Review Classification',
      description: 'Classify customer reviews by sentiment',
      status: 'in_progress',
      priority: 'high',
      annotation_type: 'sentiment',
      assignee_id: 'user1',
      assignee_name: 'John Doe',
      created_by: 'admin',
      created_at: '2025-01-15T10:00:00Z',
      updated_at: '2025-01-20T14:30:00Z',
      due_date: '2025-02-01T00:00:00Z',
      progress: 65,
      total_items: 1000,
      completed_items: 650,
      tenant_id: 'tenant1',
      tags: ['urgent', 'customer'],
    },
    {
      id: '2',
      name: 'Product Entity Recognition',
      description: 'Identify product names and attributes',
      status: 'pending',
      priority: 'medium',
      annotation_type: 'ner',
      created_by: 'admin',
      created_at: '2025-01-18T09:00:00Z',
      updated_at: '2025-01-18T09:00:00Z',
      due_date: '2025-02-15T00:00:00Z',
      progress: 0,
      total_items: 500,
      completed_items: 0,
      tenant_id: 'tenant1',
      tags: ['product'],
    },
    {
      id: '3',
      name: 'FAQ Classification',
      description: 'Categorize FAQ questions',
      status: 'completed',
      priority: 'low',
      annotation_type: 'text_classification',
      assignee_id: 'user2',
      assignee_name: 'Jane Smith',
      created_by: 'admin',
      created_at: '2025-01-10T08:00:00Z',
      updated_at: '2025-01-19T16:00:00Z',
      progress: 100,
      total_items: 200,
      completed_items: 200,
      tenant_id: 'tenant1',
    },
  ];

  return (
    <>
      {/* Statistics Cards */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('totalTasks')}
                value={stats.total}
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('inProgress')}
                value={stats.in_progress}
                prefix={<PlayCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('completed')}
                value={stats.completed}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('overdue')}
                value={stats.overdue}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <ProTable<Task>
        headerTitle={t('annotationTasks')}
        actionRef={actionRef}
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={data?.items || mockTasks}
        scroll={{ x: 1400 }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
          searchText: t('search'),
          resetText: t('reset'),
          collapseRender: (collapsed) => (
            <Button
              type="link"
              icon={<FilterOutlined />}
            >
              {collapsed ? t('expandFilters') : t('collapseFilters')}
            </Button>
          ),
        }}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => 
            t('paginationTotal', { 
              start: range[0], 
              end: range[1], 
              total 
            }),
          total: data?.total || mockTasks.length,
        }}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
          selections: [
            {
              key: 'all',
              text: t('selectAll'),
              onSelect: () => {
                setSelectedRowKeys((data?.items || mockTasks).map(item => item.id));
              },
            },
            {
              key: 'invert',
              text: t('invertSelection'),
              onSelect: () => {
                const allKeys = (data?.items || mockTasks).map(item => item.id);
                setSelectedRowKeys(allKeys.filter(key => !selectedRowKeys.includes(key)));
              },
            },
            {
              key: 'none',
              text: t('selectNone'),
              onSelect: () => {
                setSelectedRowKeys([]);
              },
            },
          ],
        }}
        toolBarRender={() => [
          selectedRowKeys.length > 0 && (
            <Dropdown
              key="batchActions"
              menu={{
                items: [
                  {
                    key: 'batchStart',
                    icon: <PlayCircleOutlined />,
                    label: t('batchStart'),
                    onClick: () => handleBatchStatusUpdate('in_progress'),
                  },
                  {
                    key: 'batchComplete',
                    icon: <CheckCircleOutlined />,
                    label: t('batchComplete'),
                    onClick: () => handleBatchStatusUpdate('completed'),
                  },
                  {
                    key: 'batchPause',
                    icon: <PauseCircleOutlined />,
                    label: t('batchPause'),
                    onClick: () => handleBatchStatusUpdate('pending'),
                  },
                  { type: 'divider' },
                  {
                    key: 'batchDelete',
                    icon: <DeleteOutlined />,
                    label: t('batchDelete'),
                    danger: true,
                    onClick: handleBatchDelete,
                  },
                ],
              }}
            >
              <Button icon={<MoreOutlined />}>
                {t('batchActions')} ({selectedRowKeys.length})
              </Button>
            </Dropdown>
          ),
          <Button
            key="export"
            icon={<DownloadOutlined />}
            onClick={handleExportTasks}
          >
            {selectedRowKeys.length > 0 
              ? t('exportSelected', { count: selectedRowKeys.length })
              : t('exportAll')
            }
          </Button>,
          <Button
            key="refresh"
            icon={<ReloadOutlined />}
            onClick={() => {
              refetch();
              actionRef.current?.reload();
            }}
          >
            {t('refresh')}
          </Button>,
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            {t('createTask')}
          </Button>,
        ]}
        onSubmit={(params) => {
          setCurrentParams(params);
        }}
        onReset={() => {
          setCurrentParams({});
        }}
        tableAlertRender={({ selectedRowKeys, onCleanSelected }) => (
          <Space size={24}>
            <span>
              {t('selectedItems', { count: selectedRowKeys.length })}
              <a style={{ marginLeft: 8 }} onClick={onCleanSelected}>
                {t('clearSelection')}
              </a>
            </span>
          </Space>
        )}
        tableAlertOptionRender={({ selectedRowKeys }) => (
          <Space size={16}>
            <a onClick={() => handleBatchStatusUpdate('in_progress')}>
              {t('batchStart')}
            </a>
            <a onClick={() => handleBatchStatusUpdate('completed')}>
              {t('batchComplete')}
            </a>
            <a onClick={handleBatchDelete} style={{ color: '#ff4d4f' }}>
              {t('batchDelete')}
            </a>
          </Space>
        )}
      />

      <TaskCreateModal
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onSuccess={() => {
          setCreateModalOpen(false);
          refetch();
        }}
      />
    </>
  );
};

export default TasksPage;
