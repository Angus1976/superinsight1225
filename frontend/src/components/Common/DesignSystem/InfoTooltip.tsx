/**
 * InfoTooltip Component
 * 
 * Consistent info tooltip for providing contextual help.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Tooltip, Typography, Space } from 'antd';
import { 
  QuestionCircleOutlined, 
  InfoCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { TooltipPlacement } from 'antd/es/tooltip';
import styles from './InfoTooltip.module.scss';

const { Text, Paragraph } = Typography;

type TooltipType = 'info' | 'help' | 'warning' | 'success';

interface InfoTooltipProps {
  title?: string;
  content: ReactNode;
  type?: TooltipType;
  placement?: TooltipPlacement;
  trigger?: 'hover' | 'click' | 'focus';
  children?: ReactNode;
  className?: string;
}

const tooltipConfig: Record<TooltipType, {
  icon: ReactNode;
  color: string;
}> = {
  info: {
    icon: <InfoCircleOutlined />,
    color: '#1890ff',
  },
  help: {
    icon: <QuestionCircleOutlined />,
    color: '#8c8c8c',
  },
  warning: {
    icon: <ExclamationCircleOutlined />,
    color: '#faad14',
  },
  success: {
    icon: <CheckCircleOutlined />,
    color: '#52c41a',
  },
};

export const InfoTooltip = memo<InfoTooltipProps>(({
  title,
  content,
  type = 'help',
  placement = 'top',
  trigger = 'hover',
  children,
  className,
}) => {
  const config = tooltipConfig[type];
  
  const tooltipContent = (
    <div className={styles.tooltipContent}>
      {title && (
        <Text strong className={styles.tooltipTitle}>
          {title}
        </Text>
      )}
      <div className={styles.tooltipBody}>
        {typeof content === 'string' ? (
          <Paragraph className={styles.tooltipText}>{content}</Paragraph>
        ) : (
          content
        )}
      </div>
    </div>
  );
  
  return (
    <Tooltip
      title={tooltipContent}
      placement={placement}
      trigger={trigger}
      overlayClassName={styles.tooltipOverlay}
    >
      {children || (
        <span 
          className={`${styles.iconWrapper} ${className || ''}`}
          style={{ color: config.color }}
        >
          {config.icon}
        </span>
      )}
    </Tooltip>
  );
});

InfoTooltip.displayName = 'InfoTooltip';

// Inline help text with tooltip
interface HelpTextProps {
  text: string;
  tooltip: string;
  className?: string;
}

export const HelpText = memo<HelpTextProps>(({
  text,
  tooltip,
  className,
}) => {
  return (
    <Space size={4} className={className}>
      <Text type="secondary">{text}</Text>
      <InfoTooltip content={tooltip} type="help" />
    </Space>
  );
});

HelpText.displayName = 'HelpText';
