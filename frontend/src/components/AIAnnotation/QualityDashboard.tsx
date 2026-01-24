/**
 * AI Annotation Quality Dashboard Component
 *
 * Displays quality metrics and trends for AI annotation:
 * - Overall quality scores
 * - Quality trend charts
 * - Inconsistencies and recommendations
 * - Engine performance comparison
 * - Quality degradation alerts
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Alert,
  Space,
  Select,
  DatePicker,
  Button,
  Tooltip,
  Badge,
  Divider,
  Empty,
  Spin,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  LineChartOutlined,
  RiseOutlined,
  FallOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

// Types
export interface QualityOverview {
  aiAccuracy: number;
  agreementRate: number;
  totalSamples: number;
  activeAlerts: number;
}

export interface AccuracyTrend {
  date: string;
  aiAccuracy: number;
  humanAccuracy: number;
  agreementRate: number;
  sampleCount: number;
}

export interface ConfidenceDistribution {
  range: string;
  count: number;
  acceptanceRate: number;
}

export interface EnginePerformance {
  engineId: string;
  engineName: string;
  accuracy: number;
  confidence: number;
  samples: number;
  suggestions: number;
  acceptanceRate: number;
}

export interface DegradationAlert {
  alertId: string;
  metric: string;
  currentValue: number;
  previousValue: number;
  degradationRate: number;
  severity: 'warning' | 'critical';
  recommendation: string;
  timestamp: string;
}

export interface Inconsistency {
  id: string;
  type: string;
  severity: 'low' | 'medium' | 'high';
  affectedDocuments: string[];
  description: string;
  suggestedFix?: string;
}

interface QualityDashboardProps {
  projectId: string;
  dateRange?: [string, string];
  engineId?: string;
}


const QualityDashboard: React.FC<QualityDashboardProps> = ({
  projectId,
  dateRange,
  engineId,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [loading, setLoading] = useState(false);
  const [overview, setOverview] = useState<QualityOverview | null>(null);
  const [accuracyTrend, setAccuracyTrend] = useState<AccuracyTrend[]>([]);
  const [confidenceDistribution, setConfidenceDistribution] = useState<ConfidenceDistribution[]>([]);
  const [enginePerformance, setEnginePerformance] = useState<EnginePerformance[]>([]);
  const [alerts, setAlerts] = useState<DegradationAlert[]>([]);
  const [inconsistencies, setInconsistencies] = useState<Inconsistency[]>([]);
  const [selectedDateRange, setSelectedDateRange] = useState<string>('last_30_days');
  const [selectedEngine, setSelectedEngine] = useState<string | undefined>(engineId);

  useEffect(() => {
    loadQualityData();
  }, [projectId, selectedDateRange, selectedEngine]);

  const loadQualityData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        project_id: projectId,
        date_range: selectedDateRange,
      });
      if (selectedEngine) {
        params.append('engine_id', selectedEngine);
      }

      const response = await fetch(`/api/v1/annotation/quality-metrics?${params}`);
      if (response.ok) {
        const data = await response.json();
        setOverview(data.overview);
        setAccuracyTrend(data.accuracy_trend || data.accuracyTrend || []);
        setConfidenceDistribution(data.confidence_distribution || data.confidenceDistribution || []);
        setEnginePerformance(data.engine_performance || data.enginePerformance || []);
        setAlerts(data.degradation_alerts || data.degradationAlerts || []);
      }

      // Load inconsistencies
      const inconsistenciesRes = await fetch(`/api/v1/annotation/inconsistencies/${projectId}?limit=10`);
      if (inconsistenciesRes.ok) {
        const inconsistenciesData = await inconsistenciesRes.json();
        setInconsistencies(inconsistenciesData);
      }
    } catch (error) {
      console.error('Failed to load quality data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.9) return '#52c41a';
    if (score >= 0.7) return '#1890ff';
    if (score >= 0.5) return '#faad14';
    return '#ff4d4f';
  };

  const getScoreStatus = (score: number): 'success' | 'normal' | 'exception' => {
    if (score >= 0.9) return 'success';
    if (score >= 0.7) return 'normal';
    return 'exception';
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
      case 'high':
        return 'red';
      case 'warning':
      case 'medium':
        return 'orange';
      case 'low':
        return 'blue';
      default:
        return 'default';
    }
  };

  const engineColumns: ColumnsType<EnginePerformance> = [
    {
      title: t('ai_annotation:quality.engine'),
      dataIndex: 'engineName',
      key: 'engineName',
    },
    {
      title: t('ai_annotation:quality.accuracy'),
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (value: number) => (
        <Progress
          percent={Math.round(value * 100)}
          size="small"
          status={getScoreStatus(value)}
          style={{ width: 100 }}
        />
      ),
      sorter: (a, b) => a.accuracy - b.accuracy,
    },
    {
      title: t('ai_annotation:quality.confidence'),
      dataIndex: 'confidence',
      key: 'confidence',
      render: (value: number) => `${(value * 100).toFixed(0)}%`,
    },
    {
      title: t('ai_annotation:quality.samples'),
      dataIndex: 'samples',
      key: 'samples',
    },
    {
      title: t('ai_annotation:quality.acceptance_rate'),
      dataIndex: 'acceptanceRate',
      key: 'acceptanceRate',
      render: (value: number) => (
        <Tag color={value >= 0.8 ? 'green' : value >= 0.6 ? 'orange' : 'red'}>
          {(value * 100).toFixed(0)}%
        </Tag>
      ),
    },
  ];

  const inconsistencyColumns: ColumnsType<Inconsistency> = [
    {
      title: t('ai_annotation:quality.type'),
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: t('ai_annotation:quality.severity'),
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>
          {t(`ai_annotation:quality.severity_levels.${severity}`)}
        </Tag>
      ),
    },
    {
      title: t('ai_annotation:quality.affected_documents'),
      dataIndex: 'affectedDocuments',
      key: 'affectedDocuments',
      render: (docs: string[]) => (
        <Tooltip title={docs.join(', ')}>
          <span>{docs.length} {t('ai_annotation:quality.documents')}</span>
        </Tooltip>
      ),
    },
    {
      title: t('ai_annotation:quality.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('ai_annotation:quality.suggested_fix'),
      dataIndex: 'suggestedFix',
      key: 'suggestedFix',
      render: (fix?: string) =>
        fix ? (
          <Tooltip title={fix}>
            <BulbOutlined style={{ color: '#1890ff' }} />
          </Tooltip>
        ) : (
          '-'
        ),
    },
  ];

  if (loading && !overview) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="quality-dashboard">
      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Select
            value={selectedDateRange}
            onChange={setSelectedDateRange}
            style={{ width: 150 }}
          >
            <Select.Option value="last_7_days">{t('ai_annotation:quality.last_7_days')}</Select.Option>
            <Select.Option value="last_30_days">{t('ai_annotation:quality.last_30_days')}</Select.Option>
            <Select.Option value="last_90_days">{t('ai_annotation:quality.last_90_days')}</Select.Option>
          </Select>
          <Select
            value={selectedEngine}
            onChange={setSelectedEngine}
            style={{ width: 200 }}
            allowClear
            placeholder={t('ai_annotation:quality.all_engines')}
          >
            {enginePerformance.map((engine) => (
              <Select.Option key={engine.engineId} value={engine.engineId}>
                {engine.engineName}
              </Select.Option>
            ))}
          </Select>
          <Button icon={<ReloadOutlined />} onClick={loadQualityData} loading={loading}>
            {t('common:actions.refresh')}
          </Button>
        </Space>
      </Card>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          {alerts.map((alert) => (
            <Alert
              key={alert.alertId}
              message={
                <Space>
                  <span>{alert.metric}</span>
                  <Tag color={alert.severity === 'critical' ? 'red' : 'orange'}>
                    {alert.degradationRate > 0 ? '+' : ''}{(alert.degradationRate * 100).toFixed(1)}%
                  </Tag>
                </Space>
              }
              description={alert.recommendation}
              type={alert.severity === 'critical' ? 'error' : 'warning'}
              showIcon
              closable
              style={{ marginBottom: 8 }}
            />
          ))}
        </div>
      )}

      {/* Overview Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('ai_annotation:quality.ai_accuracy')}
              value={overview?.aiAccuracy ? (overview.aiAccuracy * 100).toFixed(1) : 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: getScoreColor(overview?.aiAccuracy || 0) }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('ai_annotation:quality.agreement_rate')}
              value={overview?.agreementRate ? (overview.agreementRate * 100).toFixed(1) : 0}
              suffix="%"
              prefix={<LineChartOutlined />}
              valueStyle={{ color: getScoreColor(overview?.agreementRate || 0) }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('ai_annotation:quality.total_samples')}
              value={overview?.totalSamples || 0}
              prefix={<InfoCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('ai_annotation:quality.active_alerts')}
              value={overview?.activeAlerts || 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: (overview?.activeAlerts || 0) > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* Accuracy Trend */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                {t('ai_annotation:quality.accuracy_trend')}
              </Space>
            }
          >
            {accuracyTrend.length > 0 ? (
              <div style={{ height: 200 }}>
                {/* Simple trend display - in production, use a charting library */}
                <Table
                  dataSource={accuracyTrend.slice(-7)}
                  rowKey="date"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: t('ai_annotation:quality.date'), dataIndex: 'date', key: 'date' },
                    {
                      title: t('ai_annotation:quality.ai_accuracy'),
                      dataIndex: 'aiAccuracy',
                      key: 'aiAccuracy',
                      render: (v: number) => `${(v * 100).toFixed(1)}%`,
                    },
                    {
                      title: t('ai_annotation:quality.human_accuracy'),
                      dataIndex: 'humanAccuracy',
                      key: 'humanAccuracy',
                      render: (v: number) => `${(v * 100).toFixed(1)}%`,
                    },
                    {
                      title: t('ai_annotation:quality.samples'),
                      dataIndex: 'sampleCount',
                      key: 'sampleCount',
                    },
                  ]}
                />
              </div>
            ) : (
              <Empty description={t('ai_annotation:quality.no_trend_data')} />
            )}
          </Card>
        </Col>

        {/* Confidence Distribution */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <InfoCircleOutlined />
                {t('ai_annotation:quality.confidence_distribution')}
              </Space>
            }
          >
            {confidenceDistribution.length > 0 ? (
              <div>
                {confidenceDistribution.map((item) => (
                  <div key={item.range} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>{item.range}</span>
                      <Space>
                        <span>{item.count} {t('ai_annotation:quality.samples')}</span>
                        <Tag color={item.acceptanceRate >= 0.8 ? 'green' : 'orange'}>
                          {(item.acceptanceRate * 100).toFixed(0)}% {t('ai_annotation:quality.accepted')}
                        </Tag>
                      </Space>
                    </div>
                    <Progress
                      percent={Math.round((item.count / (overview?.totalSamples || 1)) * 100)}
                      showInfo={false}
                      strokeColor={item.acceptanceRate >= 0.8 ? '#52c41a' : '#faad14'}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <Empty description={t('ai_annotation:quality.no_distribution_data')} />
            )}
          </Card>
        </Col>
      </Row>

      {/* Engine Performance */}
      <Card
        title={
          <Space>
            <RiseOutlined />
            {t('ai_annotation:quality.engine_performance')}
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Table
          dataSource={enginePerformance}
          columns={engineColumns}
          rowKey="engineId"
          pagination={false}
          size="small"
        />
      </Card>

      {/* Inconsistencies */}
      {inconsistencies.length > 0 && (
        <Card
          title={
            <Space>
              <WarningOutlined style={{ color: '#faad14' }} />
              {t('ai_annotation:quality.inconsistencies')}
              <Badge count={inconsistencies.length} />
            </Space>
          }
          style={{ marginTop: 16 }}
        >
          <Table
            dataSource={inconsistencies}
            columns={inconsistencyColumns}
            rowKey="id"
            pagination={{ pageSize: 5 }}
            size="small"
          />
        </Card>
      )}
    </div>
  );
};

export default QualityDashboard;
