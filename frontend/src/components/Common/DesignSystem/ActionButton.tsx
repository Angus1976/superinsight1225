/**
 * ActionButton Component
 * 
 * Consistent action button with various styles and states.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Button, Tooltip, Space } from 'antd';
import type { ButtonProps } from 'antd';
import styles from './ActionButton.module.scss';

type ButtonVariant = 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'ghost' | 'link';

interface ActionButtonProps extends Omit<ButtonProps, 'type' | 'variant'> {
  variant?: ButtonVariant;
  icon?: ReactNode;
  tooltip?: string;
  label?: string;
  compact?: boolean;
  fullWidth?: boolean;
}

const getButtonType = (variant: ButtonVariant): ButtonProps['type'] => {
  switch (variant) {
    case 'primary':
      return 'primary';
    case 'ghost':
      return 'text';
    case 'link':
      return 'link';
    default:
      return 'default';
  }
};

const getButtonDanger = (variant: ButtonVariant): boolean => {
  return variant === 'danger';
};

export const ActionButton = memo<ActionButtonProps>(({
  variant = 'secondary',
  icon,
  tooltip,
  label,
  compact = false,
  fullWidth = false,
  className,
  children,
  ...props
}) => {
  const buttonType = getButtonType(variant);
  const isDanger = getButtonDanger(variant);
  
  const buttonContent = (
    <Button
      type={buttonType}
      danger={isDanger}
      icon={icon}
      className={`
        ${styles.actionButton}
        ${styles[variant]}
        ${compact ? styles.compact : ''}
        ${fullWidth ? styles.fullWidth : ''}
        ${className || ''}
      `}
      {...props}
    >
      {label || children}
    </Button>
  );
  
  if (tooltip) {
    return (
      <Tooltip title={tooltip}>
        {buttonContent}
      </Tooltip>
    );
  }
  
  return buttonContent;
});

ActionButton.displayName = 'ActionButton';

// Button Group for consistent action grouping
interface ActionButtonGroupProps {
  children: ReactNode;
  align?: 'left' | 'center' | 'right';
  spacing?: 'small' | 'middle' | 'large';
  wrap?: boolean;
  className?: string;
}

export const ActionButtonGroup = memo<ActionButtonGroupProps>(({
  children,
  align = 'left',
  spacing = 'middle',
  wrap = true,
  className,
}) => {
  return (
    <div 
      className={`
        ${styles.buttonGroup}
        ${styles[`align-${align}`]}
        ${className || ''}
      `}
    >
      <Space size={spacing} wrap={wrap}>
        {children}
      </Space>
    </div>
  );
});

ActionButtonGroup.displayName = 'ActionButtonGroup';
