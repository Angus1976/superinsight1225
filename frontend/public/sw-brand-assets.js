/**
 * Brand Assets Service Worker
 * 问视间品牌资源缓存服务
 * 
 * 功能：
 * - 品牌资源离线缓存
 * - 版本化资源管理
 * - 智能缓存失效机制
 * - 性能监控
 */

const CACHE_NAME = 'brand-assets-v1';
const BRAND_ASSET_VERSION = '1.0.0';

// 品牌资源列表
const BRAND_ASSETS = [
  '/favicon.svg',
  '/logo-wenshijian.svg',
  '/logo-wenshijian-simple.svg',
  '/logo-wenshijian-full.svg'
];

// 缓存配置
const CACHE_CONFIG = {
  maxAge: 7 * 24 * 60 * 60 * 1000, // 7天
  maxEntries: 50,
  networkTimeoutMs: 3000
};

// 性能指标收集
const performanceMetrics = {
  cacheHits: 0,
  cacheMisses: 0,
  networkFetches: 0,
  errors: 0
};

/**
 * 安装事件 - 预缓存品牌资源
 */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Brand SW] Pre-caching brand assets');
        return cache.addAll(BRAND_ASSETS);
      })
      .then(() => {
        console.log('[Brand SW] Brand assets cached successfully');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[Brand SW] Failed to cache brand assets:', error);
      })
  );
});

/**
 * 激活事件 - 清理旧缓存
 */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name.startsWith('brand-assets-') && name !== CACHE_NAME)
            .map((name) => {
              console.log('[Brand SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[Brand SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

/**
 * 检查是否为品牌资源请求
 */
function isBrandAssetRequest(url) {
  return BRAND_ASSETS.some((asset) => url.pathname.endsWith(asset));
}

/**
 * 缓存优先策略 - 用于品牌资源
 */
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    performanceMetrics.cacheHits++;
    
    // 后台更新缓存（stale-while-revalidate）
    updateCacheInBackground(request);
    
    return cachedResponse;
  }
  
  performanceMetrics.cacheMisses++;
  return fetchAndCache(request);
}

/**
 * 网络请求并缓存
 */
async function fetchAndCache(request) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CACHE_CONFIG.networkTimeoutMs);
    
    const response = await fetch(request, { signal: controller.signal });
    clearTimeout(timeoutId);
    
    if (response.ok) {
      performanceMetrics.networkFetches++;
      
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
      
      return response;
    }
    
    throw new Error(`Network response was not ok: ${response.status}`);
  } catch (error) {
    performanceMetrics.errors++;
    console.error('[Brand SW] Fetch failed:', error);
    
    // 尝试返回缓存的旧版本
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    throw error;
  }
}

/**
 * 后台更新缓存
 */
async function updateCacheInBackground(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response);
    }
  } catch (error) {
    // 静默失败，不影响用户体验
    console.debug('[Brand SW] Background update failed:', error);
  }
}

/**
 * Fetch事件处理
 */
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // 只处理品牌资源请求
  if (isBrandAssetRequest(url)) {
    event.respondWith(cacheFirst(event.request));
  }
});

/**
 * 消息处理 - 用于与主线程通信
 */
self.addEventListener('message', (event) => {
  const { type, data } = event.data || {};
  
  switch (type) {
    case 'GET_METRICS':
      event.ports[0].postMessage({
        type: 'METRICS',
        data: { ...performanceMetrics, version: BRAND_ASSET_VERSION }
      });
      break;
      
    case 'CLEAR_CACHE':
      caches.delete(CACHE_NAME).then(() => {
        event.ports[0].postMessage({ type: 'CACHE_CLEARED' });
      });
      break;
      
    case 'UPDATE_CACHE':
      caches.open(CACHE_NAME)
        .then((cache) => cache.addAll(BRAND_ASSETS))
        .then(() => {
          event.ports[0].postMessage({ type: 'CACHE_UPDATED' });
        });
      break;
      
    case 'GET_VERSION':
      event.ports[0].postMessage({
        type: 'VERSION',
        data: { version: BRAND_ASSET_VERSION, cacheName: CACHE_NAME }
      });
      break;
  }
});

console.log('[Brand SW] Service worker loaded, version:', BRAND_ASSET_VERSION);
