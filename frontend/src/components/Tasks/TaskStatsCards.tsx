/**
 * TaskStatsCards Component
 * Displays task statistics in a row of cards.
 * 
 * Extracted from TasksPage for reusability.
 */
import React, { memo } from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import {
  BarChartOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { TaskStats } from '@/types/task';

export interface TaskStatsCardsProps {
  stats: TaskStats;
}

const TaskStatsCardsComponent: React.FC<TaskStatsCardsProps> = ({ stats }) => {
  const { t } = useTranslation('tasks');

  return (
    <Row gutter={16} style={{ marginBottom: 16 }}>
      <Col span={6}>
        <Card>
          <Statistic
            title={t('totalTasks')}
            value={stats.total}
            prefix={<BarChartOutlined />}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title={t('inProgress')}
            value={stats.in_progress}
            prefix={<PlayCircleOutlined />}
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title={t('completed')}
            value={stats.completed}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title={t('overdue')}
            value={stats.overdue}
            prefix={<ExclamationCircleOutlined />}
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export const TaskStatsCards = memo(TaskStatsCardsComponent);
export default TaskStatsCards;
