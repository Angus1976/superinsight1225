/**
 * DataTable Component
 * 
 * A highly reusable table component with built-in sorting,
 * filtering, pagination, and row selection.
 * 
 * @module components/Common/Composable/DataTable
 * @version 1.0.0
 */

import React, { type ReactNode, useCallback, useMemo, memo, useState } from 'react';
import { Table, Input, Space, Button, Dropdown, type TableProps, type MenuProps } from 'antd';
import { SearchOutlined, FilterOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import type { ColumnsType, ColumnType } from 'antd/es/table';
import type { FilterValue, SorterResult, TablePaginationConfig } from 'antd/es/table/interface';
import styles from './DataTable.module.scss';

/**
 * Extended column definition with additional features
 */
export interface DataTableColumn<T> extends Omit<ColumnType<T>, 'key'> {
  /** Unique column key */
  key: string;
  /** Column title */
  title: string;
  /** Data index for accessing row data */
  dataIndex?: string | string[];
  /** Enable sorting */
  sortable?: boolean;
  /** Enable filtering */
  filterable?: boolean;
  /** Filter options */
  filterOptions?: { text: string; value: string | number | boolean }[];
  /** Custom render function */
  render?: (value: unknown, record: T, index: number) => ReactNode;
  /** Column width */
  width?: number | string;
  /** Fixed column position */
  fixed?: 'left' | 'right' | boolean;
  /** Hide column by default */
  hidden?: boolean;
  /** Ellipsis overflow */
  ellipsis?: boolean;
  /** Align content */
  align?: 'left' | 'center' | 'right';
}

/**
 * DataTable component props
 */
export interface DataTableProps<T extends { id?: string | number; key?: string | number }> {
  /** Table data */
  data: T[];
  /** Column definitions */
  columns: DataTableColumn<T>[];
  /** Loading state */
  loading?: boolean;
  /** Row key extractor */
  rowKey?: string | ((record: T) => string | number);
  /** Enable row selection */
  selectable?: boolean;
  /** Selected row keys */
  selectedRowKeys?: (string | number)[];
  /** Selection change handler */
  onSelectionChange?: (selectedKeys: (string | number)[], selectedRows: T[]) => void;
  /** Row click handler */
  onRowClick?: (record: T) => void;
  /** Pagination config */
  pagination?: TablePaginationConfig | false;
  /** Sort change handler */
  onSortChange?: (field: string, order: 'ascend' | 'descend' | null) => void;
  /** Filter change handler */
  onFilterChange?: (filters: Record<string, FilterValue | null>) => void;
  /** Enable search */
  searchable?: boolean;
  /** Search placeholder */
  searchPlaceholder?: string;
  /** Search handler */
  onSearch?: (value: string) => void;
  /** Refresh handler */
  onRefresh?: () => void;
  /** Custom toolbar actions */
  toolbarActions?: ReactNode;
  /** Table title */
  title?: ReactNode;
  /** Table footer */
  footer?: ReactNode;
  /** Custom class name */
  className?: string;
  /** Scroll config */
  scroll?: { x?: number | string | true; y?: number | string };
  /** Bordered style */
  bordered?: boolean;
  /** Size variant */
  size?: 'default' | 'middle' | 'small';
  /** Sticky header */
  sticky?: boolean | { offsetHeader?: number; offsetScroll?: number };
  /** Show column settings */
  showColumnSettings?: boolean;
  /** Empty text */
  emptyText?: string;
  /** Expandable config */
  expandable?: TableProps<T>['expandable'];
  /** Summary row */
  summary?: (data: readonly T[]) => ReactNode;
}

/**
 * Generic DataTable component for displaying tabular data
 */
function DataTableInner<T extends { id?: string | number; key?: string | number }>({
  data,
  columns,
  loading = false,
  rowKey = 'id',
  selectable = false,
  selectedRowKeys = [],
  onSelectionChange,
  onRowClick,
  pagination,
  onSortChange,
  onFilterChange,
  searchable = false,
  searchPlaceholder = '搜索...',
  onSearch,
  onRefresh,
  toolbarActions,
  title,
  footer,
  className,
  scroll,
  bordered = false,
  size = 'default',
  sticky = false,
  showColumnSettings = false,
  emptyText = '暂无数据',
  expandable,
  summary,
}: DataTableProps<T>): React.ReactElement {
  const [searchValue, setSearchValue] = useState('');
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(
    new Set(columns.filter(col => !col.hidden).map(col => col.key))
  );

  // Transform columns to Ant Design format
  const tableColumns = useMemo<ColumnsType<T>>(() => {
    return columns
      .filter(col => visibleColumns.has(col.key))
      .map(col => {
        const column: ColumnType<T> = {
          key: col.key,
          title: col.title,
          dataIndex: col.dataIndex,
          width: col.width,
          fixed: col.fixed,
          ellipsis: col.ellipsis,
          align: col.align,
          render: col.render,
        };

        // Add sorting
        if (col.sortable) {
          column.sorter = true;
        }

        // Add filtering
        if (col.filterable && col.filterOptions) {
          column.filters = col.filterOptions;
          column.filterMultiple = true;
        }

        return column;
      });
  }, [columns, visibleColumns]);

  // Handle table change (sort, filter, pagination)
  const handleTableChange = useCallback(
    (
      _pagination: TablePaginationConfig,
      filters: Record<string, FilterValue | null>,
      sorter: SorterResult<T> | SorterResult<T>[]
    ) => {
      // Handle sorting
      if (!Array.isArray(sorter) && sorter.field && onSortChange) {
        onSortChange(String(sorter.field), sorter.order || null);
      }

      // Handle filtering
      if (onFilterChange) {
        onFilterChange(filters);
      }
    },
    [onSortChange, onFilterChange]
  );

  // Handle search
  const handleSearch = useCallback(
    (value: string) => {
      setSearchValue(value);
      onSearch?.(value);
    },
    [onSearch]
  );

  // Column settings menu
  const columnSettingsMenu = useMemo<MenuProps>(() => {
    return {
      items: columns.map(col => ({
        key: col.key,
        label: (
          <span>
            <input
              type="checkbox"
              checked={visibleColumns.has(col.key)}
              onChange={e => {
                const newVisible = new Set(visibleColumns);
                if (e.target.checked) {
                  newVisible.add(col.key);
                } else {
                  newVisible.delete(col.key);
                }
                setVisibleColumns(newVisible);
              }}
              style={{ marginRight: 8 }}
            />
            {col.title}
          </span>
        ),
      })),
    };
  }, [columns, visibleColumns]);

  // Row selection config
  const rowSelection = useMemo(() => {
    if (!selectable) return undefined;

    return {
      selectedRowKeys,
      onChange: (keys: React.Key[], rows: T[]) => {
        onSelectionChange?.(keys as (string | number)[], rows);
      },
    };
  }, [selectable, selectedRowKeys, onSelectionChange]);

  // Row props for click handling
  const onRow = useCallback(
    (record: T) => ({
      onClick: () => onRowClick?.(record),
      style: { cursor: onRowClick ? 'pointer' : 'default' },
    }),
    [onRowClick]
  );

  return (
    <div className={`${styles.dataTable} ${className || ''}`}>
      {/* Toolbar */}
      {(searchable || onRefresh || toolbarActions || showColumnSettings) && (
        <div className={styles.toolbar}>
          <Space>
            {searchable && (
              <Input.Search
                placeholder={searchPlaceholder}
                value={searchValue}
                onChange={e => setSearchValue(e.target.value)}
                onSearch={handleSearch}
                allowClear
                prefix={<SearchOutlined />}
                className={styles.searchInput}
              />
            )}
          </Space>
          <Space>
            {toolbarActions}
            {onRefresh && (
              <Button icon={<ReloadOutlined />} onClick={onRefresh}>
                刷新
              </Button>
            )}
            {showColumnSettings && (
              <Dropdown menu={columnSettingsMenu} trigger={['click']}>
                <Button icon={<SettingOutlined />}>列设置</Button>
              </Dropdown>
            )}
          </Space>
        </div>
      )}

      {/* Table */}
      <Table<T>
        columns={tableColumns}
        dataSource={data}
        loading={loading}
        rowKey={rowKey}
        rowSelection={rowSelection}
        onRow={onRow}
        pagination={pagination}
        onChange={handleTableChange}
        title={title ? () => title : undefined}
        footer={footer ? () => footer : undefined}
        scroll={scroll}
        bordered={bordered}
        size={size}
        sticky={sticky}
        locale={{ emptyText }}
        expandable={expandable}
        summary={summary}
      />
    </div>
  );
}

// Memoize the component
export const DataTable = memo(DataTableInner) as typeof DataTableInner;
