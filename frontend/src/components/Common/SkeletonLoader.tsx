/**
 * Skeleton Loader Component
 * 
 * Provides skeleton loading states for better perceived performance.
 * Shows content placeholders while actual content is loading.
 */

import { Skeleton, Card, Row, Col, Space } from 'antd';
import { memo } from 'react';

interface SkeletonLoaderProps {
  type?: 'page' | 'card' | 'list' | 'table' | 'dashboard' | 'form';
  rows?: number;
  loading?: boolean;
  children?: React.ReactNode;
}

/**
 * Page skeleton - full page loading state
 */
const PageSkeleton = memo(() => (
  <div style={{ padding: 24 }}>
    <Skeleton active paragraph={{ rows: 0 }} style={{ marginBottom: 24 }} />
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card>
          <Skeleton active paragraph={{ rows: 4 }} />
        </Card>
      </Col>
    </Row>
  </div>
));
PageSkeleton.displayName = 'PageSkeleton';

/**
 * Card skeleton - single card loading state
 */
const CardSkeleton = memo(() => (
  <Card>
    <Skeleton active avatar paragraph={{ rows: 3 }} />
  </Card>
));
CardSkeleton.displayName = 'CardSkeleton';

/**
 * List skeleton - list items loading state
 */
const ListSkeleton = memo(({ rows = 5 }: { rows?: number }) => (
  <Space direction="vertical" style={{ width: '100%' }} size="middle">
    {Array.from({ length: rows }).map((_, index) => (
      <Card key={index} size="small">
        <Skeleton active avatar paragraph={{ rows: 2 }} />
      </Card>
    ))}
  </Space>
));
ListSkeleton.displayName = 'ListSkeleton';

/**
 * Table skeleton - table loading state
 */
const TableSkeleton = memo(({ rows = 5 }: { rows?: number }) => (
  <div>
    {/* Table header */}
    <div style={{ 
      display: 'flex', 
      gap: 16, 
      padding: '12px 16px',
      background: '#fafafa',
      borderBottom: '1px solid #f0f0f0'
    }}>
      {Array.from({ length: 5 }).map((_, index) => (
        <Skeleton.Button 
          key={index} 
          active 
          size="small" 
          style={{ width: index === 0 ? 40 : 100 }} 
        />
      ))}
    </div>
    {/* Table rows */}
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div 
        key={rowIndex}
        style={{ 
          display: 'flex', 
          gap: 16, 
          padding: '16px',
          borderBottom: '1px solid #f0f0f0'
        }}
      >
        {Array.from({ length: 5 }).map((_, colIndex) => (
          <Skeleton.Input 
            key={colIndex} 
            active 
            size="small" 
            style={{ width: colIndex === 0 ? 40 : 100 }} 
          />
        ))}
      </div>
    ))}
  </div>
));
TableSkeleton.displayName = 'TableSkeleton';

/**
 * Dashboard skeleton - dashboard cards loading state
 */
const DashboardSkeleton = memo(() => (
  <div style={{ padding: 24 }}>
    {/* Stats cards row */}
    <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
      {Array.from({ length: 4 }).map((_, index) => (
        <Col key={index} xs={24} sm={12} lg={6}>
          <Card>
            <Skeleton active paragraph={{ rows: 2 }} />
          </Card>
        </Col>
      ))}
    </Row>
    
    {/* Charts row */}
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={16}>
        <Card>
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      </Col>
      <Col xs={24} lg={8}>
        <Card>
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      </Col>
    </Row>
  </div>
));
DashboardSkeleton.displayName = 'DashboardSkeleton';

/**
 * Form skeleton - form loading state
 */
const FormSkeleton = memo(({ rows = 4 }: { rows?: number }) => (
  <Card>
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index}>
          <Skeleton.Input active size="small" style={{ width: 100, marginBottom: 8 }} />
          <Skeleton.Input active style={{ width: '100%' }} />
        </div>
      ))}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <Skeleton.Button active />
        <Skeleton.Button active />
      </div>
    </Space>
  </Card>
));
FormSkeleton.displayName = 'FormSkeleton';

/**
 * Main Skeleton Loader component
 */
export const SkeletonLoader = memo<SkeletonLoaderProps>(({ 
  type = 'page', 
  rows = 5,
  loading = true,
  children 
}) => {
  if (!loading && children) {
    return <>{children}</>;
  }

  switch (type) {
    case 'card':
      return <CardSkeleton />;
    case 'list':
      return <ListSkeleton rows={rows} />;
    case 'table':
      return <TableSkeleton rows={rows} />;
    case 'dashboard':
      return <DashboardSkeleton />;
    case 'form':
      return <FormSkeleton rows={rows} />;
    case 'page':
    default:
      return <PageSkeleton />;
  }
});

SkeletonLoader.displayName = 'SkeletonLoader';

// Export individual skeletons for direct use
export { PageSkeleton, CardSkeleton, ListSkeleton, TableSkeleton, DashboardSkeleton, FormSkeleton };
