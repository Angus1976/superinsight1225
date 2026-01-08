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
import { useEffect, useState } from 'react';

interface RealTimeMetricsProps {
  refreshInterval?: number;
  showTargets?: boolean;
}

export const RealTimeMetrics: React.FC<RealTimeMetricsProps> = ({
  refreshInterval = 30000, // 30 seconds default
  showTargets = true,
}) => {
  const { t } = useTranslation('dashboard');
  const { summary, annotationEfficiency, userActivity, isLoading, error, refetch } = useDashboard();
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Auto-refresh functionality
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

  // Extract metrics from API data or use fallback values
  const metrics = {
    activeTasks: summary?.business_metrics?.projects?.summary?.total_projects || 12,
    todayAnnotations: annotationEfficiency?.summary?.avg_annotations_per_hour ? 
      Math.round(annotationEfficiency.summary.avg_annotations_per_hour * 8) : 156, // 8 hours workday
    totalCorpus: 25000, // This would come from a separate API
    totalBilling: 8500, // This would come from billing API
    qualityScore: annotationEfficiency?.summary?.avg_quality_score || 0.85,
    completionRate: annotationEfficiency?.summary?.avg_completion_rate || 0.92,
    activeUsers: userActivity?.summary?.avg_active_users || 8,
    avgResponseTime: summary?.system_performance?.avg_request_duration?.total || 0.25,
  };

  // Calculate trends (mock data for now)
  const trends = {
    activeTasks: 5.2,
    todayAnnotations: 12.5,
    totalCorpus: 8.3,
    totalBilling: -3.1,
    qualityScore: 2.1,
    completionRate: 1.8,
    activeUsers: 15.6,
    avgResponseTime: -8.2,
  };

  // Define targets for progress tracking
  const targets = showTargets ? {
    activeTasks: 15,
    todayAnnotations: 200,
    qualityScore: 0.90,
    completionRate: 0.95,
    activeUsers: 12,
  } : {};

  return (
    <div>
      <Row gutter={[16, 16]}>
        {/* Core Business Metrics */}
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.activeTasks')}
            subtitle={t('metrics.activeTasksSubtitle')}
            value={metrics.activeTasks}
            icon={<FileTextOutlined />}
            color="#1890ff"
            loading={isLoading}
            trend={trends.activeTasks}
            trendLabel={t('trends.comparedToYesterday')}
            target={targets.activeTasks}
            progress={metrics.activeTasks}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
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
            trend={trends.todayAnnotations}
            trendLabel={t('trends.comparedToYesterday')}
            target={targets.todayAnnotations}
            progress={metrics.todayAnnotations}
            status={metrics.todayAnnotations >= (targets.todayAnnotations || 0) * 0.8 ? 'success' : 'warning'}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
          />
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.totalCorpus')}
            subtitle={t('metrics.totalCorpusSubtitle')}
            value={metrics.totalCorpus.toLocaleString()}
            icon={<DatabaseOutlined />}
            color="#faad14"
            loading={isLoading}
            trend={trends.totalCorpus}
            trendLabel={t('trends.comparedToLastWeek')}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
          />
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('metrics.totalBilling')}
            subtitle={t('metrics.totalBillingSubtitle')}
            value={metrics.totalBilling.toLocaleString()}
            suffix="¥"
            icon={<DollarOutlined />}
            color="#722ed1"
            loading={isLoading}
            trend={trends.totalBilling}
            trendLabel={t('trends.comparedToLastMonth')}
            status={trends.totalBilling < 0 ? 'warning' : 'success'}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
          />
        </Col>
      </Row>

      {/* Quality and Performance Metrics */}
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
            trend={trends.qualityScore}
            trendLabel={t('trends.comparedToLastWeek')}
            target={targets.qualityScore ? targets.qualityScore * 100 : undefined}
            progress={metrics.qualityScore * 100}
            status={metrics.qualityScore >= 0.85 ? 'success' : metrics.qualityScore >= 0.75 ? 'warning' : 'error'}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
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
            trend={trends.completionRate}
            trendLabel={t('trends.comparedToLastWeek')}
            target={targets.completionRate ? targets.completionRate * 100 : undefined}
            progress={metrics.completionRate * 100}
            status={metrics.completionRate >= 0.90 ? 'success' : 'warning'}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
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
            trend={trends.activeUsers}
            trendLabel={t('trends.comparedToYesterday')}
            target={targets.activeUsers}
            progress={metrics.activeUsers}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
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
            trend={trends.avgResponseTime}
            trendLabel={t('trends.comparedToLastHour')}
            status={metrics.avgResponseTime <= 0.5 ? 'success' : metrics.avgResponseTime <= 1.0 ? 'warning' : 'error'}
            refreshable
            onRefresh={refetch}
            lastUpdated={lastRefresh}
          />
        </Col>
      </Row>
    </div>
  );
};