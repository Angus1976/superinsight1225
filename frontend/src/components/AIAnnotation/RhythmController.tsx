/**
 * RhythmController — 标注节奏与优先级控制面板
 *
 * Rate slider, concurrency input, priority rules table with up/down reorder,
 * add-rule form, and real-time status display. Syncs with rhythmStore and
 * backend via updateRhythmConfig / getRhythmStatus APIs + WebSocket.
 */
import React, { useEffect, useCallback, useState, useRef } from 'react';
import {
  Card, Slider, InputNumber, Table, Button, Select, Space, Statistic, Row, Col, message,
} from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { useRhythmStore } from '@/stores/rhythmStore';
import type { PriorityRule } from '@/services/aiAnnotationApi';
import {
  updateRhythmConfig, getRhythmStatus, createAnnotationWebSocket,
} from '@/services/aiAnnotationApi';

interface RhythmControllerProps {
  projectId: string;
}

const FIELD_OPTIONS: PriorityRule['field'][] = ['dataType', 'labelCategory'];

const RhythmController: React.FC<RhythmControllerProps> = ({ projectId }) => {
  const { t } = useTranslation(['ai_annotation']);
  const config = useRhythmStore((s) => s.config);
  const status = useRhythmStore((s) => s.status);
  const updateRate = useRhythmStore((s) => s.updateRate);
  const updatePriority = useRhythmStore((s) => s.updatePriority);

  const [newField, setNewField] = useState<PriorityRule['field']>('dataType');
  const [newValue, setNewValue] = useState('');
  const [newPriority, setNewPriority] = useState(5);
  const wsRef = useRef<WebSocket | null>(null);

  // Poll rhythm status every 5s
  useEffect(() => {
    const poll = () => {
      getRhythmStatus()
        .then((s) => useRhythmStore.setState({ status: s }))
        .catch(() => {/* ignore */});
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  // WebSocket for sending adjustments
  useEffect(() => {
    const ws = createAnnotationWebSocket(projectId);
    wsRef.current = ws;
    return () => { ws.close(); wsRef.current = null; };
  }, [projectId]);

  const syncConfig = useCallback(async (patch: Partial<typeof config>) => {
    const next = { ...config, ...patch };
    try {
      await updateRhythmConfig(next);
      wsRef.current?.send(JSON.stringify({ type: 'rhythm_update', ...next }));
    } catch {
      message.error(t('ai_annotation:rhythm.sync_failed'));
    }
  }, [config, t]);

  const handleRateChange = useCallback((v: number) => {
    updateRate(v);
    syncConfig({ ratePerMinute: v });
  }, [updateRate, syncConfig]);

  const handleConcurrencyChange = useCallback((v: number | null) => {
    const val = v ?? 1;
    useRhythmStore.setState((s) => ({ config: { ...s.config, concurrency: val } }));
    syncConfig({ concurrency: val });
  }, [syncConfig]);

  const moveRule = useCallback((idx: number, dir: -1 | 1) => {
    const rules = [...config.priorityRules];
    const target = idx + dir;
    if (target < 0 || target >= rules.length) return;
    [rules[idx], rules[target]] = [rules[target], rules[idx]];
    updatePriority(rules);
    syncConfig({ priorityRules: rules });
  }, [config.priorityRules, updatePriority, syncConfig]);

  const removeRule = useCallback((idx: number) => {
    const rules = config.priorityRules.filter((_, i) => i !== idx);
    updatePriority(rules);
    syncConfig({ priorityRules: rules });
  }, [config.priorityRules, updatePriority, syncConfig]);

  const addRule = useCallback(() => {
    if (!newValue.trim()) return;
    const rule: PriorityRule = { field: newField, value: newValue.trim(), priority: newPriority };
    const rules = [...config.priorityRules, rule];
    updatePriority(rules);
    syncConfig({ priorityRules: rules });
    setNewValue('');
    setNewPriority(5);
  }, [newField, newValue, newPriority, config.priorityRules, updatePriority, syncConfig]);

  const columns: ColumnsType<PriorityRule & { _idx: number }> = [
    { title: '#', dataIndex: '_idx', width: 50, render: (v: number) => v + 1 },
    { title: t('ai_annotation:rhythm.field'), dataIndex: 'field', width: 130 },
    { title: t('ai_annotation:rhythm.value'), dataIndex: 'value' },
    { title: t('ai_annotation:rhythm.priority'), dataIndex: 'priority', width: 80 },
    {
      title: t('ai_annotation:rhythm.actions'), width: 130, key: 'ops',
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<ArrowUpOutlined />} disabled={r._idx === 0}
            onClick={() => moveRule(r._idx, -1)} />
          <Button size="small" icon={<ArrowDownOutlined />}
            disabled={r._idx === config.priorityRules.length - 1}
            onClick={() => moveRule(r._idx, 1)} />
          <Button size="small" danger icon={<DeleteOutlined />}
            onClick={() => removeRule(r._idx)} />
        </Space>
      ),
    },
  ];

  const tableData = config.priorityRules.map((r, i) => ({ ...r, _idx: i }));

  return (
    <div className="rhythm-controller">
      {/* Rate & Concurrency */}
      <Card title={t('ai_annotation:rhythm.config_title')} size="small" style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col xs={24} sm={14}>
            <div style={{ marginBottom: 4 }}>
              {t('ai_annotation:rhythm.rate')}: {config.ratePerMinute} {t('ai_annotation:rhythm.items_per_min')}
            </div>
            <Slider min={1} max={500} value={config.ratePerMinute} onChange={handleRateChange} />
          </Col>
          <Col xs={24} sm={10}>
            <div style={{ marginBottom: 4 }}>{t('ai_annotation:rhythm.concurrency')}</div>
            <InputNumber min={1} max={32} value={config.concurrency}
              onChange={handleConcurrencyChange} style={{ width: '100%' }} />
          </Col>
        </Row>
      </Card>

      {/* Priority rules */}
      <Card title={t('ai_annotation:rhythm.priority_title')} size="small" style={{ marginBottom: 16 }}>
        <Table<PriorityRule & { _idx: number }>
          dataSource={tableData} columns={columns}
          rowKey="_idx" size="small" pagination={false}
        />
        <Space style={{ marginTop: 12 }} wrap>
          <Select value={newField} onChange={setNewField} style={{ width: 140 }}
            options={FIELD_OPTIONS.map((f) => ({ label: t(`ai_annotation:rhythm.field_${f}`), value: f }))} />
          <InputNumber
            placeholder={t('ai_annotation:rhythm.value')}
            value={newValue}
            onChange={(v) => setNewValue(String(v ?? ''))}
            style={{ width: 140 }}
            controls={false}
            stringMode
          />
          <InputNumber min={1} max={10} value={newPriority} onChange={(v) => setNewPriority(v ?? 5)}
            style={{ width: 80 }} />
          <Button icon={<PlusOutlined />} onClick={addRule}>{t('ai_annotation:rhythm.add_rule')}</Button>
        </Space>
      </Card>

      {/* Real-time status */}
      <Card title={t('ai_annotation:rhythm.status_title')} size="small">
        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Statistic title={t('ai_annotation:rhythm.current_rate')}
              value={status.currentRate} suffix={t('ai_annotation:rhythm.items_per_min')} />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic title={t('ai_annotation:rhythm.queue_depth')} value={status.queueDepth} />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic title={t('ai_annotation:rhythm.resource_usage')}
              value={status.resourceUsage} suffix="%" />
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default RhythmController;
