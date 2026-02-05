/**
 * Brand Analytics Service
 * 品牌性能分析服务
 * 
 * 功能：
 * - 品牌资源加载性能监控
 * - 用户品牌互动跟踪
 * - 品牌使用报告生成
 * - 优化建议
 */

import type { 
  BrandAnalytics, 
  BrandPerformanceMetrics, 
  BrandLocation, 
  BrandThemeType 
} from '@/types/brand';

// 性能指标存储
interface PerformanceEntry {
  assetPath: string;
  loadTime: number;
  success: boolean;
  timestamp: number;
  cached: boolean;
}

class BrandAnalyticsService {
  private performanceEntries: PerformanceEntry[] = [];
  private impressions: Map<string, number> = new Map();
  private interactions: Map<string, number> = new Map();
  private themeUsage: Map<BrandThemeType, number> = new Map();
  private locationUsage: Map<BrandLocation, number> = new Map();
  private deviceBreakdown = { desktop: 0, mobile: 0, tablet: 0 };
  private observer: PerformanceObserver | null = null;
  private isInitialized = false;

  /**
   * 初始化性能监控
   */
  initialize(): void {
    if (this.isInitialized || typeof window === 'undefined') return;

    // 监控资源加载性能
    if ('PerformanceObserver' in window) {
      this.observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          if (this.isBrandAsset(entry.name)) {
            this.recordPerformanceEntry({
              assetPath: entry.name,
              loadTime: entry.duration,
              success: true,
              timestamp: Date.now(),
              cached: (entry as PerformanceResourceTiming).transferSize === 0
            });
          }
        });
      });

      this.observer.observe({ entryTypes: ['resource'] });
    }

    // 检测设备类型
    this.detectDeviceType();

    this.isInitialized = true;
    console.log('[BrandAnalytics] Initialized');
  }

  /**
   * 销毁监控
   */
  destroy(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    this.isInitialized = false;
  }

  /**
   * 检查是否为品牌资源
   */
  private isBrandAsset(url: string): boolean {
    const brandAssetPatterns = [
      'logo-wenshijian',
      'favicon.svg',
      'brand-'
    ];
    return brandAssetPatterns.some(pattern => url.includes(pattern));
  }

  /**
   * 记录性能条目
   */
  private recordPerformanceEntry(entry: PerformanceEntry): void {
    this.performanceEntries.push(entry);
    
    // 保留最近1000条记录
    if (this.performanceEntries.length > 1000) {
      this.performanceEntries = this.performanceEntries.slice(-1000);
    }
  }

  /**
   * 检测设备类型
   */
  private detectDeviceType(): 'desktop' | 'mobile' | 'tablet' {
    const ua = navigator.userAgent;
    let deviceType: 'desktop' | 'mobile' | 'tablet' = 'desktop';

    if (/tablet|ipad|playbook|silk/i.test(ua)) {
      deviceType = 'tablet';
    } else if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile/i.test(ua)) {
      deviceType = 'mobile';
    }

    this.deviceBreakdown[deviceType]++;
    return deviceType;
  }

  /**
   * 记录品牌展示
   */
  trackImpression(location: BrandLocation, themeId?: BrandThemeType): void {
    const key = `${location}-${themeId || 'default'}`;
    this.impressions.set(key, (this.impressions.get(key) || 0) + 1);
    this.locationUsage.set(location, (this.locationUsage.get(location) || 0) + 1);
    
    if (themeId) {
      this.themeUsage.set(themeId, (this.themeUsage.get(themeId) || 0) + 1);
    }
  }

  /**
   * 记录品牌互动
   */
  trackInteraction(action: string, location: BrandLocation): void {
    const key = `${action}-${location}`;
    this.interactions.set(key, (this.interactions.get(key) || 0) + 1);
  }

  /**
   * 记录资源加载
   */
  trackAssetLoad(assetPath: string, loadTime: number, success: boolean, cached: boolean = false): void {
    this.recordPerformanceEntry({
      assetPath,
      loadTime,
      success,
      timestamp: Date.now(),
      cached
    });
  }

  /**
   * 获取性能指标
   */
  getPerformanceMetrics(): BrandPerformanceMetrics {
    const entries = this.performanceEntries;
    const successfulEntries = entries.filter(e => e.success);
    const cachedEntries = entries.filter(e => e.cached);

    const totalLoadTime = successfulEntries.reduce((sum, e) => sum + e.loadTime, 0);
    const averageLoadTime = successfulEntries.length > 0 
      ? totalLoadTime / successfulEntries.length 
      : 0;

    const cacheHitRate = entries.length > 0 
      ? (cachedEntries.length / entries.length) * 100 
      : 0;

    return {
      assetLoadTime: averageLoadTime,
      cacheHitRate: Math.round(cacheHitRate),
      totalLoads: entries.length,
      failedLoads: entries.filter(e => !e.success).length,
      averageLoadTime: Math.round(averageLoadTime),
      lastUpdated: new Date().toISOString()
    };
  }

  /**
   * 获取完整分析数据
   */
  getAnalytics(): BrandAnalytics {
    const totalImpressions = Array.from(this.impressions.values()).reduce((a, b) => a + b, 0);
    const totalInteractions = Array.from(this.interactions.values()).reduce((a, b) => a + b, 0);

    return {
      impressions: totalImpressions,
      interactions: totalInteractions,
      themeUsage: Object.fromEntries(this.themeUsage) as Record<BrandThemeType, number>,
      locationUsage: Object.fromEntries(this.locationUsage) as Record<BrandLocation, number>,
      deviceBreakdown: { ...this.deviceBreakdown },
      performanceMetrics: this.getPerformanceMetrics()
    };
  }

  /**
   * 获取优化建议
   */
  getOptimizationSuggestions(): string[] {
    const suggestions: string[] = [];
    const metrics = this.getPerformanceMetrics();

    // 加载时间建议
    if (metrics.averageLoadTime > 100) {
      suggestions.push('品牌资源平均加载时间超过100ms，建议启用CDN加速');
    }

    // 缓存命中率建议
    if (metrics.cacheHitRate < 80) {
      suggestions.push('缓存命中率低于80%，建议检查Service Worker配置');
    }

    // 失败率建议
    const failureRate = metrics.totalLoads > 0 
      ? (metrics.failedLoads / metrics.totalLoads) * 100 
      : 0;
    if (failureRate > 5) {
      suggestions.push('资源加载失败率超过5%，建议检查资源可用性');
    }

    // 设备适配建议
    const totalDevices = this.deviceBreakdown.desktop + this.deviceBreakdown.mobile + this.deviceBreakdown.tablet;
    if (totalDevices > 0) {
      const mobileRatio = (this.deviceBreakdown.mobile + this.deviceBreakdown.tablet) / totalDevices;
      if (mobileRatio > 0.5) {
        suggestions.push('移动端用户占比超过50%，建议优化移动端品牌展示');
      }
    }

    if (suggestions.length === 0) {
      suggestions.push('品牌资源性能良好，无需优化');
    }

    return suggestions;
  }

  /**
   * 生成性能报告
   */
  generateReport(): string {
    const analytics = this.getAnalytics();
    const suggestions = this.getOptimizationSuggestions();
    const metrics = analytics.performanceMetrics;

    return `
# 问视间品牌性能报告

## 概览
- 总展示次数: ${analytics.impressions}
- 总互动次数: ${analytics.interactions}
- 互动率: ${analytics.impressions > 0 ? ((analytics.interactions / analytics.impressions) * 100).toFixed(2) : 0}%

## 性能指标
- 平均加载时间: ${metrics.averageLoadTime}ms
- 缓存命中率: ${metrics.cacheHitRate}%
- 总加载次数: ${metrics.totalLoads}
- 失败次数: ${metrics.failedLoads}

## 设备分布
- 桌面端: ${analytics.deviceBreakdown.desktop}
- 移动端: ${analytics.deviceBreakdown.mobile}
- 平板端: ${analytics.deviceBreakdown.tablet}

## 优化建议
${suggestions.map((s, i) => `${i + 1}. ${s}`).join('\n')}

---
报告生成时间: ${new Date().toLocaleString('zh-CN')}
    `.trim();
  }

  /**
   * 重置统计数据
   */
  reset(): void {
    this.performanceEntries = [];
    this.impressions.clear();
    this.interactions.clear();
    this.themeUsage.clear();
    this.locationUsage.clear();
    this.deviceBreakdown = { desktop: 0, mobile: 0, tablet: 0 };
  }

  /**
   * 导出数据为JSON
   */
  exportData(): string {
    return JSON.stringify({
      analytics: this.getAnalytics(),
      suggestions: this.getOptimizationSuggestions(),
      exportedAt: new Date().toISOString()
    }, null, 2);
  }
}

// 单例导出
export const brandAnalyticsService = new BrandAnalyticsService();

export default brandAnalyticsService;
