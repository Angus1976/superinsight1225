/**
 * Results Panel - 结果面板
 * Displays execution results with quality metrics
 */

import React from 'react';
import { Card, Button, Space, Empty, Spin, Statistic, Row, Col, Progress, Tabs } from 'antd';
import { PlayCircleOutlined, SaveOutlined, ClockCircleOutlined, SwapOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { WorkflowExecutionResult } from '../../../services/aiIntegrationApi';

interface ResultsPanelProps {
  result: WorkflowExecutionResult | null;
  executing: boolean;
  comparing: boolean;
  comparisonResult: { governed: WorkflowExecutionResult; raw: WorkflowExecutionResult } | null;
  onExecute: () => void;
  onCompare: () => void;
  onSave: () => void;
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ 
  result, 
  executing, 
  comparing,
  comparisonResult,
  onExecute, 
  onCompare,
  onSave 
}) => {
  const { t } = useTranslation('aiIntegration');

  const getQualityColor = (score: number) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const renderMetrics = (execResult: WorkflowExecutionResult) => (
    <>
      <div style={{ marginBottom: 24 }}>
        <h4>{t('workflowPlayground.results.quality.title')}</h4>
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title={t('workflowPlayground.results.quality.completeness')}
                value={execResult.qualityMetrics.completeness * 100}
                precision={1}
                suffix="%"
                valueStyle={{ color: getQualityColor(execResult.qualityMetrics.completeness) }}
              />
              <Progress
                percent={execResult.qualityMetrics.completeness * 100}
                strokeColor={getQualityColor(execResult.qualityMetrics.completeness)}
                showInfo={false}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title={t('workflowPlayground.results.quality.accuracy')}
                value={execResult.qualityMetrics.accuracy * 100}
                precision={1}
                suffix="%"
                valueStyle={{ color: getQualityColor(execResult.qualityMetrics.accuracy) }}
              />
              <Progress
                percent={execResult.qualityMetrics.accuracy * 100}
                strokeColor={getQualityColor(execResult.qualityMetrics.accuracy)}
                showInfo={false}
              />
            </Card>
          </Col>
        </Row>
      </div>
      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Card size="small">
            <Statistic
              title={t('workflowPlayground.results.metrics.executionTime')}
              value={execResult.executionTime}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
          <Card size="small">
            <Statistic
              title={t('workflowPlayground.results.metrics.qualityScore')}
              value={execResult.qualityMetrics.overallScore * 100}
              precision={1}
              suffix="%"
              valueStyle={{ color: getQualityColor(execResult.qualityMetrics.overallScore) }}
            />
          </Card>
        </Space>
      </div>
    </>
  );

  return (
    <Card
      title={t('workflowPlayground.results.title')}
      extra={
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={onExecute}
            loading={executing}
          >
            {t('workflowPlayground.results.execute')}
          </Button>
          <Button
            icon={<SwapOutlined />}
            onClick={onCompare}
            loading={comparing}
          >
            {t('workflowPlayground.results.compare')}
          </Button>
          {result && (
            <Button icon={<SaveOutlined />} onClick={onSave}>
              {t('workflowPlayground.results.save')}
            </Button>
          )}
        </Space>
      }
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, overflowY: 'auto', padding: 16 }}
    >
      {executing && (
        <div style={{ textAlign: 'center', padding: 64 }}>
          <Spin size="large" tip={t('workflowPlayground.results.executing')} />
        </div>
      )}

      {!executing && !result && !comparisonResult && (
        <Empty
          description={t('workflowPlayground.results.noResults')}
          style={{ marginTop: 64 }}
        />
      )}

      {!executing && result && !comparisonResult && (
        <div>{renderMetrics(result)}</div>
      )}

      {!executing && comparisonResult && (
        <Tabs
          items={[
            {
              key: 'governed',
              label: t('workflowPlayground.workflow.governed'),
              children: renderMetrics(comparisonResult.governed),
            },
            {
              key: 'raw',
              label: t('workflowPlayground.workflow.raw'),
              children: renderMetrics(comparisonResult.raw),
            },
          ]}
        />
      )}
    </Card>
  );
};

export default ResultsPanel;
