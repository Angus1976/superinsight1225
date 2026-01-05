/**
 * IframeManager - Manages Label Studio iframe lifecycle
 * Handles creation, destruction, refresh, and lifecycle events
 * Enhanced with lazy loading and resource caching
 */

import {
  IframeConfig,
  IframeStatus,
  IframeLoadState,
  IframeLifecycleEvent,
  IframeEventCallback,
} from './types';
import { LazyLoader, LazyLoadConfig } from './LazyLoader';
import { ResourceCache, CacheConfig } from './ResourceCache';
import { PerformanceMonitor, MonitorConfig, PerformanceReport } from './PerformanceMonitor';

export class IframeManager {
  private iframe: HTMLIFrameElement | null = null;
  private config: IframeConfig | null = null;
  private loadState: IframeLoadState = {
    isLoading: false,
    progress: 0,
    error: null,
    status: IframeStatus.DESTROYED,
  };
  private eventCallbacks: Map<string, Set<IframeEventCallback>> = new Map();
  private loadTimeout: NodeJS.Timeout | null = null;
  private retryCount: number = 0;
  private container: HTMLElement | null = null;
  private lazyLoader: LazyLoader | null = null;
  private resourceCache: ResourceCache | null = null;
  private performanceMonitor: PerformanceMonitor | null = null;
  private enableLazyLoading: boolean = false;
  private enableCaching: boolean = false;
  private enablePerformanceMonitoring: boolean = false;

  /**
   * Initialize performance optimization features
   */
  initializePerformanceOptimization(
    lazyLoadConfig?: LazyLoadConfig,
    cacheConfig?: CacheConfig,
    monitorConfig?: MonitorConfig
  ): void {
    if (lazyLoadConfig) {
      this.lazyLoader = new LazyLoader(lazyLoadConfig);
      this.enableLazyLoading = true;
    }

    if (cacheConfig) {
      this.resourceCache = new ResourceCache(cacheConfig);
      this.enableCaching = true;
    }

    if (monitorConfig) {
      this.performanceMonitor = new PerformanceMonitor(monitorConfig);
      this.enablePerformanceMonitoring = true;
    }
  }

  /**
   * Create and initialize iframe with performance optimizations
   */
  async create(config: IframeConfig, container: HTMLElement): Promise<HTMLIFrameElement> {
    if (this.iframe) {
      throw new Error('iframe already exists. Call destroy() first.');
    }

    this.config = config;
    this.container = container;
    this.loadState = {
      isLoading: true,
      progress: 0,
      error: null,
      status: IframeStatus.LOADING,
    };
    this.retryCount = 0;

    // Emit loading event
    this.emit('load', { type: 'load', timestamp: Date.now() });

    // Check if lazy loading is enabled
    if (this.enableLazyLoading && this.lazyLoader) {
      const iframeId = this.generateIframeId(config);
      this.lazyLoader.observe(container, iframeId, config);
      
      // Return a placeholder iframe that will be replaced when visible
      this.iframe = this.createPlaceholderIframe();
      container.appendChild(this.iframe);
      return this.iframe;
    }

    // Create iframe normally
    return this.createIframeElement(config, container);
  }

  /**
   * Destroy iframe and cleanup resources
   */
  async destroy(): Promise<void> {
    if (!this.iframe) {
      return;
    }

    // Clear timeout
    if (this.loadTimeout) {
      clearTimeout(this.loadTimeout);
      this.loadTimeout = null;
    }

    // Cleanup lazy loader
    if (this.lazyLoader && this.container && this.config) {
      const iframeId = this.generateIframeId(this.config);
      this.lazyLoader.unobserve(this.container, iframeId);
    }

    // Remove event listeners
    this.removeIframeListeners();

    // Remove from DOM
    if (this.iframe.parentElement) {
      this.iframe.parentElement.removeChild(this.iframe);
    }

    // Cleanup
    this.iframe = null;
    this.config = null;
    this.container = null;
    this.loadState = {
      isLoading: false,
      progress: 0,
      error: null,
      status: IframeStatus.DESTROYED,
    };

    // Emit destroy event
    this.emit('destroy', { type: 'destroy', timestamp: Date.now() });
  }

