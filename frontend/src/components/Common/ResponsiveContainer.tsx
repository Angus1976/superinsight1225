/**
 * ResponsiveContainer Component
 * 
 * A container component that adapts its layout and styling
 * based on the current viewport size.
 */

import { memo, ReactNode, CSSProperties } from 'react';
import { useResponsive, BreakpointKey } from '@/hooks/useResponsive';
import styles from './ResponsiveContainer.module.scss';

interface ResponsiveContainerProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  
  // Padding options
  padding?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  
  // Max width options
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'xxl' | 'full';
  
  // Center content
  centered?: boolean;
  
  // Full height
  fullHeight?: boolean;
  
  // Responsive visibility
  hideOn?: BreakpointKey[];
  showOn?: BreakpointKey[];
  
  // Layout direction
  direction?: 'row' | 'column';
  
  // Gap between children
  gap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  
  // Responsive direction change
  stackOnMobile?: boolean;
  
  // Alignment
  align?: 'start' | 'center' | 'end' | 'stretch';
  justify?: 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly';
  
  // Wrap children
  wrap?: boolean;
}

const MAX_WIDTHS = {
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
  full: '100%',
};

export const ResponsiveContainer = memo<ResponsiveContainerProps>(({
  children,
  className,
  style,
  padding = 'md',
  maxWidth = 'full',
  centered = false,
  fullHeight = false,
  hideOn = [],
  showOn = [],
  direction = 'column',
  gap = 'md',
  stackOnMobile = false,
  align = 'stretch',
  justify = 'start',
  wrap = false,
}) => {
  const { breakpoint, isMobile } = useResponsive();

  // Check visibility
  if (hideOn.includes(breakpoint)) {
    return null;
  }
  
  if (showOn.length > 0 && !showOn.includes(breakpoint)) {
    return null;
  }

  // Determine actual direction
  const actualDirection = stackOnMobile && isMobile ? 'column' : direction;

  const containerClasses = [
    styles.responsiveContainer,
    styles[`padding-${padding}`],
    styles[`gap-${gap}`],
    styles[`direction-${actualDirection}`],
    styles[`align-${align}`],
    styles[`justify-${justify}`],
    centered && styles.centered,
    fullHeight && styles.fullHeight,
    wrap && styles.wrap,
    className,
  ].filter(Boolean).join(' ');

  const containerStyle: CSSProperties = {
    ...style,
    maxWidth: maxWidth === 'full' ? '100%' : MAX_WIDTHS[maxWidth],
  };

  return (
    <div className={containerClasses} style={containerStyle}>
      {children}
    </div>
  );
});

ResponsiveContainer.displayName = 'ResponsiveContainer';

export default ResponsiveContainer;
