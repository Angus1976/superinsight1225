// Enhanced Dashboard page with enterprise features
import { useState, useMemo } from 'react';
import { Row, Col, Typography, Alert, Tabs, Spin, Card, Table, Tag, Space } from 'antd';
import {
  DashboardOutlined,
  BarChartOutlined,
  NodeIndexOutlined,
  CalendarOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  RealTimeMetrics,
  TrendChart,
  QuickActions,
  QualityReports,
  KnowledgeGraph,
} from '@/components/Dashboard';
import type { DashboardMetricKey } from '@/components/Dashboard/RealTimeMetrics';
import { HelpIcon } from '@/components/SmartHelp';
import { useDashboard } from '@/hooks/useDashboard';
import { useTasks } from '@/hooks/useTask';
import { useAuthStore } from '@/stores/authStore';
import type { Task, TaskStatus } from '@/types';

const { Title } = Typography;

// Map metric keys to task status filters
const metricToStatusFilter: Partial<Record<DashboardMetricKey, TaskStatus | 'all'>> = {
  activeTasks: 'in_progress',
  todayAnnotations: 'completed',
  totalCorpus: 'all',
  completionRate: 'completed',
};

const statusColorMap: Record<TaskStatus, string> = {
  pending: 'default', in_progress: 'processing', completed: 'success', cancelled: 'error',
};
const statusIconMap: Record<TaskStatus, React.ReactNode> = {
  pending: <CalendarOutlined />, in_progress: <PlayCircleOutlined />,
  completed: <CheckCircleOutlined />, cancelled: <CloseCircleOutlined />,
};

const DashboardPage: React.FC = () => {
  const { t } = useTranslation(['dashboard', 'tasks']);
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { annotationEfficiency, userActivity, isLoading, error, queriesEnabled } = useDashboard();
  const [selectedMetric, setSelectedMetric] = useState<DashboardMetricKey | null>(null);

  // Build query params based on selected metric
  const detailQueryParams = useMemo(() => {
    if (!selectedMetric) return null;
    const statusFilter = metricToStatusFilter[selectedMetric];
    if (!statusFilter) return null;
    const params: Record<string, unknown> = { page_size: 10 };
    if (statusFilter !== 'all') params.status = statusFilter;
    return params;
  }, [selectedMetric]);

  // Fetch detail data only when a metric card is clicked
  const { data: detailData, isLoading: detailLoading } = useTasks(
    detailQueryParams ?? {},
  );

  const handleMetricClick = (key: DashboardMetricKey) => {
    // Toggle: click same card again to close detail
    if (selectedMetric === key) {
      setSelectedMetric(null);
      return;
    }
    // Only open detail for metrics that have task data
    if (metricToStatusFilter[key]) {
      setSelectedMetric(key);
    }
  };

  // Chart data from annotation efficiency
  const chartData = annotationEfficiency?.trends?.map((trend) => ({
    timestamp: trend.timestamp,
    datetime: trend.datetime,
    value: trend.annotations_per_hour,
  })) || [];

  if (!queriesEnabled) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 20px' }}>
        <Spin size="large" tip={t('loading.workspace')} />
      </div>
    );
  }

  if (error) {
    return (
      <Alert type="warning" message={t('errors.dataLoadFailed')}
        description={t('errors.backendConnection')} showIcon />
    );
  }

  // Detail table columns
  const detailColumns = [
    {
      title: t('tasks:columns.name'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string, record: Task) => (
        <a onClick={() => navigate(`/tasks/${record.id}`)} style={{ fontWeight: 500 }}>{text}</a>
      ),
    },
    {
      title: t('tasks:columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: TaskStatus) => (
        <Tag color={statusColorMap[status]} icon={statusIconMap[status]}>
          {t(`tasks:status.${status === 'in_progress' ? 'inProgress' : status}`)}
        </Tag>
      ),
    },
    {
      title: t('tasks:columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => {
        const colorMap: Record<string, string> = { low: 'green', medium: 'blue', high: 'orange', urgent: 'red' };
        return <Tag color={colorMap[priority] || 'default'}>{t(`tasks:priority.${priority}`)}</Tag>;
      },
    },
    {
      title: t('tasks:columns.progress'),
      dataIndex: 'progress',
      key: 'progress',
      width: 100,
      render: (val: number) => `${Math.round(val || 0)}%`,
    },
    {
      title: t('tasks:dueDate'),
      dataIndex: 'due_date',
      key: 'due_date',
      width: 120,
      render: (val: string) => val ? new Date(val).toLocaleDateString() : '-',
    },
  ];

  // Title for the detail card based on selected metric
  const detailTitleMap: Partial<Record<DashboardMetricKey, string>> = {
    activeTasks: t('metrics.activeTasks'),
    todayAnnotations: t('metrics.todayAnnotations'),
    totalCorpus: t('metrics.totalCorpus'),
    completionRate: t('metrics.completionRate'),
  };

  const tabItems = [
    {
      key: 'overview',
      label: (
        <span><DashboardOutlined /> {t('tabs.overview')}</span>
      ),
      children: (
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <TrendChart title={t('charts.annotationTrend')} data={chartData} loading={isLoading} />
          </Col>
          <Col span={24}>
            <QuickActions />
          </Col>
        </Row>
      ),
    },
    {
      key: 'quality',
      label: (
        <span><BarChartOutlined /> {t('tabs.qualityReports')}</span>
      ),
      children: <QualityReports annotationEfficiency={annotationEfficiency} userActivity={userActivity} loading={isLoading} />,
    },
    {
      key: 'knowledgeGraph',
      label: (
        <span><NodeIndexOutlined /> {t('tabs.knowledgeGraph')}</span>
      ),
      children: <KnowledgeGraph />,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>
            {t('welcome', { name: user?.username || '' })}
            <HelpIcon helpKey="dashboard.overview" className="ml-2" />
          </Title>
        </div>

        <RealTimeMetrics
          selectedMetric={selectedMetric}
          onMetricClick={handleMetricClick}
        />

        {selectedMetric && detailQueryParams && (
          <Card
            title={`${t('detailTable.title')} - ${detailTitleMap[selectedMetric] || ''}`}
            extra={
              <CloseOutlined
                style={{ cursor: 'pointer' }}
                onClick={() => setSelectedMetric(null)}
              />
            }
          >
            <Table
              columns={detailColumns}
              dataSource={detailData?.items || []}
              rowKey="id"
              loading={detailLoading}
              pagination={{
                pageSize: 10,
                total: detailData?.total || 0,
                showTotal: (total) => t('detailTable.total', { total }),
              }}
              size="middle"
            />
          </Card>
        )}

        <Tabs defaultActiveKey="overview" items={tabItems} />
      </Space>
    </div>
  );
};

export default DashboardPage;
