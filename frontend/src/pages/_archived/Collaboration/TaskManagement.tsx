/**
 * Task Management Interface with AI Routing
 *
 * Provides intelligent task assignment and progress tracking:
 * - AI-assisted task assignment with confidence-based routing
 * - Progress tracking with AI metrics (human vs AI counts)
 * - Team performance dashboard showing human-AI collaboration
 * - Workload balancing and skill-based assignment suggestions
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Form,
  Slider,
  Switch,
  Select,
  Row,
  Col,
  Statistic,
  Tag,
  Progress,
  Space,
  Button,
  Tooltip,
  Badge,
  Alert,
  Divider,
  message,
  Tabs,
} from 'antd';
import {
  ThunderboltOutlined,
  RobotOutlined,
  UserOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  FallOutlined,
  SyncOutlined,
  FilterOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

// Types
interface RoutingConfig {
  lowConfidenceThreshold: number;
  highConfidenceThreshold: number;
  autoAssignHighConfidence: boolean;
  skillBasedRouting: boolean;
  workloadBalancing: boolean;
  reviewLevels: number;
}

interface Task {
  taskId: string;
  title: string;
  projectId: string;
  projectName: string;
  assignedTo?: string;
  assignedBy: 'ai' | 'manual';
  status: 'pending' | 'in_progress' | 'review' | 'completed';
  priority: 'high' | 'medium' | 'low';
  aiSuggestion?: {
    confidence: number;
    suggestedAssignee: string;
    reasoning: string;
  };
  metrics: {
    totalItems: number;
    humanAnnotated: number;
    aiPreAnnotated: number;
    aiSuggested: number;
    reviewRequired: number;
  };
  createdAt: string;
  deadline?: string;
}

interface TeamMember {
  userId: string;
  username: string;
  avatar?: string;
  skills: string[];
  workload: {
    activeTasks: number;
    capacity: number;
  };
  performance: {
    accuracy: number;
    avgSpeed: number; // items per hour
    aiAgreementRate: number;
    tasksCompleted: number;
  };
}

interface AIMetrics {
  totalAnnotations: number;
  humanAnnotations: number;
  aiPreAnnotations: number;
  aiSuggestions: number;
  aiAcceptanceRate: number;
  timeSaved: number; // in hours
  qualityScore: number;
}

const TaskManagement: React.FC = () => {
  const { t } = useTranslation(['task_management', 'common', 'collaboration']);
  const [routingConfig, setRoutingConfig] = useState<RoutingConfig>({
    lowConfidenceThreshold: 0.5,
    highConfidenceThreshold: 0.9,
    autoAssignHighConfidence: false,
    skillBasedRouting: true,
    workloadBalancing: true,
    reviewLevels: 2,
  });
  const [tasks, setTasks] = useState<Task[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [aiMetrics, setAIMetrics] = useState<AIMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string>('all');

  // Fetch initial data
  useEffect(() => {
    fetchTasks();
    fetchTeamMembers();
    fetchAIMetrics();
  }, [selectedProject]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const params = selectedProject !== 'all' ? `?project_id=${selectedProject}` : '';
      const response = await fetch(`/api/v1/annotation/tasks${params}`);
      if (!response.ok) throw new Error('Failed to fetch tasks');
      const data = await response.json();
      setTasks(data.tasks || []);
    } catch (error) {
      message.error(t('task_management:errors.fetch_tasks_failed'));
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await fetch('/api/v1/users/team');
      if (!response.ok) throw new Error('Failed to fetch team');
      const data = await response.json();
      setTeamMembers(data.members || []);
    } catch (error) {
      console.error('Failed to fetch team members:', error);
    }
  };

  const fetchAIMetrics = async () => {
    try {
      const params = selectedProject !== 'all' ? `?project_id=${selectedProject}` : '';
      const response = await fetch(`/api/v1/annotation/metrics${params}`);
      if (!response.ok) throw new Error('Failed to fetch metrics');
      const data = await response.json();
      setAIMetrics(data.metrics || null);
    } catch (error) {
      console.error('Failed to fetch AI metrics:', error);
    }
  };

  const handleAssignTask = async (taskId: string, assigneeId: string) => {
    try {
      const response = await fetch('/api/v1/annotation/tasks/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          assignee_id: assigneeId,
        }),
      });

      if (!response.ok) throw new Error('Failed to assign task');

      message.success(t('task_management:messages.task_assigned'));
      fetchTasks();
    } catch (error) {
      message.error(t('task_management:errors.assign_failed'));
      console.error('Failed to assign task:', error);
    }
  };

  const handleUpdateRoutingConfig = async (updates: Partial<RoutingConfig>) => {
    const newConfig = { ...routingConfig, ...updates };
    setRoutingConfig(newConfig);

    try {
      const response = await fetch('/api/v1/annotation/routing/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig),
      });

      if (!response.ok) throw new Error('Failed to update config');
      message.success(t('task_management:messages.config_updated'));
    } catch (error) {
      message.error(t('task_management:errors.config_update_failed'));
      console.error('Failed to update routing config:', error);
    }
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'high': return 'red';
      case 'medium': return 'orange';
      case 'low': return 'blue';
      default: return 'default';
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return 'success';
      case 'in_progress': return 'processing';
      case 'review': return 'warning';
      default: return 'default';
    }
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return '#52c41a';
    if (confidence >= 0.7) return '#1890ff';
    if (confidence >= 0.5) return '#faad14';
    return '#ff4d4f';
  };

  const taskColumns: ColumnsType<Task> = [
    {
      title: t('task_management:columns.task_id'),
      dataIndex: 'taskId',
      key: 'taskId',
      width: 120,
      render: (id) => <a>{id}</a>,
    },
    {
      title: t('task_management:columns.title'),
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: t('task_management:columns.project'),
      dataIndex: 'projectName',
      key: 'projectName',
    },
    {
      title: t('task_management:columns.assignee'),
      dataIndex: 'assignedTo',
      key: 'assignedTo',
      render: (assignee, record) => (
        <Space>
          {assignee ? (
            <>
              <Badge dot color={record.assignedBy === 'ai' ? '#1890ff' : '#52c41a'}>
                <UserOutlined />
              </Badge>
              {assignee}
            </>
          ) : (
            <Tag color="default">{t('task_management:labels.unassigned')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('task_management:columns.ai_suggestion'),
      key: 'aiSuggestion',
      render: (_, record) => {
        if (!record.aiSuggestion) return '-';
        return (
          <Tooltip
            title={
              <div>
                <div><strong>{t('task_management:labels.suggested_assignee')}:</strong> {record.aiSuggestion.suggestedAssignee}</div>
                <div><strong>{t('task_management:labels.reasoning')}:</strong> {record.aiSuggestion.reasoning}</div>
              </div>
            }
          >
            <Tag
              icon={<RobotOutlined />}
              color={record.aiSuggestion.confidence >= routingConfig.highConfidenceThreshold ? 'green' : 'blue'}
            >
              {(record.aiSuggestion.confidence * 100).toFixed(0)}%
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: t('task_management:columns.progress'),
      key: 'progress',
      render: (_, record) => {
        const total = record.metrics.totalItems;
        const completed = record.metrics.humanAnnotated + record.metrics.aiPreAnnotated;
        const percentage = total > 0 ? (completed / total) * 100 : 0;
        return (
          <Tooltip
            title={
              <div>
                <div>{t('task_management:labels.human_annotated')}: {record.metrics.humanAnnotated}</div>
                <div>{t('task_management:labels.ai_pre_annotated')}: {record.metrics.aiPreAnnotated}</div>
                <div>{t('task_management:labels.ai_suggested')}: {record.metrics.aiSuggested}</div>
                <div>{t('task_management:labels.review_required')}: {record.metrics.reviewRequired}</div>
              </div>
            }
          >
            <Progress percent={percentage} size="small" style={{ width: 100 }} />
          </Tooltip>
        );
      },
    },
    {
      title: t('task_management:columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Badge
          status={getStatusColor(status)}
          text={t(`task_management:status.${status}`)}
        />
      ),
    },
    {
      title: t('task_management:columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => (
        <Tag color={getPriorityColor(priority)}>
          {t(`task_management:priority.${priority}`)}
        </Tag>
      ),
    },
    {
      title: t('common:actions.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          {!record.assignedTo && record.aiSuggestion && (
            <Button
              type="link"
              size="small"
              icon={<RobotOutlined />}
              onClick={() => handleAssignTask(record.taskId, record.aiSuggestion!.suggestedAssignee)}
            >
              {t('task_management:actions.accept_ai_suggestion')}
            </Button>
          )}
          <Select
            size="small"
            placeholder={t('task_management:actions.assign_manually')}
            style={{ width: 150 }}
            onChange={(value) => handleAssignTask(record.taskId, value)}
            options={teamMembers.map((member) => ({
              value: member.userId,
              label: member.username,
            }))}
          />
        </Space>
      ),
    },
  ];

  const teamColumns: ColumnsType<TeamMember> = [
    {
      title: t('task_management:columns.member'),
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: t('task_management:columns.skills'),
      dataIndex: 'skills',
      key: 'skills',
      render: (skills: string[]) => (
        <>
          {skills.map((skill) => (
            <Tag key={skill} color="blue" style={{ marginBottom: 4 }}>
              {skill}
            </Tag>
          ))}
        </>
      ),
    },
    {
      title: t('task_management:columns.workload'),
      key: 'workload',
      render: (_, record) => {
        const percentage = (record.workload.activeTasks / record.workload.capacity) * 100;
        return (
          <Space>
            <Progress
              type="circle"
              percent={percentage}
              width={40}
              status={percentage > 80 ? 'exception' : 'normal'}
            />
            <span>{record.workload.activeTasks}/{record.workload.capacity}</span>
          </Space>
        );
      },
    },
    {
      title: t('task_management:columns.accuracy'),
      dataIndex: ['performance', 'accuracy'],
      key: 'accuracy',
      render: (accuracy) => (
        <Tag color={accuracy >= 0.9 ? 'green' : accuracy >= 0.7 ? 'blue' : 'orange'}>
          {(accuracy * 100).toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: t('task_management:columns.ai_agreement'),
      dataIndex: ['performance', 'aiAgreementRate'],
      key: 'aiAgreementRate',
      render: (rate) => (
        <Tag color={rate >= 0.8 ? 'green' : rate >= 0.6 ? 'blue' : 'orange'}>
          {(rate * 100).toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: t('task_management:columns.tasks_completed'),
      dataIndex: ['performance', 'tasksCompleted'],
      key: 'tasksCompleted',
    },
    {
      title: t('task_management:columns.avg_speed'),
      dataIndex: ['performance', 'avgSpeed'],
      key: 'avgSpeed',
      render: (speed) => `${speed.toFixed(1)} ${t('task_management:labels.items_per_hour')}`,
    },
  ];

  return (
    <div className="task-management">
      <h2 style={{ marginBottom: 24 }}>
        <RobotOutlined /> {t('task_management:title')}
      </h2>

      {/* AI Metrics Overview */}
      {aiMetrics && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.total_annotations')}
                value={aiMetrics.totalAnnotations}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.human_annotations')}
                value={aiMetrics.humanAnnotations}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.ai_annotations')}
                value={aiMetrics.aiPreAnnotations}
                prefix={<RobotOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.ai_acceptance_rate')}
                value={(aiMetrics.aiAcceptanceRate * 100).toFixed(1)}
                suffix="%"
                prefix={
                  aiMetrics.aiAcceptanceRate >= 0.7 ? (
                    <RiseOutlined style={{ color: '#52c41a' }} />
                  ) : (
                    <FallOutlined style={{ color: '#ff4d4f' }} />
                  )
                }
                valueStyle={{
                  color: aiMetrics.aiAcceptanceRate >= 0.7 ? '#52c41a' : '#ff4d4f',
                }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.time_saved')}
                value={aiMetrics.timeSaved.toFixed(1)}
                suffix={t('task_management:labels.hours')}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.quality_score')}
                value={(aiMetrics.qualityScore * 100).toFixed(1)}
                suffix="%"
                prefix={<ThunderboltOutlined />}
                valueStyle={{
                  color: aiMetrics.qualityScore >= 0.9 ? '#52c41a' : '#1890ff',
                }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Tabs
        defaultActiveKey="tasks"
        items={[
          {
            key: 'tasks',
            label: (
              <span>
                <TeamOutlined /> {t('task_management:tabs.task_queue')}
              </span>
            ),
            children: (
              <>
                {/* Filters */}
                <Space style={{ marginBottom: 16 }}>
                  <Select
                    style={{ width: 200 }}
                    placeholder={t('task_management:filters.select_project')}
                    value={selectedProject}
                    onChange={setSelectedProject}
                    options={[
                      { value: 'all', label: t('task_management:filters.all_projects') },
                      // Add more project options dynamically
                    ]}
                  />
                  <Button icon={<SyncOutlined />} onClick={fetchTasks}>
                    {t('common:actions.refresh')}
                  </Button>
                </Space>

                {/* Task Queue Table */}
                <Table
                  columns={taskColumns}
                  dataSource={tasks}
                  rowKey="taskId"
                  loading={loading}
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => t('common:pagination.total', { total }),
                  }}
                />
              </>
            ),
          },
          {
            key: 'team',
            label: (
              <span>
                <UserOutlined /> {t('task_management:tabs.team_performance')}
              </span>
            ),
            children: (
              <Table
                columns={teamColumns}
                dataSource={teamMembers}
                rowKey="userId"
                pagination={false}
              />
            ),
          },
          {
            key: 'routing',
            label: (
              <span>
                <SettingOutlined /> {t('task_management:tabs.ai_routing_config')}
              </span>
            ),
            children: (
              <Card title={t('task_management:config.routing_title')}>
                <Alert
                  message={t('task_management:config.routing_description')}
                  type="info"
                  showIcon
                  style={{ marginBottom: 24 }}
                />

                <Form layout="vertical">
                  <Row gutter={24}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label={t('task_management:config.low_confidence_threshold')}
                        tooltip={t('task_management:config.low_confidence_tooltip')}
                      >
                        <Slider
                          min={0}
                          max={1}
                          step={0.05}
                          value={routingConfig.lowConfidenceThreshold}
                          onChange={(value) =>
                            handleUpdateRoutingConfig({ lowConfidenceThreshold: value })
                          }
                          marks={{
                            0: '0%',
                            0.5: '50%',
                            1: '100%',
                          }}
                        />
                      </Form.Item>
                    </Col>

                    <Col xs={24} md={12}>
                      <Form.Item
                        label={t('task_management:config.high_confidence_threshold')}
                        tooltip={t('task_management:config.high_confidence_tooltip')}
                      >
                        <Slider
                          min={0}
                          max={1}
                          step={0.05}
                          value={routingConfig.highConfidenceThreshold}
                          onChange={(value) =>
                            handleUpdateRoutingConfig({ highConfidenceThreshold: value })
                          }
                          marks={{
                            0: '0%',
                            0.5: '50%',
                            1: '100%',
                          }}
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Divider />

                  <Row gutter={24}>
                    <Col xs={24} md={8}>
                      <Form.Item
                        label={t('task_management:config.auto_assign_high_confidence')}
                        tooltip={t('task_management:config.auto_assign_tooltip')}
                      >
                        <Switch
                          checked={routingConfig.autoAssignHighConfidence}
                          onChange={(checked) =>
                            handleUpdateRoutingConfig({ autoAssignHighConfidence: checked })
                          }
                        />
                      </Form.Item>
                    </Col>

                    <Col xs={24} md={8}>
                      <Form.Item
                        label={t('task_management:config.skill_based_routing')}
                        tooltip={t('task_management:config.skill_based_tooltip')}
                      >
                        <Switch
                          checked={routingConfig.skillBasedRouting}
                          onChange={(checked) =>
                            handleUpdateRoutingConfig({ skillBasedRouting: checked })
                          }
                        />
                      </Form.Item>
                    </Col>

                    <Col xs={24} md={8}>
                      <Form.Item
                        label={t('task_management:config.workload_balancing')}
                        tooltip={t('task_management:config.workload_balancing_tooltip')}
                      >
                        <Switch
                          checked={routingConfig.workloadBalancing}
                          onChange={(checked) =>
                            handleUpdateRoutingConfig({ workloadBalancing: checked })
                          }
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                </Form>
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
};

export default TaskManagement;
