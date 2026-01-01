// Work hours report component with detailed statistics and export
import { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Row,
  Col,
  Space,
  Button,
  DatePicker,
  Statistic,
  Tag,
  Empty,
  message,
  Typography,
  Progress,
  Tooltip,
  Descriptions,
  Modal,
} from 'antd';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  ClockCircleOutlined,
  ReloadOutlined,
  TeamOutlined,
  RiseOutlined,
  FallOutlined,
  UserOutlined,
  FileExcelOutlined,
  BarChartOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import quarterOfYear from 'dayjs/plugin/quarterOfYear';
import type { Dayjs } from 'dayjs';
import { useWorkHoursStatistics, useExportBilling } from '@/hooks/useBilling';
import type { WorkHoursStatistics } from '@/types/billing';

dayjs.extend(quarterOfYear);

const { Text } = Typography;
const { RangePicker } = DatePicker;

interface WorkHoursReportProps {
  tenantId: string;
  onExport?: () => void;
}

interface UserDetailModalProps {
  visible: boolean;
  user: WorkHoursStatistics | null;
  onClose: () => void;
}

const UserDetailModal: React.FC<UserDetailModalProps> = ({ visible, user, onClose }) => {
  if (!user) return null;

  return (
    <Modal
      title={
        <Space>
          <UserOutlined />
          <span>{user.user_name || user.user_id} - 工时详情</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={600}
    >
      <Descriptions bordered column={2}>
        <Descriptions.Item label="用户ID">{user.user_id}</Descriptions.Item>
        <Descriptions.Item label="用户名称">{user.user_name || '-'}</Descriptions.Item>
        <Descriptions.Item label="总工时">
          <Text strong>{user.total_hours.toFixed(2)}</Text> 小时
        </Descriptions.Item>
        <Descriptions.Item label="计费工时">
          <Text strong>{user.billable_hours.toFixed(2)}</Text> 小时
        </Descriptions.Item>
        <Descriptions.Item label="计费率">
          <Progress
            percent={Number(((user.billable_hours / user.total_hours) * 100).toFixed(1)) || 0}
            size="small"
            status="active"
          />
        </Descriptions.Item>
        <Descriptions.Item label="效率评分">
          <Tag color={user.efficiency_score >= 80 ? 'green' : user.efficiency_score >= 60 ? 'orange' : 'red'}>
            {user.efficiency_score.toFixed(0)}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="标注数量" span={2}>
          <Text strong>{user.total_annotations.toLocaleString()}</Text> 条
        </Descriptions.Item>
        <Descriptions.Item label="时效">
          <Text strong>{user.annotations_per_hour.toFixed(2)}</Text> 条/小时
        </Descriptions.Item>
        <Descriptions.Item label="总成本">
          <Text strong type="success">¥{user.total_cost.toLocaleString()}</Text>
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  );
};

export function WorkHoursReport({ tenantId, onExport }: WorkHoursReportProps) {
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().startOf('month'),
    dayjs().endOf('month'),
  ]);
  const [selectedUser, setSelectedUser] = useState<WorkHoursStatistics | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  const startDate = dateRange[0].format('YYYY-MM-DD');
  const endDate = dateRange[1].format('YYYY-MM-DD');

  const { data, isLoading, error, refetch } = useWorkHoursStatistics(tenantId, startDate, endDate);
  const exportMutation = useExportBilling();

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (!data?.statistics || data.statistics.length === 0) {
      return {
        totalUsers: 0,
        totalHours: 0,
        totalBillableHours: 0,
        totalAnnotations: 0,
        totalCost: 0,
        avgEfficiency: 0,
        avgHoursPerUser: 0,
        avgAnnotationsPerHour: 0,
      };
    }

    const stats = data.statistics;
    const totalHours = stats.reduce((sum, s) => sum + s.total_hours, 0);
    const totalBillableHours = stats.reduce((sum, s) => sum + s.billable_hours, 0);
    const totalAnnotations = stats.reduce((sum, s) => sum + s.total_annotations, 0);
    const totalCost = stats.reduce((sum, s) => sum + s.total_cost, 0);
    const avgEfficiency = stats.reduce((sum, s) => sum + s.efficiency_score, 0) / stats.length;

    return {
      totalUsers: stats.length,
      totalHours,
      totalBillableHours,
      totalAnnotations,
      totalCost,
      avgEfficiency,
      avgHoursPerUser: totalHours / stats.length,
      avgAnnotationsPerHour: totalHours > 0 ? totalAnnotations / totalHours : 0,
    };
  }, [data]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!data?.statistics) return [];
    return data.statistics
      .sort((a, b) => b.total_hours - a.total_hours)
      .slice(0, 10)
      .map((s) => ({
        name: s.user_name || s.user_id.slice(0, 8),
        hours: Number(s.total_hours.toFixed(1)),
        billable: Number(s.billable_hours.toFixed(1)),
        annotations: s.total_annotations,
        efficiency: s.efficiency_score,
      }));
  }, [data]);

  // Efficiency distribution
  const efficiencyDistribution = useMemo(() => {
    if (!data?.statistics) return [];
    const ranges = [
      { range: '0-40', min: 0, max: 40, count: 0 },
      { range: '40-60', min: 40, max: 60, count: 0 },
      { range: '60-80', min: 60, max: 80, count: 0 },
      { range: '80-100', min: 80, max: 100, count: 0 },
    ];

    data.statistics.forEach((s) => {
      const score = s.efficiency_score;
      for (const range of ranges) {
        if (score >= range.min && score < range.max) {
          range.count++;
          break;
        }
      }
    });

    return ranges.map((r) => ({
      name: r.range,
      count: r.count,
      percentage: data.statistics.length > 0 ? ((r.count / data.statistics.length) * 100).toFixed(1) : 0,
    }));
  }, [data]);

  const handleExportExcel = async () => {
    try {
      await exportMutation.mutateAsync({
        tenantId,
        params: {
          start_date: startDate,
          end_date: endDate,
        },
      });
      message.success('工时报表导出成功');
      onExport?.();
    } catch {
      message.error('导出失败，请重试');
    }
  };

  const handleViewDetail = (record: WorkHoursStatistics) => {
    setSelectedUser(record);
    setDetailModalVisible(true);
  };

  const columns: ColumnsType<WorkHoursStatistics> = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_, __, index) => {
        const rankColors: Record<number, string> = { 0: '#FFD700', 1: '#C0C0C0', 2: '#CD7F32' };
        return (
          <Tag color={rankColors[index] || 'default'} style={{ fontWeight: 'bold' }}>
            {index + 1}
          </Tag>
        );
      },
    },
    {
      title: '用户',
      key: 'user',
      render: (_, record) => (
        <Space>
          <UserOutlined />
          <Text strong>{record.user_name || record.user_id}</Text>
        </Space>
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
          <Text>{hours.toFixed(1)}h</Text>
        </Space>
      ),
    },
    {
      title: '计费工时',
      dataIndex: 'billable_hours',
      key: 'billable_hours',
      sorter: (a, b) => a.billable_hours - b.billable_hours,
      render: (hours: number, record) => {
        const rate = record.total_hours > 0 ? (hours / record.total_hours) * 100 : 0;
        return (
          <Tooltip title={`计费率: ${rate.toFixed(1)}%`}>
            <Space>
              <Text>{hours.toFixed(1)}h</Text>
              <Progress
                percent={Number(rate.toFixed(0))}
                size="small"
                style={{ width: 60 }}
                showInfo={false}
              />
            </Space>
          </Tooltip>
        );
      },
    },
    {
      title: '标注数',
      dataIndex: 'total_annotations',
      key: 'total_annotations',
      sorter: (a, b) => a.total_annotations - b.total_annotations,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '时效',
      dataIndex: 'annotations_per_hour',
      key: 'annotations_per_hour',
      sorter: (a, b) => a.annotations_per_hour - b.annotations_per_hour,
      render: (rate: number) => (
        <Tooltip title="每小时标注数量">
          <Text>{rate.toFixed(1)} / h</Text>
        </Tooltip>
      ),
    },
    {
      title: '效率评分',
      dataIndex: 'efficiency_score',
      key: 'efficiency_score',
      sorter: (a, b) => a.efficiency_score - b.efficiency_score,
      render: (score: number) => {
        const color = score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red';
        const icon = score >= 80 ? <RiseOutlined /> : score < 60 ? <FallOutlined /> : null;
        return (
          <Tag color={color} icon={icon}>
            {score.toFixed(0)}
          </Tag>
        );
      },
    },
    {
      title: '成本',
      dataIndex: 'total_cost',
      key: 'total_cost',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => (
        <Text type="success" strong>
          ¥{cost.toLocaleString()}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewDetail(record)}>
          详情
        </Button>
      ),
    },
  ];

  if (error) {
    return (
      <Card>
        <Empty description="加载工时数据失败">
          <Button type="primary" onClick={() => refetch()}>
            重试
          </Button>
        </Empty>
      </Card>
    );
  }

  return (
    <div className="work-hours-report">
      {/* Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space size="large">
              <Space>
                <Text>统计周期:</Text>
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
            </Space>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isLoading}>
                刷新
              </Button>
              <Button
                type="primary"
                icon={<FileExcelOutlined />}
                onClick={handleExportExcel}
                loading={exportMutation.isPending}
              >
                导出 Excel
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Summary Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="统计人数"
              value={summaryStats.totalUsers}
              prefix={<TeamOutlined />}
              suffix="人"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="总工时"
              value={summaryStats.totalHours}
              prefix={<ClockCircleOutlined />}
              precision={1}
              suffix="h"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="计费工时"
              value={summaryStats.totalBillableHours}
              precision={1}
              suffix="h"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="总标注数"
              value={summaryStats.totalAnnotations}
              groupSeparator=","
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="平均效率"
              value={summaryStats.avgEfficiency}
              precision={1}
              valueStyle={{
                color: summaryStats.avgEfficiency >= 70 ? '#3f8600' : '#cf1322',
              }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="总成本"
              value={summaryStats.totalCost}
              prefix="¥"
              precision={2}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={16}>
          <Card
            title={
              <Space>
                <BarChartOutlined />
                <span>工时排名 (Top 10)</span>
              </Space>
            }
            loading={isLoading}
          >
            {chartData.length === 0 ? (
              <Empty description="暂无数据" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    formatter={(value, name) => {
                      const labels: Record<string, string> = {
                        hours: '总工时',
                        billable: '计费工时',
                      };
                      return [`${value as number}h`, labels[name as string] || name];
                    }}
                  />
                  <Legend />
                  <Bar dataKey="hours" name="总工时" fill="#1890ff" />
                  <Bar dataKey="billable" name="计费工时" fill="#52c41a" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col span={8}>
          <Card
            title={
              <Space>
                <InfoCircleOutlined />
                <span>效率分布</span>
              </Space>
            }
            loading={isLoading}
          >
            {efficiencyDistribution.length === 0 ? (
              <Empty description="暂无数据" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={efficiencyDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <RechartsTooltip
                    formatter={(value) => [`${value as number} 人`, '人数']}
                  />
                  <Bar
                    dataKey="count"
                    fill="#722ed1"
                    label={{ position: 'top', fontSize: 12 }}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      {/* Data Table */}
      <Card
        title={
          <Space>
            <ClockCircleOutlined />
            <span>工时统计明细</span>
            <Tag>{data?.user_count || 0} 人</Tag>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={data?.statistics || []}
          rowKey="user_id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* User Detail Modal */}
      <UserDetailModal
        visible={detailModalVisible}
        user={selectedUser}
        onClose={() => {
          setDetailModalVisible(false);
          setSelectedUser(null);
        }}
      />
    </div>
  );
}

export default WorkHoursReport;
