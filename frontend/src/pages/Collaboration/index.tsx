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

const statusLabels = {
  pending: '待处理',
  in_progress: '进行中',
  review: '审核中',
  completed: '已完成',
};

const memberStatusColors = {
  online: '#52c41a',
  busy: '#faad14',
  offline: '#999',
};

const CollaborationPage: React.FC = () => {
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null);

  const handleApprove = (review: ReviewItem) => {
    message.success(`已通过标注 ${review.annotationId}`);
    setReviewModalOpen(false);
  };

  const handleReject = (review: ReviewItem) => {
    message.warning(`已驳回标注 ${review.annotationId}`);
    setReviewModalOpen(false);
  };

  const taskColumns: ColumnsType<TaskItem> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name) => <a>{name}</a>,
    },
    {
      title: '负责人',
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: keyof typeof statusColors) => (
        <Badge status={statusColors[status]} text={statusLabels[status]} />
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => (
        <Tag color={priority === 1 ? 'red' : priority === 2 ? 'orange' : 'blue'}>
          P{priority}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress) => <Progress percent={progress} size="small" style={{ width: 100 }} />,
    },
    {
      title: '截止日期',
      dataIndex: 'deadline',
      key: 'deadline',
      render: (date) => date || '-',
    },
  ];

  const reviewColumns: ColumnsType<ReviewItem> = [
    {
      title: '标注ID',
      dataIndex: 'annotationId',
      key: 'annotationId',
    },
    {
      title: '任务',
      dataIndex: 'taskName',
      key: 'taskName',
    },
    {
      title: '标注员',
      dataIndex: 'annotator',
      key: 'annotator',
    },
    {
      title: '提交时间',
      dataIndex: 'submittedAt',
      key: 'submittedAt',
    },
    {
      title: '审核级别',
      dataIndex: 'level',
      key: 'level',
      render: (level) => <Tag>L{level}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'approved' ? 'success' : status === 'rejected' ? 'error' : 'default'}>
          {status === 'approved' ? '已通过' : status === 'rejected' ? '已驳回' : '待审核'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        record.status === 'pending' && (
          <Space>
            <Button type="link" size="small" onClick={() => { setSelectedReview(record); setReviewModalOpen(true); }}>
              审核
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
      <h2 style={{ marginBottom: 24 }}>协作与审核</h2>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="进行中任务"
              value={mockTasks.filter(t => t.status === 'in_progress').length}
              prefix={<SyncOutlined spin />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="待审核"
              value={pendingReviews}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: pendingReviews > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="在线成员"
              value={onlineMembers}
              suffix={`/ ${mockTeam.length}`}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="平均准确率"
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
              label: <span><FileTextOutlined /> 任务列表</span>,
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
              label: <span><TeamOutlined /> 团队状态</span>,
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
                        description={member.currentTask ? `正在处理: ${member.currentTask}` : '空闲'}
                      />
                      <Space size="large">
                        <Statistic title="完成任务" value={member.tasksCompleted} />
                        <Statistic title="准确率" value={(member.accuracy * 100).toFixed(1)} suffix="%" />
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
                  <AuditOutlined /> 审核队列
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
              label: <span><TrophyOutlined /> 质量排名</span>,
              children: (
                <Table
                  dataSource={mockRanking}
                  rowKey="annotatorId"
                  pagination={false}
                  columns={[
                    {
                      title: '排名',
                      dataIndex: 'rank',
                      render: (rank) => (
                        <span style={{ fontWeight: rank <= 3 ? 'bold' : 'normal', color: rank === 1 ? '#faad14' : undefined }}>
                          {rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : ''} #{rank}
                        </span>
                      ),
                    },
                    { title: '标注员', dataIndex: 'name' },
                    {
                      title: '准确率',
                      dataIndex: 'accuracy',
                      render: (acc) => <Progress percent={acc * 100} size="small" style={{ width: 120 }} />,
                    },
                    { title: '完成任务', dataIndex: 'tasksCompleted' },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Review Modal */}
      <Modal
        title="审核标注"
        open={reviewModalOpen}
        onCancel={() => setReviewModalOpen(false)}
        footer={[
          <Button key="reject" danger onClick={() => selectedReview && handleReject(selectedReview)}>
            驳回
          </Button>,
          <Button key="approve" type="primary" onClick={() => selectedReview && handleApprove(selectedReview)}>
            通过
          </Button>,
        ]}
      >
        {selectedReview && (
          <div>
            <p><strong>标注ID:</strong> {selectedReview.annotationId}</p>
            <p><strong>任务:</strong> {selectedReview.taskName}</p>
            <p><strong>标注员:</strong> {selectedReview.annotator}</p>
            <p><strong>提交时间:</strong> {selectedReview.submittedAt}</p>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CollaborationPage;
