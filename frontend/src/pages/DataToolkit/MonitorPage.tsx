import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Space, Tag, Descriptions } from 'antd';
import {
  PauseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { ToolkitPageLayout, StageProgress } from '@/components/DataToolkit';

type ExecutionStatus = 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';

const STATUS_COLORS: Record<ExecutionStatus, string> = {
  running: 'processing',
  paused: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
};

const STAGE_KEYS = ['stage.parse', 'stage.clean', 'stage.transform', 'stage.store'];

const formatElapsed = (seconds: number): string => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
};

const getStageStatus = (
  stageIndex: number,
  progress: number,
): 'wait' | 'process' | 'finish' => {
  const threshold = (stageIndex + 1) * 25;
  const start = stageIndex * 25;
  if (progress >= threshold) return 'finish';
  if (progress > start) return 'process';
  return 'wait';
};

export const MonitorPage: React.FC = () => {
  const { t } = useTranslation('dataToolkit');
  const [status, setStatus] = useState<ExecutionStatus>('running');
  const [progress, setProgress] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  const currentStage = Math.min(Math.floor(progress / 25), 3);

  useEffect(() => {
    if (status !== 'running') return;
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          setStatus('completed');
          return 100;
        }
        return prev + 2;
      });
      setElapsed((prev) => prev + 1);
    }, 500);
    return () => clearInterval(timer);
  }, [status]);

  const stages = STAGE_KEYS.map((key, i) => ({
    name: t(key),
    status: getStageStatus(i, progress),
  }));

  const handlePause = useCallback(() => setStatus('paused'), []);
  const handleResume = useCallback(() => setStatus('running'), []);
  const handleCancel = useCallback(() => {
    setStatus('cancelled');
    setProgress(0);
  }, []);

  const isActive = status === 'running' || status === 'paused';

  return (
    <ToolkitPageLayout titleKey="monitor.title">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card title={t('monitor.progress')}>
          <StageProgress
            stages={stages}
            currentStage={currentStage}
            overallProgress={progress}
          />
        </Card>

        <Card title={t('monitor.status')}>
          <Descriptions column={3} size="small">
            <Descriptions.Item label={t('monitor.status')}>
              <Tag color={STATUS_COLORS[status]}>{t(`monitor.${status}`)}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('monitor.elapsed')}>
              {formatElapsed(elapsed)}
            </Descriptions.Item>
            <Descriptions.Item label={t('monitor.stage')}>
              {stages[currentStage]?.name}
            </Descriptions.Item>
          </Descriptions>

          <div style={{ marginTop: 16 }}>
            <Space>
              {status === 'running' && (
                <Button icon={<PauseCircleOutlined />} onClick={handlePause}>
                  {t('monitor.pause')}
                </Button>
              )}
              {status === 'paused' && (
                <Button icon={<PlayCircleOutlined />} onClick={handleResume}>
                  {t('monitor.resume')}
                </Button>
              )}
              {isActive && (
                <Button danger icon={<StopOutlined />} onClick={handleCancel}>
                  {t('monitor.cancel')}
                </Button>
              )}
            </Space>
          </div>
        </Card>
      </Space>
    </ToolkitPageLayout>
  );
};
