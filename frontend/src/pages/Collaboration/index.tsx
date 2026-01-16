/**
 * Collaboration Page (协作与审核流程页面)
 * 
 * Main collaboration workflow management interface including:
 * - Task list and team status
 * - Review queue and operations
 * - Quality dashboard
 */

import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Tabs,
  Badge,
  Progress,
  Modal,
  message,
  Avatar,
  List,
} from 'antd';
import {
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  UserOutlined,
  FileTextOutlined,
  AuditOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

// Types
interface TaskItem {
  id: string;
  name: string;
  assignee: string;
  status: 'pending' | 'in_progress' | 'review' | 'completed';
  priority: number;
  deadline?: string;
  progress: number;
}

interface TeamMember {
  id: string;
  name: string;
  avatar?: string;
  status: 'online' | 'busy' | 'offline';
  currentTask?: string;
  tasksCompleted: number;
  accuracy: number;
}

interface ReviewItem {
  id: string;
  annotationId: string;
  taskName: string;
  annotator: string;
  submittedAt: string;
  level: number;
  status: 'pending' | 'approved' | 'rejected';
}

interface QualityRanking {
  rank: number;
  annotatorId: string;
  name: string;
  accuracy: number;
  tasksCompleted: number;
}

// Mock data
const mockTasks: TaskItem[] = [
  { id: '1', name: '客户评论分类', assignee: '张三', status: 'in_progress', priority: 1, progress: 65, deadline: '2026-01-20' },
  { id: '2', name: '产品实体识别', assignee: '李四', status: 'review', priority: 2, progress: 100, deadline: '2026-01-18' },
  { id: '3', name: '情感分析标注', assignee: '王五', status: 'pending', priority: 3, progress: 0, deadline: '2026-01-25' },
  { id: '4', name: '意图识别', assignee: '赵六', status: 'completed', priority: 1, progress: 100 },
];

const mockTeam: TeamMember[] = [
  { id: '1', name: '张三', status: 'online', currentTask: '客户评论分类', tasksCompleted: 45, accuracy: 0.95 },
  { id: '2', name: '李四', status: 'busy', currentTask: '产品实体识别', tasksCompleted: 38, accuracy: 0.92 },
  { id: '3', name: '王五', status: 'online', tasksCompleted: 52, accuracy: 0.88 },
  { id: '4', name: '赵六', status: 'offline', tasksCompleted: 30, accuracy: 0.91 },
];

const mockReviews: ReviewItem[] = [
  { id: '1', annotationId: 'ann_001', taskName: '客户评论分类', annotator: '张三', submittedAt: '2026-01-14 10:30', level: 1, status: 'pending' },
  { id: '2', annotationId: 'ann_002', taskName: '产品实体识别', annotator: '李四', submittedAt: '2026-01-14 09:15', level: 2, status: 'pending' },
  { id: '3', annotationId: 'ann_003', taskName: '情感分析标注', annotator: '王五', submittedAt: '2026-01-13 16:45', level: 1, status: 'approved' },
];

const mockRanking: QualityRanking[] = [
  { rank: 1, annotatorId: '1', name: '张三', accuracy: 0.95, tasksCompleted: 45 },
  { rank: 2, annotatorId: '2', name: '李四', accuracy: 0.92, tasksCompleted: 38 },
  { rank: 3, annotatorId: '4', name: '赵六', accuracy: 0.91, tasksCompleted: 30 },
  { rank: 4, annotatorId: '3', name: '王五', accuracy: 0.88, tasksCompleted: 52 },
];

const statusColors = {
  pending: 'default',
  in_progress: 'processing',
  review: 'warning',
  completed: 'success',
} as const;

const memberStatusColors = {
  online: '#52c41a',
  busy: '#faad14',
  offline: '#999',
};

const CollaborationPage: React.FC = () => {
  const { t } = useTranslation('collaboration');
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null);

  const statusKeyMap: Record<string, string> = {
    pending: 'status.pending',
    in_progress: 'status.inProgress',
    review: 'status.review',
    completed: 'status.completed',
  };

  const reviewStatusKeyMap: Record<string, string> = {
    pending: 'review.pending',
    approved: 'review.approved',
    rejected: 'review.rejected',
  };

  const handleApprove = (review: ReviewItem) => {
    message.success(t('review.approveSuccess', { id: review.annotationId }));
    setReviewModalOpen(false);
  };

  const handleReject = (review: ReviewItem) => {
    message.warning(t('review.rejectSuccess', { id: review.annotationId }));
    setReviewModalOpen(false);
  };

  const taskColumns: ColumnsType<TaskItem> = [
    {
      title: t('tasks.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name) => <a>{name}</a>,
    },
    {
      title: t('tasks.assignee'),
      dataIndex: 'assignee',
      key: 'assignee',
      render: (name) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          {name}
        </Space>
      ),
    },
    {
      title: t('tasks.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: keyof typeof statusColors) => (
        <Badge status={statusColors[status]} text={t(statusKeyMap[status])} />
      ),
    },
    {
      title: t('tasks.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => (
        <Tag color={priority === 1 ? 'red' : priority === 2 ? 'orange' : 'blue'}>
          P{priority}
        </Tag>
      ),
    },
    {
      title: t('tasks.progress'),
      dataIndex: 'progress',
      key: 'progress',
      render: (progress) => <Progress percent={progress} size="small" style={{ width: 100 }} />,
    },
    {
      title: t('tasks.deadline'),
      dataIndex: 'deadline',
      key: 'deadline',
      render: (date) => date || '-',
    },
  ];

  const reviewColumns: ColumnsType<ReviewItem> = [
    {
      title: t('review.annotationId'),
      dataIndex: 'annotationId',
      key: 'annotationId',
    },
    {
      title: t('review.task'),
      dataIndex: 'taskName',
      key: 'taskName',
    },
    {
      title: t('review.annotator'),
      dataIndex: 'annotator',
      key: 'annotator',
    },
    {
      title: t('review.submittedAt'),
      dataIndex: 'submittedAt',
      key: 'submittedAt',
    },
    {
      title: t('review.reviewLevel'),
      dataIndex: 'level',
      key: 'level',
      render: (level) => <Tag>L{level}</Tag>,
    },
    {
      title: t('review.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'approved' ? 'success' : status === 'rejected' ? 'error' : 'default'}>
          {t(reviewStatusKeyMap[status])}
        </Tag>
      ),
    },
    {
      title: t('review.actions'),
      key: 'actions',
      render: (_, record) => (
        record.status === 'pending' && (
          <Space>
            <Button type="link" size="small" onClick={() => { setSelectedReview(record); setReviewModalOpen(true); }}>
              {t('review.reviewAction')}
            </Button>
          </Space>
        )
      ),
    },
  ];

  const pendingReviews = mockReviews.filter(r => r.status === 'pending').length;
  const onlineMembers = mockTeam.filter(m => m.status !== 'offline').length;

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>{t('title')}</h2>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.inProgressTasks')}
              value={mockTasks.filter(t => t.status === 'in_progress').length}
              prefix={<SyncOutlined spin />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.pendingReview')}
              value={pendingReviews}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: pendingReviews > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.onlineMembers')}
              value={onlineMembers}
              suffix={`/ ${mockTeam.length}`}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.avgAccuracy')}
              value={92.5}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card>
        <Tabs
          defaultActiveKey="tasks"
          items={[
            {
              key: 'tasks',
              label: <span><FileTextOutlined /> {t('tabs.tasks')}</span>,
              children: (
                <Table
                  columns={taskColumns}
                  dataSource={mockTasks}
                  rowKey="id"
                  pagination={false}
                />
              ),
            },
            {
              key: 'team',
              label: <span><TeamOutlined /> {t('tabs.team')}</span>,
              children: (
                <List
                  dataSource={mockTeam}
                  renderItem={(member) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          <Badge dot color={memberStatusColors[member.status]}>
                            <Avatar icon={<UserOutlined />} />
                          </Badge>
                        }
                        title={member.name}
                        description={member.currentTask ? `${t('team.processing')}: ${member.currentTask}` : t('team.idle')}
                      />
                      <Space size="large">
                        <Statistic title={t('team.completedTasks')} value={member.tasksCompleted} />
                        <Statistic title={t('team.accuracy')} value={(member.accuracy * 100).toFixed(1)} suffix="%" />
                      </Space>
                    </List.Item>
                  )}
                />
              ),
            },
            {
              key: 'review',
              label: (
                <span>
                  <AuditOutlined /> {t('tabs.review')}
                  {pendingReviews > 0 && <Badge count={pendingReviews} size="small" style={{ marginLeft: 8 }} />}
                </span>
              ),
              children: (
                <Table
                  columns={reviewColumns}
                  dataSource={mockReviews}
                  rowKey="id"
                  pagination={false}
                />
              ),
            },
            {
              key: 'quality',
              label: <span><TrophyOutlined /> {t('tabs.quality')}</span>,
              children: (
                <Table
                  dataSource={mockRanking}
                  rowKey="annotatorId"
                  pagination={false}
                  columns={[
                    {
                      title: t('ranking.rank'),
                      dataIndex: 'rank',
                      render: (rank) => (
                        <span style={{ fontWeight: rank <= 3 ? 'bold' : 'normal', color: rank === 1 ? '#faad14' : undefined }}>
                          {rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : ''} #{rank}
                        </span>
                      ),
                    },
                    { title: t('ranking.annotator'), dataIndex: 'name' },
                    {
                      title: t('ranking.accuracy'),
                      dataIndex: 'accuracy',
                      render: (acc) => <Progress percent={acc * 100} size="small" style={{ width: 120 }} />,
                    },
                    { title: t('ranking.completedTasks'), dataIndex: 'tasksCompleted' },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Review Modal */}
      <Modal
        title={t('review.modalTitle')}
        open={reviewModalOpen}
        onCancel={() => setReviewModalOpen(false)}
        footer={[
          <Button key="reject" danger onClick={() => selectedReview && handleReject(selectedReview)}>
            {t('review.reject')}
          </Button>,
          <Button key="approve" type="primary" onClick={() => selectedReview && handleApprove(selectedReview)}>
            {t('review.approve')}
          </Button>,
        ]}
      >
        {selectedReview && (
          <div>
            <p><strong>{t('review.annotationId')}:</strong> {selectedReview.annotationId}</p>
            <p><strong>{t('review.task')}:</strong> {selectedReview.taskName}</p>
            <p><strong>{t('review.annotator')}:</strong> {selectedReview.annotator}</p>
            <p><strong>{t('review.submittedAt')}:</strong> {selectedReview.submittedAt}</p>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CollaborationPage;
