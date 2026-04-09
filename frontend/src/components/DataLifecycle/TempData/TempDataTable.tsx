/**
 * TempDataTable Component
 * 
 * Ant Design Table component for displaying temporary data with CRUD operations.
 */

import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Tag, message, Modal, Dropdown, Typography, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  InboxOutlined,
  RollbackOutlined,
  EyeOutlined,
  MoreOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTempData } from '@/hooks/useDataLifecycle';
import { useAuthStore } from '@/stores/authStore';
import { useDataLifecycleStore } from '@/stores/dataLifecycleStore';
import type { TempData } from '@/services/dataLifecycle';

const { Text } = Typography;

// ============================================================================
// Types
// ============================================================================

interface TempDataTableProps {
  onEdit?: (record: TempData) => void;
  onView?: (record: TempData) => void;
  refreshKey?: number;
}

interface TableRow {
  key: string;
  id: string;
  name: string;
  state: string;
  uploadedBy: string;
  uploadedAt: string;
  updatedAt?: string;
  content?: Record<string, unknown>;
}

// ============================================================================
// Component
// ============================================================================

const TempDataTable: React.FC<TempDataTableProps> = ({ onEdit, onView, refreshKey }) => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  
  const {
    data,
    loading,
    pagination,
    fetchTempData,
    deleteTempData,
    archiveTempData,
    restoreTempData,
    setFilters,
    clearFilters,
  } = useTempData();

  const stateFilter = useDataLifecycleStore((s) => s.tempDataFilters.state);

  const [searchText, setSearchText] = useState('');

  const getTempDataByRow = useCallback(
    (row: TableRow): TempData | undefined => data.find((d) => d.id === row.id),
    [data]
  );

  // Fetch data on mount and when refreshKey changes
  useEffect(() => {
    fetchTempData({ page: 1, pageSize: 10 });
  }, [fetchTempData, refreshKey]);

  // Transform data for table
  const tableData: TableRow[] = data.map((item) => ({
    key: item.id,
    id: item.id,
    name: item.name,
    state: item.state,
    uploadedBy: item.uploaded_by,
    uploadedAt: item.uploaded_at,
    updatedAt: item.updated_at,
    content: item.content,
  }));

  // Handle table change (pagination, sorting, filtering)
  const handleTableChange = useCallback(
    (pag: { current?: number; pageSize?: number }) => {
      fetchTempData({
        page: pag.current || 1,
        pageSize: pag.pageSize || 10,
        state: stateFilter,
      });
    },
    [fetchTempData, stateFilter]
  );

  // Handle search
  const handleSearch = useCallback(
    (value: string) => {
      setSearchText(value);
      setFilters({ search: value });
      fetchTempData({ page: 1, pageSize: 10, state: stateFilter });
    },
    [setFilters, fetchTempData, stateFilter]
  );

  // Handle delete
  const handleDelete = useCallback(
    async (record: TableRow) => {
      Modal.confirm({
        title: t('tempData.messages.confirmDelete'),
        onOk: async () => {
          try {
            await deleteTempData(record.id);
            message.success(t('tempData.messages.deleteSuccess'));
          } catch {
            message.error(t('tempData.messages.deleteFailed'));
          }
        },
      });
    },
    [deleteTempData, t]
  );

  // Handle archive
  const handleArchive = useCallback(
    async (record: TableRow) => {
      try {
        await archiveTempData(record.id);
        message.success(t('tempData.messages.archiveSuccess'));
      } catch {
        message.error(t('tempData.messages.archiveFailed'));
      }
    },
    [archiveTempData, t]
  );

  // Handle restore
  const handleRestore = useCallback(
    async (record: TableRow) => {
      try {
        await restoreTempData(record.id);
        message.success(t('tempData.messages.restoreSuccess'));
      } catch {
        message.error(t('tempData.messages.restoreFailed'));
      }
    },
    [restoreTempData, t]
  );

  // Get state color
  const getStateColor = (state: string): string => {
    const colorMap: Record<string, string> = {
      draft: 'default',
      processing: 'processing',
      ready: 'success',
      archived: 'warning',
      deleted: 'error',
      temp_stored: 'blue',
      under_review: 'orange',
      rejected: 'red',
      approved: 'green',
      in_sample_library: 'cyan',
      annotation_pending: 'gold',
      annotating: 'processing',
      annotated: 'success',
      enhancing: 'processing',
      enhanced: 'success',
      trial_calculation: 'purple',
    };
    return colorMap[state] || 'default';
  };

  // Table columns
  const columns = [
    {
      title: t('tempData.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
      render: (id: string) => (
        <Tooltip title={id}>
          <Text ellipsis style={{ maxWidth: 180 }}>
            {id.substring(0, 8)}...{id.substring(id.length - 8)}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: t('tempData.columns.name'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: t('tempData.columns.state'),
      dataIndex: 'state',
      key: 'state',
      width: 120,
      render: (state: string) => (
        <Tag color={getStateColor(state)}>
          {t(`tempData.states.${state}`)}
        </Tag>
      ),
      filters: [
        { text: t('tempData.states.draft'), value: 'draft' },
        { text: t('tempData.states.processing'), value: 'processing' },
        { text: t('tempData.states.ready'), value: 'ready' },
        { text: t('tempData.states.archived'), value: 'archived' },
      ],
      onFilter: (value: unknown, record: TableRow) => record.state === value,
    },
    {
      title: t('tempData.columns.uploadedBy'),
      dataIndex: 'uploadedBy',
      key: 'uploadedBy',
      width: 120,
      render: (userId: string) => {
        if (!userId) return '-';
        // 显示 UUID 前 8 位作为短 ID
        return userId.length > 8 ? userId.substring(0, 8) + '...' : userId;
      },
      ellipsis: true,
    },
    {
      title: t('tempData.columns.uploadedAt'),
      dataIndex: 'uploadedAt',
      key: 'uploadedAt',
      width: 180,
      sorter: (a: TableRow, b: TableRow) =>
        new Date(a.uploadedAt).getTime() - new Date(b.uploadedAt).getTime(),
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('tempData.columns.updatedAt'),
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 180,
      render: (date: string | undefined) =>
        date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: t('tempData.columns.actions'),
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: TableRow) => {
        const items: MenuProps['items'] = [
          {
            key: 'view',
            label: t('tempData.actions.viewDetails'),
            icon: <EyeOutlined />,
            onClick: () => {
              const td = getTempDataByRow(record);
              if (td) onView?.(td);
            },
          },
        ];

        if (hasPermission('dataLifecycle.edit') && record.state !== 'deleted') {
          items.push({
            key: 'edit',
            label: t('tempData.actions.edit'),
            icon: <EditOutlined />,
            onClick: () => {
              const td = getTempDataByRow(record);
              if (td) onEdit?.(td);
            },
          });
        }

        if (hasPermission('dataLifecycle.archive') && record.state === 'ready') {
          items.push({
            key: 'archive',
            label: t('tempData.actions.archive'),
            icon: <InboxOutlined />,
            onClick: () => {
              void handleArchive(record);
            },
          });
        }

        if (hasPermission('dataLifecycle.restore') && record.state === 'archived') {
          items.push({
            key: 'restore',
            label: t('tempData.actions.restore'),
            icon: <RollbackOutlined />,
            onClick: () => {
              void handleRestore(record);
            },
          });
        }

        if (hasPermission('dataLifecycle.delete') && record.state !== 'deleted') {
          items.push({ type: 'divider' });
          items.push({
            key: 'delete',
            label: t('tempData.actions.delete'),
            icon: <DeleteOutlined />,
            danger: true,
            onClick: () => {
              void handleDelete(record);
            },
          });
        }

        return (
          <Space size="small">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                const td = getTempDataByRow(record);
                if (td) onView?.(td);
              }}
            />
            {hasPermission('dataLifecycle.edit') && record.state !== 'deleted' && (
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => {
                  const td = getTempDataByRow(record);
                  if (td) onEdit?.(td);
                }}
              />
            )}
            <Dropdown menu={{ items }} trigger={['click']}>
              <Button type="text" size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={tableData}
      rowKey="id"
      loading={loading}
      pagination={{
        current: pagination.page,
        pageSize: pagination.pageSize,
        total: pagination.total,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total) => t('common.pagination.total', { total }),
      }}
      onChange={handleTableChange}
      scroll={{ x: 1000 }}
      size="middle"
    />
  );
};

export default TempDataTable;