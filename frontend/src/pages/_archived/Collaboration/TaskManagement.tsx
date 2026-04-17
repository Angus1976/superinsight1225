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

import type { AIMetrics, RoutingConfig } from '@/services/aiAnnotationApi';
import { fetchJsonBody, fetchJsonResponseToSnake } from '@/utils/jsonCase';

interface Task {
  task_id: string;
  title: string;
  project_id: string;
  project_name: string;
  assigned_to?: string;
  assigned_by: 'ai' | 'manual';
  status: 'pending' | 'in_progress' | 'review' | 'completed';
  priority: 'high' | 'medium' | 'low';
  ai_suggestion?: {
    confidence: number;
    suggested_assignee: string;
    reasoning: string;
  };
  metrics: {
    total_items: number;
    human_annotated: number;
    ai_pre_annotated: number;
    ai_suggested: number;
    review_required: number;
  };
  created_at: string;
  deadline?: string;
}

interface TeamMember {
  user_id: string;
  username: string;
  avatar?: string;
  skills: string[];
  workload: {
    active_tasks: number;
    capacity: number;
  };
  performance: {
    accuracy: number;
    avg_speed: number;
    ai_agreement_rate: number;
    tasks_completed: number;
  };
}

const TaskManagement: React.FC = () => {
  const { t } = useTranslation(['task_management', 'common', 'collaboration']);
  const [routingConfig, setRoutingConfig] = useState<RoutingConfig>({
    low_confidence_threshold: 0.5,
    high_confidence_threshold: 0.9,
    auto_assign_high_confidence: false,
    skill_based_routing: true,
    workload_balancing: true,
    review_levels: 2,
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
      const data = await fetchJsonResponseToSnake<{ tasks?: Task[] }>(response);
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
      const data = await fetchJsonResponseToSnake<{ members?: TeamMember[] }>(response);
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
      const data = await fetchJsonResponseToSnake<{ metrics?: AIMetrics }>(response);
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
        body: fetchJsonBody({
          task_id: taskId,
          user_id: assigneeId,
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
        body: fetchJsonBody(newConfig),
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
      dataIndex: 'task_id',
      key: 'task_id',
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
      dataIndex: 'project_name',
      key: 'project_name',
    },
    {
      title: t('task_management:columns.assignee'),
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      render: (assignee, record) => (
        <Space>
          {assignee ? (
            <>
              <Badge dot color={record.assigned_by === 'ai' ? '#1890ff' : '#52c41a'}>
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
      key: 'ai_suggestion',
      render: (_, record) => {
        if (!record.ai_suggestion) return '-';
        return (
          <Tooltip
            title={
              <div>
                <div><strong>{t('task_management:labels.suggested_assignee')}:</strong> {record.ai_suggestion.suggested_assignee}</div>
                <div><strong>{t('task_management:labels.reasoning')}:</strong> {record.ai_suggestion.reasoning}</div>
              </div>
            }
          >
            <Tag
              icon={<RobotOutlined />}
              color={record.ai_suggestion.confidence >= routingConfig.high_confidence_threshold ? 'green' : 'blue'}
            >
              {(record.ai_suggestion.confidence * 100).toFixed(0)}%
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: t('task_management:columns.progress'),
      key: 'progress',
      render: (_, record) => {
        const total = record.metrics.total_items;
        const completed = record.metrics.human_annotated + record.metrics.ai_pre_annotated;
        const percentage = total > 0 ? (completed / total) * 100 : 0;
        return (
          <Tooltip
            title={
              <div>
                <div>{t('task_management:labels.human_annotated')}: {record.metrics.human_annotated}</div>
                <div>{t('task_management:labels.ai_pre_annotated')}: {record.metrics.ai_pre_annotated}</div>
                <div>{t('task_management:labels.ai_suggested')}: {record.metrics.ai_suggested}</div>
                <div>{t('task_management:labels.review_required')}: {record.metrics.review_required}</div>
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
          {!record.assigned_to && record.ai_suggestion && (
            <Button
              type="link"
              size="small"
              icon={<RobotOutlined />}
              onClick={() => handleAssignTask(record.task_id, record.ai_suggestion!.suggested_assignee)}
            >
              {t('task_management:actions.accept_ai_suggestion')}
            </Button>
          )}
          <Select
            size="small"
            placeholder={t('task_management:actions.assign_manually')}
            style={{ width: 150 }}
            onChange={(value) => handleAssignTask(record.task_id, value)}
            options={teamMembers.map((member) => ({
              value: member.user_id,
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
        const percentage = (record.workload.active_tasks / record.workload.capacity) * 100;
        return (
          <Space>
            <Progress
              type="circle"
              percent={percentage}
              width={40}
              status={percentage > 80 ? 'exception' : 'normal'}
            />
            <span>{record.workload.active_tasks}/{record.workload.capacity}</span>
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
      dataIndex: ['performance', 'ai_agreement_rate'],
      key: 'ai_agreement_rate',
      render: (rate) => (
        <Tag color={rate >= 0.8 ? 'green' : rate >= 0.6 ? 'blue' : 'orange'}>
          {(rate * 100).toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: t('task_management:columns.tasks_completed'),
      dataIndex: ['performance', 'tasks_completed'],
      key: 'tasks_completed',
    },
    {
      title: t('task_management:columns.avg_speed'),
      dataIndex: ['performance', 'avg_speed'],
      key: 'avg_speed',
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
                value={aiMetrics.total_annotations}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.human_annotations')}
                value={aiMetrics.human_annotations}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.ai_annotations')}
                value={aiMetrics.ai_pre_annotations}
                prefix={<RobotOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.ai_acceptance_rate')}
                value={(aiMetrics.ai_acceptance_rate * 100).toFixed(1)}
                suffix="%"
                prefix={
                  aiMetrics.ai_acceptance_rate >= 0.7 ? (
                    <RiseOutlined style={{ color: '#52c41a' }} />
                  ) : (
                    <FallOutlined style={{ color: '#ff4d4f' }} />
                  )
                }
                valueStyle={{
                  color: aiMetrics.ai_acceptance_rate >= 0.7 ? '#52c41a' : '#ff4d4f',
                }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Card>
              <Statistic
                title={t('task_management:metrics.time_saved')}
                value={aiMetrics.time_saved_hours.toFixed(1)}
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
                value={(aiMetrics.quality_score * 100).toFixed(1)}
                suffix="%"
                prefix={<ThunderboltOutlined />}
                valueStyle={{
                  color: aiMetrics.quality_score >= 0.9 ? '#52c41a' : '#1890ff',
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
                  rowKey="task_id"
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
                rowKey="user_id"
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
                          value={routingConfig.low_confidence_threshold}
                          onChange={(value) =>
                            handleUpdateRoutingConfig({ low_confidence_threshold: value })
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
                          value={routingConfig.high_confidence_threshold}
                          onChange={(value) =>
                            handleUpdateRoutingConfig({ high_confidence_threshold: value })
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
                          checked={routingConfig.auto_assign_high_confidence}
                          onChange={(checked) =>
                            handleUpdateRoutingConfig({ auto_assign_high_confidence: checked })
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
                          checked={routingConfig.skill_based_routing}
                          onChange={(checked) =>
                            handleUpdateRoutingConfig({ skill_based_routing: checked })
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
                          checked={routingConfig.workload_balancing}
                          onChange={(checked) =>
                            handleUpdateRoutingConfig({ workload_balancing: checked })
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
