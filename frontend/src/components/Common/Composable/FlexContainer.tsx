/**
 * FlexContainer Component
 * 
 * A reusable flexbox container component with common
 * layout patterns and responsive support.
 * 
 * @module components/Common/Composable/FlexContainer
 * @version 1.0.0
 */

import React, { type ReactNode, memo, useMemo } from 'react';
import styles from './FlexContainer.module.scss';

/**
 * FlexContainer component props
 */
export interface FlexContainerProps {
  /** Child elements */
  children: ReactNode;
  /** Flex direction */
  direction?: 'row' | 'column' | 'row-reverse' | 'column-reverse';
  /** Justify content */
  justify?: 'start' | 'end' | 'center' | 'between' | 'around' | 'evenly';
  /** Align items */
  align?: 'start' | 'end' | 'center' | 'stretch' | 'baseline';
  /** Flex wrap */
  wrap?: 'nowrap' | 'wrap' | 'wrap-reverse';
  /** Gap between items */
  gap?: number | string | [number | string, number | string];
  /** Padding */
  padding?: number | string | [number | string, number | string, number | string, number | string];
  /** Full width */
  fullWidth?: boolean;
  /** Full height */
  fullHeight?: boolean;
  /** Inline flex */
  inline?: boolean;
  /** Custom class name */
  className?: string;
  /** Custom style */
  style?: React.CSSProperties;
  /** HTML element type */
  as?: keyof JSX.IntrinsicElements;
  /** Click handler */
  onClick?: () => void;
  /** Responsive direction (column on mobile) */
  responsive?: boolean;
  /** Breakpoint for responsive */
  breakpoint?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

/**
 * Map justify prop to CSS value
 */
const justifyMap: Record<string, string> = {
  start: 'flex-start',
  end: 'flex-end',
  center: 'center',
  between: 'space-between',
  around: 'space-around',
  evenly: 'space-evenly',
};

/**
 * Map align prop to CSS value
 */
const alignMap: Record<string, string> = {
  start: 'flex-start',
  end: 'flex-end',
  center: 'center',
  stretch: 'stretch',
  baseline: 'baseline',
};

/**
 * FlexContainer component for flexible layouts
 */
export const FlexContainer = memo(function FlexContainer({
  children,
  direction = 'row',
  justify = 'start',
  align = 'stretch',
  wrap = 'nowrap',
  gap,
  padding,
  fullWidth = false,
  fullHeight = false,
  inline = false,
  className,
  style,
  as: Component = 'div',
  onClick,
  responsive = false,
  breakpoint = 'md',
}: FlexContainerProps): React.ReactElement {
  // Build style object
  const computedStyle = useMemo<React.CSSProperties>(() => {
    const baseStyle: React.CSSProperties = {
      display: inline ? 'inline-flex' : 'flex',
      flexDirection: direction,
      justifyContent: justifyMap[justify],
      alignItems: alignMap[align],
      flexWrap: wrap,
      ...style,
    };

    // Handle gap
    if (gap !== undefined) {
      if (Array.isArray(gap)) {
        baseStyle.rowGap = typeof gap[0] === 'number' ? `${gap[0]}px` : gap[0];
        baseStyle.columnGap = typeof gap[1] === 'number' ? `${gap[1]}px` : gap[1];
      } else {
        baseStyle.gap = typeof gap === 'number' ? `${gap}px` : gap;
      }
    }

    // Handle padding
    if (padding !== undefined) {
      if (Array.isArray(padding)) {
        baseStyle.padding = padding
          .map(p => (typeof p === 'number' ? `${p}px` : p))
          .join(' ');
      } else {
        baseStyle.padding = typeof padding === 'number' ? `${padding}px` : padding;
      }
    }

    // Handle full width/height
    if (fullWidth) {
      baseStyle.width = '100%';
    }
    if (fullHeight) {
      baseStyle.height = '100%';
    }

    return baseStyle;
  }, [direction, justify, align, wrap, gap, padding, fullWidth, fullHeight, inline, style]);

  // Build class names
  const classNames = useMemo(() => {
    const classes = [styles.flexContainer];
    if (responsive) {
      classes.push(styles.responsive);
      classes.push(styles[`responsive-${breakpoint}`]);
    }
    if (className) {
      classes.push(className);
    }
    return classes.join(' ');
  }, [responsive, breakpoint, className]);

  return (
    <Component className={classNames} style={computedStyle} onClick={onClick}>
      {children}
    </Component>
  );
});

// Convenience components for common patterns
export const Row = memo(function Row(props: Omit<FlexContainerProps, 'direction'>) {
  return <FlexContainer {...props} direction="row" />;
});

export const Column = memo(function Column(props: Omit<FlexContainerProps, 'direction'>) {
  return <FlexContainer {...props} direction="column" />;
});

export const Center = memo(function Center(props: Omit<FlexContainerProps, 'justify' | 'align'>) {
  return <FlexContainer {...props} justify="center" align="center" />;
});

export const SpaceBetween = memo(function SpaceBetween(props: Omit<FlexContainerProps, 'justify'>) {
  return <FlexContainer {...props} justify="between" />;
});
