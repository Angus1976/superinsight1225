// Work Hours Statistics and Analysis Component
import { useState, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Space,
  Button,
  Select,
  DatePicker,
  Statistic,
  Progress,
  Tag,
  Tabs,
  Alert,
  Tooltip,
  Typography,
  Divider,
  Empty,
  Spin,
} from 'antd';
import {
  ClockCircleOutlined,
  TeamOutlined,
  TrophyOutlined,
  BarChartOutlined,
  LineChartOutlined,
  ExclamationCircleOutlined,
  UserOutlined,
  RiseOutlined,
  FallOutlined,
  ExportOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
  ComposedChart,
  Area,
} from 'recharts';
import type { ColumnsType } from 'antd/es/table';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import {
  useWorkHoursStatistics,
  useWorkHoursRanking,
  useCostTrends,
  useUserProductivity,
} from '@/hooks/useBilling';
import type { WorkHoursStatistics } from '@/types/billing';

const { RangePicker } = DatePicker;
const { TabPane } = Tabs;
const { Text, Title } = Typography;

interface WorkHoursAnalysisProps {
  tenantId: string;
}

interface ProductivityTrend {
  date: string;
  hours: number;
  annotations: number;
  efficiency: number;
}

interface DepartmentStats {
  department: string;
  totalHours: number;
  avgEfficiency: number;
  userCount: number;
  cost: number;
}

interface AnomalyDetection {
  userId: string;
  userName: string;
  anomalyType: 'excessive_hours' | 'low_efficiency' | 'irregular_pattern';
  severity: 'low' | 'medium' | 'high';
  description: string;
  recommendation: string;
}

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'];

const ANOMALY_COLORS = {
  low: '#52c41a',
  medium: '#faad14',
  high: '#f5222d',
};

