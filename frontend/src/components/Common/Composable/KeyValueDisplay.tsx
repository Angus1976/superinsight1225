/**
 * KeyValueDisplay Component
 * 
 * A reusable component for displaying key-value pairs
 * in various layouts (horizontal, vertical, grid).
 * 
 * @module components/Common/Composable/KeyValueDisplay
 * @version 1.0.0
 */

import React, { type ReactNode, memo, useMemo } from 'react';
import { Descriptions, Tooltip, Typography } from 'antd';
import { InfoCircleOutlined, CopyOutlined } from '@ant-design/icons';
import styles from './KeyValueDisplay.module.scss';

const { Text } = Typography;

/**
 * Key-value item interface
 */
export interface KeyValueItem {
  /** Unique key */
  key: string;
  /** Display label */
  label: string;
  /** Value to display */
  value: ReactNode;
  /** Tooltip for the label */
  tooltip?: string;
  /** Span columns (for grid layout) */
  span?: number;
  /** Hide this item */
  hidden?: boolean;
  /** Enable copy to clipboard */
  copyable?: boolean;
  /** Custom render for value */
  render?: (value: ReactNode) => ReactNode;
}

/**
 * KeyValueDisplay component props
 */
export interface KeyValueDisplayProps {
  /** Items to display */
  items: KeyValueItem[];
  /** Layout mode */
  layout?: 'horizontal' | 'vertical';
  /** Number of columns */
  column?: number | { xs?: number; sm?: number; md?: number; lg?: number; xl?: number; xxl?: number };
  /** Bordered style */
  bordered?: boolean;
  /** Size variant */
  size?: 'default' | 'middle' | 'small';
  /** Title */
  title?: ReactNode;
  /** Extra content */
  extra?: ReactNode;
  /** Custom class name */
  className?: string;
  /** Colon after label */
  colon?: boolean;
  /** Label style */
  labelStyle?: React.CSSProperties;
  /** Content style */
  contentStyle?: React.CSSProperties;
}

/**
 * KeyValueDisplay component for displaying key-value pairs
 */
export const KeyValueDisplay = memo(function KeyValueDisplay({
  items,
  layout = 'horizontal',
  column = 3,
  bordered = false,
  size = 'default',
  title,
  extra,
  className,
  colon = true,
  labelStyle,
  contentStyle,
}: KeyValueDisplayProps): React.ReactElement {
  // Filter visible items
  const visibleItems = useMemo(() => {
    return items.filter(item => !item.hidden);
  }, [items]);

  // Handle copy to clipboard
  const handleCopy = async (value: ReactNode) => {
    const textValue = typeof value === 'string' ? value : String(value);
    try {
      await navigator.clipboard.writeText(textValue);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Render label with optional tooltip
  const renderLabel = (item: KeyValueItem) => {
    const label = (
      <span className={styles.label}>
        {item.label}
        {item.tooltip && (
          <Tooltip title={item.tooltip}>
            <InfoCircleOutlined className={styles.tooltipIcon} />
          </Tooltip>
        )}
      </span>
    );
    return label;
  };

  // Render value with optional copy button
  const renderValue = (item: KeyValueItem) => {
    const value = item.render ? item.render(item.value) : item.value;

    if (item.copyable && typeof item.value === 'string') {
      return (
        <span className={styles.copyableValue}>
          {value}
          <CopyOutlined
            className={styles.copyIcon}
            onClick={() => handleCopy(item.value)}
          />
        </span>
      );
    }

    return value;
  };

  return (
    <div className={`${styles.keyValueDisplay} ${className || ''}`}>
      <Descriptions
        title={title}
        extra={extra}
        layout={layout}
        column={column}
        bordered={bordered}
        size={size}
        colon={colon}
        labelStyle={labelStyle}
        contentStyle={contentStyle}
      >
        {visibleItems.map(item => (
          <Descriptions.Item
            key={item.key}
            label={renderLabel(item)}
            span={item.span}
          >
            {renderValue(item)}
          </Descriptions.Item>
        ))}
      </Descriptions>
    </div>
  );
});
