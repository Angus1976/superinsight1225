/**
 * ResourceCache - Manages caching of iframe resources and assets
 * Optimizes performance by caching frequently used resources
 */

export interface CacheEntry<T = any> {
  key: string;
  data: T;
  timestamp: number;
  accessCount: number;
  lastAccessed: number;
  size: number;
  ttl?: number; // Time to live in milliseconds
  metadata?: Record<string, any>;
}

export interface CacheConfig {
  maxSize?: number; // Maximum cache size in bytes
  maxEntries?: number; // Maximum number of entries
  defaultTTL?: number; // Default TTL in milliseconds
  enableCompression?: boolean; // Enable data compression
  enablePersistence?: boolean; // Enable localStorage persistence
  storageKey?: string; // Key for localStorage
  cleanupInterval?: number; // Cleanup interval in milliseconds
}

export interface CacheStats {
  totalEntries: number;
  totalSize: number;
  hitCount: number;
  missCount: number;
  hitRate: number;
  oldestEntry?: number;
  newestEntry?: number;
}

export class ResourceCache {
  private cache: Map<string, CacheEntry> = new Map();
  private config: Required<CacheConfig>;
  private stats = {
    hitCount: 0,
    missCount: 0,
  };
  private cleanupTimer: NodeJS.Timeout | null = null;

  constructor(config: CacheConfig = {}) {
    this.config = {
      maxSize: 50 * 1024 * 1024, // 50MB default
      maxEntries: 1000,
      defaultTTL: 30 * 60 * 1000, // 30 minutes
      enableCompression: false,
      enablePersistence: true,
      storageKey: 'iframe-resource-cache',
      cleanupInterval: 5 * 60 * 1000, // 5 minutes
      ...config,
    };

    this.initializeCache();
    this.startCleanupTimer();
  }

  /**
   * Initialize cache from persistent storage
   */
  private initializeCache(): void {
    if (!this.config.enablePersistence || typeof localStorage === 'undefined') {
      return;
    }

    try {
      const stored = localStorage.getItem(this.config.storageKey);
      if (stored) {
        const data = JSON.parse(stored);
        if (data.entries && Array.isArray(data.entries)) {
          data.entries.forEach((entry: CacheEntry) => {
            // Check if entry is still valid
            if (!this.isExpired(entry)) {
              this.cache.set(entry.key, entry);
            }
          });
        }
      }
    } catch (error) {
      console.warn('Failed to load cache from localStorage:', error);
    }
  }

  /**
   * Start cleanup timer
   */
  private startCleanupTimer(): void {
    this.cleanupTimer = setInterval(() => {
      this.cleanup();
    }, this.config.cleanupInterval);
  }

  /**
   * Set cache entry
   */
  set<T>(key: string, data: T, ttl?: number, metadata?: Record<string, any>): void {
    const size = this.calculateSize(data);
    const entry: CacheEntry<T> = {
      key,
      data,
      timestamp: Date.now(),
      accessCount: 0,
      lastAccessed: Date.now(),
      size,
      ttl: ttl || this.config.defaultTTL,
      metadata,
    };

    // Check if we need to make room
    this.ensureCapacity(size);

    // Add entry
    this.cache.set(key, entry);

    // Persist to storage
    this.persistCache();
  }

  /**
   * Get cache entry
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      this.stats.missCount++;
      return null;
    }

    // Check if expired
    if (this.isExpired(entry)) {
      this.cache.delete(key);
      this.stats.missCount++;
      return null;
    }

    // Update access statistics
    entry.accessCount++;
    entry.lastAccessed = Date.now();
    this.stats.hitCount++;

    return entry.data as T;
  }

  /**
   * Check if entry exists and is valid
   */
  has(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;
    
    if (this.isExpired(entry)) {
      this.cache.delete(key);
      return false;
    }
    
    return true;
  }

  /**
   * Delete cache entry
   */
  delete(key: string): boolean {
    const result = this.cache.delete(key);
    if (result) {
      this.persistCache();
    }
    return result;
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    this.stats.hitCount = 0;
    this.stats.missCount = 0;
    this.persistCache();
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    const entries = Array.from(this.cache.values());
    const totalSize = entries.reduce((sum, entry) => sum + entry.size, 0);
    const timestamps = entries.map(entry => entry.timestamp);
    
    return {
      totalEntries: this.cache.size,
      totalSize,
      hitCount: this.stats.hitCount,
      missCount: this.stats.missCount,
      hitRate: this.stats.hitCount / (this.stats.hitCount + this.stats.missCount) || 0,
      oldestEntry: timestamps.length > 0 ? Math.min(...timestamps) : undefined,
      newestEntry: timestamps.length > 0 ? Math.max(...timestamps) : undefined,
    };
  }

