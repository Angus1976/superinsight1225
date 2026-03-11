/**
 * StorageIndicator — 存储指示器组件
 *
 * Displays the primary_storage type of the currently selected strategy.
 * Reads candidates, selectedStrategy, and mode from toolkitStore.
 */

import React from 'react';
import { Tag, Space, Typography } from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useToolkitStore } from '@/stores/toolkitStore';
import type { StrategyCandidate } from '@/types/toolkit';

const { Text } = Typography;

/** Map storage type to tag color */
const getStorageColor = (storage: string): string => {
  const colorMap: Record<string, string> = {
    postgresql: 'blue',
    vectordb: 'purple',
    graphdb: 'green',
    elasticsearch: 'orange',
  };
  return colorMap[storage.toLowerCase()] ?? 'default';
};

/** Resolve the active strategy from store state */
const resolveStrategy = (
  candidates: StrategyCandidate[],
  selectedStrategy: string | null,
  mode: 'auto' | 'manual',
): StrategyCandidate | undefined => {
  if (candidates.length === 0) return undefined;
  if (mode === 'auto') return candidates[0];
  return candidates.find((c) => c.name === selectedStrategy) ?? candidates[0];
};

const StorageIndicator: React.FC = () => {
  const { t } = useTranslation(['common', 'aiProcessing']);
  const { candidates, selectedStrategy, mode } = useToolkitStore();

  const strategy = resolveStrategy(candidates, selectedStrategy, mode);
  if (!strategy) return null;

  const storageKey = strategy.primaryStorage.toLowerCase();
  const storageLabel =
    t(`common:aiProcessing.storage.types.${storageKey}`, { defaultValue: '' }) ||
    strategy.primaryStorage;

  return (
    <Space size={8} align="center">
      <DatabaseOutlined style={{ color: '#8c8c8c' }} />
      <Text type="secondary">
        {t('common:aiProcessing.storage.label')}
      </Text>
      <Tag color={getStorageColor(strategy.primaryStorage)}>
        {storageLabel}
      </Tag>
    </Space>
  );
};

export default StorageIndicator;
