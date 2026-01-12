/**
 * SearchInput Component
 * 
 * A reusable search input with debouncing, clear button,
 * and optional suggestions.
 * 
 * @module components/Common/Composable/SearchInput
 * @version 1.0.0
 */

import React, { useState, useCallback, useEffect, memo, useRef } from 'react';
import { Input, AutoComplete, Spin, type InputRef } from 'antd';
import { SearchOutlined, CloseCircleFilled, LoadingOutlined } from '@ant-design/icons';
import { useDebounce } from '../../../utils/hooks';
import styles from './SearchInput.module.scss';

/**
 * Search suggestion item
 */
export interface SearchSuggestion {
  value: string;
  label?: React.ReactNode;
  disabled?: boolean;
}

/**
 * SearchInput component props
 */
export interface SearchInputProps {
  /** Current value */
  value?: string;
  /** Value change handler */
  onChange?: (value: string) => void;
  /** Search handler (called after debounce) */
  onSearch?: (value: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Debounce delay in ms */
  debounceMs?: number;
  /** Loading state */
  loading?: boolean;
  /** Suggestions for autocomplete */
  suggestions?: SearchSuggestion[];
  /** Suggestion select handler */
  onSuggestionSelect?: (value: string) => void;
  /** Enable autocomplete */
  autoComplete?: boolean;
  /** Allow clear */
  allowClear?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Size variant */
  size?: 'large' | 'middle' | 'small';
  /** Custom class name */
  className?: string;
  /** Input width */
  width?: number | string;
  /** Auto focus */
  autoFocus?: boolean;
  /** Max length */
  maxLength?: number;
  /** Prefix icon */
  prefix?: React.ReactNode;
  /** Suffix content */
  suffix?: React.ReactNode;
  /** Enter key handler */
  onPressEnter?: (value: string) => void;
  /** Focus handler */
  onFocus?: () => void;
  /** Blur handler */
  onBlur?: () => void;
}

/**
 * SearchInput component with debouncing and autocomplete
 */
export const SearchInput = memo(function SearchInput({
  value: controlledValue,
  onChange,
  onSearch,
  placeholder = '搜索...',
  debounceMs = 300,
  loading = false,
  suggestions = [],
  onSuggestionSelect,
  autoComplete = false,
  allowClear = true,
  disabled = false,
  size = 'middle',
  className,
  width,
  autoFocus = false,
  maxLength,
  prefix,
  suffix,
  onPressEnter,
  onFocus,
  onBlur,
}: SearchInputProps): React.ReactElement {
  const [internalValue, setInternalValue] = useState(controlledValue || '');
  const inputRef = useRef<InputRef>(null);

  // Use controlled or internal value
  const value = controlledValue !== undefined ? controlledValue : internalValue;

  // Debounce the search value
  const debouncedValue = useDebounce(value, debounceMs);

  // Call onSearch when debounced value changes
  useEffect(() => {
    if (onSearch && debouncedValue !== undefined) {
      onSearch(debouncedValue);
    }
  }, [debouncedValue, onSearch]);

  // Handle value change
  const handleChange = useCallback(
    (newValue: string) => {
      if (controlledValue === undefined) {
        setInternalValue(newValue);
      }
      onChange?.(newValue);
    },
    [controlledValue, onChange]
  );

  // Handle input change
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleChange(e.target.value);
    },
    [handleChange]
  );

  // Handle clear
  const handleClear = useCallback(() => {
    handleChange('');
    inputRef.current?.focus();
  }, [handleChange]);

  // Handle enter key
  const handlePressEnter = useCallback(() => {
    onPressEnter?.(value);
  }, [onPressEnter, value]);

  // Handle suggestion select
  const handleSelect = useCallback(
    (selectedValue: string) => {
      handleChange(selectedValue);
      onSuggestionSelect?.(selectedValue);
    },
    [handleChange, onSuggestionSelect]
  );

  // Build suffix content
  const suffixContent = (
    <>
      {loading && <Spin indicator={<LoadingOutlined spin />} size="small" />}
      {allowClear && value && !loading && (
        <CloseCircleFilled
          className={styles.clearIcon}
          onClick={handleClear}
        />
      )}
      {suffix}
    </>
  );

  // Common input props
  const inputProps = {
    ref: inputRef,
    value,
    placeholder,
    disabled,
    size,
    maxLength,
    autoFocus,
    prefix: prefix || <SearchOutlined className={styles.searchIcon} />,
    suffix: suffixContent,
    onPressEnter: handlePressEnter,
    onFocus,
    onBlur,
    className: styles.input,
    style: { width },
  };

  // Render with or without autocomplete
  if (autoComplete && suggestions.length > 0) {
    return (
      <div className={`${styles.searchInput} ${className || ''}`}>
        <AutoComplete
          value={value}
          options={suggestions}
          onSelect={handleSelect}
          onChange={handleChange}
          disabled={disabled}
          style={{ width }}
        >
          <Input {...inputProps} onChange={handleInputChange} />
        </AutoComplete>
      </div>
    );
  }

  return (
    <div className={`${styles.searchInput} ${className || ''}`}>
      <Input {...inputProps} onChange={handleInputChange} />
    </div>
  );
});