  /**
   * Get all cache keys
   */
  keys(): string[] {
    return Array.from(this.cache.keys());
  }

  /**
   * Get cache entries matching pattern
   */
  getByPattern(pattern: RegExp): Array<{ key: string; data: any }> {
    const results: Array<{ key: string; data: any }> = [];
    
    for (const [key, entry] of this.cache) {
      if (pattern.test(key) && !this.isExpired(entry)) {
        entry.accessCount++;
        entry.lastAccessed = Date.now();
        results.push({ key, data: entry.data });
      }
    }
    
    return results;
  }

  /**
   * Preload resources for given URLs
   */
  async preloadResources(urls: string[]): Promise<void> {
    const promises = urls.map(url => this.preloadResource(url));
    await Promise.allSettled(promises);
  }

  /**
   * Preload single resource
   */
  private async preloadResource(url: string): Promise<void> {
    if (this.has(url)) {
      return; // Already cached
    }

    try {
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.arrayBuffer();
        this.set(url, data, undefined, {
          contentType: response.headers.get('content-type'),
          contentLength: response.headers.get('content-length'),
          lastModified: response.headers.get('last-modified'),
        });
      }
    } catch (error) {
      console.warn(`Failed to preload resource ${url}:`, error);
    }
  }

  /**
   * Check if entry is expired
   */
  private isExpired(entry: CacheEntry): boolean {
    if (!entry.ttl) return false;
    return Date.now() - entry.timestamp > entry.ttl;
  }

  /**
   * Calculate size of data
   */
  private calculateSize(data: any): number {
    if (data instanceof ArrayBuffer) {
      return data.byteLength;
    }
    
    if (typeof data === 'string') {
      return new Blob([data]).size;
    }
    
    if (data && typeof data === 'object') {
      return new Blob([JSON.stringify(data)]).size;
    }
    
    return 0;
  }

  /**
   * Ensure cache has capacity for new entry
   */
  private ensureCapacity(newEntrySize: number): void {
    const currentSize = this.getCurrentSize();
    
    // Check size limit
    while (currentSize + newEntrySize > this.config.maxSize && this.cache.size > 0) {
      this.evictLeastRecentlyUsed();
    }
    
    // Check entry count limit
    while (this.cache.size >= this.config.maxEntries) {
      this.evictLeastRecentlyUsed();
    }
  }

  /**
   * Get current cache size
   */
  private getCurrentSize(): number {
    return Array.from(this.cache.values()).reduce((sum, entry) => sum + entry.size, 0);
  }

  /**
   * Evict least recently used entry
   */
  private evictLeastRecentlyUsed(): void {
    let lruKey = '';
    let lruTime = Date.now();
    
    for (const [key, entry] of this.cache) {
      if (entry.lastAccessed < lruTime) {
        lruTime = entry.lastAccessed;
        lruKey = key;
      }
    }
    
    if (lruKey) {
      this.cache.delete(lruKey);
    }
  }

  /**
   * Cleanup expired entries
   */
  private cleanup(): void {
    const keysToDelete: string[] = [];
    
    for (const [key, entry] of this.cache) {
      if (this.isExpired(entry)) {
        keysToDelete.push(key);
      }
    }
    
    keysToDelete.forEach(key => this.cache.delete(key));
    
    if (keysToDelete.length > 0) {
      this.persistCache();
    }
  }

  /**
   * Persist cache to localStorage
   */
  private persistCache(): void {
    if (!this.config.enablePersistence || typeof localStorage === 'undefined') {
      return;
    }

    try {
      const data = {
        entries: Array.from(this.cache.values()),
        timestamp: Date.now(),
      };
      
      localStorage.setItem(this.config.storageKey, JSON.stringify(data));
    } catch (error) {
      console.warn('Failed to persist cache to localStorage:', error);
    }
  }

  /**
   * Destroy cache and cleanup resources
   */
  destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    
    this.clear();
  }
}