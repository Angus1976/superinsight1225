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
  LoadingOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTask, useUpdateTask, useDeleteTask } from '@/hooks/useTask';
import { usePermissions } from '@/hooks/usePermissions';
import { ProgressTracker } from '@/components/Tasks';
import { labelStudioService } from '@/services/labelStudioService';
import { useLanguageStore } from '@/stores/languageStore';
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
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  // Loading state for annotation operations
  const [annotationLoading, setAnnotationLoading] = useState(false);
  
  // Loading state for open in new window operation
  const [openWindowLoading, setOpenWindowLoading] = useState(false);
  
  // Get user's language preference from language store
  const { language } = useLanguageStore();

  /**
   * Handle error with detailed logging and user-friendly messages
   * Validates: Requirements 1.1, 1.6
   */
  const handleAnnotationError = (error: unknown, context: string) => {
    console.error(`[${context}] Error:`, error);
    
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { status?: number; data?: { detail?: string; message?: string } } };
      const status = axiosError.response?.status;
      const data = axiosError.response?.data as any;
      
      // Log detailed error information
      console.error(`[${context}] Status: ${status}`);
      console.error(`[${context}] Data:`, data);
      
      // Show user-friendly error message based on status code
      switch (status) {
        case 401:
          console.error(`[${context}] Authentication failed - token may be expired`);
          message.error(t('annotate.authenticationFailed'));
          break;
        case 403:
          console.error(`[${context}] Permission denied`);
          message.error(t('annotate.permissionDenied'));
          break;
        case 404:
          console.error(`[${context}] Project not found`);
          message.error(t('annotate.projectNotFound'));
          break;
        case 503:
          console.error(`[${context}] Label Studio service unavailable`);
          message.error(t('annotate.serviceUnavailable'));
          break;
        default:
          console.error(`[${context}] API error: ${data?.detail || data?.message || 'Unknown error'}`);
          message.error(data?.detail || data?.message || t('annotate.operationFailed'));
      }
    } else if (error instanceof Error) {
      console.error(`[${context}] Error message: ${error.message}`);
      message.error(error.message || t('annotate.operationFailed'));
    } else {
      console.error(`[${context}] Unknown error type`);
      message.error(t('annotate.operationFailed'));
    }
  };

  /**
   * Handle "开始标注" button click
   * Validates project exists before navigation, creates if needed
   * Validates: Requirements 1.1, 1.6
   */
  const handleStartAnnotation = async () => {
    if (!id || !task) {
      console.error('[handleStartAnnotation] Task ID or task data is missing');
      message.error('任务数据加载失败，请刷新页面重试');
      return;
    }
    
    try {
      setAnnotationLoading(true);
      console.log('[handleStartAnnotation] Starting...', { taskId: id, task });
      
      // Check if project ID exists in task
      const projectId = task.label_studio_project_id;
      console.log('[handleStartAnnotation] Current project ID:', projectId);
      
      if (projectId) {
        // Validate project exists in Label Studio
        console.log('[handleStartAnnotation] Validating project...');
        const validation = await labelStudioService.validateProject(projectId);
        console.log('[handleStartAnnotation] Validation result:', validation);
        
        if (validation.exists && validation.accessible) {
          // Project exists and is accessible, navigate directly
          console.log('[handleStartAnnotation] Project valid, navigating...');
          navigate(`/tasks/${id}/annotate`);
          return;
        }
        
        // Project doesn't exist or not accessible, need to create
        if (!validation.exists) {
          console.log('[handleStartAnnotation] Project does not exist, creating...');
          message.info(t('annotate.creatingProject'));
        }
      }
      
      // Create project automatically if needed
      console.log('[handleStartAnnotation] Calling ensureProject...');
      const result = await labelStudioService.ensureProject({
        task_id: id,
        task_name: task.name,
        annotation_type: task.annotation_type,
      });
      console.log('[handleStartAnnotation] Ensure project result:', result);
      
      if (result.status === 'ready') {
        // Update task with new project ID if it was created
        if (result.created && result.project_id !== projectId) {
          console.log('[handleStartAnnotation] Updating task with new project ID...');
          await updateTask.mutateAsync({
            id,
            payload: { label_studio_project_id: result.project_id },
          });
        }
        
        // Navigate to annotation page
        console.log('[handleStartAnnotation] Navigating to annotate page...');
        navigate(`/tasks/${id}/annotate`);
      } else {
        console.error('[handleStartAnnotation] Project creation failed:', result);
        message.error(t('annotate.projectCreationFailed'));
      }
    } catch (error) {
      handleAnnotationError(error, 'handleStartAnnotation');
    } finally {
      setAnnotationLoading(false);
    }
  };

  /**
   * Handle "在新窗口打开" button click
   * Gets authenticated URL with language preference and opens Label Studio in new window
   * Validates: Requirements 1.2, 1.5
   */
  const handleOpenInNewWindow = async () => {
    if (!id || !task) {
      console.error('[handleOpenInNewWindow] Task ID or task data is missing');
      message.error('任务数据加载失败，请刷新页面重试');
      return;
    }
    
    try {
      setOpenWindowLoading(true);
      console.log('[handleOpenInNewWindow] Starting...', { taskId: id, task });
      
      // Get project ID from task
      let projectId = task.label_studio_project_id;
      console.log('[handleOpenInNewWindow] Current project ID:', projectId);
      
      // If no project ID, ensure project exists first
      if (!projectId) {
        console.log('[handleOpenInNewWindow] No project ID, creating project...');
        message.info(t('annotate.creatingProject'));
        
        const result = await labelStudioService.ensureProject({
          task_id: id,
          task_name: task.name,
          annotation_type: task.annotation_type,
        });
        console.log('[handleOpenInNewWindow] Ensure project result:', result);
        
        if (result.status !== 'ready') {
          console.error('[handleOpenInNewWindow] Project creation failed:', result);
          message.error(t('annotate.projectCreationFailed'));
          return;
        }
        
        projectId = result.project_id;
        
        // Update task with new project ID if it was created
        if (result.created) {
          console.log('[handleOpenInNewWindow] Updating task with new project ID...');
          await updateTask.mutateAsync({
            id,
            payload: { label_studio_project_id: projectId },
          });
        }
      } else {
        // Validate project exists
        console.log('[handleOpenInNewWindow] Validating project...');
        const validation = await labelStudioService.validateProject(projectId);
        console.log('[handleOpenInNewWindow] Validation result:', validation);
        
        if (!validation.exists) {
          console.log('[handleOpenInNewWindow] Project does not exist, creating...');
          message.info(t('annotate.creatingProject'));
          
          // Project doesn't exist, create it
          const result = await labelStudioService.ensureProject({
            task_id: id,
            task_name: task.name,
            annotation_type: task.annotation_type,
          });
          console.log('[handleOpenInNewWindow] Ensure project result:', result);
          
          if (result.status !== 'ready') {
            console.error('[handleOpenInNewWindow] Project creation failed:', result);
            message.error(t('annotate.projectCreationFailed'));
            return;
          }
          
          projectId = result.project_id;
          
          // Update task with new project ID if different
          if (result.project_id !== task.label_studio_project_id) {
            console.log('[handleOpenInNewWindow] Updating task with new project ID...');
            await updateTask.mutateAsync({
              id,
              payload: { label_studio_project_id: projectId },
            });
          }
        }
      }
      
      // Get authenticated URL with user's language preference
      // Map language to Label Studio format: 'zh' or 'en'
      const labelStudioLang = language === 'zh' ? 'zh' : 'en';
      console.log('[handleOpenInNewWindow] Getting auth URL...', { projectId, language: labelStudioLang });
      const authUrlResponse = await labelStudioService.getAuthUrl(projectId, labelStudioLang);
      console.log('[handleOpenInNewWindow] Auth URL response:', { url: authUrlResponse.url, projectId: authUrlResponse.project_id });
      
      // Open Label Studio in new window with authenticated URL
      console.log('[handleOpenInNewWindow] Opening new window...');
      window.open(authUrlResponse.url, '_blank', 'noopener,noreferrer');
      
    } catch (error) {
      handleAnnotationError(error, 'handleOpenInNewWindow');
    } finally {
      setOpenWindowLoading(false);
    }
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
                            icon={annotationLoading ? <LoadingOutlined /> : <PlayCircleOutlined />}
                            loading={annotationLoading}
                            onClick={handleStartAnnotation}
                          >
                            {annotationLoading ? t('annotate.preparing') : t('startAnnotation')}
                          </Button>
                        ) : (
                          <Tooltip title={t('noAnnotationPermission')}>
                            <Button 
                              type="primary" 
                              size="large"
                              icon={<PlayCircleOutlined />}
                              disabled
                            >
                              {t('startAnnotation')}
                            </Button>
                          </Tooltip>
                        )}
                        <Button 
                          size="large"
                          icon={openWindowLoading ? <LoadingOutlined /> : <ExportOutlined />}
                          loading={openWindowLoading}
                          onClick={handleOpenInNewWindow}
                        >
                          {openWindowLoading ? t('annotate.preparing') : t('openInNewWindow')}
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
          <Badge count={currentTask.progress < 100 ? t('active') : t('completed')} />
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
