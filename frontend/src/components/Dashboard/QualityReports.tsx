// Quality reports and trend charts component with export functionality
import { Card, Row, Col, Select, DatePicker, Space, Statistic, Alert, Tooltip, Button, Dropdown, message } from 'antd';
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
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useState, useCallback } from 'react';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

interface QualityTrendData {
  timestamp: number;
  datetime: string;
  qualityScore: number;
  completionRate: number;
  revisionRate: number;
  avgAnnotationTime: number;
}

interface QualityDistributionData {
  range: string;
  count: number;
  percentage: number;
  color: string;
}

interface WorkTimeData {
  user: string;
  totalHours: number;
  efficiency: number;
  qualityScore: number;
  tasksCompleted: number;
}

interface AnomalyData {
  timestamp: number;
  datetime: string;
  type: 'quality' | 'efficiency' | 'time';
  severity: 'low' | 'medium' | 'high';
  description: string;
  value: number;
}

interface QualityReportsProps {
  data?: {
    trends: QualityTrendData[];
    distribution: QualityDistributionData[];
    workTime: WorkTimeData[];
    anomalies: AnomalyData[];
  };
  loading?: boolean;
}

export const QualityReports: React.FC<QualityReportsProps> = ({
  data,
  loading = false,
}) => {
  const { t } = useTranslation('dashboard');
  const [timeRange, setTimeRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs(),
  ]);
  const [chartType, setChartType] = useState<'line' | 'area'>('line');

  // Use real data or empty arrays
  const trends = data?.trends || [];
  const distribution = data?.distribution || [];
  const workTime = data?.workTime || [];
  const anomalies = data?.anomalies || [];

  // Format trend data for charts
  const formattedTrends = trends.map((item) => ({
    ...item,
    time: dayjs(item.datetime).format('HH:mm'),
    qualityPercent: (item.qualityScore * 100).toFixed(1),
    completionPercent: (item.completionRate * 100).toFixed(1),
    revisionPercent: (item.revisionRate * 100).toFixed(1),
  }));

  // Calculate summary statistics (handle empty data)
  const avgQuality = trends.length > 0 
    ? trends.reduce((sum, item) => sum + item.qualityScore, 0) / trends.length 
    : 0;
  const avgCompletion = trends.length > 0
    ? trends.reduce((sum, item) => sum + item.completionRate, 0) / trends.length
    : 0;
  const avgRevision = trends.length > 0
    ? trends.reduce((sum, item) => sum + item.revisionRate, 0) / trends.length
    : 0;
  const totalWorkHours = workTime.reduce((sum, item) => sum + item.totalHours, 0);

  // Export to CSV/Excel
  const exportToCSV = useCallback(() => {
    const headers = ['Time', 'Quality Score (%)', 'Completion Rate (%)', 'Revision Rate (%)', 'Avg Annotation Time (s)'];
    const rows = formattedTrends.map(item => [
      item.time,
      item.qualityPercent,
      item.completionPercent,
      item.revisionPercent,
      item.avgAnnotationTime.toFixed(1)
    ]);
    
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `quality_report_${dayjs().format('YYYY-MM-DD')}.csv`;
    link.click();
    message.success(t('export.csvSuccess') || 'CSV exported successfully');
  }, [formattedTrends, t]);

  // Export to JSON (for PDF generation via backend)
  const exportToPDF = useCallback(async () => {
    try {
      const reportData = {
        generatedAt: dayjs().toISOString(),
        period: {
          start: timeRange[0].format('YYYY-MM-DD'),
          end: timeRange[1].format('YYYY-MM-DD'),
        },
        summary: {
          avgQualityScore: (avgQuality * 100).toFixed(1),
          avgCompletionRate: (avgCompletion * 100).toFixed(1),
          avgRevisionRate: (avgRevision * 100).toFixed(1),
          totalWorkHours: totalWorkHours.toFixed(1),
        },
        trends: formattedTrends,
        distribution,
        workTime,
        anomalies,
      };
      
      // For now, export as JSON (PDF generation would require backend support)
      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `quality_report_${dayjs().format('YYYY-MM-DD')}.json`;
      link.click();
      message.success(t('export.pdfSuccess') || 'Report exported successfully');
    } catch (error) {
      message.error(t('export.error') || 'Export failed');
    }
  }, [avgQuality, avgCompletion, avgRevision, totalWorkHours, formattedTrends, distribution, workTime, anomalies, timeRange, t]);

  // Export dropdown menu
  const exportMenuItems: MenuProps['items'] = [
    {
      key: 'csv',
      icon: <FileExcelOutlined />,
      label: t('export.csv') || 'Export CSV',
      onClick: exportToCSV,
    },
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: t('export.pdf') || 'Export PDF',
      onClick: exportToPDF,
    },
  ];

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
            <Select
              value={chartType}
              onChange={setChartType}
              style={{ width: 120 }}
            >
              <Option value="line">{t('charts.lineChart')}</Option>
              <Option value="area">{t('charts.areaChart')}</Option>
            </Select>
          </Space>
          <Dropdown menu={{ items: exportMenuItems }} placement="bottomRight">
            <Button icon={<DownloadOutlined />}>
              {t('export.button') || 'Export'}
            </Button>
          </Dropdown>
        </Space>
      </Card>

      {/* Summary Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
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
          <Card>
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
          <Card>
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
          <Card>
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
                      t('metrics.revisionRate')
                    ]}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="qualityPercent"
                    stroke="#52c41a"
                    strokeWidth={2}
                    name={t('metrics.qualityScore')}
                  />
                  <Line
                    type="monotone"
                    dataKey="completionPercent"
                    stroke="#1890ff"
                    strokeWidth={2}
                    name={t('metrics.completionRate')}
                  />
                  <Line
                    type="monotone"
                    dataKey="revisionPercent"
                    stroke="#ff4d4f"
                    strokeWidth={2}
                    name={t('metrics.revisionRate')}
                  />
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
                      t('metrics.revisionRate')
                    ]}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="qualityPercent"
                    stackId="1"
                    stroke="#52c41a"
                    fill="#52c41a"
                    fillOpacity={0.6}
                    name={t('metrics.qualityScore')}
                  />
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

      {/* Work Time Analysis */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24}>
          <Card title={t('charts.workTimeAnalysis')} loading={loading}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={workTime}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="user" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <RechartsTooltip
                  formatter={(value, name) => [
                    name === 'totalHours' ? `${value}h` :
                    name === 'efficiency' || name === 'qualityScore' ? `${(Number(value) * 100).toFixed(1)}%` :
                    value,
                    name === 'totalHours' ? t('metrics.totalHours') :
                    name === 'efficiency' ? t('metrics.efficiency') :
                    name === 'qualityScore' ? t('metrics.qualityScore') :
                    t('metrics.tasksCompleted')
                  ]}
                />
                <Legend />
                <Bar
                  yAxisId="left"
                  dataKey="totalHours"
                  fill="#1890ff"
                  name={t('metrics.totalHours')}
                />
                <Bar
                  yAxisId="right"
                  dataKey="tasksCompleted"
                  fill="#52c41a"
                  name={t('metrics.tasksCompleted')}
                />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Anomaly Detection */}
      {anomalies.length > 0 && (
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Card 
              title={
                <Space>
                  <WarningOutlined style={{ color: '#faad14' }} />
                  {t('charts.anomalyDetection')}
                </Space>
              }
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {anomalies.map((anomaly, index) => (
                  <Alert
                    key={index}
                    type={anomaly.severity === 'high' ? 'error' : anomaly.severity === 'medium' ? 'warning' : 'info'}
                    message={
                      <Space>
                        <span>{anomaly.description}</span>
                        <span style={{ color: '#999' }}>
                          {dayjs(anomaly.datetime).format('YYYY-MM-DD HH:mm')}
                        </span>
                      </Space>
                    }
                    description={
                      <Tooltip title={t('anomaly.clickForDetails')}>
                        <span style={{ cursor: 'pointer' }}>
                          {t('anomaly.value')}: {(anomaly.value * 100).toFixed(1)}%
                        </span>
                      </Tooltip>
                    }
                    showIcon
                  />
                ))}
              </Space>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};