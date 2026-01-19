/**
 * AsyncContent Component
 * 
 * A utility component for handling async data fetching
 * with loading, error, and success states.
 * 
 * @module components/Common/Composable/AsyncContent
 * @version 1.0.0
 */

import React, { useState, useEffect, useCallback, memo, type ReactNode } from 'react';
import { Spin, Result, Button, Skeleton } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import styles from './AsyncContent.module.scss';

/**
 * Async state interface
 */
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * AsyncContent component props
 */
export interface AsyncContentProps<T> {
  /** Async fetch function */
  fetchFn: () => Promise<T>;
  /** Render function for success state */
  children: (data: T, refetch: () => void) => ReactNode;
  /** Dependencies for refetching */
  deps?: unknown[];
  /** Loading component */
  loadingComponent?: ReactNode;
  /** Error component */
  errorComponent?: (error: Error, retry: () => void) => ReactNode;
  /** Skeleton loading */
  skeleton?: boolean;
  /** Skeleton rows */
  skeletonRows?: number;
  /** Loading text */
  loadingText?: string;
  /** Retry on error */
  retryOnError?: boolean;
  /** Max retries */
  maxRetries?: number;
  /** Retry delay (ms) */
  retryDelay?: number;
  /** On success callback */
  onSuccess?: (data: T) => void;
  /** On error callback */
  onError?: (error: Error) => void;
  /** Initial data */
  initialData?: T;
  /** Skip initial fetch */
  skip?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * AsyncContent component for async data fetching
 */
export function AsyncContent<T>({
  fetchFn,
  children,
  deps = [],
  loadingComponent,
  errorComponent,
  skeleton = false,
  skeletonRows = 3,
  loadingText,
  retryOnError = false,
  maxRetries = 3,
  retryDelay = 1000,
  onSuccess,
  onError,
  initialData,
  skip = false,
  className,
}: AsyncContentProps<T>): React.ReactElement {
  const { t } = useTranslation('common');
  const [state, setState] = useState<AsyncState<T>>({
    data: initialData ?? null,
    loading: !skip && !initialData,
    error: null,
  });
  const [retryCount, setRetryCount] = useState(0);

  // Fetch data
  const fetchData = useCallback(async () => {
    if (skip) return;

    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const data = await fetchFn();
      setState({ data, loading: false, error: null });
      onSuccess?.(data);
      setRetryCount(0);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setState(prev => ({ ...prev, loading: false, error }));
      onError?.(error);

      // Auto retry
      if (retryOnError && retryCount < maxRetries) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
        }, retryDelay * Math.pow(2, retryCount));
      }
    }
  }, [fetchFn, skip, onSuccess, onError, retryOnError, retryCount, maxRetries, retryDelay]);

  // Fetch on mount and when deps change
  useEffect(() => {
    fetchData();
  }, [...deps, retryCount]);

  // Refetch function
  const refetch = useCallback(() => {
    setRetryCount(0);
    fetchData();
  }, [fetchData]);

  // Loading state
  if (state.loading) {
    if (loadingComponent) {
      return <div className={className}>{loadingComponent}</div>;
    }

    if (skeleton) {
      return (
        <div className={`${styles.asyncContent} ${className || ''}`}>
          <Skeleton active paragraph={{ rows: skeletonRows }} />
        </div>
      );
    }

    return (
      <div className={`${styles.asyncContent} ${styles.loading} ${className || ''}`}>
        <Spin tip={loadingText || t('status.loading')} />
      </div>
    );
  }

  // Error state
  if (state.error) {
    if (errorComponent) {
      return <div className={className}>{errorComponent(state.error, refetch)}</div>;
    }

    return (
      <div className={`${styles.asyncContent} ${className || ''}`}>
        <Result
          status="error"
          title={t('async.loadFailed')}
          subTitle={state.error.message}
          extra={
            <Button type="primary" icon={<ReloadOutlined />} onClick={refetch}>
              {t('retry')}
            </Button>
          }
        />
      </div>
    );
  }

  // Success state
  if (state.data !== null) {
    return <div className={className}>{children(state.data, refetch)}</div>;
  }

  // No data
  return <div className={className} />;
}

/**
 * useAsync hook for async data fetching
 */
export function useAsync<T>(
  fetchFn: () => Promise<T>,
  deps: unknown[] = [],
  options: {
    initialData?: T;
    skip?: boolean;
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
  } = {}
): AsyncState<T> & { refetch: () => void } {
  const { initialData, skip = false, onSuccess, onError } = options;

  const [state, setState] = useState<AsyncState<T>>({
    data: initialData ?? null,
    loading: !skip && !initialData,
    error: null,
  });

  const fetchData = useCallback(async () => {
    if (skip) return;

    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const data = await fetchFn();
      setState({ data, loading: false, error: null });
      onSuccess?.(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setState(prev => ({ ...prev, loading: false, error }));
      onError?.(error);
    }
  }, [fetchFn, skip, onSuccess, onError]);

  useEffect(() => {
    fetchData();
  }, deps);

  return { ...state, refetch: fetchData };
}
