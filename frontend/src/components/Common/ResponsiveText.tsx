/**
 * ResponsiveText Component
 * 
 * Typography component that adapts font size and styling
 * based on viewport size for optimal readability.
 */

import { memo, ReactNode, CSSProperties } from 'react';
import { Typography } from 'antd';
import { useResponsive } from '@/hooks/useResponsive';
import styles from './ResponsiveText.module.scss';

const { Title, Text, Paragraph } = Typography;

type TextVariant = 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'body' | 'caption' | 'label';
type TextAlign = 'left' | 'center' | 'right' | 'justify';

interface ResponsiveTextProps {
  children: ReactNode;
  variant?: TextVariant;
  className?: string;
  style?: CSSProperties;
  
  // Typography options
  type?: 'secondary' | 'success' | 'warning' | 'danger';
  strong?: boolean;
  italic?: boolean;
  underline?: boolean;
  delete?: boolean;
  code?: boolean;
  mark?: boolean;
  
  // Layout options
  align?: TextAlign;
  
  // Truncation
  ellipsis?: boolean | { rows?: number; expandable?: boolean };
  
  // Copyable
  copyable?: boolean;
  
  // Custom element
  as?: 'span' | 'div' | 'p';
}

// Font size mappings for different variants and breakpoints
const VARIANT_STYLES: Record<TextVariant, {
  desktop: { fontSize: number; lineHeight: number };
  tablet: { fontSize: number; lineHeight: number };
  mobile: { fontSize: number; lineHeight: number };
  weight: number;
}> = {
  h1: {
    desktop: { fontSize: 38, lineHeight: 1.2 },
    tablet: { fontSize: 32, lineHeight: 1.25 },
    mobile: { fontSize: 26, lineHeight: 1.3 },
    weight: 700,
  },
  h2: {
    desktop: { fontSize: 30, lineHeight: 1.25 },
    tablet: { fontSize: 26, lineHeight: 1.3 },
    mobile: { fontSize: 22, lineHeight: 1.35 },
    weight: 700,
  },
  h3: {
    desktop: { fontSize: 24, lineHeight: 1.3 },
    tablet: { fontSize: 22, lineHeight: 1.35 },
    mobile: { fontSize: 18, lineHeight: 1.4 },
    weight: 600,
  },
  h4: {
    desktop: { fontSize: 20, lineHeight: 1.35 },
    tablet: { fontSize: 18, lineHeight: 1.4 },
    mobile: { fontSize: 16, lineHeight: 1.45 },
    weight: 600,
  },
  h5: {
    desktop: { fontSize: 16, lineHeight: 1.4 },
    tablet: { fontSize: 15, lineHeight: 1.45 },
    mobile: { fontSize: 14, lineHeight: 1.5 },
    weight: 600,
  },
  body: {
    desktop: { fontSize: 14, lineHeight: 1.5714 },
    tablet: { fontSize: 14, lineHeight: 1.5714 },
    mobile: { fontSize: 14, lineHeight: 1.5714 },
    weight: 400,
  },
  caption: {
    desktop: { fontSize: 12, lineHeight: 1.6667 },
    tablet: { fontSize: 12, lineHeight: 1.6667 },
    mobile: { fontSize: 12, lineHeight: 1.6667 },
    weight: 400,
  },
  label: {
    desktop: { fontSize: 14, lineHeight: 1.5 },
    tablet: { fontSize: 14, lineHeight: 1.5 },
    mobile: { fontSize: 13, lineHeight: 1.5 },
    weight: 500,
  },
};

export const ResponsiveText = memo<ResponsiveTextProps>(({
  children,
  variant = 'body',
  className,
  style,
  type,
  strong,
  italic,
  underline,
  delete: deleteText,
  code,
  mark,
  align = 'left',
  ellipsis,
  copyable,
  as,
}) => {
  const { isMobile, isTablet } = useResponsive();

  // Get responsive styles
  const variantConfig = VARIANT_STYLES[variant];
  const responsiveStyle = isMobile 
    ? variantConfig.mobile 
    : isTablet 
      ? variantConfig.tablet 
      : variantConfig.desktop;

  const combinedStyle: CSSProperties = {
    fontSize: responsiveStyle.fontSize,
    lineHeight: responsiveStyle.lineHeight,
    fontWeight: strong ? 700 : variantConfig.weight,
    textAlign: align,
    ...style,
  };

  const combinedClassName = `${styles.responsiveText} ${styles[variant]} ${className || ''}`;

  // Render heading variants
  if (variant.startsWith('h')) {
    const level = parseInt(variant.charAt(1)) as 1 | 2 | 3 | 4 | 5;
    return (
      <Title
        level={level}
        type={type}
        italic={italic}
        underline={underline}
        delete={deleteText}
        code={code}
        mark={mark}
        ellipsis={ellipsis}
        copyable={copyable}
        className={combinedClassName}
        style={combinedStyle}
      >
        {children}
      </Title>
    );
  }

  // Render paragraph for body text
  if (variant === 'body' && !as) {
    return (
      <Paragraph
        type={type}
        strong={strong}
        italic={italic}
        underline={underline}
        delete={deleteText}
        code={code}
        mark={mark}
        ellipsis={ellipsis}
        copyable={copyable}
        className={combinedClassName}
        style={combinedStyle}
      >
        {children}
      </Paragraph>
    );
  }

  // Render text for other variants
  return (
    <Text
      type={type}
      strong={strong}
      italic={italic}
      underline={underline}
      delete={deleteText}
      code={code}
      mark={mark}
      ellipsis={ellipsis === true ? true : undefined}
      copyable={copyable}
      className={combinedClassName}
      style={combinedStyle}
    >
      {children}
    </Text>
  );
});

ResponsiveText.displayName = 'ResponsiveText';

export default ResponsiveText;
