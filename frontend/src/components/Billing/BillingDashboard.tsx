/**
 * Billing Analytics Dashboard Component
 * 
 * Provides comprehensive billing analytics and visualization:
 * - Real-time billing metrics
 * - Cost trends and forecasting
 * - Work hours analysis
 * - Reward distribution overview
 * - Project and department breakdowns
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Select,
  DatePicker,
  Alert,
  Typography,
  Tooltip,
  Empty,
} from 'antd';
import {
  DollarOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  FallOutlined,
  TeamOutlined,
  ProjectOutlined,
  TrophyOutlined,
  BarChartOutlined,
  PieChartOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ProjectCostBreakdown, DepartmentCostAllocation, WorkHoursRanking } from '@/types/billing';
import {
  useBillingDashboard,
  useCostTrends,
  useUserProductivity,
  useCostForecast,
  useProjectBreakdown,
  useDepartmentAllocation,
} from '@/hooks/useBilling';
import { useAuthStore } from '@/stores/authStore';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// Types
interface MetricCardProps {
  title: string;
  value: number | string;
  prefix?: React.ReactNode;
  suffix?: string;
  trend?: number;
  trendLabel?: string;
  color?: string;
  loading?: boolean;
}

interface ChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

// Metric Card Component
const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  prefix,
  suffix,
  trend,
  trendLabel,
  color = '#1890ff',
  loading = false,
}) => {
  const trendIcon = trend && trend >= 0 ? <RiseOutlined /> : <FallOutlined />;
  const trendColor = trend && trend >= 0 ? '#cf1322' : '#3f8600';

  return (
    <Card hoverable loading={loading}>
      <Statistic
        title={title}
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={{ color }}
      />
      {trend !== undefined && (
        <div style={{ marginTop: 8 }}>
          <Text style={{ color: trendColor, fontSize: 12 }}>
            {trendIcon} {Math.abs(trend).toFixed(1)}%
          </Text>
          {trendLabel && (
            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
              {trendLabel}
            </Text>
          )}
        </div>
      )}
    </Card>
  );
};

// Simple Bar Chart Component (using CSS)
const SimpleBarChart: React.FC<{
  data: ChartDataPoint[];
  height?: number;
  color?: string;
}> = ({ data, height = 200, color = '#1890ff' }) => {
  const maxValue = Math.max(...data.map(d => d.value), 1);

  return (
    <div style={{ height, display: 'flex', alignItems: 'flex-end', gap: 4 }}>
      {data.map((item, index) => (
        <Tooltip key={index} title={`${item.label || item.date}: ¥${item.value.toLocaleString()}`}>
          <div
            style={{
              flex: 1,
              height: `${(item.value / maxValue) * 100}%`,
              backgroundColor: color,
              borderRadius: '4px 4px 0 0',
              minHeight: 4,
              transition: 'height 0.3s ease',
            }}
          />
        </Tooltip>
      ))}
    </div>
  );
};

// Progress Ring Component
const ProgressRing: React.FC<{
  percent: number;
  title: string;
  subtitle?: string;
  color?: string;
}> = ({ percent, title, subtitle, color = '#1890ff' }) => (
  <div style={{ textAlign: 'center' }}>
    <Progress
      type="circle"
      percent={percent}
      strokeColor={color}
      format={(p) => `${p}%`}
    />
    <div style={{ marginTop: 8 }}>
      <Text strong>{title}</Text>
      {subtitle && (
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>{subtitle}</Text>
        </div>
      )}
    </div>
  </div>
);

// Main Dashboard Component
export const BillingDashboard: React.FC = () => {
  const { t } = useTranslation('billing');
  const { currentTenant } = useAuthStore();
  const tenantId = currentTenant?.id || 'default';

  // State
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ]);
  const [trendDays, setTrendDays] = useState(30);

  // Format dates for API
  const startDate = dateRange[0].format('YYYY-MM-DD');
  const endDate = dateRange[1].format('YYYY-MM-DD');
  const forecastMonth = dayjs().add(1, 'month').format('YYYY-MM');

  // Data hooks
  const { analysis, ranking, isLoading, error, refetch } = useBillingDashboard(tenantId);
  const { data: costTrends, isLoading: trendsLoading } = useCostTrends(tenantId, trendDays);
  const { data: productivity, isLoading: productivityLoading } = useUserProductivity(tenantId, trendDays);
  const { data: forecast, isLoading: forecastLoading } = useCostForecast(tenantId, forecastMonth);
  const { data: projectBreakdown, isLoading: projectLoading } = useProjectBreakdown(tenantId, startDate, endDate);
  const { data: departmentAllocation, isLoading: deptLoading } = useDepartmentAllocation(tenantId, startDate, endDate);

  // Computed metrics
  const metrics = useMemo(() => {
    const totalSpending: number = analysis?.total_spending || 0;
    const avgMonthly: number = analysis?.average_monthly || 0;
    const trendPct: number = analysis?.trend_percentage || 0;
    const rankingData = ranking as WorkHoursRanking[] | undefined;
    const totalHours: number = rankingData?.reduce((sum: number, r) => sum + (r.total_hours || 0), 0) || 0;
    const activeUsers: number = rankingData?.length || 0;
    const avgProductivity: number = Number(productivity?.average_productivity) || 0;
    const forecastAmount: number = Number(forecast?.predicted_amount) || 0;
    const forecastConfidence: number = Number(forecast?.confidence) || 0;

    return {
      totalSpending,
      avgMonthly,
      trendPct,
      totalHours,
      activeUsers,
      avgProductivity,
      forecastAmount,
      forecastConfidence,
    };
  }, [analysis, ranking, productivity, forecast]);

  // Chart data
  const trendChartData: ChartDataPoint[] = useMemo(() => {
    const dailyCosts = costTrends?.daily_costs as Array<{ date: string; amount: number }> | undefined;
    if (!dailyCosts || !Array.isArray(dailyCosts)) return [];
    return dailyCosts.map((item) => ({
      date: item.date,
      value: item.amount,
      label: dayjs(item.date).format('MM/DD'),
    }));
  }, [costTrends]);

  // Top performers table columns
  const performerColumns = [
    {
      title: t('dashboard.columns.rank', 'Rank'),
      key: 'rank',
      width: 60,
      render: (_: unknown, __: unknown, index: number) => (
        <Tag color={index < 3 ? ['gold', 'silver', '#cd7f32'][index] : 'default'}>
          #{index + 1}
        </Tag>
      ),
    },
    {
      title: t('dashboard.columns.user', 'User'),
      dataIndex: 'user_name',
      key: 'user_name',
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: t('dashboard.columns.hours', 'Hours'),
      dataIndex: 'total_hours',
      key: 'total_hours',
      render: (hours: number) => `${(hours || 0).toFixed(1)}h`,
    },
    {
      title: t('dashboard.columns.productivity', 'Productivity'),
      dataIndex: 'efficiency_score',
      key: 'efficiency_score',
      render: (score: number) => (
        <Progress
          percent={Math.round((score || 0) * 100)}
          size="small"
          status={(score || 0) >= 0.8 ? 'success' : (score || 0) >= 0.6 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: t('dashboard.columns.annotations', 'Annotations'),
      dataIndex: 'annotations_count',
      key: 'annotations_count',
      render: (count: number) => (
        <Text style={{ color: '#52c41a' }}>{(count || 0).toLocaleString()}</Text>
      ),
    },
  ];

  // Project breakdown table columns
  const projectColumns = [
    {
      title: t('dashboard.columns.project', 'Project'),
      dataIndex: 'project_name',
      key: 'project_name',
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: t('dashboard.columns.cost', 'Cost'),
      dataIndex: 'total_cost',
      key: 'total_cost',
      render: (cost: number) => `¥${(cost || 0).toLocaleString()}`,
      sorter: (a: ProjectCostBreakdown, b: ProjectCostBreakdown) => (a.total_cost || 0) - (b.total_cost || 0),
    },
    {
      title: t('dashboard.columns.hours', 'Hours'),
      dataIndex: 'total_time_spent',
      key: 'total_time_spent',
      render: (hours: number) => `${((hours || 0) / 3600).toFixed(1)}h`,
    },
    {
      title: t('dashboard.columns.share', 'Share'),
      dataIndex: 'percentage_of_total',
      key: 'percentage_of_total',
      render: (pct: number) => (
        <Progress percent={Math.round(pct || 0)} size="small" />
      ),
    },
  ];

  if (error) {
    return (
      <Alert
        type="error"
        message={t('dashboard.loadFailed', 'Failed to load billing dashboard')}
        description={t('messages.checkConnection')}
        action={
          <Space>
            <a onClick={() => refetch()}>{t('messages.retry')}</a>
          </Space>
        }
      />
    );
  }

  return (
    <div className="billing-dashboard">
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            <BarChartOutlined /> {t('dashboard.title', 'Billing Analytics Dashboard')}
          </Title>
        </Col>
        <Col>
          <Space>
            <Select
              value={trendDays}
              onChange={setTrendDays}
              style={{ width: 120 }}
              options={[
                { value: 7, label: t('dashboard.last7Days', 'Last 7 days') },
                { value: 30, label: t('dashboard.last30Days', 'Last 30 days') },
                { value: 90, label: t('dashboard.last90Days', 'Last 90 days') },
              ]}
            />
            <RangePicker
              value={dateRange}
              onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
              presets={[
                { label: t('dashboard.thisMonth', 'This Month'), value: [dayjs().startOf('month'), dayjs()] },
                { label: t('dashboard.lastMonth', 'Last Month'), value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
                { label: t('dashboard.thisQuarter', 'This Quarter'), value: [dayjs().startOf('quarter'), dayjs()] },
              ]}
            />
          </Space>
        </Col>
      </Row>

      {/* Key Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('totalSpending')}
            value={metrics.totalSpending.toLocaleString()}
            prefix={<DollarOutlined />}
            suffix="¥"
            trend={metrics.trendPct}
            trendLabel={t('statistics.vsLastPeriod')}
            color="#1890ff"
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('dashboard.totalWorkHours', 'Total Work Hours')}
            value={metrics.totalHours.toFixed(1)}
            prefix={<ClockCircleOutlined />}
            suffix="h"
            color="#52c41a"
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('dashboard.activeUsers', 'Active Users')}
            value={metrics.activeUsers}
            prefix={<TeamOutlined />}
            color="#722ed1"
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title={t('dashboard.forecast', 'Forecast (Next Month)')}
            value={metrics.forecastAmount.toLocaleString()}
            prefix={<ThunderboltOutlined />}
            suffix="¥"
            color="#faad14"
            loading={forecastLoading}
          />
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {/* Cost Trend Chart */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                {t('dashboard.costTrends', 'Cost Trends')}
              </Space>
            }
            loading={trendsLoading}
          >
            {trendChartData.length > 0 ? (
              <>
                <SimpleBarChart data={trendChartData} height={200} color="#1890ff" />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                  <Text type="secondary">{trendChartData[0]?.label}</Text>
                  <Text type="secondary">{trendChartData[trendChartData.length - 1]?.label}</Text>
                </div>
              </>
            ) : (
              <Empty description={t('dashboard.noTrendData', 'No trend data available')} />
            )}
          </Card>
        </Col>

        {/* Efficiency Metrics */}
        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <PieChartOutlined />
                {t('dashboard.efficiencyMetrics', 'Efficiency Metrics')}
              </Space>
            }
            loading={productivityLoading}
          >
            <Row gutter={16}>
              <Col span={12}>
                <ProgressRing
                  percent={Math.round(metrics.avgProductivity * 100)}
                  title={t('dashboard.productivity', 'Productivity')}
                  subtitle={t('dashboard.teamAverage', 'Team Average')}
                  color="#52c41a"
                />
              </Col>
              <Col span={12}>
                <ProgressRing
                  percent={Math.round(metrics.forecastConfidence * 100)}
                  title={t('dashboard.forecastLabel', 'Forecast')}
                  subtitle={t('dashboard.confidence', 'Confidence')}
                  color="#1890ff"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Tables Row */}
      <Row gutter={[16, 16]}>
        {/* Top Performers */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <TrophyOutlined style={{ color: '#faad14' }} />
                {t('dashboard.topPerformers', 'Top Performers')}
              </Space>
            }
            loading={isLoading}
          >
            <Table
              dataSource={((ranking as WorkHoursRanking[] | undefined) || []).slice(0, 5)}
              columns={performerColumns}
              rowKey="user_id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>

        {/* Project Breakdown */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ProjectOutlined />
                {t('dashboard.projectBreakdown', 'Project Cost Breakdown')}
              </Space>
            }
            loading={projectLoading}
          >
            {projectBreakdown?.breakdowns && projectBreakdown.breakdowns.length > 0 ? (
              <Table
                dataSource={projectBreakdown.breakdowns.slice(0, 5)}
                columns={projectColumns}
                rowKey="project_id"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description={t('dashboard.noProjectData', 'No project data available')} />
            )}
          </Card>
        </Col>
      </Row>

      {/* Department Allocation */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={
              <Space>
                <TeamOutlined />
                {t('dashboard.departmentAllocation', 'Department Cost Allocation')}
              </Space>
            }
            loading={deptLoading}
          >
            {departmentAllocation?.allocations && departmentAllocation.allocations.length > 0 ? (
              <Row gutter={16}>
                {departmentAllocation.allocations.map((dept: DepartmentCostAllocation) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={dept.department_id}>
                    <Card size="small" hoverable>
                      <Statistic
                        title={dept.department_name}
                        value={dept.total_cost}
                        prefix="¥"
                        valueStyle={{ fontSize: 16 }}
                      />
                      <Progress
                        percent={Math.round(dept.percentage_of_total)}
                        size="small"
                        status="active"
                      />
                    </Card>
                  </Col>
                ))}
              </Row>
            ) : (
              <Empty description={t('dashboard.noDeptData', 'No department data available')} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default BillingDashboard;
