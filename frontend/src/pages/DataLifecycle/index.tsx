/**
 * Data Lifecycle Dashboard Page
 * 
 * Main overview page for data lifecycle management.
 * Displays data flow visualization, summary statistics, and quick actions.
 */

import { useState, useEffect } from 'react';
import { Row, Col, Typography, Card, Statistic, Progress, List, Tag, Button, Space, Spin, Alert } from 'antd';
import {
  DatabaseOutlined,
  FileTextOutlined,
  StarOutlined,
  CheckCircleOutlined,
  ToolOutlined,
  ExperimentOutlined,
  ArrowRightOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTempData, useSampleLibrary, useReview, useAnnotationTask, useEnhancement, useAITrial } from '@/hooks/useDataLifecycle';
import { useAuthStore } from '@/stores/authStore';
import { HelpIcon } from '@/components/SmartHelp';
import CreateTempDataModal from '@/components/DataLifecycle/CreateTempDataModal';
import AddToLibraryModal from '@/components/DataLifecycle/AddToLibraryModal';
import SubmitReviewModal from '@/components/DataLifecycle/SubmitReviewModal';
import CreateTaskModal from '@/components/DataLifecycle/CreateTaskModal';
import CreateEnhancementModal from '@/components/DataLifecycle/CreateEnhancementModal';
import CreateTrialModal from '@/components/DataLifecycle/CreateTrialModal';

const { Title, Text, Paragraph } = Typography;

// ============================================================================
// Dashboard Card Component
// ============================================================================

interface DashboardCardProps {
  title: string;
  icon: React.ReactNode;
  count: number;
  status: 'success' | 'warning' | 'error' | 'processing';
  description: string;
  link: string;
  color: string;
}

