/**
 * LazyLoader - Implements lazy loading and preloading for iframes
 * Optimizes performance by loading iframes only when needed
 */

import { IframeConfig } from './types';

export interface LazyLoadConfig {
  threshold?: number; // Intersection threshold (0-1)
  rootMargin?: string; // Root margin for intersection observer
  preloadDistance?: number; // Distance in pixels to start preloading
  enablePreload?: boolean; // Enable preloading
  maxPreloadCount?: number; // Maximum number of preloaded iframes
  preloadTimeout?: number; // Timeout for preload operations
}

export interface PreloadedIframe {
  id: string;
  iframe: HTMLIFrameElement;
  config: IframeConfig;
  loadTime: number;
  isReady: boolean;
  lastAccessed: number;
}

export interface LazyLoadState {
  isVisible: boolean;
  isLoading: boolean;
  isPreloaded: boolean;
  loadStartTime?: number;
  loadEndTime?: number;
  error?: string;
}

export class LazyLoader {
  private observer: IntersectionObserver | null = null;
  private config: LazyLoadConfig;
  private preloadedIframes: Map<string, PreloadedIframe> = new Map();
  private loadStates: Map<string, LazyLoadState> = new Map();
  private preloadQueue: string[] = [];
  private isPreloading = false;

  constructor(config: LazyLoadConfig = {}) {
    this.config = {
      threshold: 0.1,
      rootMargin: '50px',
      preloadDistance: 200,
      enablePreload: true,
      maxPreloadCount: 3,
      preloadTimeout: 10000,
      ...config,
    };

    this.initializeObserver();
  }

