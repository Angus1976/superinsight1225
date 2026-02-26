/**
 * BatchExecutor — 渐进式批量执行器
 *
 * Batch config form, sequential batch execution via applyBatchCoverage + getQualityReport,
 * cumulative progress bar, quality trend table, auto-pause on low accuracy, and
 * between-batch config adjustment.
 */
import React, { useState, useCallback, useRef } from 'react';
import {
  Card, InputNumber, Slider, Switch, Button, Progress, Alert, Table, Space, message,
} from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { useBatchStore } from '@/stores/batchStore';
import type { BatchConfig, BatchResult } from '@/stores/batchStore';
import { applyBatchCoverage, getQualityReport } from '@/services/aiAnnotationApi';

interface BatchExecutorProps {
  projectId: string;
  totalItems: number;
  initialConfig?: Partial<BatchConfig>;
}

const BatchExecutor: React.FC<BatchExecutorProps> = ({ projectId, totalItems, initialConfig }) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const config = useBatchStore((s) => s.config);
  const progress = useBatchStore((s) => s.progress);
  const setConfig = useBatchStore((s) => s.setConfig);
  const addBatchResult = useBatchStore((s) => s.addBatchResult);

  const [loading, setLoading] = useState(false);
  const [autoPaused, setAutoPaused] = useState(false);
  const abortRef = useRef(false);
  const initializedRef = useRef(false);

  // Apply initialConfig once
  if (initialConfig && !initializedRef.current) {
    initializedRef.current = true;
    setConfig(initialConfig);
  }

  const totalBatches = Math.ceil(totalItems / config.batchSize) || 1;
  const processedCount = progress?.batchResults.reduce((s, r) => s + r.processedCount, 0) ?? 0;
  const progressPercent = totalItems > 0 ? Math.round((processedCount / totalItems) * 100) : 0;

  const runBatches = useCallback(async () => {
    setLoading(true);
    setAutoPaused(false);
    abortRef.current = false;

    const startIdx = progress?.batchResults.length ?? 0;

    for (let i = startIdx; i < totalBatches; i++) {
      if (abortRef.current) break;

      try {
        const batchSize = Math.min(config.batchSize, totalItems - i * config.batchSize);
        await applyBatchCoverage({
          project_id: projectId,
          document_ids: [],
          pattern_type: 'auto',
          min_confidence: config.qualityThreshold,
        });

        const report = await getQualityReport(projectId);
        const accuracy = report.accuracy_score ?? report.overall_score ?? 0;

        const result: BatchResult = {
          batchIndex: i,
          accuracy,
          processedCount: batchSize,
          status: 'completed',
        };
        addBatchResult(result);

        // Auto-pause check: batchStore.addBatchResult may override status to 'paused'
        if (config.autoStop && accuracy < config.qualityThreshold) {
          setAutoPaused(true);
          break;
        }

        // Wait interval between batches (skip after last)
        if (i < totalBatches - 1 && config.intervalSeconds > 0 && !abortRef.current) {
          await new Promise((r) => setTimeout(r, config.intervalSeconds * 1000));
        }
      } catch {
        addBatchResult({ batchIndex: i, accuracy: 0, processedCount: 0, status: 'failed' });
        message.error(t('ai_annotation:batch.batch_failed', { index: i + 1 }));
        break;
      }
    }
    setLoading(false);
  }, [projectId, totalItems, totalBatches, config, progress, addBatchResult, t]);

  const handleStop = useCallback(() => {
    abortRef.current = true;
  }, []);

  const batchResults = progress?.batchResults ?? [];

  const columns: ColumnsType<BatchResult> = [
    { title: t('ai_annotation:batch.batch_index'), dataIndex: 'batchIndex', key: 'idx', width: 80,
      render: (v: number) => v + 1 },
    { title: t('ai_annotation:batch.accuracy'), dataIndex: 'accuracy', key: 'acc', width: 120,
      render: (v: number) => {
        const below = v < config.qualityThreshold;
        return <span style={{ color: below ? '#ff4d4f' : '#52c41a' }}>{(v * 100).toFixed(1)}%</span>;
      } },
    { title: t('ai_annotation:batch.processed_count'), dataIndex: 'processedCount', key: 'cnt', width: 100 },
    { title: t('ai_annotation:batch.status'), dataIndex: 'status', key: 'st', width: 100 },
  ];

  return (
    <div className="batch-executor">
      {/* Config form */}
      <Card title={t('ai_annotation:batch.config_title')} size="small" style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <div>
            <div style={{ marginBottom: 4 }}>{t('ai_annotation:batch.batch_size')}</div>
            <InputNumber min={1} max={totalItems} value={config.batchSize} disabled={loading}
              onChange={(v) => setConfig({ batchSize: v ?? 100 })} style={{ width: 120 }} />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>{t('ai_annotation:batch.interval')}</div>
            <InputNumber min={0} max={600} value={config.intervalSeconds} disabled={loading}
              onChange={(v) => setConfig({ intervalSeconds: v ?? 30 })} style={{ width: 120 }}
              addonAfter="s" />
          </div>
          <div style={{ width: 220 }}>
            <div style={{ marginBottom: 4 }}>
              {t('ai_annotation:batch.quality_threshold')}: {(config.qualityThreshold * 100).toFixed(0)}%
            </div>
            <Slider min={0} max={1} step={0.05} value={config.qualityThreshold} disabled={loading}
              onChange={(v) => setConfig({ qualityThreshold: v })} />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>{t('ai_annotation:batch.auto_stop')}</div>
            <Switch checked={config.autoStop} disabled={loading}
              onChange={(v) => setConfig({ autoStop: v })} />
          </div>
        </Space>
      </Card>

      {/* Controls + progress */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Progress percent={progressPercent} style={{ width: 300 }} status={autoPaused ? 'exception' : 'active'} />
          <Space>
            {!loading && (
              <Button type="primary" icon={<PlayCircleOutlined />} onClick={runBatches}>
                {batchResults.length > 0 ? t('ai_annotation:batch.continue') : t('ai_annotation:batch.start')}
              </Button>
            )}
            {loading && (
              <Button icon={<PauseCircleOutlined />} onClick={handleStop}>
                {t('ai_annotation:batch.stop')}
              </Button>
            )}
          </Space>
        </Space>
        <div style={{ marginTop: 8, color: '#888' }}>
          {t('ai_annotation:batch.progress_summary', {
            current: batchResults.length,
            total: totalBatches,
            processed: processedCount,
            totalItems,
          })}
        </div>
      </Card>

      {/* Auto-pause alert */}
      {autoPaused && (
        <Alert type="warning" showIcon closable
          message={t('ai_annotation:batch.auto_paused')}
          description={t('ai_annotation:batch.auto_paused_desc')}
          style={{ marginBottom: 16 }} />
      )}

      {/* Quality trend table */}
      {batchResults.length > 0 && (
        <Card title={t('ai_annotation:batch.quality_trend')} size="small">
          <Table<BatchResult> dataSource={batchResults} columns={columns}
            rowKey="batchIndex" size="small" pagination={false} />
        </Card>
      )}
    </div>
  );
};

export default BatchExecutor;
