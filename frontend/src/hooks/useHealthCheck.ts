/**
 * Health Check Hook
 * 检查后台服务健康状态
 */

import { useState, useEffect } from 'react';
import { api } from '@/services/api';

interface HealthStatus {
  isHealthy: boolean;
  isLoading: boolean;
  error: string | null;
}

export const useHealthCheck = (): HealthStatus => {
  const [isHealthy, setIsHealthy] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/health');
        setIsHealthy(response.data?.status === 'healthy');
        setError(null);
      } catch (err) {
        setIsHealthy(false);
        setError(err instanceof Error ? err.message : 'Health check failed');
      } finally {
        setIsLoading(false);
      }
    };

    checkHealth();
  }, []);

  return { isHealthy, isLoading, error };
};
