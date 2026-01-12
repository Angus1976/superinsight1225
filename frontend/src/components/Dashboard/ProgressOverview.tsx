// Progress monitoring panel with real-time updates
import { Card, Row, Col, Progress, Tag, Space, Tooltip, Badge, Statistic, List, Avatar } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  ProjectOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';
import { useDashboard } from '@/hooks/useDashboard';

interface ProjectProgress {
  id: string;
  name: string;
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  pendingTasks: number;
  progress: number;
  status: 'on_track' | 'at_risk' | 'delayed' | 'completed';
  assignees: string[];
  deadline?: string;
  lastUpdated: string;
}

interface TaskStatusDistribution {
  status: string;
  count: number;
  color: string;
  icon: React.ReactNode;
}

interface ProgressOverviewProps {
  tenantId?: string;
  workspaceId?: string;
  refreshInterval?: number;
  showMilestones?: boolean;
}

export const ProgressOverview: React.FC<ProgressOverviewProps> = ({
  tenantId,
  workspaceId,
  refreshInterval = 30000,
}) => {
  const { t } = useTranslation('dashboard');
  const { isLoading, refetch } = useDashboard({ tenantId, workspaceId });
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Auto-refresh functionality
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
      setLastRefresh(new Date());
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [refetch, refreshInterval]);

  // Mock project progress data (would come from API)
  const mockProjects: ProjectProgress[] = [
    {
      id: '1',
      name: '客服对话标注项目',
      totalTasks: 500,
      completedTasks: 350,
      inProgressTasks: 100,
      pendingTasks: 50,
      progress: 70,
      status: 'on_track',
      assignees: ['张三', '李四', '王五'],
      deadline: '2026-02-15',
      lastUpdated: new Date().toISOString(),
    },
    {
      id: '2',
      name: '医疗文档实体识别',
      totalTasks: 300,
      completedTasks: 180,
      inProgressTasks: 80,
      pendingTasks: 40,
      progress: 60,
      status: 'at_risk',
      assignees: ['赵六', '钱七'],
      deadline: '2026-01-30',
      lastUpdated: new Date().toISOString(),
    },
    {
      id: '3',
      name: '金融报告分类',
      totalTasks: 200,
      completedTasks: 200,
      inProgressTasks: 0,
      pendingTasks: 0,
      progress: 100,
      status: 'completed',
      assignees: ['孙八'],
      lastUpdated: new Date().toISOString(),
    },
  ];

  // Task status distribution
  const statusDistribution: TaskStatusDistribution[] = [
    { status: t('progress.completed') || 'Completed', count: 730, color: '#52c41a', icon: <CheckCircleOutlined /> },
    { status: t('progress.inProgress') || 'In Progress', count: 180, color: '#1890ff', icon: <SyncOutlined spin /> },
    { status: t('progress.pending') || 'Pending', count: 90, color: '#faad14', icon: <ClockCircleOutlined /> },
  ];

  const totalTasks = statusDistribution.reduce((sum, item) => sum + item.count, 0);

  // Get status color and icon
  const getStatusConfig = (status: ProjectProgress['status']) => {
    switch (status) {
      case 'completed':
        return { color: 'success', text: t('progress.statusCompleted') || 'Completed', icon: <CheckCircleOutlined /> };
      case 'on_track':
        return { color: 'processing', text: t('progress.statusOnTrack') || 'On Track', icon: <SyncOutlined spin /> };
      case 'at_risk':
        return { color: 'warning', text: t('progress.statusAtRisk') || 'At Risk', icon: <ExclamationCircleOutlined /> };
      case 'delayed':
        return { color: 'error', text: t('progress.statusDelayed') || 'Delayed', icon: <ClockCircleOutlined /> };
      default:
        return { color: 'default', text: status, icon: <ProjectOutlined /> };
    }
  };

  return (
    <div>
      {/* Overall Progress Summary */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card>
            <Statistic
              title={t('progress.totalProjects') || 'Total Projects'}
              value={mockProjects.length}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <Statistic
              title={t('progress.overallProgress') || 'Overall Progress'}
              value={Math.round(mockProjects.reduce((sum, p) => sum + p.progress, 0) / mockProjects.length)}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <Statistic
              title={t('progress.totalTasks') || 'Total Tasks'}
              value={totalTasks}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Task Status Distribution */}
      <Card 
        title={t('progress.taskDistribution') || 'Task Status Distribution'} 
        style={{ marginBottom: 24 }}
        extra={
          <Tooltip title={`${t('common.lastUpdated')}: ${lastRefresh.toLocaleTimeString()}`}>
            <Badge status="processing" text={t('progress.realTime') || 'Real-time'} />
          </Tooltip>
        }
      >
        <Row gutter={[16, 16]}>
          {statusDistribution.map((item, index) => (
            <Col xs={24} sm={8} key={index}>
              <Card size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <span style={{ color: item.color }}>{item.icon}</span>
                    <span>{item.status}</span>
                  </Space>
                  <Progress
                    percent={Math.round((item.count / totalTasks) * 100)}
                    strokeColor={item.color}
                    format={() => item.count}
                  />
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Project Progress List */}
      <Card title={t('progress.projectProgress') || 'Project Progress'}>
        <List
          loading={isLoading}
          itemLayout="horizontal"
          dataSource={mockProjects}
          renderItem={(project) => {
            const statusConfig = getStatusConfig(project.status);
            return (
              <List.Item
                actions={[
                  <Tag color={statusConfig.color} icon={statusConfig.icon}>
                    {statusConfig.text}
                  </Tag>,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar 
                      style={{ backgroundColor: project.status === 'completed' ? '#52c41a' : '#1890ff' }}
                      icon={<ProjectOutlined />}
                    />
                  }
                  title={
                    <Space>
                      <span>{project.name}</span>
                      {project.deadline && (
                        <Tooltip title={t('progress.deadline') || 'Deadline'}>
                          <Tag icon={<ClockCircleOutlined />}>{project.deadline}</Tag>
                        </Tooltip>
                      )}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Progress
                        percent={project.progress}
                        status={project.status === 'completed' ? 'success' : project.status === 'at_risk' ? 'exception' : 'active'}
                        size="small"
                      />
                      <Space size="small">
                        <Tag color="green">{project.completedTasks} {t('progress.completed')}</Tag>
                        <Tag color="blue">{project.inProgressTasks} {t('progress.inProgress')}</Tag>
                        <Tag color="orange">{project.pendingTasks} {t('progress.pending')}</Tag>
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            );
          }}
        />
      </Card>
    </div>
  );
};

export default ProgressOverview;
