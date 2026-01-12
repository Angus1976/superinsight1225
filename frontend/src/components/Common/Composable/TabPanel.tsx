/**
 * TabPanel Component
 * 
 * A reusable tab panel component with support for
 * lazy loading, badges, and custom tab rendering.
 * 
 * @module components/Common/Composable/TabPanel
 * @version 1.0.0
 */

import React, { useState, useCallback, memo, useMemo, Suspense } from 'react';
import { Tabs, Badge, Spin } from 'antd';
import type { TabsProps } from 'antd';
import styles from './TabPanel.module.scss';

/**
 * Tab item interface
 */
export interface TabItem {
  /** Unique key */
  key: string;
  /** Tab label */
  label: React.ReactNode;
  /** Tab content */
  content: React.ReactNode | (() => React.ReactNode);
  /** Tab icon */
  icon?: React.ReactNode;
  /** Badge count */
  badge?: number;
  /** Badge dot */
  badgeDot?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Closable (for editable tabs) */
  closable?: boolean;
  /** Force render content */
  forceRender?: boolean;
  /** Destroy content when inactive */
  destroyInactiveTabPane?: boolean;
}

/**
 * TabPanel component props
 */
export interface TabPanelProps {
  /** Tab items */
  items: TabItem[];
  /** Active tab key (controlled) */
  activeKey?: string;
  /** Default active tab key */
  defaultActiveKey?: string;
  /** Tab change handler */
  onChange?: (key: string) => void;
  /** Tab type */
  type?: 'line' | 'card' | 'editable-card';
  /** Tab position */
  tabPosition?: 'top' | 'right' | 'bottom' | 'left';
  /** Size */
  size?: 'large' | 'middle' | 'small';
  /** Centered tabs */
  centered?: boolean;
  /** Tab bar extra content */
  tabBarExtraContent?: React.ReactNode | { left?: React.ReactNode; right?: React.ReactNode };
  /** Tab bar gutter */
  tabBarGutter?: number;
  /** Tab bar style */
  tabBarStyle?: React.CSSProperties;
  /** Custom class name */
  className?: string;
  /** Animated transitions */
  animated?: boolean | { inkBar?: boolean; tabPane?: boolean };
  /** Lazy load tab content */
  lazyLoad?: boolean;
  /** Loading component for lazy load */
  loadingComponent?: React.ReactNode;
  /** Tab add handler (for editable-card) */
  onAdd?: () => void;
  /** Tab remove handler (for editable-card) */
  onRemove?: (key: string) => void;
  /** Destroy inactive tab panes */
  destroyInactiveTabPane?: boolean;
}

/**
 * TabPanel component for tabbed content
 */
export const TabPanel = memo(function TabPanel({
  items,
  activeKey,
  defaultActiveKey,
  onChange,
  type = 'line',
  tabPosition = 'top',
  size = 'middle',
  centered = false,
  tabBarExtraContent,
  tabBarGutter,
  tabBarStyle,
  className,
  animated = true,
  lazyLoad = false,
  loadingComponent,
  onAdd,
  onRemove,
  destroyInactiveTabPane = false,
}: TabPanelProps): React.ReactElement {
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(
    new Set(defaultActiveKey ? [defaultActiveKey] : [])
  );

  // Handle tab change
  const handleChange = useCallback(
    (key: string) => {
      if (lazyLoad) {
        setLoadedTabs(prev => new Set([...prev, key]));
      }
      onChange?.(key);
    },
    [lazyLoad, onChange]
  );

  // Handle tab edit (add/remove)
  const handleEdit = useCallback(
    (targetKey: React.MouseEvent | React.KeyboardEvent | string, action: 'add' | 'remove') => {
      if (action === 'add') {
        onAdd?.();
      } else if (action === 'remove' && typeof targetKey === 'string') {
        onRemove?.(targetKey);
      }
    },
    [onAdd, onRemove]
  );

  // Convert items to Ant Design format
  const tabItems = useMemo<TabsProps['items']>(() => {
    return items.map(item => {
      // Build tab label with icon and badge
      let label: React.ReactNode = item.label;
      
      if (item.icon || item.badge !== undefined || item.badgeDot) {
        label = (
          <span className={styles.tabLabel}>
            {item.icon && <span className={styles.tabIcon}>{item.icon}</span>}
            <span>{item.label}</span>
            {(item.badge !== undefined || item.badgeDot) && (
              <Badge
                count={item.badge}
                dot={item.badgeDot}
                size="small"
                className={styles.tabBadge}
              />
            )}
          </span>
        );
      }

      // Build tab content
      let content: React.ReactNode;
      
      if (lazyLoad && !loadedTabs.has(item.key)) {
        content = null;
      } else if (typeof item.content === 'function') {
        content = (
          <Suspense fallback={loadingComponent || <Spin className={styles.loading} />}>
            {item.content()}
          </Suspense>
        );
      } else {
        content = item.content;
      }

      return {
        key: item.key,
        label,
        children: content,
        disabled: item.disabled,
        closable: item.closable,
        forceRender: item.forceRender,
        destroyInactiveTabPane: item.destroyInactiveTabPane ?? destroyInactiveTabPane,
      };
    });
  }, [items, lazyLoad, loadedTabs, loadingComponent, destroyInactiveTabPane]);

  return (
    <Tabs
      items={tabItems}
      activeKey={activeKey}
      defaultActiveKey={defaultActiveKey}
      onChange={handleChange}
      type={type}
      tabPosition={tabPosition}
      size={size}
      centered={centered}
      tabBarExtraContent={tabBarExtraContent}
      tabBarGutter={tabBarGutter}
      tabBarStyle={tabBarStyle}
      className={`${styles.tabPanel} ${className || ''}`}
      animated={animated}
      onEdit={type === 'editable-card' ? handleEdit : undefined}
    />
  );
});
