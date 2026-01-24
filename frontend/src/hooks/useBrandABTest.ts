/**
 * useBrandABTest Hook
 * 品牌A/B测试 Hook
 * 
 * 提供：
 * - 测试创建和管理
 * - 变体分配
 * - 数据跟踪
 * - 结果分析
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { brandABTestService } from '@/services/brandABTestService';
import type { ABTestConfig, BrandVariant, BrandTheme } from '@/types/brand';

export interface TestResults {
  variants: Array<{
    id: string;
    name: string;
    isControl: boolean;
    impressions: number;
    interactions: number;
    conversions: number;
    interactionRate: number;
    conversionRate: number;
  }>;
  winner: string | null;
  confidence: number;
}

export interface UseBrandABTestReturn {
  // 状态
  activeTests: ABTestConfig[];
  allTests: ABTestConfig[];
  currentVariant: BrandVariant | null;
  currentTheme: BrandTheme | null;
  isInTest: boolean;
  
  // 测试管理
  createTest: (config: ABTestConfig) => void;
  startTest: (testId: string) => void;
  stopTest: (testId: string) => void;
  deleteTest: (testId: string) => void;
  
  // 变体获取
  getVariant: (testId: string) => BrandVariant | null;
  
  // 跟踪
  trackImpression: (testId: string) => void;
  trackInteraction: (testId: string) => void;
  trackConversion: (testId: string) => void;
  
  // 结果
  getResults: (testId: string) => TestResults | null;
  generateReport: (testId: string) => string;
  
  // 工具
  resetUserAssignment: (testId: string) => void;
  reset: () => void;
  refresh: () => void;
}

export function useBrandABTest(activeTestId?: string): UseBrandABTestReturn {
  const [activeTests, setActiveTests] = useState<ABTestConfig[]>([]);
  const [allTests, setAllTests] = useState<ABTestConfig[]>([]);
  const [currentVariant, setCurrentVariant] = useState<BrandVariant | null>(null);

  // 刷新测试列表
  const refresh = useCallback(() => {
    setActiveTests(brandABTestService.getActiveTests());
    setAllTests(brandABTestService.getAllTests());
    
    if (activeTestId) {
      const variant = brandABTestService.getVariantForUser(activeTestId);
      setCurrentVariant(variant);
    }
  }, [activeTestId]);

  // 初始化
  useEffect(() => {
    refresh();
  }, [refresh]);

  // 当前主题
  const currentTheme = useMemo(() => {
    return currentVariant?.theme || null;
  }, [currentVariant]);

  // 是否在测试中
  const isInTest = useMemo(() => {
    return currentVariant !== null;
  }, [currentVariant]);

  // 创建测试
  const createTest = useCallback((config: ABTestConfig) => {
    brandABTestService.createTest(config);
    refresh();
  }, [refresh]);

  // 启动测试
  const startTest = useCallback((testId: string) => {
    brandABTestService.startTest(testId);
    refresh();
  }, [refresh]);

  // 停止测试
  const stopTest = useCallback((testId: string) => {
    brandABTestService.stopTest(testId);
    refresh();
  }, [refresh]);

  // 删除测试
  const deleteTest = useCallback((testId: string) => {
    brandABTestService.deleteTest(testId);
    refresh();
  }, [refresh]);

  // 获取变体
  const getVariant = useCallback((testId: string) => {
    return brandABTestService.getVariantForUser(testId);
  }, []);

  // 跟踪展示
  const trackImpression = useCallback((testId: string) => {
    const variant = brandABTestService.getVariantForUser(testId);
    if (variant) {
      brandABTestService.trackImpression(testId, variant.id);
    }
  }, []);

  // 跟踪互动
  const trackInteraction = useCallback((testId: string) => {
    const variant = brandABTestService.getVariantForUser(testId);
    if (variant) {
      brandABTestService.trackInteraction(testId, variant.id);
    }
  }, []);

  // 跟踪转化
  const trackConversion = useCallback((testId: string) => {
    const variant = brandABTestService.getVariantForUser(testId);
    if (variant) {
      brandABTestService.trackConversion(testId, variant.id);
    }
  }, []);

  // 获取结果
  const getResults = useCallback((testId: string) => {
    return brandABTestService.getTestResults(testId);
  }, []);

  // 生成报告
  const generateReport = useCallback((testId: string) => {
    return brandABTestService.generateReport(testId);
  }, []);

  // 重置用户分组
  const resetUserAssignment = useCallback((testId: string) => {
    brandABTestService.resetUserAssignment(testId);
    refresh();
  }, [refresh]);

  // 重置所有
  const reset = useCallback(() => {
    brandABTestService.reset();
    refresh();
  }, [refresh]);

  return {
    activeTests,
    allTests,
    currentVariant,
    currentTheme,
    isInTest,
    createTest,
    startTest,
    stopTest,
    deleteTest,
    getVariant,
    trackImpression,
    trackInteraction,
    trackConversion,
    getResults,
    generateReport,
    resetUserAssignment,
    reset,
    refresh
  };
}

/**
 * 创建品牌A/B测试配置的辅助函数
 */
export function createBrandABTest(
  id: string,
  name: string,
  description: string,
  controlTheme: BrandTheme,
  treatmentThemes: BrandTheme[],
  weights?: number[]
): ABTestConfig {
  const totalVariants = 1 + treatmentThemes.length;
  const defaultWeight = Math.floor(100 / totalVariants);
  const remainder = 100 - (defaultWeight * totalVariants);

  const variants: BrandVariant[] = [
    {
      id: `${id}-control`,
      name: `${controlTheme.nameZh} (对照)`,
      description: '对照组',
      theme: controlTheme,
      weight: weights?.[0] || (defaultWeight + remainder),
      isControl: true,
      metrics: { impressions: 0, conversions: 0, engagementRate: 0 }
    },
    ...treatmentThemes.map((theme, index) => ({
      id: `${id}-treatment-${index + 1}`,
      name: theme.nameZh,
      description: `测试组 ${index + 1}`,
      theme,
      weight: weights?.[index + 1] || defaultWeight,
      isControl: false,
      metrics: { impressions: 0, conversions: 0, engagementRate: 0 }
    }))
  ];

  return {
    id,
    name,
    description,
    variants,
    isActive: false,
    startDate: ''
  };
}

export default useBrandABTest;
