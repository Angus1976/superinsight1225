// Cost analysis chart component
import { useMemo } from 'react';
import { Card, Row, Col, Spin, Empty, Space, Tag, Tooltip } from 'antd';
import {
  AreaChart,
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
} from 'recharts';
import {
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useCostTrends, useProjectBreakdown, useDepartmentAllocation } from '@/hooks/useBilling';

interface CostAnalysisChartProps {
  tenantId: string;
  startDate: string;
  endDate: string;
  days?: number;
}

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'];

interface TrendsDataItem {
  date: string;
  cost: number;
  annotations?: number;
}

interface TrendSummary {
  total_cost?: number;
  average_daily_cost?: number;
  trend_percentage?: number;
  daily_costs?: TrendsDataItem[];
}

export const CostAnalysisChart: React.FC<CostAnalysisChartProps> = ({
  tenantId,
  startDate,
  endDate,
  days = 30,
}) => {
  const { data: trendsData, isLoading: trendsLoading } = useCostTrends(tenantId, days);
  const { data: projectData, isLoading: projectLoading } = useProjectBreakdown(tenantId, startDate, endDate);
  const { data: deptData, isLoading: deptLoading } = useDepartmentAllocation(tenantId, startDate, endDate);

  // Transform trends data for chart
  const trendChartData = useMemo(() => {
    const data = trendsData as TrendSummary | undefined;
    if (!data?.daily_costs) return [];
    return data.daily_costs.map((item: TrendsDataItem) => ({
      date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
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

  const isLoading = trendsLoading || projectLoading || deptLoading;
  const trendSummary = trendsData as TrendSummary | undefined;

  if (isLoading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>Loading cost analysis...</p>
        </div>
      </Card>
    );
  }

  return (
    <Row gutter={[16, 16]}>
      {/* Cost Trend Chart */}
      <Col span={24}>
        <Card
          title={
            <Space>
              <DollarOutlined />
              Cost Trends
              <Tooltip title="Daily cost breakdown over the selected period">
                <InfoCircleOutlined style={{ color: '#999' }} />
              </Tooltip>
            </Space>
          }
          extra={
            <Space>
              {trendSummary?.trend_percentage !== undefined && (
                <Tag
                  color={(trendSummary.trend_percentage || 0) > 0 ? 'red' : 'green'}
                  icon={(trendSummary.trend_percentage || 0) > 0 ? <RiseOutlined /> : <FallOutlined />}
                >
                  {(trendSummary.trend_percentage || 0) > 0 ? '+' : ''}
                  {(trendSummary.trend_percentage || 0).toFixed(1)}%
                </Tag>
              )}
              <span>Total: ${(trendSummary?.total_cost || 0).toLocaleString()}</span>
            </Space>
          }
        >
          {trendChartData.length === 0 ? (
            <Empty description="No trend data available" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={trendChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => `$${value}`} />
                <RechartsTooltip
                  formatter={(value, name) => {
                    const v = value as number;
                    return [
                      name === 'cost' ? `$${v.toFixed(2)}` : v,
                      name === 'cost' ? 'Cost' : 'Annotations',
                    ];
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="cost"
                  stroke="#1890ff"
                  fill="#1890ff"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>
      </Col>

      {/* Project Cost Breakdown */}
      <Col span={12}>
        <Card
          title={
            <Space>
              <DollarOutlined />
              Cost by Project
            </Space>
          }
        >
          {projectChartData.length === 0 ? (
            <Empty description="No project data available" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={projectChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, payload }) => `${name} (${(payload?.percentage || 0).toFixed(1)}%)`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {projectChartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <RechartsTooltip
                  formatter={(value) => [`$${(value as number).toLocaleString()}`, 'Cost']}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </Col>

      {/* Department Cost Allocation */}
      <Col span={12}>
        <Card
          title={
            <Space>
              <DollarOutlined />
              Cost by Department
            </Space>
          }
        >
          {deptChartData.length === 0 ? (
            <Empty description="No department data available" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={deptChartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(value) => `$${value}`} />
                <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
                <RechartsTooltip
                  formatter={(value, name) => {
                    const v = value as number;
                    return [
                      name === 'cost' ? `$${v.toLocaleString()}` : v,
                      name === 'cost' ? 'Cost' : 'Users',
                    ];
                  }}
                />
                <Bar dataKey="cost" fill="#52c41a" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </Col>
    </Row>
  );
};
