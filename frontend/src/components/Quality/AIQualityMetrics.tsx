/**
 * AI Quality Metrics Component
 *
 * Displays AI-specific quality metrics:
 * - Pre-annotation accuracy trends
 * - Confidence distribution charts
 * - Human-AI agreement rates
 * - Engine performance comparison
 * - Quality degradation alerts
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Alert,
  Select,
  DatePicker,
  Space,
  Tag,
  Divider,
  Progress,
  Table,
  Tooltip,
  Badge,
  Empty,
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  UserOutlined,
  TrendingUpOutlined,
  TrendingDownOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

interface AIQualityMetricsProps {
  projectId: string;
  dateRange?: [string, string];
}

interface AccuracyTrendPoint {
  date: string;
  aiAccuracy: number;
  humanAccuracy: number;
  agreementRate: number;
  sampleCount: number;
}

interface ConfidenceDistribution {
  range: string;
  count: number;
  percentage: number;
  acceptanceRate: number;
}

interface HumanAIAgreement {
  metric: string;
  aiValue: number;
  humanValue: number;
  agreementRate: number;
  discrepancyCount: number;
}

interface EnginePerformanceMetric {
  engineId: string;
  engineName: string;
  engineType: string;
  accuracy: number;
  avgLatency: number;
  costPer1k: number;
  throughput: number;
  sampleCount: number;
}

interface QualityDegradationAlert {
  alertId: string;
  metric: string;
  currentValue: number;
  previousValue: number;
  degradationRate: number;
  severity: 'critical' | 'warning' | 'info';
  recommendation: string;
  timestamp: string;
}

const AIQualityMetrics: React.FC<AIQualityMetricsProps> = ({
  projectId,
  dateRange,
}) => {
  const { t } = useTranslation(['quality', 'ai_annotation', 'common']);
  const [loading, setLoading] = useState(false);
  const [selectedEngine, setSelectedEngine] = useState<string>('all');

  // Mock data - In production, fetch from API
  const [accuracyTrend] = useState<AccuracyTrendPoint[]>([
    { date: '2026-01-18', aiAccuracy: 0.82, humanAccuracy: 0.95, agreementRate: 0.85, sampleCount: 150 },
    { date: '2026-01-19', aiAccuracy: 0.84, humanAccuracy: 0.94, agreementRate: 0.87, sampleCount: 180 },
    { date: '2026-01-20', aiAccuracy: 0.86, humanAccuracy: 0.96, agreementRate: 0.89, sampleCount: 165 },
    { date: '2026-01-21', aiAccuracy: 0.88, humanAccuracy: 0.95, agreementRate: 0.90, sampleCount: 190 },
    { date: '2026-01-22', aiAccuracy: 0.87, humanAccuracy: 0.94, agreementRate: 0.88, sampleCount: 175 },
    { date: '2026-01-23', aiAccuracy: 0.89, humanAccuracy: 0.96, agreementRate: 0.91, sampleCount: 200 },
    { date: '2026-01-24', aiAccuracy: 0.90, humanAccuracy: 0.95, agreementRate: 0.92, sampleCount: 190 },
  ]);

  const [confidenceDistribution] = useState<ConfidenceDistribution[]>([
    { range: '0.90-1.00', count: 450, percentage: 45.0, acceptanceRate: 0.95 },
    { range: '0.80-0.89', count: 280, percentage: 28.0, acceptanceRate: 0.88 },
    { range: '0.70-0.79', count: 150, percentage: 15.0, acceptanceRate: 0.75 },
    { range: '0.60-0.69', count: 80, percentage: 8.0, acceptanceRate: 0.60 },
    { range: '0.00-0.59', count: 40, percentage: 4.0, acceptanceRate: 0.35 },
  ]);

  const [humanAIAgreement] = useState<HumanAIAgreement[]>([
    { metric: 'Label Selection', aiValue: 0.88, humanValue: 0.95, agreementRate: 0.92, discrepancyCount: 45 },
    { metric: 'Confidence Threshold', aiValue: 0.85, humanValue: 0.90, agreementRate: 0.89, discrepancyCount: 62 },
    { metric: 'Entity Recognition', aiValue: 0.91, humanValue: 0.96, agreementRate: 0.94, discrepancyCount: 28 },
    { metric: 'Sentiment Analysis', aiValue: 0.86, humanValue: 0.93, agreementRate: 0.90, discrepancyCount: 52 },
  ]);

  const [enginePerformance] = useState<EnginePerformanceMetric[]>([
    {
      engineId: 'pre-1',
      engineName: 'GPT-4 Pre-annotation',
      engineType: 'pre-annotation',
      accuracy: 0.89,
      avgLatency: 450,
      costPer1k: 2.5,
      throughput: 120,
      sampleCount: 5420,
    },
    {
      engineId: 'mid-1',
      engineName: 'Qwen Mid-coverage',
      engineType: 'mid-coverage',
      accuracy: 0.85,
      avgLatency: 280,
      costPer1k: 0.8,
      throughput: 200,
      sampleCount: 3850,
    },
    {
      engineId: 'post-1',
      engineName: 'Zhipu Post-validation',
      engineType: 'post-validation',
      accuracy: 0.92,
      avgLatency: 520,
      costPer1k: 1.5,
      throughput: 95,
      sampleCount: 2680,
    },
  ]);

  const [degradationAlerts] = useState<QualityDegradationAlert[]>([
    {
      alertId: 'alert-1',
      metric: 'AI Accuracy',
      currentValue: 0.87,
      previousValue: 0.90,
      degradationRate: -3.3,
      severity: 'warning',
      recommendation: 'Review recent training data quality',
      timestamp: '2026-01-24T10:30:00Z',
    },
    {
      alertId: 'alert-2',
      metric: 'Agreement Rate',
      currentValue: 0.88,
      previousValue: 0.92,
      degradationRate: -4.3,
      severity: 'warning',
      recommendation: 'Check for annotation guideline changes',
      timestamp: '2026-01-24T09:15:00Z',
    },
  ]);

  const getSeverityColor = (severity: QualityDegradationAlert['severity']): string => {
    switch (severity) {
      case 'critical':
        return '#ff4d4f';
      case 'warning':
        return '#faad14';
      default:
        return '#1890ff';
    }
  };

  const getSeverityIcon = (severity: QualityDegradationAlert['severity']) => {
    switch (severity) {
      case 'critical':
        return <WarningOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      default:
        return <CheckCircleOutlined style={{ color: '#1890ff' }} />;
    }
  };

  const agreementColumns: ColumnsType<HumanAIAgreement> = [
    {
      title: t('quality:columns.metric'),
      dataIndex: 'metric',
      key: 'metric',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: (
        <Space>
          <RobotOutlined />
          {t('quality:columns.ai_value')}
        </Space>
      ),
      dataIndex: 'aiValue',
      key: 'aiValue',
      render: (value: number) => `${(value * 100).toFixed(1)}%`,
      align: 'right',
    },
    {
      title: (
        <Space>
          <UserOutlined />
          {t('quality:columns.human_value')}
        </Space>
      ),
      dataIndex: 'humanValue',
      key: 'humanValue',
      render: (value: number) => `${(value * 100).toFixed(1)}%`,
      align: 'right',
    },
    {
      title: t('quality:columns.agreement_rate'),
      dataIndex: 'agreementRate',
      key: 'agreementRate',
      render: (value: number) => (
        <Space>
          <Progress
            percent={value * 100}
            size="small"
            strokeColor={value >= 0.9 ? '#52c41a' : value >= 0.8 ? '#1890ff' : '#faad14'}
            showInfo={false}
            style={{ width: 80 }}
          />
          <span>{(value * 100).toFixed(1)}%</span>
        </Space>
      ),
      align: 'center',
    },
    {
      title: t('quality:columns.discrepancies'),
      dataIndex: 'discrepancyCount',
      key: 'discrepancyCount',
      render: (count: number) => <Tag color="orange">{count}</Tag>,
      align: 'center',
    },
  ];

  const engineColumns: ColumnsType<EnginePerformanceMetric> = [
    {
      title: t('quality:columns.engine'),
      dataIndex: 'engineName',
      key: 'engineName',
      render: (name: string, record: EnginePerformanceMetric) => (
        <Space direction="vertical" size={0}>
          <strong>{name}</strong>
          <Tag color="blue">{record.engineType}</Tag>
        </Space>
      ),
    },
    {
      title: t('ai_annotation:metrics.accuracy'),
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (value: number) => (
        <Tag color={value >= 0.9 ? 'green' : value >= 0.8 ? 'blue' : 'orange'}>
          {(value * 100).toFixed(1)}%
        </Tag>
      ),
      sorter: (a, b) => a.accuracy - b.accuracy,
      align: 'center',
    },
    {
      title: t('ai_annotation:metrics.avg_latency'),
      dataIndex: 'avgLatency',
      key: 'avgLatency',
      render: (value: number) => `${value}ms`,
      sorter: (a, b) => a.avgLatency - b.avgLatency,
      align: 'right',
    },
    {
      title: t('ai_annotation:metrics.cost_per_1k'),
      dataIndex: 'costPer1k',
      key: 'costPer1k',
      render: (value: number) => `$${value.toFixed(2)}`,
      sorter: (a, b) => a.costPer1k - b.costPer1k,
      align: 'right',
    },
    {
      title: t('ai_annotation:metrics.throughput'),
      dataIndex: 'throughput',
      key: 'throughput',
      render: (value: number) => `${value}/s`,
      sorter: (a, b) => a.throughput - b.throughput,
      align: 'right',
    },
    {
      title: t('quality:columns.samples'),
      dataIndex: 'sampleCount',
      key: 'sampleCount',
      render: (value: number) => value.toLocaleString(),
      align: 'right',
    },
  ];

  const latestTrend = accuracyTrend[accuracyTrend.length - 1];
  const previousTrend = accuracyTrend[accuracyTrend.length - 2];
  const accuracyChange = ((latestTrend.aiAccuracy - previousTrend.aiAccuracy) / previousTrend.aiAccuracy) * 100;

  return (
    <div className="ai-quality-metrics">
      {/* Summary Statistics */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quality:stats.ai_accuracy')}
              value={latestTrend.aiAccuracy * 100}
              precision={1}
              suffix="%"
              prefix={<RobotOutlined />}
              valueStyle={{
                color: accuracyChange >= 0 ? '#52c41a' : '#ff4d4f',
              }}
            />
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <Space>
                {accuracyChange >= 0 ? <TrendingUpOutlined /> : <TrendingDownOutlined />}
                <span style={{ color: accuracyChange >= 0 ? '#52c41a' : '#ff4d4f' }}>
                  {accuracyChange >= 0 ? '+' : ''}{accuracyChange.toFixed(1)}%
                </span>
                <span style={{ color: '#999' }}>{t('quality:labels.vs_previous')}</span>
              </Space>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quality:stats.agreement_rate')}
              value={latestTrend.agreementRate * 100}
              precision={1}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <Space>
                <UserOutlined />
                <span style={{ color: '#999' }}>
                  {t('quality:labels.human_accuracy')}: {(latestTrend.humanAccuracy * 100).toFixed(1)}%
                </span>
              </Space>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quality:stats.total_samples')}
              value={accuracyTrend.reduce((sum, p) => sum + p.sampleCount, 0)}
              prefix={<LineChartOutlined />}
            />
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <Space>
                <span style={{ color: '#999' }}>
                  {t('quality:labels.avg_per_day')}: {Math.round(accuracyTrend.reduce((sum, p) => sum + p.sampleCount, 0) / accuracyTrend.length)}
                </span>
              </Space>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quality:stats.active_alerts')}
              value={degradationAlerts.length}
              prefix={<WarningOutlined />}
              valueStyle={{ color: degradationAlerts.length > 0 ? '#faad14' : '#52c41a' }}
            />
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <Space>
                <Badge
                  status={degradationAlerts.length > 0 ? 'warning' : 'success'}
                  text={
                    degradationAlerts.length > 0
                      ? t('quality:labels.needs_attention')
                      : t('quality:labels.all_good')
                  }
                />
              </Space>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Quality Degradation Alerts */}
      {degradationAlerts.length > 0 && (
        <Card
          title={
            <Space>
              <WarningOutlined />
              {t('quality:titles.degradation_alerts')}
            </Space>
          }
          style={{ marginTop: 16 }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {degradationAlerts.map((alert) => (
              <Alert
                key={alert.alertId}
                message={
                  <Space>
                    {getSeverityIcon(alert.severity)}
                    <strong>{alert.metric}</strong>
                    <Tag color={getSeverityColor(alert.severity)}>
                      {alert.degradationRate >= 0 ? '+' : ''}{alert.degradationRate.toFixed(1)}%
                    </Tag>
                  </Space>
                }
                description={
                  <div>
                    <div style={{ marginBottom: 8 }}>
                      {t('quality:labels.current')}: {(alert.currentValue * 100).toFixed(1)}% →{' '}
                      {t('quality:labels.previous')}: {(alert.previousValue * 100).toFixed(1)}%
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      <ThunderboltOutlined /> {alert.recommendation}
                    </div>
                  </div>
                }
                type={alert.severity === 'critical' ? 'error' : 'warning'}
                showIcon={false}
                closable
              />
            ))}
          </Space>
        </Card>
      )}

      {/* Confidence Distribution */}
      <Card
        title={
          <Space>
            <BarChartOutlined />
            {t('quality:titles.confidence_distribution')}
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {confidenceDistribution.map((dist, idx) => (
            <div key={idx}>
              <div style={{ marginBottom: 4 }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <span>{dist.range}</span>
                  <Space>
                    <Tag color="blue">{dist.count} samples</Tag>
                    <Tag color="green">
                      {(dist.acceptanceRate * 100).toFixed(0)}% accepted
                    </Tag>
                  </Space>
                </Space>
              </div>
              <Progress
                percent={dist.percentage}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
                format={(percent) => `${percent?.toFixed(1)}%`}
              />
            </div>
          ))}
        </Space>
      </Card>

      {/* Human-AI Agreement */}
      <Card
        title={
          <Space>
            <CheckCircleOutlined />
            {t('quality:titles.human_ai_agreement')}
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Table
          columns={agreementColumns}
          dataSource={humanAIAgreement}
          rowKey="metric"
          pagination={false}
          size="small"
        />
      </Card>

      {/* Engine Performance Comparison */}
      <Card
        title={
          <Space>
            <ThunderboltOutlined />
            {t('quality:titles.engine_performance')}
          </Space>
        }
        extra={
          <Select
            value={selectedEngine}
            onChange={setSelectedEngine}
            style={{ width: 200 }}
            size="small"
          >
            <Select.Option value="all">{t('quality:filters.all_engines')}</Select.Option>
            {enginePerformance.map((engine) => (
              <Select.Option key={engine.engineId} value={engine.engineId}>
                {engine.engineName}
              </Select.Option>
            ))}
          </Select>
        }
        style={{ marginTop: 16 }}
      >
        <Table
          columns={engineColumns}
          dataSource={
            selectedEngine === 'all'
              ? enginePerformance
              : enginePerformance.filter((e) => e.engineId === selectedEngine)
          }
          rowKey="engineId"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
};

export default AIQualityMetrics;
