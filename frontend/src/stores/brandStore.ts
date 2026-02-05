/**
 * Brand Store
 * 品牌状态管理
 * 
 * 功能：
 * - 动态品牌主题管理
 * - 主题切换和预览
 * - 定时主题切换
 * - 品牌配置持久化
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { 
  BrandTheme, 
  BrandThemeType, 
  BrandConfiguration,
  BrandColors,
  LogoVariant
} from '@/types/brand';

// 默认品牌颜色
const defaultColors: BrandColors = {
  primary: '#1890ff',
  primaryHover: '#40a9ff',
  primaryActive: '#096dd9',
  primaryLight: '#e6f7ff',
  secondary: '#52c41a',
  secondaryHover: '#73d13d',
  secondaryActive: '#389e0d',
  accent: '#722ed1',
  background: '#ffffff',
  surface: '#fafafa',
  text: 'rgba(0, 0, 0, 0.88)',
  textSecondary: 'rgba(0, 0, 0, 0.65)'
};

// 预定义主题
const predefinedThemes: BrandTheme[] = [
  {
    id: 'default',
    name: 'Default',
    nameZh: '默认主题',
    description: '问视间标准品牌主题',
    colors: defaultColors,
    isActive: true,
    priority: 0
  },
  {
    id: 'spring',
    name: 'Spring',
    nameZh: '春季主题',
    description: '清新绿色春季主题',
    colors: {
      ...defaultColors,
      primary: '#52c41a',
      primaryHover: '#73d13d',
      primaryActive: '#389e0d',
      primaryLight: '#f6ffed',
      secondary: '#13c2c2',
      accent: '#eb2f96'
    },
    isActive: false,
    startDate: '2026-03-01',
    endDate: '2026-05-31',
    priority: 1
  },
  {
    id: 'summer',
    name: 'Summer',
    nameZh: '夏季主题',
    description: '活力橙色夏季主题',
    colors: {
      ...defaultColors,
      primary: '#fa8c16',
      primaryHover: '#ffa940',
      primaryActive: '#d46b08',
      primaryLight: '#fff7e6',
      secondary: '#1890ff',
      accent: '#f5222d'
    },
    isActive: false,
    startDate: '2026-06-01',
    endDate: '2026-08-31',
    priority: 1
  },
  {
    id: 'autumn',
    name: 'Autumn',
    nameZh: '秋季主题',
    description: '温暖棕色秋季主题',
    colors: {
      ...defaultColors,
      primary: '#d4380d',
      primaryHover: '#ff4d4f',
      primaryActive: '#a8071a',
      primaryLight: '#fff1f0',
      secondary: '#faad14',
      accent: '#722ed1'
    },
    isActive: false,
    startDate: '2026-09-01',
    endDate: '2026-11-30',
    priority: 1
  },
  {
    id: 'winter',
    name: 'Winter',
    nameZh: '冬季主题',
    description: '冷静蓝色冬季主题',
    colors: {
      ...defaultColors,
      primary: '#2f54eb',
      primaryHover: '#597ef7',
      primaryActive: '#1d39c4',
      primaryLight: '#f0f5ff',
      secondary: '#13c2c2',
      accent: '#eb2f96'
    },
    isActive: false,
    startDate: '2026-12-01',
    endDate: '2027-02-28',
    priority: 1
  },
  {
    id: 'festival',
    name: 'Festival',
    nameZh: '节日主题',
    description: '喜庆红色节日主题',
    colors: {
      ...defaultColors,
      primary: '#f5222d',
      primaryHover: '#ff4d4f',
      primaryActive: '#cf1322',
      primaryLight: '#fff1f0',
      secondary: '#fadb14',
      accent: '#fa8c16'
    },
    isActive: false,
    priority: 2
  }
];

// 默认品牌配置
const defaultBrandConfig: BrandConfiguration = {
  brandName: {
    zh: '问视间',
    en: 'SuperInsight'
  },
  currentTheme: 'default',
  themes: predefinedThemes,
  autoSwitch: true,
  typography: {
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    fontFamilyCode: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
  },
  spacing: {
    logoSafeArea: 16,
    minimumSize: 32
  }
};

interface BrandState {
  // 配置
  config: BrandConfiguration;
  
  // 当前主题
  currentTheme: BrandTheme;
  
  // 预览主题（用于主题预览功能）
  previewTheme: BrandTheme | null;
  
  // 是否处于预览模式
  isPreviewMode: boolean;
  
  // Actions
  setTheme: (themeId: BrandThemeType) => void;
  setPreviewTheme: (theme: BrandTheme | null) => void;
  togglePreviewMode: (enabled: boolean) => void;
  addCustomTheme: (theme: BrandTheme) => void;
  updateTheme: (themeId: BrandThemeType, updates: Partial<BrandTheme>) => void;
  removeTheme: (themeId: BrandThemeType) => void;
  setAutoSwitch: (enabled: boolean) => void;
  checkAndApplySeasonalTheme: () => void;
  getActiveTheme: () => BrandTheme;
  getLogoPath: (variant: LogoVariant) => string;
  getBrandName: (language: 'zh' | 'en') => string;
  resetToDefault: () => void;
}

export const useBrandStore = create<BrandState>()(
  persist(
    (set, get) => ({
      config: defaultBrandConfig,
      currentTheme: predefinedThemes[0],
      previewTheme: null,
      isPreviewMode: false,

      setTheme: (themeId) => {
        const theme = get().config.themes.find(t => t.id === themeId);
        if (theme) {
          set({ 
            currentTheme: theme,
            config: { ...get().config, currentTheme: themeId }
          });
          applyThemeColors(theme.colors);
        }
      },

      setPreviewTheme: (theme) => {
        set({ previewTheme: theme });
        if (theme) {
          applyThemeColors(theme.colors);
        } else {
          applyThemeColors(get().currentTheme.colors);
        }
      },

      togglePreviewMode: (enabled) => {
        set({ isPreviewMode: enabled });
        if (!enabled) {
          set({ previewTheme: null });
          applyThemeColors(get().currentTheme.colors);
        }
      },

      addCustomTheme: (theme) => {
        const newTheme: BrandTheme = {
          ...theme,
          id: 'custom' as BrandThemeType,
          priority: 3
        };
        set({
          config: {
            ...get().config,
            themes: [...get().config.themes, newTheme]
          }
        });
      },

      updateTheme: (themeId, updates) => {
        set({
          config: {
            ...get().config,
            themes: get().config.themes.map(t => 
              t.id === themeId ? { ...t, ...updates } : t
            )
          }
        });
        
        // 如果更新的是当前主题，重新应用
        if (get().currentTheme.id === themeId) {
          const updatedTheme = get().config.themes.find(t => t.id === themeId);
          if (updatedTheme) {
            set({ currentTheme: updatedTheme });
            applyThemeColors(updatedTheme.colors);
          }
        }
      },

      removeTheme: (themeId) => {
        if (themeId === 'default') return; // 不能删除默认主题
        
        set({
          config: {
            ...get().config,
            themes: get().config.themes.filter(t => t.id !== themeId)
          }
        });
        
        // 如果删除的是当前主题，切换到默认
        if (get().currentTheme.id === themeId) {
          get().setTheme('default');
        }
      },

      setAutoSwitch: (enabled) => {
        set({
          config: { ...get().config, autoSwitch: enabled }
        });
        
        if (enabled) {
          get().checkAndApplySeasonalTheme();
        }
      },

      checkAndApplySeasonalTheme: () => {
        if (!get().config.autoSwitch) return;
        
        const now = new Date();
        const themes = get().config.themes
          .filter(t => t.startDate && t.endDate)
          .filter(t => {
            const start = new Date(t.startDate!);
            const end = new Date(t.endDate!);
            return now >= start && now <= end;
          })
          .sort((a, b) => b.priority - a.priority);
        
        if (themes.length > 0) {
          get().setTheme(themes[0].id);
        } else {
          get().setTheme('default');
        }
      },

      getActiveTheme: () => {
        const state = get();
        if (state.isPreviewMode && state.previewTheme) {
          return state.previewTheme;
        }
        return state.currentTheme;
      },

      getLogoPath: (variant) => {
        const theme = get().getActiveTheme();
        const logoMap: Record<LogoVariant, string> = {
          [LogoVariant.STANDARD]: theme.logo?.standard || '/logo-wenshijian.svg',
          [LogoVariant.SIMPLE]: theme.logo?.simple || '/logo-wenshijian-simple.svg',
          [LogoVariant.FULL]: theme.logo?.full || '/logo-wenshijian-full.svg',
          [LogoVariant.FAVICON]: theme.logo?.favicon || '/favicon.svg'
        };
        return logoMap[variant];
      },

      getBrandName: (language) => {
        return get().config.brandName[language];
      },

      resetToDefault: () => {
        set({
          config: defaultBrandConfig,
          currentTheme: predefinedThemes[0],
          previewTheme: null,
          isPreviewMode: false
        });
        applyThemeColors(defaultColors);
      }
    }),
    {
      name: 'brand-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        config: state.config,
        currentTheme: state.currentTheme
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyThemeColors(state.currentTheme.colors);
          // 检查季节性主题
          state.checkAndApplySeasonalTheme();
        }
      }
    }
  )
);

/**
 * 应用主题颜色到CSS变量
 */
function applyThemeColors(colors: BrandColors): void {
  const root = document.documentElement;
  
  root.style.setProperty('--brand-primary', colors.primary);
  root.style.setProperty('--brand-primary-hover', colors.primaryHover);
  root.style.setProperty('--brand-primary-active', colors.primaryActive);
  root.style.setProperty('--brand-primary-light', colors.primaryLight);
  root.style.setProperty('--brand-secondary', colors.secondary);
  root.style.setProperty('--brand-secondary-hover', colors.secondaryHover);
  root.style.setProperty('--brand-secondary-active', colors.secondaryActive);
  root.style.setProperty('--brand-accent', colors.accent);
  root.style.setProperty('--brand-background', colors.background);
  root.style.setProperty('--brand-surface', colors.surface);
  root.style.setProperty('--brand-text', colors.text);
  root.style.setProperty('--brand-text-secondary', colors.textSecondary);
}

export default useBrandStore;
