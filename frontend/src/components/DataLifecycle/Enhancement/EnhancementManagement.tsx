/**
 * EnhancementManagement Component
 * 
 * Displays enhancement job table with filtering and action controls.
 * Requirements: 15.1, 15.2, 15.3
 */

import React from 'react';
import { Table, Tag, Button, Space, Progress, Typography } from 'antd';
import {
  EyeOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;

export interface EnhancementJob {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
  progress: number;
  iterations?: number;
  maxIterations?: number;
  createdAt: string;
  completedAt?: string;
}

export interface EnhancementManagementProps {
  jobs: EnhancementJob[];
  loading: boolean;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
  onViewResults: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  onRetry: (jobId: string) => void;
  onDelete: (jobId: string) => void;
  onPageChange: (page: number, pageSize: number) => void;
}

const EnhancementManagement: React.FC<EnhancementManagementProps> = ({
  jobs,
  loading,
  pagination,
  onViewResults,
  onCancel,
  onRetry,
  onDelete,
  onPageChange,
}) => {
  const { t } = useTranslation('dataLifecycle');

  const getStatusColor = (status: string): string => {
    const colorMap: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
      cancelled: 'default',
      paused: 'warning',
    };
    return colorMap[status] || 'default';
  };

  const columns = [
    {
      title: t('enhancement.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
      ellipsis: true,
    },
    {
      title: t('enhancement.columns.name'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: t('enhancement.columns.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => t(`enhancement.type.${type}`),
    },
    {
      title: t('enhancement.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {t(`enhancement.status.${status}`)}
        </Tag>
      ),
      filters: [
        { text: t('enhancement.status.pending'), value: 'pending' },
        { text: t('enhancement.status.running'), value: 'running' },
        { text: t('enhancement.status.completed'), value: 'completed' },
        { text: t('enhancement.status.failed'), value: 'failed' },
        { text: t('enhancement.status.cancelled'), value: 'cancelled' },
        { text: t('enhancement.status.paused'), value: 'paused' },
      ],
      onFilter: (value: any, record: EnhancementJob) => record.status === value,
    },
    {
      title: t('enhancement.columns.progress'),
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number, record: EnhancementJob) => (
        <Progress
          percent={progress}
          status={
            record.status === 'failed'
              ? 'exception'
              : record.status === 'completed'
              ? 'success'
              : 'active'
          }
          size="small"
        />
      ),
    },
    {
      title: t('enhancement.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
      sorter: (a: EnhancementJob, b: EnhancementJob) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
    },
    {
      title: t('enhancement.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: EnhancementJob) => (
        <Space size="small">
          {record.status === 'completed' && (
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onViewResults(record.id)}
            >
              {t('enhancement.actions.viewDetails')}
            </Button>
          )}
          {['pending', 'running', 'paused'].includes(record.status) && (
            <Button
              type="text"
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => onCancel(record.id)}
            >
              {t('enhancement.actions.cancel')}
            </Button>
          )}
          {record.status === 'failed' && (
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => onRetry(record.id)}
            >
              {t('common.actions.retry')}
            </Button>
          )}
          {['completed', 'failed', 'cancelled'].includes(record.status) && (
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record.id)}
            >
              {t('common.actions.delete')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={jobs}
      rowKey="id"
      loading={loading}
      pagination={{
        current: pagination.page,
        pageSize: pagination.pageSize,
        total: pagination.total,
        showSizeChanger: true,
        showQuickJumper: pagination.total > 100,
        showTotal: (total) => t('common.pagination.total', { total }),
        onChange: onPageChange,
      }}
    />
  );
};

export default EnhancementManagement;
