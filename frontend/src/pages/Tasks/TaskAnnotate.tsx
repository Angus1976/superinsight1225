// 完整的标注页面
import { useState, useEffect, useCallback } from 'react';
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
  Badge,
  Dropdown,
  Modal,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  StepForwardOutlined,
  ReloadOutlined,
  LockOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  SaveOutlined,
  SyncOutlined,
  SettingOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { LabelStudioEmbed } from '@/components/LabelStudio';
import { PermissionGuard } from '@/components/Auth/PermissionGuard';
import { useAuthStore } from '@/stores/authStore';
import { usePermissions } from '@/hooks/usePermissions';
import { useTask, useUpdateTask } from '@/hooks/useTask';
import { Permission } from '@/utils/permissions';
import apiClient from '@/services/api/client';

const { Title, Text } = Typography;

interface AnnotationResult {
  id?: number;
  result: Array<{
    value: any;
    from_name: string;
    to_name: string;
    type: string;
  }>;
  task: number;
  created_at?: string;
  updated_at?: string;
}

interface LabelStudioTask {
  id: number;
  data: {
    text: string;
    [key: string]: any;
  };
  project: number;
  is_labeled: boolean;
  annotations: AnnotationResult[];
}

interface LabelStudioProject {
  id: number;
  title: string;
  description: string;
  task_number: number;
  total_annotations_number: number;
  label_config: string;
  created_by: {
    id: number;
    username: string;
  };
}

const TaskAnnotatePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token, user } = useAuthStore();
  const { annotation: annotationPerms, roleDisplayName } = usePermissions();
  
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<LabelStudioProject | null>(null);
  const [tasks, setTasks] = useState<LabelStudioTask[]>([]);
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [annotationCount, setAnnotationCount] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [syncInProgress, setSyncInProgress] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);

  const { data: taskDetail } = useTask(id || '');
  const updateTask = useUpdateTask();

  // 获取项目和任务数据
  const fetchData = useCallback(async () => {
    if (!id || !token) return;

    try {
      setLoading(true);
      
      // 获取项目信息
      const projectResponse = await apiClient.get(`/api/label-studio/projects/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProject(projectResponse.data);
      
      // 获取任务列表
      const tasksResponse = await apiClient.get(`/api/label-studio/projects/${id}/tasks`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTasks(tasksResponse.data.results || []);
      
      // 找到第一个未标注的任务
      const unlabeledIndex = tasksResponse.data.results.findIndex((task: LabelStudioTask) => !task.is_labeled);
      if (unlabeledIndex !== -1) {
        setCurrentTaskIndex(unlabeledIndex);
      }
      
      // 统计已标注数量
      const labeled = tasksResponse.data.results.filter((task: LabelStudioTask) => task.is_labeled).length;
      setAnnotationCount(labeled);
      
    } catch (error) {
      console.error('Failed to fetch data:', error);
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const currentTask = tasks[currentTaskIndex];
  const progress = tasks.length > 0 ? Math.round((annotationCount / tasks.length) * 100) : 0;

  // 处理标注创建
  const handleAnnotationCreate = useCallback(async (annotation: AnnotationResult) => {
    if (!annotationPerms.canCreate) {
      message.error('您没有创建标注的权限');
      return;
    }

    try {
      setSyncInProgress(true);
      const response = await apiClient.post(
        `/api/label-studio/projects/${id}/tasks/${currentTask.id}/annotations`,
        annotation,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      message.success('标注已保存');
      
      // 更新任务状态
      const updatedTasks = [...tasks];
      updatedTasks[currentTaskIndex].is_labeled = true;
      updatedTasks[currentTaskIndex].annotations.push(response.data);
      setTasks(updatedTasks);
      setAnnotationCount(prev => prev + 1);
      setLastSyncTime(new Date());
      
      // 更新后端任务进度
      if (taskDetail) {
        const newProgress = Math.round(((annotationCount + 1) / tasks.length) * 100);
        await updateTask.mutateAsync({
          id: taskDetail.id,
          payload: {
            progress: newProgress,
            completed_items: annotationCount + 1,
          }
        });
      }
      
      // 自动跳转到下一个未标注任务
      setTimeout(() => {
        handleNextTask();
      }, 1500);
      
    } catch (error) {
      console.error('Failed to save annotation:', error);
      message.error('保存标注失败');
    } finally {
      setSyncInProgress(false);
    }
  }, [annotationPerms.canCreate, id, currentTask, token, tasks, currentTaskIndex, annotationCount, taskDetail, updateTask]);

  // 处理标注更新
  const handleAnnotationUpdate = useCallback(async (annotation: AnnotationResult) => {
    if (!annotationPerms.canEdit) {
      message.error('您没有编辑标注的权限');
      return;
    }

    try {
      setSyncInProgress(true);
      await apiClient.patch(
        `/api/label-studio/annotations/${currentTask.annotations[0]?.id}`,
        annotation,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      message.success('标注已更新');
      
      // 更新本地任务状态
      const updatedTasks = [...tasks];
      updatedTasks[currentTaskIndex].annotations[0] = {
        ...updatedTasks[currentTaskIndex].annotations[0],
        ...annotation
      };
      setTasks(updatedTasks);
      setLastSyncTime(new Date());
      
    } catch (error) {
      console.error('Failed to update annotation:', error);
      message.error('更新标注失败');
    } finally {
      setSyncInProgress(false);
    }
  }, [annotationPerms.canEdit, currentTask, token, tasks, currentTaskIndex]);

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
        title: '任务完成',
        content: '所有标注任务都已完成！',
        onOk: () => navigate(`/tasks/${id}`),
      });
    }
  }, [tasks, currentTaskIndex, navigate, id]);

  // 跳过当前任务
  const handleSkipTask = useCallback(() => {
    handleNextTask();
  }, [handleNextTask]);

  // 返回任务详情
  const handleBackToTask = useCallback(() => {
    navigate(`/tasks/${id}`);
  }, [navigate, id]);

  // 切换全屏模式
  const handleToggleFullscreen = useCallback(() => {
    setFullscreen(prev => !prev);
  }, []);

  // 手动同步进度
  const handleSyncProgress = useCallback(async () => {
    try {
      setSyncInProgress(true);
      await fetchData();
      setLastSyncTime(new Date());
      message.success('同步完成');
    } catch (error) {
      message.error('同步失败');
    } finally {
      setSyncInProgress(false);
    }
  }, [fetchData]);

  // 跳转到指定任务
  const handleJumpToTask = useCallback((taskIndex: number) => {
    if (taskIndex >= 0 && taskIndex < tasks.length) {
      setCurrentTaskIndex(taskIndex);
    }
  }, [tasks.length]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>加载标注任务中...</p>
      </div>
    );
  }

  if (!project || !currentTask) {
    return (
      <Alert
        type="warning"
        message="没有可标注的任务"
        description="所有任务都已完成或没有找到相关任务。"
        showIcon
        action={
          <Button onClick={handleBackToTask}>
            返回任务详情
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
          message="权限不足"
          description={
            <div>
              <p>您当前的角色是：<strong>{roleDisplayName}</strong></p>
              <p>标注功能仅对以下角色开放：</p>
              <ul>
                <li>系统管理员</li>
                <li>业务专家</li>
                <li>数据标注员</li>
              </ul>
              <p>请联系管理员获取相应权限。</p>
            </div>
          }
          action={
            <Button type="primary" onClick={() => navigate('/tasks')}>
              返回任务列表
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
                  返回任务
                </Button>
                <Divider type="vertical" />
                <Title level={4} style={{ margin: 0 }}>
                  {project.title}
                </Title>
                <Tag color="blue">
                  任务 {currentTaskIndex + 1} / {tasks.length}
                </Tag>
                <Tag color="green">
                  {roleDisplayName}
                </Tag>
                {syncInProgress && (
                  <Tag icon={<SyncOutlined spin />} color="processing">
                    同步中
                  </Tag>
                )}
              </Space>
            </Col>
            
            <Col>
              <Space>
                <Tooltip title="同步进度">
                  <Button
                    icon={<ReloadOutlined />}
                    loading={syncInProgress}
                    onClick={handleSyncProgress}
                  />
                </Tooltip>
                <Tooltip title={fullscreen ? "退出全屏" : "全屏模式"}>
                  <Button
                    icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                    onClick={handleToggleFullscreen}
                  />
                </Tooltip>
                <Dropdown
                  menu={{
                    items: tasks.map((task, index) => ({
                      key: index,
                      label: (
                        <Space>
                          <span>任务 {index + 1}</span>
                          {task.is_labeled && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                        </Space>
                      ),
                      onClick: () => handleJumpToTask(index),
                    })),
                  }}
                >
                  <Button icon={<SettingOutlined />}>
                    跳转任务
                  </Button>
                </Dropdown>
                <Statistic
                  title="已完成"
                  value={annotationCount}
                  suffix={`/ ${tasks.length}`}
                  valueStyle={{ fontSize: '16px' }}
                />
                <Progress
                  type="circle"
                  size={50}
                  percent={progress}
                  format={() => `${progress}%`}
                />
              </Space>
            </Col>
          </Row>
          
          {lastSyncTime && (
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <InfoCircleOutlined /> 最后同步: {lastSyncTime.toLocaleTimeString()}
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
                <LabelStudioEmbed
                  projectId={project.id.toString()}
                  taskId={currentTask.id.toString()}
                  token={token}
                  onAnnotationCreate={handleAnnotationCreate}
                  onAnnotationUpdate={handleAnnotationUpdate}
                  onTaskComplete={() => {
                    message.success('任务完成');
                    handleNextTask();
                  }}
                  height="100%"
                />
              </div>
            </Col>

            {/* 右侧控制面板 - 仅在非全屏模式显示 */}
            {!fullscreen && (
              <Col span={6} style={{ height: '100%' }}>
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  {/* 当前任务信息 */}
                  <Card title="当前任务" style={{ marginBottom: 16 }}>
                    <div style={{ marginBottom: 16 }}>
                      <Text strong>待标注文本：</Text>
                      <div style={{ 
                        padding: '12px', 
                        background: '#f5f5f5', 
                        borderRadius: '6px',
                        marginTop: '8px',
                        maxHeight: '120px',
                        overflow: 'auto'
                      }}>
                        {currentTask.data.text}
                      </div>
                    </div>
                    
                    <Space>
                      <Text strong>标注状态：</Text>
                      <Tag color={currentTask.is_labeled ? 'green' : 'orange'}>
                        {currentTask.is_labeled ? '已标注' : '待标注'}
                      </Tag>
                    </Space>
                  </Card>

                  {/* 操作按钮 */}
                  <Card title="操作" style={{ marginBottom: 16 }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Button
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        block
                        disabled={!currentTask.is_labeled}
                        onClick={handleNextTask}
                      >
                        下一个任务
                      </Button>
                      
                      <Button
                        icon={<StepForwardOutlined />}
                        block
                        onClick={handleSkipTask}
                      >
                        跳过此任务
                      </Button>
                      
                      <Button
                        icon={<SaveOutlined />}
                        block
                        loading={syncInProgress}
                        onClick={handleSyncProgress}
                      >
                        手动同步
                      </Button>
                    </Space>
                  </Card>

                  {/* 进度统计 */}
                  <Card title="标注进度" style={{ flex: 1 }}>
                    <div style={{ marginBottom: 16 }}>
                      <Progress
                        percent={progress}
                        status={progress === 100 ? 'success' : 'active'}
                        strokeWidth={8}
                      />
                    </div>
                    
                    <Row gutter={16}>
                      <Col span={12}>
                        <Statistic
                          title="总任务"
                          value={tasks.length}
                          valueStyle={{ fontSize: '18px' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="已完成"
                          value={annotationCount}
                          valueStyle={{ fontSize: '18px', color: '#52c41a' }}
                        />
                      </Col>
                    </Row>
                    
                    <Divider />
                    
                    <Row gutter={16}>
                      <Col span={12}>
                        <Statistic
                          title="剩余"
                          value={tasks.length - annotationCount}
                          valueStyle={{ fontSize: '18px', color: '#faad14' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="当前"
                          value={currentTaskIndex + 1}
                          valueStyle={{ fontSize: '18px', color: '#1890ff' }}
                        />
                      </Col>
                    </Row>

                    {/* 任务列表预览 */}
                    <Divider />
                    <div style={{ maxHeight: '200px', overflow: 'auto' }}>
                      <Text strong style={{ marginBottom: 8, display: 'block' }}>
                        任务列表:
                      </Text>
                      {tasks.slice(0, 10).map((task, index) => (
                        <div 
                          key={task.id}
                          style={{ 
                            padding: '4px 8px',
                            marginBottom: '4px',
                            background: index === currentTaskIndex ? '#e6f7ff' : '#f5f5f5',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            border: index === currentTaskIndex ? '1px solid #1890ff' : '1px solid transparent'
                          }}
                          onClick={() => handleJumpToTask(index)}
                        >
                          <Space size={4}>
                            <Badge 
                              status={task.is_labeled ? 'success' : 'processing'} 
                              size="small"
                            />
                            <Text style={{ fontSize: 12 }}>
                              任务 {index + 1}
                            </Text>
                            {task.is_labeled && (
                              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
                            )}
                          </Space>
                        </div>
                      ))}
                      {tasks.length > 10 && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          ... 还有 {tasks.length - 10} 个任务
                        </Text>
                      )}
                    </div>
                  </Card>
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