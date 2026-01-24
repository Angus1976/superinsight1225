/**
 * AI Annotation Task Management Component
 *
 * Manages annotation tasks with AI assistance:
 * - Task assignment UI
 * - Progress tracking display
 * - Workload statistics
 * - AI-assisted task routing
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Progress,
  Modal,
  Form,
  Select,
  DatePicker,
  Row,
  Col,
  Statistic,
  Badge,
  Avatar,
  Tooltip,
  message,
  Tabs,
  List,
  Empty,
} from 'antd';
import {
  UserOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  PlusOutlined,
  RobotOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

// Types
export interface AnnotationTask {
  taskId: string;
  title: string;
  projectId: string;
  projectName: string;
  assignedTo?: string;
  assignedBy: 'manual' | 'ai';
  status: 'pending' | 'in_progress' | 'review' | 'completed';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  deadline?: string;
  metrics: TaskMetrics;
  createdAt: string;
}

export interface TaskMetrics {
  totalItems: number;
  humanAnnotated: number;
  aiPreAnnotated: number;
  aiSuggested: number;
  reviewRequired: number;
}

export interface Annotator {
  id: string;
  name: string;
  avatar?: string;
  role: 'annotator' | 'reviewer' | 'admin';
  status: 'available' | 'busy' | 'offline';
  currentTasks: number;
  completedToday: number;
  accuracy: number;
  skills: string[];
}

export interface WorkloadStats {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  pendingTasks: number;
  avgCompletionTime: number;
  activeAnnotators: number;
  activeReviewers: number;
}

interface TaskManagementProps {
  projectId?: string;
  onTaskSelect?: (task: AnnotationTask) => void;
}


const TaskManagement: React.FC<TaskManagementProps> = ({
  projectId,
  onTaskSelect,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<AnnotationTask[]>([]);
  const [annotators, setAnnotators] = useState<Annotator[]>([]);
  const [stats, setStats] = useState<WorkloadStats | null>(null);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<AnnotationTask | null>(null);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('tasks');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  useEffect(() => {
    loadTasks();
    loadAnnotators();
    loadStats();
  }, [projectId, statusFilter]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      if (statusFilter) params.append('status', statusFilter);
      params.append('page', '1');
      params.append('page_size', '50');

      const response = await fetch(`/api/v1/annotation/tasks?${params}`);
      if (response.ok) {
        const data = await response.json();
        setTasks(data.tasks || []);
      }
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAnnotators = async () => {
    // Mock data - in production, fetch from API
    setAnnotators([
      {
        id: 'user_1',
        name: 'Alice Chen',
        role: 'annotator',
        status: 'available',
        currentTasks: 2,
        completedToday: 15,
        accuracy: 0.95,
        skills: ['NER', 'Classification'],
      },
      {
        id: 'user_2',
        name: 'Bob Wang',
        role: 'annotator',
        status: 'busy',
        currentTasks: 5,
        completedToday: 12,
        accuracy: 0.92,
        skills: ['NER', 'Relation'],
      },
      {
        id: 'user_3',
        name: 'Carol Li',
        role: 'reviewer',
        status: 'available',
        currentTasks: 3,
        completedToday: 20,
        accuracy: 0.98,
        skills: ['NER', 'Classification', 'QA'],
      },
    ]);
  };

  const loadStats = async () => {
    try {
      if (projectId) {
        const response = await fetch(`/api/v1/annotation/progress/${projectId}`);
        if (response.ok) {
          const data = await response.json();
          setStats({
            totalTasks: data.total_tasks || data.totalTasks,
            completedTasks: data.completed_tasks || data.completedTasks,
            inProgressTasks: data.in_progress_tasks || data.inProgressTasks,
            pendingTasks: data.pending_tasks || data.pendingTasks,
            avgCompletionTime: data.avg_time_per_task_minutes || data.avgTimePerTaskMinutes,
            activeAnnotators: data.active_annotators || data.activeAnnotators,
            activeReviewers: data.active_reviewers || data.activeReviewers,
          });
        }
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleAssignTask = async () => {
    if (!selectedTask) return;

    try {
      const values = await form.validateFields();
      const response = await fetch('/api/v1/annotation/tasks/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: selectedTask.taskId,
          user_id: values.userId,
          priority: values.priority,
          deadline: values.deadline?.toISOString(),
        }),
      });

      if (response.ok) {
        message.success(t('ai_annotation:tasks.assign_success'));
        setAssignModalOpen(false);
        form.resetFields();
        loadTasks();
      } else {
        throw new Error('Failed to assign task');
      }
    } catch (error) {
      message.error(t('ai_annotation:tasks.assign_failed'));
    }
  };

  const handleAutoAssign = async (task: AnnotationTask) => {
    try {
      const response = await fetch('/api/v1/annotation/tasks/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task.taskId,
          role: 'annotator',
          priority: task.priority,
        }),
      });

      if (response.ok) {
        message.success(t('ai_annotation:tasks.auto_assign_success'));
        loadTasks();
      } else {
        throw new Error('Failed to auto-assign task');
      }
    } catch (error) {
      message.error(t('ai_annotation:tasks.auto_assign_failed'));
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return 'success';
      case 'in_progress': return 'processing';
      case 'review': return 'warning';
      case 'pending': return 'default';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'urgent': return 'red';
      case 'high': return 'orange';
      case 'normal': return 'blue';
      case 'low': return 'default';
      default: return 'default';
    }
  };

  const getAnnotatorStatusColor = (status: string): string => {
    switch (status) {
      case 'available': return '#52c41a';
      case 'busy': return '#faad14';
      case 'offline': return '#999';
      default: return '#999';
    }
  };

  const taskColumns: ColumnsType<AnnotationTask> = [
    {
      title: t('ai_annotation:tasks.title'),
      dataIndex: 'title',
      key: 'title',
      render: (title: string, record: AnnotationTask) => (
        <a onClick={() => onTaskSelect?.(record)}>{title}</a>
      ),
    },
    {
      title: t('ai_annotation:tasks.project'),
      dataIndex: 'projectName',
      key: 'projectName',
    },
    {
      title: t('ai_annotation:tasks.assigned_to'),
      dataIndex: 'assignedTo',
      key: 'assignedTo',
      render: (assignedTo: string | undefined, record: AnnotationTask) => (
        assignedTo ? (
          <Space>
            <Avatar size="small" icon={<UserOutlined />} />
            <span>{assignedTo}</span>
            {record.assignedBy === 'ai' && (
              <Tooltip title={t('ai_annotation:tasks.ai_assigned')}>
                <RobotOutlined style={{ color: '#1890ff' }} />
              </Tooltip>
            )}
          </Space>
        ) : (
          <Tag>{t('ai_annotation:tasks.unassigned')}</Tag>
        )
      ),
    },
    {
      title: t('ai_annotation:tasks.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Badge status={getStatusColor(status) as any} text={t(`ai_annotation:tasks.status_${status}`)} />
      ),
      filters: [
        { text: t('ai_annotation:tasks.status_pending'), value: 'pending' },
        { text: t('ai_annotation:tasks.status_in_progress'), value: 'in_progress' },
        { text: t('ai_annotation:tasks.status_review'), value: 'review' },
        { text: t('ai_annotation:tasks.status_completed'), value: 'completed' },
      ],
    },
    {
      title: t('ai_annotation:tasks.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>
          {t(`ai_annotation:tasks.priority_${priority}`)}
        </Tag>
      ),
    },
    {
      title: t('ai_annotation:tasks.progress'),
      key: 'progress',
      render: (_, record: AnnotationTask) => {
        const total = record.metrics.totalItems;
        const completed = record.metrics.humanAnnotated + record.metrics.aiPreAnnotated;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
        return (
          <Tooltip title={`${completed}/${total}`}>
            <Progress percent={percent} size="small" style={{ width: 100 }} />
          </Tooltip>
        );
      },
    },
    {
      title: t('ai_annotation:tasks.deadline'),
      dataIndex: 'deadline',
      key: 'deadline',
      render: (deadline?: string) =>
        deadline ? dayjs(deadline).format('YYYY-MM-DD') : '-',
    },
    {
      title: t('common:columns.actions'),
      key: 'actions',
      render: (_, record: AnnotationTask) => (
        <Space>
          {!record.assignedTo && (
            <>
              <Button
                size="small"
                onClick={() => {
                  setSelectedTask(record);
                  setAssignModalOpen(true);
                }}
              >
                {t('ai_annotation:tasks.assign')}
              </Button>
              <Tooltip title={t('ai_annotation:tasks.auto_assign_tooltip')}>
                <Button
                  size="small"
                  icon={<RobotOutlined />}
                  onClick={() => handleAutoAssign(record)}
                >
                  {t('ai_annotation:tasks.auto_assign')}
                </Button>
              </Tooltip>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="task-management">
      {/* Stats Overview */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('ai_annotation:tasks.total_tasks')}
                value={stats.totalTasks}
                prefix={<BarChartOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('ai_annotation:tasks.completed')}
                value={stats.completedTasks}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('ai_annotation:tasks.in_progress')}
                value={stats.inProgressTasks}
                prefix={<SyncOutlined spin />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('ai_annotation:tasks.active_annotators')}
                value={stats.activeAnnotators}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Main Content */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'tasks',
              label: (
                <span>
                  <ThunderboltOutlined /> {t('ai_annotation:tasks.tab_tasks')}
                </span>
              ),
              children: (
                <Table
                  dataSource={tasks}
                  columns={taskColumns}
                  rowKey="taskId"
                  loading={loading}
                  pagination={{ pageSize: 10 }}
                />
              ),
            },
            {
              key: 'annotators',
              label: (
                <span>
                  <TeamOutlined /> {t('ai_annotation:tasks.tab_annotators')}
                </span>
              ),
              children: (
                <List
                  dataSource={annotators}
                  renderItem={(annotator) => (
                    <List.Item
                      actions={[
                        <Statistic
                          key="tasks"
                          title={t('ai_annotation:tasks.current_tasks')}
                          value={annotator.currentTasks}
                        />,
                        <Statistic
                          key="completed"
                          title={t('ai_annotation:tasks.completed_today')}
                          value={annotator.completedToday}
                        />,
                        <Statistic
                          key="accuracy"
                          title={t('ai_annotation:tasks.accuracy')}
                          value={(annotator.accuracy * 100).toFixed(0)}
                          suffix="%"
                        />,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={
                          <Badge dot color={getAnnotatorStatusColor(annotator.status)}>
                            <Avatar icon={<UserOutlined />} src={annotator.avatar} />
                          </Badge>
                        }
                        title={
                          <Space>
                            {annotator.name}
                            <Tag>{t(`ai_annotation:tasks.role_${annotator.role}`)}</Tag>
                          </Space>
                        }
                        description={
                          <Space>
                            {annotator.skills.map((skill) => (
                              <Tag key={skill} color="blue">{skill}</Tag>
                            ))}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Assign Task Modal */}
      <Modal
        title={t('ai_annotation:tasks.assign_task')}
        open={assignModalOpen}
        onOk={handleAssignTask}
        onCancel={() => {
          setAssignModalOpen(false);
          form.resetFields();
        }}
        okText={t('common:actions.confirm')}
        cancelText={t('common:actions.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="userId"
            label={t('ai_annotation:tasks.select_annotator')}
            rules={[{ required: true }]}
          >
            <Select placeholder={t('ai_annotation:tasks.select_annotator_placeholder')}>
              {annotators
                .filter((a) => a.status !== 'offline')
                .map((annotator) => (
                  <Select.Option key={annotator.id} value={annotator.id}>
                    <Space>
                      <Badge dot color={getAnnotatorStatusColor(annotator.status)} />
                      {annotator.name}
                      <Tag>{annotator.currentTasks} {t('ai_annotation:tasks.tasks')}</Tag>
                    </Space>
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="priority"
            label={t('ai_annotation:tasks.priority')}
            initialValue="normal"
          >
            <Select>
              <Select.Option value="low">{t('ai_annotation:tasks.priority_low')}</Select.Option>
              <Select.Option value="normal">{t('ai_annotation:tasks.priority_normal')}</Select.Option>
              <Select.Option value="high">{t('ai_annotation:tasks.priority_high')}</Select.Option>
              <Select.Option value="urgent">{t('ai_annotation:tasks.priority_urgent')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="deadline"
            label={t('ai_annotation:tasks.deadline')}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TaskManagement;
