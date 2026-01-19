// Enhanced Dashboard page with enterprise features
import { Row, Col, Typography, Alert, Tabs, Spin } from 'antd';
import {
  DashboardOutlined,
  BarChartOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { 
  RealTimeMetrics, 
  TrendChart, 
  QuickActions, 
  QualityReports, 
  KnowledgeGraph 
} from '@/components/Dashboard';
import { useDashboard } from '@/hooks/useDashboard';
import { useAuthStore } from '@/stores/authStore';

const { Title } = Typography;
const { TabPane } = Tabs;

const DashboardPage: React.FC = () => {
  const { t } = useTranslation('dashboard');
  const { user } = useAuthStore();
  const { annotationEfficiency, isLoading, error, queriesEnabled } = useDashboard();

  // Prepare chart data from annotation efficiency
  const chartData = annotationEfficiency?.trends?.map((trend) => ({
    timestamp: trend.timestamp,
    datetime: trend.datetime,
    value: trend.annotations_per_hour,
  })) || [];

  // Show loading state if queries are not enabled yet (tenant/workspace loading)
  if (!queriesEnabled) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 20px' }}>
        <Spin size="large" tip={t('loading.workspace')} />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="warning"
        message={t('errors.dataLoadFailed')}
        description={t('errors.backendConnection')}
        showIcon
      />
    );
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        {t('welcome', { name: user?.username || 'User' })}
      </Title>

      <Tabs defaultActiveKey="overview" size="large">
        <TabPane
          tab={
            <span>
              <DashboardOutlined />
              {t('tabs.overview')}
            </span>
          }
          key="overview"
        >
          {/* Real-time Metrics */}
          <RealTimeMetrics 
            refreshInterval={30000}
            showTargets={true}
          />

          {/* Charts */}
          <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
            <Col xs={24} lg={16}>
              <TrendChart
                title={t('charts.annotationTrend')}
                data={chartData.length > 0 ? chartData : generateMockChartData()}
                loading={isLoading}
                color="#1890ff"
                height={300}
              />
            </Col>
            <Col xs={24} lg={8}>
              <QuickActions />
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={
            <span>
              <BarChartOutlined />
              {t('tabs.qualityReports')}
            </span>
          }
          key="quality"
        >
          <QualityReports loading={isLoading} />
        </TabPane>

        <TabPane
          tab={
            <span>
              <NodeIndexOutlined />
              {t('tabs.knowledgeGraph')}
            </span>
          }
          key="knowledge"
        >
          <KnowledgeGraph 
            loading={isLoading}
            height={700}
            interactive={true}
          />
        </TabPane>
      </Tabs>
    </div>
  );
};

// Generate mock chart data for demo
function generateMockChartData() {
  const now = Date.now();
  return Array.from({ length: 24 }, (_, i) => ({
    timestamp: now - (23 - i) * 3600000,
    datetime: new Date(now - (23 - i) * 3600000).toISOString(),
    value: Math.floor(Math.random() * 50) + 20,
  }));
}

export default DashboardPage;
