import React from 'react';
import { Descriptions } from 'antd';
import { useTranslation } from 'react-i18next';

interface CostDisplayProps {
  timeSeconds: number;
  memoryBytes: number;
  monetaryCost: number;
}

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};

const formatTime = (seconds: number): string => {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}min`;
  return `${(seconds / 3600).toFixed(1)}h`;
};

export const CostDisplay: React.FC<CostDisplayProps> = ({
  timeSeconds,
  memoryBytes,
  monetaryCost,
}) => {
  const { t } = useTranslation('dataToolkit');

  return (
    <Descriptions column={3} size="small" bordered>
      <Descriptions.Item label={t('strategy.estimatedTime')}>
        {formatTime(timeSeconds)}
      </Descriptions.Item>
      <Descriptions.Item label={t('strategy.estimatedMemory')}>
        {formatBytes(memoryBytes)}
      </Descriptions.Item>
      <Descriptions.Item label={t('strategy.monetaryCost')}>
        ${monetaryCost.toFixed(4)}
      </Descriptions.Item>
    </Descriptions>
  );
};