export const WorkHoursAnalysis: React.FC<WorkHoursAnalysisProps> = ({ tenantId }) => {
  const { t } = useTranslation('billing');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ]);
  const [selectedPeriod, setSelectedPeriod] = useState<'week' | 'month' | 'quarter'>('month');
  const [viewType, setViewType] = useState<'individual' | 'team' | 'department'>('individual');

  const startDate = dateRange[0].format('YYYY-MM-DD');
  const endDate = dateRange[1].format('YYYY-MM-DD');
  const days = dateRange[1].diff(dateRange[0], 'day') + 1;

  // API hooks
  const { data: workHoursData, isLoading: workHoursLoading } = useWorkHoursStatistics(
    tenantId,
    startDate,
    endDate
  );
  const { data: rankingData, isLoading: rankingLoading } = useWorkHoursRanking(tenantId, selectedPeriod);
  const { data: trendsData, isLoading: trendsLoading } = useCostTrends(tenantId, days);
  const { data: productivityData, isLoading: productivityLoading } = useUserProductivity(tenantId, days);

  // Transform data for analysis
  const statistics = workHoursData?.statistics || [];
  const userCount = workHoursData?.user_count || 0;

  // Calculate summary metrics
  const summaryMetrics = useMemo(() => {
    if (statistics.length === 0) {
      return {
        totalHours: 0,
        totalBillableHours: 0,
        totalAnnotations: 0,
        avgEfficiency: 0,
        totalCost: 0,
        avgHourlyRate: 0,
        topPerformers: 0,
        lowPerformers: 0,
      };
    }

    const totalHours = statistics.reduce((sum, s) => sum + s.total_hours, 0);
    const totalBillableHours = statistics.reduce((sum, s) => sum + s.billable_hours, 0);
    const totalAnnotations = statistics.reduce((sum, s) => sum + s.total_annotations, 0);
    const avgEfficiency = statistics.reduce((sum, s) => sum + s.efficiency_score, 0) / statistics.length;
    const totalCost = statistics.reduce((sum, s) => sum + s.total_cost, 0);
    const avgHourlyRate = totalBillableHours > 0 ? totalCost / totalBillableHours : 0;
    const topPerformers = statistics.filter(s => s.efficiency_score >= 90).length;
    const lowPerformers = statistics.filter(s => s.efficiency_score < 60).length;

    return {
      totalHours,
      totalBillableHours,
      totalAnnotations,
      avgEfficiency,
      totalCost,
      avgHourlyRate,
      topPerformers,
      lowPerformers,
    };
  }, [statistics]);

  // Generate productivity trends (mock data for demo)
  const productivityTrends = useMemo((): ProductivityTrend[] => {
    const trends: ProductivityTrend[] = [];
    for (let i = 0; i < 30; i++) {
      const date = dayjs().subtract(29 - i, 'day');
      trends.push({
        date: date.format('MM/DD'),
        hours: Math.random() * 8 + 2,
        annotations: Math.floor(Math.random() * 100 + 50),
        efficiency: Math.random() * 30 + 70,
      });
    }
    return trends;
  }, []);

  // Generate department statistics (mock data for demo)
  const departmentStats = useMemo((): DepartmentStats[] => {
    return [
      { department: 'Engineering', totalHours: 320, avgEfficiency: 85, userCount: 8, cost: 25600 },
      { department: 'Quality Assurance', totalHours: 280, avgEfficiency: 92, userCount: 6, cost: 22400 },
      { department: 'Data Science', totalHours: 240, avgEfficiency: 78, userCount: 5, cost: 19200 },
      { department: 'Operations', totalHours: 180, avgEfficiency: 88, userCount: 4, cost: 14400 },
    ];
  }, []);

  // Detect anomalies (mock data for demo)
  const anomalies = useMemo((): AnomalyDetection[] => {
    return [
      {
        userId: 'user1',
        userName: 'John Doe',
        anomalyType: 'excessive_hours',
        severity: 'high',
        description: 'Working 12+ hours daily for the past week',
        recommendation: 'Consider workload redistribution to prevent burnout',
      },
      {
        userId: 'user2',
        userName: 'Jane Smith',
        anomalyType: 'low_efficiency',
        severity: 'medium',
        description: 'Efficiency dropped 25% compared to last month',
        recommendation: 'Provide additional training or support',
      },
      {
        userId: 'user3',
        userName: 'Bob Wilson',
        anomalyType: 'irregular_pattern',
        severity: 'low',
        description: 'Inconsistent work hours pattern detected',
        recommendation: 'Review work schedule and expectations',
      },
    ];
  }, []);

  // Table columns for individual statistics
  const individualColumns: ColumnsType<WorkHoursStatistics> = [
    {
      title: t('workHoursAnalysis.columns.user'),
      dataIndex: 'user_name',
      key: 'user_name',
      render: (name: string, record) => (
        <Space>
          <UserOutlined />
          <Text strong>{name || record.user_id}</Text>
        </Space>
      ),
    },
    {
      title: t('workHoursAnalysis.columns.totalHours'),
      dataIndex: 'total_hours',
      key: 'total_hours',
      sorter: (a, b) => a.total_hours - b.total_hours,
      render: (hours: number) => (
        <Space>
          <ClockCircleOutlined />
          <Text>{hours.toFixed(1)}h</Text>
        </Space>
      ),
    },
    {
      title: t('workHoursAnalysis.columns.billableHours'),
      dataIndex: 'billable_hours',
      key: 'billable_hours',
      render: (hours: number, record) => (
        <Space direction="vertical" size={0}>
          <Text>{hours.toFixed(1)}h</Text>
          <Progress
            percent={(hours / record.total_hours) * 100}
            size="small"
            showInfo={false}
          />
        </Space>
      ),
    },
    {
      title: t('workHoursAnalysis.columns.annotations'),
      dataIndex: 'total_annotations',
      key: 'total_annotations',
      sorter: (a, b) => a.total_annotations - b.total_annotations,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: t('workHoursAnalysis.columns.efficiency'),
      dataIndex: 'annotations_per_hour',
      key: 'annotations_per_hour',
      render: (rate: number) => `${rate.toFixed(1)}/h`,
    },
    {
      title: t('workHoursAnalysis.columns.qualityScore'),
      dataIndex: 'efficiency_score',
      key: 'efficiency_score',
      sorter: (a, b) => a.efficiency_score - b.efficiency_score,
      render: (score: number) => (
        <Progress
          percent={score}
          size="small"
          status={score >= 90 ? 'success' : score >= 70 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: t('workHoursAnalysis.columns.cost'),
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
  ];

  // Department columns
  const departmentColumns: ColumnsType<DepartmentStats> = [
    {
      title: t('workHoursAnalysis.columns.department'),
      dataIndex: 'department',
      key: 'department',
      render: (name: string) => (
        <Space>
          <TeamOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: t('workHoursAnalysis.columns.totalHours'),
      dataIndex: 'totalHours',
      key: 'totalHours',
      render: (hours: number) => `${hours}h`,
    },
    {
      title: t('workHoursAnalysis.columns.teamSize'),
      dataIndex: 'userCount',
      key: 'userCount',
      render: (count: number) => `${count} users`,
    },
    {
      title: t('workHoursAnalysis.columns.avgEfficiency'),
      dataIndex: 'avgEfficiency',
      key: 'avgEfficiency',
      render: (efficiency: number) => (
        <Progress
          percent={efficiency}
          size="small"
          status={efficiency >= 85 ? 'success' : 'normal'}
        />
      ),
    },
    {
      title: t('workHoursAnalysis.columns.totalCost'),
      dataIndex: 'cost',
      key: 'cost',
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
  ];

  const isLoading = workHoursLoading || rankingLoading || trendsLoading || productivityLoading;

  if (isLoading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>{t('workHoursAnalysis.loading')}</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="work-hours-analysis">
      {/* Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space size="large">
              <Space>
                <Text>{t('workHoursAnalysis.dateRange')}:</Text>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => {
                    if (dates && dates[0] && dates[1]) {
                      setDateRange([dates[0], dates[1]]);
                    }
                  }}
                  presets={[
                    { label: t('workHoursAnalysis.presets.last7Days'), value: [dayjs().subtract(7, 'day'), dayjs()] },
                    { label: t('workHoursAnalysis.presets.last30Days'), value: [dayjs().subtract(30, 'day'), dayjs()] },
                    { label: t('workHoursAnalysis.presets.last3Months'), value: [dayjs().subtract(3, 'month'), dayjs()] },
                  ]}
                />
              </Space>
              <Space>
                <Text>{t('workHoursAnalysis.view')}:</Text>
                <Select
                  value={viewType}
                  onChange={setViewType}
                  options={[
                    { value: 'individual', label: t('workHoursAnalysis.individual') },
                    { value: 'team', label: t('workHoursAnalysis.team') },
                    { value: 'department', label: t('workHoursAnalysis.department') },
                  ]}
                  style={{ width: 120 }}
                />
              </Space>
            </Space>
          </Col>
          <Col>
            <Button icon={<ExportOutlined />}>
              {t('workHoursAnalysis.exportAnalysis')}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Summary Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('workHoursAnalysis.totalHours')}
              value={summaryMetrics.totalHours.toFixed(1)}
              prefix={<ClockCircleOutlined />}
              suffix="h"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('workHoursAnalysis.billableHours')}
              value={summaryMetrics.totalBillableHours.toFixed(1)}
              prefix={<CalendarOutlined />}
              suffix="h"
            />
            <div style={{ marginTop: 8 }}>
              <Progress
                percent={(summaryMetrics.totalBillableHours / summaryMetrics.totalHours) * 100}
                size="small"
                showInfo={false}
              />
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('workHoursAnalysis.avgEfficiency')}
              value={summaryMetrics.avgEfficiency.toFixed(1)}
              prefix={<BarChartOutlined />}
              suffix="%"
              valueStyle={{
                color: summaryMetrics.avgEfficiency >= 80 ? '#3f8600' : '#faad14',
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('workHoursAnalysis.totalCost')}
              value={summaryMetrics.totalCost}
              prefix={<RiseOutlined />}
              precision={0}
            />
          </Card>
        </Col>
      </Row>

      {/* Performance Indicators */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title={t('workHoursAnalysis.topPerformers')}
              value={summaryMetrics.topPerformers}
              suffix={`/ ${userCount}`}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title={t('workHoursAnalysis.needsAttention')}
              value={summaryMetrics.lowPerformers}
              suffix={`/ ${userCount}`}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title={t('workHoursAnalysis.avgHourlyRate')}
              value={summaryMetrics.avgHourlyRate.toFixed(0)}
              prefix="¥"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Anomaly Detection Alert */}
      {anomalies.length > 0 && (
        <Alert
          message={t('workHoursAnalysis.anomaliesDetected')}
          description={t('workHoursAnalysis.anomaliesDescription', { count: anomalies.length })}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" type="link">
              {t('workHoursAnalysis.viewDetails')}
            </Button>
          }
        />
      )}

      {/* Main Analysis Tabs */}
      <Tabs defaultActiveKey="trends">
        <TabPane
          tab={
            <span>
              <LineChartOutlined />
              {t('workHoursAnalysis.productivityTrends')}
            </span>
          }
          key="trends"
        >
          <Card>
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart data={productivityTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <RechartsTooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="hours" name={t('workHoursAnalysis.charts.hours')} fill="#1890ff" />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="efficiency"
                  name={t('workHoursAnalysis.charts.efficiency')}
                  stroke="#52c41a"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <TeamOutlined />
              {viewType === 'individual' ? t('workHoursAnalysis.individual') : viewType === 'team' ? t('workHoursAnalysis.team') : t('workHoursAnalysis.department')} {t('workHoursAnalysis.analysis')}
            </span>
          }
          key="analysis"
        >
          <Card>
            {viewType === 'individual' && (
              <Table
                columns={individualColumns}
                dataSource={statistics}
                rowKey="user_id"
                pagination={{ pageSize: 10 }}
              />
            )}
            {viewType === 'department' && (
              <Table
                columns={departmentColumns}
                dataSource={departmentStats}
                rowKey="department"
                pagination={false}
              />
            )}
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <ExclamationCircleOutlined />
              {t('workHoursAnalysis.anomalyDetection')}
            </span>
          }
          key="anomalies"
        >
          <Card>
            {anomalies.length === 0 ? (
              <Empty description={t('workHoursAnalysis.noAnomalies')} />
            ) : (
              <Space direction="vertical" style={{ width: '100%' }}>
                {anomalies.map((anomaly, index) => (
                  <Card
                    key={index}
                    size="small"
                    style={{
                      borderLeft: `4px solid ${ANOMALY_COLORS[anomaly.severity]}`,
                    }}
                  >
                    <Row>
                      <Col span={18}>
                        <Space direction="vertical" size={0}>
                          <Space>
                            <Text strong>{anomaly.userName}</Text>
                            <Tag color={ANOMALY_COLORS[anomaly.severity]}>
                              {anomaly.severity.toUpperCase()}
                            </Tag>
                            <Tag>{anomaly.anomalyType.replace('_', ' ')}</Tag>
                          </Space>
                          <Text>{anomaly.description}</Text>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            Recommendation: {anomaly.recommendation}
                          </Text>
                        </Space>
                      </Col>
                      <Col span={6} style={{ textAlign: 'right' }}>
                        <Button size="small" type="link">
                          {t('workHoursAnalysis.viewDetails')}
                        </Button>
                      </Col>
                    </Row>
                  </Card>
                ))}
              </Space>
            )}
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <BarChartOutlined />
              {t('workHoursAnalysis.costAnalysis')}
            </span>
          }
          key="cost"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Card title={t('workHoursAnalysis.costByDepartment')}>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={departmentStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ department, cost }) => `${department}: ¥${cost.toLocaleString()}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="cost"
                    >
                      {departmentStats.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col span={12}>
              <Card title={t('workHoursAnalysis.efficiencyVsCost')}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={departmentStats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="department" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <RechartsTooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="cost" name={t('workHoursAnalysis.charts.cost')} fill="#1890ff" />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="avgEfficiency"
                      name={t('workHoursAnalysis.charts.efficiency')}
                      stroke="#52c41a"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default WorkHoursAnalysis;