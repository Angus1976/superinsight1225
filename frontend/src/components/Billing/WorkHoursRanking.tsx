// Work hours ranking component with real API integration
import { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Avatar,
  Tag,
  Space,
  Select,
  Button,
  Tooltip,
  Progress,
  Modal,
  Form,
  InputNumber,
  Input,
  message,
  Spin,
  Empty,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  TrophyOutlined,
  UserOutlined,
  RiseOutlined,
  FallOutlined,
  GiftOutlined,
  ExportOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useWorkHoursRanking, useExportBilling, useCostTrends } from '@/hooks/useBilling';

interface RankingUser {
  rank: number;
  user_id: string;
  user_name: string;
  avatar?: string;
  total_hours: number;
  annotations_count: number;
  efficiency_score: number;
  quality_score: number;
  trend: 'up' | 'down' | 'stable';
  trend_value: number;
  bonus_eligible: boolean;
  hourly_rate?: number;
  total_earnings?: number;
}

interface WorkHoursRankingProps {
  tenantId: string;
  onExport?: () => void;
  onReward?: (userId: string, userName: string, amount: number, reason: string) => Promise<void>;
}

interface RewardFormValues {
  amount: number;
  reason: string;
}

const periodDays: Record<string, number> = {
  week: 7,
  month: 30,
  quarter: 90,
};

const getRankIcon = (rank: number) => {
  const colors: Record<number, string> = {
    1: '#FFD700',
    2: '#C0C0C0',
    3: '#CD7F32',
  };
  if (rank <= 3) {
    return (
      <TrophyOutlined
        style={{ color: colors[rank], fontSize: 18, marginRight: 8 }}
      />
    );
  }
  return <span style={{ marginRight: 8, fontWeight: 600 }}>{rank}</span>;
};

const getTrendIcon = (trend: 'up' | 'down' | 'stable', value: number) => {
  if (trend === 'up') {
    return (
      <Tag color="success" icon={<RiseOutlined />}>
        +{value}%
      </Tag>
    );
  }
  if (trend === 'down') {
    return (
      <Tag color="error" icon={<FallOutlined />}>
        {value}%
      </Tag>
    );
  }
  return <Tag color="default">-</Tag>;
};

// Transform API data to component format
const transformRankingData = (apiData: unknown[]): RankingUser[] => {
  if (!apiData || !Array.isArray(apiData)) return [];

  return apiData.map((item: Record<string, unknown>, index) => {
    const prevRank = (item.previous_rank as number) || index + 1;
    const currentRank = (item.rank as number) || index + 1;
    const rankChange = prevRank - currentRank;

    return {
      rank: currentRank,
      user_id: (item.user_id as string) || '',
      user_name: (item.user_name as string) || 'Unknown',
      avatar: item.avatar as string | undefined,
      total_hours: (item.total_hours as number) || 0,
      annotations_count: (item.annotations_count as number) || 0,
      efficiency_score: (item.efficiency_score as number) || 0,
      quality_score: (item.quality_score as number) || (item.efficiency_score as number) || 0,
      trend: rankChange > 0 ? 'up' : rankChange < 0 ? 'down' : 'stable',
      trend_value: Math.abs(rankChange) * 10,
      bonus_eligible: (item.efficiency_score as number) >= 85 && currentRank <= 5,
      hourly_rate: item.hourly_rate as number | undefined,
      total_earnings: item.total_earnings as number | undefined,
    };
  });
};

