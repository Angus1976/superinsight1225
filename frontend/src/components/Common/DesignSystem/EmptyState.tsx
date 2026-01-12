/**
 * EmptyState Component
 * 
 * Consistent empty state display for when there's no data.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Empty, Button, Typography, Space } from 'antd';
import {
  InboxOutlined,
  FileSearchOutlined,
  FolderOpenOutlined,
  SearchOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import styles from './EmptyState.module.scss';

const { Text, Title } = Typography;

type EmptyType = 'default' | 'search' | 'folder' | 'data' | 'custom';

interface EmptyStateProps {
  type?: EmptyType;
  title?: string;
  description?: string;
  icon?: ReactNode;
  image?: string;
  action?: {
    label: string;
    onClick: () => void;
    icon?: ReactNode;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  size?: 'small' | 'default' | 'large';
  className?: string;
}

const emptyConfig: Record<EmptyType, {
  icon: ReactNode;
  defaultTitle: string;
  defaultDescription: string;
}> = {
  default: {
    icon: <InboxOutlined />,
    defaultTitle: '暂无数据',
    defaultDescription: '当前没有可显示的内容',
  },
  search: {
    icon: <SearchOutlined />,
    defaultTitle: '未找到结果',
    defaultDescription: '尝试调整搜索条件或筛选器',
  },
  folder: {
    icon: <FolderOpenOutlined />,
    defaultTitle: '文件夹为空',
    defaultDescription: '此文件夹中没有任何内容',
  },
  data: {
    icon: <FileSearchOutlined />,
    defaultTitle: '暂无数据',
    defaultDescription: '开始添加数据以查看内容',
  },
  custom: {
    icon: <InboxOutlined />,
    defaultTitle: '',
    defaultDescription: '',
  },
};

export const EmptyState = memo<EmptyStateProps>(({
  type = 'default',
  title,
  description,
  icon,
  image,
  action,
  secondaryAction,
  size = 'default',
  className,
}) => {
  const config = emptyConfig[type];
  const displayTitle = title || config.defaultTitle;
  const displayDescription = description || config.defaultDescription;
  const displayIcon = icon || config.icon;
  
  return (
    <div className={`${styles.emptyState} ${styles[size]} ${className || ''}`}>
      <Empty
        image={image || (
          <div className={styles.iconWrapper}>
            {displayIcon}
          </div>
        )}
        imageStyle={{ height: 'auto' }}
        description={null}
      >
        <div className={styles.content}>
          {displayTitle && (
            <Title level={size === 'small' ? 5 : 4} className={styles.title}>
              {displayTitle}
            </Title>
          )}
          
          {displayDescription && (
            <Text type="secondary" className={styles.description}>
              {displayDescription}
            </Text>
          )}
          
          {(action || secondaryAction) && (
            <Space size="middle" className={styles.actions}>
              {action && (
                <Button
                  type="primary"
                  icon={action.icon || <PlusOutlined />}
                  onClick={action.onClick}
                >
                  {action.label}
                </Button>
              )}
              {secondaryAction && (
                <Button onClick={secondaryAction.onClick}>
                  {secondaryAction.label}
                </Button>
              )}
            </Space>
          )}
        </div>
      </Empty>
    </div>
  );
});

EmptyState.displayName = 'EmptyState';

// Predefined empty states for common use cases
export const SearchEmptyState = memo<Omit<EmptyStateProps, 'type'>>(props => (
  <EmptyState type="search" {...props} />
));
SearchEmptyState.displayName = 'SearchEmptyState';

export const FolderEmptyState = memo<Omit<EmptyStateProps, 'type'>>(props => (
  <EmptyState type="folder" {...props} />
));
FolderEmptyState.displayName = 'FolderEmptyState';

export const DataEmptyState = memo<Omit<EmptyStateProps, 'type'>>(props => (
  <EmptyState type="data" {...props} />
));
DataEmptyState.displayName = 'DataEmptyState';
