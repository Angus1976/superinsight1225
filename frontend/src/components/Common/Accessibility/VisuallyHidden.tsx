/**
 * VisuallyHidden Component
 * 
 * Hides content visually while keeping it accessible to screen readers.
 * WCAG 2.1 - Provides accessible names and descriptions
 */

import { memo, ReactNode, CSSProperties } from 'react';

interface VisuallyHiddenProps {
  children: ReactNode;
  as?: keyof JSX.IntrinsicElements;
  focusable?: boolean;
  id?: string;
  className?: string;
}

const visuallyHiddenStyles: CSSProperties = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
};

const focusableStyles: CSSProperties = {
  ...visuallyHiddenStyles,
};

export const VisuallyHidden = memo<VisuallyHiddenProps>(({
  children,
  as: Component = 'span',
  focusable = false,
  id,
  className,
}) => {
  const styles = focusable ? focusableStyles : visuallyHiddenStyles;
  
  // For focusable elements, show on focus
  const focusableClassName = focusable ? 'sr-only-focusable' : 'sr-only';
  
  return (
    <Component
      style={!focusable ? styles : undefined}
      className={`${focusableClassName} ${className || ''}`}
      id={id}
    >
      {children}
    </Component>
  );
});

VisuallyHidden.displayName = 'VisuallyHidden';

// ============================================
// Utility Components
// ============================================

/**
 * Screen reader only text
 */
export const SrOnly = memo<{ children: ReactNode; id?: string }>(({ children, id }) => (
  <VisuallyHidden id={id}>{children}</VisuallyHidden>
));
SrOnly.displayName = 'SrOnly';

/**
 * Accessible label for icons
 */
interface IconLabelProps {
  label: string;
  id?: string;
}

export const IconLabel = memo<IconLabelProps>(({ label, id }) => (
  <VisuallyHidden id={id}>{label}</VisuallyHidden>
));
IconLabel.displayName = 'IconLabel';

/**
 * Accessible description
 */
interface AccessibleDescriptionProps {
  id: string;
  children: ReactNode;
}

export const AccessibleDescription = memo<AccessibleDescriptionProps>(({ id, children }) => (
  <VisuallyHidden id={id}>{children}</VisuallyHidden>
));
AccessibleDescription.displayName = 'AccessibleDescription';

export default VisuallyHidden;
