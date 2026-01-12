/**
 * StatCard Component
 * 
 * Consistent statistics card for displaying metrics.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Card, Typography, Space, Progress } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
import styles from './StatCard.module.scss';

const { Text, Title } = Typography;

type TrendDirection = 'up' | 'down' | 'neutral';
type StatusType = 'success' | 'warning' | 'error' | 'default';

interface StatCardProps {
  title: string;
  value: string | number;
  suffix?: string;
  prefix?: ReactNode;
  icon?: ReactNode;
  description?: string;
  trend?: {
    value: number;
    direction: TrendDirection;
    label?: string;
  };
  progress?: {
    value: number;
    target?: number;
    showInfo?: boolean;
  };
  status?: StatusType;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
  color?: string;
}

const getTrendIcon = (direction: TrendDirection) => {
  switch (direction) {
    case 'up':
      return <ArrowUpOutlined />;
    case 'down':
      return <ArrowDownOutlined />;
    default:
      return <MinusOutlined />;
  }
};

const getTrendColor = (direction: TrendDirection, isPositive: boolean = true) => {
  if (direction === 'neutral') return '#8c8c8c';
  if (direction === 'up') return isPositive ? '#52c41a' : '#ff4d4f';
  return isPositive ? '#ff4d4f' : '#52c41a';
};

const getStatusColor = (status: StatusType) => {
  switch (status) {
    case 'success':
      return '#52c41a';
    case 'warning':
      return '#faad14';
    case 'error':
      return '#ff4d4f';
    default:
      return '#1890ff';
  }
};

export const StatCard = memo<StatCardProps>(({
  title,
  value,
  suffix,
  prefix,
  icon,
  description,
  trend,
  progress,
  status = 'default',
  loading = false,
  onClick,
  className,
  color,
}) => {
  const statusColor = color || getStatusColor(status);
  
  return (
    <Card
      className={`${styles.statCard} ${onClick ? styles.clickable : ''} ${className || ''}`}
      loading={loading}
      onClick={onClick}
      bordered={false}
    >
      <div className={styles.cardContent}>
        <div className={styles.header}>
          <Text type="secondary" className={styles.title}>
            {title}
          </Text>
          {icon && (
            <div 
              className={styles.iconWrapper}
              style={{ backgroundColor: `${statusColor}15`, color: statusColor }}
            >
              {icon}
            </div>
          )}
        </div>
        
        <div className={styles.valueSection}>
          <Space size={4} align="baseline">
            {prefix && <span className={styles.prefix}>{prefix}</span>}
            <Title level={3} className={styles.value} style={{ color: statusColor }}>
              {value}
            </Title>
            {suffix && <Text type="secondary" className={styles.suffix}>{suffix}</Text>}
          </Space>
        </div>
        
        {trend && (
          <div className={styles.trendSection}>
            <Space size={4}>
              <span 
                className={styles.trendValue}
                style={{ color: getTrendColor(trend.direction) }}
              >
                {getTrendIcon(trend.direction)}
                <span>{Math.abs(trend.value)}%</span>
              </span>
              {trend.label && (
                <Text type="secondary" className={styles.trendLabel}>
                  {trend.label}
                </Text>
              )}
            </Space>
          </div>
        )}
        
        {progress && (
          <div className={styles.progressSection}>
            <Progress
              percent={progress.value}
              size="small"
              strokeColor={statusColor}
              showInfo={progress.showInfo !== false}
              format={(percent) => 
                progress.target 
                  ? `${percent}% / ${progress.target}%`
                  : `${percent}%`
              }
            />
          </div>
        )}
        
        {description && (
          <Text type="secondary" className={styles.description}>
            {description}
          </Text>
        )}
      </div>
    </Card>
  );
});

StatCard.displayName = 'StatCard';
