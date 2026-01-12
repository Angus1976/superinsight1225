/**
 * SuperInsight Design System - Theme Configuration
 * 
 * Provides consistent design tokens and theme configuration
 * for beautiful and consistent UI across the application.
 */

import type { ThemeConfig } from 'antd';

// Design Tokens - Core visual language
export const designTokens = {
  // Brand Colors
  colors: {
    primary: '#1890ff',
    primaryHover: '#40a9ff',
    primaryActive: '#096dd9',
    primaryLight: '#e6f7ff',
    
    success: '#52c41a',
    successHover: '#73d13d',
    successActive: '#389e0d',
    successLight: '#f6ffed',
    
    warning: '#faad14',
    warningHover: '#ffc53d',
    warningActive: '#d48806',
    warningLight: '#fffbe6',
    
    error: '#ff4d4f',
    errorHover: '#ff7875',
    errorActive: '#d9363e',
    errorLight: '#fff2f0',
    
    info: '#1890ff',
    infoLight: '#e6f7ff',
    
    // Neutral Colors
    neutral: {
      title: 'rgba(0, 0, 0, 0.88)',
      text: 'rgba(0, 0, 0, 0.88)',
      textSecondary: 'rgba(0, 0, 0, 0.65)',
      textTertiary: 'rgba(0, 0, 0, 0.45)',
      textDisabled: 'rgba(0, 0, 0, 0.25)',
      border: '#d9d9d9',
      borderSecondary: '#f0f0f0',
      fill: 'rgba(0, 0, 0, 0.04)',
      fillSecondary: 'rgba(0, 0, 0, 0.06)',
      fillTertiary: 'rgba(0, 0, 0, 0.08)',
      background: '#ffffff',
      backgroundSecondary: '#fafafa',
      backgroundTertiary: '#f5f5f5',
    },
  },
  
  // Typography
  typography: {
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'",
    fontFamilyCode: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace",
    fontSize: 14,
    fontSizeSm: 12,
    fontSizeLg: 16,
    fontSizeXl: 20,
    fontSizeHeading1: 38,
    fontSizeHeading2: 30,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 16,
    lineHeight: 1.5714285714285714,
    lineHeightLg: 1.5,
    lineHeightSm: 1.6666666666666667,
    fontWeightStrong: 600,
  },
  
  // Spacing
  spacing: {
    xxs: 4,
    xs: 8,
    sm: 12,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  
  // Border Radius
  borderRadius: {
    xs: 2,
    sm: 4,
    base: 6,
    lg: 8,
    xl: 12,
    full: 9999,
  },
  
  // Shadows
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)',
    base: '0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 9px 28px 8px rgba(0, 0, 0, 0.05)',
    lg: '0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 9px 28px 8px rgba(0, 0, 0, 0.05)',
    card: '0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09)',
  },
  
  // Animation
  animation: {
    durationFast: '0.1s',
    durationBase: '0.2s',
    durationSlow: '0.3s',
    easeInOut: 'cubic-bezier(0.645, 0.045, 0.355, 1)',
    easeOut: 'cubic-bezier(0.215, 0.61, 0.355, 1)',
    easeIn: 'cubic-bezier(0.55, 0.055, 0.675, 0.19)',
  },
  
  // Z-Index
  zIndex: {
    dropdown: 1050,
    sticky: 1020,
    fixed: 1030,
    modalBackdrop: 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
  },
  
  // Breakpoints
  breakpoints: {
    xs: 480,
    sm: 576,
    md: 768,
    lg: 992,
    xl: 1200,
    xxl: 1600,
  },
} as const;

