// Annotation Task List Component
import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Modal, Card, Select, DatePicker } from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { annotationTaskApi, AnnotationTask } from '@/api/annotationTaskApi';
import { useAuthStore } from '@/stores/authStore';

export const AnnotationTaskList: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  const [data, setData] = useState<AnnotationTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchData = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await annotationTaskApi.list(page, pageSize);
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
    message.info(t('annotationTask.actions.create'));
  };

  const handleStart = async (record: AnnotationTask) => {
    try {
      await annotationTaskApi.start(record.id);
      message.success(t('annotationTask.messages.startSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('annotationTask.messages.startFailed'));
    }
  };

  const handleComplete = async (record: AnnotationTask) => {
    try {
      await annotationTaskApi.complete(record.id);
      message.success(t('annotationTask.messages.completeSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('annotationTask.messages.completeFailed'));
    }
  };

  const handleCancel = (record: AnnotationTask) => {
    Modal.confirm({
      title: t('annotationTask.messages.confirmCancel'),
      onOk: async () => {
        try {
          await annotationTaskApi.cancel(record.id);
          message.success(t('annotationTask.messages.cancelSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('annotationTask.messages.cancelFailed'));
        }
      },
    });
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'processing',
      inProgress: 'blue',
      completed: 'success',
      cancelled: 'default',
    };
    return colorMap[status] || 'default';
  };

  const getPriorityColor = (priority: string) => {
    const colorMap: Record<string, string> = {
      low: 'default',
      medium: 'blue',
      high: 'orange',
      urgent: 'red',
    };
    return colorMap[priority] || 'default';
  };

  const columns = [
    {
      title: t('annotationTask.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: t('annotationTask.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('annotationTask.columns.description'),
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: t('annotationTask.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {t(`annotationTask.status.${status}`)}
        </Tag>
      ),
    },
    {
      title: t('annotationTask.columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>
          {t(`annotationTask.priority.${priority}`)}
        </Tag>
      ),
    },
    {
      title: t('annotationTask.columns.assignee'),
      dataIndex: 'assignee',
      key: 'assignee',
    },
    {
      title: t('annotationTask.columns.dueDate'),
      dataIndex: 'dueDate',
      key: 'dueDate',
      render: (date: string) => date ? new Date(date).toLocaleDateString() : '-',
    },
    {
      title: t('annotationTask.columns.progress'),
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => `${progress || 0}%`,
    },
    {
      title: t('annotationTask.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('annotationTask.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: AnnotationTask) => (
        <Space>
          {hasPermission('annotationTask.start') && record.status === 'pending' && (
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record)}
            >
              {t('annotationTask.actions.start')}
            </Button>
          )}
          {hasPermission('annotationTask.complete') && record.status === 'inProgress' && (
            <Button 
              type="text" 
              icon={<CheckCircleOutlined />}
              onClick={() => handleComplete(record)}
            >
              {t('annotationTask.actions.complete')}
            </Button>
          )}
          {hasPermission('annotationTask.cancel') && record.status !== 'completed' && record.status !== 'cancelled' && (
            <Button 
              type="text" 
              danger 
              icon={<CloseCircleOutlined />}
              onClick={() => handleCancel(record)}
            >
              {t('annotationTask.actions.cancel')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        {hasPermission('annotationTask.create') && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            {t('annotationTask.actions.create')}
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

export default AnnotationTaskList;