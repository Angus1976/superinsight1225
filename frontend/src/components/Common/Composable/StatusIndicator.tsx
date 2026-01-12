/**
 * StatusIndicator Component
 * 
 * A reusable status indicator component for displaying
 * various states with consistent styling.
 * 
 * @module components/Common/Composable/StatusIndicator
 * @version 1.0.0
 */

import React, { memo, useMemo } from 'react';
import { Badge, Tooltip, Tag } from 'antd';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ExclamationCircleFilled,
  SyncOutlined,
  ClockCircleFilled,
  MinusCircleFilled,
  QuestionCircleFilled,
} from '@ant-design/icons';
import styles from './StatusIndicator.module.scss';

/**
 * Status type
 */
export type StatusType = 
  | 'success' 
  | 'error' 
  | 'warning' 
  | 'info' 
  | 'processing' 
  | 'pending' 
  | 'disabled' 
  | 'unknown'
  | 'default';

/**
 * StatusIndicator component props
 */
export interface StatusIndicatorProps {
  /** Status type */
  status: StatusType;
  /** Status text */
  text?: string;
  /** Tooltip text */
  tooltip?: string;
  /** Display variant */
  variant?: 'dot' | 'icon' | 'tag' | 'badge';
  /** Size */
  size?: 'small' | 'default' | 'large';
  /** Show text */
  showText?: boolean;
  /** Custom class name */
  className?: string;
  /** Pulsing animation for processing */
  pulse?: boolean;
  /** Custom icon */
  icon?: React.ReactNode;
  /** Custom color */
  color?: string;
}

/**
 * Status configuration
 */
const statusConfig: Record<StatusType, { color: string; icon: React.ReactNode; text: string }> = {
  success: { color: '#52c41a', icon: <CheckCircleFilled />, text: '成功' },
  error: { color: '#ff4d4f', icon: <CloseCircleFilled />, text: '失败' },
  warning: { color: '#faad14', icon: <ExclamationCircleFilled />, text: '警告' },
  info: { color: '#1890ff', icon: <ExclamationCircleFilled />, text: '信息' },
  processing: { color: '#1890ff', icon: <SyncOutlined spin />, text: '处理中' },
  pending: { color: '#faad14', icon: <ClockCircleFilled />, text: '待处理' },
  disabled: { color: '#d9d9d9', icon: <MinusCircleFilled />, text: '已禁用' },
  unknown: { color: '#d9d9d9', icon: <QuestionCircleFilled />, text: '未知' },
  default: { color: '#d9d9d9', icon: <MinusCircleFilled />, text: '-' },
};

/**
 * StatusIndicator component for displaying status
 */
export const StatusIndicator = memo(function StatusIndicator({
  status,
  text,
  tooltip,
  variant = 'dot',
  size = 'default',
  showText = true,
  className,
  pulse = false,
  icon,
  color,
}: StatusIndicatorProps): React.ReactElement {
  const config = statusConfig[status] || statusConfig.default;
  const displayColor = color || config.color;
  const displayIcon = icon || config.icon;
  const displayText = text || config.text;

  // Render content based on variant
  const content = useMemo(() => {
    switch (variant) {
      case 'dot':
        return (
          <span className={`${styles.dotIndicator} ${styles[size]} ${pulse ? styles.pulse : ''}`}>
            <span className={styles.dot} style={{ backgroundColor: displayColor }} />
            {showText && <span className={styles.text}>{displayText}</span>}
          </span>
        );

      case 'icon':
        return (
          <span className={`${styles.iconIndicator} ${styles[size]}`} style={{ color: displayColor }}>
            {displayIcon}
            {showText && <span className={styles.text}>{displayText}</span>}
          </span>
        );

      case 'tag':
        return (
          <Tag color={displayColor} className={`${styles.tagIndicator} ${styles[size]}`}>
            {displayIcon}
            {showText && <span className={styles.tagText}>{displayText}</span>}
          </Tag>
        );

      case 'badge':
        return (
          <Badge
            status={status === 'processing' ? 'processing' : status === 'success' ? 'success' : status === 'error' ? 'error' : status === 'warning' ? 'warning' : 'default'}
            text={showText ? displayText : undefined}
            className={`${styles.badgeIndicator} ${styles[size]}`}
          />
        );

      default:
        return null;
    }
  }, [variant, size, pulse, displayColor, displayIcon, displayText, showText, status]);

  // Wrap with tooltip if provided
  if (tooltip) {
    return (
      <Tooltip title={tooltip}>
        <span className={`${styles.statusIndicator} ${className || ''}`}>
          {content}
        </span>
      </Tooltip>
    );
  }

  return (
    <span className={`${styles.statusIndicator} ${className || ''}`}>
      {content}
    </span>
  );
});
