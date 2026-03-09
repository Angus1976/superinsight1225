// Enhancement List Component
import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Modal, Card, Progress, Select } from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  RollbackOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { enhancementApi, EnhancementJob } from '@/api/enhancementApi';
import { useAuthStore } from '@/stores/authStore';

export const EnhancementList: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  const [data, setData] = useState<EnhancementJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchData = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await enhancementApi.list(page, pageSize);
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
    message.info(t('enhancement.actions.create'));
  };

  const handleStart = async (record: EnhancementJob) => {
    try {
      await enhancementApi.start(record.id);
      message.success(t('enhancement.messages.startSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('enhancement.messages.startFailed'));
    }
  };

  const handlePause = async (record: EnhancementJob) => {
    try {
      await enhancementApi.pause(record.id);
      message.success(t('enhancement.messages.pauseSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('enhancement.messages.pauseFailed'));
    }
  };

  const handleResume = async (record: EnhancementJob) => {
    try {
      await enhancementApi.resume(record.id);
      message.success(t('enhancement.messages.resumeSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('enhancement.messages.resumeFailed'));
    }
  };

  const handleCancel = (record: EnhancementJob) => {
    Modal.confirm({
      title: t('enhancement.messages.confirmCancel'),
      onOk: async () => {
        try {
          await enhancementApi.cancel(record.id);
          message.success(t('enhancement.messages.cancelSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('enhancement.messages.cancelFailed'));
        }
      },
    });
  };

  const handleRollback = (record: EnhancementJob) => {
    Modal.confirm({
      title: t('enhancement.messages.confirmRollback'),
      onOk: async () => {
        try {
          await enhancementApi.rollback(record.id, record.currentVersion);
          message.success(t('enhancement.messages.rollbackSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('enhancement.messages.rollbackFailed'));
        }
      },
    });
  };

  const handleViewHistory = (record: EnhancementJob) => {
    message.info(t('enhancement.actions.viewHistory'));
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'processing',
      running: 'blue',
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
    },
    {
      title: t('enhancement.columns.name'),
      dataIndex: 'name',
      key: 'name',
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
    },
    {
      title: t('enhancement.columns.progress'),
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number, record: EnhancementJob) => (
        <Progress 
          percent={progress} 
          status={record.status === 'failed' ? 'exception' : record.status === 'completed' ? 'success' : 'active'}
        />
      ),
    },
    {
      title: t('enhancement.columns.iterations'),
      dataIndex: 'iterations',
      key: 'iterations',
      render: (current: number, record: EnhancementJob) => 
        t('enhancement.messages.iterationProgress', { current, total: record.maxIterations || '∞' }),
    },
    {
      title: t('enhancement.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('enhancement.columns.completedAt'),
      dataIndex: 'completedAt',
      key: 'completedAt',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: t('enhancement.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: EnhancementJob) => (
        <Space>
          {hasPermission('enhancement.start') && record.status === 'pending' && (
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record)}
            >
              {t('enhancement.actions.start')}
            </Button>
          )}
          {hasPermission('enhancement.pause') && record.status === 'running' && (
            <Button 
              type="text" 
              icon={<PauseCircleOutlined />}
              onClick={() => handlePause(record)}
            >
              {t('enhancement.actions.pause')}
            </Button>
          )}
          {hasPermission('enhancement.resume') && record.status === 'paused' && (
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />}
              onClick={() => handleResume(record)}
            >
              {t('enhancement.actions.resume')}
            </Button>
          )}
          {hasPermission('enhancement.cancel') && ['pending', 'running', 'paused'].includes(record.status) && (
            <Button 
              type="text" 
              danger 
              icon={<CloseCircleOutlined />}
              onClick={() => handleCancel(record)}
            >
              {t('enhancement.actions.cancel')}
            </Button>
          )}
          {hasPermission('enhancement.rollback') && record.status === 'completed' && (
            <Button 
              type="text" 
              icon={<RollbackOutlined />}
              onClick={() => handleRollback(record)}
            >
              {t('enhancement.actions.rollback')}
            </Button>
          )}
          <Button 
            type="text" 
            icon={<HistoryOutlined />}
            onClick={() => handleViewHistory(record)}
          >
            {t('enhancement.actions.viewHistory')}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        {hasPermission('enhancement.create') && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            {t('enhancement.actions.create')}
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

export default EnhancementList;