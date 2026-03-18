import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Spin, Empty, List, Typography } from 'antd';
import { MessageOutlined, ThunderboltOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getTodayStats } from '@/services/aiAssistantApi';
import type { TodayStats } from '@/types/aiAssistant';

const { Text } = Typography;

interface StatsPanelProps {
  userRole: string;
  refreshKey?: number;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ userRole, refreshKey = 0 }) => {
  const { t } = useTranslation('workflow');
  const [stats, setStats] = useState<TodayStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const loadStats = async () => {
      setLoading(true);
      try {
        const data = await getTodayStats();
        setStats(data);
      } catch (err) {
        console.error('Failed to load stats:', err);
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, [refreshKey]);

  if (loading) {
    return (
      <Card title={t('stats.title')} size="small">
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Spin />
        </div>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card title={t('stats.title')} size="small">
        <Empty description={t('stats.noData')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  return (
    <Card title={t('stats.title')} size="small">
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Statistic
            title={t('stats.chatCount')}
            value={stats.chat_count}
            prefix={<MessageOutlined />}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={t('stats.workflowCount')}
            value={stats.workflow_count}
            prefix={<ThunderboltOutlined />}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={t('stats.dataSourceCount')}
            value={stats.data_source_count}
            prefix={<DatabaseOutlined />}
          />
        </Col>
      </Row>
      {stats.details && (
        <div style={{ marginTop: 12 }}>
          <Text
            type="secondary"
            style={{ cursor: 'pointer', fontSize: 12 }}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '▼' : '▶'} {t('stats.viewDetails')}
          </Text>
          {expanded && stats.details.chats && (
            <List
              size="small"
              style={{ marginTop: 8 }}
              dataSource={stats.details.chats}
              renderItem={(item) => (
                <List.Item>
                  <Text style={{ fontSize: 12 }}>{item.name}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>{item.timestamp}</Text>
                </List.Item>
              )}
            />
          )}
        </div>
      )}
    </Card>
  );
};

export default StatsPanel;
