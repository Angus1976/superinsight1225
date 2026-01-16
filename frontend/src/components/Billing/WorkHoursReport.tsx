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
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation('billing');
  
  if (!user) return null;

  return (
    <Modal
      title={
        <Space>
          <UserOutlined />
          <span>{user.user_name || user.user_id} - {t('workHours.report.userDetail')}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          {t('workHours.report.actions.close')}
        </Button>,
      ]}
      width={600}
    >
      <Descriptions bordered column={2}>
        <Descriptions.Item label={t('workHours.report.modal.userId')}>{user.user_id}</Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.userName')}>{user.user_name || '-'}</Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.totalHours')}>
          <Text strong>{user.total_hours.toFixed(2)}</Text> {t('workHours.report.modal.hours')}
        </Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.billableHours')}>
          <Text strong>{user.billable_hours.toFixed(2)}</Text> {t('workHours.report.modal.hours')}
        </Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.billableRate')}>
          <Progress
            percent={Number(((user.billable_hours / user.total_hours) * 100).toFixed(1)) || 0}
            size="small"
            status="active"
          />
        </Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.efficiencyScore')}>
          <Tag color={user.efficiency_score >= 80 ? 'green' : user.efficiency_score >= 60 ? 'orange' : 'red'}>
            {user.efficiency_score.toFixed(0)}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.annotationCount')} span={2}>
          <Text strong>{user.total_annotations.toLocaleString()}</Text> {t('workHours.report.modal.items')}
        </Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.rate')}>
          <Text strong>{user.annotations_per_hour.toFixed(2)}</Text> {t('workHours.report.modal.perHour')}
        </Descriptions.Item>
        <Descriptions.Item label={t('workHours.report.modal.totalCost')}>
          <Text strong type="success">¥{user.total_cost.toLocaleString()}</Text>
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  );
};

export function WorkHoursReport({ tenantId, onExport }: WorkHoursReportProps) {
  const { t } = useTranslation('billing');
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
      message.success(t('workHours.report.messages.exportSuccess'));
      onExport?.();
    } catch {
      message.error(t('workHours.report.messages.exportFailed'));
    }
  };

  const handleViewDetail = (record: WorkHoursStatistics) => {
    setSelectedUser(record);
    setDetailModalVisible(true);
  };

  const columns: ColumnsType<WorkHoursStatistics> = [
    {
      title: t('workHours.report.columns.rank'),
      key: 'rank',
      width: 70,
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
      title: t('workHours.report.columns.user'),
      key: 'user',
      width: 140,
      render: (_, record) => (
        <Space>
          <UserOutlined />
          <Text strong>{record.user_name || record.user_id}</Text>
        </Space>
      ),
    },
    {
      title: t('workHours.report.columns.totalHours'),
      dataIndex: 'total_hours',
      key: 'total_hours',
      width: 100,
      sorter: (a, b) => a.total_hours - b.total_hours,
      render: (hours: number) => (
        <Space>
          <ClockCircleOutlined />
          <Text>{hours.toFixed(1)}h</Text>
        </Space>
      ),
    },
    {
      title: t('workHours.report.columns.billableHours'),
      dataIndex: 'billable_hours',
      key: 'billable_hours',
      width: 130,
      sorter: (a, b) => a.billable_hours - b.billable_hours,
      render: (hours: number, record) => {
        const rate = record.total_hours > 0 ? (hours / record.total_hours) * 100 : 0;
        return (
          <Tooltip title={`${rate.toFixed(1)}%`}>
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
      title: t('workHours.report.columns.annotations'),
      dataIndex: 'total_annotations',
      key: 'total_annotations',
      width: 90,
      sorter: (a, b) => a.total_annotations - b.total_annotations,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: t('workHours.report.columns.rate'),
      dataIndex: 'annotations_per_hour',
      key: 'annotations_per_hour',
      width: 80,
      sorter: (a, b) => a.annotations_per_hour - b.annotations_per_hour,
      render: (rate: number) => (
        <Text>{rate.toFixed(1)}/h</Text>
      ),
    },
    {
      title: t('workHours.report.columns.efficiencyScore'),
      dataIndex: 'efficiency_score',
      key: 'efficiency_score',
      width: 90,
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
      title: t('workHours.report.columns.cost'),
      dataIndex: 'total_cost',
      key: 'total_cost',
      width: 100,
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => (
        <Text type="success" strong>
          ¥{cost.toLocaleString()}
        </Text>
      ),
    },
    {
      title: t('workHours.report.columns.action'),
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewDetail(record)}>
          {t('workHours.report.actions.detail')}
        </Button>
      ),
    },
  ];

  if (error) {
    return (
      <Card>
        <Empty description={t('workHours.report.messages.loadFailed')}>
          <Button type="primary" onClick={() => refetch()}>
            {t('workHours.report.actions.retry')}
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
                <Text>{t('workHours.report.statisticPeriod')}:</Text>
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
            </Space>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isLoading}>
                {t('workHours.report.actions.refresh')}
              </Button>
              <Button
                type="primary"
                icon={<FileExcelOutlined />}
                onClick={handleExportExcel}
                loading={exportMutation.isPending}
              >
                {t('workHours.report.actions.exportExcel')}
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
              title={t('workHours.report.stats.totalUsers')}
              value={summaryStats.totalUsers}
              prefix={<TeamOutlined />}
              suffix={t('workHours.report.messages.persons')}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('workHours.report.stats.totalHours')}
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
              title={t('workHours.report.stats.billableHours')}
              value={summaryStats.totalBillableHours}
              precision={1}
              suffix="h"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('workHours.report.stats.totalAnnotations')}
              value={summaryStats.totalAnnotations}
              groupSeparator=","
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('workHours.report.stats.avgEfficiency')}
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
              title={t('workHours.report.stats.totalCost')}
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
                <span>{t('workHours.report.charts.hoursRanking')}</span>
              </Space>
            }
            loading={isLoading}
          >
            {chartData.length === 0 ? (
              <Empty description={t('workHours.report.messages.noData')} />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    formatter={(value, name) => {
                      const labels: Record<string, string> = {
                        hours: t('workHours.report.charts.totalHours'),
                        billable: t('workHours.report.charts.billableHours'),
                      };
                      return [`${value as number}h`, labels[name as string] || name];
                    }}
                  />
                  <Legend />
                  <Bar dataKey="hours" name={t('workHours.report.charts.totalHours')} fill="#1890ff" />
                  <Bar dataKey="billable" name={t('workHours.report.charts.billableHours')} fill="#52c41a" />
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
                <span>{t('workHours.report.charts.efficiencyDist')}</span>
              </Space>
            }
            loading={isLoading}
          >
            {efficiencyDistribution.length === 0 ? (
              <Empty description={t('workHours.report.messages.noData')} />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={efficiencyDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <RechartsTooltip
                    formatter={(value) => [`${value as number}`, t('workHours.report.messages.persons')]}
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
            <span>{t('workHours.report.title')}</span>
            <Tag>{data?.user_count || 0} {t('workHours.report.messages.persons')}</Tag>
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
            showTotal: (total) => t('workHours.report.messages.totalRecords', { total }),
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
