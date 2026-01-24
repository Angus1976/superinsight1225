/**
 * Brand Cache Service
 * 品牌资源缓存服务
 * 
 * 提供：
 * - Service Worker 注册和管理
 * - 缓存性能监控
 * - 版本化资源管理
 * - 缓存失效机制
 */

export interface BrandCacheMetrics {
  cacheHits: number;
  cacheMisses: number;
  networkFetches: number;
  errors: number;
  version: string;
  cacheHitRate: number;
}

export interface BrandCacheVersion {
  version: string;
  cacheName: string;
}

class BrandCacheService {
  private registration: ServiceWorkerRegistration | null = null;
  private isSupported: boolean;

  constructor() {
    this.isSupported = 'serviceWorker' in navigator;
  }

  /**
   * 注册品牌资源 Service Worker
   */
  async register(): Promise<boolean> {
    if (!this.isSupported) {
      console.warn('[BrandCache] Service Worker not supported');
      return false;
    }

    try {
      this.registration = await navigator.serviceWorker.register('/sw-brand-assets.js', {
        scope: '/'
      });

      console.log('[BrandCache] Service Worker registered:', this.registration.scope);

      // 监听更新
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration?.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('[BrandCache] New version available');
              this.onUpdateAvailable?.();
            }
          });
        }
      });

      return true;
    } catch (error) {
      console.error('[BrandCache] Registration failed:', error);
      return false;
    }
  }

  /**
   * 注销 Service Worker
   */
  async unregister(): Promise<boolean> {
    if (!this.registration) {
      return false;
    }

    try {
      const result = await this.registration.unregister();
      this.registration = null;
      return result;
    } catch (error) {
      console.error('[BrandCache] Unregistration failed:', error);
      return false;
    }
  }

  /**
   * 获取缓存性能指标
   */
  async getMetrics(): Promise<BrandCacheMetrics | null> {
    if (!this.isSupported || !navigator.serviceWorker.controller) {
      return null;
    }

    return this.sendMessage<BrandCacheMetrics>({ type: 'GET_METRICS' });
  }

  /**
   * 获取缓存版本信息
   */
  async getVersion(): Promise<BrandCacheVersion | null> {
    if (!this.isSupported || !navigator.serviceWorker.controller) {
      return null;
    }

    return this.sendMessage<BrandCacheVersion>({ type: 'GET_VERSION' });
  }

  /**
   * 清除品牌资源缓存
   */
  async clearCache(): Promise<boolean> {
    if (!this.isSupported || !navigator.serviceWorker.controller) {
      return false;
    }

    const result = await this.sendMessage<{ type: string }>({ type: 'CLEAR_CACHE' });
    return result?.type === 'CACHE_CLEARED';
  }

  /**
   * 强制更新缓存
   */
  async updateCache(): Promise<boolean> {
    if (!this.isSupported || !navigator.serviceWorker.controller) {
      return false;
    }

    const result = await this.sendMessage<{ type: string }>({ type: 'UPDATE_CACHE' });
    return result?.type === 'CACHE_UPDATED';
  }

  /**
   * 检查 Service Worker 是否激活
   */
  isActive(): boolean {
    return this.isSupported && navigator.serviceWorker.controller !== null;
  }

  /**
   * 检查是否支持 Service Worker
   */
  isServiceWorkerSupported(): boolean {
    return this.isSupported;
  }

  /**
   * 更新可用回调
   */
  onUpdateAvailable?: () => void;

  /**
   * 发送消息到 Service Worker
   */
  private sendMessage<T>(message: { type: string; data?: unknown }): Promise<T | null> {
    return new Promise((resolve) => {
      if (!navigator.serviceWorker.controller) {
        resolve(null);
        return;
      }

      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        resolve(event.data?.data || event.data);
      };

      // 设置超时
      const timeout = setTimeout(() => {
        resolve(null);
      }, 5000);

      messageChannel.port1.onmessage = (event) => {
        clearTimeout(timeout);
        resolve(event.data?.data || event.data);
      };

      navigator.serviceWorker.controller.postMessage(message, [messageChannel.port2]);
    });
  }
}

// 单例导出
export const brandCacheService = new BrandCacheService();

/**
 * 计算缓存命中率
 */
export function calculateCacheHitRate(metrics: BrandCacheMetrics): number {
  const total = metrics.cacheHits + metrics.cacheMisses;
  if (total === 0) return 0;
  return Math.round((metrics.cacheHits / total) * 100);
}

/**
 * 格式化缓存指标
 */
export function formatCacheMetrics(metrics: BrandCacheMetrics): string {
  const hitRate = calculateCacheHitRate(metrics);
  return `Cache Hit Rate: ${hitRate}% | Hits: ${metrics.cacheHits} | Misses: ${metrics.cacheMisses} | Network: ${metrics.networkFetches} | Errors: ${metrics.errors}`;
}
