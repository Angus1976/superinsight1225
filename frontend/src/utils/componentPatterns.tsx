/**
 * Component Patterns and Higher-Order Components
 * 
 * This module provides reusable component patterns and HOCs for:
 * - Loading states
 * - Error handling
 * - Data fetching
 * - Memoization
 * - Conditional rendering
 * 
 * @module utils/componentPatterns
 * @version 1.0.0
 */

import React, {
  type ComponentType,
  type ReactNode,
  type FC,
  memo,
  Suspense,
  lazy,
  useCallback,
  useState,
  useEffect,
} from 'react';
import { Spin, Result, Button, Empty } from 'antd';
import { LoadingOutlined, ReloadOutlined } from '@ant-design/icons';

// ============================================================================
// Types
// ============================================================================

/**
 * Props for components with loading state
 */
export interface WithLoadingProps {
  isLoading?: boolean;
  loadingText?: string;
}

/**
 * Props for components with error state
 */
export interface WithErrorProps {
  error?: Error | null;
  onRetry?: () => void;
}

/**
 * Props for components with empty state
 */
export interface WithEmptyProps {
  isEmpty?: boolean;
  emptyText?: string;
  emptyDescription?: string;
}

/**
 * Combined state props
 */
export interface DataStateProps extends WithLoadingProps, WithErrorProps, WithEmptyProps {}

/**
 * Async data state
 */
export interface AsyncState<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
}

// ============================================================================
// Loading Components
// ============================================================================

/**
 * Default loading spinner component
 */
export const LoadingSpinner: FC<{ text?: string; size?: 'small' | 'default' | 'large' }> = ({
  text = '加载中...',
  size = 'default',
}) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px',
      minHeight: '200px',
    }}
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <Spin
      indicator={<LoadingOutlined style={{ fontSize: size === 'large' ? 48 : size === 'small' ? 24 : 36 }} spin />}
      size={size}
    />
    {text && (
      <span style={{ marginTop: '16px', color: '#666' }}>
        {text}
      </span>
    )}
  </div>
);

/**
 * Inline loading indicator
 */
export const InlineLoading: FC<{ text?: string }> = ({ text }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
    <Spin size="small" />
    {text && <span>{text}</span>}
  </span>
);

// ============================================================================
// Error Components
// ============================================================================

/**
 * Default error display component
 */
export const ErrorDisplay: FC<{
  error: Error;
  onRetry?: () => void;
  title?: string;
}> = ({ error, onRetry, title = '出错了' }) => (
  <Result
    status="error"
    title={title}
    subTitle={error.message || '发生了未知错误'}
    extra={
      onRetry && (
        <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
          重试
        </Button>
      )
    }
  />
);

/**
 * Compact error display for inline use
 */
export const InlineError: FC<{
  message: string;
  onRetry?: () => void;
}> = ({ message, onRetry }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      color: '#ff4d4f',
      padding: '8px',
    }}
    role="alert"
  >
    <span>{message}</span>
    {onRetry && (
      <Button type="link" size="small" onClick={onRetry}>
        重试
      </Button>
    )}
  </div>
);

// ============================================================================
// Empty State Components
// ============================================================================

/**
 * Default empty state component
 */
export const EmptyState: FC<{
  description?: string;
  image?: ReactNode;
  action?: ReactNode;
}> = ({ description = '暂无数据', image, action }) => (
  <Empty
    image={image || Empty.PRESENTED_IMAGE_SIMPLE}
    description={description}
  >
    {action}
  </Empty>
);

// ============================================================================
// Higher-Order Components
// ============================================================================

/**
 * HOC that adds loading state handling to a component
 * @param WrappedComponent - The component to wrap
 * @param LoadingComponent - Optional custom loading component
 * @returns The wrapped component with loading state
 */
