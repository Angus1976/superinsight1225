// Task review workflow component
import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Tag,
  List,
  Input,
  Form,
  Modal,
  message,
  Statistic,
  Timeline,
  Alert,
  Divider,
  Rate,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ArrowLeftOutlined,
  ExclamationCircleOutlined,
  UserOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  EditOutlined,
  RollbackOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTask } from '@/hooks/useTask';

const { TextArea } = Input;

interface ReviewItem {
  id: string;
  taskId: string;
  annotationId: string;
  content: string;
  annotation: Record<string, unknown>;
  annotator: string;
  annotatedAt: string;
  status: 'pending' | 'approved' | 'rejected' | 'revision_requested';
  reviewedBy?: string;
  reviewedAt?: string;
  comments?: ReviewComment[];
  qualityScore?: number;
}

interface ReviewComment {
  id: string;
  author: string;
  content: string;
  createdAt: string;
  type: 'comment' | 'approval' | 'rejection' | 'revision';
}

interface ReviewStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  revisionRequested: number;
}

const TaskReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation(['tasks', 'common']);
  const { data: task } = useTask(id || '');
  
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [reviewComment, setReviewComment] = useState('');
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [batchAction, setBatchAction] = useState<'approve' | 'reject' | 'revision'>('approve');

  // Mock review items
  const mockReviewItems: ReviewItem[] = [
    {
      id: 'r1',
      taskId: id || '1',
      annotationId: 'a1',
      content: '这个产品非常好用，我很满意！',
      annotation: { sentiment: 'positive', confidence: 0.95 },
      annotator: '张三',
      annotatedAt: '2026-01-10T10:30:00Z',
      status: 'pending',
      qualityScore: 4.5,
    },
    {
      id: 'r2',
      taskId: id || '1',
      annotationId: 'a2',
      content: '服务态度很差，等了很久都没人理。',
      annotation: { sentiment: 'negative', confidence: 0.88 },
      annotator: '李四',
      annotatedAt: '2026-01-10T11:15:00Z',
      status: 'approved',
      reviewedBy: '王五',
      reviewedAt: '2026-01-10T14:00:00Z',
      qualityScore: 5,
      comments: [
        { id: 'c1', author: '王五', content: '标注准确', createdAt: '2026-01-10T14:00:00Z', type: 'approval' }
      ],
    },
    {
      id: 'r3',
      taskId: id || '1',
      annotationId: 'a3',
      content: '一般般吧，没什么特别的感觉。',
      annotation: { sentiment: 'positive', confidence: 0.65 },
      annotator: '张三',
      annotatedAt: '2026-01-10T12:00:00Z',
      status: 'revision_requested',
      reviewedBy: '王五',
      reviewedAt: '2026-01-10T15:30:00Z',
      qualityScore: 2,
      comments: [
        { id: 'c2', author: '王五', content: '这应该是中性情感，请重新标注', createdAt: '2026-01-10T15:30:00Z', type: 'revision' }
      ],
    },
  ];

  const [reviewItems, setReviewItems] = useState<ReviewItem[]>(mockReviewItems);

  // Calculate stats
  const stats: ReviewStats = {
    total: reviewItems.length,
    pending: reviewItems.filter(i => i.status === 'pending').length,
    approved: reviewItems.filter(i => i.status === 'approved').length,
    rejected: reviewItems.filter(i => i.status === 'rejected').length,
    revisionRequested: reviewItems.filter(i => i.status === 'revision_requested').length,
  };

  // Handle single item review
  const handleReview = useCallback((itemId: string, action: 'approve' | 'reject' | 'revision', comment?: string) => {
    setReviewItems(prev => prev.map(item => {
      if (item.id === itemId) {
        const newComment: ReviewComment = {
          id: `c${Date.now()}`,
          author: '当前用户',
          content: comment || (action === 'approve' ? '已批准' : action === 'reject' ? '已拒绝' : '需要修订'),
          createdAt: new Date().toISOString(),
          type: action === 'approve' ? 'approval' : action === 'reject' ? 'rejection' : 'revision',
        };
        return {
          ...item,
          status: action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'revision_requested',
          reviewedBy: '当前用户',
          reviewedAt: new Date().toISOString(),
          comments: [...(item.comments || []), newComment],
        };
      }
      return item;
    }));
    message.success(t(`review.${action}Success`) || `${action} successful`);
  }, [t]);

  // Handle batch review
  const handleBatchReview = useCallback(() => {
    if (selectedItems.length === 0) {
      message.warning(t('review.selectItems') || 'Please select items to review');
      return;
    }
    
    setReviewItems(prev => prev.map(item => {
      if (selectedItems.includes(item.id)) {
        const newComment: ReviewComment = {
          id: `c${Date.now()}`,
          author: '当前用户',
          content: reviewComment || (batchAction === 'approve' ? '批量批准' : batchAction === 'reject' ? '批量拒绝' : '批量请求修订'),
          createdAt: new Date().toISOString(),
          type: batchAction === 'approve' ? 'approval' : batchAction === 'reject' ? 'rejection' : 'revision',
        };
        return {
          ...item,
          status: batchAction === 'approve' ? 'approved' : batchAction === 'reject' ? 'rejected' : 'revision_requested',
          reviewedBy: '当前用户',
          reviewedAt: new Date().toISOString(),
          comments: [...(item.comments || []), newComment],
        };
      }
      return item;
    }));
    
    setSelectedItems([]);
    setReviewComment('');
    setBatchModalVisible(false);
    message.success(t('review.batchSuccess', { count: selectedItems.length }) || `Batch ${batchAction} successful`);
  }, [selectedItems, batchAction, reviewComment, t]);

  // Get status config
  const getStatusConfig = (status: ReviewItem['status']) => {
    switch (status) {
      case 'approved':
        return { color: 'success', icon: <CheckCircleOutlined />, text: t('review.approved') || 'Approved' };
      case 'rejected':
        return { color: 'error', icon: <CloseCircleOutlined />, text: t('review.rejected') || 'Rejected' };
      case 'revision_requested':
        return { color: 'warning', icon: <EditOutlined />, text: t('review.revisionRequested') || 'Revision Requested' };
      default:
        return { color: 'default', icon: <ClockCircleOutlined />, text: t('review.pending') || 'Pending' };
    }
  };

  return (
    <div>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/tasks/${id}`)}>
            {t('tasks.backToTask')}
          </Button>
        </Space>
        <h2>{t('review.title') || 'Task Review'}: {task?.name || 'Customer Review Classification'}</h2>
      </Card>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('review.totalItems') || 'Total Items'}
              value={stats.total}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('review.pendingReview') || 'Pending Review'}
              value={stats.pending}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('review.approved') || 'Approved'}
              value={stats.approved}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('review.needsRevision') || 'Needs Revision'}
              value={stats.revisionRequested + stats.rejected}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Batch Actions */}
      {selectedItems.length > 0 && (
        <Alert
          message={t('review.selectedItems', { count: selectedItems.length }) || `${selectedItems.length} items selected`}
          type="info"
          showIcon
          action={
            <Space>
              <Button
                size="small"
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => { setBatchAction('approve'); setBatchModalVisible(true); }}
              >
                {t('review.batchApprove') || 'Batch Approve'}
              </Button>
              <Button
                size="small"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => { setBatchAction('reject'); setBatchModalVisible(true); }}
              >
                {t('review.batchReject') || 'Batch Reject'}
              </Button>
              <Button
                size="small"
                icon={<RollbackOutlined />}
                onClick={() => { setBatchAction('revision'); setBatchModalVisible(true); }}
              >
                {t('review.batchRevision') || 'Request Revision'}
              </Button>
              <Button size="small" onClick={() => setSelectedItems([])}>
                {t('common.clear') || 'Clear'}
              </Button>
            </Space>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Review List */}
      <Card title={t('review.reviewItems') || 'Review Items'}>
        <List
          itemLayout="vertical"
          dataSource={reviewItems}
          renderItem={(item) => {
            const statusConfig = getStatusConfig(item.status);
            const isSelected = selectedItems.includes(item.id);
            
            return (
              <List.Item
                key={item.id}
                style={{
                  backgroundColor: isSelected ? '#e6f7ff' : undefined,
                  padding: 16,
                  marginBottom: 8,
                  borderRadius: 8,
                  border: '1px solid #f0f0f0',
                }}
                actions={item.status === 'pending' ? [
                  <Button
                    key="approve"
                    type="primary"
                    size="small"
                    icon={<LikeOutlined />}
                    onClick={() => handleReview(item.id, 'approve')}
                  >
                    {t('review.approve') || 'Approve'}
                  </Button>,
                  <Button
                    key="reject"
                    danger
                    size="small"
                    icon={<DislikeOutlined />}
                    onClick={() => handleReview(item.id, 'reject')}
                  >
                    {t('review.reject') || 'Reject'}
                  </Button>,
                  <Button
                    key="revision"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleReview(item.id, 'revision', '请检查并修订标注')}
                  >
                    {t('review.requestRevision') || 'Request Revision'}
                  </Button>,
                ] : [
                  <Tag key="status" color={statusConfig.color} icon={statusConfig.icon}>
                    {statusConfig.text}
                  </Tag>
                ]}
                extra={
                  <Space direction="vertical" align="end">
                    <Rate disabled value={item.qualityScore} allowHalf />
                    <span style={{ color: '#999', fontSize: 12 }}>
                      {t('review.qualityScore') || 'Quality Score'}
                    </span>
                  </Space>
                }
              >
                <List.Item.Meta
                  avatar={
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedItems([...selectedItems, item.id]);
                        } else {
                          setSelectedItems(selectedItems.filter(id => id !== item.id));
                        }
                      }}
                      style={{ marginRight: 8 }}
                    />
                  }
                  title={
                    <Space>
                      <span>{t('review.annotation') || 'Annotation'} #{item.annotationId}</span>
                      <Tag color={statusConfig.color} icon={statusConfig.icon}>
                        {statusConfig.text}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space>
                      <UserOutlined /> {item.annotator}
                      <Divider type="vertical" />
                      <ClockCircleOutlined /> {new Date(item.annotatedAt).toLocaleString()}
                    </Space>
                  }
                />
                
                {/* Content */}
                <Card size="small" style={{ marginTop: 8, backgroundColor: '#fafafa' }}>
                  <p><strong>{t('review.originalText') || 'Original Text'}:</strong></p>
                  <p>{item.content}</p>
                  <Divider style={{ margin: '8px 0' }} />
                  <p><strong>{t('review.annotationResult') || 'Annotation Result'}:</strong></p>
                  <pre style={{ margin: 0, fontSize: 12 }}>
                    {JSON.stringify(item.annotation, null, 2)}
                  </pre>
                </Card>

                {/* Comments */}
                {item.comments && item.comments.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <strong>{t('review.comments') || 'Comments'}:</strong>
                    <Timeline style={{ marginTop: 8 }}>
                      {item.comments.map(comment => (
                        <Timeline.Item
                          key={comment.id}
                          color={comment.type === 'approval' ? 'green' : comment.type === 'rejection' ? 'red' : 'orange'}
                        >
                          <p style={{ marginBottom: 4 }}>
                            <strong>{comment.author}</strong>: {comment.content}
                          </p>
                          <small style={{ color: '#999' }}>
                            {new Date(comment.createdAt).toLocaleString()}
                          </small>
                        </Timeline.Item>
                      ))}
                    </Timeline>
                  </div>
                )}
              </List.Item>
            );
          }}
        />
      </Card>

      {/* Batch Review Modal */}
      <Modal
        title={t(`review.batch${batchAction.charAt(0).toUpperCase() + batchAction.slice(1)}`) || `Batch ${batchAction}`}
        open={batchModalVisible}
        onCancel={() => setBatchModalVisible(false)}
        onOk={handleBatchReview}
        okText={t('common.confirm') || 'Confirm'}
        cancelText={t('common.cancel') || 'Cancel'}
      >
        <p>{t('review.batchConfirm', { count: selectedItems.length, action: batchAction }) || `Are you sure you want to ${batchAction} ${selectedItems.length} items?`}</p>
        <Form.Item label={t('review.comment') || 'Comment'}>
          <TextArea
            rows={3}
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
            placeholder={t('review.commentPlaceholder') || 'Add a comment (optional)'}
          />
        </Form.Item>
      </Modal>
    </div>
  );
};

export default TaskReviewPage;
