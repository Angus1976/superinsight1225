// AI Trial List Component
import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Modal, Card, Progress, Statistic } from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  BarChartOutlined,
  ExportOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { aiTrialApi, AITrial } from '@/api/aiTrialApi';
import { useAuthStore } from '@/stores/authStore';

export const AITrialList: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  const [data, setData] = useState<AITrial[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchData = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await aiTrialApi.list(page, pageSize);
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
    message.info(t('aiTrial.actions.create'));
  };

  const handleStart = async (record: AITrial) => {
    try {
      await aiTrialApi.start(record.id);
      message.success(t('aiTrial.messages.startSuccess'));
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      message.error(t('aiTrial.messages.startFailed'));
    }
  };

  const handleStop = (record: AITrial) => {
    Modal.confirm({
      title: t('aiTrial.messages.confirmStop'),
      onOk: async () => {
        try {
          await aiTrialApi.stop(record.id);
          message.success(t('aiTrial.messages.stopSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('aiTrial.messages.stopFailed'));
        }
      },
    });
  };

  const handleViewResults = (record: AITrial) => {
    message.info(t('aiTrial.actions.viewResults'));
  };

  const handleExportResults = async (record: AITrial) => {
    try {
      await aiTrialApi.exportResults(record.id);
      message.success(t('aiTrial.messages.exportSuccess'));
    } catch (error) {
      message.error(t('aiTrial.messages.exportFailed'));
    }
  };

  const handleCompare = (record: AITrial) => {
    message.info(t('aiTrial.actions.compare'));
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'processing',
      running: 'blue',
      completed: 'success',
      failed: 'error',
      cancelled: 'default',
    };
    return colorMap[status] || 'default';
  };

  const columns = [
    {
      title: t('aiTrial.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: t('aiTrial.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('aiTrial.columns.model'),
      dataIndex: 'model',
      key: 'model',
    },
    {
      title: t('aiTrial.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {t(`aiTrial.status.${status}`)}
        </Tag>
      ),
    },
    {
      title: t('aiTrial.columns.trialCount'),
      dataIndex: 'trialCount',
      key: 'trialCount',
      render: (count: number) => count || 0,
    },
    {
      title: t('aiTrial.columns.successRate'),
      dataIndex: 'successRate',
      key: 'successRate',
      render: (rate: number) => `${(rate || 0).toFixed(1)}%`,
    },
    {
      title: t('aiTrial.columns.avgScore'),
      dataIndex: 'avgScore',
      key: 'avgScore',
      render: (score: number) => (score || 0).toFixed(2),
    },
    {
      title: t('aiTrial.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('aiTrial.columns.completedAt'),
      dataIndex: 'completedAt',
      key: 'completedAt',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: t('aiTrial.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: AITrial) => (
        <Space>
          {hasPermission('aiTrial.start') && record.status === 'pending' && (
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record)}
            >
              {t('aiTrial.actions.startTrial')}
            </Button>
          )}
          {hasPermission('aiTrial.stop') && record.status === 'running' && (
            <Button 
              type="text" 
              danger 
              icon={<StopOutlined />}
              onClick={() => handleStop(record)}
            >
              {t('aiTrial.actions.stop')}
            </Button>
          )}
          {hasPermission('aiTrial.view') && record.status === 'completed' && (
            <>
              <Button 
                type="text" 
                icon={<BarChartOutlined />}
                onClick={() => handleViewResults(record)}
              >
                {t('aiTrial.actions.viewResults')}
              </Button>
              <Button 
                type="text" 
                icon={<ExportOutlined />}
                onClick={() => handleExportResults(record)}
              >
                {t('aiTrial.actions.exportResults')}
              </Button>
              <Button 
                type="text" 
                icon={<SwapOutlined />}
                onClick={() => handleCompare(record)}
              >
                {t('aiTrial.actions.compare')}
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        {hasPermission('aiTrial.create') && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            {t('aiTrial.actions.create')}
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

export default AITrialList;