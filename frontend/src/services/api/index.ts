// API service exports
import apiClient, { optimizedApiClient } from './client';

// Export both clients
export { apiClient, optimizedApiClient };

// Create a unified api object for backward compatibility
export const api = {
  get: optimizedApiClient.get.bind(optimizedApiClient),
  post: optimizedApiClient.post.bind(optimizedApiClient),
  put: optimizedApiClient.put.bind(optimizedApiClient),
  patch: optimizedApiClient.patch.bind(optimizedApiClient),
  delete: optimizedApiClient.delete.bind(optimizedApiClient),
  clearCache: optimizedApiClient.clearCache.bind(optimizedApiClient),
  invalidateCache: optimizedApiClient.invalidateCache.bind(optimizedApiClient),
  getPerformanceMetrics: optimizedApiClient.getPerformanceMetrics.bind(optimizedApiClient),
};

export default api;
