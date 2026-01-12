/**
 * SectionTitle Component
 * 
 * Consistent section title for organizing content.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Typography, Space, Tooltip, Divider } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import styles from './SectionTitle.module.scss';

const { Title, Text } = Typography;

interface SectionTitleProps {
  title: string;
  subtitle?: string;
  tooltip?: string;
  icon?: ReactNode;
  extra?: ReactNode;
  level?: 1 | 2 | 3 | 4 | 5;
  divider?: boolean;
  className?: string;
}

export const SectionTitle = memo<SectionTitleProps>(({
  title,
  subtitle,
  tooltip,
  icon,
  extra,
  level = 4,
  divider = false,
  className,
}) => {
  return (
    <div className={`${styles.sectionTitle} ${className || ''}`}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <Space size={8} align="center">
            {icon && <span className={styles.icon}>{icon}</span>}
            <Title level={level} className={styles.title}>
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
        
        {extra && <div className={styles.extra}>{extra}</div>}
      </div>
      
      {divider && <Divider className={styles.divider} />}
    </div>
  );
});

SectionTitle.displayName = 'SectionTitle';

// Subsection title for nested content
interface SubsectionTitleProps {
  title: string;
  extra?: ReactNode;
  className?: string;
}

export const SubsectionTitle = memo<SubsectionTitleProps>(({
  title,
  extra,
  className,
}) => {
  return (
    <div className={`${styles.subsectionTitle} ${className || ''}`}>
      <Text strong className={styles.subsectionText}>{title}</Text>
      {extra && <div className={styles.extra}>{extra}</div>}
    </div>
  );
});

SubsectionTitle.displayName = 'SubsectionTitle';