// Light Theme Configuration
export const lightTheme: ThemeConfig = {
  token: {
    colorPrimary: designTokens.colors.primary,
    colorSuccess: designTokens.colors.success,
    colorWarning: designTokens.colors.warning,
    colorError: designTokens.colors.error,
    colorInfo: designTokens.colors.info,
    
    colorText: designTokens.colors.neutral.text,
    colorTextSecondary: designTokens.colors.neutral.textSecondary,
    colorTextTertiary: designTokens.colors.neutral.textTertiary,
    colorTextDisabled: designTokens.colors.neutral.textDisabled,
    
    colorBorder: designTokens.colors.neutral.border,
    colorBorderSecondary: designTokens.colors.neutral.borderSecondary,
    
    colorBgContainer: designTokens.colors.neutral.background,
    colorBgElevated: designTokens.colors.neutral.background,
    colorBgLayout: designTokens.colors.neutral.backgroundTertiary,
    
    fontFamily: designTokens.typography.fontFamily,
    fontSize: designTokens.typography.fontSize,
    lineHeight: designTokens.typography.lineHeight,
    
    borderRadius: designTokens.borderRadius.base,
    borderRadiusSM: designTokens.borderRadius.sm,
    borderRadiusLG: designTokens.borderRadius.lg,
    
    boxShadow: designTokens.shadows.base,
    boxShadowSecondary: designTokens.shadows.sm,
    
    motionDurationFast: designTokens.animation.durationFast,
    motionDurationMid: designTokens.animation.durationBase,
    motionDurationSlow: designTokens.animation.durationSlow,
    motionEaseInOut: designTokens.animation.easeInOut,
    motionEaseOut: designTokens.animation.easeOut,
    motionEaseIn: designTokens.animation.easeIn,
    
    padding: designTokens.spacing.md,
    paddingXS: designTokens.spacing.xs,
    paddingSM: designTokens.spacing.sm,
    paddingLG: designTokens.spacing.lg,
    paddingXL: designTokens.spacing.xl,
    
    margin: designTokens.spacing.md,
    marginXS: designTokens.spacing.xs,
    marginSM: designTokens.spacing.sm,
    marginLG: designTokens.spacing.lg,
    marginXL: designTokens.spacing.xl,
  },
  components: {
    Button: {
      borderRadius: designTokens.borderRadius.base,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
      fontWeight: 500,
    },
    Card: {
      borderRadiusLG: designTokens.borderRadius.lg,
      boxShadowTertiary: designTokens.shadows.sm,
    },
    Input: {
      borderRadius: designTokens.borderRadius.base,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
    },
    Select: {
      borderRadius: designTokens.borderRadius.base,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
    },
    Table: {
      borderRadius: designTokens.borderRadius.lg,
      headerBg: designTokens.colors.neutral.backgroundSecondary,
    },
    Menu: {
      itemBorderRadius: designTokens.borderRadius.base,
      subMenuItemBorderRadius: designTokens.borderRadius.base,
    },
    Modal: {
      borderRadiusLG: designTokens.borderRadius.xl,
    },
    Notification: {
      borderRadiusLG: designTokens.borderRadius.lg,
    },
    Message: {
      borderRadiusLG: designTokens.borderRadius.lg,
    },
    Tag: {
      borderRadiusSM: designTokens.borderRadius.sm,
    },
    Tabs: {
      cardBorderRadius: designTokens.borderRadius.lg,
    },
  },
};

// Dark Theme Configuration
export const darkTheme: ThemeConfig = {
  token: {
    ...lightTheme.token,
    colorText: 'rgba(255, 255, 255, 0.88)',
    colorTextSecondary: 'rgba(255, 255, 255, 0.65)',
    colorTextTertiary: 'rgba(255, 255, 255, 0.45)',
    colorTextDisabled: 'rgba(255, 255, 255, 0.25)',
    
    colorBorder: '#424242',
    colorBorderSecondary: '#303030',
    
    colorBgContainer: '#141414',
    colorBgElevated: '#1f1f1f',
    colorBgLayout: '#000000',
  },
  components: {
    ...lightTheme.components,
    Table: {
      ...lightTheme.components?.Table,
      headerBg: '#1f1f1f',
    },
  },
};

export type DesignTokens = typeof designTokens;
