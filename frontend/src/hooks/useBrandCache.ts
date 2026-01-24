/**
 * useBrandCache Hook
 * 品牌资源缓存管理 Hook
 * 
 * 提供：
 * - 缓存状态监控
 * - 性能指标获取
 * - 缓存操作（清除、更新）
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  brandCacheService, 
  type BrandCacheMetrics, 
  type BrandCacheVersion,
  calculateCacheHitRate 
} from '@/services/brandCacheService';

export interface UseBrandCacheReturn {
  // 状态
  isSupported: boolean;
  isActive: boolean;
  isLoading: boolean;
  metrics: BrandCacheMetrics | null;
  version: BrandCacheVersion | null;
  cacheHitRate: number;
  updateAvailable: boolean;
  
  // 操作
  register: () => Promise<boolean>;
  unregister: () => Promise<boolean>;
  clearCache: () => Promise<boolean>;
  updateCache: () => Promise<boolean>;
  refreshMetrics: () => Promise<void>;
}

export function useBrandCache(): UseBrandCacheReturn {
  const [isSupported] = useState(() => brandCacheService.isServiceWorkerSupported());
  const [isActive, setIsActive] = useState(() => brandCacheService.isActive());
  const [isLoading, setIsLoading] = useState(false);
  const [metrics, setMetrics] = useState<BrandCacheMetrics | null>(null);
  const [version, setVersion] = useState<BrandCacheVersion | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  // 刷新指标
  const refreshMetrics = useCallback(async () => {
    if (!isSupported) return;
    
    setIsLoading(true);
    try {
      const [newMetrics, newVersion] = await Promise.all([
        brandCacheService.getMetrics(),
        brandCacheService.getVersion()
      ]);
      
      setMetrics(newMetrics);
      setVersion(newVersion);
      setIsActive(brandCacheService.isActive());
    } catch (error) {
      console.error('[useBrandCache] Failed to refresh metrics:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isSupported]);

  // 注册 Service Worker
  const register = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await brandCacheService.register();
      setIsActive(brandCacheService.isActive());
      
      if (result) {
        await refreshMetrics();
      }
      
      return result;
    } finally {
      setIsLoading(false);
    }
  }, [refreshMetrics]);

  // 注销 Service Worker
  const unregister = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await brandCacheService.unregister();
      setIsActive(false);
      setMetrics(null);
      setVersion(null);
      return result;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 清除缓存
  const clearCache = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await brandCacheService.clearCache();
      if (result) {
        await refreshMetrics();
      }
      return result;
    } finally {
      setIsLoading(false);
    }
  }, [refreshMetrics]);

  // 更新缓存
  const updateCache = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await brandCacheService.updateCache();
      if (result) {
        setUpdateAvailable(false);
        await refreshMetrics();
      }
      return result;
    } finally {
      setIsLoading(false);
    }
  }, [refreshMetrics]);

  // 初始化
  useEffect(() => {
    if (!isSupported) return;

    // 设置更新回调
    brandCacheService.onUpdateAvailable = () => {
      setUpdateAvailable(true);
    };

    // 自动注册并获取初始指标
    register();

    // 定期刷新指标（每30秒）
    const intervalId = setInterval(refreshMetrics, 30000);

    return () => {
      clearInterval(intervalId);
      brandCacheService.onUpdateAvailable = undefined;
    };
  }, [isSupported, register, refreshMetrics]);

  // 计算缓存命中率
  const cacheHitRate = metrics ? calculateCacheHitRate(metrics) : 0;

  return {
    isSupported,
    isActive,
    isLoading,
    metrics,
    version,
    cacheHitRate,
    updateAvailable,
    register,
    unregister,
    clearCache,
    updateCache,
    refreshMetrics
  };
}

export default useBrandCache;
