/**
 * Brand Identity System Types
 * 品牌识别系统类型定义
 */

/**
 * LOGO变体类型
 */
export enum LogoVariant {
  STANDARD = 'standard',      // 120x120px - 主要应用
  SIMPLE = 'simple',          // 64x64px - 导航栏、小尺寸
  FULL = 'full',              // 280x80px - 页眉、横幅
  FAVICON = 'favicon'         // 32x32px - 浏览器标签
}

/**
 * LOGO资源
 */
export interface LogoAsset {
  id: string;
  name: string;
  variant: LogoVariant;
  dimensions: {
    width: number;
    height: number;
  };
  filePath: string;
  fileSize?: number;
  format: 'svg' | 'png' | 'ico';
  accessibility: {
    altText: string;
    ariaLabel: string;
  };
}

/**
 * 品牌主题类型
 */
export type BrandThemeType = 'default' | 'spring' | 'summer' | 'autumn' | 'winter' | 'festival' | 'custom';

/**
 * 品牌颜色配置
 */
export interface BrandColors {
  primary: string;
  primaryHover: string;
  primaryActive: string;
  primaryLight: string;
  secondary: string;
  secondaryHover: string;
  secondaryActive: string;
  accent: string;
  background: string;
  surface: string;
  text: string;
  textSecondary: string;
}

/**
 * 品牌主题配置
 */
export interface BrandTheme {
  id: BrandThemeType;
  name: string;
  nameZh: string;
  description: string;
  colors: BrandColors;
  logo?: {
    standard?: string;
    simple?: string;
    full?: string;
    favicon?: string;
  };
  isActive: boolean;
  startDate?: string;  // ISO date string
  endDate?: string;    // ISO date string
  priority: number;    // 优先级，数字越大优先级越高
}

/**
 * 品牌配置
 */
export interface BrandConfiguration {
  brandName: {
    zh: string;
    en: string;
  };
  currentTheme: BrandThemeType;
  themes: BrandTheme[];
  autoSwitch: boolean;  // 是否自动切换主题
  typography: {
    fontFamily: string;
    fontFamilyCode: string;
  };
  spacing: {
    logoSafeArea: number;
    minimumSize: number;
  };
}

/**
 * 品牌上下文
 */
export interface BrandContext {
  location: BrandLocation;
  size: 'small' | 'medium' | 'large';
  theme: 'light' | 'dark';
  language: 'zh' | 'en';
  deviceType: 'desktop' | 'mobile' | 'tablet';
}

/**
 * 品牌位置
 */
export enum BrandLocation {
  LOGIN_PAGE = 'login',
  NAVIGATION = 'navigation',
  FAVICON = 'favicon',
  HEADER = 'header',
  FOOTER = 'footer',
  LOADING = 'loading'
}

/**
 * 品牌性能指标
 */
export interface BrandPerformanceMetrics {
  assetLoadTime: number;
  cacheHitRate: number;
  totalLoads: number;
  failedLoads: number;
  averageLoadTime: number;
  lastUpdated: string;
}

/**
 * 品牌分析数据
 */
export interface BrandAnalytics {
  impressions: number;
  interactions: number;
  themeUsage: Record<BrandThemeType, number>;
  locationUsage: Record<BrandLocation, number>;
  deviceBreakdown: {
    desktop: number;
    mobile: number;
    tablet: number;
  };
  performanceMetrics: BrandPerformanceMetrics;
}

/**
 * 品牌A/B测试变体
 */
export interface BrandVariant {
  id: string;
  name: string;
  description: string;
  theme: BrandTheme;
  weight: number;  // 流量权重 0-100
  isControl: boolean;
  metrics: {
    impressions: number;
    conversions: number;
    engagementRate: number;
  };
}

/**
 * A/B测试配置
 */
export interface ABTestConfig {
  id: string;
  name: string;
  description: string;
  variants: BrandVariant[];
  isActive: boolean;
  startDate: string;
  endDate?: string;
  targetAudience?: {
    percentage: number;
    criteria?: Record<string, unknown>;
  };
}
