/**
 * Collapsible Component
 * 
 * A reusable collapsible/accordion component with
 * smooth animations and customizable styling.
 * 
 * @module components/Common/Composable/Collapsible
 * @version 1.0.0
 */

import React, { useState, useCallback, memo, useMemo } from 'react';
import { Collapse, Space } from 'antd';
import { CaretRightOutlined, PlusOutlined, MinusOutlined } from '@ant-design/icons';
import type { CollapseProps } from 'antd';
import styles from './Collapsible.module.scss';

/**
 * Collapsible panel item
 */
export interface CollapsibleItem {
  /** Unique key */
  key: string;
  /** Panel header */
  header: React.ReactNode;
  /** Panel content */
  content: React.ReactNode;
  /** Extra content in header */
  extra?: React.ReactNode;
  /** Disabled state */
  disabled?: boolean;
  /** Show arrow */
  showArrow?: boolean;
  /** Force render content */
  forceRender?: boolean;
  /** Collapsible trigger area */
  collapsible?: 'header' | 'icon' | 'disabled';
}

/**
 * Collapsible component props
 */
export interface CollapsibleProps {
  /** Collapsible items */
  items: CollapsibleItem[];
  /** Active keys (controlled) */
  activeKey?: string | string[];
  /** Default active keys */
  defaultActiveKey?: string | string[];
  /** Change handler */
  onChange?: (key: string | string[]) => void;
  /** Accordion mode (only one panel open) */
  accordion?: boolean;
  /** Bordered style */
  bordered?: boolean;
  /** Ghost style (no background) */
  ghost?: boolean;
  /** Expand icon position */
  expandIconPosition?: 'start' | 'end';
  /** Custom expand icon */
  expandIcon?: (panelProps: { isActive?: boolean }) => React.ReactNode;
  /** Icon style */
  iconStyle?: 'arrow' | 'plus-minus' | 'none';
  /** Size */
  size?: 'large' | 'middle' | 'small';
  /** Custom class name */
  className?: string;
  /** Destroy inactive panels */
  destroyInactivePanel?: boolean;
}

/**
 * Collapsible component for expandable content
 */
export const Collapsible = memo(function Collapsible({
  items,
  activeKey,
  defaultActiveKey,
  onChange,
  accordion = false,
  bordered = true,
  ghost = false,
  expandIconPosition = 'start',
  expandIcon,
  iconStyle = 'arrow',
  size = 'middle',
  className,
  destroyInactivePanel = false,
}: CollapsibleProps): React.ReactElement {
  // Build expand icon
  const renderExpandIcon = useCallback(
    (panelProps: { isActive?: boolean }) => {
      if (expandIcon) {
        return expandIcon(panelProps);
      }

      switch (iconStyle) {
        case 'plus-minus':
          return panelProps.isActive ? <MinusOutlined /> : <PlusOutlined />;
        case 'none':
          return null;
        case 'arrow':
        default:
          return (
            <CaretRightOutlined
              rotate={panelProps.isActive ? 90 : 0}
              className={styles.expandIcon}
            />
          );
      }
    },
    [expandIcon, iconStyle]
  );

  // Convert items to Ant Design format
  const collapseItems = useMemo<CollapseProps['items']>(() => {
    return items.map(item => ({
      key: item.key,
      label: item.header,
      children: item.content,
      extra: item.extra,
      showArrow: item.showArrow !== false && iconStyle !== 'none',
      forceRender: item.forceRender,
      collapsible: item.disabled ? 'disabled' : item.collapsible,
    }));
  }, [items, iconStyle]);

  return (
    <Collapse
      items={collapseItems}
      activeKey={activeKey}
      defaultActiveKey={defaultActiveKey}
      onChange={onChange}
      accordion={accordion}
      bordered={bordered}
      ghost={ghost}
      expandIconPosition={expandIconPosition}
      expandIcon={renderExpandIcon}
      size={size}
      className={`${styles.collapsible} ${className || ''}`}
      destroyInactivePanel={destroyInactivePanel}
    />
  );
});

/**
 * Single collapsible panel component
 */
export interface SingleCollapsibleProps {
  /** Panel header */
  header: React.ReactNode;
  /** Panel content */
  children: React.ReactNode;
  /** Open state (controlled) */
  open?: boolean;
  /** Default open state */
  defaultOpen?: boolean;
  /** Change handler */
  onOpenChange?: (open: boolean) => void;
  /** Extra content in header */
  extra?: React.ReactNode;
  /** Bordered style */
  bordered?: boolean;
  /** Ghost style */
  ghost?: boolean;
  /** Custom class name */
  className?: string;
}

export const SingleCollapsible = memo(function SingleCollapsible({
  header,
  children,
  open,
  defaultOpen = false,
  onOpenChange,
  extra,
  bordered = true,
  ghost = false,
  className,
}: SingleCollapsibleProps): React.ReactElement {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isOpen = open !== undefined ? open : internalOpen;

  const handleChange = useCallback(
    (keys: string | string[]) => {
      const newOpen = Array.isArray(keys) ? keys.includes('panel') : keys === 'panel';
      if (open === undefined) {
        setInternalOpen(newOpen);
      }
      onOpenChange?.(newOpen);
    },
    [open, onOpenChange]
  );

  return (
    <Collapsible
      items={[{ key: 'panel', header, content: children, extra }]}
      activeKey={isOpen ? ['panel'] : []}
      onChange={handleChange}
      bordered={bordered}
      ghost={ghost}
      className={className}
    />
  );
});
