import React, { useState } from 'react';
import { Card, List, Tag, Button, Space, Switch, Typography } from 'antd';
import {
  FileOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { ToolkitPageLayout, CostDisplay } from '@/components/DataToolkit';

const { Text } = Typography;

interface PipelineStage {
  id: string;
  nameKey: string;
  enabled: boolean;
  icon: React.ReactNode;
}

const INITIAL_STAGES: PipelineStage[] = [
  { id: 'parse', nameKey: 'stage.parse', enabled: true, icon: <FileOutlined /> },
  { id: 'clean', nameKey: 'stage.clean', enabled: true, icon: <ThunderboltOutlined /> },
  { id: 'transform', nameKey: 'stage.transform', enabled: true, icon: <RobotOutlined /> },
  { id: 'store', nameKey: 'stage.store', enabled: true, icon: <DatabaseOutlined /> },
];

export const StrategyConfigPage: React.FC = () => {
  const { t } = useTranslation('dataToolkit');
  const [stages, setStages] = useState<PipelineStage[]>(INITIAL_STAGES);

  const toggleStage = (id: string) => {
    setStages(prev => prev.map(s => (s.id === id ? { ...s, enabled: !s.enabled } : s)));
  };

  const enabledCount = stages.filter(s => s.enabled).length;

  return (
    <ToolkitPageLayout titleKey="strategy.title" descriptionKey="strategy.explanation">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card title={t('strategy.estimatedCost')}>
          <CostDisplay
            timeSeconds={enabledCount * 15}
            memoryBytes={enabledCount * 256 * 1024 * 1024}
            monetaryCost={enabledCount * 0.005}
          />
        </Card>

        <Card title={t('strategy.stages')}>
          <List
            dataSource={stages}
            renderItem={(stage) => (
              <List.Item
                actions={[
                  <Switch
                    key="toggle"
                    checked={stage.enabled}
                    onChange={() => toggleStage(stage.id)}
                  />,
                ]}
              >
                <List.Item.Meta
                  avatar={stage.icon}
                  title={<Text delete={!stage.enabled}>{t(stage.nameKey)}</Text>}
                />
                <Tag color={stage.enabled ? 'green' : 'default'}>
                  {stage.enabled ? t('monitor.running') : t('monitor.cancelled')}
                </Tag>
              </List.Item>
            )}
          />
        </Card>

        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button>{t('common.back')}</Button>
            <Button type="primary">{t('strategy.confirm')}</Button>
          </Space>
        </div>
      </Space>
    </ToolkitPageLayout>
  );
};
