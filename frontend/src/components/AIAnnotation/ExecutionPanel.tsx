/**
 * ExecutionPanel — AI 标注实时执行面板
 *
 * Real-time progress via WebSocket, label/confidence distributions,
 * error details, and pause/resume controls.
 */

import React, { useEffect, useCallback, useRef } from 'react';
import {
  Card, Progress, Button, Space, Row, Col,
  Statistic, Alert, Tag, Table, Empty,
} from 'antd';
import {
  PauseCircleOutlined, PlayCircleOutlined, ReloadOutlined,
  ClockCircleOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { useExecutionStore } from '@/stores/executionStore';
import { createAnnotationWebSocket } from '@/services/aiAnnotationApi';
import type { ExecutionError } from '@/services/aiAnnotationApi';

interface ExecutionPanelProps {
  taskId: string;
}

const STATUS_COLOR: Record<string, string> = {
  running: 'green', paused: 'orange', completed: 'blue', error: 'red',
};

const formatTime = (seconds: number): string => {
  if (seconds <= 0) return '--';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
};

/** Render a list of { label/range, count } as Progress bars */
const DistributionBars: React.FC<{
  items: { key: string; label: string; count: number }[];
  color: string;
  emptyText: string;
}> = ({ items, color, emptyText }) => {
  if (items.length === 0) return <Empty description={emptyText} />;
  const total = items.reduce((s, i) => s + i.count, 0);
  return (
    <>
      {items.map((item) => (
        <div key={item.key} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span>{item.label}</span>
            <span>{item.count}</span>
          </div>
          <Progress percent={total > 0 ? Math.round((item.count / total) * 100) : 0} showInfo={false} strokeColor={color} />
        </div>
      ))}
    </>
  );
};

const ExecutionPanel: React.FC<ExecutionPanelProps> = ({ taskId }) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const wsRef = useRef<WebSocket | null>(null);
  const execution = useExecutionStore((s) => s.executions[taskId]);
  const startExecution = useExecutionStore((s) => s.startExecution);
  const pauseExecution = useExecutionStore((s) => s.pauseExecution);
  const updateProgress = useExecutionStore((s) => s.updateProgress);

  const handleMessage = useCallback(
    (data: unknown) => {
      if (data && typeof data === 'object') {
        updateProgress(taskId, data as Record<string, unknown>);
      }
    },
    [taskId, updateProgress],
  );

  useEffect(() => {
    if (!execution) startExecution(taskId);
    const ws = createAnnotationWebSocket(taskId, undefined, handleMessage);
    wsRef.current = ws;
    return () => { ws.close(); wsRef.current = null; };
  }, [taskId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePauseResume = useCallback(() => {
    if (!execution) return;
    execution.status === 'running' ? pauseExecution(taskId) : startExecution(taskId);
  }, [execution, taskId, pauseExecution, startExecution]);

  const handleRetry = useCallback(() => startExecution(taskId), [taskId, startExecution]);

  if (!execution) return <Empty description={t('ai_annotation:execution.no_data')} />;

  const { progress, processed, remaining, estimatedTime, status,
    labelDistribution, confidenceDistribution, errors } = execution;
  const progressStatus = status === 'error' ? 'exception' : status === 'completed' ? 'success' : 'active';
  const noDistData = t('ai_annotation:quality.no_distribution_data');

  const errorColumns: ColumnsType<ExecutionError> = [
    { title: t('ai_annotation:execution.error_code'), dataIndex: 'code', key: 'code', width: 120 },
    { title: t('ai_annotation:execution.error_message'), dataIndex: 'message', key: 'message', ellipsis: true },
    { title: t('ai_annotation:execution.error_time'), dataIndex: 'timestamp', key: 'timestamp', width: 180 },
    { title: t('ai_annotation:execution.error_item'), dataIndex: 'itemId', key: 'itemId', width: 120 },
  ];

  return (
    <div className="execution-panel">
      {/* Status bar + controls */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Tag color={STATUS_COLOR[status]}>{t(`ai_annotation:execution.status_${status}`)}</Tag>
            <Progress percent={Math.round(progress)} status={progressStatus} style={{ width: 300 }} />
          </Space>
          <Space>
            {(status === 'running' || status === 'paused') && (
              <Button
                icon={status === 'running' ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={handlePauseResume}
              >
                {t(`ai_annotation:execution.${status === 'running' ? 'pause' : 'resume'}`)}
              </Button>
            )}
            {status === 'error' && (
              <Button icon={<ReloadOutlined />} onClick={handleRetry}>
                {t('ai_annotation:execution.retry')}
              </Button>
            )}
          </Space>
        </Space>
      </Card>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card><Statistic title={t('ai_annotation:execution.processed')} value={processed}
            suffix={t('ai_annotation:execution.items')} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card><Statistic title={t('ai_annotation:execution.remaining')} value={remaining}
            suffix={t('ai_annotation:execution.items')} prefix={<ExclamationCircleOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card><Statistic title={t('ai_annotation:execution.estimated_time')}
            value={formatTime(estimatedTime)} prefix={<ClockCircleOutlined />} /></Card>
        </Col>
      </Row>

      {/* Distributions */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={t('ai_annotation:execution.label_distribution')} size="small">
            <DistributionBars
              items={labelDistribution.map((d) => ({ key: d.label, label: d.label, count: d.count }))}
              color="#1890ff" emptyText={noDistData}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t('ai_annotation:execution.confidence_distribution')} size="small">
            <DistributionBars
              items={confidenceDistribution.map((d) => ({ key: d.range, label: d.range, count: d.count }))}
              color="#52c41a" emptyText={noDistData}
            />
          </Card>
        </Col>
      </Row>

      {/* Errors */}
      {errors.length > 0 && (
        <Alert type="error" message={t('ai_annotation:execution.errors')} description={
          <Table dataSource={errors} columns={errorColumns}
            rowKey={(r) => `${r.code}-${r.timestamp}`} size="small" pagination={false} />
        } />
      )}
    </div>
  );
};

export default ExecutionPanel;
