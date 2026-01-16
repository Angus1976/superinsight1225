// Billing reports visualization component with enhanced report generation
import { useState, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Space,
  Button,
  DatePicker,
  Select,
  Statistic,
  Tag,
  Empty,
  message,
  Typography,
  Tabs,
  Progress,
  Descriptions,
  Divider,
} from 'antd';
import {
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar,
  ComposedChart,
  Line,
} from 'recharts';
import {
  FileTextOutlined,
  DownloadOutlined,
  DollarOutlined,
  PieChartOutlined,
  BarChartOutlined,
  LineChartOutlined,
  TeamOutlined,
  ProjectOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import quarterOfYear from 'dayjs/plugin/quarterOfYear';
import type { Dayjs } from 'dayjs';
import { useTranslation } from 'react-i18next';

dayjs.extend(quarterOfYear);
import {
  useGenerateReport,
  useProjectBreakdown,
  useDepartmentAllocation,
  useCostTrends,
  useWorkHoursStatistics,
} from '@/hooks/useBilling';
import type {
  EnhancedBillingReport,
  ReportType,
  ProjectCostBreakdown,
  DepartmentCostAllocation,
  WorkHoursStatistics,
} from '@/types/billing';

const { Text } = Typography;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

interface BillingReportsProps {
  tenantId: string;
  currentUserId: string;
}

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'];

interface TrendDataItem {
  date: string;
  cost: number;
  annotations?: number;
}

interface TrendSummary {
  total_cost?: number;
  average_daily_cost?: number;
  trend_percentage?: number;
  daily_costs?: TrendDataItem[];
}

export function BillingReports({ tenantId }: BillingReportsProps) {
  const { t } = useTranslation(['billing', 'common']);
  
  const REPORT_TYPE_OPTIONS: { value: ReportType; label: string }[] = [
    { value: 'summary', label: t('reports.summary') },
    { value: 'detailed', label: t('reports.detailed') },
    { value: 'user_breakdown', label: t('reports.userBreakdown') },
    { value: 'project_breakdown', label: t('reports.projectBreakdown') },
    { value: 'department_breakdown', label: t('reports.departmentBreakdown') },
    { value: 'work_hours', label: t('reports.workHours') },
    { value: 'trend_analysis', label: t('reports.trendAnalysis') },
  ];
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().startOf('month'),
    dayjs().endOf('month'),
  ]);
  const [reportType, setReportType] = useState<ReportType>('summary');
  const [generatedReport, setGeneratedReport] = useState<EnhancedBillingReport | null>(null);

  const startDate = dateRange[0].format('YYYY-MM-DD');
  const endDate = dateRange[1].format('YYYY-MM-DD');
  const days = dateRange[1].diff(dateRange[0], 'day') + 1;

  const { data: projectData, isLoading: projectLoading } = useProjectBreakdown(
    tenantId,
    startDate,
    endDate
  );
  const { data: deptData, isLoading: deptLoading } = useDepartmentAllocation(
    tenantId,
    startDate,
    endDate
  );
  const { data: trendsData, isLoading: trendsLoading } = useCostTrends(tenantId, days);
  const { data: workHoursData, isLoading: workHoursLoading } = useWorkHoursStatistics(
    tenantId,
    startDate,
    endDate
  );

  const generateReportMutation = useGenerateReport();

  const handleGenerateReport = async () => {
    try {
      const result = await generateReportMutation.mutateAsync({
        tenant_id: tenantId,
        start_date: startDate,
        end_date: endDate,
        report_type: reportType,
      });
      setGeneratedReport(result);
      message.success(t('reports.generateSuccess'));
    } catch {
      message.error(t('reports.generateFailed'));
    }
  };

  const handleExportReport = () => {
    if (!generatedReport) {
      message.warning(t('reports.pleaseGenerateFirst'));
      return;
    }
    const dataStr = JSON.stringify(generatedReport, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `billing-report-${startDate}-${endDate}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success(t('reports.exportSuccess'));
  };

  // Transform trends data for chart
  const trendChartData = useMemo(() => {
    const data = trendsData as TrendSummary | undefined;
    if (!data?.daily_costs) return [];
    return data.daily_costs.map((item: TrendDataItem) => ({
      date: dayjs(item.date).format('MM/DD'),
      cost: item.cost,
      annotations: item.annotations || 0,
    }));
  }, [trendsData]);

  // Transform project data for pie chart
  const projectChartData = useMemo(() => {
    if (!projectData?.breakdowns) return [];
    return projectData.breakdowns.slice(0, 8).map((item) => ({
      name: item.project_name,
      value: item.total_cost,
      percentage: item.percentage_of_total,
    }));
  }, [projectData]);

  // Transform department data for bar chart
  const deptChartData = useMemo(() => {
    if (!deptData?.allocations) return [];
    return deptData.allocations.map((item) => ({
      name: item.department_name,
      cost: item.total_cost,
      users: item.user_count,
      percentage: item.percentage_of_total,
    }));
  }, [deptData]);

  const trendSummary = trendsData as TrendSummary | undefined;

  const projectColumns: ColumnsType<ProjectCostBreakdown> = [
    {
      title: t('reports.columns.projectName'),
      dataIndex: 'project_name',
      key: 'project_name',
      render: (name: string) => (
        <Space>
          <ProjectOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: t('reports.columns.totalCost'),
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
    {
      title: t('reports.columns.annotations'),
      dataIndex: 'total_annotations',
      key: 'total_annotations',
      sorter: (a, b) => a.total_annotations - b.total_annotations,
    },
    {
      title: t('reports.columns.timeSpent'),
      dataIndex: 'total_time_spent',
      key: 'total_time_spent',
      render: (time: number) => time.toFixed(1),
    },
    {
      title: t('reports.columns.avgCostPerAnnotation'),
      dataIndex: 'avg_cost_per_annotation',
      key: 'avg_cost_per_annotation',
      render: (cost: number) => <Text type="secondary">¥{cost.toFixed(2)}</Text>,
    },
    {
      title: t('reports.columns.percentage'),
      dataIndex: 'percentage_of_total',
      key: 'percentage_of_total',
      render: (pct: number) => (
        <Progress percent={pct} size="small" format={(p) => `${p?.toFixed(1)}%`} />
      ),
    },
  ];

  const departmentColumns: ColumnsType<DepartmentCostAllocation> = [
    {
      title: t('reports.columns.departmentName'),
      dataIndex: 'department_name',
      key: 'department_name',
      render: (name: string) => (
        <Space>
          <TeamOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: t('reports.columns.totalCost'),
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
    {
      title: t('reports.columns.userCount'),
      dataIndex: 'user_count',
      key: 'user_count',
    },
    {
      title: t('reports.columns.projects'),
      dataIndex: 'projects',
      key: 'projects',
      render: (projects: string[]) => (
        <Space wrap>
          {projects.slice(0, 3).map((p) => (
            <Tag key={p}>{p}</Tag>
          ))}
          {projects.length > 3 && <Tag>+{projects.length - 3}</Tag>}
        </Space>
      ),
    },
    {
      title: t('reports.columns.percentage'),
      dataIndex: 'percentage_of_total',
      key: 'percentage_of_total',
      render: (pct: number) => (
        <Progress percent={pct} size="small" format={(p) => `${p?.toFixed(1)}%`} />
      ),
    },
  ];

  const workHoursColumns: ColumnsType<WorkHoursStatistics> = [
    {
      title: t('reports.columns.user'),
      dataIndex: 'user_name',
      key: 'user_name',
      render: (name: string, record) => (
        <Text strong>{name || record.user_id}</Text>
      ),
    },
    {
      title: t('reports.columns.totalHours'),
      dataIndex: 'total_hours',
      key: 'total_hours',
      sorter: (a, b) => a.total_hours - b.total_hours,
      render: (hours: number) => (
        <Space>
          <ClockCircleOutlined />
          <span>{hours.toFixed(1)}h</span>
        </Space>
      ),
    },
    {
      title: t('reports.columns.billableHours'),
      dataIndex: 'billable_hours',
      key: 'billable_hours',
      render: (hours: number) => `${hours.toFixed(1)}h`,
    },
    {
      title: t('reports.columns.annotations'),
      dataIndex: 'total_annotations',
      key: 'total_annotations',
      sorter: (a, b) => a.total_annotations - b.total_annotations,
    },
    {
      title: t('reports.columns.rate'),
      dataIndex: 'annotations_per_hour',
      key: 'annotations_per_hour',
      render: (rate: number) => `${rate.toFixed(1)} / h`,
    },
    {
      title: t('reports.columns.cost'),
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
    {
      title: t('reports.columns.efficiencyScore'),
      dataIndex: 'efficiency_score',
      key: 'efficiency_score',
      render: (score: number) => (
        <Tag color={score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red'}>
          {score.toFixed(0)}
        </Tag>
      ),
    },
  ];

  // Combined loading state for potential future use
  void (projectLoading || deptLoading || trendsLoading || workHoursLoading);

  return (
    <div className="billing-reports">
      {/* Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space size="large">
              <Space>
                <Text>{t('reports.dateRange')}:</Text>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => {
                    if (dates && dates[0] && dates[1]) {
                      setDateRange([dates[0], dates[1]]);
                    }
                  }}
                  presets={[
                    { label: t('workHours.report.datePresets.thisWeek'), value: [dayjs().startOf('week'), dayjs().endOf('week')] },
                    { label: t('workHours.report.datePresets.thisMonth'), value: [dayjs().startOf('month'), dayjs().endOf('month')] },
                    { label: t('workHours.report.datePresets.lastMonth'), value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
                    { label: t('workHours.report.datePresets.thisQuarter'), value: [dayjs().startOf('quarter'), dayjs().endOf('quarter')] },
                  ]}
                />
              </Space>
              <Space>
                <Text>{t('reports.type')}:</Text>
                <Select
                  value={reportType}
                  onChange={setReportType}
                  options={REPORT_TYPE_OPTIONS}
                  style={{ width: 150 }}
                />
              </Space>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<FileTextOutlined />}
                onClick={handleGenerateReport}
                loading={generateReportMutation.isPending}
              >
                {t('reports.generate')}
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportReport}
                disabled={!generatedReport}
              >
                {t('reports.export')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Summary Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('reports.stats.totalCost')}
              value={trendSummary?.total_cost || 0}
              prefix={<DollarOutlined />}
              precision={2}
              suffix="¥"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('reports.stats.dailyAvgCost')}
              value={trendSummary?.average_daily_cost || 0}
              prefix={<LineChartOutlined />}
              precision={2}
              suffix="¥"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('reports.stats.projectCount')}
              value={projectData?.breakdowns?.length || 0}
              prefix={<ProjectOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('reports.stats.costTrend')}
              value={Math.abs(trendSummary?.trend_percentage || 0)}
              precision={1}
              prefix={(trendSummary?.trend_percentage || 0) >= 0 ? <RiseOutlined /> : <FallOutlined />}
              suffix="%"
              valueStyle={{
                color: (trendSummary?.trend_percentage || 0) >= 0 ? '#cf1322' : '#3f8600',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts and Tables */}
      <Tabs defaultActiveKey="trends">
        <TabPane
          tab={
            <span>
              <LineChartOutlined />
              {t('reports.tabs.trends')}
            </span>
          }
          key="trends"
        >
          <Card loading={trendsLoading}>
            {trendChartData.length === 0 ? (
              <Empty description={t('reports.noTrendData')} />
            ) : (
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `¥${value}`}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fontSize: 12 }}
                  />
                  <RechartsTooltip
                    formatter={(value, name) => {
                      const v = value as number;
                      return [
                        name === 'cost' ? `¥${v.toFixed(2)}` : v,
                        name === 'cost' ? t('reports.charts.cost') : t('reports.charts.annotations'),
                      ];
                    }}
                  />
                  <Legend />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="cost"
                    name={t('reports.charts.cost')}
                    stroke="#1890ff"
                    fill="#1890ff"
                    fillOpacity={0.3}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="annotations"
                    name={t('reports.charts.annotations')}
                    stroke="#52c41a"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <PieChartOutlined />
              {t('reports.tabs.projects')}
            </span>
          }
          key="projects"
        >
          <Row gutter={16}>
            <Col span={10}>
              <Card title={t('reports.charts.projectCostDist')} loading={projectLoading}>
                {projectChartData.length === 0 ? (
                  <Empty description={t('reports.noProjectData')} />
                ) : (
                  <ResponsiveContainer width="100%" height={350}>
                    <PieChart>
                      <Pie
                        data={projectChartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, payload }) => `${name} (${(payload?.percentage || 0).toFixed(1)}%)`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {projectChartData.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Legend />
                      <RechartsTooltip
                        formatter={(value) => [`¥${(value as number).toLocaleString()}`, t('reports.charts.cost')]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </Col>
            <Col span={14}>
              <Card title={t('reports.charts.projectCostDetail')} loading={projectLoading}>
                <Table
                  columns={projectColumns}
                  dataSource={projectData?.breakdowns || []}
                  rowKey="project_id"
                  size="small"
                  pagination={{ pageSize: 5 }}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={
            <span>
              <BarChartOutlined />
              {t('reports.tabs.departments')}
            </span>
          }
          key="departments"
        >
          <Row gutter={16}>
            <Col span={10}>
              <Card title={t('reports.charts.deptCostDist')} loading={deptLoading}>
                {deptChartData.length === 0 ? (
                  <Empty description={t('reports.noDeptData')} />
                ) : (
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={deptChartData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tickFormatter={(value) => `¥${value}`} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={100}
                        tick={{ fontSize: 12 }}
                      />
                      <RechartsTooltip
                        formatter={(value, name) => {
                          const v = value as number;
                          return [
                            name === 'cost' ? `¥${v.toLocaleString()}` : v,
                            name === 'cost' ? t('reports.charts.cost') : t('reports.columns.userCount'),
                          ];
                        }}
                      />
                      <Bar dataKey="cost" name={t('reports.charts.cost')} fill="#52c41a" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </Col>
            <Col span={14}>
              <Card title={t('reports.charts.deptCostDetail')} loading={deptLoading}>
                <Table
                  columns={departmentColumns}
                  dataSource={deptData?.allocations || []}
                  rowKey="department_id"
                  size="small"
                  pagination={{ pageSize: 5 }}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={
            <span>
              <TeamOutlined />
              {t('reports.tabs.workhours')}
            </span>
          }
          key="workhours"
        >
          <Card loading={workHoursLoading}>
            <Descriptions bordered size="small" column={4} style={{ marginBottom: 16 }}>
              <Descriptions.Item label={t('reports.stats.userCount')}>
                {workHoursData?.user_count || 0} {t('reports.persons')}
              </Descriptions.Item>
              <Descriptions.Item label={t('reports.stats.totalHours')}>
                {(workHoursData?.statistics?.reduce((sum, s) => sum + s.total_hours, 0) || 0).toFixed(1)} {t('reports.hours')}
              </Descriptions.Item>
              <Descriptions.Item label={t('reports.stats.totalAnnotations')}>
                {workHoursData?.statistics?.reduce((sum, s) => sum + s.total_annotations, 0) || 0}
              </Descriptions.Item>
              <Descriptions.Item label={t('reports.stats.totalCostLabel')}>
                ¥{(workHoursData?.statistics?.reduce((sum, s) => sum + s.total_cost, 0) || 0).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>
            <Table
              columns={workHoursColumns}
              dataSource={workHoursData?.statistics || []}
              rowKey="user_id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <FileTextOutlined />
              {t('reports.tabs.report')}
            </span>
          }
          key="report"
        >
          <Card>
            {generatedReport ? (
              <>
                <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                  <Descriptions.Item label={t('reports.reportId')}>{generatedReport.id}</Descriptions.Item>
                  <Descriptions.Item label={t('reports.reportType')}>
                    <Tag>{generatedReport.report_type}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label={t('reports.statisticPeriod')}>
                    {generatedReport.start_date} ~ {generatedReport.end_date}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('reports.generatedAt')}>
                    {dayjs(generatedReport.generated_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('reports.stats.totalCost')}>
                    <Text strong>¥{generatedReport.total_cost.toLocaleString()}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label={t('reports.totalAnnotations')}>
                    {generatedReport.total_annotations.toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('reports.totalTimeSpent')}>
                    {generatedReport.total_time_spent.toFixed(1)} {t('reports.hours')}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('reports.billingRuleVersion')}>
                    {generatedReport.billing_rule_version || '-'}
                  </Descriptions.Item>
                </Descriptions>

                <Divider>{t('reports.userBreakdownTitle')}</Divider>
                <Table
                  dataSource={Object.entries(generatedReport.user_breakdown || {}).map(
                    ([userId, data]) => ({
                      user_id: userId,
                      ...data,
                    })
                  )}
                  columns={[
                    { title: t('reports.userId'), dataIndex: 'user_id', key: 'user_id' },
                    { title: t('reports.columns.annotations'), dataIndex: 'annotations', key: 'annotations' },
                    {
                      title: t('reports.timeSpentHours'),
                      dataIndex: 'time_spent',
                      key: 'time_spent',
                      render: (v: number) => `${v.toFixed(1)}h`,
                    },
                    {
                      title: t('reports.columns.cost'),
                      dataIndex: 'cost',
                      key: 'cost',
                      render: (v: number) => `¥${v.toLocaleString()}`,
                    },
                  ]}
                  rowKey="user_id"
                  size="small"
                  pagination={{ pageSize: 5 }}
                />
              </>
            ) : (
              <Empty description={t('reports.pleaseGenerateReport')} />
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
}

export default BillingReports;
