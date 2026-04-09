/**
 * TaskManagement Component
 * 
 * Displays annotation tasks with expandable rows, progress tracking, and action buttons.
 * Provides comprehensive task management with status filtering and assignment controls.
 * 
 * Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 19.3
 */

import React, { useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Progress,
  Tooltip,
  Modal,
  message,
  Typography,
  Descriptions,
} from 'antd';
import type { TableProps, TablePaginationConfig } from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  UserAddOutlined,
  StopOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AnnotationTask } from '@/services/dataLifecycle';

const { confirm } = Modal;
const { Text } = Typography;

// ============================================================================
// Types
// ============================================================================

export interface TaskManagementProps {
  tasks: AnnotationTask[];
  loading: boolean;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
  onViewDetails: (id: string) => void;
  onEdit: (id: string) => void;
  onAssign: (id: string) => void;
  onCancel: (id: string) => void;
  onPageChange: (page: number, pageSize: number) => void;
}

// ============================================================================
// Component
// ============================================================================

const TaskManagement: React.FC<TaskManagementProps> = ({
  tasks,
  loading,
  pagination,
  onViewDetails,
  onEdit,
  onAssign,
  onCancel,
  onPageChange,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);

  // Handle cancel with confirmation
  const handleCancel = useCallback((id: string, name: string) => {
    confirm({
      title: t('annotationTask.messages.confirmCancel'),
      icon: <ExclamationCircleOutlined />,
      content: name,
      okText: t('common.actions.confirm'),
      okType: 'danger',
      cancelText: t('common.actions.cancel'),
      onOk: () => {
        onCancel(id);
      },
    });
  }, [onCancel, t]);

  // Get status color
  const getStatusColor = (status: string): string => {
    const colorMap: Record<string, string> = {
      created: 'default',
      in_progress: 'processing',
      completed: 'success',
      cancelled: 'error',
    };
    return colorMap[status] || 'default';
  };

  // Get priority color
  const getPriorityColor = (priority: string): string => {
    const colorMap: Record<string, string> = {
      low: 'default',
      medium: 'blue',
      high: 'orange',
      urgent: 'red',
    };
    return colorMap[priority] || 'default';
  };

  const calculateProgress = (task: AnnotationTask): number => {
    return Math.min(100, Math.max(0, Math.round(Number(task.progress) || 0)));
  };

  // Expandable row render
  const expandedRowRender = (record: AnnotationTask) => {
    return (
      <div style={{ padding: '16px 24px' }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label={t('annotationTask.columns.description')}>
            {record.description || '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('annotationTask.columns.assignee')}>
            {record.assigned_to?.join(', ') || '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('annotationTask.columns.createdAt')}>
            {new Date(record.created_at).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label={t('annotationTask.columns.dueDate')}>
            {record.deadline ? new Date(record.deadline).toLocaleString() : '-'}
          </Descriptions.Item>
        </Descriptions>
        
        {record.sample_ids && record.sample_ids.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Text strong>{t('sampleLibrary.title')}: </Text>
            <Text type="secondary">
              {record.sample_ids.length} {t('annotationTask.progress.total')}
            </Text>
          </div>
        )}
      </div>
    );
  };

  // Table columns configuration
  const columns: TableProps<AnnotationTask>['columns'] = [
    {
      title: t('annotationTask.columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: t('annotationTask.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {t(`annotationTask.status.${status}`)}
        </Tag>
      ),
      filters: [
        { text: t('annotationTask.status.pending'), value: 'created' },
        { text: t('annotationTask.status.inProgress'), value: 'in_progress' },
        { text: t('annotationTask.status.completed'), value: 'completed' },
        { text: t('annotationTask.status.cancelled'), value: 'cancelled' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: t('annotationTask.columns.progress'),
      key: 'progress',
      width: 200,
      render: (_, record) => {
        const percentage = calculateProgress(record);
        const sampleTotal = record.sample_ids?.length ?? 0;
        const labeledCount =
          sampleTotal > 0 ? Math.round((percentage / 100) * sampleTotal) : 0;

        return (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Progress
              percent={percentage}
              size="small"
              status={record.status === 'completed' ? 'success' : 'active'}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {labeledCount}/{sampleTotal || '—'} {t('annotationTask.progress.labeled')}
            </Text>
          </Space>
        );
      },
    },
    {
      title: t('annotationTask.columns.assignee'),
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      width: 150,
      ellipsis: true,
      render: (assignees: string[]) => (
        <Tooltip title={assignees?.join(', ')}>
          <Text ellipsis>
            {assignees?.length > 0 ? assignees.join(', ') : '-'}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: t('annotationTask.columns.dueDate'),
      dataIndex: 'deadline',
      key: 'deadline',
      width: 180,
      sorter: (a, b) => {
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
      },
      render: (date: string) => {
        if (!date) return '-';
        const dueDate = new Date(date);
        const now = new Date();
        const isOverdue = dueDate < now;
        
        return (
          <Text type={isOverdue ? 'danger' : undefined}>
            {dueDate.toLocaleString()}
          </Text>
        );
      },
    },
    {
      title: t('annotationTask.columns.actions'),
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={t('tempData.actions.viewDetails')}>
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onViewDetails(record.id)}
            />
          </Tooltip>
          {record.status !== 'completed' && record.status !== 'cancelled' && (
            <>
              <Tooltip title={t('common.actions.edit')}>
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => onEdit(record.id)}
                />
              </Tooltip>
              <Tooltip title={t('annotationTask.actions.assign')}>
                <Button
                  type="text"
                  size="small"
                  icon={<UserAddOutlined />}
                  onClick={() => onAssign(record.id)}
                />
              </Tooltip>
              <Tooltip title={t('annotationTask.actions.cancel')}>
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<StopOutlined />}
                  onClick={() => handleCancel(record.id, record.name)}
                />
              </Tooltip>
            </>
          )}
        </Space>
      ),
    },
  ];

  // Pagination configuration
  const paginationConfig: TablePaginationConfig = {
    current: pagination.page,
    pageSize: pagination.pageSize,
    total: pagination.total,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total) => t('common.pagination.total', { total }),
    pageSizeOptions: ['10', '20', '50', '100'],
    onChange: onPageChange,
  };

  return (
    <Table<AnnotationTask>
      columns={columns}
      dataSource={tasks}
      rowKey="id"
      loading={loading}
      pagination={paginationConfig}
      expandable={{
        expandedRowKeys,
        onExpandedRowsChange: (keys) => setExpandedRowKeys(keys as string[]),
        expandedRowRender,
      }}
      scroll={{ x: 1200 }}
      size="middle"
    />
  );
};

export default TaskManagement;
