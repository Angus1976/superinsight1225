// Temporary Data List Component
import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Modal, Card, Typography } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  InboxOutlined,
  RestoreOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { tempDataApi, TempData } from '@/api/tempDataApi';
import { useAuthStore } from '@/stores/authStore';

const { Text } = Typography;

export const TempDataList: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  const [data, setData] = useState<TempData[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchData = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await tempDataApi.list(page, pageSize);
      setData(response.items);
      setPagination({ current: page, pageSize, total: response.total });
    } catch (error) {
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = () => {
    // TODO: Open create modal
    message.info(t('tempData.actions.create'));
  };

  const handleEdit = (record: TempData) => {
    // TODO: Open edit modal
    message.info(t('tempData.actions.edit'));
  };

  const handleDelete = (record: TempData) => {
    Modal.confirm({
      title: t('tempData.messages.confirmDelete'),
      onOk: async () => {
        try {
          await tempDataApi.delete(record.id);
          message.success(t('tempData.messages.deleteSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('tempData.messages.deleteFailed'));
        }
      },
    });
  };

  const handleArchive = async (record: TempData) => {
    try {
      await tempDataApi.archive(record.id);
      message.success(t('tempData.messages.archiveSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('tempData.messages.archiveFailed'));
    }
  };

  const handleRestore = async (record: TempData) => {
    try {
      await tempDataApi.restore(record.id);
      message.success(t('tempData.messages.restoreSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('tempData.messages.restoreFailed'));
    }
  };

  const columns = [
    {
      title: t('tempData.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: t('tempData.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('tempData.columns.state'),
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => {
        const colorMap: Record<string, string> = {
          draft: 'default',
          processing: 'processing',
          ready: 'success',
          archived: 'warning',
          deleted: 'error',
        };
        return (
          <Tag color={colorMap[state] || 'default'}>
            {t(`tempData.states.${state}`)}
          </Tag>
        );
      },
    },
    {
      title: t('tempData.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('tempData.columns.updatedAt'),
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('tempData.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: TempData) => (
        <Space>
          <Button 
            type="text" 
            icon={<EyeOutlined />}
            onClick={() => handleEdit(record)}
          />
          {hasPermission('dataLifecycle.edit') && (
            <Button 
              type="text" 
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          )}
          {hasPermission('dataLifecycle.delete') && record.state !== 'deleted' && (
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          )}
          {hasPermission('dataLifecycle.archive') && record.state === 'ready' && (
            <Button 
              type="text" 
              icon={<InboxOutlined />}
              onClick={() => handleArchive(record)}
            />
          )}
          {hasPermission('dataLifecycle.restore') && record.state === 'archived' && (
            <Button 
              type="text" 
              icon={<RestoreOutlined />}
              onClick={() => handleRestore(record)}
            />
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        {hasPermission('dataLifecycle.create') && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            {t('tempData.actions.create')}
          </Button>
        )}
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total) => t('common.pagination.total', { total }),
        }}
        onChange={(pag) => fetchData(pag.current || 1, pag.pageSize || 10)}
      />
    </Card>
  );
};

export default TempDataList;