export const WorkHoursRanking: React.FC<WorkHoursRankingProps> = ({
  tenantId,
  onExport,
  onReward,
}) => {
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter'>('month');
  const [rewardModalVisible, setRewardModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<RankingUser | null>(null);
  const [rewardLoading, setRewardLoading] = useState(false);
  const [form] = Form.useForm<RewardFormValues>();

  // API hooks
  const { data: apiRankingData, isLoading, error, refetch } = useWorkHoursRanking(tenantId, period);
  const { data: trendsData } = useCostTrends(tenantId, periodDays[period]);
  const exportMutation = useExportBilling();

  // Transform data
  const rankingData = useMemo(() => {
    return transformRankingData(apiRankingData || []);
  }, [apiRankingData]);

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (rankingData.length === 0) {
      return {
        totalHours: 0,
        totalAnnotations: 0,
        avgEfficiency: 0,
        topPerformers: 0,
      };
    }
    const totalHours = rankingData.reduce((sum, u) => sum + u.total_hours, 0);
    const totalAnnotations = rankingData.reduce((sum, u) => sum + u.annotations_count, 0);
    const avgEfficiency = rankingData.reduce((sum, u) => sum + u.efficiency_score, 0) / rankingData.length;
    const topPerformers = rankingData.filter((u) => u.efficiency_score >= 90).length;

    return { totalHours, totalAnnotations, avgEfficiency, topPerformers };
  }, [rankingData]);

  // Handle reward click
  const handleRewardClick = (user: RankingUser) => {
    setSelectedUser(user);
    form.setFieldsValue({ amount: 100, reason: 'Excellent performance' });
    setRewardModalVisible(true);
  };

  // Handle reward submission
  const handleRewardSubmit = async () => {
    if (!selectedUser || !onReward) return;

    try {
      const values = await form.validateFields();
      setRewardLoading(true);
      await onReward(selectedUser.user_id, selectedUser.user_name, values.amount, values.reason);
      message.success(`Reward of $${values.amount} sent to ${selectedUser.user_name}`);
      setRewardModalVisible(false);
      form.resetFields();
    } catch {
      message.error('Failed to send reward');
    } finally {
      setRewardLoading(false);
    }
  };

  // Handle export
  const handleExport = () => {
    if (onExport) {
      onExport();
    } else {
      exportMutation.mutate({ tenantId });
    }
  };

  const columns: ColumnsType<RankingUser> = [
    {
      title: 'Rank',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {getRankIcon(rank)}
        </div>
      ),
    },
    {
      title: 'User',
      dataIndex: 'user_name',
      key: 'user_name',
      render: (name, record) => (
        <Space>
          <Avatar src={record.avatar} icon={<UserOutlined />} size="small" />
          <span style={{ fontWeight: record.rank <= 3 ? 600 : 400 }}>{name}</span>
          {record.bonus_eligible && (
            <Tooltip title="Eligible for bonus">
              <GiftOutlined style={{ color: '#faad14' }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Hours',
      dataIndex: 'total_hours',
      key: 'total_hours',
      width: 100,
      render: (hours) => (
        <span style={{ fontWeight: 600 }}>{hours.toFixed(1)}h</span>
      ),
      sorter: (a, b) => a.total_hours - b.total_hours,
    },
    {
      title: 'Annotations',
      dataIndex: 'annotations_count',
      key: 'annotations_count',
      width: 120,
      render: (count) => count.toLocaleString(),
      sorter: (a, b) => a.annotations_count - b.annotations_count,
    },
    {
      title: 'Efficiency',
      dataIndex: 'efficiency_score',
      key: 'efficiency_score',
      width: 120,
      render: (score) => (
        <Progress
          percent={score}
          size="small"
          status={score >= 90 ? 'success' : score >= 70 ? 'normal' : 'exception'}
        />
      ),
      sorter: (a, b) => a.efficiency_score - b.efficiency_score,
    },
    {
      title: 'Quality',
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 120,
      render: (score) => (
        <Progress
          percent={score}
          size="small"
          status={score >= 90 ? 'success' : score >= 70 ? 'normal' : 'exception'}
        />
      ),
      sorter: (a, b) => a.quality_score - b.quality_score,
    },
    {
      title: 'Trend',
      dataIndex: 'trend',
      key: 'trend',
      width: 100,
      render: (trend, record) => getTrendIcon(trend, record.trend_value),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) =>
        record.bonus_eligible && onReward && (
          <Button
            type="link"
            size="small"
            icon={<GiftOutlined />}
            onClick={() => handleRewardClick(record)}
          >
            Reward
          </Button>
        ),
    },
  ];

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>Loading ranking data...</p>
        </div>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card>
        <Empty
          description="Failed to load ranking data"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => refetch()}>
            Retry
          </Button>
        </Empty>
      </Card>
    );
  }

  return (
    <>
      {/* Summary Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Total Hours"
              value={summaryStats.totalHours.toFixed(1)}
              prefix={<ClockCircleOutlined />}
              suffix="h"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Total Annotations"
              value={summaryStats.totalAnnotations}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Avg Efficiency"
              value={summaryStats.avgEfficiency.toFixed(1)}
              prefix={<RiseOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Top Performers"
              value={summaryStats.topPerformers}
              prefix={<TeamOutlined />}
              suffix={`/ ${rankingData.length}`}
            />
          </Card>
        </Col>
      </Row>

      {/* Ranking Table */}
      <Card
        title={
          <Space>
            <TrophyOutlined style={{ color: '#faad14' }} />
            Work Hours Ranking
          </Space>
        }
        extra={
          <Space>
            <Select
              value={period}
              onChange={setPeriod}
              style={{ width: 120 }}
              options={[
                { value: 'week', label: 'This Week' },
                { value: 'month', label: 'This Month' },
                { value: 'quarter', label: 'This Quarter' },
              ]}
            />
            <Button
              icon={<ExportOutlined />}
              onClick={handleExport}
              loading={exportMutation.isPending}
            >
              Export
            </Button>
          </Space>
        }
      >
        {rankingData.length === 0 ? (
          <Empty description="No ranking data available" />
        ) : (
          <Table<RankingUser>
            columns={columns}
            dataSource={rankingData}
            rowKey="user_id"
            loading={isLoading}
            pagination={rankingData.length > 10 ? { pageSize: 10 } : false}
            size="middle"
            rowClassName={(record) => (record.rank <= 3 ? 'highlight-row' : '')}
          />
        )}

        {/* Cost Trends Summary */}
        {trendsData && (
          <div style={{ marginTop: 16, padding: 16, background: '#fafafa', borderRadius: 8 }}>
            <Space size="large">
              <Statistic
                title="Period Cost"
                value={(trendsData as { total_cost?: number }).total_cost || 0}
                prefix={<DollarOutlined />}
                precision={2}
              />
              <Statistic
                title="Cost Trend"
                value={(trendsData as { trend_percentage?: number }).trend_percentage || 0}
                suffix="%"
                valueStyle={{
                  color:
                    ((trendsData as { trend_percentage?: number }).trend_percentage || 0) > 0
                      ? '#cf1322'
                      : '#3f8600',
                }}
              />
            </Space>
          </div>
        )}
      </Card>

      {/* Reward Modal */}
      <Modal
        title={
          <Space>
            <GiftOutlined style={{ color: '#faad14' }} />
            Send Reward to {selectedUser?.user_name}
          </Space>
        }
        open={rewardModalVisible}
        onOk={handleRewardSubmit}
        onCancel={() => {
          setRewardModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={rewardLoading}
        okText="Send Reward"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="amount"
            label="Reward Amount ($)"
            rules={[
              { required: true, message: 'Please enter reward amount' },
              { type: 'number', min: 1, message: 'Amount must be at least $1' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              max={10000}
              prefix={<DollarOutlined />}
              placeholder="Enter reward amount"
            />
          </Form.Item>
          <Form.Item
            name="reason"
            label="Reason"
            rules={[{ required: true, message: 'Please enter a reason' }]}
          >
            <Input.TextArea
              rows={3}
              placeholder="Enter reason for the reward"
              maxLength={200}
              showCount
            />
          </Form.Item>
          {selectedUser && (
            <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 6 }}>
              <p style={{ margin: 0 }}>
                <strong>Performance Summary:</strong>
              </p>
              <p style={{ margin: '4px 0' }}>
                Total Hours: {selectedUser.total_hours.toFixed(1)}h
              </p>
              <p style={{ margin: '4px 0' }}>
                Annotations: {selectedUser.annotations_count.toLocaleString()}
              </p>
              <p style={{ margin: 0 }}>
                Efficiency: {selectedUser.efficiency_score}%
              </p>
            </div>
          )}
        </Form>
      </Modal>
    </>
  );
};
