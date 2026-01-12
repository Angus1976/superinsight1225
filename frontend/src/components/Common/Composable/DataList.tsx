/**
 * DataList Component
 * 
 * A highly reusable list component for displaying data items
 * with support for custom rendering, selection, and actions.
 * 
 * @module components/Common/Composable/DataList
 * @version 1.0.0
 */

import React, { type ReactNode, useCallback, useMemo, memo } from 'react';
import { List, Checkbox, Empty, Spin } from 'antd';
import styles from './DataList.module.scss';

/**
 * Data list item interface
 */
export interface DataListItem<T = unknown> {
  id: string | number;
  data: T;
  disabled?: boolean;
}

/**
 * DataList component props
 */
export interface DataListProps<T> {
  /** List items */
  items: DataListItem<T>[];
  /** Custom item renderer */
  renderItem: (item: DataListItem<T>, index: number) => ReactNode;
  /** Loading state */
  loading?: boolean;
  /** Empty state message */
  emptyText?: string;
  /** Empty state description */
  emptyDescription?: string;
  /** Enable selection */
  selectable?: boolean;
  /** Selected item IDs */
  selectedIds?: (string | number)[];
  /** Selection change handler */
  onSelectionChange?: (selectedIds: (string | number)[]) => void;
  /** Item click handler */
  onItemClick?: (item: DataListItem<T>) => void;
  /** Custom class name */
  className?: string;
  /** Grid layout columns */
  grid?: { gutter?: number; column?: number; xs?: number; sm?: number; md?: number; lg?: number; xl?: number; xxl?: number };
  /** Pagination config */
  pagination?: {
    current?: number;
    pageSize?: number;
    total?: number;
    onChange?: (page: number, pageSize: number) => void;
  };
  /** Header content */
  header?: ReactNode;
  /** Footer content */
  footer?: ReactNode;
  /** Item key extractor */
  keyExtractor?: (item: DataListItem<T>) => string | number;
  /** Bordered style */
  bordered?: boolean;
  /** Split items with divider */
  split?: boolean;
  /** Size variant */
  size?: 'default' | 'small' | 'large';
}

/**
 * Generic DataList component for displaying lists of data
 */
function DataListInner<T>({
  items,
  renderItem,
  loading = false,
  emptyText = '暂无数据',
  emptyDescription,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
  onItemClick,
  className,
  grid,
  pagination,
  header,
  footer,
  keyExtractor,
  bordered = false,
  split = true,
  size = 'default',
}: DataListProps<T>): React.ReactElement {
  // Memoize selected IDs set for O(1) lookup
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  // Handle item selection
  const handleSelect = useCallback(
    (itemId: string | number, checked: boolean) => {
      if (!onSelectionChange) return;

      const newSelectedIds = checked
        ? [...selectedIds, itemId]
        : selectedIds.filter(id => id !== itemId);

      onSelectionChange(newSelectedIds);
    },
    [selectedIds, onSelectionChange]
  );

  // Handle select all
  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (!onSelectionChange) return;

      const newSelectedIds = checked
        ? items.filter(item => !item.disabled).map(item => item.id)
        : [];

      onSelectionChange(newSelectedIds);
    },
    [items, onSelectionChange]
  );

  // Check if all items are selected
  const allSelected = useMemo(() => {
    const selectableItems = items.filter(item => !item.disabled);
    return selectableItems.length > 0 && selectableItems.every(item => selectedSet.has(item.id));
  }, [items, selectedSet]);

  // Check if some items are selected
  const someSelected = useMemo(() => {
    return selectedIds.length > 0 && !allSelected;
  }, [selectedIds.length, allSelected]);

  // Get item key
  const getKey = useCallback(
    (item: DataListItem<T>) => {
      return keyExtractor ? keyExtractor(item) : item.id;
    },
    [keyExtractor]
  );

  // Render list item
  const renderListItem = useCallback(
    (item: DataListItem<T>, index: number) => {
      const isSelected = selectedSet.has(item.id);
      const itemContent = renderItem(item, index);

      return (
        <List.Item
          key={getKey(item)}
          className={`${styles.listItem} ${isSelected ? styles.selected : ''} ${item.disabled ? styles.disabled : ''}`}
          onClick={() => !item.disabled && onItemClick?.(item)}
        >
          {selectable && (
            <Checkbox
              checked={isSelected}
              disabled={item.disabled}
              onChange={e => handleSelect(item.id, e.target.checked)}
              onClick={e => e.stopPropagation()}
              className={styles.checkbox}
            />
          )}
          <div className={styles.itemContent}>{itemContent}</div>
        </List.Item>
      );
    },
    [selectedSet, renderItem, getKey, selectable, onItemClick, handleSelect]
  );

  // Render header with select all
  const renderHeader = useMemo(() => {
    if (!header && !selectable) return undefined;

    return (
      <div className={styles.header}>
        {selectable && (
          <Checkbox
            checked={allSelected}
            indeterminate={someSelected}
            onChange={e => handleSelectAll(e.target.checked)}
            className={styles.selectAll}
          >
            全选
          </Checkbox>
        )}
        {header}
      </div>
    );
  }, [header, selectable, allSelected, someSelected, handleSelectAll]);

  return (
    <div className={`${styles.dataList} ${className || ''}`}>
      <List
        loading={loading}
        dataSource={items}
        renderItem={renderListItem}
        header={renderHeader}
        footer={footer}
        grid={grid}
        pagination={pagination}
        bordered={bordered}
        split={split}
        size={size}
        locale={{
          emptyText: (
            <Empty
              description={emptyDescription || emptyText}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ),
        }}
      />
    </div>
  );
}

// Memoize the component
export const DataList = memo(DataListInner) as typeof DataListInner;