  /**
   * Initialize intersection observer for lazy loading
   */
  private initializeObserver(): void {
    if (!('IntersectionObserver' in window)) {
      console.warn('IntersectionObserver not supported, falling back to immediate loading');
      return;
    }

    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const element = entry.target as HTMLElement;
          const iframeId = element.dataset.iframeId;
          
          if (!iframeId) return;

          const state = this.loadStates.get(iframeId);
          if (!state) return;

          if (entry.isIntersecting && !state.isVisible) {
            this.handleElementVisible(iframeId, element);
          } else if (!entry.isIntersecting && state.isVisible) {
            this.handleElementHidden(iframeId);
          }
        });
      },
      {
        threshold: this.config.threshold,
        rootMargin: this.config.rootMargin,
      }
    );
  }

  /**
   * Register element for lazy loading
   */
  observe(element: HTMLElement, iframeId: string, config: IframeConfig): void {
    if (!this.observer) {
      // Fallback: load immediately if observer not available
      this.loadIframe(iframeId, element, config);
      return;
    }

    // Set iframe ID on element
    element.dataset.iframeId = iframeId;

    // Initialize load state
    this.loadStates.set(iframeId, {
      isVisible: false,
      isLoading: false,
      isPreloaded: false,
    });

    // Start observing
    this.observer.observe(element);

    // Check if preloading is enabled and queue for preload
    if (this.config.enablePreload) {
      this.queueForPreload(iframeId, config);
    }
  }

  /**
   * Unregister element from lazy loading
   */
  unobserve(element: HTMLElement, iframeId: string): void {
    if (this.observer) {
      this.observer.unobserve(element);
    }

    // Cleanup state
    this.loadStates.delete(iframeId);
    
    // Remove from preload queue
    const queueIndex = this.preloadQueue.indexOf(iframeId);
    if (queueIndex > -1) {
      this.preloadQueue.splice(queueIndex, 1);
    }

    // Cleanup preloaded iframe
    this.cleanupPreloadedIframe(iframeId);
  }

  /**
   * Handle element becoming visible
   */
  private handleElementVisible(iframeId: string, element: HTMLElement): void {
    const state = this.loadStates.get(iframeId);
    if (!state) return;

    state.isVisible = true;

    // Check if already preloaded
    const preloaded = this.preloadedIframes.get(iframeId);
    if (preloaded && preloaded.isReady) {
      this.usePreloadedIframe(iframeId, element, preloaded);
    } else if (!state.isLoading) {
      // Load iframe normally
      const config = this.getConfigFromElement(element);
      if (config) {
        this.loadIframe(iframeId, element, config);
      }
    }
  }

  /**
   * Handle element becoming hidden
   */
  private handleElementHidden(iframeId: string): void {
    const state = this.loadStates.get(iframeId);
    if (state) {
      state.isVisible = false;
    }
  }

  /**
   * Queue iframe for preloading
   */
  private queueForPreload(iframeId: string, config: IframeConfig): void {
    if (this.preloadQueue.includes(iframeId)) return;
    if (this.preloadedIframes.has(iframeId)) return;

    this.preloadQueue.push(iframeId);
    this.processPreloadQueue();
  }

  /**
   * Process preload queue
   */
  private async processPreloadQueue(): Promise<void> {
    if (this.isPreloading) return;
    if (this.preloadQueue.length === 0) return;
    if (this.preloadedIframes.size >= (this.config.maxPreloadCount || 3)) {
      this.cleanupOldestPreloadedIframe();
    }

    this.isPreloading = true;

    try {
      const iframeId = this.preloadQueue.shift();
      if (iframeId) {
        await this.preloadIframe(iframeId);
      }
    } catch (error) {
      console.error('Error preloading iframe:', error);
    } finally {
      this.isPreloading = false;
      
      // Process next item in queue
      if (this.preloadQueue.length > 0) {
        setTimeout(() => this.processPreloadQueue(), 100);
      }
    }
  }

  /**
   * Preload iframe in background
   */
  private async preloadIframe(iframeId: string): Promise<void> {
    const config = this.getStoredConfig(iframeId);
    if (!config) return;

    return new Promise((resolve, reject) => {
      const iframe = document.createElement('iframe');
      iframe.src = config.url;
      iframe.style.position = 'absolute';
      iframe.style.left = '-9999px';
      iframe.style.top = '-9999px';
      iframe.style.width = '1px';
      iframe.style.height = '1px';
      iframe.style.visibility = 'hidden';
      iframe.title = 'Preloaded Label Studio';

      const timeout = setTimeout(() => {
        cleanup();
        reject(new Error('Preload timeout'));
      }, this.config.preloadTimeout);

      const cleanup = () => {
        clearTimeout(timeout);
        iframe.removeEventListener('load', onLoad);
        iframe.removeEventListener('error', onError);
      };

      const onLoad = () => {
        cleanup();
        
        const preloaded: PreloadedIframe = {
          id: iframeId,
          iframe,
          config,
          loadTime: Date.now(),
          isReady: true,
          lastAccessed: Date.now(),
        };

        this.preloadedIframes.set(iframeId, preloaded);
        
        const state = this.loadStates.get(iframeId);
        if (state) {
          state.isPreloaded = true;
        }

        resolve();
      };

      const onError = () => {
        cleanup();
        document.body.removeChild(iframe);
        reject(new Error('Failed to preload iframe'));
      };

      iframe.addEventListener('load', onLoad);
      iframe.addEventListener('error', onError);

      // Add to DOM (hidden)
      document.body.appendChild(iframe);
    });
  }

  /**
   * Use preloaded iframe
   */
  private usePreloadedIframe(
    iframeId: string,
    container: HTMLElement,
    preloaded: PreloadedIframe
  ): void {
    const iframe = preloaded.iframe;
    
    // Update iframe styles for visible use
    iframe.style.position = 'static';
    iframe.style.left = 'auto';
    iframe.style.top = 'auto';
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.visibility = 'visible';
    iframe.style.border = 'none';

    // Move to container
    container.appendChild(iframe);

    // Update access time
    preloaded.lastAccessed = Date.now();

    // Update state
    const state = this.loadStates.get(iframeId);
    if (state) {
      state.isLoading = false;
      state.loadEndTime = Date.now();
    }

    // Remove from preloaded map since it's now in use
    this.preloadedIframes.delete(iframeId);
  }

  /**
   * Load iframe normally (not preloaded)
   */
  private loadIframe(iframeId: string, container: HTMLElement, config: IframeConfig): void {
    const state = this.loadStates.get(iframeId);
    if (!state) return;

    state.isLoading = true;
    state.loadStartTime = Date.now();

    const iframe = document.createElement('iframe');
    iframe.src = config.url;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.title = 'Label Studio';
    iframe.allow = 'clipboard-read; clipboard-write';

    const onLoad = () => {
      state.isLoading = false;
      state.loadEndTime = Date.now();
      iframe.removeEventListener('load', onLoad);
      iframe.removeEventListener('error', onError);
    };

    const onError = () => {
      state.isLoading = false;
      state.error = 'Failed to load iframe';
      iframe.removeEventListener('load', onLoad);
      iframe.removeEventListener('error', onError);
    };

    iframe.addEventListener('load', onLoad);
    iframe.addEventListener('error', onError);

    container.appendChild(iframe);
  }

  /**
   * Cleanup oldest preloaded iframe to make room for new ones
   */
  private cleanupOldestPreloadedIframe(): void {
    let oldest: PreloadedIframe | null = null;
    let oldestId = '';

    for (const [id, preloaded] of this.preloadedIframes) {
      if (!oldest || preloaded.lastAccessed < oldest.lastAccessed) {
        oldest = preloaded;
        oldestId = id;
      }
    }

    if (oldest) {
      this.cleanupPreloadedIframe(oldestId);
    }
  }

  /**
   * Cleanup specific preloaded iframe
   */
  private cleanupPreloadedIframe(iframeId: string): void {
    const preloaded = this.preloadedIframes.get(iframeId);
    if (preloaded) {
      if (preloaded.iframe.parentElement) {
        preloaded.iframe.parentElement.removeChild(preloaded.iframe);
      }
      this.preloadedIframes.delete(iframeId);
    }
  }

  /**
   * Get config from element data attributes (placeholder implementation)
   */
  private getConfigFromElement(element: HTMLElement): IframeConfig | null {
    // This would typically extract config from data attributes
    // For now, return null to indicate config should be provided externally
    return null;
  }

  /**
   * Get stored config for iframe (placeholder implementation)
   */
  private getStoredConfig(iframeId: string): IframeConfig | null {
    // This would typically retrieve stored config
    // For now, return null to indicate config should be provided externally
    return null;
  }

  /**
   * Get load state for iframe
   */
  getLoadState(iframeId: string): LazyLoadState | null {
    return this.loadStates.get(iframeId) || null;
  }

  /**
   * Get preload statistics
   */
  getPreloadStats(): {
    preloadedCount: number;
    queueLength: number;
    isPreloading: boolean;
    preloadedIds: string[];
  } {
    return {
      preloadedCount: this.preloadedIframes.size,
      queueLength: this.preloadQueue.length,
      isPreloading: this.isPreloading,
      preloadedIds: Array.from(this.preloadedIframes.keys()),
    };
  }

  /**
   * Cleanup all resources
   */
  destroy(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }

    // Cleanup all preloaded iframes
    for (const iframeId of this.preloadedIframes.keys()) {
      this.cleanupPreloadedIframe(iframeId);
    }

    this.preloadedIframes.clear();
    this.loadStates.clear();
    this.preloadQueue.length = 0;
    this.isPreloading = false;
  }
}