/**
 * ProgressBar Component
 * 
 * A reusable progress bar component with various styles
 * and animation options.
 * 
 * @module components/Common/Composable/ProgressBar
 * @version 1.0.0
 */

import React, { memo, useMemo } from 'react';
import { Progress, Tooltip } from 'antd';
import type { ProgressProps as AntProgressProps } from 'antd';
import styles from './ProgressBar.module.scss';

/**
 * ProgressBar component props
 */
export interface ProgressBarProps {
  /** Progress percentage (0-100) */
  percent: number;
  /** Progress type */
  type?: 'line' | 'circle' | 'dashboard';
  /** Status */
  status?: 'success' | 'exception' | 'normal' | 'active';
  /** Show percentage text */
  showInfo?: boolean;
  /** Custom format for percentage text */
  format?: (percent: number) => React.ReactNode;
  /** Stroke color (can be gradient) */
  strokeColor?: string | { from: string; to: string } | { [key: string]: string };
  /** Trail color */
  trailColor?: string;
  /** Stroke width */
  strokeWidth?: number;
  /** Size (for circle/dashboard) */
  size?: number | 'small' | 'default';
  /** Width (for line) */
  width?: number | string;
  /** Steps mode */
  steps?: number;
  /** Custom class name */
  className?: string;
  /** Tooltip text */
  tooltip?: string;
  /** Success threshold */
  successThreshold?: number;
  /** Warning threshold */
  warningThreshold?: number;
  /** Animated */
  animated?: boolean;
  /** Label text */
  label?: string;
  /** Show label */
  showLabel?: boolean;
}

/**
 * ProgressBar component for displaying progress
 */
export const ProgressBar = memo(function ProgressBar({
  percent,
  type = 'line',
  status,
  showInfo = true,
  format,
  strokeColor,
  trailColor,
  strokeWidth,
  size = 'default',
  width,
  steps,
  className,
  tooltip,
  successThreshold = 100,
  warningThreshold = 50,
  animated = true,
  label,
  showLabel = false,
}: ProgressBarProps): React.ReactElement {
  // Determine status based on thresholds if not provided
  const computedStatus = useMemo(() => {
    if (status) return status;
    if (percent >= successThreshold) return 'success';
    if (percent < warningThreshold) return 'exception';
    return 'normal';
  }, [status, percent, successThreshold, warningThreshold]);

  // Determine stroke color based on status if not provided
  const computedStrokeColor = useMemo(() => {
    if (strokeColor) return strokeColor;
    
    // Gradient based on progress
    return {
      '0%': '#108ee9',
      '100%': '#87d068',
    };
  }, [strokeColor]);

  // Build progress props
  const progressProps: AntProgressProps = {
    percent,
    type,
    status: computedStatus,
    showInfo,
    format,
    strokeColor: computedStrokeColor,
    trailColor,
    strokeWidth,
    steps,
  };

  // Handle size
  if (type === 'circle' || type === 'dashboard') {
    if (typeof size === 'number') {
      progressProps.size = size;
    } else if (size === 'small') {
      progressProps.size = 80;
    }
  }

  // Render progress
  const progressElement = (
    <div 
      className={`${styles.progressBar} ${animated ? styles.animated : ''} ${className || ''}`}
      style={{ width: type === 'line' ? width : undefined }}
    >
      {showLabel && label && (
        <div className={styles.label}>{label}</div>
      )}
      <Progress {...progressProps} />
    </div>
  );

  // Wrap with tooltip if provided
  if (tooltip) {
    return (
      <Tooltip title={tooltip}>
        {progressElement}
      </Tooltip>
    );
  }

  return progressElement;
});

/**
 * MultiProgressBar for showing multiple progress values
 */
export interface MultiProgressItem {
  key: string;
  label: string;
  percent: number;
  color?: string;
}

export interface MultiProgressBarProps {
  items: MultiProgressItem[];
  showLabels?: boolean;
  className?: string;
}

export const MultiProgressBar = memo(function MultiProgressBar({
  items,
  showLabels = true,
  className,
}: MultiProgressBarProps): React.ReactElement {
  return (
    <div className={`${styles.multiProgressBar} ${className || ''}`}>
      {items.map(item => (
        <div key={item.key} className={styles.progressItem}>
          {showLabels && (
            <div className={styles.itemLabel}>
              <span>{item.label}</span>
              <span>{item.percent}%</span>
            </div>
          )}
          <Progress
            percent={item.percent}
            showInfo={false}
            strokeColor={item.color}
            size="small"
          />
        </div>
      ))}
    </div>
  );
});
