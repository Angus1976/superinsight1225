/**
 * GridLayout Component
 * 
 * A reusable CSS Grid layout component with responsive
 * column support and common grid patterns.
 * 
 * @module components/Common/Composable/GridLayout
 * @version 1.0.0
 */

import React, { type ReactNode, memo, useMemo } from 'react';
import styles from './GridLayout.module.scss';

/**
 * Responsive column configuration
 */
export interface ResponsiveColumns {
  xs?: number;
  sm?: number;
  md?: number;
  lg?: number;
  xl?: number;
  xxl?: number;
}

/**
 * GridLayout component props
 */
export interface GridLayoutProps {
  /** Child elements */
  children: ReactNode;
  /** Number of columns (or responsive config) */
  columns?: number | ResponsiveColumns;
  /** Gap between items */
  gap?: number | string | [number | string, number | string];
  /** Row height */
  rowHeight?: number | string | 'auto';
  /** Align items */
  alignItems?: 'start' | 'end' | 'center' | 'stretch';
  /** Justify items */
  justifyItems?: 'start' | 'end' | 'center' | 'stretch';
  /** Padding */
  padding?: number | string;
  /** Full width */
  fullWidth?: boolean;
  /** Custom class name */
  className?: string;
  /** Custom style */
  style?: React.CSSProperties;
  /** Auto-fit columns */
  autoFit?: boolean;
  /** Minimum column width for auto-fit */
  minColumnWidth?: number | string;
  /** Maximum column width for auto-fit */
  maxColumnWidth?: number | string;
}

/**
 * GridLayout component for grid-based layouts
 */
export const GridLayout = memo(function GridLayout({
  children,
  columns = 3,
  gap = 16,
  rowHeight = 'auto',
  alignItems = 'stretch',
  justifyItems = 'stretch',
  padding,
  fullWidth = true,
  className,
  style,
  autoFit = false,
  minColumnWidth = 200,
  maxColumnWidth = '1fr',
}: GridLayoutProps): React.ReactElement {
  // Build style object
  const computedStyle = useMemo<React.CSSProperties>(() => {
    const baseStyle: React.CSSProperties = {
      display: 'grid',
      alignItems,
      justifyItems,
      ...style,
    };

    // Handle columns
    if (autoFit) {
      const minWidth = typeof minColumnWidth === 'number' ? `${minColumnWidth}px` : minColumnWidth;
      const maxWidth = typeof maxColumnWidth === 'number' ? `${maxColumnWidth}px` : maxColumnWidth;
      baseStyle.gridTemplateColumns = `repeat(auto-fit, minmax(${minWidth}, ${maxWidth}))`;
    } else if (typeof columns === 'number') {
      baseStyle.gridTemplateColumns = `repeat(${columns}, 1fr)`;
    }

    // Handle gap
    if (gap !== undefined) {
      if (Array.isArray(gap)) {
        baseStyle.rowGap = typeof gap[0] === 'number' ? `${gap[0]}px` : gap[0];
        baseStyle.columnGap = typeof gap[1] === 'number' ? `${gap[1]}px` : gap[1];
      } else {
        baseStyle.gap = typeof gap === 'number' ? `${gap}px` : gap;
      }
    }

    // Handle row height
    if (rowHeight !== 'auto') {
      baseStyle.gridAutoRows = typeof rowHeight === 'number' ? `${rowHeight}px` : rowHeight;
    }

    // Handle padding
    if (padding !== undefined) {
      baseStyle.padding = typeof padding === 'number' ? `${padding}px` : padding;
    }

    // Handle full width
    if (fullWidth) {
      baseStyle.width = '100%';
    }

    return baseStyle;
  }, [columns, gap, rowHeight, alignItems, justifyItems, padding, fullWidth, autoFit, minColumnWidth, maxColumnWidth, style]);

  // Build class names for responsive columns
  const classNames = useMemo(() => {
    const classes = [styles.gridLayout];
    
    if (typeof columns === 'object') {
      Object.entries(columns).forEach(([breakpoint, cols]) => {
        classes.push(styles[`cols-${breakpoint}-${cols}`]);
      });
    }
    
    if (className) {
      classes.push(className);
    }
    
    return classes.join(' ');
  }, [columns, className]);

  return (
    <div className={classNames} style={computedStyle}>
      {children}
    </div>
  );
});

/**
 * GridItem component for grid children with span support
 */
export interface GridItemProps {
  children: ReactNode;
  colSpan?: number;
  rowSpan?: number;
  className?: string;
  style?: React.CSSProperties;
}

export const GridItem = memo(function GridItem({
  children,
  colSpan,
  rowSpan,
  className,
  style,
}: GridItemProps): React.ReactElement {
  const computedStyle = useMemo<React.CSSProperties>(() => {
    const baseStyle: React.CSSProperties = { ...style };
    
    if (colSpan) {
      baseStyle.gridColumn = `span ${colSpan}`;
    }
    if (rowSpan) {
      baseStyle.gridRow = `span ${rowSpan}`;
    }
    
    return baseStyle;
  }, [colSpan, rowSpan, style]);

  return (
    <div className={className} style={computedStyle}>
      {children}
    </div>
  );
});
