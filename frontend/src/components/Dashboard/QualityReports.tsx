// Quality reports and trend charts component with export functionality
import { Card, Row, Col, Select, DatePicker, Space, Statistic, Alert, Tooltip, Button, Dropdown, Table, message } from 'antd';
import type { MenuProps } from 'antd';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  TrophyOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  WarningOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useState, useCallback } from 'react';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import type { AnnotationEfficiency, UserActivityMetrics } from '@/types';

const { RangePicker } = DatePicker;
const { Option } = Select;

export type QualityMetricKey = 'avgQualityScore' | 'avgCompletionRate' | 'avgRevisionRate' | 'totalWorkHours';

interface QualityReportsProps {
  annotationEfficiency?: AnnotationEfficiency;
  userActivity?: UserActivityMetrics;
  loading?: boolean;
}

export const QualityReports: React.FC<QualityReportsProps> = ({
  annotationEfficiency,
  userActivity,
  loading = false,
}) => {
  const { t } = useTranslation('dashboard');
  const [timeRange, setTimeRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs(),
  ]);
  const [chartType, setChartType] = useState<'line' | 'area'>('line');
  const [selectedCard, setSelectedCard] = useState<QualityMetricKey | null>(null);

  // Real data from backend
  const trends = annotationEfficiency?.trends || [];
  const summary = annotationEfficiency?.summary;

  // Format trend data for charts
  const formattedTrends = trends.map((item) => ({
    ...item,
    time: dayjs(item.datetime).format('MM-DD HH:mm'),
    qualityPercent: (item.quality_score * 100).toFixed(1),
    completionPercent: (item.completion_rate * 100).toFixed(1),
    revisionPercent: (item.revision_rate * 100).toFixed(1),
  }));

  // Summary statistics from real data
  const avgQuality = summary?.avg_quality_score ?? 0;
  const avgCompletion = summary?.avg_completion_rate ?? 0;
  const avgRevision = summary?.avg_revision_rate ?? 0;
  const totalWorkHours = userActivity?.summary?.avg_session_duration
    ? (userActivity.summary.avg_active_users * userActivity.summary.avg_session_duration / 3600)
    : 0;

  const handleCardClick = (key: QualityMetricKey) => {
    setSelectedCard(selectedCard === key ? null : key);
  };

  const cardStyle = (key: QualityMetricKey, color: string) => ({
    cursor: 'pointer' as const,
    borderColor: selectedCard === key ? color : undefined,
    borderWidth: selectedCard === key ? 2 : undefined,
    transition: 'border-color 0.3s',
  });

  // Detail table columns for trend data
  const trendDetailColumns = [
    {
      title: t('qualityDetail.time'),
      dataIndex: 'datetime',
      key: 'datetime',
      width: 160,
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('metrics.qualityScore'),
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 120,
      render: (val: number) => `${(val * 100).toFixed(1)}%`,
      sorter: (a: any, b: any) => a.quality_score - b.quality_score,
    },
    {
      title: t('metrics.completionRate'),
      dataIndex: 'completion_rate',
      key: 'completion_rate',
      width: 120,
      render: (val: number) => `${(val * 100).toFixed(1)}%`,
      sorter: (a: any, b: any) => a.completion_rate - b.completion_rate,
    },
    {
      title: t('metrics.revisionRate'),
      dataIndex: 'revision_rate',
      key: 'revision_rate',
      width: 120,
      render: (val: number) => `${(val * 100).toFixed(1)}%`,
      sorter: (a: any, b: any) => a.revision_rate - b.revision_rate,
    },
    {
      title: t('qualityDetail.annotationsPerHour'),
      dataIndex: 'annotations_per_hour',
      key: 'annotations_per_hour',
      width: 140,
      render: (val: number) => val.toFixed(1),
      sorter: (a: any, b: any) => a.annotations_per_hour - b.annotations_per_hour,
    },
  ];

  // User activity detail columns
  const userActivityColumns = [
    {
      title: t('qualityDetail.time'),
      dataIndex: 'datetime',
      key: 'datetime',
      width: 160,
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('metrics.activeUsers'),
      dataIndex: 'active_users_count',
      key: 'active_users_count',
      width: 120,
    },
    {
      title: t('qualityDetail.sessionDuration'),
      dataIndex: 'session_duration_avg',
      key: 'session_duration_avg',
      width: 140,
      render: (val: number) => `${(val / 60).toFixed(1)} min`,
    },
    {
      title: t('qualityDetail.actionsPerSession'),
      dataIndex: 'actions_per_session',
      key: 'actions_per_session',
      width: 140,
      render: (val: number) => val.toFixed(1),
    },
  ];

  const detailTitleMap: Record<QualityMetricKey, string> = {
    avgQualityScore: t('metrics.avgQualityScore'),
    avgCompletionRate: t('metrics.avgCompletionRate'),
    avgRevisionRate: t('metrics.avgRevisionRate'),
    totalWorkHours: t('metrics.totalWorkHours'),
  };

  // Export to CSV
  const exportToCSV = useCallback(() => {
    const headers = ['Time', 'Quality Score (%)', 'Completion Rate (%)', 'Revision Rate (%)', 'Annotations/Hour'];
    const rows = formattedTrends.map(item => [
      item.time, item.qualityPercent, item.completionPercent, item.revisionPercent,
      item.annotations_per_hour.toFixed(1),
    ]);
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `quality_report_${dayjs().format('YYYY-MM-DD')}.csv`;
    link.click();
    message.success(t('export.csvSuccess'));
  }, [formattedTrends, t]);

  const exportToPDF = useCallback(async () => {
    try {
      const reportData = {
        generatedAt: dayjs().toISOString(),
        period: { start: timeRange[0].format('YYYY-MM-DD'), end: timeRange[1].format('YYYY-MM-DD') },
        summary: {
          avgQualityScore: (avgQuality * 100).toFixed(1),
          avgCompletionRate: (avgCompletion * 100).toFixed(1),
          avgRevisionRate: (avgRevision * 100).toFixed(1),
          totalWorkHours: totalWorkHours.toFixed(1),
        },
        trends: formattedTrends,
      };
      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `quality_report_${dayjs().format('YYYY-MM-DD')}.json`;
      link.click();
      message.success(t('export.pdfSuccess'));
    } catch {
      message.error(t('export.error'));
    }
  }, [avgQuality, avgCompletion, avgRevision, totalWorkHours, formattedTrends, timeRange, t]);

  const exportMenuItems: MenuProps['items'] = [
    { key: 'csv', icon: <FileExcelOutlined />, label: t('export.csv'), onClick: exportToCSV },
    { key: 'pdf', icon: <FilePdfOutlined />, label: t('export.pdf'), onClick: exportToPDF },
  ];

  // Quality distribution from trends (group by score ranges)
  const distribution = (() => {
    if (trends.length === 0) return [];
    const ranges = [
      { range: '90-100%', min: 0.9, max: 1.01, color: '#52c41a' },
      { range: '80-90%', min: 0.8, max: 0.9, color: '#1890ff' },
      { range: '70-80%', min: 0.7, max: 0.8, color: '#faad14' },
      { range: '<70%', min: 0, max: 0.7, color: '#ff4d4f' },
    ];
    return ranges.map(r => {
      const count = trends.filter(t => t.quality_score >= r.min && t.quality_score < r.max).length;
      return { ...r, count, percentage: trends.length > 0 ? Math.round(count / trends.length * 100) : 0 };
    }).filter(r => r.count > 0);
  })();

  return (
    <div>
      {/* Controls */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <RangePicker
              value={timeRange}
              onChange={(dates) => dates && setTimeRange(dates as [Dayjs, Dayjs])}
              format="YYYY-MM-DD"
            />
            <Select value={chartType} onChange={setChartType} style={{ width: 120 }}>
              <Option value="line">{t('charts.lineChart')}</Option>
              <Option value="area">{t('charts.areaChart')}</Option>
            </Select>
          </Space>
          <Dropdown menu={{ items: exportMenuItems }} placement="bottomRight">
            <Button icon={<DownloadOutlined />}>{t('export.button')}</Button>
          </Dropdown>
        </Space>
      </Card>

      {/* Summary Statistics - Clickable Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card hoverable style={cardStyle('avgQualityScore', '#52c41a')} onClick={() => handleCardClick('avgQualityScore')}>
            <Statistic
              title={t('metrics.avgQualityScore')}
              value={(avgQuality * 100).toFixed(1)}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: avgQuality >= 0.8 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card hoverable style={cardStyle('avgCompletionRate', '#1890ff')} onClick={() => handleCardClick('avgCompletionRate')}>
            <Statistic
              title={t('metrics.avgCompletionRate')}
              value={(avgCompletion * 100).toFixed(1)}
              suffix="%"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: avgCompletion >= 0.9 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card hoverable style={cardStyle('avgRevisionRate', '#ff4d4f')} onClick={() => handleCardClick('avgRevisionRate')}>
            <Statistic
              title={t('metrics.avgRevisionRate')}
              value={(avgRevision * 100).toFixed(1)}
              suffix="%"
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: avgRevision <= 0.1 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card hoverable style={cardStyle('totalWorkHours', '#1890ff')} onClick={() => handleCardClick('totalWorkHours')}>
            <Statistic
              title={t('metrics.totalWorkHours')}
              value={totalWorkHours.toFixed(1)}
              suffix="h"
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Detail Table - shown when a card is clicked */}
      {selectedCard && (
        <Card
          title={`${t('detailTable.title')} - ${detailTitleMap[selectedCard]}`}
          extra={<CloseOutlined style={{ cursor: 'pointer' }} onClick={() => setSelectedCard(null)} />}
          style={{ marginBottom: 24 }}
        >
          <Table
            columns={selectedCard === 'totalWorkHours' ? userActivityColumns : trendDetailColumns}
            dataSource={selectedCard === 'totalWorkHours' ? (userActivity?.trends || []) : trends}
            rowKey={(_, index) => String(index)}
            loading={loading}
            pagination={{ pageSize: 10, showTotal: (total) => t('detailTable.total', { total }) }}
            size="middle"
            scroll={{ x: 600 }}
          />
        </Card>
      )}

      {/* Quality Trend Chart */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title={t('charts.qualityTrend')} loading={loading}>
            <ResponsiveContainer width="100%" height={300}>
              {chartType === 'line' ? (
                <LineChart data={formattedTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <RechartsTooltip
                    formatter={(value, name) => [
                      `${value}%`,
                      name === 'qualityPercent' ? t('metrics.qualityScore') :
                      name === 'completionPercent' ? t('metrics.completionRate') :
                      t('metrics.revisionRate'),
                    ]}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="qualityPercent" stroke="#52c41a" strokeWidth={2} name={t('metrics.qualityScore')} />
                  <Line type="monotone" dataKey="completionPercent" stroke="#1890ff" strokeWidth={2} name={t('metrics.completionRate')} />
                  <Line type="monotone" dataKey="revisionPercent" stroke="#ff4d4f" strokeWidth={2} name={t('metrics.revisionRate')} />
                </LineChart>
              ) : (
                <AreaChart data={formattedTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <RechartsTooltip
                    formatter={(value, name) => [
                      `${value}%`,
                      name === 'qualityPercent' ? t('metrics.qualityScore') :
                      name === 'completionPercent' ? t('metrics.completionRate') :
                      t('metrics.revisionRate'),
                    ]}
                  />
                  <Legend />
                  <Area type="monotone" dataKey="qualityPercent" stackId="1" stroke="#52c41a" fill="#52c41a" fillOpacity={0.6} name={t('metrics.qualityScore')} />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* Quality Distribution Pie Chart */}
        <Col xs={24} lg={8}>
          <Card title={t('charts.qualityDistribution')} loading={loading}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={distribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry: any) => `${entry.range}: ${entry.percentage}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  );
};
