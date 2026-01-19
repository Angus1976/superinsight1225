/**
 * InfiniteScroll Component
 * 
 * A utility component for infinite scrolling with
 * automatic loading and virtualization support.
 * 
 * @module components/Common/Composable/InfiniteScroll
 * @version 1.0.0
 */

import React, { useRef, useEffect, useCallback, useState, memo, type ReactNode } from 'react';
import { Spin, Empty, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import styles from './InfiniteScroll.module.scss';

/**
 * InfiniteScroll component props
 */
export interface InfiniteScrollProps<T> {
  /** Data items */
  items: T[];
  /** Render function for each item */
  renderItem: (item: T, index: number) => ReactNode;
  /** Load more function */
  loadMore: () => Promise<void>;
  /** Has more items to load */
  hasMore: boolean;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: Error | null;
  /** Retry handler */
  onRetry?: () => void;
  /** Threshold for triggering load (pixels from bottom) */
  threshold?: number;
  /** Loading component */
  loadingComponent?: ReactNode;
  /** End message */
  endMessage?: ReactNode;
  /** Empty component */
  emptyComponent?: ReactNode;
  /** Custom class name */
  className?: string;
  /** Container height (for scrollable container) */
  height?: number | string;
  /** Use window scroll */
  useWindowScroll?: boolean;
  /** Item key extractor */
  keyExtractor?: (item: T, index: number) => string | number;
  /** Initial load */
  initialLoad?: boolean;
  /** Scroll direction */
  direction?: 'vertical' | 'horizontal';
  /** Reverse scroll (load at top) */
  reverse?: boolean;
}

/**
 * InfiniteScroll component for infinite scrolling
 */
export function InfiniteScroll<T>({
  items,
  renderItem,
  loadMore,
  hasMore,
  loading = false,
  error = null,
  onRetry,
  threshold = 200,
  loadingComponent,
  endMessage,
  emptyComponent,
  className,
  height,
  useWindowScroll = false,
  keyExtractor,
  initialLoad = true,
  direction = 'vertical',
  reverse = false,
}: InfiniteScrollProps<T>): React.ReactElement {
  const { t } = useTranslation('common');
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Get item key
  const getKey = useCallback(
    (item: T, index: number) => {
      return keyExtractor ? keyExtractor(item, index) : index;
    },
    [keyExtractor]
  );

  // Handle scroll
  const handleScroll = useCallback(async () => {
    if (loading || isLoadingMore || !hasMore || error) return;

    const container = useWindowScroll ? document.documentElement : containerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const scrollPosition = reverse
      ? scrollTop
      : scrollHeight - scrollTop - clientHeight;

    if (scrollPosition <= threshold) {
      setIsLoadingMore(true);
      try {
        await loadMore();
      } finally {
        setIsLoadingMore(false);
      }
    }
  }, [loading, isLoadingMore, hasMore, error, loadMore, threshold, useWindowScroll, reverse]);

  // Add scroll listener
  useEffect(() => {
    const target = useWindowScroll ? window : containerRef.current;
    if (!target) return;

    target.addEventListener('scroll', handleScroll, { passive: true });
    return () => target.removeEventListener('scroll', handleScroll);
  }, [handleScroll, useWindowScroll]);

  // Initial load
  useEffect(() => {
    if (initialLoad && items.length === 0 && hasMore && !loading) {
      loadMore();
    }
  }, []);

  // Render loading indicator
  const renderLoading = () => {
    if (loadingComponent) {
      return loadingComponent;
    }

    return (
      <div className={styles.loadingIndicator}>
        <Spin size="small" />
        <span>{t('status.loading')}</span>
      </div>
    );
  };

  // Render end message
  const renderEndMessage = () => {
    if (endMessage) {
      return endMessage;
    }

    if (items.length > 0) {
      return (
        <div className={styles.endMessage}>
          {t('infiniteScroll.noMore')}
        </div>
      );
    }

    return null;
  };

  // Render error
  const renderError = () => {
    return (
      <div className={styles.errorMessage}>
        <span>{t('infiniteScroll.loadFailed')}</span>
        {onRetry && (
          <Button
            type="link"
            size="small"
            icon={<ReloadOutlined />}
            onClick={onRetry}
          >
            {t('retry')}
          </Button>
        )}
      </div>
    );
  };

  // Render empty state
  if (items.length === 0 && !loading && !hasMore) {
    if (emptyComponent) {
      return <div className={className}>{emptyComponent}</div>;
    }

    return (
      <div className={`${styles.infiniteScroll} ${className || ''}`}>
        <Empty description={t('emptyState.noData')} />
      </div>
    );
  }

  // Build container style
  const containerStyle: React.CSSProperties = {};
  if (height && !useWindowScroll) {
    containerStyle.height = height;
    containerStyle.overflow = 'auto';
  }
  if (direction === 'horizontal') {
    containerStyle.overflowX = 'auto';
    containerStyle.overflowY = 'hidden';
  }

  return (
    <div
      ref={containerRef}
      className={`${styles.infiniteScroll} ${styles[direction]} ${className || ''}`}
      style={containerStyle}
    >
      <div className={styles.content}>
        {reverse && (loading || isLoadingMore) && renderLoading()}
        
        {items.map((item, index) => (
          <div key={getKey(item, index)} className={styles.item}>
            {renderItem(item, index)}
          </div>
        ))}
        
        {!reverse && (loading || isLoadingMore) && renderLoading()}
        {error && renderError()}
        {!hasMore && !loading && renderEndMessage()}
      </div>
    </div>
  );
}

// Memoized version
export const MemoizedInfiniteScroll = memo(InfiniteScroll) as typeof InfiniteScroll;
