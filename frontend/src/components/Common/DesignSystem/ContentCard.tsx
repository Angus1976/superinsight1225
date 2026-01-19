/**
 * ContentCard Component
 * 
 * Consistent card component for content sections.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Card, Typography, Space, Tooltip, Button } from 'antd';
import { ReloadOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import styles from './ContentCard.module.scss';

const { Title, Text } = Typography;

interface ContentCardProps {
  title?: string;
  subtitle?: string;
  tooltip?: string;
  icon?: ReactNode;
  extra?: ReactNode;
  actions?: ReactNode;
  loading?: boolean;
  refreshable?: boolean;
  onRefresh?: () => void;
  children: ReactNode;
  className?: string;
  bodyStyle?: React.CSSProperties;
  bordered?: boolean;
  hoverable?: boolean;
  size?: 'default' | 'small';
  fullHeight?: boolean;
}

export const ContentCard = memo<ContentCardProps>(({
  title,
  subtitle,
  tooltip,
  icon,
  extra,
  actions,
  loading = false,
  refreshable = false,
  onRefresh,
  children,
  className,
  bodyStyle,
  bordered = false,
  hoverable = false,
  size = 'default',
  fullHeight = false,
}) => {
  const { t } = useTranslation('common');

  const cardTitle = title ? (
    <div className={styles.cardHeader}>
      <div className={styles.titleSection}>
        {icon && <span className={styles.icon}>{icon}</span>}
        <div className={styles.titleContent}>
          <Space size={4}>
            <Title level={5} className={styles.title}>
              {title}
            </Title>
            {tooltip && (
              <Tooltip title={tooltip}>
                <QuestionCircleOutlined className={styles.tooltipIcon} />
              </Tooltip>
            )}
          </Space>
          {subtitle && (
            <Text type="secondary" className={styles.subtitle}>
              {subtitle}
            </Text>
          )}
        </div>
      </div>
      
      <div className={styles.headerActions}>
        {refreshable && (
          <Tooltip title={t('refresh')}>
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined spin={loading} />}
              onClick={onRefresh}
              disabled={loading}
            />
          </Tooltip>
        )}
        {extra}
      </div>
    </div>
  ) : null;

  return (
    <Card
      title={cardTitle}
      loading={loading}
      className={`${styles.contentCard} ${hoverable ? styles.hoverable : ''} ${fullHeight ? styles.fullHeight : ''} ${className || ''}`}
      bodyStyle={bodyStyle}
      bordered={bordered}
      size={size}
      actions={actions ? [actions] : undefined}
    >
      {children}
    </Card>
  );
});

ContentCard.displayName = 'ContentCard';
