// 完整的标注页面
// Performance optimizations:
// - All callback functions are wrapped with useCallback to ensure stable references
// - Computed values use useMemo to avoid recalculation
// - Child components are memoized with React.memo
// - Inline functions in JSX are replaced with stable callback references
// - Lazy loading for task data with useLazyTask hook
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  Alert,
  Spin,
  message,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Divider,
  Typography,
  Tooltip,
  Dropdown,
  Modal,
  Result,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  LockOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  SyncOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
  LoginOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { PermissionGuard } from '@/components/Auth/PermissionGuard';
import { 
  AnnotationGuide, 
  AnnotationStats, 
  AnnotationActions, 
  CurrentTaskInfo 
} from '@/components/Tasks';
import { useAuthStore } from '@/stores/authStore';
import { usePermissions } from '@/hooks/usePermissions';
import { useTask, useLazyTask, useUpdateTask } from '@/hooks/useTask';
import { useLabelStudio, type LabelStudioError } from '@/hooks';
import { Permission } from '@/utils/permissions';
import apiClient from '@/services/api/client';
import { labelStudioService } from '@/services/labelStudioService';
import type { 
  LabelStudioTask, 
  LabelStudioProject,
} from '@/types/task';

const { Title, Text } = Typography;

const TaskAnnotatePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const { annotation: annotationPerms, roleDisplayName } = usePermissions();
  const { t } = useTranslation(['tasks', 'common']);
  
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<LabelStudioProject | null>(null);
  const [tasks, setTasks] = useState<LabelStudioTask[]>([]);
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [annotationCount, setAnnotationCount] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [syncInProgress, setSyncInProgress] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  
  // Error state for better error handling
  const [error, setError] = useState<LabelStudioError | null>(null);

  const { data: taskDetail } = useTask(id || '');
  const updateTask = useUpdateTask();
  const { prefetchTask } = useLazyTask();
  const { 
    openLabelStudio, 
    handleError: handleLabelStudioError, 
    navigateToTaskDetail 
  } = useLabelStudio();

  // Track if initial fetch has been done to prevent loops
  const [initialFetchDone, setInitialFetchDone] = useState(false);

  // Prefetch task data when component mounts for faster subsequent loads
  useEffect(() => {
    if (id) {
      prefetchTask(id);
    }
  }, [id, prefetchTask]);

  // 获取项目和任务数据 - Enhanced with better error handling
  const fetchData = useCallback(async () => {
    if (!id || !token) return;
    
    // Prevent re-fetching if already done (avoid infinite loop)
    if (initialFetchDone) return;

    try {
      setLoading(true);
      setError(null);
      
      // Step 1: Validate project exists
      let projectId = taskDetail?.label_studio_project_id;
      
      // If no project ID, try to create project automatically
      if (!projectId) {
        try {
          message.loading({ content: t('annotate.creatingProjectAuto'), key: 'project-creation' });
          
          const ensureResult = await labelStudioService.ensureProject({
            task_id: id,
            task_name: taskDetail?.name || 'Annotation Project',
            annotation_type: taskDetail?.annotation_type || 'text_classification',
          });
          
          projectId = ensureResult.project_id;
          message.success({ content: t('annotate.projectCreatedSuccess'), key: 'project-creation' });
          
          // Update task with project ID if we have taskDetail
          if (taskDetail) {
            await updateTask.mutateAsync({
              id: taskDetail.id,
              payload: { label_studio_project_id: projectId }
            });
          }
        } catch (createError) {
          console.error('Failed to create project:', createError);
          setError({
            type: 'service',
            message: t('annotate.projectCreationFailed'),
            details: createError instanceof Error ? createError.message : undefined,
          });
          return;
        }
      }
      
      // Step 2: Fetch project info
      const projectResponse = await apiClient.get(`/api/label-studio/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProject(projectResponse.data);
      
      // Step 3: Fetch tasks
      const tasksResponse = await apiClient.get(`/api/label-studio/projects/${projectId}/tasks`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const tasksList = tasksResponse.data.tasks || tasksResponse.data.results || [];
      
      // If no tasks, try to import them
      if (tasksList.length === 0 && id) {
        try {
          message.loading({ content: t('annotate.importingTasks'), key: 'task-import' });
          
          await labelStudioService.importTasks(projectId, id);
          
          // Refetch tasks after import
          const refetchResponse = await apiClient.get(`/api/label-studio/projects/${projectId}/tasks`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          
          const importedTasks = refetchResponse.data.tasks || refetchResponse.data.results || [];
          setTasks(importedTasks);
          message.success({ content: t('annotate.tasksImportedSuccess'), key: 'task-import' });
          
          // Find first unlabeled task
          const unlabeledIndex = importedTasks.findIndex((task: LabelStudioTask) => !task.is_labeled);
          if (unlabeledIndex !== -1) {
            setCurrentTaskIndex(unlabeledIndex);
          }
          
          // Count labeled tasks
          const labeled = importedTasks.filter((task: LabelStudioTask) => task.is_labeled).length;
          setAnnotationCount(labeled);
        } catch (importError) {
          console.error('Failed to import tasks:', importError);
          // Continue with empty task list - user can still see the project
          setTasks([]);
        }
      } else {
        setTasks(tasksList);
        
        // Find first unlabeled task
        const unlabeledIndex = tasksList.findIndex((task: LabelStudioTask) => !task.is_labeled);
        if (unlabeledIndex !== -1) {
          setCurrentTaskIndex(unlabeledIndex);
        }
        
        // Count labeled tasks
        const labeled = tasksList.filter((task: LabelStudioTask) => task.is_labeled).length;
        setAnnotationCount(labeled);
      }
      
    } catch (err) {
      console.error('Failed to fetch data:', err);
      
      // Use unified error handling from useLabelStudio hook
      const errorInfo = handleLabelStudioError(err);
      setError(errorInfo);
    } finally {
      setLoading(false);
      setInitialFetchDone(true);
    }
  }, [id, token, taskDetail, updateTask, t, initialFetchDone]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Memoize computed values to avoid recalculation on each render
  const currentTask = useMemo(() => tasks[currentTaskIndex], [tasks, currentTaskIndex]);
  const progress = useMemo(
    () => tasks.length > 0 ? Math.round((annotationCount / tasks.length) * 100) : 0,
    [annotationCount, tasks.length]
  );
  const tasksLength = useMemo(() => tasks.length, [tasks.length]);

  // 处理标注创建 - 引导用户在 LS 中标注后同步
  const handleAnnotationCreate = useCallback(async (_annotation: unknown) => {
    if (!annotationPerms.canCreate) {
      message.error(t('annotate.noCreatePermission'));
      return;
    }

    // 标注操作应在 LS 中完成，完成后点击"同步标注结果"按钮
    message.info(t('annotate.syncAnnotations'));
  }, [annotationPerms.canCreate, t]);

  // 处理标注更新 - 引导用户在 LS 中编辑后同步
  const handleAnnotationUpdate = useCallback(async (_annotation: unknown) => {
    if (!annotationPerms.canEdit) {
      message.error(t('annotate.noEditPermission'));
      return;
    }

    // 标注编辑应在 LS 中完成，完成后点击"同步标注结果"按钮
    message.info(t('annotate.syncAnnotations'));
  }, [annotationPerms.canEdit, t]);

  // 同步标注结果 - 从 LS 拉取标注数据到 SuperInsight
  const handleSyncAnnotations = useCallback(async () => {
    if (!project) return;

    try {
      setSyncInProgress(true);
      const result = await labelStudioService.syncAnnotations(String(project.id));

      if (result.synced_count === 0) {
        message.info(t('annotate.noAnnotationsToSync'));
        return;
      }

      message.success(
        t('annotate.syncAnnotationsSuccess') +
        ' — ' +
        t('annotate.syncedCount', { count: result.synced_count })
      );

      // 刷新页面数据和进度
      setInitialFetchDone(false);
      setLastSyncTime(new Date());
    } catch (err) {
      console.error('Failed to sync annotations:', err);
      message.error(t('annotate.syncAnnotationsFailed'));
    } finally {
      setSyncInProgress(false);
    }
  }, [project, t]);

  // 跳转到下一个任务
  const handleNextTask = useCallback(() => {
    const nextUnlabeledIndex = tasks.findIndex((task, index) => 
      index > currentTaskIndex && !task.is_labeled
    );
    
    if (nextUnlabeledIndex !== -1) {
      setCurrentTaskIndex(nextUnlabeledIndex);
    } else {
      // 所有任务都已完成
      Modal.success({
        title: t('annotate.taskComplete'),
        content: t('annotate.allTasksCompletedModal'),
        onOk: () => navigate(`/tasks/${id}`),
      });
    }
  }, [tasks, currentTaskIndex, navigate, id, t]);

  // 跳过当前任务
  const handleSkipTask = useCallback(() => {
    handleNextTask();
  }, [handleNextTask]);

  // 返回任务详情
  const handleBackToTask = useCallback(() => {
    if (id) {
      navigateToTaskDetail(id);
    }
  }, [id, navigateToTaskDetail]);

  // 切换全屏模式
  const handleToggleFullscreen = useCallback(() => {
    setFullscreen(prev => !prev);
  }, []);

  // 手动同步进度
  const handleSyncProgress = useCallback(async () => {
    try {
      setSyncInProgress(true);
      setError(null);
      await fetchData();
      setLastSyncTime(new Date());
      message.success(t('annotate.syncComplete'));
    } catch (err) {
      message.error(t('annotate.syncFailed'));
    } finally {
      setSyncInProgress(false);
    }
  }, [fetchData, t]);

  // Handle retry after error
  const handleRetry = useCallback(async () => {
    setError(null);
    await fetchData();
  }, [fetchData]);

  // Handle re-login for auth errors
  const handleReLogin = useCallback(() => {
    // Navigate to login page
    navigate('/login', { state: { from: `/tasks/${id}/annotate` } });
  }, [navigate, id]);

  // Handle create project for not found errors
  const handleCreateProject = useCallback(async () => {
    if (!id || !taskDetail) return;
    
    try {
      setLoading(true);
      setError(null);
      
      message.loading({ content: t('annotate.creatingProjectAuto'), key: 'project-creation' });
      
      const ensureResult = await labelStudioService.ensureProject({
        task_id: id,
        task_name: taskDetail.name || 'Annotation Project',
        annotation_type: taskDetail.annotation_type || 'text_classification',
      });
      
      message.success({ content: t('annotate.projectCreatedSuccess'), key: 'project-creation' });
      
      // Update task with project ID
      await updateTask.mutateAsync({
        id: taskDetail.id,
        payload: { label_studio_project_id: ensureResult.project_id }
      });
      
      // Refetch data
      await fetchData();
    } catch (err) {
      console.error('Failed to create project:', err);
      setError({
        type: 'service',
        message: t('annotate.projectCreationFailed'),
        details: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setLoading(false);
    }
  }, [id, taskDetail, updateTask, fetchData, t]);

  // Memoized callback for opening Label Studio - avoids inline function in JSX
  const handleOpenLabelStudioCallback = useCallback(() => {
    if (project) {
      openLabelStudio(project.id);
    }
  }, [project, openLabelStudio]);

  // Memoized progress format function to avoid inline function in JSX
  const progressFormat = useCallback(() => `${progress}%`, [progress]);

  // 跳转到指定任务 - defined before jumpToTaskMenuItems to avoid circular dependency
  const handleJumpToTask = useCallback((taskIndex: number) => {
    if (taskIndex >= 0 && taskIndex < tasks.length) {
      setCurrentTaskIndex(taskIndex);
    }
  }, [tasks.length]);

  // Memoized dropdown menu items for task jumping - avoids recreating on each render
  const jumpToTaskMenuItems = useMemo(() => 
    tasks.map((task, index) => ({
      key: index,
      label: (
        <Space>
          <span>{t('annotate.task')} {index + 1}</span>
          {task.is_labeled && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
        </Space>
      ),
      onClick: () => handleJumpToTask(index),
    })),
    [tasks, t, handleJumpToTask]
  );

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>{t('annotate.loadingTask')}</p>
      </div>
    );
  }

  // Error state with recovery options
  if (error) {
    const getErrorIcon = () => {
      switch (error.type) {
        case 'not_found':
          return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
        case 'auth':
          return <LockOutlined style={{ color: '#ff4d4f' }} />;
        case 'network':
        case 'service':
          return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
        default:
          return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      }
    };

    const getErrorActions = () => {
      switch (error.type) {
        case 'not_found':
          return (
            <Space>
              <Button type="primary" onClick={handleCreateProject}>
                {t('annotate.creatingProject')}
              </Button>
              <Button onClick={handleBackToTask}>
                {t('annotate.backToTask')}
              </Button>
            </Space>
          );
        case 'auth':
          return (
            <Space>
              <Button type="primary" icon={<LoginOutlined />} onClick={handleReLogin}>
                {t('common:login')}
              </Button>
              <Button onClick={handleBackToTask}>
                {t('annotate.backToTask')}
              </Button>
            </Space>
          );
        case 'network':
        case 'service':
          return (
            <Space>
              <Button type="primary" icon={<ReloadOutlined />} onClick={handleRetry}>
                {t('annotate.retryLoading')}
              </Button>
              <Button onClick={handleBackToTask}>
                {t('annotate.backToTask')}
              </Button>
            </Space>
          );
        default:
          return (
            <Space>
              <Button type="primary" icon={<ReloadOutlined />} onClick={handleRetry}>
                {t('annotate.retryLoading')}
              </Button>
              <Button onClick={handleBackToTask}>
                {t('annotate.backToTask')}
              </Button>
            </Space>
          );
      }
    };

    return (
      <div style={{ padding: '50px', maxWidth: '600px', margin: '0 auto' }}>
        <Result
          icon={getErrorIcon()}
          title={error.message}
          subTitle={error.details}
          extra={getErrorActions()}
        />
        {error.details && error.type === 'unknown' && (
          <Alert
            type="info"
            message={t('annotate.errorDetails')}
            description={
              <div>
                <p>{error.details}</p>
                <p style={{ marginTop: 8, color: '#666' }}>
                  {t('annotate.contactSupport')}
                </p>
              </div>
            }
            style={{ marginTop: 16 }}
          />
        )}
      </div>
    );
  }

  if (!project || !currentTask) {
    return (
      <Alert
        type="warning"
        message={t('annotate.noTasksAvailable')}
        description={t('annotate.allTasksCompleted')}
        showIcon
        action={
          <Button onClick={handleBackToTask}>
            {t('annotate.backToDetail')}
          </Button>
        }
      />
    );
  }

  return (
    <PermissionGuard 
      permission={Permission.VIEW_ANNOTATION}
      fallback={
        <Alert
          type="warning"
          showIcon
          icon={<LockOutlined />}
          message={t('annotate.insufficientPermission')}
          description={
            <div>
              <p>{t('annotate.currentRole')}: <strong>{roleDisplayName}</strong></p>
              <p>{t('annotate.annotationRolesOnly')}</p>
              <ul>
                <li>{t('annotate.systemAdmin')}</li>
                <li>{t('annotate.businessExpert')}</li>
                <li>{t('annotate.dataAnnotator')}</li>
              </ul>
              <p>{t('annotate.contactAdmin')}</p>
            </div>
          }
          action={
            <Button type="primary" onClick={() => navigate('/tasks')}>
              {t('annotate.backToTaskList')}
            </Button>
          }
          style={{ margin: '20px' }}
        />
      }
    >
      <div style={{ 
        height: fullscreen ? '100vh' : 'calc(100vh - 64px)', 
        display: 'flex', 
        flexDirection: 'column',
        position: fullscreen ? 'fixed' : 'relative',
        top: fullscreen ? 0 : 'auto',
        left: fullscreen ? 0 : 'auto',
        right: fullscreen ? 0 : 'auto',
        bottom: fullscreen ? 0 : 'auto',
        zIndex: fullscreen ? 1000 : 'auto',
        background: '#fff'
      }}>
        {/* 顶部工具栏 */}
        <Card style={{ marginBottom: fullscreen ? 0 : 16, borderRadius: fullscreen ? 0 : undefined }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Space>
                <Button 
                  icon={<ArrowLeftOutlined />} 
                  onClick={handleBackToTask}
                  disabled={fullscreen}
                >
                  {t('annotate.backToTask')}
                </Button>
                <Divider type="vertical" />
                <Title level={4} style={{ margin: 0 }}>
                  {project.title}
                </Title>
                <Tag color="blue">
                  {t('annotate.task')} {currentTaskIndex + 1} / {tasks.length}
                </Tag>
                <Tag color="green">
                  {roleDisplayName}
                </Tag>
                {syncInProgress && (
                  <Tag icon={<SyncOutlined spin />} color="processing">
                    {t('annotate.syncing')}
                  </Tag>
                )}
              </Space>
            </Col>
            
            <Col>
              <Space>
                <Tooltip title={t('annotate.syncAnnotations')}>
                  <Button
                    type="primary"
                    icon={<SyncOutlined />}
                    loading={syncInProgress}
                    onClick={handleSyncAnnotations}
                  >
                    {t('annotate.syncAnnotations')}
                  </Button>
                </Tooltip>
                <Tooltip title={t('annotate.syncProgress')}>
                  <Button
                    icon={<ReloadOutlined />}
                    loading={syncInProgress}
                    onClick={handleSyncProgress}
                  />
                </Tooltip>
                <Tooltip title={fullscreen ? t('annotate.exitFullscreen') : t('annotate.fullscreenMode')}>
                  <Button
                    icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                    onClick={handleToggleFullscreen}
                  />
                </Tooltip>
                <Dropdown
                  menu={{
                    items: jumpToTaskMenuItems,
                  }}
                >
                  <Button icon={<SettingOutlined />}>
                    {t('annotate.jumpToTask')}
                  </Button>
                </Dropdown>
                <Statistic
                  title={t('annotate.completed')}
                  value={annotationCount}
                  suffix={`/ ${tasks.length}`}
                  valueStyle={{ fontSize: '16px' }}
                />
                <Progress
                  type="circle"
                  size={50}
                  percent={progress}
                  format={progressFormat}
                />
              </Space>
            </Col>
          </Row>
          
          {lastSyncTime && (
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <InfoCircleOutlined /> {t('annotate.lastSync')}: {lastSyncTime.toLocaleTimeString()}
              </Text>
            </div>
          )}
        </Card>

        {/* Label Studio 集成区域 */}
        <div style={{ flex: 1, display: 'flex' }}>
          <Row style={{ width: '100%', height: '100%' }}>
            {/* 主要标注区域 */}
            <Col span={fullscreen ? 24 : 18} style={{ height: '100%' }}>
              <div style={{ height: '100%', marginRight: fullscreen ? 0 : 8 }}>
                {currentTask ? (
                  <Card 
                    title={t('annotate.title')}
                    style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
                    styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' } }}
                  >
                    <AnnotationGuide
                      projectId={project.id}
                      currentTaskIndex={currentTaskIndex}
                      totalTasks={tasks.length}
                      onOpenLabelStudio={handleOpenLabelStudioCallback}
                      onBackToTask={handleBackToTask}
                    />
                  </Card>
                ) : (
                  <Alert
                    type="warning"
                    message={t('annotate.noCurrentTask')}
                    description={
                      <div>
                        <p>{t('annotate.projectIdLabel')}: {project.id}</p>
                        <p>{t('annotate.totalTasksLabel')}: {tasks.length}</p>
                        <p>{t('annotate.currentIndexLabel')}: {currentTaskIndex}</p>
                      </div>
                    }
                  />
                )}
              </div>
            </Col>

            {/* Right control panel - only shown in non-fullscreen mode */}
            {!fullscreen && (
              <Col span={6} style={{ height: '100%' }}>
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  {/* 当前任务信息 */}
                  <CurrentTaskInfo task={currentTask} />

                  {/* 操作按钮 */}
                  <AnnotationActions
                    currentTask={currentTask}
                    syncInProgress={syncInProgress}
                    onNextTask={handleNextTask}
                    onSkipTask={handleSkipTask}
                    onSyncProgress={handleSyncProgress}
                  />

                  {/* 进度统计 */}
                  <AnnotationStats
                    totalTasks={tasks.length}
                    completedCount={annotationCount}
                    currentTaskIndex={currentTaskIndex}
                    progress={progress}
                    tasks={tasks}
                    onJumpToTask={handleJumpToTask}
                  />
                </div>
              </Col>
            )}
          </Row>
        </div>
      </div>
    </PermissionGuard>
  );
};

export default TaskAnnotatePage;