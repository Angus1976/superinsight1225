// Overview cards component with multi-tenant support
import { Row, Col, Card, Tag, Space, Tooltip } from 'antd';
import {
  TeamOutlined,
  AppstoreOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { MetricCard } from './MetricCard';
import { useDashboard } from '@/hooks/useDashboard';
import { useAuthStore } from '@/stores/authStore';

interface OverviewCardsProps {
  tenantId?: string;
  workspaceId?: string;
  showContext?: boolean;
  compact?: boolean;
}

export const OverviewCards: React.FC<OverviewCardsProps> = ({
  tenantId,
  workspaceId,
  showContext = true,
  compact = false,
}) => {
  const { t } = useTranslation('dashboard');
  const { currentTenant, currentWorkspace } = useAuthStore();
  const { summary, annotationEfficiency, isLoading, refetch } = useDashboard({
    tenantId,
    workspaceId,
  });

  // Display context info
  const displayTenant = currentTenant?.name || tenantId || t('common.allTenants');
  const displayWorkspace = currentWorkspace?.name || workspaceId || t('common.allWorkspaces');

  // Extract metrics
  const metrics = {
    totalProjects: summary?.business_metrics?.projects?.summary?.total_projects || 0,
    activeProjects: summary?.business_metrics?.projects?.summary?.projects_on_track || 0,
    completedProjects: summary?.business_metrics?.projects?.summary?.completed_projects || 0,
    avgCompletion: summary?.business_metrics?.projects?.summary?.avg_completion_percentage || 0,
    qualityScore: annotationEfficiency?.summary?.avg_quality_score || 0,
    completionRate: annotationEfficiency?.summary?.avg_completion_rate || 0,
  };

  const colSpan = compact ? { xs: 24, sm: 12, lg: 8 } : { xs: 24, sm: 12, lg: 6 };

  return (
    <div>
      {/* Context Header */}
      {showContext && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space size="large">
            <Tooltip title={t('context.currentTenant')}>
              <Space>
                <TeamOutlined />
                <span>{t('context.tenant')}:</span>
                <Tag color="blue">{displayTenant}</Tag>
              </Space>
            </Tooltip>
            <Tooltip title={t('context.currentWorkspace')}>
              <Space>
                <AppstoreOutlined />
                <span>{t('context.workspace')}:</span>
                <Tag color="green">{displayWorkspace}</Tag>
              </Space>
            </Tooltip>
          </Space>
        </Card>
      )}

      {/* Metric Cards */}
      <Row gutter={[16, 16]}>
        <Col {...colSpan}>
          <MetricCard
            title={t('overview.totalProjects')}
            subtitle={t('overview.totalProjectsSubtitle')}
            value={metrics.totalProjects}
            icon={<FileTextOutlined />}
            color="#1890ff"
            loading={isLoading}
            refreshable
            onRefresh={refetch}
          />
        </Col>

        <Col {...colSpan}>
          <MetricCard
            title={t('overview.activeProjects')}
            subtitle={t('overview.activeProjectsSubtitle')}
            value={metrics.activeProjects}
            icon={<ClockCircleOutlined />}
            color="#52c41a"
            loading={isLoading}
            target={metrics.totalProjects}
            progress={metrics.activeProjects}
            refreshable
            onRefresh={refetch}
          />
        </Col>

        <Col {...colSpan}>
          <MetricCard
            title={t('overview.completedTasks')}
            subtitle={t('overview.completedTasksSubtitle')}
            value={`${metrics.completedProjects}/${metrics.totalProjects}`}
            icon={<CheckCircleOutlined />}
            color="#722ed1"
            loading={isLoading}
            target={metrics.totalProjects}
            progress={metrics.completedProjects}
            status={metrics.totalProjects > 0 && metrics.completedProjects / metrics.totalProjects >= 0.8 ? 'success' : 'normal'}
            refreshable
            onRefresh={refetch}
          />
        </Col>

        <Col {...colSpan}>
          <MetricCard
            title={t('overview.qualityScore')}
            subtitle={t('overview.qualityScoreSubtitle')}
            value={(metrics.qualityScore * 100).toFixed(1)}
            suffix="%"
            icon={<TrophyOutlined />}
            color="#13c2c2"
            loading={isLoading}
            target={90}
            progress={metrics.qualityScore * 100}
            status={metrics.qualityScore >= 0.85 ? 'success' : metrics.qualityScore >= 0.7 ? 'warning' : 'error'}
            refreshable
            onRefresh={refetch}
          />
        </Col>
      </Row>
    </div>
  );
};

export default OverviewCards;
