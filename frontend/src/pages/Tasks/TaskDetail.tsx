// Task detail page
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Tag,
  Progress,
  Space,
  Button,
  Skeleton,
  Alert,
  Timeline,
  Divider,
  Row,
  Col,
  Statistic,
  Tabs,
  Badge,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  TeamOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTask, useUpdateTask, useDeleteTask } from '@/hooks/useTask';
import { usePermissions } from '@/hooks/usePermissions';
import { ProgressTracker } from '@/components/Tasks';
import type { TaskStatus, TaskPriority } from '@/types';

const statusColorMap: Record<TaskStatus, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  cancelled: 'error',
};

const priorityColorMap: Record<TaskPriority, string> = {
  low: 'green',
  medium: 'blue',
  high: 'orange',
  urgent: 'red',
};

const TaskDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation('tasks');
  const { data: task, isLoading, error } = useTask(id || '');
  const { annotation: annotationPerms } = usePermissions();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  // Mock data for development
  const mockTask = {
    id: id || '1',
    name: 'Customer Review Classification',
    description:
      'Classify customer reviews by sentiment to understand customer satisfaction levels. This task involves analyzing text reviews and categorizing them as positive, negative, or neutral.',
    status: 'in_progress' as TaskStatus,
    priority: 'high' as TaskPriority,
    annotation_type: 'sentiment' as const,
    assignee_id: 'user1',
    assignee_name: 'John Doe',
    created_by: 'admin',
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-20T14:30:00Z',
    due_date: '2025-02-01T00:00:00Z',
    progress: 65,
    total_items: 1000,
    completed_items: 650,
    tenant_id: 'tenant1',
    label_studio_project_id: 'ls-project-123',
    tags: ['urgent', 'customer', 'sentiment'],
  };

  const currentTask = task || mockTask;

  const handleStatusChange = async (newStatus: TaskStatus) => {
    if (id) {
      await updateTask.mutateAsync({ id, payload: { status: newStatus } });
    }
  };

  const handleDelete = async () => {
    if (id) {
      await deleteTask.mutateAsync(id);
      navigate('/tasks');
    }
  };

  const handleProgressUpdate = (progressData: any) => {
    console.log('Progress updated:', progressData);
    // Handle real-time progress updates
  };

  const handleAnomalyDetected = (anomaly: any) => {
    console.warn('Anomaly detected:', anomaly);
    // Handle anomaly detection (show notifications, alerts, etc.)
  };

  if (isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 10 }} />
      </Card>
    );
  }

  if (error && !mockTask) {
    return (
      <Alert
        type="error"
        message={t('failedToLoadTask')}
        description={t('failedToLoadTaskDescription')}
        showIcon
      />
    );
  }

  const tabItems = [
    {
      key: 'overview',
      label: (
        <Space>
          <FileTextOutlined />
          {t('overview')}
        </Space>
      ),
      children: (
        <Row gutter={16}>
          {/* Main Content */}
          <Col xs={24} lg={16}>
            {/* Progress Card */}
            <Card title={t('progress')} style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title={t('totalItems')}
                    value={currentTask.total_items}
                    prefix={<ClockCircleOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title={t('completed')}
                    value={currentTask.completed_items}
                    valueStyle={{ color: '#52c41a' }}
                    prefix={<CheckCircleOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title={t('remaining')}
                    value={currentTask.total_items - currentTask.completed_items}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Col>
              </Row>
              <Divider />
              <div>
                <span style={{ marginBottom: 8, display: 'block' }}>
                  {t('overallProgress')}: {currentTask.progress}%
                </span>
                <Progress
                  percent={currentTask.progress}
                  status={currentTask.status === 'completed' ? 'success' : 'active'}
                  strokeWidth={12}
                />
              </div>
            </Card>

            {/* Description */}
            <Card title={t('description')} style={{ marginBottom: 16 }}>
              <p>{currentTask.description || t('noDescription')}</p>
            </Card>

            {/* 标注集成 */}
            {currentTask.label_studio_project_id && (
              <Card title={t('dataAnnotation')} style={{ marginBottom: 16 }}>
                <Alert
                  message={t('annotationFunction')}
                  description={
                    <div>
                      <p>
                        {t('projectId')}: <strong>{currentTask.label_studio_project_id}</strong>
                      </p>
                      <p>{t('annotationType')}: <strong>{currentTask.annotation_type}</strong></p>
                      <Space style={{ marginTop: 12 }}>
                        {annotationPerms.canView ? (
                          <Button 
                            type="primary" 
                            size="large"
                            onClick={() => navigate(`/tasks/${id}/annotate`)}
                          >
                            {t('startAnnotation')}
                          </Button>
                        ) : (
                          <Button 
                            type="primary" 
                            size="large"
                            disabled
                            title={t('noAnnotationPermission')}
                          >
                            {t('startAnnotation')}
                          </Button>
                        )}
                        <Button 
                          onClick={() => window.open(`/api/label-studio/projects/${currentTask.label_studio_project_id}`, '_blank')}
                        >
                          {t('openInNewWindow')}
                        </Button>
                      </Space>
                    </div>
                  }
                  type="info"
                  showIcon
                />
              </Card>
            )}
          </Col>

          {/* Sidebar */}
          <Col xs={24} lg={8}>
            {/* Details */}
            <Card title={t('details')} style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label={t('annotationType')}>
                  {currentTask.annotation_type.replace('_', ' ')}
                </Descriptions.Item>
                <Descriptions.Item label={t('assignee')}>
                  {currentTask.assignee_name || t('unassigned')}
                </Descriptions.Item>
                <Descriptions.Item label={t('createdBy')}>{currentTask.created_by}</Descriptions.Item>
                <Descriptions.Item label={t('createdAt')}>
                  {new Date(currentTask.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label={t('updatedAt')}>
                  {new Date(currentTask.updated_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label={t('dueDate')}>
                  {currentTask.due_date
                    ? new Date(currentTask.due_date).toLocaleDateString()
                    : t('noDueDate')}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* Activity Timeline */}
            <Card title={t('activity')}>
              <Timeline
                items={[
                  {
                    color: 'green',
                    children: (
                      <>
                        <p style={{ marginBottom: 4 }}>{t('taskCreated')}</p>
                        <small style={{ color: '#999' }}>
                          {new Date(currentTask.created_at).toLocaleString()}
                        </small>
                      </>
                    ),
                  },
                  {
                    color: 'blue',
                    children: (
                      <>
                        <p style={{ marginBottom: 4 }}>{t('assignedTo', { name: currentTask.assignee_name })}</p>
                        <small style={{ color: '#999' }}>
                          {new Date(currentTask.updated_at).toLocaleString()}
                        </small>
                      </>
                    ),
                  },
                  {
                    color: 'gray',
                    children: (
                      <>
                        <p style={{ marginBottom: 4 }}>{t('progressUpdated', { progress: 65 })}</p>
                        <small style={{ color: '#999' }}>
                          {new Date(currentTask.updated_at).toLocaleString()}
                        </small>
                      </>
                    ),
                  },
                ]}
              />
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'progress',
      label: (
        <Space>
          <BarChartOutlined />
          {t('progressTracking')}
          <Badge count={currentTask.progress < 100 ? 'Active' : 'Complete'} />
        </Space>
      ),
      children: (
        <ProgressTracker
          taskId={currentTask.id}
          realtime={true}
          showTimeEntries={true}
          showMilestones={true}
          onProgressUpdate={handleProgressUpdate}
          onAnomalyDetected={handleAnomalyDetected}
        />
      ),
    },
    {
      key: 'team',
      label: (
        <Space>
          <TeamOutlined />
          {t('teamCollaboration')}
        </Space>
      ),
      children: (
        <Card>
          <Alert
            type="info"
            message={t('teamCollaborationFeature')}
            description={t('teamCollaborationDescription')}
            showIcon
          />
        </Card>
      ),
    },
  ];

  return (
    <div>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
            {t('backToTasks')}
          </Button>
        </Space>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <div>
            <h2 style={{ marginBottom: 8 }}>{currentTask.name}</h2>
            <Space>
              <Tag color={statusColorMap[currentTask.status]}>
                {t(`tasks.status${currentTask.status.charAt(0).toUpperCase() + currentTask.status.slice(1).replace('_', '')}`)}
              </Tag>
              <Tag color={priorityColorMap[currentTask.priority]}>
                {t(`tasks.priority${currentTask.priority.charAt(0).toUpperCase() + currentTask.priority.slice(1)}`)}
              </Tag>
              {currentTask.tags?.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
          </div>

          <Space>
            {currentTask.status === 'pending' && (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStatusChange('in_progress')}
              >
                {t('startTask')}
              </Button>
            )}
            {currentTask.status === 'in_progress' && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => handleStatusChange('completed')}
              >
                {t('completeTask')}
              </Button>
            )}
            <Button icon={<EditOutlined />} onClick={() => navigate(`/tasks/${id}/edit`)}>
              {t('edit')}
            </Button>
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              {t('delete')}
            </Button>
          </Space>
        </div>
      </Card>

      {/* Tabbed Content */}
      <Card>
        <Tabs defaultActiveKey="overview" items={tabItems} />
      </Card>
    </div>
  );
};

export default TaskDetailPage;
