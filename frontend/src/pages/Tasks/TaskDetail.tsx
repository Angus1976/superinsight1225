// Task detail page
import { useState } from 'react';
import { useParams, useNavigate, useLocation, Navigate } from 'react-router-dom';
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
  Tooltip,
  message,
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
  ExportOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTask, useUpdateTask, useDeleteTask } from '@/hooks/useTask';
import { usePermissions } from '@/hooks/usePermissions';
import { useLabelStudio } from '@/hooks';
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
  const params = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation('tasks');
  
  // Get ID with fallback to URL parsing
  let id = params.id;
  
  // Debug logging
  console.log('[TaskDetail] useParams:', params);
  console.log('[TaskDetail] location.pathname:', location.pathname);
  
  // If useParams fails, parse from URL
  if (!id) {
    const pathParts = location.pathname.split('/');
    const taskIndex = pathParts.indexOf('tasks');
    if (taskIndex >= 0 && pathParts[taskIndex + 1]) {
      id = pathParts[taskIndex + 1];
      console.warn('[TaskDetail] useParams failed, using URL parsing. ID:', id);
    }
  }
  
  console.log('[TaskDetail] Final ID:', id);
  
  // If still no ID, redirect to tasks list
  if (!id || id === 'undefined') {
    console.error('[TaskDetail] No valid ID found, redirecting to tasks list');
    return <Navigate to="/tasks" replace />;
  }
  
  const { data: task, isLoading, error } = useTask(id);
  const { annotation: annotationPerms } = usePermissions();
  const { openLabelStudio, isValidProject, navigateToAnnotate } = useLabelStudio();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  // Debug: Log permission state
  console.log('[TaskDetail] annotationPerms:', annotationPerms);
  console.log('[TaskDetail] task:', task);
  console.log('[TaskDetail] task.label_studio_project_id:', task?.label_studio_project_id);

  /**
   * Handle "开始标注" button click
   * Navigates directly to annotation page - validation happens there
   * Validates: Requirements 1.1, 1.6
   */
  const handleStartAnnotation = () => {
    console.log('[handleStartAnnotation] ========== START ==========');
    console.log('[handleStartAnnotation] id:', id);
    console.log('[handleStartAnnotation] task:', task);
    
    if (!id || !task) {
      console.error('[handleStartAnnotation] Task ID or task data is missing');
      message.error(t('detail.taskDataLoadFailed'));
      return;
    }
    
    // Navigate directly to annotation page using the hook
    console.log('[handleStartAnnotation] Navigating to:', `/tasks/${id}/annotate`);
    navigateToAnnotate(id);
    console.log('[handleStartAnnotation] ========== END ==========');
  };

  /**
   * Handle "在新窗口打开" button click
   * Opens Label Studio project in a new window
   * Validates: Requirements 1.2, 1.5
   */
  const handleOpenInNewWindow = () => {
    console.log('[handleOpenInNewWindow] ========== START ==========');
    console.log('[handleOpenInNewWindow] id:', id);
    console.log('[handleOpenInNewWindow] task:', task);
    
    if (!id || !task) {
      console.error('[handleOpenInNewWindow] Task ID or task data is missing');
      message.error(t('detail.taskDataLoadFailed'));
      return;
    }
    
    const projectId = task.label_studio_project_id;
    
    if (!isValidProject(projectId)) {
      // No valid project ID, navigate to annotation page first to create project
      message.info(t('detail.projectNotCreated'));
      navigateToAnnotate(id);
      return;
    }
    
    // Open Label Studio data manager using the hook
    console.log('[handleOpenInNewWindow] Opening Label Studio for project:', projectId);
    openLabelStudio(projectId);
    console.log('[handleOpenInNewWindow] ========== END ==========');
  };

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

  if (error || !task) {
    return (
      <Alert
        type="error"
        message={t('failedToLoadTask')}
        description={error?.message || t('failedToLoadTaskDescription')}
        showIcon
        action={
          <Button type="primary" onClick={() => navigate('/tasks')}>
            {t('backToTasks')}
          </Button>
        }
      />
    );
  }

  // Use real task data
  const currentTask = task;

  const tabItems = [
    {
      key: 'overview',
      label: (
        <Space>
          <FileTextOutlined />
          {t('detail.overview')}
        </Space>
      ),
      children: (
        <Row gutter={16}>
          {/* Main Content */}
          <Col xs={24} lg={16}>
            {/* Progress Card */}
            <Card title={t('progressLabel')} style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title={t('detail.totalItems')}
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
                    title={t('detail.remaining')}
                    value={currentTask.total_items - currentTask.completed_items}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Col>
              </Row>
              <Divider />
              <div>
                <span style={{ marginBottom: 8, display: 'block' }}>
                  {t('detail.overallProgress')}: {currentTask.progress}%
                </span>
                <Progress
                  percent={currentTask.progress}
                  status={currentTask.status === 'completed' ? 'success' : 'active'}
                  size={[null, 12]}
                />
              </div>
            </Card>

            {/* Description */}
            <Card title={t('description')} style={{ marginBottom: 16 }}>
              <p>{currentTask.description || t('detail.noDescription')}</p>
            </Card>

            {/* 标注集成 */}
            {currentTask.label_studio_project_id && (
              <Card title={t('detail.dataAnnotation')} style={{ marginBottom: 16 }}>
                <Alert
                  message={t('detail.annotationFunction')}
                  description={
                    <div>
                      <p>
                        {t('detail.projectId')}: <strong>{currentTask.label_studio_project_id}</strong>
                      </p>
                      <p>{t('annotationTypeLabel')}: <strong>{currentTask.annotation_type}</strong></p>
                      <Space style={{ marginTop: 12 }}>
                        {annotationPerms.canView ? (
                          <Button 
                            type="primary" 
                            size="large"
                            icon={<PlayCircleOutlined />}
                            onClick={handleStartAnnotation}
                          >
                            {t('detail.startAnnotation')}
                          </Button>
                        ) : (
                          <Tooltip title={t('detail.noAnnotationPermission')}>
                            <Button 
                              type="primary" 
                              size="large"
                              icon={<PlayCircleOutlined />}
                              disabled
                            >
                              {t('detail.startAnnotation')}
                            </Button>
                          </Tooltip>
                        )}
                        <Button 
                          size="large"
                          icon={<ExportOutlined />}
                          onClick={handleOpenInNewWindow}
                        >
                          {t('detail.openInNewWindow')}
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
            <Card title={t('detail.details')} style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label={t('annotationTypeLabel')}>
                  {currentTask.annotation_type ? currentTask.annotation_type.replace('_', ' ') : '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('assignee')}>
                  {currentTask.assignee_name || t('unassigned')}
                </Descriptions.Item>
                <Descriptions.Item label={t('detail.createdBy')}>{currentTask.created_by}</Descriptions.Item>
                <Descriptions.Item label={t('detail.createdAt')}>
                  {new Date(currentTask.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label={t('detail.updatedAt')}>
                  {new Date(currentTask.updated_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label={t('dueDate')}>
                  {currentTask.due_date
                    ? new Date(currentTask.due_date).toLocaleDateString()
                    : t('detail.noDueDate')}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* Activity Timeline */}
            <Card title={t('detail.activity')}>
              <Timeline
                items={[
                  {
                    color: 'green',
                    children: (
                      <>
                        <p style={{ marginBottom: 4 }}>{t('detail.taskCreated')}</p>
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
                        <p style={{ marginBottom: 4 }}>{t('detail.assignedTo', { name: currentTask.assignee_name })}</p>
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
                        <p style={{ marginBottom: 4 }}>{t('detail.progressUpdated', { progress: 65 })}</p>
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
          {t('detail.progressTracking')}
          <Badge count={currentTask.progress < 100 ? t('common.active') : t('completed')} />
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
          {t('detail.teamCollaboration')}
        </Space>
      ),
      children: (
        <Card>
          <Alert
            type="info"
            message={t('detail.teamCollaborationFeature')}
            description={t('detail.teamCollaborationDescription')}
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
            {t('detail.backToTasks')}
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
                {t({
                  pending: 'statusPending',
                  in_progress: 'statusInProgress',
                  completed: 'statusCompleted',
                  cancelled: 'statusCancelled',
                }[currentTask.status])}
              </Tag>
              <Tag color={priorityColorMap[currentTask.priority]}>
                {t({
                  low: 'priorityLow',
                  medium: 'priorityMedium',
                  high: 'priorityHigh',
                  urgent: 'priorityUrgent',
                }[currentTask.priority])}
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
                {t('detail.startTask')}
              </Button>
            )}
            {currentTask.status === 'in_progress' && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => handleStatusChange('completed')}
              >
                {t('detail.completeTask')}
              </Button>
            )}
            <Button icon={<EditOutlined />} onClick={() => navigate(`/tasks/${id}/edit`)}>
              {t('editAction')}
            </Button>
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              {t('deleteAction')}
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
