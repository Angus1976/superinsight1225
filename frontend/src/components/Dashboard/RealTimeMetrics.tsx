// Real-time metrics component for enterprise dashboard
import { Row, Col, Alert } from 'antd';
import {
  FileTextOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  DollarOutlined,
  UserOutlined,
  ClockCircleOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { MetricCard } from './MetricCard';
import { useDashboard } from '@/hooks/useDashboard';
import { useTaskStats } from '@/hooks/useTask';
import { useEffect, useState } from 'react';

export type DashboardMetricKey =
  | 'activeTasks'
  | 'todayAnnotations'
  | 'totalCorpus'
  | 'totalBilling'
  | 'qualityScore'
  | 'completionRate'
  | 'activeUsers'
  | 'avgResponseTime';

interface RealTimeMetricsProps {
  refreshInterval?: number;
  showTargets?: boolean;
  selectedMetric?: DashboardMetricKey | null;
  onMetricClick?: (key: DashboardMetricKey) => void;
}

export const RealTimeMetrics: React.FC<RealTimeMetricsProps> = ({
  refreshInterval = 30000,
  showTargets = true,
  selectedMetric,
  onMetricClick,
}) => {
  const { t } = useTranslation('dashboard');
  const { summary, annotationEfficiency, userActivity, isLoading, error, refetch } = useDashboard();
  const { data: taskStats } = useTaskStats();
  const [lastRefresh, setLastRefresh] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
      setLastRefresh(new Date());
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [refetch, refreshInterval]);

  if (error) {
    return (
      <Alert
        type="warning"
        message={t('errors.dataLoadFailed')}
        description={t('errors.backendConnection')}
        showIcon
        style={{ marginBottom: 24 }}
      />
    );
  }

  // Real data from task stats API, with safe fallbacks
  const total = taskStats?.total ?? 0;
  const completed = taskStats?.completed ?? 0;
  const metrics = {
    activeTasks: taskStats?.in_progress ?? 0,
    todayAnnotations: annotationEfficiency?.summary?.avg_annotations_per_hour
      ? Math.round(annotationEfficiency.summary.avg_annotations_per_hour * 8)
      : completed,
    totalCorpus: total,
    totalBilling: 0,
    qualityScore: annotationEfficiency?.summary?.avg_quality_score ?? 0,
    completionRate: total > 0 ? completed / total : 0,
    activeUsers: userActivity?.summary?.avg_active_users ?? 0,
    avgResponseTime: summary?.system_performance?.avg_request_duration?.total ?? 0,
  };

  const targets = showTargets ? {
    activeTasks: 15,
    todayAnnotations: 200,
    qualityScore: 0.90,
    completionRate: 0.95,
    activeUsers: 12,
  } : {};

  const handleClick = (key: DashboardMetricKey) => {
    onMetricClick?.(key);
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.activeTasks')}
            subtitle={t('metrics.activeTasksSubtitle')}
            value={metrics.activeTasks}
            icon={<FileTextOutlined />}
            color="#1890ff"
            loading={isLoading}
            target={targets.activeTasks}
            progress={metrics.activeTasks}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
            onClick={() => handleClick('activeTasks')}
            selected={selectedMetric === 'activeTasks'}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.todayAnnotations')}
            subtitle={t('metrics.todayAnnotationsSubtitle')}
            value={metrics.todayAnnotations}
            icon={<CheckCircleOutlined />}
            color="#52c41a"
            loading={isLoading}
            target={targets.todayAnnotations}
            progress={metrics.todayAnnotations}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
            onClick={() => handleClick('todayAnnotations')}
            selected={selectedMetric === 'todayAnnotations'}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.totalCorpus')}
            subtitle={t('metrics.totalCorpusSubtitle')}
            value={metrics.totalCorpus}
            icon={<DatabaseOutlined />}
            color="#faad14"
            loading={isLoading}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
            onClick={() => handleClick('totalCorpus')}
            selected={selectedMetric === 'totalCorpus'}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.totalBilling')}
            subtitle={t('metrics.totalBillingSubtitle')}
            value={metrics.totalBilling}
            suffix="¥"
            icon={<DollarOutlined />}
            color="#722ed1"
            loading={isLoading}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.qualityScore')}
            subtitle={t('metrics.qualityScoreSubtitle')}
            value={(metrics.qualityScore * 100).toFixed(1)}
            suffix="%"
            icon={<TrophyOutlined />}
            color="#13c2c2"
            loading={isLoading}
            target={targets.qualityScore ? targets.qualityScore * 100 : undefined}
            progress={metrics.qualityScore * 100}
            status={metrics.qualityScore >= 0.85 ? 'success' : metrics.qualityScore >= 0.75 ? 'warning' : 'error'}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.completionRate')}
            subtitle={t('metrics.completionRateSubtitle')}
            value={(metrics.completionRate * 100).toFixed(1)}
            suffix="%"
            icon={<CheckCircleOutlined />}
            color="#52c41a"
            loading={isLoading}
            target={targets.completionRate ? targets.completionRate * 100 : undefined}
            progress={metrics.completionRate * 100}
            status={metrics.completionRate >= 0.90 ? 'success' : 'warning'}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
            onClick={() => handleClick('completionRate')}
            selected={selectedMetric === 'completionRate'}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.activeUsers')}
            subtitle={t('metrics.activeUsersSubtitle')}
            value={metrics.activeUsers}
            icon={<UserOutlined />}
            color="#eb2f96"
            loading={isLoading}
            target={targets.activeUsers}
            progress={metrics.activeUsers}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.avgResponseTime')}
            subtitle={t('metrics.avgResponseTimeSubtitle')}
            value={metrics.avgResponseTime.toFixed(2)}
            suffix="s"
            icon={<ClockCircleOutlined />}
            color="#fa8c16"
            loading={isLoading}
            status={metrics.avgResponseTime <= 0.5 ? 'success' : metrics.avgResponseTime <= 1.0 ? 'warning' : 'error'}
            refreshable onRefresh={refetch} lastUpdated={lastRefresh}
          />
        </Col>
      </Row>
    </div>
  );
};
