/**
 * StatusBadge Component
 * 
 * Consistent status badge for displaying various states.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo } from 'react';
import { Tag, Badge, Space, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  MinusCircleOutlined,
  PauseCircleOutlined,
} from '@ant-design/icons';
import styles from './StatusBadge.module.scss';

type StatusType = 
  | 'success' 
  | 'error' 
  | 'warning' 
  | 'info' 
  | 'pending' 
  | 'processing' 
  | 'default'
  | 'paused'
  | 'cancelled';

type BadgeVariant = 'tag' | 'dot' | 'text';

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  variant?: BadgeVariant;
  size?: 'small' | 'default';
  tooltip?: string;
  showIcon?: boolean;
  className?: string;
}

const statusConfig: Record<StatusType, {
  color: string;
  icon: React.ReactNode;
  defaultLabel: string;
}> = {
  success: {
    color: '#52c41a',
    icon: <CheckCircleOutlined />,
    defaultLabel: '成功',
  },
  error: {
    color: '#ff4d4f',
    icon: <CloseCircleOutlined />,
    defaultLabel: '失败',
  },
  warning: {
    color: '#faad14',
    icon: <ExclamationCircleOutlined />,
    defaultLabel: '警告',
  },
  info: {
    color: '#1890ff',
    icon: <ExclamationCircleOutlined />,
    defaultLabel: '信息',
  },
  pending: {
    color: '#8c8c8c',
    icon: <ClockCircleOutlined />,
    defaultLabel: '待处理',
  },
  processing: {
    color: '#1890ff',
    icon: <SyncOutlined spin />,
    defaultLabel: '处理中',
  },
  default: {
    color: '#d9d9d9',
    icon: <MinusCircleOutlined />,
    defaultLabel: '默认',
  },
  paused: {
    color: '#faad14',
    icon: <PauseCircleOutlined />,
    defaultLabel: '已暂停',
  },
  cancelled: {
    color: '#8c8c8c',
    icon: <CloseCircleOutlined />,
    defaultLabel: '已取消',
  },
};

export const StatusBadge = memo<StatusBadgeProps>(({
  status,
  label,
  variant = 'tag',
  size = 'default',
  tooltip,
  showIcon = true,
  className,
}) => {
  const config = statusConfig[status] || statusConfig.default;
  const displayLabel = label || config.defaultLabel;
  
  const renderContent = () => {
    switch (variant) {
      case 'dot':
        return (
          <Badge
            status={status === 'processing' ? 'processing' : 'default'}
            color={config.color}
            text={displayLabel}
            className={`${styles.dotBadge} ${styles[size]} ${className || ''}`}
          />
        );
      
      case 'text':
        return (
          <Space size={4} className={`${styles.textBadge} ${styles[size]} ${className || ''}`}>
            {showIcon && (
              <span style={{ color: config.color }}>{config.icon}</span>
            )}
            <span style={{ color: config.color }}>{displayLabel}</span>
          </Space>
        );
      
      case 'tag':
      default:
        return (
          <Tag
            color={config.color}
            icon={showIcon ? config.icon : undefined}
            className={`${styles.tagBadge} ${styles[size]} ${className || ''}`}
          >
            {displayLabel}
          </Tag>
        );
    }
  };
  
  const content = renderContent();
  
  if (tooltip) {
    return <Tooltip title={tooltip}>{content}</Tooltip>;
  }
  
  return content;
});

StatusBadge.displayName = 'StatusBadge';

// Predefined status badges for common use cases
export const SuccessBadge = memo<Omit<StatusBadgeProps, 'status'>>(props => (
  <StatusBadge status="success" {...props} />
));
SuccessBadge.displayName = 'SuccessBadge';

export const ErrorBadge = memo<Omit<StatusBadgeProps, 'status'>>(props => (
  <StatusBadge status="error" {...props} />
));
ErrorBadge.displayName = 'ErrorBadge';

export const WarningBadge = memo<Omit<StatusBadgeProps, 'status'>>(props => (
  <StatusBadge status="warning" {...props} />
));
WarningBadge.displayName = 'WarningBadge';

export const PendingBadge = memo<Omit<StatusBadgeProps, 'status'>>(props => (
  <StatusBadge status="pending" {...props} />
));
PendingBadge.displayName = 'PendingBadge';

export const ProcessingBadge = memo<Omit<StatusBadgeProps, 'status'>>(props => (
  <StatusBadge status="processing" {...props} />
));
ProcessingBadge.displayName = 'ProcessingBadge';
