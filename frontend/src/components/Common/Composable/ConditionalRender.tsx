/**
 * ConditionalRender Component
 * 
 * A utility component for conditional rendering with
 * support for loading, error, and empty states.
 * 
 * @module components/Common/Composable/ConditionalRender
 * @version 1.0.0
 */

import React, { type ReactNode, memo } from 'react';
import { Spin, Result, Empty, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

/**
 * ConditionalRender component props
 */
export interface ConditionalRenderProps {
  /** Condition to check */
  condition: boolean;
  /** Content to render when condition is true */
  children: ReactNode;
  /** Fallback content when condition is false */
  fallback?: ReactNode;
  /** Loading state */
  loading?: boolean;
  /** Loading text */
  loadingText?: string;
  /** Error state */
  error?: Error | string | null;
  /** Error retry handler */
  onRetry?: () => void;
  /** Empty state */
  empty?: boolean;
  /** Empty text */
  emptyText?: string;
  /** Empty description */
  emptyDescription?: string;
  /** Empty action */
  emptyAction?: ReactNode;
}

/**
 * ConditionalRender component for conditional rendering
 */
export const ConditionalRender = memo(function ConditionalRender({
  condition,
  children,
  fallback = null,
  loading = false,
  loadingText,
  error = null,
  onRetry,
  empty = false,
  emptyText,
  emptyDescription,
  emptyAction,
}: ConditionalRenderProps): React.ReactElement {
  const { t } = useTranslation('common');

  // Loading state
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '40px' }}>
        <Spin tip={loadingText || t('status.loading')} />
      </div>
    );
  }

  // Error state
  if (error) {
    const errorMessage = typeof error === 'string' ? error : error.message;
    return (
      <Result
        status="error"
        title={t('error.title')}
        subTitle={errorMessage}
        extra={
          onRetry && (
            <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
              {t('retry')}
            </Button>
          )
        }
      />
    );
  }

  // Empty state
  if (empty) {
    return (
      <Empty description={emptyDescription || emptyText || t('emptyState.noData')}>
        {emptyAction}
      </Empty>
    );
  }

  // Conditional render
  if (condition) {
    return <>{children}</>;
  }

  return <>{fallback}</>;
});

/**
 * Show component - renders children only when condition is true
 */
export interface ShowProps {
  when: boolean;
  children: ReactNode;
  fallback?: ReactNode;
}

export const Show = memo(function Show({ when, children, fallback = null }: ShowProps): React.ReactElement {
  return when ? <>{children}</> : <>{fallback}</>;
});

/**
 * Hide component - renders children only when condition is false
 */
export interface HideProps {
  when: boolean;
  children: ReactNode;
}

export const Hide = memo(function Hide({ when, children }: HideProps): React.ReactElement | null {
  return when ? null : <>{children}</>;
});

/**
 * Switch component - renders first matching case
 */
export interface SwitchProps<T> {
  value: T;
  children: ReactNode;
}

export interface CaseProps<T> {
  value: T;
  children: ReactNode;
}

export interface DefaultProps {
  children: ReactNode;
}

export function Switch<T>({ value, children }: SwitchProps<T>): React.ReactElement | null {
  const childArray = React.Children.toArray(children);
  
  for (const child of childArray) {
    if (React.isValidElement(child)) {
      // Check for Case component
      if (child.props.value === value) {
        return <>{child.props.children}</>;
      }
    }
  }
  
  // Look for Default component
  for (const child of childArray) {
    if (React.isValidElement(child) && child.props.value === undefined) {
      return <>{child.props.children}</>;
    }
  }
  
  return null;
}

export function Case<T>({ children }: CaseProps<T>): React.ReactElement {
  return <>{children}</>;
}

export function Default({ children }: DefaultProps): React.ReactElement {
  return <>{children}</>;
}

/**
 * For component - renders children for each item in array
 */
export interface ForProps<T> {
  each: T[];
  children: (item: T, index: number) => ReactNode;
  fallback?: ReactNode;
}

export function For<T>({ each, children, fallback = null }: ForProps<T>): React.ReactElement {
  if (!each || each.length === 0) {
    return <>{fallback}</>;
  }
  
  return <>{each.map((item, index) => children(item, index))}</>;
}
