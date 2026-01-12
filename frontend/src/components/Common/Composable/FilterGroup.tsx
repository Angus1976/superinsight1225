/**
 * FilterGroup Component
 * 
 * A reusable filter group component for filtering data
 * with multiple filter types (select, checkbox, radio, date range).
 * 
 * @module components/Common/Composable/FilterGroup
 * @version 1.0.0
 */

import React, { useCallback, memo, useMemo } from 'react';
import { Select, Checkbox, Radio, DatePicker, Space, Button, Tag, Divider } from 'antd';
import { FilterOutlined, ClearOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import styles from './FilterGroup.module.scss';

const { RangePicker } = DatePicker;

/**
 * Filter option interface
 */
export interface FilterOption {
  /** Option value */
  value: string | number | boolean;
  /** Option label */
  label: string;
  /** Disabled state */
  disabled?: boolean;
  /** Option count (for display) */
  count?: number;
}

/**
 * Filter definition interface
 */
export interface FilterDefinition {
  /** Unique filter key */
  key: string;
  /** Filter label */
  label: string;
  /** Filter type */
  type: 'select' | 'multiselect' | 'checkbox' | 'radio' | 'daterange';
  /** Filter options (for select, checkbox, radio) */
  options?: FilterOption[];
  /** Placeholder text */
  placeholder?: string;
  /** Default value */
  defaultValue?: unknown;
  /** Allow clear */
  allowClear?: boolean;
  /** Width for select */
  width?: number | string;
}

/**
 * Filter values type
 */
export type FilterValues = Record<string, unknown>;

/**
 * FilterGroup component props
 */
export interface FilterGroupProps {
  /** Filter definitions */
  filters: FilterDefinition[];
  /** Current filter values */
  values: FilterValues;
  /** Filter change handler */
  onChange: (values: FilterValues) => void;
  /** Layout mode */
  layout?: 'horizontal' | 'vertical' | 'inline';
  /** Show clear all button */
  showClearAll?: boolean;
  /** Show active filter tags */
  showTags?: boolean;
  /** Custom class name */
  className?: string;
  /** Collapsible filters */
  collapsible?: boolean;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Size variant */
  size?: 'large' | 'middle' | 'small';
}

/**
 * FilterGroup component for filtering data
 */
export const FilterGroup = memo(function FilterGroup({
  filters,
  values,
  onChange,
  layout = 'horizontal',
  showClearAll = true,
  showTags = true,
  className,
  collapsible = false,
  defaultCollapsed = false,
  size = 'middle',
}: FilterGroupProps): React.ReactElement {
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed);

  // Handle single filter change
  const handleFilterChange = useCallback(
    (key: string, value: unknown) => {
      onChange({
        ...values,
        [key]: value,
      });
    },
    [values, onChange]
  );

  // Handle clear all filters
  const handleClearAll = useCallback(() => {
    const clearedValues: FilterValues = {};
    filters.forEach(filter => {
      clearedValues[filter.key] = filter.defaultValue ?? undefined;
    });
    onChange(clearedValues);
  }, [filters, onChange]);

  // Handle remove single filter
  const handleRemoveFilter = useCallback(
    (key: string) => {
      const filter = filters.find(f => f.key === key);
      onChange({
        ...values,
        [key]: filter?.defaultValue ?? undefined,
      });
    },
    [filters, values, onChange]
  );

  // Get active filters for tags
  const activeFilters = useMemo(() => {
    return filters.filter(filter => {
      const value = values[filter.key];
      if (value === undefined || value === null || value === '') return false;
      if (Array.isArray(value) && value.length === 0) return false;
      return true;
    });
  }, [filters, values]);

  // Render filter by type
  const renderFilter = useCallback(
    (filter: FilterDefinition) => {
      const value = values[filter.key];

      switch (filter.type) {
        case 'select':
          return (
            <Select
              value={value as string | number | undefined}
              onChange={v => handleFilterChange(filter.key, v)}
              options={filter.options}
              placeholder={filter.placeholder || `选择${filter.label}`}
              allowClear={filter.allowClear !== false}
              style={{ width: filter.width || 160 }}
              size={size}
            />
          );

        case 'multiselect':
          return (
            <Select
              mode="multiple"
              value={value as (string | number)[] | undefined}
              onChange={v => handleFilterChange(filter.key, v)}
              options={filter.options}
              placeholder={filter.placeholder || `选择${filter.label}`}
              allowClear={filter.allowClear !== false}
              style={{ width: filter.width || 200 }}
              size={size}
              maxTagCount="responsive"
            />
          );

        case 'checkbox':
          return (
            <Checkbox.Group
              value={value as (string | number | boolean)[] | undefined}
              onChange={v => handleFilterChange(filter.key, v)}
              options={filter.options?.map(opt => ({
                label: opt.count !== undefined ? `${opt.label} (${opt.count})` : opt.label,
                value: opt.value,
                disabled: opt.disabled,
              }))}
            />
          );

        case 'radio':
          return (
            <Radio.Group
              value={value}
              onChange={e => handleFilterChange(filter.key, e.target.value)}
              options={filter.options?.map(opt => ({
                label: opt.count !== undefined ? `${opt.label} (${opt.count})` : opt.label,
                value: opt.value,
                disabled: opt.disabled,
              }))}
            />
          );

        case 'daterange':
          return (
            <RangePicker
              value={value as [Dayjs, Dayjs] | undefined}
              onChange={v => handleFilterChange(filter.key, v)}
              placeholder={['开始日期', '结束日期']}
              allowClear={filter.allowClear !== false}
              size={size}
            />
          );

        default:
          return null;
      }
    },
    [values, handleFilterChange, size]
  );

  // Get label for active filter value
  const getFilterValueLabel = useCallback(
    (filter: FilterDefinition, value: unknown): string => {
      if (filter.type === 'daterange' && Array.isArray(value)) {
        return `${value[0]?.format('YYYY-MM-DD')} ~ ${value[1]?.format('YYYY-MM-DD')}`;
      }

      if (Array.isArray(value)) {
        return value
          .map(v => filter.options?.find(opt => opt.value === v)?.label || String(v))
          .join(', ');
      }

      return filter.options?.find(opt => opt.value === value)?.label || String(value);
    },
    []
  );

  return (
    <div className={`${styles.filterGroup} ${styles[layout]} ${className || ''}`}>
      {/* Filter controls */}
      {(!collapsible || !collapsed) && (
        <div className={styles.filters}>
          {filters.map(filter => (
            <div key={filter.key} className={styles.filterItem}>
              <span className={styles.filterLabel}>{filter.label}:</span>
              {renderFilter(filter)}
            </div>
          ))}

          {showClearAll && activeFilters.length > 0 && (
            <Button
              type="link"
              icon={<ClearOutlined />}
              onClick={handleClearAll}
              size={size}
            >
              清除全部
            </Button>
          )}
        </div>
      )}

      {/* Collapsible toggle */}
      {collapsible && (
        <Button
          type="link"
          icon={<FilterOutlined />}
          onClick={() => setCollapsed(!collapsed)}
          className={styles.toggleButton}
        >
          {collapsed ? '展开筛选' : '收起筛选'}
          {collapsed && activeFilters.length > 0 && (
            <Tag color="blue" className={styles.countTag}>
              {activeFilters.length}
            </Tag>
          )}
        </Button>
      )}

      {/* Active filter tags */}
      {showTags && activeFilters.length > 0 && (
        <>
          <Divider type="vertical" />
          <div className={styles.activeTags}>
            {activeFilters.map(filter => (
              <Tag
                key={filter.key}
                closable
                onClose={() => handleRemoveFilter(filter.key)}
                className={styles.filterTag}
              >
                {filter.label}: {getFilterValueLabel(filter, values[filter.key])}
              </Tag>
            ))}
          </div>
        </>
      )}
    </div>
  );
});
