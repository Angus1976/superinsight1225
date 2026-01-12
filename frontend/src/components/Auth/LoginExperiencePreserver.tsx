/**
 * LoginExperiencePreserver Component
 * 
 * This component ensures backward compatibility and maintains the existing login experience
 * while supporting multi-tenant features. It handles:
 * - Automatic tenant detection for single-tenant deployments
 * - Graceful fallback when tenant API is unavailable
 * - Seamless transition between single and multi-tenant modes
 * - Preservation of existing login flow and UX
 */

import { useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { authService } from '@/services/auth';
import type { Tenant } from '@/types';

export interface LoginExperienceConfig {
  // Whether to show tenant selector (auto-detected if not specified)
  showTenantSelector?: boolean;
  // Default tenant ID for single-tenant deployments
  defaultTenantId?: string;
  // Whether to auto-select single tenant
  autoSelectSingleTenant?: boolean;
  // Callback when tenant mode is determined
  onTenantModeDetected?: (isMultiTenant: boolean) => void;
}

export interface LoginExperienceState {
  tenants: Tenant[];
  isMultiTenant: boolean;
  isLoading: boolean;
  error: string | null;
  selectedTenantId: string | null;
}

export interface UseLoginExperienceReturn extends LoginExperienceState {
  selectTenant: (tenantId: string) => void;
  refreshTenants: () => Promise<void>;
  shouldShowTenantSelector: boolean;
}

/**
 * Hook to manage login experience with multi-tenant support
 * while preserving the existing single-tenant login flow
 */
export function useLoginExperience(config: LoginExperienceConfig = {}): UseLoginExperienceReturn {
  const { t } = useTranslation('auth');
  const {
    showTenantSelector,
    defaultTenantId,
    autoSelectSingleTenant = true,
    onTenantModeDetected,
  } = config;

  const [state, setState] = useState<LoginExperienceState>({
    tenants: [],
    isMultiTenant: false,
    isLoading: true,
    error: null,
    selectedTenantId: defaultTenantId || null,
  });

  const loadTenants = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const tenantList = await authService.getTenants();
      
      const isMultiTenant = tenantList.length > 1;
      let selectedTenantId = state.selectedTenantId;
      
      // Auto-select single tenant if configured
      if (autoSelectSingleTenant && tenantList.length === 1) {
        selectedTenantId = tenantList[0].id;
      }
      
      // Use default tenant if specified and available
      if (defaultTenantId && tenantList.some(t => t.id === defaultTenantId)) {
        selectedTenantId = defaultTenantId;
      }
      
      setState({
        tenants: tenantList,
        isMultiTenant,
        isLoading: false,
        error: null,
        selectedTenantId,
      });
      
      onTenantModeDetected?.(isMultiTenant);
    } catch (error) {
      console.error('Failed to load tenants:', error);
      
      // Graceful fallback - continue without tenant selection
      // This preserves the existing login experience for single-tenant deployments
      setState({
        tenants: [],
        isMultiTenant: false,
        isLoading: false,
        error: null, // Don't show error to user - just hide tenant selector
        selectedTenantId: defaultTenantId || null,
      });
      
      onTenantModeDetected?.(false);
    }
  }, [autoSelectSingleTenant, defaultTenantId, onTenantModeDetected, state.selectedTenantId]);

  useEffect(() => {
    loadTenants();
  }, []);

  const selectTenant = useCallback((tenantId: string) => {
    setState(prev => ({ ...prev, selectedTenantId: tenantId }));
  }, []);

  const refreshTenants = useCallback(async () => {
    await loadTenants();
  }, [loadTenants]);

  // Determine if tenant selector should be shown
  const shouldShowTenantSelector = 
    showTenantSelector !== undefined 
      ? showTenantSelector 
      : state.isMultiTenant && state.tenants.length > 1;

  return {
    ...state,
    selectTenant,
    refreshTenants,
    shouldShowTenantSelector,
  };
}

/**
 * Component that wraps login form to preserve existing experience
 */
interface LoginExperiencePreserverProps {
  children: (props: UseLoginExperienceReturn) => React.ReactNode;
  config?: LoginExperienceConfig;
}

export const LoginExperiencePreserver: React.FC<LoginExperiencePreserverProps> = ({
  children,
  config,
}) => {
  const loginExperience = useLoginExperience(config);
  return <>{children(loginExperience)}</>;
};

/**
 * Utility function to get login credentials with tenant support
 */
export function prepareLoginCredentials(
  username: string,
  password: string,
  tenantId?: string | null,
  isMultiTenant?: boolean
): { username: string; password: string; tenant_id?: string } {
  const credentials: { username: string; password: string; tenant_id?: string } = {
    username,
    password,
  };

  // Only include tenant_id if in multi-tenant mode and tenant is selected
  if (isMultiTenant && tenantId) {
    credentials.tenant_id = tenantId;
  }

  return credentials;
}

/**
 * Utility to check if the deployment is multi-tenant
 */
export async function checkMultiTenantMode(): Promise<boolean> {
  try {
    const tenants = await authService.getTenants();
    return tenants.length > 1;
  } catch {
    return false;
  }
}

export default LoginExperiencePreserver;
