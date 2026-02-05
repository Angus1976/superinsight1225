/**
 * useBrandTheme Hook
 * 品牌主题管理 Hook
 * 
 * 提供：
 * - 主题切换
 * - 主题预览
 * - 季节性主题自动切换
 * - 主题配置管理
 */

import { useCallback, useEffect, useMemo } from 'react';
import { useBrandStore } from '@/stores/brandStore';
import type { BrandTheme, BrandThemeType, LogoVariant, BrandColors } from '@/types/brand';

export interface UseBrandThemeReturn {
  // 当前状态
  currentTheme: BrandTheme;
  activeTheme: BrandTheme;
  availableThemes: BrandTheme[];
  isPreviewMode: boolean;
  previewTheme: BrandTheme | null;
  autoSwitch: boolean;
  
  // 品牌信息
  brandName: string;
  brandNameZh: string;
  brandNameEn: string;
  
  // 颜色
  colors: BrandColors;
  primaryColor: string;
  secondaryColor: string;
  
  // LOGO路径
  logoStandard: string;
  logoSimple: string;
  logoFull: string;
  logoFavicon: string;
  getLogoPath: (variant: LogoVariant) => string;
  
  // 操作
  setTheme: (themeId: BrandThemeType) => void;
  previewThemeById: (themeId: BrandThemeType) => void;
  startPreview: (theme: BrandTheme) => void;
  stopPreview: () => void;
  toggleAutoSwitch: (enabled: boolean) => void;
  addCustomTheme: (theme: Omit<BrandTheme, 'id' | 'priority'>) => void;
  updateTheme: (themeId: BrandThemeType, updates: Partial<BrandTheme>) => void;
  removeTheme: (themeId: BrandThemeType) => void;
  resetToDefault: () => void;
}

export function useBrandTheme(language: 'zh' | 'en' = 'zh'): UseBrandThemeReturn {
  const store = useBrandStore();
  
  // 获取活动主题
  const activeTheme = useMemo(() => store.getActiveTheme(), [
    store.currentTheme,
    store.previewTheme,
    store.isPreviewMode
  ]);
  
  // 品牌名称
  const brandName = useMemo(() => store.getBrandName(language), [language, store.config.brandName]);
  const brandNameZh = store.config.brandName.zh;
  const brandNameEn = store.config.brandName.en;
  
  // 颜色
  const colors = activeTheme.colors;
  const primaryColor = colors.primary;
  const secondaryColor = colors.secondary;
  
  // LOGO路径
  const logoStandard = store.getLogoPath(LogoVariant.STANDARD);
  const logoSimple = store.getLogoPath(LogoVariant.SIMPLE);
  const logoFull = store.getLogoPath(LogoVariant.FULL);
  const logoFavicon = store.getLogoPath(LogoVariant.FAVICON);
  
  // 预览指定主题
  const previewThemeById = useCallback((themeId: BrandThemeType) => {
    const theme = store.config.themes.find(t => t.id === themeId);
    if (theme) {
      store.setPreviewTheme(theme);
      store.togglePreviewMode(true);
    }
  }, [store]);
  
  // 开始预览
  const startPreview = useCallback((theme: BrandTheme) => {
    store.setPreviewTheme(theme);
    store.togglePreviewMode(true);
  }, [store]);
  
  // 停止预览
  const stopPreview = useCallback(() => {
    store.togglePreviewMode(false);
  }, [store]);
  
  // 切换自动切换
  const toggleAutoSwitch = useCallback((enabled: boolean) => {
    store.setAutoSwitch(enabled);
  }, [store]);
  
  // 添加自定义主题
  const addCustomTheme = useCallback((theme: Omit<BrandTheme, 'id' | 'priority'>) => {
    store.addCustomTheme({
      ...theme,
      id: 'custom',
      priority: 3
    } as BrandTheme);
  }, [store]);
  
  // 初始化时检查季节性主题
  useEffect(() => {
    if (store.config.autoSwitch) {
      store.checkAndApplySeasonalTheme();
    }
  }, []);
  
  // 每天检查一次季节性主题
  useEffect(() => {
    if (!store.config.autoSwitch) return;
    
    const checkInterval = setInterval(() => {
      store.checkAndApplySeasonalTheme();
    }, 24 * 60 * 60 * 1000); // 24小时
    
    return () => clearInterval(checkInterval);
  }, [store.config.autoSwitch]);
  
  return {
    // 状态
    currentTheme: store.currentTheme,
    activeTheme,
    availableThemes: store.config.themes,
    isPreviewMode: store.isPreviewMode,
    previewTheme: store.previewTheme,
    autoSwitch: store.config.autoSwitch,
    
    // 品牌信息
    brandName,
    brandNameZh,
    brandNameEn,
    
    // 颜色
    colors,
    primaryColor,
    secondaryColor,
    
    // LOGO
    logoStandard,
    logoSimple,
    logoFull,
    logoFavicon,
    getLogoPath: store.getLogoPath,
    
    // 操作
    setTheme: store.setTheme,
    previewThemeById,
    startPreview,
    stopPreview,
    toggleAutoSwitch,
    addCustomTheme,
    updateTheme: store.updateTheme,
    removeTheme: store.removeTheme,
    resetToDefault: store.resetToDefault
  };
}

export default useBrandTheme;
