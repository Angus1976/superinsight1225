// Enhanced metric card component for enterprise dashboard
import { Card, Statistic, Tooltip, Badge, Progress } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  prefix?: ReactNode;
  trend?: number;
  trendLabel?: string;
  loading?: boolean;
  color?: string;
  icon?: ReactNode;
  // Enhanced features for enterprise dashboard
  subtitle?: string;
  target?: number;
  progress?: number;
  status?: 'normal' | 'warning' | 'error' | 'success';
  refreshable?: boolean;
  onRefresh?: () => void;
  lastUpdated?: Date;
  extra?: ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  suffix,
  prefix,
  trend,
  trendLabel,
  loading = false,
  color,
  icon,
  subtitle,
  target,
  progress,
  status = 'normal',
  refreshable = false,
  onRefresh,
  lastUpdated,
  extra,
}) => {
  const { t } = useTranslation('dashboard');

  const getTrendIcon = () => {
    if (trend === undefined || trend === 0) {
      return <MinusOutlined style={{ color: '#999' }} />;
    }
    if (trend > 0) {
      return <ArrowUpOutlined style={{ color: '#52c41a' }} />;
    }
    return <ArrowDownOutlined style={{ color: '#ff4d4f' }} />;
  };

  const getTrendColor = () => {
    if (trend === undefined || trend === 0) return '#999';
    return trend > 0 ? '#52c41a' : '#ff4d4f';
  };

  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return '#52c41a';
      case 'warning':
        return '#faad14';
      case 'error':
        return '#ff4d4f';
      default:
        return color || '#1890ff';
    }
  };

  const cardExtra = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {refreshable && (
        <Tooltip title={t('common.refresh')}>
          <ReloadOutlined
            style={{ cursor: 'pointer', color: '#999' }}
            onClick={onRefresh}
          />
        </Tooltip>
      )}
      {extra}
    </div>
  );

  return (
    <Badge.Ribbon
      text={status === 'error' ? t('common.error') : status === 'warning' ? t('common.warning') : undefined}
      color={status === 'error' ? 'red' : status === 'warning' ? 'orange' : undefined}
    >
      <Card loading={loading} extra={cardExtra}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ flex: 1 }}>
            <Statistic
              title={
                <div>
                  <div>{title}</div>
                  {subtitle && (
                    <div style={{ fontSize: '12px', color: '#999', marginTop: 2 }}>
                      {subtitle}
                    </div>
                  )}
                </div>
              }
              value={value}
              suffix={suffix}
              prefix={prefix}
              valueStyle={{ color: getStatusColor() }}
            />
            
            {/* Progress bar for targets */}
            {progress !== undefined && target !== undefined && (
              <div style={{ marginTop: 8 }}>
                <Progress
                  percent={Math.min((progress / target) * 100, 100)}
                  size="small"
                  strokeColor={getStatusColor()}
                  showInfo={false}
                />
                <div style={{ fontSize: '12px', color: '#999', marginTop: 2 }}>
                  {t('metrics.target')}: {target.toLocaleString()}{suffix}
                </div>
              </div>
            )}
          </div>
          
          {icon && (
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                backgroundColor: `${getStatusColor()}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 24,
                color: getStatusColor(),
              }}
            >
              {icon}
            </div>
          )}
        </div>
        
        {/* Trend and last updated info */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
          {trend !== undefined && (
            <Tooltip title={trendLabel}>
              <div style={{ color: getTrendColor(), fontSize: '12px' }}>
                {getTrendIcon()}
                <span style={{ marginLeft: 4 }}>
                  {Math.abs(trend).toFixed(1)}%
                </span>
              </div>
            </Tooltip>
          )}
          
          {lastUpdated && (
            <div style={{ fontSize: '12px', color: '#999' }}>
              {t('common.lastUpdated')}: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
      </Card>
    </Badge.Ribbon>
  );
};
