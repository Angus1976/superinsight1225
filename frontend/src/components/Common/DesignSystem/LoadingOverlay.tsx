/**
 * LoadingOverlay Component
 * 
 * Consistent loading overlay for async operations.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import styles from './LoadingOverlay.module.scss';

const { Text } = Typography;

interface LoadingOverlayProps {
  loading: boolean;
  tip?: string;
  size?: 'small' | 'default' | 'large';
  fullScreen?: boolean;
  blur?: boolean;
  children?: ReactNode;
  className?: string;
}

const spinSizes = {
  small: 24,
  default: 32,
  large: 48,
};

export const LoadingOverlay = memo<LoadingOverlayProps>(({
  loading,
  tip,
  size = 'default',
  fullScreen = false,
  blur = true,
  children,
  className,
}) => {
  const antIcon = <LoadingOutlined style={{ fontSize: spinSizes[size] }} spin />;
  
  if (!loading && children) {
    return <>{children}</>;
  }
  
  if (!loading) {
    return null;
  }
  
  const overlay = (
    <div 
      className={`
        ${styles.loadingOverlay}
        ${fullScreen ? styles.fullScreen : ''}
        ${blur ? styles.blur : ''}
        ${styles[size]}
        ${className || ''}
      `}
    >
      <div className={styles.content}>
        <Spin indicator={antIcon} />
        {tip && (
          <Text type="secondary" className={styles.tip}>
            {tip}
          </Text>
        )}
      </div>
    </div>
  );
  
  if (children) {
    return (
      <div className={styles.wrapper}>
        {children}
        {overlay}
      </div>
    );
  }
  
  return overlay;
});

LoadingOverlay.displayName = 'LoadingOverlay';

// Inline loading spinner
interface LoadingSpinnerProps {
  size?: 'small' | 'default' | 'large';
  tip?: string;
  className?: string;
}

export const LoadingSpinner = memo<LoadingSpinnerProps>(({
  size = 'default',
  tip,
  className,
}) => {
  const antIcon = <LoadingOutlined style={{ fontSize: spinSizes[size] }} spin />;
  
  return (
    <div className={`${styles.spinner} ${styles[size]} ${className || ''}`}>
      <Spin indicator={antIcon} tip={tip} />
    </div>
  );
});

LoadingSpinner.displayName = 'LoadingSpinner';

// Page loading state
interface PageLoadingProps {
  tip?: string;
}

export const PageLoading = memo<PageLoadingProps>(({ tip = '加载中...' }) => (
  <LoadingOverlay loading fullScreen tip={tip} size="large" />
));

PageLoading.displayName = 'PageLoading';
