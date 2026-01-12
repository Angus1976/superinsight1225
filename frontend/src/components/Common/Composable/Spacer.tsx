/**
 * Spacer Component
 * 
 * A simple utility component for adding consistent
 * spacing between elements.
 * 
 * @module components/Common/Composable/Spacer
 * @version 1.0.0
 */

import React, { memo, useMemo } from 'react';

/**
 * Spacer component props
 */
export interface SpacerProps {
  /** Horizontal size */
  x?: number | string;
  /** Vertical size */
  y?: number | string;
  /** Both directions (shorthand) */
  size?: number | string;
  /** Flex grow to fill available space */
  flex?: boolean | number;
  /** Custom class name */
  className?: string;
  /** Custom style */
  style?: React.CSSProperties;
}

/**
 * Spacer component for adding space between elements
 */
export const Spacer = memo(function Spacer({
  x,
  y,
  size,
  flex,
  className,
  style,
}: SpacerProps): React.ReactElement {
  const computedStyle = useMemo<React.CSSProperties>(() => {
    const baseStyle: React.CSSProperties = {
      flexShrink: 0,
      ...style,
    };

    // Handle size shorthand
    const horizontalSize = x ?? size;
    const verticalSize = y ?? size;

    if (horizontalSize !== undefined) {
      baseStyle.width = typeof horizontalSize === 'number' ? `${horizontalSize}px` : horizontalSize;
    }

    if (verticalSize !== undefined) {
      baseStyle.height = typeof verticalSize === 'number' ? `${verticalSize}px` : verticalSize;
    }

    // Handle flex
    if (flex !== undefined) {
      baseStyle.flex = typeof flex === 'number' ? flex : 1;
      baseStyle.flexShrink = 1;
    }

    return baseStyle;
  }, [x, y, size, flex, style]);

  return <div className={className} style={computedStyle} aria-hidden="true" />;
});

// Convenience components for common spacing
export const HorizontalSpacer = memo(function HorizontalSpacer({ size = 16 }: { size?: number | string }) {
  return <Spacer x={size} />;
});

export const VerticalSpacer = memo(function VerticalSpacer({ size = 16 }: { size?: number | string }) {
  return <Spacer y={size} />;
});

export const FlexSpacer = memo(function FlexSpacer() {
  return <Spacer flex />;
});
