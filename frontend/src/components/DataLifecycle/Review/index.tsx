// Review List Component
import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Modal, Card, Input } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  EyeOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { reviewApi, Review } from '@/api/reviewApi';
import { useAuthStore } from '@/stores/authStore';

export const ReviewList: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  const [data, setData] = useState<Review[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchData = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await reviewApi.list(page, pageSize);
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

  const handleApprove = (record: Review) => {
    Modal.confirm({
      title: t('review.messages.confirmApprove'),
      onOk: async () => {
        try {
          await reviewApi.approve(record.id);
          message.success(t('review.messages.approveSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('review.messages.approveFailed'));
        }
      },
    });
  };

  const handleReject = (record: Review) => {
    Modal.confirm({
      title: t('review.messages.rejectionReason'),
      onOk: async () => {
        try {
          await reviewApi.reject(record.id, 'Rejected by reviewer');
          message.success(t('review.messages.rejectSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('review.messages.rejectFailed'));
        }
      },
    });
  };

  const handleCancel = (record: Review) => {
    Modal.confirm({
      title: t('review.messages.confirmCancel'),
      onOk: async () => {
        try {
          await reviewApi.cancel(record.id);
          message.success(t('review.messages.cancelSuccess'));
          fetchData(pagination.current, pagination.pageSize);
        } catch (error) {
          message.error(t('review.messages.cancelFailed'));
        }
      },
    });
  };

  const handleViewDetails = (record: Review) => {
    message.info(t('review.actions.viewDetails'));
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'processing',
      approved: 'success',
      rejected: 'error',
      cancelled: 'default',
    };
    return colorMap[status] || 'default';
  };

  const columns = [
    {
      title: t('review.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: t('review.columns.targetType'),
      dataIndex: 'targetType',
      key: 'targetType',
    },
    {
      title: t('review.columns.targetId'),
      dataIndex: 'targetId',
      key: 'targetId',
      width: 200,
    },
    {
      title: t('review.columns.requester'),
      dataIndex: 'requester',
      key: 'requester',
    },
    {
      title: t('review.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {t(`review.status.${status}`)}
        </Tag>
      ),
    },
    {
      title: t('review.columns.submittedAt'),
      dataIndex: 'submittedAt',
      key: 'submittedAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('review.columns.reviewer'),
      dataIndex: 'reviewer',
      key: 'reviewer',
    },
    {
      title: t('review.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: Review) => (
        <Space>
          <Button 
            type="text" 
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            {t('review.actions.viewDetails')}
          </Button>
          {hasPermission('review.approve') && record.status === 'pending' && (
            <>
              <Button 
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => handleApprove(record)}
              >
                {t('review.actions.approve')}
              </Button>
              <Button 
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => handleReject(record)}
              >
                {t('review.actions.reject')}
              </Button>
            </>
          )}
          {hasPermission('review.cancel') && record.status === 'pending' && (
            <Button 
              icon={<StopOutlined />}
              onClick={() => handleCancel(record)}
            >
              {t('review.actions.cancel')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card>
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

export default ReviewList;