  /**
   * Refresh iframe
   */
  async refresh(): Promise<void> {
    if (!this.iframe) {
      throw new Error('iframe does not exist');
    }

    this.loadState = {
      isLoading: true,
      progress: 0,
      error: null,
      status: IframeStatus.LOADING,
    };
    this.retryCount = 0;

    // Emit refresh event
    this.emit('refresh', { type: 'refresh', timestamp: Date.now() });

    // Reload iframe
    this.iframe.src = this.config?.url || '';

    // Setup load timeout
    this.setupLoadTimeout();
  }

  /**
   * Get current iframe status
   */
  getStatus(): IframeStatus {
    return this.loadState.status;
  }

  /**
   * Get current load state
   */
  getLoadState(): IframeLoadState {
    return { ...this.loadState };
  }

  /**
   * Get iframe element
   */
  getIframe(): HTMLIFrameElement | null {
    return this.iframe;
  }

  /**
   * Register event listener
   */
  on(event: string, callback: IframeEventCallback): void {
    if (!this.eventCallbacks.has(event)) {
      this.eventCallbacks.set(event, new Set());
    }
    this.eventCallbacks.get(event)!.add(callback);
  }

  /**
   * Unregister event listener
   */
  off(event: string, callback: IframeEventCallback): void {
    const callbacks = this.eventCallbacks.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  /**
   * Setup iframe event listeners
   */
  private setupIframeListeners(): void {
    if (!this.iframe) return;

    this.iframe.addEventListener('load', this.handleIframeLoad);
    this.iframe.addEventListener('error', this.handleIframeError);
  }

  /**
   * Remove iframe event listeners
   */
  private removeIframeListeners(): void {
    if (!this.iframe) return;

    this.iframe.removeEventListener('load', this.handleIframeLoad);
    this.iframe.removeEventListener('error', this.handleIframeError);
  }

  /**
   * Handle iframe load event
   */
  private handleIframeLoad = (): void => {
    if (this.loadTimeout) {
      clearTimeout(this.loadTimeout);
      this.loadTimeout = null;
    }

    this.loadState = {
      isLoading: false,
      progress: 100,
      error: null,
      status: IframeStatus.READY,
      loadEndTime: Date.now(),
    };

    // Start performance monitoring if enabled
    if (this.enablePerformanceMonitoring && this.performanceMonitor && this.iframe && this.config) {
      const iframeId = this.generateIframeId(this.config);
      this.performanceMonitor.startMonitoring(iframeId, this.iframe);
    }

    // Emit ready event
    this.emit('ready', { type: 'ready', timestamp: Date.now() });
  };

  /**
   * Handle iframe error event
   */
  private handleIframeError = (): void => {
    const error = 'Failed to load iframe';

    this.loadState = {
      isLoading: false,
      progress: 0,
      error,
      status: IframeStatus.ERROR,
    };

    // Record error in performance monitor
    if (this.enablePerformanceMonitoring && this.performanceMonitor && this.config) {
      const iframeId = this.generateIframeId(this.config);
      this.performanceMonitor.recordError(iframeId, new Error(error));
    }

    // Emit error event
    this.emit('error', {
      type: 'error',
      timestamp: Date.now(),
      data: { error },
    });
  };

  /**
   * Setup load timeout
   */
  private setupLoadTimeout(): void {
    const timeout = this.config?.timeout || 30000; // 30 seconds default

    if (this.loadTimeout) {
      clearTimeout(this.loadTimeout);
    }

    this.loadTimeout = setTimeout(() => {
      if (this.loadState.status === IframeStatus.LOADING) {
        this.handleLoadTimeout();
      }
    }, timeout);
  }

  /**
   * Handle load timeout
   */
  private handleLoadTimeout(): void {
    const maxRetries = this.config?.retryAttempts || 3;

    if (this.retryCount < maxRetries) {
      this.retryCount++;
      this.refresh();
    } else {
      const error = `iframe load timeout after ${maxRetries} retries`;

      this.loadState = {
        isLoading: false,
        progress: 0,
        error,
        status: IframeStatus.ERROR,
      };

      // Emit error event
      this.emit('error', {
        type: 'error',
        timestamp: Date.now(),
        data: { error, retries: this.retryCount },
      });
    }
  }

  /**
   * Emit event to all registered listeners
   */
  private emit(event: string, data: IframeLifecycleEvent): void {
    const callbacks = this.eventCallbacks.get(event);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(data);
        } catch (err) {
          console.error(`Error in iframe event listener for ${event}:`, err);
        }
      });
    }
  }

  /**
   * Generate unique iframe ID
   */
  private generateIframeId(config: IframeConfig): string {
    return `iframe-${config.projectId}-${config.taskId || 'default'}-${config.userId}`;
  }

  /**
   * Create placeholder iframe for lazy loading
   */
  private createPlaceholderIframe(): HTMLIFrameElement {
    const iframe = document.createElement('iframe');
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.backgroundColor = '#f5f5f5';
    iframe.title = 'Loading Label Studio...';
    
    // Add loading indicator
    iframe.srcdoc = `
      <html>
        <body style="margin:0;padding:20px;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#f5f5f5;">
          <div style="text-align:center;">
            <div style="width:40px;height:40px;border:4px solid #e0e0e0;border-top:4px solid #1890ff;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 16px;"></div>
            <div style="color:#666;font-size:14px;">Loading Label Studio...</div>
          </div>
          <style>
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          </style>
        </body>
      </html>
    `;
    
    return iframe;
  }

  /**
   * Create actual iframe element
   */
  private createIframeElement(config: IframeConfig, container: HTMLElement): HTMLIFrameElement {
    const iframe = document.createElement('iframe');
    
    // Record load start time
    this.loadState.loadStartTime = Date.now();
    
    // Check cache for preloaded content
    if (this.enableCaching && this.resourceCache) {
      const cachedContent = this.resourceCache.get(config.url);
      if (cachedContent) {
        // Use cached content if available
        iframe.srcdoc = cachedContent as string;
      } else {
        iframe.src = config.url;
      }
    } else {
      iframe.src = config.url;
    }

    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.display = 'block';
    iframe.title = 'Label Studio';
    iframe.allow = 'clipboard-read; clipboard-write';

    // Setup event listeners
    this.setupIframeListeners();

    // Append to container
    container.appendChild(iframe);

    // Setup load timeout
    this.setupLoadTimeout();

    this.iframe = iframe;
    return iframe;
  }

  /**
   * Get performance statistics
   */
  getPerformanceStats(): {
    lazyLoading?: any;
    caching?: any;
    monitoring?: any;
    loadTime?: number;
  } {
    const stats: any = {};

    if (this.lazyLoader) {
      stats.lazyLoading = this.lazyLoader.getPreloadStats();
    }

    if (this.resourceCache) {
      stats.caching = this.resourceCache.getStats();
    }

    if (this.performanceMonitor) {
      stats.monitoring = this.performanceMonitor.getOverallSummary();
    }

    if (this.loadState.loadStartTime && this.loadState.loadEndTime) {
      stats.loadTime = this.loadState.loadEndTime - this.loadState.loadStartTime;
    }

    return stats;
  }

  /**
   * Get performance report for current iframe
   */
  getPerformanceReport(): PerformanceReport | null {
    if (!this.performanceMonitor || !this.config) {
      return null;
    }

    const iframeId = this.generateIframeId(this.config);
    return this.performanceMonitor.generateReport(iframeId);
  }

  /**
   * Record performance error
   */
  recordError(error: Error): void {
    if (this.performanceMonitor && this.config) {
      const iframeId = this.generateIframeId(this.config);
      this.performanceMonitor.recordError(iframeId, error);
    }
  }

  /**
   * Preload resources for better performance
   */
  async preloadResources(urls: string[]): Promise<void> {
    if (this.resourceCache) {
      await this.resourceCache.preloadResources(urls);
    }
  }

  /**
   * Cleanup performance optimization resources
   */
  destroyPerformanceOptimization(): void {
    if (this.lazyLoader) {
      this.lazyLoader.destroy();
      this.lazyLoader = null;
    }

    if (this.resourceCache) {
      this.resourceCache.destroy();
      this.resourceCache = null;
    }

    if (this.performanceMonitor) {
      if (this.config) {
        const iframeId = this.generateIframeId(this.config);
        this.performanceMonitor.stopMonitoring(iframeId);
      }
      this.performanceMonitor.destroy();
      this.performanceMonitor = null;
    }

    this.enableLazyLoading = false;
    this.enableCaching = false;
    this.enablePerformanceMonitoring = false;
  }
}
