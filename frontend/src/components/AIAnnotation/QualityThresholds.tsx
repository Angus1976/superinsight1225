/**
 * Quality Thresholds Component
 *
 * Provides quality threshold configuration and visualization:
 * - Threshold sliders for accuracy, consistency, completeness, recall
 * - Real-time quality metrics visualization
 * - Threshold impact analysis
 * - Historical performance comparison
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Slider,
  Select,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  Alert,
  Divider,
  Tag,
  Tooltip,
  Progress,
  message,
  Table,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  PercentageOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

import type { EngineConfig } from '@/pages/AIAnnotation/EngineConfiguration';

interface QualityThresholdsProps {
  engines: EngineConfig[];
  onSave: (config: EngineConfig) => Promise<void>;
  loading?: boolean;
}

interface QualityMetrics {
  accuracy: number;
  consistency: number;
  completeness: number;
  recall: number;
  f1Score: number;
  precision: number;
}

interface ThresholdImpact {
  metric: string;
  currentValue: number;
  threshold: number;
  status: 'pass' | 'warning' | 'fail';
  impact: string;
}

const QualityThresholds: React.FC<QualityThresholdsProps> = ({
  engines,
  onSave,
  loading = false,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [form] = Form.useForm();
  const [selectedEngine, setSelectedEngine] = useState<EngineConfig | null>(null);
  const [currentMetrics, setCurrentMetrics] = useState<QualityMetrics>({
    accuracy: 0.87,
    consistency: 0.82,
    completeness: 0.91,
    recall: 0.78,
    f1Score: 0.84,
    precision: 0.89,
  });
  const [thresholds, setThresholds] = useState({
    accuracy: 0.85,
    consistency: 0.80,
    completeness: 0.90,
    recall: 0.75,
  });

  useEffect(() => {
    if (engines.length > 0) {
      setSelectedEngine(engines[0]);
      const engine = engines[0];
      setThresholds({
        accuracy: engine.qualityThresholds.accuracy,
        consistency: engine.qualityThresholds.consistency,
        completeness: engine.qualityThresholds.completeness,
        recall: engine.qualityThresholds.recall,
      });
      form.setFieldsValue(engine.qualityThresholds);
      loadMetrics(engine.id!);
    }
  }, [engines, form]);

  const loadMetrics = async (engineId: string) => {
    try {
      const response = await fetch(`/api/v1/annotation/engines/${engineId}/metrics`);
      if (!response.ok) return;
      const data = await response.json();
      setCurrentMetrics(data.metrics || currentMetrics);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  };

  const handleEngineSelect = (engineId: string) => {
    const engine = engines.find((e) => e.id === engineId);
    if (engine) {
      setSelectedEngine(engine);
      setThresholds({
        accuracy: engine.qualityThresholds.accuracy,
        consistency: engine.qualityThresholds.consistency,
        completeness: engine.qualityThresholds.completeness,
        recall: engine.qualityThresholds.recall,
      });
      form.setFieldsValue(engine.qualityThresholds);
      loadMetrics(engineId);
    }
  };

  const handleThresholdChange = (metric: keyof typeof thresholds, value: number) => {
    setThresholds((prev) => ({
      ...prev,
      [metric]: value,
    }));
  };

  const handleSave = async () => {
    try {
      if (!selectedEngine) {
        message.error(t('ai_annotation:errors.no_engine_selected'));
        return;
      }

      const values = await form.validateFields();
      const updatedConfig: EngineConfig = {
        ...selectedEngine,
        qualityThresholds: values,
      };

      await onSave(updatedConfig);
      message.success(t('ai_annotation:messages.thresholds_saved'));
    } catch (error) {
      console.error('Failed to save thresholds:', error);
    }
  };

  const getMetricStatus = (
    value: number,
    threshold: number
  ): 'pass' | 'warning' | 'fail' => {
    if (value >= threshold) return 'pass';
    if (value >= threshold * 0.9) return 'warning';
    return 'fail';
  };

  const getStatusColor = (status: 'pass' | 'warning' | 'fail'): string => {
    switch (status) {
      case 'pass':
        return '#52c41a';
      case 'warning':
        return '#faad14';
      case 'fail':
        return '#ff4d4f';
    }
  };

  const getStatusIcon = (status: 'pass' | 'warning' | 'fail') => {
    switch (status) {
      case 'pass':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'fail':
        return <WarningOutlined style={{ color: '#ff4d4f' }} />;
    }
  };

  const calculateImpact = (): ThresholdImpact[] => {
    return [
      {
        metric: t('ai_annotation:metrics.accuracy'),
        currentValue: currentMetrics.accuracy,
        threshold: thresholds.accuracy,
        status: getMetricStatus(currentMetrics.accuracy, thresholds.accuracy),
        impact:
          currentMetrics.accuracy >= thresholds.accuracy
            ? t('ai_annotation:impact.meeting_expectations')
            : t('ai_annotation:impact.needs_improvement'),
      },
      {
        metric: t('ai_annotation:metrics.consistency'),
        currentValue: currentMetrics.consistency,
        threshold: thresholds.consistency,
        status: getMetricStatus(currentMetrics.consistency, thresholds.consistency),
        impact:
          currentMetrics.consistency >= thresholds.consistency
            ? t('ai_annotation:impact.meeting_expectations')
            : t('ai_annotation:impact.needs_improvement'),
      },
      {
        metric: t('ai_annotation:metrics.completeness'),
        currentValue: currentMetrics.completeness,
        threshold: thresholds.completeness,
        status: getMetricStatus(currentMetrics.completeness, thresholds.completeness),
        impact:
          currentMetrics.completeness >= thresholds.completeness
            ? t('ai_annotation:impact.meeting_expectations')
            : t('ai_annotation:impact.needs_improvement'),
      },
      {
        metric: t('ai_annotation:metrics.recall'),
        currentValue: currentMetrics.recall,
        threshold: thresholds.recall,
        status: getMetricStatus(currentMetrics.recall, thresholds.recall),
        impact:
          currentMetrics.recall >= thresholds.recall
            ? t('ai_annotation:impact.meeting_expectations')
            : t('ai_annotation:impact.needs_improvement'),
      },
    ];
  };

  const impactData = calculateImpact();
  const passCount = impactData.filter((i) => i.status === 'pass').length;
  const warningCount = impactData.filter((i) => i.status === 'warning').length;
  const failCount = impactData.filter((i) => i.status === 'fail').length;

  const impactColumns: ColumnsType<ThresholdImpact> = [
    {
      title: t('ai_annotation:columns.metric'),
      dataIndex: 'metric',
      key: 'metric',
      render: (metric: string) => <strong>{metric}</strong>,
    },
    {
      title: t('ai_annotation:columns.current_value'),
      dataIndex: 'currentValue',
      key: 'currentValue',
      render: (value: number) => (
        <Tag color="blue">{(value * 100).toFixed(1)}%</Tag>
      ),
    },
    {
      title: t('ai_annotation:columns.threshold'),
      dataIndex: 'threshold',
      key: 'threshold',
      render: (value: number) => `${(value * 100).toFixed(0)}%`,
    },
    {
      title: t('ai_annotation:columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: 'pass' | 'warning' | 'fail') => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>
            {t(`ai_annotation:status.${status}`)}
          </Tag>
        </Space>
      ),
    },
    {
      title: t('ai_annotation:columns.impact'),
      dataIndex: 'impact',
      key: 'impact',
    },
  ];

  const renderMetricSlider = (
    name: keyof typeof thresholds,
    label: string,
    tooltip: string
  ) => {
    const currentValue = currentMetrics[name];
    const threshold = thresholds[name];
    const status = getMetricStatus(currentValue, threshold);

    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={6}>
            <strong>{label}</strong>
            <div style={{ fontSize: 12, color: '#999' }}>
              <Tooltip title={tooltip}>
                <InfoCircleOutlined style={{ marginRight: 4 }} />
              </Tooltip>
              {tooltip}
            </div>
          </Col>
          <Col span={12}>
            <Form.Item
              name={name}
              noStyle
              rules={[{ required: true, type: 'number', min: 0, max: 1 }]}
            >
              <Slider
                min={0}
                max={1}
                step={0.05}
                marks={{
                  0: '0%',
                  0.5: '50%',
                  1: '100%',
                }}
                tooltip={{
                  formatter: (value) => `${((value || 0) * 100).toFixed(0)}%`,
                }}
                onChange={(value) => handleThresholdChange(name, value)}
              />
            </Form.Item>
          </Col>
          <Col span={6}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div>
                <Space>
                  {getStatusIcon(status)}
                  <span style={{ fontSize: 12 }}>
                    {t('ai_annotation:labels.current')}:{' '}
                    <strong style={{ color: getStatusColor(status) }}>
                      {(currentValue * 100).toFixed(1)}%
                    </strong>
                  </span>
                </Space>
              </div>
              <Progress
                percent={currentValue * 100}
                strokeColor={getStatusColor(status)}
                showInfo={false}
                size="small"
              />
            </Space>
          </Col>
        </Row>
      </Card>
    );
  };

  return (
    <div className="quality-thresholds">
      <Row gutter={16}>
        <Col span={6}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined />
                {t('ai_annotation:sections.select_engine')}
              </Space>
            }
            size="small"
          >
            <Select
              style={{ width: '100%' }}
              value={selectedEngine?.id}
              onChange={handleEngineSelect}
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

            {selectedEngine && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Statistic
                    title={t('ai_annotation:stats.overall_quality')}
                    value={
                      ((currentMetrics.accuracy +
                        currentMetrics.consistency +
                        currentMetrics.completeness +
                        currentMetrics.recall) /
                        4) *
                      100
                    }
                    precision={1}
                    suffix="%"
                    valueStyle={{
                      color:
                        passCount === 4
                          ? '#52c41a'
                          : failCount > 0
                          ? '#ff4d4f'
                          : '#faad14',
                    }}
                  />
                </Space>
              </>
            )}
          </Card>

          <Card
            title={
              <Space>
                <LineChartOutlined />
                {t('ai_annotation:sections.quality_summary')}
              </Space>
            }
            size="small"
            style={{ marginTop: 16 }}
          >
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Statistic
                title={t('ai_annotation:stats.passing_metrics')}
                value={passCount}
                suffix={`/ ${impactData.length}`}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
              <Statistic
                title={t('ai_annotation:stats.warning_metrics')}
                value={warningCount}
                suffix={`/ ${impactData.length}`}
                prefix={<WarningOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
              <Statistic
                title={t('ai_annotation:stats.failing_metrics')}
                value={failCount}
                suffix={`/ ${impactData.length}`}
                prefix={<WarningOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Space>
          </Card>
        </Col>

        <Col span={18}>
          <Card
            title={
              <Space>
                <PercentageOutlined />
                {t('ai_annotation:sections.threshold_configuration')}
              </Space>
            }
            extra={
              <Button type="primary" onClick={handleSave} loading={loading}>
                {t('common:actions.save')}
              </Button>
            }
          >
            {failCount > 0 && (
              <Alert
                message={t('ai_annotation:alerts.quality_below_threshold_title')}
                description={t('ai_annotation:alerts.quality_below_threshold_desc', {
                  count: failCount,
                })}
                type="error"
                showIcon
                closable
                style={{ marginBottom: 16 }}
              />
            )}

            {warningCount > 0 && failCount === 0 && (
              <Alert
                message={t('ai_annotation:alerts.quality_warning_title')}
                description={t('ai_annotation:alerts.quality_warning_desc', {
                  count: warningCount,
                })}
                type="warning"
                showIcon
                closable
                style={{ marginBottom: 16 }}
              />
            )}

            {passCount === impactData.length && (
              <Alert
                message={t('ai_annotation:alerts.quality_excellent_title')}
                description={t('ai_annotation:alerts.quality_excellent_desc')}
                type="success"
                showIcon
                closable
                style={{ marginBottom: 16 }}
              />
            )}

            <Form form={form} layout="vertical">
              <Divider orientation="left">
                {t('ai_annotation:sections.core_metrics')}
              </Divider>

              {renderMetricSlider(
                'accuracy',
                t('ai_annotation:metrics.accuracy'),
                t('ai_annotation:tooltips.accuracy')
              )}

              {renderMetricSlider(
                'consistency',
                t('ai_annotation:metrics.consistency'),
                t('ai_annotation:tooltips.consistency')
              )}

              {renderMetricSlider(
                'completeness',
                t('ai_annotation:metrics.completeness'),
                t('ai_annotation:tooltips.completeness')
              )}

              {renderMetricSlider(
                'recall',
                t('ai_annotation:metrics.recall'),
                t('ai_annotation:tooltips.recall')
              )}

              <Divider orientation="left">
                {t('ai_annotation:sections.additional_metrics')}
              </Divider>

              <Row gutter={16}>
                <Col span={8}>
                  <Card size="small">
                    <Statistic
                      title={t('ai_annotation:metrics.f1_score')}
                      value={currentMetrics.f1Score * 100}
                      precision={1}
                      suffix="%"
                      prefix={<LineChartOutlined />}
                      valueStyle={{ fontSize: 20 }}
                    />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small">
                    <Statistic
                      title={t('ai_annotation:metrics.precision')}
                      value={currentMetrics.precision * 100}
                      precision={1}
                      suffix="%"
                      prefix={<PercentageOutlined />}
                      valueStyle={{ fontSize: 20 }}
                    />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small">
                    <Statistic
                      title={t('ai_annotation:metrics.recall')}
                      value={currentMetrics.recall * 100}
                      precision={1}
                      suffix="%"
                      prefix={<CheckCircleOutlined />}
                      valueStyle={{ fontSize: 20 }}
                    />
                  </Card>
                </Col>
              </Row>

              <Divider orientation="left">
                {t('ai_annotation:sections.threshold_impact_analysis')}
              </Divider>

              <Table
                columns={impactColumns}
                dataSource={impactData}
                rowKey="metric"
                pagination={false}
                size="small"
              />

              <Alert
                message={t('ai_annotation:info.threshold_recommendations')}
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    <li>{t('ai_annotation:info.accuracy_recommendation')}</li>
                    <li>{t('ai_annotation:info.consistency_recommendation')}</li>
                    <li>{t('ai_annotation:info.completeness_recommendation')}</li>
                    <li>{t('ai_annotation:info.recall_recommendation')}</li>
                  </ul>
                }
                type="info"
                showIcon
                icon={<InfoCircleOutlined />}
                style={{ marginTop: 16 }}
              />
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default QualityThresholds;