export function withLoading<P extends object>(
  WrappedComponent: ComponentType<P>,
  LoadingComponent: ComponentType<{ text?: string }> = LoadingSpinner
): FC<P & WithLoadingProps> {
  const WithLoadingComponent: FC<P & WithLoadingProps> = ({
    isLoading,
    loadingText,
    ...props
  }) => {
    if (isLoading) {
      return <LoadingComponent text={loadingText} />;
    }
    return <WrappedComponent {...(props as P)} />;
  };

  WithLoadingComponent.displayName = `withLoading(${getDisplayName(WrappedComponent)})`;
  return WithLoadingComponent;
}

/**
 * HOC that adds error state handling to a component
 * @param WrappedComponent - The component to wrap
 * @param ErrorComponent - Optional custom error component
 * @returns The wrapped component with error state
 */
export function withError<P extends object>(
  WrappedComponent: ComponentType<P>,
  ErrorComponent: ComponentType<{ error: Error; onRetry?: () => void }> = ErrorDisplay
): FC<P & WithErrorProps> {
  const WithErrorComponent: FC<P & WithErrorProps> = ({
    error,
    onRetry,
    ...props
  }) => {
    if (error) {
      return <ErrorComponent error={error} onRetry={onRetry} />;
    }
    return <WrappedComponent {...(props as P)} />;
  };

  WithErrorComponent.displayName = `withError(${getDisplayName(WrappedComponent)})`;
  return WithErrorComponent;
}

/**
 * HOC that adds empty state handling to a component
 * @param WrappedComponent - The component to wrap
 * @param EmptyComponent - Optional custom empty component
 * @returns The wrapped component with empty state
 */
export function withEmpty<P extends object>(
  WrappedComponent: ComponentType<P>,
  EmptyComponent: ComponentType<{ description?: string }> = EmptyState
): FC<P & WithEmptyProps> {
  const WithEmptyComponent: FC<P & WithEmptyProps> = ({
    isEmpty,
    emptyText,
    emptyDescription,
    ...props
  }) => {
    if (isEmpty) {
      return <EmptyComponent description={emptyDescription || emptyText} />;
    }
    return <WrappedComponent {...(props as P)} />;
  };

  WithEmptyComponent.displayName = `withEmpty(${getDisplayName(WrappedComponent)})`;
  return WithEmptyComponent;
}

/**
 * HOC that combines loading, error, and empty state handling
 * @param WrappedComponent - The component to wrap
 * @returns The wrapped component with all data states
 */
export function withDataState<P extends object>(
  WrappedComponent: ComponentType<P>
): FC<P & DataStateProps> {
  const WithDataStateComponent: FC<P & DataStateProps> = ({
    isLoading,
    loadingText,
    error,
    onRetry,
    isEmpty,
    emptyText,
    emptyDescription,
    ...props
  }) => {
    if (isLoading) {
      return <LoadingSpinner text={loadingText} />;
    }

    if (error) {
      return <ErrorDisplay error={error} onRetry={onRetry} />;
    }

    if (isEmpty) {
      return <EmptyState description={emptyDescription || emptyText} />;
    }

    return <WrappedComponent {...(props as P)} />;
  };

  WithDataStateComponent.displayName = `withDataState(${getDisplayName(WrappedComponent)})`;
  return WithDataStateComponent;
}

// ============================================================================
// Render Props Patterns
// ============================================================================

/**
 * Component that handles async data fetching with render props
 */
export interface AsyncDataProps<T> {
  fetchFn: () => Promise<T>;
  children: (state: AsyncState<T> & { refetch: () => void }) => ReactNode;
  deps?: unknown[];
}

export function AsyncData<T>({ fetchFn, children, deps = [] }: AsyncDataProps<T>): ReactNode {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    isLoading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const data = await fetchFn();
      setState({ data, isLoading: false, error: null });
    } catch (error) {
      setState({
        data: null,
        isLoading: false,
        error: error instanceof Error ? error : new Error(String(error)),
      });
    }
  }, [fetchFn]);

  useEffect(() => {
    fetchData();
  }, [...deps, fetchData]);

  return children({ ...state, refetch: fetchData });
}

