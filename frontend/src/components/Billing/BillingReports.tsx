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

const REPORT_TYPE_OPTIONS: { value: ReportType; label: string }[] = [
  { value: 'summary', label: '概览报表' },
  { value: 'detailed', label: '详细报表' },
  { value: 'user_breakdown', label: '用户分析' },
  { value: 'project_breakdown', label: '项目分析' },
  { value: 'department_breakdown', label: '部门分析' },
  { value: 'work_hours', label: '工时报表' },
  { value: 'trend_analysis', label: '趋势分析' },
];

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
      message.success('报表生成成功');
    } catch {
      message.error('报表生成失败');
    }
  };

  const handleExportReport = () => {
    if (!generatedReport) {
      message.warning('请先生成报表');
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
    message.success('报表导出成功');
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
      title: '项目名称',
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
      title: '总成本',
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
    {
      title: '标注数量',
      dataIndex: 'total_annotations',
      key: 'total_annotations',
      sorter: (a, b) => a.total_annotations - b.total_annotations,
    },
    {
      title: '工时 (小时)',
      dataIndex: 'total_time_spent',
      key: 'total_time_spent',
      render: (time: number) => time.toFixed(1),
    },
    {
      title: '单条成本',
      dataIndex: 'avg_cost_per_annotation',
      key: 'avg_cost_per_annotation',
      render: (cost: number) => <Text type="secondary">¥{cost.toFixed(2)}</Text>,
    },
    {
      title: '占比',
      dataIndex: 'percentage_of_total',
      key: 'percentage_of_total',
      render: (pct: number) => (
        <Progress percent={pct} size="small" format={(p) => `${p?.toFixed(1)}%`} />
      ),
    },
  ];

  const departmentColumns: ColumnsType<DepartmentCostAllocation> = [
    {
      title: '部门名称',
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
      title: '总成本',
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
    {
      title: '人数',
      dataIndex: 'user_count',
      key: 'user_count',
    },
    {
      title: '关联项目',
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
      title: '占比',
      dataIndex: 'percentage_of_total',
      key: 'percentage_of_total',
      render: (pct: number) => (
        <Progress percent={pct} size="small" format={(p) => `${p?.toFixed(1)}%`} />
      ),
    },
  ];

  const workHoursColumns: ColumnsType<WorkHoursStatistics> = [
    {
      title: '用户',
      dataIndex: 'user_name',
      key: 'user_name',
      render: (name: string, record) => (
        <Text strong>{name || record.user_id}</Text>
      ),
    },
    {
      title: '总工时',
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
      title: '计费工时',
      dataIndex: 'billable_hours',
      key: 'billable_hours',
      render: (hours: number) => `${hours.toFixed(1)}h`,
    },
    {
      title: '标注数',
      dataIndex: 'total_annotations',
      key: 'total_annotations',
      sorter: (a, b) => a.total_annotations - b.total_annotations,
    },
    {
      title: '时效',
      dataIndex: 'annotations_per_hour',
      key: 'annotations_per_hour',
      render: (rate: number) => `${rate.toFixed(1)} / h`,
    },
    {
      title: '成本',
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => <Text>¥{cost.toLocaleString()}</Text>,
    },
    {
      title: '效率评分',
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
                <Text>日期范围:</Text>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => {
                    if (dates && dates[0] && dates[1]) {
                      setDateRange([dates[0], dates[1]]);
                    }
                  }}
                  presets={[
                    { label: '本周', value: [dayjs().startOf('week'), dayjs().endOf('week')] },
                    { label: '本月', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
                    { label: '上月', value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
                    { label: '本季度', value: [dayjs().startOf('quarter'), dayjs().endOf('quarter')] },
                  ]}
                />
              </Space>
              <Space>
                <Text>报表类型:</Text>
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
                生成报表
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportReport}
                disabled={!generatedReport}
              >
                导出报表
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
              title="总成本"
              value={trendSummary?.total_cost || 0}
              prefix={<DollarOutlined />}
              precision={2}
              suffix="元"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="日均成本"
              value={trendSummary?.average_daily_cost || 0}
              prefix={<LineChartOutlined />}
              precision={2}
              suffix="元"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="项目数量"
              value={projectData?.breakdowns?.length || 0}
              prefix={<ProjectOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成本趋势"
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
              成本趋势
            </span>
          }
          key="trends"
        >
          <Card loading={trendsLoading}>
            {trendChartData.length === 0 ? (
              <Empty description="暂无趋势数据" />
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
                        name === 'cost' ? '成本' : '标注数',
                      ];
                    }}
                  />
                  <Legend />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="cost"
                    name="成本"
                    stroke="#1890ff"
                    fill="#1890ff"
                    fillOpacity={0.3}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="annotations"
                    name="标注数"
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
              项目分析
            </span>
          }
          key="projects"
        >
          <Row gutter={16}>
            <Col span={10}>
              <Card title="项目成本分布" loading={projectLoading}>
                {projectChartData.length === 0 ? (
                  <Empty description="暂无项目数据" />
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
                        formatter={(value) => [`¥${(value as number).toLocaleString()}`, '成本']}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </Col>
            <Col span={14}>
              <Card title="项目成本明细" loading={projectLoading}>
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
              部门分析
            </span>
          }
          key="departments"
        >
          <Row gutter={16}>
            <Col span={10}>
              <Card title="部门成本分布" loading={deptLoading}>
                {deptChartData.length === 0 ? (
                  <Empty description="暂无部门数据" />
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
                            name === 'cost' ? '成本' : '人数',
                          ];
                        }}
                      />
                      <Bar dataKey="cost" name="成本" fill="#52c41a" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </Col>
            <Col span={14}>
              <Card title="部门成本明细" loading={deptLoading}>
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
              工时统计
            </span>
          }
          key="workhours"
        >
          <Card loading={workHoursLoading}>
            <Descriptions bordered size="small" column={4} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="统计人数">
                {workHoursData?.user_count || 0} 人
              </Descriptions.Item>
              <Descriptions.Item label="总工时">
                {(workHoursData?.statistics?.reduce((sum, s) => sum + s.total_hours, 0) || 0).toFixed(1)} 小时
              </Descriptions.Item>
              <Descriptions.Item label="总标注数">
                {workHoursData?.statistics?.reduce((sum, s) => sum + s.total_annotations, 0) || 0}
              </Descriptions.Item>
              <Descriptions.Item label="总成本">
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
              报表详情
            </span>
          }
          key="report"
        >
          <Card>
            {generatedReport ? (
              <>
                <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="报表ID">{generatedReport.id}</Descriptions.Item>
                  <Descriptions.Item label="报表类型">
                    <Tag>{generatedReport.report_type}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="统计周期">
                    {generatedReport.start_date} ~ {generatedReport.end_date}
                  </Descriptions.Item>
                  <Descriptions.Item label="生成时间">
                    {dayjs(generatedReport.generated_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label="总成本">
                    <Text strong>¥{generatedReport.total_cost.toLocaleString()}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="总标注数">
                    {generatedReport.total_annotations.toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="总工时">
                    {generatedReport.total_time_spent.toFixed(1)} 小时
                  </Descriptions.Item>
                  <Descriptions.Item label="计费规则版本">
                    {generatedReport.billing_rule_version || '-'}
                  </Descriptions.Item>
                </Descriptions>

                <Divider>用户明细</Divider>
                <Table
                  dataSource={Object.entries(generatedReport.user_breakdown || {}).map(
                    ([userId, data]) => ({
                      user_id: userId,
                      ...data,
                    })
                  )}
                  columns={[
                    { title: '用户ID', dataIndex: 'user_id', key: 'user_id' },
                    { title: '标注数', dataIndex: 'annotations', key: 'annotations' },
                    {
                      title: '工时',
                      dataIndex: 'time_spent',
                      key: 'time_spent',
                      render: (v: number) => `${v.toFixed(1)}h`,
                    },
                    {
                      title: '成本',
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
              <Empty description="请先生成报表查看详情" />
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
}

export default BillingReports;
