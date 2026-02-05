/**
 * useBrandAnalytics Hook
 * 品牌分析 Hook
 * 
 * 提供：
 * - 性能指标监控
 * - 用户互动跟踪
 * - 分析报告生成
 * - 优化建议
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { brandAnalyticsService } from '@/services/brandAnalyticsService';
import type { 
  BrandAnalytics, 
  BrandPerformanceMetrics, 
  BrandLocation, 
  BrandThemeType 
} from '@/types/brand';

export interface UseBrandAnalyticsReturn {
  // 数据
  analytics: BrandAnalytics | null;
  performanceMetrics: BrandPerformanceMetrics | null;
  suggestions: string[];
  isLoading: boolean;
  
  // 跟踪方法
  trackImpression: (location: BrandLocation, themeId?: BrandThemeType) => void;
  trackInteraction: (action: string, location: BrandLocation) => void;
  trackAssetLoad: (assetPath: string, loadTime: number, success: boolean, cached?: boolean) => void;
  
  // 报告方法
  refreshAnalytics: () => void;
  generateReport: () => string;
  exportData: () => string;
  reset: () => void;
}

export function useBrandAnalytics(autoRefreshInterval: number = 30000): UseBrandAnalyticsReturn {
  const [analytics, setAnalytics] = useState<BrandAnalytics | null>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<BrandPerformanceMetrics | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const isInitialized = useRef(false);

  // 刷新分析数据
  const refreshAnalytics = useCallback(() => {
    setIsLoading(true);
    try {
      const newAnalytics = brandAnalyticsService.getAnalytics();
      const newMetrics = brandAnalyticsService.getPerformanceMetrics();
      const newSuggestions = brandAnalyticsService.getOptimizationSuggestions();
      
      setAnalytics(newAnalytics);
      setPerformanceMetrics(newMetrics);
      setSuggestions(newSuggestions);
    } catch (error) {
      console.error('[useBrandAnalytics] Failed to refresh analytics:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 跟踪展示
  const trackImpression = useCallback((location: BrandLocation, themeId?: BrandThemeType) => {
    brandAnalyticsService.trackImpression(location, themeId);
  }, []);

  // 跟踪互动
  const trackInteraction = useCallback((action: string, location: BrandLocation) => {
    brandAnalyticsService.trackInteraction(action, location);
  }, []);

  // 跟踪资源加载
  const trackAssetLoad = useCallback((
    assetPath: string, 
    loadTime: number, 
    success: boolean, 
    cached: boolean = false
  ) => {
    brandAnalyticsService.trackAssetLoad(assetPath, loadTime, success, cached);
  }, []);

  // 生成报告
  const generateReport = useCallback(() => {
    return brandAnalyticsService.generateReport();
  }, []);

  // 导出数据
  const exportData = useCallback(() => {
    return brandAnalyticsService.exportData();
  }, []);

  // 重置数据
  const reset = useCallback(() => {
    brandAnalyticsService.reset();
    refreshAnalytics();
  }, [refreshAnalytics]);

  // 初始化
  useEffect(() => {
    if (!isInitialized.current) {
      brandAnalyticsService.initialize();
      isInitialized.current = true;
    }

    // 初始加载
    refreshAnalytics();

    // 自动刷新
    const intervalId = setInterval(refreshAnalytics, autoRefreshInterval);

    return () => {
      clearInterval(intervalId);
    };
  }, [autoRefreshInterval, refreshAnalytics]);

  return {
    analytics,
    performanceMetrics,
    suggestions,
    isLoading,
    trackImpression,
    trackInteraction,
    trackAssetLoad,
    refreshAnalytics,
    generateReport,
    exportData,
    reset
  };
}

/**
 * 简化版 Hook - 仅用于跟踪
 */
export function useBrandTracking() {
  const trackImpression = useCallback((location: BrandLocation, themeId?: BrandThemeType) => {
    brandAnalyticsService.trackImpression(location, themeId);
  }, []);

  const trackInteraction = useCallback((action: string, location: BrandLocation) => {
    brandAnalyticsService.trackInteraction(action, location);
  }, []);

  return { trackImpression, trackInteraction };
}

export default useBrandAnalytics;
