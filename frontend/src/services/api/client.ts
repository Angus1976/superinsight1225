// Axios API client with performance optimization
import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
  type AxiosError,
} from 'axios';
import { getToken, setToken, isTokenExpired, getRefreshToken, clearAuthTokens } from '@/utils/token';
import { API_ENDPOINTS } from '@/constants';
import {
  apiPerformanceMonitor,
  requestCache,
  requestDeduplicator,
  isCacheableEndpoint,
  API_RESPONSE_BUDGET,
  type ApiPerformanceMetrics,
} from '@/utils/apiPerformance';

// Optimized timeout for API response budget compliance
// Increased to 10 seconds to prevent premature timeouts during workspace loading
const OPTIMIZED_TIMEOUT = 10000;

/**
 * Auth endpoints that may legitimately return 401 (e.g. wrong password on login).
 * They must not trigger the refresh-token flow: auth_simple does not issue refresh_token,
 * so the interceptor would always log errors and force-redirect.
 */
function isPublicAuthRequest(config: InternalAxiosRequestConfig | undefined): boolean {
  const raw = config?.url;
  if (!raw) return false;
  try {
    const path = raw.startsWith('http') ? new URL(raw).pathname : raw.split('?')[0];
    const publicPaths = [
      '/api/auth/login',
      '/api/auth/register',
      '/api/auth/forgot-password',
      '/api/auth/reset-password',
      '/api/auth/refresh',
      '/api/auth/tenants',
    ];
    return publicPaths.some((p) => path === p || path.endsWith(p));
  } catch {
    return false;
  }
}

// Create axios instance with optimized settings
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  timeout: OPTIMIZED_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor with performance tracking
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken();
    if (token && !isTokenExpired(token)) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add request start time for performance tracking
    (config as InternalAxiosRequestConfig & { metadata?: { startTime: number } }).metadata = {
      startTime: performance.now(),
    };
    
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor with performance tracking
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Track API performance
    const config = response.config as InternalAxiosRequestConfig & { metadata?: { startTime: number } };
    if (config.metadata?.startTime) {
      const responseTime = performance.now() - config.metadata.startTime;
      const metrics: ApiPerformanceMetrics = {
        endpoint: config.url || 'unknown',
        method: (config.method || 'GET').toUpperCase(),
        responseTime: Math.round(responseTime),
        isWithinBudget: responseTime <= API_RESPONSE_BUDGET,
        timestamp: Date.now(),
        cached: false,
        status: response.status,
      };
      apiPerformanceMonitor.record(metrics);
      
      // Cache successful GET responses for cacheable endpoints
      if (config.method?.toUpperCase() === 'GET' && config.url) {
        const { cacheable, ttl } = isCacheableEndpoint(config.url, 'GET');
        if (cacheable) {
          const cacheKey = requestCache.generateKey(config);
          requestCache.set(cacheKey, response.data, ttl);
        }
      }
    }
    
    return response;
  },
  async (error: AxiosError) => {
    // Track failed API calls
    const config = error.config as InternalAxiosRequestConfig & { metadata?: { startTime: number } };
    if (config?.metadata?.startTime) {
      const responseTime = performance.now() - config.metadata.startTime;
      const metrics: ApiPerformanceMetrics = {
        endpoint: config.url || 'unknown',
        method: (config.method || 'GET').toUpperCase(),
        responseTime: Math.round(responseTime),
        isWithinBudget: false,
        timestamp: Date.now(),
        cached: false,
        status: error.response?.status,
        error: error.message,
      };
      apiPerformanceMonitor.record(metrics);
    }
    
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isPublicAuthRequest(originalRequest)) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const refreshUrl = `${apiClient.defaults.baseURL ?? ''}${API_ENDPOINTS.AUTH.REFRESH}`;
          const response = await axios.post(refreshUrl, {
            refresh_token: refreshToken,
          });
          const newToken = response.data.access_token;
          setToken(newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        } catch {
          // Refresh failed, clear tokens and redirect to login
          console.error('[API Client] Token refresh failed, redirecting to login');
          clearAuthTokens();
          // Only redirect if not already on login page
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          return Promise.reject(error);
        }
      } else {
        // No refresh token, clear tokens and redirect to login
        console.error('[API Client] No refresh token available, redirecting to login');
        clearAuthTokens();
        // Only redirect if not already on login page
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Enhanced API client with caching and deduplication support
 */
export const optimizedApiClient = {
  /**
   * GET request with optional caching
   */
  async get<T>(
    url: string,
    config?: AxiosRequestConfig & { useCache?: boolean; cacheTtl?: number }
  ): Promise<AxiosResponse<T>> {
    const { useCache = true, cacheTtl, ...axiosConfig } = config || {};
    
    // Check cache first
    if (useCache) {
      const cacheKey = requestCache.generateKey({ method: 'GET', url, ...axiosConfig });
      const cached = requestCache.get<T>(cacheKey);
      
      if (cached !== null) {
        // Record cache hit
        apiPerformanceMonitor.record({
          endpoint: url,
          method: 'GET',
          responseTime: 0,
          isWithinBudget: true,
          timestamp: Date.now(),
          cached: true,
        });
        
        return { data: cached, status: 200, statusText: 'OK', headers: {}, config: axiosConfig } as AxiosResponse<T>;
      }
    }
    
    // Make actual request with deduplication
    const cacheKey = requestCache.generateKey({ method: 'GET', url, ...axiosConfig });
    const { data, deduplicated } = await requestDeduplicator.deduplicate(
      cacheKey,
      () => apiClient.get<T>(url, axiosConfig)
    );
    
    // Cache the response if cacheable
    if (useCache && !deduplicated) {
      const { cacheable, ttl } = isCacheableEndpoint(url, 'GET');
      if (cacheable) {
        requestCache.set(cacheKey, (data as AxiosResponse<T>).data, cacheTtl || ttl);
      }
    }
    
    return data as AxiosResponse<T>;
  },

  /**
   * POST request (no caching, invalidates related cache)
   */
  async post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const response = await apiClient.post<T>(url, data, config);
    
    // Invalidate related cache entries
    requestCache.invalidatePattern(url.split('/').slice(0, -1).join('/'));
    
    return response;
  },

  /**
   * PUT request (no caching, invalidates related cache)
   */
  async put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const response = await apiClient.put<T>(url, data, config);
    
    // Invalidate related cache entries
    requestCache.invalidatePattern(url.split('/').slice(0, -1).join('/'));
    
    return response;
  },

  /**
   * PATCH request (no caching, invalidates related cache)
   */
  async patch<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const response = await apiClient.patch<T>(url, data, config);
    
    // Invalidate related cache entries
    requestCache.invalidatePattern(url.split('/').slice(0, -1).join('/'));
    
    return response;
  },

  /**
   * DELETE request (no caching, invalidates related cache)
   */
  async delete<T>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const response = await apiClient.delete<T>(url, config);
    
    // Invalidate related cache entries
    requestCache.invalidatePattern(url.split('/').slice(0, -1).join('/'));
    
    return response;
  },

  /**
   * Clear all cached data
   */
  clearCache(): void {
    requestCache.clear();
  },

  /**
   * Invalidate specific cache entries
   */
  invalidateCache(pattern: string | RegExp): void {
    requestCache.invalidatePattern(pattern);
  },

  /**
   * Get performance metrics
   */
  getPerformanceMetrics() {
    return apiPerformanceMonitor.getSummary();
  },
};

export default apiClient;
