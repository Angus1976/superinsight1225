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

import type { QualityMetrics, Inconsistency } from '@/services/aiAnnotationApi';
import { fetchJsonResponseToSnake } from '@/utils/jsonCase';

export type QualityOverview = QualityMetrics['overview'];
export type AccuracyTrend = QualityMetrics['accuracy_trend'][number];
export type ConfidenceDistribution = QualityMetrics['confidence_distribution'][number];
export type EnginePerformance = QualityMetrics['engine_performance'][number];
export type DegradationAlert = QualityMetrics['degradation_alerts'][number];

interface QualityDashboardProps {
  projectId: string;
  dateRange?: [string, string];
  engineId?: string;
  /** 仪表盘卡片内嵌时可缩小密度 */
  compact?: boolean;
}

const QualityDashboard: React.FC<QualityDashboardProps> = ({
  projectId,
  dateRange,
  engineId,
  compact = false,
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
        const data = await fetchJsonResponseToSnake<QualityMetrics>(response);
        setOverview(data.overview);
        setAccuracyTrend(data.accuracy_trend ?? []);
        setConfidenceDistribution(data.confidence_distribution ?? []);
        setEnginePerformance(data.engine_performance ?? []);
        setAlerts(data.degradation_alerts ?? []);
      }

      const inconsistenciesRes = await fetch(`/api/v1/annotation/inconsistencies/${projectId}?limit=10`);
      if (inconsistenciesRes.ok) {
        const inconsistenciesData = await fetchJsonResponseToSnake<Inconsistency[]>(inconsistenciesRes);
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
      dataIndex: 'engine_name',
      key: 'engine_name',
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
      dataIndex: 'acceptance_rate',
      key: 'acceptance_rate',
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
      dataIndex: 'affected_documents',
      key: 'affected_documents',
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
      dataIndex: 'suggested_fix',
      key: 'suggested_fix',
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
      <Card size="small" style={{ marginBottom: compact ? 8 : 16 }}>
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
              <Select.Option key={engine.engine_id} value={engine.engine_id}>
                {engine.engine_name}
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
              key={alert.alert_id}
              message={
                <Space>
                  <span>{alert.metric}</span>
                  <Tag color={alert.severity === 'critical' ? 'red' : 'orange'}>
                    {alert.degradation_rate > 0 ? '+' : ''}{(alert.degradation_rate * 100).toFixed(1)}%
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
              value={overview?.ai_accuracy ? (overview.ai_accuracy * 100).toFixed(1) : 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: getScoreColor(overview?.ai_accuracy || 0) }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('ai_annotation:quality.agreement_rate')}
              value={overview?.agreement_rate ? (overview.agreement_rate * 100).toFixed(1) : 0}
              suffix="%"
              prefix={<LineChartOutlined />}
              valueStyle={{ color: getScoreColor(overview?.agreement_rate || 0) }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('ai_annotation:quality.total_samples')}
              value={overview?.total_samples || 0}
              prefix={<InfoCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('ai_annotation:quality.active_alerts')}
              value={overview?.active_alerts || 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: (overview?.active_alerts || 0) > 0 ? '#faad14' : '#52c41a' }}
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
                <Table
                  dataSource={accuracyTrend.slice(-7)}
                  rowKey="date"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: t('ai_annotation:quality.date'), dataIndex: 'date', key: 'date' },
                    {
                      title: t('ai_annotation:quality.ai_accuracy'),
                      dataIndex: 'ai_accuracy',
                      key: 'ai_accuracy',
                      render: (v: number) => `${(v * 100).toFixed(1)}%`,
                    },
                    {
                      title: t('ai_annotation:quality.human_accuracy'),
                      dataIndex: 'human_accuracy',
                      key: 'human_accuracy',
                      render: (v: number) => `${(v * 100).toFixed(1)}%`,
                    },
                    {
                      title: t('ai_annotation:quality.samples'),
                      dataIndex: 'sample_count',
                      key: 'sample_count',
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
                        <Tag color={item.acceptance_rate >= 0.8 ? 'green' : 'orange'}>
                          {(item.acceptance_rate * 100).toFixed(0)}% {t('ai_annotation:quality.accepted')}
                        </Tag>
                      </Space>
                    </div>
                    <Progress
                      percent={Math.round((item.count / (overview?.total_samples || 1)) * 100)}
                      showInfo={false}
                      strokeColor={item.acceptance_rate >= 0.8 ? '#52c41a' : '#faad14'}
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
          rowKey="engine_id"
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
            rowKey="inconsistency_id"
            pagination={{ pageSize: 5 }}
            size="small"
          />
        </Card>
      )}
    </div>
  );
};

export default QualityDashboard;
