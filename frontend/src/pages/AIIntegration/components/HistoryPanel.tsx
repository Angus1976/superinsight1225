/**
 * History Panel - 历史面板
 * Displays execution history
 */

import React from 'react';
import { Card, List, Tag, Empty } from 'antd';
import { ClockCircleOutlined, DatabaseOutlined, FileTextOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { WorkflowExecutionResult } from '../../../services/aiIntegrationApi';

interface HistoryPanelProps {
  history: WorkflowExecutionResult[];
}

const HistoryPanel: React.FC<HistoryPanelProps> = ({ history }) => {
  const { t } = useTranslation('aiIntegration');

  const getQualityColor = (score: number) => {
    if (score >= 0.8) return 'green';
    if (score >= 0.6) return 'orange';
    return 'red';
  };

  return (
    <Card
      title={t('workflowPlayground.history.title')}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, overflowY: 'auto', padding: 16 }}
    >
      {history.length === 0 ? (
        <Empty description={t('workflowPlayground.history.empty')} />
      ) : (
        <List
          size="small"
          dataSource={history}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                avatar={
                  item.dataSource === 'governed' ? (
                    <DatabaseOutlined style={{ fontSize: 20, color: '#1890ff' }} />
                  ) : (
                    <FileTextOutlined style={{ fontSize: 20, color: '#52c41a' }} />
                  )
                }
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>
                      {item.dataSource === 'governed'
                        ? t('workflowPlayground.workflow.governed')
                        : t('workflowPlayground.workflow.raw')}
                    </span>
                    <Tag color={getQualityColor(item.qualityMetrics.overallScore)}>
                      {(item.qualityMetrics.overallScore * 100).toFixed(0)}%
                    </Tag>
                  </div>
                }
                description={
                  <div style={{ fontSize: 12, color: '#999' }}>
                    <ClockCircleOutlined /> {new Date(item.createdAt).toLocaleString()}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
};

export default HistoryPanel;
