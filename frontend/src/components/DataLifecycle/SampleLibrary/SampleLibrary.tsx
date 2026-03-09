/**
 * SampleLibrary Component
 * 
 * Displays sample library with search filters, multi-select, and action buttons.
 * Provides comprehensive sample management with pagination and filtering capabilities.
 * 
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 19.3
 */

import React, { useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Tooltip,
  Modal,
  message,
} from 'antd';
import type { TableProps, TablePaginationConfig } from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { Sample } from '@/services/dataLifecycle';
import SearchFilters from './SearchFilters.tsx';
import type { SearchFilters as ISearchFilters } from './SearchFilters.tsx';

const { confirm } = Modal;

// ============================================================================
// Types
// ============================================================================

export interface SampleLibraryProps {
  samples: Sample[];
  loading: boolean;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
  selectedSamples: string[];
  onSelectionChange: (selectedIds: string[]) => void;
  onCreateTask: () => void;
  onViewDetails: (id: string) => void;
  onEditTags: (id: string) => void;
  onDelete: (id: string) => void;
  onSearch: (filters: ISearchFilters) => void;
  onPageChange: (page: number, pageSize: number) => void;
}

// ============================================================================
// Component
// ============================================================================

const SampleLibrary: React.FC<SampleLibraryProps> = ({
  samples,
  loading,
  pagination,
  selectedSamples,
  onSelectionChange,
  onCreateTask,
  onViewDetails,
  onEditTags,
  onDelete,
  onSearch,
  onPageChange,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [filters, setFilters] = useState<ISearchFilters>({});

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: ISearchFilters) => {
    setFilters(newFilters);
    onSearch(newFilters);
  }, [onSearch]);

  // Handle delete with confirmation
  const handleDelete = useCallback((id: string, name: string) => {
    confirm({
      title: t('sampleLibrary.messages.confirmRemove'),
      icon: <ExclamationCircleOutlined />,
      content: name,
      okText: t('common.actions.confirm'),
      okType: 'danger',
      cancelText: t('common.actions.cancel'),
      onOk: () => {
        onDelete(id);
      },
    });
  }, [onDelete, t]);

  // Table columns configuration
  const columns: TableProps<Sample>['columns'] = [
    {
      title: t('sampleLibrary.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 280,
      ellipsis: true,
      render: (id: string) => (
        <Tooltip title={id}>
          <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
            {id.substring(0, 8)}...
          </span>
        </Tooltip>
      ),
    },
    {
      title: t('sampleLibrary.columns.dataType'),
      dataIndex: 'data_type',
      key: 'data_type',
      width: 120,
      render: (type: string) => (
        <Tag color="blue">{type || t('common.type')}</Tag>
      ),
    },
    {
      title: t('sampleLibrary.columns.qualityScore'),
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 120,
      sorter: (a, b) => (a.quality_score || 0) - (b.quality_score || 0),
      render: (score: number) => {
        const value = score || 0;
        let color = 'default';
        if (value >= 0.8) color = 'success';
        else if (value >= 0.6) color = 'processing';
        else if (value >= 0.4) color = 'warning';
        else color = 'error';
        
        return (
          <Tag color={color}>
            {value.toFixed(2)}
          </Tag>
        );
      },
    },
    {
      title: t('sampleLibrary.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('sampleLibrary.columns.usageCount'),
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 120,
      sorter: (a, b) => (a.usage_count || 0) - (b.usage_count || 0),
      render: (count: number) => count || 0,
    },
    {
      title: t('sampleLibrary.columns.actions'),
      key: 'actions',
      width: 180,
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
          <Tooltip title={t('common.actions.edit')}>
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEditTags(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('common.actions.delete')}>
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id, record.data_type || record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Row selection configuration
  const rowSelection: TableProps<Sample>['rowSelection'] = {
    selectedRowKeys: selectedSamples,
    onChange: (selectedRowKeys) => {
      onSelectionChange(selectedRowKeys as string[]);
    },
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  };

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
    <div className="sample-library">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Search Filters */}
        <SearchFilters
          filters={filters}
          onChange={handleFilterChange}
        />

        {/* Action Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <span style={{ color: '#666' }}>
              {t('sampleLibrary.statistics.selected', { count: selectedSamples.length })}
            </span>
          </Space>
          <Button
            type="primary"
            disabled={selectedSamples.length === 0}
            onClick={onCreateTask}
          >
            {t('sampleLibrary.actions.createTask')}
          </Button>
        </div>

        {/* Sample Table */}
        <Table<Sample>
          columns={columns}
          dataSource={samples}
          rowKey="id"
          loading={loading}
          rowSelection={rowSelection}
          pagination={paginationConfig}
          scroll={{ x: 1200 }}
          size="middle"
        />
      </Space>
    </div>
  );
};

export default SampleLibrary;
