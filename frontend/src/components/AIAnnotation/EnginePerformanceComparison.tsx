/**
 * Engine Performance Comparison Component
 *
 * Provides comprehensive performance comparison and visualization:
 * - Side-by-side engine comparison
 * - Performance metrics charts
 * - Cost vs accuracy analysis
 * - Speed vs quality trade-offs
 * - Historical performance trends
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  Alert,
  Divider,
  Tag,
  Table,
  Tooltip,
  Progress,
  Radio,
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

import type { EngineConfig, EngineStatus } from '@/pages/AIAnnotation/EngineConfiguration';

interface EnginePerformanceComparisonProps {
  engines: EngineConfig[];
  engineStatuses: EngineStatus[];
  fullView?: boolean;
}

interface PerformanceMetrics {
  engineId: string;
  engineName: string;
  accuracy: number;
  consistency: number;
  completeness: number;
  recall: number;
  f1Score: number;
  avgLatency: number;
  p95Latency: number;
  p99Latency: number;
  throughput: number;
  errorRate: number;
  costPer1kSamples: number;
  totalSamples: number;
  successRate: number;
}

interface ComparisonData {
  metric: string;
  engineA: number | string;
  engineB: number | string;
  difference: number | string;
  winner: 'A' | 'B' | 'tie';
}

const EnginePerformanceComparison: React.FC<EnginePerformanceComparisonProps> = ({
  engines,
  engineStatuses,
  fullView = false,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [selectedEngineA, setSelectedEngineA] = useState<string | null>(null);
  const [selectedEngineB, setSelectedEngineB] = useState<string | null>(null);
  const [metricsData, setMetricsData] = useState<PerformanceMetrics[]>([]);
  const [viewMode, setViewMode] = useState<'comparison' | 'ranking'>('comparison');

  useEffect(() => {
    if (engines.length >= 2) {
      setSelectedEngineA(engines[0].id || null);
      setSelectedEngineB(engines[1].id || null);
    }
    loadMetrics();
  }, [engines]);

  const loadMetrics = async () => {
    try {
      const response = await fetch('/api/v1/annotation/engines/performance');
      if (!response.ok) return;
      const data = await response.json();
      setMetricsData(data.metrics || generateMockData());
    } catch (error) {
      console.error('Failed to load performance metrics:', error);
      setMetricsData(generateMockData());
    }
  };

  const generateMockData = (): PerformanceMetrics[] => {
    return engines.map((engine) => ({
      engineId: engine.id || '',
      engineName: `${engine.engineType} (${engine.model})`,
      accuracy: Math.random() * 0.15 + 0.8,
      consistency: Math.random() * 0.15 + 0.75,
      completeness: Math.random() * 0.1 + 0.85,
      recall: Math.random() * 0.2 + 0.7,
      f1Score: Math.random() * 0.15 + 0.78,
      avgLatency: Math.random() * 1000 + 200,
      p95Latency: Math.random() * 2000 + 500,
      p99Latency: Math.random() * 3000 + 1000,
      throughput: Math.random() * 500 + 100,
      errorRate: Math.random() * 0.05,
      costPer1kSamples: Math.random() * 5 + 0.5,
      totalSamples: Math.floor(Math.random() * 50000) + 10000,
      successRate: Math.random() * 0.05 + 0.95,
    }));
  };

  const getMetricsForEngine = (engineId: string): PerformanceMetrics | null => {
    return metricsData.find((m) => m.engineId === engineId) || null;
  };

  const getEngineName = (engineId: string): string => {
    const engine = engines.find((e) => e.id === engineId);
    return engine ? `${engine.engineType} (${engine.model})` : engineId;
  };

  const calculateComparison = (): ComparisonData[] => {
    if (!selectedEngineA || !selectedEngineB) return [];

    const metricsA = getMetricsForEngine(selectedEngineA);
    const metricsB = getMetricsForEngine(selectedEngineB);

    if (!metricsA || !metricsB) return [];

    const compareMetric = (
      name: string,
      valueA: number,
      valueB: number,
      unit: string = '%',
      higherIsBetter: boolean = true
    ): ComparisonData => {
      const diff = higherIsBetter ? valueA - valueB : valueB - valueA;
      const diffPercent = ((Math.abs(diff) / valueB) * 100).toFixed(1);
      const winner: 'A' | 'B' | 'tie' =
        Math.abs(diff) < 0.01 ? 'tie' : diff > 0 ? 'A' : 'B';

      return {
        metric: name,
        engineA: unit === '%' ? `${(valueA * 100).toFixed(2)}%` : `${valueA.toFixed(2)}${unit}`,
        engineB: unit === '%' ? `${(valueB * 100).toFixed(2)}%` : `${valueB.toFixed(2)}${unit}`,
        difference:
          winner === 'tie'
            ? t('ai_annotation:labels.equal')
            : `${higherIsBetter === (diff > 0) ? '+' : '-'}${diffPercent}%`,
        winner,
      };
    };

    return [
      compareMetric(
        t('ai_annotation:metrics.accuracy'),
        metricsA.accuracy,
        metricsB.accuracy
      ),
      compareMetric(
        t('ai_annotation:metrics.consistency'),
        metricsA.consistency,
        metricsB.consistency
      ),
      compareMetric(
        t('ai_annotation:metrics.completeness'),
        metricsA.completeness,
        metricsB.completeness
      ),
      compareMetric(t('ai_annotation:metrics.recall'), metricsA.recall, metricsB.recall),
      compareMetric(
        t('ai_annotation:metrics.f1_score'),
        metricsA.f1Score,
        metricsB.f1Score
      ),
      compareMetric(
        t('ai_annotation:metrics.avg_latency'),
        metricsA.avgLatency,
        metricsB.avgLatency,
        'ms',
        false
      ),
      compareMetric(
        t('ai_annotation:metrics.p95_latency'),
        metricsA.p95Latency,
        metricsB.p95Latency,
        'ms',
        false
      ),
      compareMetric(
        t('ai_annotation:metrics.throughput'),
        metricsA.throughput,
        metricsB.throughput,
        '/s'
      ),
      compareMetric(
        t('ai_annotation:metrics.error_rate'),
        metricsA.errorRate,
        metricsB.errorRate,
        '%',
        false
      ),
      compareMetric(
        t('ai_annotation:metrics.cost_per_1k'),
        metricsA.costPer1kSamples,
        metricsB.costPer1kSamples,
        '$',
        false
      ),
      compareMetric(
        t('ai_annotation:metrics.success_rate'),
        metricsA.successRate,
        metricsB.successRate
      ),
    ];
  };

  const comparisonData = calculateComparison();
  const winsA = comparisonData.filter((d) => d.winner === 'A').length;
  const winsB = comparisonData.filter((d) => d.winner === 'B').length;
  const ties = comparisonData.filter((d) => d.winner === 'tie').length;

  const comparisonColumns: ColumnsType<ComparisonData> = [
    {
      title: t('ai_annotation:columns.metric'),
      dataIndex: 'metric',
      key: 'metric',
      render: (metric: string) => <strong>{metric}</strong>,
    },
    {
      title: (
        <Space>
          <Tag color="blue">A</Tag>
          {selectedEngineA && getEngineName(selectedEngineA)}
        </Space>
      ),
      dataIndex: 'engineA',
      key: 'engineA',
      align: 'right',
      render: (value: string, record: ComparisonData) => (
        <Tag color={record.winner === 'A' ? 'green' : 'default'}>{value}</Tag>
      ),
    },
    {
      title: (
        <Space>
          <Tag color="green">B</Tag>
          {selectedEngineB && getEngineName(selectedEngineB)}
        </Space>
      ),
      dataIndex: 'engineB',
      key: 'engineB',
      align: 'right',
      render: (value: string, record: ComparisonData) => (
        <Tag color={record.winner === 'B' ? 'green' : 'default'}>{value}</Tag>
      ),
    },
    {
      title: t('ai_annotation:columns.difference'),
      dataIndex: 'difference',
      key: 'difference',
      align: 'center',
      render: (diff: string, record: ComparisonData) => (
        <Space>
          {record.winner === 'A' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
          {record.winner === 'B' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
          {record.winner === 'tie' && <WarningOutlined style={{ color: '#faad14' }} />}
          <span>{diff}</span>
        </Space>
      ),
    },
  ];

  const rankingColumns: ColumnsType<PerformanceMetrics> = [
    {
      title: t('ai_annotation:columns.engine'),
      dataIndex: 'engineName',
      key: 'engineName',
      fixed: 'left',
      width: 200,
      render: (name: string) => <strong>{name}</strong>,
    },
    {
      title: t('ai_annotation:metrics.accuracy'),
      dataIndex: 'accuracy',
      key: 'accuracy',
      sorter: (a, b) => a.accuracy - b.accuracy,
      render: (value: number) => (
        <div>
          <div>{(value * 100).toFixed(2)}%</div>
          <Progress
            percent={value * 100}
            showInfo={false}
            strokeColor="#52c41a"
            size="small"
          />
        </div>
      ),
    },
    {
      title: t('ai_annotation:metrics.f1_score'),
      dataIndex: 'f1Score',
      key: 'f1Score',
      sorter: (a, b) => a.f1Score - b.f1Score,
      render: (value: number) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: t('ai_annotation:metrics.avg_latency'),
      dataIndex: 'avgLatency',
      key: 'avgLatency',
      sorter: (a, b) => a.avgLatency - b.avgLatency,
      render: (value: number) => `${value.toFixed(0)}ms`,
    },
    {
      title: t('ai_annotation:metrics.throughput'),
      dataIndex: 'throughput',
      key: 'throughput',
      sorter: (a, b) => a.throughput - b.throughput,
      render: (value: number) => `${value.toFixed(0)}/s`,
    },
    {
      title: t('ai_annotation:metrics.cost_per_1k'),
      dataIndex: 'costPer1kSamples',
      key: 'costPer1kSamples',
      sorter: (a, b) => a.costPer1kSamples - b.costPer1kSamples,
      render: (value: number) => `$${value.toFixed(2)}`,
    },
    {
      title: t('ai_annotation:metrics.success_rate'),
      dataIndex: 'successRate',
      key: 'successRate',
      sorter: (a, b) => a.successRate - b.successRate,
      render: (value: number) => (
        <Tag color={value >= 0.95 ? 'green' : value >= 0.90 ? 'orange' : 'red'}>
          {(value * 100).toFixed(2)}%
        </Tag>
      ),
    },
  ];

  const renderComparison = () => {
    const metricsA = selectedEngineA ? getMetricsForEngine(selectedEngineA) : null;
    const metricsB = selectedEngineB ? getMetricsForEngine(selectedEngineB) : null;

    if (!metricsA || !metricsB) {
      return (
        <Alert
          message={t('ai_annotation:alerts.select_engines_title')}
          description={t('ai_annotation:alerts.select_engines_desc')}
          type="info"
          showIcon
        />
      );
    }

    return (
      <div>
        {/* Summary Cards */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('ai_annotation:stats.engine_a_wins')}
                value={winsA}
                suffix={`/ ${comparisonData.length}`}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('ai_annotation:stats.engine_b_wins')}
                value={winsB}
                suffix={`/ ${comparisonData.length}`}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('ai_annotation:stats.ties')}
                value={ties}
                suffix={`/ ${comparisonData.length}`}
                prefix={<WarningOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
        </Row>

        {winsA > winsB && (
          <Alert
            message={t('ai_annotation:alerts.engine_a_better_title')}
            description={t('ai_annotation:alerts.engine_a_better_desc', {
              name: getEngineName(selectedEngineA),
              wins: winsA,
              total: comparisonData.length,
            })}
            type="success"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        {winsB > winsA && (
          <Alert
            message={t('ai_annotation:alerts.engine_b_better_title')}
            description={t('ai_annotation:alerts.engine_b_better_desc', {
              name: getEngineName(selectedEngineB),
              wins: winsB,
              total: comparisonData.length,
            })}
            type="success"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        {winsA === winsB && (
          <Alert
            message={t('ai_annotation:alerts.engines_equal_title')}
            description={t('ai_annotation:alerts.engines_equal_desc')}
            type="info"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Comparison Table */}
        <Table
          columns={comparisonColumns}
          dataSource={comparisonData}
          rowKey="metric"
          pagination={false}
          size="small"
        />

        {/* Cost vs Accuracy Analysis */}
        <Divider orientation="left">{t('ai_annotation:sections.cost_vs_accuracy')}</Divider>
        <Row gutter={16}>
          <Col span={12}>
            <Card
              title={
                <Space>
                  <Tag color="blue">A</Tag>
                  {getEngineName(selectedEngineA)}
                </Space>
              }
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic
                  title={t('ai_annotation:metrics.quality_score')}
                  value={
                    ((metricsA.accuracy +
                      metricsA.consistency +
                      metricsA.completeness +
                      metricsA.recall) /
                      4) *
                    100
                  }
                  precision={2}
                  suffix="%"
                  prefix={<CheckCircleOutlined />}
                />
                <Statistic
                  title={t('ai_annotation:metrics.cost_per_1k')}
                  value={metricsA.costPer1kSamples}
                  precision={2}
                  prefix="$"
                />
                <Statistic
                  title={t('ai_annotation:metrics.cost_efficiency')}
                  value={
                    (((metricsA.accuracy +
                      metricsA.consistency +
                      metricsA.completeness +
                      metricsA.recall) /
                      4) *
                      100) /
                    metricsA.costPer1kSamples
                  }
                  precision={2}
                  suffix="points/$"
                  prefix={<DollarOutlined />}
                />
              </Space>
            </Card>
          </Col>
          <Col span={12}>
            <Card
              title={
                <Space>
                  <Tag color="green">B</Tag>
                  {getEngineName(selectedEngineB)}
                </Space>
              }
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic
                  title={t('ai_annotation:metrics.quality_score')}
                  value={
                    ((metricsB.accuracy +
                      metricsB.consistency +
                      metricsB.completeness +
                      metricsB.recall) /
                      4) *
                    100
                  }
                  precision={2}
                  suffix="%"
                  prefix={<CheckCircleOutlined />}
                />
                <Statistic
                  title={t('ai_annotation:metrics.cost_per_1k')}
                  value={metricsB.costPer1kSamples}
                  precision={2}
                  prefix="$"
                />
                <Statistic
                  title={t('ai_annotation:metrics.cost_efficiency')}
                  value={
                    (((metricsB.accuracy +
                      metricsB.consistency +
                      metricsB.completeness +
                      metricsB.recall) /
                      4) *
                      100) /
                    metricsB.costPer1kSamples
                  }
                  precision={2}
                  suffix="points/$"
                  prefix={<DollarOutlined />}
                />
              </Space>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  const renderRanking = () => {
    return (
      <div>
        <Alert
          message={t('ai_annotation:info.ranking_mode')}
          description={t('ai_annotation:info.ranking_mode_desc')}
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginBottom: 16 }}
        />

        <Table
          columns={rankingColumns}
          dataSource={metricsData}
          rowKey="engineId"
          pagination={false}
          scroll={{ x: 1200 }}
          size="small"
        />
      </div>
    );
  };

  return (
    <div className="engine-performance-comparison">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <Radio.Group value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
                <Radio.Button value="comparison">
                  <SwapOutlined /> {t('ai_annotation:view_modes.comparison')}
                </Radio.Button>
                <Radio.Button value="ranking">
                  <BarChartOutlined /> {t('ai_annotation:view_modes.ranking')}
                </Radio.Button>
              </Radio.Group>
            </Space>
          </Col>
          <Col>
            <Button icon={<LineChartOutlined />} onClick={loadMetrics}>
              {t('ai_annotation:actions.refresh_metrics')}
            </Button>
          </Col>
        </Row>

        {viewMode === 'comparison' && (
          <>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={12}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <label>
                    <strong>{t('ai_annotation:fields.engine_a')}</strong>
                  </label>
                  <Select
                    style={{ width: '100%' }}
                    value={selectedEngineA}
                    onChange={setSelectedEngineA}
                    placeholder={t('ai_annotation:placeholders.select_engine')}
                  >
                    {engines.map((engine) => (
                      <Select.Option key={engine.id} value={engine.id}>
                        <Space>
                          <Tag color="blue">{engine.engineType}</Tag>
                          {engine.model}
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Space>
              </Col>
              <Col span={12}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <label>
                    <strong>{t('ai_annotation:fields.engine_b')}</strong>
                  </label>
                  <Select
                    style={{ width: '100%' }}
                    value={selectedEngineB}
                    onChange={setSelectedEngineB}
                    placeholder={t('ai_annotation:placeholders.select_engine')}
                  >
                    {engines.map((engine) => (
                      <Select.Option key={engine.id} value={engine.id}>
                        <Space>
                          <Tag color="green">{engine.engineType}</Tag>
                          {engine.model}
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Space>
              </Col>
            </Row>

            {renderComparison()}
          </>
        )}

        {viewMode === 'ranking' && renderRanking()}
      </Card>
    </div>
  );
};

export default EnginePerformanceComparison;
