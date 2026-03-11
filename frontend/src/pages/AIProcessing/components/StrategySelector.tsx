/**
 * StrategySelector — 策略选择器组件
 *
 * Displays candidate strategies from evaluate_strategies() ranked by score.
 * In auto mode: highlights the top-ranked strategy.
 * In manual mode: allows clicking to select any strategy.
 */

import React from 'react';
import { Card, List, Tag, Typography, Space } from 'antd';
import { TrophyOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useToolkitStore } from '@/stores/toolkitStore';
import type { StrategyCandidate } from '@/types/toolkit';

const { Text, Paragraph } = Typography;

/** Format score as percentage string */
const formatScore = (score: number): string =>
  `${(score * 100).toFixed(0)}%`;

/** Determine tag color based on score value */
const getScoreColor = (score: number): string => {
  if (score >= 0.8) return 'green';
  if (score >= 0.5) return 'orange';
  return 'default';
};

const StrategySelector: React.FC = () => {
  const { t } = useTranslation(['common', 'aiProcessing']);
  const { candidates, mode, selectedStrategy, selectStrategy } = useToolkitStore();

  if (candidates.length === 0) return null;

  const isSelected = (name: string): boolean => {
    if (mode === 'auto') return name === candidates[0]?.name;
    return name === selectedStrategy;
  };

  const handleClick = (name: string): void => {
    if (mode === 'manual') selectStrategy(name);
  };

  const renderItem = (item: StrategyCandidate, index: number) => {
    const active = isSelected(item.name);
    const isTopRanked = index === 0;

    return (
      <List.Item
        onClick={() => handleClick(item.name)}
        style={{
          cursor: mode === 'manual' ? 'pointer' : 'default',
          border: active ? '1px solid #1890ff' : '1px solid #f0f0f0',
          borderRadius: 6,
          padding: '12px 16px',
          marginBottom: 8,
          background: active ? '#e6f7ff' : undefined,
          transition: 'all 0.2s',
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={4}>
          <Space>
            {isTopRanked && (
              <TrophyOutlined style={{ color: '#faad14' }} />
            )}
            <Text strong>{item.name}</Text>
            <Tag color={getScoreColor(item.score)}>
              {formatScore(item.score)}
            </Tag>
            {isTopRanked && (
              <Tag color="blue">
                {t('common:aiProcessing.strategy.recommended')}
              </Tag>
            )}
          </Space>
          <Paragraph
            type="secondary"
            style={{ margin: 0, fontSize: 13 }}
            ellipsis={{ rows: 2 }}
          >
            {item.explanation}
          </Paragraph>
        </Space>
      </List.Item>
    );
  };

  return (
    <Card
      size="small"
      title={t('common:aiProcessing.strategy.title')}
    >
      <List
        dataSource={candidates}
        renderItem={renderItem}
        size="small"
      />
      {mode === 'manual' && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {t('common:aiProcessing.strategy.manualHint')}
        </Text>
      )}
    </Card>
  );
};

export default StrategySelector;