/**
 * Conditional rendering component
 */
export interface ConditionalProps {
  condition: boolean;
  children: ReactNode;
  fallback?: ReactNode;
}

export const Conditional: FC<ConditionalProps> = ({
  condition,
  children,
  fallback = null,
}) => {
  return condition ? <>{children}</> : <>{fallback}</>;
};

/**
 * Switch component for multiple conditions
 */
export interface SwitchCaseProps<T> {
  value: T;
  cases: Record<string, ReactNode>;
  default?: ReactNode;
}

export function SwitchCase<T extends string | number>({
  value,
  cases,
  default: defaultCase = null,
}: SwitchCaseProps<T>): ReactNode {
  return cases[String(value)] ?? defaultCase;
}

// ============================================================================
// Lazy Loading Utilities
// ============================================================================

/**
 * Creates a lazy-loaded component with a loading fallback
 * @param importFn - The dynamic import function
 * @param fallback - Optional loading fallback
 * @returns The lazy-loaded component
 */
export function lazyWithFallback<T extends ComponentType<unknown>>(
  importFn: () => Promise<{ default: T }>,
  fallback: ReactNode = <LoadingSpinner />
): FC<React.ComponentProps<T>> {
  const LazyComponent = lazy(importFn);

  const LazyWithFallback: FC<React.ComponentProps<T>> = (props) => (
    <Suspense fallback={fallback}>
      <LazyComponent {...props} />
    </Suspense>
  );

  return LazyWithFallback;
}

/**
 * Creates a lazy-loaded component with retry capability
 * @param importFn - The dynamic import function
 * @param retries - Number of retries
 * @returns The lazy-loaded component
 */
export function lazyWithRetry<T extends ComponentType<unknown>>(
  importFn: () => Promise<{ default: T }>,
  retries = 3
): React.LazyExoticComponent<T> {
  return lazy(async () => {
    let lastError: Error | undefined;

    for (let i = 0; i < retries; i++) {
      try {
        return await importFn();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        // Wait before retry with exponential backoff
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
      }
    }

    throw lastError;
  });
}

// ============================================================================
// Memoization Utilities
// ============================================================================

/**
 * Creates a memoized component with custom comparison
 * @param Component - The component to memoize
 * @param propsAreEqual - Custom comparison function
 * @returns The memoized component
 */
export function memoWithCompare<P extends object>(
  Component: FC<P>,
  propsAreEqual: (prevProps: Readonly<P>, nextProps: Readonly<P>) => boolean
): FC<P> {
  return memo(Component, propsAreEqual);
}

/**
 * Creates a memoized component that only re-renders when specified props change
 * @param Component - The component to memoize
 * @param keys - The prop keys to watch for changes
 * @returns The memoized component
 */
export function memoByKeys<P extends object>(
  Component: FC<P>,
  keys: (keyof P)[]
): FC<P> {
  return memo(Component, (prevProps, nextProps) => {
    return keys.every(key => prevProps[key] === nextProps[key]);
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Gets the display name of a component
 * @param Component - The component
 * @returns The display name
 */
function getDisplayName<P>(Component: ComponentType<P>): string {
  return Component.displayName || Component.name || 'Component';
}

/**
 * Creates a component that renders nothing (useful for conditional rendering)
 */
export const Nothing: FC = () => null;

/**
 * Creates a fragment wrapper component
 */
export const Fragment: FC<{ children: ReactNode }> = ({ children }) => <>{children}</>;

/**
 * Creates a portal-like component for rendering children
 */
export interface RenderChildrenProps {
  children: ReactNode | ((props: Record<string, unknown>) => ReactNode);
  props?: Record<string, unknown>;
}

export const RenderChildren: FC<RenderChildrenProps> = ({ children, props = {} }) => {
  if (typeof children === 'function') {
    return <>{children(props)}</>;
  }
  return <>{children}</>;
};
