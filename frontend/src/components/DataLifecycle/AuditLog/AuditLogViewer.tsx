/**
 * AuditLogViewer Component
 * 
 * Displays audit logs with filtering, pagination, and export capabilities.
 * Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 19.3
 */

import React, { useState } from 'react';
import { Table, Button, Input, Select, DatePicker, Space, Tag } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import './AuditLogViewer.css';

const { RangePicker } = DatePicker;

// Types based on design document
export interface AuditOperation {
  operationType: string;
  userId: string;
  resource: {
    type: string;
    id: string;
  };
  action: string;
  timestamp: Date;
  details?: Record<string, any>;
  ipAddress?: string;
  userAgent?: string;
}

export interface AuditLog {
  id: string;
  operation: AuditOperation;
  result: 'success' | 'failure' | 'partial';
  duration: number;
  timestamp: Date;
  error?: string;
}

export interface AuditFilters {
  userId?: string;
  resourceType?: string;
  operationType?: string;
  dateRange?: [Date, Date];
  result?: 'success' | 'failure' | 'partial';
}

export type ExportFormat = 'csv' | 'json';

export interface AuditLogViewerProps {
  logs: AuditLog[];
  loading?: boolean;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
  };
  onFilter?: (filters: AuditFilters) => void;
  onExport?: (filters: AuditFilters, format: ExportFormat) => void;
  onPageChange?: (page: number, pageSize: number) => void;
}

const AuditLogViewer: React.FC<AuditLogViewerProps> = ({
  logs,
  loading = false,
  pagination = { page: 1, pageSize: 10, total: 0 },
  onFilter,
  onExport,
  onPageChange,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [filters, setFilters] = useState<AuditFilters>({});

  const handleFilterChange = (key: keyof AuditFilters, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
  };

  const handleSearch = () => {
    onFilter?.(filters);
  };

  const handleReset = () => {
    setFilters({});
    onFilter?.({});
  };

  const handleExport = () => {
    onExport?.(filters, 'csv');
  };

  const getResultColor = (result: string) => {
    switch (result) {
      case 'success':
        return 'success';
      case 'failure':
        return 'error';
      case 'partial':
        return 'warning';
      default:
        return 'default';
    }
  };

  const columns: ColumnsType<AuditLog> = [
    {
      title: t('audit.columns.timestamp'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp: Date) => new Date(timestamp).toLocaleString(),
      sorter: true,
    },
    {
      title: t('audit.columns.userId'),
      dataIndex: ['operation', 'userId'],
      key: 'userId',
    },
    {
      title: t('audit.columns.operationType'),
      dataIndex: ['operation', 'operationType'],
      key: 'operationType',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: t('audit.columns.resourceType'),
      dataIndex: ['operation', 'resource', 'type'],
      key: 'resourceType',
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: t('audit.columns.action'),
      dataIndex: ['operation', 'action'],
      key: 'action',
    },
    {
      title: t('audit.columns.result'),
      dataIndex: 'result',
      key: 'result',
      render: (result: string) => (
        <Tag color={getResultColor(result)}>{result}</Tag>
      ),
    },
    {
      title: t('audit.columns.duration'),
      dataIndex: 'duration',
      key: 'duration',
      render: (ms: number) => `${ms}ms`,
      sorter: true,
    },
  ];

  return (
    <div className="audit-log-viewer">
      <div className="audit-log-filters">
        <Space wrap>
          <Input
            placeholder={t('audit.filters.userId')}
            value={filters.userId}
            onChange={(e) => handleFilterChange('userId', e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            placeholder={t('audit.filters.resourceType')}
            value={filters.resourceType}
            onChange={(value) => handleFilterChange('resourceType', value)}
            style={{ width: 200 }}
            allowClear
            options={[
              { label: 'temp_data', value: 'temp_data' },
              { label: 'sample', value: 'sample' },
              { label: 'annotation_task', value: 'annotation_task' },
              { label: 'annotated_data', value: 'annotated_data' },
              { label: 'enhanced_data', value: 'enhanced_data' },
              { label: 'trial', value: 'trial' },
            ]}
          />
          <Select
            placeholder={t('audit.filters.operationType')}
            value={filters.operationType}
            onChange={(value) => handleFilterChange('operationType', value)}
            style={{ width: 200 }}
            allowClear
            options={[
              { label: 'create', value: 'create' },
              { label: 'read', value: 'read' },
              { label: 'update', value: 'update' },
              { label: 'delete', value: 'delete' },
              { label: 'transfer', value: 'transfer' },
              { label: 'state_change', value: 'state_change' },
            ]}
          />
          <RangePicker
            placeholder={[t('audit.filters.startDate'), t('audit.filters.endDate')]}
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) {
                handleFilterChange('dateRange', [dates[0].toDate(), dates[1].toDate()]);
              } else {
                handleFilterChange('dateRange', undefined);
              }
            }}
          />
          <Select
            placeholder={t('audit.filters.result')}
            value={filters.result}
            onChange={(value) => handleFilterChange('result', value)}
            style={{ width: 150 }}
            allowClear
            options={[
              { label: t('audit.results.success'), value: 'success' },
              { label: t('audit.results.failure'), value: 'failure' },
              { label: t('audit.results.partial'), value: 'partial' },
            ]}
          />
          <Button type="primary" onClick={handleSearch}>
            {t('common.actions.search')}
          </Button>
          <Button onClick={handleReset}>
            {t('common.actions.reset')}
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
          >
            {t('audit.export')}
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={logs}
        loading={loading}
        rowKey="id"
        pagination={{
          current: pagination.page,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => t('common.pagination.total', { total }),
          onChange: onPageChange,
        }}
        expandable={{
          expandedRowRender: (record) => (
            <div className="audit-log-details">
              <pre>{JSON.stringify(record.operation.details, null, 2)}</pre>
            </div>
          ),
        }}
      />
    </div>
  );
};

export default AuditLogViewer;
