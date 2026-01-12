/**
 * PageHeader Component
 * 
 * Consistent page header with title, description, and actions.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Typography, Space, Breadcrumb, Divider } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import styles from './PageHeader.module.scss';

const { Title, Text } = Typography;

interface BreadcrumbItem {
  title: string;
  path?: string;
  icon?: ReactNode;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: ReactNode;
  extra?: ReactNode;
  tags?: ReactNode;
  className?: string;
  compact?: boolean;
}

export const PageHeader = memo<PageHeaderProps>(({
  title,
  subtitle,
  description,
  breadcrumbs,
  actions,
  extra,
  tags,
  className,
  compact = false,
}) => {
  const breadcrumbItems = breadcrumbs?.map((item, index) => ({
    key: index,
    title: item.path ? (
      <Link to={item.path}>
        <Space size={4}>
          {item.icon}
          <span>{item.title}</span>
        </Space>
      </Link>
    ) : (
      <Space size={4}>
        {item.icon}
        <span>{item.title}</span>
      </Space>
    ),
  }));

  return (
    <div className={`${styles.pageHeader} ${compact ? styles.compact : ''} ${className || ''}`}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb
          className={styles.breadcrumb}
          items={[
            {
              key: 'home',
              title: (
                <Link to="/">
                  <HomeOutlined />
                </Link>
              ),
            },
            ...(breadcrumbItems || []),
          ]}
        />
      )}
      
      <div className={styles.headerContent}>
        <div className={styles.titleSection}>
          <div className={styles.titleRow}>
            <Title level={compact ? 4 : 3} className={styles.title}>
              {title}
            </Title>
            {tags && <div className={styles.tags}>{tags}</div>}
          </div>
          
          {subtitle && (
            <Text type="secondary" className={styles.subtitle}>
              {subtitle}
            </Text>
          )}
          
          {description && (
            <Text type="secondary" className={styles.description}>
              {description}
            </Text>
          )}
        </div>
        
        {actions && (
          <div className={styles.actions}>
            <Space size="middle">{actions}</Space>
          </div>
        )}
      </div>
      
      {extra && (
        <>
          <Divider className={styles.divider} />
          <div className={styles.extra}>{extra}</div>
        </>
      )}
    </div>
  );
});

PageHeader.displayName = 'PageHeader';
