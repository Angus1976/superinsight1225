/**
 * GlobalSearch Component
 *
 * Search trigger with ⌘K hint badge + Ant Design Modal overlay.
 * Uses useGlobalSearch hook for state, sanitizes query before calling onSearch.
 */

import React from 'react';
import { Input, Modal } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useGlobalSearch } from '@/hooks/useGlobalSearch';
import { sanitizeSearchQuery } from '@/utils/sanitize';
import styles from './GlobalSearch.module.scss';

export interface GlobalSearchProps {
  onSearch: (query: string) => void;
}

/** Detect macOS for shortcut label */
const isMac =
  typeof navigator !== 'undefined' &&
  /mac/i.test(navigator.userAgent);

export const GlobalSearch: React.FC<GlobalSearchProps> = ({ onSearch }) => {
  const { t } = useTranslation('common');
  const { isOpen, query, open, close, setQuery } = useGlobalSearch();

  const handleSearch = () => {
    const sanitized = sanitizeSearchQuery(query);
    if (!sanitized) return;
    onSearch(sanitized);
    close();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <>
      <div
        data-testid="global-search-trigger"
        className={styles.trigger}
        onClick={open}
        role="button"
        tabIndex={0}
        aria-label={t('header.search', '搜索')}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') open();
        }}
      >
        <SearchOutlined />
        <span className={styles.triggerText}>
          {t('header.search', '搜索')}
        </span>
        <span className={styles.shortcutBadge}>
          {isMac ? '⌘' : 'Ctrl'}K
        </span>
      </div>

      <Modal
        open={isOpen}
        onCancel={close}
        footer={null}
        closable={false}
        width={520}
        destroyOnClose
      >
        <Input
          className={styles.searchInput}
          placeholder={t('header.searchPlaceholder', '搜索内容...')}
          prefix={<SearchOutlined />}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          allowClear
          size="large"
        />
      </Modal>
    </>
  );
};

export default GlobalSearch;
