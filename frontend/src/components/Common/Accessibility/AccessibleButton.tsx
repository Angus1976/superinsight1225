/**
 * AccessibleButton Component
 * 
 * Fully accessible button with proper ARIA attributes and keyboard support.
 * WCAG 2.1 Success Criteria 2.1.1, 4.1.2
 */

import { memo, forwardRef, ReactNode, ButtonHTMLAttributes, useCallback } from 'react';
import { Button, Tooltip } from 'antd';
import type { ButtonProps } from 'antd';
import { useLiveRegion } from './LiveRegion';

interface AccessibleButtonProps extends Omit<ButtonProps, 'aria-label'> {
  /** Accessible label for screen readers */
  accessibleLabel?: string;
  /** Description for screen readers */
  accessibleDescription?: string;
  /** Tooltip text (also used as accessible label if not provided) */
  tooltip?: string;
  /** Whether the button controls an expanded element */
  expanded?: boolean;
  /** ID of the element this button controls */
  controls?: string;
  /** Whether the button is pressed (for toggle buttons) */
  pressed?: boolean;
  /** Whether to announce action to screen readers */
  announceOnClick?: string;
  /** Icon element */
  icon?: ReactNode;
  /** Children content */
  children?: ReactNode;
}

export const AccessibleButton = memo(forwardRef<HTMLButtonElement, AccessibleButtonProps>(({
  accessibleLabel,
  accessibleDescription,
  tooltip,
  expanded,
  controls,
  pressed,
  announceOnClick,
  icon,
  children,
  onClick,
  disabled,
  loading,
  ...props
}, ref) => {
  const { announcePolite } = useLiveRegion();

  // Determine the accessible name
  const ariaLabel = accessibleLabel || tooltip || (typeof children === 'string' ? children : undefined);

  // Handle click with announcement
  const handleClick = useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    if (announceOnClick) {
      announcePolite(announceOnClick);
    }
    onClick?.(e);
  }, [onClick, announceOnClick, announcePolite]);

  const button = (
    <Button
      ref={ref}
      icon={icon}
      onClick={handleClick}
      disabled={disabled}
      loading={loading}
      aria-label={ariaLabel}
      aria-describedby={accessibleDescription ? `${props.id}-desc` : undefined}
      aria-expanded={expanded}
      aria-controls={controls}
      aria-pressed={pressed}
      aria-disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {children}
      {accessibleDescription && (
        <span id={`${props.id}-desc`} className="sr-only">
          {accessibleDescription}
        </span>
      )}
    </Button>
  );

  if (tooltip) {
    return (
      <Tooltip title={tooltip}>
        {button}
      </Tooltip>
    );
  }

  return button;
}));

AccessibleButton.displayName = 'AccessibleButton';

// ============================================
// Icon Button Variant
// ============================================

interface AccessibleIconButtonProps extends Omit<AccessibleButtonProps, 'children'> {
  /** Required accessible label for icon-only buttons */
  accessibleLabel: string;
}

export const AccessibleIconButton = memo(forwardRef<HTMLButtonElement, AccessibleIconButtonProps>(({
  accessibleLabel,
  icon,
  ...props
}, ref) => (
  <AccessibleButton
    ref={ref}
    icon={icon}
    accessibleLabel={accessibleLabel}
    type="text"
    {...props}
  />
)));

AccessibleIconButton.displayName = 'AccessibleIconButton';

// ============================================
// Toggle Button Variant
// ============================================

interface AccessibleToggleButtonProps extends Omit<AccessibleButtonProps, 'pressed'> {
  /** Whether the toggle is active */
  isActive: boolean;
  /** Label when active */
  activeLabel?: string;
  /** Label when inactive */
  inactiveLabel?: string;
}

export const AccessibleToggleButton = memo(forwardRef<HTMLButtonElement, AccessibleToggleButtonProps>(({
  isActive,
  activeLabel,
  inactiveLabel,
  accessibleLabel,
  children,
  ...props
}, ref) => {
  const label = isActive 
    ? (activeLabel || accessibleLabel) 
    : (inactiveLabel || accessibleLabel);

  return (
    <AccessibleButton
      ref={ref}
      pressed={isActive}
      accessibleLabel={label}
      type={isActive ? 'primary' : 'default'}
      {...props}
    >
      {children}
    </AccessibleButton>
  );
}));

AccessibleToggleButton.displayName = 'AccessibleToggleButton';

export default AccessibleButton;
