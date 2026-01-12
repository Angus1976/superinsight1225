/**
 * ResponsiveGrid Component
 * 
 * A flexible grid component that automatically adapts
 * its column layout based on viewport size.
 */

import { memo, ReactNode, CSSProperties } from 'react';
import { Row, Col } from 'antd';
import { useResponsive } from '@/hooks/useResponsive';
import styles from './ResponsiveGrid.module.scss';

interface ResponsiveColSpan {
  xs?: number;
  sm?: number;
  md?: number;
  lg?: number;
  xl?: number;
  xxl?: number;
}

interface ResponsiveGridProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  
  // Gutter (gap between columns)
  gutter?: number | [number, number];
  
  // Responsive gutter
  responsiveGutter?: boolean;
  
  // Alignment
  align?: 'top' | 'middle' | 'bottom' | 'stretch';
  justify?: 'start' | 'end' | 'center' | 'space-around' | 'space-between' | 'space-evenly';
  
  // Wrap
  wrap?: boolean;
}

interface ResponsiveGridItemProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  
  // Column span (out of 24)
  span?: number | ResponsiveColSpan;
  
  // Offset
  offset?: number | ResponsiveColSpan;
  
  // Order
  order?: number;
  
  // Push/Pull
  push?: number;
  pull?: number;
  
  // Flex
  flex?: string | number;
}

// Default responsive gutters
const getResponsiveGutter = (isMobile: boolean, isTablet: boolean): [number, number] => {
  if (isMobile) return [8, 8];
  if (isTablet) return [12, 12];
  return [16, 16];
};

export const ResponsiveGrid = memo<ResponsiveGridProps>(({
  children,
  className,
  style,
  gutter,
  responsiveGutter = true,
  align = 'top',
  justify = 'start',
  wrap = true,
}) => {
  const { isMobile, isTablet } = useResponsive();

  // Determine gutter
  const actualGutter = gutter ?? (responsiveGutter ? getResponsiveGutter(isMobile, isTablet) : [16, 16]);

  return (
    <Row
      gutter={actualGutter}
      align={align}
      justify={justify}
      wrap={wrap}
      className={`${styles.responsiveGrid} ${className || ''}`}
      style={style}
    >
      {children}
    </Row>
  );
});

ResponsiveGrid.displayName = 'ResponsiveGrid';

export const ResponsiveGridItem = memo<ResponsiveGridItemProps>(({
  children,
  className,
  style,
  span = 24,
  offset,
  order,
  push,
  pull,
  flex,
}) => {
  // Convert span to responsive object if it's a number
  const spanProps = typeof span === 'number' 
    ? { span } 
    : {
        xs: span.xs ?? 24,
        sm: span.sm ?? span.xs ?? 24,
        md: span.md ?? span.sm ?? span.xs ?? 24,
        lg: span.lg ?? span.md ?? span.sm ?? span.xs ?? 24,
        xl: span.xl ?? span.lg ?? span.md ?? span.sm ?? span.xs ?? 24,
        xxl: span.xxl ?? span.xl ?? span.lg ?? span.md ?? span.sm ?? span.xs ?? 24,
      };

  // Convert offset to responsive object if it's a number
  const offsetProps = offset !== undefined
    ? typeof offset === 'number'
      ? { offset }
      : {
          xs: offset.xs,
          sm: offset.sm,
          md: offset.md,
          lg: offset.lg,
          xl: offset.xl,
          xxl: offset.xxl,
        }
    : {};

  return (
    <Col
      {...spanProps}
      {...offsetProps}
      order={order}
      push={push}
      pull={pull}
      flex={flex}
      className={`${styles.responsiveGridItem} ${className || ''}`}
      style={style}
    >
      {children}
    </Col>
  );
});

ResponsiveGridItem.displayName = 'ResponsiveGridItem';

// Re-export presets from separate file
export { GridPresets } from './ResponsiveGridPresets';
export type { ResponsiveColSpan };

export default ResponsiveGrid;