const DashboardCard: React.FC<DashboardCardProps> = ({ title, icon, count, status, description, link, color }) => {
  const { t } = useTranslation('dataLifecycle');
  
  const getStatusColor = () => {
    switch (status) {
      case 'success': return '#52c41a';
      case 'warning': return '#faad14';
      case 'error': return '#ff4d4f';
      case 'processing': return '#1890ff';
      default: return '#1890ff';
    }
  };

  return (
    <Card
      hoverable
      style={{ height: '100%' }}
      className="data-lifecycle-card"
    >
      <Row align="middle" gutter={16}>
        <Col>
          <div style={{ 
            width: 48, 
            height: 48, 
            borderRadius: 8, 
            backgroundColor: `${color}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 24,
            color: color
          }}>
            {icon}
          </div>
        </Col>
        <Col flex="auto">
          <Text type="secondary" style={{ fontSize: 12 }}>{title}</Text>
          <Row align="middle" gutter={8}>
            <Col>
              <Statistic value={count} valueStyle={{ fontSize: 28, fontWeight: 600 }} />
            </Col>
            <Col>
              <Progress 
                type="circle" 
                percent={Math.min(count * 10, 100)} 
                width={32} 
                strokeColor={getStatusColor()}
                showInfo={false}
              />
            </Col>
          </Row>
          <Text type="secondary" style={{ fontSize: 12 }}>{description}</Text>
        </Col>
        <Col>
          <Button type="text" icon={<ArrowRightOutlined />} />
        </Col>
      </Row>
    </Card>
  );
};

// ============================================================================
// Summary Statistics Component
// ============================================================================

interface SummaryStatsProps {
  tempDataCount: number;
  sampleCount: number;
  pendingReviews: number;
  pendingTasks: number;
  runningEnhancements: number;
  runningTrials: number;
}

const SummaryStats: React.FC<SummaryStatsProps> = ({
  tempDataCount,
  sampleCount,
  pendingReviews,
  pendingTasks,
  runningEnhancements,
  runningTrials,
}) => {
  const { t } = useTranslation('dataLifecycle');

  const stats = [
    { label: t('tempData.title'), value: tempDataCount, color: '#1890ff' },
    { label: t('sampleLibrary.title'), value: sampleCount, color: '#52c41a' },
    { label: t('review.title'), value: pendingReviews, color: '#faad14', suffix: t('review.status.pending') },
    { label: t('annotationTask.title'), value: pendingTasks, color: '#722ed1', suffix: t('annotationTask.status.pending') },
    { label: t('enhancement.title'), value: runningEnhancements, color: '#13c2c2', suffix: t('enhancement.status.running') },
    { label: t('aiTrial.title'), value: runningTrials, color: '#eb2f96', suffix: t('aiTrial.status.running') },
  ];

  return (
    <Card title={t('interface.title')} extra={<HelpIcon helpKey="dataLifecycle" />}>
      <Row gutter={[16, 16]}>
        {stats.map((stat, index) => (
          <Col xs={24} sm={12} md={8} lg={4} key={index}>
            <div style={{ textAlign: 'center', padding: '8px 0' }}>
              <div style={{ fontSize: 32, fontWeight: 600, color: stat.color }}>
                {stat.value}
              </div>
              <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
                {stat.label}
                {stat.suffix && (
                  <Tag color={stat.color} style={{ marginLeft: 4 }}>
                    {stat.suffix}
                  </Tag>
                )}
              </div>
            </div>
          </Col>
        ))}
      </Row>
    </Card>
  );
};

// ============================================================================
// Quick Actions Component
// ============================================================================

interface ModalVisibility {
  createTempData: boolean;
  addToLibrary: boolean;
  submitReview: boolean;
  createTask: boolean;
  createEnhancement: boolean;
  createTrial: boolean;
}

const QuickActions: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();

  // Modal visibility state
  const [modalVisibility, setModalVisibility] = useState<ModalVisibility>({
    createTempData: false,
    addToLibrary: false,
    submitReview: false,
    createTask: false,
    createEnhancement: false,
    createTrial: false,
  });

  const actions = [
    { key: 'createTempData', label: t('tempData.actions.create'), icon: <DatabaseOutlined />, permission: 'dataLifecycle.create', color: '#1890ff' },
    { key: 'addToLibrary', label: t('sampleLibrary.actions.addToLibrary'), icon: <StarOutlined />, permission: 'sampleLibrary.create', color: '#52c41a' },
    { key: 'submitReview', label: t('review.actions.submit'), icon: <CheckCircleOutlined />, permission: 'review.create', color: '#faad14' },
    { key: 'createTask', label: t('annotationTask.actions.create'), icon: <FileTextOutlined />, permission: 'annotationTask.create', color: '#722ed1' },
    { key: 'createEnhancement', label: t('enhancement.actions.create'), icon: <ToolOutlined />, permission: 'enhancement.create', color: '#13c2c2' },
    { key: 'createTrial', label: t('aiTrial.actions.create'), icon: <ExperimentOutlined />, permission: 'aiTrial.create', color: '#eb2f96' },
  ];

  const handleAction = (key: string) => {
    setModalVisibility(prev => ({ ...prev, [key]: true }));
  };

  const closeModal = (key: keyof ModalVisibility) => {
    setModalVisibility(prev => ({ ...prev, [key]: false }));
  };

  return (
    <Card title={t('common.quickActions')} style={{ marginTop: 16 }}>
      <Row gutter={[16, 16]}>
        {actions.map((action, index) => (
          <Col xs={24} sm={12} md={8} key={index}>
            <Button
              type="default"
              icon={action.icon}
              onClick={() => handleAction(action.key)}
              block
              style={{ 
                height: 60,
                borderColor: action.color,
                color: action.color,
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 500 }}>{action.label}</div>
            </Button>
          </Col>
        ))}
      </Row>

      {/* Modal components */}
      <CreateTempDataModal
        visible={modalVisibility.createTempData}
        onClose={() => closeModal('createTempData')}
      />
      <AddToLibraryModal
        visible={modalVisibility.addToLibrary}
        onClose={() => closeModal('addToLibrary')}
      />
      <SubmitReviewModal
        visible={modalVisibility.submitReview}
        onClose={() => closeModal('submitReview')}
      />
      <CreateTaskModal
        visible={modalVisibility.createTask}
        onClose={() => closeModal('createTask')}
      />
      <CreateEnhancementModal
        visible={modalVisibility.createEnhancement}
        onClose={() => closeModal('createEnhancement')}
      />
      <CreateTrialModal
        visible={modalVisibility.createTrial}
        onClose={() => closeModal('createTrial')}
      />
    </Card>
  );
};

// ============================================================================
// Recent Activity Component
// ============================================================================

interface ActivityItem {
  id: string;
  type: string;
  action: string;
  target: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed';
}

const RecentActivity: React.FC = () => {
  const { t } = useTranslation(['dataLifecycle', 'common']);

  // Mock activity data - in real implementation, this would come from API
  const activities: ActivityItem[] = [
    { id: '1', type: 'tempData', action: 'created', target: 'Document #1234', timestamp: '2024-01-15 10:30:00', status: 'success' },
    { id: '2', type: 'review', action: 'approved', target: 'Enhancement #5678', timestamp: '2024-01-15 10:25:00', status: 'success' },
    { id: '3', type: 'enhancement', action: 'started', target: 'Job #9012', timestamp: '2024-01-15 10:20:00', status: 'pending' },
    { id: '4', type: 'sample', action: 'added', target: 'Sample #3456', timestamp: '2024-01-15 10:15:00', status: 'success' },
    { id: '5', type: 'trial', action: 'completed', target: 'Trial #7890', timestamp: '2024-01-15 10:10:00', status: 'success' },
  ];

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'tempData': return <DatabaseOutlined style={{ color: '#1890ff' }} />;
      case 'review': return <CheckCircleOutlined style={{ color: '#faad14' }} />;
      case 'enhancement': return <ToolOutlined style={{ color: '#13c2c2' }} />;
      case 'sample': return <StarOutlined style={{ color: '#52c41a' }} />;
      case 'trial': return <ExperimentOutlined style={{ color: '#eb2f96' }} />;
      default: return <FileTextOutlined />;
    }
  };

  const getStatusTag = (status: ActivityItem['status']) => {
    switch (status) {
      case 'success': return <Tag color="success">{t(`common.status.${status}`)}</Tag>;
      case 'pending': return <Tag color="processing">{t(`common.status.${status}`)}</Tag>;
      case 'failed': return <Tag color="error">{t(`common.status.${status}`)}</Tag>;
      default: return null;
    }
  };

  return (
    <Card title={t('common.recentActivity')} style={{ marginTop: 16 }}>
      <List
        itemLayout="horizontal"
        dataSource={activities}
        renderItem={(item) => (
          <List.Item>
            <List.Item.Meta
              avatar={getActivityIcon(item.type)}
              title={
                <Space>
                  <Text strong>{item.target}</Text>
                  {getStatusTag(item.status)}
                </Space>
              }
              description={`${t(`common.${item.action}`)} - ${item.timestamp}`}
            />
          </List.Item>
        )}
      />
    </Card>
  );
};

// ============================================================================
// Main Dashboard Component
// ============================================================================

const DataLifecycleDashboard: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  
  // Use hooks for data fetching
  const { data: tempData, loading: tempDataLoading, pagination: tempDataPagination, fetchTempData } = useTempData();
  const { samples, loading: samplesLoading, pagination: samplePagination, fetchSamples } = useSampleLibrary();
  const { reviews, loading: reviewsLoading, pagination: reviewPagination, fetchReviews } = useReview();
  const { tasks, loading: tasksLoading, pagination: taskPagination, fetchTasks } = useAnnotationTask();
  const { jobs: enhancements, loading: enhancementsLoading, pagination: enhancementPagination, fetchJobs } = useEnhancement();
  const { trials, loading: trialsLoading, pagination: trialPagination, fetchTrials } = useAITrial();

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        await Promise.allSettled([
          fetchTempData({ page: 1 }),
          fetchSamples({ page: 1 }),
          fetchReviews({ page: 1 }),
          fetchTasks({ page: 1 }),
          fetchJobs({ page: 1 }),
          fetchTrials({ page: 1 }),
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Calculate summary statistics using pagination.total for accurate counts
  const tempDataCount = tempDataPagination.total;
  const sampleCount = samplePagination.total;
  const pendingReviews = reviews.filter(r => r.status === 'pending').length;
  const pendingTasks = tasks.filter(t => t.status === 'pending').length;
  const runningEnhancements = enhancements.filter(e => e.status === 'running').length;
  const runningTrials = trials.filter(t => t.status === 'running').length;

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 20px' }}>
        <Spin size="large" tip={t('interface.loading')} />
      </div>
    );
  }

  return (
    <div data-help-key="dataLifecycleDashboard">
      <Title level={4} style={{ marginBottom: 24 }}>
        {t('interface.title')}
        <HelpIcon helpKey="dataLifecycle" size="small" />
      </Title>

      {/* Summary Statistics */}
      <SummaryStats
        tempDataCount={tempDataCount}
        sampleCount={sampleCount}
        pendingReviews={pendingReviews}
        pendingTasks={pendingTasks}
        runningEnhancements={runningEnhancements}
        runningTrials={runningTrials}
      />

      {/* Quick Actions */}
      <QuickActions />

      {/* Dashboard Cards */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} md={8} lg={4}>
          <DashboardCard
            title={t('tabs.tempData')}
            icon={<DatabaseOutlined />}
            count={tempDataCount}
            status="success"
            description={t('tempData.description')}
            link="/data-lifecycle/temp-data"
            color="#1890ff"
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <DashboardCard
            title={t('tabs.sampleLibrary')}
            icon={<StarOutlined />}
            count={sampleCount}
            status="success"
            description={t('sampleLibrary.description')}
            link="/data-lifecycle/samples"
            color="#52c41a"
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <DashboardCard
            title={t('tabs.review')}
            icon={<CheckCircleOutlined />}
            count={pendingReviews}
            status={pendingReviews > 0 ? 'warning' : 'success'}
            description={`${pendingReviews} ${t('review.status.pending')}`}
            link="/data-lifecycle/review"
            color="#faad14"
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <DashboardCard
            title={t('tabs.annotation')}
            icon={<FileTextOutlined />}
            count={pendingTasks}
            status={pendingTasks > 0 ? 'warning' : 'success'}
            description={`${pendingTasks} ${t('annotationTask.status.pending')}`}
            link="/data-lifecycle/tasks"
            color="#722ed1"
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <DashboardCard
            title={t('tabs.enhancement')}
            icon={<ToolOutlined />}
            count={runningEnhancements}
            status={runningEnhancements > 0 ? 'processing' : 'success'}
            description={`${runningEnhancements} ${t('enhancement.status.running')}`}
            link="/data-lifecycle/enhancement"
            color="#13c2c2"
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <DashboardCard
            title={t('tabs.aiTrial')}
            icon={<ExperimentOutlined />}
            count={runningTrials}
            status={runningTrials > 0 ? 'processing' : 'success'}
            description={`${runningTrials} ${t('aiTrial.status.running')}`}
            link="/data-lifecycle/trials"
            color="#eb2f96"
          />
        </Col>
      </Row>

      {/* Recent Activity */}
      <RecentActivity />
    </div>
  );
};

export default DataLifecycleDashboard;