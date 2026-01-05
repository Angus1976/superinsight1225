// 完整的标注页面
import { useState, useEffect } from 'react';
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
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  StepForwardOutlined,
  ReloadOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { AnnotationInterface } from '@/components/Annotation';
import { PermissionGuard } from '@/components/Auth/PermissionGuard';
import { useAuthStore } from '@/stores/authStore';
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/utils/permissions';
import apiClient from '@/services/api/client';

const { Title, Text } = Typography;

interface Task {
  id: number;
  data: {
    text: string;
  };
  project: number;
  is_labeled: boolean;
  annotations: any[];
}

interface Project {
  id: number;
  title: string;
  description: string;
  task_number: number;
  total_annotations_number: number;
  label_config: string;
}

const TaskAnnotatePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const { annotation: annotationPerms, roleDisplayName } = usePermissions();
  
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [annotationCount, setAnnotationCount] = useState(0);

  // 获取项目和任务数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // 获取项目信息
        const projectResponse = await apiClient.get(`/api/label-studio/projects/${id}`);
        setProject(projectResponse.data);
        
        // 获取任务列表
        const tasksResponse = await apiClient.get(`/api/label-studio/projects/${id}/tasks`);
        setTasks(tasksResponse.data.results);
        
        // 找到第一个未标注的任务
        const unlabeledIndex = tasksResponse.data.results.findIndex((task: Task) => !task.is_labeled);
        if (unlabeledIndex !== -1) {
          setCurrentTaskIndex(unlabeledIndex);
        }
        
        // 统计已标注数量
        const labeled = tasksResponse.data.results.filter((task: Task) => task.is_labeled).length;
        setAnnotationCount(labeled);
        
      } catch (error) {
        console.error('Failed to fetch data:', error);
        message.error('加载数据失败');
      } finally {
        setLoading(false);
      }
    };

    if (id && token) {
      fetchData();
    }
  }, [id, token]);

  const currentTask = tasks[currentTaskIndex];
  const progress = tasks.length > 0 ? Math.round((annotationCount / tasks.length) * 100) : 0;

  // 处理标注创建
  const handleAnnotationCreate = async (annotation: any) => {
    if (!annotationPerms.canCreate) {
      message.error('您没有创建标注的权限');
      return;
    }

    try {
      const response = await apiClient.post(
        `/api/label-studio/projects/${id}/tasks/${currentTask.id}/annotations`,
        annotation
      );
      
      message.success('标注已保存');
      
      // 更新任务状态
      const updatedTasks = [...tasks];
      updatedTasks[currentTaskIndex].is_labeled = true;
      updatedTasks[currentTaskIndex].annotations.push(response.data);
      setTasks(updatedTasks);
      setAnnotationCount(prev => prev + 1);
      
      // 自动跳转到下一个未标注任务
      setTimeout(() => {
        handleNextTask();
      }, 1500);
      
    } catch (error) {
      console.error('Failed to save annotation:', error);
      message.error('保存标注失败');
    }
  };

  // 处理标注更新
  const handleAnnotationUpdate = async (annotation: any) => {
    if (!annotationPerms.canEdit) {
      message.error('您没有编辑标注的权限');
      return;
    }

    try {
      await apiClient.patch(
        `/api/label-studio/annotations/${currentTask.annotations[0]?.id}`,
        annotation
      );
      
      message.success('标注已更新');
      
      // 更新本地任务状态
      const updatedTasks = [...tasks];
      updatedTasks[currentTaskIndex].annotations[0] = {
        ...updatedTasks[currentTaskIndex].annotations[0],
        ...annotation
      };
      setTasks(updatedTasks);
      
    } catch (error) {
      console.error('Failed to update annotation:', error);
      message.error('更新标注失败');
    }
  };

  // 跳转到下一个任务
  const handleNextTask = () => {
    const nextUnlabeledIndex = tasks.findIndex((task, index) => 
      index > currentTaskIndex && !task.is_labeled
    );
    
    if (nextUnlabeledIndex !== -1) {
      setCurrentTaskIndex(nextUnlabeledIndex);
    } else {
      // 所有任务都已完成
      message.success('所有任务都已完成！');
      navigate(`/tasks/${id}`);
    }
  };

  // 跳过当前任务
  const handleSkipTask = () => {
    handleNextTask();
  };

  // 返回任务详情
  const handleBackToTask = () => {
    navigate(`/tasks/${id}`);
  };

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
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* 顶部工具栏 */}
      <Card style={{ marginBottom: 16, borderRadius: 0 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button 
                icon={<ArrowLeftOutlined />} 
                onClick={handleBackToTask}
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
            </Space>
          </Col>
          
          <Col>
            <Space>
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
      </Card>

      {/* 标注区域 */}
      <div style={{ flex: 1, display: 'flex' }}>
        <Row style={{ width: '100%', height: '100%' }}>
          {/* 左侧：标注界面 */}
          <Col span={18} style={{ height: '100%' }}>
            <Card 
              title="标注"
              style={{ height: '100%', marginRight: 8 }}
              styles={{ body: { height: 'calc(100% - 57px)', padding: '16px' } }}
            >
              <AnnotationInterface
                project={project}
                task={currentTask}
                onAnnotationSave={handleAnnotationCreate}
                onAnnotationUpdate={handleAnnotationUpdate}
                loading={loading}
              />
            </Card>
          </Col>

          {/* 右侧：任务信息和控制面板 */}
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
                
                <div>
                  <Text strong>标注状态：</Text>
                  <Tag color={currentTask.is_labeled ? 'green' : 'orange'}>
                    {currentTask.is_labeled ? '已标注' : '待标注'}
                  </Tag>
                </div>
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
                    icon={<ReloadOutlined />}
                    block
                    onClick={() => window.location.reload()}
                  >
                    刷新页面
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
              </Card>
            </div>
          </Col>
        </Row>
      </div>
    </div>
    </PermissionGuard>
  );
};

export default TaskAnnotatePage;